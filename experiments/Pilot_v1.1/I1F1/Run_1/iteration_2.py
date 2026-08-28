#!/usr/bin/env python3
"""
Procedural generator for 2-D disordered mechanical metamaterials.
Revision round 2.

Output convention
-----------------
solid = 1
void  = 0

The program creates exactly:

    generated_microstructures/sample_seed_00.png
    generated_microstructures/sample_seed_00.npy
    ...
    generated_microstructures/sample_seed_19.png
    generated_microstructures/sample_seed_19.npy

Algorithm
---------
1. A mildly jittered stochastic lattice supplies pore generators.  The reduced
   jitter in this revision produces more persistent horizontal/vertical wall
   segments while retaining disorder.

2. A weighted Chebyshev (L-infinity) Voronoi-like partition produces an
   irregular cellular/vein topology.

3. Interfaces are ranked by geometric persistence (interface length with a
   stochastic multiplier).  A controlled fraction of the shortest/least
   persistent interfaces is suppressed.  This merges selected neighboring
   cells and lets the same amount of solid be carried by fewer, thicker paths.

4. Retained interfaces receive three width levels:
       ordinary branch
       secondary vein
       trunk vein

   True multi-cell junctions are locally reinforced.

5. A narrow per-realization width search places the material fraction just
   below its target.  A small connected boundary-growth correction then
   finishes the requested volume fraction without creating isolated islands
   or one-pixel branches.

6. For each requested seed, two independent procedural candidates are drawn.
   The candidate whose two-point correlation and directional lineal-path
   statistics best match the supplied DEVELOPMENT SUMMARY is retained.
   Only the scalar/statistical targets supplied in the prompt are used.
   No reference pixels, image, traced geometry, external files, models,
   datasets, APIs, or internet access are used.

7. The final solid is explicitly reduced to one dominant 4-connected
   component and must span left-right and top-bottom.

Important adjustable parameters
-------------------------------
CELL_SIZE
    Primary feature / pore spacing.

GENERATOR_JITTER
    Positional disorder of pore generators.  Larger values make the network
    less directionally organized.

REMOVE_EDGE_FRACTION
    Fraction of low-persistence cellular interfaces omitted.  Increasing it
    gives fewer, thicker load paths and larger compound pores.

BASE_HALF_WIDTH, SECONDARY_HALF_WIDTH, TRUNK_HALF_WIDTH
    Relative strut hierarchy.

SECONDARY_FRACTION, TRUNK_FRACTION
    Fractions of retained interfaces promoted to wider vein classes.

TARGET_SOLID_FRACTION
    Mean requested solid volume fraction.

CANDIDATES_PER_SEED
    Number of independent procedural candidates compared for each output
    seed.  Increasing it improves statistical matching at additional runtime.

Dependencies
------------
numpy
scipy
Pillow

The script never reads the supplied reference image at runtime.
"""

from pathlib import Path
import hashlib

import numpy as np
from scipy import ndimage as ndi
from PIL import Image


# ============================================================================
# Output
# ============================================================================

SIZE = 256
N_SAMPLES = 20
OUTPUT_DIR = Path("generated_microstructures")


# ============================================================================
# Stochastic cellular geometry
# ============================================================================

# Revision-2 feature scale.  The slightly smaller spacing compensates for the
# deliberate removal of short interfaces later in the construction.
CELL_SIZE = 21.95

# Retained generator-site probability.
KEEP_PROB = 0.75

# Reduced from the previous revision.  This increases persistent horizontal
# and vertical segments while remaining visibly stochastic.
GENERATOR_JITTER = 0.26

# Random additive generator weights.
CELL_WEIGHT_STD = 0.10

# Weak directional anisotropy.
ANISO_X = 1.08
ANISO_Y = 0.96

DISTANCE_CHUNK = 12


# ============================================================================
# Interface topology
# ============================================================================

# Key revision: omit short / low-persistence interfaces.  This reduces the
# excessive skeleton length of the previous generator and transfers material
# into thicker, longer load-bearing veins.
REMOVE_EDGE_FRACTION = 0.41

