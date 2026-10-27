# v0.6.1 Windows rectangle execution packet

Windows and ANSYS execution have NOT been performed in this session. Templates
remain DRAFT_UNVERIFIED. The current blocker is no accessible solver; no license
checkout was attempted. The corrected full fine mesh is geometrically accepted,
but do not launch its roughly5.53million translational DOFs before rectangle,
license, memory/disk and prospective pilot checks pass.

## Setup and actual release review

From a repository checkout, use Python3.12 (Linux-tested version) or another
compatible Python supported by the installed packages and ANSYS release.

```powershell
py -3.12 -m venv .venv-fem
.\.venv-fem\Scripts\Activate.ps1
python -m pip install -e . pytest
python -m pip install -r requirements-v0.6.txt
$env:EVALUATOR_PATH = 'validation/evaluators/evaluator_v1_1.py'
python -m pytest tests validation/test_evaluator.py -q
```

Set ANSYS_EXECUTABLE to the actual licensed MAPDL executable path, and
YD_ANSYS_RELEASE to its expected release, for example2026 R1 only if that release
is actually installed. No source-file edits or confidential license information
are needed. Do not commit license files, server credentials or installation files.
AWP_ROOT release selectors and supported executable names are also discovered.
A configured file path is not proof of a working solver/license.

```powershell
python -m metamaterial_eval.simulation.ansys_qualification environment `
  --smoke --expected-release $env:YD_ANSYS_RELEASE `
  --output experiments/pipeline_v0.6.1/ansys_environment/windows_001
```

This records discovery and, if an executable is found, attempts a bounded120s
licensed direct rectangle. Missing executable, license failure, version mismatch,
timeout and output failure are separate states. A recognized-release completed
run establishes observed execution only; it does not establish model acceptance.

Consult official element/contact/command documentation for that exact release.
Review PLANE183 six-node triangle ordering and KEYOPT(1)=1, plane-stress/strain
KEYOPT(3), thickness/force units, CONTA172/TARGE169 normal/target association,
pilot DOFs, finite sliding, stiffness defaults, contact result items and all
export commands. Do not infer compatibility from a different-release example.

## Generate matched small benchmarks

Use unique output IDs; every command refuses an existing run/output directory.

```powershell
python -m metamaterial_eval.simulation.ansys_qualification prepare `
  --output experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001
```

The packet has generated/direct and generated/platen_contact, with the same
10.24mm rectangle, provisional E/nu/thickness, mesh and four small-strain targets.
ANALYTICAL_reference.csv is not solver data. Static lint is not ANSYS import.
Use --mode plane_strain for a separate unit-depth benchmark, not a mixed curve.

## Direct solve, extraction and qualification first

```powershell
python -m metamaterial_eval.simulation solve `
  --input experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/direct `
  --output experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/direct_execution

python -m metamaterial_eval.simulation postprocess `
  --input experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/direct_execution `
  --output experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/direct_results
```

Copy MODEL_REVIEW_TEMPLATE.json to a separate direct review file. Record the
actual solver_status.json SHA256 (Get-FileHash -Algorithm SHA256), actual release,
and observations from model_inventory.txt NLIST/ELIST/material/real-constant/
component/DOF listings plus solver output. All flags begin false. Mark an item
verified only after inspecting the actual model; for direct contact-specific
items, verify the intended absence of contact. Record the release documentation
used. This is scientific model verification, not an approval inferred from lint.

```powershell
python -m metamaterial_eval.simulation.ansys_qualification qualify `
  --execution experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/direct_execution `
  --numeric-results experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/direct_results `
  --review direct_model_review.json --expected-release $env:YD_ANSYS_RELEASE `
  --output experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/direct_qualification
```

A SOLVER_VERIFIED report requires authentic clean execution, matched release,
complete model review, raw/derived numerical agreement, achieved targets,
force equilibrium and analytical agreement. A partial/failed result may be
retained, but cannot qualify the final benchmark. Never alter failed data to fit
an analytical curve.

## Platen contact only after direct qualification

```powershell
python -m metamaterial_eval.simulation solve `
  --input experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/platen_contact `
  --output experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/contact_execution `
  --benchmark-evidence experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/direct_qualification/qualification.json

python -m metamaterial_eval.simulation postprocess `
  --input experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/contact_execution `
  --output experiments/pipeline_v0.6.1/rectangle_benchmarks/windows_001/generated/contact_results
```

Inspect and record a new contact_model_review.json linked to the contact receipt,
including both actual normals/initial gaps, contact/target associations, active
status, pressure, force transfer, penetration and equilibrium. Qualify it with
these contact execution/results/review paths and a new contact_qualification
output directory, using the same qualify command. Do not reuse the direct receipt
or review. Missing contact rows and incomplete inventories are failures.

## Outputs and troubleshooting

Preserve solver.out, launcher.log, model_inventory.txt, compression.rst,
history.csv, nodal_fields.csv, contact_fields.csv for contact, mesh.npz,
input_manifest.json and solver_status.json. Actual CSV curves and fields come
from postprocess, never screenshots or analytical values. Pseudo-time is a load
parameter, not physical seconds. Failed/unverified data are quarantined and
unconverged sets excluded; original raw results are retained. Local stress peaks
at corners are not automatically converged.

The equivalent raw MAPDL call is -b -j compression -i compression.inp
-o solver.out -np 1. Use the Python runner for receipts; raw invocation alone
cannot satisfy the qualification chain. If no executable is found, correct
ANSYS_EXECUTABLE/AWP_ROOT/PATH. If licensing fails, use the organization's
configured license mechanism; never put keys or secrets in Git. For syntax,
element, contact or output errors, preserve logs and review the actual release;
do not disable contact or replace it with specimen displacement constraints.

Do not advance a failed direct case to contact. Do not advance a failed contact
case to a porous pilot. A future pilot needs a separately frozen protocol tied
to the accepted fine mesh, actual benchmark evidence, solver/license/memory/disk
capacity and conservative loading. Internal self-contact and mechanical mesh
convergence remain separate unqualified objectives. No batch FEM,3D or autonomous
LLM optimization is part of this packet.
