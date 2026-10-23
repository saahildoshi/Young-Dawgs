# Independent scientific requalification — v0.5C.1

**Overall scientific status: HOLD_SMALL_PORE_POLICY**. Feature qualification and cumulative pore policy are separate. Production remains HOLD / UNQUALIFIED. No export or CAD work is implemented.

## Method and root cause

The historical width-loss failure is reproduced byte-for-byte by original B2. At D4/S1 epsilon 0.50, the fixed vertical section at (57.5,556.5) changes from 9 to 8.916666666666629 cells. Original proposal p0000391 replaces [(57,561),(60,561),(60,560),(63,560)] with [(57,561),(63,560)]. The opposite boundary remains y=552. Direct coordinate interpolation gives y=560.9166666667 at x=57.5. This is a real 1/12-cell loss, not numeric tolerance.

The four states remain G0 canonical native1024 binary occupancy, G1 exact cell geometry, G2 explicit A1 manifold candidate and G3 revised protected simplification. Every source is authenticated; G1→G2, G2→G3, actual G1→G3 and native-grid reconstruction remain distinct. All prior files and scientific statuses are immutable.

The versioned proposal gate and independent audit are detailed in FEATURE_PROTECTION_CORRECTION.md and the frozen protocol. Event-slab source/opposition width functions are affine where single-valued; the largest qualifying loss is checked at the applicable interval endpoints. One-sided limits are explicitly distinguished from a possibly ambiguous section exactly at an event coordinate. Only the registered directions/horizon are covered. Unsupported or ambiguous input remains a failure, not a zero measurement.

## Synthetic and regression evidence

50 new targeted tests cover safe/unsafe/uncertain sections, conservative restoration and small-pore diagnostics. Original B2 reproduced the historical failure byte-for-byte; revised actual width is 9.000000000000 cells. All 100 regression settings are retained with original/revised proposal, geometry, vertex and timing comparisons.

## Untouched independent cohort

Six new parameter combinations were selected by scipy.stats.qmc.LatinHypercube with seed 20261021 inside exactly the original v0.3 bounds. Replicate seeds are 12031 and 12032. All prior ten points/seeds are consumed evidence. Final corrected code, settings, controls, regression results, policy and cohort were hashed before generating or inspecting the new native outputs. No parameter was selected for expected passing behavior and no holdout was used to tune the algorithm.

| New point | Solid fraction target | Strut scale | Pore scale | Nearest old normalized distance |
|---|---:|---:|---:|---:|
| 0 | 0.47391792432449481 | 4.3129301970676144 | 7.6134571228175716 | 0.28141614 |
| 1 | 0.5071124053412055 | 4.5131755982467219 | 6.5932592838580835 | 0.24770561 |
| 2 | 0.48027415063591694 | 3.9258404496996087 | 8.0668450853653582 | 0.14973229 |
| 3 | 0.43434070185531642 | 3.8494114592366788 | 5.9161109887336298 | 0.31940680 |
| 4 | 0.45822996429946322 | 3.5468023790059169 | 6.9360312184938921 | 0.29244702 |
| 5 | 0.51597099294438797 | 4.5499273116490402 | 8.5495930287802135 | 0.32064472 |

Independent structures: 12/12; independent configurations: 60/60 at [0,0.20,0.35,0.50,0.75]. Unsupported sources: []. Internal errors: []. Independent feature status: **PASS_TESTED_DOMAIN**. No unsupported or failed case is excluded from the expected denominator.

## Continuous, discrete and feature results

Frozen hard constraints passed 160/160; independently manifold 160/160; XOR zero 160/160; frozen descriptor equality 160/160. Maximum G2→G3 symmetric area 672.5 cell²; actual G1→G3 672.75 cell². Added/removed maxima 336.25/336.25 cell². Independent displacement upper maxima G2→G3 0.702155172414, G1→G3 0.702155172414 cell, against sqrt(2)/2 + 1e-10.

