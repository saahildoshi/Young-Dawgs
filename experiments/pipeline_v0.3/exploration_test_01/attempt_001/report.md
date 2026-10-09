# Parametric exploration report

Measured: 20/20; connected and spanning: 20/20; all numeric gates passed: 19/20.

Unique geometries: 20. Duplicate groups: 0.

| Control | Requested/measured Spearman | Between-design SD | Within-design RMS SD |
|---|---:|---:|---:|
| solid_fraction_target | 1 | 0.029433 | 0 |
| strut_scale | 0.32121 | 0.38147 | 0.032462 |
| pore_scale | 0.85317 | 0.76596 | 0.15865 |

## Revision guidance

Retain the same parameter interface and design plan when comparing revisions.
Repair disconnected networks in the generator; never add islands to satisfy density.
If a control has negligible measured span or weak/reversed association, inspect its implementation.
Inspect failed designs and requested-versus-achieved columns, not only ensemble means.
Reduce curve errors only enough to meet the stated family limits; do not collapse designs to the anchor.
Inspect montage.png for recognizable morphology and unwanted artifacts.

- Spearman associations from a small multivariable design are not causal sensitivity estimates.
- Large between-design variation alone does not demonstrate useful morphology control.
- Common random seeds pair designs; within-design standard deviation uses ddof=1.
- Curve gates are necessary numeric checks, not proof of recognizable morphology; inspect montage.
- Bounds may be jointly infeasible. Requested values are controls, not guaranteed measurements.
- No FEM, mechanical properties or strength predictions have been computed.
