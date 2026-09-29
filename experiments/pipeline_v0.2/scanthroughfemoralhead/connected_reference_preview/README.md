# Trabecular connected-reference preview

This is a deterministic preprocessing preview, **not a completed LLM experiment**.
The source was the canonical reference from
`experiments/pipeline_v0.1/scanthroughfemoralhead/image_01/reference/reference_binary.npy`.
The previous experiment was not modified.

| Measurement | Raw | Structural |
|---|---:|---:|
| Solid components (4-connected) | 162 | 1 |
| Solid pixels | 20,374 | 17,863 |
| Solid fraction | 0.310883 | 0.272568 |
| Largest-component fraction | 0.876755 | 1.000000 |
| Horizontal / vertical percolation | 1 / 1 | 1 / 1 |

The structural reference retains the largest component. Removed: 161 components,
2,511 solid pixels (12.3245% of raw solid, 3.83148% of image area).

- `reference_comparison.png`: raw, structural and removed-material panels.
- `reference_raw.npy/.png`: uncleaned binary target.
- `reference_structural.npy/.png`: cleaned active target.
- `reference_binary.npy` and `reference.png`: active-target compatibility aliases.
- `raw_target_metrics.json` and `target_metrics.json`: independently computed
  complete descriptors from frozen evaluator v1.1.
- `metadata.json`: source provenance, hashes and removal definitions.
- `prompt_preview.txt`: connected-network prompt for inspection.

Paths in preview provenance reflect the preparation computer. Start the actual
experiment on Windows using the commands in
[the v0.2 guide](../../../../docs/PIPELINE_V0_2.md); do not treat this directory as
a resumable run. Generated samples will be evaluated unchanged, without cleanup.
