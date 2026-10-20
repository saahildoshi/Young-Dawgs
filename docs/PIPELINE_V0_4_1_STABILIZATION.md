# Pipeline v0.4.1 — resolution-convergence stabilization

## Decision

**Topology corrected; finite-resolution dimensional convergence demonstrated;
scientific acceptance remains HOLD. Do not advance to v0.5/CAD.**

The investigation is complete, but successful execution and software tests are
not equivalent to passing the scientific protocol. No width parameters, density
quantiles, nuclei, random fields, or evaluator definitions were tuned to obtain
a passing result. The original v0.4 evidence remains intact.

## Results at a glance

| Check | Original v0.4 | v0.4.1 |
|---|---:|---:|
| Single component and both percolation directions | 28/30 | **30/30** |
| 256 bitwise equality to saved v0.3 and original generator | 10/10 | **10/10** |
| Raw realization identical to v0.4, including rejected arrays | — | **30/30** |
| Final arrays identical to accepted v0.4 outputs | — | **28/28** |
| Deterministic repeat / distinct samples at each N | preserved | 30/30 repeats; 10 distinct at each N |
| Maximum absolute solid-fraction change, 256→1024 | $6.68\times10^{-6}$ | $7.63\times10^{-6}$ |
| Maximum $S_2$ NRMSE, 256→1024 | 0.01184 | 0.01184 |
| Maximum lineal-path NRMSE, 256→1024 | 0.03934 | 0.03934 |
| Mean thickness, 512→1024, ≤3% | 5/9 successful pairs | **5/10: HOLD** |
| P10 thickness, 512→1024, ≤10% | 6/9 successful pairs | **7/10: HOLD** |
| Pore median, 512→1024, ≤3% | 9/9 successful pairs | **10/10** |

The old table uses only the nine complete triplets where appropriate. The new
table includes all ten. No rejected case is silently removed from acceptance.

## Thickness and pore root cause

All dimensional measurements use the **unchanged frozen evaluator v1.1**:
$t=2\,\mathrm{EDT}$ on the solid pixel skeleton; one maximal-inscribed diameter
per enclosed 4-connected void component. Normalization is $t/N$ and $d_p/N$.

For the nine originally successful triplets:

| Metric | 256→512 absolute relative change | 512→1024 absolute relative change |
|---|---:|---:|
| Mean thickness | 5.61–6.99% | 2.69–3.67% |
| Pore median | 0–6.97% | 0–2.17% |

Mean thickness decreases with increasing N. Pore changes can have either sign.
All individual signed values, including P10, are in `diagnostics/DIAGNOSTICS.md`.

### Fixed analytic geometries

Twenty-four controls independently sample 4- and 6-baseline-pixel-wide bars
(horizontal, vertical, 45°) and annuli at 256, 512, and 1024. There is no final
binary interpolation. Bars have normalized length 0.5. Annuli have centerline
radius 0.2 and normalized wall width $w/256$.

- Axis-aligned bars: normalized mean thickness changes by less than 0.4%
  overall. Endpoint skeletonization contributes small differences.
- A 6-pixel-wide 45° bar: normalized mean thickness changes from 0.028099 to
  0.023515, despite unchanged analytic width $6/256=0.0234375$ (about 16.31%).
- The 4-pixel ring changes from 0.016333 to 0.015533 (about 4.90%).
- Ring pore medians also drift with sampling; open bar voids correctly return
  no enclosed-pore measurement rather than a fabricated zero.

Thus stable axis-aligned bars do **not** establish an unbiased estimator for
curved or oblique networks. The 45° width-4 case also shows that a small
successive increment alone need not imply small error relative to analytic truth.

### Three native 2048 diagnostics

Selected before observing the 2048 results: Design 1/seed 0 (largest previous
successive mean-thickness change), Design 2/seed 0 (high density), and Design
5/seed 0 (envelope center). All three retain the unmodified v0.4 generator.

| Design / seed | Mean: 512→1024 | Mean: 1024→2048 | Pore: 512→1024 | Pore: 1024→2048 |
|---|---:|---:|---:|---:|
| 1 / 0 | −3.6710% | −1.8670% | +0.9570% | +0.1179% |
| 2 / 0 | −2.9876% | −1.7594% | −0.9419% | −0.2391% |
| 5 / 0 | −2.6853% | −1.5292% | −1.5202% | +0.2774% |

2048 generation took 2.35–2.46 s and evaluation 4.57–4.79 s locally. Peak
traced generation allocation was about 681 MiB, **not total process RSS**.
This limited sample is diagnostic only; 2048 is not a new production standard.

### Stronger attribution: fixed-2048-geometry sampling control

The same three completed 2048 masks were held fixed, then sampled on lower
endpoint-aligned grids. These are explicitly labeled **CONTROL_ONLY_NOT_NATIVE**;
they are never accepted production outputs. No generator operation occurs
between these measurements.

