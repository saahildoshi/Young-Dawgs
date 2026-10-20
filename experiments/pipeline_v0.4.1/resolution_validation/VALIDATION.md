# v0.4.1 — post-fix validation

Scientific status: **HOLD**. CAD/vectorization: not started.

The documented amendment uses successive dimensional convergence; the original coarse-baseline gates are still reported and are not retroactively marked PASS.

| Gate | Result |
|---|---|
| topology_30_of_30 | PASS |
| baseline_10_of_10 | PASS |
| stochastic_identity | PASS |
| historical_unchanged | PASS |
| successive_dimensions | HOLD |
| density_and_curves | PASS |
| smaller_2048_increments | PASS |
| all_jobs_complete | PASS |

## Successive-resolution dimensional gates

| Metric | Limit (512 → 1024) | Passing pairs |
|---|---:|---:|
| mean_strut_relative | 3% | 5/10 |
| p10_strut_relative | 10% | 7/10 |
| pore_relative | 3% | 10/10 |

## All post-fix pairs

| Design | Seed | Step | Mean thickness % | P10 thickness % | Pore median % |
|---:|---:|---|---:|---:|---:|
| 0 | 0 | 256 → 512 | -5.8831 | +11.8034 | +0.0000 |
| 0 | 0 | 512 → 1024 | -2.8739 | +11.8034 | -2.1720 |
| 0 | 1 | 256 → 512 | -6.0036 | +11.8034 | +0.0000 |
| 0 | 1 | 512 → 1024 | -2.9157 | +11.8034 | +0.1835 |
| 1 | 0 | 256 → 512 | -6.6079 | +0.0000 | +0.0000 |
| 1 | 0 | 512 → 1024 | -3.6710 | +0.0000 | +0.9570 |
| 1 | 1 | 256 → 512 | -6.9879 | +0.0000 | -4.2790 |
| 1 | 1 | 512 → 1024 | -3.4558 | +0.0000 | +2.1006 |
| 2 | 0 | 256 → 512 | -6.7148 | +11.8034 | +0.0000 |
| 2 | 0 | 512 → 1024 | -2.9876 | +11.8034 | -0.9419 |
| 2 | 1 | 256 → 512 | -6.8447 | +11.8034 | +3.6542 |
| 2 | 1 | 512 → 1024 | -3.3785 | +0.0000 | -0.8491 |
| 5 | 0 | 256 → 512 | -6.2748 | +41.4214 | -4.8028 |
| 5 | 0 | 512 → 1024 | -2.6853 | -9.8612 | -1.5202 |
| 5 | 1 | 256 → 512 | -5.6121 | +41.4214 | -2.3719 |
| 5 | 1 | 512 → 1024 | -2.8377 | -9.8612 | +0.0000 |
| 9 | 0 | 256 → 512 | -6.9747 | +0.0000 | -6.9739 |
| 9 | 0 | 512 → 1024 | -3.4796 | +3.0776 | +0.0000 |
| 9 | 1 | 256 → 512 | -6.9707 | +0.0000 | -2.9275 |
| 9 | 1 | 512 → 1024 | -3.2658 | +3.0776 | -0.7683 |

## Explicit generator repairs

| Design | Seed | N | Components before → after | Added pixels | Added area fraction |
|---:|---:|---:|---|---:|---:|
| 9 | 1 | 512 | 2 → 1 | 4 | 0.000015259 |
| 9 | 1 | 1024 | 2 → 1 | 15 | 0.000014305 |

No solid pixels were removed. No density erosion was needed: additions are far below the unchanged 0.005 solid-fraction tolerance.

See `summary.json` for every original and amended gate, native metrics, hashes, stochastic checks and repair endpoints; `manifest.json` retains source inventories and worker failures.

A HOLD means the implementation and diagnostics are complete, not that scientific acceptance has been obtained. Do not begin v0.5 on the basis of software test passes.
