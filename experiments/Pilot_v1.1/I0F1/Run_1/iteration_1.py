#!/usr/bin/env python3
"""
Procedural generator for binary cellular microstructures.

Revision 1
----------
The main correction is that the connected inter-cellular channel network is
treated as SOLID, while the enclosed cell interiors are VOID.  This produces
the requested low-volume-fraction, highly connected solid skeleton rather than
a collection of disconnected solid islands.

Algorithm
---------
1. Place random nuclei in a periodic 256x256 domain.
2. Build a Voronoi-like tessellation from the nuclei.
3. Smoothly warp the sampling coordinates with two-scale Gaussian random
   displacement fields so cell boundaries are irregular and tortuous.
4. Detect the 4-neighbour interfaces between neighboring cells.
5. Compute Euclidean distance from every pixel to the interface network.
6. Give the solid struts a smoothly varying local half-width.
7. Adapt the mean half-width by bisection so each realization stays close to
   the requested solid-volume fraction while retaining stochastic geometry.
8. Treat the thickened interface network as SOLID=1 and cell interiors as
   VOID=0.
9. Verify 4-connected horizontal and vertical percolation.  A very small
   deterministic fallback connector is added only if a realization fails to
   span one of the four image borders.

The reference image is never read, embedded, traced, or accessed at runtime.

Output convention
-----------------
    solid = 1
    void  = 0

Twenty independent realizations are generated with random seeds 0 through 19.
Each realization is saved as both PNG and NPY.

Dependencies
------------
    numpy
    scipy
    Pillow

Important adjustable parameters
-------------------------------
BASE_NUCLEI
    Controls characteristic pore size.  Larger values create smaller pores.

COARSE_WARP_SIGMA / COARSE_WARP_AMPLITUDE
    Control long-wavelength curvature of the cellular interfaces.

FINE_WARP_SIGMA / FINE_WARP_AMPLITUDE
    Control shorter-scale tortuosity.  Increasing FINE_WARP_AMPLITUDE tends
    to reduce long straight solid paths.

WIDTH_JITTER / WIDTH_NOISE_SIGMA
    Control local strut-width variability.  The larger width jitter used in
    this revision deliberately produces a population of approximately
    four-pixel-thick narrow struts.

TARGET_SOLID_FRACTION
    Mean requested solid fraction.  A small seed-dependent fluctuation is
    added so realizations do not all have exactly the same volume fraction.

SOLID_FRACTION_STD
    Controls the sample-to-sample fluctuation in volume fraction.
"""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import (
    distance_transform_edt,
    gaussian_filter,
    generate_binary_structure,
    label,
)
from scipy.spatial import cKDTree


# ============================================================================
# Output configuration
# ============================================================================

SIZE = 256
N_SAMPLES = 20
OUTPUT_DIR = Path("generated_microstructures")


# ============================================================================
# Morphology parameters
# ============================================================================

# Cell population.  This range gives roughly the desired characteristic
# enclosed-pore scale after the spatial warping.
BASE_NUCLEI = 68
NUCLEI_JITTER = 3

# Large-scale interface distortion.
COARSE_WARP_SIGMA = 14.0
COARSE_WARP_AMPLITUDE = 3.5

# Shorter-scale interface distortion.  Slightly stronger than the first
# version to decrease overly long/straight lineal paths.
FINE_WARP_SIGMA = 4.0
FINE_WARP_AMPLITUDE = 1.15

# Spatial variation in strut width.
WIDTH_NOISE_SIGMA = 22.0
WIDTH_JITTER = 1.00

# Local half-width limits, in pixels.
MIN_HALF_WIDTH = 0.60
MAX_HALF_WIDTH = 4.60

# The generator adjusts its scalar mean half-width inside this interval.
WIDTH_SEARCH_MIN = 1.50
WIDTH_SEARCH_MAX = 4.00
WIDTH_BISECTION_STEPS = 24

# Target phase fraction.  The development target is approximately 0.395.
TARGET_SOLID_FRACTION = 0.3947

# Retain a small natural realization-to-realization variation.
SOLID_FRACTION_STD = 0.0030
MIN_TARGET_SOLID_FRACTION = 0.387
MAX_TARGET_SOLID_FRACTION = 0.403


# ============================================================================
# Random-field utilities
# ============================================================================

