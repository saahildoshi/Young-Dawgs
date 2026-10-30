# v0.6.6 mesh strategy

Selected primary: unchanged qualified historical fine mesh,2,766,505nodes and1,261,670TRI6 elements. The minimum angle is11.404135deg, above frozen10deg; all412pores, registered area/topology/boundary checks and original quadratic mappings are preserved. Actual registered sampled solid-chord rule is>=3 elements; the fine mesh observed minimum is7. These are explicitly distinguished.

One prospective exact-source candidate used boundary size0.005mm,bulk0.06mm with the existing POLICY_B, Gmsh4.15. It generated1,383,233nodes and610,630TRI6 in48.39s. Original angle gate FAILED:8.3031647757deg<10deg. It is rejected, not an accepted reuse of a historical8.303deg mesh. Full quality/features/configuration/hash evidence is in mesh_strategy/candidate_001.json.

The candidate has2.066times fewer elements. This is only an inventory reduction, not demonstrated licensed solver speed or qualified computational advantage. No mechanics benchmark was run on the rejected mesh, no accepted coarse/fine sensitivity study exists and mechanical mesh convergence remains UNQUALIFIED. The fine native restart is retained to preserve model identity and a real accepted parent. No canonical source, generator, pore, neck or gate was changed.
