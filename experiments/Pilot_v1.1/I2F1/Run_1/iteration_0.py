#!/usr/bin/env python3
"""
Procedural generator for a 256x256 two-phase disordered mechanical
metamaterial. Solid is stored as 1 (white in PNG); void is 0 (black).

Algorithm
---------
1. Generate a blue-noise-like set of cell nuclei by rejection sampling.
2. Build a mildly anisotropic Voronoi tessellation, then warp it with two
   correlated random displacement fields. The thick cell boundaries form the
   primary load-bearing vein network.
3. Optionally grow short, curved, dead-end secondary veins into some larger
   pores to create a leaf-vein branching character without fully subdividing
   every pore.
4. Grow the connected primary network with a spatially correlated width field.
   A priority flood keeps the solid 4-connected while targeting the requested
   number of primary-network pixels.
5. Add a few small, isolated solid inclusions in deep pore interiors. Their
   total area is chosen from the target largest-component fraction, leaving
   one dominant 4-connected network. The dominant network is explicitly made
   to span left-right and top-bottom.
6. For each requested seed, generate several fully procedural candidates and
   retain the one whose measured strut/pore descriptors and periodic radial
   two-point correlation best match the supplied numerical targets.

The script never reads a reference image and uses no external data or models.

Dependencies: numpy, scipy, scikit-image, Pillow
"""

from __future__ import annotations

import heapq
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.draw import line as draw_line
from skimage.morphology import skeletonize
from skimage.segmentation import find_boundaries


# ----------------------------- user controls ----------------------------- #

SIZE = 256
SEEDS = range(20)                 # required seeds 0, 1, ..., 19
OUT_DIR = Path("generated_microstructures")

# More trials give tighter statistical matching at the cost of runtime.
TRIALS_PER_SEED = 20

# Target descriptors.
TARGET_PHI = 0.394699
TARGET_LARGEST = 0.992384
TARGET_TMEAN = 6.53986
TARGET_TP10 = 4.0
TARGET_PORE_MED = 16.4924

RADII = (0, 1, 2, 4, 8, 16, 32, 64)
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
    dtype=float,
)

# Supplied lineal-path targets. The morphology controls that mainly affect
# these values are branch probability, width amplitude, cell spacing, and
# warp amplitude.
TARGET_LINEAL = np.array(
    [
        0.394699,
        0.351303,
        0.308788,
        0.227493,
        0.125214,
        0.054344,
        0.012596,
        0.000519,
    ],
    dtype=float,
)

# Candidate-search ranges.
#
# Cell count / spacing:
#     primary pore scale and oscillation in S2.
#
# Anisotropy:
#     directional organization; >1 makes cells mildly longer in x.
#
# Warp amplitudes:
#     tortuosity, irregularity, and non-polygonal vein character.
#
# Width amplitude / scale:
#     local strut-thickness variation.
#
# Branch probability:
#     short secondary leaf-vein branches and lineal-path decay.

CELLULAR_N_RANGE = (87, 100)       # upper endpoint excluded
BRANCHED_N_RANGE = (74, 89)

MIN_SPACING_RANGE = (17.0, 20.5)
ANISOTROPY_RANGE = (1.00, 1.25)

LARGE_WARP_RANGE = (0.70, 1.35)
SMALL_WARP_CELLULAR = (0.45, 1.15)
SMALL_WARP_BRANCHED = (0.45, 0.95)

WIDTH_AMPLITUDE_RANGE = (0.72, 0.95)
WIDTH_SCALE_RANGE = (8.0, 12.0)

BRANCH_PROB_RANGE = (0.16, 0.38)


# -------------------------- derived fixed values ------------------------- #

H = W = SIZE
NPIX = H * W

# Integer budgets implied by the supplied descriptors.
TOTAL_SOLID = int(round(TARGET_PHI * NPIX))
PRIMARY_SOLID = int(round(TOTAL_SOLID * TARGET_LARGEST))
ISLAND_SOLID = TOTAL_SOLID - PRIMARY_SOLID

