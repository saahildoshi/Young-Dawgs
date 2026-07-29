"""Morphological and statistical metrics for two-phase 2-D structures."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
from scipy import ndimage, signal
from skimage.morphology import skeletonize

from .io import validate_binary_array


FOUR_CONNECTED_STRUCTURE = np.array(
    [[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=np.uint8
)


def _validate_max_r(max_r: int) -> int:
    if isinstance(max_r, bool) or int(max_r) != max_r or max_r < 0:
        raise ValueError(f"max_r must be a non-negative integer, received {max_r}.")
    return int(max_r)


def compute_basic_metrics(binary_array: np.ndarray) -> dict[str, float | bool | int]:
    """Compute volume fraction, 4-connectedness, and directional percolation.

    A component percolates in ``x`` when it touches both the left and right
    image boundaries. It percolates in ``y`` when it touches both the top and
    bottom boundaries.
    """
    binary = validate_binary_array(binary_array)
    solid_pixels = int(binary.sum())
    volume_fraction = solid_pixels / binary.size

    labels, component_count = ndimage.label(
        binary, structure=FOUR_CONNECTED_STRUCTURE
    )
    if component_count == 0:
        largest_pixels = 0
        largest_fraction = 0.0
        percolates_x = False
        percolates_y = False
    else:
        counts = np.bincount(labels.ravel())
        counts[0] = 0
        largest_pixels = int(counts.max())
        largest_fraction = largest_pixels / solid_pixels

        left = set(np.unique(labels[:, 0])) - {0}
        right = set(np.unique(labels[:, -1])) - {0}
        top = set(np.unique(labels[0, :])) - {0}
        bottom = set(np.unique(labels[-1, :])) - {0}
        percolates_x = bool(left.intersection(right))
        percolates_y = bool(top.intersection(bottom))

    return {
        "solid_volume_fraction": float(volume_fraction),
        "largest_component_fraction": float(largest_fraction),
        "percolates_x": percolates_x,
        "percolates_y": percolates_y,
        "solid_pixels": solid_pixels,
        "largest_component_pixels": largest_pixels,
        "component_count": int(component_count),
    }


def compute_s2_correlation(
    binary_array: np.ndarray, max_r: int = 64
) -> dict[str, np.ndarray | float]:
    """Compute the finite-domain, radially averaged two-point function ``S2(r)``.

    Linear (zero-padded) FFT correlation is used rather than a periodic
    correlation. For each integer-radius annulus, the number of solid-solid
    pixel pairs is divided by the number of geometrically available pairs.
    Annuli are assigned by rounding Euclidean displacement to the nearest
    integer. Thus ``S2[0]`` is exactly the solid volume fraction.
    """
    binary = validate_binary_array(binary_array)
    max_r = _validate_max_r(max_r)
    height, width = binary.shape
    if max_r > int(np.hypot(height - 1, width - 1)):
        raise ValueError("max_r exceeds the maximum possible image displacement.")

    values = binary.astype(np.float64, copy=False)
    ones = np.ones_like(values)
    # fftconvolve(a, reversed(a)) produces full linear cross-correlation.
    pair_counts = signal.fftconvolve(values, values[::-1, ::-1], mode="full")
    overlap_counts = signal.fftconvolve(ones, ones[::-1, ::-1], mode="full")
    pair_counts = np.maximum(pair_counts, 0.0)  # suppress roundoff near zero
    overlap_counts = np.maximum(overlap_counts, 1.0)

    dy = np.arange(-(height - 1), height)
    dx = np.arange(-(width - 1), width)
    radius_bins = np.rint(np.hypot(dy[:, None], dx[None, :])).astype(np.int32)
    include = radius_bins <= max_r

    numerator = np.bincount(
        radius_bins[include].ravel(),
        weights=pair_counts[include].ravel(),
        minlength=max_r + 1,
    )
    denominator = np.bincount(
        radius_bins[include].ravel(),
        weights=overlap_counts[include].ravel(),
        minlength=max_r + 1,
    )
    s2 = np.divide(
        numerator,
        denominator,
        out=np.full(max_r + 1, np.nan, dtype=np.float64),
        where=denominator > 0,
    )
    phi_s = float(values.mean())
    s2[0] = phi_s
    if not np.isclose(s2[0], phi_s, rtol=0.0, atol=1e-12):
        raise RuntimeError("Internal S2 validation failed at r=0.")

    return {
        "r": np.arange(max_r + 1, dtype=np.int32),
        "s2": s2,
        "solid_volume_fraction": phi_s,
    }


def _run_lengths(lines: Iterable[np.ndarray]) -> np.ndarray:
    """Return lengths of all nonzero runs across a sequence of 1-D lines."""
    runs: list[np.ndarray] = []
    for line in lines:
        padded = np.pad(np.asarray(line, dtype=np.int8), (1, 1))
        transitions = np.diff(padded)
        starts = np.flatnonzero(transitions == 1)
        stops = np.flatnonzero(transitions == -1)
        if starts.size:
            runs.append(stops - starts)
    return np.concatenate(runs) if runs else np.empty(0, dtype=np.int32)


def _lineal_curve(
    lines: list[np.ndarray], max_r: int
) -> tuple[np.ndarray, np.ndarray]:
    """Compute lineal probability and denominators for endpoint separation r."""
    lengths = _run_lengths(lines)
    line_lengths = np.fromiter((line.size for line in lines), dtype=np.int64)
    r = np.arange(max_r + 1, dtype=np.int64)
    segment_pixels = r + 1

    if lengths.size:
        valid = np.maximum(lengths[:, None] - segment_pixels[None, :] + 1, 0)
        numerator = valid.sum(axis=0, dtype=np.int64)
    else:
        numerator = np.zeros(max_r + 1, dtype=np.int64)
    denominator = np.maximum(
        line_lengths[:, None] - segment_pixels[None, :] + 1, 0
    ).sum(axis=0, dtype=np.int64)
    probability = np.divide(
        numerator,
        denominator,
        out=np.full(max_r + 1, np.nan, dtype=np.float64),
        where=denominator > 0,
    )
    return probability, denominator


def compute_lineal_path(
    binary_array: np.ndarray, max_r: int = 64
) -> dict[str, np.ndarray]:
    """Compute directional and approximately radial lineal-path functions.

    ``r`` is endpoint separation in pixels, so a tested segment contains
    ``r + 1`` digital pixels and ``L(0) = phi_s``. ``L_x`` and ``L_y`` use
    horizontal and vertical segments. The isotropic ``L`` is a denominator-
    weighted average over 0, 45, 90, and 135 degree lattice directions. This
    four-orientation estimator is deterministic and substantially less costly
    than dense angular ray sampling.
    """
    binary = validate_binary_array(binary_array)
    max_r = _validate_max_r(max_r)
    height, width = binary.shape
    if max_r >= max(height, width):
        raise ValueError(
            "max_r must be smaller than the largest image dimension."
        )

    horizontal = [binary[row, :] for row in range(height)]
    vertical = [binary[:, col] for col in range(width)]
    diagonal_up = [
        np.diagonal(binary, offset=offset)
        for offset in range(-(height - 1), width)
    ]
    flipped = np.fliplr(binary)
    diagonal_down = [
        np.diagonal(flipped, offset=offset)
        for offset in range(-(height - 1), width)
    ]

    lx, nx = _lineal_curve(horizontal, max_r)
    ly, ny = _lineal_curve(vertical, max_r)
    l45, n45 = _lineal_curve(diagonal_up, max_r)
    l135, n135 = _lineal_curve(diagonal_down, max_r)
    denominators = np.vstack((nx, ny, n45, n135))
    curves = np.vstack((lx, ly, l45, l135))
    total_denominator = denominators.sum(axis=0)
    radial = np.divide(
        np.nansum(curves * denominators, axis=0),
        total_denominator,
        out=np.full(max_r + 1, np.nan, dtype=np.float64),
        where=total_denominator > 0,
    )
    radial[0] = binary.mean()

    return {
        "r": np.arange(max_r + 1, dtype=np.int32),
        "l_x": lx,
        "l_y": ly,
        "l_45": l45,
        "l_135": l135,
        "l": radial,
    }


def _distribution(samples: np.ndarray) -> dict[str, np.ndarray]:
    """Create a unit-bin probability-mass histogram for nonnegative samples."""
    if samples.size == 0:
        return {
            "bin_edges": np.array([], dtype=np.float64),
            "probability": np.array([], dtype=np.float64),
        }
    upper = max(1.0, float(np.ceil(samples.max())))
    edges = np.arange(0.0, upper + 1.0, 1.0)
    if edges[-1] <= samples.max():
        edges = np.append(edges, edges[-1] + 1.0)
    counts, edges = np.histogram(samples, bins=edges)
    return {
        "bin_edges": edges,
        "probability": counts.astype(np.float64) / counts.sum(),
    }


def compute_local_dimensions(binary_array: np.ndarray) -> dict[str, object]:
    """Measure skeleton strut widths and enclosed-pore diameters using EDT.

    Strut thickness is twice the solid EDT sampled on the solid skeleton. Each
    enclosed 4-connected void component contributes one pore diameter equal to
    twice its maximum void EDT. Boundary-touching void is classified as
    open/external and excluded from the pore population.
    """
    binary = validate_binary_array(binary_array)
    solid = binary.astype(bool)
    void = ~solid

    if solid.any() and void.any():
        solid_edt = ndimage.distance_transform_edt(solid)
        strut_samples = 2.0 * solid_edt[skeletonize(solid)]

        void_edt = ndimage.distance_transform_edt(void)
        void_labels, void_component_count = ndimage.label(
            void, structure=FOUR_CONNECTED_STRUCTURE
        )
        boundary_labels = set(np.unique(void_labels[0, :]))
        boundary_labels.update(np.unique(void_labels[-1, :]))
        boundary_labels.update(np.unique(void_labels[:, 0]))
        boundary_labels.update(np.unique(void_labels[:, -1]))
        boundary_labels.discard(0)
        enclosed_labels = [
            label
            for label in range(1, void_component_count + 1)
            if label not in boundary_labels
        ]
        pore_samples = np.asarray(
            [
                2.0 * float(void_edt[void_labels == label].max())
                for label in enclosed_labels
            ],
            dtype=np.float64,
        )
        excluded_open_pores = len(boundary_labels)
    else:
        strut_samples = np.empty(0, dtype=np.float64)
        pore_samples = np.empty(0, dtype=np.float64)
        excluded_open_pores = int(void.any())

    mean_thickness = (
        float(np.mean(strut_samples)) if strut_samples.size else float("nan")
    )
    p10_thickness = (
        float(np.percentile(strut_samples, 10))
        if strut_samples.size
        else float("nan")
    )
    median_pore = (
        float(np.median(pore_samples)) if pore_samples.size else float("nan")
    )

    return {
        "strut_thickness_samples": strut_samples,
        "pore_diameter_samples": pore_samples,
        "strut_thickness_distribution": _distribution(strut_samples),
        "pore_diameter_distribution": _distribution(pore_samples),
        "mean_strut_thickness": mean_thickness,
        "p10_strut_thickness": p10_thickness,
        "median_pore_diameter": median_pore,
        "excluded_open_pore_components": excluded_open_pores,
        "strut_measurement": "2*solid_EDT sampled on solid skeleton",
        "pore_measurement": (
            "one 2*max(void_EDT) value per enclosed 4-connected void component"
        ),
    }
