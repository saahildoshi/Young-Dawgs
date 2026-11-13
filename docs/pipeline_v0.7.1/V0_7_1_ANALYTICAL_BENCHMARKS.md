# Licensed analytical qualification

The actual ANSYS2024R1 homogeneous control passed all registered checks. Fitted modulus=1000.0000000000126MPa (analytical1000MPa), with five native0.1–0.5% checkpoints. Final force is5N and elastic energy0.0125Nmm within registered tolerance. Reactions balance, horizontal pin force is negligible, Poisson lateral displacement and plane-stress constitutive fields agree. Two separate native read-only processes reopened the original RST; repeated common exports match exactly. The second export also corroborates every native quadrilateral connectivity entry.

Native ETLIST reports PLANE182 plane-stress, KEYOPT(1)=0, KEYOPT(3)=3, KEYOPT(6)=0; RLIST gives thickness1. Both installed material definitions match the intended inputs. No installed R1 element manual was available; the adjacent-release official manual was checked and the actual R1 settings/behavior verified natively. Layered and equal-material controls follow; no actual contrast-10 P3 mechanics has been accepted yet.

A Python boolean serialization defect occurred after successful solve/readback. It was corrected and preserved in verification/SERIALIZATION_DIAGNOSTIC.json; qualification reused native evidence without rerunning or altering the solver result.
