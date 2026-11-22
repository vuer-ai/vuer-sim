"""USD converters for ``PhysicsMaterial`` (``UsdPhysics.MaterialAPI``).

Needs ``pxr``: ``pip install 'vuer-sim[usd]'`` (the ``usd-core`` wheel).

Mapping
-------
================================  ===========================================
PhysicsMaterial                   USD attribute
================================  ===========================================
``friction[0]`` (slide)           ``physics:dynamicFriction`` and
                                  ``physics:staticFriction`` (both written; the
                                  dynamic value is read, as the robot-env seed)
``restitution``                   ``physics:restitution``
``density`` (kg/m^3)              ``physics:density`` in stage units:
                                  ``kg/m^3 * metersPerUnit^3 / kilogramsPerUnit``
``friction[1:]``, ``solref[0]``,  ``vuersim:torsionalFriction``,
``solimp``, ``condim``,           ``vuersim:rollingFriction``, ``vuersim:timeconst``,
``priority``, ``margin``          ``vuersim:solimp``, ``vuersim:condim``,
                                  ``vuersim:priority``, ``vuersim:margin``
                                  (custom attributes; PhysX ignores them)
================================  ===========================================

USD stores restitution directly, so ``solref[1]`` is not written: it is
recomputed from ``physics:restitution`` on read. The material is bound with the
``physics`` purpose (``bind``), as ``UsdPhysics`` asks.
"""

from __future__ import annotations

from typing import Any

from .physics import DEFAULT_FRICTION, DEFAULT_SOLREF, PhysicsMaterial

NS = "vuersim"


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


def write_physics_material(mat: PhysicsMaterial, stage: Any, path: str) -> Any:
    """Define (or update) a physics material prim at ``path``. Return the ``UsdShade.Material``."""
    Sdf, _, _, UsdPhysics, UsdShade = _pxr()
    material = UsdShade.Material.Define(stage, path)
    prim = material.GetPrim()
    api = UsdPhysics.MaterialAPI.Apply(prim)
    mpu, kpu = _units(stage)
    api.CreateDynamicFrictionAttr().Set(float(mat.friction[0]))
    api.CreateStaticFrictionAttr().Set(float(mat.friction[0]))
    api.CreateRestitutionAttr().Set(float(mat.restitution or 0.0))
    api.CreateDensityAttr().Set(float(mat.density) * mpu**3 / kpu)
    f = Sdf.ValueTypeNames
    prim.CreateAttribute(f"{NS}:torsionalFriction", f.Double).Set(float(mat.friction[1]))
    prim.CreateAttribute(f"{NS}:rollingFriction", f.Double).Set(float(mat.friction[2]))
    prim.CreateAttribute(f"{NS}:timeconst", f.Double).Set(float(mat.solref[0]))
    prim.CreateAttribute(f"{NS}:solimp", f.DoubleArray).Set([float(v) for v in mat.solimp])
    prim.CreateAttribute(f"{NS}:condim", f.Int).Set(int(mat.condim))
    prim.CreateAttribute(f"{NS}:priority", f.Int).Set(int(mat.priority))
    prim.CreateAttribute(f"{NS}:margin", f.Double).Set(float(mat.margin))
    return material


def bind(prim: Any, material: Any) -> None:
    """Bind ``material`` (a ``UsdShade.Material``) to ``prim`` for physics."""
    _, _, _, _, UsdShade = _pxr()
    UsdShade.MaterialBindingAPI.Apply(prim).Bind(material, UsdShade.Tokens.weakerThanDescendants, "physics")


def read_physics_material(prim: Any, cls: type = PhysicsMaterial, name: str | None = None) -> Any:
    """``PhysicsMaterial`` of a material prim, or of the physics material bound to ``prim``."""
    _, _, _, UsdPhysics, UsdShade = _pxr()
    if not prim.HasAPI(UsdPhysics.MaterialAPI):
        bound, _ = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial("physics")
        if not bound or not bound.GetPrim().HasAPI(UsdPhysics.MaterialAPI):
            return None
        prim = bound.GetPrim()
    api = UsdPhysics.MaterialAPI(prim)
    mpu, kpu = _units(prim.GetStage())

    def authored(attr: Any, default: Any) -> Any:
        return attr.Get() if attr and attr.HasAuthoredValue() else default

    def custom(key: str, default: Any) -> Any:
        return authored(prim.GetAttribute(f"{NS}:{key}"), default)

    slide = authored(api.GetDynamicFrictionAttr(), None)
    if slide is None:
        slide = authored(api.GetStaticFrictionAttr(), DEFAULT_FRICTION[0])
    density = authored(api.GetDensityAttr(), 0.0)
    kw: dict[str, Any] = {
        "friction": (
            float(slide),
            float(custom("torsionalFriction", DEFAULT_FRICTION[1])),
            float(custom("rollingFriction", DEFAULT_FRICTION[2])),
        ),
        "restitution": float(authored(api.GetRestitutionAttr(), 0.0)),
        "solref": (float(custom("timeconst", DEFAULT_SOLREF[0])), DEFAULT_SOLREF[1]),
        "condim": int(custom("condim", 3)),
        "priority": int(custom("priority", 0)),
        "margin": float(custom("margin", 0.0)),
    }
    # UsdPhysics: density 0 means "not set" (the mass comes from elsewhere).
    if density and density > 0:
        kw["density"] = float(density) * kpu / mpu**3
    solimp = custom("solimp", None)
    if solimp is not None:
        kw["solimp"] = tuple(float(v) for v in solimp)
    mat = cls(name=name or prim.GetName(), **kw)
    static = authored(api.GetStaticFrictionAttr(), None)
    if static is not None and abs(float(static) - mat.friction[0]) > 1e-6:
        mat.extra["static_friction"] = float(static)
    return mat
