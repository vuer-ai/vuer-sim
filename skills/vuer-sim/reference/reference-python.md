# Python API

All names below are importable from `vuer_sim` unless a module is given.

## Materials

| Name | Description |
| --- | --- |
| `PhysicsMaterial(name, friction, restitution, density, solref, solimp, condim, priority, margin, gap)` | Contact material of a geom. See [Physics materials](reference/guides-physics-materials.md). |
| `PhysicsMaterial.to_mjcf() -> dict[str, str]` | MJCF geom attributes. |
| `PhysicsMaterial.to_mjcf_default(class_name=None) -> Element` | `<default class><geom/></default>`. |
| `PhysicsMaterial.from_mjcf(source, name=None, base=None)` | Read a `<geom>`, a `<default>`, a mapping or XML text. |
| `PhysicsMaterial.from_model(model, geom, name=None)` | Read a geom of a compiled `MjModel` (density not kept). |
| `PhysicsMaterial.to_usd(stage, path, colliders=())` / `from_usd(prim, name=None)` | USD converters with the `mjcPhysics` names of MuJoCo 4.0.1 (needs `pxr`). `from_usd` reads a collider or a material prim; `None` when there is nothing to read. |
| `PhysicsMaterial.to_dict()` / `from_dict(d, name=None)` | The stored JSON form. |
| `PhysicsMaterial.max_stable_timestep() -> float` | `timeconst · min(0.5, dampratio)`. |
| `mjcf_defaults(root) -> dict[str, PhysicsMaterial]` | Resolve all `<default>` classes with inheritance. |
| `SensorMaterial(name, lidar_reflectivity, intensity, dropout, transparent, depth_noise_std)` | How a surface looks to sensors. `reported_intensity` gives the intensity. `to_usd` / `from_usd` use `vuersim:` attributes. |

## Restitution

| Name | Description |
| --- | --- |
| `restitution_to_dampratio(e) -> float` | `z = -ln(e) / sqrt(π² + ln(e)²)`; `e = 0` gives 1. |
| `dampratio_to_restitution(z) -> float` | `e = exp(-π z / sqrt(1 - z²))`; `z ≥ 1` gives 0. |
| `solref_restitution(solref) -> float` | Restitution of a standard or direct `solref`. |
| `max_stable_timestep(timeconst, restitution) -> float` | The stability rule of [Restitution in MuJoCo](reference/guides-restitution.md). |

## Inference

| Name | Description |
| --- | --- |
| `infer_physics(pbr_or_name, name=None) -> Inferred` | Guess from a name or PBR parameters. |
| `Inferred` | `material`, `category`, `confidence`, `matched`, `sources`, `ranges`, `sensor`. |
| `CATEGORIES` | The lookup table (`vuer_sim.infer.Category` rows). |
| `lookup_table() -> list[dict]` | The table as JSON-ready rows. |

## Sensors

| Name | Description |
| --- | --- |
| `lidar_returns(geom_ids, ranges, table, rng=None, *, range_at_10pct=40.0, max_range=None) -> LidarReturns` | Apply sensor materials to one frame. |
| `LidarReturns` | `ranges`, `valid`, `intensity`. |
| `SensorArrays.from_materials(materials, ngeom=None, default=SensorMaterial())` | Per-geom-id arrays. |

## Tables

| Name | Description |
| --- | --- |
| `MaterialTable(physics, sensor, assign)` | Named materials and assignment rules. |
| `MaterialTable.load(bundle)` / `save(bundle) -> Path` | `<bundle>/materials.json`, or a `.json` path. |
| `MaterialTable.loads(text)` / `dumps() -> str` | The stored form as text. |
| `MaterialTable.add(*materials)` | Add physics or sensor materials by name. |
| `MaterialTable.resolve(geom_name, visual_material=None)` | Material name for a geom. |
| `MaterialTable.assignments(model) -> dict[int, str]` | Geom id to material name. |
| `MaterialTable.apply(model_or_spec) -> ApplyReport` | Write physics materials; `assigned` and `warnings`. |
| `MaterialTable.sensor_arrays(model, default=None) -> SensorArrays` | Input for `lidar_returns`. |

## Modules

| Module | Description |
| --- | --- |
| `vuer_sim.usd` | `MJC_SCHEMA_VERSION` (`"4.0.1"`), `write_physics_material`, `write_collider`, `bind(prim, material, physics=None)`, `read_physics_material`, `write_sensor_material`, `read_sensor_material`, `authored_api_schemas`. |
| `vuer_sim.scene` | `scene_summary(model, data=None, groups=None)`: geoms as JSON for the editor. |
| `vuer_sim.viewer` | `EVENTS`, `MaterialsEndpoint`, `attach(app, bundle, scene=None)`, `serve(bundle, scene=None, port=8012)`. See [Editor](reference/editor-overview.md). |
