"""MJCF <-> PhysicsMaterial <-> USD round trips. Needs pxr (usd-core): heavy, local only."""

import xml.etree.ElementTree as ET

import pytest

pytest.importorskip("pxr")
from pxr import Usd, UsdGeom, UsdPhysics, UsdShade  # noqa: E402

from vuer_sim import PhysicsMaterial  # noqa: E402
from vuer_sim.usd import bind  # noqa: E402

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
)


def approx_equal(a: PhysicsMaterial, b: PhysicsMaterial, rel=1e-6):
    for key in ("friction", "solref", "solimp"):
        assert getattr(a, key) == pytest.approx(getattr(b, key), rel=rel), key
    for key in ("restitution", "density", "margin"):
        assert getattr(a, key) == pytest.approx(getattr(b, key), rel=rel, abs=1e-7), key
    assert (a.condim, a.priority) == (b.condim, b.priority)


def stage(meters_per_unit=1.0, kg_per_unit=1.0):
    s = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageMetersPerUnit(s, meters_per_unit)
    UsdPhysics.SetStageKilogramsPerUnit(s, kg_per_unit)
    return s


def test_usd_round_trip():
    s = stage()
    MATERIAL.to_usd(s, "/Materials/rubber")
    back = PhysicsMaterial.from_usd(s.GetPrimAtPath("/Materials/rubber"))
    assert back.name == "rubber"
    approx_equal(back, MATERIAL)


def test_mjcf_usd_mjcf_round_trip():
    el = ET.Element("geom", MATERIAL.to_mjcf())
    from_mjcf = PhysicsMaterial.from_mjcf(el, name="rubber")
    s = stage()
    from_mjcf.to_usd(s, "/M/rubber")
    from_usd = PhysicsMaterial.from_usd(s.GetPrimAtPath("/M/rubber"))
    again = PhysicsMaterial.from_mjcf(ET.Element("geom", from_usd.to_mjcf()), name="rubber")
    approx_equal(again, MATERIAL)


def test_units_centimetres_and_grams():
    s = stage(meters_per_unit=0.01, kg_per_unit=0.001)
    MATERIAL.to_usd(s, "/M/rubber")
    api = UsdPhysics.MaterialAPI(s.GetPrimAtPath("/M/rubber"))
    # 1200 kg/m^3 = 1.2 g/cm^3
    assert api.GetDensityAttr().Get() == pytest.approx(1.2)
    assert PhysicsMaterial.from_usd(s.GetPrimAtPath("/M/rubber")).density == pytest.approx(1200)


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
