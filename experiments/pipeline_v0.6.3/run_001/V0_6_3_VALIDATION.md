# v0.6.3 scientific validation

## A. Executive summary

**MESH_IDENTITY_AND_IMPORT_PASS — MICROSTRUCTURE_NUMERICAL_HOLD — RESEARCH_HOLD**. Historical semantic mesh identity reproduced exactly, all frozen
geometry/mesh gates passed and the full actual MAPDL import was exhaustively
verified. Two bounded real full-model contact attempts were made; valid results
are restricted to the checkpoints explicitly recorded in the pilot report.

## B–D. Recovery, qualification and import

See V0_6_3_MESH_RECOVERY.md and V0_6_3_ANSYS_IMPORT.md. The original NPZ container
was not recovered; the reproduced arrays exactly match the historical semantic
hash. Raw ZIP byte equality is not claimed. All 2,766,505 nodes / 1,261,670 TRI6,
412 pores and seven-element registered chords are preserved. The 10° requirement
was not relaxed; minimum angle 11.404135°. Geometry and historical HOLDs unchanged.

## E–F. Resources and contact

See V0_6_3_RESOURCE_FEASIBILITY.md and V0_6_3_CONTACT_SENSITIVITY.md. Actual
assembly and factorization evidence supplement—not merely repeat—array-size
estimates. Hardware memory fit does not establish nonlinear convergence.
Every correction was registered prospectively; original failed data remain.

## G–H. Pilot and mechanical data

See V0_6_3_MICROSTRUCTURE_PILOT.md and mechanical_results/attempt_002. Status:
RESOURCE_LIMIT. Valid checkpoint count: 0. No predicted, unconverged
or rectangle data substitute for microstructure response. Feedback explicitly
excludes invalid numerical output from design ranking.

## I–J. Numerical and scientific limitations

Single geometrically qualified mesh; mechanical refinement convergence remains
UNQUALIFIED. PLATEN_CONTACT_ONLY; internal pore/strut self-contact is not configured
or demonstrated. Material, scale and plane stress are provisional; no experimental
calibration, yield/failure model or paper-quality comparative dataset. Historical
cumulative small-pore fidelity / production simplification HOLDs and the recorded
15-pixel repair remain. Contact sensitivity is bounded, and fixed-stiffness warnings
are retained. v241 help access remains incomplete; supported commands are evidenced
by actual v241 execution plus official adjacent-release comparison documentation.

## K. Reproducibility and verification

Artifact root is configurable via YD_ARTIFACT_ROOT; manifests retain relative
paths, source/config/runtime identities and both semantic/byte hashes. No upload
or required cloud service. Full raw solver files remain local; receipts,
scientific summaries, numerical checkpoint CSVs and figures are tracked.

Active tests: 676 collected,
676 passed,
0 failed. Archive fixture replay:
475 passed separately.
Real v063 evidence checks: 6 passed,
1 failed. The actual-converged-response
check intentionally fails if no microstructure checkpoint converged; its expected
outcome is never weakened to improve counts. Overlapping suites are not summed.
Historical files and original collection/context failures remain unchanged.
The release command scopes the active suite to tests/ and validation/test_evaluator.py
with EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py, as documented before
this milestone. An initial run without that environment selection used frozen
legacy v1.0 and returned 20 failed / 655 passed; the complete output is preserved.
An additional unscoped repository collection encountered 11 historical snapshot
module-name collisions; both collection outputs are preserved separately.
The previous v062 real-evidence checks passed again: 5.
Native solver .out/.err/.mntr files retain their whitespace and exact bytes;
Git whitespace review flags those native diagnostic lines. Source-code diff
review passes separately; native evidence is not rewritten for formatting.

## Independent acceptance