| Design / seed | Native mean change 512→1024 | Fixed-geometry mean change 512→1024 |
|---|---:|---:|
| 1 / 0 | −3.6710% | −3.6997% |
| 2 / 0 | −2.9876% | −3.4226% |
| 5 / 0 | −2.6853% | −2.8903% |

These controls reproduce the dominant thickness trend without changing the
generator geometry. **Sampling/skeleton/EDT effects are the dominant explanation
in these three tested cases.** This is not proof of zero generator discretization
error: the renderer still uses native lattice interfaces and an EDT-based score,
and a fixed 2048 raster is not exact continuum truth. No empirical bias correction
is applied to reported metrics.

## Topology root cause and minimal correction

Design 9/seed 1 has a one-row neck on the **top boundary** at 256. Removing
any one of pixels $(y,x)=(0,2),(0,3),(0,4)$ in a diagnostic copy separates the
corner. At 512 there is one void pixel between the nearest solid endpoints;
at 1024 there are two. This identifies a coarse-grid aliasing connection at a
clipped boundary, not evidence requiring a global change to nuclei or widths.
The claim concerns these sampled rasters; no analytic continuum boundary was
available to prove an exact continuum gap.

| N | Detached pixels | Area / $N^2$ | Inclusive bounding box $(y,x)$ | Nearest solid pixel centers | Center distance / $(N-1)$ |
|---:|---:|---:|---|---|---:|
| 512 | 25 | 0.000095367 | (0,0) to (6,4) | (0,4) to (0,6): 2 px | 0.003913894 |
| 1024 | 91 | 0.000086784 | (0,0) to (12,9) | (0,9) to (0,12): 3 px | 0.002932551 |

The new `stabilized_resolution.py` wraps the preserved `native_resolution.py`:

1. Select the same accepted v0.3 latent realization.
2. Render with the unchanged v0.4 renderer (or return the exact 256 baseline).
3. If disconnected, join the closest fragment to the largest component using
   a native-grid Euclidean capsule. Repeat deterministically if needed.
4. Check exact 4-connectivity and both percolation directions.

The capsule width is **2/255 of the endpoint-defined domain**, preserving the
original two-sided interface scale. Maximum centerline length is **4/255**.
Added area is bounded by **0.001 of domain area**. Larger repairs fail explicitly.
These are conservative geometry limits, not guarantees for arbitrary designs.
There is no forced perimeter, removal of islands, re-seeding, or density erosion.

Actual repairs: **4 pixels at 512**, **15 at 1024**, respectively
$1.526\times10^{-5}$ and $1.431\times10^{-5}$ of total area. These additions
are far below the unchanged 0.005 density tolerance, so no density readjustment
was justified. Already connected outputs are bitwise unchanged. Width is
specified in normalized space; lattice boundary clipping still introduces
ordinary finite-resolution differences in capsule area.

## Protocol amendment and remaining HOLD

`resolution_validation/protocol_amendment.json` was written **before** the
post-fix 30-case rerun. The original 256→1024 errors remain reported; they
were not rewritten as passes.

The amendment replaces coarse-reference dimensional gates with:

- Mean thickness: absolute relative change ≤3% at 512→1024.
- P10 thickness: ≤10% at 512→1024; its original tolerance is retained.
- Median pore diameter: ≤3% at 512→1024.
- Mean and pore changes at 1024→2048 must be smaller than their preceding
  increments in all three preselected diagnostics.
- Original density and $S_2/L$ limits, all 30 topology checks, baseline identity,
  stochastic identity and unchanged historical inventories remain mandatory.

Mean-thickness failures: **D1/S0, D1/S1, D2/S1, D9/S0, D9/S1**.
P10 failures: **D0/S0, D0/S1, D2/S0**, each 11.8034% versus the 10% limit.
These failures are not waived because estimator quantization is present.

The full five-design cohort now gives rank associations **1.0 / 0.2 / 1.0**
for density / strut scale / pore scale at every resolution. The earlier 0.4
strut association used only four fully successful designs. This cohort change
is not degraded strut control caused by the repair. Identifiability remains a
separate future study.

Before scientific acceptance, the unresolved question is whether a justified
resolution/measurement protocol should accommodate the demonstrated quantization,
or require further high-resolution validation. Do not change these thresholds
merely because the present run fails them. No further geometry tuning is supported
by this investigation.

## Files and output organization

All experiment paths below are relative to `experiments/pipeline_v0.4.1/`.

