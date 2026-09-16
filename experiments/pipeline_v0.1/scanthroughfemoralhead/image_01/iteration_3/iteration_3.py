#!/usr/bin/env python3
"""
Procedural generator for 256x256 binary disordered mechanical metamaterials.

Phase convention:
    solid = 1 = white
    void  = 0 = black

Default output:
    20 samples
    seeds 0 through 19
    256 x 256

Required command-line interface:
    --seed-start INTEGER
    --num-samples INTEGER
    --output-dir PATH

Example held-out run:
    python generator.py \
        --seed-start 100 \
        --num-samples 20 \
        --output-dir held_out

Dependencies:
    numpy
    scipy
    scikit-image
    Pillow

Algorithm
---------
1. A multiscale correlated Gaussian random field is generated procedurally.
2. A narrow band around its zero level set creates an irregular cellular
   strut network.
3. Nearby components are connected until one dominant 4-connected network
   spans both image axes.
4. The dominant component is explicitly connected to all four boundaries.
5. A controlled fraction of the naturally generated secondary struts is
   retained. Larger and more elongated components are preferentially retained.
   This preserves the good S2 and lineal-path morphology from the first
   revision.
6. The dominant component is grown to the exact requested mass while remaining
   separated from all retained secondary material.
7. The remainder of the detached-solid budget is generated as small rounded
   fragments, with only moderate preference for large void regions. This
   reduces the oversized pores of revision 1 without the severe pore
   fragmentation of revision 2.
8. Several completely procedural candidates are generated for each requested
   seed. The candidate with the closest S2 / strut-thickness descriptors is
   selected. No reference pixels or external data are used.

Principal adjustable parameters:
    FIELD_SIGMA
        Characteristic cellular scale.

    BASE_PRECURSOR_FRACTION
        Width/density of the initial zero-level band.

    NATURAL_RETENTION_FRACTION
        Fraction of the detached-solid budget preferably occupied by
        field-derived secondary struts. Increasing it moves morphology toward
        revision 1; decreasing it moves toward revision 2.

    DEEP_PORE_BIAS
        Probability that newly generated detached fragments are placed in a
        relatively large void region.

    BLOB_MEDIAN_RADIUS / BLOB_LOG_SIGMA
        Size distribution of newly generated detached fragments.

The script does not read the supplied reference image at runtime.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.draw import line
from skimage.morphology import skeletonize


# ============================================================================
# Fixed output specification
# ============================================================================

SIZE = 256
N_PIXELS = SIZE * SIZE

TARGET_SOLID_FRACTION = 0.310883
TARGET_LARGEST_COMPONENT_FRACTION = 0.876755
TARGET_MEAN_STRUT = 2.655

TARGET_SOLID_PIXELS = int(
    round(TARGET_SOLID_FRACTION * N_PIXELS)
)

TARGET_MAIN_PIXELS = int(
    round(
        TARGET_LARGEST_COMPONENT_FRACTION
        * TARGET_SOLID_PIXELS
    )
)

TARGET_DETACHED_PIXELS = (
    TARGET_SOLID_PIXELS
    - TARGET_MAIN_PIXELS
)


# S2 targets are used only for descriptor-based selection among independently
# generated procedural candidates.
S2_RADII = np.array(
    [0, 1, 2, 4, 8, 16, 32, 64],
    dtype=int,
)

S2_TARGET = np.array(
    [
        0.310883,
        0.213261,
        0.155861,
        0.103486,
        0.091954,
        0.096406,
        0.097038,
        0.096978,
    ],
    dtype=float,
)


FOUR_CONNECTED = ndi.generate_binary_structure(
    2,
    1,
)


# ============================================================================
# Morphology parameters
# ============================================================================

# Retained from the successful short-range morphology of revision 1.
FIELD_SIGMA = 2.40
BASE_PRECURSOR_FRACTION = 0.29

SECOND_SCALE_WEIGHT = 0.12
SECOND_SCALE_FACTOR = 1.80


# Network repair.
BRIDGE_BATCH = 8
MAX_BRIDGE_LOOPS = 100


# Main-network thickening.
GROWTH_NEIGHBOR_WEIGHT = 0.30


# ---------------------------------------------------------------------------
# Final-round detached-phase compromise.
#
# Revision 1 effectively retained nearly all naturally generated secondary
# struts and produced overly large pores.
#
# Revision 2 discarded essentially all of them and rebuilt the detached phase
# from compact fragments, producing overly small pores.
#
# Retaining roughly the middle portion, with preference for the long/large
# natural components, interpolates between those regimes while keeping more
# of the correlation structure of revision 1.
# ---------------------------------------------------------------------------

NATURAL_RETENTION_FRACTION = 0.45


# New detached fragments retain the radius statistics of earlier revisions.
BLOB_MEDIAN_RADIUS = 1.55
BLOB_LOG_SIGMA = 0.32
BLOB_RADIUS_MIN = 0.80
BLOB_RADIUS_MAX = 3.20


# Moderate rather than aggressive pore splitting.
DEEP_PORE_BIAS = 0.55
DEEP_PEAK_FILTER_SIZE = 7

# Rebuild candidate-center pools after several successful insertions so their
# geometry tracks the evolving void.
CENTER_REFRESH_EVERY = 12


# Detached components are prevented from occupying this boundary band.
# Therefore only the dominant component participates in boundary spanning.
DETACHED_BOUNDARY_MARGIN = 3


# Generate several independent procedural candidates and select using
# descriptors computed from the generated candidate itself.
CANDIDATES_PER_SEED = 3


# ============================================================================
# Randomness
# ============================================================================

def _seed_sequence(
    seed: int,
    salt: int,
    attempt: int = 0,
):
    """
    Deterministic random stream derived from the requested integer seed.

    Thus seed 100 always reproduces seed 100, while different seeds remain
    genuinely stochastic and independent.
    """
    if attempt == 0:
        return np.random.SeedSequence(
            [int(seed), int(salt)]
        )

    return np.random.SeedSequence(
        [
            int(seed),
            int(salt),
            int(attempt),
        ]
    )


# ============================================================================
# Connected-component utilities
# ============================================================================

def _component_labels(
    solid: np.ndarray,
):
    """
    Strict 4-connected component analysis.
    """
    labels, n_components = ndi.label(
        solid,
        structure=FOUR_CONNECTED,
    )

    sizes = np.bincount(
        labels.ravel(),
        minlength=n_components + 1,
    )

    if n_components == 0:
        return labels, sizes, 0

    main_id = (
        1
        + int(
            np.argmax(
                sizes[1:]
            )
        )
    )

    return labels, sizes, main_id


def _same_component_spans(
    labels: np.ndarray,
    component_id: int,
) -> bool:
    """
    Require the SAME strict 4-connected component to span left-right
    and top-bottom.
    """
    main = (
        labels
        == component_id
    )

    return bool(
        main[:, 0].any()
        and main[:, -1].any()
        and main[0, :].any()
        and main[-1, :].any()
    )


# ============================================================================
# Correlation-field precursor
# ============================================================================

def _make_precursor(
    seed: int,
    attempt: int,
) -> np.ndarray:
    """
    Create an organic cellular precursor from the zero-level neighborhood of
    a multiscale Gaussian random field.

    The narrow level-set band produces wall/strut morphology instead of
    isolated thresholded particles.
    """
    rng = np.random.default_rng(
        _seed_sequence(
            seed,
            0x1234,
            attempt,
        )
    )

    noise_1 = rng.standard_normal(
        (SIZE, SIZE)
    )

    noise_2 = rng.standard_normal(
        (SIZE, SIZE)
    )

    field = ndi.gaussian_filter(
        noise_1,
        sigma=FIELD_SIGMA,
        mode="wrap",
    )

    field += (
        SECOND_SCALE_WEIGHT
        * ndi.gaussian_filter(
            noise_2,
            sigma=(
                FIELD_SIGMA
                * SECOND_SCALE_FACTOR
            ),
            mode="wrap",
        )
    )

    field = (
        field - field.mean()
    ) / (
        field.std()
        + 1.0e-12
    )

    threshold = np.quantile(
        np.abs(field),
        BASE_PRECURSOR_FRACTION,
    )

    return (
        np.abs(field)
        <= threshold
    )


# ============================================================================
# 4-connected bridging
# ============================================================================

def _draw_four_connected_bridge(
    solid: np.ndarray,
    y0: int,
    x0: int,
    y1: int,
    x1: int,
    rng: np.random.Generator,
) -> None:
    """
    Draw a raster bridge whose diagonal steps are corner-filled so the bridge
    is guaranteed to be 4-connected.
    """
    rr, cc = line(
        y0,
        x0,
        y1,
        x1,
    )

    solid[
        rr,
        cc,
    ] = True

    for p in range(
        len(rr) - 1
    ):
        dy = abs(
            int(rr[p + 1])
            - int(rr[p])
        )

        dx = abs(
            int(cc[p + 1])
            - int(cc[p])
        )

        if (
            dy == 1
            and dx == 1
        ):
            if rng.random() < 0.5:
                solid[
                    rr[p],
                    cc[p + 1],
                ] = True
            else:
                solid[
                    rr[p + 1],
                    cc[p],
                ] = True


def _bridge_components(
    solid: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Connect nearby precursor pieces until one dominant component is present,
    reaches every image side, and the amount outside it is at most the final
    detached-solid budget.
    """
    solid = solid.copy()

    height, width = solid.shape

    for _ in range(
        MAX_BRIDGE_LOOPS
    ):
        (
            labels,
            sizes,
            main_id,
        ) = _component_labels(
            solid
        )

        if main_id == 0:
            break

        main = (
            labels
            == main_id
        )

        main_size = int(
            sizes[
                main_id
            ]
        )

        detached_size = (
            int(solid.sum())
            - main_size
        )

        touches_left = bool(
            main[:, 0].any()
        )

        touches_right = bool(
            main[:, -1].any()
        )

        touches_top = bool(
            main[0, :].any()
        )

        touches_bottom = bool(
            main[-1, :].any()
        )

        if (
            detached_size
            <= TARGET_DETACHED_PIXELS
            and touches_left
            and touches_right
            and touches_top
            and touches_bottom
        ):
            return solid

        (
            distance,
            nearest,
        ) = ndi.distance_transform_edt(
            ~main,
            return_indices=True,
        )

        component_ids = np.arange(
            1,
            len(sizes),
            dtype=int,
        )

        component_ids = (
            component_ids[
                component_ids
                != main_id
            ]
        )

        if (
            component_ids.size
            == 0
        ):
            break

        required = set()

        if not touches_left:
            required.update(
                np.unique(
                    labels[:, 0]
                ).tolist()
            )

        if not touches_right:
            required.update(
                np.unique(
                    labels[:, -1]
                ).tolist()
            )

        if not touches_top:
            required.update(
                np.unique(
                    labels[0, :]
                ).tolist()
            )

        if not touches_bottom:
            required.update(
                np.unique(
                    labels[-1, :]
                ).tolist()
            )

        required.discard(0)
        required.discard(
            main_id
        )

        if required:
            candidates = np.array(
                sorted(
                    required
                ),
                dtype=int,
            )
        else:
            candidates = (
                component_ids
            )

        min_distances = ndi.minimum(
            distance,
            labels=labels,
            index=candidates,
        )

        # Geometry is primary. Component size is only a very weak tiebreaker.
        order = np.argsort(
            min_distances
            + 0.0005
            * np.sqrt(
                sizes[
                    candidates
                ]
            )
        )

        pixels_to_absorb = max(
            0,
            detached_size
            - TARGET_DETACHED_PIXELS,
        )

        chosen = []
        absorbed = 0

        for j in order:
            component_id = int(
                candidates[
                    j
                ]
            )

            chosen.append(
                component_id
            )

            absorbed += int(
                sizes[
                    component_id
                ]
            )

            if required:

                if (
                    len(chosen)
                    >= min(
                        2,
                        BRIDGE_BATCH,
                    )
                ):
                    break

            else:

                if (
                    len(chosen)
                    >= BRIDGE_BATCH
                    or absorbed
                    >= max(
                        256,
                        0.35
                        * pixels_to_absorb,
                    )
                ):
                    break

        for component_id in chosen:

            ys, xs = np.where(
                labels
                == component_id
            )

            nearest_index = int(
                np.argmin(
                    distance[
                        ys,
                        xs,
                    ]
                )
            )

            y = int(
                ys[
                    nearest_index
                ]
            )

            x = int(
                xs[
                    nearest_index
                ]
            )

            main_y = int(
                nearest[
                    0,
                    y,
                    x,
                ]
            )

            main_x = int(
                nearest[
                    1,
                    y,
                    x,
                ]
            )

            _draw_four_connected_bridge(
                solid,
                y,
                x,
                main_y,
                main_x,
                rng,
            )

            # Mild local thickening keeps a newly constructed bridge from
            # looking like an artificial isolated one-pixel wire.
            if rng.random() < 0.5:

                rr, cc = line(
                    y,
                    x,
                    main_y,
                    main_x,
                )

                if len(rr) > 1:

                    p = (
                        len(rr)
                        // 2
                    )

                    cy = int(
                        rr[p]
                    )

                    cx = int(
                        cc[p]
                    )

                    neighbors = [
                        (
                            cy - 1,
                            cx,
                        ),
                        (
                            cy + 1,
                            cx,
                        ),
                        (
                            cy,
                            cx - 1,
                        ),
                        (
                            cy,
                            cx + 1,
                        ),
                    ]

                    rng.shuffle(
                        neighbors
                    )

                    for (
                        yy,
                        xx,
                    ) in neighbors:

                        if (
                            0
                            <= yy
                            < height
                            and 0
                            <= xx
                            < width
                        ):
                            solid[
                                yy,
                                xx,
                            ] = True
                            break

    return solid


