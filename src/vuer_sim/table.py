"""``MaterialTable``: named materials plus geom assignments, stored as JSON in a bundle.

Stored form (``<bundle>/materials.json``; sorted keys, 2-space indent, trailing
newline, as in the DreamLake bundle contract)::

    {
      "assign": {"floor": "wood", "cup_*": "ceramic", "material:glass": "glass"},
      "materials": {
        "wood": {"physics": {...PhysicsMaterial...}, "sensor": {...SensorMaterial...}}
      },
      "schema": "vuer-sim.materials/1"
    }

A material has a ``physics`` part, a ``sensor`` part, or both.

Assignment keys select geoms, most specific first:

1. the exact geom name;
2. ``material:<name>``: the exact name of the geom's visual (MJCF) material;
3. a glob pattern (``*``, ``?``, ``[...]``) over the geom name, or ``material:<glob>``
   over the visual material name. The longest pattern wins; equal lengths go in
   key order.
"""

from __future__ import annotations

import fnmatch
import json
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ._fmt import dumps
from .physics import PhysicsMaterial
from .sensor import SensorArrays, SensorMaterial

FILENAME = "materials.json"
SCHEMA = "vuer-sim.materials/1"
_GLOB = set("*?[")


@dataclass
class ApplyReport:
    """What ``MaterialTable.apply`` did."""

    assigned: dict[str, str] = field(default_factory=dict)  # geom name (or #id) -> material
    warnings: list[str] = field(default_factory=list)