# Ranking randomness prevents the same classes of lattice edges from always
# being removed or promoted.
EDGE_PRIORITY_NOISE = 0.42

# Width hierarchy among interfaces that remain.
SECONDARY_FRACTION = 0.34
TRUNK_FRACTION = 0.11


# ============================================================================
# Strut dimensions
# ============================================================================

BASE_HALF_WIDTH = 1.80
SECONDARY_HALF_WIDTH = 3.05
TRUNK_HALF_WIDTH = 4.65

# Reinforcement around genuine three/four-cell vertices.
JUNCTION_RADIUS = 4.25

# Global width search.  All three hierarchy widths are scaled by the same
# candidate multiplier, so their relative organization is preserved.
WIDTH_SCALE_MIN = 0.68
WIDTH_SCALE_MAX = 1.35
N_WIDTH_SCALES = 68


# ============================================================================
# Material fraction and cleanup
# ============================================================================

TARGET_SOLID_FRACTION = 0.394699
TARGET_SOLID_STD = 0.0012
TARGET_SOLID_MIN = 0.3920
TARGET_SOLID_MAX = 0.3975

# Only very small void defects are filled.
MIN_VOID_AREA = 30

FOUR_CONNECTED = ndi.generate_binary_structure(2, 1)

FOUR_NEIGHBOR_KERNEL = np.array(
    [
        [0, 1, 0],
        [1, 0, 1],
        [0, 1, 0],
    ],
    dtype=np.uint8,
)


# ============================================================================
# Candidate selection targets
#
# These are scalar/statistical DEVELOPMENT TARGETS supplied explicitly in
# the prompt.  They are not reference pixels or a stored/traced image.
# ============================================================================

S2_RADII = np.array(
    [1, 2, 4, 8, 16, 32, 64],
    dtype=np.int32,
)

