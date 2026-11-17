# F1 mechanical benchmark

Actual licensed ANSYS solves were completed for three controls, the authenticated C/PEEK reference annotation and the prospectively selected genuine archived F1_B_02/r0/seed0 output. Reference and generated source both received H1/H2. There were seven new source solves and seven independent readbacks, each with five actual strain checkpoints through0.5%. No native failures or geometry repairs occurred.

| Model | H1 apparent modulus (MPa) | H2 apparent modulus (MPa) | H2 change relative to H1 |
|---|---:|---:|---:|
|Reference|2230.445255|2158.151037|-3.241%|
|Genuine F1_B_02/r0/seed0|2147.601360|2093.076563|-2.539%|

Homogeneous matrix control gave1000MPa (analytical1000); the parallel two-solid,nu0 control gave5500MPa (analytical5500); the explicit-void control gave500MPa (analytical500). The void control has two separate full-height load-carrying matrix strips with one minimal transverse pin per strip. It verifies pruned-node boundary enumeration and full-envelope nominal stress normalization. No arbitrary porous analytical solution is claimed.

Native phase semantics remain matrix0→MAT1, fiber cross-sections1→MAT2, void2→no element. The reference has34585/29668/1283 matrix/fiber/void pixels; the generated field has34084/30096/1356. Both have one edge-connected solid component, with no floating island or corner-only component attachment. Void elements and unused nodes are removed; internal void boundaries receive no restraints. Shared matrix/fiber interfaces are ideally bonded. No weak springs, pore filling, fiber removal, contact or large-strain simulation was used.

Illustrative plane-stress properties are E1000/10000MPa,nu0.30. The1mm square/thickness is a computational convention, not microscopy calibration. Nominal stress is total boundary reaction over the full envelope, including void; volume-integrated solid stress independently agrees. All cases pass reaction balance, external work/strain energy, phase constitutive fields, mesh/material/constraint inventories and independent RST reopening. The archived generator receipt/source/output hashes authenticate the genuine specimen; no new F1 generator call or researcher replacement baseline was counted.

F1_NATIVE_CURVES.csv records35 actual checkpoint rows including signed reactions/displacements and strain energy. F1_PHASE_SUMMARY.csv contains native element-associated phase stress/strain/energy summaries; F1_MECHANICAL_SUMMARY.csv records all seven models. Source/readback paths and native hashes are preserved in the mechanical-response manifests. The figures show actual stress–strain/force response, phase maps, native axial/equivalent stress, native nodal displacement and deformation at1× scale. Void regions remain blank; no cross-material nodal stress averaging is used.

The reference is a transverse cross-section. Approximately circular fiber annotations carry documented boundary and void-label uncertainty; no longitudinal fiber length or in-plane fiber-axis orientation is inferred. One reference and one archived generated realization do not establish cross-family generalization. H2 reduces apparent modulus by about3.24% and2.54%; these non-negligible changes must accompany comparisons. Two levels do not establish mesh convergence or a rigorous error bound. Mechanical material calibration, physical composite behavior, RVE homogenization and isotropy remain unverified. Additional archived C02 comparisons were optional and were not run, preserving focus on the registered P3 trial.
