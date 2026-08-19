# Young Dawgs Evaluator: Project Reference and Command Catalog

This is the operating reference for the repository. Run all commands from the
repository root unless a section states otherwise.

## 1. Scientific data contract

| Property | Required convention |
|---|---|
| Array shape | `256 x 256` pixels |
| NPY dtype | `numpy.uint8` |
| Solid phase | `1` in NPY; white (`255`) in PNG |
| Void phase | `0` in NPY; black (`0`) in PNG |
| Component connectivity | 4-neighbor (edge contact only) |
| Default curve limit | `max_r = 64` pixels |
| Valid sample | $f_\mathrm{largest} \ge 0.98$, $P_x=1$, and $P_y=1$ |

NPY files are the numerical source of truth. PNG files are human-viewable
companions. When matching NPY and PNG stems occur together, the evaluator
selects the NPY so that a sample is counted once.

## 2. Repository map

```text
Young-Dawgs-VSCode/
├── README.md                         quick-start landing page
├── pyproject.toml                    install metadata and dependencies
├── requirements.txt                  plain dependency list
├── metamaterial_eval/                reusable finite-domain package
│   ├── __init__.py                   public Python API
│   ├── __main__.py                   python -m entry point
│   ├── cli.py                        prepare/evaluate commands
│   ├── io.py                         binary input and target preparation
│   ├── metrics.py                    morphology and spatial metrics
│   └── evaluation.py                 ensemble aggregation and reports
├── scripts/
│   └── evaluate_and_plot.py          periodic evaluator and five plots
├── data/reference/                   canonical target files
├── experiments/pilot_voronoi/
│   ├── generator_prompt.txt          original generator prompt
│   ├── generate_microstructures.py   seed-controlled generator
│   ├── provenance/                   original LLM transcript
│   ├── samples/                      20 NPY and 20 PNG samples
│   ├── results/                      accepted current results
│   │   ├── finite_domain/            compact JSON/text package output
│   │   └── periodic/                 v1.1 JSON and diagnostic figures
│   └── archive/v1_0/                 superseded results for provenance
├── validation/
│   ├── evaluators/                   frozen v1.0 and accepted v1.1
│   ├── fixtures/                     analytical binary test patterns
│   ├── expected/                     hand-calculated expectations
│   ├── results/                      stored validation evidence
│   ├── test_evaluator.py             56 scientific acceptance tests
│   ├── validation_notes.md           detailed validation record
│   └── OBSIDIAN_ANALYTICAL_TEST_RESULTS.md
├── tests/test_evaluation.py          reusable-package regression tests
└── docs/
    ├── METRICS.md                    detailed scientific definitions
    └── PROJECT_REFERENCE.md          this document
```

## 3. What each software component does

| Component | Responsibility | Use it when |
|---|---|---|
| `metamaterial_eval.io.prepare_target` | Converts an input image to grayscale, thresholds it, nearest-neighbor resizes it, and saves PNG/NPY binary targets | Introducing a new reference microstructure |
| `metamaterial_eval.io.load_binary` | Loads PNG or NPY and enforces binary/shape rules | Reading target or generated data safely |
| `compute_basic_metrics` | Computes $\phi_s$, component count, $f_\mathrm{largest}$, $P_x$, and $P_y$ | Checking density and network topology |
| `compute_s2_correlation` | Computes finite-domain FFT-based radial $S_2(r)$ | Comparing pairwise solid spatial statistics |
| `compute_lineal_path` | Computes finite-domain $L_x(r)$, $L_y(r)$, and four-direction radial $L(r)$ | Comparing continuous solid paths and anisotropy |
| `compute_local_dimensions` | Computes skeleton-sampled strut thickness and one diameter per enclosed pore | Comparing feature sizes |
| `make_target_dict` | Precomputes all reference metrics and curves | Preparing target data for batch evaluation |
| `evaluate_generator_output` | Evaluates one sample or a folder and writes compact JSON/text reports | Fast generator feedback and LLM iteration |
| `scripts/evaluate_and_plot.py` | Computes periodic descriptors, sanity controls, novelty/diversity, and five plots | Full research diagnostics and visual review |
| `validation/test_evaluator.py` | Applies analytical and integration acceptance tests to a selected evaluator snapshot | Verifying evaluator correctness or future changes |

## 4. Metric meanings

