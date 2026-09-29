#!/usr/bin/env python3
"""
Procedural generator for connected disordered binary mechanical metamaterials.

Output convention:
    solid = 1
    void  = 0

Default behavior:
    - Generate twenty independent 256 x 256 samples.
    - Seeds 0 through 19.
    - Save both .npy and .png files.

Required command-line arguments:
    --seed-start INTEGER
    --num-samples INTEGER
    --output-dir PATH

Example:
    python generate_microstructures.py \
        --seed-start 100 \
        --num-samples 20 \
        --output-dir generated

Dependencies:
    numpy
    scipy
    Pillow

The algorithm is fully procedural. It does not read a reference image,
external dataset, model, API, or internet resource at runtime.
"""

from __future__ import annotations

import argparse
import heapq
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.spatial import cKDTree


# ---------------------------------------------------------------------------
# Global design parameters
# ---------------------------------------------------------------------------

SIZE = 256

# Measured target solid volume fraction.
TARGET_SOLID_FRACTION = 0.477341

# Approximate pore density / characteristic pore scale.
# More sites -> more, smaller pores and, at fixed solid fraction, thinner walls.
NUM_SITES = 425

# Smooth coordinate deformation that turns nominal Voronoi cells into
# irregular rounded/disordered cells.
WARP_SIGMA = 7.0
WARP_AMPLITUDE = 5.0

# Smooth modulation used while thickening the connected wall network.
# It produces realistic strut-thickness variability.
THICKNESS_NOISE_SIGMA = 8.0
THICKNESS_NOISE_AMPLITUDE = 0.30

# Small uncorrelated perturbation only breaks otherwise deterministic ties
# during connected growth.
GROWTH_JITTER = 0.055

# Random-site jitter inside approximately uniform grid cells.
SITE_JITTER_LOW = 0.06
SITE_JITTER_HIGH = 0.94

FOUR_CONNECTED = np.array(
    [
        [0, 1, 0],
        [1, 1, 1],
        [0, 1, 0],
    ],
    dtype=bool,
)


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------

def normalized_smooth_noise(
    rng: np.random.Generator,
    shape: tuple[int, int],
    sigma: float,
) -> np.ndarray:
    """Return zero-mean, unit-standard-deviation smooth Gaussian noise."""
    x = rng.standard_normal(shape)
    x = ndimage.gaussian_filter(x, sigma=sigma, mode="reflect")

    std = float(x.std())
    if std < 1.0e-12:
        return np.zeros(shape, dtype=np.float64)

    return (x - x.mean()) / std


def raster_line_4connected(
    mask: np.ndarray,
    y0: int,
    x0: int,
    y1: int,
    x1: int,
) -> None:
    """
    Draw a Manhattan path from (y0,x0) to (y1,x1).

    The resulting path is guaranteed to be 4-connected.
    """
    y = int(y0)
    x = int(x0)

    mask[y, x] = True

    sy = 1 if y1 >= y else -1
    while y != y1:
        y += sy
        mask[y, x] = True

    sx = 1 if x1 >= x else -1
    while x != x1:
        x += sx
        mask[y, x] = True


def connect_all_components(mask: np.ndarray) -> np.ndarray:
    """
    Join every 4-connected component using short Manhattan bridges.

    In normal operation the thickened Voronoi interface is already nearly
    always one component, so this is primarily an engineering safeguard.
    """
    mask = mask.astype(bool, copy=True)

    while True:
        labels, count = ndimage.label(mask, structure=FOUR_CONNECTED)

        if count <= 1:
            return mask

        populations = np.bincount(labels.ravel())
        populations[0] = 0
        main_id = int(np.argmax(populations))
        main = labels == main_id

        # Distance and nearest-main coordinate for every non-main pixel.
        distance, indices = ndimage.distance_transform_edt(
            ~main,
            return_indices=True,
        )

        other = (labels != 0) & (labels != main_id)
        candidate_distance = np.where(other, distance, np.inf)

        y0, x0 = np.unravel_index(
            int(np.argmin(candidate_distance)),
            mask.shape,
        )

        y1 = int(indices[0, y0, x0])
        x1 = int(indices[1, y0, x0])

        raster_line_4connected(mask, y0, x0, y1, x1)


def ensure_four_side_contact(mask: np.ndarray) -> np.ndarray:
    """
    Extend a connected network to all four image sides.

    Since the network is one component, touching all four sides guarantees
    left-right and top-bottom percolation.
    """
    mask = mask.astype(bool, copy=True)
    h, w = mask.shape

    if not mask[:, 0].any():
        ys, xs = np.where(mask)
        k = int(np.argmin(xs))
        raster_line_4connected(mask, int(ys[k]), int(xs[k]), int(ys[k]), 0)

    if not mask[:, w - 1].any():
        ys, xs = np.where(mask)
        k = int(np.argmax(xs))
        raster_line_4connected(
            mask,
            int(ys[k]),
            int(xs[k]),
            int(ys[k]),
            w - 1,
        )

    if not mask[0, :].any():
        ys, xs = np.where(mask)
        k = int(np.argmin(ys))
        raster_line_4connected(mask, int(ys[k]), int(xs[k]), 0, int(xs[k]))

    if not mask[h - 1, :].any():
        ys, xs = np.where(mask)
        k = int(np.argmax(ys))
        raster_line_4connected(
            mask,
            int(ys[k]),
            int(xs[k]),
            h - 1,
            int(xs[k]),
        )

    return connect_all_components(mask)