def normalized_smooth_noise(rng, shape, sigma):
    """
    Return periodic Gaussian-smoothed random noise with mean 0 and std 1.
    """
    field = rng.standard_normal(shape)
    field = gaussian_filter(field, sigma=sigma, mode="wrap")

    field -= field.mean()
    std = field.std()

    if std < 1.0e-12:
        return np.zeros(shape, dtype=np.float64)

    return field / std


def make_warp_field(rng, shape):
    """
    Generate two-scale smooth x/y displacement fields.
    """
    coarse_y = normalized_smooth_noise(
        rng, shape, COARSE_WARP_SIGMA
    )
    coarse_x = normalized_smooth_noise(
        rng, shape, COARSE_WARP_SIGMA
    )

    fine_y = normalized_smooth_noise(
        rng, shape, FINE_WARP_SIGMA
    )
    fine_x = normalized_smooth_noise(
        rng, shape, FINE_WARP_SIGMA
    )

    dy = (
        COARSE_WARP_AMPLITUDE * coarse_y
        + FINE_WARP_AMPLITUDE * fine_y
    )

    dx = (
        COARSE_WARP_AMPLITUDE * coarse_x
        + FINE_WARP_AMPLITUDE * fine_x
    )

    return dy, dx


# ============================================================================
# Periodic geometric utilities
# ============================================================================

def periodic_distance_to_mask(mask):
    """
    Euclidean distance to a boolean mask using periodic boundary conditions.

    A 3x3 tiling is used and only the center tile is retained.
    """
    h, w = mask.shape

    tiled = np.tile(mask, (3, 3))
    tiled_distance = distance_transform_edt(~tiled)

    return tiled_distance[h:2 * h, w:2 * w]


def build_warped_cell_interfaces(rng):
    """
    Construct an irregular periodic Voronoi-like interface network.

    Returns
    -------
    interface : (SIZE, SIZE) bool ndarray
        Pixels adjacent to a change in nearest-cell label.
    """
    shape = (SIZE, SIZE)

    n_nuclei = BASE_NUCLEI + int(
        rng.integers(-NUCLEI_JITTER, NUCLEI_JITTER + 1)
    )

    nuclei = rng.uniform(
        0.0,
        float(SIZE),
        size=(n_nuclei, 2),
    )

    yy, xx = np.indices(shape, dtype=np.float64)

    dy, dx = make_warp_field(rng, shape)

    warped_y = np.mod(yy + dy, SIZE)
    warped_x = np.mod(xx + dx, SIZE)

    query_points = np.column_stack(
        (
            warped_y.ravel(),
            warped_x.ravel(),
        )
    )

    # Periodic nearest-neighbour assignment.
    tree = cKDTree(
        nuclei,
        boxsize=(SIZE, SIZE),
    )

    _, labels = tree.query(
        query_points,
        k=1,
    )

    labels = labels.reshape(shape)

    # Mark both sides of every 4-neighbour cell boundary.  This produces a
    # connected digital representation of the tessellation interfaces.
    interface = np.zeros(shape, dtype=bool)

    interface |= labels != np.roll(labels, 1, axis=0)
    interface |= labels != np.roll(labels, -1, axis=0)
    interface |= labels != np.roll(labels, 1, axis=1)
    interface |= labels != np.roll(labels, -1, axis=1)

    return interface


# ============================================================================
# Connectivity utilities
# ============================================================================

FOUR_CONNECTED = generate_binary_structure(2, 1)


def component_labels(binary):
    """
    4-connected component labels.
    """
    return label(binary.astype(bool), structure=FOUR_CONNECTED)


def largest_component_id(binary):
    """
    Return the label number of the largest 4-connected solid component.
    """
    labels, n_components = component_labels(binary)

    if n_components == 0:
        return labels, 0

    sizes = np.bincount(labels.ravel())
    sizes[0] = 0

    return labels, int(np.argmax(sizes))


def component_touches_all_borders(labels, component_id):
    """
    Test whether one component touches left, right, top, and bottom borders.
    """
    if component_id == 0:
        return False

    left = np.any(labels[:, 0] == component_id)
    right = np.any(labels[:, -1] == component_id)
    top = np.any(labels[0, :] == component_id)
    bottom = np.any(labels[-1, :] == component_id)

    return left and right and top and bottom


