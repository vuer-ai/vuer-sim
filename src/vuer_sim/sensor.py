"""Sensor-facing materials and the LiDAR return model.

``lidar_returns`` takes what a ray-cast LiDAR gives per ray (the hit geom id, -1
for no hit, and the range) and applies the material of each hit geom:

1. **No hit**: ``geom_id < 0`` or ``range <= 0`` gives no return.
2. **Range noise**: ``ranges + N(0, depth_noise_std)`` of the material.
3. **Dropout**: the return is lost with probability ``dropout``.
4. **Glass** (``transparent``): the beam goes through. The surface gives a
   return only with probability ``lidar_reflectivity`` (the Fresnel reflection
   of glass at near-normal incidence is about 4 to 8 percent). The pure
   function cannot see what is behind the glass; to get those returns, cast the
   rays with the glass geoms in an excluded geom group.
5. **Black surfaces**: the received power of a diffuse target falls as
   ``reflectivity / range**2``, so the largest range for reflectivity ``p`` is
   ``range_at_10pct * sqrt(p / 0.1)``. ``range_at_10pct`` is 40 m for the Livox
   Mid-360 (data sheet: 40 m at 10 percent, 70 m at 80 percent; the 80 percent
   value is capped by the sensor, so the square-root law holds for dark targets
   only, which is where it matters).
6. **Intensity**: ``SensorMaterial.intensity`` when set, else the Livox
   convention ``round(150 * reflectivity)`` (0-150 diffuse, 151-255
   retroreflective).

The geom ids are those of ``mujoco.mj_multiRay``, as robot-env's simulated
LiDAR (``rigs.sim.lidar.RayLidar``) produces them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields
from typing import Any, NamedTuple

import numpy as np

#: Livox Mid-360 data sheet: 40 m range at 10 percent reflectivity.
MID360_RANGE_AT_10PCT = 40.0


@dataclass
class SensorMaterial:
    """How a surface looks to LiDAR and depth cameras.

    ``lidar_reflectivity``: diffuse reflectivity at the LiDAR wavelength, 0-1.
    ``intensity``: reported intensity override (0-255, Livox scale); ``None``
    derives it from the reflectivity. ``dropout``: probability that a return is
    lost. ``transparent``: rays pass through (glass). ``depth_noise_std``: extra
    range noise in metres, 1 sigma.
    """

    name: str = "default"
    lidar_reflectivity: float = 0.5
    intensity: float | None = None
    dropout: float = 0.0
    transparent: bool = False
    depth_noise_std: float = 0.0

    def __post_init__(self) -> None:
        self.lidar_reflectivity = float(self.lidar_reflectivity)
        if not 0.0 <= self.lidar_reflectivity <= 1.0:
            raise ValueError(f"lidar_reflectivity must be in [0, 1], got {self.lidar_reflectivity}")
        self.dropout = float(self.dropout)
        if not 0.0 <= self.dropout <= 1.0:
            raise ValueError(f"dropout must be in [0, 1], got {self.dropout}")
        if self.intensity is not None:
            self.intensity = float(self.intensity)
        self.transparent = bool(self.transparent)
        self.depth_noise_std = float(self.depth_noise_std)
        if self.depth_noise_std < 0:
            raise ValueError("depth_noise_std must be >= 0")

    @property
    def reported_intensity(self) -> float:
        if self.intensity is not None:
            return self.intensity
        return float(round(150.0 * self.lidar_reflectivity))

    def to_usd(self, stage: Any, path: str) -> Any:
        """Write the ``vuersim:`` sensor attributes on the material prim at ``path``. Needs ``pxr``."""
        from .usd import write_sensor_material

        return write_sensor_material(self, stage, path)

    @classmethod
    def from_usd(cls, prim: Any, name: str | None = None) -> "SensorMaterial | None":
        """Read the ``vuersim:`` sensor attributes of a material prim or of its bound material."""
        from .usd import read_sensor_material

        return read_sensor_material(prim, name=name)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("name")
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any], name: str | None = None) -> "SensorMaterial":
        known = {f.name for f in fields(cls)}
        unknown = set(d) - known
        if unknown:
            raise ValueError(f"unknown SensorMaterial fields: {sorted(unknown)}")
        kw = dict(d)
        if name is not None:
            kw["name"] = name
        return cls(**kw)


DEFAULT_SENSOR = SensorMaterial()


class SensorArrays(NamedTuple):
    """Per-geom-id arrays of sensor properties (index = MuJoCo geom id)."""

    reflectivity: np.ndarray
    intensity: np.ndarray
    dropout: np.ndarray
    transparent: np.ndarray
    noise: np.ndarray

    @classmethod
    def from_materials(
        cls,
        materials: "Mapping[int, SensorMaterial] | list[SensorMaterial | None]",
        ngeom: int | None = None,
        default: SensorMaterial = DEFAULT_SENSOR,
    ) -> "SensorArrays":
        items = dict(enumerate(materials)) if isinstance(materials, list) else dict(materials)
        n = ngeom if ngeom is not None else (max(items) + 1 if items else 0)
        mats = [items.get(i) or default for i in range(n)]
        return cls(
            reflectivity=np.array([m.lidar_reflectivity for m in mats], np.float64),
            intensity=np.array([m.reported_intensity for m in mats], np.float64),
            dropout=np.array([m.dropout for m in mats], np.float64),
            transparent=np.array([m.transparent for m in mats], bool),
            noise=np.array([m.depth_noise_std for m in mats], np.float64),
        )


class LidarReturns(NamedTuple):
    ranges: np.ndarray  # float64 (N,), 0 where not valid
    valid: np.ndarray  # bool (N,)
    intensity: np.ndarray  # float32 (N,), 0 where not valid


def lidar_returns(
    geom_ids: np.ndarray,
    ranges: np.ndarray,
    table: Any,
    rng: np.random.Generator | int | None = None,
    *,
    range_at_10pct: float = MID360_RANGE_AT_10PCT,
    max_range: float | None = None,
) -> LidarReturns:
    """Apply sensor materials to one LiDAR frame. Pure: the only state is ``rng``.

    ``table`` is a ``SensorArrays``, a ``{geom_id: SensorMaterial}`` mapping, or a
    list indexed by geom id (geoms without a material get ``DEFAULT_SENSOR``).
    For a ``MaterialTable`` call ``table.sensor_arrays(model)`` once per model.
    """
    geom = np.asarray(geom_ids).astype(np.int64, copy=False).reshape(-1)
    r = np.asarray(ranges, np.float64).reshape(-1)
    if geom.shape != r.shape:
        raise ValueError(f"geom_ids {geom.shape} and ranges {r.shape} differ")
    if not isinstance(rng, np.random.Generator):
        rng = np.random.default_rng(rng)
    if not isinstance(table, SensorArrays):
        hit_max = int(np.max(geom)) + 1 if geom.size else 0
        if isinstance(table, list):
            n = max(len(table), hit_max)
        else:
            n = max([hit_max, *(int(k) + 1 for k in table)])
        table = SensorArrays.from_materials(table, ngeom=n)

    hit = (geom >= 0) & (r > 0)
    if hit.any() and int(np.max(geom[hit])) >= len(table.reflectivity):
        raise ValueError("geom id beyond the sensor table: build it with the model's ngeom")
    if len(table.reflectivity) == 0:
        return LidarReturns(np.zeros_like(r), np.zeros(r.shape, bool), np.zeros(r.shape, np.float32))
    g = np.where(hit, geom, 0)
    refl = table.reflectivity[g]
    u = rng.random((2, r.size))  # one draw per ray and test: stable stream for a fixed seed

    noise = table.noise[g]
    out = r + rng.standard_normal(r.size) * noise
    valid = hit & (u[0] >= table.dropout[g])
    glass = table.transparent[g]
    valid &= ~glass | (u[1] < refl)
    reach = range_at_10pct * np.sqrt(np.maximum(refl, 0.0) / 0.1)
    valid &= glass | (r <= reach)
    if max_range is not None:
        valid &= out <= max_range
    valid &= out > 0
    intensity = np.where(valid, table.intensity[g], 0.0).astype(np.float32)
    return LidarReturns(np.where(valid, out, 0.0), valid, intensity)
