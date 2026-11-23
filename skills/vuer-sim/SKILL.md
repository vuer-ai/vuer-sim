---
name: vuer-sim
description: vuer-sim gives MuJoCo and USD scenes simulation materials: PhysicsMaterial with MJCF and USD converters (restitution through the solref damping ratio), a visual-to-physics lookup table, LiDAR sensor materials with lidar_returns, a JSON MaterialTable stored in a bundle, and a vuer editor (@vuer-ai/vuer-sim). Use when setting friction, restitution or density of MuJoCo or USD geoms; converting physics materials between MJCF and USD (UsdPhysics MaterialAPI); mapping restitution to MuJoCo solref; guessing physics materials from visual material names or PBR parameters; simulating LiDAR returns on glass, black or noisy surfaces; reading, writing or applying a materials.json material table in a scene bundle; building or wiring the vuer-sim material editor (@vuer-ai/vuer-sim).
---
# vuer-sim

vuer-sim gives MuJoCo and USD scenes simulation materials: PhysicsMaterial with MJCF and USD converters (restitution through the solref damping ratio), a visual-to-physics lookup table, LiDAR sensor materials with lidar_returns, a JSON MaterialTable stored in a bundle, and a vuer editor (@vuer-ai/vuer-sim).

This skill bundles the vuer-sim documentation. Read the reference
file that matches the question; each is a self-contained markdown page.

## Reference

**Get started**

- `reference/overview.md` — Introduction: What vuer-sim does, the two packages, and where to start.
- `reference/get-started-install.md` — Install: Install vuer-sim and its optional extras for MuJoCo, USD and the vuer editor.

**Guides**

- `reference/guides-physics-materials.md` — Physics materials: PhysicsMaterial fields and the MJCF (geom attributes and default classes) and USD (UsdPhysics and MuJoCo mjcPhysics schema, pinned at 4.0.1) converters.
- `reference/guides-restitution.md` — Restitution in MuJoCo: How restitution maps to the solref damping ratio, the formula, the stability limit, and measured bounce values.
- `reference/guides-inference.md` — Visual to physics: infer_physics guesses a PhysicsMaterial from a material name or PBR parameters, with a documented lookup table, cited typical values and a confidence.
- `reference/guides-sensor-materials.md` — Sensor materials: SensorMaterial and lidar_returns — dropout, glass, black surfaces, range noise and intensity applied to per-ray geom ids from a ray-cast LiDAR.
- `reference/guides-material-table.md` — Material tables: MaterialTable load, save and apply — the materials.json file in a scene bundle, its stored form, and the assignment rules.

**Reference**

- `reference/reference-python.md` — Python API: Every public name of vuer_sim, with its signature and a one-line description.

**Editor**

- `reference/editor-overview.md` — Material editor: Edit a material table in the browser with @vuer-ai/vuer-sim and save it to the bundle through vuer events that vuer_sim.viewer handles.

**Contributing**

- `reference/contributing.md` — Development and releases: The CI policy (fast checks only), the local heavy checks, the docs and skill generator, and the release process.

## Canonical source

These docs live at https://vuer-sim.dreamlake.ai. Each page is also fetchable as markdown
at `<page-url>.md`, and the full corpus at https://vuer-sim.dreamlake.ai/llms-full.txt.
