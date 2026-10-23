# v0.5B2 handoff — explicit protected candidates

Authoritative final study:
`experiments/pipeline_v0.5/protected_simplification/run_002`.
Read its `summary/ACCEPTANCE.md` / `.json` for every development and reserved
holdout configuration, and `verification/COMPLETION.json` for the final combined
software/preservation/figure verification. Scientific interpretation is in
`PROTECTED_SIMPLIFICATION_VALIDATION.md`. No v0.5C implementation is included.

## Algorithm and API boundary

The new opt-in `geometry/protected` package implements deterministic guarded
Douglas–Peucker on original-coordinate open chains. It preserves whole protected
segments, their endpoints, ring ownership and orientation. Eligibility is based
on saved repair metadata, 24 supported natural chord probes per fixture, the
saved top connector, all low-EDT skeleton supports, all skeleton junctions and
identified close boundary pairs. Tolerance-influenced local guards cover both
sides of each repaired clearance and the change support of neighboring chords.

`engine.simplify_protected` returns **PARTIAL_REQUIRES_QUALIFICATION**, never an
accepted output. `qualification.qualify` applies all independent global and local
gates before assigning ACCEPTED_CANDIDATE or ACCEPTED_NOOP. Unsupported input
and internal errors have distinct records. The CLI is the authenticated source,
registration, qualified-output and reproducibility entry point. Do not select a
WKB just because it exists: raw rejected candidates are deliberately retained.

| Module | Role |
|---|---|
| `settings.py` | Prospective JSON policy and finite nonnegative tolerance validation |
| `model.py` | Stable source ring/segment IDs, original-coordinate assembly and cyclic chains |
| `guards.py` | Dense risk detection, supported probes, local guards and full protected membership |
| `engine.py` | DP proposals, chord/hull/neighbor/raster/budget checks, local restoration and assembly conflict rollback |
| `qualification.py` | Independent B1 metrics, exact guarded coordinates/sets, pore IDs/areas, width/clearance gates and matched-chain displacement certificate |
| `sources.py` | Unchanged authenticated development artifacts and new additive frozen-algorithm holdout ingress |
| `study.py` | Register, development, final freeze, holdout and report execution |
| `reporting.py` | Per-setting tables, diagnostic figures and scoped acceptance |
| `__init__.py` | Explicit experimental namespace; existing production interfaces unchanged |

The run-local and script-level verification additionally records guard dimensions,
adjacent eligible chains, actual chord versus guard interactions, rejected
proposals and source segment coordinates. Full pore records carry source IDs,
source/candidate boundaries and hashes, overlap/containment and relative areas.

## Failure policy and invariants

Rejected leaf proposals retain the original subchain without another tolerance
attempt. New-chord conflicts restore implicated source chains in one batch. If
the assembled candidate fails any hard gate, retain its raw WKB/qualification and
restore all remaining changed chains once; independently qualify the baseline
fallback. An accepted no-op never relabels a rejected raw geometry as accepted.
No automatic repair, smoothing, buffering or morphology operation is performed.

The frozen protocol requires exact guard geometry, original protected segment
coordinates, defined relevant clearances/chords, zero registered width loss,
unchanged solid/hole/void identities and exterior channels, OGC and dedicated
manifold validity, exact raster/frozen-descriptor identity, <=0.25% added and
<=0.25% removed occupied area, <=0.5% symmetric redistribution and per-pore area
distortion, and a continuous displacement upper bound <=sqrt(2)/2 native cell.
The last ceiling is independent of requested ε. Conservative signed fan areas
budget proposals; actual Boolean areas are independently checked afterward.
Budgets are prospective geometric screens, not validated mechanical limits.

The displacement certificate matches each original continuous subchain with its
endpoint chord. Maximum source vertex distance to that chord bounds both
directions; unchanged chains have zero bound. Qualification independently checks
index/coordinate coverage and sampled lower distance consistency. Both manifold
and exact cumulative comparisons remain stored; raster equality does not imply
continuous equality. Frozen whole-mask P10 and its historic caveat are unchanged.

## Reproduction on the executed platform

Run from the canonical repository root in the versions recorded by environment.json.
The executed environment is macOS ARM64 with `.venv-macos/bin/python`. Choose a
fresh, nonexistent output directory; do not overwrite or resume an old execution.

