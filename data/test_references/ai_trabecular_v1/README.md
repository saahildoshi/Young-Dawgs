# AI-edited trabecular-style pipeline test reference

For pipeline capability testing only. NOT experimental evidence, a restored
micrograph, or a faithful reconstruction of the original material.

The built-in image editor used the user's 187 x 187 original
`scanthroughfemoralhead (1).png` as its edit target. Despite a preservation
instruction, the result visibly changes pore layout, smoothness and strut widths.
Treat it as a synthetic trabecular-inspired reference, not an enhanced original.
The original and previous experiments were not modified.

`ai_edited_source.png` preserves the image-editor output. The existing pipeline
prepared it with grayscale conversion, threshold 0.5, nearest-neighbor resize
to 256 x 256, and largest-4-connected-component extraction. Before extraction
there were three components; 23 solid pixels outside the largest were removed.
No hole filling or bridging was applied by the pipeline.

`prepared/reference_structural.npy` and `.png` are the ready-to-use target.
`prepared/reference_raw.npy` and `.png` retain the thresholded image before
component extraction. JSON files preserve metrics and preparation provenance.

Start a new experiment from the repository root in Windows PowerShell:

```powershell
python -m metamaterial_eval.pipeline start "data\test_references\ai_trabecular_v1\prepared\reference_structural.npy" --topology-mode single_connected_network --run-name ai_test_01
```

The run will be under
`experiments\pipeline_v0.2\reference_structural\ai_test_01`.
Send its prompt and structural PNG to the model, save the numbered response,
then resume that run path. No LLM experiment has been executed for this asset.

The exact image-edit prompt is in `image_edit_prompt.txt`.
