# Pipeline v0.6 — 2D compression validation

**HOLD. No ANSYS simulation was executed. No mechanical curve or effective
stiffness exists.** The solver-independent implementation and all three mesh
levels are retained. The final fine mesh fails the registered minimum-angle
criterion; stop before microstructure input preparation/solving. Do not bypass
this failure by choosing the passing medium level.

## Research objective and scope

Current priority: native2D design → actual2D finite elements → contact-enabled
ANSYS compression → stress–strain/deformation → structured future feedback.
Three-dimensional CAD, extrusion, mesh, manufacturing and autonomous LLM design
iteration are deferred. The first real contact-enabled microstructure milestone
remains incomplete. This is an engineering feasibility study, not a new geometry,
material, manufacturing or paper-readiness qualification.

## Software and audit

Linux x86_64, Python3.12.14, Gmsh4.15.0, Shapely2.1.2; precise packages are in
[environment.json](../../experiments/pipeline_v0.6/mesh_validation/run_003/environment.json).
No Mechanical, MAPDL, Workbench, PyMAPDL or PyMechanical runtime was found on PATH
or conventional installation locations. License checkout is NOT TESTED, rather
than an asserted license denial. There is no configured remote solver endpoint.
Official ANSYS/Gmsh web documentation was blocked by proxy403. Distributed Gmsh
API documentation and official PyMAPDL command documentation were consulted;
actual ANSYS release compatibility remains pending. See audit/DOCUMENTATION.md.

The supplied checkout has v0.5C/C.1 documents but lacks their referenced study
runs, protected simplification implementation and saved candidates. Their
acceptance cannot be independently authenticated here. Preserve the reported
cumulative-small-pore HOLD and all historical acceptance states.

## Reused source geometry and conventions

Design9, seed1, saved native1024 mask and run_003 exact WKB/loop serialization.
Selected for one connected spanning solid, valid manifold boundary, complete
available provenance and no new subpixel contact regularization. Reused strict
NPY/PNG loading, existing topology/manifold inspection, exact-loop reconstruction,
independent rasterization, source-only axial probe selection and frozen evaluator
interfaces. No procedural generator or frozen evaluator was changed or invoked
to generate a new design.

- Canonical raster SHA256: `e4b28517f4147a9f5eefd045a023f8f7bf2f99c63e950d995ad9ce5bbe68faf8`.
- Raw pixel SHA256: `a29ab50312d0181c6bce0aa1fa644da953fdb467f42acd945d79507c3d28d145`.
- Exact WKB SHA256: `4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1`.
- Generator SHA256: `dcc4529aab090cb1ff2fe9bfd1b0325ca3b1f00724743aeefe9a9c6aea78239b`.
- Solid area500104cell² =50.0104mm²; solid fraction0.476936340332.
- 412 enclosed pores; one solid component and both percolation directions.
- Minimum geometry clearance1cell; smallest sampled solid axial chord1cell.
  These are geometric diagnostics, not exhaustive neck/strength certification.
- The saved15-pixel generator topology repair is retained and disclosed; it is
  distinct from subpixel manifold regularization, which was not added.
- Explicit y-down→y-up reflection: x'=xW/1024, y'=H-yH/1024, lower-left origin.
  Restored CCW exterior/CW pore winding; no silent rotation or reflection.

The existing exact source geometry is retained. No pore removal, smoothing,
strut widening, raster resizing, CAD export or hidden geometric repair occurred.

## Provisional mechanics assumptions and protocol

The frozen revision1 protocol precedes all mesh attempts; each run stores its
SHA256 and exact copy. Demonstration-only W=H=10.24mm, pixel=.01mm, thickness1mm,
E=1000MPa, nu=.3, homogeneous isotropic elastic material, consistent mm–N–MPa.
Dimensions and material are assumed, not measured or supplied physical data.
Plane stress is the provisional pilot choice; plane strain is exposed separately
with unit-depth forces. Thin unconstrained sheet behavior differs from
out-of-plane constrained plane strain. Neither has been scientifically chosen
from a specified physical specimen.

Gmsh produces genuine2D straight-sided quadratic TRI6 elements, intended for
PLANE183 six-node triangles (KEYOPT(1)=1); no degenerate quad representation.
The adapter prepares KEYOPT(3)=3 for thickness-based plane stress and2 for plane
strain. Those element settings, contact compatibility and thickness behavior
require target-release review and actual solver tests.

## Actual mesh generation and independent checks

Exact exterior and every pore loop become Gmsh plane-surface loops. Distance
fields refine boundaries; bulk size=.04mm is fixed in this feasibility study.
Single-thread algorithm6, element order2, linear midsides. Independent checks
cover node inventory, conforming midsides, positive Jacobians, complete edges,
nonoverlapping coverage, connected components, Euler hole count, independently
reconstructed domain, full area, exact straight-segment boundary coverage,
group ownership and outward geometric normals. Sampled axial chords require
at least3 distinct elements across each selected solid chord. Full mechanical
convergence and exhaustive narrow-neck certification are separate.

