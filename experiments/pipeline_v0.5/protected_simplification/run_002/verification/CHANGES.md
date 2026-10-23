# v0.5B2 file changes

All 3719 pre-existing inventoried files are byte-identical. No historical file was modified.

New implementation: geometry/protected/{__init__,settings,model,guards,engine,qualification,sources,study,reporting}.py.
New tests: tests/test_protected_simplification.py. New verification script: scripts/pipeline_v0_5b2_audit.py.
New architecture/protocol/validation/handoff documentation under docs/pipeline_v0.5.
New protected_simplification/run_001 retains first development and arithmetic-correction evidence; run_002 holds final repeated development, frozen holdouts, complete reports and verification.

The exact file list, sizes and SHA-256 hashes are in new_files.json; its own bytes are excluded to avoid a circular hash.
