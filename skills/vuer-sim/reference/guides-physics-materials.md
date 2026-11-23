# Physics materials

`PhysicsMaterial` holds the contact parameters of one surface.

```python
from vuer_sim import PhysicsMaterial

rubber = PhysicsMaterial(
    "rubber",
    friction=(0.9, 0.005, 0.0001),   # slide, torsion, roll
    restitution=0.7,
    density=1200,                    # kg/m^3
)
rubber.solref        # (0.02, 0.1128...): restitution sets the damping ratio
```

## Fields

| Field | Default | Meaning |
| --- | --- | --- |
| `name` | `"default"` | The material name. |
| `friction` | `(1, 0.005, 0.0001)` | MuJoCo `friction`: sliding, torsional and rolling coefficients. One or two values fill the rest with the defaults, as MJCF does. |
| `restitution` | from `solref` | Coefficient of restitution, 0 to 1. It sets `solref[1]`. See [Restitution in MuJoCo](reference/guides-restitution.md). |
| `density` | `1000` | kg/m³. MuJoCo uses it to compute the inertia. |
| `solref` | `(0.02, 1)` | MuJoCo `solref`: `(timeconst, dampratio)`, or `(-stiffness, -damping)`. |
| `solimp` | `(0.9, 0.95, 0.001, 0.5, 2)` | MuJoCo `solimp`. Three values fill the last two with the defaults. |
| `condim` | `3` | Contact dimension: 1, 3, 4 or 6. |
| `priority` | `0` | The geom with the higher priority gives its parameters to the contact. |
| `margin` | `0` | Contact margin in metres. |
| `gap` | `0` | Contact gap in metres: contacts within `margin + gap` are detected, forces start at `margin`. |

The defaults are the MuJoCo defaults, so an empty `PhysicsMaterial()` does not
change a scene.

`restitution` and `solref[1]` describe the same quantity. If you give
`restitution`, it sets `solref[1]`. If you do not give it, it is computed from
`solref`. If you give both, `restitution` wins.

## MJCF

`to_mjcf()` returns the geom attributes as strings. Numbers use the shortest
text that reads back to the same float.

```python
rubber.to_mjcf()
# {'friction': '0.9 0.005 0.0001', 'solref': '0.02 0.11280...', 'solimp': '0.9 0.95 0.001 0.5 2',
#  'condim': '3', 'priority': '0', 'margin': '0', 'gap': '0', 'density': '1200'}

import xml.etree.ElementTree as ET
ET.tostring(rubber.to_mjcf_default())   # <default class="rubber"><geom .../></default>
```

`from_mjcf` reads a `<geom>` element, a `<default class>` element, an attribute
mapping, or XML text. Attributes that are not there keep the values of `base`
(the MuJoCo defaults when `base` is `None`).

```python
PhysicsMaterial.from_mjcf('<geom friction="0.4" solref="0.02 0.215" density="700"/>', name="wood")
```

`mjcf_defaults(root)` resolves every `<default>` class of a model, with
inheritance from the parent class, as MuJoCo does:

```python
from vuer_sim import mjcf_defaults
classes = mjcf_defaults(ET.parse("scene.xml").getroot())   # {"main": ..., "soft": ...}
```

`PhysicsMaterial.from_model(model, geom)` reads a compiled `mujoco.MjModel`.
The compiled model does not keep the density, so the result has the default
density.

## USD

The USD converters need `pxr` (`pip install 'vuer-sim[usd]'`). The attribute
names are those of MuJoCo's own USD schema, `mjcPhysics`, pinned at **MuJoCo
4.0.1** (`src/experimental/usd/mjcPhysics/schema.usda`). They match what
MuJoCo's USD exporter writes and what its importer reads at that version.

```python
from pxr import Usd, UsdGeom

stage = Usd.Stage.CreateNew("scene.usda")
ball = UsdGeom.Sphere.Define(stage, "/World/ball").GetPrim()
rubber.to_usd(stage, "/Materials/rubber", colliders=[ball])   # material prim + binding + collider attributes

PhysicsMaterial.from_usd(ball)   # everything: collider attributes + bound material
```

