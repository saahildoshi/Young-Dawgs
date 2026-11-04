# Pipeline v0.6.8 — scientific validation

## A. Executive summary

The original full Design 9/seed 1 specimen (Track A) retains its historical independently accepted maximum of **0.9270608836206897%**. A better local contact fixture and native unified detection did not pass the fixed full-parent comparison, so no full retry was justified. The separate central-crop specimen (Track B) was solved progressively with licensed ANSYS. Its highest native converged state is **1.5%**, while its highest continuously independently accepted saved state is **1.2575%**. The 30%/40% targets and even 5% were not reached. This is a bounded failed large-strain attempt with valid early mechanical data, not a 30–40% demonstration.

## B. Historical context

The original 1024-pixel Design 9/seed 1 source WKB SHA-256 is `4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1`. Its 15-point accepted full response ends at load step 3/substep 6, engineering strain 0.009270608836206897 and travel 0.09493103448275862 mm. Earlier platen-only and Gauss-contact 1% states remain rejected. The authenticated full fine mesh and restart were preserved without modification.

## C. Track A localization

The original upper exterior hotspot includes boundary indices 27837, 27838, 28504–28506 and residual nodes 98184, 99405, 99399 and 4990. The expanded original-mesh local fixture has 12,228 nodes, 5,544 TRI6 elements, 1,095 physical faces and 43 artificial cut faces. All 89 cut nodes have 15 measured parent displacement histories. Earliest measured states still show approximately 88% core SYY RMS error against the full model, despite good later-state displacement agreement. The sampled near-gap changes under local cropping; its exact quadratic certificate is retained separately.

## D. Contact algorithm qualification

ANSYS 2024 R1 installed CONTA172 unified detection KEYOPT(4)=5 in the connected small fixture, the original-mesh local case and the selected crop's deformable pair. Both original-mesh local variants passed native two-sided structural-force readback at their engaged saved states. The selected crop's localized pair replaced exactly 22 native general-contact skins while retaining 15,386 others; the corrected face inventory has no duplicate or omitted physical face. Its 1.2575% selected pair has two closed source skins, maximum 18.0355 MPa pressure and 9.6554×10⁻⁷ mm endpoint penetration below the registered 5×10⁻⁵ mm crop limit. Independent signed force transfer passes. Native pressure alone was never treated as sufficient proof.

## E. Track A correction

The nodal local case stopped near 0.968875%; the unified case converged to a hypothetical local 1%. Both fail the prospectively fixed early parent-field comparison. Neither is a qualified original full correction. A full restart compatibility claim was therefore not made.

## F. Track A full-specimen result

No new full solve was launched. The maximum accepted full-specimen strain remains **0.9270608836206897%**, with the preserved load-step-3/substep-6 native restart. There is no accepted full 1%, 5%, 10%, 20%, 30% or 40% state in this milestone.

## G. Track B specimen

The prospectively selected central [384,384,640,640] source-pixel crop measures 2.56 × 2.56 mm, has area 3.2195 mm², 49.125671% solid fraction, 19 enclosed pores and one connected load-bearing solid. Its independent mesh has 174,746 nodes, 79,678 quadratic TRI6 elements and 15,408 physical boundary faces. Reference mapping, topology and geometry-quality gates pass. The model uses plane stress, 1 mm thickness, assumed E = 1000 MPa and ν = 0.3, NLGEOM, frictionless rigid platens, and deformable general plus selected pair contact. Mechanical mesh convergence and material calibration have not been demonstrated.

## H. Track B compression

Fresh and restart-based native nonlinear solves reached complete accepted unified-pair stages at 0.5%, 1%, 1.1%, 1.15% and 1.2%. The next 1.5% stage converged through 32 saved substeps. Independent all-state readback accepts only substeps 1–7, ending at **1.2575%**. Substep 8 at 1.2675% has an opened contact skin at a crossed selected arc; subsequent substeps remain rejected. The last complete valid restart stage is 1.2%; the 1.2575% state is a validated saved result in a failed continuation. No invalid state was used to initiate a further stage.

## I. Mechanical response