# 4-connected neighborhood.
ST4 = ndi.generate_binary_structure(2, 1)

YY, XX = np.mgrid[0:H, 0:W]
PIXEL_COORDS = np.column_stack((YY.ravel(), XX.ravel()))

# Relative tolerances used only to rank stochastic candidates.
S2_TOL = np.array(
    [1.0, 0.0025, 0.0035, 0.0060, 0.0080, 0.0100, 0.0100, 0.0060]
)


# ---------------------------- basic utilities ---------------------------- #

def smooth_unit_noise(
    rng: np.random.Generator,
    sigma,
) -> np.ndarray:
    """Zero-mean, unit-standard-deviation correlated Gaussian field."""
    z = ndi.gaussian_filter(
        rng.standard_normal((H, W)),
        sigma=sigma,
        mode="reflect",
    )
    return (z - z.mean()) / (z.std() + 1.0e-12)


def poisson_points(
    rng: np.random.Generator,
    n: int,
    min_distance: float,
) -> np.ndarray:
    """
    Generate approximately blue-noise cell nuclei by staged rejection
    sampling.

    The minimum spacing is gradually relaxed only if required, preventing
    pathological rejection loops while retaining short-range order.
    """
    points: list[np.ndarray] = []
    dmin = float(min_distance)

    for _stage in range(6):
        for _ in range(50000):
            if len(points) >= n:
                break

            p = np.array(
                [
                    rng.uniform(0.0, H - 1.0),
                    rng.uniform(0.0, W - 1.0),
                ]
            )

            if not points:
                points.append(p)
                continue

            q = np.asarray(points)
            if np.all(
                np.sum((q - p) ** 2, axis=1) >= dmin ** 2
            ):
                points.append(p)

        if len(points) >= n:
            break

        dmin *= 0.92

    # Conservative fallback.
    while len(points) < n:
        p = np.array(
            [
                rng.uniform(0.0, H - 1.0),
                rng.uniform(0.0, W - 1.0),
            ]
        )

        if (
            not points
            or np.min(
                np.sum((np.asarray(points) - p) ** 2, axis=1)
            )
            > 4.0
        ):
            points.append(p)

    return np.asarray(points[:n], dtype=float)


def anisotropic_voronoi(
    points: np.ndarray,
    x_anisotropy: float,
) -> np.ndarray:
    """
    Nearest-nucleus labels using a weak anisotropic metric.

    x_anisotropy > 1 makes separation in x less costly and therefore tends
    to produce slightly longer features in the horizontal direction.
    """
    a = float(x_anisotropy)

    if abs(a - 1.0) < 1.0e-12:
        sample_coords = PIXEL_COORDS
        p = points
    else:
        sample_coords = np.column_stack(
            (YY.ravel(), XX.ravel() / a)
        )
        p = np.column_stack(
            (points[:, 0], points[:, 1] / a)
        )

    tree = cKDTree(p)
    _, labels = tree.query(sample_coords, k=1)

    return labels.reshape(H, W).astype(np.int32)


def largest_4_component(mask: np.ndarray) -> np.ndarray:
    """Return only the largest 4-connected component."""
    labels, n = ndi.label(mask, structure=ST4)

    if n == 0:
        raise RuntimeError("Empty backbone.")

    counts = np.bincount(labels.ravel())
    k = 1 + int(np.argmax(counts[1:]))

    return labels == k


def force_spanning(backbone: np.ndarray) -> np.ndarray:
    """
    Retain one 4-connected backbone and explicitly make it touch all four
    sides. Because it remains one component, this guarantees both LR and TB
    percolation.
    """
    b = largest_4_component(backbone)

    # Left.
    ys, xs = np.nonzero(b)
    i = int(np.argmin(xs))
    y, x = int(ys[i]), int(xs[i])
    b[y, :x + 1] = True

    # Right.
    ys, xs = np.nonzero(b)
    i = int(np.argmax(xs))
    y, x = int(ys[i]), int(xs[i])
    b[y, x:] = True

    # Top.
    ys, xs = np.nonzero(b)
    i = int(np.argmin(ys))
    y, x = int(ys[i]), int(xs[i])
    b[:y + 1, x] = True

    # Bottom.
    ys, xs = np.nonzero(b)
    i = int(np.argmax(ys))
    y, x = int(ys[i]), int(xs[i])
    b[y:, x] = True

    return largest_4_component(b)


