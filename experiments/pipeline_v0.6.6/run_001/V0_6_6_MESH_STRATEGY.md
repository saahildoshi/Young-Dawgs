# v0.6.6 mesh strategy

Selected primary: unchanged qualified historical fine mesh,2,766,505nodes and1,261,670TRI6 elements. The minimum angle is11.404135deg, above frozen10deg; all412pores, registered area/topology/boundary checks and original quadratic mappings are preserved. Actual registered sampled solid-chord rule is>=3 elements; the fine mesh observed minimum is7. These are explicitly distinguished.

One prospective exact-source candidate used boundary size0.005mm,bulk0.06mm with the existing POLICY_B, Gmsh4.15. It generated1,383,233nodes and610,630TRI6 in48.39s. Original angle gate FAILED:8.3031647757deg<10deg. It is rejected, not an accepted reuse of a historical8.303deg mesh. Full quality/features/configuration/hash evidence is in mesh_strategy/candidate_001.json.

The candidate has2.066times fewer elements. This is only an inventory reduction, not demonstrated licensed solver speed or qualified computational advantage. No mechanics benchmark was run on the rejected mesh, no accepted coarse/fine sensitivity study exists and mechanical mesh convergence remains UNQUALIFIED. The fine native restart is retained to preserve model identity and a real accepted parent. No canonical source, generator, pore, neck or gate was changed.
## Final v0.6.6 outcome

Scientific status: **PROGRESSIVE_FINE_MESH_RESEARCH_HOLD__TARGET_NOT_REACHED**. Highest independently qualified strain across branches: **0.927060884%**. Highest completed native strain: **1%**; convergence alone does not establish qualification. Primary branch `FINE_FULL_SELF_CONTACT_NODAL_V066_021` is qualified through **0.927060884%**.

Stop reason: The registered 30-minute limit without a new converged state stopped the single bounded contact-onset retry after 3019.84 s. Force residuals kept cycling during the next contact-active trial despite one native bisection. No 1% endpoint passed; 5–40% stages were not executed. This is a numerical contact/control limit under the registered budget, not a demonstrated material-collapse limit.

Thirty percent primary target: NOT REACHED. Forty percent stretch: NOT REACHED. All reported curves stop at actual qualified points. The distinct contact-model branches are never spliced.

Authoritative final branch/gate/resource evidence is in V0_6_6_VALIDATION.md and summary/V0_6_6_VALIDATION.json. Each full-GC model preserves the fine mesh, adds all exposed self-contact skins and remains separate from the original platen-only native restart branch. Actual restart inventories and numerical-frequency correction are preserved in audit 015 and restart_validation/RETENTION_QUALIFICATION.json. Native mid-load-step ENDSTEP and the bounded controller recovery are independently documented in restart_validation/ENDSTEP_CONTROL_QUALIFICATION.json and protocol 025; cumulative loads and required fields passed the actual small-model comparison.