# ============================================================================
# Robust spanning backbone
# ============================================================================

def _connect_to_side(
    main: np.ndarray,
    side: str,
) -> None:
    """
    Connect the current component to an image side with a strict Manhattan
    path and construct a small boundary cap.

    This makes boundary percolation unambiguous under strict 4-connectivity.
    """
    ys, xs = np.where(
        main
    )

    if len(ys) == 0:
        raise RuntimeError(
            "empty dominant component"
        )

    if side == "left":

        k = int(
            np.argmin(xs)
        )

        y = int(ys[k])
        x = int(xs[k])

        main[
            y,
            : x + 1,
        ] = True

        main[
            max(0, y - 1):
            min(SIZE, y + 2),
            0,
        ] = True

    elif side == "right":

        k = int(
            np.argmax(xs)
        )

        y = int(ys[k])
        x = int(xs[k])

        main[
            y,
            x:,
        ] = True

        main[
            max(0, y - 1):
            min(SIZE, y + 2),
            -1,
        ] = True

    elif side == "top":

        k = int(
            np.argmin(ys)
        )

        y = int(ys[k])
        x = int(xs[k])

        main[
            : y + 1,
            x,
        ] = True

        main[
            0,
            max(0, x - 1):
            min(SIZE, x + 2),
        ] = True

    elif side == "bottom":

        k = int(
            np.argmax(ys)
        )

        y = int(ys[k])
        x = int(xs[k])

        main[
            y:,
            x,
        ] = True

        main[
            -1,
            max(0, x - 1):
            min(SIZE, x + 2),
        ] = True

    else:
        raise ValueError(
            f"unknown side: {side}"
        )