# ----------------------- primary leaf-vein scaffold ---------------------- #

def primary_backbone(
    rng: np.random.Generator,
    n_cells: int,
    min_spacing: float,
    anisotropy: float,
    large_warp: float,
    small_warp: float,
) -> np.ndarray:
    """
    Build the main cellular/vein scaffold from a warped blue-noise Voronoi
    tessellation.
    """
    points = poisson_points(
        rng,
        n_cells,
        min_spacing,
    )

    labels = anisotropic_voronoi(
        points,
        anisotropy,
    )

    # Two spatial scales give broad directional meandering plus smaller,
    # more angular/organic edge perturbations.
    uy = (
        large_warp
        * smooth_unit_noise(rng, (14.0, 20.0))
        + small_warp
        * smooth_unit_noise(rng, (2.2, 3.0))
    )

    ux = (
        large_warp
        * smooth_unit_noise(rng, (20.0, 14.0))
        + small_warp
        * smooth_unit_noise(rng, (3.0, 2.2))
    )

    warped = ndi.map_coordinates(
        labels,
        [
            np.clip(YY + uy, 0.0, H - 1.0),
            np.clip(XX + ux, 0.0, W - 1.0),
        ],
        order=0,
        mode="nearest",
    )

    # Thick digital boundaries make a robust 4-connected cellular scaffold.
    boundary = find_boundaries(
        warped,
        connectivity=1,
        mode="thick",
    )

    return force_spanning(boundary)


def add_secondary_veins(
    backbone: np.ndarray,
    rng: np.random.Generator,
    probability: float,
) -> np.ndarray:
    """
    Grow short curved veins from existing walls toward the interiors of
    selected larger pores.

    They are deliberately dead-ended instead of spanning an entire pore,
    giving a branching leaf-vein character without turning every pore into
    small triangular cells.
    """
    if probability <= 0.0:
        return backbone

    b = backbone.copy()

    void_labels, nvoid = ndi.label(
        ~b,
        structure=ST4,
    )

    dvoid = ndi.distance_transform_edt(~b)

    max_radius = ndi.maximum(
        dvoid,
        labels=void_labels,
        index=np.arange(1, nvoid + 1),
    )

    # For every void pixel, coordinates of its nearest solid-backbone pixel.
    _, nearest = ndi.distance_transform_edt(
        ~b,
        return_indices=True,
    )

    # Larger pores are considered first.
    for idx in np.argsort(max_radius)[::-1]:
        label_id = int(idx + 1)
        radius = float(max_radius[idx])

        if radius < 7.0:
            continue

        p = min(
            0.90,
            probability * radius / 9.0,
        )

        if rng.random() > p:
            continue

        coords = np.argwhere(
            void_labels == label_id
        )

        if len(coords) == 0:
            continue

        vals = dvoid[
            void_labels == label_id
        ]

        cutoff = np.percentile(vals, 95.0)

        # Randomly choose one of the deep interior points rather than always
        # using exactly the distance-transform maximum.
        top = coords[vals >= cutoff]
        cy, cx = top[
            int(rng.integers(len(top)))
        ]

        cy = int(cy)
        cx = int(cx)

        # Nearest point on existing solid.
        by = int(nearest[0, cy, cx])
        bx = int(nearest[1, cy, cx])

        # Stop before crossing the entire pore.
        frac = float(
            rng.uniform(0.45, 0.78)
        )

        ey = by + frac * (cy - by)
        ex = bx + frac * (cx - bx)

        dy = ey - by
        dx = ex - bx
        length = math.hypot(dx, dy)

        if length < 2.0:
            continue

        # Curved quadratic Bezier path.
        ny = -dx / length
        nx = dy / length

        curve_offset = float(
            rng.normal(0.0, 1.2)
        )

        my = (
            0.5 * (by + ey)
            + curve_offset * ny
        )

        mx = (
            0.5 * (bx + ex)
            + curve_offset * nx
        )

        t = np.linspace(
            0.0,
            1.0,
            max(4, int(2.0 * length)),
        )

        ycurve = (
            (1.0 - t) ** 2 * by
            + 2.0 * (1.0 - t) * t * my
            + t ** 2 * ey
        )

        xcurve = (
            (1.0 - t) ** 2 * bx
            + 2.0 * (1.0 - t) * t * mx
            + t ** 2 * ex
        )

        pts = np.column_stack(
            (
                np.rint(ycurve).astype(int),
                np.rint(xcurve).astype(int),
            )
        )

        pts[:, 0] = np.clip(
            pts[:, 0],
            0,
            H - 1,
        )

        pts[:, 1] = np.clip(
            pts[:, 1],
            0,
            W - 1,
        )

        for j in range(len(pts) - 1):
            rr, cc = draw_line(
                pts[j, 0],
                pts[j, 1],
                pts[j + 1, 0],
                pts[j + 1, 1],
            )

            b[rr, cc] = True

    return force_spanning(b)


