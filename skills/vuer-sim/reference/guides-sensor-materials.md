# Sensor materials

`SensorMaterial` tells simulated sensors how a surface looks.

```python
from vuer_sim import SensorMaterial

glass = SensorMaterial("glass", lidar_reflectivity=0.08, transparent=True)
velvet = SensorMaterial("black_velvet", lidar_reflectivity=0.02)
foliage = SensorMaterial("foliage", dropout=0.3, depth_noise_std=0.02)
```

| Field | Default | Meaning |
| --- | --- | --- |
| `lidar_reflectivity` | 0.5 | Diffuse reflectivity at the LiDAR wavelength, 0 to 1. |
| `intensity` | `None` | Reported intensity (0–255, Livox scale). `None` gives `round(150 × reflectivity)`. |
| `dropout` | 0 | Probability that a return is lost. |
| `transparent` | `False` | The beam goes through the surface (glass). |
| `depth_noise_std` | 0 | Extra range noise in metres, 1 sigma. |

## lidar_returns

`lidar_returns(geom_ids, ranges, table, rng)` is a pure function. Its input is
what a ray-cast LiDAR gives for each ray: the id of the geom that the ray hit
(-1 for no hit) and the range. robot-env's simulated Livox Mid-360
(`rigs.sim.lidar.RayLidar`, on the `vuer-env/lab-room` branch) casts its rays
with `mujoco.mj_multiRay` and keeps these two arrays.

```python
import numpy as np
from vuer_sim import MaterialTable, lidar_returns

table = MaterialTable.load("bundle")
arrays = table.sensor_arrays(model)            # once per model: per-geom-id arrays
rng = np.random.default_rng(0)

# geom (N,) int32 and dist (N,) float64, from mj_multiRay
out = lidar_returns(geom, dist, arrays, rng)
out.ranges      # (N,) float64, 0 where there is no return
out.valid       # (N,) bool
out.intensity   # (N,) float32, 0 where there is no return
points = directions * out.ranges[:, None]
```

`table` can also be a `{geom_id: SensorMaterial}` mapping or a list indexed by
geom id. Geoms without a sensor material get `SensorMaterial()`.

## What it does, in order

1. **No hit.** `geom_id < 0` or `range ≤ 0` gives no return.
2. **Range noise.** The range gets `N(0, depth_noise_std)` of the material.
3. **Dropout.** The return is lost with probability `dropout`.
4. **Glass.** For a `transparent` material, the surface gives a return only
   with probability `lidar_reflectivity`. The Fresnel reflection of glass at
   near-normal incidence is about 4 to 8 percent.
5. **Black surfaces.** The received power of a diffuse target falls as
   `reflectivity / range²`. So the largest range for reflectivity `p` is
   `range_at_10pct × sqrt(p / 0.1)`. The default `range_at_10pct` is 40 m, the
   Livox Mid-360 data-sheet range at 10 percent reflectivity. A black surface
   of 2.5 percent is visible to 20 m. Transparent materials do not use this law.
6. **Intensity.** `SensorMaterial.intensity` if it is set, else
   `round(150 × reflectivity)` (the Livox scale: 0–150 diffuse, 151–255
   retroreflective).
7. `max_range` (optional) removes returns beyond it.

The function draws the same number of random values for every frame, so a
fixed seed gives the same output.

## Limits

- **Behind the glass.** The function gets only the first hit of each ray, so it
  cannot return what is behind a glass pane. To see through glass, put the
  glass geoms in a geom group that the rays exclude (the `geomgroup` argument
  of `mj_multiRay`), and keep a second cast with the glass included for the
  glass returns.
- **No incidence angle.** The reflectivity does not change with the angle of
  incidence. Grazing rays on dark surfaces are too strong.
- **No multipath and no mixed pixels.** A beam that hits an edge returns one
  range.
- The data-sheet range at 80 percent (70 m) is lower than the square-root law
  gives (113 m), because the sensor caps it. The law is for dark targets, where
  it matters. Use `max_range` for the cap.

## Statistics that the tests check

`tests/test_sensor.py` checks, on frames of 200,000 rays:

- the dropout rate is `dropout` within 4 standard errors;
- the range noise has mean 0 and standard deviation `depth_noise_std` within 2 percent;
- the glass return rate is `lidar_reflectivity`, at 2 m and at 100 m;
- a 2.5 percent surface returns at 19.9 m and not at 20.1 m;
- a mixed frame keeps the rate of each geom.

`tests/test_mujoco.py::test_lidar_on_scene` casts rays at the glass window of
the sample scene with `mj_multiRay` and checks the return rate.
