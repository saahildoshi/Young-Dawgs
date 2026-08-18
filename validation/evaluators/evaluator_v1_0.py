#!/usr/bin/env python3
"""Validate and evaluate an ensemble of generated binary microstructures.

The statistical descriptors in this script use periodic boundary conditions.
Consequently, S2 and the four-direction lineal-path estimator are invariant to
integer translations made with ``numpy.roll``. Connectivity/percolation and
Euclidean distance-transform measurements use the ordinary finite image.

Example
-------
python scripts/evaluate_and_plot.py \
    experiments/pilot_voronoi/generated_microstructures \
    --target data/reference/reference_binary.npy \
    --output-dir experiments/pilot_voronoi/evaluation_results
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage
from skimage.metrics import structural_similarity


FOUR_CONNECTED = np.array(
    [[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8
)


def natural_key(path: Path) -> list[str | int]:
    """Sort paths naturally (sample_2 before sample_10)."""
    return [
        int(token) if token.isdigit() else token.casefold()
        for token in re.split(r"(\d+)", path.name)
    ]


def load_binary(path: Path, expected_shape: tuple[int, int] | None = None) -> np.ndarray:
    """Load a 2-D binary NPY array and canonicalize it to contiguous uint8 0/1."""
    if not path.is_file():
        raise FileNotFoundError(f"Binary array not found: {path}")
    array = np.load(path, allow_pickle=False)
    if array.ndim != 2:
        raise ValueError(f"{path}: expected a 2-D array, received {array.shape}")
    if expected_shape is not None and tuple(array.shape) != tuple(expected_shape):
        raise ValueError(
            f"{path}: expected shape {expected_shape}, received {array.shape}"
        )
    if array.size == 0:
        raise ValueError(f"{path}: array is empty")
    unique = np.unique(array)
    if not (
        np.all(np.isin(unique, (0, 1)))
        or np.all(np.isin(unique, (0, 255)))
    ):
        raise ValueError(
            f"{path}: expected binary values {{0,1}} or {{0,255}}, "
            f"found {unique[:10].tolist()}"
        )
    return np.ascontiguousarray(array != 0, dtype=np.uint8)


def find_samples(directory: Path) -> list[Path]:
    """Return naturally sorted NPY samples directly within a directory."""
    if not directory.is_dir():
        raise NotADirectoryError(f"Sample directory not found: {directory}")
    return sorted(
        (path for path in directory.iterdir() if path.is_file() and path.suffix.lower() == ".npy"),
        key=natural_key,
    )


def basic_metrics(binary: np.ndarray) -> dict[str, float | int]:
    """Compute solid fraction, finite-domain connectivity, and percolation."""
    solid = binary.astype(bool)
    solid_pixels = int(solid.sum())
    labels, component_count = ndimage.label(solid, structure=FOUR_CONNECTED)

    if component_count == 0:
        largest_pixels = 0
        largest_fraction = 0.0
        percolates_x = 0
        percolates_y = 0
    else:
        counts = np.bincount(labels.ravel())
        counts[0] = 0
        largest_pixels = int(counts.max())
        largest_fraction = largest_pixels / solid_pixels
        percolates_x = int(
            bool(
                (set(np.unique(labels[:, 0])) - {0})
                & (set(np.unique(labels[:, -1])) - {0})
            )
        )
        percolates_y = int(
            bool(
                (set(np.unique(labels[0, :])) - {0})
                & (set(np.unique(labels[-1, :])) - {0})
            )
        )

    return {
        "phi_s": float(solid.mean()),
        "f_largest": float(largest_fraction),
        "Px": percolates_x,
        "Py": percolates_y,
        "component_count": int(component_count),
        "solid_pixels": solid_pixels,
        "largest_component_pixels": largest_pixels,
    }


def local_dimensions(binary: np.ndarray) -> dict[str, Any]:
    """Compute pixel-weighted EDT diameter samples for solid and void phases."""
    solid = binary.astype(bool)
    void = ~solid
    if solid.any() and void.any():
        strut_diameters = 2.0 * ndimage.distance_transform_edt(solid)[solid]
        pore_diameters = 2.0 * ndimage.distance_transform_edt(void)[void]
    else:
        strut_diameters = np.empty(0, dtype=np.float64)
        pore_diameters = np.empty(0, dtype=np.float64)

    def summary(samples: np.ndarray, statistic: str) -> float:
        if not samples.size:
            return float("nan")
        if statistic == "mean":
            return float(np.mean(samples))
        if statistic == "p10":
            return float(np.percentile(samples, 10))
        return float(np.median(samples))

    return {
        "mean_strut_thickness": summary(strut_diameters, "mean"),
        "p10_strut_thickness": summary(strut_diameters, "p10"),
        "median_pore_diameter": summary(pore_diameters, "median"),
        "strut_diameters": strut_diameters,
        "pore_diameters": pore_diameters,
    }


def radial_bin_map(shape: tuple[int, int], max_r: int) -> tuple[np.ndarray, np.ndarray]:
    """Return minimum-image integer radial bins and their populations."""
    height, width = shape
    dy = np.minimum(np.arange(height), height - np.arange(height))
    dx = np.minimum(np.arange(width), width - np.arange(width))
    bins = np.rint(np.hypot(dy[:, None], dx[None, :])).astype(np.int32)
    counts = np.bincount(
        bins[bins <= max_r].ravel(), minlength=max_r + 1
    ).astype(np.float64)
    return bins, counts


def s2_periodic(
    binary: np.ndarray,
    max_r: int,
    bins: np.ndarray,
    bin_counts: np.ndarray,
) -> np.ndarray:
    """Periodic FFT two-point probability, radially averaged by integer radius."""
    values = binary.astype(np.float64, copy=False)
    spectrum = np.fft.fft2(values)
    autocorrelation = np.fft.ifft2(spectrum * spectrum.conj()).real / values.size
    include = bins <= max_r
    sums = np.bincount(
        bins[include].ravel(),
        weights=autocorrelation[include].ravel(),
        minlength=max_r + 1,
    )
    curve = np.divide(
        sums,
        bin_counts,
        out=np.full(max_r + 1, np.nan, dtype=np.float64),
        where=bin_counts > 0,
    )
    curve[0] = float(values.mean())
    return curve


def lineal_path_periodic(binary: np.ndarray, max_r: int) -> np.ndarray:
    """Periodic four-direction lineal-path probability for separations 0..max_r.

    The directions are horizontal, vertical, and the two 45-degree diagonals.
    A segment at separation r contains r+1 digital pixels.
    """
    solid = binary.astype(bool)
    directions = ((0, 1), (1, 0), (1, 1), (1, -1))
    directional = np.empty((len(directions), max_r + 1), dtype=np.float64)
    for index, (dy, dx) in enumerate(directions):
        running = solid.copy()
        directional[index, 0] = running.mean()
        for radius in range(1, max_r + 1):
            running &= np.roll(solid, shift=(-radius * dy, -radius * dx), axis=(0, 1))
            directional[index, radius] = running.mean()
    return directional.mean(axis=0)


def normalized_rmse(sample: np.ndarray, target: np.ndarray) -> float:
    """RMSE normalized by the RMS magnitude of the target curve."""
    sample = np.asarray(sample, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    finite = np.isfinite(sample) & np.isfinite(target)
    if not finite.any():
        return float("nan")
    numerator = float(np.sqrt(np.mean(np.square(sample[finite] - target[finite]))))
    denominator = float(np.sqrt(np.mean(np.square(target[finite]))))
    if denominator <= np.finfo(float).eps:
        return 0.0 if numerator <= np.finfo(float).eps else float("inf")
    return numerator / denominator


def ncc(first: np.ndarray, second: np.ndarray) -> float:
    """Zero-mean normalized cross-correlation at zero spatial lag."""
    a = first.astype(np.float64).ravel()
    b = second.astype(np.float64).ravel()
    a -= a.mean()
    b -= b.mean()
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator <= np.finfo(float).eps:
        return 1.0 if np.array_equal(first, second) else 0.0
    return float(np.dot(a, b) / denominator)


def similarity_metrics(sample: np.ndarray, target: np.ndarray) -> tuple[float, float]:
    """Return aligned SSIM and NCC for target-leakage screening."""
    ssim = float(
        structural_similarity(
            target.astype(np.float64),
            sample.astype(np.float64),
            data_range=1.0,
        )
    )
    return ssim, ncc(sample, target)


def evaluate_structure(
    binary: np.ndarray,
    target_s2: np.ndarray,
    target_lineal: np.ndarray,
    target: np.ndarray,
    max_r: int,
    bins: np.ndarray,
    bin_counts: np.ndarray,
) -> tuple[dict[str, Any], np.ndarray]:
    """Evaluate one structure and return its metrics plus pore samples."""
    basic = basic_metrics(binary)
    local = local_dimensions(binary)
    s2 = s2_periodic(binary, max_r, bins, bin_counts)
    lineal = lineal_path_periodic(binary, max_r)
    ssim, correlation = similarity_metrics(binary, target)
    record = {
        **basic,
        "mean_strut_thickness": local["mean_strut_thickness"],
        "p10_strut_thickness": local["p10_strut_thickness"],
        "median_pore_diameter": local["median_pore_diameter"],
        "E_S2": normalized_rmse(s2, target_s2),
        "E_L": normalized_rmse(lineal, target_lineal),
        "SSIM": ssim,
        "NCC": correlation,
        "potential_trivial_copy": bool(ssim > 0.85),
        "S2": s2,
        "L": lineal,
    }
    return record, local["pore_diameters"]


def pairwise_disagreement(samples: np.ndarray) -> tuple[np.ndarray, float]:
    """Compute the full D_ij matrix and its strict-upper-triangle mean."""
    count, height, width = samples.shape
    flattened = samples.reshape(count, height * width).astype(np.int64)
    solid_counts = flattened.sum(axis=1)
    intersections = flattened @ flattened.T
    matrix = (
        solid_counts[:, None] + solid_counts[None, :] - 2 * intersections
    ).astype(np.float64) / flattened.shape[1]
    np.fill_diagonal(matrix, 0.0)
    diversity = (
        float(matrix[np.triu_indices(count, k=1)].mean())
        if count > 1
        else 0.0
    )
    return matrix, diversity


def make_matched_bernoulli(target: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Randomly place exactly the target's number of solid pixels."""
    noise = np.zeros(target.size, dtype=np.uint8)
    solid_count = int(target.sum())
    noise[rng.choice(target.size, size=solid_count, replace=False)] = 1
    return noise.reshape(target.shape)


