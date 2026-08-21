#!/usr/bin/env python3
"""
Revision 3 procedural generator for stochastic binary microstructures.

Output convention
-----------------
    solid = 1
    void  = 0

Twenty independent 256x256 realizations are produced using root seeds 0..19.
Each sample is saved as both PNG and NPY using the same filenames as before.

Algorithm
---------
The generator uses a warped cellular-interface model, with several targeted
changes based on the development metrics:

1. Mildly repulsive ("blue-noise") random nuclei give more uniform pore
   spacing and a stronger medium-range anticorrelation than Poisson Voronoi
   nuclei.
2. A periodic Voronoi-like tessellation is smoothly warped at two spatial
   scales.
3. The cell interfaces form the backbone of the solid phase.
4. Three independent width fields act at long, intermediate, and pixel scales.
   The intermediate/pixel-scale fields create constrictions and irregular
   edges, reducing excessive continuous lineal paths.
5. Junctions receive controlled local thickening.  Combined with the
   constrictions this preserves a ~4 px lower-tail strut thickness while
   maintaining the desired mean strut thickness.
6. Exactly TARGET_MAIN_SOLID_PIXELS are assigned to one 4-connected solid
   network.  The network is explicitly forced to span left-right and
   top-bottom.
7. The target largest-component fraction implies a small amount of solid
   outside the dominant network.  That fraction is generated procedurally as
   several compact, isolated stochastic islands inside sufficiently large
   pores.  This gives the requested dominant-component fraction without
   endangering percolation.
8. A small bank of nearby procedural parameter settings is generated for each
   root seed.  Selection uses ONLY the aggregate target statistics supplied
   with this revision (radial two-point correlation and pore-scale target).
   No reference image or target pixels are read or embedded.

The reference image is never accessed at runtime.

Dependencies
------------
    numpy
    scipy
    Pillow

Adjustable parameters
---------------------
BASE_NUCLEI in CANDIDATE_VARIANTS:
    Characteristic pore density.

BEST_CANDIDATES:
    Degree of repulsion between random nuclei.  Larger values make pore
    spacing more uniform.

COARSE_WARP_* / FINE_WARP_*:
    Interface tortuosity at large and medium scales.

WIDTH_JITTER:
    Slow strut-width variation.

MID_WIDTH_STRENGTH:
    Intermediate-scale constrictions/thickenings.  Particularly useful for
    controlling lineal-path statistics.

PIXEL_WIDTH_STRENGTH:
    Fine boundary roughness and the lower tail of strut thickness.

NODE_STRENGTH:
    Extra thickness around cellular junctions.

N_PROCEDURAL_CANDIDATES:
    Number of nearby stochastic morphology settings tested per output seed.
"""

from pathlib import Path
import heapq

import numpy as np
from PIL import Image
from scipy.ndimage import (
    binary_dilation,
    distance_transform_edt,
    gaussian_filter,
    generate_binary_structure,
    label,
    maximum as labeled_maximum,
)
from scipy.spatial import cKDTree


# ============================================================================
# Fixed output requirements
# ============================================================================

SIZE = 256
N_SAMPLES = 20
OUTPUT_DIR = Path("generated_microstructures")

TOTAL_PIXELS = SIZE * SIZE

# The supplied target fraction corresponds to exactly 25867 / 65536 pixels.
TARGET_SOLID_FRACTION = 0.394699
TARGET_SOLID_PIXELS = int(round(TARGET_SOLID_FRACTION * TOTAL_PIXELS))

# The supplied largest-component target implies exactly 25670 of those solid
# pixels in the dominant component.
TARGET_LARGEST_COMPONENT_FRACTION = 0.992384
TARGET_MAIN_SOLID_PIXELS = int(
    round(TARGET_LARGEST_COMPONENT_FRACTION * TARGET_SOLID_PIXELS)
)

TARGET_ISOLATED_SOLID_PIXELS = (
    TARGET_SOLID_PIXELS - TARGET_MAIN_SOLID_PIXELS
)

# Several small isolated solid inclusions produce the requested dominant-
# component fraction. Their locations, sizes, and shapes remain stochastic.
N_ISLANDS = 5


# ============================================================================
# Aggregate calibration targets supplied by the user
# ============================================================================

S2_RADII = np.array([0, 1, 2, 4, 8, 16, 32, 64], dtype=int)

