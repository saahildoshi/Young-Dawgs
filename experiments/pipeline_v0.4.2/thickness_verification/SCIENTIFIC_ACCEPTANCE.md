# Pipeline v0.4.2 — thickness convergence verification

Scientific status: **HOLD**. Generator v0.4.1 and evaluator v1.1 unchanged. No CAD started.

## Acceptance

| Gate | Result |
|---|---|
| topology_30_of_30 | PASS |
| baseline_10_of_10 | PASS |
| stochastic_identity | PASS |
| density_and_curves | PASS |
| all_ten_2048_complete | PASS |
| 2048_topology_repeat_identity | PASS |
| p10_controls_qualified | HOLD |
| p10_control_width_coverage | PASS | 
| mean_1024_2048 | PASS |
| p10_1024_2048 | PASS |
| pore_1024_2048 | PASS |
| density_curves_1024_2048 | PASS |
| repaired_neck_local_screen | PASS |
| historical_and_code_unchanged | PASS |

## All ten high-resolution pairs

P10 limit from controls: 10.000000%; mean and pore limits: 3%.

| Design | Seed | Mean % | P10 % | Pore % | All pair gates |
|---:|---:|---:|---:|---:|---|
| 0 | 0 | 1.595965 | 0.000000 | 0.863618 | PASS |
| 0 | 1 | 1.693696 | 0.000000 | 0.114370 | PASS |
| 1 | 0 | 1.866973 | 2.371879 | 0.117855 | PASS |
| 1 | 1 | 1.845614 | 2.371879 | 0.396715 | PASS |
| 2 | 0 | 1.759402 | 7.804555 | 0.239139 | PASS |
| 2 | 1 | 1.793689 | 1.242284 | 0.222140 | PASS |
| 5 | 0 | 1.529162 | 0.956960 | 0.277393 | PASS |
| 5 | 1 | 1.579684 | 0.956960 | 0.127962 | PASS |
| 9 | 0 | 1.631651 | 2.899151 | 0.138793 | PASS |
| 9 | 1 | 1.843516 | 2.899151 | 0.324445 | PASS |

## Successive changes (signed, lower-resolution denominator)

| Design | Seed | Step | Mean % | P10 % | Pore % |
|---:|---:|---|---:|---:|---:|
| 0 | 0 | 256 → 512 | -5.883106 | +11.803399 | +0.000000 |
| 0 | 0 | 512 → 1024 | -2.873899 | +11.803399 | -2.172026 |
| 0 | 0 | 1024 → 2048 | -1.595965 | +0.000000 | +0.863618 |
| 0 | 1 | 256 → 512 | -6.003583 | +11.803399 | +0.000000 |
| 0 | 1 | 512 → 1024 | -2.915698 | +11.803399 | +0.183487 |
| 0 | 1 | 1024 → 2048 | -1.693696 | +0.000000 | -0.114370 |
| 1 | 0 | 256 → 512 | -6.607923 | +0.000000 | +0.000000 |
| 1 | 0 | 512 → 1024 | -3.671028 | +0.000000 | +0.956960 |
| 1 | 0 | 1024 → 2048 | -1.866973 | -2.371879 | +0.117855 |
| 1 | 1 | 256 → 512 | -6.987907 | +0.000000 | -4.278998 |
| 1 | 1 | 512 → 1024 | -3.455766 | +0.000000 | +2.100579 |
| 1 | 1 | 1024 → 2048 | -1.845614 | -2.371879 | -0.396715 |
| 2 | 0 | 256 → 512 | -6.714769 | +11.803399 | +0.000000 |
| 2 | 0 | 512 → 1024 | -2.987598 | +11.803399 | -0.941936 |
| 2 | 0 | 1024 → 2048 | -1.759402 | -7.804555 | -0.239139 |
| 2 | 1 | 256 → 512 | -6.844739 | +11.803399 | +3.654150 |
| 2 | 1 | 512 → 1024 | -3.378525 | +0.000000 | -0.849099 |
| 2 | 1 | 1024 → 2048 | -1.793689 | +1.242284 | -0.222140 |
| 5 | 0 | 256 → 512 | -6.274841 | +41.421356 | -4.802836 |
| 5 | 0 | 512 → 1024 | -2.685265 | -9.861218 | -1.520175 |
| 5 | 0 | 1024 → 2048 | -1.529162 | +0.956960 | +0.277393 |
| 5 | 1 | 256 → 512 | -5.612092 | +41.421356 | -2.371879 |
| 5 | 1 | 512 → 1024 | -2.837710 | -9.861218 | +0.000000 |
| 5 | 1 | 1024 → 2048 | -1.579684 | +0.956960 | +0.127962 |
| 9 | 0 | 256 → 512 | -6.974708 | +0.000000 | -6.973949 |
| 9 | 0 | 512 → 1024 | -3.479638 | +3.077641 | +0.000000 |
| 9 | 0 | 1024 → 2048 | -1.631651 | +2.899151 | +0.138793 |
| 9 | 1 | 256 → 512 | -6.970747 | +0.000000 | -2.927466 |
| 9 | 1 | 512 → 1024 | -3.265799 | +3.077641 | -0.768257 |
| 9 | 1 | 1024 → 2048 | -1.843516 | +2.899151 | -0.324445 |