def run_sanity_checks(
    target: np.ndarray,
    target_s2: np.ndarray,
    target_lineal: np.ndarray,
    max_r: int,
    bins: np.ndarray,
    bin_counts: np.ndarray,
    rng: np.random.Generator,
) -> dict[str, Any]:
    """Exercise the metric engine against copy, translation, and noise controls."""
    copy_s2 = s2_periodic(target, max_r, bins, bin_counts)
    copy_lineal = lineal_path_periodic(target, max_r)
    copy_ssim, _ = similarity_metrics(target, target)
    copy_result = {
        "E_S2": normalized_rmse(copy_s2, target_s2),
        "E_L": normalized_rmse(copy_lineal, target_lineal),
        "target_copy_similarity": copy_ssim,
    }
    copy_result["passed"] = bool(
        copy_result["E_S2"] <= 1e-12
        and copy_result["E_L"] <= 1e-12
        and abs(copy_result["target_copy_similarity"] - 1.0) <= 1e-12
    )

    shift = (17 % target.shape[0], 29 % target.shape[1])
    translated = np.roll(target, shift=shift, axis=(0, 1))
    translated_s2 = s2_periodic(translated, max_r, bins, bin_counts)
    translated_lineal = lineal_path_periodic(translated, max_r)
    translated_ssim, translated_ncc = similarity_metrics(translated, target)
    translation_result = {
        "shift_pixels": list(shift),
        "E_S2": normalized_rmse(translated_s2, target_s2),
        "E_L": normalized_rmse(translated_lineal, target_lineal),
        "aligned_SSIM": translated_ssim,
        "aligned_NCC": translated_ncc,
    }
    translation_result["periodic_invariance_passed"] = bool(
        translation_result["E_S2"] <= 1e-12
        and translation_result["E_L"] <= 1e-12
    )

    noise = make_matched_bernoulli(target, rng)
    noise_basic = basic_metrics(noise)
    noise_s2 = s2_periodic(noise, max_r, bins, bin_counts)
    noise_lineal = lineal_path_periodic(noise, max_r)
    noise_result = {
        "phi_s": noise_basic["phi_s"],
        "target_phi_s": float(target.mean()),
        "f_largest": noise_basic["f_largest"],
        "Px": noise_basic["Px"],
        "Py": noise_basic["Py"],
        "E_S2": normalized_rmse(noise_s2, target_s2),
        "E_L": normalized_rmse(noise_lineal, target_lineal),
    }
    noise_result["matched_phi_passed"] = bool(
        abs(noise_result["phi_s"] - noise_result["target_phi_s"]) <= 1e-12
    )
    noise_result["connectivity_failed_as_expected"] = bool(
        noise_result["f_largest"] < 0.98
    )
    # These thresholds catch a descriptor accidentally returning the target
    # while remaining scale-agnostic enough for a broad range of targets.
    noise_result["high_descriptor_errors"] = bool(
        noise_result["E_S2"] > 0.05 and noise_result["E_L"] > 0.05
    )
    noise_result["passed"] = bool(
        noise_result["matched_phi_passed"]
        and noise_result["connectivity_failed_as_expected"]
        and noise_result["high_descriptor_errors"]
    )

    return {
        "target_vs_target": copy_result,
        "target_vs_periodic_translation": translation_result,
        "matched_bernoulli_noise": noise_result,
        "all_required_checks_passed": bool(
            copy_result["passed"]
            and translation_result["periodic_invariance_passed"]
            and noise_result["passed"]
        ),
    }


