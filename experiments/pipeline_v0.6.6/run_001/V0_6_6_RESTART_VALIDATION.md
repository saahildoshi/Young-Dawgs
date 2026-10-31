# v0.6.6 actual restart validation

PASS on two actual licensed ANSYS2024R1 fixtures: accepted rectangle and compliant control. Continuous targets0.0025→0.005 were compared with an independently exited pause at0.0025 and native multiframe restart to0.005. RDB/LDHI/Rnnn/RST files were authenticated and copied into fresh directories; no coordinate-only or imposed-initial-displacement substitute was used.

Rectangle restarted LS1/SS2→LS2/SS2. Compliant restarted LS1/SS3→LS2/SS2. Both load steps were independently reopened, native gates passed, actual total upper displacement matched -height*target and U/S/EPEL/contact/history fields agreed. Maximum column-scaled discrepancy: rectangle6.776e-16; compliant3.305e-7, below prospective1e-5. Exact per-column comparisons and native provenance are in restart_validation/RESTART_VALIDATION.json and per-job evidence.

Two implementation failures remain recorded. An initial continuous deck used FINISH between SOLVEs and reset the subsequent load step; the duplicate time was rejected. The corrected deck stays in SOLU. An early multi-set exporter omitted FILE rebinding after re-entering POST1; it tried readonly.rst and failed. Corrected export explicitly binds the native RST before every SET. Successful source solves were reused in fresh read-only exports; failed evidence was preserved and no gate was relaxed.

Installed-release behavior is established by native execution, not documentation alone. Syntax references from adjacent official ANSYS releases appear in the registered plan. The main fine continuation subsequently reuses the authenticated v0.6.5 LS1/SS1 checkpoint; actual results are reported separately.
## Final v0.6.6 outcome

Scientific status: **PROGRESSIVE_FINE_MESH_RESEARCH_HOLD__TARGET_NOT_REACHED**. Highest independently qualified strain across branches: **0.927060884%**. Highest completed native strain: **1%**; convergence alone does not establish qualification. Primary branch `FINE_FULL_SELF_CONTACT_NODAL_V066_021` is qualified through **0.927060884%**.

Stop reason: The registered 30-minute limit without a new converged state stopped the single bounded contact-onset retry after 3019.84 s. Force residuals kept cycling during the next contact-active trial despite one native bisection. No 1% endpoint passed; 5–40% stages were not executed. This is a numerical contact/control limit under the registered budget, not a demonstrated material-collapse limit.

Thirty percent primary target: NOT REACHED. Forty percent stretch: NOT REACHED. All reported curves stop at actual qualified points. The distinct contact-model branches are never spliced.

Authoritative final branch/gate/resource evidence is in V0_6_6_VALIDATION.md and summary/V0_6_6_VALIDATION.json. Each full-GC model preserves the fine mesh, adds all exposed self-contact skins and remains separate from the original platen-only native restart branch. Actual restart inventories and numerical-frequency correction are preserved in audit 015 and restart_validation/RETENTION_QUALIFICATION.json. Native mid-load-step ENDSTEP and the bounded controller recovery are independently documented in restart_validation/ENDSTEP_CONTROL_QUALIFICATION.json and protocol 025; cumulative loads and required fields passed the actual small-model comparison.