| Category | Status |
|---|---|
| SOURCE_GEOMETRY_AUTHENTICATED | PASS |
| HISTORICAL_MESH_RECOVERED | ORIGINAL_NPZ_NOT_FOUND |
| HISTORICAL_MESH_IDENTITY_VERIFIED | PASS_EXACT_SEMANTIC_REPRODUCTION |
| GEOMETRIC_MESH_QUALIFICATION | PASS_UNCHANGED_GATES |
| ANSYS_IMPORT | PASS_EXHAUSTIVE_FULL_MESH |
| CONTACT_SENSITIVITY | BOUNDED_TESTS_AND_DOCUMENTED_ALGORITHM_AMENDMENT |
| RESOURCE_FEASIBILITY | ACTUAL_ASSEMBLY_AND_FACTORIZATION_EVIDENCE_WITH_REGISTERED_LIMITS |
| MICROSTRUCTURE_PILOT | RESOURCE_LIMIT |
| INTERNAL_SELF_CONTACT | UNQUALIFIED_NOT_CONFIGURED |
| MECHANICAL_MESH_CONVERGENCE | UNQUALIFIED |
| PAPER_READINESS | RESEARCH_HOLD |
| LLM_FEEDBACK_LOOP | NOT_IMPLEMENTED |
| LLM_OPTIMIZATION | NOT_IMPLEMENTED |
| MANUFACTURING | UNQUALIFIED |
| REGENERATED_MESH_QUALIFIED | PASS_EXACT_HISTORICAL_IDENTITY |
| MAPDL_IMPORT_PASS | PASS |
| MODEL_RESOURCE_ASSESSMENT_PASS | PASS_BOUNDED_ASSEMBLY_AND_ACTUAL_FACTORIZATION_SCOPE_ONLY |
| CONTACT_SENSITIVITY_REVIEWED | PASS_BOUNDED_SCOPE_WITH_WARNINGS |
| MICROSTRUCTURE_PLATEN_CONTACT_CONFIGURED | PASS_INITIAL_SOLVER_CHECKS |
| MICROSTRUCTURE_SOLVER_PASS | FAIL_NO_CONVERGED_CHECKPOINT |
| MICROSTRUCTURE_CONTACT_FORCE_PASS | CONFIGURED_NOT_DEMONSTRATED |
| MICROSTRUCTURE_MECHANICAL_RESULTS_PASS | NOT_AVAILABLE_NO_VALID_CHECKPOINT |

## L. Git history

Started clean at 9af3d404c94293c9fa705552bb41497358ddd63e on master. No push or
history rewrite. Protected generators/evaluators/canonical geometry and all
v0.6/v0.6.1/v0.6.2 experiments are unchanged under the saved diff.

- `00c194a04ae6e945f7c610992b3c60d97cb06dc0` — docs(fem): register v0.6.3 mesh recovery and bounded pilot gates
- `6be0a434eee45100235bc8053f02349d1a69ba62` — feat(mesh): authenticate portable mesh archives and frozen Windows reproduction
- `4548f7d4c6d2c8ad354ede98d64d150c0b63bc87` — feat(mesh): reproduce and qualify historical native-1024 mesh identity
- `9a45102a72fa0147716e7c1738e5f2ec2f128915` — feat(ansys): verify full TRI6 microstructure import and contact sensitivity
- `8672c8482547cbbf21b4afd99a555547cce2aab8` — feat(ansys): freeze resource-bounded staged microstructure contact pilot
- `0dd458813569f0671bc7eb9d390d6d311a189ffd` — feat(fem): validate microstructure checkpoints and exclude invalid numerical feedback
- `71bf347e6817c4bb82fb405c6cbb28a322033095` — fix(ansys): register fixed-penalty correction after microstructure residual plateau
- `7cb9411e3f844fe8c471cf5ad987ca9149ac350a` — test(fem): verify native import evidence and portable artifact retrieval
- `362d67fbc3df24915edf8c028dd5534237943edd` — fix(ansys): preserve solver warnings and record bounded pilot nonconvergence
- `f2feed53e84e439d74e95fb901eb229a84521e8d` — fix(mesh): normalize portable artifact paths and verify durable local recovery

Final reporting commit is the commit containing this document; its exact hash
is supplied in final response/Git history to avoid a self-referential hash.

## M. Next milestone

Diagnose full-model nonlinear convergence with early cutback and explicit contact-iteration telemetry under a new protocol; do not repeat identical failed large jobs or alter qualified geometry.
Only then produce a calibrated, uncertainty-aware mechanical dataset and review
the feedback contract for the first controlled LLM-guided iteration. No batch
FEM, autonomous optimization, manufacturing qualification or 3D work was implemented.
