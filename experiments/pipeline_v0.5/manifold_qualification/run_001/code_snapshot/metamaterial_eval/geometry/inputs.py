"""Strict scientific input contract, deliberately stricter than image loading."""
from pathlib import Path
import hashlib

import numpy as np
from PIL import Image


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_mask(mask):
    if not isinstance(mask, np.ndarray):
        raise ValueError("Require an explicit NumPy array, not an inferred array-like.")
    if mask.ndim != 2 or mask.shape[0] != mask.shape[1] or mask.size == 0:
        raise ValueError("Require a nonempty square (N,N) two-dimensional mask.")
    if mask.dtype != np.uint8:
        raise ValueError("Require uint8; implicit dtype conversion is forbidden.")
    if not np.all((mask == 0) | (mask == 1)):
        raise ValueError("Require binary values 0 (void) and 1 (solid).")
    if not mask.any():
        raise ValueError("Empty solid phase is unsupported in v0.5A.")
    return mask


def load_binary_reference(path, png_path=None):
    path = Path(path)
    if path.suffix.lower() != ".npy":
        raise ValueError("Canonical input must be NPY; images cannot define geometry.")
    mask = validate_mask(np.load(path, allow_pickle=False))
    if png_path is not None:
        png_path = Path(png_path)
        if png_path.suffix.lower() != ".png":
            raise ValueError("Preview must be PNG.")
        with Image.open(png_path) as image:
            # Reject palettes, alpha, grayscale thresholds and color conversions.
            if image.mode != "L":
                raise ValueError("Preview must be a grayscale L-mode binary PNG.")
            preview = np.asarray(image)
        if preview.shape != mask.shape or not np.array_equal(preview, mask * 255):
            raise ValueError("PNG/NPY phase mismatch: require white=solid, black=void exactly.")
    return mask


COORDINATES = {
    "units": "raster_cell", "physical_scale": None,
    "cell_mapping": "(row,column) -> [column,column+1] x [row,row+1]",
    "center_mapping": "(column+0.5,row+0.5)",
    "x_axis": "right", "y_axis": "down", "display_transform": [1, 0, 0, 1, 0, 0],
    "solid": 1, "void": 0,
}