TARGET_S2 = np.array(
    [
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

# The four-direction digital lineal-path estimator used below closely tracks
# the supplied target at these distances.  r=64 is omitted from selection
# because a four-direction estimator becomes too sparse there.
LINEAL_RADII = np.array(
    [1, 2, 4, 8, 16, 32],
    dtype=np.int32,
)

TARGET_LINEAL = np.array(
    [
        0.351303,
        0.308788,
        0.227493,
        0.125214,
        0.054344,
        0.012596,
    ],
    dtype=np.float64,
)

TARGET_MEDIAN_PORE_DIAMETER = 16.4924

# Two accepted stochastic candidates per requested seed gives statistical
# selection without turning the generator into an expensive optimization.
CANDIDATES_PER_SEED = 2
MAX_DRAWS_PER_SEED = 7


# ============================================================================
# Generator placement
# ============================================================================

def _make_generators(
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """
    Place jittered pore generators, including a ghost margin outside the
    image so that boundaries enter and leave the domain naturally.
    """
    c = CELL_SIZE

    xs = np.arange(
        -0.75 * c,
        n + 1.25 * c,
        c,
    )

    ys = np.arange(
        -0.75 * c,
        n + 1.25 * c,
        c,
    )

    points = []

    for y0 in ys:
        for x0 in xs:

            if rng.random() > KEEP_PROB:
                continue

            x = (
                x0
                + rng.uniform(
                    -GENERATOR_JITTER,
                    GENERATOR_JITTER,
                )
                * c
            )

            y = (
                y0
                + rng.uniform(
                    -GENERATOR_JITTER,
                    GENERATOR_JITTER,
                )
                * c
            )

            points.append(
                (x, y)
            )

    if len(points) < 20:
        raise RuntimeError(
            "Too few pore generators."
        )

    return np.asarray(
        points,
        dtype=np.float64,
    )


# ============================================================================
# Weighted L-infinity partition
# ============================================================================

def _partition_labels(
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """
    Produce a stochastic weighted Chebyshev Voronoi-like partition.

    L-infinity distance supplies the useful horizontal/vertical/diagonal
    organization, while generator jitter and weights prevent periodicity.
    """
    points = _make_generators(
        rng,
        n,
    )

    n_points = len(points)

    yy, xx = np.mgrid[0:n, 0:n]

    xx = xx.astype(
        np.float64
    )

    yy = yy.astype(
        np.float64
    )

    weights = (
        rng.standard_normal(n_points)
        * CELL_WEIGHT_STD
    )

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

        dx = np.abs(
            (
                xx[None, :, :]
                - px
            )
            / ANISO_X
        )

        dy = np.abs(
            (
                yy[None, :, :]
                - py
            )
            / ANISO_Y
        )

        d = np.maximum(
            dx,
            dy,
        )

        d += weights[
            start:stop,
            None,
            None,
        ]

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

        take = (
            local_best
            < best_distance
        )

        best_distance[take] = (
            local_best[take]
        )

        labels[take] = (
            start
            + local_index[take]
        )

    return labels


# ============================================================================
# Cellular interface graph
# ============================================================================

def _edge_code(
    a: np.ndarray,
    b: np.ndarray,
    n_labels: int,
) -> np.ndarray:
    """
    Integer code for an unordered pair of neighboring cell labels.
    """
    lo = np.minimum(
        a,
        b,
    ).astype(
        np.int64
    )

    hi = np.maximum(
        a,
        b,
    ).astype(
        np.int64
    )

    return (
        lo * n_labels
        + hi
    )


def _interface_hierarchy(
    labels: np.ndarray,
    rng: np.random.Generator,
):
    """
    Construct the retained-interface wall masks.

    Interfaces are ranked principally by their rasterized length.  A
    lognormal stochastic multiplier perturbs the ordering.

    The lowest-priority REMOVE_EDGE_FRACTION is discarded entirely.  This is
    the main topology correction in this revision: short cellular loops merge
    into compound pores, while long persistent interfaces carry the load.
    """
    n = labels.shape[0]

    n_labels = (
        int(labels.max())
        + 1
    )

    n_codes = (
        n_labels
        * n_labels
    )

    # ------------------------------------------------------------------
    # Collect label-pair codes for all four-neighbor cell interfaces.
    # ------------------------------------------------------------------

    left = labels[:, :-1]
    right = labels[:, 1:]

    vertical_change = (
        left != right
    )

    vertical_codes = _edge_code(
        left[vertical_change],
        right[vertical_change],
        n_labels,
    )

    upper = labels[:-1, :]
    lower = labels[1:, :]

    horizontal_change = (
        upper != lower
    )

    horizontal_codes = _edge_code(
        upper[horizontal_change],
        lower[horizontal_change],
        n_labels,
    )

    all_codes = np.concatenate(
        (
            vertical_codes,
            horizontal_codes,
        )
    )

    counts = np.bincount(
        all_codes,
        minlength=n_codes,
    ).astype(
        np.float64
    )

    present_codes = np.flatnonzero(
        counts > 0
    )

    # ------------------------------------------------------------------
    # Persistent/long edges rank highest, with stochastic modulation.
    # ------------------------------------------------------------------

    random_factor = np.exp(
        EDGE_PRIORITY_NOISE
        * rng.standard_normal(
            len(present_codes)
        )
    )

    priority = (
        counts[present_codes]
        * random_factor
    )

    order = np.argsort(
        priority
    )[::-1]

    ranked_codes = (
        present_codes[order]
    )

    n_edges = len(
        ranked_codes
    )

    n_remove = int(
        np.rint(
            REMOVE_EDGE_FRACTION
            * n_edges
        )
    )

    n_keep = max(
        8,
        n_edges - n_remove,
    )

    retained_codes = (
        ranked_codes[:n_keep]
    )

    n_secondary = max(
        1,
        int(
            np.rint(
                SECONDARY_FRACTION
                * n_keep
            )
        ),
    )

    n_trunk = max(
        1,
        int(
            np.rint(
                TRUNK_FRACTION
                * n_keep
            )
        ),
    )

    n_secondary = max(
        n_secondary,
        n_trunk,
    )

    # -1 = omitted
    #  0 = ordinary branch
    #  1 = secondary
    #  2 = trunk
    level = np.full(
        n_codes,
        -1,
        dtype=np.int8,
    )

    level[
        retained_codes
    ] = 0

    level[
        retained_codes[:n_secondary]
    ] = 1

    level[
        retained_codes[:n_trunk]
    ] = 2

    base_wall = np.zeros(
        (n, n),
        dtype=bool,
    )

    secondary_wall = np.zeros_like(
        base_wall
    )

    trunk_wall = np.zeros_like(
        base_wall
    )

    # ------------------------------------------------------------------
    # Left-right interfaces.
    # ------------------------------------------------------------------

    yy, xx = np.nonzero(
        vertical_change
    )

    codes = _edge_code(
        left[vertical_change],
        right[vertical_change],
        n_labels,
    )

    edge_levels = level[
        codes
    ]

    selected = (
        edge_levels >= 0
    )

    base_wall[
        yy[selected],
        xx[selected],
    ] = True

    base_wall[
        yy[selected],
        xx[selected] + 1,
    ] = True

    selected = (
        edge_levels >= 1
    )

    secondary_wall[
        yy[selected],
        xx[selected],
    ] = True

    secondary_wall[
        yy[selected],
        xx[selected] + 1,
    ] = True

    selected = (
        edge_levels >= 2
    )

    trunk_wall[
        yy[selected],
        xx[selected],
    ] = True

    trunk_wall[
        yy[selected],
        xx[selected] + 1,
    ] = True

    # ------------------------------------------------------------------
    # Up-down interfaces.
    # ------------------------------------------------------------------

    yy, xx = np.nonzero(
        horizontal_change
    )

    codes = _edge_code(
        upper[horizontal_change],
        lower[horizontal_change],
        n_labels,
    )

    edge_levels = level[
        codes
    ]

    selected = (
        edge_levels >= 0
    )

    base_wall[
        yy[selected],
        xx[selected],
    ] = True

    base_wall[
        yy[selected] + 1,
        xx[selected],
    ] = True

    selected = (
        edge_levels >= 1
    )

    secondary_wall[
        yy[selected],
        xx[selected],
    ] = True

    secondary_wall[
        yy[selected] + 1,
        xx[selected],
    ] = True

    selected = (
        edge_levels >= 2
    )

    trunk_wall[
        yy[selected],
        xx[selected],
    ] = True

    trunk_wall[
        yy[selected] + 1,
        xx[selected],
    ] = True

    return (
        base_wall,
        secondary_wall,
        trunk_wall,
    )


def _junction_mask(
    labels: np.ndarray,
) -> np.ndarray:
    """
    Detect true multi-cell vertices from 2x2 neighborhoods.

    Local reinforcement of these points keeps narrow branches mechanically
    joined even after stochastic removal of low-priority interfaces.
    """
    a = labels[:-1, :-1]
    b = labels[:-1, 1:]
    c = labels[1:, :-1]
    d = labels[1:, 1:]

    stacked = np.stack(
        (
            a,
            b,
            c,
            d,
        ),
        axis=0,
    )

    stacked.sort(
        axis=0
    )

    n_unique = (
        1
        + (
            stacked[1:, :, :]
            != stacked[:-1, :, :]
        ).sum(
            axis=0
        )
    )

    is_junction = (
        n_unique >= 3
    )

    junction = np.zeros_like(
        labels,
        dtype=bool,
    )

    junction[:-1, :-1] = (
        is_junction
    )

    return junction


# ============================================================================
# Connectivity cleanup
# ============================================================================

def _fill_small_voids(
    solid: np.ndarray,
) -> np.ndarray:
    """
    Fill only sub-resolution four-connected void defects.
    """
    labels, n_void = ndi.label(
        ~solid,
        structure=FOUR_CONNECTED,
    )

    if n_void == 0:
        return solid

    areas = np.bincount(
        labels.ravel()
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
        | fill[labels]
    )


def _largest_component(
    solid: np.ndarray,
) -> np.ndarray:
    """
    Retain the dominant four-connected solid component.
    """
    labels, n_components = ndi.label(
        solid,
        structure=FOUR_CONNECTED,
    )

    if n_components == 0:
        return np.zeros_like(
            solid,
            dtype=bool,
        )

    areas = np.bincount(
        labels.ravel()
    )

    areas[0] = 0

    largest = int(
        np.argmax(areas)
    )

    return (
        labels
        == largest
    )


def _spans_both_axes(
    solid: np.ndarray,
) -> bool:
    """
    The same four-connected solid component must touch:
        left + right
        top + bottom
    """
    labels, n_components = ndi.label(
        solid,
        structure=FOUR_CONNECTED,
    )

    if n_components != 1:
        return False

    left_right = (
        np.any(
            labels[:, 0] == 1
        )
        and
        np.any(
            labels[:, -1] == 1
        )
    )

    top_bottom = (
        np.any(
            labels[0, :] == 1
        )
        and
        np.any(
            labels[-1, :] == 1
        )
    )

    return bool(
        left_right
        and top_bottom
    )


def _clean_network(
    solid: np.ndarray,
) -> np.ndarray:
    solid = _fill_small_voids(
        solid
    )

    solid = _largest_component(
        solid
    )

    return solid


# ============================================================================
# Material-fraction correction
# ============================================================================

def _grow_to_pixel_count(
    solid: np.ndarray,
    target_count: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Add a small number of boundary pixels to reach target_count.

    New pixels preferentially have at least two four-connected solid
    neighbors, so this operation thickens existing struts/corners instead of
    growing one-pixel dangling branches.

    Because pixels are only added to the existing main component, connectivity
    and percolation cannot be lost.
    """
    solid = solid.copy()

    need = (
        int(target_count)
        - int(solid.sum())
    )

    if need <= 0:
        return solid

    # Smooth stochastic priority causes additions to occur in small coherent
    # patches rather than salt-and-pepper single pixels.
    priority = ndi.gaussian_filter(
        rng.standard_normal(
            solid.shape
        ),
        sigma=1.5,
        mode="reflect",
    )

    for required_neighbors in (
        3,
        2,
        1,
    ):
        while need > 0:

            neighbor_count = ndi.convolve(
                solid.astype(
                    np.uint8
                ),
                FOUR_NEIGHBOR_KERNEL,
                mode="constant",
                cval=0,
            )

            candidates = (
                (~solid)
                & (
                    neighbor_count
                    >= required_neighbors
                )
            )

            flat = np.flatnonzero(
                candidates
            )

            if flat.size == 0:
                break

            take_n = min(
                need,
                flat.size,
            )

            candidate_score = (
                priority.ravel()[flat]
                + 0.12
                * neighbor_count.ravel()[flat]
            )

            if take_n < flat.size:

                chosen_local = np.argpartition(
                    candidate_score,
                    -take_n,
                )[-take_n:]

                chosen = flat[
                    chosen_local
                ]

            else:
                chosen = flat

            solid.ravel()[
                chosen
            ] = True

            need -= len(
                chosen
            )

            if need <= 0:
                break

    return solid


# ============================================================================
# One procedural candidate
# ============================================================================

def _candidate(
    rng: np.random.Generator,
    adjustment_rng: np.random.Generator,
    target_fraction: float,
    n: int,
):
    labels = _partition_labels(
        rng,
        n,
    )

    (
        base_wall,
        secondary_wall,
        trunk_wall,
    ) = _interface_hierarchy(
        labels,
        rng,
    )

    junction = _junction_mask(
        labels
    )

    distance_base = ndi.distance_transform_edt(
        ~base_wall
    )

    if np.any(
        secondary_wall
    ):
        distance_secondary = ndi.distance_transform_edt(
            ~secondary_wall
        )
    else:
        distance_secondary = np.full(
            (n, n),
            np.inf,
        )

    if np.any(
        trunk_wall
    ):
        distance_trunk = ndi.distance_transform_edt(
            ~trunk_wall
        )
    else:
        distance_trunk = np.full(
            (n, n),
            np.inf,
        )

    if np.any(
        junction
    ):
        distance_junction = ndi.distance_transform_edt(
            ~junction
        )
    else:
        distance_junction = np.full(
            (n, n),
            np.inf,
        )

    target_count = int(
        np.rint(
            target_fraction
            * n
            * n
        )
    )

    best_under = None
    best_under_count = -1

    best_nearest = None
    best_nearest_error = np.inf

    scales = np.linspace(
        WIDTH_SCALE_MIN,
        WIDTH_SCALE_MAX,
        N_WIDTH_SCALES,
    )

    for scale in scales:

        solid = (
            distance_base
            <= BASE_HALF_WIDTH
            * scale
        )

        solid |= (
            distance_secondary
            <= SECONDARY_HALF_WIDTH
            * scale
        )

        solid |= (
            distance_trunk
            <= TRUNK_HALF_WIDTH
            * scale
        )

        solid |= (
            distance_junction
            <= JUNCTION_RADIUS
            * scale
        )

        solid = _clean_network(
            solid
        )

        if not _spans_both_axes(
            solid
        ):
            continue

        count = int(
            solid.sum()
        )

        error = abs(
            count
            - target_count
        )

        if error < best_nearest_error:
            best_nearest_error = error
            best_nearest = solid

        # Prefer a candidate just below the target.  It can be brought to the
        # target by connectivity-preserving thickening.
        if (
            count <= target_count
            and count > best_under_count
        ):
            best_under_count = count
            best_under = solid

    if best_under is not None:
        solid = best_under
    elif best_nearest is not None:
        solid = best_nearest
    else:
        return None

    if int(
        solid.sum()
    ) < target_count:

        solid = _grow_to_pixel_count(
            solid,
            target_count,
            adjustment_rng,
        )

    # Addition cannot disconnect the network, but explicitly verify anyway.
    solid = _largest_component(
        solid
    )

    if not _spans_both_axes(
        solid
    ):
        return None

    return solid


# ============================================================================
# Statistical selection metrics
# ============================================================================

def _radial_s2(
    solid: np.ndarray,
    radii: np.ndarray,
) -> np.ndarray:
    """
    Periodic FFT two-point correlation, radially averaged in one-pixel shells.

    This reproduces the usual discrete radial S2 definition:
        r - 0.5 <= radius < r + 0.5
    """
    a = solid.astype(
        np.float64
    )

    transform = np.fft.fftn(
        a
    )

    autocorrelation = np.fft.ifftn(
        transform
        * np.conj(transform)
    ).real

    autocorrelation /= (
        a.size
    )

    autocorrelation = np.fft.fftshift(
        autocorrelation
    )

    h, w = a.shape

    yy, xx = np.indices(
        a.shape
    )

    radial_distance = np.sqrt(
        (
            yy
            - h // 2
        ) ** 2
        +
        (
            xx
            - w // 2
        ) ** 2
    )

    values = []

    for radius in radii:

        shell = (
            (
                radial_distance
                >= radius - 0.5
            )
            &
            (
                radial_distance
                < radius + 0.5
            )
        )

        values.append(
            float(
                autocorrelation[
                    shell
                ].mean()
            )
        )

    return np.asarray(
        values,
        dtype=np.float64,
    )


def _lineal_one_direction(
    solid: np.ndarray,
    r: int,
    dy: int,
    dx: int,
) -> float:
    """
    Probability that every pixel on a unit-step digital segment is solid.

    Only the four principal unoriented line families are used by the
    candidate-selection surrogate.
    """
    h, w = solid.shape

    y0 = max(
        0,
        -dy * r,
    )

    y1 = min(
        h,
        h - dy * r,
    )

    x0 = max(
        0,
        -dx * r,
    )

    x1 = min(
        w,
        w - dx * r,
    )

    if (
        y1 <= y0
        or x1 <= x0
    ):
        return 0.0

    path = np.ones(
        (
            y1 - y0,
            x1 - x0,
        ),
        dtype=bool,
    )

    for k in range(
        r + 1
    ):

        ys = slice(
            y0 + dy * k,
            y1 + dy * k,
        )

        xs = slice(
            x0 + dx * k,
            x1 + dx * k,
        )

        path &= solid[
            ys,
            xs,
        ]

    return float(
        path.mean()
    )


def _directional_lineal_path(
    solid: np.ndarray,
    radii: np.ndarray,
) -> np.ndarray:
    """
    Four-direction lineal-path surrogate:
        horizontal
        vertical
        +45 degrees
        -45 degrees
    """
    directions = (
        (0, 1),
        (1, 0),
        (1, 1),
        (1, -1),
    )

    result = []

    for r in radii:

        values = [
            _lineal_one_direction(
                solid,
                int(r),
                dy,
                dx,
            )
            for dy, dx in directions
        ]

        result.append(
            float(
                np.mean(values)
            )
        )

    return np.asarray(
        result,
        dtype=np.float64,
    )


def _median_interior_pore_diameter(
    solid: np.ndarray,
) -> float:
    """
    Median diameter of the largest inscribed circle in each interior
    four-connected void region.

    Boundary-touching pores are excluded.
    """
    void = ~solid

    labels, n_void = ndi.label(
        void,
        structure=FOUR_CONNECTED,
    )

    if n_void == 0:
        return 0.0

    distance = ndi.distance_transform_edt(
        void
    )

    indices = np.arange(
        1,
        n_void + 1,
    )

    max_radius = ndi.maximum(
        distance,
        labels=labels,
        index=indices,
    )

    boundary_labels = set(
        np.unique(
            np.concatenate(
                (
                    labels[0, :],
                    labels[-1, :],
                    labels[:, 0],
                    labels[:, -1],
                )
            )
        ).tolist()
    )

    diameters = [
        2.0
        * float(
            max_radius[
                label_id - 1
            ]
        )
        for label_id in indices
        if label_id
        not in boundary_labels
    ]

    if not diameters:

        diameters = (
            2.0
            * np.asarray(
                max_radius,
                dtype=np.float64,
            )
        ).tolist()

    return float(
        np.median(
            diameters
        )
    )


def _candidate_score(
    solid: np.ndarray,
) -> float:
    """
    Compare only statistical summaries supplied in the development prompt.

    Lower is better.
    """
    s2 = _radial_s2(
        solid,
        S2_RADII,
    )

    lineal = _directional_lineal_path(
        solid,
        LINEAL_RADII,
    )

    pore_diameter = (
        _median_interior_pore_diameter(
            solid
        )
    )

    s2_rmse = float(
        np.sqrt(
            np.mean(
                (
                    s2
                    - TARGET_S2
                ) ** 2
            )
        )
    )

    lineal_rmse = float(
        np.sqrt(
            np.mean(
                (
                    lineal
                    - TARGET_LINEAL
                ) ** 2
            )
        )
    )

    pore_error = abs(
        pore_diameter
        - TARGET_MEDIAN_PORE_DIAMETER
    )

    # Scaling constants only balance the three terms; they have no geometric
    # content and do not encode target pixels.
    score = (
        s2_rmse
        / 0.010
        +
        0.80
        * lineal_rmse
        / 0.010
        +
        0.18
        * pore_error
        / 1.5
    )

    return float(
        score
    )


# ============================================================================
# Public generator
# ============================================================================

def generate_microstructure(
    seed: int,
    n: int = SIZE,
) -> np.ndarray:
    """
    Generate one validated realization for the requested seed.

    Seeds 0...19 are used exactly as requested.  A separate deterministic
    control RNG handles the small volume-fraction adjustment so it does not
    consume the topology RNG before the first cellular realization.
    """
    topology_rng = np.random.default_rng(
        seed
    )

    control_rng = np.random.default_rng(
        100000
        + seed
    )

    target_fraction = float(
        np.clip(
            TARGET_SOLID_FRACTION
            + TARGET_SOLID_STD
            * control_rng.standard_normal(),
            TARGET_SOLID_MIN,
            TARGET_SOLID_MAX,
        )
    )

    best = None
    best_score = np.inf
    n_valid = 0

    for _ in range(
        MAX_DRAWS_PER_SEED
    ):

        candidate = _candidate(
            topology_rng,
            control_rng,
            target_fraction,
            n,
        )

        if candidate is None:
            continue

        if not _spans_both_axes(
            candidate
        ):
            continue

        score = _candidate_score(
            candidate
        )

        n_valid += 1

        if score < best_score:
            best_score = score
            best = candidate

        if (
            n_valid
            >= CANDIDATES_PER_SEED
        ):
            break

    if best is None:
        raise RuntimeError(
            "Could not produce a validated "
            f"4-connected, doubly spanning "
            f"network for seed {seed}."
        )

    best = _largest_component(
        best
    )

    if not _spans_both_axes(
        best
    ):
        raise RuntimeError(
            "Final connectivity validation "
            f"failed for seed {seed}."
        )

    return best.astype(
        np.uint8
    )


# ============================================================================
# Output helpers
# ============================================================================

def _save_sample(
    arr: np.ndarray,
    seed: int,
    out_dir: Path,
) -> None:
    """
    Save both required representations.

    NPY:
        solid = 1
        void  = 0

    PNG:
        solid = 255 / white
        void  =   0 / black
    """
    stem = (
        f"sample_seed_{seed:02d}"
    )

    np.save(
        out_dir
        / f"{stem}.npy",
        arr.astype(
            np.uint8,
            copy=False,
        ),
    )

    png = (
        arr * 255
    ).astype(
        np.uint8
    )

    Image.fromarray(
        png,
        mode="L",
    ).save(
        out_dir
        / f"{stem}.png"
    )


def _component_count(
    arr: np.ndarray,
) -> int:
    _, n_components = ndi.label(
        arr.astype(bool),
        structure=FOUR_CONNECTED,
    )

    return int(
        n_components
    )


def _void_count(
    arr: np.ndarray,
) -> int:
    _, n_void = ndi.label(
        arr == 0,
        structure=FOUR_CONNECTED,
    )

    return int(
        n_void
    )


# ============================================================================
# Main
# ============================================================================

def main() -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    seen_hashes = set()

    # Exactly the requested random seeds.
    for seed in range(
        N_SAMPLES
    ):

        arr = generate_microstructure(
            seed,
            SIZE,
        )

        # ------------------------------------------------------------
        # Required invariants
        # ------------------------------------------------------------

        if arr.shape != (
            SIZE,
            SIZE,
        ):
            raise AssertionError(
                "Unexpected output dimensions."
            )

        if arr.dtype != np.uint8:
            raise AssertionError(
                "Output dtype must be uint8."
            )

        if not np.all(
            (arr == 0)
            | (arr == 1)
        ):
            raise AssertionError(
                "Output is not binary."
            )

        if _component_count(
            arr
        ) != 1:
            raise AssertionError(
                "Final solid phase is not one "
                "4-connected component."
            )

        if not _spans_both_axes(
            arr.astype(bool)
        ):
            raise AssertionError(
                "Final solid network does not "
                "span both image axes."
            )

        # ------------------------------------------------------------
        # Guarantee genuinely distinct output arrays.
        # ------------------------------------------------------------

        digest = hashlib.sha256(
            arr.tobytes()
        ).hexdigest()

        if digest in seen_hashes:
            raise RuntimeError(
                "Duplicate realization detected "
                f"for seed {seed}."
            )

        seen_hashes.add(
            digest
        )

        # ------------------------------------------------------------
        # Save NPY + PNG.
        # ------------------------------------------------------------

        _save_sample(
            arr,
            seed,
            OUTPUT_DIR,
        )

        pore_diameter = (
            _median_interior_pore_diameter(
                arr.astype(bool)
            )
        )

        print(
            f"seed={seed:02d}  "
            f"solid_fraction={arr.mean():.4f}  "
            f"solid_components={_component_count(arr)}  "
            f"void_regions={_void_count(arr):3d}  "
            f"median_pore_diameter={pore_diameter:.3f}"
        )


if __name__ == "__main__":
    main()