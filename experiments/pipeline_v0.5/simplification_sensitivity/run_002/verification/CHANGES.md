# v0.5B1 session changes

All changes are additive. Zero of the 3,226 pre-existing inventoried files changed.

## New implementation

- `metamaterial_eval/geometry/sensitivity/__init__.py`
- `metamaterial_eval/geometry/sensitivity/analysis.py`
- `metamaterial_eval/geometry/sensitivity/distance.py`
- `metamaterial_eval/geometry/sensitivity/features.py`
- `metamaterial_eval/geometry/sensitivity/metrics.py`
- `metamaterial_eval/geometry/sensitivity/morphology.py`
- `metamaterial_eval/geometry/sensitivity/records.py`
- `metamaterial_eval/geometry/sensitivity/reporting.py`
- `metamaterial_eval/geometry/sensitivity/simplification.py`
- `metamaterial_eval/geometry/sensitivity/sources.py`
- `metamaterial_eval/geometry/sensitivity/study.py`

- `tests/test_simplification_sensitivity.py` (29 tests)

## New documentation

- `docs/pipeline_v0.5/SIMPLIFICATION_SENSITIVITY.md`
- `docs/pipeline_v0.5/V0_5B1_HANDOFF.md`
- `docs/pipeline_v0.5/V0_5B1_PLAN.md`
- `docs/pipeline_v0.5/V0_5B1_PROTOCOL.json`
- `docs/pipeline_v0.5/V0_5B2_DESIGN_RECOMMENDATION.md`

## New experimental artifacts

- `experiments/pipeline_v0.5/simplification_sensitivity/run_001/`: retained first 43 evaluations, frozen snapshots and correction coverage note.
- `experiments/pipeline_v0.5/simplification_sensitivity/run_002/`: corrected final 43 evaluations, five baselines, authenticated caches, snapshots, JSON/CSV/Markdown reports, fourteen figures and verification artifacts.

The exact file list, byte sizes and SHA-256 hashes are in new_files.json. That ledger excludes its own bytes to avoid a circular hash. Virtual environments, Git metadata and transient caches are excluded consistently with the initial snapshot.

No source generator, frozen evaluator, existing test, exact geometry, accepted manifold candidate, historical experiment or historical acceptance decision was edited. B2 protection remains a proposed architecture only.
