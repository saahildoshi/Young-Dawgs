#!/usr/bin/env python3
"""
Procedural generator for a binary disordered mechanical metamaterial.

Phase convention
----------------
    1 = solid (saved white in PNG)
    0 = void  (saved black in PNG)

Default output
--------------
Twenty independent 256 x 256 samples are generated for seeds 0..19.
For each seed the script saves:
    microstructure_seed_<seed>.npy
    microstructure_seed_<seed>.png

Algorithm
---------
1. Create a jittered set of cellular sites.
2. Apply a smooth stochastic coordinate warp and rasterize the resulting
   nearest-site (Voronoi-like) tessellation.
3. Use the cell interfaces as a disordered wall network.
4. Repair the wall network so it is one 4-connected component and touches
   all four image boundaries.
5. Grow solid only from that connected network, with a smooth random
   thickness modulation, until the requested solid-pixel count is reached.
   Because growth is restricted to the 4-neighbour frontier, connectivity is
   preserved by construction.

Revision tuning
---------------
Round-3 feedback showed that topology, solid fraction, p10 strut thickness, and
median enclosed-pore diameter were already matched, while mean local strut
thickness was only 0.15% low. This revision therefore keeps the same cellular
wall construction and exact solid budget. It broadens site-position jitter
slightly, lengthens the smooth warp scale, and reduces frontier tie-breaking
jitter. These small changes preserve the pore scale while increasing geometric
disorder and bringing the mean local strut thickness onto the target.

The thickening step remains budget-aware. If a rare seed would make the
initial wall network larger than the requested solid fraction, the script
automatically retains the thinner connected wall seed rather than failing.

Adjustable morphology parameters are grouped in the constants below. The
most influential are NUM_SITES (pore scale), WARP_SIGMA/WARP_AMPLITUDE
(boundary irregularity), and WIDTH_NOISE_SIGMA/WIDTH_NOISE_AMPLITUDE
(spatial variation in strut width).
"""

from __future__ import annotations

import argparse
import heapq
from pathlib import Path
from typing import Tuple

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree


# -----------------------------------------------------------------------------
# Fixed output / target settings
# -----------------------------------------------------------------------------
IMAGE_SIZE = 256
TARGET_SOLID_FRACTION = 0.477341

# Morphology controls.
NUM_SITES = 380
SITE_JITTER_MIN = 0.05
SITE_JITTER_MAX = 0.95

WARP_SIGMA = 8.7
WARP_AMPLITUDE = 2.8

WIDTH_NOISE_SIGMA = 8.0
WIDTH_NOISE_AMPLITUDE = 0.30

FRONTIER_JITTER = 0.013
INITIAL_WALL_THICKENING = 1

# Four-connected neighbourhood.
STRUCTURE_4 = np.array(
    [
        [False, True, False],
        [True, True, True],
        [False, True, False],
    ],
    dtype=bool,
)


# -----------------------------------------------------------------------------
# Geometry helpers
# -----------------------------------------------------------------------------
def _draw_manhattan_connection(
    mask: np.ndarray,
    y0: int,
    x0: int,
    y1: int,
    x1: int,
    rng: np.random.Generator,
) -> None:
    """Add an L-shaped, 4-connected path between two pixels in-place."""
    if rng.random() < 0.5:
        xa, xb = sorted((x0, x1))
        mask[y0, xa : xb + 1] = True

        ya, yb = sorted((y0, y1))
        mask[ya : yb + 1, x1] = True
    else:
        ya, yb = sorted((y0, y1))
        mask[ya : yb + 1, x0] = True

        xa, xb = sorted((x0, x1))
        mask[y1, xa : xb + 1] = True


