# v0.4 implementation and validation handoff

## Status

Native rendering, backward compatibility, the validation workflow and reporting
are implemented. **The scientific resolution-independence milestone has NOT met
all acceptance targets. Do not advance to v0.5 based on this run.**

Five existing LHS designs (0, 1, 2, 5, 9), seeds 0 and 1, were requested at
256/512/1024. Twenty-eight outputs passed the strict topology contract. Design 9,
seed 1 was rejected at 512 and 1024; it was not repaired or replaced with another
random realization. All ten baseline outputs equal both the preserved v0.3
generator and the saved Windows arrays bit-for-bit. Historical file inventory
and the frozen evaluator hash were unchanged.

## Observations and blockers

Among the nine fully available 256→1024 pairs:

| Quantity | Observed range | Provisional criterion | Interpretation |
|---|---:|---:|---|
| Absolute solid-fraction difference | 0.000000954–0.000006676 | <=0.005 | Passed |
| Relative normalized mean thickness difference | 8.29–10.21% | <=5% | Failed |
| Relative normalized P10 difference | 0–27.48% | <=10% | Only 3 of 9 passed |
| Relative normalized median pore difference | 0.18–6.97% | <=5% | 7 of 9 passed |
| S2 NRMSE | 0.00707–0.01184 | <=0.05 | Passed |
| Lineal-path NRMSE | 0.02345–0.03934 | <=0.05 | Passed |

The complete planned-pair denominator is ten; the missing/rejected pair does not
count as a pass. The main report correctly uses that denominator.

512→1024 shows tighter agreement: maximum mean-width drift 3.67%, pore drift
2.17%, S2 NRMSE 0.00319, lineal NRMSE 0.00818. Maximum P10 drift remains 11.80%.
Thus finer-grid convergence is observable, but that does not erase disagreement
with the preserved 256 baseline.

Native montage crops visually show finer boundaries, not enlarged 256 pixel
blocks. Underlying nuclei, random coefficients and accepted candidate are shared.
The retained 256 continuous latent-field bandwidth is deliberate.

### Rejected corner evidence

`failure_diagnostics.json` records replay measurements of the two rejected native
candidates. Their `rejected_evidence/REJECTED.npy` and `.png` files are diagnostic
only, not accepted generator outputs. At 512 the detached corner contains 25
pixels; at 1024 it contains 91. It lies at the top-left boundary. The 256 raster
connects this corner, but the native continuation does not. A coarse pixel bridge
is not necessarily a connected region in the inferred continuous geometry.

An earlier endpoint-sampling issue was fixed by retaining the original [0,255]
sampled coordinate endpoints; that corrected design 0 / seed 1 without adding
material. It did not solve design 9 / seed 1. The remaining case was preserved
as a blocker instead of introducing bridges or deleting islands.

### Parameter trends

On the selected complete design groups, density Spearman association is 1.0 at
all N; pore association is 1.0. Strut association is weak: 0.2 at 256 and 0.4 at
higher N. **Those higher-N figures use only four fully successful design groups,
versus five at 256**, so they cannot by themselves establish improved control.
The full original ten-design strut association was only 0.32121. This milestone
does not recalibrate that coupled relationship.

The report also compares **the identical complete cohort (designs 0, 1, 2, 5)**
at every resolution. Its density/strut/pore rank associations are **1.0 / 0.4 /
1.0 at all three resolutions**. Parameter ordering is preserved in this small
matched subset, including the already weak strut association. This is not proof
of independent causal control or of generalization outside these designs.

### Runtime and memory

| N | Mean generation seconds | Mean evaluation seconds | Mean traced generation peak |
|---|---:|---:|---:|
| 256 | 0.0655 | 0.1672 | 10.59 MiB |
| 512 | 0.2319 | 0.2584 | 43.74 MiB |
| 1024 | 0.6385 | 0.7978 | 171.24 MiB |

These means include successful jobs only (10/9/9). Generation includes cold
baseline selection and allocation tracing; it excludes process startup and
repeatability checks. Memory is traced allocations, not full RSS. Approximate
quadratic raster storage is observed. The frozen lineal loop grows with both
pixel count and radius; it was not rewritten. Pore-wise EDT summaries also scan
the image repeatedly. No O(N^4) pixel-pair distance matrix was introduced.

## Remaining scientific work

1. Resolve the top-left continuous-boundary ambiguity while preserving the
   accepted 256 morphology; do not silently repair or substitute a realization.
2. Separate skeleton/EDT quantization bias from native interface-continuation
   effects before accepting or revising normalized thickness tolerances.
3. Repeat matched validation after any justified change. Retain this report
   and use a new experiment directory.

No CAD, vectorization, FEM or image-AI work was performed.

## Source files introduced in this milestone

- `metamaterial_eval/generators/__init__.py`
- `metamaterial_eval/generators/v03_baseline.py` — exact preserved baseline bytes.
- `metamaterial_eval/generators/native_resolution.py` — native geometric rendering.
- `metamaterial_eval/pipeline/resolution.py` — scaling, radii and diagnostic reduction.
- `metamaterial_eval/pipeline/resolution_worker.py` — per-render profiling/evaluation.
- `metamaterial_eval/pipeline/resolution_validation.py` — matched-design experiment.
- `metamaterial_eval/pipeline/resolution_report.py` — convergence tables and figures.
- `tests/test_pipeline_resolution.py`
- `docs/PIPELINE_V0_4_AUDIT.md`
- `docs/PIPELINE_V0_4_RESOLUTION.md`

Existing files modified: `metamaterial_eval/pipeline/cli.py` and `README.md`.
Earlier uncommitted v0.3 implementation work was preserved. No completed v0.3
experiment files or frozen evaluator definitions were modified.

All experiment artifacts are listed in `artifact_inventory.txt` alongside this
document. The command guide is `docs/PIPELINE_V0_4_RESOLUTION.md`.
