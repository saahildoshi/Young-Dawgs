# v0.4 pre-implementation audit and plan

The audit and plan were completed in the task conversation before file edits.
This document records that decision and constant classification for maintenance.

## Repository baseline

- `metamaterial_eval/`: reusable finite-domain metrics and image preparation.
- `metamaterial_eval/pipeline/`: v0.1/v0.2 replication, v0.3 exploration;
  manual response extraction, immutable hashes, subprocess execution and reports.
- `experiments/Pilot_v1.1`, `pilot_voronoi`, `pipeline_v0.1`, `pipeline_v0.2`:
  historical studies, not targets for modification.
- `experiments/pipeline_v0.3/exploration_test_01`: completed current baseline.
- `validation/evaluators/evaluator_v1_1.py`: frozen source of scientific metrics.
- `tests/`: package, replication, topology, preprocessing and exploration tests.
- `pyproject.toml`: Python >=3.10; scientific package dependencies, editable install.
- `.github/workflows/windows-pipeline.yml`: package + frozen tests on Windows.
- `docs/`: versioned guides, metric conventions and project reference.

Current generator SHA-256:
`61304070aad94b8eb4595c65ce61dc9cab35fe14caada60bc4526fb0175f3839`.
It exposes `generate_microstructure(seed, solid_fraction_target, strut_scale, pore_scale)`.
Saved run: 20/20 unique, single-component spanning structures; 19/20 envelope
passes. Across all ten original LHS designs, density/strut/pore rank associations
were 1.0 / 0.32121 / 0.85317. A weak strut association is baseline behavior,
not permission to change the model in a resolution-only milestone.

The saved LHS plan contains 10 designs × 2 paired seeds (0 and 1), generated with
design seed 42. Bounds are preserved exactly from its `design_plan.json`.
White/1 is solid. Connectivity is finite-domain four-neighbor connectivity.
The saved runtime is Windows Python 3.14.6, NumPy 2.5.1, SciPy 1.18.0,
scikit-image 0.26.0; local verification records its different environment.

## Resolution assumptions and classification

| Quantity in generator | Class | v0.4 handling |
|---|---|---|
| Array shape / indices / 256 FFT dimensions | Grid sampling | Native N×N grid; evaluation radii scale with N |
| Pitch prefactor 13.25, scale anchors 7.21110255 and 4.11262391 | Baseline spatial calibration | Preserve controls and compute geometry in baseline units; raster coordinates use 256/N |
| Margin 2.5×pitch, exclusion 0.72×pitch, site positions and repulsive displacement | Linear spatial | Same physical positions in baseline units; pixel coordinates scale N/256 |
| Warp amplitude 1.7×(pitch/13)^0.75 | Linear spatial | Same baseline-unit deformation evaluated on requested native grid |
| Gaussian blur sigmas 1 and 2 | Linear spatial / latent field | Keep canonical continuous field, interpolate only that field; physical correlation lengths fixed |
| Random grids 20, 42, 15, 34 | Latent feature counts / spatial frequency | Fixed; do not consume additional random draws at higher N |
| Site count max(4, round(((256+2×margin)/pitch)^2)) | Physical feature count | Fixed; original domain 256 retained in this expression |
| Painted cellular transition on both neighboring pixels | Baseline spatial interface thickness | Native transition + EDT buffer of 1−256/N baseline units |
| EDT distances and radial distances | Linear spatial | Native EDT divided by N/256; radial distance remains in baseline units |
| Requested void pixel count (1−phi)×side² | Area | Uses N²; density quantile retains original definition |
| Spatial offsets in random locations, coordinate boundaries | Linear spatial | Baseline-coordinate physical domain preserved; native samples at i×256/N |
| Harmonic orders 2/3, weights .13/.055, size/width lognormal factors .18/.14/.08 | Dimensionless morphology | Unchanged |
| Pitch exponents .82/.44, density factor 1.2, reference phi .477340698 | Dimensionless morphology | Unchanged |
| Score weights .80/−.20, warp mixture .25, repulsion relaxation .28 | Dimensionless algorithm/model | Unchanged |
| Seven repulsion steps, 32 candidate attempts, min four nuclei | Algorithmic/topological counts | Unchanged |
| 1e−9 separation floor, 1e−12 normalization stabilizer | Numerical tolerances | Same baseline-coordinate/value units; unchanged |
| Internal family gates .25 and sampled radii 0,1,2,4,8,16,32,64 | Candidate selection | Original v0.3 gate chooses same candidate once on baseline; not recomputed to select a different high-N realization |
| Public scales, phi, random seed | Design controls | Unchanged at every N |

No branching steps, line-drawing API, skeleton generator, or iterative dilation/
erosion/closing/opening exists in this source. Skeletonization belongs to the
frozen measurement function, not generation. The new interface buffer is a
native distance-based continuation of the old two-sided raster wall, not
connectivity repair or final-image upsampling.

## Evaluator and orchestration

The frozen evaluator's `basic_metrics`, `local_dimensions`, `radial_bin_map`,
`s2_periodic` and `lineal_path_periodic_directional` accept arbitrary shape.
Its CLI target validation assumes 256; do not alter that historical CLI.
`PipelineConfig` already supports shape/max_r overrides. v0.3 worker/report and
prompt hard-code 256; they remain unchanged for backward compatibility.
v0.4 uses a separate worker with explicit shape and normalized-distance mapping.

Hotspots: nearest-neighbor query and continuous-field sampling are approximately
O(N²) for fixed site count; evaluator's all-radius lineal loop grows roughly
O(N³) as max_r grows with N. Pore-wise EDT maxima repeatedly scan arrays but
physical pore count is approximately fixed. There is no pairwise pixel-distance
matrix. Keep the validated definitions; profile before considering optimization.

## Implementation plan

1. Preserve exact baseline bytes in a versioned module; do not edit the experiment.
2. Separate accepted latent realization from native raster sampling. Retain
   original candidate selection and RNG state across resolutions.
3. Add centralized validation/scaling/radius conversion, not new design controls.
4. Add shape/seed/topology/baseline/no-resize/failure/manifest unit tests and run
   existing regressions plus frozen evaluator acceptance tests.
5. Select five existing LHS points by center, density extremes and opposed
   scale corners; use both saved seeds and all 256/512/1024 resolutions.
6. Preserve all source-file hashes before/after, record runtime/memory and all
   raw/normalized metrics; generate tables, native crops and convergence plots.
7. Report every missed engineering target without retuning morphology.
   Stop before vectorization/CAD/FEM.