# -------------------- variable-width connected thickening ---------------- #

def connected_priority_fill(
    backbone: np.ndarray,
    score: np.ndarray,
    target_count: int,
) -> np.ndarray:
    """
    Grow from the backbone in priority order while always using 4-neighbor
    growth. This makes the requested primary solid exactly one connected
    component.
    """
    b = force_spanning(backbone)

    if int(b.sum()) > target_count:
        raise RuntimeError(
            "Backbone is denser than requested primary solid."
        )

    solid = b.copy()

    in_heap = np.zeros(
        (H, W),
        dtype=bool,
    )

    heap: list[
        tuple[float, int, int]
    ] = []

    frontier = (
        ndi.binary_dilation(
            solid,
            structure=ST4,
        )
        & ~solid
    )

    ys, xs = np.nonzero(frontier)

    for y, x in zip(ys, xs):
        heapq.heappush(
            heap,
            (
                float(score[y, x]),
                int(y),
                int(x),
            ),
        )
        in_heap[y, x] = True

    count = int(solid.sum())

    while count < target_count:
        if not heap:
            raise RuntimeError(
                "Connected growth frontier exhausted."
            )

        _, y, x = heapq.heappop(heap)

        if solid[y, x]:
            continue

        solid[y, x] = True
        count += 1

        for yy, xx in (
            (y - 1, x),
            (y + 1, x),
            (y, x - 1),
            (y, x + 1),
        ):
            if (
                0 <= yy < H
                and 0 <= xx < W
                and not solid[yy, xx]
                and not in_heap[yy, xx]
            ):
                heapq.heappush(
                    heap,
                    (
                        float(score[yy, xx]),
                        yy,
                        xx,
                    ),
                )

                in_heap[yy, xx] = True

    return solid


# ------------------------ small isolated inclusions ---------------------- #

def grow_island(
    center: tuple[int, int],
    size: int,
    safe: np.ndarray,
    banned: np.ndarray,
    rng: np.random.Generator,
) -> np.ndarray | None:
    """
    Priority-grow one compact, irregular, 4-connected solid island.
    """
    cy, cx = center

    theta = float(
        rng.uniform(0.0, math.pi)
    )

    ct = math.cos(theta)
    st = math.sin(theta)

    aspect = float(
        np.exp(
            rng.normal(0.0, 0.22)
        )
    )

    heap: list[
        tuple[float, int, int]
    ] = [
        (0.0, cy, cx)
    ]

    seen: set[
        tuple[int, int]
    ] = set()

    chosen: list[
        tuple[int, int]
    ] = []

    while heap and len(chosen) < size:
        _, y, x = heapq.heappop(heap)

        if (y, x) in seen:
            continue

        seen.add((y, x))

        if (
            not safe[y, x]
            or banned[y, x]
        ):
            continue

        chosen.append((y, x))

        for yy, xx in (
            (y - 1, x),
            (y + 1, x),
            (y, x - 1),
            (y, x + 1),
        ):
            if not (
                0 <= yy < H
                and 0 <= xx < W
            ):
                continue

            if (
                (yy, xx) in seen
                or not safe[yy, xx]
                or banned[yy, xx]
            ):
                continue

            dy = yy - cy
            dx = xx - cx

            # Rotated elliptical distance plus small stochastic perturbation.
            u = ct * dx + st * dy
            v = -st * dx + ct * dy

            q = (
                (u / aspect) ** 2
                + (v * aspect) ** 2
            )

            q += float(
                rng.uniform(0.0, 0.75)
            )

            heapq.heappush(
                heap,
                (
                    q,
                    yy,
                    xx,
                ),
            )

    if len(chosen) != size:
        return None

    island = np.zeros(
        (H, W),
        dtype=bool,
    )

    ys, xs = zip(*chosen)

    island[
        np.asarray(ys),
        np.asarray(xs),
    ] = True

    return island


