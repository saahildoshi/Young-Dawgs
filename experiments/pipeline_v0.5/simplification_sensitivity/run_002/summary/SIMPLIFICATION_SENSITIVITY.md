# v0.5B1 — Simplification sensitivity and feature-risk analysis

Scientific status: **EXPLORATORY STUDY EXECUTED; NOT FULL v0.5B ACCEPTANCE**. Regression and preservation verification are recorded separately. No production tolerance is selected.

## Objective and immutable sources

Measure complexity reduction and failure mechanisms using five saved accepted manifold candidates. Source geometries and exact baselines are separately hashed; no masks, generators or regularizations are regenerated.

## Methods

Douglas–Peucker, preserve_topology=True, independently from each saved baseline at ε=[0,0.05,0.10,0.20,0.35,0.50,0.75,1.00] native cells. Three D0 negative controls use False at [0.35,0.75,1.00]. Epsilon zero is an unchanged WKB clone. No automatic repair or feature protection.

A=manifold→simplified continuous error; B=exact→final cumulative error; C=canonical/baseline raster→reconstruction. All three are retained separately. Vertices exclude closure duplicates. Existing exact collinear reduction is not credited to this study.

Rasterization uses original half-integer centers and x-right/y-down coordinates. Frozen evaluator v1.1 uses the established native interface; cache reuse requires verified raster/evaluator/configuration identity. P10 qualification remains scoped and the historic v0.4.2 calibration remains failed.

Boundary distance uses indexed samples at ≤0.25-cell spacing, exact sample-to-segment distance, and a Lipschitz upper bound. Local spacing is ≤0.0625 cell. Bounds are not an exact continuous maximum. Validity and manifoldness are checked independently. Positive-area overlap tracks hole/solid/void correspondence, not just counts.

Fixed repair ROI half-width=r+0.75=1 cell. Per-contact retention, local separation, local links, displacement and geometry differences are recorded. Three deterministic low-EDT/PCA neck probes and the saved D9 boundary connector are monitored; this is not exhaustive neck screening or mechanics.

## Baseline complexity

| Fixture | Exposed vertices | Exact coalesced | Existing reduction % | Accepted vertices | Holes | Area | Repairs | GEOS clearance diagnostic |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| design_000_seed_000 | 67550 | 38830 | 42.517 | 38832 | 289 | 502791.0625 | 1 | 0.353553 |
| design_009_seed_001 | 81192 | 47382 | 41.642 | 47382 | 412 | 500104.0 | 0 | 1.000000 |
| design_001_seed_000 | 82352 | 47888 | 41.850 | 47900 | 404 | 453505.375 | 6 | 0.353553 |
| design_002_seed_000 | 80634 | 46528 | 42.297 | 46544 | 466 | 542961.5 | 8 | 0.353553 |
| design_005_seed_000 | 68820 | 39524 | 42.569 | 39542 | 321 | 528285.5625 | 9 | 0.353553 |

