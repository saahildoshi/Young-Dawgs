# v0.6.4 scientific validation

## A. Executive summary

**NATIVE_NONZERO_EQUILIBRIUM_RECOVERED__RESOURCE_AND_OUTPUT_QUALIFICATION_HOLD**. The evidence supports a contact-detection correction in the
compliant fixture. Full accepted checkpoint count:0. Native equilibrium at0.005%
was recovered, but full RF/contact/stress/strain writing failed under the20GiB
cap. Actual displacement-only diagnostics are quarantined from performance. Historical
contact trajectories remain unknown; current results do not rewrite them.

## B. Historical reconstruction

Both v063 runs reconstructed from actual saved evidence:9/14completedupdates,
no converged substep and no observed cutback before stop. Expensive iterations
and force stagnation were observed. Missing contact/residual telemetry was not
invented. See V0_6_4_FAILURE_FORENSICS.md.

## C. Root-cause hypotheses

All eight registered hypotheses and evidence limits are recorded in the
contact/constraint report and summary/hypotheses.json. Contact-detection
sensitivity is supported prospectively; the exclusive historical cause remains
UNRESOLVED. Resources now prevent complete output, rather than equilibrium.

## D. Diagnostic instrumentation

Native v241 telemetry was tested on the accepted rectangle and compliant
synthetic fixture. Native CND, NRRE, EFLG, NLHIST, logs and actual resource
samples were parsed with version-specific checks. See
V0_6_4_NONLINEAR_DIAGNOSTICS.md for commands, hashes and limitations.

## E. Contact analysis

Gauss detection reproduced failure with native chatter and platen-local FY
residuals. Both pairs retained active elements; total support loss was not
observed. Nodal detection passed the small fixture while retaining fixed PP100.
Some chatter persisted even in successful runs. Historical contact trajectories
were not recorded. Pair-level counts do not identify individual transitions.

## F. Structural and constraint analysis

Analytical rigid-motion rank and actual support listings were checked.
Distributed active normal constraints give rank3 on planar rigid motions;
both-open contact would leave insufficient support. No arbitrary springs or
extra specimen restraints were added. Full flexible modes remain unqualified;
absence of logged negative pivots does not prove their absence.

## G. Controlled experiments

Direct compression converged with different physical supports. Linearized
contact, smaller increments, updated stiffness and fixed FKN1 did not cure
the Gauss fixture. NEQIT8 failed even with nodal detection. All failed controls
are retained. The exact NEQIT24 recovery control passed with automatic
increment prediction and zero failed-trial bisections.

## H. Corrective action

Nodal target-normal detection passed the compliant fixture and matched
rectangle with the original physical assumptions and acceptance limits.
This justified KEYOPT4=2 while retaining fixed PP100, frictionless separable
contact and NLGEOM ON. Actual two-SMP controls preserved the rectangle response.

## I. Full-model retry

The primary reached equilibrium at 0.005% after seven updates, then stopped
at 20.0424 GiB and 422.151 s. Its RST had no readable data set. The conditional
technical repair repeated that known increment and announced equilibrium
after seven updates, then stopped during output at 20.3953 GiB and 333.559 s.
Neither run had a bisection. The memory guard was enforced with sampled
overshoot; the peak was not within the 20-GiB cap. Geometry, mesh and physical
assumptions were preserved. See V0_6_4_RECOVERY_EXPERIMENT.md and native receipts.

## J. Mechanical results

Status:OUTPUT_INCOMPLETE_RESOURCE_LIMIT. Qualified registered checkpoints:0.
No fabricated midside stress, trial-state force curve or extrapolated loading.
There is no accepted point; both secant and fitted initial modulus are null.
The full stress–strain curve remains unavailable.

## K. Scientific limitations

Single geometrically qualified mesh; mechanical refinement convergence is
UNQUALIFIED. Internal self-contact is UNQUALIFIED_NOT_CONFIGURED. E,nu,scale,
thickness and plane stress are provisional and uncalibrated. No yielding,
fracture or pore-closure qualification. Historical small-pore fidelity and
production simplification HOLDs and documented15pixelrepair remain. This
milestone does not qualify paper conclusions, manufacturing or LLM ranking.

## L. Reproducibility and verification

744 active tests passed; 475 archived fixture replay tests passed separately;
16 licensed diagnostic/evidence checks passed, 1 failed.
Counts overlap and are not summed. Synthetic parser controls are not licensed
integration evidence. Historical files/protected paths remain unchanged.
Failed small controls, the monitor race and the initial header-rounding check
remain preserved. Native diagnostic bytes and all solver binaries remain in
the configurable local artifact root; tracked copies are explicitly normalized
text excerpts/receipts/compacttelemetry. Frozen full input/protocol are unchanged.

Execution commands and portable artifact-root handling are documented in
`docs/pipeline_v0.6.4/WINDOWS_EXECUTION.md`. The licensed failure is the actual
full mechanical-acceptance assertion; it is retained without weakening it.

Actual diagnostic figures (hashes in figures/figure_manifest.json):

