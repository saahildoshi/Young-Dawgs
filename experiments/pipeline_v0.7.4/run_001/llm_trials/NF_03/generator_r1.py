
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial.distance import cdist
from skimage.measure import regionprops

SIZE = 256
TARGET_REINFORCEMENT = 20731
MAX_CANDIDATES = 8

STRIP_LIMITS = {
    1: (0.79, 0.18, 0.78, 0.20),
    8: (0.74, 0.17, 0.75, 0.19),
    16: (0.71, 0.16, 0.69, 0.17),
    32: (0.64, 0.14, 0.63, 0.16),
}

CORRELATION_LAGS = (16, 32, 64)


def _heap_push(heap, item):
    heap.append(item)
    i = len(heap) - 1
    while i:
        parent = (i - 1) // 2
        if heap[parent] <= item:
            break
        heap[i] = heap[parent]
        i = parent
    heap[i] = item


def _heap_pop(heap):
    result = heap[0]
    last = heap.pop()
    if heap:
        n = len(heap)
        i = 0
        while 2 * i + 1 < n:
            child = 2 * i + 1
            if child + 1 < n and heap[child + 1] < heap[child]:
                child += 1
            if last <= heap[child]:
                break
            heap[i] = heap[child]
            i = child
        heap[i] = last
    return result


def _make_sites(rng):
    """
    Perturbed finite point process.

    Increased positional disorder relative to the initial
    generator reduces regularity of inclusion spacing.
    """
    missing = set(
        int(v)
        for v in rng.choice(
            49,
            size=int(rng.integers(3, 6)),
            replace=False,
        )
    )

    sites = []
    indices = []
    boundary = []

    for j in range(9):
        for i in range(9):
            if 0 < i < 8 and 0 < j < 8:
                if (j - 1) * 7 + (i - 1) in missing:
                    continue

            if i == 0:
                x = rng.uniform(2.0, 5.5)
            elif i == 8:
                x = rng.uniform(250.5, 254.0)
            else:
                x = 4.0 + 31.0 * i + rng.uniform(-8.5, 8.5)

            if j == 0:
                y = rng.uniform(2.0, 5.5)
            elif j == 8:
                y = rng.uniform(250.5, 254.0)
            else:
                y = 4.0 + 31.0 * j + rng.uniform(-8.5, 8.5)

            sites.append((y, x))
            indices.append((j, i))
            boundary.append(
                i in (0, 8) or j in (0, 8)
            )

    return (
        np.asarray(sites, dtype=float),
        np.asarray(indices, dtype=int),
        np.asarray(boundary, dtype=bool),
    )


def _territories(sites):
    """
    Finite nonperiodic Voronoi-like allocation.

    The exclusion zone between neighboring territories
    keeps independently grown reinforcement regions
    physically separated in the raster geometry.
    """
    yy, xx = np.indices((SIZE, SIZE))

    nearest = np.full((SIZE, SIZE), np.inf)
    owner = np.zeros((SIZE, SIZE), dtype=np.int16)

    for k, (cy, cx) in enumerate(sites):
        distance = (yy - cy) ** 2 + (xx - cx) ** 2
        closer = distance < nearest

        owner[closer] = k
        np.minimum(nearest, distance, out=nearest)

    low = ndi.minimum_filter(
        owner, size=7, mode="nearest"
    )
    high = ndi.maximum_filter(
        owner, size=7, mode="nearest"
    )

    return owner, low == high


