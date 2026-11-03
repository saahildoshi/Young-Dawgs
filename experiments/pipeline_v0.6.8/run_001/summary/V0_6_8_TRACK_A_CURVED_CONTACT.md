# v0.6.8 Track A — curved-surface contact on the original fine specimen

The original full specimen remains the Design 9, seed 1, 1024-pixel fine TRI6 model. Its authenticated last accepted native restart is load step 3, substep 6 at **0.9270608836206897% engineering compression**. The earlier platen-only and Gauss-contact 1% states remain rejected. This document describes original-mesh **local diagnostics**, not additional full-specimen compression.

The v0.6.8 fixture retains 5,544 original fine TRI6 elements, 12,228 original nodes, 1,095 physical faces and 43 artificial cut faces in the preselected centroid window [1.55, 2.40] × [9.75, 10.24] mm. All 89 cut nodes receive the 15 measured, independently stored full-parent displacement histories. Generated contact skins on artificial cuts are deleted. The physical-face native topology was independently checked against the source mesh.

The implicated original exterior faces are boundary indices 27837, 27838, 28504, 28505 and 28506, near original x ≈ 1.97 mm and y ≈ 10.22 mm. The earlier native residual study identified nodes 98184, 99405, 99399 and 4990 and a near-endpoint contact switch. See the archived [v0.6.7 forensics](../../../pipeline_v0.6.7/run_001/summary/V0_6_7_CONTACT_ONSET_FORENSICS.md) and the present [expanded extraction](../track_A_local_fixture/SOURCE_EXTRACTION.json).

Both licensed local cases preserve the original plane-stress PLANE183 material, rigid top platen, and general-contact physical-face scope. The nodal baseline uses KEYOPT(4)=2; the alternative uses native-verified unified detection KEYOPT(4)=5. The installed v241 option inventory and small compliant unified-contact fixture verify that this is an available release option. No penalty-only sweep was repeated.

| Expanded local case | Native outcome | Last local time | Parent match | Complete local mechanical gate |
|---|---|---:|---|---|
| Original nodal detection | Solver stopped during load step 18 | 0.968875% approximately | Fails at first three measured states | Hold: engaged interface force proof pending |
| Unified detection | Native solve completed local 1% target | 1.000000% | Fails at first three measured states | Hold: engaged interface force proof pending |

At the final measured parent state (load step 15), the expanded nodal fixture has a core displacement RMS relative error of 1.26×10⁻⁶, and the unified fixture 1.22×10⁻⁶. Their first measured state instead has about 1.94% displacement RMS error and roughly 88% SYY RMS error. The second and third measured states also fail the **prospectively fixed** 2% displacement/10% stress–strain parent gate; load steps 4–15 pass. Exact cut displacement agreement alone does not repair the early stress mismatch.

The two preidentified original-face pairs have their geometric near-gap compared in [nodal](../track_A_local_fixture/track_A_expanded_nodal2_001_nanogap.json) and [unified](../track_A_local_fixture/track_A_expanded_unified5_001_nanogap.json) records. For pair 27837/28505, the parent’s 1,000-segment sampled distance is about 6.33×10⁻¹⁰ mm; the nodal local distance is about 1.27×10⁻⁹ mm, while the unified local sampling reaches zero. These sampled distances are **not** rigorous physical gap measurements. The separate conservative quadratic certificates and signed local-minus-parent differences are recorded so that the nanogap mismatch is not hidden by the good bulk-field match.

The local fixtures change global compliance and contact onset. Their native convergence and native contact activity cannot be promoted to the original full model. The exact parent-match and two-sided-force entry gate is not met. All original full-specimen results therefore remain on HOLD at the authenticated 0.9270608836206897% state.