def add_isolated_islands(
    primary: np.ndarray,
    rng: np.random.Generator,
    budget: int,
) -> np.ndarray:
    """
    Add 4-6 stochastic disconnected blobs whose total pixel count is exactly
    the area outside the target dominant component.
    """
    if budget <= 0:
        return primary.copy()

    n_islands = int(
        rng.integers(4, 7)
    )

    minimum_each = min(
        18,
        max(
            1,
            budget // (2 * n_islands),
        ),
    )

    remaining = (
        budget
        - n_islands * minimum_each
    )

    weights = rng.dirichlet(
        np.full(
            n_islands,
            2.0,
        )
    )

    extra = np.floor(
        weights * remaining
    ).astype(int)

    for i in range(
        remaining - int(extra.sum())
    ):
        extra[
            i % n_islands
        ] += 1

    sizes = list(
        (
            extra
            + minimum_each
        ).astype(int)
    )

    rng.shuffle(sizes)

    # Distance into void from main network.
    dmain = ndi.distance_transform_edt(
        ~primary
    )

    # Keep islands away from the load-bearing network.
    safe = dmain >= 2.5

    banned = ndi.binary_dilation(
        primary,
        structure=np.ones(
            (3, 3),
            bool,
        ),
    )

    islands = np.zeros(
        (H, W),
        dtype=bool,
    )

    for size in sizes:
        placed = False

        for _ in range(250):
            clearance = max(
                4.0,
                0.55 * math.sqrt(size),
            )

            candidates = np.argwhere(
                safe
                & ~banned
                & (dmain >= clearance)
            )

            if len(candidates) == 0:
                candidates = np.argwhere(
                    safe
                    & ~banned
                )

            if len(candidates) == 0:
                break

            cy, cx = candidates[
                int(
                    rng.integers(
                        len(candidates)
                    )
                )
            ]

            island = grow_island(
                (
                    int(cy),
                    int(cx),
                ),
                size,
                safe,
                banned,
                rng,
            )

            if island is None:
                continue

            # Require a one-pixel 4-neighbor moat.
            if np.any(
                ndi.binary_dilation(
                    island,
                    structure=ST4,
                )
                & (
                    primary
                    | islands
                )
            ):
                continue

            islands |= island

            banned |= ndi.binary_dilation(
                island,
                structure=np.ones(
                    (3, 3),
                    bool,
                ),
            )

            placed = True
            break

        if not placed:
            raise RuntimeError(
                "Unable to place isolated solid island."
            )

    out = primary | islands

    if (
        int(out.sum())
        != int(primary.sum()) + budget
    ):
        raise RuntimeError(
            "Island pixel accounting failed."
        )

    return out


# --------------------------- candidate creation -------------------------- #

