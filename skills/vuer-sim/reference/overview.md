# vuer-sim

vuer-sim gives simulation scenes their materials. A material tells the physics
engine how a surface touches other surfaces, and it tells simulated sensors how
the surface looks to a LiDAR or a depth camera.

## The two packages

| Package | Language | What it gives |
| --- | --- | --- |
| `vuer-sim` (PyPI, import `vuer_sim`) | Python | `PhysicsMaterial` with MJCF and USD converters, `infer_physics`, `SensorMaterial` and `lidar_returns`, `MaterialTable`, the editor's vuer events |
| `@vuer-ai/vuer-sim` (npm) | TypeScript | `MaterialInspector`, `PhysicsMaterialEditor`, `SensorMaterialOverlay`, `useMaterialTable` |

The Python core needs only numpy. MuJoCo, USD (`pxr`) and vuer are optional
extras. vuer-sim does not depend on vuer-robot.

## Where to start

- [Install](reference/get-started-install.md) the package and the extras that you need.
- [Physics materials](reference/guides-physics-materials.md): friction, restitution, density and the MuJoCo contact parameters, read from and written to MJCF and USD.
- [Restitution in MuJoCo](reference/guides-restitution.md): the formula, its limits and measured values.
- [Visual to physics](reference/guides-inference.md): guess a physics material from a material name or PBR parameters.
- [Sensor materials](reference/guides-sensor-materials.md): LiDAR reflectivity, dropout, glass and black surfaces.
- [Material tables](reference/guides-material-table.md): the JSON file in a scene bundle, and how to apply it to a model.
- [Editor](reference/editor-overview.md): edit a table in the browser and save it back through vuer.

## A first example

```python file="example.py"
import mujoco
from vuer_sim import MaterialTable, infer_physics

spec = mujoco.MjSpec.from_file("examples/lab_table/scene.xml")
table = MaterialTable()
for material in spec.materials:
    guess = infer_physics({"name": material.name, "base_color": list(material.rgba)}, name=material.name)
    table.add(guess.material)
    table.assign[f"material:{material.name}"] = material.name

table.save("examples/lab_table")  # writes examples/lab_table/materials.json
report = table.apply(spec)  # sets friction, solref, solimp, density, ...
model = spec.compile()
```

The full script is `examples/build_material_table.py`.
