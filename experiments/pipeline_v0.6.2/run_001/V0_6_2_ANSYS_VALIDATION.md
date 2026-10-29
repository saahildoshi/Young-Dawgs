# v0.6.2 licensed ANSYS validation

## A. Executive summary

**RECTANGLE_ENGINEERING_PASS — MICROSTRUCTURE_PILOT_BLOCKED — RESEARCH_HOLD.**

Real ANSYS 2024 R1 direct and frictionless platen-contact rectangle calculations
executed and converged through 2% requested compression. The corrected contact
run has two active force-transmitting interfaces, balanced reactions, measured
contact-element forces, supported displacement/stress/strain fields and actual
stress–strain data. A repeated licensed solve produced identical history CSV
bytes. No microstructure solve executed: the selected qualified mesh bytes are
absent. Internal self-contact and mechanical mesh convergence remain unqualified.

The prospective protocol was committed before the first solver attempt. The
failed initial exporter and failed default-contact benchmark remain preserved.
Nothing in v0.6/v0.6.1 or the historical scientific HOLD record was rewritten.

## B. Windows environment

Windows 11; ANSYS 2024 R1, build 24.1, UP20231106. Actual Workbench RunWB2.exe,
Mechanical AnsysWBU.exe and MAPDL ANSYS241.exe were found under the discovered
AWP_ROOT241. Workbench journal execution, hidden Mechanical launch and embedded
ExtAPI scripting completed (one analysis returned). The actual solver banner
identifies **Mechanical Enterprise Academic Research**. Completed finite-element
calculations and real RST results establish observed licensed execution. No
license file, credentials or license-server setting was requested or committed.

Hardware audit: 20 logical processors, 68,403,589,120 bytes physical RAM
(63.71 GiB), 36,100,104,192 bytes available RAM, and 1,463,142,694,912 bytes
free on the run drive. All jobs used one shared-memory core. Parallel-license
capacity and the full model's license-size capacity were not tested.

Python 3.14.6; NumPy 2.5.1, SciPy 1.18.0, scikit-image 0.26.0, Matplotlib
3.11.1, Shapely 2.2.0, Gmsh 4.15.0, pytest 9.2.0 and psutil 7.2.2.
PyMAPDL/PyMechanical were not installed or needed. The Shapely version differs
from the historical optional 2.1.2 pin; the historical requirements are retained
and the measured Windows dependency set is separately recorded.

Initial audit/legacy smoke JSON records are immutable observations, not current
acceptance states: the old release regex matched an input comment and its license
label was conservative. The actual banner, corrected runs and evidence below
establish release and licensed solver acceptance independently of those labels.

## C. Automation architecture

Workbench/Mechanical scripting was evaluated first and worked. Direct MAPDL
batch is the production route for the existing externally meshed 2D model:
it accepts explicit N/EN TRI6 records, permits transparent PLANE183/contact
definitions and exports exact solver-side inventories. The new windows_ansys
module supervises owned process trees with timeout/RSS limits; licensed_benchmark
prepares inputs, validates actual results and rereads RST contact endpoints.

No alternative production Workbench integration, fabricated GUI API or 3D
surrogate was introduced. A Workbench project solve and External Model import
were NOT EXECUTED. Mechanical's ability to open and answer a scripting query is
reported separately from the actual MAPDL structural solve.

Official v241 help pages were attempted but inaccessible, and the local help
contains a documentation-not-installed placeholder. Official v242 PLANE183,
CONTA172, TARGE169 and ETABLE pages were used as comparison references, with
commands/settings checked empirically against actual v241 output. This is not
a claim that unavailable installed-release documentation was fully reviewed.

## D. Mesh transfer and model definitions

The original adapter emits APDL N/EN text, not Gmsh .msh ingestion or a blocked
CDB archive. The real solver additionally generated genuine blocked CDB files
with CDWRITE. Their Workbench External Model compatibility remains unverified;
direct MAPDL transfer was actually demonstrated.

