"""vuer-sim: simulation materials for MuJoCo and USD scenes.

The core needs only numpy. Optional extras: ``[mujoco]`` (apply tables to
models), ``[usd]`` (``pxr`` converters), ``[viewer]`` (the vuer editor events).
"""

from .infer import CATEGORIES, Inferred, infer_physics, lookup_table
from .physics import (
    PhysicsMaterial,
    dampratio_to_restitution,
    max_stable_timestep,
    mjcf_defaults,
    restitution_to_dampratio,
    solref_restitution,
)
from .sensor import LidarReturns, SensorArrays, SensorMaterial, lidar_returns
from .table import ApplyReport, MaterialTable

try:
    from importlib.metadata import version as _version

    __version__ = _version("vuer-sim")
except Exception:  # pragma: no cover - source tree without an install
    __version__ = "0+unknown"

__all__ = [
    "ApplyReport",
    "CATEGORIES",
    "Inferred",
    "LidarReturns",
    "MaterialTable",
    "PhysicsMaterial",
    "SensorArrays",
    "SensorMaterial",
    "dampratio_to_restitution",
    "infer_physics",
    "lidar_returns",
    "lookup_table",
    "max_stable_timestep",
    "mjcf_defaults",
    "restitution_to_dampratio",
    "solref_restitution",
]
