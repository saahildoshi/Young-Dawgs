#!/usr/bin/env python3
"""
Procedural generator for 2-D disordered mechanical metamaterials.
Revision 1.

Output convention
-----------------
solid = 1
void  = 0

Each run produces:
    generated_microstructures/sample_seed_00.png
    generated_microstructures/sample_seed_00.npy
    ...
    generated_microstructures/sample_seed_19.png
    generated_microstructures/sample_seed_19.npy

Algorithm
---------
1. Generate a jittered, randomly thinned lattice of pore generators, including
   generators outside the image boundary.

2. Construct a weighted L-infinity (Chebyshev) Voronoi-like partition.
   Compared with a smooth Euclidean Voronoi construction, this creates longer
   horizontal, vertical and diagonal interface runs.  This is useful for the
   lineal-path statistics and gives the network a more angular, vein-like
   character without imposing a deterministic grid.

3. Turn the interfaces into a hierarchical solid network.  Every interface
   receives a stochastic hierarchy level:
       - fine branch,
       - secondary vein,
       - primary/trunk vein.

   Long interfaces are preferentially promoted to secondary/trunk veins, with
   random modulation.  This concentrates solid material into persistent
   load-bearing paths instead of uniformly widening every wall.

4. Locally reinforce true multi-cell junctions.  This raises the mean local
   thickness while retaining thinner branch segments, helping maintain a
   lower 10th-percentile thickness.

5. Select a small global width multiplier for each realization so that the
   solid fraction stays near the desired value without fixing the topology.
   The topology, pore positions, hierarchy and branch organization remain
   stochastic for every seed.

6. Fill only tiny void defects, retain the dominant 4-connected solid
   component, and explicitly require the resulting network to span both
   horizontal and vertical axes.

Main adjustable parameters
--------------------------
CELL_SIZE
    Nominal spatial scale of the pore-generator lattice.

KEEP_PROB
    Fraction of lattice sites retained.  Together with CELL_SIZE, controls
    pore count and pore size.

GENERATOR_JITTER
    Positional disorder of the pore generators.

CELL_WEIGHT_STD
    Local stochastic variation of cell size.

ANISO_X, ANISO_Y
    Weak directional anisotropy.

BASE_HALF_WIDTH
    Width of the finer branches.

SECONDARY_HALF_WIDTH
    Width of secondary vein segments.

TRUNK_HALF_WIDTH
    Width of the longest / most persistent vein segments.

SECONDARY_FRACTION, TRUNK_FRACTION
    Fractions of interfaces promoted to wider hierarchy levels.

JUNCTION_RADIUS
    Additional reinforcement around true multi-cell junctions.

TARGET_SOLID_FRACTION
    Center of the narrow solid-fraction controller.

TARGET_SOLID_STD
    Small realization-to-realization variation in solid fraction.

The script is completely procedural.  It does not read a reference image,
external data, pretrained model, API, or internet resource at runtime.

Dependencies
------------
numpy
scipy
Pillow
"""

from pathlib import Path
import hashlib

import numpy as np
from scipy import ndimage as ndi
from PIL import Image


# ============================================================================
# Output configuration
# ============================================================================

SIZE = 256
N_SAMPLES = 20
OUTPUT_DIR = Path("generated_microstructures")


# ============================================================================
# Geometry parameters
# ============================================================================

# Pore-generator organization.
CELL_SIZE = 23.0
KEEP_PROB = 0.75
GENERATOR_JITTER = 0.42

# Weighted Chebyshev partition.
CELL_WEIGHT_STD = 0.10
ANISO_X = 1.08
ANISO_Y = 0.96

# Chunk size used while evaluating generator distances.
DISTANCE_CHUNK = 12


# ============================================================================
# Hierarchical strut-width parameters
# ============================================================================

# Fine branches remain deliberately narrower than primary veins.
BASE_HALF_WIDTH = 1.80

# Longer interfaces receive progressively larger widths.
SECONDARY_HALF_WIDTH = 3.05
TRUNK_HALF_WIDTH = 4.65

# Approximate fractions of graph edges assigned to these two upper levels.
# TRUNK_FRACTION is contained inside SECONDARY_FRACTION.
SECONDARY_FRACTION = 0.34
TRUNK_FRACTION = 0.11

# Random perturbation of the edge-length hierarchy.  Larger values make
# hierarchy selection less strongly determined by geometric edge length.
EDGE_PRIORITY_NOISE = 0.42

