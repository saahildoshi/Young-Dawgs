# Final v0.7.2 validation

| Verification | Passed | Scope |
|---|---:|---|
| active | 912 | Zero failures, errors or skips |
| archived_replays | 475 | Zero failures, errors or skips |
| historical_licensed_artifacts | 49 | Zero failures, errors or skips |
| new_v072_licensed_artifacts | 76 | Zero failures, errors or skips |

The active suite includes 16 new optimization tests. Archived 475 checks are replays across nine groups, not additional unique tests. Historical 49 licensed-artifact checks comprise 26 v0.7.1 and 23 older checks, with no old native jobs. Final 76 new licensed checks supersede the earlier nine baseline-only checks; do not add both as independent evidence. All 71 source models were independently reopened; each has five actual solved checkpoints, complete mesh/material/constraint readback, reaction balance, strain-energy/work and native field acceptance. H1 uses65,536 elements/66,049 nodes; H2 uses262,144/263,169 while preserving the same labels and geometry.

Actual native processes142 =71 solves +71 readbacks, below the150-call limit. Supervised native wall-time sum 2869.449s (47.824min), peak single process-tree RSS 2.780 GiB, minimum available RAM 39.206 GiB; raw artifact storage 39.455 GiB at `C:\Users\sd22446\AppData\Local\YoungDawgs\artifacts\solver\v072\run_001`. Two cores, one native job at a time, existing system-health supervision, no arbitrary RSS cap or pagefile change. Paging values are system proxies, not per-solver/pagefile-only rates. Native outputs and derived true-scale coordinates stay outside Git.

All 16,596 originally tracked files are unchanged; all 497 critical new native artifacts authenticate. Prompts, code, seed partition, material/BC/element/mesh policy and morphology constraints retain their frozen identities. All 50 held-out structures satisfy the registered limits and diversity diagnostics. No researcher repairs, seed substitutions, hidden result access before collective freeze or extra model calls occurred. One Windows display-capture failure delayed the fourth capture and was resolved by user display reconnection; it caused no model resubmission or scientific-data substitution.

The source evaluator and actual R1 configuration are inherited unchanged from v0.7.1. Its exact-release manual-access limitation remains documented there; actual R1 inventories and analytical/constitutive controls establish the executed behavior. No new claim of experimental material validation follows from this software/native verification.

| Independent scientific status | Outcome |
|---|---|
| STARTING_GENERATOR_AUTHENTICATED | PASS_VERIFIED |
| COMMON_STARTING_POINT_FROZEN | PASS_VERIFIED |
| COMPOSITION_CONSTRAINT_REGISTERED | PASS_VERIFIED |
| MORPHOLOGY_CONSTRAINTS_REGISTERED | PASS_VERIFIED |
| BASELINE_STRUCTURAL_FEASIBILITY | PASS_VERIFIED |
| BASELINE_MECHANICAL_VARIABILITY_MEASURED | PASS_VERIFIED |
| BASELINE_NATIVE_STRESS_STRAIN_AVAILABLE | PASS_VERIFIED |
| MF_NF_PROMPTS_MATCHED | PASS_VERIFIED |
| MECHANICAL_FEEDBACK_PACKET_AUTHENTICATED | PASS_VERIFIED |
| GENUINE_MF_RESPONSES_CAPTURED | PASS_VERIFIED |
| GENUINE_NF_RESPONSES_CAPTURED | PASS_VERIFIED |
| EQUAL_REVISION_BUDGET_VERIFIED | PASS_VERIFIED |
| ALL_OPTIMIZATION_SCRIPTS_FROZEN | PASS_VERIFIED |
| HELDOUT_SEED_ISOLATION_VERIFIED | PASS_VERIFIED |
| MF_STRUCTURAL_FEASIBILITY | PASS_VERIFIED |
| NF_STRUCTURAL_FEASIBILITY | PASS_VERIFIED |
| STOCHASTIC_DIVERSITY_PRESERVED | PASS_VERIFIED |
| HELDOUT_MECHANICAL_EVALUATION | PASS_VERIFIED |
| NATIVE_FULL_CURVE_CONFIRMATION | PASS_VERIFIED |
| LLM_MECHANICAL_FEEDBACK_EXECUTED | PASS_VERIFIED |
| FIXED_COMPOSITION_PRESERVED | PASS_REGISTERED64_PIXEL_TOLERANCE__REVISED40_OF40_EXACT20731__BASE_NOT_EXACT |
| DISPERSED_MORPHOLOGY_PRESERVED | PASS_FROZEN_NUMERIC_ENVELOPE__STRONG_NATURAL_PARTICLE_FAMILY_PRESERVATION_NOT_ESTABLISHED |
| BASELINE_RELATIVE_IMPROVEMENT | ALL_FOUR_SCRIPT_MEAN_GAINS_POSITIVE |
| FEEDBACK_VERSUS_CONTROL_COMPARISON | COMPLETED_DESCRIPTIVE_NF_HIGHER_OR_EQUAL |
| SCREENING_MODULUS_VERIFIED | FINAL_POINT_SECANT_AGREES_WITH_FULL_CURVE_FIT__NO_ONE_POINT_ONLY_NATIVE_ROUTE |
| H2_MESH_CONFIRMATION | 15_PROSPECTIVELY_SELECTED_GEOMETRIES_EXECUTED__OTHER35_H1_ONLY |
| H2_PRELIMINARY_2PERCENT_GATE | PASS_FOR_ALL15 |
| OPTIMIZATION_EFFECT_NUMERICALLY_RESOLVED | ALL12_REFINED_REVISION_PAIRS_PERSIST_ABOVE_OBSERVED_CHANGE_DIAGNOSTIC |
| COMPOSITION_CONFOUNDING_ASSESSED | EXACT_MF_VS_NF__BASE_TOLERANCE_ONLY__NO_GUESSED_CORRECTION_OR_STRONG_GEOMETRY_ONLY_ATTRIBUTION |
| PRELIMINARY_LLM_MECHANICAL_OPTIMIZATION_SUPPORTED | CONSTRAINED_NUMERICAL_STIFFENING_OBSERVED__STRONG_PHYSICAL_PARTICLE_COMPOSITE_OPTIMIZATION_NOT_QUALIFIED |
| PRELIMINARY_FEEDBACK_ADVANTAGE_SUPPORTED | NOT_SUPPORTED__NO_FEEDBACK_ARM_MEAN_IS_HIGHER_OR_EQUAL |
| PHYSICAL_MATERIAL_CALIBRATION | NOT_CALIBRATED |
| REPRESENTATIVE_VOLUME_QUALIFICATION | NOT_QUALIFIED |
| CROSS_FAMILY_MECHANICAL_OPTIMIZATION | NOT_RUN |
| PAPER_READINESS | CONTROLLED_SMALL_NUMERICAL_PILOT__NO_PHYSICAL_OR_GENERAL_LLM_TREATMENT_EFFECT_CLAIM |
