# v0.6.1 rectangle benchmark preparation

**DIRECT AND CONTACT BENCHMARKS: NOT EXECUTED.**

A deterministic small Gmsh mesh has617 nodes and268 TRI6 elements, minimum angle
26.51343265°, valid straight midsides and positive whole-element determinant.
The same mesh is used by direct and platen-contact draft inputs. It represents
a solid rectangle10.24×10.24mm, plane-stress thickness1mm, assumed E1000MPa and
nu0.3. Every value is provisional, not an experimentally measured specimen.
Plane strain is separately configurable with unit-depth forces.

Four prospective small-strain targets are .0001,.0005,.001,.005. Direct loading
sets bottom UY=0, top UY=-epsilon H, and one bottom UX anchor, with other lateral
DOFs free. Contact loading uses actual separate rigid platen targets/pilots and
specimen contact faces, not direct specimen UY constraints. Both use geometric
nonlinearity, adaptive stepping and the same material/dimensions.

Infinitesimal free-lateral plane-stress reference: sigma=E epsilon,
F=sigma W b. At0.5%, sigma=5MPa, delta=.0512mm, F=51.2N. These are explicitly
ANALYTICAL_NOT_ANSYS values in ANALYTICAL_reference.csv. With plane strain and
free sigma_x, epsilon_z=0 gives E_effective=E/(1-nu²), not the laterally constrained
modulus. Finite deformation and different lateral/friction constraints must not
be silently compared with the wrong analytical formula.

Frozen acceptance: analytical relative error≤2%, reaction imbalance≤1%, contact
penetration≤.001mm, all requested targets achieved, whole model import/material/
thickness/DOF/contact review and actual converged output. All are UNVERIFIED.
Actual reaction, analytical-relative discrepancy, force balance, stiffness,
contact engagement, pressure, penetration, increments and field results are null.
No solver curve or deformation figure was fabricated.

The package contains draft APDL, extraction macro, mesh NPZ, manifests, local
transfer lint and a false-by-default MODEL_REVIEW_TEMPLATE. Local transfer lint
checks records, not an ANSYS parser or real import. PLANE183/CONTA172/TARGE169
and thickness behavior await installed-release review and actual execution.

The postprocessor authenticates raw files and completed-substep log evidence.
The qualification screen also re-derives curve values from authenticated raw
reaction history, verifies active contact inventories when relevant, compares
with the prospective analytical tolerance, and requires a receipt-linked full
model review. A fabricated pass string or edited derivative CSV cannot qualify
the run. Numeric unit controls are labelled analytical/unit controls and never
stand in for a real solver run.