# ---------------------------------------------------------------------------
# Procedural morphology construction
# ---------------------------------------------------------------------------

def make_random_sites(
    rng: np.random.Generator,
    size: int,
    number: int,
) -> np.ndarray:
    """
    Construct quasi-uniform random sites.

    Starting from a jittered grid avoids very large empty regions while
    retaining substantial stochastic disorder.
    """
    grid_count = int(np.ceil(np.sqrt(number)))
    spacing = float(size) / float(grid_count)

    sites = []

    for gy in range(grid_count):
        for gx in range(grid_count):
            jy = rng.uniform(SITE_JITTER_LOW, SITE_JITTER_HIGH)
            jx = rng.uniform(SITE_JITTER_LOW, SITE_JITTER_HIGH)

            y = (gy + jy) * spacing
            x = (gx + jx) * spacing

            sites.append((y, x))

    sites = np.asarray(sites, dtype=np.float64)

    # Select exactly NUM_SITES from the slightly larger square grid.
    chosen = rng.choice(
        sites.shape[0],
        size=number,
        replace=False,
    )

    return sites[chosen]


def warped_voronoi_labels(
    rng: np.random.Generator,
    size: int,
    sites: np.ndarray,
) -> np.ndarray:
    """
    Generate a spatially warped Voronoi tessellation.

    The smooth coordinate distortion bends nominal Voronoi interfaces and
    gives the pore boundaries a disordered, biological/foam-like appearance.
    """
    shape = (size, size)

    warp_y = normalized_smooth_noise(rng, shape, WARP_SIGMA)
    warp_x = normalized_smooth_noise(rng, shape, WARP_SIGMA)

    warp_y *= WARP_AMPLITUDE
    warp_x *= WARP_AMPLITUDE

    yy, xx = np.mgrid[0:size, 0:size]

    query_points = np.column_stack(
        (
            (yy + warp_y).ravel(),
            (xx + warp_x).ravel(),
        )
    )

    tree = cKDTree(sites)

    _, labels = tree.query(
        query_points,
        k=1,
        workers=1,  # deterministic and portable
    )

    return labels.reshape(shape)


def voronoi_interface(labels: np.ndarray) -> np.ndarray:
    """
    Convert cell labels into a wall/interface mask.

    Both sides of each label discontinuity are marked. A small 4-connected
    dilation subsequently removes diagonal-only contacts and produces a
    robust seed network for connected strut growth.
    """
    wall = np.zeros(labels.shape, dtype=bool)

    horizontal_change = labels[:, 1:] != labels[:, :-1]
    wall[:, 1:] |= horizontal_change
    wall[:, :-1] |= horizontal_change

    vertical_change = labels[1:, :] != labels[:-1, :]
    wall[1:, :] |= vertical_change
    wall[:-1, :] |= vertical_change

    # One cross-shaped dilation is useful here: it converts many diagonal
    # raster contacts into explicit 4-connected contacts while retaining a
    # narrow network.
    wall = ndimage.binary_dilation(
        wall,
        structure=FOUR_CONNECTED,
        iterations=1,
    )

    wall = connect_all_components(wall)
    wall = ensure_four_side_contact(wall)

    return wall


