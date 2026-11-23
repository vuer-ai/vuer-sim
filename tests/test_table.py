import json

import pytest

from vuer_sim import MaterialTable, PhysicsMaterial, SensorMaterial
from vuer_sim.table import SCHEMA


def sample() -> MaterialTable:
    t = MaterialTable(assign={"floor": "stone", "cup_*": "ceramic", "material:window_glass": "glass"})
    t.add(PhysicsMaterial("stone", friction=(0.6, 0.005, 0.0001), restitution=0.3, density=2400))
    t.add(PhysicsMaterial("ceramic", restitution=0.5, density=2400))
    t.add(SensorMaterial("glass", lidar_reflectivity=0.08, transparent=True))
    return t


def test_stored_form(tmp_path):
    path = sample().save(tmp_path)
    text = path.read_text()
    assert path.name == "materials.json"
    assert text.endswith("}\n") and not text.endswith("\n\n")
    data = json.loads(text)
    assert text == json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    assert data["schema"] == SCHEMA
    assert set(data["materials"]["glass"]) == {"sensor"}
    assert set(data["materials"]["stone"]) == {"physics"}


def test_load_save_round_trip(tmp_path):
    t = sample()
    t.save(tmp_path / "bundle")
    back = MaterialTable.load(tmp_path / "bundle")
    assert back == t
    assert back.dumps() == t.dumps()
    back.save(tmp_path / "again.json")
    assert (tmp_path / "again.json").read_text() == (tmp_path / "bundle" / "materials.json").read_text()


def test_validation():
    with pytest.raises(ValueError, match="unknown materials"):
        MaterialTable.from_dict({"assign": {"x": "nope"}, "materials": {}})
    with pytest.raises(ValueError, match="schema"):
        MaterialTable.from_dict({"schema": "other/2"})
    with pytest.raises(ValueError, match="unknown keys"):
        MaterialTable.from_dict({"materials": {"a": {"physic": {}}}})
    with pytest.raises(TypeError):
        MaterialTable().add("wood")  # type: ignore[arg-type]


def test_resolve_rules():
    t = MaterialTable(
        physics={n: PhysicsMaterial(n) for n in "abcde"},
        assign={"cup_1": "a", "cup_*": "b", "cup_1*": "c", "material:glass": "d", "material:gl*": "e"},
    )
    assert t.resolve("cup_1") == "a"  # exact name
    assert t.resolve("cup_12") == "c"  # longer pattern wins
    assert t.resolve("cup_2") == "b"
    assert t.resolve("lamp", "glass") == "d"  # exact visual material
    assert t.resolve("lamp", "glossy") == "e"
    assert t.resolve("cup_1", "glass") == "a"  # name beats material
    assert t.resolve("lamp") is None
