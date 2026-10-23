# v0.5A.1 handoff: optional candidates, exact baseline unchanged

The new optional `solid_separate_contacts` workflow receives
**AMENDED_PASS_TESTED_DOMAIN_OPTIONAL_CANDIDATE_WORKFLOW** on five registered
1024 fixtures and 287 tests. Historical exact v0.5A remains HOLD. Its primary
source boundary remains non-manifold; it has not been relabeled or overwritten.

## Explicit selection contract

Canonical data is the original NPY. Exact v0.5A geometry remains the reference
for scientific comparisons. A local candidate is a distinct continuous set
under a separately recorded policy. Default behavior preserves exact geometry.

```python
from metamaterial_eval.geometry import load_binary_reference, convert_exact
from metamaterial_eval.geometry.manifold import qualify_manifold_geometry

mask = load_binary_reference("path/to/microstructure.npy")
exact = convert_exact(mask)
preserved = qualify_manifold_geometry(mask, exact)  # preserve_exact
candidate = qualify_manifold_geometry(mask, exact, "solid_separate_contacts")
if candidate["accepted"]:
    # Explicitly retain this as a candidate, with policy, settings and metrics.
    print(candidate["status"], candidate["metrics"])
```

Never select a geometry solely because a file exists or OGC validity is true.
Read the accepted flag plus fidelity, classification, manifold, modification
budget, morphology, provenance and physical-feature statuses. Rejected candidate
geometries are intentionally retained and must not be mistaken for accepted ones.
Unsupported contacts yield `REJECT_UNSUPPORTED_CONTACT` without a candidate or
fallback. Preserve mode is always available for quarantine.

## Reproduce from the repository root

Dependencies are unchanged from v0.5A; requirements-v0.5.txt pins Shapely 2.1.2.
The code adds no network/LLM dependency and does not regenerate any source mask.

```sh
python -m pip install -e .
python -m pip install -r requirements-v0.5.txt
python -m pip install pytest
python -m metamaterial_eval.geometry.manifold.study prepare --output-dir experiments/pipeline_v0.5/manifold_qualification/new_run
python -m metamaterial_eval.geometry.manifold.study run experiments/pipeline_v0.5/manifold_qualification/new_run
```

Preparation records settings, source hashes and code snapshots before execution.
Execution refuses changed registered sources and any already-started run.
Preserve interrupted evidence and register a new directory. Exit 3 denotes
geometry-study HOLD; inspect failure and per-policy qualification files.
summary.json records geometric results pending regression; final ACCEPTANCE.json
records the combined decision after tests and preservation verification. This
separation prevents geometry-only execution from claiming full software acceptance.

Windows/PowerShell instructions (documented, **not executed**):

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -r requirements-v0.5.txt
python -m pip install pytest
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest tests validation/test_evaluator.py -q
Remove-Item Env:EVALUATOR_PATH
python -m metamaterial_eval.geometry.manifold.study prepare --output-dir experiments/pipeline_v0.5/manifold_qualification/windows_run_001
python -m metamaterial_eval.geometry.manifold.study run experiments/pipeline_v0.5/manifold_qualification/windows_run_001
```

Match the recorded environment if exact platform comparisons are required;
review differences rather than tuning thresholds. No Windows equivalence is claimed.

## What later v0.5B can assume after review and authorization

For the five selected-policy outputs only: candidate validity/manifoldness,
registered local geometric budgets, exact 1024 raster descriptors and original
solid/OGC-hole counts passed. Candidate changes and contact neighborhoods are
explicitly recorded. Already manifold D9 is unchanged, including its original
generator repair. Exact geometry remains separately accessible for all cases.

Simplification must preserve contact clearance, all pores/channels and global
connectivity. The smallest introduced ligament is 0.353553 cell; treating a
global simplification tolerance of 0.25 cell as automatically safe could destroy
that feature. Register tolerances prospectively against protected local widths
and test candidates against the exact baseline and the qualified local candidate.
Do not smooth, collapse, silently enlarge or erase those neighborhoods.

No mechanical meaning is assigned to the subpixel ligament. Physical dimensions,
materials, loads, minimum physical feature criteria, CAD reimport behavior,
extrusion validity, mesh quality and manufacturing process remain unresolved.
The scoped v0.4.3 neck qualification is not evidence for this new tiny feature.
Unsupported multi-ring/crossing/overlap/non-grid/separate-solid contacts remain
blocked and must not enter a repair fallback.

The recommended next action is scientific review of the explicit local-change
policy and feature-size implications. Only after authorization should v0.5B be
implemented. No simplification, export, 3D or FEM work has begun here.
