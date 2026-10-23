# v0.5C reproduction and artifact review

Executed environment: macOS ARM64, Python3.10, Shapely2.1.2/GEOS3.13.1,
NumPy2.2.6, SciPy1.14.1, scikit-image0.25.2. Exact versions are captured under
scientific_validation/run_001/protocol/environment.json. Windows was not run.

The saved run is immutable scientific evidence. Execution markers deliberately
reject overwriting an existing reference/holdout phase. A checking repetition must reuse the now-persisted C native arrays and geometry,
not call the first-source-creation path again. Authenticate every frozen
source/implementation hash. Keep all failed ingress and candidate artifacts.
Repeating consumed parameter points is reproducibility work, not fresh holdout
evidence for a revised algorithm.

Executed commands at the repository root:

```sh
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py .venv-macos/bin/python -m pytest tests validation/test_evaluator.py -q --junitxml=/tmp/yd-v05c-regression.xml
.venv-macos/bin/python -m metamaterial_eval.geometry.validation.study freeze
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py .venv-macos/bin/python -W error::RuntimeWarning -m metamaterial_eval.geometry.validation.study reference
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py .venv-macos/bin/python -W error::RuntimeWarning -m metamaterial_eval.geometry.validation.study holdouts
.venv-macos/bin/python scripts/pipeline_v0_5c_supplement.py
.venv-macos/bin/python scripts/pipeline_v0_5c_report.py
```

The commands above are the actual first-creation provenance, not instructions to
regenerate these now-existing source masks in another run. `holdouts` is the
registered first-creation entrypoint for run_001; it must not be reused to rerender
this cohort. For independent rechecking, load the G0 paths and G1/G2/G3 paths in
each independent_validation.json and source_manifests record, authenticate their
hashes, and call the checks module on those persisted arrays/geometries. A future
registered execution must explicitly reuse these canonical C sources and record
that source-selection procedure. The
supplement script defaults to run_001; adapt only its output-path constant for a
separately recorded reporting repetition. Never rerun generation on saved masks.

PowerShell syntax for the validation suite (documentation, not a Windows result):

```powershell
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest tests validation/test_evaluator.py -q
python -W error::RuntimeWarning -m metamaterial_eval.geometry.validation.study reference --output-dir experiments/pipeline_v0.5/scientific_validation/<fresh-run>
```

A fresh run must have an independently copied protocol, implementation freeze
and complete directory structure first. This documentation does not demonstrate
cross-platform byte identity, future CAD interoperability or production policy.