The rectangle uses 617 specimen nodes and 268 six-node PLANE183 triangles.
Every node coordinate and all six connectivity entries were read back from
ANSYS and compared to the input mesh. Maximum coordinate difference was
5.33e-15 mm. Actual material/real/type attributes are 1/1/1; ETLIST identifies
a 2-D six-node plane-stress solid, KEYOPT(1)=1 and KEYOPT(3)=3. Actual RLIST
confirms initial thickness 1 mm. E=1000 MPa and nu=0.3 are provisional.
All specimen nodes lie in global XY with z=0. Independent Gmsh mesh validation
and source hash checks were reused.

Contact adds six user-defined target/pilot nodes and 44 target/contact elements:
623 user nodes and 312 elements before solution. ANSYS creates two internal
pilot-control nodes during solution. They are distinct from imported specimen
nodes. Actual DLIST confirms no specimen UY constraints bypass the contact.

## E. Direct rectangle benchmark

Width and height are 10.24 mm; initial thickness is 1 mm. The bottom has UY=0;
the top has prescribed UY; one bottom node has UX=0 to remove drift. Lateral
expansion remains free. NLGEOM is on. Six requested stages and 36 saved
converged substeps were achieved. Raw native RF is negative at the upper
support and positive at the lower support.

| Requested compression | Achieved travel [mm] | Analytical infinitesimal force [N] | Direct force magnitude [N] | Accepted contact force [N] |
|---|---:|---:|---:|---:|
| 0.01% | 0.001024 | 1.024 | 1.0241127 | 1.0241109 |
| 0.05% | 0.005120 | 5.120 | 5.1228174 | 5.1228225 |
| 0.1% | 0.010240 | 10.240 | 10.251275 | 10.251275 |
| 0.5% | 0.051200 | 51.200 | 51.483029 | 51.483018 |
| 1% | 0.102400 | 102.400 | 103.537910 | 103.537890 |
| 2% | 0.204800 | 204.800 | 209.398590 | 209.398570 |

The frozen analytical acceptance domain is through 0.5%, with 2% relative force
tolerance. Its maximum observed discrepancy is 0.552791%. Direct reactions
balance to the exported precision. At 2% the infinitesimal-reference difference
is 2.2454%; this higher stage was prospectively a finite-deformation diagnostic,
not an infinitesimal acceptance test. Spatial stress and nominal stress use
different area conventions as the plane-stress specimen deforms.

## F. Contact rectangle benchmark

Two rigid TARGE169 line targets with pilot controls oppose specimen CONTA172
surfaces. They share real sets 2 and 3 respectively. The lower pilot is fixed;
the upper pilot moves downward with UX/ROTZ fixed. The specimen has only one
UX anchor. Both pairs are frictionless, permit separation and use standard
KEYOPT(12)=0, augmented Lagrange and Gauss-point detection. No bonded contact,
weak springs or contact damping were substituted. Geometric normals, actual
initial gap/contact checks and successful force transmission agree.

The default first contact attempt converged but was rejected: its automatic
penetration tolerances were about 0.054–0.058 mm, force at 0.5% was 48.780826 N,
and maximum element-averaged penetration at 2% was about 0.00517 mm. Its input,
raw logs, RST and QUARANTINE.json remain. A prospective correction was committed
before rerunning: retain FKN=1 and specify absolute FTOLN=1e-7 mm. The actual
solver printout confirms that tolerance and an automatically computed initial
contact stiffness of 2e10. Thus retaining FKN did not retain the old absolute
stiffness. The coefficient-ratio >1e8 warning is explicitly retained.

The corrected run converged at all 36 saved sets. CNCHECK found both pairs
initially closed, initial penetration 0 and 3.55e-15 mm. At the last stage all
40 contact elements are closed/sliding (20 per pair), and both interfaces
transmit compression. Maximum reaction-equilibrium residual over saved sets is
0.020469% (registered limit 1%). Maximum stored endpoint pressure is 20.202709
MPa, and maximum stored endpoint penetration is **1.0101354e-8 mm**. Actual total
contact-element force magnitudes agree with pilot reactions within 7.02e-8
relative difference. The reported contact-element CNFY sums have the opposite
sign to the corresponding support RF, consistent with internal resisting-force
versus support-reaction conventions; both original signed columns are retained.
A second independent licensed run has identical history
CSV bytes. This is repeatability evidence, not contact sensitivity or convergence.