# Reinforcement of genuine >=3-cell vertices.
JUNCTION_RADIUS = 4.25


# ============================================================================
# Global morphology / validation parameters
# ============================================================================

# The topology remains stochastic; this merely keeps total material content
# in the desired narrow range.
TARGET_SOLID_FRACTION = 0.3947
TARGET_SOLID_STD = 0.0025
TARGET_SOLID_MIN = 0.388
TARGET_SOLID_MAX = 0.402

# Search range for a single realization-wide multiplier on all hierarchy
# widths.  A dense discrete search is robust to rasterization thresholds.
WIDTH_SCALE_MIN = 0.76
WIDTH_SCALE_MAX = 1.16
N_WIDTH_SCALES = 41

# Fill only genuinely tiny void artifacts.
MIN_VOID_AREA = 30

# A failed candidate is regenerated from the same seeded RNG stream.
MAX_ATTEMPTS = 12

FOUR_CONNECTED = ndi.generate_binary_structure(2, 1)


# ============================================================================
# Generator placement
# ============================================================================

def _make_generators(
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """
    Produce jittered stochastic pore generators.

    A ghost margin outside the image prevents artificial treatment of the
    image boundary and allows cell interfaces to enter/leave naturally.
    """
    c = CELL_SIZE

    xs = np.arange(-0.75 * c, n + 1.25 * c, c)
    ys = np.arange(-0.75 * c, n + 1.25 * c, c)

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

            points.append((x, y))

    if len(points) < 20:
        raise RuntimeError(
            "Too few pore generators. "
            "Increase KEEP_PROB or reduce CELL_SIZE."
        )

    return np.asarray(
        points,
        dtype=np.float64,
    )


# ============================================================================
# Directionally organized stochastic partition
# ============================================================================

def _partition_labels(
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """
    Create a weighted L-infinity Voronoi-like partition.

    The Chebyshev metric produces interfaces with a natural preference for
    horizontal, vertical, and +/-45-degree runs.  Jittered generators and
    stochastic cell weights prevent the result from becoming a regular grid.
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

    # Additive generator weights produce controlled cell-size disorder.
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
            (xx[None, :, :] - px)
            / ANISO_X
        )

        dy = np.abs(
            (yy[None, :, :] - py)
            / ANISO_Y
        )

        # Exact L-infinity / Chebyshev metric.
        d = np.maximum(
            dx,
            dy,
        )

        # Dimensionless additive cell weights.
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
# Interface graph and hierarchy
# ============================================================================

def _edge_code(
    a: np.ndarray,
    b: np.ndarray,
    n_labels: int,
) -> np.ndarray:
    """
    Unique deterministic code for an unordered pair of cell labels.
    """
    lo = np.minimum(
        a,
        b,
    ).astype(np.int64)

    hi = np.maximum(
        a,
        b,
    ).astype(np.int64)

    return (
        lo * n_labels
        + hi
    )


def _interface_hierarchy(
    labels: np.ndarray,
    rng: np.random.Generator,
):
    """
    Build the primitive wall plus secondary/trunk masks.

    Long interfaces have greater probability of becoming primary load paths.
    Random multiplicative modulation prevents identical hierarchy selection
    among samples with similar geometric edge lengths.
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

    # ---------------------------------------------------------------
    # Collect all neighboring label-pair codes.
    # ---------------------------------------------------------------

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
    ).astype(np.float64)

    present_codes = np.flatnonzero(
        counts > 0
    )

    # ---------------------------------------------------------------
    # Hierarchy priority.
    #
    # Interface length is the principal term.  A lognormal multiplier
    # preserves randomness while retaining a preference for long veins.
    # ---------------------------------------------------------------

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

    n_trunk = max(
        1,
        int(
            np.rint(
                TRUNK_FRACTION
                * n_edges
            )
        ),
    )

    n_secondary = max(
        n_trunk,
        int(
            np.rint(
                SECONDARY_FRACTION
                * n_edges
            )
        ),
    )

    level = np.zeros(
        n_codes,
        dtype=np.uint8,
    )

    level[
        ranked_codes[:n_secondary]
    ] = 1

    level[
        ranked_codes[:n_trunk]
    ] = 2

    # ---------------------------------------------------------------
    # Rasterize the wall hierarchy.
    # ---------------------------------------------------------------

    base_wall = np.zeros(
        (n, n),
        dtype=bool,
    )

    secondary_wall = np.zeros(
        (n, n),
        dtype=bool,
    )

    trunk_wall = np.zeros(
        (n, n),
        dtype=bool,
    )

    # Left/right cell interfaces.
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

    base_wall[
        yy,
        xx,
    ] = True

    base_wall[
        yy,
        xx + 1,
    ] = True

    sel = (
        edge_levels >= 1
    )

    secondary_wall[
        yy[sel],
        xx[sel],
    ] = True

    secondary_wall[
        yy[sel],
        xx[sel] + 1,
    ] = True

    sel = (
        edge_levels >= 2
    )

    trunk_wall[
        yy[sel],
        xx[sel],
    ] = True

    trunk_wall[
        yy[sel],
        xx[sel] + 1,
    ] = True

    # Upper/lower cell interfaces.
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

    base_wall[
        yy,
        xx,
    ] = True

    base_wall[
        yy + 1,
        xx,
    ] = True

    sel = (
        edge_levels >= 1
    )

    secondary_wall[
        yy[sel],
        xx[sel],
    ] = True

    secondary_wall[
        yy[sel] + 1,
        xx[sel],
    ] = True

    sel = (
        edge_levels >= 2
    )

    trunk_wall[
        yy[sel],
        xx[sel],
    ] = True

    trunk_wall[
        yy[sel] + 1,
        xx[sel],
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
    Detect true multi-cell vertices.

    A 2x2 block containing at least three different partition labels is a
    topological branch/junction rather than merely a bend in one interface.
    """
    a = labels[:-1, :-1]
    b = labels[:-1, 1:]
    c = labels[1:, :-1]
    d = labels[1:, 1:]

    stack = np.stack(
        (
            a,
            b,
            c,
            d,
        ),
        axis=0,
    )

    stack.sort(
        axis=0
    )

    n_unique = (
        1
        + (
            stack[1:, :, :]
            != stack[:-1, :, :]
        ).sum(axis=0)
    )

    is_vertex = (
        n_unique >= 3
    )

    junction = np.zeros_like(
        labels,
        dtype=bool,
    )

    # A single representative raster point is sufficient; distance-based
    # reinforcement below expands it in a controlled way.
    junction[:-1, :-1] = (
        is_vertex
    )

    return junction


# ============================================================================
# Morphological cleanup and validation
# ============================================================================

def _fill_small_voids(
    solid: np.ndarray,
) -> np.ndarray:
    """
    Fill only tiny 4-connected void defects.
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


def _largest_4_connected_component(
    solid: np.ndarray,
) -> np.ndarray:
    """
    Keep the dominant 4-connected solid network and discard fragments.
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
    Require the same 4-connected component to span left-right and top-bottom.
    """
    labels, n_components = ndi.label(
        solid,
        structure=FOUR_CONNECTED,
    )

    if n_components != 1:
        return False

    component = 1

    left_right = (
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

    top_bottom = (
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
        left_right
        and top_bottom
    )


def _clean_network(
    solid: np.ndarray,
) -> np.ndarray:
    """
    Perform only connectivity-oriented cleanup; no smoothing is used.
    """
    solid = _fill_small_voids(
        solid
    )

    solid = _largest_4_connected_component(
        solid
    )

    return solid


# ============================================================================
# Hierarchical network construction
# ============================================================================

def _network_from_scale(
    distance_base: np.ndarray,
    distance_secondary: np.ndarray,
    distance_trunk: np.ndarray,
    distance_junction: np.ndarray,
    scale: float,
) -> np.ndarray:
    """
    Create one network realization for a given common width multiplier.
    """
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

    return solid


def _candidate(
    rng: np.random.Generator,
    n: int,
) -> np.ndarray:
    """
    Generate one stochastic candidate and select its width scale.

    The width-scale search changes only wall thickness.  It never changes
    pore-generator positions, topology, hierarchy, or target pixels.
    """
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

    # Distance fields are calculated once; candidate width scales are then
    # inexpensive threshold operations.
    distance_base = ndi.distance_transform_edt(
        ~base_wall
    )

    if np.any(
        secondary_wall
    ):
        distance_secondary = (
            ndi.distance_transform_edt(
                ~secondary_wall
            )
        )
    else:
        distance_secondary = np.full(
            (n, n),
            np.inf,
        )

    if np.any(
        trunk_wall
    ):
        distance_trunk = (
            ndi.distance_transform_edt(
                ~trunk_wall
            )
        )
    else:
        distance_trunk = np.full(
            (n, n),
            np.inf,
        )

    if np.any(
        junction
    ):
        distance_junction = (
            ndi.distance_transform_edt(
                ~junction
            )
        )
    else:
        distance_junction = np.full(
            (n, n),
            np.inf,
        )

    # A small target variation prevents the volume fraction itself from
    # becoming artificially identical among realizations.
    target_fraction = (
        TARGET_SOLID_FRACTION
        + TARGET_SOLID_STD
        * rng.standard_normal()
    )

    target_fraction = float(
        np.clip(
            target_fraction,
            TARGET_SOLID_MIN,
            TARGET_SOLID_MAX,
        )
    )

    scales = np.linspace(
        WIDTH_SCALE_MIN,
        WIDTH_SCALE_MAX,
        N_WIDTH_SCALES,
    )

    best_solid = None
    best_error = np.inf

    # Select using the cleaned and validated structure, so postprocessing
    # cannot move the material fraction unexpectedly.
    for scale in scales:

        solid = _network_from_scale(
            distance_base,
            distance_secondary,
            distance_trunk,
            distance_junction,
            float(scale),
        )

        solid = _clean_network(
            solid
        )

        if not _spans_both_axes(
            solid
        ):
            continue

        error = abs(
            float(solid.mean())
            - target_fraction
        )

        if error < best_error:
            best_error = error
            best_solid = solid

    if best_solid is None:
        return np.zeros(
            (n, n),
            dtype=bool,
        )

    return best_solid


# ============================================================================
# Public generator
# ============================================================================

def generate_microstructure(
    seed: int,
    n: int = SIZE,
) -> np.ndarray:
    """
    Generate one validated binary structure.

    The RNG is initialized directly with the requested seed.  Any rare retry
    continues from that same seeded random stream.
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

        if not np.any(
            solid
        ):
            continue

        # Explicit final enforcement of a single dominant component.
        solid = _largest_4_connected_component(
            solid
        )

        if not _spans_both_axes(
            solid
        ):
            continue

        # Reject pathological structures with implausible material fractions
        # rather than silently saving them.
        fraction = float(
            solid.mean()
        )

        if not (
            0.36
            <= fraction
            <= 0.43
        ):
            continue

        return solid.astype(
            np.uint8
        )

    raise RuntimeError(
        "Could not generate a validated horizontally and vertically "
        f"percolating realization for seed {seed}."
    )


# ============================================================================
# Output
# ============================================================================

def save_sample(
    arr: np.ndarray,
    seed: int,
    out_dir: Path,
) -> None:
    """
    Save one sample as both NPY and PNG.

    NPY:
        solid = 1
        void  = 0

    PNG:
        solid = white
        void  = black
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

    image = Image.fromarray(
        (
            arr * 255
        ).astype(
            np.uint8
        ),
        mode="L",
    )

    image.save(
        out_dir
        / f"{stem}.png"
    )


def _component_count(
    arr: np.ndarray,
) -> int:
    """
    Number of 4-connected solid components, for diagnostics.
    """
    _, n_components = ndi.label(
        arr.astype(bool),
        structure=FOUR_CONNECTED,
    )

    return int(
        n_components
    )


def _pore_count(
    arr: np.ndarray,
) -> int:
    """
    Number of 4-connected void regions, for diagnostics.
    """
    _, n_pores = ndi.label(
        arr == 0,
        structure=FOUR_CONNECTED,
    )

    return int(
        n_pores
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

    # Exactly the required random seeds: 0 through 19.
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

        if not _spans_both_axes(
            arr.astype(bool)
        ):
            raise AssertionError(
                "The final solid network does not span both axes."
            )

        if _component_count(
            arr
        ) != 1:
            raise AssertionError(
                "The final solid phase is not one 4-connected network."
            )

        # ------------------------------------------------------------
        # Ensure genuinely distinct stochastic realizations.
        # ------------------------------------------------------------

        digest = hashlib.sha256(
            arr.tobytes()
        ).hexdigest()

        if digest in seen_hashes:
            raise RuntimeError(
                "Duplicate realization "
                f"detected for seed {seed}."
            )

        seen_hashes.add(
            digest
        )

        # ------------------------------------------------------------
        # Save PNG + NPY.
        # ------------------------------------------------------------

        save_sample(
            arr,
            seed,
            OUTPUT_DIR,
        )

        print(
            f"seed={seed:02d}  "
            f"solid_fraction={arr.mean():.4f}  "
            f"solid_components={_component_count(arr)}  "
            f"void_regions={_pore_count(arr):3d}"
        )


if __name__ == "__main__":
    main()