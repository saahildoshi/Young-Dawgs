# Pipeline v0.1 Reference

Pipeline v0.1 implements the project’s I2F1 experimental workflow for binary
2-D microstructures. It converts a reference into a traceable target, prepares
quantitative prompts, executes model-produced procedural generators, evaluates
each development iteration with frozen evaluator v1.1, and validates the frozen
final generator on a separate held-out seed set.

The pipeline ends at evaluated `256 x 256` binary images. It does **not** create
CAD geometry, contours, meshes, STL/STEP/DXF/SVG files, ANSYS inputs, or
manufacturing corrections.

## Fixed experimental design

| Property | Pipeline v0.1 value |
|---|---|
| Prompt strategy | I2F1 |
| Pipeline version | 0.1.0 |
| Prompt version | 1.0 |
| Evaluator | accepted v1.1 |
| Array contract | `uint8`, `256 x 256`, solid `1`, void `0` |
| Topology | 4-connectivity |
| Validity | $f_\mathrm{largest} \ge 0.98$, $P_x=1$, and $P_y=1$ |
| Development seeds | 0–19 (20 samples) |
| Held-out seeds | 100–119 (20 samples) |
| Maximum feedback rounds | 3 after iteration 0 |
| Default generator timeout | 1800 seconds |
| Default evaluator timeout | 600 seconds |
| Descriptor radii | 0, 1, 2, 4, 8, 16, 32, 64 pixels |

Evaluator v1.1 in `validation/evaluators/evaluator_v1_1.py` is the scientific
source of truth. The pipeline imports its functions to measure the target and
runs its CLI unchanged to evaluate generated ensembles. Do not casually modify
that evaluator: changing it would break comparability with the analytically
validated pilot methodology.

Evaluator v1.1's CLI count option assumes seeds begin at zero. For held-out
seeds 100–119, the pipeline therefore performs its own exact seed audit first
and invokes the unchanged evaluator with its count check disabled. Consult
`pipeline_seed_audit.json` for authoritative held-out seed identity; all
scientific descriptor and plotting behavior still comes from evaluator v1.1.

## Install and inspect the CLI

From the repository root:

```bash
source .venv-macos/bin/activate
python -m pip install -e .
python -m metamaterial_eval.pipeline --help
python -m metamaterial_eval.pipeline start --help
```

The editable install also provides the equivalent command
`young-dawgs-pipeline`.

## Start a run

This command uses the existing canonical reference and creates a run named
`concrete_01`:

```bash
python -m metamaterial_eval.pipeline start \
  data/reference/reference_binary.npy \
  --run-name concrete_01
```

The resulting run is:

```text
experiments/pipeline_v0.1/reference_binary/concrete_01/
```

The `start` command performs all deterministic work up to the first model
boundary:

1. validates and copies the reference;
2. writes the canonical `reference_binary.npy` and `reference.png`;
3. records provenance and SHA-256 hashes;
4. measures target descriptors with evaluator v1.1;
5. writes `target_metrics.json`;
6. renders `iteration_0/prompt_0.txt` and its structured context;
7. pauses at `WAITING_FOR_INITIAL_LLM`.

For an ambiguous grayscale PNG, the pipeline fails unless an explicit threshold
is supplied:

```bash
python -m metamaterial_eval.pipeline start \
  path/to/reference.png \
  --threshold 0.5 \
  --run-name png_reference_01
```

Strict binary PNGs containing only 0 and 255 do not need a threshold. References
must already be `256 x 256`; Pipeline v0.1 deliberately performs no silent
resizing or morphology-changing cleanup.

## Manual LLM handoff

Pipeline v0.1 ships with the `manual-file` provider because the repository has
no authenticated model API integration. The status command always identifies
the exact file required next:

```bash
python -m metamaterial_eval.pipeline status \
  experiments/pipeline_v0.1/reference_binary/concrete_01
```

For iteration 0:

1. Open `iteration_0/prompt_0.txt`.
2. Attach `reference/reference.png` to the multimodal model.
3. Send the prompt without changing it.
4. Save the model’s complete raw response, unmodified, as
   `iteration_0/response_0.txt`.
5. Resume the run:

```bash
python -m metamaterial_eval.pipeline resume \
  experiments/pipeline_v0.1/reference_binary/concrete_01
```

The pipeline extracts one unambiguous complete Python script, hashes it, runs it
on seeds 0–19, audits all NPY/PNG outputs, evaluates the ensemble, calculates
raw target differences, and writes `iteration_1/prompt_1.txt`. It then pauses at
`WAITING_FOR_REVISION`.

Repeat the same handoff for `response_1.txt`, `response_2.txt`, and
`response_3.txt`:

```bash
python -m metamaterial_eval.pipeline resume \
  experiments/pipeline_v0.1/reference_binary/concrete_01
```

One resume command advances through every deterministic stage until the next
model boundary. After iteration 3, the pipeline freezes the exact final script,
runs it unchanged on seeds 100–119, evaluates those held-out samples, and writes
the final reports. Held-out measurements are created only after the script hash
is frozen and are structurally absent from every feedback-builder input.

## Execution-repair boundary

If a generated script exits unsuccessfully or times out, the pipeline preserves
its partial outputs and logs, writes `repair_prompt.txt`, and pauses at
`WAITING_FOR_EXECUTION_REPAIR`. Send only that repair prompt to the model and
save the raw answer as `repair_response.txt`, then resume normally.

Exactly one execution repair is permitted per iteration. The pipeline does not
edit model-produced morphology code itself. A second execution failure is
preserved as a non-recoverable failed run.

If a stage is marked failed but the manifest names a `recoverable_state`, fix
the recorded cause and use:

```bash
python -m metamaterial_eval.pipeline resume \
  experiments/pipeline_v0.1/reference_binary/concrete_01 \
  --retry-failed
```

