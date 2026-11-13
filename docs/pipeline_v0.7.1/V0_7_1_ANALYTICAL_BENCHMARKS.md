# Licensed analytical qualification

The actual ANSYS2024R1 homogeneous control passed all registered checks. Fitted modulus=1000.0000000000126MPa (analytical1000MPa), with five native0.1â€“0.5% checkpoints. Final force is5N and elastic energy0.0125Nmm within registered tolerance. Reactions balance, horizontal pin force is negligible, Poisson lateral displacement and plane-stress constitutive fields agree. Two separate native read-only processes reopened the original RST; repeated common exports match exactly. The second export also corroborates every native quadrilateral connectivity entry.

Native ETLIST reports PLANE182 plane-stress, KEYOPT(1)=0, KEYOPT(3)=3, KEYOPT(6)=0; RLIST gives thickness1. Both installed material definitions match the intended inputs. No installed R1 element manual was available; the adjacent-release official manual was checked and the actual R1 settings/behavior verified natively. Both layered controls and the recovered equal-material P3 control now pass. No actual contrast-10 P3 mechanics has been accepted yet.

A Python boolean serialization defect occurred after successful solve/readback. It was corrected and preserved in verification/SERIALIZATION_DIAGNOSTIC.json; qualification reused native evidence without rerunning or altering the solver result.

| Control | Analytical E (MPa) | Native fitted E (MPa) | Accepted |
|---|---:|---:|---|
| M0_matrix attempt1 | 1000 | 1000 | PASS |
| M1_parallel attempt1 | 5500 | 5499.99999992 | PASS |
| M1_series attempt1 | 1818.18182 | 1818.18181797 | PASS |
| M1_equal attempt2 | 1000 | 999.999999999 | PASS |

The first equal-material P3 attempt failed mechanical qualification despite native process completion. Default coordinate-selection tolerance selected three constrained y rows instead of two (771 UY constraints versus514). The corrected mesh writer selects exact node-ID ranges, and native DLIST inventory must now match every intended boundary constraint. Attempt002 passed at999.999999999MPa. Every failed input, native result, export and qualification is retained; no tolerance, morphology or material was changed to obtain acceptance.
