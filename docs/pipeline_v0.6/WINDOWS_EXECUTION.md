# Windows execution and release review

Current stop: the final registered refinement fails the10° angle gate (8.275°).
No microstructure input or solve is authorized by these numerical gates. Preserve
run_003 and freeze a new protocol revision before investigating a new mesh setup.
A passing medium mesh does not override the failed refinement. Separately, this
Linux checkout has no ANSYS installation, license checkout or real solver result.

## Prepare a Windows environment

Use Python3.10 or newer and a separately installed, licensed ANSYS MAPDL. Record
its actual release, executable path and applicable license checkout. A Python
ANSYS package is not a solver license. No PyMechanical/PyMAPDL service is required
by the batch adapter. Do not copy license files into this repository.

```powershell
py -3.10 -m venv .venv-fem
.\.venv-fem\Scripts\Activate.ps1
python -m pip install -e . pytest
python -m pip install -r requirements-v0.6.txt
$env:EVALUATOR_PATH = 'validation/evaluators/evaluator_v1_1.py'
python -m pytest tests validation/test_evaluator.py -q
```

Consult the official documentation matching the installed release. Review the
TRI6 connectivity and PLANE183 KEYOPT(1)=1, KEYOPT(3)=3/2, thickness real constant,
CONTA172/TARGE169 compatibility, contact normals, pilot coupling/DOFs,
finite-sliding defaults, automatic normal stiffness, contact force/thickness
scaling, penalty penetration, result item names, SET/NSET and field export.
The local transfer lint is a record roundtrip, not an ANSYS parser. In particular,
plane-stress contact total-force scaling needs actual thickness-sensitivity tests.
Do not infer correct import/material from element counts alone.

## Rectangle execution first

Generate a unique run. Existing directories are refused.

```powershell
python -m metamaterial_eval.simulation benchmarks `
  --output experiments/pipeline_v0.6/ansys_benchmarks/windows_001

$mapdlExe = 'C:\Program Files\ANSYS Inc\v261\ansys\bin\winx64\ANSYS261.exe'
python -m metamaterial_eval.simulation solve `
  --input experiments/pipeline_v0.6/ansys_benchmarks/windows_001/generated/plane_stress_direct `
  --output experiments/pipeline_v0.6/ansys_benchmarks/windows_001/generated/direct_execution `
  --executable $mapdlExe

python -m metamaterial_eval.simulation solve `
  --input experiments/pipeline_v0.6/ansys_benchmarks/windows_001/generated/plane_stress_contact `
  --output experiments/pipeline_v0.6/ansys_benchmarks/windows_001/generated/contact_execution `
  --executable $mapdlExe

python -m metamaterial_eval.simulation postprocess `
  --input experiments/pipeline_v0.6/ansys_benchmarks/windows_001/generated/contact_execution `
  --output experiments/pipeline_v0.6/ansys_benchmarks/windows_001/generated/contact_results
```

The v261 path is an example, not a detected installation. The equivalent raw
batch command, from the generated input directory, is:

```powershell
& $mapdlExe -b -j compression -i compression.inp -o solver.out -np 1
```

Use the Python runner for receipts and output hashes. Direct invocation alone
does not create authenticated workflow receipts. Preserve launcher.log,
solver.out, model_inventory.txt, compression.rst, history.csv, nodal_fields.csv,
contact_fields.csv and solver_status.json. Large raw files stay in generated/.
An absent executable, license denial, nonzero return code, solver errors,
timeout and missing output produce separate failure states. Return code zero is
never a mechanical PASS. A failed run may retain earlier converged sets.

Compare NLIST/ELIST/CMLIST/DLIST, material/real-constant listings and dimensions
against the source manifest, nodes and connectivity. Verify every 2D material
assignment, hole, contact edge, normal, pilot DOF and reaction. Demonstrate active
upper/lower contact with positive pressure, balanced reactions within1%, maximum
penetration≤0.001mm and benchmark stiffness error≤2% at small strain. Compare
frictionless/unconstrained infinitesimal plane-stress E and plane-strain
E/(1-nu²); do not equate all finite-deformation points with this linear reference.
The shipped analytical CSV is explicitly not an ANSYS result.

Postprocessing validates output hashes, requires solver convergence-log evidence,
checks reaction signs and balance, checks actual active contacts/penetration,
and screens node/element counts and field completeness. Failed numeric screens
write data under quarantine/. Full import/material review remains manual and
must be retained as evidence. No automatic LLM performance eligibility is granted.

## Blocked microstructure and internal-contact stages

The `input` command reauthenticates source and mesh bytes, reruns independent
mesh/feature gates and refuses a parent run containing FAILURE.json. Do not
remove that failure file to proceed. After a newly registered passing study:

```powershell
python -m metamaterial_eval.simulation input `
  --mesh-level experiments/pipeline_v0.6/mesh_validation/NEW_PASSING_RUN/level_02 `
  --output experiments/pipeline_v0.6/microstructure_compression/NEW_RUN/generated/input
```

A pilot solve additionally requires a benchmark-evidence JSON with
`import_acceptance`, `material_acceptance`, `direct_rectangle_acceptance` and
`platen_contact_acceptance` all `SOLVER_VERIFIED`, plus the actual
`solver_receipt_sha256`; supply it with `--benchmark-evidence`. These are recorded
scientific review assertions, not permission to fabricate a receipt or automatic
proof of correctness. Preserve the underlying real run and review evidence.

Internal self-contact is deliberately unconfigured and blocks advanced
compression, comparison studies and research readiness. The connected C-channel
candidate has a0.02mm gap; its opposing nonadjacent horizontal faces and adjacent
web exclusion are documented in internal_contact_candidate.json. Review the
installed-release deformable-contact approach, implement it separately, then
show gap closure, active status/pressure, limited penetration and consistent
reaction change against an otherwise identical contact-disabled internal case.
Do not infer internal contact from external platen contact.

All times are quasi-static load parameters, not physical seconds. Only actual
achieved converged strains may become snapshots or curve points. No solver
response, stiffness, energy, stress or deformation is provided by this checkout.