| Level | Boundary h [mm] | Nodes | TRI6 elements | Min quality | Min angle [deg] | Max aspect | Min sampled elements across | Combined gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 0.01 | 604,875 | 263,602 | 0.413745 | 16.082222 | 5.099474 | 2 | HOLD |
| 1 | 0.005 | 1,178,740 | 516,291 | 0.283468 | 12.034855 | 7.943773 | 3 | PASS |
| 2 | 0.00333333 | 1,839,714 | 814,939 | 0.246037 | 8.275134 | 7.476381 | 8 | HOLD |

All levels retain412 pores, one mesh component, exact50.0104mm² solid area,
zero domain symmetric difference and zero boundary/segment coverage discrepancy.
Area relative errors are below7.4e-15. Quality is4√3A/Σl²; aspect is longest edge
squared / twice area. The fine mesh has27 elements below
10°; its minimum8.275134° fails the independent angle gate despite minimum
quality.246037 exceeding.1. The failure is retained in FAILURE.json and
angle_failure_details.json. No thresholds were relaxed.

Whole completed run: 188.067s, process peak RSS
1,684,410,368bytes (1.569GiB).
Generation-only times were24.685s,41.290s and65.240s. RSS includes Python, Gmsh,
GEOS, validation and plotting, not just mesher allocations. Earlier performance
attempts run_001/run_002 remain preserved. Indexed boundary checks and complete
boundary reconstruction removed scaling bottlenecks without changing gates.
Repeated coarse mesh content hashes are identical across independent runs.

## Contact, transfer and benchmarks

Four rectangle draft input bundles cover direct/contact loading and plane
stress/strain. External contact uses separate upper/lower CONTA172 pairs,
TARGE169 rigid line targets and pilot controls, zero initial geometric gap,
frictionless separation without bonding, augmented Lagrange and finite sliding.
The bottom pilot is fixed; upper UY is negative, UX/ROTZ fixed. One bottom specimen
UX anchor removes lateral drift; specimen UY is transmitted by actual contact
in the draft contact model rather than top/bottom direct constraints.
Actual ANSYS normals/defaults/stiffness/thickness scaling remain unverified.

Local record lint roundtrips coordinates, TRI6 connectivity, counts, material,
formulation and contact inventory. It is not an ANSYS parser or import test.
Input manifests say DRAFT_UNVERIFIED. No microstructure input bundle was advanced
after the fine mesh failure. The rectangle input bundles remain applicable
preparation for a licensed Windows benchmark.

The connected synthetic C-channel is meshed as an engagement-test candidate with
.02mm initial gap and explicit exclusion of its connecting web/shared-node faces.
Internal contact elements are NOT configured and no contact engagement was
observed. Internal self-contact stays unqualified and blocks advanced compression.
No arbitrary all-pairs contact or bonded pore walls were introduced.

Analytical rectangle references use infinitesimal plane-stress E and plane-strain
E/(1-nu²), under matched frictionless/free-lateral assumptions. They are labelled
ANALYTICAL_INFINITESIMAL_NOT_ANSYS. No synthetic FEM response or surrogate solve
has been presented as ANSYS evidence. The preflight returns
MISSING_ANSYS_INSTALLATION / NOT_TESTED_NO_SOLVER.

## Loading, extraction and missing outputs

Draft loading is static displacement control with NLGEOM, full Newton, automatic
substeps10/100/1,50 equilibrium iterations, line search and force-residual.005;
no stabilization/damping. Requested compression stages are0,.5,1,2%. No stage was
solved, converged or failed in ANSYS; the mesh gate failed before a pilot solve.
Pseudo-time is a load parameter, never elapsed seconds.

Draft exports cover reaction histories, load/substep identities, nodal U/SYY/
SEQV/elasticEYY, and contact status/pressure/penetration/gap. The batch runner
retains logs and hashes, detects missing installation/license/process/output
failures, and never treats return code zero as acceptance. The postprocessor
requires authentic outputs and completed-substep log evidence, filters unverified
sets, checks signs, force balance, active platen contacts, penetration and field
completeness, and quarantines invalid measurements. Full import/material review
is still required; counts alone do not prove it. Those commands have not been
executed or validated in an actual solver.

Definitions: positive compression epsilon=-UY_top/H, nominal sigma=RF_top/(Wb),
using the full envelope, not solid-only area. Plane strain uses unit-depth forces.
Effective modulus is a through-origin fit over0<epsilon<=.005, requiring at least
two achieved small-strain samples. Force balance tolerance1%; penetration limit
.001mm; rectangle small-strain stiffness tolerance2%. None has been measured.
No force–displacement curve, stress–strain curve, modulus, reaction balance,
contact penetration, nodal deformation/stress/strain field or energy exists.
The CSV files at experiment root contain headers and zero data rows by design.

