# Pipeline v0.4.3 — P10 metric qualification

## Decision and boundaries

The recorded decision is **AMENDED_PASS_TESTED_DOMAIN**. This is a methodological
amendment to resolution acceptance, not a new generator version. The generator
remains v0.4.1 and the frozen evaluator remains v1.1. No generator execution,
geometry modification, CAD conversion, or FEM was performed in this study.

The original P10 calibration remains **FAILED** (maximum analytic change
12.6681% against its original 10% ceiling). The historical v0.4.2 decision remains
**HOLD**. Neither result was overwritten. Whole-mask P10 retains its definition
and all twenty recomputed native values exactly match their historical values.

This amendment qualifies the specified aggregate lower-tail measurement and
scoped local-neck screen for the tested morphologies. It does **not** establish
a universal substitute for P10, exhaustive network-neck detection, mechanical
strength, or manufacturing suitability.

## Registered method

Let $T=2\,\mathrm{EDT}/N$ be the thickness samples on the unchanged frozen
evaluator's pixel skeleton and $F_N(w)=P(T\leq w)$ their empirical CDF.
The new aggregate criterion is

$$
A=\int_0^{4/256}|F_{1024}(w)-F_{2048}(w)|\,dw\leq\frac{1}{1024}.
$$

The interval is $[0,0.015625]$ in normalized width. CDFs use **all skeleton
samples** in their denominators; samples are neither pruned nor reweighted, and
the tail is not renormalized. The area is integrated exactly over empirical
step-function knots, independently of plot sampling.

Reports show $1024A$, with a limit of 1. This is an integrated distribution
displacement expressed in nominal 1024-grid pixels, **not** a maximum local
width error. The tolerance is a declared numerical-resolution budget, not a
physical safety tolerance or a theoretical raster-error bound.

The separate local-neck screen requires occupied normal depth
$d_{\min}/N\geq3/1024=0.0029296875$ in a predefined neck region, with one connected
solid component in the analytic control. Its implementation assumes a single
contiguous axis-aligned cross-section. Native checks reuse the previously
inspected repair cross-sections and topology evidence; they do not search every
neck in every network.

The protocol, controls, tolerances, code hashes, and historical file inventories
were recorded in `protocol.json` before independent controls were measured.
Qualification results were saved before the native pairs were evaluated.
“Independent” means previously untested analytic parameter choices, not a
statistical independence or confidence-interval claim.

## Results

| Check | Purpose | Result |
|---|---|---|
| Ten fixed-geometry controls | Measure resolution sensitivity on new bars, rings, and junctions | 10/10 passed; $1024A=0.102292$–$0.417704$ |
| Three 25% uniform-thinning controls | Confirm sensitivity to a substantial width defect | 3/3 detected; $1024A=2.303995$–$2.461699$, exceeding 1 |
| Healthy/weak necks at 1024 and 2048 | Check localized defects separately from global statistics | 4/4 expected outcomes |
| Ten saved native 1024→2048 pairs | Apply the independently qualified aggregate test | 10/10 passed; $1024A=0.136371$–$0.207747$ |
| Whole-mask native P10 | Preserve historical comparability | All 20 values unchanged |
| Existing repaired connection | Retain direct geometry checks | 3/512, 5/1024, and 9/2048 normalized inward depths all exceed 3/1024 |
| Prior topology and baseline checks | Retain engineering acceptance evidence | Preserved 30/30 topology and 10/10 bitwise-baseline passes |
| Other prior convergence checks | Retain mean, pore, density, spatial statistics and identity requirements | All inherited gates passed; not rerun as generation jobs |
| Historical files and registered source | Detect accidental changes during the study | All recorded hashes unchanged |
| Software and frozen-evaluator regression suite | Check implementation contracts and existing behavior | 212 passed in 28.54 seconds on macOS |

The native sample set is **five parameter designs (0, 1, 2, 5, 9) × two seeds**,
not ten statistically independent designs.

The healthy analytic neck occupies 3 pixels at 1024 and 8 pixels at 2048;
the weak neck occupies 1 and 2 pixels respectively. These are measured raster
depths, not forced matches to the nominal analytic widths.

### Important sensitivity limitation

