"""Input/output utilities for binary microstructure images."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image


def _validate_threshold(threshold: float) -> float:
    threshold = float(threshold)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(f"threshold must lie in [0, 1], received {threshold}.")
    return threshold


def validate_binary_array(
    array: np.ndarray,
    *,
    expected_shape: tuple[int, int] | None = None,
) -> np.ndarray:
    """Validate and return a contiguous ``uint8`` array containing only 0 and 1.

    Parameters
    ----------
    array:
        Candidate 2-D binary array.
    expected_shape:
        Optional exact ``(height, width)`` requirement.
    """
    arr = np.asarray(array)
    if arr.ndim != 2:
        raise ValueError(f"Expected a 2-D array, received shape {arr.shape}.")
    if expected_shape is not None and tuple(arr.shape) != tuple(expected_shape):
        raise ValueError(
            f"Expected array shape {expected_shape}, received {arr.shape}."
        )
    if arr.size == 0:
        raise ValueError("Binary arrays must not be empty.")
    if not np.all(np.logical_or(arr == 0, arr == 1)):
        unique = np.unique(arr)
        preview = unique[:8].tolist()
        raise ValueError(f"Array must contain only 0 and 1; found {preview}.")
    return np.ascontiguousarray(arr, dtype=np.uint8)


def load_binary(
    path: str | Path,
    *,
    threshold: float = 0.5,
    expected_shape: tuple[int, int] | None = None,
) -> np.ndarray:
    """Load a binary ``.npy`` array or threshold a grayscale image.

    Image intensities are normalized to ``[0, 1]`` and values greater than or
    equal to ``threshold`` are interpreted as solid.
    """
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Input file does not exist: {source}")

    if source.suffix.lower() == ".npy":
        array = np.load(source, allow_pickle=False)
        return validate_binary_array(array, expected_shape=expected_shape)

    threshold = _validate_threshold(threshold)
    with Image.open(source) as image:
        grayscale = np.asarray(image.convert("L"), dtype=np.float64) / 255.0
    binary = (grayscale >= threshold).astype(np.uint8)
    return validate_binary_array(binary, expected_shape=expected_shape)


def prepare_target(
    image_path: str | Path,
    threshold: float = 0.5,
    target_shape: Sequence[int] = (256, 256),
) -> np.ndarray:
    """Create and persist a binary target image.

    The source is converted to grayscale, thresholded, and then resized with
    nearest-neighbor interpolation. The output files are written beside the
    input as ``<stem>_binary.png`` and ``<stem>_binary.npy``.

    Notes
    -----
    ``target_shape`` follows NumPy convention ``(height, width)``. Pillow uses
    ``(width, height)``, so the order is intentionally reversed when resizing.
    """
    source = Path(image_path)
    if not source.is_file():
        raise FileNotFoundError(f"Target image does not exist: {source}")
    threshold = _validate_threshold(threshold)

    shape = tuple(int(value) for value in target_shape)
    if len(shape) != 2 or any(value <= 0 for value in shape):
        raise ValueError(
            f"target_shape must contain two positive integers; received {shape}."
        )

    with Image.open(source) as image:
        grayscale = np.asarray(image.convert("L"), dtype=np.float64) / 255.0
    thresholded = (grayscale >= threshold).astype(np.uint8) * 255
    binary_image = Image.fromarray(thresholded, mode="L")
    resized = binary_image.resize((shape[1], shape[0]), resample=Image.Resampling.NEAREST)
    binary = (np.asarray(resized, dtype=np.uint8) > 0).astype(np.uint8)

    output_stem = source.with_name(f"{source.stem}_binary")
    png_path = output_stem.with_suffix(".png")
    npy_path = output_stem.with_suffix(".npy")
    Image.fromarray(binary * 255, mode="L").save(png_path)
    np.save(npy_path, binary, allow_pickle=False)
    return binary
