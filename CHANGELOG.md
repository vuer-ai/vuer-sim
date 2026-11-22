# Changelog

## 0.0.1 — 2026-11-22

First release.

- `PhysicsMaterial` with MJCF (geom attributes, `<default>` classes, compiled models) and
  USD (`UsdPhysics.MaterialAPI`) converters. Restitution maps to the `solref` damping ratio.
- `infer_physics`: a documented visual-to-physics lookup table with sources and confidence.
- `SensorMaterial` and `lidar_returns`: dropout, glass, black surfaces, range noise, intensity.
- `MaterialTable`: `materials.json` in a bundle (stored form), assignment rules, `apply` to
  `MjSpec` or `MjModel`, `sensor_arrays`.
- `vuer_sim.viewer`: vuer events that load and save the table for the `@vuer-ai/vuer-sim` editor.
- Dockit docs site and the `vuer-sim` agent skill.
