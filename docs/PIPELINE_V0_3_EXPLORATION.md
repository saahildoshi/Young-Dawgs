# Pipeline v0.3: parametric exploration

This is a separate workflow alongside replication. Version v0.2 already names
the connected-reference policy, so the exploration milestone is versioned v0.3.
Existing `start`, `resume`, prompts, experiments and evaluator v1.1 are unchanged.

| Workflow | Purpose | Commands |
|---|---|---|
| Replication | Same morphology parameters, multiple seeds; match an anchor | `start`, `resume`, `status` |
| Exploration | Pipeline-selected parameter combinations, replicated by seed | `explore-start`, `explore-resume`, `explore-status` |

## What is implemented

1. Retain the largest 4-connected reference component; recompute all descriptors.
   The retained anchor must span both image axes. Raw and structural files remain separate.
2. Define a three-dimensional envelope: solid fraction, strut scale, pore scale.
3. Save a seeded Latin-hypercube plan: by default 10 designs × 2 seeds = 20 samples.
4. Ask the LLM for one module exposing
   `generate_microstructure(seed, solid_fraction_target, strut_scale, pore_scale)`.
5. Invoke that function with pipeline-selected arguments. The pipeline saves
   each returned array as PNG/NPY without cleanup. Each call is repeated once
   to check exact reproducibility with identical arguments (40 calls for 20 outputs).
6. Measure every sample, compare requested and achieved controls, and report
   engineering, morphology-family and envelope compliance independently.

No FEM, CAD conversion, automatic LLM calls, automated mechanical optimization,
or claims of independent parameter control are included. Anisotropy as a fourth
control is deferred until its definition and calibration are chosen.

## Start on Windows

From the repository root, with `.venv` activated:

```powershell
python -m pip install -e .
python -m metamaterial_eval.pipeline explore-start `
  "data\test_references\ai_trabecular_v1\prepared\reference_structural.npy" `
  --output-dir "experiments\pipeline_v0.3\exploration_test_01" `
  --s2-limit 0.25 --lineal-limit 0.25
```

**The two 0.25 limits above are illustrative smoke-test choices, not validated
scientific cutoffs.** Set explicit limits appropriate to your study. The CLI
requires them to avoid silently assuming a universal morphology tolerance.
The supplied AI-edited reference is synthetic/test-only, not experimental data.

For a different raw PNG, substitute its path and add `--prepare-png --threshold 0.5`.
Inspect segmentation first: a threshold of 0.5 is not universally appropriate.

Send `prompt.txt` and `reference\reference_structural.png` from the new folder
to the LLM. Save the entire reply in `response.txt`. Review its Python before
execution, then run:

```powershell
python -m metamaterial_eval.pipeline explore-resume `
  "experiments\pipeline_v0.3\exploration_test_01" --execute
python -m metamaterial_eval.pipeline explore-status `
  "experiments\pipeline_v0.3\exploration_test_01"
