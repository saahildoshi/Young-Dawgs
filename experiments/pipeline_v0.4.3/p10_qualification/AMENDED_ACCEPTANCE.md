# v0.4.3 — amended lower-tail qualification decision

Decision: **AMENDED_PASS_TESTED_DOMAIN**.

Original 10% P10 calibration: **FAILED, unchanged**. Historical v0.4.2: **HOLD, unchanged**.
P10 is retained as a diagnostic, not relabeled as a passing calibration. No generator/evaluator change or CAD execution.

## Prospective method

$A=\int_0^{4/256}|F_{1024}(w)-F_{2048}(w)|\,dw \le 1/1024$.
CDFs are unconditional empirical distributions of unchanged frozen skeleton-thickness samples. Integration uses exact step-function knots.
One 1024 pixel is a declared aggregate numerical-displacement budget, not a physical safety tolerance.
Local necks require occupied normal depth ≥3/1024 in the specified ROI. Aggregate CDF checks alone may miss rare defects.

## Independent invariant controls

| Control | CDF area ×1024 (limit 1) | Maximum CDF gap (diagnostic) | Pass |
|---|---:|---:|---|
| bar17_w2.5 | 0.266135 | 0.453330 | True |
| bar17_w3.5 | 0.417704 | 0.567752 | True |
| bar38_w2.5 | 0.120530 | 0.550055 | True |
| bar38_w3.5 | 0.285079 | 0.404163 | True |
| bar67_w2.5 | 0.297588 | 0.501658 | True |
| bar67_w3.5 | 0.344601 | 0.455465 | True |
| ring_w2.5 | 0.102292 | 0.364770 | True |
| ring_w3.5 | 0.145944 | 0.297195 | True |
| junction_w2.5 | 0.140851 | 0.426597 | True |
| junction_w3.5 | 0.127820 | 0.312699 | True |

## Independent defect controls

| Control (25% thinner) | CDF area ×1024 | Defect detected |
|---|---:|---|
| bar38_w2.5 | 2.303995 | True |
| ring_w2.5 | 2.447381 | True |
| junction_w2.5 | 2.461699 | True |

| N | Neck | Minimum depth (px) | Minimum normalized depth | Expected outcome met |
|---:|---|---:|---:|---|
| 1024 | healthy | 3 | 0.00292969 | True |
| 1024 | weak | 1 | 0.00097656 | True |
| 2048 | healthy | 8 | 0.00390625 | True |
| 2048 | weak | 2 | 0.00097656 | True |

## Saved native pairs — only evaluated after independent qualification

| Design | Seed | CDF area ×1024 | Whole-mask P10 at 1024 | Whole-mask P10 at 2048 | Pass |
|---:|---:|---:|---:|---:|---|
| 0 | 0 | 0.157786 | 0.009765625 | 0.009765625 | True |
| 0 | 1 | 0.152510 | 0.009765625 | 0.009765625 | True |
| 1 | 0 | 0.204852 | 0.007812500 | 0.007627197 | True |
| 1 | 1 | 0.207747 | 0.007812500 | 0.007627197 | True |
| 2 | 0 | 0.189357 | 0.009765625 | 0.009003461 | True |
| 2 | 1 | 0.190135 | 0.008734641 | 0.008843150 | True |
| 5 | 0 | 0.147889 | 0.009959022 | 0.010054326 | True |
| 5 | 1 | 0.136371 | 0.009959022 | 0.010054326 | True |
| 9 | 0 | 0.188583 | 0.008052941 | 0.008286408 | True |
| 9 | 1 | 0.193391 | 0.008052941 | 0.008286408 | True |

## Decision gates

| Gate | Pass |
|---|---|
| invariant_controls | True |
| detects_25percent_thinning | True |
| local_neck_controls | True |
| topology_30_of_30 | True |
| baseline_10_of_10 | True |
| stochastic_identity | True |
| density_and_curves | True |
| all_ten_2048_complete | True |
| 2048_topology_repeat_identity | True |
| mean_1024_2048 | True |
| pore_1024_2048 | True |
| density_curves_1024_2048 | True |
| repaired_neck_local_screen | True |
| historical_and_code_unchanged | True |
| all_native_lower_tail | True |
| whole_p10_preserved | True |
| repair_neck_resolution_screen | True |
| inputs_and_code_unchanged | True |

## Limitations

- Deterministic unseen-parameter controls, not statistical independence or a confidence guarantee.
- Qualification covers the specified lower-tail interval and tested morphologies only.
- Sensitivity demonstrated for 25% uniform thinning, not all smaller/local defects.
- Local neck qualification is scoped to axis-aligned controls and inspected repairs; not an exhaustive network neck audit.
- No physical scale, material/load or manufacturing minimum is certified.
- Prior failed P10 calibration remains failed; no retrospective gate substitution in historical reports.

An amended tested-domain PASS permits considering a separate single-sample v0.5 raster-to-vector validation; it does not establish CAD validity or manufacturing suitability.
This study does not itself begin v0.5. Windows reproduction commands are documented; execution here was on macOS.
