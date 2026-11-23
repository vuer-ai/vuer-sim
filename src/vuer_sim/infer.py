"""Visual material -> physics material: a documented lookup table.

``infer_physics("OakWood_02")`` or ``infer_physics({"name": ..., "metallic": 1.0})``
returns an ``Inferred`` with a ``PhysicsMaterial``, the matched category, the
match and a ``confidence`` in [0, 1].

The values are typical values for a dry contact of the material against a hard
surface, with the range that the sources give. They are a starting point for a
scene, not measurements of your objects. Sources (``SOURCES``):

* ``et-friction``: Engineering ToolBox, *Friction and Friction Coefficients for
  some Common Materials*.
* ``et-density``: Engineering ToolBox, *Densities of Solids*.
* ``wiki-friction``: Wikipedia, *Friction*, table of approximate coefficients.
* ``wiki-cor``: Wikipedia, *Coefficient of restitution*, and R. Cross, *The
  bounce of a ball*, Am. J. Phys. 67, 222 (1999). Restitution depends strongly
  on the impact speed and on the other body, so its confidence is lower.

``confidence`` is the confidence of the category values (``Category.confidence``)
times the quality of the match: 1.0 for a whole word of the name, 0.8 for a part
of a word, 0.6 for a guess from PBR parameters only. No match gives the MuJoCo
defaults with confidence 0.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .physics import PhysicsMaterial
from .sensor import SensorMaterial

SOURCES = {
    "et-friction": "https://www.engineeringtoolbox.com/friction-coefficients-d_778.html",
    "et-density": "https://www.engineeringtoolbox.com/density-solids-d_1265.html",
    "wiki-friction": "https://en.wikipedia.org/wiki/Friction#Approximate_coefficients_of_friction",
    "wiki-cor": "https://en.wikipedia.org/wiki/Coefficient_of_restitution",
}


@dataclass(frozen=True)
class Category:
    """Typical values of one material category, with (low, high) ranges."""

    name: str
    keywords: tuple[str, ...]
    friction: float
    friction_range: tuple[float, float]
    density: float
    density_range: tuple[float, float]
    restitution: float
    restitution_range: tuple[float, float]
    confidence: float
    sources: tuple[str, ...] = ("et-friction", "et-density", "wiki-cor")
    # Sensor assumptions (not from the sources above): diffuse reflectivity at
    # 905 nm and whether LiDAR and depth cameras see through the surface.
    lidar_reflectivity: float = 0.5
    transparent: bool = False
    note: str = ""


CATEGORIES: tuple[Category, ...] = (
    Category(
        "wood",
        (
            "wood",
            "wooden",
            "oak",
            "pine",
            "maple",
            "walnut",
            "birch",
            "plywood",
            "mdf",
            "timber",
            "parquet",
            "bamboo",
            "teak",
            "cherry",
            "ash",
        ),
        0.4,
        (0.25, 0.5),
        700,
        (500, 900),
        0.5,
        (0.4, 0.6),
        0.6,
        lidar_reflectivity=0.5,
        note="wood on wood, clean and dry; pine 500 to oak 900 kg/m^3",
    ),
    Category(
        "metal",
        (
            "metal",
            "metallic",
            "steel",
            "iron",
            "chrome",
            "stainless",
            "brass",
            "copper",
            "nickel",
            "bronze",
            "tin",
        ),
        0.6,
        (0.5, 0.8),
        7850,
        (7700, 8900),
        0.6,
        (0.5, 0.8),
        0.6,
        lidar_reflectivity=0.6,
        note="steel on steel, dry; copper and brass reach 8900 kg/m^3",
    ),
    Category(
        "aluminum",
        ("aluminum", "aluminium", "alu", "anodized"),
        0.6,
        (0.45, 1.05),
        2700,
        (2640, 2810),
        0.5,
        (0.4, 0.7),
        0.6,
        lidar_reflectivity=0.6,
        note="aluminium on steel 0.47-0.61, on aluminium up to 1.05",
    ),
    Category(
        "plastic",
        (
            "plastic",
            "abs",
            "pvc",
            "polypropylene",
            "polyethylene",
            "nylon",
            "polymer",
            "vinyl",
            "pet",
            "polycarbonate",
            "pp",
            "hdpe",
            "pla",
        ),
        0.35,
        (0.2, 0.5),
        1050,
        (900, 1400),
        0.5,
        (0.3, 0.7),
        0.4,
        lidar_reflectivity=0.4,
        note="polyethylene on steel 0.2, ABS and nylon higher",
    ),
    Category(
        "rubber",
        ("rubber", "silicone", "latex", "tire", "tyre", "neoprene", "elastomer"),
        0.9,
        (0.6, 1.2),
        1200,
        (920, 1500),
        0.7,
        (0.5, 0.9),
        0.5,
        lidar_reflectivity=0.05,
        note="rubber on dry concrete 0.6-0.85; soft rubber exceeds 1",
    ),
    Category(
        "glass",
        ("glass", "window", "glazing", "crystal", "pyrex"),
        0.5,
        (0.4, 1.0),
        2500,
        (2400, 2800),
        0.6,
        (0.5, 0.7),
        0.5,
        lidar_reflectivity=0.08,
        transparent=True,
        note="clean glass on glass is 0.9-1.0, any film lowers it; glass on metal 0.5-0.7",
    ),
    Category(
        "fabric",
        (
            "fabric",
            "cloth",
            "textile",
            "cotton",
            "linen",
            "wool",
            "felt",
            "carpet",
            "rug",
            "upholstery",
            "velvet",
            "denim",
            "canvas",
            "towel",
        ),
        0.5,
        (0.3, 0.7),
        300,
        (100, 600),
        0.1,
        (0.0, 0.2),
        0.3,
        lidar_reflectivity=0.4,
        note="bulk density of folded or padded cloth; the fibre is ~1500",
    ),
    Category(
        "ceramic",
        ("ceramic", "porcelain", "tile", "clay", "terracotta", "stoneware", "earthenware", "china", "mug"),
        0.5,
        (0.4, 0.7),
        2400,
        (2000, 2500),
        0.5,
        (0.3, 0.6),
        0.5,
        lidar_reflectivity=0.7,
    ),
    Category(
        "stone",
        ("stone", "concrete", "granite", "marble", "cement", "brick", "rock", "slate", "plaster", "asphalt"),
        0.6,
        (0.5, 0.8),
        2400,
        (1800, 2800),
        0.3,
        (0.2, 0.5),
        0.5,
        lidar_reflectivity=0.3,
        note="concrete 2300-2400, granite and marble 2600-2800, brick 1800",
    ),
    Category(
        "paper",
        ("paper", "cardboard", "carton", "paperboard", "book"),
        0.4,
        (0.3, 0.5),
        700,
        (100, 1150),
        0.2,
        (0.1, 0.4),
        0.3,
        lidar_reflectivity=0.8,
        note="sheet paper 700-1150; an empty cardboard box is far lighter",
    ),
    Category(
        "foam",
        ("foam", "sponge", "styrofoam", "polystyrene", "eva"),
        0.7,
        (0.5, 1.0),
        50,
        (20, 100),
        0.2,
        (0.1, 0.4),
        0.3,
        lidar_reflectivity=0.6,
    ),
    Category(
        "leather",
        ("leather", "suede"),
        0.6,
        (0.4, 0.7),
        860,
        (800, 950),
        0.3,
        (0.2, 0.4),
        0.4,
        lidar_reflectivity=0.2,
        note="leather on wood about 0.6",
    ),
)

# MuJoCo defaults: what an unknown material gets.
UNKNOWN = Category("unknown", (), 1.0, (0.0, 2.0), 1000, (1, 20000), 0.0, (0.0, 1.0), 0.0, sources=())

_WORD = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])|\d+")


@dataclass
class Inferred:
    """Result of ``infer_physics``."""

    material: PhysicsMaterial
    category: str
    confidence: float
    matched: str = ""  # the keyword or rule that matched
    sources: tuple[str, ...] = ()
    ranges: dict[str, tuple[float, float]] = field(default_factory=dict)
    sensor: SensorMaterial | None = None


def words(name: str) -> list[str]:
    """Lower-case words of a name: ``"OakWood_02.001"`` -> ``["oak", "wood", "02", "001"]``."""
    return [w.lower() for w in _WORD.findall(name or "")]


def match_category(name: str) -> tuple[Category, str, float]:
    """(category, keyword, match quality) for a material name; ``UNKNOWN`` when nothing matches."""
    ws = words(name)
    for cat in CATEGORIES:  # whole words first
        for kw in cat.keywords:
            if kw in ws:
                return cat, kw, 1.0
    joined = "".join(ws)
    best: tuple[Category, str] | None = None
    for cat in CATEGORIES:  # then a long keyword inside a word ("oakwood")
        for kw in cat.keywords:
            if len(kw) >= 4 and kw in joined and (best is None or len(kw) > len(best[1])):
                best = (cat, kw)
    if best:
        return best[0], best[1], 0.8
    return UNKNOWN, "", 0.0


def _pbr(pbr: Any) -> dict[str, Any]:
    if isinstance(pbr, str):
        return {"name": pbr}
    if isinstance(pbr, Mapping):
        return dict(pbr)
    return {k: getattr(pbr, k) for k in dir(pbr) if not k.startswith("_")}


def _luminance(color: Any) -> float | None:
    if color is None:
        return None
    c = [float(v) for v in list(color)[:3]]
    if max(c) > 1.0:
        c = [v / 255.0 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def infer_physics(pbr_or_name: Any, name: str | None = None) -> Inferred:
    """Guess a ``PhysicsMaterial`` from a material name or PBR parameters.

    ``pbr_or_name`` is a name, or a mapping or object with any of ``name``,
    ``base_color`` (RGB or RGBA, 0-1 or 0-255), ``metallic``, ``roughness``,
    ``opacity`` and ``transmission``. The name wins over the PBR rules.
    ``name`` sets the name of the returned material.
    """
    p = _pbr(pbr_or_name)
    cat, matched, quality = match_category(str(p.get("name", "")))
    if cat is UNKNOWN:
        metallic = float(p.get("metallic", 0.0) or 0.0)
        transmission = float(p.get("transmission", 0.0) or 0.0)
        opacity = p.get("opacity")
        if opacity is None and p.get("base_color") is not None and len(list(p["base_color"])) == 4:
            opacity = list(p["base_color"])[3]
        if metallic >= 0.5:
            cat, matched, quality = _cat("metal"), "metallic>=0.5", 0.6
        elif transmission >= 0.5 or (opacity is not None and float(opacity) < 0.5):
            cat, matched, quality = _cat("glass"), "transmission>=0.5 or opacity<0.5", 0.6
    mat = PhysicsMaterial(
        name=name or (cat.name if cat is not UNKNOWN else str(p.get("name") or "default")),
        friction=(cat.friction, 0.005, 0.0001),
        density=cat.density,
        restitution=cat.restitution,
    )
    lum = _luminance(p.get("base_color"))
    reflectivity = cat.lidar_reflectivity
    if lum is not None and not cat.transparent:
        # A dark albedo in the visible band is usually dark at 905 nm too.
        reflectivity = round(min(reflectivity, 0.05 + 0.85 * lum), 3)
    sensor = SensorMaterial(name=mat.name, lidar_reflectivity=reflectivity, transparent=cat.transparent)
    return Inferred(
        material=mat,
        category=cat.name,
        confidence=round(cat.confidence * quality, 3),
        matched=matched,
        sources=tuple(SOURCES[s] for s in cat.sources),
        ranges={
            "friction": cat.friction_range,
            "density": cat.density_range,
            "restitution": cat.restitution_range,
        },
        sensor=sensor,
    )


def _cat(name: str) -> Category:
    return next(c for c in CATEGORIES if c.name == name)


def lookup_table() -> list[dict[str, Any]]:
    """The table as rows (for docs and the editor)."""
    return [
        {
            "category": c.name,
            "keywords": list(c.keywords),
            "friction": c.friction,
            "friction_range": list(c.friction_range),
            "density": c.density,
            "density_range": list(c.density_range),
            "restitution": c.restitution,
            "restitution_range": list(c.restitution_range),
            "confidence": c.confidence,
            "lidar_reflectivity": c.lidar_reflectivity,
            "transparent": c.transparent,
            "sources": [SOURCES[s] for s in c.sources],
            "note": c.note,
        }
        for c in CATEGORIES
    ]
