# Windows evidence replay and final HOLD

The completed v0.6.4 milestone ends after the primary run and its single
preregistered conditional technical repair. Do not execute another full solve
from these scripts. A future solve needs a separate reviewed protocol.

Use the repository Python environment and keep native solver data outside Git.
`metamaterial_eval.simulation.mesh_artifacts.artifact_root()` resolves the local
artifact store. `YD_ARTIFACT_ROOT` selects a portable replacement. Native jobs
are under `solver/v064`; durable copies also exist under
`C:/Users/sd22446/YoungDawgs-Artifacts`. The desktop app may virtualize
LOCALAPPDATA; use the resolver rather than guessing the physical package path.
Raw RST/DB/RDB/NR files are large and must not be staged or committed.

## Replay existing evidence

From the repository in PowerShell:

```powershell
$env:EVALUATOR_PATH = 'validation/evaluators/evaluator_v1_1.py'
.\.venv\Scripts\python.exe -m pytest -q tests validation/test_evaluator.py
.\.venv\Scripts\python.exe -m pytest -q validation/ansys_v064_integration.py
```

The active suite has 744 passing tests. The explicit licensed evidence suite
has 16 passing checks and one retained mechanical-acceptance failure. It reads
actual saved ANSYS output; it does not launch a fresh solve. Missing native
artifacts prevent replay and must not be replaced by synthetic fixtures.
Archived fixture replay results are separately recorded under
`verification/archive_replay` (475 passes; counts overlap with active tests).

`scripts/v064_small_study.py`, `v064_recovery.py` and
`v064_checkpoint_repair.py` retain the executed procedures. Their prepare and
execute operations create new native jobs and are not part of read-only
replay. Inputs, hashes, resource caps and prospective amendments are recorded
under `experiments/pipeline_v0.6.4/run_001/protocol`.
`scripts/report_v064.py:write_reports` builds reports from existing evidence;
its default entry point regenerates diagnostic figures only.

## Interpretation

Both full runs announced nonzero equilibrium at 0.005% strain after seven
Newton updates. The 20-GiB guard stopped them during the next factorization
or result output. The conditional RST has a readable displacement field;
reactions, contact-element results, stress and elastic strain are missing.
Read-only export return code zero does not qualify those missing fields.
Ignored queries produced zero/sentinel arrays, which are quarantined.

Final status is
`NATIVE_NONZERO_EQUILIBRIUM_RECOVERED__RESOURCE_AND_OUTPUT_QUALIFICATION_HOLD`.
There are no mechanically accepted checkpoints, no modulus, no stress–strain
curve and no performance score. Inspect the six run reports, validation JSON,
quarantine record, native hashes and figure manifest before interpretation.
The next milestone is a bounded memory/output diagnostic, followed by proof
of complete native-field capture. Existing geometry and scientific HOLDs,
including mechanical mesh convergence and internal self-contact, remain.