Budgets are unchanged: added/removed each 0.0025 of G2 occupied area; symmetric 0.005 of G2 occupied area; each matched G2 pore distortion 0.005 of that pore; guard coordinates/sets exact; registered widths and repair clearances permit zero loss with 1e-10-cell numeric allowance. C cumulative global screens use G1 occupied area and actual G1→G3 displacement. No cumulative per-pore0.5% cap is invented retrospectively.

Registered repair sites 161; registered natural probes 768; unique independent axial probes 6144; oblique probes 1536. Axial/oblique evaluations 30720/7680. Narrowing events 0/0; undefined 0; maximum measured new independent narrowing 0 cell. Registered width-loss maximum 0; repair-clearance-loss maximum 0 cell.

Pore identity, split/merge/birth/deletion and domain-void incidence are independently checked alongside direct edge/ring incidence, orientation, WKB/coordinate reconstruction and native-center rasterization. Boundary displacement uses the unchanged C changed-line sampling with maximum gap0.025 cell and an explicit Lipschitz upper bound; sampled maxima alone are not exact continuous Hausdorff distances. Descriptor reuse requires independently proven identical arrays; fresh original and selected changed-candidate integration evaluations are retained. Frozen whole-mask P10 and its historical calibration caveat are unchanged.

### Separate transformation maxima

Each column is its own maximum across evaluable configurations; a row does not describe one selected fixture. Areas are cell²; displacement is cells.

| Transformation | Added | Removed | Symmetric | Relative symmetric | Displacement upper |
|---|---:|---:|---:|---:|---:|
| G1→G2 | 0.6875 | 0 | 0.6875 | 0.00013835% | 0.189276695297 |
| G2→G3 | 336.25 | 336.25 | 672.5 | 0.12429874% | 0.702155172414 |
| G1→G3 | 336.5 | 336.25 | 672.75 | 0.12434501% | 0.702155172414 |

Actual cumulative G1→G3 matched-pore maxima: absolute 0.0625 cell²; relative 6.25000000%. These are measured directly, rather than inferred by summing stage errors.

### Monitored-section coverage

Counts include repeated tolerances. A chord intersection may retain a collinear section; it does not alone establish a width change.

| Cohort | Method | Evaluations | Unguarded centers | Sections not entirely guarded | Section geometry changed | Accepted chord incidence | Metadata unresolved |
|---|---|---:|---:|---:|---:|---:|---:|
| regression | registered | 2400 | 0 | 0 | 0 | 0 | 0 |
| regression | axial | 19200 | 2410 | 2794 | 0 | 0 | 0 |
| regression | oblique | 4800 | 0 | 734 | 0 | 0 | 0 |
| independent_cohort | registered | 1440 | 0 | 0 | 0 | 0 | 0 |
| independent_cohort | axial | 11520 | 1479 | 1710 | 0 | 0 | 0 |
| independent_cohort | oblique | 2880 | 28 | 489 | 0 | 0 | 0 |

Undefined width measurements and unresolved reporting metadata are separate. A reporting incidence calculation never changes the prospectively registered width decision.

**Coverage limitation:** none of the monitored registered, axial, or oblique sections intersects an accepted replacement chord in this study. Consequently these finite audits verify unchanged sampled sections; they do not independently interrogate every accepted edit. The proposal-integrated affine gate supplies the direct changed-region protection in the registered native directions. Oblique probe selection is biased toward short source corridors, many already guarded. This limits the strength of feature generalization despite all prospective sampled gates passing.

## Small-pore policy

**Disposition: the existing policy was applied correctly within its geometric scope; cumulative small-pore scientific fidelity remains UNQUALIFIED. No amended fidelity allowance is adopted.** A physical/measurement-based criterion and fresh policy qualification remain necessary. No pore is excluded and no merge, split or deletion is forgiven because its area is small. The original C finding and HOLD remain historical evidence.

Actual cumulative G1→G3 matched-pore maxima over every setting: absolute 0.0625 cell²; relative 6.25000000%. These direct measurements are separate from the G1→G2 maxima above.

