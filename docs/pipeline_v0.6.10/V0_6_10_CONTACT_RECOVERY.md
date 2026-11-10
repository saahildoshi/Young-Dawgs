# Registered contact recovery

No contact correction was selected for polymer crop production. Both licensed candidates were supported sufficiently to build native inventories and run actual E1000 crop sources, but neither supplied an accepted path through the 1.2675% barrier.

| E1000 source | Native states | Native maximum | Accepted prefix states | Accepted maximum | First rejection |
|---|---:|---:|---:|---:|---:|
| `track_B_pair5_arc_trial_001` | 34 | 1.18106% | 0 | none | 0.05000% |
| `track_B_pair5_arc_strict_001` | 91 | 1.50000% | 62 | 1.2575000% | 1.26083% |
| `reverse/track_B_pair5_arc_trial_001` | 94 | 1.46232% | 47 | 1.1545455% | 1.15909% |

All three source attempts start from the unloaded authenticated crop. Geometry, TRI6 mesh, E=1000 MPa,ν=0.3, friction0, unified CONTA172 KEYOPT(4)=5, selected-pair FKN10 and general-contact FKN100 remain fixed. Candidate1 uses source24,target22,GC15362. Candidate2 exchanges source/target roles to22/24 while retaining the same physical partition. Native setup/ETLIST/RLIST/GCDEF and exact oriented topologies are retained under the relevant `track_B_contact_fixture/` and `native_results/` directories.

The coarse candidate1 has no accepted prefix because its first 0.05% state has about1.32% reaction imbalance. It converges34 states to1.18106%, then a trial distortion of element36599 triggers the historical error-stop supervisor while ANSYS is attempting a bisection. This is preserved as an interrupted attempt, not proof that native adaptive cutback could not recover. The separately registered strict accuracy retry and supervisor correction are technical controls, not a third physical contact candidate.

The strict forward source reaches native1.5% with91 states,62 accepted fromzero to1.2575%. Later convergence does not repair the first unsupported crossing at1.260833333%. The reversed source has94 native states but only47 accepted in the uninterrupted prefix to1.154545455%. The first crossing at1.159090909% carries no selected-pair pressure. Its native failure near1.4624% is separately recorded. All outputs, failed native states and nonlinear telemetry are retained outside Git, with compact evidence and hashes versioned.

Independent opposing structural patch-force scans cover all saved native states for each attempt. Endpoint status/pressure/penetration and pressure-bearing target IDs are checked alongside physical boundary evidence. At1.2575% the forward force proof passes, two selected source faces are closed and maximum endpoint penetration is8.539264e−7 mm. Correct opening remains representable: open faces genuinely have native status0/1, and no artificial tie was imposed. This does not establish successful separation after a high-strain contact cycle; no unloading cycle was run.

No general-contact pore skin closes in any of these accepted prefixes. General contact is configured and its exact coverage verified; pore-contact force transfer at large strain remains untested. No internally closed pair is inferred from an empty native contact field file.

The final `_mechanical_qualification.json` combines native pressure/force/whole-boundary qualification with the additional continuous selected-arc certificate. Both are required. Failed states are never used to authorize continuation, a material change or a restart. No further parameter sweep was performed after exhausting the two registered physical candidates.
