# Reference Data

- `reference.png`: original grayscale research image.
- `reference_binary.png`: thresholded 256×256 visualization.
- `reference_binary.npy`: canonical numerical target (`uint8`, solid = 1).

Evaluation commands should use the NPY file to avoid ambiguity from image
thresholding or color-profile handling.