def _allocate_areas(rng, capacities, indices, boundary):
    """
    Exact integer allocation with bounded local capacities.

    Spatially correlated and independent fluctuations
    generate variation in reinforcement region sizes.
    """
    n = len(capacities)
    caps = np.floor(0.79 * capacities).astype(int)
    minimum = 32

    if np.any(caps < minimum):
        raise RuntimeError("Local territory capacity exhausted")

    if int(caps.sum()) < TARGET_REINFORCEMENT:
        raise RuntimeError("Insufficient total capacity")

    coarse = ndi.gaussian_filter(
        rng.normal(size=(9, 9)),
        1.15,
        mode="reflect",
    )
    coarse /= max(float(coarse.std()), 1e-9)

    spatial = coarse[indices[:, 0], indices[:, 1]]

    weights = np.exp(
        rng.normal(0.0, 0.48, n)
        + 0.27 * spatial
    )

    weights *= np.where(boundary, 0.87, 1.08)

    low = 0.0
    high = float(TARGET_REINFORCEMENT)

    for _ in range(55):
        mid = 0.5 * (low + high)
        real = np.minimum(
            caps, minimum + mid * weights
        )

        if real.sum() < TARGET_REINFORCEMENT:
            low = mid
        else:
            high = mid

    real = np.minimum(
        caps, minimum + high * weights
    )

    quotas = np.floor(real).astype(int)

    remaining = (
        TARGET_REINFORCEMENT - int(quotas.sum())
    )

    if remaining < 0 or remaining > n:
        raise RuntimeError("Integer allocation failed")

    if remaining:
        fractions = real - quotas
        eligible = np.flatnonzero(quotas < caps)

        order = eligible[
            np.argsort(-fractions[eligible])
        ]

        if len(order) < remaining:
            raise RuntimeError(
                "Integer allocation capacity exhausted"
            )

        quotas[order[:remaining]] += 1

    if int(quotas.sum()) != TARGET_REINFORCEMENT:
        raise RuntimeError("Exact composition allocation failed")

    return quotas


def _priority_field(rng, shape, center, origin):
    """
    Irregular angular particle geometry with a moderate
    horizontal axial preference.

    The horizontal preference is a geometry-based hypothesis
    for moderating vertical reinforcement efficiency. It is
    not calibrated from measured mechanical responses.

    Orientation remains stochastic and nonuniform.
    """
    h, w = shape
    y0, x0 = origin
    cy, cx = center

    yy, xx = np.indices((h, w), dtype=float)
    yy += y0 - cy
    xx += x0 - cx

    aspect = float(
        np.clip(
            rng.lognormal(np.log(1.90), 0.26),
            1.08,
            2.85,
        )
    )

    if rng.random() < 0.82:
        angle = (
            0.5 * rng.vonmises(0.0, 1.05)
        ) % np.pi
    else:
        angle = rng.uniform(0.0, np.pi)

    c = np.cos(angle)
    s = np.sin(angle)
    root = np.sqrt(aspect)

    u = (xx * c + yy * s) / root
    v = (-xx * s + yy * c) * root

    radial = np.hypot(u, v)

    knots = int(rng.integers(12, 21))
    perturbation = rng.normal(
        0.0, 0.26, knots
    )

    perturbation = (
        0.68 * perturbation
        + 0.16 * np.roll(perturbation, 1)
        + 0.16 * np.roll(perturbation, -1)
    )

    profile = np.clip(
        1.0 + perturbation, 0.58, 1.43
    )

    theta = (
        np.arctan2(v, u) + np.pi
    ) * (knots / (2.0 * np.pi))

    base = np.floor(theta)
    index = base.astype(int) % knots
    fraction = theta - base

    local_radius = (
        (1.0 - fraction) * profile[index]
        + fraction * profile[(index + 1) % knots]
    )

    rough = ndi.gaussian_filter(
        rng.normal(size=(h, w)),
        1.15,
        mode="reflect",
    )
    rough /= max(float(rough.std()), 1e-9)

    score = (
        radial / local_radius
        + 0.40 * rough
        + rng.normal(0.0, 0.055, (h, w))
    )

    return score


