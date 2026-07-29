# Young Dawgs Metamaterial Evaluation

This repository contains a reusable Python package for evaluating 2-D binary
mechanical metamaterials, the current reference microstructure, and a complete
pilot experiment that generated and evaluated 20 stochastic Voronoi-like
networks.

All binary arrays use the same contract:

- shape: `256 x 256`;
- NumPy dtype: `uint8`;
- solid phase: `1` (white in PNG);
- void phase: `0` (black in PNG);
- component connectivity: 4-neighbor.

## Repository map

```text
Young-Dawgs-VSCode/
├── metamaterial_eval/              reusable evaluation package
│   ├── io.py                       loading, validation, target preparation
│   ├── metrics.py                  morphology and spatial statistics
│   ├── evaluation.py               batch evaluation and reporting
│   └── cli.py                      command-line interface
├── data/reference/                 original and prepared target images
├── tests/pilot_voronoi/
│   ├── prompt.txt                  prompt used for the pilot generator
│   ├── iteration_0.py              procedural generator
│   └── generated_microstructures/  seeds 0-19 and evaluation reports
├── scripts/                        standalone analysis/plotting entry points
├── docs/METRICS.md                 equations and interpretation
├── tests/test_evaluation.py        automated numerical tests
├── pyproject.toml                  package/dependency configuration
└── requirements.txt                plain dependency list
```

The package is the stable research infrastructure. The historical pilot is
retained under `tests/pilot_voronoi/` to match the synchronized project
structure. New generator studies should receive a separate directory under
`experiments/`, containing their prompt, generator source, outputs, and
reports. Automated package assertions remain in `tests/test_evaluation.py`.

## 1. One-time installation

Open a terminal at the repository root.

### macOS or Linux

```bash
python3 -m venv .venv-macos
source .venv-macos/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Windows PowerShell

```powershell
py -m venv .venv-windows
.\.venv-windows\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

A virtual environment is operating-system specific. Do not synchronize or
reuse a Windows environment on macOS. The `.venv*` directories are ignored by
Git and should be recreated locally on each computer. The existing `.venv`
contains Windows Python 3.14 and is not usable from macOS.

Confirm the installation:

```bash
python -m unittest discover -s tests -v
python -m metamaterial_eval --help
```

## 2. Reproduce the existing pilot experiment

Generate seeds 0 through 19:

```bash
python tests/pilot_voronoi/iteration_0.py \
  --output-dir tests/pilot_voronoi/generated_microstructures
```

This writes one `.npy` and one `.png` for every seed. The NPY is the numerical
source of truth; the PNG is for visualization.

Evaluate the complete ensemble:

```bash
python -m metamaterial_eval evaluate \
  data/reference/reference_binary.npy \
  tests/pilot_voronoi/generated_microstructures \
  --shape 256x256 \
  --max-r 64
```

The evaluator prefers NPY when PNG and NPY have the same stem, so each seed is
counted once. It writes:

- `metrics_report.json`: complete structured data, including each curve;
- `metrics_report.txt`: compact feedback suitable for an LLM refinement prompt.

## 3. Evaluate one generated sample

Single-file evaluation is supported:

```bash
python -m metamaterial_eval evaluate \
  data/reference/reference_binary.npy \
  tests/pilot_voronoi/generated_microstructures/microstructure_seed_00.npy
```

The two report files are written beside the selected sample. This is the
single-sample extension added after the original package implementation.

## 4. Prepare a different reference image

```bash
python -m metamaterial_eval prepare path/to/new_reference.png \
  --threshold 0.5 \
  --shape 256x256
```

The command converts the image to grayscale, thresholds values greater than or
equal to `0.5` as solid, resizes with nearest-neighbor interpolation, and writes
`new_reference_binary.png` plus `new_reference_binary.npy` beside the source.

Before replacing the canonical reference, visually confirm that white pixels
represent solid material. An inverted phase definition changes every reported
metric.

## 5. Use the Python API

```python
from metamaterial_eval import (
    evaluate_generator_output,
    load_binary,
    make_target_dict,
)

target = load_binary(
    "data/reference/reference_binary.npy",
    expected_shape=(256, 256),
)
target_metrics = make_target_dict(target, max_r=64)
report = evaluate_generator_output(
    target_metrics,
    "tests/pilot_voronoi/generated_microstructures",
)

print(report["valid_sample_count"])
print(report["aggregate_valid_samples"]["nrmse_s2"]["mean"])
```

See [docs/METRICS.md](docs/METRICS.md) for exact definitions and guidance on
interpreting the report.

## 6. Add a new LLM generator experiment

Create a new directory without modifying the pilot:

```text
experiments/<experiment_name>/
├── prompt.txt
├── generate_microstructures.py
└── generated_microstructures/
```

The generator must produce 20 independent NPY arrays and matching PNGs. Run the
same evaluation command with the new output directory, compare ensemble means
and standard deviations against the target, revise the generator parameters,
and preserve each iteration as a separate experiment or versioned report.

Standalone plotting tools such as `evaluate_and_plot.py` belong in `scripts/`
and should import the package rather than duplicate metric implementations.

## 7. Run the improved periodic evaluator and plots

Your `evaluate_and_plot.py` provides the research-grade ensemble diagnostics:

```bash
python scripts/evaluate_and_plot.py
```

Its defaults now point to the stored pilot samples and canonical target. The
equivalent fully explicit command is:

```bash
python scripts/evaluate_and_plot.py \
  tests/pilot_voronoi/generated_microstructures \
  --target data/reference/reference_binary.npy \
  --output-dir tests/pilot_voronoi/evaluation_results \
  --max-r 64 \
  --expected-count 20
```

It writes `evaluation_summary.json` and five figures:

1. target/generated montage;
2. periodic two-point-correlation ensemble;
3. periodic lineal-path ensemble;
4. target/generated pore-size distributions;
5. pairwise pixel-disagreement heatmap.

It also performs three evaluator sanity checks, flags translated, rotated, and
mirrored target copies using transformation-aware periodic NCC, audits seeds,
reports directional lineal paths, and measures ensemble diversity using mean
pairwise pixel disagreement.

The two evaluators intentionally use different boundary conditions:

- `python -m metamaterial_eval evaluate ...` uses finite-domain, zero-padded
  spatial statistics and produces compact LLM feedback;
- `python scripts/evaluate_and_plot.py` uses periodic spatial statistics,
  formal sanity controls, novelty/diversity checks, and diagnostic plots.

Do not compare their NRMSE values as if they were computed by the same
estimator. Use one estimator consistently when comparing generator iterations.

## 8. Evaluator validation

The frozen v1.0 evaluator failed 20 of 56 acceptance tests. The corrected v1.1
evaluator passes all 56 tests and two full 20-sample reproducibility runs.

```bash
EVALUATOR_PATH=evaluator_validation/evaluator/evaluator_v1_1.py \
python -m pytest evaluator_validation/test_evaluator.py -v
```

The complete validation record, hashes, fixtures, JUnit output, pilot JSON, and
figures are under `evaluator_validation/`. The accepted conventions and
quantitative findings are summarized in
`evaluator_validation/validation_notes.md`.
