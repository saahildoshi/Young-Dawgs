"""Raw metric differences and final research summaries."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

from .prompts import format_number
from .state import write_json


METRIC_MAP = {
    "solid_volume_fraction": ("phi_s", "phi_s"),
    "largest_component_fraction": ("f_largest", "f_largest"),
    "mean_strut_thickness": ("mean_strut_thickness", "mean_strut_thickness"),
    "p10_strut_thickness": ("p10_strut_thickness", "p10_strut_thickness"),
    "median_pore_diameter": ("median_pore_diameter", "median_pore_diameter"),
}


def _relative_percent(value: float, reference: float) -> float | None:
    return 100.0 * (value - reference) / reference if reference != 0 else None


def compare_to_target(
    target: dict[str, Any],
    report: dict[str, Any],
    expected_count: int,
) -> dict[str, Any]:
    """Create interpretable, unweighted target-vs-development differences."""
    generated = report["ensemble_summary"]
    differences: dict[str, Any] = {}
    lines: list[str] = []
    for output_key, (target_key, generated_key) in METRIC_MAP.items():
        target_value = float(target[target_key])
        mean = generated[generated_key]["mean"]
        std = generated[generated_key]["std"]
        if mean is None:
            differences[output_key] = {
                "target": target_value,
                "generated_mean": None,
                "generated_population_std": std,
                "absolute_difference": None,
                "relative_percent_error": None,
            }
            lines.append(f"{output_key} is undefined for this ensemble.")
            continue
        mean = float(mean)
        difference = mean - target_value
        relative = _relative_percent(mean, target_value)
        differences[output_key] = {
            "target": target_value,
            "generated_mean": mean,
            "generated_population_std": float(std),
            "absolute_difference": difference,
            "relative_percent_error": relative,
        }
        direction = "above" if difference > 0 else "below"
        if abs(difference) <= 1e-12:
            lines.append(f"{output_key} matches the target within numerical precision.")
        elif relative is not None:
            lines.append(
                f"{output_key} is {abs(relative):.2f}% {direction} the target "
                f"(mean {mean:.6g}, target {target_value:.6g})."
            )

    valid_count = int(report["valid_sample_count"])
    differences["valid_sample_count"] = {
        "target": expected_count,
        "generated": valid_count,
        "absolute_difference": valid_count - expected_count,
    }
    differences["mean_s2_nrmse"] = {
        "target": 0.0,
        "generated_mean": generated["E_S2"]["mean"],
        "generated_population_std": generated["E_S2"]["std"],
        "absolute_difference": generated["E_S2"]["mean"],
        "relative_percent_error": None,
    }
    differences["mean_lineal_path_nrmse"] = {
        "target": 0.0,
        "generated_mean": generated["E_L"]["mean"],
        "generated_population_std": generated["E_L"]["std"],
        "absolute_difference": generated["E_L"]["mean"],
        "relative_percent_error": None,
    }
    lines.extend(
        [
            f"{valid_count} of {expected_count} samples satisfy the topology validity rule.",
            f"Mean S2 NRMSE is {format_number(generated['E_S2']['mean'])}.",
            f"Mean lineal-path NRMSE is {format_number(generated['E_L']['mean'])}.",
        ]
    )
    return {"differences": differences, "summary_lines": lines}


def _summary_values(report: dict[str, Any]) -> dict[str, Any]:
    summary = report["ensemble_summary"]
    return {
        "valid_sample_count": report["valid_sample_count"],
        "sample_count": report["sample_count"],
        "phi_s": summary["phi_s"]["mean"],
        "f_largest": summary["f_largest"]["mean"],
        "mean_strut_thickness": summary["mean_strut_thickness"]["mean"],
        "p10_strut_thickness": summary["p10_strut_thickness"]["mean"],
        "median_pore_diameter": summary["median_pore_diameter"]["mean"],
        "E_S2": summary["E_S2"]["mean"],
        "E_L": summary["E_L"]["mean"],
        "D_pair": report["diversity"]["D_pair"],
        "diversity_healthy": report["diversity"]["healthy"],
        "copy_flags": report["novelty"]["flagged_files"],
    }


def _compare_dev_heldout(
    development: dict[str, Any], heldout: dict[str, Any]
) -> dict[str, Any]:
    comparison: dict[str, Any] = {}
    for key in (
        "phi_s",
        "f_largest",
        "mean_strut_thickness",
        "p10_strut_thickness",
        "median_pore_diameter",
        "E_S2",
        "E_L",
        "D_pair",
    ):
        dev = development[key]
        held = heldout[key]
        if dev is None or held is None:
            comparison[key] = {
                "development": dev,
                "heldout": held,
                "absolute_difference": None,
                "relative_percent_change": None,
            }
        else:
            dev_float = float(dev)
            held_float = float(held)
            comparison[key] = {
                "development": dev_float,
                "heldout": held_float,
                "absolute_difference": held_float - dev_float,
                "relative_percent_change": _relative_percent(held_float, dev_float),
            }
    return comparison


def collect_warnings(
    reports: Mapping[int | str, dict[str, Any]],
    audits: Mapping[str, dict[str, Any]],
) -> list[str]:
    warnings: list[str] = []
    for label, report in reports.items():
        if report["valid_sample_count"] < report["sample_count"]:
            warnings.append(
                f"{label}: {report['valid_sample_count']} of "
                f"{report['sample_count']} samples satisfied topology validity."
            )
        if report["novelty"]["flagged_files"]:
            warnings.append(
                f"{label}: copy-detection flags: {report['novelty']['flagged_files']}"
            )
        if not report["diversity"]["healthy"]:
            warnings.append(f"{label}: evaluator diversity criterion was not satisfied.")
        for key, item in report["ensemble_summary"].items():
            if item["mean"] is None or (
                isinstance(item["mean"], float) and not math.isfinite(item["mean"])
            ):
                warnings.append(f"{label}: metric {key} is undefined or non-finite.")
    for label, audit in audits.items():
        if not audit["passed"]:
            warnings.append(f"{label}: sample audit failed: {audit['problems']}")
    return warnings


def build_final_summary(
    *,
    run_dir: Path,
    manifest: dict[str, Any],
    target: dict[str, Any],
    iteration_reports: Mapping[int, dict[str, Any]],
    heldout_report: dict[str, Any],
    audits: Mapping[str, dict[str, Any]],
    final_script: Path,
    final_hash: str,
    final_iteration: int,
    final_runtime_seconds: float,
) -> dict[str, Any]:
    """Write concise machine- and human-readable final run summaries."""
    trajectory = [
        {"iteration": iteration, **_summary_values(iteration_reports[iteration])}
        for iteration in sorted(iteration_reports)
    ]
    final_development = trajectory[-1]
    heldout = _summary_values(heldout_report)
    warnings = collect_warnings(
        {**{f"iteration_{k}": v for k, v in iteration_reports.items()}, "heldout": heldout_report},
        audits,
    )
    summary = {
        "run_id": manifest["run_id"],
        "reference_name": manifest["reference_name"],
        "pipeline_version": manifest["pipeline_version"],
        "evaluator_version": manifest["evaluator_version"],
        "prompt_strategy": "I2F1",
        "iterations_completed": len(trajectory),
        "target": {
            key: target[key]
            for key in (
                "phi_s",
                "f_largest",
                "Px",
                "Py",
                "mean_strut_thickness",
                "p10_strut_thickness",
                "median_pore_diameter",
            )
        },
        "development_trajectory": trajectory,
        "final_development_performance": final_development,
        "heldout_performance": heldout,
        "development_vs_heldout": _compare_dev_heldout(final_development, heldout),
        "generator_metadata": {
            "script_path": str(final_script),
            "sha256": final_hash,
            "source_iteration": final_iteration,
            "line_count": len(final_script.read_text(encoding="utf-8").splitlines()),
            "heldout_runtime_seconds": final_runtime_seconds,
            "repair_used": manifest["execution_repairs"],
            "target_information_available_to_generator": {
                "solid_fraction": True,
                "largest_component_fraction": True,
                "S2": True,
                "lineal_path": True,
                "thickness": True,
                "pore_diameter": True,
            },
        },
        "warnings": warnings,
    }
    final_dir = run_dir / "final"
    write_json(final_dir / "summary.json", summary)
    (final_dir / "summary.md").write_text(
        render_summary_markdown(summary), encoding="utf-8"
    )
    return summary


def render_summary_markdown(summary: dict[str, Any]) -> str:
    target = summary["target"]
    lines = [
        "# Pipeline Run Summary",
        "",
        f"Reference: `{summary['reference_name']}`  ",
        f"Run ID: `{summary['run_id']}`  ",
        f"Pipeline version: `{summary['pipeline_version']}`  ",
        f"Evaluator: `v{summary['evaluator_version']}`  ",
        "Prompt strategy: `I2F1`  ",
        f"Iterations completed: `{summary['iterations_completed']}`",
        "",
        "## Target",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in target.items():
        lines.append(f"| {key} | {format_number(value)} |")
    lines.extend(
        [
            "",
            "## Development trajectory",
            "",
            "| Iteration | Valid | $\\phi_s$ | $f_\\mathrm{largest}$ | "
            "Mean thickness | P10 | Pore diameter | $S_2$ NRMSE | $L$ NRMSE |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["development_trajectory"]:
        lines.append(
            f"| {row['iteration']} | {row['valid_sample_count']}/{row['sample_count']} | "
            f"{format_number(row['phi_s'])} | {format_number(row['f_largest'])} | "
            f"{format_number(row['mean_strut_thickness'])} | "
            f"{format_number(row['p10_strut_thickness'])} | "
            f"{format_number(row['median_pore_diameter'])} | "
            f"{format_number(row['E_S2'])} | {format_number(row['E_L'])} |"
        )
    for heading, key in (
        ("Final development performance", "final_development_performance"),
        ("Held-out performance", "heldout_performance"),
    ):
        row = summary[key]
        lines.extend(
            [
                "",
                f"## {heading}",
                "",
                f"- Valid samples: {row['valid_sample_count']}/{row['sample_count']}",
                f"- Mean $S_2$ NRMSE: {format_number(row['E_S2'])}",
                f"- Mean $L$ NRMSE: {format_number(row['E_L'])}",
                f"- $D_\\mathrm{{pair}}$: {format_number(row['D_pair'])}",
                f"- Copy flags: {row['copy_flags'] or 'none'}",
            ]
        )
    lines.extend(["", "## Development vs held-out comparison", ""])
    for key, item in summary["development_vs_heldout"].items():
        lines.append(
            f"- {key}: development {format_number(item['development'])}; "
            f"held-out {format_number(item['heldout'])}; difference "
            f"{format_number(item['absolute_difference'])}."
        )
    metadata = summary["generator_metadata"]
    lines.extend(
        [
            "",
            "## Generator metadata",
            "",
            f"- Script hash: `{metadata['sha256']}`",
            f"- Source iteration: {metadata['source_iteration']}",
            f"- Line count: {metadata['line_count']}",
            f"- Held-out runtime: {metadata['heldout_runtime_seconds']:.3f} s",
            f"- Repair usage: `{metadata['repair_used']}`",
            "- Target information used: solid fraction, largest-component fraction, "
            "$S_2$, lineal path, thickness, and pore diameter.",
            "",
            "## Notes / warnings",
            "",
        ]
    )
    if summary["warnings"]:
        lines.extend(f"- {warning}" for warning in summary["warnings"])
    else:
        lines.append("- No automated warnings were recorded.")
    lines.append("")
    return "\n".join(lines)