def _grow_particle(rng, territory, center, quota):
    """
    Four-connected priority-front growth.

    Each accepted pixel is connected to the existing
    inclusion. Growth stops at the exact assigned area.
    """
    ys, xs = np.nonzero(territory)

    if len(ys) < quota:
        raise RuntimeError(
            "Particle quota exceeds territory"
        )

    y0 = int(ys.min())
    y1 = int(ys.max()) + 1
    x0 = int(xs.min())
    x1 = int(xs.max()) + 1

    permitted = territory[y0:y1, x0:x1]
    h, w = permitted.shape

    score = _priority_field(
        rng,
        (h, w),
        center,
        (y0, x0),
    )

    cy, cx = center
    sy = int(np.rint(cy)) - y0
    sx = int(np.rint(cx)) - x0

    if (
        sy < 0
        or sy >= h
        or sx < 0
        or sx >= w
        or not permitted[sy, sx]
    ):
        distance = (
            (ys - cy) ** 2
            + (xs - cx) ** 2
        )
        nearest = int(np.argmin(distance))
        sy = int(ys[nearest]) - y0
        sx = int(xs[nearest]) - x0

    accepted = np.zeros(
        (h, w), dtype=bool
    )
    queued = np.zeros(
        (h, w), dtype=bool
    )
    heap = []

    _heap_push(
        heap,
        (float(score[sy, sx]), sy, sx),
    )
    queued[sy, sx] = True

    count = 0

    while heap and count < quota:
        _, y, x = _heap_pop(heap)

        accepted[y, x] = True
        count += 1

        for dy, dx in (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
        ):
            ny = y + dy
            nx = x + dx

            if not (
                0 <= ny < h
                and 0 <= nx < w
            ):
                continue

            if (
                not permitted[ny, nx]
                or queued[ny, nx]
            ):
                continue

            queued[ny, nx] = True

            _heap_push(
                heap,
                (
                    float(score[ny, nx]),
                    ny,
                    nx,
                ),
            )

    if count != quota:
        raise RuntimeError(
            "Connected growth exhausted territory"
        )

    return y0, y1, x0, x1, accepted


def _candidate(rng):
    sites, indices, boundary = _make_sites(rng)

    owner, safe = _territories(sites)

    capacities = np.bincount(
        owner[safe].ravel(),
        minlength=len(sites),
    )

    quotas = _allocate_areas(
        rng,
        capacities,
        indices,
        boundary,
    )

    canvas = np.zeros(
        (SIZE, SIZE), dtype=bool
    )

    for k, center in enumerate(sites):
        territory = safe & (owner == k)

        y0, y1, x0, x1, particle = (
            _grow_particle(
                rng,
                territory,
                center,
                int(quotas[k]),
            )
        )

        if np.any(
            canvas[y0:y1, x0:x1] & particle
        ):
            raise RuntimeError(
                "Overlapping reinforcement regions"
            )

        canvas[y0:y1, x0:x1] |= particle

    if int(canvas.sum()) != TARGET_REINFORCEMENT:
        raise RuntimeError(
            "Generated reinforcement count mismatch"
        )

    return np.where(
        canvas, 5, 1
    ).astype(np.uint8)


def _topology(mask, connectivity=1):
    structure = ndi.generate_binary_structure(
        2, connectivity
    )
    labels, count = ndi.label(
        mask, structure
    )

    sizes = np.bincount(
        labels.ravel()
    )[1:]

    total = int(mask.sum())

    left = set(np.unique(labels[:, 0]))
    right = set(np.unique(labels[:, -1]))
    top = set(np.unique(labels[0, :]))
    bottom = set(np.unique(labels[-1, :]))

    return {
        "regions": int(count),
        "largest_fraction": (
            float(sizes.max() / total)
            if total else 0.0
        ),
        "spans_x": bool(
            (left & right) - {0}
        ),
        "spans_y": bool(
            (top & bottom) - {0}
        ),
        "singleton_fraction": (
            float(
                sizes[sizes == 1].sum() / total
            )
            if total else 0.0
        ),
    }


def _limited_gap_run(line):
    positions = np.flatnonzero(line)

    if not len(positions):
        return 0

    splits = np.r_[
        0,
        np.flatnonzero(
            np.diff(positions) > 3
        ) + 1,
        len(positions),
    ]

    return max(
        int(
            positions[b - 1]
            - positions[a]
            + 1
        )
        for a, b in zip(
            splits[:-1], splits[1:]
        )
    )


