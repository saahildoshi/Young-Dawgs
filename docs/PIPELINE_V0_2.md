# Pipeline v0.2 — connected-network references

Pipeline v0.2 uses prompt version 1.1 and the **unchanged frozen evaluator v1.1**.
It separates reference topology preparation from generated-sample assessment.
All arrays remain 256 × 256, uint8, with 1 = solid and 4-connectivity.

## Choose the topology policy

| Mode | Reference preparation | Generated-sample engineering validity |
|---|---|---|
| `preserve_reference` (default) | Preserve every solid component | $f_\mathrm{largest}\ge0.98$, $P_x=P_y=1$ (legacy rule) |
| `single_connected_network` | Retain only the largest 4-connected solid component | $N_\mathrm{components}=1$, $P_x=P_y=1$ |

Use the second mode for the trabecular experiment and subsequent connected-network
references. Preserving particulate references is supported; a particulate-specific
engineering validity rule has not been introduced.

Cleaning occurs only on the reference. **Generated images are never cleaned by
the pipeline.** The generator must produce connected structures itself.
An empty solid reference is rejected in single-network mode. Equal-size
components select the first row-major label. A nonspanning retained network
produces a warning, not fabricated percolation or added bridges.

## Rerun the trabecular case on Windows

Run these commands in PowerShell from the repository root with your environment
activated. This creates a new experiment without modifying the previous run:

```powershell
python -m pip install -e .
python -m metamaterial_eval.pipeline start `
  "experiments\pipeline_v0.1\scanthroughfemoralhead\image_01\reference\reference_binary.npy" `
  --topology-mode single_connected_network `
  --run-name trabecular_connected_01
```

The source filename determines the reference folder. The new run is therefore
`experiments\pipeline_v0.2\reference_binary\trabecular_connected_01`.
Do not resume the old run expecting a new topology policy.

1. Send `iteration_0\prompt_0.txt` and
   `reference\reference_structural.png` from the **new run** to your LLM.
2. Save the complete response in `iteration_0\response_0.txt`.
3. Advance with:

```powershell
python -m metamaterial_eval.pipeline resume `
  "experiments\pipeline_v0.2\reference_binary\trabecular_connected_01"
```

4. At each subsequent waiting boundary, send the next numbered prompt and save
   the corresponding numbered response; repeat the same resume command.
5. Read `final\summary.md` and `final\summary.json` after completion.

The default design remains iterations 0–3, development seeds 0–19, and held-out
seeds 100–119. Held-out results do not enter revision prompts.
Only the manual-file LLM provider is available: starting a run does not obtain
model responses automatically.

Inspect progress or retry a corrected failure:

```powershell
python -m metamaterial_eval.pipeline status `
  "experiments\pipeline_v0.2\reference_binary\trabecular_connected_01"
python -m metamaterial_eval.pipeline resume `
  "experiments\pipeline_v0.2\reference_binary\trabecular_connected_01" --retry-failed
```

## Use a new PNG

```powershell
python -m metamaterial_eval.pipeline start "data\reference\new_network.png" `
  --prepare-png --threshold 0.5 `
  --topology-mode single_connected_network --run-name connected_01
```

This converts to grayscale, thresholds light pixels as solid, resizes using
nearest-neighbor interpolation, then extracts the largest component. Non-square
inputs are stretched to 256 × 256. Inspect the structural PNG before sending it.
Strict NPY inputs must already satisfy the array contract.

To inspect preprocessing without creating an experiment:

```powershell
python -m metamaterial_eval.pipeline prepare-reference "data\reference\new_network.png" `
  --prepare-png --threshold 0.5 --topology-mode single_connected_network `
  --output-dir "experiments\reference_previews\new_network"
```

Choose a new output directory each time; existing previews are not overwritten.
Preview output includes both descriptor sets and `prompt_preview.txt`, but no
run manifest. Use `start` with the original source to create an actual run.

## What the files mean

| Artifact | Purpose |
|---|---|
| `reference_raw.npy/.png` | Binary reference after segmentation/resizing, before topology cleaning |
| `reference_structural.npy/.png` | Active target after the selected topology policy |
| `reference_binary.npy`, `reference.png` | Compatibility aliases containing the active structural target |
| Original source copy | Unmodified source provenance |
| `metadata.json` | Hashes, preprocessing settings, raw/structural metrics, removal statistics and warnings |
| `target_metrics.json` | All descriptors freshly measured on the structural target, including component count, thickness, pores, $S_2$ and $L$ |
| `raw_target_metrics.json` | Raw-reference descriptors, available in standalone previews |
| `evaluation_summary.json` | Original frozen evaluator report, retaining legacy validity |
| `pipeline_evaluation_summary.json` | **Authoritative policy-aware report** for new runs: component-count statistics, strict validity, valid-only statistics, and explicit legacy counts |
| `evaluation/target_comparison.json`, numbered feedback prompts | Target/ensemble differences and topology-specific revision guidance |
| `final/summary.md`, `final/summary.json` | Development trajectory, final/held-out component counts, selected validity rule and cleaning provenance |

Frozen evaluator plots and its original reports retain the legacy validity rule.
Use the policy-aware JSON and pipeline final summary for single-network valid
counts. Morphological measurements themselves are unchanged; only target
preparation and engineering classification differ.

Removal fractions have explicit denominators:

- `removed_solid_fraction`: removed solid pixels / raw solid pixels.
- `removed_image_fraction`: removed solid pixels / all image pixels.
- `retained_solid_fraction`: retained solid pixels / all image pixels.

Prompts prohibit disconnected islands added to match density and instruct the
model to change the connected network itself. Feedback includes generated
component-count statistics. A one-pixel island fails the new engineering rule,
even when $f_\mathrm{largest}>0.99$.

## Prepared trabecular reference

The saved preview is
`experiments/pipeline_v0.2/scanthroughfemoralhead/connected_reference_preview/`.
It is **not a completed new LLM experiment**.

| Measurement | Raw | Structural |
|---|---:|---:|
| Solid component count | 162 | 1 |
| Solid pixels | 20,374 | 17,863 |
| Solid fraction | 0.310883 | 0.272568 |
| Largest-component fraction | 0.876755 | 1.000000 |
| Horizontal / vertical percolation | 1 / 1 | 1 / 1 |
| Mean strut thickness (pixels) | 2.655004 | 2.693554 |
| 10th-percentile strut thickness (pixels) | 2 | 2 |
| Median pore diameter (pixels) | 6.324555 | 7.211103 |

Removed: 161 components and 2,511 pixels, approximately 12.3245% of the
original solid. Inspect `reference_comparison.png` for the raw target,
structural target and removed material. Both full descriptor sets were
recalculated, including the complete correlation and lineal-path curves.

Compare the old and new experiments as different target-preparation protocols;
their descriptor errors are relative to different targets, so smaller errors
alone do not establish improvement. Compare morphology, component counts,
percolation, curve shapes, thickness, pores and diversity together.
Single-component spanning geometry is a topology criterion, not proof of
mechanical strength, manufacturability or CAD readiness.

## Compatibility and checks

Existing v0.1 manifests keep their original prompts and legacy validity.
No historical experiment is migrated automatically. Pipeline v0.2 stores
results separately and leaves the accepted evaluator file unchanged.

```powershell
python -m pytest tests -q
$env:EVALUATOR_PATH = "validation/evaluators/evaluator_v1_1.py"
python -m pytest validation/test_evaluator.py -q
Remove-Item Env:EVALUATOR_PATH
```

See [the original workflow guide](PIPELINE_V0_1.md) for generator response
format, recovery details and other unchanged operational conventions.
