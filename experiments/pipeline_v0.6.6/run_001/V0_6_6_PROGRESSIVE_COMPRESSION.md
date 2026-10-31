# v0.6.6 progressive compression

Scientific status: **PROGRESSIVE_FINE_MESH_RESEARCH_HOLD__TARGET_NOT_REACHED**. Highest independently qualified strain across branches: **0.927060884%**. Highest completed native strain: **1%**; convergence alone does not establish qualification. Primary branch `FINE_FULL_SELF_CONTACT_NODAL_V066_021` is qualified through **0.927060884%**.

Stop reason: The registered 30-minute limit without a new converged state stopped the single bounded contact-onset retry after 3019.84 s. Force residuals kept cycling during the next contact-active trial despite one native bisection. No 1% endpoint passed; 5–40% stages were not executed. This is a numerical contact/control limit under the registered budget, not a demonstrated material-collapse limit.

Thirty percent primary target: NOT REACHED. Forty percent stretch: NOT REACHED. All reported curves stop at actual qualified points. The distinct contact-model branches are never spliced.


## Primary actual mechanical response

| Engineering compression fraction | Travel mm | Upper RF N | Lower RF N | Nominal stress MPa | Signed imbalance fraction | Secant MPa |
|---|---|---|---|---|---|---|
| 0.0005 | 0.00512 | -0.6039598776 | 0.6075600911 | 0.0589804568 | 0.005925691204 | 117.9609136 |
| 0.001 | 0.01024 | -1.203355235 | 1.202968495 | 0.1175151597 | 0.0003213851482 | 117.5151597 |
| 0.0015 | 0.01536 | -1.79775728 | 1.794248435 | 0.1755622344 | 0.001951790059 | 117.0414896 |
| 0.002 | 0.02048 | -2.394127853 | 2.38952216 | 0.2338015482 | 0.001923745766 | 116.9007741 |
| 0.0025 | 0.0256 | -2.984222322 | 2.983730001 | 0.2914279611 | 0.0001649747288 | 116.5711844 |
| 0.00325 | 0.03328 | -3.872668942 | 3.872656431 | 0.3781903264 | 3.230697364e-06 | 116.3662543 |
| 0.004375 | 0.0448 | -5.200910085 | 5.203892937 | 0.5079013755 | 0.0005731963446 | 116.091743 |
| 0.0060625 | 0.06208 | -7.18060304 | 7.180412866 | 0.7012307656 | 2.648444458e-05 | 115.6669304 |
| 0.00859375 | 0.088 | -10.12260211 | 10.12195318 | 0.9885353621 | 6.410673519e-05 | 115.0295694 |
| 0.008642241379 | 0.08849655172 | -10.17841266 | 10.17829922 | 0.9939856109 | 1.114497601e-05 | 115.0147939 |
| 0.008690732759 | 0.08899310345 | -10.23396396 | 10.2339637 | 0.9994105431 | 2.589606333e-08 | 114.9972702 |
| 0.008763469828 | 0.08973793103 | -10.31795284 | 10.31795321 | 1.007612582 | 3.551030933e-08 | 114.9787244 |
| 0.008872575431 | 0.09085517241 | -10.44389105 | 10.44389045 | 1.019911235 | 5.73799292e-08 | 114.9509794 |
| 0.009036233836 | 0.09253103448 | -10.63267798 | 10.63267605 | 1.038347459 | 1.810893243e-07 | 114.909317 |
| 0.009270608836 | 0.09493103448 | -10.90307047 | 10.90287636 | 1.064752975 | 1.780304805e-05 | 114.8525403 |

Peak force over this computed primary interval: 10.90307046622248 N; peak nominal stress: 1.064752975217039 MPa. These are not ultimate strength predictions. Nominal stress uses original width*thickness; compression is positive in plots and upper reaction remains negative.

