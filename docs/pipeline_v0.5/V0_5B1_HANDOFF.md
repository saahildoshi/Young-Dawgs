# v0.5B1 handoff

Authoritative results:
`experiments/pipeline_v0.5/simplification_sensitivity/run_002`.
Read `SIMPLIFICATION_SENSITIVITY.md` in this documentation directory for the
scientific interpretation and the run's `summary/SIMPLIFICATION_SENSITIVITY.md`
for complete primary tables and threshold sequences. The final authority for
completion is `verification/COMPLETION.json`; the earlier sweep JSON records
the execution-stage status before report and regression completion.

## Implementation map

All implementation is additive in `metamaterial_eval/geometry/sensitivity/`:

| Module | Responsibility |
|---|---|
| `__init__.py` | Isolated experimental namespace |
| `simplification.py` | Immutable independently constructed diagnostic candidates |
| `sources.py` | Saved accepted source loading and ledger/hash authentication |
| `distance.py` | Indexed bidirectional boundary sampling and continuous bounds |
| `metrics.py` | Complexity, validity, actual Boolean area, region correspondence and raster comparisons |
| `features.py` | Fixed repair ROIs, original patch retention, relevant clearance, local links and neck probes |
| `morphology.py` | Frozen native evaluator interface, bounded authenticated descriptor cache and comparisons |
| `analysis.py` | Independent A/B/C candidate evaluation and tri-valued diagnostic flags |
| `records.py` | Append-only candidate serialization and discrete/non-monotonic threshold sequences |
| `study.py` | Register, characterize, run and report CLI with immutable code snapshots |
| `reporting.py` | Detailed tables, interpretation JSON and eleven main figures |

Reused unchanged: `geometry.planar.rasterize_exact_geometry`,
`geometry.manifold.contacts.inspect_boundary` / `polygon_rings`, raster/topology
helpers, `geometry.reporting` environment/inventory functions, the established
`pipeline.evaluator` loader and `pipeline.resolution_worker.evaluate_native`.
Source audit also checked the earlier comparison/neck utilities; new continuous
simplification diagnostics are isolated rather than changing their definitions.
The frozen v1.1 evaluator and procedural generators are unchanged.

`tests/test_simplification_sensitivity.py` adds 29 tests. All 316 project tests
passed. Full JUnit and command/environment details are retained in verification.
The run-local `verification/supplemental_analysis.py` reads completed records to
check direct GEOS worst-point distances, compare retained runs, flatten morphology/
neck/performance tables and render Figures 12–14. It does not generate candidates,
change metrics or implement the proposed protected simplifier. Figure QA fixed
the supplemental Figure 13 rendering; frozen study code was not edited.

## Reproduce a fresh study on macOS

Start in the canonical repository root. Use the recorded environment versions in
run_002/environment.json. The tested interpreter is `.venv-macos/bin/python`.
The example fresh output below must not already exist; choose another unused
run ID if needed. Never remove or overwrite retained experiments to rerun them.

```sh
.venv-macos/bin/python -m metamaterial_eval.geometry.sensitivity.study register --output-dir experiments/pipeline_v0.5/simplification_sensitivity/run_003
.venv-macos/bin/python -m metamaterial_eval.geometry.sensitivity.study characterize --output-dir experiments/pipeline_v0.5/simplification_sensitivity/run_003
.venv-macos/bin/python -m metamaterial_eval.geometry.sensitivity.study run --output-dir experiments/pipeline_v0.5/simplification_sensitivity/run_003
.venv-macos/bin/python -m metamaterial_eval.geometry.sensitivity.study report --output-dir experiments/pipeline_v0.5/simplification_sensitivity/run_003
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py .venv-macos/bin/python -m pytest tests validation/test_evaluator.py -q
```

Register freezes the protocol, source identities, relevant code and repository
inventory before characterization. Characterize must complete before run. Run
refuses to resume or overwrite an existing execution; partial evidence must be
retained and a fresh run registered. Code changes require a fresh registration.
Report runs from the repository root because saved source paths are repository
relative. All metric JSON/WKB/npy artifacts remain diagnostic, never production
selected geometry.

## Windows commands — documented, not executed

In PowerShell at the repository root, use a Python environment matching the
recorded package versions. These commands are a reproduction procedure; the
verified run was macOS ARM64. Windows RSS may be unavailable and is reported as
null rather than invented.

```powershell
python -m metamaterial_eval.geometry.sensitivity.study register --output-dir experiments/pipeline_v0.5/simplification_sensitivity/run_windows_001
python -m metamaterial_eval.geometry.sensitivity.study characterize --output-dir experiments/pipeline_v0.5/simplification_sensitivity/run_windows_001
python -m metamaterial_eval.geometry.sensitivity.study run --output-dir experiments/pipeline_v0.5/simplification_sensitivity/run_windows_001
python -m metamaterial_eval.geometry.sensitivity.study report --output-dir experiments/pipeline_v0.5/simplification_sensitivity/run_windows_001
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest tests validation/test_evaluator.py -q
```

## Artifact and stage boundaries

The run retains five complete baseline/provenance records, 40 primary candidates,
three separately labeled negative controls, geometry and raster hashes, full
metrics/descriptor comparisons, fourteen inspected figures, CSV tables, source
snapshots, timing/memory records and explicit undefined reasons. The first run
is retained with COVERAGE_NOTE.md explaining the aggregate-reporting correction.
The complete new-file/hash inventory and unchanged historical-file verification
are in `verification/new_files.json`, `CHANGES.md` and `PRESERVATION.json`.
Inventories exclude Git metadata, virtual environments, Python/pytest caches and
editable-install metadata, consistent with the initial repository snapshot.

No dependencies, existing shared interfaces or historical files were edited.
Pre-existing local changes relative to Git are preserved, not reset. The exact
v0.5A HOLD and scoped v0.5A.1 amended PASS remain unchanged. Before v0.5C,
implement and qualify an explicitly authorized protected simplifier under a
prospectively frozen B2 protocol, then separately specify and test 2D export.
See `V0_5B2_DESIGN_RECOMMENDATION.md` for the proposed architecture and tests.
No B2, C, D, CAD, physical scaling, FEM or manufacturing qualification is included.