| Metric | Definition | Interpretation |
|---|---|---|
| Solid fraction $\phi_s$ | $\phi_s=N_\mathrm{solid}/N_\mathrm{total}$ | Relative material content; match this before interpreting higher-order metrics |
| Largest-component fraction $f_\mathrm{largest}$ | Solid pixels in the largest 4-connected component divided by all solid pixels | Near 1 means nearly all solid material belongs to one load-carrying network |
| $P_x$ | One 4-connected solid component touches left and right boundaries | Binary horizontal percolation indicator |
| $P_y$ | One 4-connected solid component touches top and bottom boundaries | Binary vertical percolation indicator |
| $S_2(r)$ | Probability that two points separated by $r$ are both solid | Captures volume fraction, characteristic spacing, and short-range order; $S_2(0)=\phi_s$ |
| $L_x(r),L_y(r)$ | Probability that every pixel in a horizontal/vertical segment of endpoint separation $r$ is solid | Directional continuity and anisotropy |
| $L(r)$ | Available-segment-weighted four-direction lineal-path average | Compact continuous-path descriptor |
| Mean strut thickness | Mean of $2D_s$ sampled on the solid skeleton, where $D_s$ is the solid EDT | Typical centerline-based strut width in pixels |
| P10 strut thickness | 10th percentile of skeleton thickness samples | Thin-feature or bottleneck indicator |
| Median pore diameter | Median of one $2\max(D_v)$ value per enclosed 4-connected void | Typical enclosed pore size; boundary-touching void is excluded |
| NRMSE | $\sqrt{\mathrm{mean}[(C_s-C_t)^2]}/\sqrt{\mathrm{mean}[C_t^2]}$ | Dimensionless curve error; lower is better |
| SSIM | Structural similarity between sample and target | Image-level similarity; diagnostic, not a physical equivalence measure |
| NCC | Normalized cross-correlation against the target | High values can indicate a trivial copy |
| $D_\mathrm{pair}$ | Mean upper-triangle pairwise pixel disagreement | Ensemble diversity; stored criterion is $D_\mathrm{pair}>0.05$ |

All length outputs are pixels. If the physical resolution is $s$ mm/pixel,
convert a reported length $d_\mathrm{px}$ using $d_\mathrm{mm}=s\,d_\mathrm{px}$.

## 5. Two evaluation protocols

| Property | Finite-domain package | Periodic plotting evaluator |
|---|---|---|
| Entry point | `python -m metamaterial_eval evaluate` | `python scripts/evaluate_and_plot.py` |
| Boundary model | Zero-padded finite image | Periodic wraparound |
| Primary output | Compact JSON and LLM-readable text | Detailed JSON plus five figures |
| Special checks | Valid/all-sample aggregation | Sanity controls, seed audit, SSIM/NCC, copy detection, diversity |
| Recommended role | Rapid iterative feedback | Research diagnostics and comparative plots |

The two protocols intentionally estimate different boundary conditions. Do not
compare their NRMSE values as though they were produced by the same estimator.
Use one protocol consistently when ranking generator iterations.

## 6. One-time installation

### macOS or Linux

```bash
cd "/Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode"
python3 -m venv .venv-macos
source .venv-macos/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Windows PowerShell

```powershell
cd "PATH\TO\Young-Dawgs-VSCode"
py -m venv .venv-windows
.\.venv-windows\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Virtual environments are machine- and operating-system-specific. They are
ignored by Git and should be recreated rather than synchronized.

### Verify the installation

```bash
python -m metamaterial_eval --help
python -m pytest -q
```

## 7. Routine command catalog

### Generate or reproduce the 20 pilot samples

```bash
python experiments/pilot_voronoi/generate_microstructures.py \
  --output-dir experiments/pilot_voronoi/samples
```

The script always uses seeds 0 through 19. It writes 20 NPY files and 20 PNG
files and rejects an accidental duplicate realization.

### Run finite-domain evaluation on the full pilot

```bash
python -m metamaterial_eval evaluate \
  data/reference/reference_binary.npy \
  experiments/pilot_voronoi/samples \
  --output-dir experiments/pilot_voronoi/results/finite_domain \
  --shape 256x256 \
  --max-r 64
```

This command writes `metrics_report.json` and `metrics_report.txt` to the
organized finite-domain results directory.

### Evaluate one sample

```bash
python -m metamaterial_eval evaluate \
  data/reference/reference_binary.npy \
  experiments/pilot_voronoi/samples/microstructure_seed_00.npy \
  --output-dir experiments/pilot_voronoi/results/single_seed_00
```

Omit `--output-dir` only when you intentionally want the two reports written
beside the selected sample.

### Run periodic evaluation and plots with defaults

```bash
python scripts/evaluate_and_plot.py
```

The defaults are the canonical target, pilot sample folder, `max_r=64`, 20
expected samples, random-control seed 2026, and
`experiments/pilot_voronoi/results/periodic/` as the output directory.

### Run periodic evaluation with every option explicit

```bash
python scripts/evaluate_and_plot.py \
  experiments/pilot_voronoi/samples \
  --target data/reference/reference_binary.npy \
  --output-dir experiments/pilot_voronoi/results/periodic \
  --max-r 64 \
  --expected-count 20 \
  --seed 2026
```

