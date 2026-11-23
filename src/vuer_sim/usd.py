"""USD converters for ``PhysicsMaterial`` and ``SensorMaterial``.

Needs ``pxr``: ``pip install 'vuer-sim[usd]'`` (the ``usd-core`` wheel).

The attribute names follow MuJoCo's own USD schema, ``mjcPhysics``, pinned at
**MuJoCo 4.0.1** (``src/experimental/usd/mjcPhysics/schema.usda``), and what
MuJoCo's USD exporter (``mujoco_to_usd.cc``) and importer (``usd_decoder.cc``)
read and write at that version. The schema puts the parameters on two prims:

Material prim (``UsdShade.Material``, ``PhysicsMaterialAPI`` + ``MjcMaterialAPI``)
================================  ===================================================
PhysicsMaterial                   USD attribute
================================  ===================================================
``friction[0]`` (slide)           ``physics:dynamicFriction`` (and
                                  ``physics:staticFriction``, for PhysX)
``friction[1]`` (torsion)         ``mjc:torsionalfriction`` + ``newton:torsionalFriction``
``friction[2]`` (roll)            ``mjc:rollingfriction`` + ``newton:rollingFriction``
``restitution``                   ``physics:restitution`` (MuJoCo's importer ignores it;
                                  the bounce travels in ``mjc:solref`` below)
``density`` (kg/m^3)              ``physics:density`` in stage units:
                                  ``kg/m^3 * metersPerUnit^3 / kilogramsPerUnit``
================================  ===================================================

Collider prim (``PhysicsCollisionAPI`` + ``MjcCollisionAPI``; written by ``bind``)
================================  ===================================================
``solref``, ``solimp``            ``mjc:solref``, ``mjc:solimp``
``condim``, ``priority``          ``mjc:condim``, ``mjc:priority``
``margin``, ``gap``               ``mjc:margin`` + ``newton:contactMargin``,
                                  ``mjc:gap`` + ``newton:contactGap``
================================  ===================================================

At 4.0.1 the schema marks ``mjc:torsionalfriction``, ``mjc:rollingfriction``,
``mjc:margin`` and ``mjc:gap`` as deprecated in favour of the ``newton:`` names.
vuer-sim writes both with the same value: MuJoCo's importer reads the ``mjc:``
value first and does not warn when the ``newton:`` twin is also there. On
read, ``mjc:`` wins, then ``newton:``.

``SensorMaterial`` has no MuJoCo equivalent. It goes on the material prim under
``vuersim:`` (``vuersim:lidarReflectivity``, ``vuersim:lidarIntensity``,
``vuersim:dropout``, ``vuersim:transparent``, ``vuersim:depthNoiseStd``).
"""

from __future__ import annotations

from typing import Any

from .physics import DEFAULT_FRICTION, DEFAULT_SOLIMP, DEFAULT_SOLREF, PhysicsMaterial
from .sensor import SensorMaterial

#: MuJoCo version whose ``mjcPhysics`` schema these names come from.
MJC_SCHEMA_VERSION = "4.0.1"
NS = "vuersim"
MATERIAL_API = "MjcMaterialAPI"
COLLISION_API = "MjcCollisionAPI"


def _pxr():
    try:
        from pxr import Sdf, Usd, UsdGeom, UsdPhysics, UsdShade
    except ImportError as e:  # pragma: no cover - depends on the extra
        raise ImportError("vuer_sim.usd needs pxr: pip install 'vuer-sim[usd]'") from e
    return Sdf, Usd, UsdGeom, UsdPhysics, UsdShade


def _units(stage: Any) -> tuple[float, float]:
    """(metersPerUnit, kilogramsPerUnit) of a stage."""
    _, _, UsdGeom, UsdPhysics, _ = _pxr()
    return float(UsdGeom.GetStageMetersPerUnit(stage)), float(UsdPhysics.GetStageKilogramsPerUnit(stage))


def _apply_api(prim: Any, name: str) -> None:
    """Add an applied API schema by name. ``usd-core`` has no mjcPhysics plugin,
    so the schema is added to ``apiSchemas`` as a token, as MuJoCo's exporter does."""
    prim.AddAppliedSchema(name)  # idempotent; GetAppliedSchemas() hides unregistered names


