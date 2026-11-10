# v0.6.10 protocol and disposition

The highest independently accepted crop compression remains **1.2575%**, at 0.032192 mm top-platen travel, with upper/lower reactions −3.790084913840559/+3.790084911690149 N and nominal compression stress 1.4805019194689684 MPa. This is a new forward-contact E1000 reference run that reproduces the historical maximum; it does not extend it. **30% and 40% crop compression were not achieved.**

The illustrative polymer coupon passed through 40%. No polymer crop source solve was launched because neither registered contact candidate passed the 1.2675% onset gate. The finite campaign stopped at its two-candidate limit with machine time remaining. Local-fixture parent matching did not block either direct crop trial.

Registration: `protocol/PROTOCOL.json`, 2026-11-10T18:12:43.557895Z; request SHA256 `9f01d756da98de0fa3e7d0b7f1485604357127228ed6772104d08a3f51ccb247`; starting HEAD `3fda931f857730e2abef04cfd5f04ef08378f7fb`. Sole structural specimen: authenticated central256 crop, [384,384,640,640], 2.56 × 2.56 mm, 1 mm reference thickness, one connected solid, 19 pores, raster solid fraction 0.491256713867188. The preserved boundary-conforming mesh has 174746 nodes and 79678 TRI6 elements. No original full-specimen source solve was performed.

Prospective limits: 12 hours campaign time, 5400 s source stage, 1200 s without converged progress, one native process, 80 GiB free-disk reserve, system-health supervision, no arbitrary RSS cap. Each native launch uses a unique path-derived job ID. Internal `compression` filenames remain isolated by directory for native restart compatibility. No material, geometry, mesh, friction or force/penetration gate was silently changed.

Gates: upper/lower reaction imbalance ≤1%; independent opposing contact-force imbalance ≤1%; native endpoint penetration ≤5e−5 mm; positive analytic deformed TRI6 maps; no unexplained quadratic-boundary crossing; complete authenticated native histories and fields. The supplementary continuous selected-arc depth certificate uses ≤5e−6 mm source arclength spacing, ≤1e−8 mm target chord error, a Lipschitz sampling margin and artificial-cut clearance. It cannot override a pressure-bearing native contact failure. `_mechanical_qualification.json` is the final continuation authority.

Candidate 1 extended both contiguous arcs by six original faces at each end. After its coarse solve failed reaction accuracy, one registered fresh accuracy retry tightened CNVTOL,F from 0.005 to 0.00001 and precontact increments, without changing physical contact. A separate registered technical supervisor correction lets ANSYS handle recoverable trial errors and cutbacks; fatal errors, stall, health, disk and clock limits remain active. The shared monitor defaults retain historical behavior.

Candidate 2 was initially tentative symmetric two-pass contact. Before execution, `CANDIDATE_002_REVERSED_ROLES.json` explicitly replaced it with a single reversed pair to isolate directional assignment and avoid simultaneous redundant constraints. Both physical candidates used the actual crop; no truncated local parent-match prerequisite applied.

`POLYMER_ENTRY_GATE_001.json` prospectively required an uninterrupted accepted E1000 prefix through 1.2675%. A fresh unloaded polymer database, separately defined material and independent polymer path were required after that gate. No material-incompatible restart is permitted. Planned polymer targets were 0.5%,1%,1.5%,2%,5%,10%,15%,20%,25%,30%,35%,40%. Those polymer crop targets were not executed.

| E1000 source | Native states | Native maximum | Accepted prefix states | Accepted maximum | First rejection |
|---|---:|---:|---:|---:|---:|
| `track_B_pair5_arc_trial_001` | 34 | 1.18106% | 0 | none | 0.05000% |
| `track_B_pair5_arc_strict_001` | 91 | 1.50000% | 62 | 1.2575000% | 1.26083% |
| `reverse/track_B_pair5_arc_trial_001` | 94 | 1.46232% | 47 | 1.1545455% | 1.15909% |

Final disposition: `HOLD_CONTACT_ONSET__POLYMER_CROP_NOT_EXECUTED__THIRTY_PERCENT_NOT_ACHIEVED`. `protocol/CAMPAIGN_STOP.json` records the exhausted candidate budget and preserved failures. No acceptance threshold was relaxed. Read-only final extraction and verification continued after the source-study stop.

All experiment links below are relative to `experiments/pipeline_v0.6.10/run_001/`. Raw licensed files are retained under `C:\Users\sd22446\AppData\Local\YoungDawgs\artifacts\solver\v0610`. Hashes bind the local raw artifacts; source RSTs and databases are intentionally outside Git.
