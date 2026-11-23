# Changelog

## Unreleased

- `PhysicsMaterial` (friction, restitution, density, solref, solimp, condim, priority, margin,
  gap) with MJCF (geom attributes, `<default>` classes, compiled models) and
  USD converters: UsdPhysics plus the `mjcPhysics` names of MuJoCo 4.0.1 (`mjc:solref`,
  `mjc:torsionalfriction`, ... on material and collider prims). Restitution maps to the
  `solref` damping ratio. Sensor materials use `vuersim:` attributes.
- `infer_physics`: a documented visual-to-physics lookup table with sources and confidence.
- `SensorMaterial` and `lidar_returns`: dropout, glass, black surfaces, range noise, intensity.
- `MaterialTable`: `materials.json` in a bundle (stored form), assignment rules, `apply` to
  `MjSpec` or `MjModel`, `sensor_arrays`.
- `vuer_sim.viewer`: vuer events that load and save the table for the `@vuer-ai/vuer-sim` editor.
- Dockit docs site and the `vuer-sim` agent skill.
