# v0.6.1 scientific validation

**PARTIAL ENGINEERING PASS. Mesh remediation qualified one replacement fine
mesh. ANSYS_EXECUTION_BLOCKED; research readiness remains HOLD.** No real ANSYS
simulation, contact verification or mechanical result was produced.

## Objective, source and preservation

This milestone addresses two independent blockers: the original8.28° fine-mesh
angle failure and the unavailable licensed solver. Existing native1024 Design9,
seed1 exact geometry remains unchanged: one connected spanning solid,412 pores,
500104cell² solid area, explicit x-right/y-up engineering transform. No new
subpixel manifold repair was added. The saved historical15-pixel topology repair
is disclosed and retained. Geometry/generator/evaluator hashes and all prior
scientific artifacts supplied in the checkout remain unchanged. Historical
cumulative-small-pore HOLD and missing C/C.1 evidence are not reinterpreted.

The original fine mesh is retained byte-identical, SHA256
2d28fe9afe9be78b9a0c09cd8b58667e08b11305c4946ff8808f8aafe0faeef1.
No pore filling, source smoothing, strut widening, downsampling, hidden crop of
the selected specimen or3D representation was introduced.

## Diagnosis and independent mapping validation

All27 original failures were reproduced independently with atan2 corner angles;
minimum8.27513422° at one-based element4970.23 failing elements have only
interior corner vertices, three have actual boundary edges, and one touches a
boundary vertex without a boundary edge. Exact source angles are≥90°, so the
10° gate is not incompatible with the immutable boundary. Boundary-corner
failures have strongly unequal mesh legs; the original Distance field uses
only three samples per curve. Interior failures are poor mesh layout. These
observations support the registered combined correction, not a claim that a
single isolated setting caused every defect.

Corner quality, straight midside placement, whole TRI6 map, boundary fidelity
and finite narrow-feature resolution remain separate. The map determinant is a
quadratic polynomial; production validation checks vertices, edge stationary
points and an interior stationary point over the entire reference triangle,
with a scaled floating-point guard. Bernstein coefficient lower bounds provide
an additional sufficient check. This is not numerical sampling or formal
interval arithmetic. No invalid/uncertified higher-order element was found in
the original or accepted replacement mesh; synthetic inverted/curved controls
are rejected. Details/IDs/coordinates/neighbors/source entities/distances and
actual mesh figures are in V0_6_1_MESH_DIAGNOSIS.md and mesh_diagnosis/run_001.

## Frozen protocol, candidates and selected result

MESH_PROTOCOL revision1 was committed before candidate settings changed. The
10° gate, quality≥.1, aspect≤20, source/area/boundary/topology/pore checks and
at least three elements across every registered axial chord were retained.
All trial freezes authenticate that protocol.

Registered A forced Relocate2D on saved discrete local patches and moved intended
fixed boundary nodes by up to.102mm. It was rejected, never applied to the
original file and not escalated to a full candidate. Run001 preserved its input
and failure reason but not the rejected output because the invariant raised
before serialization. Run002 repeats the same settings with failure-output
capture and retains the actual rejected coordinates. This limitation is explicit.

Registered B keeps algorithm6, buckets distance-field sampling by curve length,
sets boundary point sizes, relocates the CAD-backed linear mesh for ten
iterations, then creates straight TRI6 midsides. Two explicitly labelled local
source-intersection crops passed at19.4334° and23.3796°, with exact domains and
valid maps. Their repeat hashes match. They are not full-specimen simulations.

| New level | Boundary/bulk h [mm] | Nodes | TRI6 elements | Min angle | Below10° | Result |
|---|---|---:|---:|---:|---:|---|
| fine_new | .0033333/.04 | 2,766,505 | 1,261,670 | 11.404135° | 0 | PASS all registered geometric gates |
| coarse_new | .005/.06 | 1,383,233 | 610,630 | 8.303165° | 45 | HOLD angle gate |
| finer_new | .0025/.03 | — | — | — | — | NOT ATTEMPTED after failed coarse level |

The accepted fine mesh preserves412 pores, one component,50.0104mm² area,
zero domain symmetric difference and exact source-segment coverage. Minimum
quality.335816809; maximum aspect5.182422667; minimum whole-map detJ
2.39763699599e-6mm²; maximum midpoint error1.2561e-15mm. All registered solid
axial chords have≥7 intersected elements. This is a finite mesh-resolution
screen, not exhaustive minimum-neck or strength certification.

