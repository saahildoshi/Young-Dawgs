"""Strict reference canonicalization and provenance metadata."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from metamaterial_eval.io import validate_binary_array

from .config import PipelineConfig
from .state import utc_now, write_json


def array_sha256(array: np.ndarray) -> str:
    canonical = np.ascontiguousarray(array, dtype=np.uint8)
    return hashlib.sha256(canonical.tobytes()).hexdigest()


def _load_reference(
    source: Path,
    *,
    expected_shape: tuple[int, int],
    threshold: float | None,
) -> np.ndarray:
    if source.suffix.lower() == ".npy":
        return validate_binary_array(
            np.load(source, allow_pickle=False), expected_shape=expected_shape
        )
    if source.suffix.lower() != ".png":
        raise ValueError("Pipeline v0.1 reference input must be .npy or .png.")

    with Image.open(source) as image:
        grayscale = np.asarray(image.convert("L"), dtype=np.uint8)
    if tuple(grayscale.shape) != expected_shape:
        raise ValueError(
            f"Expected reference shape {expected_shape}, received {grayscale.shape}."
        )
    unique = np.unique(grayscale)
    if np.all(np.isin(unique, (0, 255))):
        return np.ascontiguousarray(grayscale != 0, dtype=np.uint8)
    if threshold is None:
        raise ValueError(
            "Reference PNG contains ambiguous grayscale values. Supply --threshold "
            "explicitly; no silent threshold is applied."
        )
    if not 0.0 <= float(threshold) <= 1.0:
        raise ValueError("threshold must lie in [0, 1].")
    return np.ascontiguousarray(grayscale / 255.0 >= float(threshold), dtype=np.uint8)


def canonicalize_reference(
    source_path: Path,
    reference_dir: Path,
    config: PipelineConfig,
    *,
    threshold: float | None,
    evaluator_hash: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Create canonical NPY/PNG reference files without morphology changes."""
    source = source_path.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Reference does not exist: {source}")
    reference_dir.mkdir(parents=True, exist_ok=False)
    binary = _load_reference(
        source, expected_shape=config.image_shape, threshold=threshold
    )
    canonical_npy = reference_dir / "reference_binary.npy"
    canonical_png = reference_dir / "reference.png"
    np.save(canonical_npy, binary, allow_pickle=False)
    Image.fromarray(binary * 255, mode="L").save(canonical_png)
    source_copy = reference_dir / f"source{source.suffix.lower()}"
    shutil.copy2(source, source_copy)

    metadata = {
        "source_path": str(source),
        "source_copy": str(source_copy),
        "canonical_path": str(canonical_npy),
        "canonical_png": str(canonical_png),
        "shape": list(binary.shape),
        "dtype": str(binary.dtype),
        "phase_convention": {"solid": 1, "void": 0},
        "sha256_canonical_binary": array_sha256(binary),
        "created_at_utc": utc_now(),
        "pipeline_version": config.pipeline_version,
        "evaluator_version": config.evaluator_version,
        "evaluator_sha256": evaluator_hash,
        "threshold": threshold,
    }
    write_json(reference_dir / "metadata.json", metadata)
    return binary, metadata

