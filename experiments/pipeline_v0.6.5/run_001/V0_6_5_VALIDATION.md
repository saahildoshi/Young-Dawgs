# v0.6.5 scientific validation

Scientific status: **FIRST_ACCEPTED_NATIVE_CHECKPOINT__PRELIMINARY_SINGLE_MESH_RESEARCH_HOLD**. Accepted checkpoints: 1.
Source `4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1`; mesh `e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc`.
Input `bad607c1d0fee99944fdd77a96331c0fd9271e1b6597f60427c03e9884ce5d13`; native RST `8ad26dd081ae2dd42f7a9d6dcec224a9ca8a08f500823e1adc63ed2db3161d14`.

## 1. Previous equilibrium

The v064 full model reached0.005% equilibrium after7updates, but had no
mechanically accepted checkpoint. These historical facts remain unchanged.

## 2. Output failure

The external20GiB guard interrupted native execution. Historical conditional
RST retained displacement only. Exact command-allocation cause is UNRESOLVED.
See V0_6_5_MEMORY_AND_OUTPUT_AUDIT.md.

## 3. Updated memory policy

No process RSS threshold. Sustained6GiB available-memory reserve/30s,
critical1GiB/3s, corroborated commit/Windows notification guards, severe
paging without output growth,20GiB free disk and1800s wall protection.
Recovery resets transient low-memory durations. No unrelated apps/pagefile
settings were changed. Exact policy is frozen in JSON and tested synthetically.

## 4. Actual available memory

Physical 63.7058GiB; before run
40.5872GiB; minimum sampled available
21.9146GiB. Installed RAM was
not assumed to equal currently available RAM.

## 5. Output protocol

Explicit NSOL/RSOL/STRS/EPEL/CONT/MISC LAST, suppressed text/duplicate selected
results, one final restart frame, MODEL-only DB and separate read-only export.
See V0_6_5_OUTPUT_PROTOCOL.md.

## 6. Small licensed verification

Matched full/selective rectangle and compliant solves passed unchanged physical
gates. Repeated native extraction matched exactly. Missing EPEL was correctly
quarantined. The initial overprecise comparison failure is retained in audit002.

## 7. Full execution

One full solve: PROCESS_EXITED, returncode0,
7updates, 0bisections.
No additional strain points or exploratory contact changes.

## 8. Native output

RST 679018496bytes, hash above. File size alone
was never an acceptance gate. Actual result writing and file-growth samples
are recorded in performance/ and native logs.

## 9. Independent read-only validation

Qualification FIRST_ACCEPTED_NATIVE_CHECKPOINT__PRELIMINARY_SINGLE_MESH_RESEARCH_HOLD. Result-set inventory, provenance, native fields,
all node IDs/corner IDs, signed reactions/contact forces and every deformed
TRI6 mapping were checked. Repeated full extraction is independently compared.

## 10. Support reactions

Upper -0.060434415130058N; lower 0.06074445939887244N;
normalized reaction imbalance 0.005104074871727321.

## 11. Platen contact

[{'closed_elements': 773, 'contact_element_force_y_N': -0.060744459394838, 'max_stored_endpoint_penetration_mm': 5.440885e-10, 'max_stored_endpoint_pressure_MPa': 0.32710794, 'minimum_signed_gap_mm': -7.0687194e-05, 'pair': 'bottom', 'pilot_reaction_y_N': 0.06074445939887244, 'signed_opposition_residual_relative': 6.641658332480353e-11, 'total_elements': 1368}, {'closed_elements': 657, 'contact_element_force_y_N': 0.06043441524864, 'max_stored_endpoint_penetration_mm': 2.830074e-10, 'max_stored_endpoint_pressure_MPa': 0.16914761, 'minimum_signed_gap_mm': -2.4550722e-05, 'pair': 'top', 'pilot_reaction_y_N': -0.060434415130058, 'signed_opposition_residual_relative': 1.9621602206461835e-09, 'total_elements': 1230}]
Stored endpoint maxima are not continuous-contact bounds. Internal self-contact
is not configured. No force was inferred from the opposite support.

## 12. Stress and strain

Native supported corner-node SYY/SEQV/EPEL Y/X; 752212nodes.
No midside stress fabrication. All-node UX/UY plus derived displacement magnitude
and deformed coordinates are preserved with artifact hashes.

## 13. Stress–strain measurement

Achieved strain 5.0000000000000016e-05; nominal stress
0.005901798352544726MPa. One measurement is not a curve.
Secant 118.03596705089448MPa is separately labeled;
no fitted modulus is justified.

## 14. Runtime and memory

