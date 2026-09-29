"""Prepare inspectable reference artifacts before starting a Windows run."""

from dataclasses import replace
from pathlib import Path

import numpy as np

from .config import PipelineConfig, default_evaluator_path
from .evaluator import evaluator_hash, extract_target_descriptors
from .prompts import build_initial_prompt
from .reference import canonicalize_reference
from .state import write_json


def prepare_reference(
    source: Path,
    output_dir: Path,
    *,
    config: PipelineConfig,
    threshold: float | None = None,
    prepare_png: bool = False,
    evaluator_path: Path | None = None,
) -> dict:
    """Create raw/structural images, both descriptor sets, and a prompt preview.

    This is a preprocessing preview, not a model experiment or run manifest.
    Existing output directories are rejected by canonicalize_reference.
    """
    evaluator_path = (evaluator_path or default_evaluator_path()).resolve()
    output_dir = output_dir.resolve()
    structural, metadata = canonicalize_reference(
        source, output_dir, config, threshold=threshold,
        evaluator_hash=evaluator_hash(evaluator_path), prepare_png=prepare_png,
        evaluator_path=evaluator_path,
    )
    raw = np.load(output_dir / "reference_raw.npy", allow_pickle=False)
    write_json(
        output_dir / "raw_target_metrics.json",
        extract_target_descriptors(
            raw, replace(config, topology_mode="preserve_reference"), evaluator_path
        ),
    )
    target = extract_target_descriptors(structural, config, evaluator_path)
    write_json(output_dir / "target_metrics.json", target)
    (output_dir / "prompt_preview.txt").write_bytes(build_initial_prompt(target).encode("utf-8"))
    return metadata
