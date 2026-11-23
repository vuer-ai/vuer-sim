"""MJCF <-> PhysicsMaterial <-> USD round trips (mjcPhysics names, MuJoCo 4.0.1).

Needs pxr (usd-core): heavy, local only.
"""

import xml.etree.ElementTree as ET

import pytest

pytest.importorskip("pxr")
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade  # noqa: E402

from vuer_sim import PhysicsMaterial, SensorMaterial  # noqa: E402
from vuer_sim.usd import MJC_SCHEMA_VERSION, authored_api_schemas, bind  # noqa: E402

pytestmark = pytest.mark.usd

MATERIAL = PhysicsMaterial(
    "rubber",
    friction=(0.9, 0.01, 0.001),
    restitution=0.7,
    density=1200,
    solimp=(0.95, 0.99, 0.001, 0.5, 2),
    condim=4,
    priority=1,
    margin=0.001,
    gap=0.0005,
)


def approx_equal(a: PhysicsMaterial, b: PhysicsMaterial, rel=1e-6):
    for key in ("friction", "solref", "solimp"):
        assert getattr(a, key) == pytest.approx(getattr(b, key), rel=rel), key
    for key in ("restitution", "density", "margin", "gap"):
        assert getattr(a, key) == pytest.approx(getattr(b, key), rel=rel, abs=1e-7), key
    assert (a.condim, a.priority) == (b.condim, b.priority)


def stage(meters_per_unit=1.0, kg_per_unit=1.0):
    s = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(s, meters_per_unit)
    UsdPhysics.SetStageKilogramsPerUnit(s, kg_per_unit)
    return s


def with_collider(mat: PhysicsMaterial, s=None):
    s = s or stage()
    cube = UsdGeom.Cube.Define(s, "/World/ball")
    mat.to_usd(s, "/Materials/rubber", colliders=[cube.GetPrim()])
    return s, cube.GetPrim()


def test_pinned_schema_version():
    assert MJC_SCHEMA_VERSION == "4.0.1"


def test_attribute_names_follow_mjcphysics():
    s, collider = with_collider(MATERIAL)
    material = s.GetPrimAtPath("/Materials/rubber")
    assert {"PhysicsMaterialAPI", "MjcMaterialAPI"} <= set(authored_api_schemas(material))
    assert {"PhysicsCollisionAPI", "MjcCollisionAPI", "MaterialBindingAPI"} <= set(
        authored_api_schemas(collider)
    )
    get = lambda p, n: p.GetAttribute(n).Get()  # noqa: E731
    assert get(material, "physics:dynamicFriction") == pytest.approx(0.9)
    assert get(material, "mjc:torsionalfriction") == pytest.approx(0.01)
    assert get(material, "mjc:rollingfriction") == pytest.approx(0.001)
    assert get(material, "newton:torsionalFriction") == pytest.approx(0.01)
    assert get(material, "newton:rollingFriction") == pytest.approx(0.001)
    assert list(get(collider, "mjc:solref")) == pytest.approx(list(MATERIAL.solref))
    assert list(get(collider, "mjc:solimp")) == pytest.approx(list(MATERIAL.solimp))
    assert get(collider, "mjc:condim") == 4 and get(collider, "mjc:priority") == 1
    assert get(collider, "mjc:margin") == pytest.approx(0.001)
    assert get(collider, "mjc:gap") == pytest.approx(0.0005)
    assert get(collider, "newton:contactMargin") == pytest.approx(0.001)
    assert get(collider, "newton:contactGap") == pytest.approx(0.0005)
    # Only sensor fields are custom: no vuersim: attribute on a physics-only material.
    names = [a.GetName() for p in (material, collider) for a in p.GetAttributes()]
    assert not [n for n in names if n.startswith("vuersim:")]


def test_usd_round_trip_through_collider():
    _, collider = with_collider(MATERIAL)
    back = PhysicsMaterial.from_usd(collider)
    assert back.name == "rubber"
    approx_equal(back, MATERIAL)


def test_mjcf_usd_mjcf_round_trip():
    el = ET.Element("geom", MATERIAL.to_mjcf())
    from_mjcf = PhysicsMaterial.from_mjcf(el, name="rubber")
    _, collider = with_collider(from_mjcf)
    from_usd = PhysicsMaterial.from_usd(collider)
    again = PhysicsMaterial.from_mjcf(ET.Element("geom", from_usd.to_mjcf()), name="rubber")
    approx_equal(again, MATERIAL)


def test_material_prim_alone():
    """A material prim carries friction, restitution and density; the rest is per collider."""
    s = stage()
    MATERIAL.to_usd(s, "/Materials/rubber")
    back = PhysicsMaterial.from_usd(s.GetPrimAtPath("/Materials/rubber"))
    assert back.friction == pytest.approx(MATERIAL.friction)
    assert back.restitution == pytest.approx(0.7)
    assert back.density == pytest.approx(1200)
    assert (back.condim, back.priority, back.margin, back.gap) == (3, 0, 0.0, 0.0)