A passing fine mesh does not qualify rejected coarse/original meshes. The
study stopped further levels at the next failure. It does not establish
mechanical mesh convergence; only one new corrected level is accepted and
there are zero solved mechanical levels. Local peak stress convergence is
independently unqualified. V0_6_1_MESH_REMEDIATION.md has the full record.

## Solver environment and rectangle packet

Fresh Linux/Python inspection found no accessible Mechanical/MAPDL/Workbench
installation or PyMAPDL/PyMechanical runtime. No remote endpoint/identity is
configured. --smoke preflight stopped at discovery; no process or license
checkout ran. Actual solver version is null. License NOT_TESTED_NO_SOLVER is
not a measured license denial. Windows execution is NOT VERIFIED.

A small617-node/268-element Gmsh rectangle package uses the same provisional
10.24mm envelope, plane-stress1mm thickness, assumed E1000MPa and nu.3. Direct
and contact drafts share the mesh/material/load schedule(.01,.05,.1,.5%). Plane
strain is separately exposed with unit depth. PLANE183 TRI6 and CONTA172/TARGE169
settings, normals, pilot controls, actual defaults and thickness scaling still
require official documentation matching the actual installed release and real
import/material checks. Local APDL lint is only a record roundtrip.

The51.2N value at.5% is explicitly an infinitesimal plane-stress analytical
reference, not an actual reaction. Plane-strain free-lateral reference is
E/(1-nu²), not the laterally constrained formula. Both dimensions and material
are computational assumptions, not physical data supplied by Dr.Wang.

No solver force, contact pressure/status/gap/penetration, equilibrium,
convergence, stiffness, deformation/stress/strain field or actual curve exists.
No solver-result figure was fabricated. Static mesh/source figures and clearly
labelled analytical references are separate from missing ANSYS outputs.

The batch/qualification workflow detects missing installation/license/version/
process/output failures. Contact cannot run before a receipt-linked direct
qualification with matching configuration/schedule. Qualification re-derives
curves from authenticated raw completed-step history, checks equilibrium and
contact inventories/engagement/penetration, compares the registered analytical
tolerance and requires full actual model review. A false-by-default model-review
template is provided; setting a JSON string without actual receipts cannot
qualify a result. A pilot additionally requires direct/contact evidence and a
frozen mesh/loading-specific protocol. No microstructure input or solve was
launched; its roughly5.53million translational DOFs also need real solver
memory/license/disk evaluation. Internal self-contact remains unconfigured.

## Software coverage and457-versus371 reconciliation

Final primary command: EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py
python -m pytest tests validation/test_evaluator.py -q. **421 collected/executed,
421 passed,0 failed/errors/skipped/deselected**,56.44s. The initial current
inventory was371, matching the preserved v0.6 JUnit. The old40 focused checks
are a subset of371, not40 additional unique tests. This milestone adds50 unique
primary cases and removes none. An intermediate415-case run is retained before
the last six raw-output corroboration controls; use final_regression for final
counts. Tests cover actual Gmsh and independent analytical/map/control behavior;
zero licensed ANSYS integration cases executed.

The three available archived snapshot test files collect112 cases. Direct
execution initially passed108 and failed4 because each snapshot's own root
lacks its referenced experiment fixtures. These failures/logs are retained.
Byte-identical archived test copies were then replayed in temporary roots with
links to authenticated current fixtures and the unchanged geometry implementation:
37+75=112 passed, no failures/skips or weakened assertions. Original snapshots
were untouched. These overlapping historical controls are reported separately,
not added to a larger unique primary headline count.

The user-reported457-test C.1 study/inventory and its producer/requalification
artifacts are absent from the supplied checkout and available path history.
The exact86-test difference from the pre-change371 cannot be mapped to specific
tests without that inventory. No tests were invented, deleted or deselected to
match457. Available suites, exact commands, source hashes, collections, replay
manifest and JUnit outputs are in verification/ and scripts/replay_geometry_archives.py.

## Performance, evidence and limitations