Never delete failed output merely to make a run appear successful; retain it as
part of the experimental record.

## Pipeline Prompt v1.0 generator contract

Every new pipeline generator must accept:

```bash
python iteration_0.py \
  --seed-start 0 \
  --num-samples 20 \
  --output-dir path/to/output
```

The script must default to 20 samples with seeds 0–19, but it must also support
any requested consecutive seed range. The pipeline uses the identical frozen
script for held-out validation:

```bash
python final_generator.py \
  --seed-start 100 \
  --num-samples 20 \
  --output-dir path/to/heldout
```

Each seed must yield one `.npy` and one `.png` file whose filename contains the
integer seed. Arrays must satisfy the fixed binary contract. Missing,
unexpected, duplicated, nonbinary, wrongly shaped, or byte-identical outputs
cause an explicit audit failure.

This CLI contract applies only to Pipeline Prompt v1.0. Historical pilot prompts
and generators remain unchanged.

## Run structure

```text
experiments/pipeline_v0.1/<reference_name>/<run_id>/
├── manifest.json
├── reference/
│   ├── source.npy or source.png
│   ├── reference_binary.npy
│   ├── reference.png
│   ├── metadata.json
│   └── target_metrics.json
├── iteration_0/
│   ├── prompt_0.txt
│   ├── prompt_context.json
│   ├── response_0.txt
│   ├── iteration_0.py
│   ├── iteration_0_sha256.txt
│   ├── execution/
│   ├── generated/development/
│   └── evaluation/
├── iteration_1/ ... iteration_3/
└── final/
    ├── final_generator.py
    ├── generator_sha256.txt
    ├── development/reference.json
    ├── heldout/
    │   ├── generated/
    │   ├── execution/
    │   └── evaluation/
    ├── summary.json
    └── summary.md
```

Development artifacts remain in their original iteration directories. The final
development record is a small provenance reference rather than a duplicate of
large sample and plot directories.

## What each record means

| Record | Meaning |
|---|---|
| `manifest.json` | Durable state, configuration, hashes, runtimes, repairs, counts, and final metrics |
| `reference/metadata.json` | Input provenance, phase convention, dimensions, threshold, and canonical hash |
| `target_metrics.json` | Target scalar descriptors and complete/sampled $S_2$ and lineal-path curves |
| `prompt_context.json` | Exact data classes and file references used to build a prompt; always records `heldout_data_included: false` |
| `response_i.txt` | Immutable raw model response supplied by the researcher/provider |
| `iteration_i.py` | Conservatively extracted, syntactically checked model-generated script |
| `execution/` | Command, return code, UTC timestamps, wall time, standard output, and standard error |
| `pipeline_seed_audit.json` | Exact seed, count, PNG companion, format, and identical-output checks |
| `evaluation_summary.json` | Complete structured evaluator v1.1 result |
| `target_comparison.json` | Unweighted absolute/relative differences used for feedback |
| `final/summary.json` | Machine-readable development trajectory, held-out results, provenance, and warnings |
| `final/summary.md` | Concise Obsidian-compatible run report |

The evaluator also writes its existing montage and plots for $S_2$, lineal path,
pore distributions, diversity, and related diagnostics. Those files are retained
inside each `evaluation/` directory.

## State and recovery model

The manifest records the completed boundary, so expensive work is not repeated
after an interruption. Normal states include:

```text
CREATED → REFERENCE_READY → TARGET_EVALUATED
→ WAITING_FOR_INITIAL_LLM
→ DEVELOPMENT_GENERATED → DEVELOPMENT_EVALUATED
→ WAITING_FOR_REVISION (repeated through iteration 3)
→ FINAL_GENERATOR_FROZEN → HELDOUT_GENERATED
→ HELDOUT_EVALUATED → COMPLETE
```

`FAILED` retains a plain-language reason. Where deterministic retry is safe, it
also retains the state from which `--retry-failed` may continue.

## Inspecting results

Read `final/summary.md` first. It contains target values, the full development
trajectory, final development performance, held-out performance,
development-to-held-out differences, the frozen script hash, runtime, repair
usage, diversity status, copy flags, and automated warnings.

Use `final/summary.json` for analysis scripts. Use each iteration’s full
`evaluation_summary.json` and evaluator figures when diagnosing a metric or
verifying a warning. Pipeline v0.1 reports raw measurements and does not invent
an aggregate weighted quality score or an automated scientific conclusion.

## Future API-backed provider

The nondeterministic boundary is intentionally narrow:

```python
class LLMProvider:
    def generate(initial_prompt, reference_image, context) -> LLMResponse | None: ...
    def revise(feedback_prompt, previous_context) -> LLMResponse | None: ...
```

An API integration should add one provider implementation in
`metamaterial_eval/pipeline/providers.py` and register it in `make_provider`.
The runner will continue to preserve raw responses and all downstream stages
without change. Credentials must come from normal secure configuration; they
must never be hard-coded in the repository.

## Current limitations and safety

- Only strict `.npy` and `.png` references are accepted.
- The shipped provider is manual; there is no authenticated API call.
- The pipeline runs model-generated code in a separate process and isolated
  output directory, but this is not an operating-system security sandbox.
  Inspect untrusted scripts before execution on a sensitive machine.
- The final generator is iteration 3 by experimental design; v0.1 does not
  perform model selection or early stopping.
- Integrity hashes detect changes to the reference, evaluator, and frozen
  generator. They do not replace repository backups or version control.

## Validation commands

Run the orchestration tests:

```bash
python -m pytest tests/test_pipeline.py -q
```

Run all reusable-package tests and the frozen evaluator acceptance suite:

```bash
python -m pytest tests -q
EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py \
  python -m pytest validation/test_evaluator.py -q
```