def random_manhattan_path(rng, start, end):
    """
    Create a 4-connected stochastic Manhattan path between two pixels.

    This is used only as a rare validity fallback.  The order of horizontal
    and vertical moves is randomized, avoiding a forced long straight line.
    """
    y, x = start
    ey, ex = end

    path = [(y, x)]

    moves = []

    if ey > y:
        moves.extend([(1, 0)] * (ey - y))
    elif ey < y:
        moves.extend([(-1, 0)] * (y - ey))

    if ex > x:
        moves.extend([(0, 1)] * (ex - x))
    elif ex < x:
        moves.extend([(0, -1)] * (x - ex))

    if moves:
        order = rng.permutation(len(moves))

        for i in order:
            dy, dx = moves[i]
            y += dy
            x += dx
            path.append((y, x))

    return path


def connect_component_to_border(binary, component_mask, border, rng):
    """
    Connect the selected solid component to a requested image border.

    The nearest component pixel in the relevant coordinate direction is used,
    so the added path is normally extremely short.
    """
    coords = np.argwhere(component_mask)

    if coords.size == 0:
        return

    if border == "left":
        idx = np.argmin(coords[:, 1])
        start = tuple(coords[idx])
        end = (int(start[0]), 0)

    elif border == "right":
        idx = np.argmax(coords[:, 1])
        start = tuple(coords[idx])
        end = (int(start[0]), SIZE - 1)

    elif border == "top":
        idx = np.argmin(coords[:, 0])
        start = tuple(coords[idx])
        end = (0, int(start[1]))

    elif border == "bottom":
        idx = np.argmax(coords[:, 0])
        start = tuple(coords[idx])
        end = (SIZE - 1, int(start[1]))

    else:
        raise ValueError(f"Unknown border: {border}")

    for y, x in random_manhattan_path(rng, start, end):
        binary[y, x] = True


