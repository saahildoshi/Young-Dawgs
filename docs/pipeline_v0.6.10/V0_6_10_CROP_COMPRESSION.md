# Actual crop compression

The highest independently accepted crop compression remains **1.2575%**, at 0.032192 mm top-platen travel, with upper/lower reactions −3.790084913840559/+3.790084911690149 N and nominal compression stress 1.4805019194689684 MPa. This is a new forward-contact E1000 reference run that reproduces the historical maximum; it does not extend it. **30% and 40% crop compression were not achieved.**

The illustrative polymer coupon passed through 40%. No polymer crop source solve was launched because neither registered contact candidate passed the 1.2675% onset gate. The finite campaign stopped at its two-candidate limit with machine time remaining. Local-fixture parent matching did not block either direct crop trial.

| E1000 source | Native states | Native maximum | Accepted prefix states | Accepted maximum | First rejection |
|---|---:|---:|---:|---:|---:|
| `track_B_pair5_arc_trial_001` | 34 | 1.18106% | 0 | none | 0.05000% |
| `track_B_pair5_arc_strict_001` | 91 | 1.50000% | 62 | 1.2575000% | 1.26083% |
| `reverse/track_B_pair5_arc_trial_001` | 94 | 1.46232% | 47 | 1.1545455% | 1.15909% |

The actual static loading uses NLGEOM, sparse direct solution, full Newton, line search, adaptive substeps,40 Newton iterations per trial, all native output at every converged substep and NLOAD for structural-force proof. Source targets are0.5%,1%,1.15%,1.2%,1.2575%,1.2675%,1.5%. Strict sources use CNVTOL,F=0.00001, initial precontact strain step0.0001,max0.0005; near onset initial0.00005,max0.0001,min1e−6. These are pseudo-time strain targets, not measured strain rates. Rigid frictionless platens impose top UY=−2.56ε; the original support/control-node scheme is unchanged.

There are219 native saved crop states across the three separate attempts. The forward strict accepted prefix contains62 states; the reverse accepted prefix47. They are separate contact-branch results and cannot be concatenated. The coarse prefix has zero accepted states. Parsed native cutback events: coarse1,strict0,reverse10. The reverse source exits at minimum increment near1.4624% after its94th converged state; all later failed iterations are diagnostics. No native1.5% state is mechanically accepted.

`mechanical_response/ALL_NATIVE_CHECKPOINTS.csv` has every native checkpoint, material/contact identity, exact independently extracted strain where qualified, travel, reactions, nominal stress, equilibrium/contact/mesh quantities, rejection reason and source/input/mesh/proof hashes. A blank mechanical quantity means it was not promoted by qualification; it is not an invented zero. `BRANCH_SUMMARY.json` records continuous path lengths. Raw all-state POST1 CSVs remain in the corresponding source `_post1_all_v2` directory.

At the last accepted forward state nominal stress is |upper reaction|/(2.56mm×1mm), engineering compression is |top UY|/2.56mm. This nominal stress is not the average native Cauchy SYY. The fitted initial loading slope is119.82004470 MPa over0.0100%–0.5%; it is an apparent finite-crop branch slope, not the constituent E. The trapezoidal loading-work density from0.01% to1.2575% is0.0093904110 MJ/m³. No unmeasured zero-to-first increment is filled. There is no unloading/hysteresis measurement and no defensible plateau/densification/collapse strain from this short trajectory.

The historical accepted1.2% restart was authenticated, but all new sources are fresh unloaded solves. **Zero genuine restarts occurred.** The strict accepted1.2575% result can be independently read at LS5/SS8; the full source contains later rejected states and is not approved as an all-valid restart parent. No polymer branch changes an E1000 nonlinear restart. The optional polymer infrastructure remains gated and unexecuted.
