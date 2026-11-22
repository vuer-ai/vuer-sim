"""Serve a scene's material table to the vuer-sim editor.

    uv run --group heavy python examples/edit_materials.py [examples/lab_table] [--port 8012]

Then open the editor (``pnpm demo`` in vuer-ai/vuer-sim-ts) and point it at
``ws://localhost:8012``. Every save in the browser writes
``<bundle>/materials.json`` through the ``VUER_SIM_MATERIALS_SAVE`` event.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import mujoco

from vuer_sim import MaterialTable, infer_physics
from vuer_sim.scene import scene_summary
from vuer_sim.viewer import serve

parser = argparse.ArgumentParser()
parser.add_argument("bundle", nargs="?", default=str(Path(__file__).parent / "lab_table"))
parser.add_argument("--port", type=int, default=8012)
args = parser.parse_args()

bundle = Path(args.bundle)
model = mujoco.MjModel.from_xml_path(str(bundle / "scene.xml"))
if not MaterialTable.path(bundle).exists():  # start from the inferred table
    table = MaterialTable()
    for i in range(model.nmat):
        name = model.material(i).name
        guess = infer_physics({"name": name, "base_color": list(model.mat_rgba[i])}, name=name)
        guess.sensor.name = name
        table.add(guess.material, guess.sensor)
        table.assign[f"material:{name}"] = name
    table.save(bundle)

serve(bundle, scene=scene_summary(model, groups=(0, 1, 2)), port=args.port)
