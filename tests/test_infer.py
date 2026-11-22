import pytest

from vuer_sim import CATEGORIES, infer_physics, lookup_table
from vuer_sim.infer import SOURCES, words


def test_words():
    assert words("OakWood_02.001") == ["oak", "wood", "02", "001"]
    assert words("BrushedMETAL") == ["brushed", "metal"]


@pytest.mark.parametrize(
    "name,category",
    [
        ("wood", "wood"),
        ("OakWood_02", "wood"),
        ("table_top_walnut", "wood"),
        ("Brushed Steel", "metal"),
        ("chrome-handle", "metal"),
        ("aluminium_frame", "aluminum"),
        ("abs_plastic_blue", "plastic"),
        ("RubberMat", "rubber"),
        ("tyre", "rubber"),
        ("window_glass", "glass"),
        ("sofa_fabric", "fabric"),
        ("Carpet01", "fabric"),
        ("porcelain_mug", "ceramic"),
        ("FloorTile", "ceramic"),
        ("concrete_floor", "stone"),
        ("cardboard_box", "paper"),
        ("foam_pad", "foam"),
        ("leather_chair", "leather"),
    ],
)
def test_name_lookup(name, category):
    got = infer_physics(name)
    assert got.category == category
    assert got.confidence > 0
    assert got.sources


def test_whole_word_beats_substring():
    assert infer_physics("oak").confidence > infer_physics("oakwoodish").confidence
    assert infer_physics("apple").category == "unknown"  # "pp" is a plastic keyword, not a substring match


def test_values_come_from_table():
    wood = next(c for c in CATEGORIES if c.name == "wood")
    got = infer_physics("wood")
    assert got.material.friction[0] == wood.friction
    assert got.material.density == wood.density
    assert got.material.restitution == pytest.approx(wood.restitution)
    lo, hi = got.ranges["friction"]
    assert lo <= got.material.friction[0] <= hi


def test_every_category_is_consistent():
    for row in lookup_table():
        for key in ("friction", "density", "restitution"):
            lo, hi = row[f"{key}_range"]
            assert lo <= row[key] <= hi, (row["category"], key)
        assert 0 < row["confidence"] <= 1
        assert all(s in SOURCES.values() for s in row["sources"])


def test_pbr_rules():
    metal = infer_physics({"name": "Material.003", "metallic": 1.0, "roughness": 0.3})
    assert metal.category == "metal" and metal.confidence == pytest.approx(0.36)
    glass = infer_physics({"name": "", "base_color": (0.9, 0.9, 1.0, 0.2)})
    assert glass.category == "glass" and glass.sensor.transparent
    named = infer_physics({"name": "rubber", "metallic": 1.0})
    assert named.category == "rubber"  # the name wins


def test_unknown_gives_mujoco_defaults():
    got = infer_physics("Material.001")
    assert got.category == "unknown" and got.confidence == 0
    assert got.material.friction == (1.0, 0.005, 0.0001) and got.material.density == 1000


def test_dark_base_colour_lowers_reflectivity():
    light = infer_physics({"name": "plastic", "base_color": (1, 1, 1)})
    dark = infer_physics({"name": "plastic", "base_color": (10, 10, 10)})
    assert dark.sensor.lidar_reflectivity < 0.1 < light.sensor.lidar_reflectivity


def test_docs_table_matches_lookup_table():
    from pathlib import Path

    page = Path(__file__).parents[1] / "docs" / "pages" / "guides" / "inference" / "+Page.mdx"
    if not page.exists():
        pytest.skip("docs not present")
    text = page.read_text()
    for r in lookup_table():

        def cell(k, r=r):
            return f"{r[k]:g} ({r[k + '_range'][0]:g}–{r[k + '_range'][1]:g})"

        row = (
            f"| {r['category']} | {', '.join(r['keywords'][:5])} | {cell('friction')} | "
            f"{cell('density')} | {cell('restitution')} |"
        )
        assert row in text, f"docs table out of date for {r['category']}"
