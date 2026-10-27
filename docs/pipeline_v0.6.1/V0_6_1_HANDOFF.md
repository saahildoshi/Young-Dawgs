# v0.6.1 handoff

Selected fine replacement is geometrically qualified; ANSYS remains blocked.
Start with V0_6_1_VALIDATION.md, its JSON and acceptance_states.csv. All66 requested
answers are in verification/request_checklist.csv. The corrected NPZ and raw
failed candidates live under ignored generated/ directories; reproduce rather
than committing these large files. Original v0.6 scientific evidence is unchanged.

## Reproduce the solver-independent study

The original saved fine mesh must exist for diagnosis/local trials. If missing,
regenerate the historical workflow at a NEW run path and authenticate its mesh
content; never overwrite historical runs or relabel regenerated data as the
original saved NPZ. The original frozen configuration and existing v0.6 CLI are
available for that purpose. The small worst-element fixture remains tracked.

Use unique output identifiers for every command:

```bash
python -m metamaterial_eval.simulation.mesh_remediation local --output experiments/pipeline_v0.6.1/mesh_candidates/NEW_LOCAL_RUN
python -m metamaterial_eval.simulation.mesh_remediation study --output experiments/pipeline_v0.6.1/mesh_candidates/NEW_FULL_RUN --local-evidence experiments/pipeline_v0.6.1/mesh_candidates/NEW_LOCAL_RUN/local_trial_summary.json
python -m metamaterial_eval.simulation.remediation_reporting --study experiments/pipeline_v0.6.1/mesh_candidates/NEW_FULL_RUN --output experiments/pipeline_v0.6.1/mesh_quality/NEW_REPORT
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py python -m pytest tests validation/test_evaluator.py -q
python scripts/replay_geometry_archives.py --output experiments/pipeline_v0.6.1/verification/NEW_ARCHIVE_REPLAY
```

The full-study worker and RSS monitor were tested on Linux. The archival replay
uses symlink-based temporary fixture roots and is Linux-tested; Windows requires
symlink rights. The dedicated Windows rectangle packet is documented separately.
No command above launches ANSYS. No unregistered parameter search or acceptance
threshold change is permitted; stop and preserve failures/resource overruns.

For repeatable standalone diagnosis, load the saved mesh with mesh_diagnosis.
load_mesh, authenticate the geometry with geometry_adapter.authenticate_fixture,
then call mesh_diagnosis.diagnose with a unique output path; see the recorded
protocol/source/mesh hashes. element_quality provides the independent corner and
TRI6 map validators. Source corner angles are90° or larger; do not repair the
geometry to hide a meshing defect.

## Next licensed milestone

Follow WINDOWS_EXECUTION.md. Set actual executable/release selectors, run the
bounded smoke, prepare/execute/inspect/qualify direct rectangle, then run real
platen contact with direct qualification evidence. Preserve actual receipts,
model listings, version, raw results and field/curve CSVs. No actual solver output
is provided by this session. Analytical51.2N is a reference, not a measurement.

Only then register a pilot tied to the corrected mesh hash/loading, verify
license/memory/disk capacity for approximately5.53million translational DOFs,
and consider one conservative porous solve. Internal self-contact requires its
own nonadjacent-surface engagement benchmark. Mechanical convergence needs
multiple independently accepted solved meshes. New coarse level remains rejected.
Historical cumulative-small-pore HOLD and all physical/material calibration
limitations remain. Stop before batch FEM,3D or autonomous LLM optimization.

Standalone saved-mesh diagnosis (choose a NEW output ID):

```python
from pathlib import Path
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.geometry_adapter import authenticate_fixture
from metamaterial_eval.simulation.mesh_diagnosis import load_mesh, diagnose
config = CompressionConfig()
geometry, mask, provenance = authenticate_fixture(Path('.'), config)
mesh = load_mesh('experiments/pipeline_v0.6/mesh_validation/run_003/level_02/generated/mesh.npz')
diagnose(mesh, geometry, provenance, config,
         'experiments/pipeline_v0.6.1/mesh_diagnosis/NEW_RUN')
```
