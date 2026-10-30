# v0.6.6 actual restart validation

PASS on two actual licensed ANSYS2024R1 fixtures: accepted rectangle and compliant control. Continuous targets0.0025→0.005 were compared with an independently exited pause at0.0025 and native multiframe restart to0.005. RDB/LDHI/Rnnn/RST files were authenticated and copied into fresh directories; no coordinate-only or imposed-initial-displacement substitute was used.

Rectangle restarted LS1/SS2→LS2/SS2. Compliant restarted LS1/SS3→LS2/SS2. Both load steps were independently reopened, native gates passed, actual total upper displacement matched -height*target and U/S/EPEL/contact/history fields agreed. Maximum column-scaled discrepancy: rectangle6.776e-16; compliant3.305e-7, below prospective1e-5. Exact per-column comparisons and native provenance are in restart_validation/RESTART_VALIDATION.json and per-job evidence.

Two implementation failures remain recorded. An initial continuous deck used FINISH between SOLVEs and reset the subsequent load step; the duplicate time was rejected. The corrected deck stays in SOLU. An early multi-set exporter omitted FILE rebinding after re-entering POST1; it tried readonly.rst and failed. Corrected export explicitly binds the native RST before every SET. Successful source solves were reused in fresh read-only exports; failed evidence was preserved and no gate was relaxed.

Installed-release behavior is established by native execution, not documentation alone. Syntax references from adjacent official ANSYS releases appear in the registered plan. The main fine continuation subsequently reuses the authenticated v0.6.5 LS1/SS1 checkpoint; actual results are reported separately.
