#!/usr/bin/env python3
"""
Procedural generator for binary microstructures resembling a connected,
bright intergranular network surrounding irregular dark domains.

Algorithm
---------
1. Randomly place a mildly repulsive set of cell sites in and just outside
   the image domain.
2. Build a distorted, weighted Voronoi-like tessellation. Smooth random
   coordinate warps make the cell boundaries non-straight and stochastic.
3. Detect interfaces between neighboring cells.
4. Convert those interfaces into a finite-width solid network. Two smooth
   random fields modulate boundary roughness and local width.
5. Threshold the interface score to obtain the requested solid fraction,
   then apply one 3x3 majority pass to remove single-pixel artifacts.

The reference image is NOT read at runtime. Every sample is generated from
scratch from its RNG seed.

Important adjustable parameters are grouped in Config below:
- nominal_cells: controls the characteristic domain size.
- min_site_separation: prevents too many tiny cells.
- warp_sigma / warp_amplitude: control large-scale boundary waviness.
- site_weight_std: controls variation in cell size.
- rough_sigma / rough_amplitude: control small-scale interface irregularity.
- width_sigma / width_amplitude: control spatial variation of network width.
- target_solid_fraction: controls the amount of solid (1) versus void (0).

Dependencies: numpy, scipy, pillow
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree


@dataclass(frozen=True)
class Config:
    size: int = 256
    nominal_cells: int = 68
    outside_margin: float = 24.0
    min_site_separation: float = 11.5

    # Large-scale distortion of the cellular partition.
    warp_sigma: float = 8.0
    warp_amplitude: float = 4.5

    # Random additive weights applied to nearby sites; this broadens the
    # cell-size distribution without changing the basic cellular character.
    site_weight_std: float = 1.8
    nearest_candidates: int = 5

    # Small-scale roughening of the interface.
    rough_sigma: float = 3.0
    rough_amplitude: float = 0.55

    # Slow spatial modulation of the solid-network width.
    width_sigma: float = 13.0
    width_amplitude: float = 0.60

    # Solid is encoded as 1, void as 0.
    target_solid_fraction: float = 0.40

    # One majority pass removes isolated one-pixel defects while preserving
    # irregular boundaries.
    majority_passes: int = 1


CFG = Config()


def smooth_standard_noise(
    rng: np.random.Generator,
    shape: tuple[int, int],
    sigma: float,
) -> np.ndarray:
    """Return zero-mean, unit-variance smooth Gaussian random noise."""
    z = rng.standard_normal(shape)
    z = ndi.gaussian_filter(z, sigma=sigma, mode="reflect")
    z -= z.mean()
    z /= z.std() + 1.0e-12
    return z


def sample_sites(
    rng: np.random.Generator,
    cfg: Config,
) -> np.ndarray:
    """
    Sample random cellular sites in an expanded box using simple rejection
    to impose a mild minimum separation.

    The expanded box prevents abnormally large truncated cells at the image
    edge while keeping the final image non-periodic.
    """
    n = cfg.size
    margin = cfg.outside_margin
    low = -margin
    high = n + margin

    expanded_area = (high - low) ** 2
    target = int(round(cfg.nominal_cells * expanded_area / (n * n)))

    points: list[np.ndarray] = []
    min_sep2 = cfg.min_site_separation ** 2
    max_attempts = target * 500

    for _ in range(max_attempts):
        if len(points) >= target:
            break

        candidate = rng.uniform(low, high, size=2)
        if not points:
            points.append(candidate)
            continue

        p = np.asarray(points)
        d2 = np.sum((p - candidate) ** 2, axis=1)
        if np.min(d2) >= min_sep2:
            points.append(candidate)

    # This fallback is rarely needed; it guarantees completion even after
    # aggressive parameter changes.
    if len(points) < target:
        extra = rng.uniform(low, high, size=(target - len(points), 2))
        points.extend(extra)

    return np.asarray(points, dtype=np.float64)


def make_partition(
    rng: np.random.Generator,
    cfg: Config,
    sites: np.ndarray,
) -> np.ndarray:
    """Create a warped, weighted Voronoi-like integer label field."""
    n = cfg.size
    y, x = np.mgrid[0:n, 0:n]

    dy = smooth_standard_noise(rng, (n, n), cfg.warp_sigma)
    dx = smooth_standard_noise(rng, (n, n), cfg.warp_sigma)
    dy *= cfg.warp_amplitude
    dx *= cfg.warp_amplitude

    query_points = np.column_stack(
        ((y + dy).ravel(), (x + dx).ravel())
    )

    tree = cKDTree(sites)
    k = min(cfg.nearest_candidates, len(sites))
    distances, indices = tree.query(query_points, k=k)

    # cKDTree returns 1-D arrays when k == 1; normalize the shape.
    if k == 1:
        distances = distances[:, None]
        indices = indices[:, None]

    site_weights = rng.normal(0.0, cfg.site_weight_std, size=len(sites))
    weighted_score = distances + site_weights[indices]
    choice = np.argmin(weighted_score, axis=1)

    labels = indices[np.arange(indices.shape[0]), choice]
    return labels.reshape(n, n)


def interface_mask(labels: np.ndarray) -> np.ndarray:
    """Mark pixels touching a different cell label in the 4-neighborhood."""
    boundary = np.zeros(labels.shape, dtype=bool)

    diff = labels[1:, :] != labels[:-1, :]
    boundary[1:, :] |= diff
    boundary[:-1, :] |= diff

    diff = labels[:, 1:] != labels[:, :-1]
    boundary[:, 1:] |= diff
    boundary[:, :-1] |= diff

    return boundary


def generate_microstructure(seed: int, cfg: Config = CFG) -> np.ndarray:
    """
    Generate one uint8 binary microstructure.

    Returns
    -------
    array, shape (256, 256), dtype uint8
        solid = 1
        void  = 0
    """
    rng = np.random.default_rng(seed)

    sites = sample_sites(rng, cfg)
    labels = make_partition(rng, cfg, sites)
    boundary = interface_mask(labels)

    # Euclidean distance from every pixel to the nearest cellular interface.
    distance_to_interface = ndi.distance_transform_edt(~boundary)

    # Small-scale roughness perturbs the interface contour, while the
    # low-frequency width field makes some ligaments locally thicker/thinner.
    rough = smooth_standard_noise(rng, labels.shape, cfg.rough_sigma)
    rough *= cfg.rough_amplitude

    width_modulation = smooth_standard_noise(
        rng, labels.shape, cfg.width_sigma
    )
    width_modulation *= cfg.width_amplitude

    # Lower score means "more interface-like" and therefore more likely solid.
    interface_score = (
        distance_to_interface + rough - width_modulation
    )

    # Quantile thresholding gives stable phase fraction across independent
    # realizations while preserving different geometry for each seed.
    threshold = np.quantile(
        interface_score, cfg.target_solid_fraction
    )
    solid = interface_score <= threshold

    # Remove isolated one-pixel irregularities with a local majority rule.
    kernel = np.ones((3, 3), dtype=np.int8)
    for _ in range(cfg.majority_passes):
        count = ndi.convolve(
            solid.astype(np.int8),
            kernel,
            mode="reflect",
        )
        solid = count >= 5

    return solid.astype(np.uint8)


def save_sample(
    array: np.ndarray,
    seed: int,
    out_dir: Path,
) -> None:
    """Save one sample as both 0/1 NPY and true 1-bit PNG."""
    stem = f"microstructure_seed_{seed:02d}"

    # NPY preserves the required binary encoding exactly:
    # solid = 1, void = 0.
    np.save(
        out_dir / f"{stem}.npy",
        array.astype(np.uint8, copy=False),
    )

    # Save a true 1-bit PNG:
    # stored bit 1 = solid, stored bit 0 = void.
    # Image viewers display 1 as white and 0 as black.
    png = Image.fromarray(array.astype(bool))
    png.save(out_dir / f"{stem}.png")


def main() -> None:
    out_dir = Path("generated_microstructures")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Exactly twenty independent stochastic realizations:
    # seeds 0, 1, ..., 19.
    for seed in range(20):
        sample = generate_microstructure(seed, CFG)

        # Defensive checks for the requested format.
        assert sample.shape == (256, 256)
        assert sample.dtype == np.uint8
        assert np.all((sample == 0) | (sample == 1))

        save_sample(sample, seed, out_dir)

        print(
            f"seed={seed:02d}  "
            f"solid_fraction={sample.mean():.4f}  "
            f"saved={out_dir / ('microstructure_seed_' + format(seed, '02d'))}"
            ".[png|npy]"
        )


if __name__ == "__main__":
    main()