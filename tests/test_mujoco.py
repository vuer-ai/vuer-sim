"""MuJoCo smoke tests: apply a table and step a scene. Heavy: local or manual dispatch."""

from pathlib import Path

import numpy as np
import pytest

mujoco = pytest.importorskip("mujoco")

from vuer_sim import MaterialTable, PhysicsMaterial, SensorMaterial, infer_physics, lidar_returns  # noqa: E402
from vuer_sim.scene import scene_summary  # noqa: E402

pytestmark = pytest.mark.mujoco
SCENE = Path(__file__).parents[1] / "examples" / "lab_table" / "scene.xml"


def lab_table() -> MaterialTable:
    t = MaterialTable()
    for name in (
        "concrete_floor",
        "oak_wood",
        "porcelain",
        "window_glass",
        "black_rubber",
        "brushed_steel",
        "abs_plastic",
        "cotton_fabric",
    ):
        g = infer_physics(name, name=name)
        g.sensor.name = name
        t.add(g.material, g.sensor)
        t.assign[f"material:{name}"] = name
    return t


def test_apply_to_spec_and_step():
    spec = mujoco.MjSpec.from_file(str(SCENE))
    table = lab_table()
    report = table.apply(spec)
    assert report.assigned["table_top"] == "oak_wood"
    assert report.assigned["ball"] == "black_rubber"
    assert not report.warnings
    model = spec.compile()
    gid = model.geom("can_body").id
    assert model.geom_friction[gid][0] == pytest.approx(0.6)
    assert model.geom_solref[gid][1] == pytest.approx(table.physics["brushed_steel"].solref[1])
    # Density reached the inertia: steel can of r 0.033, h 0.12.
    assert model.body("can").mass[0] == pytest.approx(7850 * np.pi * 0.033**2 * 0.12, rel=1e-6)
    data = mujoco.MjData(model)
    for _ in range(1500):
        mujoco.mj_step(model, data)
    assert np.isfinite(data.qpos).all()
    assert data.body("mug").xpos[2] == pytest.approx(0.81, abs=0.01)  # resting on the table
    assert data.body("ball").xpos[2] == pytest.approx(0.766 + 0.035, abs=0.005)  # on the mat


def test_apply_to_compiled_model_round_trip():
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    table = lab_table()
    report = table.apply(model)
    assert "density is not applied" in report.warnings[0]
    gid = model.geom("mug_body").id
    back = PhysicsMaterial.from_model(model, gid)
    want = table.physics["porcelain"]
    assert back.friction == pytest.approx(want.friction)
    assert back.restitution == pytest.approx(want.restitution)
    assert table.assignments(model)[gid] == "porcelain"


def test_stability_warning():
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    t = MaterialTable(
        physics={"bouncy": PhysicsMaterial("bouncy", restitution=0.95)}, assign={"ball": "bouncy"}
    )
    assert any("timestep" in w for w in t.apply(model).warnings)


def bounce(e: float, timestep: float = 0.002, timeconst: float = 0.02, v0: float = 2.0) -> float:
    mat = PhysicsMaterial("m", restitution=e, solref=(timeconst, 1.0))
    t = MaterialTable(physics={"m": mat}, assign={"*": "m"})
    spec = mujoco.MjSpec.from_string(
        f"""<mujoco><option timestep="{timestep}" gravity="0 0 0"/><worldbody>
        <geom name="ground" type="plane" size="1 1 .1"/>
        <body pos="0 0 0.06"><freejoint/><geom name="ball" size="0.05"/></body></worldbody></mujoco>"""
    )
    t.apply(spec)
    model = spec.compile()
    data = mujoco.MjData(model)
    data.qvel[2] = -v0
    touched = False
    for _ in range(4000):
        mujoco.mj_step(model, data)
        touched = touched or data.ncon > 0
        if touched and data.ncon == 0:
            return float(data.qvel[2] / v0)
    raise AssertionError("no bounce")


@pytest.mark.parametrize("e", [0.2, 0.4, 0.6, 0.8])
def test_measured_restitution(e):
    """Within 0.12 of the target at the default timeconst and a 2 ms step (the documented limit)."""
    assert bounce(e) == pytest.approx(e, abs=0.12)


def test_measured_restitution_small_timestep():
    assert bounce(0.9, timestep=0.0005) == pytest.approx(0.9, abs=0.03)


def test_lidar_on_scene():
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    table = lab_table()
    arrays = table.sensor_arrays(model)
    window = model.geom("window").id
    assert arrays.transparent[window]
    n = 2000
    directions = np.tile([0.0, 1.0, 0.0], (n, 1))  # straight at the window
    geom, dist = np.zeros(n, np.int32), np.zeros(n)
    mujoco.mj_multiRay(
        model, data, np.array([0.0, 0.0, 1.2]), directions.reshape(-1), None, 1, -1, geom, dist, None, n, 40.0
    )
    assert (geom == window).all()
    out = lidar_returns(geom, dist, arrays, rng=0)
    assert out.valid.mean() == pytest.approx(0.08, abs=0.03)


def test_scene_summary():
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    geoms = scene_summary(model)
    names = {g["name"]: g for g in geoms}
    assert names["table_top"]["material"] == "oak_wood"
    assert names["table_top"]["pos"] == pytest.approx([0, 0, 0.74])
    assert names["floor"]["type"] == "plane"
    assert len(geoms) == model.ngeom


def test_sensor_default_for_unassigned():
    model = mujoco.MjModel.from_xml_path(str(SCENE))
    t = MaterialTable(sensor={"s": SensorMaterial("s", dropout=1.0)}, assign={"ball": "s"})
    arrays = t.sensor_arrays(model)
    assert arrays.dropout[model.geom("ball").id] == 1.0
    assert arrays.dropout[model.geom("floor").id] == 0.0