## Sampling versus generator contribution

Fixed-2048 controls vary sampling only. Agreement supports a dominant sampling pattern; it does not prove zero generator discretization error.

| Design | Seed | Native mean step % | Fixed-geometry mean step % | Residual percentage points | Dominant pattern |
|---:|---:|---:|---:|---:|---|
| 0 | 0 | -1.595965 | -1.726051 | +0.130086 | True |
| 0 | 1 | -1.693696 | -1.618570 | -0.075126 | True |
| 1 | 0 | -1.866973 | -1.926400 | +0.059427 | True |
| 1 | 1 | -1.845614 | -1.811638 | -0.033976 | True |
| 2 | 0 | -1.759402 | -1.825912 | +0.066510 | True |
| 2 | 1 | -1.793689 | -1.874272 | +0.080582 | True |
| 5 | 0 | -1.529162 | -1.612283 | +0.083120 | True |
| 5 | 1 | -1.579684 | -1.640428 | +0.060744 | True |
| 9 | 0 | -1.631651 | -1.943707 | +0.312056 | True |
| 9 | 1 | -1.843516 | -1.834522 | -0.008994 | True |

## Repaired neck screen

| Design | Seed | N | Added pixels | Solid pixels tested individually | Articulation pixels | Local screen |
|---:|---:|---:|---:|---:|---:|---|
| 9 | 1 | 512 | 4 | 44 | 0 | PASS |
| 9 | 1 | 1024 | 15 | 92 | 0 | PASS |
| 9 | 1 | 2048 | 46 | 229 | 0 | PASS |

Boundary clipping means the occupied neck depth can be roughly HALF the nominal capsule diameter. Inspect `repair_inspection.json` and the native-pixel repair figures.
A no-one-pixel-neck result is NOT mechanical, mesh-quality or manufacturing certification: physical scale, loads, material and minimum feature size are unspecified.

## Preservation and scope

Historical inventories unchanged: True. Code unchanged: True.
Previous v0.4.1 HOLD remains historical evidence. The new criterion was recorded before all ten new native diagnostics.
2048 is a diagnostic grid, not a newly adopted production resolution. This milestone produces no CAD, vector geometry, mesh, STEP or STL.
Execution was on macOS. PowerShell reproduction commands are documented separately; Windows execution is not claimed.

## Post-run scientific interpretation

All ten native pairs satisfy every numerical pair gate: mean thickness changes
by 1.529–1.867%, P10 by 0–7.805%, and pore diameter by 0.114–0.864%.
**The sole overall HOLD is analytic P10 calibration, not a failed native sample.**
The unchanged generator is preserving morphology sufficiently to satisfy the
specified native high-resolution tests in this ten-case subset. No new
generator defect was identified that justifies a corrective revision.

The 48 analytic geometry/width/offset combinations (192 masks across four
resolutions) require a maximum P10 discretization envelope of **12.6681%**.
The protocol prospectively capped this at 10%, so calibration is unqualified
even though all native P10 changes are within 10%. This ceiling was not raised
after seeing the additional results.

The worst control is a shifted 30° bar of width $6/256$. Its fraction of thin
skeleton samples, below 90% of nominal width, rises from 9.9156% to 11.2720%.
All such samples lie near the bar ends; crossing the 10% threshold moves P10
into this endpoint tail. This is a sampling/skeleton-statistic sensitivity in
unchanged analytic geometry. The [post-hoc endpoint audit](../control_outlier_audit/ENDPOINT_AUDIT.md)
explains it without excluding the control or replacing frozen whole-mask P10.

The fixed-2048 controls reproduce the dominant native mean-thickness pattern
in all ten cases, with a maximum residual of 0.3121 percentage points.
Nine native P10 change magnitudes are reproduced exactly. Design 2/seed 1 is
an exception: native +1.2423% versus sampling-only −9.4461%. Therefore the
evidence supports a dominant sampling explanation, not a claim of zero
generator discretization error in all lower-tail measurements.

The repaired boundary connections have inward depths of 3, 5 and 9 pixels at
512, 1024 and 2048. None of 365 individually tested connector-neighborhood
solid pixels is an articulation. This resolves the local one-pixel-neck screen;
it does not certify the physical strength or manufacturability of a neck.

**Recommendation:** conclude this diagnostic pass without another generator
revision. The remaining decision is how to qualify P10 as an acceptance metric
given its demonstrated endpoint-population sensitivity. Do not silently waive
the recorded calibration failure or begin CAD under a full-resolution PASS.

Software verification: **196 tests passed**. The three earlier 2048 diagnostic
arrays were reproduced bitwise, and historical v0.4/v0.4.1 inventories and all
registered generator/evaluator code hashes remain unchanged. See
[verification evidence](../verification/verification.json).