Primary initial-fit result: {'effective_modulus_MPa': None, 'minimum_points': 3, 'points': 2, 'registered_interval': [5e-05, 0.001], 'status': 'INSUFFICIENT_POINTS'}. Preserved platen-only initial reference fit: {'R_squared': 0.9999995892388926, 'effective_modulus_MPa': 117.13641689053354, 'minimum_points': 3, 'normalized_modulus': 0.11713641689053354, 'points': 4, 'registered_interval': [5e-05, 0.001], 'status': 'PRELIMINARY_SINGLE_MESH_THROUGH_ORIGIN_FIT'}. The latter is not silently transferred into a fitted full-GC curve. Secants are pointwise stress/actual strain, not fitted tangent moduli.

Observed-interval loading work: {'limitation': 'Accepted states of this model only, on observed interval; sparse quadrature is not an energy/dissipation convergence study. No origin extrapolation.', 'points': 15, 'status': 'OBSERVED_INTERVAL_TRAPEZOIDAL_ESTIMATE', 'travel_interval_mm': [0.005120000000000001, 0.09493103448275862], 'work_J': 0.0005194930414848452, 'work_N_mm': 0.5194930414848452}. This is numerical trapezoidal work, not validated dissipation/energy absorption. No origin or uncomputed high-strain extension is added.

## Execution and stopping

Displacement-controlled quasi-static pseudo-time, total upperUY=-10.24*engineering_strain mm. Full Newton, line search, AUTOTS, NEQIT=24, force CNVTOL=0.005/norm 2/minimum reference 1e-8; initial increment <=0.0005, maximum 0.005, minimum 1e-6. Sparse DEFAULT memory selection, actual licensed SMP settings recorded in receipts. No fixed RSS cap; system available/committed memory and paging HealthPolicy, 40 GiB free-disk reserve, one native job at a time, original six-hour campaign/90-minute stage/30-minute no-progress bounds. The qualified numerical restart frequency is 1, with three rolling frames; the legacy ALL-frequency retention deviation is explicitly documented. A single same-nodal-model contact-onset recovery used native ENDSTEP at the accepted intermediate frame, then NEQIT=12, initial global increment 5e-5, maximum 2.5e-4 and minimum 1e-6. Its native input, actual outcomes and finite 60-minute bound are recorded under protocol 025. The original nodal 1% trial was deliberately interrupted after oscillation; a predictive native bisection occurred just before the ABT was acknowledged. Its seven converged states remain independently accepted, while SS999999 is debug-only.

New completed fine-mesh substeps across the distinct numerical contact branches: 36; explicit native cutback events: 2; completed Newton updates: 98. Force evaluations are not miscounted as updates. Native source failures/stops: [{'controlled_native_ABT_requested': False, 'job': 'fine_nodal_recovery01_001', 'last_converged': {'load_step': 3, 'pseudo_time': 0.00927061, 'source_line': 3325, 'substep': 6, 'time_increment': 0.000234375}, 'returncode': 15, 'status': 'NO_CONVERGED_PROGRESS_TIMEOUT'}, {'controlled_native_ABT_requested': True, 'job': 'fine_nodal_stage02_001', 'last_converged': {'load_step': 2, 'pseudo_time': 0.00859375, 'source_line': 3834, 'substep': 7, 'time_increment': 0.00253125}, 'returncode': 15, 'status': 'NATIVE_SOLVER_ERROR_OR_DISTORTION'}].

Last valid restart description: fine_nodal_recovery01_001, load step 3/substep 6, strain 0.0092706088362069, frame compression.r001; authenticated RDB/LDHI/Rnnn and native fields in restart_validation/FINAL_VALID_NATIVE_RESTART.json. A readable converged RST field and an available native Rnnn frame are reported separately; no coordinate-only restart is substituted.

## Reference branch

The original platen-only branch is separately preserved through 0.809375% at 10 qualified points. Its1% state has two exact quadratic free-boundary crossings and is excluded. Its retained load-step restart endpoints differ from the intermediate field inventory; see audit 015. Each subsequent full-GC model is a fresh same-fine-mesh model because adding contact topology changes the original restart model.
