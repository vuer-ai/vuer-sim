# vuer-sim

Simulation materials for MuJoCo and USD scenes.

- **`PhysicsMaterial`**: friction (slide, torsion, roll), restitution, density, `solref`,
  `solimp`, `condim`, `priority`, `margin`, with `from_mjcf`/`to_mjcf` (geom attributes and
  `<default>` classes) and `from_usd`/`to_usd` (`UsdPhysics.MaterialAPI`).
- **Restitution in MuJoCo** through the `solref` damping ratio:
  `z = -ln(e) / sqrt(π² + ln(e)²)`. The [docs](docs/pages/guides/restitution/+Page.mdx)
  give the limits and measured bounce values.
- **`infer_physics`**: a visual-to-physics lookup table (wood, metal, plastic, rubber,
  glass, fabric, ceramic, ...) with sources and a confidence.
- **`SensorMaterial`** and **`lidar_returns`**: dropout, glass, black surfaces, range noise
  and intensity for the per-ray geom ids of a ray-cast LiDAR.
- **`MaterialTable`**: `materials.json` in a scene bundle; `load`, `save`, `apply(model)`.
- **Editor**: `@vuer-ai/vuer-sim` (TypeScript) edits a table in the browser and saves it
  through vuer events that `vuer_sim.viewer` handles.

The core needs only numpy. vuer is optional.

```bash
pip install vuer-sim              # core
pip install 'vuer-sim[mujoco]'    # apply tables to MuJoCo models
pip install 'vuer-sim[usd]'       # USD converters (usd-core)
pip install 'vuer-sim[viewer]'    # editor events (vuer)
```

```python
import mujoco
from vuer_sim import MaterialTable, infer_physics

spec = mujoco.MjSpec.from_file("examples/lab_table/scene.xml")
table = MaterialTable()
for m in spec.materials:
    guess = infer_physics({"name": m.name, "base_color": list(m.rgba)}, name=m.name)
    table.add(guess.material)
    table.assign[f"material:{m.name}"] = m.name
table.save("examples/lab_table")  # materials.json
table.apply(spec)
model = spec.compile()
```

See `examples/build_material_table.py` and `examples/edit_materials.py`.

## Docs

The docs are a [dockit](https://dockit.dreamlake.ai) site in `docs/` (`pnpm --dir docs dev`).
The agent skill is generated into `skills/vuer-sim/`.

## Development

```bash
uv sync --group dev --group heavy
make check                  # lint, typecheck, fast tests: what PR CI runs
./scripts/local-checks.sh   # MuJoCo, USD and vuer tests, and the example
```

Release: a `Release vX.Y.Z` PR bumps `pyproject.toml` and `CHANGELOG.md`; after the merge,
`make release` tags `vX.Y.Z` and publishes to PyPI.

## License

MIT
