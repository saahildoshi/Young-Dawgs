"""Per-design measurements, replication diagnostics and family-envelope checks."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from metamaterial_eval.io import validate_binary_array
from .config import PipelineConfig, default_evaluator_path
from .design_space import CONTROLS
from .evaluator import extract_target_descriptors, load_evaluator
from .scripts import sha256_file
from .state import read_json, write_json

METRICS = ("phi_s", "mean_strut_thickness", "p10_strut_thickness",
           "median_pore_diameter", "component_count", "f_largest", "Px", "Py")


def stats(values: list) -> dict:
    values = np.asarray([v for v in values if v is not None and np.isfinite(v)], dtype=float)
    return {"count": len(values), "mean": float(values.mean()) if len(values) else None,
            "std": float(values.std(ddof=1)) if len(values) > 1 else None}


def evaluate_exploration(run: Path, attempt: Path, plan: dict) -> dict:
    """Measure saved geometry unchanged, keeping invalid samples in the dataset.

    Curve errors retain evaluator v1.1's RMS-target normalization. They are gates,
    not optimization objectives. Undefined measurements fail envelope checks.
    Between-design statistics use complete replicate groups to avoid bias from
    partially generated designs; invalid but measured geometries remain included.
    """
    evaluator_path = default_evaluator_path()
    evaluator = load_evaluator(str(evaluator_path))
    config = PipelineConfig(topology_mode="single_connected_network")
    target = read_json(run / "reference/target_metrics.json")
    generation_file = attempt / "samples/generation_results.json"
    generation = read_json(generation_file)["samples"] if generation_file.exists() else []
    generated = {r["sample_id"]: r for r in generation}
    records, hashes = [], {}
    for row in plan["samples"]:
        record = {**row, "measured": None, "engineering_valid": False,
                  "family_pass": False, "envelope_pass": False, "eligible": False}
        result = generated.get(row["sample_id"], {})
        if not result.get("success"):
            record["error"] = result.get("error", "No successful generator result (process failure or timeout).")
            records.append(record)
            continue
        try:
            path = attempt / "samples" / (row["sample_id"] + ".npy")
            array = np.load(path, allow_pickle=False)
            if array.dtype != np.uint8:
                raise ValueError("Saved sample dtype is not uint8.")
            array = validate_binary_array(array, expected_shape=(256, 256))
            measured = extract_target_descriptors(array, config, evaluator_path)
            errors = {name: evaluator.normalized_rmse(np.array(measured["curves"][curve]),
                                                     np.array(target["curves"][curve]))
                      for name, curve in (("E_S2", "s2"), ("E_L", "lineal_path"))}
            within = {control: measured[metric] is not None and
                      limits[0] <= measured[metric] <= limits[1]
                      for control, limits in plan["bounds"].items()
                      for metric in [CONTROLS[control][0]]}
            record.update(measured=measured, curve_errors=errors,
                          engineering_valid=measured["valid"],
                          family_pass=all(np.isfinite(v) and v <= plan["family_limits"][k]
                                          for k, v in errors.items()),
                          envelope_checks=within, envelope_pass=all(within.values()),
                          requested_minus_achieved={c: row["requested"][c] - measured[m]
                              if measured[m] is not None else None for c, (m, _) in CONTROLS.items()},
                          npy_path=str(path.relative_to(run)), sha256=sha256_file(path))
            record["eligible"] = all(record[k] for k in ("engineering_valid", "family_pass", "envelope_pass"))
            hashes.setdefault(record["sha256"], []).append(row["sample_id"])
        except (ValueError, OSError) as error:
            record["error"] = str(error)
        records.append(record)

    groups = []
    for design in range(plan["design_count"]):
        rows = [r for r in records if r["design_id"] == design]
        measured = [r["measured"] for r in rows if r["measured"] is not None]
        groups.append({"design_id": design, "requested": rows[0]["requested"],
                       "measured_count": len(measured),
                       "complete": len(measured) == plan["replicates"],
                       "metrics": {k: stats([r[k] for r in measured]) for k in METRICS}})
    sensitivity = {}
    for control, (metric, _) in CONTROLS.items():
        groups_ok = [g for g in groups if g["complete"] and
                     g["metrics"][metric]["count"] == plan["replicates"]]
        x = [g["requested"][control] for g in groups_ok]
        y = [g["metrics"][metric]["mean"] for g in groups_ok]
        rho = float(spearmanr(x, y).statistic) if len(y) >= 3 and np.ptp(y) > 0 else None
        variances = [g["metrics"][metric]["std"] ** 2 for g in groups_ok
                     if g["metrics"][metric]["std"] is not None]
        sensitivity[control] = {
            "measured_metric": metric, "complete_designs": len(groups_ok),
            "spearman_requested_vs_design_mean": rho,
            "between_design_mean_std": stats(y)["std"],
            "within_design_rms_std": float(np.sqrt(np.mean(variances))) if variances else None,
            "measured_span": float(np.ptp(y)) if y else None,
            "requested_span": float(np.ptp(x)) if x else None,
        }
    duplicates = [ids for ids in hashes.values() if len(ids) > 1]
    duplicate_ids = {sample_id for group in duplicates for sample_id in group}
    for record in records:
        record["duplicate_geometry"] = record["sample_id"] in duplicate_ids
    report = {"mode": "exploration", "pipeline_version": "0.3.0",
              "expected_count": len(records), "measured_count": sum(r["measured"] is not None for r in records),
              **{f"{k}_count": sum(r[k] for r in records) for k in
                 ("engineering_valid", "family_pass", "envelope_pass", "eligible")},
              "family_limits": plan["family_limits"], "bounds": plan["bounds"],
              "samples": records, "design_summary": groups, "control_diagnostics": sensitivity,
              "duplicate_groups": duplicates, "unique_geometry_count": len(hashes),
              "limitations": ["Spearman associations from a small multivariable design are not causal sensitivity estimates.",
                              "Large between-design variation alone does not demonstrate useful morphology control.",
                              "Common random seeds pair designs; within-design standard deviation uses ddof=1.",
                              "Curve gates are necessary numeric checks, not proof of recognizable morphology; inspect montage.",
                              "Bounds may be jointly infeasible. Requested values are controls, not guaranteed measurements.",
                              "No FEM, mechanical properties or strength predictions have been computed."]}
    write_json(attempt / "exploration_report.json", evaluator.json_safe(report))
    fields = ["sample_id", "design_id", "replicate", "seed"] + ["requested_" + k for k in CONTROLS]
    fields += list(METRICS) + ["E_S2", "E_L", "engineering_valid", "family_pass", "envelope_pass", "eligible", "duplicate_geometry", "npy_path", "sha256", "error"]
    with (attempt / "morphology_dataset.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for r in records:
            row = {k: r.get(k) for k in fields}
            row.update({"requested_" + k: v for k, v in r["requested"].items()})
            row.update({k: (r["measured"] or {}).get(k) for k in METRICS})
            row.update(r.get("curve_errors", {}))
            writer.writerow(row)
    lines = ["# Parametric exploration report", "",
             f"Measured: {report['measured_count']}/{len(records)}; connected and spanning: "
             f"{report['engineering_valid_count']}/{len(records)}; all numeric gates passed: "
             f"{report['eligible_count']}/{len(records)}.", "",
             f"Unique geometries: {len(hashes)}. Duplicate groups: {len(duplicates)}.", "",
             "| Control | Requested/measured Spearman | Between-design SD | Within-design RMS SD |",
             "|---|---:|---:|---:|"]
    for c, d in sensitivity.items():
        fmt = lambda v: "N/A" if v is None else f"{v:.5g}"
        lines.append(f"| {c} | {fmt(d['spearman_requested_vs_design_mean'])} | "
                     f"{fmt(d['between_design_mean_std'])} | {fmt(d['within_design_rms_std'])} |")
    lines += ["", "## Revision guidance", "",
              "Retain the same parameter interface and design plan when comparing revisions.",
              "Repair disconnected networks in the generator; never add islands to satisfy density.",
              "If a control has negligible measured span or weak/reversed association, inspect its implementation.",
              "Inspect failed designs and requested-versus-achieved columns, not only ensemble means.",
              "Reduce curve errors only enough to meet the stated family limits; do not collapse designs to the anchor.",
              "Inspect montage.png for recognizable morphology and unwanted artifacts.", "",
              *[f"- {line}" for line in report["limitations"]]]
    (attempt / "report.md").write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    plot_report(run, attempt, records, target)
    return report


def plot_report(run: Path, attempt: Path, records: list, target: dict) -> None:
    """Static QC: all geometries and requested-versus-achieved controls."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    columns = 5
    fig, axes = plt.subplots((len(records) + 1 + columns - 1) // columns, columns,
                             figsize=(12, 2.5 * ((len(records) + columns) // columns)), squeeze=False)
    for ax in axes.ravel():
        ax.axis("off")
    axes.flat[0].imshow(np.load(run / "reference/reference_binary.npy"), cmap="gray", vmin=0, vmax=1)
    axes.flat[0].set_title("Structural anchor")
    for ax, r in zip(list(axes.flat)[1:], records):
        if r["measured"] is not None:
            ax.imshow(np.load(run / r["npy_path"]), cmap="gray", vmin=0, vmax=1)
        label = "numeric gates pass" if r["eligible"] else "check / failed"
        if r["duplicate_geometry"]:
            label += "; duplicate"
        ax.set_title(r["sample_id"] + "\n" + label, fontsize=8)
    fig.tight_layout()
    fig.savefig(attempt / "montage.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (control, (metric, _)) in zip(axes, CONTROLS.items()):
        for r in records:
            if r["measured"] is not None and r["measured"][metric] is not None:
                ax.scatter(r["requested"][control], r["measured"][metric],
                           color="tab:blue" if r["engineering_valid"] else "tab:red", s=18)
        if target[metric] is not None:
            ax.axhline(target[metric], color="gray", linestyle=":", label="anchor")
        ax.set(xlabel=f"Requested {control}", ylabel=f"Measured {metric}")
    fig.suptitle("Achieved controls: blue = topology valid; red = invalid")
    fig.tight_layout()
    fig.savefig(attempt / "control_response.png", dpi=150)
    plt.close(fig)
