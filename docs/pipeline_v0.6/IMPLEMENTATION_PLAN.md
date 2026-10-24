# Pipeline v0.6 implementation and evidence plan

The current priority is a reproducible, actual 2D contact-enabled compression
pipeline. Historical 3D plans are deferred. This is a separate engineering proof
of concept; it does not advance historical scientific or manufacturing status.

## Audit checkpoint, 2026-10-24

Repository branch `work`, initial HEAD
`b92dc0afbe08e1858f65ea0e41fa471f038cac55`; clean working tree; no prior AGENTS.md.
Read README, package/dependency/test conventions, v0.5 architecture, manifold
qualification/contact analysis/policy, scientific architecture/protocol and
small-pore qualification pointer. Inspected geometry serialization, rasterization,
source manifests, generator interfaces, manifold diagnostics and tests.

Important snapshot discrepancy: this checkout has the C/C.1 documentation, but
its referenced scientific_validation/scientific_requalification runs and protected
simplification implementation/artifacts are absent. Their reported acceptance
cannot be reauthenticated here. Preserve the stated cumulative-small-pore HOLD;
do not substitute a simplified candidate or reconstruct missing history.

Select saved native1024 Design 9 / seed 1 and its run_003 exact WKB. Authenticate
NPY, PNG, raw pixels, source manifest and generator fingerprints; independently
rasterize the WKB and inspect manifoldness. It has 412 holes and 500104 cell²
solid area, no subpixel regularization, and a saved 15-pixel generator topology
repair. Reuse those exact artifacts without regeneration or geometric repair.

Linux x86_64, Python 3.12.14. Existing .venv has NumPy, SciPy, Shapely 2.1.2,
Matplotlib and pytest. No ANSYS executable on PATH or conventional installation
locations, Workbench/MAPDL/PyMechanical/PyMAPDL absent. License checkout cannot be
tested without a solver. No remote solver endpoint or credentials configured.
Install isolated Gmsh 4.15.0 for native 2D meshing. ANSYS import, license, contact,
solve, mechanical fields and response convergence remain NOT VERIFIED.

Official v261 ANSYS element help and Gmsh web manual requests returned proxy
403 (restricted network). Use installed Gmsh public API documentation and exercise
it in tests. APDL decks remain reviewable DRAFT_UNVERIFIED until commands and
contact/thickness behavior are reviewed against the actual Windows release and
rectangle benchmark. No claim of matching an installed ANSYS version is possible.

## Coherent checkpoints

1. Commit persistent instructions, this audit and implementation plan.
2. Add authenticated geometry adapter, explicit y-up/mm transform, deterministic
   hole-aware Gmsh mesh, boundary groups and independent mesh/feature screens.
   Synthetic holes, necks and adverse mesh controls precede real geometry.
3. Add draft APDL continuum transfer, direct/contact rectangle inputs and pilot
   inputs, preflight/runner, contact construction checks and strict result gates.
   Investigate internal contact; never claim unexecuted self-contact qualified.
4. Add evidence-gated metrics/feedback interfaces, prospective refinement and
   reporting, diagnostic figures, full regression and historical preservation.

Freeze prospective modeling protocol before microstructure meshing/input
preparation. Never launch a microstructure solve before rectangle import,
material, platen engagement and required internal-contact evidence passes.
Use unique output paths, retain failures, quarantine invalid results and keep
large generated meshes/decks/solver output ignored and reproducible.
