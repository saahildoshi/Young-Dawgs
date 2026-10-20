# Pipeline v0.4.2 — thickness convergence verification

## Scope and version distinction

This is a **validation-only milestone**. It uses generator **v0.4.1** and the
unchanged frozen evaluator **v1.1**. No generator width, topology-repair rule,
random realization, or evaluator definition is modified. No CAD, vectorization,
extrusion, mesh, STEP or STL is produced.

The investigation adds ten native 2048 diagnostics to the existing matched
256/512/1024 subset. All ten are freshly generated, including the three cases
previously examined at 2048. Workers run sequentially to limit peak memory.
The execution host has 24 GiB physical memory; earlier 2048 runs used roughly
681 MiB peak traced generation allocations. Tracemalloc is not total process
RSS, and these observations are not a Windows memory guarantee.

The completed scientific decision and per-case results are in
[`SCIENTIFIC_ACCEPTANCE.md`](../experiments/pipeline_v0.4.2/thickness_verification/SCIENTIFIC_ACCEPTANCE.md).
The historical v0.4.1 HOLD is preserved, irrespective of the new milestone's result.

## Completed result

**All ten native high-resolution pairs pass the numerical convergence limits.
Overall scientific status remains HOLD solely because the analytic P10
calibration exceeds its predeclared ceiling.**

| Check | Result |
|---|---|
| Native 2048 generation, exact topology, repeatability and latent identity | 10/10 pass |
| Mean thickness, 1024→2048 | 1.529–1.867%; 10/10 below 3% |
| P10 thickness, 1024→2048 | 0–7.805%; 10/10 below the retained 10% ceiling |
| Pore median, 1024→2048 | 0.114–0.864%; 10/10 below 3% |
| Maximum absolute solid-fraction change | $2.8611\times10^{-6}$ |
| Maximum $S_2$ NRMSE | 0.001010 (rounded upward) |
| Maximum lineal-path NRMSE | 0.003686 (rounded upward) |
| Fixed-geometry mean-step attribution | Dominant sampling pattern in 10/10; maximum residual 0.3121 percentage points |
| P10 calibration | Largest analytic change 12.6681%; exceeds registered 10% ceiling |
| Repaired-neck local screen | Pass at 512, 1024 and 2048; no articulation in 365 tested solid pixels |

The remaining HOLD is **not a failed native structure** and is not evidence
supporting another generator-width correction. The native mean-thickness
convergence evidence is now complete across this ten-case subset.

Software verification: **196 tests passed** (140 package tests and 56 frozen
evaluator tests). The three previous 2048 diagnostics were reproduced bitwise.
Durable logs and unchanged-history checks are in
`experiments/pipeline_v0.4.2/verification/`.

Nine of ten native P10 change magnitudes are reproduced exactly by fixed-2048
sampling controls. Design 2/seed 1 differs: native +1.2423% versus fixed-geometry
−9.4461%. This exception reinforces that a lower-tail skeleton statistic can
respond discontinuously to small sampling/geometry differences; the evidence
does not establish zero generator discretization error in every metric.

### Why the P10 calibration is on HOLD

The worst analytic control is the 30° straight bar of nominal width $6/256$,
shifted by $0.37/256$. Its whole-mask P10 changes from 0.021836601 at 1024 to
0.019070316 at 2048: **−12.6681%**, despite identical analytic geometry.

A post-hoc endpoint audit found that samples below 90% of nominal width rise
from **9.9156% to 11.2720%** of all skeleton samples. All such samples are
within one nominal width of an analytic bar end. Crossing the 10% population
threshold moves P10 into this endpoint tail. Interior P10 instead changes from
0.022777156 to 0.023150917, but **that interior-only statistic is not substituted
for the frozen evaluator**.

See [the endpoint audit](../experiments/pipeline_v0.4.2/control_outlier_audit/ENDPOINT_AUDIT.md).
This was an explanatory follow-up after calibration, not a new acceptance
criterion. The bar remains in the control suite, its failure is retained, and
the tolerance was not raised after seeing the native results.

The scientifically appropriate next decision concerns **qualification of the
P10 measurement protocol**, not another resolution sweep or generator revision.
The control-derived 12.6681% envelope is evidence to discuss, not an automatically
approved new threshold. This validation pass is complete; CAD was not begun.

### Repaired-neck findings