def make_candidate(
    rng: np.random.Generator,
    *,
    n_cells: int,
    min_spacing: float,
    anisotropy: float,
    large_warp: float,
    small_warp: float,
    width_amplitude: float,
    width_scale: float,
    branch_probability: float,
) -> np.ndarray:
    """
    Create one fully procedural candidate.

    No reference data or target pixels are used: only stochastic fields,
    point processes, geometry, and the scalar target descriptors.
    """
    backbone = primary_backbone(
        rng,
        n_cells,
        min_spacing,
        anisotropy,
        large_warp,
        small_warp,
    )

    backbone = add_secondary_veins(
        backbone,
        rng,
        branch_probability,
    )

    # Distance from the vein scaffold.
    d = ndi.distance_transform_edt(
        ~backbone
    )

    # Smooth spatial width variation.
    width_noise = smooth_unit_noise(
        rng,
        (
            width_scale,
            1.12 * width_scale,
        ),
    )

    # Lower scores are filled first. Distance gives normal dilation; the
    # correlated perturbation makes the strut width vary smoothly.
    width_score = (
        d
        - width_amplitude * width_noise
    )

    primary = connected_priority_fill(
        backbone,
        width_score,
        PRIMARY_SOLID,
    )

    result = add_isolated_islands(
        primary,
        rng,
        ISLAND_SOLID,
    )

    return result.astype(np.uint8)


# ------------------------- numerical descriptors ------------------------- #

def radial_offsets(
    r: int,
) -> list[tuple[int, int]]:
    """
    Integer displacement vectors in a rounded Euclidean radial shell.

    For example, r=1 contains all eight nearest/diagonal neighbors.
    """
    if r == 0:
        return [(0, 0)]

    R = int(
        math.ceil(
            r + 0.5
        )
    )

    out = []

    for dy in range(
        -R,
        R + 1,
    ):
        for dx in range(
            -R,
            R + 1,
        ):
            if (
                dx == 0
                and dy == 0
            ):
                continue

            rho = math.hypot(
                dx,
                dy,
            )

            if (
                r - 0.5
                <= rho
                < r + 0.5
            ):
                out.append(
                    (dy, dx)
                )

    return out


RADIAL_OFFSETS = {
    r: radial_offsets(r)
    for r in RADII
}


def two_point_correlation(
    binary: np.ndarray,
) -> np.ndarray:
    """
    Periodic radial two-point solid-solid correlation.

    FFT autocorrelation makes candidate evaluation much faster than explicitly
    rolling the image for every displacement vector.
    """
    a = binary.astype(float)

    f = np.fft.fft2(a)

    ac = (
        np.fft.ifft2(
            f * np.conj(f)
        ).real
        / a.size
    )

    values = []

    for r in RADII:
        offsets = RADIAL_OFFSETS[r]

        values.append(
            float(
                np.mean(
                    [
                        ac[
                            dy % H,
                            dx % W,
                        ]
                        for dy, dx
                        in offsets
                    ]
                )
            )
        )

    return np.asarray(values)


def measured_descriptors(
    binary: np.ndarray,
) -> dict[str, float | bool]:
    """
    Measure the descriptors used during stochastic candidate selection.

    Strut thickness:
        skeletonize(solid), then 2*EDT(solid) evaluated on skeleton pixels.

    Pore diameter:
        each 4-connected void component receives diameter
        2*max(EDT(void)); the reported value is the component median.
    """
    a = binary.astype(bool)

    # Solid connectivity.
    labels, ncomp = ndi.label(
        a,
        structure=ST4,
    )

    counts = np.bincount(
        labels.ravel()
    )[1:]

    largest = float(
        counts.max()
        / a.sum()
    )

    # Strut thickness.
    skel = skeletonize(a)

    dsolid = ndi.distance_transform_edt(
        a
    )

    local_thickness = (
        2.0
        * dsolid[skel]
    )

    # Pore diameter.
    void_labels, nvoid = ndi.label(
        ~a,
        structure=ST4,
    )

    dvoid = ndi.distance_transform_edt(
        ~a
    )

    max_void_r = ndi.maximum(
        dvoid,
        labels=void_labels,
        index=np.arange(
            1,
            nvoid + 1,
        ),
    )

    pore_diameters = (
        2.0
        * np.asarray(max_void_r)
    )

    # Percolation.
    left = (
        set(
            np.unique(
                labels[:, 0]
            )
        )
        - {0}
    )

    right = (
        set(
            np.unique(
                labels[:, -1]
            )
        )
        - {0}
    )

    top = (
        set(
            np.unique(
                labels[0, :]
            )
        )
        - {0}
    )

    bottom = (
        set(
            np.unique(
                labels[-1, :]
            )
        )
        - {0}
    )

    return {
        "phi": float(
            a.mean()
        ),
        "largest": largest,
        "lr": bool(
            left & right
        ),
        "tb": bool(
            top & bottom
        ),
        "tmean": float(
            local_thickness.mean()
        ),
        "tp10": float(
            np.percentile(
                local_thickness,
                10.0,
            )
        ),
        "pore_med": float(
            np.median(
                pore_diameters
            )
        ),
        "nsolid_components": int(
            ncomp
        ),
        "nvoid_components": int(
            nvoid
        ),
    }