@dataclass
class MaterialTable:
    physics: dict[str, PhysicsMaterial] = field(default_factory=dict)
    sensor: dict[str, SensorMaterial] = field(default_factory=dict)
    assign: dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ edit

    def add(self, *materials: PhysicsMaterial | SensorMaterial) -> "MaterialTable":
        for m in materials:
            if isinstance(m, PhysicsMaterial):
                self.physics[m.name] = m
            elif isinstance(m, SensorMaterial):
                self.sensor[m.name] = m
            else:
                raise TypeError(f"not a material: {m!r}")
        return self

    @property
    def names(self) -> list[str]:
        return sorted(set(self.physics) | set(self.sensor))

    # ------------------------------------------------------------------ JSON

    def to_dict(self) -> dict[str, Any]:
        materials: dict[str, dict[str, Any]] = {}
        for name in self.names:
            entry: dict[str, Any] = {}
            if name in self.physics:
                entry["physics"] = self.physics[name].to_dict()
            if name in self.sensor:
                entry["sensor"] = self.sensor[name].to_dict()
            materials[name] = entry
        return {"assign": dict(self.assign), "materials": materials, "schema": SCHEMA}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "MaterialTable":
        schema = d.get("schema", SCHEMA)
        if schema != SCHEMA:
            raise ValueError(f"unsupported schema {schema!r}; this version reads {SCHEMA!r}")
        unknown = set(d) - {"assign", "materials", "schema"}
        if unknown:
            raise ValueError(f"unknown MaterialTable keys: {sorted(unknown)}")
        table = cls(assign={str(k): str(v) for k, v in dict(d.get("assign", {})).items()})
        for name, entry in dict(d.get("materials", {})).items():
            extra = set(entry) - {"physics", "sensor"}
            if extra:
                raise ValueError(f"material {name!r}: unknown keys {sorted(extra)}")
            if "physics" in entry:
                table.physics[name] = PhysicsMaterial.from_dict(entry["physics"], name=name)
            if "sensor" in entry:
                table.sensor[name] = SensorMaterial.from_dict(entry["sensor"], name=name)
        missing = sorted(set(table.assign.values()) - set(table.names))
        if missing:
            raise ValueError(f"assign names unknown materials: {missing}")
        return table

    def dumps(self) -> str:
        return dumps(self.to_dict())

    @classmethod
    def loads(cls, text: str) -> "MaterialTable":
        return cls.from_dict(json.loads(text))

    @staticmethod
    def path(bundle: str | os.PathLike) -> Path:
        """``<bundle>/materials.json``, or ``bundle`` itself when it names a ``.json`` file."""
        p = Path(bundle)
        return p if p.suffix == ".json" else p / FILENAME

    @classmethod
    def load(cls, bundle: str | os.PathLike) -> "MaterialTable":
        return cls.loads(cls.path(bundle).read_text(encoding="utf-8"))

    def save(self, bundle: str | os.PathLike) -> Path:
        """Write the stored form atomically. Return the file path."""
        p = self.path(bundle)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(self.dumps(), encoding="utf-8")
        os.replace(tmp, p)
        return p

    # ------------------------------------------------------------------ resolve

    def resolve(self, geom_name: str, visual_material: str | None = None) -> str | None:
        """Material name for a geom, by the rules in the module docstring."""
        if geom_name in self.assign:
            return self.assign[geom_name]
        if visual_material and f"material:{visual_material}" in self.assign:
            return self.assign[f"material:{visual_material}"]
        best: tuple[int, str] | None = None
        for key, value in self.assign.items():
            if not _GLOB & set(key):
                continue
            if key.startswith("material:"):
                ok = visual_material is not None and fnmatch.fnmatchcase(visual_material, key[9:])
            else:
                ok = fnmatch.fnmatchcase(geom_name, key)
            if ok and (best is None or len(key) > best[0]):
                best = (len(key), value)
        return best[1] if best else None

    def assignments(self, model: Any) -> dict[int, str]:
        """``{geom id: material name}`` for a compiled ``mujoco.MjModel``."""
        out = {}
        for gid in range(model.ngeom):
            name = self.resolve(*_model_geom_names(model, gid))
            if name is not None:
                out[gid] = name
        return out

    def sensor_arrays(self, model: Any, default: SensorMaterial | None = None) -> SensorArrays:
        """Per-geom sensor arrays for ``lidar_returns``; unassigned geoms get ``default``."""
        mats = {gid: self.sensor[n] for gid, n in self.assignments(model).items() if n in self.sensor}
        return SensorArrays.from_materials(mats, ngeom=model.ngeom, default=default or SensorMaterial())

    # ------------------------------------------------------------------ apply

    def apply(self, model: Any) -> ApplyReport:
        """Write the physics materials into a ``mujoco.MjSpec`` or a compiled ``mujoco.MjModel``.

        On an ``MjSpec`` every field is set (recompile afterwards). On an
        ``MjModel`` the density cannot change (it is baked into the inertia), so
        it is skipped with a warning; friction, solref, solimp, condim, priority,
        margin and gap take effect at the next step.
        """
        report = ApplyReport()
        if hasattr(model, "geoms") and hasattr(model, "compile"):
            self._apply_spec(model, report)
        else:
            self._apply_model(model, report)
        timestep = _timestep(model)
        if timestep:
            for name in sorted(set(report.assigned.values())):
                mat = self.physics.get(name)
                if mat is not None and timestep > mat.max_stable_timestep() * (1 + 1e-9):
                    report.warnings.append(
                        f"{name}: timestep {timestep:g} s > {mat.max_stable_timestep():.3g} s "
                        f"(timeconst * dampratio); restitution {mat.restitution:.2f} will be inaccurate"
                    )
        return report

    def _apply_spec(self, spec: Any, report: ApplyReport) -> None:
        for i, geom in enumerate(spec.geoms):
            name = self.resolve(geom.name, geom.material or None)
            mat = self.physics.get(name) if name else None
            if mat is None:
                continue
            geom.friction = list(mat.friction)
            geom.solref = list(mat.solref)
            geom.solimp = list(mat.solimp)
            geom.condim = mat.condim
            geom.priority = mat.priority
            geom.margin = mat.margin
            geom.gap = mat.gap
            geom.density = mat.density
            report.assigned[geom.name or f"#{i}"] = mat.name

    def _apply_model(self, model: Any, report: ApplyReport) -> None:
        density = False
        for gid, name in self.assignments(model).items():
            mat = self.physics.get(name)
            if mat is None:
                continue
            model.geom_friction[gid] = mat.friction
            model.geom_solref[gid] = mat.solref
            model.geom_solimp[gid] = mat.solimp
            model.geom_condim[gid] = mat.condim
            model.geom_priority[gid] = mat.priority
            model.geom_margin[gid] = mat.margin
            model.geom_gap[gid] = mat.gap
            density = density or mat.density != 1000.0
            report.assigned[_model_geom_names(model, gid)[0] or f"#{gid}"] = mat.name
        if density:
            report.warnings.append(
                "density is not applied to a compiled MjModel; apply the table to the MjSpec to set it"
            )


def _model_geom_names(model: Any, gid: int) -> tuple[str, str | None]:
    geom = model.geom(gid)
    matid = int(model.geom_matid[gid])
    return geom.name, (model.material(matid).name if matid >= 0 else None)


def _timestep(model: Any) -> float | None:
    opt = getattr(model, "opt", None) or getattr(model, "option", None)
    return float(opt.timestep) if opt is not None and hasattr(opt, "timestep") else None