**New independent finding:** 7 source pores attain the maximum relative error. Each has area 1→0.9375 cell² and two incident contact repairs, so two 1/32-cell² triangles give 6.25% loss. All are independent-cohort pores, and identities remain unique. Their fixture/pore/contact identifiers are retained in REAL_COHORT_PORE_AUDIT.json. The construction envelope predicts this loss; it does not justify accepting it as scientific fidelity. Both fixed absolute and relative diagnostic screens reject these cases. No rule was changed after this finding.


## Performance

Regression plus independent execution: 2703.774 s, excluding development, reporting, tests and targeted profiling. Whole-study process lifetime RSS high-water: 913.875 MiB. The studies were untraced; targeted same-fixture engine tracing and native-worker generation peaks are separately saved. Do not present selected stage peaks as a measured full-validation tracemalloc peak. GEOS-native allocation is incompletely covered by Python tracing.

Matched targeted instrumented engine times: original 2.212345 s, revised 4.094561 s. Traced engine peaks: 23.143 and 23.138 MiB. Single-run observations; historical C/B2 studies used different instrumentation and are not fair speed comparators.

## Scientific interpretation and limitations

The correction addresses a generalized native-axis corridor mechanism and preserves useful local simplification, with conservative no-op behavior for uncertain edits. Independent oblique measurements supplement its finite orientation set. Neither finite probe success nor the affine local rule establishes arbitrary-direction/global minimum-neck preservation. Fixed directions/horizon, feature-selection bias, source resolution, floating arithmetic and shared GEOS remain limitations. Raster equality is discrete consistency evidence, not continuous equivalence.

The small-pore result remains scientifically unresolved under a cumulative fidelity policy. No physical dimensions, CAD-kernel tolerance/interoperability, material law, loads, meshing, strength or manufacturing criteria are established. The v0.4.2 failure, scoped v0.4.3 amendment, A HOLD, A1/B2 geometric acceptances and historical C HOLD are unchanged.

## Separate acceptance statuses

| Scope | Status |
|---|---|
| A_source_preservation | PASS_BYTE_IDENTICAL |
| B_root_cause | PASS_REPRODUCED |
| C_generalized_correction | PASS_DOCUMENTED_FAILURE_CLASS |
| D_synthetic_controls | PASS_50_TARGETED_TESTS |
| E_regression | PASS_TESTED_DOMAIN |
| F_independent_features | PASS_TESTED_DOMAIN |
| G_continuous_geometry | PASS_TESTED_BUDGETS |
| H_raster_morphology | PASS_EXACT |
| I_small_pore_policy | UNQUALIFIED_CUMULATIVE_FIDELITY |
| J_overall_scientific | HOLD_SMALL_PORE_POLICY |
| K_production | HOLD_UNQUALIFIED |
| L_CAD_manufacturing_FEM | UNQUALIFIED |

## Handoff and verification

General advancement remains HOLD while the cumulative pore-fidelity policy is unqualified. Even a feature-screen pass is not production, CAD or FEM qualification. A later policy decision or algorithm revision requires separately versioned rules and newly reserved independent evidence. The C.1 handoff defines these restrictions; v0.5D is not implemented.

Final software regression, historical preservation, hash ledger, repeat checks and figure inspection are recorded under verification/COMPLETION.json. CONFIGURATIONS.csv lists every case, including failures; FEATURE_HOLDS.json retains any independent disagreements. FINAL_RESPONSE.md answers all42 requested completion questions.

## Scientific figures

[01_original_failure](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/01_original_failure.png)

[02_corrected_behavior](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/02_corrected_behavior.png)

[03_feature_coverage](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/03_feature_coverage.png)

[04_width_changes](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/04_width_changes.png)

[05_vertex_reduction](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/05_vertex_reduction.png)

[06_continuous_difference](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/06_continuous_difference.png)

[07_small_pore](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/07_small_pore.png)

[08_independent_cohort](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/08_independent_cohort.png)

[09_holdout_results](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/09_holdout_results.png)

[10_runtime_memory](/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/scientific_requalification/run_001/figures/10_runtime_memory.png)