def candidate_score(
    binary: np.ndarray,
):
    """
    Dimensionless mismatch score used to select among independent procedural
    candidates for one requested seed.
    """
    d = measured_descriptors(
        binary
    )

    if not (
        d["lr"]
        and d["tb"]
    ):
        return (
            float("inf"),
            d,
            None,
        )

    # Exact phase budget.
    if (
        int(binary.sum())
        != TOTAL_SOLID
    ):
        return (
            float("inf"),
            d,
            None,
        )

    # Exact dominant-component pixel budget.
    expected_largest = (
        PRIMARY_SOLID
        / TOTAL_SOLID
    )

    if (
        abs(
            float(d["largest"])
            - expected_largest
        )
        > 1.0e-12
    ):
        return (
            float("inf"),
            d,
            None,
        )

    s2 = two_point_correlation(
        binary
    )

    score = (
        (
            (
                float(d["tmean"])
                - TARGET_TMEAN
            )
            / 0.18
        )
        ** 2
    )

    score += (
        0.90
        * (
            (
                float(d["tp10"])
                - TARGET_TP10
            )
            / 0.80
        )
        ** 2
    )

    score += (
        2.20
        * (
            (
                float(d["pore_med"])
                - TARGET_PORE_MED
            )
            / 1.20
        )
        ** 2
    )

    score += (
        0.50
        * float(
            np.sum(
                (
                    (
                        s2[1:]
                        - TARGET_S2[1:]
                    )
                    / S2_TOL[1:]
                )
                ** 2
            )
        )
    )

    return (
        float(score),
        d,
        s2,
    )


# ------------------------ stochastic parameter search -------------------- #

def draw_trial_parameters(
    master: np.random.Generator,
) -> dict:
    """
    Sample one parameter set.

    Roughly half of candidates are more purely cellular and half emphasize
    secondary branches. Candidate selection then chooses whichever realization
    most closely matches the descriptors for that seed.
    """
    if master.random() < 0.50:
        # More cellular network.
        n_cells = int(
            master.integers(
                *CELLULAR_N_RANGE
            )
        )

        branch_probability = (
            0.0
            if master.random() < 0.80
            else float(
                master.uniform(
                    0.04,
                    0.12,
                )
            )
        )

        small_warp = float(
            master.uniform(
                *SMALL_WARP_CELLULAR
            )
        )

    else:
        # Slightly coarser primary cells with more secondary branching.
        n_cells = int(
            master.integers(
                *BRANCHED_N_RANGE
            )
        )

        branch_probability = float(
            master.uniform(
                *BRANCH_PROB_RANGE
            )
        )

        small_warp = float(
            master.uniform(
                *SMALL_WARP_BRANCHED
            )
        )

    return {
        "n_cells": n_cells,
        "min_spacing": float(
            master.uniform(
                *MIN_SPACING_RANGE
            )
        ),
        "anisotropy": float(
            master.uniform(
                *ANISOTROPY_RANGE
            )
        ),
        "large_warp": float(
            master.uniform(
                *LARGE_WARP_RANGE
            )
        ),
        "small_warp": small_warp,
        "width_amplitude": float(
            master.uniform(
                *WIDTH_AMPLITUDE_RANGE
            )
        ),
        "width_scale": float(
            master.uniform(
                *WIDTH_SCALE_RANGE
            )
        ),
        "branch_probability": branch_probability,
    }


