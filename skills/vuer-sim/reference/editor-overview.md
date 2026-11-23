# Material editor

The editor is the TypeScript package `@vuer-ai/vuer-sim` (repository
`vuer-ai/vuer-sim-ts`). It shows the scene geoms, coloured by a material
property. You select a geom, edit its material and click **Save**. The save
goes to Python as a vuer event, and Python writes `materials.json`.

![The editor on the lab_table sample scene, coloured by restitution, with table_top selected](/editor.png)

## Run it on the sample scene

```bash file="terminal"
# vuer-ai/vuer-sim
uv run --group heavy python examples/edit_materials.py examples/lab_table --port 8012

# vuer-ai/vuer-sim-ts
pnpm install && pnpm demo     # open http://localhost:5178/?ws=ws://localhost:8012
```

`examples/edit_materials.py` infers a table when the bundle has none, sends the
geoms of the scene (`vuer_sim.scene.scene_summary`) with the table, and writes
every save. The demo follows the host theme (`?theme=light|dark`, or a
`{type: 'theme', theme}` message from the parent frame), else the system theme.
`?dt=` gives the model timestep for the stability warning (default 0.002).

## Python side

```python
from vuer import Vuer
from vuer_sim.scene import scene_summary
from vuer_sim.viewer import attach

app = Vuer()
attach(app, "path/to/bundle", scene=scene_summary(model))   # registers the load and save handlers
app.run()
```

`serve(bundle, scene=None, port=8012)` does the same in one call. The logic is
in `MaterialsEndpoint`, which does not need vuer.

## Protocol

| Client to server | Server to client |
| --- | --- |
| `VUER_SIM_MATERIALS_LOAD` `{}` | `VUER_SIM_MATERIALS` `{json, path, saved: false, revision, scene}` |
| `VUER_SIM_MATERIALS_SAVE` `{json, revision}` | `VUER_SIM_MATERIALS` `{json, path, saved: true, revision}`, or `{error, revision}` |

- The table travels as its stored JSON text. vuer packs the floats of server
  events as float32, which would change a value such as `0.005` on the way to
  the browser.
- Python validates the table with `MaterialTable.loads` and writes it in the
  stored form. A table that does not validate gives `error`, and the file does
  not change.
- `revision` counts the saves. A save from an older revision is refused, so a
  second tab cannot overwrite a newer table. Reload, then save again.

## TypeScript side

```tsx
import { Canvas } from '@react-three/fiber'
import {
  MaterialInspector, OverlayLegend, SensorMaterialOverlay,
  createWebSocketTransport, useMaterialTable,
} from '@vuer-ai/vuer-sim'

const transport = createWebSocketTransport('ws://localhost:8012')

function Editor() {
  const editor = useMaterialTable(transport)
  const [geom, setGeom] = useState(null)
  return (
    <>
      <Canvas>
        <SensorMaterialOverlay geoms={editor.scene} table={editor.table}
          property="restitution" selected={geom?.name} onSelect={setGeom} />
      </Canvas>
      <OverlayLegend property="restitution" />
      <MaterialInspector geom={geom} editing={editor} timestep={0.002} />
      <button disabled={!editor.dirty} onClick={editor.save}>Save</button>
    </>
  )
}
```

Inside a `<Vuer>` app, use its socket: `useMaterialTable(useVuerTransport())`
from `@vuer-ai/vuer-sim/vuer`. Only that entry imports `@vuer-ai/vuer`.

| Export | What it does |
| --- | --- |
| `useMaterialTable(transport)` | Loads the table, edits it (`setPhysics`, `setSensor`, `assign`, `addMaterial`, `setTable`) and saves it. State: `table`, `scene`, `loaded`, `dirty`, `saving`, `revision`, `error`, `path`, `savedAt`. |
| `MaterialInspector` | The material of the selected geom: assignment by geom name or by visual material, then the physics or the sensor part. |
| `PhysicsMaterialEditor` | Friction, restitution with the derived `solref` damping ratio, density, time constant, `solimp`, `condim` (button group), priority, margin. Warns when the timestep breaks the [stability rule](reference/guides-restitution.md). |
| `SensorMaterialEditor` | LiDAR reflectivity, dropout, depth noise, intensity, transparent. |
| `SensorMaterialOverlay`, `OverlayLegend`, `overlayColors` | Draw the geoms coloured by `friction`, `restitution`, `density`, `lidar_reflectivity`, `dropout` or `transparent`. Geoms without a material are gray. |
| `parseTable`, `serializeTable`, `resolve` | The stored form (byte-identical to Python) and the assignment rules. |
| `restitutionToDampratio`, `dampratioToRestitution`, `setRestitution` | The restitution mapping, identical to Python. |
| `createWebSocketTransport`, `createLocalTransport`, `useVuerTransport` | Transports: vuer's wire protocol over a WebSocket, in memory (tests), or the socket of a vuer app. |

The components use `@dreamlake/uikit` 0.3 and its theme tokens: square
toggles, button groups for one-of-many choices, and few frames.

## Later: simulation in the browser

In-browser simulation will go through `@vuer-ai/mujoco-ts`. Version 0.0.1
edits the table only; the physics runs in Python.
