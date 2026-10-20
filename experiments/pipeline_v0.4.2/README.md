# v0.4.2 — validation-only result index

**Native convergence: all ten pairs pass. Overall scientific acceptance: HOLD
solely because analytic P10 calibration exceeds the predeclared ceiling.**

The generator remains v0.4.1, the frozen evaluator remains v1.1, and historical
results are unchanged. No CAD, mesh, STEP or STL was created.

| Evidence | Result | Location |
|---|---|---|
| Ten fresh 2048 cases | 10/10 topology, percolation, deterministic repeat and latent identity | [Scientific acceptance report](thickness_verification/SCIENTIFIC_ACCEPTANCE.md) |
| Successive mean thickness, 1024→2048 | 1.529–1.867%; 10/10 pass ≤3% | Same report |
| Successive P10 thickness, 1024→2048 | 0–7.805%; 10/10 within retained 10% ceiling | Same report |
| Successive median pore diameter, 1024→2048 | 0.114–0.864%; 10/10 pass ≤3% | Same report |
| Analytic controls | 192 masks; maximum P10 change 12.6681%, exceeding the registered ceiling | [Analytic controls](thickness_verification/ANALYTIC_CONTROLS.md) |
| Endpoint explanation | Thin endpoint population crosses the 10% threshold; no control excluded and no metric changed | [Endpoint audit](control_outlier_audit/ENDPOINT_AUDIT.md) |
| Repaired necks | Inward depths 3/5/9 pixels at 512/1024/2048; zero single-pixel articulations among 365 tested pixels | [Repair inspection data](thickness_verification/repair_inspection.json) |
| Protocol | Criteria recorded before new native 2048 results | [Protocol](thickness_verification/protocol.json) |
| Machine-readable decision | Only P10 control qualification is HOLD | [Summary](thickness_verification/summary.json) |
| Frozen history and regression verification | Independent verification and test logs | [Verification](verification/verification.json) |

The 10/10 native P10 result is conditional on the retained 10% ceiling; it does
**not** override the failed calibration gate. The fixed-geometry control supports
a dominant sampling contribution to mean-thickness drift in all ten cases,
but does not prove zero native geometry-discretization error.

For the full interpretation, limitations, file reference, and Windows commands,
read [the v0.4.2 guide](../../docs/PIPELINE_V0_4_2_THICKNESS.md).
That guide also explains why this is now a measurement-protocol decision,
not a reason to distort the generator or automatically run more resolutions.