Accepted fine: generation-only85.129s; generation plus authentication87.776s;
full validation31.566s; sampled feature checks1.260s; total worker127.584s;
peakRSS2,415,714,304bytes (about2.25GiB). New coarse total68.538s,
peak1,285,341,184bytes. Diagnosis metrics1.686s, excluding its
figures. Input-packet preparation0.043s
includes small meshing/validation and both draft bundles. Optimization time is
included in generation, not separately captured for the completed full run;
no retrospective separate timing is invented. Solver/startup/extraction time
and solver memory are unavailable. PERFORMANCE.json records these scopes,
measured audit-to-report wall window, disk and reporting time.

Worker RSS is a lifetime process high-water measure; the historical188s/1.57GiB
run used a different whole-process lifetime including figures. Do not present
these as identical profiling methods or claim an unsupported speedup. The4GiB/
600s worker limits and2GiB disk-free gate were enforced for full candidates.

No material calibration, experimental mechanics, yield/failure model, internal
contact qualification, mechanical refinement evidence, paper readiness,
manufacturing qualification or autonomous feedback iteration. The old cumulative
small-pore fidelity HOLD remains. Numerical model failure must not be interpreted
as a measured structurally poor design. No batch FEM or3D work was implemented.

## Independent acceptance states

| Category | Decision |
|---|---|
| A_SOURCE_INTEGRITY | PASS_SUPPLIED_PROTECTED_INPUTS_UNCHANGED |
| B_MESH_FAILURE_DIAGNOSED | PASS_27_FAILURES_REPRODUCED_MESH_INDUCED |
| C_MESH_QUALITY_QUALIFIED | PASS_SELECTED_FINE_NEW_ONLY |
| D_QUADRATIC_ELEMENT_QUALIFIED | PASS_ANALYTIC_POLYNOMIAL_MINIMUM_WITH_FLOATING_POINT_GUARD |
| E_NARROW_FEATURE_QUALIFIED | PASS_REGISTERED_FINITE_AXIAL_SCREEN_ONLY |
| F_ANSYS_ENVIRONMENT_AVAILABLE | BLOCKED_NO_EXECUTABLE_LICENSE_NOT_TESTED |
| G_ANSYS_IMPORT_VERIFIED | NOT_EXECUTED |
| H_DIRECT_COMPRESSION_BENCHMARK_PASS | NOT_EXECUTED |
| I_PLATEN_CONTACT_BENCHMARK_PASS | NOT_EXECUTED |
| J_INTERNAL_SELF_CONTACT | NOT_CONFIGURED_NOT_DEMONSTRATED |
| K_MECHANICAL_OUTPUT_VERIFIED | NOT_EXECUTED_NO_ACTUAL_MECHANICAL_DATA |
| L_MICROSTRUCTURE_PILOT | BLOCKED_MISSING_LICENSED_RECTANGLE_AND_IMPORT_QUALIFICATION |
| M_MECHANICAL_MESH_CONVERGENCE | UNQUALIFIED |
| N_PAPER_READINESS | UNQUALIFIED_RESEARCH_HOLD |
| O_LLM_OPTIMIZATION_READINESS | UNQUALIFIED_NOT_IMPLEMENTED |
| P_MANUFACTURING_READINESS | UNQUALIFIED |

## Commits and handoff

- `4d15640866a64c01578eefbae3443f7a6f46e4f4` — docs(fem): register v0.6.1 mesh diagnosis and remediation protocol
- `80257e8216e12ef1cea301147e0c3f3037f7a1dc` — test(mesh): diagnose all fine-mesh defects and verify quadratic mapping extrema
- `2bbdba5b76ac818626d8d479d963cf9fd85fa712` — fix(mesh): qualify a fine TRI6 mesh with boundary-aware sizing and relocation
- `10c7fda4983be1bce15679a9ebdd54289c36f4e7` — feat(ansys): gate rectangle contact qualification on authenticated licensed evidence

The final reporting commit is the commit containing this report; its hash and
all messages are included in the final chat handoff and Git history, avoiding
a self-referential embedded commit hash. No push was requested or performed.
The numbered66-item handoff, changed-file inventory, historical preservation,
protocol verification and final working-tree check accompany the reports.
Next priority: licensed small direct/contact rectangle qualification, then a
separately registered conservative pilot with resource/import/output evidence.
Stop before batch studies, autonomous LLM iteration or3D modeling.