def connected_strut_growth(
    rng: np.random.Generator,
    skeleton: np.ndarray,
    target_pixels: int,
) -> np.ndarray:
    """
    Grow a connected solid phase outward from the wall skeleton.

    Pixels are added only from the current 4-neighbor frontier. Therefore
    every added pixel is attached to the existing solid network and no
    disconnected solid islands can be produced.

    Priority is primarily distance from the skeleton, modulated by smooth
    random thickness noise, which creates locally thick and thin struts.
    """
    h, w = skeleton.shape

    initial_pixels = int(skeleton.sum())
    if initial_pixels > target_pixels:
        raise RuntimeError(
            "Initial connected skeleton exceeds requested solid fraction. "
            "Reduce NUM_SITES or the initial wall dilation."
        )

    distance = ndimage.distance_transform_edt(~skeleton)

    thickness_noise = normalized_smooth_noise(
        rng,
        skeleton.shape,
        THICKNESS_NOISE_SIGMA,
    )

    # Limit extreme fluctuations so unusual seeds remain well behaved.
    thickness_noise = np.clip(thickness_noise, -2.25, 2.25)

    width_factor = np.exp(
        THICKNESS_NOISE_AMPLITUDE * thickness_noise
    )

    priority = distance / width_factor

    # Tiny random term breaks ties and adds fine irregularity without
    # overwhelming the distance-controlled wall morphology.
    priority += GROWTH_JITTER * rng.random(skeleton.shape)

    solid = skeleton.astype(bool, copy=True)

    # "queued" prevents repeated heap insertion of the same pixel.
    queued = solid.copy()
    heap: list[tuple[float, int, int]] = []

    def queue_pixel(y: int, x: int) -> None:
        if 0 <= y < h and 0 <= x < w and not queued[y, x]:
            queued[y, x] = True
            heapq.heappush(
                heap,
                (float(priority[y, x]), int(y), int(x)),
            )

    # Initialize the growth frontier.
    ys, xs = np.where(solid)

    for y, x in zip(ys, xs):
        queue_pixel(int(y) - 1, int(x))
        queue_pixel(int(y) + 1, int(x))
        queue_pixel(int(y), int(x) - 1)
        queue_pixel(int(y), int(x) + 1)

    pixel_count = initial_pixels

    while pixel_count < target_pixels:
        if not heap:
            raise RuntimeError("Connected growth frontier unexpectedly empty.")

        _, y, x = heapq.heappop(heap)

        if solid[y, x]:
            continue

        # Every heap pixel entered through a 4-neighbor of an already-grown
        # pixel. Thus adding it preserves 4-connectivity.
        solid[y, x] = True
        pixel_count += 1

        queue_pixel(y - 1, x)
        queue_pixel(y + 1, x)
        queue_pixel(y, x - 1)
        queue_pixel(y, x + 1)

    return solid


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_engineering_rules(array: np.ndarray) -> None:
    """
    Verify the exact validity rules requested by the problem.

    Required:
        component_count == 1
        Px == 1
        Py == 1
    """
    if array.dtype != np.uint8:
        raise RuntimeError("Output array must have dtype uint8.")

    unique = np.unique(array)
    if not np.all(np.isin(unique, [0, 1])):
        raise RuntimeError("Output array must contain only 0 and 1.")

    solid = array.astype(bool)

    labels, component_count = ndimage.label(
        solid,
        structure=FOUR_CONNECTED,
    )

    if component_count != 1:
        raise RuntimeError(
            f"Invalid structure: component_count={component_count}, expected 1."
        )

    component_id = int(labels[solid][0])

    touches_left = np.any(labels[:, 0] == component_id)
    touches_right = np.any(labels[:, -1] == component_id)
    touches_top = np.any(labels[0, :] == component_id)
    touches_bottom = np.any(labels[-1, :] == component_id)

    px = bool(touches_left and touches_right)
    py = bool(touches_top and touches_bottom)

    if not px:
        raise RuntimeError("Invalid structure: left-right percolation failed.")

    if not py:
        raise RuntimeError("Invalid structure: top-bottom percolation failed.")


def generate_microstructure(seed: int) -> np.ndarray:
    """
    Generate one independent 256 x 256 stochastic microstructure.
    """
    rng = np.random.default_rng(seed)

    sites = make_random_sites(
        rng=rng,
        size=SIZE,
        number=NUM_SITES,
    )

    labels = warped_voronoi_labels(
        rng=rng,
        size=SIZE,
        sites=sites,
    )

    connected_wall_skeleton = voronoi_interface(labels)

    target_pixels = int(
        round(TARGET_SOLID_FRACTION * SIZE * SIZE)
    )

    solid = connected_strut_growth(
        rng=rng,
        skeleton=connected_wall_skeleton,
        target_pixels=target_pixels,
    )

    result = solid.astype(np.uint8)

    validate_engineering_rules(result)

    return result


# ---------------------------------------------------------------------------
# File output
# ---------------------------------------------------------------------------

def save_microstructure(
    array: np.ndarray,
    seed: int,
    output_dir: Path,
) -> None:
    """
    Save uint8 NPY and binary PNG.

    PNG convention follows the supplied morphology:
        white = solid = 1
        black = void  = 0
    """
    stem = f"microstructure_seed_{seed}"

    npy_path = output_dir / f"{stem}.npy"
    png_path = output_dir / f"{stem}.png"

    np.save(npy_path, array.astype(np.uint8, copy=False))

    png = Image.fromarray(
        (array * np.uint8(255)).astype(np.uint8),
        mode="L",
    )
    png.save(png_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate stochastic connected binary mechanical "
            "metamaterial microstructures."
        )
    )

    parser.add_argument(
        "--seed-start",
        type=int,
        default=0,
        help="First random seed. Default: 0",
    )

    parser.add_argument(
        "--num-samples",
        type=int,
        default=20,
        help="Number of consecutive seeds to generate. Default: 20",
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("generated_microstructures"),
        help=(
            "Directory receiving PNG and NPY outputs. "
            "Default: generated_microstructures"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.num_samples < 1:
        raise ValueError("--num-samples must be at least 1.")

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stop_seed = args.seed_start + args.num_samples

    for seed in range(args.seed_start, stop_seed):
        array = generate_microstructure(seed)

        save_microstructure(
            array=array,
            seed=seed,
            output_dir=args.output_dir,
        )

        actual_fraction = float(array.mean())

        print(
            f"seed {seed}: "
            f"saved; solid_fraction={actual_fraction:.6f}; "
            "component_count=1; Px=1; Py=1"
        )


if __name__ == "__main__":
    main()