def authored_api_schemas(prim: Any) -> list[str]:
    """API schema tokens authored on ``prim``, registered or not (``mjc*`` included)."""
    ops = prim.GetMetadata("apiSchemas")
    return list(ops.GetAddedOrExplicitItems()) if ops else []


def _set(prim: Any, name: str, type_name: Any, value: Any) -> None:
    attr = prim.CreateAttribute(name, type_name, custom=False)
    attr.SetVariability(_pxr()[0].VariabilityUniform)
    attr.Set(value)


def _get(prim: Any, *names: str) -> Any:
    """Value of the first authored attribute among ``names``, else ``None``."""
    for name in names:
        attr = prim.GetAttribute(name)
        if attr and attr.HasAuthoredValue():
            return attr.Get()
    return None


# --------------------------------------------------------------------- write


def write_physics_material(mat: PhysicsMaterial, stage: Any, path: str) -> Any:
    """Define (or update) a material prim at ``path``. Return the ``UsdShade.Material``."""
    Sdf, _, _, UsdPhysics, UsdShade = _pxr()
    material = UsdShade.Material.Define(stage, path)
    prim = material.GetPrim()
    api = UsdPhysics.MaterialAPI.Apply(prim)
    _apply_api(prim, MATERIAL_API)
    mpu, kpu = _units(stage)
    api.CreateDynamicFrictionAttr().Set(float(mat.friction[0]))
    api.CreateStaticFrictionAttr().Set(float(mat.friction[0]))
    api.CreateRestitutionAttr().Set(float(mat.restitution or 0.0))
    api.CreateDensityAttr().Set(float(mat.density) * mpu**3 / kpu)
    t = Sdf.ValueTypeNames
    _set(prim, "mjc:torsionalfriction", t.Double, float(mat.friction[1]))
    _set(prim, "mjc:rollingfriction", t.Double, float(mat.friction[2]))
    _set(prim, "newton:torsionalFriction", t.Float, float(mat.friction[1]))
    _set(prim, "newton:rollingFriction", t.Float, float(mat.friction[2]))
    return material


def write_collider(prim: Any, mat: PhysicsMaterial) -> None:
    """Write the contact parameters of ``mat`` on a collider prim (``MjcCollisionAPI``)."""
    Sdf, _, _, UsdPhysics, _ = _pxr()
    UsdPhysics.CollisionAPI.Apply(prim)
    _apply_api(prim, COLLISION_API)
    t = Sdf.ValueTypeNames
    _set(prim, "mjc:solref", t.DoubleArray, [float(v) for v in mat.solref])
    _set(prim, "mjc:solimp", t.DoubleArray, [float(v) for v in mat.solimp])
    _set(prim, "mjc:condim", t.Int, int(mat.condim))
    _set(prim, "mjc:priority", t.Int, int(mat.priority))
    _set(prim, "mjc:margin", t.Double, float(mat.margin))
    _set(prim, "mjc:gap", t.Double, float(mat.gap))
    _set(prim, "newton:contactMargin", t.Float, float(mat.margin))
    _set(prim, "newton:contactGap", t.Float, float(mat.gap))


def bind(prim: Any, material: Any, physics: PhysicsMaterial | None = None) -> None:
    """Bind ``material`` (a ``UsdShade.Material``) to ``prim`` for physics.

    With ``physics``, also write its collider parameters on ``prim`` (``write_collider``).
    """
    _, _, _, _, UsdShade = _pxr()
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(material, UsdShade.Tokens.weakerThanDescendants, "physics")
    if physics is not None:
        write_collider(prim, physics)


def write_sensor_material(mat: SensorMaterial, stage: Any, path: str) -> Any:
    """Write a ``SensorMaterial`` on the material prim at ``path`` (``vuersim:`` attributes)."""
    Sdf, _, _, _, UsdShade = _pxr()
    material = UsdShade.Material.Define(stage, path)
    prim = material.GetPrim()
    t = Sdf.ValueTypeNames
    _set(prim, f"{NS}:lidarReflectivity", t.Double, float(mat.lidar_reflectivity))
    if mat.intensity is not None:
        _set(prim, f"{NS}:lidarIntensity", t.Double, float(mat.intensity))
    _set(prim, f"{NS}:dropout", t.Double, float(mat.dropout))
    _set(prim, f"{NS}:transparent", t.Bool, bool(mat.transparent))
    _set(prim, f"{NS}:depthNoiseStd", t.Double, float(mat.depth_noise_std))
    return material