def enforce_four_connected_spanning_network(binary, rng):
    """
    Ensure the dominant 4-connected solid component spans both image axes.

    For the tessellation-interface construction this normally changes nothing.
    It exists as a deterministic safety net for all requested seeds.
    """
    binary = binary.astype(bool, copy=True)

    for _ in range(3):
        labels, component_id = largest_component_id(binary)

        if component_id == 0:
            # Pathological fallback; not expected for normal parameters.
            binary[SIZE // 2, SIZE // 2] = True
            continue

        if component_touches_all_borders(labels, component_id):
            return binary

        component_mask = labels == component_id

        if not np.any(component_mask[:, 0]):
            connect_component_to_border(
                binary, component_mask, "left", rng
            )

        labels, component_id = largest_component_id(binary)
        component_mask = labels == component_id

        if not np.any(component_mask[:, -1]):
            connect_component_to_border(
                binary, component_mask, "right", rng
            )

        labels, component_id = largest_component_id(binary)
        component_mask = labels == component_id

        if not np.any(component_mask[0, :]):
            connect_component_to_border(
                binary, component_mask, "top", rng
            )

        labels, component_id = largest_component_id(binary)
        component_mask = labels == component_id

        if not np.any(component_mask[-1, :]):
            connect_component_to_border(
                binary, component_mask, "bottom", rng
            )

    return binary


# ============================================================================
# Main procedural generator
# ============================================================================

def generate_microstructure(seed):
    """
    Generate one stochastic 256x256 binary microstructure.

    Returns
    -------
    solid : uint8 ndarray
        Values are exactly
            1 = solid connected strut network
            0 = void cell interiors
    """
    rng = np.random.default_rng(seed)

    shape = (SIZE, SIZE)

    # ----------------------------------------------------------------------
    # 1. Generate a new random warped cellular tessellation.
    # ----------------------------------------------------------------------

    interface = build_warped_cell_interfaces(rng)

    # ----------------------------------------------------------------------
    # 2. Distance from every pixel to the interface network.
    # ----------------------------------------------------------------------

    distance = periodic_distance_to_mask(interface)

    # ----------------------------------------------------------------------
    # 3. Independent smooth field controlling local strut width.
    #
    #    The larger variation compared with revision 0 gives a substantial
    #    population of narrow struts while retaining locally thicker nodes.
    # ----------------------------------------------------------------------

    width_noise = normalized_smooth_noise(
        rng,
        shape,
        WIDTH_NOISE_SIGMA,
    )

    # Seed-dependent but tightly controlled target volume fraction.
    requested_fraction = (
        TARGET_SOLID_FRACTION
        + SOLID_FRACTION_STD * rng.standard_normal()
    )

    requested_fraction = float(
        np.clip(
            requested_fraction,
            MIN_TARGET_SOLID_FRACTION,
            MAX_TARGET_SOLID_FRACTION,
        )
    )

    # ----------------------------------------------------------------------
    # 4. Adapt the mean interface half-width.
    #
    #    Thickened INTERFACES are the SOLID phase.  This is the essential
    #    phase-orientation correction relative to the previous generator.
    # ----------------------------------------------------------------------

    low = WIDTH_SEARCH_MIN
    high = WIDTH_SEARCH_MAX

    solid = None

    for _ in range(WIDTH_BISECTION_STEPS):
        mean_half_width = 0.5 * (low + high)

        local_half_width = np.clip(
            mean_half_width + WIDTH_JITTER * width_noise,
            MIN_HALF_WIDTH,
            MAX_HALF_WIDTH,
        )

        candidate = distance <= local_half_width
        fraction = candidate.mean()

        if fraction < requested_fraction:
            low = mean_half_width
        else:
            high = mean_half_width

        solid = candidate

    # Final threshold at the converged width.
    mean_half_width = 0.5 * (low + high)

    local_half_width = np.clip(
        mean_half_width + WIDTH_JITTER * width_noise,
        MIN_HALF_WIDTH,
        MAX_HALF_WIDTH,
    )

    solid = distance <= local_half_width

    # ----------------------------------------------------------------------
    # 5. Enforce a dominant 4-connected network spanning both axes.
    # ----------------------------------------------------------------------

    solid = enforce_four_connected_spanning_network(
        solid,
        rng,
    )

    return solid.astype(np.uint8)


# ============================================================================
# Validation
# ============================================================================

def validate_sample(array01):
    """
    Check dimensions, phase values, dominance, and 4-connected percolation.
    """
    if array01.shape != (SIZE, SIZE):
        raise RuntimeError(
            f"Wrong output shape: {array01.shape}"
        )

    if array01.dtype != np.uint8:
        raise RuntimeError(
            f"Wrong output dtype: {array01.dtype}"
        )

    if not np.all((array01 == 0) | (array01 == 1)):
        raise RuntimeError(
            "Generated image contains values other than 0 and 1."
        )

    solid = array01.astype(bool)

    labels, component_id = largest_component_id(solid)

    if component_id == 0:
        raise RuntimeError("No solid component was generated.")

    solid_pixels = int(solid.sum())
    largest_pixels = int(
        np.count_nonzero(labels == component_id)
    )

    largest_fraction = largest_pixels / solid_pixels

    left_right = (
        np.any(labels[:, 0] == component_id)
        and np.any(labels[:, -1] == component_id)
    )

    top_bottom = (
        np.any(labels[0, :] == component_id)
        and np.any(labels[-1, :] == component_id)
    )

    if not left_right:
        raise RuntimeError(
            "Dominant solid component does not percolate left-to-right."
        )

    if not top_bottom:
        raise RuntimeError(
            "Dominant solid component does not percolate top-to-bottom."
        )

    return largest_fraction


# ============================================================================
# File output
# ============================================================================

def save_binary_png(array01, filename):
    """
    Save a PNG whose stored palette indices remain exactly 0 and 1.

        palette index 0 = void
        palette index 1 = solid

    Display colors are kept identical to the previous script:
        void  -> white
        solid -> black
    """
    if array01.dtype != np.uint8:
        array01 = array01.astype(np.uint8)

    if not np.all((array01 == 0) | (array01 == 1)):
        raise ValueError(
            "PNG input must contain only binary values 0 and 1."
        )

    image = Image.fromarray(array01, mode="P")

    palette = [
        255, 255, 255,  # index 0: void
        0, 0, 0,        # index 1: solid
    ]

    palette.extend([0, 0, 0] * 254)

    image.putpalette(palette)
    image.save(filename)


# ============================================================================
# Main
# ============================================================================

def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for seed in range(N_SAMPLES):
        solid = generate_microstructure(seed)

        largest_fraction = validate_sample(solid)

        stem = f"microstructure_seed_{seed:02d}"

        npy_path = OUTPUT_DIR / f"{stem}.npy"
        png_path = OUTPUT_DIR / f"{stem}.png"

        # Exact uint8 phase field:
        #   1 = solid
        #   0 = void
        np.save(npy_path, solid)

        save_binary_png(
            solid,
            png_path,
        )

        print(
            f"seed={seed:02d} | "
            f"solid_fraction={solid.mean():.6f} | "
            f"largest_component_fraction={largest_fraction:.6f} | "
            f"{png_path.name} | "
            f"{npy_path.name}"
        )


if __name__ == "__main__":
    main()