def _make_robust_main(
    solid: np.ndarray,
) -> tuple:
    """
    Extract the largest component and explicitly make it span all four sides.

    The original non-main phase is also returned for subsequent selection of
    naturally generated detached struts.
    """
    (
        labels,
        sizes,
        main_id,
    ) = _component_labels(
        solid
    )

    if main_id == 0:
        raise RuntimeError(
            "no dominant component"
        )

    original_main = (
        labels
        == main_id
    )

    secondary = (
        solid
        & ~original_main
    )

    main = (
        original_main.copy()
    )

    # Always construct robust contacts rather than merely relying on a single
    # accidental edge pixel.
    for side in (
        "left",
        "right",
        "top",
        "bottom",
    ):
        _connect_to_side(
            main,
            side,
        )

    return (
        main,
        secondary,
    )


# ============================================================================
# Retain a controlled amount of natural secondary morphology
# ============================================================================

def _retain_natural_secondary(
    main: np.ndarray,
    secondary: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Keep a controlled fraction of the naturally generated disconnected struts.

    Larger and more elongated components are preferred because those pieces
    carry the cellular morphology and longer-range correlation of revision 1.

    Compact/small secondary pieces are preferentially replaced later.
    """
    secondary = (
        secondary.copy()
    )

    # Anything touching or immediately adjacent to the reconstructed main
    # component would alter the exact largest-component mass.
    blocked = ndi.binary_dilation(
        main,
        structure=FOUR_CONNECTED,
    )

    secondary[
        blocked
    ] = False

    # Detached material cannot touch any image boundary. Thus every boundary
    # contact in the finished sample belongs to the dominant component.
    m = (
        DETACHED_BOUNDARY_MARGIN
    )

    secondary[
        :m,
        :,
    ] = False

    secondary[
        -m:,
        :,
    ] = False

    secondary[
        :,
        :m,
    ] = False

    secondary[
        :,
        -m:,
    ] = False

    (
        labels,
        sizes,
        _,
    ) = _component_labels(
        secondary
    )

    component_ids = np.arange(
        1,
        len(sizes),
        dtype=int,
    )

    if (
        component_ids.size
        == 0
    ):
        return np.zeros_like(
            secondary,
            dtype=bool,
        )

    target_mass = int(
        round(
            NATURAL_RETENTION_FRACTION
            * TARGET_DETACHED_PIXELS
        )
    )

    properties = []

    for component_id in component_ids:

        size = int(
            sizes[
                component_id
            ]
        )

        if size <= 0:
            continue

        ys, xs = np.where(
            labels
            == component_id
        )

        height = (
            int(
                ys.max()
                - ys.min()
            )
            + 1
        )

        width = (
            int(
                xs.max()
                - xs.min()
            )
            + 1
        )

        span = float(
            max(
                height,
                width,
            )
        )

        # At fixed area, a larger bounding span indicates a more strut-like,
        # elongated component.
        elongation = (
            span
            / np.sqrt(
                float(size)
                + 1.0e-12
            )
        )

        score = (
            np.log1p(
                float(size)
            )
            + 0.70
            * elongation
            + 0.10
            * float(
                rng.standard_normal()
            )
        )

        properties.append(
            (
                score,
                component_id,
                size,
            )
        )

    properties.sort(
        reverse=True,
        key=lambda item: item[0],
    )

    retained = np.zeros_like(
        secondary,
        dtype=bool,
    )

    retained_mass = 0

    for (
        _,
        component_id,
        size,
    ) in properties:

        remaining = (
            target_mass
            - retained_mass
        )

        if remaining <= 0:
            break

        # Avoid one very large component causing a large overshoot of the
        # intended retention fraction.
        if (
            size > remaining
            and retained_mass > 0
        ):
            continue

        retained[
            labels
            == component_id
        ] = True

        retained_mass += size

    # One more strict separation pass.
    retained[
        ndi.binary_dilation(
            main,
            structure=FOUR_CONNECTED,
        )
    ] = False

    return retained


# ============================================================================
# Grow dominant component to exact mass
# ============================================================================

def _grow_main_to_target(
    main: np.ndarray,
    retained: np.ndarray,
    rng: np.random.Generator,
):
    """
    Grow only through 4-neighbor additions, so connectivity can never be lost.

    A one-pixel moat around retained detached material prevents accidental
    merging.
    """
    main = (
        main.copy()
    )

    if (
        int(main.sum())
        > TARGET_MAIN_PIXELS
    ):
        return None

    forbidden = ndi.binary_dilation(
        retained,
        structure=FOUR_CONNECTED,
    )

    for _ in range(100):

        main_size = int(
            main.sum()
        )

        if (
            main_size
            == TARGET_MAIN_PIXELS
        ):
            return main

        candidates = (
            ndi.binary_dilation(
                main,
                structure=FOUR_CONNECTED,
            )
            & ~main
            & ~retained
            & ~forbidden
        )

        coords = np.argwhere(
            candidates
        )

        if (
            len(coords)
            == 0
        ):
            return None

        remaining = (
            TARGET_MAIN_PIXELS
            - main_size
        )

        n8 = ndi.convolve(
            main.astype(
                np.uint8
            ),
            np.ones(
                (3, 3),
                dtype=np.uint8,
            ),
            mode="constant",
        )

        score = (
            GROWTH_NEIGHBOR_WEIGHT
            * n8[
                coords[:, 0],
                coords[:, 1],
            ].astype(float)
            + 0.75
            * rng.random(
                len(coords)
            )
        )

        k = min(
            remaining,
            len(coords),
            max(
                64,
                min(
                    1024,
                    remaining,
                ),
            ),
        )

        if (
            k
            == len(coords)
        ):
            selected = (
                coords
            )

        else:
            indices = np.argpartition(
                score,
                -k,
            )[-k:]

            selected = (
                coords[
                    indices
                ]
            )

        main[
            selected[:, 0],
            selected[:, 1],
        ] = True

    return None


# ============================================================================
# Detached replacement fragments
# ============================================================================

def _make_ellipse(
    cy: int,
    cx: int,
    rng: np.random.Generator,
):
    """
    Generate a small randomly oriented elliptical fragment.
    """
    radius = float(
        np.clip(
            rng.lognormal(
                np.log(
                    BLOB_MEDIAN_RADIUS
                ),
                BLOB_LOG_SIGMA,
            ),
            BLOB_RADIUS_MIN,
            BLOB_RADIUS_MAX,
        )
    )

    ry = (
        radius
        * float(
            rng.uniform(
                0.75,
                1.30,
            )
        )
    )

    rx = (
        radius
        * float(
            rng.uniform(
                0.75,
                1.30,
            )
        )
    )

    angle = float(
        rng.uniform(
            0.0,
            np.pi,
        )
    )

    pad = (
        int(
            np.ceil(
                max(
                    rx,
                    ry,
                )
            )
        )
        + 2
    )

    y0 = max(
        0,
        cy - pad,
    )

    y1 = min(
        SIZE,
        cy + pad + 1,
    )

    x0 = max(
        0,
        cx - pad,
    )

    x1 = min(
        SIZE,
        cx + pad + 1,
    )

    yy, xx = np.mgrid[
        y0:y1,
        x0:x1,
    ]

    dy = (
        yy - cy
    )

    dx = (
        xx - cx
    )

    c = np.cos(
        angle
    )

    s = np.sin(
        angle
    )

    u = (
        c * dx
        + s * dy
    )

    v = (
        -s * dx
        + c * dy
    )

    mask = (
        (u / rx) ** 2
        + (v / ry) ** 2
        <= 1.0
    )

    return (
        y0,
        y1,
        x0,
        x1,
        mask,
    )


def _trim_compact_mask(
    mask: np.ndarray,
    count: int,
    center_y: float,
    center_x: float,
) -> np.ndarray:
    """
    Trim a final fragment to an exact pixel count while keeping it compact.
    """
    n = int(
        mask.sum()
    )

    if n <= count:
        return mask

    coords = np.argwhere(
        mask
    )

    d2 = (
        (
            coords[:, 0]
            - center_y
        ) ** 2
        + (
            coords[:, 1]
            - center_x
        ) ** 2
    )

    keep = coords[
        np.argsort(
            d2
        )[:count]
    ]

    result = np.zeros_like(
        mask,
        dtype=bool,
    )

    result[
        keep[:, 0],
        keep[:, 1],
    ] = True

    return result


def _candidate_centers(
    solid: np.ndarray,
    rng: np.random.Generator,
):
    """
    Create:
        deep centers  -> centers of comparatively large pores
        random centers -> general legal detached-fragment locations
    """
    legal = (
        ~solid
        & ~ndi.binary_dilation(
            solid,
            structure=FOUR_CONNECTED,
        )
    )

    m = (
        DETACHED_BOUNDARY_MARGIN
    )

    legal[
        :m,
        :,
    ] = False

    legal[
        -m:,
        :,
    ] = False

    legal[
        :,
        :m,
    ] = False

    legal[
        :,
        -m:,
    ] = False

    random_centers = np.argwhere(
        legal
    )

    if (
        len(random_centers)
        > 0
    ):
        rng.shuffle(
            random_centers
        )

    distance = ndi.distance_transform_edt(
        ~solid
    )

    deep_mask = (
        legal
        & (
            distance
            == ndi.maximum_filter(
                distance,
                size=DEEP_PEAK_FILTER_SIZE,
                mode="nearest",
            )
        )
    )

    deep_centers = np.argwhere(
        deep_mask
    )

    if (
        len(deep_centers)
        > 0
    ):
        depth = distance[
            deep_centers[:, 0],
            deep_centers[:, 1],
        ]

        # Preserve stochasticity while still preferring the larger pores.
        ranking = (
            depth
            + 0.35
            * rng.random(
                len(deep_centers)
            )
        )

        deep_centers = deep_centers[
            np.argsort(
                ranking
            )[::-1]
        ]

    return (
        deep_centers,
        random_centers,
    )


def _insert_one_fragment(
    solid: np.ndarray,
    cy: int,
    cx: int,
    remaining: int,
    rng: np.random.Generator,
) -> int:
    """
    Try to insert one fragment without 4-neighbor contact to any existing
    solid. Returns the inserted pixel count, or zero on rejection.
    """
    (
        y0,
        y1,
        x0,
        x1,
        fragment,
    ) = _make_ellipse(
        cy,
        cx,
        rng,
    )

    if not fragment.any():
        return 0

    if (
        int(fragment.sum())
        > remaining
    ):
        fragment = _trim_compact_mask(
            fragment,
            remaining,
            center_y=(
                cy - y0
            ),
            center_x=(
                cx - x0
            ),
        )

    if not fragment.any():
        return 0

    guard = ndi.binary_dilation(
        fragment,
        structure=FOUR_CONNECTED,
    )

    sub = solid[
        y0:y1,
        x0:x1,
    ]

    if np.any(
        sub & guard
    ):
        return 0

    count = int(
        fragment.sum()
    )

    sub[
        fragment
    ] = True

    return count


def _fill_detached_budget(
    main: np.ndarray,
    retained: np.ndarray,
    rng: np.random.Generator,
):
    """
    Fill exactly TARGET_DETACHED_PIXELS.

    Unlike revision 2, only part of the detached phase consists of newly
    generated compact fragments. The long/large field-derived secondary
    pieces survive.

    New fragments have a moderate, not overwhelming, preference for deep void
    regions.
    """
    solid = (
        main
        | retained
    )

    solid = solid.copy()

    remaining = (
        TARGET_SOLID_PIXELS
        - int(
            solid.sum()
        )
    )

    if remaining < 0:
        return None

    successful_since_refresh = (
        CENTER_REFRESH_EVERY
    )

    deep = np.empty(
        (0, 2),
        dtype=int,
    )

    random_centers = np.empty(
        (0, 2),
        dtype=int,
    )

    deep_index = 0
    random_index = 0

    attempts = 0

    while (
        remaining > 0
        and attempts < 100000
    ):
        attempts += 1

        if (
            successful_since_refresh
            >= CENTER_REFRESH_EVERY
            or (
                deep_index
                >= len(deep)
                and random_index
                >= len(
                    random_centers
                )
            )
        ):
            (
                deep,
                random_centers,
            ) = _candidate_centers(
                solid,
                rng,
            )

            deep_index = 0
            random_index = 0
            successful_since_refresh = 0

        use_deep = (
            len(deep) > 0
            and deep_index
            < len(deep)
            and rng.random()
            < DEEP_PORE_BIAS
        )

        if use_deep:

            cy, cx = map(
                int,
                deep[
                    deep_index
                ],
            )

            deep_index += 1

        else:

            if (
                random_index
                >= len(
                    random_centers
                )
            ):
                successful_since_refresh = (
                    CENTER_REFRESH_EVERY
                )
                continue

            cy, cx = map(
                int,
                random_centers[
                    random_index
                ],
            )

            random_index += 1

        inserted = (
            _insert_one_fragment(
                solid,
                cy,
                cx,
                remaining,
                rng,
            )
        )

        if inserted > 0:
            remaining -= inserted
            successful_since_refresh += 1

    # Exact-count fallback. These isolated pixels are used only for a small
    # awkward terminal remainder.
    if remaining > 0:

        legal = (
            ~solid
            & ~ndi.binary_dilation(
                solid,
                structure=FOUR_CONNECTED,
            )
        )

        m = (
            DETACHED_BOUNDARY_MARGIN
        )

        legal[
            :m,
            :,
        ] = False

        legal[
            -m:,
            :,
        ] = False

        legal[
            :,
            :m,
        ] = False

        legal[
            :,
            -m:,
        ] = False

        coords = np.argwhere(
            legal
        )

        rng.shuffle(
            coords
        )

        for (
            y,
            x,
        ) in coords:

            if remaining <= 0:
                break

            y = int(y)
            x = int(x)

            vertical_contact = solid[
                max(0, y - 1):
                min(SIZE, y + 2),
                x,
            ].any()

            horizontal_contact = solid[
                y,
                max(0, x - 1):
                min(SIZE, x + 2),
            ].any()

            if (
                not vertical_contact
                and not horizontal_contact
            ):
                solid[
                    y,
                    x,
                ] = True

                remaining -= 1

    if remaining != 0:
        return None

    return solid


# ============================================================================
# Descriptor calculations for procedural candidate selection
# ============================================================================

def _shell_offsets(
    radius: int,
):
    """
    Integer lattice offsets in a radial shell [r-0.5, r+0.5).

    This permits a rotationally averaged periodic S2 calculation.
    """
    if radius == 0:
        return [
            (0, 0)
        ]

    limit = int(
        np.ceil(
            radius + 0.5
        )
    )

    offsets = []

    for dy in range(
        -limit,
        limit + 1,
    ):
        for dx in range(
            -limit,
            limit + 1,
        ):
            distance = np.sqrt(
                float(
                    dx * dx
                    + dy * dy
                )
            )

            if (
                abs(
                    distance
                    - radius
                )
                < 0.5
            ):
                offsets.append(
                    (
                        dy,
                        dx,
                    )
                )

    return offsets


S2_SHELLS = {
    int(radius):
    _shell_offsets(
        int(radius)
    )
    for radius in S2_RADII
}


def _s2_descriptor(
    solid: np.ndarray,
) -> np.ndarray:
    """
    Periodic two-point correlation evaluated with FFT autocorrelation and
    radial lattice-shell averaging.
    """
    phase = solid.astype(
        np.float64
    )

    spectrum = np.fft.fft2(
        phase
    )

    autocorrelation = np.fft.ifft2(
        spectrum
        * np.conjugate(
            spectrum
        )
    ).real

    autocorrelation /= float(
        phase.size
    )

    values = []

    for radius in S2_RADII:

        shell = S2_SHELLS[
            int(radius)
        ]

        shell_values = [
            autocorrelation[
                dy % SIZE,
                dx % SIZE,
            ]
            for (
                dy,
                dx,
            ) in shell
        ]

        values.append(
            float(
                np.mean(
                    shell_values
                )
            )
        )

    return np.array(
        values,
        dtype=float,
    )


def _mean_strut_thickness(
    solid: np.ndarray,
) -> float:
    """
    Local thickness proxy evaluated on the one-pixel solid skeleton.
    """
    distance = ndi.distance_transform_edt(
        solid
    )

    skeleton = skeletonize(
        solid
    )

    values = (
        2.0
        * distance[
            skeleton
        ]
    )

    if (
        values.size == 0
    ):
        return np.inf

    return float(
        np.mean(
            values
        )
    )


def _candidate_score(
    solid: np.ndarray,
) -> float:
    """
    Select among fully procedural candidates without comparing to reference
    pixels.

    S2 receives the dominant weight because it degraded substantially in
    revision 2. Strut thickness receives a smaller stabilizing penalty.
    """
    s2 = _s2_descriptor(
        solid
    )

    # r=0 is fixed exactly through solid volume fraction, so it supplies no
    # useful discrimination among candidates.
    s2_error = np.sqrt(
        np.mean(
            (
                (
                    s2[1:]
                    - S2_TARGET[1:]
                )
                / S2_TARGET[1:]
            )
            ** 2
        )
    )

    mean_strut = (
        _mean_strut_thickness(
            solid
        )
    )

    strut_error = abs(
        mean_strut
        - TARGET_MEAN_STRUT
    ) / TARGET_MEAN_STRUT

    return float(
        s2_error
        + 0.30
        * strut_error
    )


# ============================================================================
# Final validation
# ============================================================================

def _valid_structure(
    solid: np.ndarray,
) -> bool:
    """
    Hard output checks.

    In particular, the largest component itself—not merely arbitrary solid
    pixels—must span both image axes under strict 4-connectivity.
    """
    if solid.shape != (
        SIZE,
        SIZE,
    ):
        return False

    if (
        int(
            solid.sum()
        )
        != TARGET_SOLID_PIXELS
    ):
        return False

    (
        labels,
        sizes,
        main_id,
    ) = _component_labels(
        solid
    )

    if main_id == 0:
        return False

    if (
        int(
            sizes[
                main_id
            ]
        )
        != TARGET_MAIN_PIXELS
    ):
        return False

    if not _same_component_spans(
        labels,
        main_id,
    ):
        return False

    # Only the dominant network is allowed to occupy the image boundary.
    boundary_labels = np.unique(
        np.concatenate(
            [
                labels[:, 0],
                labels[:, -1],
                labels[0, :],
                labels[-1, :],
            ]
        )
    )

    boundary_labels = (
        boundary_labels[
            boundary_labels
            != 0
        ]
    )

    if np.any(
        boundary_labels
        != main_id
    ):
        return False

    return True


# ============================================================================
# Generate one procedural candidate
# ============================================================================

def _generate_candidate(
    seed: int,
    attempt: int,
):
    rng = np.random.default_rng(
        _seed_sequence(
            seed,
            0xA5A5,
            attempt,
        )
    )

    precursor = _make_precursor(
        seed,
        attempt,
    )

    precursor = _bridge_components(
        precursor,
        rng,
    )

    try:
        (
            main,
            secondary,
        ) = _make_robust_main(
            precursor
        )

    except RuntimeError:
        return None

    retained = (
        _retain_natural_secondary(
            main,
            secondary,
            rng,
        )
    )

    main = _grow_main_to_target(
        main,
        retained,
        rng,
    )

    if main is None:
        return None

    if (
        int(
            main.sum()
        )
        != TARGET_MAIN_PIXELS
    ):
        return None

    solid = _fill_detached_budget(
        main,
        retained,
        rng,
    )

    if solid is None:
        return None

    if not _valid_structure(
        solid
    ):
        return None

    return solid.astype(
        np.uint8
    )


# ============================================================================
# Generate one requested seed
# ============================================================================

def generate_microstructure(
    seed: int,
) -> np.ndarray:
    """
    Generate several independent procedural candidates for this seed and keep
    the one with the best generated-descriptor score.

    This remains deterministic: the same integer seed always generates the
    same candidate set and therefore the same selected output.
    """
    candidates = []

    # Try additional attempts only as a robustness reserve. Normally the first
    # CANDIDATES_PER_SEED valid candidates are sufficient.
    max_attempts = (
        CANDIDATES_PER_SEED
        + 5
    )

    for attempt in range(
        max_attempts
    ):
        candidate = (
            _generate_candidate(
                seed,
                attempt,
            )
        )

        if candidate is None:
            continue

        score = _candidate_score(
            candidate
        )

        candidates.append(
            (
                score,
                candidate,
            )
        )

        if (
            len(candidates)
            >= CANDIDATES_PER_SEED
        ):
            break

    if not candidates:
        raise RuntimeError(
            f"Failed to construct a valid "
            f"microstructure for seed {seed}."
        )

    candidates.sort(
        key=lambda item: item[0]
    )

    result = (
        candidates[0][1]
    )

    # Final independent hard check before any file is written.
    if not _valid_structure(
        result.astype(bool)
    ):
        raise RuntimeError(
            f"Internal final validation failed "
            f"for seed {seed}."
        )

    return result


# ============================================================================
# Output
# ============================================================================

def save_sample(
    sample: np.ndarray,
    seed: int,
    output_dir: Path,
) -> None:
    """
    Save:
        microstructure_seed_<seed>.npy
        microstructure_seed_<seed>.png

    NPY values:
        0 = void
        1 = solid

    PNG:
        0   = black void
        255 = white solid
    """
    stem = (
        f"microstructure_seed_{seed}"
    )

    np.save(
        output_dir
        / f"{stem}.npy",
        sample.astype(
            np.uint8,
            copy=False,
        ),
    )

    png = (
        sample.astype(
            np.uint8
        )
        * 255
    )

    Image.fromarray(
        png
    ).save(
        output_dir
        / f"{stem}.png"
    )


# ============================================================================
# Required command-line interface
# ============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Generate stochastic 256x256 "
            "binary mechanical-metamaterial "
            "microstructures."
        )
    )

    parser.add_argument(
        "--seed-start",
        type=int,
        default=0,
    )

    parser.add_argument(
        "--num-samples",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "microstructures"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if (
        args.num_samples
        < 1
    ):
        raise ValueError(
            "--num-samples must "
            "be at least 1"
        )

    args.output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    stop_seed = (
        args.seed_start
        + args.num_samples
    )

    for seed in range(
        args.seed_start,
        stop_seed,
    ):
        sample = (
            generate_microstructure(
                seed
            )
        )

        save_sample(
            sample,
            seed,
            args.output_dir,
        )

        (
            labels,
            sizes,
            main_id,
        ) = _component_labels(
            sample.astype(bool)
        )

        print(
            f"saved seed {seed}: "
            f"solid={int(sample.sum())}, "
            f"largest={int(sizes[main_id])}, "
            f"LR/TB=valid"
        )


if __name__ == "__main__":
    main()
