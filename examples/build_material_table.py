"""Build a material table for a MuJoCo scene, apply it, step the scene, and simulate a LiDAR frame.

    uv run --group heavy python examples/build_material_table.py [examples/lab_table]

1. Infer a physics and a sensor material for each visual material of the scene.
2. Save the table to ``<bundle>/materials.json``.
3. Apply it to the MjSpec, compile, and step two seconds.
4. Cast one ring of LiDAR rays and apply the sensor materials with ``lidar_returns``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import mujoco
import numpy as np

from vuer_sim import MaterialTable, infer_physics, lidar_returns

bundle = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).parent / "lab_table")
spec = mujoco.MjSpec.from_file(str(bundle / "scene.xml"))

table = MaterialTable()
for material in spec.materials:
    guess = infer_physics({"name": material.name, "base_color": list(material.rgba)})
    guess.material.name = guess.sensor.name = material.name
    table.add(guess.material, guess.sensor)
    table.assign[f"material:{material.name}"] = material.name
    print(
        f"{material.name:16s} -> {guess.category:8s} confidence {guess.confidence:.2f}  "
        f"friction {guess.material.friction[0]:.2f} density {guess.material.density:6.0f} "
        f"restitution {guess.material.restitution:.2f} reflectivity {guess.sensor.lidar_reflectivity:.2f}"
    )
print("saved", table.save(bundle))

report = table.apply(spec)
for warning in report.warnings:
    print("warning:", warning)
model = spec.compile()
data = mujoco.MjData(model)
for _ in range(1000):
    mujoco.mj_step(model, data)
print(f"stepped {data.time:.1f} s; ball at z = {data.body('ball').xpos[2]:.3f} m")

# One horizontal ring of rays from 0.9 m above the floor (robot-env casts the same way).
n = 3600
angle = np.linspace(-np.pi, np.pi, n, endpoint=False)
directions = np.stack([np.cos(angle), np.sin(angle), np.full(n, -0.05)], axis=1)
directions /= np.linalg.norm(directions, axis=1, keepdims=True)
geom = np.zeros(n, np.int32)
dist = np.zeros(n)
mujoco.mj_multiRay(
    model, data, np.array([0.0, -0.6, 0.9]), directions.reshape(-1), None, 1, -1, geom, dist, None, n, 40.0
)
out = lidar_returns(geom, dist, table.sensor_arrays(model), rng=0)
print(
    f"lidar: {int((geom >= 0).sum())} hits, {int(out.valid.sum())} returns, "
    f"mean intensity {out.intensity[out.valid].mean():.0f}"
)
