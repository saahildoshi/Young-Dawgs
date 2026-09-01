#!/usr/bin/env python3
"""
Procedural generator for 256x256 two-phase disordered mechanical metamaterials.

White / solid = 1 in the saved NPY files (255 in PNG visualization).
Black / void  = 0.

Algorithm
---------
1. Place ~100-108 blue-noise-like (Poisson-disc) sites in the domain.
2. Create a smooth random coordinate warp so cell boundaries are curved/tortuous.
3. Apply a weak random anisotropic metric to introduce directional organization.
4. For every pixel, compute distances d1 and d2 to the nearest and second-nearest
   sites in the warped/anisotropic coordinate system.  d2-d1 is smallest on the
   Voronoi-like ridge network, so thresholding it creates a connected vein network.
5. Modulate the ridge score by a second smooth random field to vary local strut width.
6. Keep exactly the target number of solid pixels.
7. For each requested random seed, generate several independent procedural candidates
   and select the one that best matches the supplied statistical descriptors while
   requiring one dominant 4-connected component that spans left-right and top-bottom.

The reference image is NOT read, loaded, or embedded by this script.
Only the numerical target descriptors below are used.

Dependencies: numpy, scipy, scikit-image, Pillow
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.morphology import medial_axis


# -----------------------------------------------------------------------------
# Output / target settings
# -----------------------------------------------------------------------------
SIZE = 256
N_SAMPLES = 20
SEEDS = range(20)
OUTDIR = Path("generated_microstructures")

TARGET_PHI = 0.394699
TARGET_SOLID_PIXELS = int(round(TARGET_PHI * SIZE * SIZE))  # 25867 pixels
TARGET_MEAN_STRUT = 6.53986
TARGET_P10_STRUT = 4.0
TARGET_MEDIAN_PORE = 16.4924
TARGET_LARGEST_COMPONENT = 0.992384

R_VALUES = (0, 1, 2, 4, 8, 16, 32, 64)
TARGET_S2 = {
    0: 0.394699,
    1: 0.351303,
    2: 0.318398,
    4: 0.253283,
    8: 0.167153,
    16: 0.137501,
    32: 0.155534,
    64: 0.155713,
}

# The lineal-path targets are included for documentation.  The generator controls
# their decay mainly through strut thickness, warp/tortuosity and the S2 fit.
TARGET_LINEAL = {
    0: 0.394699,
    1: 0.351303,
    2: 0.308788,
    4: 0.227493,
    8: 0.125214,
    16: 0.054344,
    32: 0.012596,
    64: 0.000519,
}

# Number of stochastic candidates tried for each requested seed.
# Increase for tighter statistical matching; decrease for faster generation.
CANDIDATES_PER_SEED = 10

# 4-neighbour connectivity structure.
CROSS4 = ndi.generate_binary_structure(2, 1)


# -----------------------------------------------------------------------------
# Adjustable morphology ranges
# -----------------------------------------------------------------------------
# More sites -> smaller pores and, at fixed volume fraction, thinner struts.
N_SITES_RANGE = (100, 108)          # inclusive lower, exclusive upper in rng.integers

# Larger minimum site spacing -> more uniform pore scale and a stronger S2 minimum.
MIN_SITE_DISTANCE_RANGE = (16.5, 18.5)

# Larger anisotropy -> more elongated / directionally organized pores.
ANISOTROPY_RANGE = (1.08, 1.30)

# Warp amplitude controls curvature/tortuosity of the vein network.
WARP_AMPLITUDE_RANGE = (2.6, 4.1)   # pixels
WARP_SIGMA_RANGE = (7.5, 10.5)      # pixels

# Width modulation controls local strut-thickness variability.
WIDTH_MODULATION_RANGE = (0.07, 0.18)
WIDTH_NOISE_SIGMA_RANGE = (17.0, 23.0)


# -----------------------------------------------------------------------------
# Geometry helpers
# -----------------------------------------------------------------------------
def poisson_disc_sites(
    rng: np.random.Generator,
    n_sites: int,
    min_distance: float,
    margin: float = 3.0,
    max_attempts: int = 60000,
) -> np.ndarray:
    """Simple rejection-based blue-noise point set for ~100 sites."""
    points = []
    min_d2 = float(min_distance * min_distance)

    attempts = 0
    while len(points) < n_sites and attempts < max_attempts:
        p = np.array(
            [
                rng.uniform(margin, SIZE - margin),
                rng.uniform(margin, SIZE - margin),
            ],
            dtype=float,
        )

        if not points:
            points.append(p)
        else:
            arr = np.asarray(points)
            d2 = np.sum((arr - p) ** 2, axis=1)
            if float(d2.min()) >= min_d2:
                points.append(p)
        attempts += 1

    # Extremely unlikely fallback: fill any remaining sites randomly.  The later
    # candidate-selection stage will tend to reject a poor realization.
    while len(points) < n_sites:
        points.append(
            np.array(
                [
                    rng.uniform(margin, SIZE - margin),
                    rng.uniform(margin, SIZE - margin),
                ],
                dtype=float,
            )
        )

    return np.asarray(points, dtype=float)


def smooth_unit_noise(
    rng: np.random.Generator,
    sigma: float,
) -> np.ndarray:
    """Zero-mean, unit-standard-deviation correlated Gaussian noise."""
    z = rng.standard_normal((SIZE, SIZE))
    z = ndi.gaussian_filter(z, sigma=sigma, mode="reflect")
    z -= z.mean()
    z /= z.std() + 1.0e-12
    return z


def query_two_nearest(tree: cKDTree, pts: np.ndarray) -> np.ndarray:
    """SciPy-version-compatible k=2 KD-tree query."""
    try:
        distances, _ = tree.query(pts, k=2, workers=-1)
    except TypeError:  # older SciPy
        distances, _ = tree.query(pts, k=2)
    return distances


def generate_candidate(master_seed: int, candidate_index: int) -> Tuple[np.ndarray, Dict[str, float]]:
    """Generate one fully procedural binary candidate."""
    # A SeedSequence makes every candidate deterministic yet independent.
    rng = np.random.default_rng(
        np.random.SeedSequence([int(master_seed), int(candidate_index), 734291])
    )

    n_sites = int(rng.integers(N_SITES_RANGE[0], N_SITES_RANGE[1]))
    min_site_distance = float(rng.uniform(*MIN_SITE_DISTANCE_RANGE))
    anisotropy = float(rng.uniform(*ANISOTROPY_RANGE))
    warp_amplitude = float(rng.uniform(*WARP_AMPLITUDE_RANGE))
    warp_sigma = float(rng.uniform(*WARP_SIGMA_RANGE))
    width_modulation = float(rng.uniform(*WIDTH_MODULATION_RANGE))
    width_noise_sigma = float(rng.uniform(*WIDTH_NOISE_SIGMA_RANGE))

    sites = poisson_disc_sites(rng, n_sites, min_site_distance)

    # Smooth stochastic coordinate warp.
    warp_y = smooth_unit_noise(rng, warp_sigma) * warp_amplitude
    warp_x = smooth_unit_noise(rng, warp_sigma) * warp_amplitude

    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    warped_pixels = np.column_stack(
        ((yy + warp_y).ravel(), (xx + warp_x).ravel())
    )

    # Apply the same warp to the generator sites by interpolation.
    site_warp_y = ndi.map_coordinates(
        warp_y, [sites[:, 0], sites[:, 1]], order=1, mode="reflect"
    )
    site_warp_x = ndi.map_coordinates(
        warp_x, [sites[:, 0], sites[:, 1]], order=1, mode="reflect"
    )
    warped_sites = sites + np.column_stack((site_warp_y, site_warp_x))

    # Weak anisotropic distance metric with a different preferred angle per sample.
    theta = float(rng.uniform(0.0, math.pi))
    c, s = math.cos(theta), math.sin(theta)
    rotation = np.array([[c, -s], [s, c]], dtype=float)
    metric = rotation @ np.diag([1.0 / anisotropy, anisotropy]) @ rotation.T

    q_pixels = warped_pixels @ metric.T
    q_sites = warped_sites @ metric.T

    tree = cKDTree(q_sites)
    d = query_two_nearest(tree, q_pixels)

    # d2-d1 is zero on generalized Voronoi boundaries and grows into cell interiors.
    ridge_score = (d[:, 1] - d[:, 0]).reshape(SIZE, SIZE)

    # Spatial width modulation gives a realistic distribution of strut thicknesses.
    width_noise = smooth_unit_noise(rng, width_noise_sigma)
    ridge_score = ridge_score / np.exp(width_modulation * width_noise)

    # Exactly match the target solid-pixel count without any traced/template pixels.
    flat_score = ridge_score.ravel()
    selected = np.argpartition(flat_score, TARGET_SOLID_PIXELS - 1)[:TARGET_SOLID_PIXELS]
    mask = np.zeros(SIZE * SIZE, dtype=bool)
    mask[selected] = True
    mask = mask.reshape(SIZE, SIZE)

    params = {
        "n_sites": float(n_sites),
        "min_site_distance": min_site_distance,
        "anisotropy": anisotropy,
        "theta": theta,
        "warp_amplitude": warp_amplitude,
        "warp_sigma": warp_sigma,
        "width_modulation": width_modulation,
        "width_noise_sigma": width_noise_sigma,
    }
    return mask, params


# -----------------------------------------------------------------------------
# Descriptor calculations used only to choose among procedural candidates
# -----------------------------------------------------------------------------
def connectivity_metrics(mask: np.ndarray) -> Tuple[float, bool, bool]:
    labels, n = ndi.label(mask, structure=CROSS4)
    if n == 0:
        return 0.0, False, False

    counts = np.bincount(labels.ravel())[1:]
    largest_label = int(np.argmax(counts) + 1)
    dominant = labels == largest_label
    largest_fraction = float(counts.max() / mask.sum())

    lr = bool(dominant[:, 0].any() and dominant[:, -1].any())
    tb = bool(dominant[0, :].any() and dominant[-1, :].any())
    return largest_fraction, lr, tb


def medial_axis_with_distance(mask: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    # rng=0 makes tie-breaking deterministic in recent scikit-image releases.
    try:
        return medial_axis(mask, return_distance=True, rng=0)
    except TypeError:
        return medial_axis(mask, return_distance=True)


def local_strut_statistics(mask: np.ndarray) -> Tuple[float, float]:
    skeleton, distance = medial_axis_with_distance(mask)
    diameters = 2.0 * distance[skeleton]
    return float(diameters.mean()), float(np.percentile(diameters, 10.0))


def median_pore_diameter(mask: np.ndarray) -> float:
    """Median over void components of twice their maximum Euclidean inscribed radius."""
    void = ~mask
    labels, n = ndi.label(void, structure=CROSS4)
    if n == 0:
        return 0.0

    edt = ndi.distance_transform_edt(void)
    maxima = ndi.maximum(edt, labels=labels, index=np.arange(1, n + 1))
    return float(np.median(2.0 * maxima))


def two_point_correlation(mask: np.ndarray) -> Dict[int, float]:
    """Periodic isotropic S2 using FFT autocorrelation and one-pixel radial bins."""
    a = mask.astype(np.float64)
    f = np.fft.fftn(a)
    corr = np.fft.ifftn(f * np.conj(f)).real / a.size
    corr = np.fft.fftshift(corr)

    yy, xx = np.indices(mask.shape)
    cy, cx = np.array(mask.shape) // 2
    radius = np.hypot(yy - cy, xx - cx)

    result: Dict[int, float] = {}
    for r in R_VALUES:
        if r == 0:
            result[r] = float(mask.mean())
        else:
            annulus = np.abs(radius - r) < 0.5
            result[r] = float(corr[annulus].mean())
    return result


def candidate_score(mask: np.ndarray) -> Tuple[float, Dict[str, float]]:
    largest, lr, tb = connectivity_metrics(mask)
    mean_t, p10_t = local_strut_statistics(mask)
    pore_d = median_pore_diameter(mask)
    s2 = two_point_correlation(mask)

    # Hard preference for one dominant 4-connected network spanning both directions.
    if not (lr and tb and largest >= 0.985):
        score = 1.0e6
    else:
        score = 0.0

    # Scale errors by practical tolerances rather than demanding pixel-for-pixel fit.
    score += ((mean_t - TARGET_MEAN_STRUT) / 0.38) ** 2
    score += ((p10_t - TARGET_P10_STRUT) / 0.75) ** 2
    score += ((pore_d - TARGET_MEDIAN_PORE) / 0.85) ** 2

    # Being fully connected (largest fraction = 1) is acceptable; only weakly favor
    # the reported 0.992 value so connectivity is never sacrificed for the fit.
    score += 0.10 * ((largest - TARGET_LARGEST_COMPONENT) / 0.02) ** 2

    s2_tolerances = {
        1: 0.005,
        2: 0.007,
        4: 0.009,
        8: 0.010,
        16: 0.010,
        32: 0.010,
        64: 0.010,
    }
    s2_weights = {1: 1.0, 2: 1.0, 4: 1.0, 8: 1.2, 16: 1.4, 32: 0.8, 64: 0.8}
    for r, tol in s2_tolerances.items():
        score += s2_weights[r] * ((s2[r] - TARGET_S2[r]) / tol) ** 2

    metrics = {
        "solid_fraction": float(mask.mean()),
        "largest_component_fraction": largest,
        "left_right_percolation": float(lr),
        "top_bottom_percolation": float(tb),
        "mean_strut_thickness": mean_t,
        "p10_strut_thickness": p10_t,
        "median_pore_diameter": pore_d,
    }
    for r in R_VALUES:
        metrics[f"S2_r{r}"] = s2[r]

    return float(score), metrics


# -----------------------------------------------------------------------------
# Rare safety repair for spanning (normally candidate selection makes this unused)
# -----------------------------------------------------------------------------
def force_dominant_component_to_all_edges(mask: np.ndarray) -> np.ndarray:
    """Attach the largest 4-connected component to any missing domain edge."""
    out = mask.copy()
    labels, n = ndi.label(out, structure=CROSS4)
    if n == 0:
        raise RuntimeError("Generated an empty solid phase, which should be impossible.")

    counts = np.bincount(labels.ravel())[1:]
    main_label = int(np.argmax(counts) + 1)
    main = labels == main_label
    ys, xs = np.where(main)

    # Straight Manhattan extensions preserve 4-connectivity.
    i = int(np.argmin(xs))
    out[ys[i], : xs[i] + 1] = True
    i = int(np.argmax(xs))
    out[ys[i], xs[i] :] = True
    i = int(np.argmin(ys))
    out[: ys[i] + 1, xs[i]] = True
    i = int(np.argmax(ys))
    out[ys[i] :, xs[i]] = True

    return out


# -----------------------------------------------------------------------------
# Main generation loop
# -----------------------------------------------------------------------------
def generate_one(seed: int) -> Tuple[np.ndarray, Dict[str, float], Dict[str, float]]:
    best_mask = None
    best_params = None
    best_metrics = None
    best_score = float("inf")

    for candidate_index in range(CANDIDATES_PER_SEED):
        mask, params = generate_candidate(seed, candidate_index)
        score, metrics = candidate_score(mask)

        if score < best_score:
            best_score = score
            best_mask = mask
            best_params = params
            best_metrics = metrics

    assert best_mask is not None and best_params is not None and best_metrics is not None

    largest, lr, tb = connectivity_metrics(best_mask)
    if not (lr and tb and largest >= 0.985):
        best_mask = force_dominant_component_to_all_edges(best_mask)
        _, best_metrics = candidate_score(best_mask)

    return best_mask, best_params, best_metrics


def save_sample(mask: np.ndarray, seed: int) -> None:
    arr = mask.astype(np.uint8)  # solid=1, void=0

    npy_path = OUTDIR / f"microstructure_seed_{seed:02d}.npy"
    png_path = OUTDIR / f"microstructure_seed_{seed:02d}.png"

    np.save(npy_path, arr)
    Image.fromarray(arr * 255, mode="L").save(png_path)


def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    print(f"Generating {N_SAMPLES} samples in: {OUTDIR.resolve()}")
    print(f"Target solid pixels per sample: {TARGET_SOLID_PIXELS}/{SIZE*SIZE}")

    for seed in SEEDS:
        mask, params, metrics = generate_one(seed)
        save_sample(mask, seed)

        print(
            f"seed {seed:02d} | "
            f"phi={metrics['solid_fraction']:.6f} | "
            f"LCF={metrics['largest_component_fraction']:.6f} | "
            f"LR={bool(metrics['left_right_percolation'])} "
            f"TB={bool(metrics['top_bottom_percolation'])} | "
            f"mean_t={metrics['mean_strut_thickness']:.3f} | "
            f"p10_t={metrics['p10_strut_thickness']:.3f} | "
            f"pore50={metrics['median_pore_diameter']:.3f} | "
            f"sites={int(params['n_sites'])}"
        )

    print("Done. Each sample was saved as both PNG and NPY (uint8, solid=1, void=0).")


if __name__ == "__main__":
    main()
