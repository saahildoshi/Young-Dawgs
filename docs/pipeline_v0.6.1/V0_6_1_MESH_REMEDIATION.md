# v0.6.1 mesh remediation

**Geometric replacement candidate PASS; mechanical convergence UNQUALIFIED.**
The accepted new fine mesh has2,766,505 nodes and
1,261,670 quadratic triangles, minimum angle
11.404135026°≥10°. No acceptance threshold changed.

Registered A: importing the saved local layout as discrete entities and forcing
Gmsh Relocate2D moved intended fixed boundary corners by up to0.102mm. Both
patch trials were rejected; no full A mesh was launched. The first attempt
retained the input and rejection reason, but its rejected output was not written
because the invariant raised before serialization. A repeated, separately retained
run with identical settings captures the actual rejected output. This evidence
handling correction did not change meshing parameters. Do not call the first
failed output archived when only its input/reason are available.

Registered B: retain algorithm6 and exact source; bucket curves by length using
power-of-two Distance Sampling counts for spacing≤boundary h/2, apply explicit
boundary point sizes, generate linear triangles, run ten Relocate2D iterations
on the CAD-backed surface, then setOrder(2) with SecondOrderLinear=1. This fixes
long-curve sampling/spacing and allows interior quality improvement. Default
MeshingPolicy keeps historical generation behavior unchanged unless opted in.

Local actual source-intersection crops around the worst interior and boundary
corner passed at19.4334° and23.3796°, with zero domain difference and valid full
TRI6 maps. These are explicitly translated diagnostic crops, not replacement
full specimens. Repeated B local meshes had identical content hashes.

The full B fine candidate uses h_boundary=.0033333333mm and h_bulk=.04mm.
It preserves all412 pores, one connected solid,50.0104mm² area, zero domain
symmetric difference and exact source-boundary segment coverage. Minimum quality
0.335816809, maximum aspect5.182422667,
relative area error7.25e-15. Every sampled axial
solid chord has at least7 elements across it;
this remains a finite feature screen, not exhaustive neck certification.

No quadratic element is inverted or uncertified under the registered analytic
whole-reference-domain determinant check. Minimum detJ is
2.39763699599e-06mm². Corner shape,
higher-order mapping, boundary fidelity and narrow-feature screens remain separate.
The test uses floating-point coefficients with a scaled guard, not interval
arithmetic or a sampled-positivity proof. Curved geometry remains unsupported.

A genuinely different coarse new level (h_boundary=.005,h_bulk=.06mm) generated
1,383,233 nodes/610,630 elements, but failed at
8.303164776°. Its other gates and sampled features passed.
It remains rejected. The study stopped additional levels; finer_new was NOT
ATTEMPTED. Passing fine does not retroactively qualify old or new coarse meshes,
and passing geometry does not establish mechanical mesh convergence.

Fine generation-only85.129s; independent full
validation31.566s; sampled features
1.260s; complete worker127.584s.
Peak worker RSS2,415,714,304bytes. Coarse worker
68.538s, peakRSS1,285,341,184bytes. Workers were
monitored against the registered4GiB RSS/600s budget, with large raw outputs
ignored and retained. RSS is worker lifetime high-water memory, not a directly
comparable mesher-only allocation. The historical188s/1.57GiB study also included
plotting in a different process lifetime; no unsupported speedup claim is made.

Reproduce with mesh_remediation local/study and remediation_reporting module
commands documented in the handoff. All attempts, freezes, source hashes,
actual-mesh figures and detailed gate summaries are versioned separately from
v0.6. The accepted file is mesh_candidates/full_run_001/fine_new/generated/mesh.npz.
No full-size ANSYS input or solve was started.