Use `--expected-count 0` to allow any positive sample count.

### Prepare a new target image

```bash
python -m metamaterial_eval prepare path/to/reference.png \
  --threshold 0.5 \
  --shape 256x256
```

This creates `reference_binary.npy` and `reference_binary.png` beside the
source. Confirm visually that white represents solid before using it.

### Run reusable-package tests

```bash
python -m pytest tests/test_evaluation.py -v
```

### Validate accepted evaluator v1.1

```bash
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py \
python -m pytest validation/test_evaluator.py -v
```

Expected result: `56 passed`.

### Reproduce historical v1.0 validation failures

```bash
EVALUATOR_PATH=validation/evaluators/evaluator_v1_0.py \
python -m pytest validation/test_evaluator.py -v
```

Expected result: 36 passes and 20 failures. This is provenance, not the
accepted research configuration.

### Regenerate analytical validation fixtures

```bash
python validation/generate_test_images.py
```

### Display command help

```bash
python -m metamaterial_eval --help
python -m metamaterial_eval prepare --help
python -m metamaterial_eval evaluate --help
python scripts/evaluate_and_plot.py --help
python experiments/pilot_voronoi/generate_microstructures.py --help
```

## 8. Python API example

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
    "experiments/pilot_voronoi/samples",
    output_dir="experiments/pilot_voronoi/results/finite_domain",
)

print(report["valid_sample_count"])
print(report["aggregate_valid_samples"]["nrmse_s2"]["mean"])
```

## 9. Output files and how to read them

### Finite-domain `metrics_report.json`

| Key | Contents |
|---|---|
| `definitions` | Boundary, connectivity, and metric conventions |
| `target` | Target scalar metrics and curves |
| `sample_count` | Discovered sample count after NPY/PNG stem de-duplication |
| `evaluated_sample_count` | Samples that passed input validation |
| `valid_sample_count` | Samples satisfying the topology rule |
| `aggregate_all_samples` | Population mean/std/count over every evaluated sample |
| `aggregate_valid_samples` | Same statistics after topology filtering |
| `samples` | Per-file metrics, curves, and validity state |
| `errors` | Files rejected during loading or computation |

`metrics_report.txt` is a compact version intended for pasting into the next
LLM generator-refinement prompt.

### Periodic `evaluation_summary.json`

| Key | Contents |
|---|---|
| `methodology` | Periodic definitions and thresholds |
| `sample_seed_audit` | Expected, discovered, missing, and duplicate seed checks |
| `sanity_checks` | Target-copy, translation, and Bernoulli controls |
| `novelty` | Transform-aware target-copy screening |
| `diversity` | Pairwise disagreement matrix and $D_\mathrm{pair}$ |
| `ensemble_summary` | Population statistics for all samples |
| `valid_ensemble_summary` | Statistics for topology-valid samples only |
| `figures` | Paths to five generated diagnostic figures |

The five figures are: sample montage, periodic $S_2$, periodic lineal path,
pore-size distributions, and pairwise-diversity heatmap.

## 10. Starting a new generator experiment

Create a self-contained directory:

```text
experiments/<experiment_name>/
├── README.md
├── generator_prompt.txt
├── generate_microstructures.py
├── provenance/
├── samples/
├── results/
│   ├── finite_domain/
│   └── periodic/
└── archive/
```

Recommended iteration procedure:

1. Preserve the exact prompt and generator source.
2. Generate 20 independent NPY/PNG pairs with explicit seeds.
3. Verify every NPY is `(256, 256)`, `uint8`, and binary.
4. Run the topology filter and both evaluation protocols.
5. Compare means, population standard deviations, distributions, and curves.
6. Change generator parameters or logic, not evaluator conventions.
7. Archive the superseded results before overwriting current outputs.

## 11. Version and provenance rules

- Use v1.1 results for research interpretation.
- Keep `archive/v1_0/` unchanged; it documents the superseded calculations.
- Do not modify `validation/evaluators/evaluator_v1_0.py` or
  `evaluator_v1_1.py`; create a new version if evaluator behavior changes.
- Re-run both test suites after evaluator or package changes.
- Keep generated environments, `.DS_Store`, Python caches, and package
  `*.egg-info` out of the repository.
- Treat the OneDrive Git repository as the canonical working copy.

## 12. Common interpretation errors

- A valid sample is connected and percolating; it is not necessarily similar
  to the target.
- Low $S_2$ NRMSE does not prove that strut thickness, pore distribution, or
  mechanical response matches.
- Finite-domain and periodic curve errors are not directly interchangeable.
- Boundary-touching void is excluded from the enclosed-pore population.
- A PNG with reversed black/white phases invalidates all comparisons.
- Reported dimensions remain in pixels until multiplied by a calibrated
  physical pixel scale.