## G. Mechanical output extraction

Raw history contains actual set, load step, substep, pseudo-time, platen UY and
signed reactions. Derived CSVs include force_displacement, stress_strain,
reaction_balance and contact_diagnostics. Nominal compression strain is
-UY/H; nominal compression stress is -upper_RF/(initial W × initial t).
Pseudo-time is a load parameter, never physical seconds. Zero is initial
geometry/CNCHECK, not a fabricated zero-load solution row.

The first exporter queried unavailable midside stresses and retained stale
parameters. Those fields are invalid and unused. The corrected exporter saves
actual UX/UY for all 617 nodes and stress/elastic strain only at the 175 corner
nodes. No midside stress was invented. Vertical and equivalent stress, vertical
and lateral elastic strain and true-scale deformation were obtained. The
through-origin stiffness fit over achieved 0<strain<=0.005 gives 1004.3572 MPa
direct and 1004.3571 MPa contact (base modulus 1000 MPa).

CONT ETABLE values are element averages; the original summaries' maximum-contact
labels mean the maximum across those element averages. The supplemental real
RST reader independently exports endpoint pressure, signed gap/penetration and
total contact force via SMISC1/2 and NMISC5/6/22. The pointwise figures/report use
those stored endpoint values. They are not an exhaustive continuous-surface
penetration bound. Receipt-linked original RST and CSV hashes are retained.

Five inspected composite figures cover the requested mesh/setup/contact,
deformation/displacement/stress/strain, force/reference/stress–strain,
penetration/contact-force and convergence panels. Numerical fields accompany
the images. Figures are generated from genuine solver data, not assumed fields.

## H. Microstructure import

The Design 9, seed 1 native-1024 source was authenticated without regenerating
or modifying it. Source WKB SHA256 is
4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1;
412 pores and 50.0104 mm² solid area were confirmed in source geometry.

The selected fine_new manifest records semantic mesh SHA256
e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc,
2,766,505 nodes and 1,261,670 TRI6. Its generated/mesh.npz is absent; the
repository search found only newly generated rectangle meshes. Therefore the
fine mesh itself was NOT AUTHENTICATED, NOT IMPORTED and NOT SOLVED here.
The recorded counts and source pore count are not actual solver-import counts.
No smaller/rejected mesh was substituted.

## I. Resource feasibility

The recorded model has 5,533,010 unconstrained translational DOFs before contact.
Coordinate/TRI6 arrays alone require about 104.8 MB; one displacement field
about 44.3 MB; three checkpoint displacement fields about 132.8 MB. Naively
storing 144 double-valued stiffness contributions per triangle is about 1.45
GB before indices/assembly. These are storage calculations, not predictions of
sparse factorization, contact workspace or complete result-file size. Full
solver memory, disk, runtime and licensing feasibility remain UNQUALIFIED.
The computer is not declared capable or incapable without model-specific evidence.

Observed bounded direct and accepted-contact launches took 8.73 and 9.16 s;
contact repeat took 9.19 s. Highest sampled solver-tree RSS among supervised
benchmark solves was 321,060,864 bytes (rejected default contact); accepted
contact reached 314,470,400 bytes. Workbench/Mechanical probe took 48.54 s,
peak sampled tree RSS 1,242,058,752 bytes. These are sampled process-tree
measurements, not exact OS lifetime peaks. The initial legacy smoke took 14.39
s without a measured RSS. Audit-to-report elapsed time is in the JSON report.

## J. Microstructure pilot

**BLOCKED — NOT ATTEMPTED.** First failed prerequisite: authenticated selected
mesh bytes are unavailable. No full import, pilot protocol, converged stage,
microstructure force, stiffness, deformation or stress–strain curve exists.
mechanical_feedback.json explicitly distinguishes missing input/resource
qualification from a physically poor design. Rectangle response is not assigned
to the microstructure or made eligible for design ranking.

