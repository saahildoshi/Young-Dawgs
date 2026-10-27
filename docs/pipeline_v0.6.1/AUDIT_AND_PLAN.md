# v0.6.1 audit and prospective plan

Audit date2026-10-27. Branch work, initial HEAD
51f8370c95f800dea5bb64af93c93cfe9d02df97, clean worktree. AGENTS.md commit
policy retained. Hash all3315 tracked files before changes; also authenticate
the ignored saved fine mesh (SHA256
2d28fe9afe9be78b9a0c09cd8b58667e08b11305c4946ff8808f8aafe0faeef1).
No expensive remeshing preceded this audit.

Read v0.6 validation, Windows instructions,50-item checklist and changed-file
inventory; v0.5 architecture/manifold/scientific architecture and small-pore
qualification pointer; actual simulation configuration/generation/validation,
geometry adapter, contact/APDL, execution, export, postprocessing and tests.
Historical small-pore HOLD remains; missing C/C.1 run artifacts cannot be restored
or treated as authenticated from summaries alone.

## Required15-point audit

1. The three meshes use the exact Design9/seed1 polygon and all412 holes, Gmsh
   algorithm6, one thread, quadratic triangles, straight midsides, a threshold
   distance field and no explicit post-generation relocation.
2. Only boundary SizeMin/MeshSizeMin changes (.01,.005,.003333333333mm).
   Bulk size remains .04mm; DistMin=.005, DistMax=.02. Distance Sampling=3 per
   curve; point-size and boundary-extension constraints are disabled. Long
   boundary curves can therefore have poorly sampled boundary-distance fields.
3. Existing minimum-angle measurement uses arccos of corner-edge dot products.
4. It checks corner angles and separately requires midsides within1e-10mm of
   edge means. It does not evaluate a general curved quadratic map.
5. Existing determinant is the signed corner cross-product. It proves an affine
   triangle positive only when midsides are exactly affine; the allowed midpoint
   tolerance was not accompanied by a whole-element Jacobian bound. Strengthen
   with the full quadratic determinant polynomial over the reference triangle.
6. Source-only short axial solid chords require≥3 distinct intersected TRI6
   interiors and complete chord coverage. This finite screen is not exhaustive
   minimum-neck qualification; preserve its definition and historical outcomes.
7. Saved angle_failure_details.json lists27 failing TRI6 elements. Worst is
   zero-based4969 (one-based4970),8.27513422°, near(3.96143,3.62847)mm.
8. Preliminary saved-mesh inspection:23 failures have no boundary corner, one
   has one, one has two and two have all three corners on boundaries. Three
   triangles have actual boundary edges. Centroids lie .001809–.011591mm from
   the source boundary. Two corner triangles have a90° immutable wedge but
   strongly unequal sampled boundary legs (.005428 vs about.032mm). All source
   segments are axis-aligned: the8° angle is not an acute immutable domain wedge.
   Detailed one-ring/entity/width/Jacobian diagnosis precedes candidate trials.
9. Transfer emits explicit N/EN records, PLANE183 KEYOPT(1)=1, plane-stress/strain
   KEYOPT(3), material/real constants, geometric components and CONTA172/TARGE169
   pairs with pilot controls. Local record lint is not an ANSYS parser/import.
10. Python3.12.14/Linux x86_64, Gmsh4.15.0, NumPy2.5.4, Shapely2.1.2. No Mechanical,
    MAPDL, Workbench, PyMAPDL or PyMechanical found on PATH/conventional locations.
11. License is NOT_TESTED_NO_SOLVER, not an asserted license denial. No remote
    solver endpoint/credential is configured. Recheck and save explicit evidence.
12. Only Python construction/record-transfer and numerical-control tests have
    run. Release-specific element ordering, material/thickness behavior,
    contact normals/force transmission and all solver outputs are unverified.
13. Explicit collection of tests and validation/test_evaluator.py with v1.1
    currently collects371 tests.40 focused simulation tests are a subset, not
    additional unique tests. Historical457 cannot be reconstructed from an
    absent C.1 test inventory; do not invent the86-test difference. Archive
    snapshots are inventoried separately from current executable test roots.
14. Valid solver qualification requires actual version/license execution, full
    node/connectivity/material/thickness import inspection, converged direct
    rectangle force/stress/displacement agreement, then real active upper/lower
    contact, pressure, controlled penetration, balanced force and matched response.
15. Without ANSYS, all actual import/material/direct/contact/mechanical and pilot
    acceptance remain BLOCKED. Mesh diagnosis/remediation proceeds independently.

## Work and commit checkpoints

A. Commit audit and frozen protocol before changing mesher settings.
B. Add independent corner/quadratic-map metrics and full saved-mesh diagnosis,
   all27 failures, geometry/neighbor/feature context and figures; test and commit.
C. Test registered bounded local candidates, then at most three full new levels
   only after local evidence supports the strategy. Retain every attempt and
   original meshes; freeze10° and all original gates; test and commit.
D. Reassess solver; prepare version-reviewed draft Windows rectangle package,
   smoke/license diagnostics, positive evidence gates and actual-output handling.
   If no executable, do not invent results or launch a microstructure model.
E. Reconcile collection/run inventories; regression and preservation checks;
   independent A–P acceptance,66-answer handoff and final descriptive commit.

The installed official Gmsh Python documentation confirms optimize methods
Laplace2D, Relocate2D, HighOrder and related methods. Default/Netgen optimization
is for tetrahedra, not a justified fix here. Since historical midsides are straight,
first address linear triangle layout/size transitions and regenerate straight
midsides. Record actual API behavior on small controls before a full candidate.