def generate_one(
    seed: int,
    trials: int = TRIALS_PER_SEED,
):
    """
    Generate one independent saved realization associated with `seed`.

    The seed controls a master RNG; all candidate sub-seeds and parameters are
    deterministic descendants of it, so rerunning the script reproduces the
    exact same twenty outputs.
    """
    master = np.random.default_rng(
        seed
    )

    best = None

    for _ in range(trials):
        params = draw_trial_parameters(
            master
        )

        trial_seed = int(
            master.integers(
                0,
                np.iinfo(
                    np.int64
                ).max,
            )
        )

        rng = np.random.default_rng(
            trial_seed
        )

        try:
            binary = make_candidate(
                rng,
                **params,
            )

            score, desc, s2 = candidate_score(
                binary
            )

        except (
            RuntimeError,
            ValueError,
        ):
            continue

        if (
            best is None
            or score < best[0]
        ):
            best = (
                score,
                binary,
                desc,
                s2,
                params,
            )

    if best is None:
        raise RuntimeError(
            f"No valid candidate was generated for seed {seed}."
        )

    return best


# ------------------------------- output ---------------------------------- #

def save_sample(
    binary: np.ndarray,
    seed: int,
    out_dir: Path,
) -> None:
    """
    Save:
      NPY: uint8, solid=1, void=0
      PNG: solid=255/white, void=0/black
    """
    stem = (
        f"microstructure_seed_{seed:02d}"
    )

    np.save(
        out_dir
        / f"{stem}.npy",
        binary.astype(
            np.uint8
        ),
    )

    Image.fromarray(
        (
            binary * 255
        ).astype(
            np.uint8
        )
    ).save(
        out_dir
        / f"{stem}.png"
    )


def main() -> None:
    OUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_desc = []
    all_s2 = []

    for seed in SEEDS:
        (
            score,
            binary,
            desc,
            s2,
            params,
        ) = generate_one(seed)

        save_sample(
            binary,
            seed,
            OUT_DIR,
        )

        all_desc.append(desc)
        all_s2.append(s2)

        print(
            f"seed {seed:02d}  "
            f"score={score:6.3f}  "
            f"phi={desc['phi']:.6f}  "
            f"LC={desc['largest']:.6f}  "
            f"LR={desc['lr']} "
            f"TB={desc['tb']}  "
            f"tmean={desc['tmean']:.3f}  "
            f"p10={desc['tp10']:.3f}  "
            f"pore_med={desc['pore_med']:.3f}"
        )

    mean_t = np.mean(
        [
            float(d["tmean"])
            for d in all_desc
        ]
    )

    mean_p10 = np.mean(
        [
            float(d["tp10"])
            for d in all_desc
        ]
    )

    mean_pore = np.mean(
        [
            float(d["pore_med"])
            for d in all_desc
        ]
    )

    mean_s2 = np.mean(
        np.vstack(all_s2),
        axis=0,
    )

    print("\nEnsemble summary")

    print(
        f"mean strut thickness: "
        f"{mean_t:.4f}  "
        f"(target {TARGET_TMEAN:.4f})"
    )

    print(
        f"mean p10 thickness:   "
        f"{mean_p10:.4f}  "
        f"(target {TARGET_TP10:.4f})"
    )

    print(
        f"mean pore diameter:   "
        f"{mean_pore:.4f}  "
        f"(target {TARGET_PORE_MED:.4f})"
    )

    print("mean S2:")

    for (
        r,
        value,
        target,
    ) in zip(
        RADII,
        mean_s2,
        TARGET_S2,
    ):
        print(
            f"  r={r:2d}: "
            f"{value:.6f}  "
            f"target={target:.6f}"
        )

    print(
        f"\nSaved 20 PNG/NPY pairs in: "
        f"{OUT_DIR.resolve()}"
    )


if __name__ == "__main__":
    main()