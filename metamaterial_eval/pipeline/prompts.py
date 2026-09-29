"""Deterministic rendering of versioned I2F1 prompt templates."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence
from .topology import validity_rule


TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _template(name: str) -> str:
    return (TEMPLATE_DIR / name).read_text(encoding="utf-8")


def format_number(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.6g}"


def format_boolean(value: Any) -> str:
    return "true" if bool(value) else "false"


def format_sampled_curve(
    radius: Sequence[int],
    curve: Sequence[float],
    sample_radii: Sequence[int],
) -> str:
    """Format selected curve values deterministically in requested order."""
    radius_to_value = {int(r): float(v) for r, v in zip(radius, curve)}
    missing = [int(r) for r in sample_radii if int(r) not in radius_to_value]
    if missing:
        raise ValueError(f"Curve does not contain requested radii: {missing}")
    return ", ".join(
        f"r={int(r)}: {radius_to_value[int(r)]:.6f}" for r in sample_radii
    )


def _target_fields(target: dict[str, Any]) -> dict[str, str]:
    sampled = target["sampled_descriptors"]
    return {
        "solid_volume_fraction": format_number(target["phi_s"]),
        "largest_component_fraction": (
            f"{target['f_largest']:.6f}" if target.get("prompt_version") == "1.1"
            else format_number(target["f_largest"])
        ),
        "component_count": format_number(target.get("component_count")),
        "topology_mode": target.get("topology_mode", "preserve_reference"),
        "validity_rule": validity_rule(target.get("topology_mode", "preserve_reference")),
        "topology_instructions": _topology_instructions(target),
        "left_right_percolation": format_boolean(target["Px"]),
        "top_bottom_percolation": format_boolean(target["Py"]),
        "mean_strut_thickness_px": format_number(target["mean_strut_thickness"]),
        "p10_strut_thickness_px": format_number(target["p10_strut_thickness"]),
        "median_pore_diameter_px": format_number(target["median_pore_diameter"]),
        "sampled_s2": sampled["s2_text"],
        "sampled_lineal_path": sampled["lineal_path_text"],
    }


def _topology_instructions(target: dict[str, Any]) -> str:
    if target.get("topology_mode") == "single_connected_network":
        return (
            "The reference has been preprocessed to retain only its largest "
            "4-connected solid component.\n"
            "The generated solid phase must form one 4-connected component.\n"
            "All solid pixels must belong to the same network, spanning the image "
            "horizontally and vertically.\n"
            "Do not create disconnected solid islands, detached particles, or isolated regions.\n"
            "Do not add isolated solid islands merely to match solid volume fraction.\n"
            "Preserve the target morphology and other descriptors by modifying the "
            "connected network itself.\n"
            "The measured percolation values below describe the reference; the generated "
            "design must span both axes even if the reference does not."
        )
    return (
        "The reference topology has been preserved without removing components.\n"
        "Match the measured descriptors and visible morphology. This policy retains "
        "the historical engineering rule f_largest >= 0.98 with percolation on both axes; "
        "it does not require exactly one component."
    )


def build_initial_prompt(target: dict[str, Any]) -> str:
    """Render the configured prompt version using measured target descriptors."""
    name = "initial_i2_v1_1.txt" if target.get("prompt_version") == "1.1" else "initial_i2.txt"
    return _template(name).format(**_target_fields(target))


def format_generated_metrics(report: dict[str, Any]) -> str:
    summary = report["ensemble_summary"]
    lines = []
    for key in (
        "component_count",
        "phi_s",
        "f_largest",
        "mean_strut_thickness",
        "p10_strut_thickness",
        "median_pore_diameter",
        "E_S2",
        "E_L",
    ):
        if key not in summary:
            continue
        item = summary[key]
        lines.append(
            f"- {key}: {format_number(item['mean'])} +/- "
            f"{format_number(item['std'])}"
        )
    return "\n".join(lines)


def build_feedback_prompt(
    target: dict[str, Any],
    development_report: dict[str, Any],
    comparison: dict[str, Any],
    *,
    round_number: int,
    max_rounds: int,
    development_count: int,
) -> str:
    """Render feedback from development data only.

    The signature intentionally has no held-out input, enforcing the research
    boundary structurally.
    """
    fields = _target_fields(target)
    fields.update(
        {
            "round_number": str(round_number),
            "max_rounds": str(max_rounds),
            "generated_metrics": format_generated_metrics(development_report),
            "valid_count": str(development_report["valid_sample_count"]),
            "development_count": str(development_count),
            "difference_summary": "\n".join(
                f"- {line}" for line in comparison["summary_lines"]
            ),
        }
    )
    name = "feedback_i2_v1_1.txt" if target.get("prompt_version") == "1.1" else "feedback_i2.txt"
    return _template(name).format(**fields)


def build_execution_repair_prompt(stderr: str) -> str:
    return _template("execution_repair.txt").format(
        traceback=stderr.rstrip() or "No traceback was emitted."
    )