| N | Added pixels | Minimum gap-column inward depth | Depth / $(N-1)$ | Tested connector-neighborhood pixels | Articulations |
|---:|---:|---:|---:|---:|---:|
| 512 | 4 | 3 px | 0.00587084 | 44 | 0 |
| 1024 | 15 | 5 px | 0.00488759 | 92 | 0 |
| 2048 | 46 | 9 px | 0.00439668 | 229 | 0 |

The existing repair policy was used unchanged. At 2048 it added 46 pixels to
Design 9/seed 1; it was not redesigned for this study. These are not isolated
one-pixel bridges in the inspected neighborhoods. The physical adequacy of a
neck approximately 0.44% of domain width still depends on the actual domain
dimension, loads, material, mesh and manufacturing process.

## Prospective protocol

The workflow separates `prepare` from `run`. Preparation records the rule and
all control definitions **before** analytic calibration, and writes the
calibration result **before** any new native 2048 case is executed.

| Quantity | New high-resolution rule |
|---|---|
| Mean thickness | All ten pairs satisfy $\lvert t^*_{2048}/t^*_{1024}-1\rvert\le0.03$ |
| P10 thickness | Control-derived relative-change envelope, never exceeding the previous 10% ceiling |
| Median pore diameter | All ten pairs satisfy ≤3% relative change |
| Solid fraction | Absolute change ≤0.005 |
| $S_2$ and lineal path | Each NRMSE ≤0.05, with lower-resolution curve RMS as denominator |
| New 2048 masks | Exact single 4-connected component, both percolation directions, deterministic repeat, same accepted latent candidate |
| Historical evidence | Preserve previous baseline, stochastic identity, density/correlation and topology passes; verify files and source hashes |
| Local repaired neck | No one-pixel articulation in the connector neighborhood; occupied inward depth across the boundary gap ≥$1/255$ of the endpoint-defined domain |

Normalized dimensional measurements remain $t/N$ and $d_p/N$. Geometry and
repair coordinates retain the renderer's endpoint convention $i/(N-1)$.
The normalization distinction is not silently changed in this milestone.

### Analytic P10 calibration

There are **192 analytic masks**:

- Six families: 0°, 30° and 45° straight bars, an annulus, a T junction, and a Y junction.
- Four fixed normalized widths: $2/256$, $3/256$, $4/256$, and $6/256$.
- Two fixed position offsets: 0 and 0.37 baseline pixels.
- Four resolutions: 256, 512, 1024 and 2048.

Every mask is sampled independently at pixel centers from an analytic shape;
finished masks are never interpolated to produce these controls. The offsets
are constant in normalized space, not constant in output pixels. At an exact
analytic boundary, the specified inclusion rule determines occupancy: a nominal
odd-width centered bar need not contain that exact integer number of pixels on
an even grid. This is part of the sampling sensitivity, not a changed physical width.

Straight bars have length 0.5. The annulus has centerline radius 0.2. Junctions
are unions of three round-ended rays of length 0.22. Junction widths increase
at the node, so the nominal arm width is **not** asserted to equal the true
whole-junction mean thickness.

For each of the 48 geometry/width/offset combinations, calculate the relative
P10 change from 1024 to 2048. The largest value is the empirical discretization
envelope. The effective limit is the smaller of this envelope and 10%; if the
envelope exceeds 10%, **calibration itself fails**. Missing or undefined control
measurements also fail. A floating-point comparison allowance of $10^{-12}$
does not represent a scientific tolerance adjustment.

The native 1024 P10 range must also lie within the control P10 range. This is a
range-coverage check, not proof that the analytic suite exhausts all network
morphologies. The envelope is neither a statistical confidence interval nor
a universal error bound.

### Sampling-versus-generation control

Each of the ten new 2048 masks is held fixed and sampled on endpoint-aligned
256/512/1024 grids. Frozen local-dimension measurements are repeated without
re-running the generator at those lower grids. These are **measurement-only
controls**, never accepted native outputs or analytic continuum truth.

The report compares the native 1024→2048 mean-thickness increment with the
fixed-geometry sampling increment. A residual no larger than half the native
increment is classified as a dominant sampling pattern for that case. This
predefined descriptive test is not an empirical bias correction and is not
substituted for the actual convergence gate. P10 and pore values from the
sampling controls are retained in the machine-readable results as well.

## Repaired-neck inspection

All repairs encountered in the previous 30 cases and the new ten cases are
examined. Original pre-repair arrays are replayed with the unchanged native
renderer and checked against their recorded hashes.