def metric_summary(records: Sequence[dict[str, Any]], key: str) -> dict[str, float]:
    """Return mean, sample standard deviation, minimum, and maximum."""
    values = np.asarray([record[key] for record in records], dtype=np.float64)
    finite = values[np.isfinite(values)]
    if not finite.size:
        return {name: float("nan") for name in ("mean", "std", "min", "max")}
    return {
        "mean": float(finite.mean()),
        "std": float(finite.std(ddof=1)) if finite.size > 1 else 0.0,
        "min": float(finite.min()),
        "max": float(finite.max()),
    }


def pore_histogram(samples: np.ndarray, edges: np.ndarray) -> dict[str, np.ndarray]:
    """Return probability mass and density on shared pore-diameter bins."""
    finite = samples[np.isfinite(samples)]
    if not finite.size:
        probability = np.zeros(edges.size - 1, dtype=np.float64)
    else:
        counts, _ = np.histogram(finite, bins=edges)
        probability = counts.astype(np.float64) / counts.sum()
    return {
        "probability_mass": probability,
        "probability_density": np.divide(
            probability,
            np.diff(edges),
            out=np.zeros_like(probability),
            where=np.diff(edges) > 0,
        ),
    }


def plot_montage(
    target: np.ndarray,
    samples: np.ndarray,
    records: Sequence[dict[str, Any]],
    names: Sequence[str],
    figures_dir: Path,
    rng: np.random.Generator,
) -> None:
    count = len(records)
    random_indices = rng.choice(count, size=4, replace=False)
    best_s2 = int(np.argmin([record["E_S2"] for record in records]))
    worst_s2 = int(np.argmax([record["E_S2"] for record in records]))
    worst_l = int(np.argmax([record["E_L"] for record in records]))
    panels: list[tuple[np.ndarray, str]] = [(target, "Target")]
    panels.extend(
        (samples[index], f"Random: {names[index]}") for index in random_indices
    )
    panels.extend(
        [
            (samples[best_s2], f"Best S2: {names[best_s2]}"),
            (samples[worst_s2], f"Worst S2: {names[worst_s2]}"),
            (samples[worst_l], f"Worst L: {names[worst_l]}"),
        ]
    )
    figure, axes = plt.subplots(2, 4, figsize=(13, 7), constrained_layout=True)
    for axis, (image, title) in zip(axes.ravel(), panels):
        axis.imshow(image, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
        axis.set_title(title, fontsize=9)
        axis.axis("off")
    figure.suptitle("Target and generated microstructure diagnostics", fontsize=14)
    figure.savefig(figures_dir / "fig1_montage.png", dpi=220)
    plt.close(figure)


def plot_curve_ensemble(
    radius: np.ndarray,
    target_curve: np.ndarray,
    generated_curves: np.ndarray,
    ylabel: str,
    title: str,
    path: Path,
) -> None:
    mean = generated_curves.mean(axis=0)
    std = generated_curves.std(axis=0, ddof=1) if len(generated_curves) > 1 else np.zeros_like(mean)
    figure, axis = plt.subplots(figsize=(7.5, 5.2), constrained_layout=True)
    axis.plot(radius, target_curve, color="black", linewidth=2.2, label="Target")
    axis.plot(radius, mean, color="#c44e52", linewidth=2.0, label="Generated mean")
    axis.fill_between(
        radius,
        np.clip(mean - std, 0.0, 1.0),
        np.clip(mean + std, 0.0, 1.0),
        color="#c44e52",
        alpha=0.25,
        label="Generated ±1 SD",
    )
    axis.set(xlabel="Separation r (pixels)", ylabel=ylabel, title=title)
    axis.grid(alpha=0.25)
    axis.legend(frameon=False)
    figure.savefig(path, dpi=220)
    plt.close(figure)


def plot_pore_distribution(
    target_pores: np.ndarray,
    generated_pores: np.ndarray,
    edges: np.ndarray,
    figures_dir: Path,
) -> None:
    centers = (edges[:-1] + edges[1:]) / 2.0
    target_density = pore_histogram(target_pores, edges)["probability_density"]
    generated_density = pore_histogram(generated_pores, edges)["probability_density"]
    target_median = float(np.median(target_pores)) if target_pores.size else float("nan")
    generated_median = (
        float(np.median(generated_pores)) if generated_pores.size else float("nan")
    )

    figure, axis = plt.subplots(figsize=(7.5, 5.2), constrained_layout=True)
    axis.step(
        centers,
        target_density,
        where="mid",
        color="black",
        linewidth=2.0,
        label=f"Target (median {target_median:.2f} px)",
    )
    axis.step(
        centers,
        generated_density,
        where="mid",
        color="#4c72b0",
        linewidth=2.0,
        label=f"Generated (median {generated_median:.2f} px)",
    )
    if math.isfinite(target_median):
        axis.axvline(target_median, color="black", linestyle="--", alpha=0.7)
    if math.isfinite(generated_median):
        axis.axvline(generated_median, color="#4c72b0", linestyle="--", alpha=0.7)
    axis.set(
        xlabel="EDT pore diameter (pixels)",
        ylabel="Probability density",
        title="Pore-size distribution (pixel-weighted EDT diameters)",
        xlim=(float(edges[0]), float(edges[-1])),
    )
    axis.grid(alpha=0.2)
    axis.legend(frameon=False)
    figure.savefig(figures_dir / "fig4_pore_distribution.png", dpi=220)
    plt.close(figure)


def plot_diversity_heatmap(
    disagreement: np.ndarray,
    names: Sequence[str],
    figures_dir: Path,
) -> None:
    count = len(names)
    figure, axis = plt.subplots(figsize=(8.4, 7.2), constrained_layout=True)
    image = axis.imshow(
        disagreement,
        cmap="viridis",
        vmin=0.0,
        vmax=max(0.05, float(disagreement.max())),
        interpolation="nearest",
    )
    labels = [Path(name).stem for name in names]
    axis.set_xticks(np.arange(count), labels=labels, rotation=90, fontsize=7)
    axis.set_yticks(np.arange(count), labels=labels, fontsize=7)
    axis.set_title("Pairwise pixel disagreement $D_{ij}$")
    colorbar = figure.colorbar(image, ax=axis, shrink=0.86)
    colorbar.set_label("Fraction of disagreeing pixels")
    figure.savefig(figures_dir / "fig5_diversity_heatmap.png", dpi=220)
    plt.close(figure)


def json_safe(value: Any) -> Any:
    """Recursively convert NumPy objects and non-finite numbers for strict JSON."""
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def format_float(value: Any, width: int = 8, precision: int = 4) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:{width}.{precision}f}" if math.isfinite(number) else f"{'nan':>{width}}"