```sh
.venv-macos/bin/python -m metamaterial_eval.geometry.protected.study register --output-dir experiments/pipeline_v0.5/protected_simplification/run_003
.venv-macos/bin/python -W error::RuntimeWarning -m metamaterial_eval.geometry.protected.study development --output-dir experiments/pipeline_v0.5/protected_simplification/run_003
.venv-macos/bin/python -m metamaterial_eval.geometry.protected.study freeze --output-dir experiments/pipeline_v0.5/protected_simplification/run_003
.venv-macos/bin/python -W error::RuntimeWarning -m metamaterial_eval.geometry.protected.study holdout --output-dir experiments/pipeline_v0.5/protected_simplification/run_003
.venv-macos/bin/python -m metamaterial_eval.geometry.protected.study report --output-dir experiments/pipeline_v0.5/protected_simplification/run_003
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py .venv-macos/bin/python -m pytest tests validation/test_evaluator.py -q
```

These commands reproduce an already-defined method on the same fixtures; once
holdouts have been examined, repeating them is reproducibility work, not fresh
independent evidence for a tuned algorithm. A future changed algorithm needs a
new version/protocol and fresh independently reserved samples. Do not reuse this
consumed holdout set while calling it independent after tuning.

The final record-enrichment script runs after both stages:

```sh
.venv-macos/bin/python scripts/pipeline_v0_5b2_audit.py experiments/pipeline_v0.5/protected_simplification/run_002
```

It reads candidates and writes reporting/verification artifacts; it does not
modify geometry or qualification. Its `--finalize` action requires completed
regression JUnit, all final figure inspection and documentation.

## Windows reproduction — not executed

Use PowerShell at the repository root with package versions matching the saved
environment; the original optional requirements-v0.5.txt pins Shapely 2.1.2.
No Windows verification is claimed.

```powershell
python -m metamaterial_eval.geometry.protected.study register --output-dir experiments/pipeline_v0.5/protected_simplification/windows_run_001
python -W error::RuntimeWarning -m metamaterial_eval.geometry.protected.study development --output-dir experiments/pipeline_v0.5/protected_simplification/windows_run_001
python -m metamaterial_eval.geometry.protected.study freeze --output-dir experiments/pipeline_v0.5/protected_simplification/windows_run_001
python -W error::RuntimeWarning -m metamaterial_eval.geometry.protected.study holdout --output-dir experiments/pipeline_v0.5/protected_simplification/windows_run_001
python -m metamaterial_eval.geometry.protected.study report --output-dir experiments/pipeline_v0.5/protected_simplification/windows_run_001
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest tests validation/test_evaluator.py -q
```

Same-environment repeated WKB is verified. Cross-platform/GEOS byte identity is
not established. Peak RSS is reported where available; Python tracing omits some
GEOS-native allocations. Runtime observations are not statistical benchmarks.

## Scientific and stage boundary

Five B1 development structures and all five remaining registered native-1024
v0.4.1 design/seed combinations define the study. Holdouts were reserved by path
membership before geometry outcomes, and were processed only after the final
implementation/configuration freeze. Missing holdout vectors are explicitly
derived as new ingress artifacts using unchanged A/A1 algorithms on existing
authenticated masks, with all source qualification outcomes retained. This does
not regenerate masks, extend historical acceptance or replace existing vectors.

Run_001 retains first development and finite-input matrix-warning evidence.
The final arithmetic uses explicit 2D component products and treats runtime
warnings as errors. No guard or acceptance budget was changed. Run_002 repeats
development before opening the reserved holdouts; repeat-comparison evidence
is retained. Initial synthetic failures and their pre-real-study corrections
are recorded separately. Historical files and acceptance decisions remain intact.

Only explicitly accepted final outputs with their qualification/provenance can
be proposed as inputs to a separately authorized formal v0.5C investigation
under this scoped geometric screen. No general production tolerance/policy,
export round-trip certification, physical dimensions, meshing, load capacity,
FEM readiness or manufacturing qualification is established. Future work must
address policy/generalization limits and separately register the scientific
round-trip/export acceptance procedure. **Stop before v0.5C.**
