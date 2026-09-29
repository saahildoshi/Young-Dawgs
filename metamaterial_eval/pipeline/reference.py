"""Strict reference loading and explicit PNG preparation with provenance."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from metamaterial_eval.io import validate_binary_array

from .config import PipelineConfig, default_evaluator_path
from .evaluator import load_evaluator
from .state import utc_now, write_json
from .topology import structural_reference


def array_sha256(array: np.ndarray) -> str:
    canonical = np.ascontiguousarray(array, dtype=np.uint8)
    return hashlib.sha256(canonical.tobytes()).hexdigest()


def _load_reference(
    source: Path,
    *,
    expected_shape: tuple[int, int],
    threshold: float | None,
    prepare_png: bool = False,
) -> np.ndarray:
    if prepare_png and source.suffix.lower() != ".png":
        raise ValueError("--prepare-png is only supported for PNG references.")
    if threshold is not None and not 0.0 <= float(threshold) <= 1.0:
        raise ValueError("threshold must lie in [0, 1].")
    if source.suffix.lower() == ".npy":
        return validate_binary_array(
            np.load(source, allow_pickle=False), expected_shape=expected_shape
        )
    if source.suffix.lower() != ".png":
        raise ValueError("Pipeline v0.1 reference input must be .npy or .png.")

    with Image.open(source) as image:
        grayscale = np.asarray(image.convert("L"), dtype=np.uint8)
    if prepare_png:
        # Match prepare_target's established order: grayscale -> threshold ->
        # nearest-neighbor resize. Resampling binary pixels cannot add gray values.
        effective_threshold = 0.5 if threshold is None else float(threshold)
        thresholded = (grayscale / 255.0 >= effective_threshold).astype(np.uint8)
        resized = Image.fromarray(thresholded * 255).resize(
            (expected_shape[1], expected_shape[0]),
            resample=Image.Resampling.NEAREST,
        )
        return np.ascontiguousarray(np.asarray(resized) != 0, dtype=np.uint8)
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
    prepare_png: bool = False,
    evaluator_path: Path | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Save canonical NPY/PNG files, optionally preparing a raw PNG explicitly.

    Preparation thresholds grayscale intensities at 0.5 by default and resizes
    with nearest-neighbor interpolation. Strict loading remains the default.
    """
    source = source_path.resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Reference does not exist: {source}")
    reference_dir.mkdir(parents=True, exist_ok=False)
    raw = _load_reference(
        source,
        expected_shape=config.image_shape,
        threshold=threshold,
        prepare_png=prepare_png,
    )
    evaluator = load_evaluator(str((evaluator_path or default_evaluator_path()).resolve()))
    binary, cleaning = structural_reference(raw, config.topology_mode, evaluator)
    for name, array in (("reference_raw", raw), ("reference_structural", binary)):
        np.save(reference_dir / f"{name}.npy", array, allow_pickle=False)
        Image.fromarray(array * 255).save(reference_dir / f"{name}.png")
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
        "sha256_raw_binary": array_sha256(raw),
        "sha256_structural_binary": array_sha256(binary),
        "raw_path": str(reference_dir / "reference_raw.npy"),
        "structural_path": str(reference_dir / "reference_structural.npy"),
        "topology_mode": config.topology_mode,
        "cleaning": cleaning,
        "active_target": "reference_structural",
        "created_at_utc": utc_now(),
        "pipeline_version": config.pipeline_version,
        "evaluator_version": config.evaluator_version,
        "evaluator_sha256": evaluator_hash,
        "threshold": 0.5 if prepare_png and threshold is None else threshold,
        "preprocessing": {"enabled": prepare_png},
    }
    if source.suffix.lower() == ".png":
        with Image.open(source) as image:
            metadata["source_shape"] = [image.height, image.width]
            metadata["source_image_mode"] = image.mode
    if prepare_png:
        metadata["preprocessing"].update(
            {
                "steps": ["grayscale", "threshold", "resize"],
                "interpolation": "nearest_neighbor",
                "aspect_ratio_policy": "stretch_to_target_shape",
                "output_shape": list(config.image_shape),
            }
        )
    write_json(reference_dir / "metadata.json", metadata)
    return binary, metadata
