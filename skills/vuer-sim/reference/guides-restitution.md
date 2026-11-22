# Restitution in MuJoCo

MuJoCo has no restitution coefficient. vuer-sim maps restitution to the damping
ratio of the contact, `solref[1]`. The owner approved this mapping on
2026-11-22.

## The model

A MuJoCo contact is a soft constraint. Its reference acceleration is that of a
mass-spring-damper, set by `solref = (timeconst, dampratio)`:

- damping `b = 2 / (dmax · timeconst)`
- stiffness `k = d(r) / (dmax² · timeconst² · dampratio²)`

At a constant impedance `d`, the effective damping ratio of this oscillator is
`dampratio`. A linear spring-damper with damping ratio `z < 1` that stays in
contact for one half period leaves with the coefficient of restitution `e`:

```text
e = exp(-π z / sqrt(1 - z²))          restitution from the damping ratio
z = -ln(e) / sqrt(π² + ln(e)²)        damping ratio from the restitution
```

| Restitution e | 0 | 0.2 | 0.4 | 0.5 | 0.6 | 0.8 | 0.9 | 1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Damping ratio z = `solref[1]` | 1 | 0.456 | 0.280 | 0.215 | 0.160 | 0.071 | 0.034 | 0 |

`e = 0` maps to `z = 1`, critical damping, which is the MuJoCo default. Every
`z ≥ 1` maps back to `e = 0`, so an over-damped `solref` loses its exact value
in a round trip through `restitution`.

The direct form `solref = (-stiffness, -damping)` maps through
`z = damping / (2 · sqrt(stiffness))`. `from_mjcf` reads it. A `restitution`
on a direct-form material keeps the stiffness and sets the damping.

```python
from vuer_sim import restitution_to_dampratio, dampratio_to_restitution, solref_restitution

restitution_to_dampratio(0.5)  # 0.2154
dampratio_to_restitution(0.2154)  # 0.5
solref_restitution((-10000, -100))  # 0.163 (z = 0.5)
```

## Limits

The formula is exact for a linear oscillator that can pull as well as push. A
MuJoCo contact is different in three ways:

1. **The contact releases early.** It stops when the constraint force reaches
   zero, not when the penetration reaches zero.
2. **The impedance changes with depth.** `solimp` makes `d(r)` grow from
   `solimp[0]` to `solimp[1]` over the width `solimp[2]`.
3. **The step is discrete.** The stiffness grows as
   `1 / (timeconst · dampratio)²`. When `timestep > timeconst · dampratio`, the
   error grows, and high restitution gains energy (the ball leaves faster than
   it came in).

Keep `timestep ≤ timeconst · min(0.5, dampratio)`. `PhysicsMaterial.max_stable_timestep()`
gives this value, and `MaterialTable.apply` adds a warning for each material
that breaks it. At `e = 0` the rule is MuJoCo's own rule, `timeconst ≥ 2 · timestep`.

## Measured values

A sphere of radius 5 cm hits a plane at 2 m/s, with no gravity, the default
`solimp`, and the integrator `implicitfast` (`Euler` gives the same values).
The value is the exit speed divided by the impact speed. MuJoCo 4.0.1.

| target e | 0 | 0.2 | 0.4 | 0.6 | 0.8 | 0.9 |
| --- | --- | --- | --- | --- | --- | --- |
| timeconst 0.02 s, timestep 2 ms | 0.13 | 0.31 | 0.46 | 0.62 | 0.76 | unstable (3.65) |
| timeconst 0.01 s, timestep 2 ms | 0.12 | 0.30 | 0.45 | 0.61 | unstable | unstable |
| timeconst 0.02 s, timestep 0.5 ms | 0.13 | 0.31 | 0.46 | 0.62 | 0.80 | 0.89 |
| timeconst 0.02 s, timestep 2 ms, 0.5 m/s | 0.11 | 0.28 | 0.41 | 0.58 | 0.95 | unstable |
| timeconst 0.02 s, timestep 2 ms, 5 m/s | 0.14 | 0.35 | 0.51 | 0.73 | 1.19 | unstable |

What the table shows:

- Between `e = 0.2` and `e = 0.6`, at a stable timestep, the measured value is
  within 0.11 of the target.
- At `e = 0`, a ball still leaves at about 0.12 of its impact speed. This comes
  from the early release.
- The result depends on the impact speed, because `solimp` makes the contact
  nonlinear.
- Above the stability limit, the result is wrong and can gain energy.

`tests/test_mujoco.py::test_measured_restitution` checks the 2 ms row within
0.12, and the 0.5 ms row at `e = 0.9` within 0.03.

## Pairs of materials

MuJoCo mixes the `solref` of the two geoms by `solmix`, or it takes the
`solref` of the geom with the higher `priority`. The restitution of the pair is
the restitution of the mixed `solref`, not a mix of the two restitutions. To
get an exact restitution for a pair, give one of the two geoms a higher
priority.
