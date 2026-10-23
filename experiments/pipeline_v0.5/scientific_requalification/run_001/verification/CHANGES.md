# v0.5C.1 change boundaries

All implementation and evidence additions belong to v0.5C.1. The initial
inventory covers 5,777 preexisting files. PRESERVATION.json reports the final
byte-level comparison; new_files.json enumerates additions and SHA-256 hashes.

New implementation: `metamaterial_eval/geometry/protected_v2/` contains the
explicit algorithm version, additive guarded-DP implementation, local affine
width gate, independent oblique audit, and registered study orchestration.
Earlier protected, validation, exact conversion, manifold, generator, and
evaluator modules are reused without editing them.

New verification: `tests/test_feature_protection_v2.py` supplies 50 targeted
tests. The original 407 tests remain unchanged. The executed full regression
and JUnit report are saved in this directory.

New analysis scripts: `scripts/pipeline_v0_5c1_*.py` provide original/revised
comparison, targeted instrumentation, separate pore-policy analysis, reporting,
and closeout. Reporting and closeout scripts may be corrected after the freeze
to describe existing measurements; they cannot change candidates, decisions,
registered thresholds, or frozen algorithm files.

New documentation: the C.1 architecture, reproduction instructions, three
scientific-report pointers, and C.1 handoff reside in `docs/pipeline_v0.5/`.
The authoritative executed reports and all measurements reside in this new
scientific_requalification experiment. The historical V0_5D_HANDOFF.md remains
unchanged; the new C.1 handoff describes restrictions for a future stage.

The initial four-direction prototype and two rotated-control lookup failures
remain documented development evidence. All corrections to geometry logic and
test controls preceded the final freeze and untouched cohort generation.
No holdout outcome was used to revise the algorithm or acceptance criteria.

No existing source, experiment, acceptance status, raster, or candidate is
intentionally modified. No export, CAD, 3D, FEM, or manufacturing implementation
is added. Completion of this implementation is distinct from scientific
advancement, which remains subject to the separate statuses in the main report.
