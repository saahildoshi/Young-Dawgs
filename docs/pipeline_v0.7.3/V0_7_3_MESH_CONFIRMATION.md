# Development mesh confirmation

| Family / seed3100 | H1 MPa | H2 MPa | Relative change |
|---|---:|---:|---:|
| BASE | 1751.880129 | 1740.976774 | 0.6224% |
| V1_ELONGATION | 1750.964717 | 1740.038077 | 0.6240% |
| V2_VERTICAL | 1738.211449 | 1727.915645 | 0.5923% |
| V3_HORIZONTAL | 1644.697742 | 1635.695181 | 0.5474% |
| V4_DISPERSION | 1728.975761 | 1718.738107 | 0.5921% |

All five first-seed geometries were selected before outcomes and independently reopened. H2 subdivides each unchanged source pixel into2×2 quads, preserving count and phase geometry. No final held-out H2 cases exist. Largest observed relative change is 0.624035%. The horizontal-bias first-seed reduction persists beyond combined observed H1/H2 changes. Elongation, vertical-bias and dispersion means do not receive the required first-seed effect support under the registered rule; this is not proof their true effects are zero.

The registered rule proposes 1658.524267 MPa toward V3_HORIZONTAL, but rejects it: baseline separation 33.117710 MPa is below the required 69.831672 MPa. The ±2.0% proposal band contains the baseline mean. No actual target or J_target was frozen; their machine-readable values are null.

There is no target-hit classification or target improvement to confirm. These differences are observed sensitivity diagnostics, not rigorous FE error bounds, complete mesh convergence or segmentation-resolution convergence.