TARGET_S2 = np.array(
    [
        0.394699,
        0.351303,
        0.318398,
        0.253283,
        0.167153,
        0.137501,
        0.155534,
        0.155713,
    ],
    dtype=np.float64,
)

TARGET_MEDIAN_PORE_DIAMETER = 16.4924


# ============================================================================
# Procedural morphology parameters
# ============================================================================

NUCLEI_JITTER = 3

COARSE_WARP_SIGMA = 14.0
FINE_WARP_SIGMA = 4.0

SLOW_WIDTH_SIGMA = 10.0
MID_WIDTH_SIGMA = 2.5
PIXEL_WIDTH_SIGMA = 0.70

BASE_LOCAL_HALF_WIDTH = 2.50

NODE_SIGMA = 4.0

MIN_LOCAL_HALF_WIDTH = 0.50
MAX_LOCAL_HALF_WIDTH = 5.00

# The settings deliberately occupy a narrow region of parameter space.
# Candidate choice is stochastic because each variant is generated from its
# own deterministic substream of the requested root seed.
CANDIDATE_VARIANTS = (
    {
        "base_nuclei": 66,
        "best_candidates": 12,
        "coarse_warp_amplitude": 5.00,
        "fine_warp_amplitude": 1.70,
        "width_jitter": 0.20,
        "mid_width_strength": 0.70,
        "pixel_width_strength": 0.55,
        "node_strength": 1.35,
    },
    {
        "base_nuclei": 65,
        "best_candidates": 12,
        "coarse_warp_amplitude": 5.00,
        "fine_warp_amplitude": 1.70,
        "width_jitter": 0.20,
        "mid_width_strength": 0.70,
        "pixel_width_strength": 0.58,
        "node_strength": 1.50,
    },
    {
        "base_nuclei": 66,
        "best_candidates": 16,
        "coarse_warp_amplitude": 5.50,
        "fine_warp_amplitude": 1.90,
        "width_jitter": 0.20,
        "mid_width_strength": 0.75,
        "pixel_width_strength": 0.55,
        "node_strength": 1.50,
    },
    {
        "base_nuclei": 65,
        "best_candidates": 10,
        "coarse_warp_amplitude": 4.80,
        "fine_warp_amplitude": 1.60,
        "width_jitter": 0.15,
        "mid_width_strength": 0.65,
        "pixel_width_strength": 0.56,
        "node_strength": 1.45,
    },
)

N_PROCEDURAL_CANDIDATES = len(CANDIDATE_VARIANTS)

# S2 is the principal candidate-selection objective.  The weak pore term
# prevents selection from drifting toward an inappropriate pore scale.
PORE_SCORE_WEIGHT = 0.12


# ============================================================================
# Connectivity
# ============================================================================

FOUR_CONNECTED = generate_binary_structure(2, 1)

NEIGHBORS_4 = (
    (-1, 0),
    (1, 0),
    (0, -1),
    (0, 1),
)


# ============================================================================
# Precompute radial bins used for S2
# ============================================================================

_YY_CENTERED, _XX_CENTERED = np.indices((SIZE, SIZE), dtype=np.float64)
_YY_CENTERED -= SIZE // 2
_XX_CENTERED -= SIZE // 2

_RADIUS_GRID = np.hypot(_YY_CENTERED, _XX_CENTERED)

S2_RING_MASKS = []

