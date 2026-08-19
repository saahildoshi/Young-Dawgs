"""Batch evaluation and machine-/LLM-readable reporting."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from .io import load_binary, validate_binary_array
from .metrics import (
    compute_basic_metrics,
    compute_lineal_path,
    compute_local_dimensions,
    compute_s2_correlation,
)


SCALAR_METRICS = (
    "solid_volume_fraction",
    "largest_component_fraction",
    "mean_strut_thickness",
    "p10_strut_thickness",
    "median_pore_diameter",
    "nrmse_s2",
    "nrmse_lineal_path",
)


def _natural_key(path: Path) -> list[str | int]:
    return [
        int(token) if token.isdigit() else token.lower()
        for token in re.split(r"(\d+)", path.name)
    ]


def _json_safe(value: Any) -> Any:
    """Recursively convert NumPy values and non-finite floats for strict JSON."""
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _normalized_rmse(sample: np.ndarray, target: np.ndarray) -> float:
    """Return RMSE normalized by the target curve's RMS magnitude."""
    sample = np.asarray(sample, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    if sample.shape != target.shape:
        raise ValueError(
            f"Curve shape mismatch: sample {sample.shape}, target {target.shape}."
        )
    finite = np.isfinite(sample) & np.isfinite(target)
    if not finite.any():
        return float("nan")
    difference_rms = float(np.sqrt(np.mean((sample[finite] - target[finite]) ** 2)))
    target_rms = float(np.sqrt(np.mean(target[finite] ** 2)))
    if target_rms <= np.finfo(np.float64).eps:
        return 0.0 if difference_rms <= np.finfo(np.float64).eps else float("inf")
    return difference_rms / target_rms


def make_target_dict(binary_array: np.ndarray, max_r: int = 64) -> dict[str, Any]:
    """Compute the canonical target dictionary accepted by batch evaluation."""
    binary = validate_binary_array(binary_array)
    return {
        "binary_array": binary,
        "basic_metrics": compute_basic_metrics(binary),
        "s2_correlation": compute_s2_correlation(binary, max_r=max_r),
        "lineal_path": compute_lineal_path(binary, max_r=max_r),
        "local_dimensions": compute_local_dimensions(binary),
    }


def _canonicalize_target(target_dict: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(target_dict, dict):
        raise TypeError("target_dict must be a dictionary.")

    binary_value = target_dict.get("binary_array", target_dict.get("binary"))
    if binary_value is not None:
        binary = validate_binary_array(binary_value)
        provided_s2 = target_dict.get("s2_correlation")
        if isinstance(provided_s2, dict):
            inferred_max_r = len(np.asarray(provided_s2["s2"])) - 1
        elif provided_s2 is not None:
            inferred_max_r = len(np.asarray(provided_s2)) - 1
        else:
            inferred_max_r = 64
        canonical = make_target_dict(binary, max_r=inferred_max_r)
        # Explicitly supplied values take precedence.
        canonical.update(target_dict)
        canonical["binary_array"] = binary
    else:
        canonical = dict(target_dict)

    s2_value = canonical.get("s2_correlation", canonical.get("s2"))
    lineal_value = canonical.get("lineal_path", canonical.get("l"))
    if s2_value is None or lineal_value is None:
        raise ValueError(
            "target_dict requires a binary_array or both S2 and lineal-path curves."
        )

    s2_curve = s2_value["s2"] if isinstance(s2_value, dict) else s2_value
    lineal_curve = lineal_value["l"] if isinstance(lineal_value, dict) else lineal_value
    s2_curve = np.asarray(s2_curve, dtype=np.float64)
    lineal_curve = np.asarray(lineal_curve, dtype=np.float64)
    if s2_curve.ndim != 1 or lineal_curve.ndim != 1:
        raise ValueError("Target S2 and lineal-path curves must be one-dimensional.")
    if len(s2_curve) != len(lineal_curve):
        raise ValueError("Target S2 and lineal-path curves must have equal lengths.")

    canonical["_s2_curve"] = s2_curve
    canonical["_lineal_curve"] = lineal_curve
    canonical["_max_r"] = len(s2_curve) - 1
    return canonical


def _sample_files(path: Path) -> list[Path]:
    """Return one input per stem, or a single file when a file is given."""
    if path.is_file():
        if path.suffix.lower() not in {".npy", ".png"}:
            raise ValueError(f"Unsupported sample file type: {path.suffix}")
        return [path]

    selected: dict[str, Path] = {}
    for candidate in path.iterdir():
        if not candidate.is_file() or candidate.suffix.lower() not in {".npy", ".png"}:
            continue
        if candidate.name in {"metrics_report.json"}:
            continue
        current = selected.get(candidate.stem)
        if current is None or candidate.suffix.lower() == ".npy":
            selected[candidate.stem] = candidate
    return sorted(selected.values(), key=_natural_key)


def _evaluate_sample(
    path: Path,
    *,
    target_s2: np.ndarray,
    target_lineal: np.ndarray,
    target_shape: tuple[int, int] | None,
    max_r: int,
) -> dict[str, Any]:
    binary = load_binary(path, expected_shape=target_shape)
    basic = compute_basic_metrics(binary)
    s2 = compute_s2_correlation(binary, max_r=max_r)
    lineal = compute_lineal_path(binary, max_r=max_r)
    local = compute_local_dimensions(binary)
    valid = bool(
        basic["largest_component_fraction"] >= 0.98
        and basic["percolates_x"]
        and basic["percolates_y"]
    )
    return {
        "file": path.name,
        "valid": valid,
        "solid_volume_fraction": basic["solid_volume_fraction"],
        "largest_component_fraction": basic["largest_component_fraction"],
        "percolates_x": basic["percolates_x"],
        "percolates_y": basic["percolates_y"],
        "component_count": basic["component_count"],
        "mean_strut_thickness": local["mean_strut_thickness"],
        "p10_strut_thickness": local["p10_strut_thickness"],
        "median_pore_diameter": local["median_pore_diameter"],
        "nrmse_s2": _normalized_rmse(s2["s2"], target_s2),
        "nrmse_lineal_path": _normalized_rmse(lineal["l"], target_lineal),
        "curves": {
            "r": s2["r"],
            "s2": s2["s2"],
            "l": lineal["l"],
            "l_x": lineal["l_x"],
            "l_y": lineal["l_y"],
        },
    }


def _aggregate(
    records: list[dict[str, Any]], *, valid_only: bool
) -> dict[str, dict[str, float | int | None]]:
    selected = [record for record in records if record["valid"] or not valid_only]
    result: dict[str, dict[str, float | int | None]] = {}
    for metric in SCALAR_METRICS:
        values = np.asarray([record[metric] for record in selected], dtype=np.float64)
        values = values[np.isfinite(values)]
        result[metric] = {
            "mean": float(np.mean(values)) if values.size else None,
            "std": float(np.std(values, ddof=0)) if values.size else None,
            "count": int(values.size),
        }
    return result


def _target_summary(target: dict[str, Any]) -> dict[str, Any]:
    basic = target.get("basic_metrics", {})
    local = target.get("local_dimensions", {})
    return {
        "shape": (
            list(target["binary_array"].shape)
            if "binary_array" in target
            else None
        ),
        "solid_volume_fraction": basic.get("solid_volume_fraction"),
        "largest_component_fraction": basic.get("largest_component_fraction"),
        "percolates_x": basic.get("percolates_x"),
        "percolates_y": basic.get("percolates_y"),
        "mean_strut_thickness": local.get("mean_strut_thickness"),
        "p10_strut_thickness": local.get("p10_strut_thickness"),
        "median_pore_diameter": local.get("median_pore_diameter"),
        "curves": {
            "r": np.arange(target["_max_r"] + 1),
            "s2": target["_s2_curve"],
            "l": target["_lineal_curve"],
        },
    }


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}g}"
    return str(value)


