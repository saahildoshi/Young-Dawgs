# Pipeline v0.4 — Resolution Independence

## Goal and scope

Render the audited v0.3 cellular morphology natively at higher resolution while
preserving its design controls and stochastic realization. This is **not** a new
morphology optimizer. The completed v0.3 experiment, replication workflow,
exploration plan, and frozen evaluator remain unchanged.

The port is specific to `experiments/pipeline_v0.3/exploration_test_01/generator.py`,
SHA-256 `61304070aad94b8eb4595c65ce61dc9cab35fe14caada60bc4526fb0175f3839`.
An unrelated generator cannot be converted merely by setting a resolution flag.

## Supported resolutions

Validation levels: **256, 512, 1024**. Integer square sizes from 256 to 4096 are
accepted; values beyond the validation levels require their own convergence and
resource checks. Booleans, fractional resolutions, nonpositive and tiny sizes
are rejected rather than silently rounded. The upper limit is a resource guard,
not an assertion that every 4096 design is feasible.

## What resolution means

The physical domain is fixed. Increasing N increases sampling density, not the
number of nuclei, random coefficients or intended pores. No completed 256 mask
is resized into the native output. Nuclei and deformed coordinates are evaluated
on an N×N grid, followed by native label transitions, native EDT and a native
density quantile.

All returned arrays remain uint8 with only 0/1; 1 is solid. Native PNGs contain
black/white pixels. Matplotlib may scale their *display* in figures; those figures
are not canonical generator outputs.

## Interface and Windows commands

The original four-argument call still defaults to 256:

```python
from metamaterial_eval.generators.native_resolution import generate_microstructure

image = generate_microstructure(
    seed=0,
    solid_fraction_target=0.47949869779450194,
    strut_scale=3.8117182167728196,
    pore_scale=8.405665555093796,
    resolution=1024,
)
```

`generate_microstructure_at_resolution` is an alias. No manual multiplication
of strut/pore controls is needed. These are the actual baseline-pixel calibrated
scales, not newly reinterpreted multipliers such as “1 means reference-like.”

From the repository root in PowerShell with the environment activated:

```powershell
python -m pip install -e .
python -m metamaterial_eval.pipeline resolution-generate `
  --seed 0 --solid-fraction-target 0.47949869779450194 `
  --strut-scale 3.8117182167728196 --pore-scale 8.405665555093796 `
  --resolution 1024 `
  --output-dir "experiments\pipeline_v0.4\single_native_1024"
```

This produces the native PNG/NPY, evaluator metrics, normalized descriptors,
hashes and timing. Existing output directories are never overwritten.

Run the full matched validation (five existing designs × both saved seeds ×
three resolutions = 30 outputs):

```powershell
python -m metamaterial_eval.pipeline resolution-validate `
  "experiments\pipeline_v0.3\exploration_test_01" `
  --output-dir "experiments\pipeline_v0.4\resolution_validation_windows" `
  --resolutions 256 512 1024 --designs 5 --timeout 600
