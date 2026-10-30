# v0.6.5 execution and evidence replay

The single full recovery run is complete. Do not run another full solve for
this milestone. Source jobs and read-only postprocessors exited normally.

Use the repository environment in PowerShell:

```powershell
$env:EVALUATOR_PATH = 'validation/evaluators/evaluator_v1_1.py'
.\.venv\Scripts\python.exe -m pytest -q tests validation/test_evaluator.py
.\.venv\Scripts\python.exe -m pytest -q validation/ansys_v065_integration.py
```

Actual results: 784 active passes, 475 archived fixture replay passes and20
explicit licensed evidence passes. Counts overlap; do not sum them. The
explicit licensed suite reads saved actual ANSYS data and launches no solver.
Synthetic health/unit controls do not count as licensed execution evidence.
Archive replay procedure: scripts/replay_geometry_archives.py, with a new
unique output directory; existing logs/manifests are preserved under
experiments/pipeline_v0.6.5/run_001/verification/archive_replay.

## Native artifact locations

`metamaterial_eval.simulation.mesh_artifacts.artifact_root()` resolves the
large-artifact root; `YD_ARTIFACT_ROOT` selects a portable store. The desktop
app may virtualize LOCALAPPDATA into its package cache. Use the resolver
rather than guessing the physical path. Jobs are under solver/v065:

- full_recovery_001: source solve, RST, MODEL-only DB and final restart frame.
- full_recovery_001_post: first independent read-only native export.
- full_recovery_001_repeat: separate read-only repeated extraction.
- full_recovery_001_qualified: streamed/memory-mapped scientific field arrays.

Keep raw RST, DB/RDB/Rnnn, NR files, large CSVs and NPY arrays outside Git.
Compact metadata carries exact byte/hash provenance. Restoring native files
requires their original hashes. Frozen source decks contain authenticated
absolute paths; do not rewrite them to relocate a run. A future reproduction
needs a new directory/protocol and fresh bindings to the same native hashes.

## Procedures and safeguards

scripts/v065_recovery.py preserves small, prepare-full, execute-full and
extract-full procedures. Existing process directories refuse execution again.
The full input/protocol were committed before launch. The new job explicitly
passes rss_limit=None and min_available_ram=0, replacing the old immediate
process/reserve rules with sustained actual-system-health safeguards.
Legacy caller defaults remain backward compatible and historical jobs are
unchanged. No pagefile or unrelated application settings were modified.

The emergency policy records native Windows commit, available physical memory,
low-memory notification, Page Reads/sec hard-fault disk-read proxy, disk,
file growth and owned child status. Transient memory lows reset after recovery.
Exact durations and limits are frozen in FULL_RECOVERY_001.json. The successful
source process peaked at18.5923GiB; no claim of actual>20GiB use is made.

Read-only export uses a MODEL-only DB and native SET1,1, without SOLVE or SAVE.
APDL vectors are bounded to250000nodes. Python streams100000rows and checks
20000TRI6 mappings per chunk; native field arrays are memory mapped.
Reactions and contact signs are preserved, with positive compression magnitudes
calculated separately. Stress/strain are supported corner-node averages only.

The accepted result is one0.005% point. It is not a complete curve or fitted
modulus. Contact/mechanical mesh sensitivity, internal self-contact, physical
calibration, paper/manufacturing readiness and LLM ranking remain unqualified.
See the six scientific reports in experiments/pipeline_v0.6.5/run_001.