327.063s; peak18.5923GiB;
maximum commit fraction0.7012224746292272; Windows low-memory
samples0. System hard-fault disk-read
proxy maximum282.1218050191998; native paging counters
cannot attribute every hard fault to pagefile-only I/O.

## 15. Limitations

Single mesh/limited loading, mechanical mesh convergence UNQUALIFIED, internal
self-contact UNQUALIFIED_NOT_CONFIGURED. E1000MPa,nu0.3,scale/thickness,plane
stress and homogeneous elasticity remain provisional and uncalibrated. Prior
small-pore fidelity, production simplification and historical repair HOLDs
remain. No yielding/fracture, paper or manufacturing qualification is claimed.

## 16. Scientific acceptance and tests

| Category | Status |
|---|---|
| MEMORY_POLICY_UPDATED | PASS_NO_PROCESS_RSS_CAP |
| SYSTEM_RESOURCE_MONITORING | PASS_ACTUAL_WINDOWS_SIGNALS |
| MINIMAL_OUTPUT_PROTOCOL_VERIFIED | PASS_ACTUAL_LICENSED_V241 |
| HISTORICAL_GEOMETRY_INTEGRITY | PASS_UNCHANGED_SOURCE_AND_MESH |
| NONLINEAR_EQUILIBRIUM | PASS_NATIVE |
| NATIVE_OUTPUT_COMPLETE | PASS_INDEPENDENT_RST_REOPEN_AND_REQUIRED_FIELDS |
| INDEPENDENT_REACTION_BALANCE | PASS |
| PLATEN_CONTACT_FORCE | PASS |
| STRESS_STRAIN_FIELDS | PASS_NATIVE_SUPPORTED_CORNER_AVERAGES |
| MICROSTRUCTURE_MECHANICAL_CHECKPOINT | PASS_ONE_NONZERO_CHECKPOINT |
| STRESS_STRAIN_CURVE | UNQUALIFIED_ONE_POINT |
| EFFECTIVE_MODULUS | FIT_UNQUALIFIED; SECANT_SEPARATELY_LABELED |
| MECHANICAL_MESH_CONVERGENCE | UNQUALIFIED |
| INTERNAL_SELF_CONTACT | UNQUALIFIED_NOT_CONFIGURED |
| PAPER_READINESS | RESEARCH_HOLD |
| LLM_OPTIMIZATION | NOT_IMPLEMENTED |

Active 784passed/0failed; archived
475passed separately; licensed20passed/
0failed. Counts overlap and are not summed. Synthetic
monitor/parser tests are distinct from real licensed evidence. Protected
historical experiments, generators and evaluator remain unchanged.

## 17. Git commits

Started clean on master at `0de6cd7c77652ad0d265200881642cd0d228a047`. No push or history rewrite.

- `c4a49487b407115dd11b89a447d29935a7699628` — docs(ansys): register v0.6.5 memory and output qualification protocol
- `754ee9b3890d582a75acfa081abda7da0e688df5` — fix(ansys): replace fixed RSS cap with sustained system-health supervision
- `12503481770cbdd2d80362f496a9e610d850e56e` — feat(ansys): preserve selective native records with bounded read-only field exports
- `858cfe3ca36d58a4ad51caf4c15794aee69308f0` — test(ansys): qualify selective output and independent native field recovery
- `b141e0a10fc408beaf67dc2f64e59206e1f5df08` — docs(ansys): freeze uncapped system-health recovery at known 0.005 percent checkpoint
- `3c7c5c29adb3b565f110e4bcf64cb0847c2c5f3c` — feat(fem): accept first native microstructure compression checkpoint

The containing final reporting commit is identified in Git history/final response.

## 18. Next-stage handoff

Repeat the accepted checkpoint, then prospectively qualify contact/output sensitivity and mechanical mesh convergence before a small additional strain point. No automatic multi-point campaign.
No batch FEM,3D,LLM optimization or manufacturing work was implemented.

Actual figures and hashes are in figures/figure_manifest.json. Full binary
artifacts remain external; execution/replay instructions are in
docs/pipeline_v0.6.5/WINDOWS_EXECUTION.md.

- [Undeformed and true-scale deformed boundaries](figures/geometry_and_deformation.png)
- [Displacement fields](figures/displacement_fields.png)
- [Native continuum stress](figures/continuum_stress.png)
- [Native elastic strain](figures/elastic_strain.png)
- [Contact status, pressure, gap and penetration](figures/contact_results.png)
- [Signed reactions and first measurement](figures/reaction_and_first_measurement.png)
- [Actual system resources](figures/system_resources.png)
- [Output writing and convergence](figures/native_output_timeline.png)
