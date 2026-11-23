# Schema reference

This page lists every field that vuer-sim stores or converts. The guides
explain each part:
- [Physics materials](reference/guides-physics-materials.md)
- [Sensor materials](reference/guides-sensor-materials.md)
- [Material tables](reference/guides-material-table.md)
- [Restitution in MuJoCo](reference/guides-restitution.md)

## PhysicsMaterial

| Field | Type | Default | MJCF geom attribute | USD attribute (prim) |
| --- | --- | --- | --- | --- |
| `friction[0]` slide | float | 1 | `friction` (1st) | `physics:dynamicFriction` (material) |
| `friction[1]` torsion | float | 0.005 | `friction` (2nd) | `mjc:torsionalfriction` + `newton:torsionalFriction` (material) |
| `friction[2]` roll | float | 0.0001 | `friction` (3rd) | `mjc:rollingfriction` + `newton:rollingFriction` (material) |
| `restitution` | float, 0–1 | from `solref` | via `solref[1]` | `physics:restitution` (material) |
| `density` | float, kg/m³ | 1000 | `density` | `physics:density`, stage units (material) |
| `solref` | 2 floats | `[0.02, 1]` | `solref` | `mjc:solref` (collider) |
| `solimp` | 5 floats | `[0.9, 0.95, 0.001, 0.5, 2]` | `solimp` | `mjc:solimp` (collider) |
| `condim` | 1, 3, 4 or 6 | 3 | `condim` | `mjc:condim` (collider) |
| `priority` | int | 0 | `priority` | `mjc:priority` (collider) |
| `margin` | float, m | 0 | `margin` | `mjc:margin` + `newton:contactMargin` (collider) |
| `gap` | float, m | 0 | `gap` | `mjc:gap` + `newton:contactGap` (collider) |

- The defaults are MuJoCo's defaults.
- `restitution` sets `solref[1]` through `z = -ln(e) / sqrt(π² + ln(e)²)`.
- The USD material prim gets `PhysicsMaterialAPI` and `MjcMaterialAPI`. A
  collider prim gets `PhysicsCollisionAPI`, `MjcCollisionAPI` and a binding to
  the material with the purpose `physics`.
- The names come from MuJoCo's `mjcPhysics` schema at MuJoCo **4.0.1**. The
  `newton:` twins are written with the same value; on read, `mjc:` wins.

## SensorMaterial

| Field | Type | Default | USD attribute (material prim) |
| --- | --- | --- | --- |
| `lidar_reflectivity` | float, 0–1 | 0.5 | `vuersim:lidarReflectivity` |
| `intensity` | float or null, 0–255 | null (= `round(150 × reflectivity)`) | `vuersim:lidarIntensity` |
| `dropout` | float, 0–1 | 0 | `vuersim:dropout` |
| `transparent` | bool | false | `vuersim:transparent` |
| `depth_noise_std` | float, m | 0 | `vuersim:depthNoiseStd` |

Sensor materials have no MuJoCo or UsdPhysics equivalent. They are the only
`vuersim:` attributes.

## materials.json

A `MaterialTable` is stored as `<bundle>/materials.json`, with the schema id
`vuer-sim.materials/1`.

```json file="bundle/materials.json"
{
  "assign": {
    "<geom name | glob | material:<visual material> | material:<glob>>": "<material name>"
  },
  "materials": {
    "<material name>": {
      "physics": {
        "condim": 3,
        "density": 1000.0,
        "friction": [1.0, 0.005, 0.0001],
        "gap": 0.0,
        "margin": 0.0,
        "priority": 0,
        "restitution": 0.0,
        "solimp": [0.9, 0.95, 0.001, 0.5, 2.0],
        "solref": [0.02, 1.0]
      },
      "sensor": {
        "depth_noise_std": 0.0,
        "dropout": 0.0,
        "intensity": null,
        "lidar_reflectivity": 0.5,
        "transparent": false
      }
    }
  },
  "schema": "vuer-sim.materials/1"
}
```

(The arrays are on one line here; the file has one value per line.)

| Rule | Detail |
| --- | --- |
| Stored form | Sorted keys, 2-space indent, trailing newline (the DreamLake bundle contract). Python and `@vuer-ai/vuer-sim` write the same bytes. |
| Parts | A material has `physics`, `sensor`, or both. Missing fields take the defaults above. |
| Validation | Unknown keys, an unknown `schema`, and assignments to unknown materials are refused. |
| `restitution` vs `solref` | Both are stored. When they disagree after a hand edit, `restitution` wins. |
| Assignment | Exact geom name, then exact `material:<name>`, then the longest glob. |

## Editor events

| Event | Direction | Payload |
| --- | --- | --- |
| `VUER_SIM_MATERIALS_LOAD` | client → server | `{}` |
| `VUER_SIM_MATERIALS_SAVE` | client → server | `{json, revision}` |
| `VUER_SIM_MATERIALS` | server → client | `{json, path, saved, revision, scene}` or `{error, revision}` |

The table travels as its stored JSON text. See [Material editor](reference/editor-overview.md).