def _shape_statistics(regions):
    areas = []
    aspects = []
    angles = []
    anisotropies = []

    for region in regions:
        xy = region.coords[:, [1, 0]].astype(float)
        xy[:, 1] *= -1.0
        xy -= xy.mean(axis=0)

        covariance = xy.T @ xy / len(xy)
        values, vectors = np.linalg.eigh(
            covariance
        )

        if values[0] <= 1e-12:
            continue

        aspect = float(
            np.sqrt(values[1] / values[0])
        )
        direction = vectors[:, 1]

        anisotropy = float(
            (values[1] - values[0])
            / values.sum()
        )

        areas.append(float(region.area))
        aspects.append(aspect)
        angles.append(
            float(
                np.arctan2(
                    direction[1],
                    direction[0],
                ) % np.pi
            )
        )
        anisotropies.append(anisotropy)

    if not areas:
        return None

    areas = np.asarray(areas)
    aspects = np.asarray(aspects)
    angles = np.asarray(angles)
    anisotropies = np.asarray(anisotropies)

    total = float(
        sum(region.area for region in regions)
    )

    order = np.argsort(
        aspects, kind="stable"
    )
    sorted_areas = areas[order]
    sorted_aspects = aspects[order]

    index = np.searchsorted(
        np.cumsum(sorted_areas),
        0.95 * areas.sum(),
        side="left",
    )
    index = min(
        index, len(aspects) - 1
    )

    weights = (
        areas
        * anisotropies
        * (anisotropies >= 0.05)
    )

    if weights.sum() <= 1e-12:
        axial_order = None
        horizontal_alignment = None
    else:
        z = np.sum(
            weights * np.exp(2j * angles)
        ) / weights.sum()

        axial_order = float(abs(z))
        horizontal_alignment = float(z.real)

    return {
        "defined_fraction": float(
            areas.sum() / total
        ),
        "area_weighted_aspect": float(
            np.average(
                aspects, weights=areas
            )
        ),
        "area_weighted_p95": float(
            sorted_aspects[index]
        ),
        "fraction_gt3": float(
            areas[aspects > 3.0].sum()
            / total
        ),
        "fraction_gt4": float(
            areas[aspects > 4.0].sum()
            / total
        ),
        "axial_order": axial_order,
        "horizontal_alignment": horizontal_alignment,
    }


