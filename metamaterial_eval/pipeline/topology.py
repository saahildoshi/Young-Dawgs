"""Explicit reference and engineering policies layered over evaluator v1.1."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np
from scipy import ndimage

LEGACY_RULE = "f_largest >= 0.98 and Px == 1 and Py == 1"
SINGLE_NETWORK_RULE = "component_count == 1 and Px == 1 and Py == 1"


def validity_rule(mode: str) -> str:
    if mode == "single_connected_network":
        return SINGLE_NETWORK_RULE
    if mode == "preserve_reference":
        return LEGACY_RULE
    raise ValueError(f"Unknown topology mode: {mode}")


def is_valid(basic: dict[str, Any], mode: str) -> bool:
    validity_rule(mode)  # validate policy, including on empty arrays
    connected = (
        basic["component_count"] == 1
        if mode == "single_connected_network"
        else basic["f_largest"] >= 0.98
    )
    return bool(connected and basic["Px"] == 1 and basic["Py"] == 1)


def structural_reference(
    raw: np.ndarray, mode: str, evaluator: Any
) -> tuple[np.ndarray, dict[str, Any]]:
    """Retain the largest 4-connected component only when explicitly selected.

    Equal-size ties use the first label in row-major order. No bridges, dilation,
    hole filling, or generated-sample cleanup is performed.
    """
    validity_rule(mode)
    before = evaluator.basic_metrics(raw)
    selected = raw.copy()
    if mode == "single_connected_network":
        labels, count = ndimage.label(raw != 0, structure=evaluator.FOUR_CONNECTED)
        if count == 0:
            raise ValueError("Cannot retain a solid network: reference contains no solid pixels.")
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        selected = np.ascontiguousarray(labels == int(sizes.argmax()), dtype=np.uint8)
    after = evaluator.basic_metrics(selected)
    removed = before["solid_pixels"] - after["solid_pixels"]
    return selected, {
        "topology_mode": mode,
        "connectivity": 4,
        "tie_break": "first_label_in_row_major_order",
        "raw": before,
        "structural": after,
        "raw_component_count": before["component_count"],
        "retained_component_count": after["component_count"],
        "removed_component_count": before["component_count"] - after["component_count"],
        "removed_solid_pixels": removed,
        "removed_solid_fraction": removed / before["solid_pixels"] if before["solid_pixels"] else 0.0,
        "removed_image_fraction": removed / raw.size,
        "retained_solid_fraction": after["phi_s"],
        "fraction_definitions": {
            "removed_solid_fraction": "removed pixels / raw solid pixels",
            "removed_image_fraction": "removed pixels / all image pixels",
            "retained_solid_fraction": "retained solid pixels / all image pixels",
        },
        "reference_satisfies_engineering_rule": is_valid(after, mode),
        "warnings": (
            ["Structural reference does not span both axes; measured percolation is retained. "
             "Generated samples must still span both axes."]
            if mode == "single_connected_network" and not is_valid(after, mode) else []
        ),
    }


def apply_report_policy(report: dict[str, Any], mode: str, evaluator: Any) -> dict[str, Any]:
    """Add policy validity using the frozen evaluator's measured components.

    The caller retains the evaluator's original JSON. This derived report keeps
    legacy flags/counts explicit and recomputes valid-only statistics under the
    selected engineering rule. No measurements or sample images are changed.
    """
    result = deepcopy(report)
    result["topology_mode"] = mode
    result["validity_rule"] = validity_rule(mode)
    result["legacy_valid_sample_count"] = report["valid_sample_count"]
    result["legacy_validity_rule"] = LEGACY_RULE
    result["methodology"]["validity"] = validity_rule(mode)
    result["methodology"]["topology_policy_layer"] = "pipeline v0.2; evaluator v1.1 unchanged"
    for record in [result["target"], *result["samples"]]:
        record["legacy_valid"] = record["valid"]
        record["valid"] = is_valid(record, mode)
    records = result["samples"]
    valid_records = [record for record in records if record["valid"]]
    result["valid_sample_count"] = len(valid_records)
    result["disconnected_sample_count"] = sum(r["component_count"] > 1 for r in records)
    result["ensemble_summary"]["component_count"] = evaluator.metric_summary(records, "component_count")
    result["valid_ensemble_summary"] = {
        key: evaluator.metric_summary(valid_records, key)
        for key in result["ensemble_summary"]
    }
    return evaluator.json_safe(result)