# --------------------------------------------------------------------- read


def _bound_material_prim(prim: Any) -> Any:
    _, _, _, UsdPhysics, UsdShade = _pxr()
    if prim.HasAPI(UsdPhysics.MaterialAPI) or prim.IsA(UsdShade.Material):
        return prim
    bound, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial("physics")
    return bound.GetPrim() if bound else None


def read_physics_material(prim: Any, cls: type = PhysicsMaterial, name: str | None = None) -> Any:
    """``PhysicsMaterial`` of a collider prim, or of a material prim.

    A collider prim gives everything: its ``MjcCollisionAPI`` attributes plus its
    bound physics material. A material prim alone gives friction, restitution and
    density; ``solimp``, ``condim``, ``priority``, ``margin``, ``gap`` and
    ``solref[0]`` keep the MuJoCo defaults. Returns ``None`` when there is neither
    a physics material nor ``mjc:`` collider attributes.
    """
    _, _, _, UsdPhysics, _ = _pxr()
    material_prim = _bound_material_prim(prim)
    has_material = bool(material_prim) and material_prim.HasAPI(UsdPhysics.MaterialAPI)
    collider = prim if prim != material_prim else None
    has_collider = collider is not None and _get(collider, "mjc:solref", "mjc:condim") is not None
    if not has_material and not has_collider:
        return None

    kw: dict[str, Any] = {}
    friction = list(DEFAULT_FRICTION)
    if has_material:
        api = UsdPhysics.MaterialAPI(material_prim)
        mpu, kpu = _units(material_prim.GetStage())
        slide = _get(material_prim, "physics:dynamicFriction", "physics:staticFriction")
        torsion = _get(material_prim, "mjc:torsionalfriction", "newton:torsionalFriction")
        roll = _get(material_prim, "mjc:rollingfriction", "newton:rollingFriction")
        for i, v in enumerate((slide, torsion, roll)):
            if v is not None:
                friction[i] = float(v)
        restitution = _get(material_prim, "physics:restitution")
        if restitution is not None:
            kw["restitution"] = float(restitution)
        density = api.GetDensityAttr().Get() if api.GetDensityAttr().HasAuthoredValue() else 0.0
        # UsdPhysics: density 0 means "not set" (the mass comes from elsewhere).
        if density and density > 0:
            kw["density"] = float(density) * kpu / mpu**3
    kw["friction"] = tuple(friction)

    solref = tuple(DEFAULT_SOLREF)
    if has_collider:
        assert collider is not None
        value = _get(collider, "mjc:solref")
        if value is not None:
            solref = tuple(float(v) for v in value)
            kw.pop("restitution", None)  # mjc:solref is what MuJoCo uses
        solimp = _get(collider, "mjc:solimp")
        kw["solimp"] = tuple(float(v) for v in solimp) if solimp is not None else DEFAULT_SOLIMP
        for key in ("condim", "priority"):
            v = _get(collider, f"mjc:{key}")
            if v is not None:
                kw[key] = int(v)
        for key, newton in (("margin", "newton:contactMargin"), ("gap", "newton:contactGap")):
            v = _get(collider, f"mjc:{key}", newton)
            if v is not None:
                kw[key] = float(v)
    kw["solref"] = solref
    label = name or (material_prim.GetName() if has_material else prim.GetName())
    mat = cls(name=label, **kw)
    if has_material:
        static = _get(material_prim, "physics:staticFriction")
        if static is not None and abs(float(static) - mat.friction[0]) > 1e-6:
            mat.extra["static_friction"] = float(static)
    return mat


def read_sensor_material(prim: Any, name: str | None = None) -> SensorMaterial | None:
    """``SensorMaterial`` from the ``vuersim:`` attributes of a material prim (or its binding)."""
    material_prim = _bound_material_prim(prim) or prim
    reflectivity = _get(material_prim, f"{NS}:lidarReflectivity")
    if reflectivity is None:
        return None
    return SensorMaterial(
        name=name or material_prim.GetName(),
        lidar_reflectivity=float(reflectivity),
        intensity=_get(material_prim, f"{NS}:lidarIntensity"),
        dropout=float(_get(material_prim, f"{NS}:dropout") or 0.0),
        transparent=bool(_get(material_prim, f"{NS}:transparent") or False),
        depth_noise_std=float(_get(material_prim, f"{NS}:depthNoiseStd") or 0.0),
    )