for radius in S2_RADII:
    if radius == 0:
        mask = np.zeros((SIZE, SIZE), dtype=bool)
        mask[SIZE // 2, SIZE // 2] = True
    else:
        mask = (
            (_RADIUS_GRID >= radius - 0.5)
            & (_RADIUS_GRID < radius + 0.5)
        )

    S2_RING_MASKS.append(mask)


# ============================================================================
# Random-field utilities
# ============================================================================

def normalized_smooth_noise(rng, shape, sigma):
    """
    Generate periodic Gaussian random noise with mean 0 and standard deviation 1.
    """
    field = rng.standard_normal(shape)

    field = gaussian_filter(
        field,
        sigma=sigma,
        mode="wrap",
    )

    field -= field.mean()

    std = field.std()

    if std < 1.0e-12:
        return np.zeros(shape, dtype=np.float64)

    return field / std


# ============================================================================
# Mild blue-noise point process
# ============================================================================

def best_candidate_points(rng, n_points, n_candidates):
    """
    Generate stochastic mildly repulsive nuclei on a periodic square.

    For each new point, several uniformly random proposals are drawn and the
    proposal having the largest distance to the existing nuclei is retained.

    This is not a lattice: every nucleus remains stochastic, but the extreme
    pore-size variation of an unconstrained Poisson process is reduced.
    """
    points = np.empty((n_points, 2), dtype=np.float64)

    points[0] = rng.uniform(
        0.0,
        float(SIZE),
        size=2,
    )

    for i in range(1, n_points):

        proposals = rng.uniform(
            0.0,
            float(SIZE),
            size=(n_candidates, 2),
        )

        existing = points[:i]

        delta = np.abs(
            proposals[:, None, :] - existing[None, :, :]
        )

        # Periodic minimum-image convention.
        delta = np.minimum(
            delta,
            SIZE - delta,
        )

        distance_sq = np.sum(
            delta * delta,
            axis=2,
        )

        nearest_sq = distance_sq.min(axis=1)

        best = int(np.argmax(nearest_sq))

        points[i] = proposals[best]

    return points


# ============================================================================
# Cellular skeleton
# ============================================================================

def make_warp_fields(rng, coarse_amplitude, fine_amplitude):
    """
    Generate stochastic periodic x/y coordinate distortions.
    """
    shape = (SIZE, SIZE)

    coarse_y = normalized_smooth_noise(
        rng,
        shape,
        COARSE_WARP_SIGMA,
    )

    coarse_x = normalized_smooth_noise(
        rng,
        shape,
        COARSE_WARP_SIGMA,
    )

    fine_y = normalized_smooth_noise(
        rng,
        shape,
        FINE_WARP_SIGMA,
    )

    fine_x = normalized_smooth_noise(
        rng,
        shape,
        FINE_WARP_SIGMA,
    )

    dy = (
        coarse_amplitude * coarse_y
        + fine_amplitude * fine_y
    )

    dx = (
        coarse_amplitude * coarse_x
        + fine_amplitude * fine_x
    )

    return dy, dx


def build_warped_interface(rng, params):
    """
    Construct a periodic, warped Voronoi-like cellular interface network.
    """
    n_nuclei = int(
        params["base_nuclei"]
        + rng.integers(
            -NUCLEI_JITTER,
            NUCLEI_JITTER + 1,
        )
    )

    nuclei = best_candidate_points(
        rng,
        n_points=n_nuclei,
        n_candidates=params["best_candidates"],
    )

    yy, xx = np.indices(
        (SIZE, SIZE),
        dtype=np.float64,
    )

    dy, dx = make_warp_fields(
        rng,
        coarse_amplitude=params["coarse_warp_amplitude"],
        fine_amplitude=params["fine_warp_amplitude"],
    )

    warped_y = np.mod(
        yy + dy,
        SIZE,
    )

    warped_x = np.mod(
        xx + dx,
        SIZE,
    )

    query_points = np.column_stack(
        (
            warped_y.ravel(),
            warped_x.ravel(),
        )
    )

    tree = cKDTree(
        nuclei,
        boxsize=(SIZE, SIZE),
    )

    _, labels = tree.query(
        query_points,
        k=1,
    )

    labels = labels.reshape(
        SIZE,
        SIZE,
    )

    interface = np.zeros(
        (SIZE, SIZE),
        dtype=bool,
    )

    # Mark both sides of all 4-neighbour cell interfaces.
    interface |= labels != np.roll(labels, 1, axis=0)
    interface |= labels != np.roll(labels, -1, axis=0)
    interface |= labels != np.roll(labels, 1, axis=1)
    interface |= labels != np.roll(labels, -1, axis=1)

    return interface


def periodic_distance_to_mask(mask):
    """
    Euclidean distance to a mask with periodic boundary conditions.
    """
    tiled = np.tile(
        mask,
        (3, 3),
    )

    distance = distance_transform_edt(
        ~tiled,
    )

    return distance[
        SIZE:2 * SIZE,
        SIZE:2 * SIZE,
    ]


# ============================================================================
# 4-connected component utilities
# ============================================================================

def largest_component_mask(binary):
    """
    Return a boolean mask containing only the largest 4-connected component.
    """
    labels, n_components = label(
        binary.astype(bool),
        structure=FOUR_CONNECTED,
    )

    if n_components == 0:
        return np.zeros_like(
            binary,
            dtype=bool,
        )

    sizes = np.bincount(
        labels.ravel()
    )

    sizes[0] = 0

    component_id = int(
        np.argmax(sizes)
    )

    return labels == component_id


def spans_both_axes(binary):
    """
    True when one 4-connected component touches all four image borders.
    """
    labels, n_components = label(
        binary.astype(bool),
        structure=FOUR_CONNECTED,
    )

    if n_components == 0:
        return False

    sizes = np.bincount(
        labels.ravel()
    )

    sizes[0] = 0

    component_id = int(
        np.argmax(sizes)
    )

    return (
        np.any(labels[:, 0] == component_id)
        and np.any(labels[:, -1] == component_id)
        and np.any(labels[0, :] == component_id)
        and np.any(labels[-1, :] == component_id)
    )


def connect_component_to_all_borders(component):
    """
    Rare safety fallback that makes one connected component touch all borders.

    The cellular interface normally already spans every border.  When it does
    not, only a shortest axis-aligned connection from the existing component
    to the missing border is added.
    """
    out = component.astype(
        bool,
        copy=True,
    )

    if not np.any(out):
        out[SIZE // 2, SIZE // 2] = True

    # Left.
    if not np.any(out[:, 0]):
        coords = np.argwhere(out)
        y, x = coords[
            np.argmin(coords[:, 1])
        ]
        out[y, :x + 1] = True

    # Right.
    if not np.any(out[:, -1]):
        coords = np.argwhere(out)
        y, x = coords[
            np.argmax(coords[:, 1])
        ]
        out[y, x:] = True

    # Top.
    if not np.any(out[0, :]):
        coords = np.argwhere(out)
        y, x = coords[
            np.argmin(coords[:, 0])
        ]
        out[:y + 1, x] = True

    # Bottom.
    if not np.any(out[-1, :]):
        coords = np.argwhere(out)
        y, x = coords[
            np.argmax(coords[:, 0])
        ]
        out[y:, x] = True

    return out


# ============================================================================
# Exact connected-network construction
# ============================================================================

def exact_top_k_mask(score, k):
    """
    Select exactly k pixels with the largest scalar scores.
    """
    flat = score.ravel()

    if not 0 < k <= flat.size:
        raise ValueError("Invalid requested pixel count.")

    selection = np.argpartition(
        flat,
        flat.size - k,
    )[flat.size - k:]

    result = np.zeros(
        flat.size,
        dtype=bool,
    )

    result[selection] = True

    return result.reshape(
        score.shape
    )


def grow_connected_to_size(core, score, target_pixels):
    """
    Grow one 4-connected component to an exact number of pixels.

    Growth follows a max-priority frontier using the procedural morphology
    score, so the operation mostly restores high-score pixels removed when
    disconnected fragments of the initial threshold are discarded.
    """
    main = core.astype(
        bool,
        copy=True,
    )

    count = int(
        main.sum()
    )

    if count > target_pixels:
        raise RuntimeError(
            "Forced spanning core exceeds requested main-network size."
        )

    if count == target_pixels:
        return main

    in_heap = np.zeros_like(
        main,
        dtype=bool,
    )

    heap = []

    def push(y, x):
        if (
            0 <= y < SIZE
            and 0 <= x < SIZE
            and not main[y, x]
            and not in_heap[y, x]
        ):
            heapq.heappush(
                heap,
                (
                    -float(score[y, x]),
                    y * SIZE + x,
                ),
            )
            in_heap[y, x] = True

    ys, xs = np.nonzero(main)

    for y, x in zip(ys, xs):
        for dy, dx in NEIGHBORS_4:
            push(
                int(y + dy),
                int(x + dx),
            )

    while count < target_pixels:

        if not heap:
            raise RuntimeError(
                "Connected growth frontier unexpectedly became empty."
            )

        _, flat_index = heapq.heappop(
            heap
        )

        y, x = divmod(
            flat_index,
            SIZE,
        )

        if main[y, x]:
            continue

        main[y, x] = True
        count += 1

        for dy, dx in NEIGHBORS_4:
            push(
                y + dy,
                x + dx,
            )

    return main


def make_main_network(rng, params):
    """
    Produce the exact-size, single dominant 4-connected spanning network.
    """
    interface = build_warped_interface(
        rng,
        params,
    )

    # Use the principal interface component as an immutable connected backbone.
    backbone = largest_component_mask(
        interface
    )

    backbone = connect_component_to_all_borders(
        backbone
    )

    if backbone.sum() >= TARGET_MAIN_SOLID_PIXELS:
        raise RuntimeError(
            "Backbone unexpectedly exceeds target network size."
        )

    distance = periodic_distance_to_mask(
        backbone
    )

    # Long-scale strut variation.
    slow_width = normalized_smooth_noise(
        rng,
        (SIZE, SIZE),
        SLOW_WIDTH_SIGMA,
    )

    # Intermediate modulation primarily controls constrictions and lineal path.
    mid_width = normalized_smooth_noise(
        rng,
        (SIZE, SIZE),
        MID_WIDTH_SIGMA,
    )

    # Pixel-scale roughness increases interfacial complexity.
    pixel_width = normalized_smooth_noise(
        rng,
        (SIZE, SIZE),
        PIXEL_WIDTH_SIGMA,
    )

    # Junction detector.
    neighbor_density = np.zeros(
        (SIZE, SIZE),
        dtype=np.float64,
    )

    for dy, dx in NEIGHBORS_4:
        neighbor_density += np.roll(
            np.roll(
                backbone.astype(np.float64),
                dy,
                axis=0,
            ),
            dx,
            axis=1,
        )

    node_field = gaussian_filter(
        neighbor_density,
        sigma=NODE_SIGMA,
        mode="wrap",
    )

    node_field -= node_field.mean()

    node_std = node_field.std()

    if node_std > 1.0e-12:
        node_field /= node_std

    node_boost = np.maximum(
        node_field,
        0.0,
    )

    local_half_width = (
        BASE_LOCAL_HALF_WIDTH
        + params["width_jitter"] * slow_width
        + params["mid_width_strength"] * mid_width
        + params["pixel_width_strength"] * pixel_width
        + params["node_strength"] * node_boost
    )

    local_half_width = np.clip(
        local_half_width,
        MIN_LOCAL_HALF_WIDTH,
        MAX_LOCAL_HALF_WIDTH,
    )

    # Positive means that the pixel lies preferentially inside a local strut.
    score = (
        local_half_width
        - distance
    )

    # Guarantee inclusion of the percolating cellular backbone.
    forced_score = float(
        np.max(score) + 100.0
    )

    score[backbone] = forced_score

    initial = exact_top_k_mask(
        score,
        TARGET_MAIN_SOLID_PIXELS,
    )

    main = largest_component_mask(
        initial
    )

    # Because the forced backbone is present, this component must span.
    if not spans_both_axes(main):
        main = connect_component_to_all_borders(
            main
        )

    # Disconnected high-score pixels are replaced with high-score pixels
    # adjacent to the main network.
    main = grow_connected_to_size(
        main,
        score,
        TARGET_MAIN_SOLID_PIXELS,
    )

    if int(main.sum()) != TARGET_MAIN_SOLID_PIXELS:
        raise RuntimeError(
            "Main-network size enforcement failed."
        )

    if not spans_both_axes(main):
        raise RuntimeError(
            "Main network failed final percolation validation."
        )

    return main


# ============================================================================
# Procedural isolated solid islands
# ============================================================================

def partition_island_pixels(rng, total_pixels, n_islands):
    """
    Stochastically partition the isolated-solid budget into compact components.
    """
    minimum = 8

    if n_islands * minimum >= total_pixels:
        raise ValueError(
            "Not enough isolated pixels for requested island count."
        )

    remaining = (
        total_pixels
        - n_islands * minimum
    )

    # Retry only to avoid a single pathologically dominant island.
    for _ in range(100):

        weights = rng.gamma(
            shape=3.0,
            scale=1.0,
            size=n_islands,
        )

        probabilities = (
            weights / weights.sum()
        )

        extra = rng.multinomial(
            remaining,
            probabilities,
        )

        sizes = (
            extra + minimum
        )

        if sizes.max() <= 75:
            return sizes.astype(int)

    # Extremely unlikely fallback.
    sizes = np.full(
        n_islands,
        total_pixels // n_islands,
        dtype=int,
    )

    sizes[:total_pixels - sizes.sum()] += 1

    return sizes


def grow_compact_blob(allowed, component_id_mask, center, target_size, rng):
    """
    Grow one irregular but compact 4-connected blob inside an allowed pore.
    """
    blob = np.zeros(
        (SIZE, SIZE),
        dtype=bool,
    )

    cy, cx = center

    theta = rng.uniform(
        0.0,
        np.pi,
    )

    cos_t = np.cos(theta)
    sin_t = np.sin(theta)

    # Modest stochastic anisotropy prevents circular synthetic inclusions.
    aspect = np.exp(
        rng.normal(
            loc=0.0,
            scale=0.18,
        )
    )

    visited = np.zeros(
        (SIZE, SIZE),
        dtype=bool,
    )

    heap = []

    def geometric_priority(y, x):
        dy = y - cy
        dx = x - cx

        u = (
            cos_t * dx
            + sin_t * dy
        )

        v = (
            -sin_t * dx
            + cos_t * dy
        )

        radial_cost = (
            (u / aspect) ** 2
            + (v * aspect) ** 2
        )

        return (
            radial_cost
            + rng.normal(0.0, 1.1)
        )

    heapq.heappush(
        heap,
        (
            geometric_priority(cy, cx),
            cy * SIZE + cx,
        ),
    )

    visited[cy, cx] = True

    count = 0

    while heap and count < target_size:

        _, flat_index = heapq.heappop(
            heap
        )

        y, x = divmod(
            flat_index,
            SIZE,
        )

        if (
            not allowed[y, x]
            or not component_id_mask[y, x]
            or blob[y, x]
        ):
            continue

        # Every point after the first must remain 4-connected to the blob.
        if count > 0:
            touches_blob = False

            for dy, dx in NEIGHBORS_4:
                yy = y + dy
                xx = x + dx

                if (
                    0 <= yy < SIZE
                    and 0 <= xx < SIZE
                    and blob[yy, xx]
                ):
                    touches_blob = True
                    break

            if not touches_blob:
                continue

        blob[y, x] = True
        count += 1

        for dy, dx in NEIGHBORS_4:

            yy = y + dy
            xx = x + dx

            if (
                0 <= yy < SIZE
                and 0 <= xx < SIZE
                and allowed[yy, xx]
                and component_id_mask[yy, xx]
                and not visited[yy, xx]
            ):
                visited[yy, xx] = True

                heapq.heappush(
                    heap,
                    (
                        geometric_priority(yy, xx),
                        yy * SIZE + xx,
                    ),
                )

    if count != target_size:
        raise RuntimeError(
            "Failed to grow requested isolated island."
        )

    return blob


def add_isolated_islands(main, rng):
    """
    Add the exact isolated-solid budget while keeping every island separated
    from the dominant network and from every other island by at least one
    4-neighbour void pixel.
    """
    solid = main.astype(
        bool,
        copy=True,
    )

    island_sizes = partition_island_pixels(
        rng,
        TARGET_ISOLATED_SOLID_PIXELS,
        N_ISLANDS,
    )

    for target_size in island_sizes:

        # Exclude both current solid and its 4-neighbour ring.
        forbidden = binary_dilation(
            solid,
            structure=FOUR_CONNECTED,
            iterations=1,
        )

        allowed = ~forbidden

        allowed_labels, n_regions = label(
            allowed,
            structure=FOUR_CONNECTED,
        )

        if n_regions == 0:
            raise RuntimeError(
                "No pore region available for isolated island."
            )

        region_sizes = np.bincount(
            allowed_labels.ravel()
        )

        region_sizes[0] = 0

        eligible_ids = np.flatnonzero(
            region_sizes >= int(target_size)
        )

        if eligible_ids.size == 0:
            raise RuntimeError(
                "No sufficiently large pore for isolated island."
            )

        # Prefer large pores, but do not deterministically choose the largest.
        eligible_weights = region_sizes[
            eligible_ids
        ].astype(np.float64)

        eligible_weights /= (
            eligible_weights.sum()
        )

        chosen_region = int(
            rng.choice(
                eligible_ids,
                p=eligible_weights,
            )
        )

        region_mask = (
            allowed_labels == chosen_region
        )

        # Pick a center well inside the available pore region.
        clearance = distance_transform_edt(
            region_mask
        )

        max_clearance = clearance.max()

        interior_candidates = np.argwhere(
            clearance
            >= 0.75 * max_clearance
        )

        center = tuple(
            interior_candidates[
                rng.integers(
                    0,
                    len(interior_candidates),
                )
            ]
        )

        island = grow_compact_blob(
            allowed=allowed,
            component_id_mask=region_mask,
            center=center,
            target_size=int(target_size),
            rng=rng,
        )

        solid |= island

    if int(solid.sum()) != TARGET_SOLID_PIXELS:
        raise RuntimeError(
            "Final solid pixel count is incorrect."
        )

    return solid.astype(
        np.uint8
    )


# ============================================================================
# Two-point and pore-scale candidate scoring
# ============================================================================

def radial_two_point_correlation(binary):
    """
    Periodic isotropic S2 using FFT autocorrelation and integer-radius shells.
    """
    field = binary.astype(
        np.float64
    )

    spectrum = np.fft.fftn(
        field
    )

    autocorrelation = np.fft.ifftn(
        spectrum * np.conjugate(spectrum)
    ).real

    autocorrelation /= field.size

    autocorrelation = np.fft.fftshift(
        autocorrelation
    )

    values = np.empty(
        len(S2_RADII),
        dtype=np.float64,
    )

    for i, mask in enumerate(S2_RING_MASKS):
        values[i] = autocorrelation[
            mask
        ].mean()

    return values


def median_pore_diameter_proxy(binary):
    """
    Median maximum-inscribed diameter of 4-connected void components.

    This inexpensive SciPy-only quantity is used only as a candidate-selection
    scale constraint; it does not alter the phase convention or connectivity.
    """
    void = ~binary.astype(
        bool
    )

    void_labels, n_pores = label(
        void,
        structure=FOUR_CONNECTED,
    )

    if n_pores == 0:
        return 0.0

    void_distance = distance_transform_edt(
        void
    )

    pore_ids = np.arange(
        1,
        n_pores + 1,
        dtype=int,
    )

    maximum_radii = labeled_maximum(
        void_distance,
        labels=void_labels,
        index=pore_ids,
    )

    maximum_radii = np.asarray(
        maximum_radii,
        dtype=np.float64,
    )

    return float(
        2.0 * np.median(maximum_radii)
    )


def candidate_score(binary):
    """
    Score one fully procedural candidate against aggregate calibration data.

    No pixel template or reference image participates in this calculation.
    """
    s2 = radial_two_point_correlation(
        binary
    )

    # Scale by phase fraction so all radii contribute in absolute probability
    # units rather than unstable pointwise percentage errors.
    s2_error = np.sqrt(
        np.mean(
            (
                (s2 - TARGET_S2)
                / TARGET_S2[0]
            ) ** 2
        )
    )

    pore_diameter = median_pore_diameter_proxy(
        binary
    )

    pore_error = (
        abs(
            pore_diameter
            - TARGET_MEDIAN_PORE_DIAMETER
        )
        / TARGET_MEDIAN_PORE_DIAMETER
    )

    total_score = (
        s2_error
        + PORE_SCORE_WEIGHT * pore_error
    )

    return (
        float(total_score),
        s2,
        float(pore_diameter),
    )


# ============================================================================
# Complete stochastic sample generation
# ============================================================================

def generate_candidate(root_seed, variant_index):
    """
    Generate one candidate using a deterministic substream of root_seed.

    Thus output seed 0 is rooted in seed 0, output seed 1 in seed 1, etc.,
    while the candidate bank does not reuse an identical random stream.
    """
    seed_sequence = np.random.SeedSequence(
        [
            int(root_seed),
            int(variant_index),
            0x5A17C3,
        ]
    )

    rng = np.random.default_rng(
        seed_sequence
    )

    params = CANDIDATE_VARIANTS[
        variant_index
    ]

    main = make_main_network(
        rng,
        params,
    )

    sample = add_isolated_islands(
        main,
        rng,
    )

    return sample


def generate_microstructure(seed):
    """
    Generate the selected realization for one root seed.
    """
    best_sample = None
    best_score = np.inf
    best_variant = None
    best_s2 = None
    best_pore = None

    for variant_index in range(
        N_PROCEDURAL_CANDIDATES
    ):

        candidate = generate_candidate(
            seed,
            variant_index,
        )

        score, s2, pore = candidate_score(
            candidate
        )

        if score < best_score:

            best_score = score
            best_sample = candidate
            best_variant = variant_index
            best_s2 = s2
            best_pore = pore

    if best_sample is None:
        raise RuntimeError(
            "No procedural candidate was generated."
        )

    return (
        best_sample.astype(np.uint8),
        best_variant,
        best_score,
        best_s2,
        best_pore,
    )


# ============================================================================
# Validation
# ============================================================================

def validate_sample(binary):
    """
    Validate phase values, exact size, component dominance, and percolation.
    """
    if binary.shape != (
        SIZE,
        SIZE,
    ):
        raise RuntimeError(
            f"Incorrect image dimensions: {binary.shape}"
        )

    if binary.dtype != np.uint8:
        raise RuntimeError(
            f"Incorrect dtype: {binary.dtype}"
        )

    if not np.all(
        (binary == 0)
        | (binary == 1)
    ):
        raise RuntimeError(
            "Generated field is not binary."
        )

    solid_pixels = int(
        binary.sum()
    )

    if solid_pixels != TARGET_SOLID_PIXELS:
        raise RuntimeError(
            f"Expected {TARGET_SOLID_PIXELS} solid pixels, "
            f"got {solid_pixels}."
        )

    labels, n_components = label(
        binary.astype(bool),
        structure=FOUR_CONNECTED,
    )

    if n_components == 0:
        raise RuntimeError(
            "No solid component exists."
        )

    sizes = np.bincount(
        labels.ravel()
    )

    sizes[0] = 0

    component_id = int(
        np.argmax(sizes)
    )

    largest_pixels = int(
        sizes[component_id]
    )

    largest_fraction = (
        largest_pixels
        / solid_pixels
    )

    if largest_pixels != TARGET_MAIN_SOLID_PIXELS:
        raise RuntimeError(
            "Dominant-component pixel count differs from requested value."
        )

    left_right = (
        np.any(
            labels[:, 0] == component_id
        )
        and np.any(
            labels[:, -1] == component_id
        )
    )

    top_bottom = (
        np.any(
            labels[0, :] == component_id
        )
        and np.any(
            labels[-1, :] == component_id
        )
    )

    if not left_right:
        raise RuntimeError(
            "Dominant component does not percolate left-to-right."
        )

    if not top_bottom:
        raise RuntimeError(
            "Dominant component does not percolate top-to-bottom."
        )

    return (
        largest_fraction,
        left_right,
        top_bottom,
        n_components,
    )


# ============================================================================
# File output
# ============================================================================

def save_binary_png(array01, filename):
    """
    Save phase indices exactly as 0 and 1 in a palette PNG.

        0 = void  -> white display color
        1 = solid -> black display color
    """
    if array01.dtype != np.uint8:
        array01 = array01.astype(
            np.uint8
        )

    if not np.all(
        (array01 == 0)
        | (array01 == 1)
    ):
        raise ValueError(
            "PNG input must contain only 0 and 1."
        )

    image = Image.fromarray(
        array01,
        mode="P",
    )

    palette = [
        255, 255, 255,  # index 0: void
        0,   0,   0,    # index 1: solid
    ]

    palette.extend(
        [0, 0, 0] * 254
    )

    image.putpalette(
        palette
    )

    image.save(
        filename
    )


# ============================================================================
# Main
# ============================================================================

def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for seed in range(
        N_SAMPLES
    ):

        (
            sample,
            variant,
            score,
            s2,
            pore_proxy,
        ) = generate_microstructure(
            seed
        )

        (
            largest_fraction,
            left_right,
            top_bottom,
            component_count,
        ) = validate_sample(
            sample
        )

        stem = (
            f"microstructure_seed_{seed:02d}"
        )

        npy_path = (
            OUTPUT_DIR
            / f"{stem}.npy"
        )

        png_path = (
            OUTPUT_DIR
            / f"{stem}.png"
        )

        # Exact phase convention:
        #     1 = solid
        #     0 = void
        np.save(
            npy_path,
            sample,
        )

        save_binary_png(
            sample,
            png_path,
        )

        print(
            f"seed={seed:02d} | "
            f"variant={variant} | "
            f"solid_fraction={sample.mean():.9f} | "
            f"largest_component_fraction={largest_fraction:.9f} | "
            f"LR={left_right} | "
            f"TB={top_bottom} | "
            f"solid_components={component_count} | "
            f"pore_diameter_proxy={pore_proxy:.3f} | "
            f"S2_score={score:.6f} | "
            f"{png_path.name} | "
            f"{npy_path.name}"
        )


if __name__ == "__main__":
    main()