def _text_report(report: dict[str, Any]) -> str:
    all_stats = report["aggregate_all_samples"]
    valid_stats = report["aggregate_valid_samples"]
    target = report["target"]
    lines = [
        "METAMATERIAL GENERATOR EVALUATION",
        "=" * 36,
        f"Samples discovered: {report['sample_count']}",
        f"Samples evaluated: {report['evaluated_sample_count']}",
        f"Valid samples: {report['valid_sample_count']}",
        f"Failed samples: {report['failed_sample_count']}",
        (
            "Validity rule: largest-component fraction >= 0.98 and "
            "percolation in both x and y."
        ),
        "",
        "TARGET",
        f"  solid_volume_fraction: {_fmt(target['solid_volume_fraction'])}",
        f"  largest_component_fraction: {_fmt(target['largest_component_fraction'])}",
        f"  mean_strut_thickness_px: {_fmt(target['mean_strut_thickness'])}",
        f"  p10_strut_thickness_px: {_fmt(target['p10_strut_thickness'])}",
        f"  median_pore_diameter_px: {_fmt(target['median_pore_diameter'])}",
        "",
        "ENSEMBLE METRICS (mean +/- population std)",
    ]
    for metric in SCALAR_METRICS:
        all_metric = all_stats[metric]
        valid_metric = valid_stats[metric]
        lines.append(
            f"  {metric}: all={_fmt(all_metric['mean'])} +/- "
            f"{_fmt(all_metric['std'])} (n={all_metric['count']}); "
            f"valid={_fmt(valid_metric['mean'])} +/- "
            f"{_fmt(valid_metric['std'])} (n={valid_metric['count']})"
        )

    if report["errors"]:
        lines.extend(["", "FAILED INPUTS"])
        for error in report["errors"]:
            lines.append(f"  {error['file']}: {error['error']}")

    lines.extend(
        [
            "",
            "LLM REFINEMENT SIGNAL",
            (
                "  Reduce mean nrmse_s2 to improve two-point spatial statistics; "
                "reduce mean nrmse_lineal_path to improve continuous solid-path "
                "statistics."
            ),
            (
                "  Increase valid_sample_count by enforcing one dominant "
                "4-connected solid network spanning both image axes."
            ),
            (
                "  Thickness and pore dimensions are reported in pixels and should "
                "be compared against the target values above."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def evaluate_generator_output(
    target_dict: dict[str, Any],
    samples_folder: str | Path,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate all unique ``.npy``/``.png`` samples and write two reports.

    If both formats share a stem, the ``.npy`` file is evaluated once and the
    PNG is treated as its visualization. Invalid samples remain in the ensemble
    statistics; a second aggregate reports valid samples only. Per-curve NRMSE
    is normalized by the target curve's RMS magnitude.
    """
    samples_path = Path(samples_folder)
    if not samples_path.exists():
        raise FileNotFoundError(f"Samples path does not exist: {samples_path}")
    if not samples_path.is_file() and not samples_path.is_dir():
        raise NotADirectoryError(
            f"Samples path is not a file or directory: {samples_path}"
        )

    report_dir = (
        Path(output_dir)
        if output_dir is not None
        else (samples_path.parent if samples_path.is_file() else samples_path)
    )
    report_dir.mkdir(parents=True, exist_ok=True)

    target = _canonicalize_target(target_dict)
    max_r = target["_max_r"]
    target_shape = (
        tuple(target["binary_array"].shape) if "binary_array" in target else (256, 256)
    )
    paths = _sample_files(samples_path)
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for path in paths:
        try:
            records.append(
                _evaluate_sample(
                    path,
                    target_s2=target["_s2_curve"],
                    target_lineal=target["_lineal_curve"],
                    target_shape=target_shape,
                    max_r=max_r,
                )
            )
        except Exception as exc:  # isolate malformed generator outputs
            errors.append({"file": path.name, "error": f"{type(exc).__name__}: {exc}"})

    report = {
        "schema_version": "1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "definitions": {
            "connectivity": 4,
            "validity": (
                "largest_component_fraction >= 0.98 and percolates_x and "
                "percolates_y"
            ),
            "standard_deviation": "population (ddof=0)",
            "curve_nrmse": "RMSE(sample, target) / RMS(target)",
            "lineal_radial_estimator": (
                "denominator-weighted lattice directions 0, 45, 90, 135 degrees"
            ),
            "strut_thickness": "2*solid EDT sampled on the solid skeleton",
            "pore_diameter": (
                "one 2*maximum void EDT value per enclosed 4-connected "
                "void component; boundary-touching void is excluded"
            ),
        },
        "target": _target_summary(target),
        "sample_count": len(paths),
        "evaluated_sample_count": len(records),
        "valid_sample_count": sum(record["valid"] for record in records),
        "failed_sample_count": len(errors),
        "aggregate_all_samples": _aggregate(records, valid_only=False),
        "aggregate_valid_samples": _aggregate(records, valid_only=True),
        "samples": records,
        "errors": errors,
    }
    safe_report = _json_safe(report)

    json_path = report_dir / "metrics_report.json"
    text_path = report_dir / "metrics_report.txt"
    with json_path.open("w", encoding="utf-8") as stream:
        json.dump(safe_report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    text_path.write_text(_text_report(safe_report), encoding="utf-8")
    return safe_report