The inspection deletes each solid pixel in the connector's bounding
neighborhood, **one at a time in an in-memory copy**, and checks finite-domain
4-connectivity. The saved masks are never edited. A pixel whose removal splits
the network is recorded as a local articulation.

For the top/bottom boundary connectors, the study additionally measures the
contiguous inward solid depth in each intervening gap column. It does not use
twice a boundary EDT as a substitute for the actual occupied neck width:
boundary clipping can leave approximately half of the nominal capsule diameter.
Unsupported connector orientations are explicitly unqualified rather than
automatically marked safe.

The local depth screen is tied to the existing capsule radius, $1/255$, not a
new manufacturing specification. **No mechanical/manufacturing approval is
possible from these pixels alone.** Physical domain size, minimum printable or
machinable feature size, material, loads, and mesh size remain unspecified.

## Output reference

Default study location: `experiments/pipeline_v0.4.2/thickness_verification/`.

| File/folder | Meaning |
|---|---|
| `protocol.json` | Prospective criteria, selected cases, source/evaluator hashes and historical inventories |
| `analytic_controls.json` | Mean/P10/pore measurements for all 192 analytic masks |
| `analytic/` | Native-resolution PNGs of the analytic controls |
| `ANALYTIC_CONTROLS.md` | Control measurements and calibrated P10 limit |
| `p10_calibration.json` | The 48 high-resolution control changes, envelope, ceiling and qualification result |
| `native_2048/design_*_seed_*/` | Ten new native PNG/NPY outputs, metrics, repeatability checks, repair audits and timings |
| `logs/` | Per-worker command, stdout/stderr, elapsed time and timeout information |
| `manifest.json` | Execution progress; source and history preservation results |
| `successive_changes.json` | All three successive steps for each fully completed matched quadruplet |
| `fixed_geometry_controls.json` | Sampling-only thickness and pore measurements at all four grids |
| `repair_inspection.json` | Connector articulation tests and actual boundary cross-section depths |
| `repair_inspection/*/repair.png` | Native-pixel raw/repaired/added-pixel comparison |
| `thickness_convergence.png` | Four-resolution mean and P10 trajectories |
| `summary.json` | Final gate-by-gate decision; failed cases remain visible |
| `SCIENTIFIC_ACCEPTANCE.md` | Main human-readable scientific report |

## Windows / PowerShell reproduction

Run from the repository root. Use the existing Windows virtual environment;
do not copy the macOS environment.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest
```

First register the protocol and run the analytic controls in a **new** directory:

```powershell
python -m metamaterial_eval.pipeline.thickness_verification prepare `
  --previous-run "experiments\pipeline_v0.4.1\resolution_validation" `
  --v04-run "experiments\pipeline_v0.4\resolution_validation" `
  --output-dir "experiments\pipeline_v0.4.2\thickness_verification_windows"
```

Then execute the ten native diagnostics and produce the scientific report:

```powershell
python -m metamaterial_eval.pipeline.thickness_verification run `
  "experiments\pipeline_v0.4.2\thickness_verification_windows" `
  --timeout 600
```

The code and calibration are hash-checked between stages. Editing them requires
a fresh study directory. Re-running `run` in a started directory is refused;
retain interrupted evidence and prepare a new directory. A native failure or
timeout is recorded rather than excluded. Exit code **3** denotes scientific
HOLD, not necessarily a crashed worker. Inspect the report and individual logs.

The old single-sample command continues to specify `--generator-version 0.4.1`.
There is intentionally **no generator v0.4.2**.

Optionally reproduce the post-hoc endpoint explanation in a separate new folder:

```powershell
python -m metamaterial_eval.pipeline.thickness_control_audit `
  --output-dir "experiments\pipeline_v0.4.2\endpoint_audit_windows"
```

Run the full software and frozen-evaluator test suites:

```powershell
$env:EVALUATOR_PATH = "validation\evaluators\evaluator_v1_1.py"
python -m pytest tests validation\test_evaluator.py -q
Remove-Item Env:EVALUATOR_PATH
```

These commands are written for Windows. The present execution took place on
macOS and does not establish Windows runtime equivalence. Per-job package
versions and hashes support later comparison.

## Decision boundary after this milestone

A resolution-stage PASS would support selecting one 1024 sample for a **separate**
v0.5 boundary extraction, topology-preserving polygon construction, simplification,
and rasterize-back study. It does not establish CAD validity or authorize automatic
extrusion/exports. A HOLD must identify the remaining failed criteria without
retuning the generator or relaxing thresholds merely to obtain a PASS.