def _connect_all_4_components(
    mask: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Return a copy of mask containing one 4-connected foreground component.

    Rasterized cellular interfaces are normally already connected. Rare
    one-pixel raster gaps are repaired by joining the nearest non-main
    component to the largest component with a shortest Manhattan connector.
    """
    connected = np.asarray(
        mask,
        dtype=bool,
    ).copy()

    for _ in range(256):
        labels, count = ndi.label(
            connected,
            structure=STRUCTURE_4,
        )

        if count <= 1:
            return connected

        component_sizes = np.bincount(
            labels.ravel()
        )
        component_sizes[0] = 0

        main_label = int(
            np.argmax(component_sizes)
        )
        main = (
            labels
            == main_label
        )

        distance, nearest = ndi.distance_transform_edt(
            ~main,
            return_indices=True,
        )

        other = (
            (labels != 0)
            & (labels != main_label)
        )

        candidate_distance = np.where(
            other,
            distance,
            np.inf,
        )

        flat_index = int(
            np.argmin(
                candidate_distance
            )
        )

        y0, x0 = np.unravel_index(
            flat_index,
            connected.shape,
        )

        if not np.isfinite(
            candidate_distance[y0, x0]
        ):
            raise RuntimeError(
                "Could not locate a component to connect."
            )

        y1 = int(
            nearest[0, y0, x0]
        )
        x1 = int(
            nearest[1, y0, x0]
        )

        _draw_manhattan_connection(
            connected,
            int(y0),
            int(x0),
            y1,
            x1,
            rng,
        )

    raise RuntimeError(
        "Could not merge the wall network into one component."
    )


def _force_boundary_spanning(
    mask: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """Ensure the connected wall network touches left/right/top/bottom."""
    spanning = np.asarray(
        mask,
        dtype=bool,
    ).copy()

    if not spanning.any():
        raise RuntimeError(
            "Cannot span boundaries from an empty wall network."
        )

    # Left edge.
    if not np.any(
        spanning[:, 0]
    ):
        ys, xs = np.where(
            spanning
        )

        i = int(
            np.argmin(xs)
        )

        y = int(ys[i])
        x = int(xs[i])

        spanning[
            y,
            : x + 1,
        ] = True

    # Right edge.
    if not np.any(
        spanning[:, -1]
    ):
        ys, xs = np.where(
            spanning
        )

        i = int(
            np.argmax(xs)
        )

        y = int(ys[i])
        x = int(xs[i])

        spanning[
            y,
            x:,
        ] = True

    # Top edge.
    if not np.any(
        spanning[0, :]
    ):
        ys, xs = np.where(
            spanning
        )

        i = int(
            np.argmin(ys)
        )

        y = int(ys[i])
        x = int(xs[i])

        spanning[
            : y + 1,
            x,
        ] = True

    # Bottom edge.
    if not np.any(
        spanning[-1, :]
    ):
        ys, xs = np.where(
            spanning
        )

        i = int(
            np.argmax(ys)
        )

        y = int(ys[i])
        x = int(xs[i])

        spanning[
            y:,
            x,
        ] = True

    return _connect_all_4_components(
        spanning,
        rng,
    )


# -----------------------------------------------------------------------------
# Stochastic wall construction
# -----------------------------------------------------------------------------
def _jittered_sites(
    rng: np.random.Generator,
    size: int,
    num_sites: int,
) -> np.ndarray:
    """Generate approximately uniform but stochastic 2-D cellular sites."""
    side = int(
        np.ceil(
            np.sqrt(num_sites)
        )
    )

    cell = (
        float(size)
        / float(side)
    )

    candidates = np.empty(
        (
            side * side,
            2,
        ),
        dtype=np.float64,
    )

    k = 0

    for iy in range(side):
        for ix in range(side):
            candidates[
                k,
                0,
            ] = (
                iy
                + rng.uniform(
                    SITE_JITTER_MIN,
                    SITE_JITTER_MAX,
                )
            ) * cell

            candidates[
                k,
                1,
            ] = (
                ix
                + rng.uniform(
                    SITE_JITTER_MIN,
                    SITE_JITTER_MAX,
                )
            ) * cell

            k += 1

    selection = rng.choice(
        candidates.shape[0],
        size=num_sites,
        replace=False,
    )

    return candidates[
        selection
    ]


def _smooth_warp_field(
    rng: np.random.Generator,
    size: int,
) -> Tuple[
    np.ndarray,
    np.ndarray,
]:
    """Generate smooth y/x coordinate perturbations in pixel units."""
    dy = ndi.gaussian_filter(
        rng.standard_normal(
            (size, size)
        ),
        sigma=WARP_SIGMA,
        mode="reflect",
    )

    dx = ndi.gaussian_filter(
        rng.standard_normal(
            (size, size)
        ),
        sigma=WARP_SIGMA,
        mode="reflect",
    )

    dy *= (
        WARP_AMPLITUDE
        / (
            float(dy.std())
            + 1.0e-12
        )
    )

    dx *= (
        WARP_AMPLITUDE
        / (
            float(dx.std())
            + 1.0e-12
        )
    )

    return dy, dx


def _rasterized_cell_walls(
    rng: np.random.Generator,
    size: int = IMAGE_SIZE,
    num_sites: int = NUM_SITES,
) -> np.ndarray:
    """
    Build a warped Voronoi-like cellular wall mask.

    Both pixels adjacent to a nearest-site label change are marked.
    """
    sites = _jittered_sites(
        rng,
        size=size,
        num_sites=num_sites,
    )

    dy, dx = _smooth_warp_field(
        rng,
        size=size,
    )

    yy, xx = np.mgrid[
        0:size,
        0:size,
    ]

    queries = np.column_stack(
        (
            (
                yy
                + dy
            ).ravel(),
            (
                xx
                + dx
            ).ravel(),
        )
    )

    tree = cKDTree(
        sites
    )

    nearest_site = tree.query(
        queries,
        k=1,
    )[1].reshape(
        size,
        size,
    )

    walls = np.zeros(
        (
            size,
            size,
        ),
        dtype=bool,
    )

    horizontal_change = (
        nearest_site[:, 1:]
        != nearest_site[:, :-1]
    )

    walls[:, 1:] |= (
        horizontal_change
    )

    walls[:, :-1] |= (
        horizontal_change
    )

    vertical_change = (
        nearest_site[1:, :]
        != nearest_site[:-1, :]
    )

    walls[1:, :] |= (
        vertical_change
    )

    walls[:-1, :] |= (
        vertical_change
    )

    return walls


def build_connected_wall_skeleton(
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Construct the connected, boundary-spanning seed network for wall growth.

    One four-neighbour closing suppresses grid-scale notches. A one-pixel
    four-neighbour dilation is then used only when it fits inside the exact
    final solid-pixel budget.
    """
    walls = _rasterized_cell_walls(
        rng
    )

    walls = ndi.binary_closing(
        walls,
        structure=STRUCTURE_4,
        iterations=1,
    )

    walls = _connect_all_4_components(
        walls,
        rng,
    )

    walls = _force_boundary_spanning(
        walls,
        rng,
    )

    target_pixels = int(
        round(
            TARGET_SOLID_FRACTION
            * IMAGE_SIZE
            * IMAGE_SIZE
        )
    )

    if (
        INITIAL_WALL_THICKENING
        > 0
    ):
        thickened = ndi.binary_dilation(
            walls,
            structure=STRUCTURE_4,
            iterations=INITIAL_WALL_THICKENING,
        )

        if (
            int(
                thickened.sum()
            )
            <= target_pixels
        ):
            walls = thickened

    return walls


# -----------------------------------------------------------------------------
# Connected variable-width growth
# -----------------------------------------------------------------------------
def _make_growth_score(
    rng: np.random.Generator,
    skeleton: np.ndarray,
) -> np.ndarray:
    """
    Construct the priority field used during connected growth.

    Lower values are filled first. Distance from the connected wall network
    controls nominal thickness. A smooth multiplicative random field creates
    local strut-width variation.
    """
    smooth = ndi.gaussian_filter(
        rng.standard_normal(
            skeleton.shape
        ),
        sigma=WIDTH_NOISE_SIGMA,
        mode="reflect",
    )

    smooth = (
        smooth
        - float(
            smooth.mean()
        )
    ) / (
        float(
            smooth.std()
        )
        + 1.0e-12
    )

    width_factor = np.exp(
        WIDTH_NOISE_AMPLITUDE
        * np.clip(
            smooth,
            -2.5,
            2.5,
        )
    )

    distance = (
        ndi.distance_transform_edt(
            ~skeleton
        )
    )

    score = (
        distance
        / width_factor
    )

    score += (
        FRONTIER_JITTER
        * rng.random(
            skeleton.shape
        )
    )

    return score


def connected_strut_growth(
    rng: np.random.Generator,
    skeleton: np.ndarray,
    target_pixels: int,
) -> np.ndarray:
    """
    Grow a single 4-connected solid until exactly target_pixels are present.

    Every new solid pixel is selected from the current 4-neighbour frontier.
    Therefore no disconnected solid island can be introduced.
    """
    solid = np.asarray(
        skeleton,
        dtype=bool,
    ).copy()

    height, width = (
        solid.shape
    )

    initial_pixels = int(
        solid.sum()
    )

    if (
        initial_pixels
        > target_pixels
    ):
        raise RuntimeError(
            "Initial connected wall network exceeds requested "
            "solid fraction. Reduce the wall density or "
            "initial thickening."
        )

    if (
        initial_pixels
        == target_pixels
    ):
        return solid

    score = _make_growth_score(
        rng,
        solid,
    )

    # True means either already solid or already inserted in the frontier.
    seen = solid.copy()

    frontier: list[
        tuple[
            float,
            int,
            int,
        ]
    ] = []

    ys, xs = np.where(
        solid
    )

    for y, x in zip(
        ys.tolist(),
        xs.tolist(),
    ):
        if (
            y > 0
            and not seen[
                y - 1,
                x,
            ]
        ):
            seen[
                y - 1,
                x,
            ] = True

            heapq.heappush(
                frontier,
                (
                    float(
                        score[
                            y - 1,
                            x,
                        ]
                    ),
                    y - 1,
                    x,
                ),
            )

        if (
            y + 1 < height
            and not seen[
                y + 1,
                x,
            ]
        ):
            seen[
                y + 1,
                x,
            ] = True

            heapq.heappush(
                frontier,
                (
                    float(
                        score[
                            y + 1,
                            x,
                        ]
                    ),
                    y + 1,
                    x,
                ),
            )

        if (
            x > 0
            and not seen[
                y,
                x - 1,
            ]
        ):
            seen[
                y,
                x - 1,
            ] = True

            heapq.heappush(
                frontier,
                (
                    float(
                        score[
                            y,
                            x - 1,
                        ]
                    ),
                    y,
                    x - 1,
                ),
            )

        if (
            x + 1 < width
            and not seen[
                y,
                x + 1,
            ]
        ):
            seen[
                y,
                x + 1,
            ] = True

            heapq.heappush(
                frontier,
                (
                    float(
                        score[
                            y,
                            x + 1,
                        ]
                    ),
                    y,
                    x + 1,
                ),
            )

    solid_count = (
        initial_pixels
    )

    while (
        solid_count
        < target_pixels
    ):
        if not frontier:
            raise RuntimeError(
                "Connected growth frontier became empty before "
                "reaching the target solid fraction."
            )

        _, y, x = (
            heapq.heappop(
                frontier
            )
        )

        solid[
            y,
            x,
        ] = True

        solid_count += 1

        if (
            y > 0
            and not seen[
                y - 1,
                x,
            ]
        ):
            seen[
                y - 1,
                x,
            ] = True

            heapq.heappush(
                frontier,
                (
                    float(
                        score[
                            y - 1,
                            x,
                        ]
                    ),
                    y - 1,
                    x,
                ),
            )

        if (
            y + 1 < height
            and not seen[
                y + 1,
                x,
            ]
        ):
            seen[
                y + 1,
                x,
            ] = True

            heapq.heappush(
                frontier,
                (
                    float(
                        score[
                            y + 1,
                            x,
                        ]
                    ),
                    y + 1,
                    x,
                ),
            )

        if (
            x > 0
            and not seen[
                y,
                x - 1,
            ]
        ):
            seen[
                y,
                x - 1,
            ] = True

            heapq.heappush(
                frontier,
                (
                    float(
                        score[
                            y,
                            x - 1,
                        ]
                    ),
                    y,
                    x - 1,
                ),
            )

        if (
            x + 1 < width
            and not seen[
                y,
                x + 1,
            ]
        ):
            seen[
                y,
                x + 1,
            ] = True

            heapq.heappush(
                frontier,
                (
                    float(
                        score[
                            y,
                            x + 1,
                        ]
                    ),
                    y,
                    x + 1,
                ),
            )

    return solid


# -----------------------------------------------------------------------------
# Engineering validity checks
# -----------------------------------------------------------------------------
def _percolates_left_right(
    solid: np.ndarray,
) -> bool:
    labels, _ = ndi.label(
        solid,
        structure=STRUCTURE_4,
    )

    left_labels = np.unique(
        labels[:, 0]
    )

    right_labels = np.unique(
        labels[:, -1]
    )

    common = np.intersect1d(
        left_labels,
        right_labels,
        assume_unique=False,
    )

    return bool(
        np.any(
            common > 0
        )
    )


def _percolates_top_bottom(
    solid: np.ndarray,
) -> bool:
    labels, _ = ndi.label(
        solid,
        structure=STRUCTURE_4,
    )

    top_labels = np.unique(
        labels[0, :]
    )

    bottom_labels = np.unique(
        labels[-1, :]
    )

    common = np.intersect1d(
        top_labels,
        bottom_labels,
        assume_unique=False,
    )

    return bool(
        np.any(
            common > 0
        )
    )


def validate_engineering_rule(
    array: np.ndarray,
) -> Tuple[
    int,
    bool,
    bool,
]:
    """
    Return (component_count, Px, Py).

    Raise RuntimeError if any required engineering-validity rule is violated.
    """
    if (
        array.dtype
        != np.uint8
    ):
        raise RuntimeError(
            f"Generated array dtype is "
            f"{array.dtype}, not uint8."
        )

    if (
        array.shape
        != (
            IMAGE_SIZE,
            IMAGE_SIZE,
        )
    ):
        raise RuntimeError(
            f"Generated array has unexpected "
            f"shape {array.shape}."
        )

    if not np.all(
        (array == 0)
        | (array == 1)
    ):
        raise RuntimeError(
            "Generated array contains values other than 0 and 1."
        )

    solid = array.astype(
        bool
    )

    _, component_count = ndi.label(
        solid,
        structure=STRUCTURE_4,
    )

    px = _percolates_left_right(
        solid
    )

    py = _percolates_top_bottom(
        solid
    )

    if (
        component_count != 1
        or not px
        or not py
    ):
        raise RuntimeError(
            "Engineering validity failure: "
            f"component_count="
            f"{component_count}, "
            f"Px={int(px)}, "
            f"Py={int(py)}"
        )

    return (
        int(component_count),
        bool(px),
        bool(py),
    )


# -----------------------------------------------------------------------------
# Public generator / output
# -----------------------------------------------------------------------------
def generate_microstructure(
    seed: int,
) -> np.ndarray:
    """
    Generate one stochastic 256 x 256 uint8 microstructure.

    Solid is 1 and void is 0.
    """
    if seed < 0:
        raise ValueError(
            "Seed must be a non-negative integer."
        )

    rng = np.random.default_rng(
        seed
    )

    target_pixels = int(
        round(
            TARGET_SOLID_FRACTION
            * IMAGE_SIZE
            * IMAGE_SIZE
        )
    )

    connected_wall_skeleton = (
        build_connected_wall_skeleton(
            rng
        )
    )

    solid = connected_strut_growth(
        rng=rng,
        skeleton=connected_wall_skeleton,
        target_pixels=target_pixels,
    )

    array = solid.astype(
        np.uint8,
        copy=False,
    )

    validate_engineering_rule(
        array
    )

    return array


def save_microstructure(
    array: np.ndarray,
    seed: int,
    output_dir: Path,
) -> None:
    """
    Save the exact 0/1 array as NPY and an equivalent black/white PNG.
    """
    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stem = (
        f"microstructure_seed_{seed}"
    )

    npy_path = (
        output_dir
        / f"{stem}.npy"
    )

    png_path = (
        output_dir
        / f"{stem}.png"
    )

    np.save(
        npy_path,
        array.astype(
            np.uint8,
            copy=False,
        ),
        allow_pickle=False,
    )

    png_array = (
        array
        * np.uint8(255)
    ).astype(
        np.uint8,
        copy=False,
    )

    Image.fromarray(
        png_array,
        mode="L",
    ).save(
        png_path
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate connected stochastic binary "
            "mechanical-metamaterial microstructures."
        )
    )

    parser.add_argument(
        "--seed-start",
        type=int,
        default=0,
        help=(
            "First integer seed "
            "(default: 0)."
        ),
    )

    parser.add_argument(
        "--num-samples",
        type=int,
        default=20,
        help=(
            "Number of consecutive seeds "
            "to generate (default: 20)."
        ),
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "generated_microstructures"
        ),
        help=(
            "Directory for PNG and NPY outputs."
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if (
        args.seed_start
        < 0
    ):
        raise ValueError(
            "--seed-start must be non-negative."
        )

    if (
        args.num_samples
        < 0
    ):
        raise ValueError(
            "--num-samples must be non-negative."
        )

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    for seed in range(
        args.seed_start,
        args.seed_start
        + args.num_samples,
    ):
        array = (
            generate_microstructure(
                seed
            )
        )

        (
            component_count,
            px,
            py,
        ) = validate_engineering_rule(
            array
        )

        save_microstructure(
            array,
            seed,
            args.output_dir,
        )

        print(
            f"seed={seed} "
            f"solid_fraction="
            f"{array.mean():.6f} "
            f"component_count="
            f"{component_count} "
            f"Px={int(px)} "
            f"Py={int(py)}"
        )


if __name__ == "__main__":
    main()