```

`--execute` acknowledges that generated Python executes with your account's
permissions. A subprocess timeout is NOT a security sandbox. Only run code you
trust. The module must not perform work on import; it must return a binary uint8
array, not write images or choose its own design combinations.

## Design choices

Default bounds are relative to the cleaned anchor, not percentage-point offsets:

| Control | Anchor measurement | Default range | Units |
|---|---|---|---|
| `solid_fraction_target` | `phi_s` | 0.90–1.10 × anchor; upper clipped to 0.999 | Dimensionless |
| `strut_scale` | `mean_strut_thickness` | 0.85–1.15 × anchor | Pixels |
| `pore_scale` | `median_pore_diameter` | 0.80–1.20 × anchor | Pixels |

These are development heuristics. Thickness, pores and density are coupled;
some combinations may be infeasible. The generator should expose interpretable
controls rather than add islands or force measured values to exact targets.
If a required anchor descriptor is undefined, supply explicit bounds or choose
a different anchor. The pipeline never replaces an undefined measurement with zero.

Override bounds with `--bounds "my_bounds.json"` containing all three entries:

```json
{
  "solid_fraction_target": [0.27, 0.33],
  "strut_scale": [2.3, 3.1],
  "pore_scale": [5.6, 8.4]
}
```

Those numbers are examples, not calibrated values for the synthetic reference.
Bounds must be finite, positive and increasing; solid fraction must be below one.

Use `--designs 20 --replicates 1` for 20 unique parameter points, or the default
10 × 2 for replication. `--design-seed 42` controls the Latin hypercube.
`--seed-start 0` gives replicate seeds 0 and 1 at **each** design by default.
Reusing seeds across designs is deliberate common-random-number pairing;
different replicates within each design have different seeds.

The full realized plan is saved, so results do not depend on regenerating a
Latin hypercube under a future SciPy version. Keep design and replicate seeds
unchanged for comparisons of generator revisions.

## Acceptance and interpretation

- Engineering validity: exactly one solid component and percolation in both axes.
- Family pass: both $E_{S_2}$ and $E_L$ are below their configured upper limits.
  Errors use frozen v1.1's $\mathrm{RMSE}(sample,target)/\mathrm{RMS}(target)$
  over radii 0–64, including radius zero. Density changes therefore affect the
  curve gates. These errors are not minimized to zero in exploration.
- Envelope pass: achieved solid fraction, mean thickness and median enclosed-pore
  diameter each lie within their respective design bounds. This does not require
  exact agreement with the individual requested value.
- `eligible`: all three numeric checks pass. This is **not** FEM qualification,
  manufacturability certification or proof of visual morphology fidelity.

Failed and invalid rows remain visible. Missing measurements are blank in CSV
and null in JSON. Missing outputs do not become zero-valued geometry. Generated
images are never cleaned, bridged, dilated or silently repaired by the pipeline.

## Outputs

| File | Meaning |
|---|---|
| `exploration_manifest.json` | Mode, version, hashes, status and latest attempt |
| `design_plan.json` | Bounds, sampler seed, replicate seeds, limits and requested values per design |
| `reference/` | Raw/structural references, descriptors and provenance |
| `prompt.txt`, `response.txt` | Manual LLM handoff |
| `generator.py`, `generator_sha256.txt` | Extracted module and exact saved-byte hash |
| `attempt_001/samples/design_NNN_rep_NN.npy/.png` | Saved geometry, indexed by design and replicate rather than seed alone |
| `attempt_001/samples/generation_results.json` | Success/failure record for each attempted function call |
| `attempt_001/execution/` | Process logs, timeout and exit status |
| `attempt_001/environment.json` | Python and scientific-library versions used for this attempt |
| `attempt_001/morphology_dataset.csv` | Per-sample requested controls, measured geometry, curve errors, gate flags and image hashes/paths |
| `attempt_001/exploration_report.json` | Full curves, design summaries, duplicate groups and control diagnostics |
| `attempt_001/report.md` | Concise results and generator-revision guidance |
| `attempt_001/montage.png` | Anchor and every planned design for visual QC |
| `attempt_001/control_response.png` | Requested versus achieved metrics |

Per-design statistics use sample SD (`ddof=1`). One replicate gives undefined
within-design SD, not zero. Control diagnostics use complete replicate groups:

- Spearman association between a requested control and its measured design mean;
- SD across design means;
- root-mean-square within-design SD;
- measured and requested spans.

These are exploratory diagnostics from a small multivariable design, not causal
effects or calibrated sensitivity coefficients. Exact duplicates are flagged,
but unique pixels alone do not prove meaningful diversity. Inspect the montage,
control plots and failed rows. Follow up with one-factor sweeps or larger designs
before claiming that controls move geometry predictably.

## Recovery and revisions

`COMPLETE` means all planned geometries were measured, **not** all constraints
passed. Check the report counts. A blank response remains waiting. Runtime,
contract or missing-output failures yield `FAILED`, with partial rows retained.

To retry the **same unchanged generator**, preserving earlier attempts:

```powershell
python -m metamaterial_eval.pipeline explore-resume `
  "experiments\pipeline_v0.3\exploration_test_01" --execute --retry-failed
```

Each retry creates a fresh numbered attempt. An interrupted `RUNNING` attempt
requires the same flag. Do not rerun while an earlier process is still active.
Repeated resume on a completed run is a no-op.

For a revised generator, create a new output directory with the same reference,
bounds, limits and seeds. Supply the previous report as additional model feedback
and save the revised response in the new run. There is no automatic I2F1 revision
loop in exploration v0.3. Historical attempts, extracted scripts, design plans and
responses are not overwritten to accommodate revisions. Modified protected inputs
are rejected. All manifest artifact paths are relative to the run for portability.

## Verification

```powershell
python -m pytest tests -q
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest validation/test_evaluator.py -q
Remove-Item Env:EVALUATOR_PATH
```

Tests include Latin-hypercube stratification, repeated seeds, ignored controls,
duplicate geometry, islands, undefined metrics, failed attempts, byte-preserving
extraction, fixed-input integrity and the manual execution boundary. Synthetic
test generators exercise software behavior; they do not establish LLM performance.