def _structural_metrics(array):
    if array.shape != (SIZE, SIZE):
        return None

    if array.dtype != np.uint8:
        return None

    if int(np.count_nonzero(array == 5)) != (
        TARGET_REINFORCEMENT
    ):
        return None

    if np.any(
        (array != 1) & (array != 5)
    ):
        return None

    reinforcement = array == 5

    matrix = _topology(
        ~reinforcement, 1
    )

    if matrix["largest_fraction"] < 0.95:
        return None

    if not (
        matrix["spans_x"]
        and matrix["spans_y"]
    ):
        return None

    for connectivity in (1, 2):
        result = _topology(
            reinforcement, connectivity
        )

        if (
            result["spans_x"]
            or result["spans_y"]
        ):
            return None

        if result["largest_fraction"] > 0.15:
            return None

        if (
            connectivity == 1
            and result["singleton_fraction"] > 0.001
        ):
            return None

    labels, count = ndi.label(
        reinforcement
    )

    if not 50 <= count <= 125:
        return None

    regions = regionprops(labels)

    edge_labels = set(
        np.unique(
            np.r_[
                labels[0, :],
                labels[-1, :],
                labels[:, 0],
                labels[:, -1],
            ]
        )
    ) - {0}

    complete = [
        region
        for region in regions
        if region.label not in edge_labels
    ]

    if not 40 <= len(complete) <= 75:
        return None

    if not 5 <= len(edge_labels) <= 50:
        return None

    diameters = np.asarray([
        region.equivalent_diameter_area
        for region in complete
    ])

    if not (
        12.0
        <= float(diameters.mean())
        <= 20.0
    ):
        return None

    complete_aspects = [
        region.axis_major_length
        / region.axis_minor_length
        for region in complete
        if region.axis_minor_length > 0
    ]

    if not complete_aspects:
        return None

    if not (
        1.2
        <= float(np.mean(complete_aspects))
        <= 3.0
    ):
        return None

    shapes = _shape_statistics(regions)

    if shapes is None:
        return None

    if shapes["defined_fraction"] < 0.995:
        return None

    if not (
        1.0
        <= shapes["area_weighted_aspect"]
        <= 2.59
    ):
        return None

    if not (
        1.0
        <= shapes["area_weighted_p95"]
        <= 6.13
    ):
        return None

    if shapes["fraction_gt3"] > 0.27:
        return None

    if shapes["fraction_gt4"] > 0.16:
        return None

    if shapes["axial_order"] is None:
        return None

    if shapes["axial_order"] > 0.59:
        return None

    centers = np.asarray([
        region.centroid
        for region in complete
    ])

    distances = cdist(
        centers, centers
    )
    np.fill_diagonal(
        distances, np.inf
    )

    nearest = distances.min(axis=1)

    neighbor_cv = float(
        nearest.std()
        / max(nearest.mean(), 1e-12)
    )

    if not (
        0.10 <= neighbor_cv <= 0.69
    ):
        return None

    column_fraction = (
        reinforcement.mean(axis=0)
    )
    row_fraction = (
        reinforcement.mean(axis=1)
    )

    for width, limits in STRIP_LIMITS.items():
        columns = np.convolve(
            column_fraction,
            np.ones(width) / width,
            mode="valid",
        )
        rows = np.convolve(
            row_fraction,
            np.ones(width) / width,
            mode="valid",
        )

        col_max, col_std, row_max, row_std = limits

        if columns.max() > col_max:
            return None

        if columns.std() > col_std:
            return None

        if rows.max() > row_max:
            return None

        if rows.std() > row_std:
            return None

    differences = []

    for lag in CORRELATION_LAGS:
        sx = float(np.mean(
            reinforcement[:, :-lag]
            & reinforcement[:, lag:]
        ))
        sy = float(np.mean(
            reinforcement[:-lag, :]
            & reinforcement[lag:, :]
        ))

        differences.append(
            abs(sy - sx)
        )

    if float(np.mean(differences)) > 0.04:
        return None

    longest_x = max(
        _limited_gap_run(
            reinforcement[row, :]
        )
        for row in range(SIZE)
    ) / SIZE

    longest_y = max(
        _limited_gap_run(
            reinforcement[:, col]
        )
        for col in range(SIZE)
    ) / SIZE

    if longest_x > 0.60:
        return None

    if longest_y > 0.56:
        return None

    yy, xx = np.mgrid[-2:3, -2:3]
    disk = (
        xx * xx + yy * yy <= 4
    )

    dilated = ndi.binary_dilation(
        reinforcement,
        structure=disk,
        border_value=0,
    )

    dilation = _topology(
        dilated, 2
    )

    if (
        dilation["spans_x"]
        or dilation["spans_y"]
    ):
        return None

    if dilation["largest_fraction"] > 0.59:
        return None

    return {
        "horizontal_alignment": (
            shapes["horizontal_alignment"]
        ),
        "area_weighted_aspect": (
            shapes["area_weighted_aspect"]
        ),
        "neighbor_cv": neighbor_cv,
        "long_range_difference": float(
            np.mean(differences)
        ),
    }


def _geometry_score(metrics):
    """
    Geometry-only ranking among feasible candidates.

    Prefer moderate horizontal inclusion alignment and
    moderate elongation, rather than maximizing either.
    No mechanical response or mechanical surrogate is
    calculated or used in candidate selection.
    """
    horizontal = metrics["horizontal_alignment"]
    aspect = metrics["area_weighted_aspect"]

    return float(
        1.4 * (horizontal - 0.30) ** 2
        + 0.35 * (aspect - 1.80) ** 2
    )


def generate_microstructure(seed, parameters={}):
    """
    Stochastic P3 reinforcement/matrix generator.

    Output:
        shape (256, 256)
        dtype uint8
        label 1: matrix-like solid
        label 5: provisional reinforcement-like solid

    Exact composition:
        label 1: 44,805 pixels
        label 5: 20,731 pixels

    Candidate selection is strictly geometric and bounded.
    No mechanical calculation, reference-image retrieval,
    measured modulus, or cached result is used.

    Each invocation creates independent stochastic geometry
    from a local random generator. Identical seeds replay
    exactly. Candidate count is at most eight.
    """
    rng = np.random.default_rng(seed)

    best = None
    best_score = np.inf

    for _ in range(MAX_CANDIDATES):
        try:
            candidate = _candidate(rng)
        except RuntimeError:
            continue

        metrics = _structural_metrics(candidate)

        if metrics is None:
            continue

        score = _geometry_score(metrics)

        if score < best_score:
            best_score = score
            best = candidate

    if best is None:
        raise RuntimeError(
            "No structurally feasible P3 microstructure "
            "within eight geometry candidates"
        )

    return best
