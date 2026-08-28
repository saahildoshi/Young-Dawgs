#!/usr/bin/env python3
"""
Procedural generator for 2-D two-phase disordered mechanical metamaterials.

Output convention
-----------------
solid = 1 (white in PNG)
void  = 0 (black in PNG)

Algorithm
---------
1. Place pore generators on a jittered, randomly thinned lattice, including
   "ghost" generators just outside the image. This fixes the dominant feature
   scale while preserving sample-to-sample disorder.

2. Build a weighted p-norm Voronoi-like partition in smoothly warped
   coordinates. The smooth warp bends cell walls; p > 2 and mild x/y
   anisotropy give the network a weak directional, vein-like organization.

3. Convert 4-neighbor label changes into a wall skeleton and thicken it with
   a spatially varying half-width. This creates a load-bearing solid network
   with controlled strut thickness and avoids one-pixel branches.

4. Fill sub-resolution void specks, retain only the largest 4-connected solid
   component, and verify that the same solid network spans left-to-right and
   top-to-bottom. If a rare candidate fails, a new candidate is drawn from
   the same seeded random stream.

Main adjustable parameters
--------------------------
CELL_SIZE          : dominant pore / feature scale
KEEP_PROB          : density of pore generators; lower -> larger/more varied pores
LP_POWER           : directional character; 2 is Euclidean, >2 more axis-organized
ANISO_X, ANISO_Y   : global x/y anisotropy
WARP_AMPLITUDE     : wall tortuosity / curvature
WARP_SIGMA_X/Y     : spatial scale of the wall warp
BASE_HALF_WIDTH    : mean strut half-width
WIDTH_JITTER       : local strut-thickness variation
MIN_VOID_AREA      : fills tiny void specks below this area

Dependencies: numpy, scipy, Pillow.

The script is fully procedural and does not read any reference image, external
dataset, pretrained model, API, or internet resource.
"""

from pathlib import Path
import hashlib

import numpy as np
from scipy import ndimage as ndi
from PIL import Image


# ============================================================================
# User-adjustable parameters
# ============================================================================

SIZE = 256
N_SAMPLES = 20
OUTPUT_DIR = Path("generated_microstructures")

# Dominant pore / feature scale.
CELL_SIZE = 24.0

# Probability that a generator site from the jittered lattice is retained.
# Lower values produce fewer, larger, more variable pores.
KEEP_PROB = 0.82

# p-norm exponent. Values above 2 introduce mild axis-organized character
# without producing a perfectly rectilinear network.
LP_POWER = 3.2

# Global directional anisotropy.
ANISO_X = 1.10
ANISO_Y = 0.95

# Sample-to-sample coherent shear.
SHEAR_STD = 0.06

# Smooth coordinate distortion controlling wall curvature/tortuosity.
WARP_AMPLITUDE = 4.0
WARP_SIGMA_X = 18.0
WARP_SIGMA_Y = 12.0

# Variation in effective local pore size.
SEED_WEIGHT_SCALE = 0.20

# Solid strut thickness.
# Primitive interfaces already occupy roughly two raster pixels; this
# additional distance threshold produces struts several pixels thick.
BASE_HALF_WIDTH = 2.45
WIDTH_JITTER = 0.45
WIDTH_NOISE_SIGMA = 2.5
WIDTH_NOISE_CLIP = 1.3

# Remove very small void defects.
MIN_VOID_AREA = 35

# Number of candidates allowed for a given random seed if spanning validation
# happens to fail.
MAX_ATTEMPTS = 12

# Number of pore generators processed simultaneously during distance
# evaluation. Lower values use less memory.
DISTANCE_CHUNK = 12

# Explicit 4-neighbor connectivity.
FOUR_CONNECTED = ndi.generate_binary_structure(2, 1)


# ============================================================================
# Helper functions
# ============================================================================

def _standardize(a: np.ndarray) -> np.ndarray:
    """Return array with zero mean and unit standard deviation."""
    return (a - a.mean()) / (a.std() + 1.0e-12)


