# Material tables

A `MaterialTable` holds named materials and the rules that assign them to
geoms. It lives in a scene bundle as `materials.json`.

```python
from vuer_sim import MaterialTable, PhysicsMaterial, SensorMaterial

table = MaterialTable(assign={"floor": "stone", "cup_*": "ceramic", "material:window_glass": "glass"})
table.add(PhysicsMaterial("stone", friction=0.6, restitution=0.3, density=2400))
table.add(PhysicsMaterial("ceramic", restitution=0.5, density=2400))
table.add(SensorMaterial("glass", lidar_reflectivity=0.08, transparent=True))

table.save("bundle")                  # bundle/materials.json
table = MaterialTable.load("bundle")  # or a path to a .json file
```

## Stored form

```json file="bundle/materials.json"
{
  "assign": {
    "cup_*": "ceramic",
    "floor": "stone",
    "material:window_glass": "glass"
  },
  "materials": {
    "glass": {
      "sensor": {
        "depth_noise_std": 0.0,
        "dropout": 0.0,
        "intensity": null,
        "lidar_reflectivity": 0.08,
        "transparent": true
      }
    },
    "stone": {
      "physics": {
        "condim": 3,
        "density": 2400.0,
        "friction": [0.6, 0.005, 0.0001],
        "margin": 0.0,
        "priority": 0,
        "restitution": 0.3,
        "solimp": [0.9, 0.95, 0.001, 0.5, 2.0],
        "solref": [0.02, 0.3579...]
      }
    }
  },
  "schema": "vuer-sim.materials/1"
}
```

(The `friction` and `solimp` arrays are shown on one line here; the file has
one value per line.)

- The file uses the stored form of the DreamLake bundle contract: sorted keys,
  2-space indent, a trailing newline. So the same table always gives the same
  bytes, and diffs are small.
- `save` writes a temporary file and renames it, so a reader never sees half a file.
- A material has a `physics` part, a `sensor` part, or both.
- `restitution` is stored next to `solref` for people who read the file. When
  the two disagree after a hand edit, `restitution` wins.
- `load` refuses unknown keys, an unknown `schema`, and assignments to
  materials that do not exist.

## Assignment rules

A key of `assign` selects geoms. The most specific key wins:

1. The exact geom name.
2. `material:<name>`: the exact name of the geom's visual (MJCF) material.
3. A glob pattern (`*`, `?`, `[...]`) on the geom name, or `material:<glob>` on
   the visual material name. The longest pattern wins. Patterns of the same
   length go in key order.

```python
table.resolve("cup_12")                      # "ceramic"
table.resolve("lamp_shade", "window_glass")  # "glass"
table.assignments(model)                     # {geom id: material name}
```

## Apply to a model

```python
import mujoco

spec = mujoco.MjSpec.from_file("bundle/scene.xml")
report = table.apply(spec)      # sets friction, solref, solimp, condim, priority, margin, density
model = spec.compile()
report.assigned                 # {"floor": "stone", "cup_1": "ceramic", ...}
report.warnings                 # e.g. a restitution that the timestep cannot hold
```

`apply` also takes a compiled `MjModel`. Then the changes take effect at the
next step, but the density cannot change: MuJoCo has already computed the
inertia from it. `apply` adds a warning in that case. Apply the table to the
`MjSpec` to set the density.

`apply` checks `model.opt.timestep` against `max_stable_timestep()` of every
assigned material and adds a warning for each one that breaks it (see
[Restitution in MuJoCo](reference/guides-restitution.md)).

## Sensor arrays

`table.sensor_arrays(model)` gives per-geom-id arrays for
[`lidar_returns`](reference/guides-sensor-materials.md). Build them once per model.