The localized weak neck **passes the aggregate CDF comparison** against its
healthy counterpart at both resolutions ($1024A=0.140328$ and $0.217882$).
The separate geometry screen correctly rejects it. This deliberately demonstrates
why CDF convergence alone cannot establish that every connection is robust.
Sensitivity to smaller uniform defects, other neck orientations, or unknown
network bottlenecks has not been established.

### Historical 30-degree bar

The known failing control is regression evidence only, not part of the ten
independent controls. Its whole-mask P10 still changes by 12.6681%, while the
new lower-tail area is $1024A=0.220015$.

Crucially, this control's P10 widths (0.0218366 and 0.0190703) lie **above** the
registered upper width of 0.015625. Only approximately 6.54% and 8.17% of its
samples are inside the new interval. The small CDF area therefore supports
stability of that specified tail, **not** qualification of the original P10
values or the entire distribution. The original failure remains scientifically
meaningful and is not converted into a pass.

## Files and their meaning

All study outputs are under
`experiments/pipeline_v0.4.3/p10_qualification/`.

| File | Meaning |
|---|---|
| `protocol.json` | Prospective rules, controls, tolerances, source hashes, environment, historical inventories |
| `execution.json` | Run timestamps, protocol hash, completion state, preservation result |
| `controls/` | Independently rendered analytic masks and deliberately defective masks |
| `independent_qualification.json` | Independent control measurements and decision, recorded before native evaluation |
| `summary.json` | Machine-readable amended decision, native results, diagnostic P10, limits and all gates |
| `AMENDED_ACCEPTANCE.md` | Obsidian-compatible per-control and per-sample result tables |
| `qualification.png` | Example invariant/thinned CDFs and the ten invariant-control areas |
| `../verification/full_tests/` | Automated regression-test output and execution metadata |

Implementation: `metamaterial_eval/pipeline/p10_qualification.py`.
Unit tests: `tests/test_p10_qualification.py`.
Existing v0.4.1/v0.4.2 folders remain the source of the inherited engineering
evidence and saved native masks.

## Windows PowerShell commands

Run from the project root with the project environment active:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Register a **new** study directory. Do not reuse the saved evidence directory:

```powershell
python -m metamaterial_eval.pipeline.p10_qualification register `
  --previous-run "experiments\pipeline_v0.4.2\thickness_verification" `
  --output-dir "experiments\pipeline_v0.4.3\qualification_windows"
```

Run the registered protocol:

```powershell
python -m metamaterial_eval.pipeline.p10_qualification qualify `
  "experiments\pipeline_v0.4.3\qualification_windows"
```

The study uses existing native masks; it does not regenerate them. Keep the
v0.4.1/v0.4.2 inputs unchanged and fully available locally in OneDrive. Register
on the machine that will execute the study; protocol paths are machine-local.
Do not change registered source or historical inputs between these stages.
Use a new output name for every attempt. No overwrite/resume option is provided.

The qualification command returns 0 for amended acceptance and 3 for HOLD;
an exception signals an execution/integrity problem, not scientific acceptance.
If interrupted after execution begins, preserve that attempt and register a new
directory. Do not delete its execution record to force a rerun.

View the resulting report:

```powershell
Get-Content "experiments\pipeline_v0.4.3\qualification_windows\AMENDED_ACCEPTANCE.md"
Invoke-Item "experiments\pipeline_v0.4.3\qualification_windows\qualification.png"
```

Run the software and frozen-evaluator regression suites:

```powershell
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest tests validation/test_evaluator.py -q
```

Explicit evaluator selection matters: the historical validation harness otherwise
defaults to v1.0. The recorded study was executed on macOS with Python 3.10,
NumPy 1.26.4, SciPy 1.13.1, scikit-image 0.25.2 and Pillow 12.3.0.
These Windows commands have not been claimed as a Windows execution result.
Dependency/platform differences can change skeleton sampling; review any
different results rather than changing acceptance limits to match them.

## Next decision

The amended tested-domain pass supports considering a **separate, single-sample
1024×1024 raster-to-vector validation**. It is not evidence that vectorization
already works and does not start v0.5 automatically. Retain the repaired-neck
warning and require topology and geometry checks in that future study.