def _make_generators(
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """
    Construct stochastic pore generators.

    Generators start from a regular lattice but are:
      - randomly removed,
      - independently jittered,
      - extended one cell outside the image.

    The outside "ghost" generators allow partition boundaries to intersect
    image edges naturally rather than forcing a special artificial frame.
    """
    c = CELL_SIZE

    xs = np.arange(-0.5 * c, n + c, c)
    ys = np.arange(-0.5 * c, n + c, c)

    points = []

    for y0 in ys:
        for x0 in xs:
            if rng.random() < KEEP_PROB:
                x = x0 + rng.uniform(-0.42, 0.42) * c
                y = y0 + rng.uniform(-0.42, 0.42) * c
                points.append((x, y))

    if len(points) < 16:
        raise RuntimeError(
            "Too few pore generators. Increase KEEP_PROB."
        )

    return np.asarray(points, dtype=np.float64)


def _partition_labels(
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """
    Generate a warped weighted p-norm Voronoi-like partition.

    Each pixel is assigned to the pore generator with the smallest distorted
    p-norm distance. Smooth coordinate warping produces curved irregular
    interfaces while retaining a controlled pore scale.
    """
    points = _make_generators(rng, n)
    n_points = len(points)

    # ----------------------------------------------------------------------
    # Smooth stochastic coordinate warp
    # ----------------------------------------------------------------------

    raw_x = rng.standard_normal((n, n))
    raw_y = rng.standard_normal((n, n))

    dx = ndi.gaussian_filter(
        raw_x,
        sigma=(WARP_SIGMA_Y, WARP_SIGMA_X),
        mode="reflect",
    )

    dy = ndi.gaussian_filter(
        raw_y,
        sigma=(WARP_SIGMA_X, WARP_SIGMA_Y),
        mode="reflect",
    )

    dx = _standardize(dx) * WARP_AMPLITUDE
    dy = _standardize(dy) * WARP_AMPLITUDE

    yy, xx = np.mgrid[0:n, 0:n]

    xw = xx + dx
    yw = yy + dy

    # Small coherent shear varies among samples but keeps the general
    # directional organization similar.
    shear = rng.normal(0.0, SHEAR_STD)
    xw = xw + shear * (yw - 0.5 * n)

    # ----------------------------------------------------------------------
    # Random cell-size weights
    # ----------------------------------------------------------------------

    weights = rng.normal(
        loc=0.0,
        scale=1.0,
        size=n_points,
    )

    weight_unit = (
        CELL_SIZE * SEED_WEIGHT_SCALE
    ) ** LP_POWER

    # ----------------------------------------------------------------------
    # Assign each pixel to its closest distorted generator
    # ----------------------------------------------------------------------

    best_distance = np.full(
        (n, n),
        np.inf,
        dtype=np.float64,
    )

    labels = np.full(
        (n, n),
        -1,
        dtype=np.int32,
    )

    for start in range(
        0,
        n_points,
        DISTANCE_CHUNK,
    ):
        stop = min(
            start + DISTANCE_CHUNK,
            n_points,
        )

        px = points[
            start:stop,
            0,
            None,
            None,
        ]

        py = points[
            start:stop,
            1,
            None,
            None,
        ]

        # Superelliptic / p-norm distance.
        d = (
            np.abs(
                (xw[None, :, :] - px) / ANISO_X
            ) ** LP_POWER
            +
            np.abs(
                (yw[None, :, :] - py) / ANISO_Y
            ) ** LP_POWER
        )

        # Add a small generator-specific weight so neighboring pores are not
        # all identical in size.
        d += (
            weights[
                start:stop,
                None,
                None,
            ]
            * weight_unit
        )

        local_index = np.argmin(
            d,
            axis=0,
        )

        local_best = np.take_along_axis(
            d,
            local_index[
                None,
                :,
                :,
            ],
            axis=0,
        )[0]

        take = local_best < best_distance

        best_distance[take] = local_best[take]

        labels[take] = (
            start
            + local_index[take]
        )

    return labels


def _walls_from_labels(
    labels: np.ndarray,
) -> np.ndarray:
    """
    Convert partition interfaces into a binary primitive solid wall.

    Both pixels neighboring each 4-neighbor label transition are marked.
    This provides a robust rasterized interface before wall thickening.
    """
    wall = np.zeros_like(
        labels,
        dtype=bool,
    )

    # Vertical interfaces between left/right neighboring pixels.
    different = (
        labels[:, 1:]
        != labels[:, :-1]
    )

    wall[:, 1:] |= different
    wall[:, :-1] |= different

    # Horizontal interfaces between upper/lower neighboring pixels.
    different = (
        labels[1:, :]
        != labels[:-1, :]
    )

    wall[1:, :] |= different
    wall[:-1, :] |= different

    return wall


def _fill_small_voids(
    solid: np.ndarray,
) -> np.ndarray:
    """
    Fill only tiny 4-connected void regions.

    This suppresses sub-resolution pore defects without globally smoothing
    the structure.
    """
    void_labels, n_void = ndi.label(
        ~solid,
        structure=FOUR_CONNECTED,
    )

    if n_void == 0:
        return solid

    areas = np.bincount(
        void_labels.ravel()
    )

    fill = np.zeros(
        n_void + 1,
        dtype=bool,
    )

    fill[1:] = (
        areas[1:]
        < MIN_VOID_AREA
    )

    return (
        solid
        | fill[void_labels]
    )


def _largest_4_connected_component(
    mask: np.ndarray,
) -> np.ndarray:
    """
    Retain only the largest 4-connected solid component.

    This removes isolated solid islands or detached fragments entirely.
    """
    labels, n_components = ndi.label(
        mask,
        structure=FOUR_CONNECTED,
    )

    if n_components == 0:
        return np.zeros_like(
            mask,
            dtype=bool,
        )

    areas = np.bincount(
        labels.ravel()
    )

    # Ignore background.
    areas[0] = 0

    main_component = int(
        np.argmax(areas)
    )

    return (
        labels
        == main_component
    )


def _spans_both_axes(
    solid: np.ndarray,
) -> bool:
    """
    Test that exactly one 4-connected solid component spans both axes.

    Horizontal spanning:
        component touches both left and right image boundaries.

    Vertical spanning:
        the same component touches both top and bottom boundaries.
    """
    labels, n_components = ndi.label(
        solid,
        structure=FOUR_CONNECTED,
    )

    if n_components != 1:
        return False

    component = 1

    horizontal = (
        np.any(
            labels[:, 0]
            == component
        )
        and
        np.any(
            labels[:, -1]
            == component
        )
    )

    vertical = (
        np.any(
            labels[0, :]
            == component
        )
        and
        np.any(
            labels[-1, :]
            == component
        )
    )

    return bool(
        horizontal
        and vertical
    )


def _candidate(
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """Generate one candidate solid network."""
    labels = _partition_labels(
        rng,
        n,
    )

    primitive_wall = _walls_from_labels(
        labels
    )

    # Euclidean distance from every pixel to the primitive partition wall.
    dist = ndi.distance_transform_edt(
        ~primitive_wall
    )

    # ----------------------------------------------------------------------
    # Spatially varying strut thickness
    # ----------------------------------------------------------------------

    width_noise = ndi.gaussian_filter(
        rng.standard_normal((n, n)),
        sigma=WIDTH_NOISE_SIGMA,
        mode="reflect",
    )

    width_noise = _standardize(
        width_noise
    )

    width_noise = np.clip(
        width_noise,
        -WIDTH_NOISE_CLIP,
        WIDTH_NOISE_CLIP,
    )

    local_half_width = (
        BASE_HALF_WIDTH
        + WIDTH_JITTER
        * width_noise
    )

    solid = (
        dist
        <= local_half_width
    )

    # Remove very small void defects.
    solid = _fill_small_voids(
        solid
    )

    # Enforce one dominant 4-connected network and remove all solid islands.
    solid = _largest_4_connected_component(
        solid
    )

    return solid


def generate_microstructure(
    seed: int,
    n: int = SIZE,
) -> np.ndarray:
    """
    Generate one validated binary microstructure.

    The RNG is initialized directly with the requested seed.

    Any rare retry simply continues drawing from that same seeded random
    stream, so the realizations are still controlled by seeds 0 through 19.
    """
    rng = np.random.default_rng(
        seed
    )

    for _ in range(
        MAX_ATTEMPTS
    ):
        solid = _candidate(
            rng,
            n,
        )

        if _spans_both_axes(
            solid
        ):
            # Confirm the final network consists of exactly one
            # 4-connected solid component.
            _, n_components = ndi.label(
                solid,
                structure=FOUR_CONNECTED,
            )

            if n_components == 1:
                return solid.astype(
                    np.uint8
                )

    raise RuntimeError(
        "Could not produce a spanning "
        f"4-connected network for seed {seed}. "
        "Try increasing KEEP_PROB or BASE_HALF_WIDTH."
    )


def save_sample(
    arr: np.ndarray,
    seed: int,
    out_dir: Path,
) -> None:
    """
    Save a realization in both required formats.

    NPY:
        uint8 values exactly 0 and 1.

    PNG:
        void  = black, 0
        solid = white, 255
    """
    stem = (
        f"sample_seed_{seed:02d}"
    )

    np.save(
        out_dir / f"{stem}.npy",
        arr.astype(
            np.uint8,
            copy=False,
        ),
    )

    png_array = (
        arr * 255
    ).astype(
        np.uint8
    )

    image = Image.fromarray(
        png_array,
        mode="L",
    )

    image.save(
        out_dir / f"{stem}.png"
    )


def pore_count(
    arr: np.ndarray,
) -> int:
    """
    Count 4-connected void regions.

    Used only for printed diagnostics; it does not alter the structure.
    """
    _, n = ndi.label(
        arr == 0,
        structure=FOUR_CONNECTED,
    )

    return int(n)


# ============================================================================
# Main program
# ============================================================================

def main() -> None:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Ensure all twenty realizations are genuinely distinct.
    seen_hashes = set()

    # Exactly the required random seeds: 0 through 19.
    for seed in range(
        N_SAMPLES
    ):
        arr = generate_microstructure(
            seed,
            SIZE,
        )

        # ------------------------------------------------------------------
        # Safety / invariant checks
        # ------------------------------------------------------------------

        if arr.shape != (
            SIZE,
            SIZE,
        ):
            raise AssertionError(
                "Unexpected array size."
            )

        if arr.dtype != np.uint8:
            raise AssertionError(
                "Output must have dtype uint8."
            )

        if not np.all(
            (arr == 0)
            | (arr == 1)
        ):
            raise AssertionError(
                "Output is not binary."
            )

        if not _spans_both_axes(
            arr.astype(bool)
        ):
            raise AssertionError(
                "Solid network does not "
                "span both axes."
            )

        digest = hashlib.sha256(
            arr.tobytes()
        ).hexdigest()

        if digest in seen_hashes:
            raise RuntimeError(
                "Duplicate realization "
                f"detected at seed {seed}."
            )

        seen_hashes.add(
            digest
        )

        # ------------------------------------------------------------------
        # Save PNG and NPY
        # ------------------------------------------------------------------

        save_sample(
            arr,
            seed,
            OUTPUT_DIR,
        )

        print(
            f"seed={seed:02d}  "
            f"solid_fraction={arr.mean():.3f}  "
            f"void_regions={pore_count(arr):3d}  "
            f"saved={OUTPUT_DIR / ('sample_seed_' + format(seed, '02d'))}"
        )


if __name__ == "__main__":
    main()