| File/folder | Purpose |
|---|---|
| `diagnostics/DIAGNOSTICS.md` | Nine-pair stepwise results, 24 analytic controls, three 2048 cases, fragment geometry |
| `diagnostics/topology_overlay.png` | Common-coordinate view of the 256/512/1024 corner |
| `diagnostics/topology/<N>/main.npy`, `detached.npy` | Isolated original components, not repaired outputs |
| `diagnostics/synthetic/` | Independently sampled analytic masks and frozen measurements |
| `diagnostics/diagnostic_2048/` | Three native 2048 masks, frozen metrics, timing and provenance |
| `fixed_geometry_control/FIXED_GEOMETRY.md` | Sampling-only control; masks explicitly excluded from production |
| `coarse_neck_diagnostic.json` | Single-pixel graph-sensitivity evidence at the original top boundary |
| `resolution_validation/VALIDATION.md` | Full post-fix acceptance results and all signed dimensional changes |
| `resolution_validation/summary.json` | Machine-readable original/amended gates and full native measurements |
| `resolution_validation/protocol_amendment.json` | Prospective post-diagnostic acceptance protocol |
| `resolution_validation/manifest.json` | All jobs, hashes, source inventories and preservation check |
| `resolution_validation/design_*/seed_*/<N>/` | Accepted native PNG/NPY, repair audit, metrics and timings |
| `resolution_validation/figures/` | Native montages/crops, curves, normalized dimensions, controls, runtime |

Code: `generators/stabilized_resolution.py` implements the repair;
`pipeline/stabilization.py` runs diagnostics and validation;
`pipeline/resolution_worker.py` profiles/evaluates each isolated job;
`tests/test_pipeline_stabilization.py` tests the new contracts.
Frozen evaluator v1.1 and the v0.3/v0.4 renderers are unchanged.

Software verification: **177 tests passed** (121 package tests, including 21 new
stabilization tests, plus 56 frozen-evaluator tests). Durable output is saved in
`experiments/pipeline_v0.4.1/verification/tests/stdout.txt`; source-inventory
and evaluator-hash checks are in `verification/verification.json`.

## Windows / PowerShell commands

Run from the repository root with your Windows environment activated. Do not
copy a macOS virtual environment to Windows. These results were executed on
macOS; the commands are Windows-compatible but a Windows execution has not
been claimed.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pytest
```

Reproduce the investigation in **new** output folders:

```powershell
python -m metamaterial_eval.pipeline.stabilization investigate `
  --baseline "experiments\pipeline_v0.4\resolution_validation" `
  --source-run "experiments\pipeline_v0.3\exploration_test_01" `
  --output-dir "experiments\pipeline_v0.4.1\diagnostics_windows" `
  --timeout 600

python -m metamaterial_eval.pipeline.stabilization fixed-geometry `
  --diagnostics "experiments\pipeline_v0.4.1\diagnostics_windows" `
  --output-dir "experiments\pipeline_v0.4.1\fixed_geometry_windows"

python -m metamaterial_eval.pipeline.stabilization validate `
  --baseline "experiments\pipeline_v0.4\resolution_validation" `
  --source-run "experiments\pipeline_v0.3\exploration_test_01" `
  --diagnostics "experiments\pipeline_v0.4.1\diagnostics_windows" `
  --output-dir "experiments\pipeline_v0.4.1\validation_windows" `
  --timeout 600
```

Each command refuses to reuse an output directory. There is no resume support
for this diagnostic workflow: retain an interrupted directory and use a new name.
An execution timeout is recorded as failure, not skipped. Exit code **3** means
the validation executed but scientific acceptance is **HOLD**. It is not the
old empty-response/script-extraction error. Read `VALIDATION.md` and `summary.json`.

Generate a single stabilized native sample (opt-in; the old CLI default remains v0.4):

```powershell
python -m metamaterial_eval.pipeline resolution-generate `
  --generator-version 0.4.1 `
  --seed 1 --solid-fraction-target 0.47692251183925727 `
  --strut-scale 4.340345305340277 --pore-scale 6.148748802851207 `
  --resolution 1024 `
  --output-dir "experiments\pipeline_v0.4.1\single_sample_windows"
```

Programmatic use:

```python
from metamaterial_eval.generators.stabilized_resolution import generate_with_metadata

binary, repair = generate_with_metadata(
    seed=1, solid_fraction_target=0.47692251183925727,
    strut_scale=4.340345305340277, pore_scale=6.148748802851207,
    resolution=1024,
)
print(repair)  # Never conceal whether a connector was added.
```

Run package tests and explicitly select frozen **v1.1**, because the historical
evaluator test harness defaults to v1.0:

```powershell
$env:EVALUATOR_PATH = "validation\evaluators\evaluator_v1_1.py"
python -m pytest tests validation\test_evaluator.py -q
Remove-Item Env:EVALUATOR_PATH
```

The frozen SHA-256 is
`5f28ed1f77f95fd23a517cd223bbe6c6b5edc7d5508093f36f523b2d4f85cebb`.
Future library versions may alter skeleton tie handling; compare the saved
environment metadata, golden arrays and the frozen tests before comparing runs.
