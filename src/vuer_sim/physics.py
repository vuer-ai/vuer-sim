"""``PhysicsMaterial``: one contact material, with MJCF and USD converters.

Restitution in MuJoCo
---------------------
MuJoCo has no restitution coefficient. A contact is a soft constraint whose
reference acceleration is that of a mass-spring-damper, set by
``solref = (timeconst, dampratio)``. At constant impedance the effective damping
ratio of that oscillator is ``dampratio``. A linear spring-damper with damping
ratio ``z < 1`` that stays in contact for one half period leaves with

    e = exp(-pi * z / sqrt(1 - z**2))            (restitution from z)
    z = -ln(e) / sqrt(pi**2 + ln(e)**2)           (z from restitution)

``e = 0`` maps to ``z = 1`` (critical damping, the MuJoCo default). Any ``z >= 1``
maps back to ``e = 0``. This is the mapping the owner approved on 2026-11-22.

Limits (measured, see ``docs/pages/guides/restitution``):

* The mapping is exact only for a linear, bilateral oscillator. A MuJoCo contact
  releases when the constraint force reaches zero, and ``solimp`` changes the
  impedance with depth, so the measured restitution differs by about +0.1 at
  ``e <= 0.2`` and by -0.05 at ``e = 0.8`` (``timeconst`` 0.02 s, timestep 2 ms).
* The contact stiffness grows as ``1 / (timeconst * dampratio)**2``. Keep
  ``timestep <= timeconst * dampratio`` (see ``max_stable_timestep``); above it
  the error grows and high restitution becomes unstable (energy gain).
* MuJoCo mixes the ``solref`` of two geoms in contact by ``solmix`` (or takes the
  geom with the higher ``priority``). The restitution of a pair is the
  restitution of the mixed ``solref``, not a mix of the two restitutions.
* The direct form (``solref < 0``: ``-stiffness, -damping``) maps through
  ``z = damping / (2 * sqrt(stiffness))``. ``from_mjcf`` reads it; ``to_mjcf``
  always writes the standard form.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, fields
from typing import Any

from ._fmt import num, nums, parse_nums

# MuJoCo defaults (https://mujoco.readthedocs.io/en/stable/XMLreference.html#body-geom).
DEFAULT_FRICTION = (1.0, 0.005, 0.0001)
DEFAULT_SOLREF = (0.02, 1.0)
DEFAULT_SOLIMP = (0.9, 0.95, 0.001, 0.5, 2.0)
DEFAULT_DENSITY = 1000.0

#: The MJCF geom attributes that a ``PhysicsMaterial`` owns.
MJCF_ATTRIBUTES = ("friction", "solref", "solimp", "condim", "priority", "margin", "gap", "density")


def restitution_to_dampratio(e: float) -> float:
    """Damping ratio of a linear oscillator with coefficient of restitution ``e``."""
    e = float(e)
    if not 0.0 <= e <= 1.0:
        raise ValueError(f"restitution must be in [0, 1], got {e}")
    if e == 0.0:
        return 1.0
    if e == 1.0:
        return 0.0
    ln = math.log(e)
    return -ln / math.sqrt(math.pi**2 + ln * ln)


def dampratio_to_restitution(z: float) -> float:
    """Coefficient of restitution of a linear oscillator with damping ratio ``z``."""
    z = float(z)
    if z < 0:
        raise ValueError(f"dampratio must be >= 0, got {z}")
    if z >= 1.0:
        return 0.0
    return math.exp(-math.pi * z / math.sqrt(1.0 - z * z))


def solref_restitution(solref: tuple[float, float]) -> float:
    """Restitution of a ``solref`` pair, standard (positive) or direct (negative) form."""
    a, b = float(solref[0]), float(solref[1])
    if a < 0 and b <= 0:  # direct form: -stiffness, -damping (mass-normalised)
        stiffness, damping = -a, -b
        return dampratio_to_restitution(damping / (2.0 * math.sqrt(stiffness)))
    return dampratio_to_restitution(b)


def max_stable_timestep(timeconst: float, restitution: float) -> float:
    """Largest timestep for which the contact of this material stays accurate.

    The rule ``timestep <= timeconst * dampratio`` keeps the contact frequency
    times the timestep at or below 1 (``dampratio`` is clamped to 0.5 from above, which
    gives MuJoCo's own ``timeconst >= 2 * timestep`` rule at ``e = 0``).
    """
    return float(timeconst) * min(0.5, restitution_to_dampratio(restitution))


@dataclass
class PhysicsMaterial:
    """Contact material of a geom.

    ``friction`` is MuJoCo's ``(slide, torsion, roll)``. ``density`` is in kg/m^3.
    ``solref``, ``solimp``, ``condim``, ``priority``, ``margin`` and ``gap`` are the
    MJCF geom attributes of the same names.

    ``restitution`` and ``solref[1]`` describe the same thing. When you give
    ``restitution``, it sets ``solref[1]``; when you leave it ``None``, it is
    computed from ``solref``. So ``restitution`` wins if both are given.
    """

    name: str = "default"
    friction: tuple[float, float, float] = DEFAULT_FRICTION
    restitution: float | None = None
    density: float = DEFAULT_DENSITY
    solref: tuple[float, float] = DEFAULT_SOLREF
    solimp: tuple[float, float, float, float, float] = DEFAULT_SOLIMP
    condim: int = 3
    priority: int = 0
    margin: float = 0.0
    gap: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict, compare=False, repr=False)

    def __post_init__(self) -> None:
        f = tuple(float(v) for v in _as_tuple(self.friction))
        if len(f) == 1:  # MJCF allows fewer values; the rest keep their defaults
            f = (f[0], *DEFAULT_FRICTION[1:])
        elif len(f) == 2:
            f = (f[0], f[1], DEFAULT_FRICTION[2])
        if len(f) != 3:
            raise ValueError(f"friction needs 1 to 3 values, got {self.friction!r}")
        self.friction = f  # type: ignore[assignment]
        solref = tuple(float(v) for v in _as_tuple(self.solref))
        if len(solref) != 2:
            raise ValueError(f"solref needs 2 values, got {self.solref!r}")
        solimp = tuple(float(v) for v in _as_tuple(self.solimp))
        if len(solimp) == 3:
            solimp = (*solimp, *DEFAULT_SOLIMP[3:])
        if len(solimp) != 5:
            raise ValueError(f"solimp needs 3 or 5 values, got {self.solimp!r}")
        self.solimp = solimp  # type: ignore[assignment]
        if self.restitution is None:
            # 12 decimals hide the float noise of exp(log(e)) (0.6 -> 0.5999999999999999).
            self.restitution = round(solref_restitution(solref), 12)
        else:
            self.restitution = float(self.restitution)
            z = restitution_to_dampratio(self.restitution)
            if solref[0] < 0:  # direct form: keep the stiffness, set the damping
                solref = (solref[0], -2.0 * z * math.sqrt(-solref[0]))
            else:
                solref = (solref[0], z)
        self.solref = solref  # type: ignore[assignment]
        self.density = float(self.density)
        self.condim = int(self.condim)
        if self.condim not in (1, 3, 4, 6):
            raise ValueError(f"condim must be 1, 3, 4 or 6, got {self.condim}")
        self.priority = int(self.priority)
        self.margin = float(self.margin)
        self.gap = float(self.gap)

    # ------------------------------------------------------------------ dict

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready dict (the form ``MaterialTable`` stores)."""
        d = asdict(self)
        d.pop("extra")
        d.pop("name")
        d["friction"] = list(self.friction)
        d["solref"] = list(self.solref)
        d["solimp"] = list(self.solimp)
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any], name: str | None = None) -> "PhysicsMaterial":
        known = {f.name for f in fields(cls)} - {"extra"}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown PhysicsMaterial fields: {sorted(unknown)}")
        kw = dict(d)
        if name is not None:
            kw["name"] = name
        # The stored restitution is derived from solref. When the two agree, read
        # solref as the source (no float drift); when they disagree, restitution wins.
        if "solref" in kw and "restitution" in kw:
            stored = solref_restitution(kw["solref"])
            if math.isclose(stored, float(kw["restitution"]), abs_tol=1e-9):
                kw.pop("restitution")
        return cls(**kw)

    # ------------------------------------------------------------------ MJCF

    def to_mjcf(self) -> dict[str, str]:
        """MJCF geom attributes (strings), for ``<geom>`` or ``<default><geom>``."""
        return {
            "friction": nums(self.friction),
            "solref": nums(self.solref),
            "solimp": nums(self.solimp),
            "condim": str(self.condim),
            "priority": str(self.priority),
            "margin": num(self.margin),
            "gap": num(self.gap),
            "density": num(self.density),
        }

    def to_mjcf_default(self, class_name: str | None = None) -> ET.Element:
        """``<default class="..."><geom .../></default>`` element for this material."""
        el = ET.Element("default", {"class": class_name or self.name})
        ET.SubElement(el, "geom", self.to_mjcf())
        return el

    @classmethod
    def from_mjcf(
        cls,
        source: ET.Element | Mapping[str, str] | str,
        name: str | None = None,
        base: "PhysicsMaterial | None" = None,
    ) -> "PhysicsMaterial":
        """Read a material from MJCF.

        ``source`` is a ``<geom>`` element, a ``<default class>`` element (its
        ``<geom>`` child is read), an attribute mapping, or XML text of either
        element. Attributes that are missing keep the values of ``base`` (MuJoCo
        defaults when ``base`` is ``None``); use ``mjcf_defaults`` to resolve
        ``<default>`` class inheritance first.
        """
        if isinstance(source, str):
            source = ET.fromstring(source)
        if isinstance(source, ET.Element):
            el = source
            if el.tag == "default":
                name = name or el.get("class") or "main"
                geom = el.find("geom")
                attrs: Mapping[str, str] = geom.attrib if geom is not None else {}
            else:
                name = name or el.get("material") or el.get("class") or el.get("name")
                attrs = el.attrib
        else:
            attrs = source
        kw: dict[str, Any] = {} if base is None else base.to_dict()
        kw.pop("restitution", None)
        for key in ("friction", "solref", "solimp"):
            if key in attrs:
                kw[key] = parse_nums(attrs[key])
        for key in ("condim", "priority"):
            if key in attrs:
                kw[key] = int(attrs[key])
        for key in ("margin", "gap", "density"):
            if key in attrs:
                kw[key] = float(attrs[key])
        mat = cls(name=name or (base.name if base else "default"), **kw)
        mat.extra = {k: v for k, v in attrs.items() if k == "solmix"}
        return mat

    @classmethod
    def from_model(cls, model: Any, geom: int | str, name: str | None = None) -> "PhysicsMaterial":
        """Read the material of a geom of a compiled ``mujoco.MjModel``.

        The compiled model does not keep ``density`` (MuJoCo uses it only to
        compute inertia), so the result has the default density.
        """
        gid = geom if isinstance(geom, int) else model.geom(geom).id
        return cls(
            name=name or model.geom(gid).name or f"geom{gid}",
            friction=tuple(model.geom_friction[gid]),
            solref=tuple(model.geom_solref[gid]),
            solimp=tuple(model.geom_solimp[gid]),
            condim=int(model.geom_condim[gid]),
            priority=int(model.geom_priority[gid]),
            margin=float(model.geom_margin[gid]),
            gap=float(model.geom_gap[gid]),
        )

    # ------------------------------------------------------------------ USD

    def to_usd(self, stage: Any, path: str, colliders: Any = ()) -> Any:
        """Write the material prim at ``path`` and bind it to ``colliders``.

        The material prim gets ``UsdPhysics.MaterialAPI`` and ``MjcMaterialAPI``
        (friction, restitution, density). Each collider prim (or prim path) gets
        the binding plus ``MjcCollisionAPI`` (``solref``, ``solimp``, ``condim``,
        ``priority``, ``margin``, ``gap``), as in MuJoCo's own USD schema. Needs
        ``pxr`` (``pip install 'vuer-sim[usd]'``). See ``vuer_sim.usd``.
        """
        from .usd import bind, write_physics_material

        material = write_physics_material(self, stage, path)
        for c in colliders:
            bind(stage.GetPrimAtPath(c) if isinstance(c, str) else c, material, self)
        return material

    @classmethod
    def from_usd(cls, prim: Any, name: str | None = None) -> "PhysicsMaterial | None":
        """Read a collider prim (its ``mjc:`` attributes and bound material) or a material prim.

        Returns ``None`` when there is no physics material and no ``mjc:`` collider
        attributes. Needs ``pxr``.
        """
        from .usd import read_physics_material

        return read_physics_material(prim, cls, name=name)

    # ------------------------------------------------------------------ checks

    def max_stable_timestep(self) -> float:
        """See the module function ``max_stable_timestep``."""
        timeconst = self.solref[0] if self.solref[0] > 0 else 0.02
        return max_stable_timestep(timeconst, float(self.restitution or 0.0))


def mjcf_defaults(root: ET.Element) -> dict[str, PhysicsMaterial]:
    """Resolve every ``<default>`` class of an MJCF tree to a ``PhysicsMaterial``.

    Nested classes inherit the attributes of their parent class, as in MuJoCo.
    The top-level class is ``"main"``.
    """
    out: dict[str, PhysicsMaterial] = {}

    def walk(el: ET.Element, parent: PhysicsMaterial | None) -> None:
        name = el.get("class") or "main"
        mat = PhysicsMaterial.from_mjcf(el, name=name, base=parent)
        out[name] = mat
        for child in el.findall("default"):
            walk(child, mat)

    tops = [root] if root.tag == "default" else root.findall("default")
    for top in tops:
        walk(top, None)
    return out


def _as_tuple(v: Any) -> tuple:
    if isinstance(v, str):
        return parse_nums(v)
    try:
        return tuple(v)
    except TypeError:
        return (v,)
