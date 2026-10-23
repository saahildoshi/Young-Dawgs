# v0.5C.1 execution and reproduction boundaries

The actual execution uses macOS ARM64 and the repository's .venv-macos Python.
Full software versions and GEOS version are saved in protocol/environment.json.
Windows syntax below is documentation only, not a Windows result.

Commands used for the registered first study, from the repository root:

```sh
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py .venv-macos/bin/python -m pytest tests validation/test_evaluator.py -q
.venv-macos/bin/python -m metamaterial_eval.geometry.protected_v2.study root-cause
.venv-macos/bin/python -m metamaterial_eval.geometry.protected_v2.study regression
.venv-macos/bin/python scripts/pipeline_v0_5c1_pore_policy.py
.venv-macos/bin/python -m metamaterial_eval.geometry.protected_v2.study freeze
.venv-macos/bin/python -m metamaterial_eval.geometry.protected_v2.study holdouts
.venv-macos/bin/python scripts/pipeline_v0_5c1_compare.py
.venv-macos/bin/python scripts/pipeline_v0_5c1_report.py
```

Freeze authenticates the corrected and frozen producer code before new native
sources are opened. Execution markers reject overwriting regression or holdout
phases. These commands record the original first-creation procedure; do not
rerender the now-existing canonical holdout masks in another directory. To
recheck results, authenticate source and candidate hashes, load persisted G0–G3,
and call the versioned engine or independent checks on those same sources in a
separate derivative study. A changed algorithm needs a newly reserved cohort.

The root_cause directory preserves the full original B2 WKB/engine and revised
counterpart. Reproduction of the original behavior does not revise its historical
failure. `algorithm_version` snapshots the corrected and reused code, while
`protocol/FINAL_FREEZE.json` hashes the final settings, source code and regression
summary before independent generation. `verification/new_files.json` authenticates
all final additions and `PRESERVATION.json` compares every initial file.

Full regression on Windows, if a matching environment is separately prepared:

```powershell
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest tests validation/test_evaluator.py -q
```

Cross-platform byte identity has not been executed or established. All geometry
units remain native raster cells; no physical scaling, export or CAD contract is
introduced by these commands.
