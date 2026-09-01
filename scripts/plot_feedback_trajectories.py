#!/usr/bin/env python3
"""Evaluate and plot Pilot v1.1 feedback trajectories.

The script compares I0F1, I1F1, and I2F1 over iterations 0 -> 1 -> 2 -> 3.
It plots ensemble metrics only; it does not create microstructure montages.

Examples
--------
Plot the existing finite-domain reports::

    python scripts/plot_feedback_trajectories.py

Reevaluate every ensemble before plotting::

    python scripts/plot_feedback_trajectories.py --evaluate

Plot statistics from topology-valid samples only::

    python scripts/plot_feedback_trajectories.py --population valid
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from metamaterial_eval import (
    evaluate_generator_output,
    load_binary,
    make_target_dict,
)


DEFAULT_TRAJECTORIES = ("I0F1", "I1F1", "I2F1")
BASELINE_LABEL = "I0F0 Run_1 baseline"
ITERATIONS = (0, 1, 2, 3)
COLORS = {
    "I0F1": "#0072B2",
    "I1F1": "#D55E00",
    "I2F1": "#009E73",
    BASELINE_LABEL: "#CC79A7",
}


@dataclass(frozen=True)
class MetricSpec:
    key: str
    title: str
    ylabel: str
    target_key: str | None = None
    ideal: float | None = None
    percent: bool = False


METRICS = (
    MetricSpec(
        "valid_fraction",
        "Topology-valid samples",
        "Valid samples (%)",
        ideal=1.0,
        percent=True,
    ),
    MetricSpec(
        "solid_volume_fraction",
        "Solid volume fraction",
        r"$\phi_s$",
        target_key="solid_volume_fraction",
    ),
    MetricSpec(
        "largest_component_fraction",
        "Largest-component fraction",
        r"$f_{\mathrm{largest}}$",
        target_key="largest_component_fraction",
    ),
    MetricSpec(
        "nrmse_s2",
        "Two-point correlation error",
        r"NRMSE $S_2(r)$",
        ideal=0.0,
    ),
    MetricSpec(
        "nrmse_lineal_path",
        "Lineal-path error",
        r"NRMSE $L(r)$",
        ideal=0.0,
    ),
    MetricSpec(
        "mean_strut_thickness",
        "Mean strut thickness",
        "Thickness (px)",
        target_key="mean_strut_thickness",
    ),
    MetricSpec(
        "p10_strut_thickness",
        "P10 strut thickness",
        "Thickness (px)",
        target_key="p10_strut_thickness",
    ),
    MetricSpec(
        "median_pore_diameter",
        "Median enclosed-pore diameter",
        "Diameter (px)",
        target_key="median_pore_diameter",
    ),
)


def _finite_report(run_dir: Path, iteration: int) -> Path:
    return run_dir / f"results_{iteration}" / "finite_domain" / "metrics_report.json"


def _sample_dir(run_dir: Path, iteration: int) -> Path:
    return run_dir / f"generated_microstructures_{iteration}"


def evaluate_reports(
    pilot_root: Path,
    target_path: Path,
    trajectories: Sequence[str],
    run_name: str,
    max_r: int,
    expected_count: int,
    baseline_run: Path | None,
) -> None:
    """Reevaluate every requested trajectory/iteration in-place."""
    target = load_binary(target_path, expected_shape=(256, 256))
    target_dict = make_target_dict(target, max_r=max_r)

    for trajectory in trajectories:
        run_dir = pilot_root / trajectory / run_name
        for iteration in ITERATIONS:
            samples = _sample_dir(run_dir, iteration)
            if not samples.is_dir():
                raise FileNotFoundError(f"Missing sample directory: {samples}")
            npy_count = len(list(samples.glob("*.npy")))
            if expected_count > 0 and npy_count != expected_count:
                raise ValueError(
                    f"{trajectory} iteration {iteration}: expected "
                    f"{expected_count} NPY samples, found {npy_count}."
                )
            output_dir = _finite_report(run_dir, iteration).parent
            report = evaluate_generator_output(
                target_dict,
                samples,
                output_dir=output_dir,
            )
            print(
                f"Evaluated {trajectory} iteration {iteration}: "
                f"{report['evaluated_sample_count']} samples, "
                f"{report['valid_sample_count']} valid."
            )

    if baseline_run is not None:
        samples = baseline_run / "generated_microstructures"
        if not samples.is_dir():
            raise FileNotFoundError(f"Missing baseline sample directory: {samples}")
        npy_count = len(list(samples.glob("*.npy")))
        if expected_count > 0 and npy_count != expected_count:
            raise ValueError(
                f"I0F0 Run_1: expected {expected_count} NPY samples, "
                f"found {npy_count}."
            )
        output_dir = baseline_run / "results" / "finite_domain"
        report = evaluate_generator_output(
            target_dict,
            samples,
            output_dir=output_dir,
        )
        print(
            f"Evaluated {BASELINE_LABEL}: "
            f"{report['evaluated_sample_count']} samples, "
            f"{report['valid_sample_count']} valid."
        )


def load_trajectory_records(
    pilot_root: Path,
    trajectories: Sequence[str],
    run_name: str,
    population: str,
    baseline_run: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, float]]:
    """Load the 12 reports into one tidy list and verify target consistency."""
    aggregate_key = (
        "aggregate_all_samples"
        if population == "all"
        else "aggregate_valid_samples"
    )
    records: list[dict[str, Any]] = []
    target_values: dict[str, float] | None = None

    def append_report(label: str, iteration: int, report_path: Path) -> None:
        nonlocal target_values
        if not report_path.is_file():
            raise FileNotFoundError(
                f"Missing report: {report_path}. Run again with --evaluate."
            )
        with report_path.open(encoding="utf-8") as stream:
            report = json.load(stream)

        current_target = {
            key: float(report["target"][key])
            for key in (
                "solid_volume_fraction",
                "largest_component_fraction",
                "mean_strut_thickness",
                "p10_strut_thickness",
                "median_pore_diameter",
            )
        }
        if target_values is None:
            target_values = current_target
        elif any(
            not np.isclose(current_target[key], target_values[key])
            for key in target_values
        ):
            raise ValueError(f"Target metrics differ in {report_path}.")

        aggregate = report[aggregate_key]
        sample_count = int(report["evaluated_sample_count"])
        valid_count = int(report["valid_sample_count"])
        record: dict[str, Any] = {
            "trajectory": label,
            "iteration": iteration,
            "sample_count": sample_count,
            "valid_sample_count": valid_count,
            "valid_fraction": valid_count / sample_count if sample_count else np.nan,
            "valid_fraction_std": 0.0,
            "report": str(report_path),
        }
        for spec in METRICS:
            if spec.key == "valid_fraction":
                continue
            summary = aggregate[spec.key]
            mean = summary["mean"]
            std = summary["std"]
            record[spec.key] = np.nan if mean is None else float(mean)
            record[f"{spec.key}_std"] = np.nan if std is None else float(std)
            record[f"{spec.key}_count"] = int(summary["count"])
        records.append(record)

    if baseline_run is not None:
        append_report(
            BASELINE_LABEL,
            0,
            baseline_run / "results" / "finite_domain" / "metrics_report.json",
        )

    for trajectory in trajectories:
        run_dir = pilot_root / trajectory / run_name
        for iteration in ITERATIONS:
            append_report(trajectory, iteration, _finite_report(run_dir, iteration))

    assert target_values is not None
    return records, target_values


def _trajectory_rows(
    records: Sequence[dict[str, Any]], trajectory: str
) -> list[dict[str, Any]]:
    return sorted(
        (row for row in records if row["trajectory"] == trajectory),
        key=lambda row: row["iteration"],
    )


def _plot_metric(
    axis: plt.Axes,
    records: Sequence[dict[str, Any]],
    trajectories: Sequence[str],
    spec: MetricSpec,
    target_values: dict[str, float],
) -> None:
    for trajectory in trajectories:
        rows = _trajectory_rows(records, trajectory)
        x = np.asarray([row["iteration"] for row in rows], dtype=float)
        y = np.asarray([row[spec.key] for row in rows], dtype=float)
        std = np.asarray([row[f"{spec.key}_std"] for row in rows], dtype=float)
        if spec.percent:
            y = 100.0 * y
            std = 100.0 * std
        axis.errorbar(
            x,
            y,
            yerr=std,
            marker="D" if trajectory == BASELINE_LABEL else "o",
            markersize=6 if trajectory == BASELINE_LABEL else 5,
            linewidth=0 if trajectory == BASELINE_LABEL else 2,
            capsize=3,
            label=trajectory,
            color=COLORS.get(trajectory),
        )

    reference = None
    reference_label = None
    if spec.target_key is not None:
        reference = target_values[spec.target_key]
        reference_label = "Reference"
    elif spec.ideal is not None:
        reference = spec.ideal * (100.0 if spec.percent else 1.0)
        reference_label = "Reference"
    if reference is not None:
        axis.axhline(
            reference,
            color="black",
            linestyle="--",
            linewidth=1.25,
            alpha=0.65,
            label=reference_label,
        )

    axis.set_title(spec.title)
    axis.set_ylabel(spec.ylabel)
    axis.set_xticks(ITERATIONS)
    axis.set_xlabel("Feedback iteration")
    axis.grid(True, alpha=0.25)


def create_figure(
    records: Sequence[dict[str, Any]],
    trajectories: Sequence[str],
    target_values: dict[str, float],
    title: str,
    output_path: Path,
) -> None:
    """Create an eight-panel trajectory figure."""
    figure, axes = plt.subplots(4, 2, figsize=(13, 16))
    for axis, spec in zip(axes.ravel(), METRICS):
        _plot_metric(axis, records, trajectories, spec, target_values)

    handles, labels = axes.ravel()[0].get_legend_handles_labels()
    unique = dict(zip(labels, handles))
    figure.legend(
        unique.values(),
        unique.keys(),
        loc="upper center",
        bbox_to_anchor=(0.5, 0.985),
        ncol=len(unique),
        frameon=False,
    )
    figure.suptitle(title, fontsize=16, fontweight="bold", y=0.955)
    figure.tight_layout(rect=(0.0, 0.0, 1.0, 0.925))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)


def write_csv(records: Sequence[dict[str, Any]], output_path: Path) -> None:
    """Write a tidy machine-readable trajectory table."""
    fields = [
        "trajectory",
        "iteration",
        "sample_count",
        "valid_sample_count",
        "valid_fraction",
    ]
    for spec in METRICS:
        if spec.key != "valid_fraction":
            fields.extend((spec.key, f"{spec.key}_std", f"{spec.key}_count"))
    fields.append("report")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate and plot I0F1, I1F1, and I2F1 over feedback "
            "iterations 0 through 3. No microstructure montage is generated."
        )
    )
    parser.add_argument(
        "--pilot-root",
        type=Path,
        default=Path("experiments/Pilot_v1.1"),
        help="Pilot experiment root (default: experiments/Pilot_v1.1)",
    )
    parser.add_argument(
        "--trajectories",
        nargs="+",
        default=list(DEFAULT_TRAJECTORIES),
        help="feedback conditions to plot (default: I0F1 I1F1 I2F1)",
    )
    parser.add_argument("--run", default="Run_1", help="run directory name")
    parser.add_argument(
        "--baseline-run",
        type=Path,
        default=Path("experiments/Pilot_v1.1/I0F0/Run_1"),
        help="successful no-feedback baseline (default: I0F0/Run_1)",
    )
    parser.add_argument(
        "--no-baseline",
        action="store_true",
        help="omit the I0F0 Run_1 baseline marker",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("data/reference/reference_binary.npy"),
        help="target NPY used when --evaluate is supplied",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/Pilot_v1.1/feedback_trajectories"),
        help="directory for plots and CSV",
    )
    parser.add_argument(
        "--population",
        choices=("all", "valid"),
        default="all",
        help=(
            "ensemble population for plotted means (default: all; required "
            "to retain I0F1 iteration 0, which has no valid samples)"
        ),
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="reevaluate all 12 sample folders before plotting",
    )
    parser.add_argument("--max-r", type=int, default=64)
    parser.add_argument("--expected-count", type=int, default=20)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    baseline_run = None if args.no_baseline else args.baseline_run
    if args.evaluate:
        evaluate_reports(
            args.pilot_root,
            args.target,
            args.trajectories,
            args.run,
            args.max_r,
            args.expected_count,
            baseline_run,
        )

    records, target_values = load_trajectory_records(
        args.pilot_root,
        args.trajectories,
        args.run,
        args.population,
        baseline_run,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)

    plotted_series = list(args.trajectories)
    if baseline_run is not None:
        plotted_series.append(BASELINE_LABEL)

    combined_path = args.output_dir / f"feedback_trajectories_{args.population}.png"
    create_figure(
        records,
        plotted_series,
        target_values,
        "Pilot v1.1 Feedback Trajectories: Iteration 0 → 1 → 2 → 3",
        combined_path,
    )
    for trajectory in args.trajectories:
        individual_series = [trajectory]
        if baseline_run is not None:
            individual_series.append(BASELINE_LABEL)
        create_figure(
            records,
            individual_series,
            target_values,
            f"Pilot v1.1 {trajectory}: Iteration 0 → 1 → 2 → 3",
            args.output_dir / f"{trajectory}_trajectory_{args.population}.png",
        )

    csv_path = args.output_dir / f"feedback_trajectories_{args.population}.csv"
    write_csv(records, csv_path)
    print(f"Combined plot: {combined_path}")
    print(f"Individual plots: {args.output_dir}/<trajectory>_trajectory_{args.population}.png")
    print(f"Trajectory table: {csv_path}")


if __name__ == "__main__":
    main()