## Figures and convergence

Actual source/vector/mesh/narrow-region/quality/boundary-plan plots, worst-angle
failure detail, mesh-feasibility refinement plots and synthetic benchmark setup
are retained. Mesh/platen previews say ANSYS NOT EXECUTED. Solver contact-status,
deformed comparisons, force/stress curves and displacement/stress/strain fields
are unavailable and are not fabricated. Boundary h refinement with fixed bulk
size is not full global mesh independence. Mechanical response, contact
penetration and peak-stress convergence were not evaluated. A future registered
study must refine the whole relevant field and keep geometry/material/contact/
loading fixed; local corner stress needs its own convergence analysis.

## Acceptance states

| Scope | Decision |
|---|---|
| A_geometry | ACCEPT_AUTHENTICATED_EXACT_MANIFOLD_ENGINEERING_INPUT_ONLY |
| B_2d_mesh | HOLD_FINE_ANGLE_GATE_FAILED; MEDIUM_FEASIBILITY_PASS |
| C_ansys_import | NOT_VERIFIED_NOT_EXECUTED |
| D_material | ASSUMED_PREPARED_NOT_SOLVER_VERIFIED |
| E_platen_contact | RECTANGLE_DRAFT_CONFIGURED_NOT_DEMONSTRATED |
| F_internal_self_contact | NOT_CONFIGURED_NOT_DEMONSTRATED |
| G_solver | NOT_EXECUTED_NO_ANSYS |
| H_mechanical_data | NO_ACTUAL_SOLVER_DATA |
| I_mesh_convergence | BOUNDARY_MESH_FEASIBILITY_ONLY; MECHANICAL_NOT_EVALUATED |
| J_research_readiness | HOLD |
| K_llm_optimization_readiness | NOT_QUALIFIED_NOT_IMPLEMENTED |
| L_manufacturing_readiness | NOT_QUALIFIED |

## Limitations, feedback and next milestone

No physical dimensions/material calibration, experimental validation, plasticity,
yield/failure law, solved strain range or manufacturing qualification. Historical
small-pore HOLD remains, and this snapshot lacks its later evidence. Finite
source/mesh screens do not certify all narrow features. No new subpixel repair
was introduced, but existing saved topology repair is part of the selected source.

mechanical_feedback.json provides design/seed/parameters, morphology/provenance,
mesh diagnostics, failure classification, warning and future field references.
All mechanical values are null; performance eligibility is false. A numerical
failure must not be labelled a structurally poor design. No autonomous LLM loop
or batch FEM study was implemented.

Next: preserve this failure, register a new protocol for fixing fine-mesh angles,
then verify a passing mesh and real licensed rectangle direct/contact import,
material/thickness, force, pressure and penetration benchmarks. Separately
validate nonadjacent internal self-contact engagement. Only then execute the
first conservative authenticated microstructure pilot, extract actual fields,
and establish mechanical refinement convergence before batch comparisons or
paper claims. Windows commands are in WINDOWS_EXECUTION.md.

## Repository changes and validation evidence

New package metamaterial_eval/simulation/ contains configuration, provenance and
coordinate adapter, Gmsh generation/validation, contact inventory, draft APDL
transfer/export, solver runner, postprocessing, mechanical definitions,
benchmarks, diagnostics and CLI. New tests exercise construction and analytical
numerical controls, not fabricated ANSYS data. requirements-v0.6.txt pins Gmsh.
AGENTS.md persists the mandatory descriptive-commit policy. README changes the
current priority; .gitignore excludes generated/ and solver products.

All3219 original tracked files were hashed.3217 remain byte-identical; only
README.md and .gitignore intentionally changed. Every generator, frozen
evaluator, canonical artifact, historical run and prior scientific decision is
unchanged. Large meshes/decks/logs are ignored and reproducible; small evidence
and selected figures are tracked. Missing historical artifacts were not invented.

Run the complete suite with EVALUATOR_PATH selecting v1.1. The initial unselected
run exposed20 known v1.0 validation failures; the correct v1.1 regression passed
370 tests before adding the final stop-condition control. Final regression: **371 passed, 0 failed**, 55.54s, including40 new simulation
controls. Results are in verification/regression.log and regression.xml; no historical test was weakened.
The complete changed-file manifest and preservation comparison are under
verification/. Commits are recorded in Git history and the final handoff; no push.

The numbered50-item response is in experiments/pipeline_v0.6/verification/
request_checklist.csv; figure_availability.csv accounts for all18 requested figure categories.