```

Use a fresh output directory for each execution. Per-job failures and timeouts
are recorded and the next resolution is still attempted. The first release
does not resume an interrupted validation; prior files remain available and a
new full run must use a new directory. Execution `COMPLETE` is not proof that
convergence gates passed—read the scientific report.

The run selection uses existing LHS points nearest the envelope center, minimum/
maximum density and opposite strut/pore corners. It does not sample new bounds.
`--designs 10` reuses all original points for a larger control-trend assessment.

## Scaling rules and same-seed behavior

- Linear pixel quantities scale with N/256.
- Area/pixel counts representing material scale with (N/256)².
- Nuclei counts, latent random grid sizes and harmonic orders stay fixed.
- Density, mixture weights, exponents, repulsion iterations and rejection budget
  remain unchanged.

Geometry uses **baseline-pixel coordinates**, mathematically equivalent to
normalized coordinates divided by 256. The requested raster samples those
coordinates at spacing 256/N. This retains the old arithmetic and makes exact
256 regression practical. See [the audit](PIPELINE_V0_4_AUDIT.md) for every
generator constant category and the orchestration assumptions.

The original v0.3 rejection process selects the accepted candidate and its RNG
state on the baseline grid. Every N then uses that same state, nuclei and random
coefficients. The native output is **not** the resized baseline selection mask.
The retained v0.3 family gate exists only to preserve candidate identity; the
frozen evaluator independently measures all final native outputs.

Continuous random fields use v0.3's smoothed 256-grid latent representation,
interpolated onto the native grid. This is permitted internal field interpolation,
not binary-mask upscaling. It deliberately retains the original random bandwidth.
Higher N does not add smaller random pores or new high-frequency noise.

The native cellular transition initially occupies two native pixels. Its EDT
buffer restores the approximate physical width of v0.3's two-baseline-pixel
interface. The exact lattice footprint is not perfectly resolution invariant;
it is a documented approximation to a raster-defined baseline model.

If the matched native realization is disconnected or fails either spanning
direction, generation fails with an explicit record. It does not change seed,
choose a different high-resolution realization, remove islands or insert bridges.

## Evaluation and validation

The accepted evaluator v1.1 file is byte-unchanged. Its array functions measure
variable shapes directly; the historical CLI's fixed 256 contract is untouched.
v0.4 sets max_r to ceil(N/4), computes all native integer radii, and interpolates
curves onto the common grid rho = 0, 1/256, …, 64/256. The three required
resolutions have exact matching radii; arbitrary N may need interpolation.
The radius utility reports nearest native radii and rounding errors separately.

Mean thickness, P10 thickness and median enclosed-pore diameter are reported both
in raw pixels and divided by N. Density is already dimensionless. Curve NRMSE
uses the **lower-resolution curve as denominator**, with the frozen evaluator's
RMSE/RMS definition. All three pairings (256–512, 256–1024, 512–1024) are saved.

Secondary same-seed correspondence uses block-area averaging to 256, then
majority threshold >=0.5. IoU and pixel disagreement supplement the evaluator's
SSIM/NCC. This diagnostic does not affect generation or acceptance. It is not
available for noninteger multiples of 256. Common-grid ensemble diversity also
uses the frozen evaluator's pairwise disagreement function.

Provisional engineering targets for 256–1024:

| Quantity | Target |
|---|---:|
| Topology | One component, horizontal and vertical percolation |
| Absolute solid-fraction change | <=0.005 |
| Relative normalized mean thickness change | <=5% |
| Relative normalized pore diameter change | <=5% |
| Relative normalized P10 thickness change | <=10% |
| S2 NRMSE | <=0.05 |
| Lineal-path NRMSE | <=0.05 |

Failures remain failures; morphology is not recalibrated to manufacture a pass.
Control plots and rank correlations use matched design means, not requested
values masquerading as measured values. Controls are coupled in the original
model, so rank correlations are not isolated causal sensitivity estimates.

## Files and provenance

```
experiments/pipeline_v0.4/<validation_run>/
    manifest.json
    selected_designs.json
    jobs/
    logs/
    design_NNN/seed_NNN/256|512|1024/
        microstructure.npy
        microstructure.png
        manifest.json
        timing.json
        evaluation/metrics.json
    summary/
        resolution_convergence.json
        resolution_convergence.csv
        resolution_convergence.md
        figures/
```

Per-output manifests contain controls, seed, resolution, scale, generator/source/
evaluator hashes, raw and normalized metrics, curve data, exact repeatability,
baseline regression, timing, output hashes/sizes and environment versions.
The top manifest fingerprints every source-experiment file before/after.
Relative output directories are used; historical source paths are provenance
on the computer that executed the validation, not portable commands.

Figures include equal-display-size same-seed montages, native central-quarter
crops, normalized width/pore/density/P10 plots, per-seed S2/L overlays, parameter
control comparisons and runtime/memory scaling. Plot colors use defaults.

Generation timing includes cold baseline candidate selection and tracemalloc
instrumentation, but excludes process startup, file saving and the repeated
determinism check. Evaluation timing is separate. Memory is peak **traced
allocations during generation**, not complete RSS or peak evaluation memory.
The generator uses nearest-neighbor trees rather than pixel-pair distance arrays.
The existing lineal evaluator's growing radius loop is the expected high-N
hotspot; no validated formulas were rewritten for speed.

## Limitations and next-stage boundary

A 256 raster-defined baseline has no uniquely specified continuous boundary.
Native rendering preserves nuclei and fields but cannot remove the discrete
EDT/skeleton bias from the historical metrics. Narrow-feature P10 estimates are
particularly sensitive. Quantization and interface continuation can therefore
miss provisional convergence targets even with excellent density/correspondence.
Report those discrepancies rather than silently changing parameter meanings.

No CAD, vectorization, contour extraction, STEP, STL, SVG/DXF, 3D extrusion,
meshing, FEM, ANSYS or manufacturing functionality is included. No AI upscaler,
Canva or neural super-resolution is used. A high-resolution file alone does not
establish readiness for v0.5; the report explicitly distinguishes execution
success from scientific convergence and readiness.

## Tests

```powershell
python -m pytest tests -q
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest validation/test_evaluator.py -q
Remove-Item Env:EVALUATOR_PATH
```

Regression fixtures are three real saved v0.3 design/seed arrays, represented by
their exact pixel SHA-256 values, plus live equality to the preserved generator.
The full validation expands that check to all selected design/seed pairs.