## K. Internal self-contact

**UNQUALIFIED_NOT_CONFIGURED_NOT_DEMONSTRATED.** Candidate pair-based/general
contact capabilities and nonadjacent-surface exclusions are documented in the
next-milestone handoff. No initially separate deformable surfaces were shown
to engage internally. Platen qualification does not establish self-contact.

## L. Independent acceptance and scientific limitations

| Category | Decision |
|---|---|
| A WINDOWS_ENVIRONMENT | PASS |
| B LICENSED_SOLVER | PASS actual finite-element execution |
| C AUTOMATION | PASS MAPDL; Workbench/Mechanical scripting probe also passed |
| D MESH_TRANSFER | PASS small rectangle only |
| E DIRECT_RECTANGLE | PASS registered domain |
| F PLATEN_CONTACT | PASS empirical registered rectangle |
| G MECHANICAL_RESULTS | PASS rectangle only |
| H MICROSTRUCTURE_IMPORT | NOT EXECUTED: missing mesh bytes |
| I MICROSTRUCTURE_RESOURCE | UNQUALIFIED |
| J MICROSTRUCTURE_PILOT | BLOCKED / NOT ATTEMPTED |
| K INTERNAL_SELF_CONTACT | UNQUALIFIED |
| L MECHANICAL_MESH_CONVERGENCE | UNQUALIFIED |
| M PAPER_READINESS | UNQUALIFIED / RESEARCH_HOLD |
| N LLM_FEEDBACK_LOOP | NOT IMPLEMENTED |
| O MANUFACTURING | UNQUALIFIED |

Material, dimensions and plane stress are provisional; there is no experimental
calibration, failure/yield validation, mechanical refinement study, contact
sensitivity study or manufacturing qualification. The finite homogeneous
benchmark is not a porous-material result. Tight contact tolerance produces
a conditioning warning. Installed-release help review remains incomplete.
Prior cumulative small-pore fidelity HOLD remains. No autonomous optimization,
batch mechanical comparison or 3D workflow was implemented.

Final active suite: **631 passed**, zero failures/errors/skips/deselections,
67.06 s console runtime. Real solver-evidence integration: **5 passed**,
reported separately from unit controls. Broad native archive discovery:
468 passed / 7 failed from missing snapshot-relative fixtures/source context.
The first fixture replay retained 2 context failures. The completed unchanged-test
replay passed **475/475**; those overlapping archived cases are not added to the
unique active count. The historical 421 inventory omitted four geometry modules
present now (198 cases); 12 v0.6.2 unit cases account for 421+198+12=631. The
missing historical 457-test inventory is not claimed restored. Raw failures,
JUnit, collection logs, replay source hashes and reconciliation are saved.

## M. Git commits and preservation

Started clean on master at 4e261f3. All completed changes are additive to the
new milestone except tested solver discovery/supervision, archive portability
and optional dependency/attribute updates. Generators, frozen evaluators,
canonical sources, geometry implementation and v0.6/v0.6.1 artifacts remain
unchanged under the saved preservation diff. No solver databases, RST binaries,
license files or installation files are tracked. No push occurred.

The JSON report lists all preceding commit hashes/messages. The final reporting
commit is the commit containing this report; its exact hash is provided in Git
history and the final chat handoff, avoiding a self-referential commit hash.

## N. Next milestone

Retrieve the original selected fine mesh and authenticate its bytes/semantic
hash. Perform a real import-only inventory, measure model-specific resource and
license-size feasibility, then prospectively register one bounded conservative
platen-contact microstructure pilot. Before controlled multi-design comparison
or a paper dataset, resolve refinement/contact sensitivity, internal-contact
requirements, provisional assumptions and scientific HOLDs. Before an LLM
iteration, review the feedback contract and invalid-result handling. Stop before
batch FEM, autonomous optimization or 3D work.

See docs/pipeline_v0.6.2/WINDOWS_EXECUTION.md for reproducibility and
INTERNAL_CONTACT_AND_NEXT_MILESTONE.md for the separate self-contact gate.
