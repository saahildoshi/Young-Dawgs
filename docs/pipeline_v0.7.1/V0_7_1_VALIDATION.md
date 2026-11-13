# Validation and scientific acceptance

| Verification | Passed | Scope |
|---|---:|---|
| Active software suite | 896 | Includes 11 new phase/mesh/boundary regression checks |
| Archived geometry replays | 475 | Nine original groups; replay counts are not new unique tests |
| Historical licensed artifacts | 23 | Read-only checks of retained v0.6.10 evidence; no old solver campaign restarted |
| New licensed artifacts | 26 | Real RST/DB hashes, connectivity, analytical controls, exact phases, readback and budget |

All groups have zero failures, errors or skips. Native execution comprised 15 source solves and 17 separate read-only processes, within the 32-call limit. Fourteen source models passed all mechanical gates, providing 70 actual accepted native load checkpoints. The first equal-material dense-grid model was rejected, preserved, diagnosed and recovered using exact boundary node IDs. A result-serialization issue was corrected using already saved native data. No failed result was substituted for an accepted result.

The source RSTs were reopened independently; the reference was reopened twice with byte-identical curve, displacement, stress/strain and connectivity exports. Native coordinates, material IDs, every quadrilateral connectivity entry and complete constraint inventories match the intended meshes. Reactions, signed displacements, plane-stress constitutive relations, engineering shear, volume-mean stress and energy checks pass. Native element-averaged fields remain phase associated; they are not globally averaged nodal stresses or physical failure predictions.

The local 2024 R1 installation did not contain a PLANE182 element manual, and the exact R1 online manual was not retrievable. The [official adjacent-release element reference](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_PLANE182.html) and [ETABLE reference](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_ETABLE.html) informed the implementation. Actual R1 ETLIST/RLIST/MPLIST and the licensed analytical/constitutive controls corroborate the executed options and behavior. This documentation limitation is retained explicitly.

All 16,294 previously tracked files authenticate unchanged. This includes the P3/F1 originals and annotations, frozen LLM scripts, 320 prior generated arrays, morphology scores and historical porous research. Raw native files remain under `C:\Users\sd22446\AppData\Local\YoungDawgs\artifacts\solver\v071\run_001`. No RST was copied for independent readback. Critical native artifacts authenticate against recorded hashes; all ten figure files authenticate against their native provenance manifests.

Supervised native wall time summed across jobs: 680.945s (11.349min). Peak single-process-tree RSS: 2.779GiB. Minimum observed available RAM: 38.419GiB. Raw artifact storage: 9.229GiB. One native job ran at a time with two cores, existing system-health supervision and no fixed RSS cap. Paging counters are system hard-fault disk-read proxies, not pagefile-only or per-solver measurements. Full samples and commit/paging availability are retained in process receipts.

Independent acceptance statuses are recorded below. A useful numerical milestone does not imply material calibration, representative volume qualification, asymptotic convergence or optimization.

| Scientific status | Outcome |
|---|---|
| V070_REFERENCE_DATA_PRESERVED | PASS_VERIFIED |
| V070_LLM_SCRIPTS_PRESERVED | PASS_VERIFIED |
| V070_HELDOUT_OUTPUTS_PRESERVED | PASS_VERIFIED |
| P3_SOURCE_AUTHENTICATED | PASS_VERIFIED |
| STRUCTURED_MESH_QUALIFIED | PASS_VERIFIED |
| MATERIAL_ASSIGNMENT_VERIFIED | PASS_VERIFIED |
| BONDED_INTERFACE_TOPOLOGY_VERIFIED | PASS_VERIFIED |
| HOMOGENEOUS_ANALYTICAL_BENCHMARK | PASS_VERIFIED |
| TWO_PHASE_PARALLEL_BENCHMARK | PASS_VERIFIED |
| TWO_PHASE_SERIES_BENCHMARK | PASS_VERIFIED |
| EQUAL_MATERIAL_CONTROL | PASS_VERIFIED |
| BOUNDARY_CONDITIONS_VERIFIED | PASS_VERIFIED |
| REACTION_EXTRACTION_VERIFIED | PASS_VERIFIED |
| STRAIN_ENERGY_VERIFIED | PASS_VERIFIED |
| P3_REFERENCE_NATIVE_SOLVE | PASS_VERIFIED |
| P3_REFERENCE_STRESS_STRAIN | PASS_VERIFIED |
| P3_REFERENCE_EFFECTIVE_MODULUS | PASS_VERIFIED |
| P3_A01_MECHANICALLY_EVALUATED | PASS_VERIFIED |
| P3_B02_MECHANICALLY_EVALUATED | PASS_VERIFIED |
| P3_C02_R1_MECHANICALLY_EVALUATED | PASS_VERIFIED |
| P3_C02_PAIRED_MECHANICAL_COMPARISON | PASS_VERIFIED |
| P3_PHASE_STRESS_FIELDS | PASS_VERIFIED |
| P3_REFERENCE_RELATIVE_MECHANICAL_COMPARISON | PASS_VERIFIED |
| HISTORICAL_POROUS_MECHANICS_PRESERVED | PASS_TRACKED_HASHES_AND23_APPLICABLE_NATIVE_ARTIFACT_CHECKS__NO_NEW_HISTORICAL_SOLVES |
| P3_PHASE_SEMANTICS_VERIFIED | PASS_TWO_SOLID_MECHANICAL_MAPPING__PHASE5_CHEMISTRY_PROVISIONAL |
| P3_REFERENCE_MESH_SENSITIVITY | PASS_PRELIMINARY_H1_H2_2PERCENT_GATE |
| MORPHOLOGY_MECHANICS_LINK_ESTABLISHED | EXPLORATORY_EXACT_SEED_NATIVE_ASSOCIATION__NO_CAUSAL_OR_POPULATION_CLAIM |
| MECHANICAL_MESH_CONVERGENCE | PRELIMINARY_TWO_LEVEL_SENSITIVITY_ONLY__ASYMPTOTIC_CONVERGENCE_NOT_QUALIFIED |
| PHYSICAL_MATERIAL_CALIBRATION | NOT_CALIBRATED |
| REPRESENTATIVE_VOLUME_QUALIFICATION | NOT_QUALIFIED |
| F1_MECHANICS | NOT_RUN_DEFERRED |
| MECHANICAL_FEEDBACK_SCHEMA | FROZEN_AND_POPULATED_WITH_ACTUAL_RESULTS__FUTURE_FEEDBACK_SCHEMA_ONLY |
| LLM_MECHANICAL_FEEDBACK_EXECUTED | NOT_RUN |
| LLM_MECHANICAL_OPTIMIZATION | NOT_IMPLEMENTED |
| PAPER_READINESS | EXPLORATORY_NUMERICAL_BENCHMARK_ONLY__NO_CALIBRATED_MATERIAL_OR_POPULATION_CLAIMS |