GEOS minimum_clearance is a robustness diagnostic, not a physical neck width. All baseline topology, shell/hole vertices, boundary lengths, source hashes, local probes and archived neck context are in fixtures/*/baseline.json.

## Per-tolerance primary results

### design_000_seed_000

| ε | Vertices | Reduction % | OGC | Manifold | Holes | Added / removed cell² | Symmetric cell² | Boundary measured / upper | Repair min clearance | Raster XOR |
|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0 | 38832 | 0.000 | True | True | 289 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.05 | 38832 | 0.000 | True | True | 289 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.1 | 38832 | 0.000 | True | True | 289 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.2 | 38831 | 0.003 | True | True | 289 | 0.093750 / 0.000000 | 0.093750 | 0.181902 / 0.306902 | 0.3535533905932738 | 0 |
| 0.35 | 38830 | 0.005 | True | True | 289 | 0.437500 / 0.000000 | 0.437500 | 0.228375 / 0.353375 | 0.48507125007266594 | 0 |
| 0.5 | 31190 | 19.680 | True | True | 289 | 1283.187500 / 1282.750000 | 2565.937500 | 0.499681 / 0.624681 | 0.48507125007266594 | 0 |
| 0.75 | 15191 | 60.880 | True | True | 289 | 4517.032554 / 4897.595054 | 9414.627608 | 1.245682 / 1.370682 | 0.48507125007266594 | 6116 |
| 1 | 5859 | 84.912 | True | True | 289 | 7805.471828 / 8474.034328 | 16279.506156 | 1.972788 / 2.097788 | N/A or undefined | 12912 |

### design_009_seed_001

| ε | Vertices | Reduction % | OGC | Manifold | Holes | Added / removed cell² | Symmetric cell² | Boundary measured / upper | Repair min clearance | Raster XOR |
|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0 | 47382 | 0.000 | True | True | 412 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | N/A or undefined | 0 |
| 0.05 | 47382 | 0.000 | True | True | 412 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | N/A or undefined | 0 |
| 0.1 | 47382 | 0.000 | True | True | 412 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | N/A or undefined | 0 |
| 0.2 | 47382 | 0.000 | True | True | 412 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | N/A or undefined | 0 |
| 0.35 | 47382 | 0.000 | True | True | 412 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | N/A or undefined | 0 |
| 0.5 | 37774 | 20.278 | True | True | 412 | 1611.000000 / 1611.000000 | 3222.000000 | 0.499376 / 0.624376 | N/A or undefined | 0 |
| 0.75 | 18292 | 61.395 | True | True | 412 | 5580.366334 / 6153.366334 | 11733.732669 | 0.749532 / 0.874532 | N/A or undefined | 7679 |
| 1 | 7415 | 84.351 | True | True | 412 | 8027.808694 / 10706.808694 | 18734.617388 | 1.373606 / 1.498606 | N/A or undefined | 14594 |

### design_001_seed_000

| ε | Vertices | Reduction % | OGC | Manifold | Holes | Added / removed cell² | Symmetric cell² | Boundary measured / upper | Repair min clearance | Raster XOR |
|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0 | 47900 | 0.000 | True | True | 404 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.05 | 47900 | 0.000 | True | True | 404 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.1 | 47900 | 0.000 | True | True | 404 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.2 | 47893 | 0.015 | True | True | 404 | 0.656250 / 0.000000 | 0.656250 | 0.181902 / 0.306902 | 0.3535533905932738 | 0 |
| 0.35 | 47888 | 0.025 | True | True | 404 | 2.000000 / 0.000000 | 2.000000 | 0.228375 / 0.353375 | 0.3535533905932738 | 0 |
| 0.5 | 38472 | 19.683 | True | True | 404 | 1600.250000 / 1598.250000 | 3198.500000 | 0.499567 / 0.624567 | 0.3535533905932738 | 0 |
| 0.75 | 18547 | 61.280 | True | True | 404 | 5561.178573 / 6227.303573 | 11788.482145 | 1.252078 / 1.377078 | 0.3535533905932738 | 7788 |
| 1 | 7352 | 84.651 | True | True | 404 | 9447.767531 / 10524.517531 | 19972.285062 | 1.987767 / 2.112767 | N/A or undefined | 15717 |

### design_002_seed_000

| ε | Vertices | Reduction % | OGC | Manifold | Holes | Added / removed cell² | Symmetric cell² | Boundary measured / upper | Repair min clearance | Raster XOR |
|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0 | 46544 | 0.000 | True | True | 466 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.05 | 46544 | 0.000 | True | True | 466 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.1 | 46544 | 0.000 | True | True | 466 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.2 | 46532 | 0.026 | True | True | 466 | 1.125000 / 0.000000 | 1.125000 | 0.181902 / 0.306902 | 0.3535533905932738 | 0 |
| 0.35 | 46528 | 0.034 | True | True | 466 | 2.500000 / 0.000000 | 2.500000 | 0.237204 / 0.362204 | 0.3535533905932738 | 0 |
| 0.5 | 37280 | 19.904 | True | True | 466 | 1572.500000 / 1570.000000 | 3142.500000 | 0.499484 / 0.624484 | 0.3535533905932738 | 0 |
| 0.75 | 18314 | 60.652 | True | True | 466 | 5338.545743 / 6058.045743 | 11396.591485 | 1.193118 / 1.318118 | 0.31234752377721214 | 7675 |
| 1 | 7422 | 84.054 | True | True | 466 | 8798.590057 / 10397.090057 | 19195.680114 | 1.952374 / 2.077374 | N/A or undefined | 15315 |

### design_005_seed_000

| ε | Vertices | Reduction % | OGC | Manifold | Holes | Added / removed cell² | Symmetric cell² | Boundary measured / upper | Repair min clearance | Raster XOR |
|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0 | 39542 | 0.000 | True | True | 321 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.05 | 39542 | 0.000 | True | True | 321 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.1 | 39542 | 0.000 | True | True | 321 | 0.000000 / 0.000000 | 0.000000 | 0.000000 / 0.000000 | 0.3535533905932738 | 0 |
| 0.2 | 39528 | 0.035 | True | True | 321 | 1.312500 / 0.000000 | 1.312500 | 0.181902 / 0.306902 | 0.3535533905932738 | 0 |
| 0.35 | 39524 | 0.046 | True | True | 321 | 3.312500 / 0.000000 | 3.312500 | 0.242069 / 0.367069 | 0.48507125007266594 | 0 |
| 0.5 | 31566 | 20.171 | True | True | 321 | 1371.937500 / 1368.750000 | 2740.687500 | 0.499230 / 0.624230 | 0.48507125007266594 | 0 |
| 0.75 | 15408 | 61.034 | True | True | 321 | 4580.027161 / 5132.339661 | 9712.366822 | 1.290020 / 1.415020 | 0.48507125007266594 | 6489 |
| 1 | 6071 | 84.647 | True | True | 321 | 7536.597183 / 8891.659683 | 16428.256865 | 1.923048 / 2.048048 | N/A or undefined | 13041 |

## Contact, neck and morphology sensitivity

PER_CONTACT.csv contains every registered repair at every tolerance, including undefined reasons in the individual metrics.json files. Removed original patch material is distinguished from a still-resolved but shifted/widened connection. Local anchor failures and chord changes are geometric warnings, not predictions of strength.

Each candidate has full raster FP/FN/IoU/connectivity/percolation results against both canonical and baseline rasters, plus frozen scalar/curve differences with cache provenance. Continuous differences can be nonzero despite exact raster descriptors.

Notable descriptor and material-repair flags use the prospective exploratory definitions in protocol.json; they are not a scientific production acceptance gate.

## First observed events and non-monotonicity

| Fixture | Event | First tested event | Preceding tested ε | Non-monotonic recovery ε |
|---|---|---:|---:|---|
| design_000_seed_000 | any_descriptor_drift | 0.75 | 0.5 | [] |
| design_000_seed_000 | continuous_connectivity_change | none observed | None | [] |
| design_000_seed_000 | exterior_channel_change | none observed | None | [] |
| design_000_seed_000 | geometry_collapse | none observed | None | [] |
| design_000_seed_000 | hole_topology_change | none observed | None | [] |
| design_000_seed_000 | monitored_neck_link_lost | none observed | None | [] |
| design_000_seed_000 | monitored_neck_narrowed | 0.75 | 0.5 | [] |
| design_000_seed_000 | new_near_zero_geos_robustness_distance | none observed | None | [] |
| design_000_seed_000 | nonmanifold | none observed | None | [] |
| design_000_seed_000 | notable_descriptor_drift | 0.75 | 0.5 | [] |
| design_000_seed_000 | ogc_invalid | none observed | None | [] |
| design_000_seed_000 | raster_disagreement | 0.75 | 0.5 | [] |
| design_000_seed_000 | raster_topology_change | none observed | None | [] |
| design_000_seed_000 | repair_clearance_below_baseline | none observed | None | [] |
| design_000_seed_000 | repair_clearance_unavailable | 1.0 | 0.75 | [] |
| design_000_seed_000 | repair_material_risk | 0.2 | 0.1 | [] |
| design_000_seed_000 | repair_unresolved | none observed | None | [] |
| design_001_seed_000 | any_descriptor_drift | 0.75 | 0.5 | [] |
| design_001_seed_000 | continuous_connectivity_change | none observed | None | [] |
| design_001_seed_000 | exterior_channel_change | none observed | None | [] |
| design_001_seed_000 | geometry_collapse | none observed | None | [] |
| design_001_seed_000 | hole_topology_change | none observed | None | [] |
| design_001_seed_000 | monitored_neck_link_lost | none observed | None | [] |
| design_001_seed_000 | monitored_neck_narrowed | 1.0 | 0.75 | [] |
| design_001_seed_000 | new_near_zero_geos_robustness_distance | none observed | None | [] |
| design_001_seed_000 | nonmanifold | none observed | None | [] |
| design_001_seed_000 | notable_descriptor_drift | 0.75 | 0.5 | [] |
| design_001_seed_000 | ogc_invalid | none observed | None | [] |
| design_001_seed_000 | raster_disagreement | 0.75 | 0.5 | [] |
| design_001_seed_000 | raster_topology_change | none observed | None | [] |
| design_001_seed_000 | repair_clearance_below_baseline | none observed | None | [] |
| design_001_seed_000 | repair_clearance_unavailable | 1.0 | 0.75 | [] |
| design_001_seed_000 | repair_material_risk | 0.2 | 0.1 | [] |
| design_001_seed_000 | repair_unresolved | none observed | None | [] |
| design_002_seed_000 | any_descriptor_drift | 0.75 | 0.5 | [] |
| design_002_seed_000 | continuous_connectivity_change | none observed | None | [] |
| design_002_seed_000 | exterior_channel_change | none observed | None | [] |
| design_002_seed_000 | geometry_collapse | none observed | None | [] |
| design_002_seed_000 | hole_topology_change | none observed | None | [] |
| design_002_seed_000 | monitored_neck_link_lost | none observed | None | [] |
| design_002_seed_000 | monitored_neck_narrowed | 0.5 | 0.35 | [] |
| design_002_seed_000 | new_near_zero_geos_robustness_distance | none observed | None | [] |
| design_002_seed_000 | nonmanifold | none observed | None | [] |
| design_002_seed_000 | notable_descriptor_drift | 0.75 | 0.5 | [] |
| design_002_seed_000 | ogc_invalid | none observed | None | [] |
| design_002_seed_000 | raster_disagreement | 0.75 | 0.5 | [] |
| design_002_seed_000 | raster_topology_change | none observed | None | [] |
| design_002_seed_000 | repair_clearance_below_baseline | 0.75 | 0.5 | [] |
| design_002_seed_000 | repair_clearance_unavailable | 1.0 | 0.75 | [] |
| design_002_seed_000 | repair_material_risk | 0.2 | 0.1 | [] |
| design_002_seed_000 | repair_unresolved | none observed | None | [] |
| design_005_seed_000 | any_descriptor_drift | 0.75 | 0.5 | [] |
| design_005_seed_000 | continuous_connectivity_change | none observed | None | [] |
| design_005_seed_000 | exterior_channel_change | none observed | None | [] |
| design_005_seed_000 | geometry_collapse | none observed | None | [] |
| design_005_seed_000 | hole_topology_change | none observed | None | [] |
| design_005_seed_000 | monitored_neck_link_lost | none observed | None | [] |
| design_005_seed_000 | monitored_neck_narrowed | 0.5 | 0.35 | [] |
| design_005_seed_000 | new_near_zero_geos_robustness_distance | none observed | None | [] |
| design_005_seed_000 | nonmanifold | none observed | None | [] |
| design_005_seed_000 | notable_descriptor_drift | 0.75 | 0.5 | [] |
| design_005_seed_000 | ogc_invalid | none observed | None | [] |
| design_005_seed_000 | raster_disagreement | 0.75 | 0.5 | [] |
| design_005_seed_000 | raster_topology_change | none observed | None | [] |
| design_005_seed_000 | repair_clearance_below_baseline | none observed | None | [] |
| design_005_seed_000 | repair_clearance_unavailable | 1.0 | 0.75 | [] |
| design_005_seed_000 | repair_material_risk | 0.2 | 0.1 | [] |
| design_005_seed_000 | repair_unresolved | none observed | None | [] |
| design_009_seed_001 | any_descriptor_drift | 0.75 | 0.5 | [] |
| design_009_seed_001 | continuous_connectivity_change | none observed | None | [] |
| design_009_seed_001 | exterior_channel_change | none observed | None | [] |
| design_009_seed_001 | geometry_collapse | none observed | None | [] |
| design_009_seed_001 | hole_topology_change | none observed | None | [] |
| design_009_seed_001 | monitored_neck_link_lost | none observed | None | [] |
| design_009_seed_001 | monitored_neck_narrowed | 0.5 | 0.35 | [] |
| design_009_seed_001 | new_near_zero_geos_robustness_distance | none observed | None | [] |
| design_009_seed_001 | nonmanifold | none observed | None | [] |
| design_009_seed_001 | notable_descriptor_drift | 0.75 | 0.5 | [] |
| design_009_seed_001 | ogc_invalid | none observed | None | [] |
| design_009_seed_001 | raster_disagreement | 0.75 | 0.5 | [] |
| design_009_seed_001 | raster_topology_change | none observed | None | [] |
| design_009_seed_001 | repair_clearance_below_baseline | none observed | None | [] |
| design_009_seed_001 | repair_clearance_unavailable | none observed | None | [] |
| design_009_seed_001 | repair_material_risk | none observed | None | [] |
| design_009_seed_001 | repair_unresolved | none observed | None | [] |

These are discrete observed brackets, not exact thresholds. Null diagnostics do not count as recovered passes. Complete sequences are retained.

## Conservative promising diagnostic points

- design_000_seed_000: []
- design_009_seed_001: []
- design_001_seed_000: []
- design_002_seed_000: []
- design_005_seed_000: []

Intersection across all five fixtures: []. This is a strict available-diagnostics screen requiring positive vertex reduction; it is not production selection.

## Performance

Sweep elapsed: 185.997 s; maximum traced candidate-stage allocation: 91.241 MiB; process lifetime peak RSS: 616185856 bytes.

Per-candidate files split simplification, geometry, manifold, distance, feature, raster and frozen morphology time. Python tracing does not include all GEOS-native allocations; lazy baseline caches can contribute to the first candidate peak. RSS is process lifetime high-water, not incremental candidate memory.

## Limitations and stage boundary

Only five registered fixtures and the stated controls were tested. No physical units, FEM, manufacturing criteria, universal morphology preservation or production tolerance are established. Raster equality does not imply continuous equality. v0.5B1 is not full v0.5B acceptance. Historical v0.5A HOLD and scoped v0.5A.1 amended PASS remain unchanged.

Review the study-specific scientific interpretation and proposed v0.5B2 architecture in the accompanying new documentation. No protected simplifier or later stage has been implemented.