def test_units_centimetres_and_grams():
    s = stage(meters_per_unit=0.01, kg_per_unit=0.001)
    MATERIAL.to_usd(s, "/M/rubber")
    api = UsdPhysics.MaterialAPI(s.GetPrimAtPath("/M/rubber"))
    assert api.GetDensityAttr().Get() == pytest.approx(1.2)  # 1200 kg/m^3 = 1.2 g/cm^3
    assert PhysicsMaterial.from_usd(s.GetPrimAtPath("/M/rubber")).density == pytest.approx(1200)


def test_mujoco_exporter_style_newton_only():
    """MuJoCo 4.0.1's exporter writes the newton: names only; we read them."""
    s = stage()
    mat = UsdShade.Material.Define(s, "/Looks/steel")
    prim = mat.GetPrim()
    UsdPhysics.MaterialAPI.Apply(prim).CreateDynamicFrictionAttr(0.6)
    prim.AddAppliedSchema("MjcMaterialAPI")
    from pxr import Sdf

    prim.CreateAttribute("newton:torsionalFriction", Sdf.ValueTypeNames.Float).Set(0.02)
    prim.CreateAttribute("newton:rollingFriction", Sdf.ValueTypeNames.Float).Set(0.003)
    cube = UsdGeom.Cube.Define(s, "/World/can").GetPrim()
    bind(cube, mat)
    cube.CreateAttribute("mjc:solref", Sdf.ValueTypeNames.DoubleArray).Set([0.01, 0.5])
    cube.CreateAttribute("newton:contactMargin", Sdf.ValueTypeNames.Float).Set(0.002)
    got = PhysicsMaterial.from_usd(cube)
    assert got.friction == pytest.approx((0.6, 0.02, 0.003))
    assert got.solref == pytest.approx((0.01, 0.5))
    assert got.margin == pytest.approx(0.002)


def test_mjc_wins_over_newton():
    s = stage()
    mat = UsdShade.Material.Define(s, "/Looks/m")
    prim = mat.GetPrim()
    UsdPhysics.MaterialAPI.Apply(prim)
    from pxr import Sdf

    prim.CreateAttribute("mjc:torsionalfriction", Sdf.ValueTypeNames.Double).Set(0.03)
    prim.CreateAttribute("newton:torsionalFriction", Sdf.ValueTypeNames.Float).Set(0.09)
    assert PhysicsMaterial.from_usd(prim).friction[1] == pytest.approx(0.03)


def test_plain_usd_physics_material_and_binding():
    """A material written by another tool: only UsdPhysics attributes, bound with purpose physics."""
    s = stage(meters_per_unit=0.01)
    mat = UsdShade.Material.Define(s, "/Looks/oak")
    api = UsdPhysics.MaterialAPI.Apply(mat.GetPrim())
    api.CreateDynamicFrictionAttr(0.4)
    api.CreateStaticFrictionAttr(0.5)
    api.CreateRestitutionAttr(0.5)
    api.CreateDensityAttr(0.0007)  # kg/cm^3
    cube = UsdGeom.Cube.Define(s, "/World/table")
    bind(cube.GetPrim(), mat)
    got = PhysicsMaterial.from_usd(cube.GetPrim())
    assert got.name == "oak"
    assert got.friction == pytest.approx((0.4, 0.005, 0.0001))
    assert got.restitution == pytest.approx(0.5)
    assert got.density == pytest.approx(700)
    assert got.extra["static_friction"] == pytest.approx(0.5)


def test_unbound_prim_returns_none():
    s = stage()
    cube = UsdGeom.Cube.Define(s, "/World/box")
    assert PhysicsMaterial.from_usd(cube.GetPrim()) is None


def test_unset_density_keeps_default():
    s = stage()
    mat = UsdShade.Material.Define(s, "/M/x")
    UsdPhysics.MaterialAPI.Apply(mat.GetPrim()).CreateDynamicFrictionAttr(0.0)
    got = PhysicsMaterial.from_usd(mat.GetPrim())
    assert got.density == 1000 and got.friction[0] == 0.0


def test_sensor_material_round_trip():
    s, collider = with_collider(MATERIAL)
    glass = SensorMaterial(
        "rubber", lidar_reflectivity=0.08, intensity=12, dropout=0.1, transparent=True, depth_noise_std=0.01
    )
    glass.to_usd(s, "/Materials/rubber")
    material = s.GetPrimAtPath("/Materials/rubber")
    assert material.GetAttribute("vuersim:lidarReflectivity").Get() == pytest.approx(0.08)
    assert SensorMaterial.from_usd(collider) == glass  # through the physics binding
    assert SensorMaterial.from_usd(UsdGeom.Cube.Define(s, "/World/other").GetPrim()) is None