def print_report(report: dict[str, Any]) -> None:
    """Print sanity, per-sample, and ensemble summary tables."""
    sanity = report["sanity_checks"]
    copy = sanity["target_vs_target"]
    shifted = sanity["target_vs_periodic_translation"]
    noise = sanity["matched_bernoulli_noise"]
    print("\nEVALUATOR SANITY CHECKS")
    print("case                       E_S2       E_L      f_largest  result")
    print(
        f"target vs target        {copy['E_S2']:9.3g} {copy['E_L']:9.3g}"
        f" {'--':>14}  {'PASS' if copy['passed'] else 'FAIL'}"
    )
    print(
        f"periodic translation    {shifted['E_S2']:9.3g} {shifted['E_L']:9.3g}"
        f" {'--':>14}  {'PASS' if shifted['periodic_invariance_passed'] else 'FAIL'}"
    )
    print(
        f"matched Bernoulli       {noise['E_S2']:9.3g} {noise['E_L']:9.3g}"
        f" {noise['f_largest']:14.4f}  {'PASS' if noise['passed'] else 'FAIL'}"
    )

    target = report["target"]
    print("\nTARGET METRICS")
    print(
        "phi_s     f_largest  Px  Py  mean_strut  p10_strut  median_pore"
    )
    print(
        f"{target['phi_s']:8.4f} {target['f_largest']:10.4f}"
        f" {target['Px']:3d} {target['Py']:3d}"
        f" {target['mean_strut_thickness']:11.4f}"
        f" {target['p10_strut_thickness']:10.4f}"
        f" {target['median_pore_diameter']:12.4f}"
    )

    print("\nGENERATED SAMPLE METRICS")
    print(
        "sample                    phi_s   f_largest Px Py"
        "   strut_mu strut_p10 pore_med     E_S2       E_L"
        "     SSIM      NCC copy?"
    )
    for record in report["samples"]:
        print(
            f"{record['file'][:24]:24}"
            f" {record['phi_s']:7.4f} {record['f_largest']:9.4f}"
            f" {record['Px']:2d} {record['Py']:2d}"
            f" {record['mean_strut_thickness']:10.4f}"
            f" {record['p10_strut_thickness']:9.4f}"
            f" {record['median_pore_diameter']:8.4f}"
            f" {record['E_S2']:9.4f} {record['E_L']:9.4f}"
            f" {record['SSIM']:8.4f} {record['NCC']:8.4f}"
            f" {'YES' if record['potential_trivial_copy'] else 'no':>5}"
        )

    diversity = report["diversity"]
    print("\nENSEMBLE SUMMARY")
    print(f"Samples evaluated: {report['sample_count']}")
    print(
        f"D_pair: {diversity['D_pair']:.6f} -> "
        f"{'HEALTHY' if diversity['healthy'] else 'COLLAPSED'} "
        f"(criterion: D_pair > {diversity['threshold']:.2f})"
    )
    print(
        "Potential trivial copies (SSIM > 0.85): "
        + (
            ", ".join(report["novelty"]["flagged_files"])
            if report["novelty"]["flagged_files"]
            else "none"
        )
    )
    print("metric                    mean        std        min        max")
    for key, summary in report["ensemble_summary"].items():
        print(
            f"{key:24}"
            f" {format_float(summary['mean'], 10, 5)}"
            f" {format_float(summary['std'], 10, 5)}"
            f" {format_float(summary['min'], 10, 5)}"
            f" {format_float(summary['max'], 10, 5)}"
        )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and evaluate generated 256x256 binary microstructures."
    )
    parser.add_argument(
        "samples_dir",
        nargs="?",
        type=Path,
        default=Path("experiments/pilot_voronoi/generated_microstructures"),
        help=(
            "directory containing generated .npy arrays "
            "(default: experiments/pilot_voronoi/generated_microstructures)"
        ),
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("data/reference/reference_binary.npy"),
        help=(
            "target binary .npy file "
            "(default: data/reference/reference_binary.npy)"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/pilot_voronoi/evaluation_results"),
        help=(
            "directory for JSON and figures "
            "(default: experiments/pilot_voronoi/evaluation_results)"
        ),
    )
    parser.add_argument(
        "--max-r",
        type=int,
        default=64,
        help="maximum S2 and lineal-path separation in pixels (default: 64)",
    )
    parser.add_argument(
        "--expected-count",
        type=int,
        default=20,
        help="required number of generated samples; use 0 to allow any positive count",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=2026,
        help="random seed for controls and montage selection (default: 2026)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        target = load_binary(args.target, expected_shape=(256, 256))
        if args.max_r < 0 or args.max_r >= min(target.shape) // 2:
            raise ValueError(
                f"--max-r must be in [0, {min(target.shape) // 2 - 1}] "
                "for unambiguous minimum-image radial bins"
            )
        sample_paths = find_samples(args.samples_dir)
        if not sample_paths:
            raise ValueError(f"No .npy samples found in {args.samples_dir}")
        if args.expected_count > 0 and len(sample_paths) != args.expected_count:
            raise ValueError(
                f"Expected {args.expected_count} samples, found {len(sample_paths)} "
                f"in {args.samples_dir}"
            )
        if len(sample_paths) < 4:
            raise ValueError("At least four samples are required for the montage")
        samples = np.stack(
            [load_binary(path, expected_shape=target.shape) for path in sample_paths]
        )

        figures_dir = args.output_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        control_rng = np.random.default_rng(args.seed)
        montage_rng = np.random.default_rng(args.seed + 1)

        bins, bin_counts = radial_bin_map(target.shape, args.max_r)
        radius = np.arange(args.max_r + 1)
        target_basic = basic_metrics(target)
        target_local = local_dimensions(target)
        target_s2 = s2_periodic(target, args.max_r, bins, bin_counts)
        target_lineal = lineal_path_periodic(target, args.max_r)
        target_record = {
            **target_basic,
            "mean_strut_thickness": target_local["mean_strut_thickness"],
            "p10_strut_thickness": target_local["p10_strut_thickness"],
            "median_pore_diameter": target_local["median_pore_diameter"],
            "S2": target_s2,
            "L": target_lineal,
        }

        sanity = run_sanity_checks(
            target,
            target_s2,
            target_lineal,
            args.max_r,
            bins,
            bin_counts,
            control_rng,
        )

        records: list[dict[str, Any]] = []
        generated_pores: list[np.ndarray] = []
        for path, sample in zip(sample_paths, samples):
            record, pore_samples = evaluate_structure(
                sample,
                target_s2,
                target_lineal,
                target,
                args.max_r,
                bins,
                bin_counts,
            )
            record["file"] = path.name
            records.append(record)
            generated_pores.append(pore_samples)

        disagreement, diversity = pairwise_disagreement(samples)
        generated_s2 = np.stack([record["S2"] for record in records])
        generated_lineal = np.stack([record["L"] for record in records])
        all_generated_pores = (
            np.concatenate(generated_pores)
            if any(samples_.size for samples_ in generated_pores)
            else np.empty(0, dtype=np.float64)
        )
        all_pores = np.concatenate(
            (target_local["pore_diameters"], all_generated_pores)
        )
        pore_upper = (
            max(2.0, float(np.ceil(all_pores.max()))) if all_pores.size else 2.0
        )
        pore_edges = np.linspace(0.0, pore_upper, 51)
        target_pore_histogram = pore_histogram(
            target_local["pore_diameters"], pore_edges
        )
        ensemble_pore_histogram = pore_histogram(
            all_generated_pores, pore_edges
        )
        for record, pore_samples in zip(records, generated_pores):
            record["pore_size_distribution"] = {
                "probability_mass": pore_histogram(
                    pore_samples, pore_edges
                )["probability_mass"]
            }

        plot_montage(
            target,
            samples,
            records,
            [path.name for path in sample_paths],
            figures_dir,
            montage_rng,
        )
        plot_curve_ensemble(
            radius,
            target_s2,
            generated_s2,
            "$S_2(r)$",
            "Periodic two-point correlation",
            figures_dir / "fig2_s2_correlation.png",
        )
        plot_curve_ensemble(
            radius,
            target_lineal,
            generated_lineal,
            "$L(r)$",
            "Periodic four-direction lineal-path function",
            figures_dir / "fig3_lineal_path.png",
        )
        plot_pore_distribution(
            target_local["pore_diameters"],
            all_generated_pores,
            pore_edges,
            figures_dir,
        )
        plot_diversity_heatmap(
            disagreement, [path.name for path in sample_paths], figures_dir
        )

        scalar_keys = (
            "phi_s",
            "f_largest",
            "mean_strut_thickness",
            "p10_strut_thickness",
            "median_pore_diameter",
            "E_S2",
            "E_L",
            "SSIM",
            "NCC",
        )
        flagged = [
            record["file"] for record in records if record["potential_trivial_copy"]
        ]
        report = {
            "methodology": {
                "boundary_conditions": {
                    "S2": "periodic FFT autocorrelation with minimum-image radial averaging",
                    "lineal_path": "periodic, equally weighted 0/45/90/135 degree estimator",
                    "connectivity_and_EDT": "finite image domain",
                },
                "connectivity": "4-neighbor solid phase",
                "percolation": "a connected solid component touches opposing image edges",
                "local_dimensions": "twice the Euclidean distance transform at each phase pixel",
                "normalized_rmse": "RMSE(sample,target) / RMS(target)",
                "max_r": args.max_r,
            },
            "target_file": str(args.target),
            "samples_directory": str(args.samples_dir),
            "sample_count": len(records),
            "sanity_checks": sanity,
            "target": target_record,
            "samples": records,
            "pore_size_distributions": {
                "bin_edges_pixels": pore_edges,
                "target": target_pore_histogram,
                "generated_ensemble": ensemble_pore_histogram,
            },
            "novelty": {
                "SSIM_copy_threshold": 0.85,
                "flagged_count": len(flagged),
                "flagged_files": flagged,
            },
            "diversity": {
                "D_pair": diversity,
                "threshold": 0.05,
                "healthy": bool(diversity > 0.05),
                "pairwise_disagreement_matrix": disagreement,
            },
            "ensemble_summary": {
                key: metric_summary(records, key) for key in scalar_keys
            },
            "figures": [
                str(figures_dir / "fig1_montage.png"),
                str(figures_dir / "fig2_s2_correlation.png"),
                str(figures_dir / "fig3_lineal_path.png"),
                str(figures_dir / "fig4_pore_distribution.png"),
                str(figures_dir / "fig5_diversity_heatmap.png"),
            ],
        }
        output_path = args.output_dir / "evaluation_summary.json"
        output_path.write_text(
            json.dumps(json_safe(report), indent=2, allow_nan=False),
            encoding="utf-8",
        )
        print_report(report)
        print(f"\nJSON report: {output_path}")
        print(f"Figures: {figures_dir}")
        if not sanity["all_required_checks_passed"]:
            print(
                "WARNING: one or more evaluator sanity checks failed; "
                "inspect evaluation_summary.json.",
                file=sys.stderr,
            )
        return 0
    except (FileNotFoundError, NotADirectoryError, OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
