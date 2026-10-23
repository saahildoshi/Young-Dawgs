# v0.5A handoff and operating instructions

Current decision: **HOLD on manifold-boundary readiness**, despite exact boundary
and OGC-polygon round-trips for both 1024 fixtures. Implementation and regression
verification are complete for the present v0.5A scope. Do not start v0.5B yet.

## Entry points and reusable interfaces

Run from the repository root. No machine-specific project root is embedded in
the commands or fixture configuration. Canonical inputs must be available locally.

```sh
python -m pip install -e .
python -m pip install -r requirements-v0.5.txt
python -m pip install pytest
python -m metamaterial_eval.geometry.reporting --output-dir experiments/pipeline_v0.5/baseline_vectorization/new_run
```

Exit code 3 means the geometry acceptance is HOLD; inspect summary.json and
FAILURE.json. Existing directories are refused. Preserve interrupted or failed
runs; select a new directory. The fixture runner hashes both NPY and PNG against
their original manifests and verifies saved repaired-pixel hashes. No generator,
LLM or network service is invoked. Dependency installation is separate from runs.

```python
from metamaterial_eval.geometry import load_binary_reference, convert_exact

mask = load_binary_reference("path/to/microstructure.npy", "path/to/microstructure.png")
result = convert_exact(mask)
print(result["status"], result["validity"], result["comparison"]["xor_pixels"])
```

Core functions are also available separately in inputs.py, topology.py,
boundaries.py, planar.py and raster.py. `exact_boundaries.json` is the exact
baseline document; `polygon_candidate.wkb` is a derived, annotated representation.
Read metadata and validity before consuming either. Candidate WKB is never
advertised as CAD interchange readiness.

## Windows reproduction, not Windows verification

Use an actual Windows virtual environment, not a copied macOS environment:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m pip install -r requirements-v0.5.txt
python -m pip install pytest
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest tests validation/test_evaluator.py -q
Remove-Item Env:EVALUATOR_PATH
python -m metamaterial_eval.geometry.reporting --output-dir experiments/pipeline_v0.5/baseline_vectorization/windows_run_001
```

The recorded macOS environment is in run_003/environment.json. For matching its
numeric stack, NumPy 2.2.6, SciPy 1.14.1, scikit-image 0.25.2, Shapely 2.1.2,
Matplotlib 3.10.9 and Pillow 12.3.0 were used. GEOS and Python versions are also
recorded. Windows execution has not been tested. RSS is null on platforms without
the resource module; traced allocation measurement remains available.

## Remaining v0.5A decision

Fixture A has two hole rings sharing (31,296). The closed occupied-cell set and
every pixel are retained; OGC validity does not certify a manifold boundary.
The original face walk is self-pinched, but decomposition at an existing shared
vertex yields 289 simple polygon holes from 288 complementary-8 digital pores.
This is exact ring bookkeeping, not filling a pore, adding a bridge or smoothing.

Do not waive the prospectively recorded manifold condition simply because GEOS
accepts the object. Before general simplification, review an explicit policy for
non-manifold cell complexes/contact graphs. If ordinary simple disjoint CAD rings
are mandatory, this source cannot meet that boundary condition unchanged.
Any proposal to change the point contact needs separate scientific authorization,
its own immutable candidate and quantified topology/fidelity assessment.
The current deliverable does not perform that change.

## Required next steps after review and explicit v0.5B authorization

1. Freeze the v0.5A baseline and source inventories. Preserve all three runs;
   run_001 records initial tracing/visual limitations, run_002 improves inspection
   windows, and run_003 is the current exact-ring-decomposition result.
2. Resolve how non-manifold contacts are represented and whether they are eligible
   for simplification. Do not use Design 9 alone to exclude the ordinary blocker.
3. Prospectively register several simplification tolerances relative to raster
   resolution and measured local feature width. Establish hard connectivity,
   pore/channel and validity constraints before measuring candidates.
4. Implement simplification in separate modules and immutable candidate folders;
   retain exact original loops, contact graph and polygon candidates. Reject
   candidates that merge pores, close channels, sever struts or create islands.
5. Implement broader frozen-descriptor comparison only in separately authorized
   v0.5C. Use evaluator v1.1 and the scoped v0.4.3 qualification policy without
   rewriting the original failed P10 calibration. Do not borrow resolution
   thresholds as automatic simplification tolerances.
6. Leave SVG/DXF integration for v0.5D, including independent reimport checks.
   Physical scale remains unspecified; no 3D, FEM or manufacturing claim follows.

No code for these later stages is included.