The accepted unified-pair curve has 12 native points in [CSV](../figures/TRACK_B_ACCEPTED_RESPONSE.csv), including seven saved substeps beyond 1.2%. At 1.2575%, imposed travel is 0.032192 mm, upper/lower platen reactions are −3.7900865216/+3.7900865393 N, and nominal stress based on gross 2.56 mm width and assumed 1 mm thickness is 1.48050255 MPa. The observed accepted force and nominal-stress maxima occur at this endpoint. The original full-specimen 15-point response is separate and has not been spliced into these plots.

## J. Deformation

The selected accepted state has all 174,746 native displacement vectors, all 47,525 corner-node stress/elastic-strain records, and a true-scale deformed-boundary image. Maximum nodal displacement magnitude is 0.0428179 mm; native equivalent-stress maximum is 73.8017 MPa and minimum elastic EYY is −0.0553843. These local extrema do not diagnose failure of the provisional elastic material. The 19 pore loops are tracked, but no internal general-contact skin is closed at the accepted maximum. No complete pore closure, buckling or collapse is established.

## K. Numerical validity

At 1.2575%, independent upper/lower reaction imbalance is 4.66×10⁻⁹. Signed platen contact forces and the local pair's opposing structural patch forces pass fixed 1% checks; pair penetration passes its fixed 5×10⁻⁵ mm gate. All 79,678 analytic deformed TRI6 mappings are positive. The two exterior-arc screen flags at the accepted state are explained by closed pressure-bearing selected pair skins. At 1.2675%, the analogous crossing loses its native pressure-bearing pair and is rejected, even though the later solver states converge. Full original contact uses a stricter 10⁻⁵ mm penetration requirement.

## L. Scientific limitations

The crop has different boundaries and morphology from the full structure. Its E and ν are assumptions, the model is 2D plane stress with 1 mm assumed thickness, and nonlinear elastic behavior has no experimental calibration. Neither mechanical mesh sensitivity nor a reliable high-compression contact formulation was established. The early curve cannot be extrapolated to 30–40%, used as original full-specimen behavior, or treated as paper-ready constitutive evidence.

## M. Performance

The observed v0.6.8 ledger records **28 native source-solve processes**, **19 genuine restart-continuation processes**, **38 read-only POST1 processes**, and **70 total native processes**. Source-solve wall times sum to 2777.786 s; all native-process wall times sum to 3156.816 s. Peak sampled process-tree RSS was 3.473 GiB; the minimum sampled free physical RAM was 35.38 GiB. Maximum sampled page reads were 4273.22/s, with no sustained severe paging in the receipts. Retained raw artifact usage is 44,453,512,091 bytes (41.40 GiB), including copied restart/result files. These are process samples and artifact totals, not a full-system peak-memory measurement.

## N. Reproducibility

The [registered protocols](../protocol), [crop geometry/mesh receipts](../track_B_geometry/GEOMETRY_001.json), [exact pair setup](../track_B_contact_fixture/PAIR_UNIFIED5_SETUP_QUALIFICATION.json), [native source receipts](../track_B_native_results), [all-state POST1 qualification](../track_B_progressive_compression/track_B_pair5_to_01500_001_qualification.json), [native opposing-force scan](../track_B_contact_fixture/track_B_pair5_to_01500_001_pair_force_scan.json), [figures and CSV hash inventory](../figures/FIGURE_INVENTORY.json), and [resource ledger](../performance/PERFORMANCE.json) bind each conclusion to versioned data and native files. Large solver databases stay outside Git under `C:\Users\sd22446\AppData\Local\YoungDawgs\artifacts\solver\v068`.

Verification completed with **799 active tests**, **475 archived replay checks across nine groups**, and **140 licensed-artifact checks** (131 inherited v0.6.6/0.6.7 checks plus nine new v0.6.8 checks). These are overlapping check categories, not 1,414 different native simulations.

## O. Git history

Changes were committed after coherent implementation and evidence phases. The full hashes and messages through the final reporting phase are listed in the [handoff](V0_6_8_HANDOFF.md) and the final response. No push was made. Historical source files and previously rejected results were preserved.

## P. Next milestone

Track A needs a parent-matched local model across its earliest measured states before any full fine-mesh retry. Track B needs a prospectively registered contact formulation that maintains pressure-bearing opposing surfaces through the 1.2675% opening event, followed by independent all-state checks, material calibration, and mechanical mesh sensitivity before 30–40% claims or LLM mechanical-feedback iteration. This milestone stops at the demonstrated contact-validity bound; it does not start 3D, manufacturing, batch design, or autonomous optimization work.
