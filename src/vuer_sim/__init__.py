"""vuer-sim: simulation materials for MuJoCo and USD scenes.

The core needs only numpy. Optional extras: ``[mujoco]``, ``[usd]``, ``[viewer]``.
"""

try:
    from importlib.metadata import version as _version

    __version__ = _version("vuer-sim")
except Exception:  # pragma: no cover - source tree without an install
    __version__ = "0+unknown"

__all__: list[str] = []
