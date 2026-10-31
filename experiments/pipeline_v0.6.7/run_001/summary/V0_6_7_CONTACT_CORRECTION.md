# v0.6.7 contact correction

No correction is selected for a full-model retry. Eight small solver processes comprise three invalid setup comparisons, four controlled contact variants and one native iteration-limit recovery. Each addition was registered and committed before execution. The initial limits were prospectively amended for documented extraction defects and one evidence-directed NEQIT recovery; clocks and physical gates were unchanged.

|Actual local variant|Native return|Last converged LS/SS|Printed boundary-load parameter|Native cutbacks|
|---|---:|---|---:|---:|
|local_baseline_003|1|17/16|0.00950498|12|
|local_fkn10_002|15|18/15|0.00953351|8|
|local_fkn1_001|1|18/8|0.00953293|7|
|local_projection3_001|0|19/2|0.01|1|
|local_fkn1_neqit64_001|1|18/9|0.00953395|1|

Nodal target-normal detection with FKN 100, 10 and 1 all develops onset cycling and fails before the complete registered local path. Penalty scaling alone is insufficient. FKN 1's terminal residual decreases from 0.002921 to 0.002628 N against0.002603 N, justifying one bounded64-iteration continuation. It gains LS 18SS9 at native time 0.009533949392187499, then fails LS 18SS10 with residual 0.003722 N against0.002604 N after 64 iterations. No further parameter trial is authorized by the final registered stopping rule.

Standard projection KEYOPT 4=3 is accepted by actual licensed 2024R1 and converges to boundary parameter 0.01. It is rejected mechanically: unexplained quadratic crossings remain, including original faces 28506/27837 and 28505/27838. Native converged contact diagnostics report penetration 1.433883e−6 mm at the endpoint, while endpoint-only sequence outputs are zero. Zero endpoint output does not establish zero penetration at projection integration points. The unchanged direct target-facet/positive-separation checks fail. No enlarged neighborhood or relaxed overlap criterion is introduced.

All independently screened converged TRI6 mappings remain positive. The corrected nodal baseline and the one recovered local state pass force, penetration and native-linked contact geometry checks; they remain local diagnostic states under prescribed cut motion. A valid lower local state does not establish a robust correction through the required onset path.

Force extraction correction: selected contact elements do not represent both sides of this interface. Fresh POST1 sums original structural element force contributions on both localized physical boundary patches and independently checks zero platen contribution there. Equal/opposite force transmission passes the unchanged1% gate. This establishes local transmission, not full-model internal contact or global performance.

Official syntax/context: [CONTA172](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_CONTA172.html), [GCDEF section rules](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_GCDEF.html), [FSUM selected-element scope](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_FSUM.html). These adjacent-release references guide interpretation; actualv241 decks, listings and licensed outputs establish installed behavior.