The schema puts the contact parameters on two prims. The friction, restitution
and density belong to the **material prim**. The constraint parameters belong
to each **collider prim**, because MuJoCo sets them per geom.

| PhysicsMaterial | Prim | USD attribute |
| --- | --- | --- |
| `friction[0]` (slide) | material | `physics:dynamicFriction` (also `physics:staticFriction`, for PhysX) |
| `friction[1]` (torsion) | material | `mjc:torsionalfriction` + `newton:torsionalFriction` |
| `friction[2]` (roll) | material | `mjc:rollingfriction` + `newton:rollingFriction` |
| `restitution` | material | `physics:restitution` |
| `density` | material | `physics:density`, in stage units: `kg/m³ × metersPerUnit³ / kilogramsPerUnit` |
| `solref`, `solimp` | collider | `mjc:solref`, `mjc:solimp` |
| `condim`, `priority` | collider | `mjc:condim`, `mjc:priority` |
| `margin`, `gap` | collider | `mjc:margin` + `newton:contactMargin`, `mjc:gap` + `newton:contactGap` |

The material prim gets `PhysicsMaterialAPI` and `MjcMaterialAPI`. Each collider
gets `PhysicsCollisionAPI`, `MjcCollisionAPI` and the material binding with the
purpose `physics`. usd-core does not register the `mjcPhysics` plugin, so the
API names are authored as tokens in `apiSchemas`, as MuJoCo's exporter does.
`vuer_sim.usd.authored_api_schemas(prim)` lists them.

**The `newton:` twins.** At 4.0.1 the schema marks `mjc:torsionalfriction`,
`mjc:rollingfriction`, `mjc:margin` and `mjc:gap` as deprecated in favour of the
`newton:` names. vuer-sim writes both with the same value. MuJoCo's importer
reads the `mjc:` value first and does not warn when the `newton:` twin is also
present. When vuer-sim reads, `mjc:` wins, then `newton:`. So files from
MuJoCo's own exporter, which write only the `newton:` names, read correctly.

**Restitution.** MuJoCo's importer ignores `physics:restitution` and warns.
The bounce that MuJoCo uses travels in `mjc:solref` on the collider. When a
collider has `mjc:solref`, `from_usd` reads `solref` from it and computes
`restitution` from it. A material prim alone gives `restitution` from
`physics:restitution` (with the default time constant).

**A material prim alone** gives friction, restitution and density. `solimp`,
`condim`, `priority`, `margin`, `gap` and the time constant keep the MuJoCo
defaults, because the schema has no place for them on a material.

A material from another tool has only the `UsdPhysics` attributes. Then the
torsion and roll friction get the MuJoCo defaults. A `physics:density` of 0
means "not set" in UsdPhysics, so the density stays at 1000 kg/m³. When the
static friction differs from the dynamic friction, it goes to
`extra["static_friction"]`. `solmix` is not mapped.

**Sensor materials** have no MuJoCo equivalent. They are the only custom
attributes: `SensorMaterial.to_usd(stage, path)` writes
`vuersim:lidarReflectivity`, `vuersim:lidarIntensity`, `vuersim:dropout`,
`vuersim:transparent` and `vuersim:depthNoiseStd` on the material prim.
`SensorMaterial.from_usd(prim)` reads them from a material prim or through the
binding of a collider.

The pip `mujoco` wheel has no USD decoder plugin, so the tests check the
attribute names and the round trips with `pxr`, not by an import into MuJoCo.

## How MuJoCo combines two materials

A contact has two geoms. MuJoCo combines their parameters:

- **Friction**: the larger value of each of the three coefficients. PhysX uses
  the average by default, so the same USD scene can slide differently in
  MuJoCo and in Isaac Sim.
- **solref and solimp**: a weighted mean with the weights of `solmix`. So the
  restitution of a pair is the restitution of the mixed `solref`.
- **priority**: when the priorities are different, the geom with the higher
  priority gives all its parameters.

To get one exact pair value, give one geom of the pair a higher priority.