- [Historical residuals and timing](figures/historical_failures.png)
- [Synthetic fixture and residual localization](figures/synthetic_fixture_and_residuals.png)
- [Small contact iteration diagnostics](figures/small_contact_iteration_diagnostics.png)
- [Controlled small experiments](figures/controlled_small_experiments.png)
- [Full convergence and resources](figures/full_recovery_diagnostics.png)
- [Full residual localization](figures/full_residual_localization.png)
- [Displacement-only diagnostic](figures/displacement_only_diagnostic.png)

Stress/strain fields, accepted contact fields and force/stress–strain curves
are unavailable and are not plotted.

## Independent acceptance

| Category | Status |
|---|---|
| SOURCE_GEOMETRY_INTEGRITY | PASS_UNCHANGED |
| MESH_IDENTITY_AND_QUALITY | PASS_EXACT_HISTORICAL_SEMANTIC_IDENTITY |
| ANSYS_IMPORT | PASS_REUSED_EXHAUSTIVE_V063_NATIVE_IMPORT |
| HISTORICAL_FAILURE_DIAGNOSED | FORCE_STAGNATION_AND_ITERATION_COST_OBSERVED; HISTORICAL_CONTACT_CAUSE_UNRESOLVED |
| NONLINEAR_TELEMETRY_VERIFIED | PASS_ACTUAL_V241 |
| CONTACT_ITERATION_DIAGNOSTICS | PASS_NATIVE_PAIR_COUNTS_CHATTER_STIFFNESS_GAP_AND_FORCE |
| STRUCTURAL_STABILITY_DIAGNOSTICS | RIGID_SUBSPACE_INVESTIGATED; FLEXIBLE_MODES_NOT_EIGENQUALIFIED |
| SMALL_MODEL_VALIDATION | PASS_BOUNDED_CAUSAL_DIAGNOSTICS_WITH_FAILED_CONTROLS_RETAINED |
| CORRECTION_JUSTIFIED | PASS_SMALL_CONTACT_DETECTION_CONTROL_AND_MATCHED_RECTANGLE |
| FULL_MODEL_RECOVERY_ATTEMPT | MEMORY_BUDGET_EXCEEDED |
| PRIMARY_RETRY_RESOURCE_STATUS | MEMORY_BUDGET_EXCEEDED |
| CONDITIONAL_TECHNICAL_REPAIR | PREREGISTERED_DIRECT_CHECKPOINT_RETENTION_REPAIR; NOT_PARAMETER_SEARCH |
| MICROSTRUCTURE_NONZERO_CONVERGENCE | PASS_NATIVE_NONZERO_SUBSTEP |
| MICROSTRUCTURE_PLATEN_FORCE | NATIVE_PAIR_FORCE_EVIDENCE; INDEPENDENT_PILOT_RF_VALIDATION_INCOMPLETE |
| MICROSTRUCTURE_MECHANICAL_OUTPUT | OUTPUT_INCOMPLETE_RESOURCE_LIMIT |
| FULL_STRESS_STRAIN_CURVE | UNAVAILABLE |
| MECHANICAL_MESH_CONVERGENCE | UNQUALIFIED |
| INTERNAL_SELF_CONTACT | UNQUALIFIED_NOT_CONFIGURED |
| PAPER_READINESS | RESEARCH_HOLD |
| LLM_FEEDBACK_LOOP | NOT_IMPLEMENTED |
| MANUFACTURING | UNQUALIFIED |

## M. Git commits

Started clean on master at224741cfec6f0fa4021f18e2f38624ce4210700d.
No push or history rewrite.

- `3f4905d19aeb13a110d1c08d5871b2a929699ae7` — docs(ansys): register v0.6.4 nonlinear convergence diagnostic protocol
- `982a19cb83b913441d64702884b5340b946f58bb` — feat(ansys): capture native nonlinear telemetry and reproduce compliant contact failure
- `954522996163acf82364e71860610caa72f3399b` — fix(ansys): validate nodal contact correction and freeze single full-model recovery
- `0cafe526431e89ddbebfbe35fde6cb07ff39d9a6` — fix(ansys): bind observed native jobname without altering frozen recovery input
- `4cc81c8cf49b8c49f7b131d2e354a07c425719e8` — fix(ansys): register conditional repair for converged-state retention and memory stop
- `31e6d760d7131c5ddc199e32708c50e075b3f0c5` — feat(ansys): authenticate separate read-only field exports and preserve primary recovery evidence
- `e97434ccc91e87ea3ef577b557d8347047f10db6` — fix(ansys): quarantine incomplete native outputs after equilibrium and memory stop
- `5fa147dd0ced84cf5bb09f4e953916b42bf21c48` — docs(fem): report recovered equilibrium and native-output resource hold

The final reporting commit contains this document; its exact hash is in the
final response/Git history, avoiding self-reference.

## N. Next milestone

Register a memory/output diagnostic using a minimal required result set and separately reviewed one-SMP memory behavior; prove complete RF/contact/stress/strain writing and read-only extraction before another full study. Do not retune geometry/contact blindly or raise caps automatically.
Only after credible numerical/physical qualification should a controlled
multi-design dataset and reviewed LLM feedback protocol be considered. No
batch FEM, autonomous optimization,3D or manufacturing workflow was implemented.
