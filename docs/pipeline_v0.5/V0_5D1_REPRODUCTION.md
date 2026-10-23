# v0.5D1 reproduction and persistence boundaries

Actual execution: macOS ARM64, repository `.venv-macos`, Shapely 2.1.2 and the
unchanged frozen evaluator v1.1. Environment and code/protocol hashes are in
`experiments/pipeline_v0.5/svg_export_validation/run_001/protocol/`.

First-creation commands, retained for provenance:

```sh
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py .venv-macos/bin/python -m pytest tests validation/test_evaluator.py -q
.venv-macos/bin/python -m metamaterial_eval.geometry.svg_io.study controls
.venv-macos/bin/python -m metamaterial_eval.geometry.svg_io.study freeze
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py .venv-macos/bin/python -m metamaterial_eval.geometry.svg_io.study run
.venv-macos/bin/python -m metamaterial_eval.geometry.svg_io.study precision
.venv-macos/bin/python -m metamaterial_eval.geometry.svg_io.study profile
.venv-macos/bin/python scripts/pipeline_v0_5d1_report.py
.venv-macos/bin/python scripts/pipeline_v0_5d1_closeout.py --finalize
```

These commands describe the completed creation procedure. Do not repeat them
over completed evidence. Real-study/freeze/precision markers and canonical
export creation reject overwrite. The two initial synthetic development runs
remain retained; the third is the complete registered control result. The final
closeout requires recorded visual figure QA before it can complete.

Read-only reimport check from the repository root:

```python
import json
from pathlib import Path
import shapely
from metamaterial_eval.geometry.svg_io.importer import read_svg
from metamaterial_eval.geometry.svg_io.verification import compare_geometry

folder = Path("experiments/pipeline_v0.5/svg_export_validation/run_001/exports")
sidecar = folder / "C_G3_D4S1_E050.json"
record = json.loads(sidecar.read_text())
source = shapely.from_wkb(Path(record["source_geometry_path"]).read_bytes())
result = read_svg(folder / record["svg_filename"], sidecar,
                  expected_source_sha256=record["source_geometry_sha256"])
assert compare_geometry(source, result["geometry"])["passed"]
```

Use the ledger and frozen protocol as trust anchors when authenticating source,
SVG and sidecar hashes. The reader never uses original geometry coordinates or
sidecar ring roles to build its result. Coordinate/ring ordering can differ;
the represented region and complete binary64 vertex/edge multiplicities must
remain exact. No physical dimensions or units are inferred.

Preview rendering uses the already bundled Node/Sharp runtime. Its actual path
and Sharp/libvips/librsvg versions are stored in every real sidecar. A separately
prepared environment can set `YOUNG_DAWGS_NODE` and `YOUNG_DAWGS_SHARP` to its
runtime/module paths. Preview rendering is not part of continuous equivalence
or a downstream CAD-kernel test. Python SVG export/import needs no additional
Python dependency beyond the existing geometry environment.

Windows test syntax, documentation only:

```powershell
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest tests validation/test_evaluator.py -q
```

Windows execution and cross-platform byte identity were not established.
The D1 export result does not lift the cumulative small-pore scientific HOLD,
choose production simplification, assign a physical scale, or authorize DXF/3D.
