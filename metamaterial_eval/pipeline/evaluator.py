"""Thin integration layer around the frozen evaluator v1.1."""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Sequence

import numpy as np

from .config import PipelineConfig
from .execution import run_subprocess
from .prompts import format_sampled_curve
from .scripts import sha256_bytes, sha256_file
from .state import write_json


class PipelineEvaluationError(RuntimeError):
    pass


@lru_cache(maxsize=4)
def load_evaluator(path_string: str) -> ModuleType:
    """Load the accepted evaluator file without copying its implementation."""
    path = Path(path_string).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Evaluator v1.1 not found: {path}")
    spec = importlib.util.spec_from_file_location("young_dawgs_evaluator_v1_1", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluator_hash(evaluator_path: Path) -> str:
    return sha256_file(evaluator_path)


def extract_target_descriptors(
    binary: np.ndarray,
    config: PipelineConfig,
    evaluator_path: Path,
) -> dict[str, Any]:
    """Calculate target descriptors exclusively with evaluator v1.1 functions."""
    evaluator = load_evaluator(str(evaluator_path.resolve()))
    array = np.ascontiguousarray(binary, dtype=np.uint8)
    bins, bin_counts = evaluator.radial_bin_map(array.shape, config.max_r)
    basic = evaluator.basic_metrics(array)
    local = evaluator.local_dimensions(array)
    s2 = evaluator.s2_periodic(array, config.max_r, bins, bin_counts)
    lineal = evaluator.lineal_path_periodic_directional(array, config.max_r)
    radius = np.arange(config.max_r + 1, dtype=int)
    result = {
        "evaluator_version": config.evaluator_version,
        "evaluator_sha256": evaluator_hash(evaluator_path),
        "shape": list(array.shape),
        "phase_convention": {"solid": 1, "void": 0},
        "connectivity": 4,
        "validity_rule": "f_largest >= 0.98 and Px == 1 and Py == 1",
        "phi_s": float(basic["phi_s"]),
        "f_largest": float(basic["f_largest"]),
        "Px": int(basic["Px"]),
        "Py": int(basic["Py"]),
        "valid": bool(evaluator.structure_is_valid(basic)),
        "mean_strut_thickness": float(local["mean_strut_thickness"]),
        "p10_strut_thickness": float(local["p10_strut_thickness"]),
        "median_pore_diameter": float(local["median_pore_diameter"]),
        "curves": {
            "r": radius.tolist(),
            "s2": np.asarray(s2, dtype=float).tolist(),
            "lineal_path": np.asarray(lineal["l"], dtype=float).tolist(),
            "l_x": np.asarray(lineal["l_x"], dtype=float).tolist(),
            "l_y": np.asarray(lineal["l_y"], dtype=float).tolist(),
            "l_45": np.asarray(lineal["l_45"], dtype=float).tolist(),
            "l_135": np.asarray(lineal["l_135"], dtype=float).tolist(),
        },
    }
    result["sampled_descriptors"] = {
        "radii": list(config.sample_radii),
        "s2": [result["curves"]["s2"][r] for r in config.sample_radii],
        "lineal_path": [
            result["curves"]["lineal_path"][r] for r in config.sample_radii
        ],
        "s2_text": format_sampled_curve(
            result["curves"]["r"], result["curves"]["s2"], config.sample_radii
        ),
        "lineal_path_text": format_sampled_curve(
            result["curves"]["r"],
            result["curves"]["lineal_path"],
            config.sample_radii,
        ),
    }
    return result


def audit_generated_samples(
    samples_dir: Path,
    expected_seeds: Sequence[int],
    expected_shape: tuple[int, int],
    evaluator_path: Path,
) -> dict[str, Any]:
    """Audit exact seeds, binary validity, PNG companions, and duplicates."""
    evaluator = load_evaluator(str(evaluator_path.resolve()))
    paths = evaluator.find_samples(samples_dir)
    seed_audit = evaluator.audit_sample_seeds(paths, expected_seeds)
    expected = list(int(seed) for seed in expected_seeds)
    problems: list[str] = []
    if len(paths) != len(expected):
        problems.append(f"expected {len(expected)} NPY files, found {len(paths)}")
    for key in ("missing_seeds", "unexpected_seeds", "duplicate_seeds", "unparseable_files"):
        if seed_audit[key]:
            problems.append(f"{key}: {seed_audit[key]}")

    content_hashes: dict[str, list[str]] = {}
    png_missing: list[str] = []
    for path in paths:
        array = evaluator.load_binary(path, expected_shape=expected_shape)
        digest = sha256_bytes(np.ascontiguousarray(array).tobytes())
        content_hashes.setdefault(digest, []).append(path.name)
        if not path.with_suffix(".png").is_file():
            png_missing.append(path.with_suffix(".png").name)
    duplicate_outputs = {
        digest: names for digest, names in content_hashes.items() if len(names) > 1
    }
    if duplicate_outputs:
        problems.append(f"identical outputs: {duplicate_outputs}")
    if png_missing:
        problems.append(f"missing PNG companions: {png_missing}")

    return {
        "expected_seeds": expected,
        **seed_audit,
        "npy_count": len(paths),
        "png_missing": png_missing,
        "duplicate_content_hashes": duplicate_outputs,
        "passed": not problems,
        "problems": problems,
    }


def run_v1_1_evaluation(
    *,
    samples_dir: Path,
    reference_path: Path,
    output_dir: Path,
    expected_seeds: Sequence[int],
    config: PipelineConfig,
    evaluator_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Audit a sample set, then execute frozen evaluator v1.1 unchanged."""
    audit = audit_generated_samples(
        samples_dir, expected_seeds, config.image_shape, evaluator_path
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "pipeline_seed_audit.json", audit)
    if not audit["passed"]:
        raise PipelineEvaluationError(
            "Generated sample audit failed: " + "; ".join(audit["problems"])
        )

    development_default = list(expected_seeds) == list(config.development_seeds)
    evaluator_expected_count = len(expected_seeds) if development_default else 0
    command = [
        sys.executable,
        str(evaluator_path.resolve()),
        str(samples_dir.resolve()),
        "--target",
        str(reference_path.resolve()),
        "--output-dir",
        str(output_dir.resolve()),
        "--max-r",
        str(config.max_r),
        "--expected-count",
        str(evaluator_expected_count),
    ]
    result = run_subprocess(
        command,
        cwd=output_dir,
        log_dir=output_dir / "execution",
        timeout_seconds=config.evaluator_timeout_seconds,
    )
    if not result.succeeded:
        stderr = Path(result.stderr_path).read_text(encoding="utf-8")
        raise PipelineEvaluationError(
            f"Evaluator v1.1 failed (return code {result.return_code}): {stderr}"
        )
    report_path = output_dir / "evaluation_summary.json"
    if not report_path.is_file():
        raise PipelineEvaluationError("Evaluator did not create evaluation_summary.json.")
    with report_path.open(encoding="utf-8") as stream:
        report = json.load(stream)
    return report, audit


def seed_from_filename(filename: str) -> int | None:
    match = re.search(r"(?:sample|seed)[_-]?(\d+)", filename, re.IGNORECASE)
    return int(match.group(1)) if match else None
