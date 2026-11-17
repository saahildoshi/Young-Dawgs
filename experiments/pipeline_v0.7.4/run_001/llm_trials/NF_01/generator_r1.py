import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import regionprops


SIZE = 256
TARGET_REINFORCEMENT = 20731
N_COMPLETE = 57
N_BOUNDARY = 20
MAX_CANDIDATES = 8

# Geometry-only revision: moderate horizontal axial preference, slightly
# greater inclusion elongation, and modestly less regular nucleus spacing.
# These changes may reduce apparent vertical stiffness by altering the
# load-transfer geometry. No measured modulus or mechanical solver is used.
ORIENTATION_KAPPA = 0.90
ASPECT_MEDIAN = 1.85
ASPECT_LOG_STD = 0.23
ASPECT_MAX = 2.75
PLACEMENT_JITTER = 4.25
TERRITORY_MARGIN = 6.5

STRIP_BOUNDS = {
    1: (0.79, 0.18, 0.78, 0.20),
    8: (0.74, 0.17, 0.75, 0.19),
    16: (0.71, 0.16, 0.69, 0.17),
    32: (0.64, 0.14, 0.63, 0.16),
}


def _centers(rng):
    """
    Construct independent, nonperiodic reinforcement nuclei.

    Twenty boundary nuclei are distributed over the specimen edges.
    Fifty-seven interior nuclei use stochastic best-candidate inhibition.
    No preferred placement rows, columns, or reinforcement lanes are used.
    """
    centers = []

    for side in range(4):
        positions = np.linspace(24.0, 232.0, 5)
        positions += rng.uniform(-12.0, 12.0, 5)

        for p in positions:
            if side == 0:
                centers.append((p, 0.0))
            elif side == 1:
                centers.append((p, 255.0))
            elif side == 2:
                centers.append((0.0, p))
            else:
                centers.append((255.0, p))

    for _ in range(N_COMPLETE):
        proposals = rng.uniform(18.0, 238.0, (40, 2))
        existing = np.asarray(centers, dtype=float)

        distances = np.sqrt(
            np.sum(
                (
                    proposals[:, None, :]
                    - existing[None, :, :]
                ) ** 2,
                axis=2,
            )
        ).min(axis=1)

        scores = distances + rng.gumbel(
            0.0, PLACEMENT_JITTER, len(proposals)
        )
        scores[distances < 19.0] = -np.inf

        index = int(np.argmax(scores))

        if not np.isfinite(scores[index]):
            raise RuntimeError("Interior nucleus packing exhausted")

        centers.append(tuple(proposals[index]))

    return np.asarray(centers, dtype=float)


def _territories(centers):
    """
    Assign pixels to finite nearest-nucleus territories.

    The distance-difference exclusion margin retains intervening
    matrix ligaments and strongly discourages diagnostic radius-2
    connections between different reinforcement regions.
    """
    yy, xx = np.indices((SIZE, SIZE))
    coordinates = np.column_stack((xx.ravel(), yy.ravel()))

    tree = cKDTree(centers)
    distances, nearest = tree.query(coordinates, k=2)

    owner = nearest[:, 0].astype(np.int16)

    owner[
        distances[:, 1] - distances[:, 0] < TERRITORY_MARGIN
    ] = -1

    owner = owner.reshape(SIZE, SIZE)

    # Interior inclusions are required to remain complete.
    for edge in (
        owner[0, :],
        owner[-1, :],
        owner[:, 0],
        owner[:, -1],
    ):
        edge[edge >= N_BOUNDARY] = -1

    return owner


def _allocate_areas(rng, capacities):
    """
    Allocate exactly 20,731 reinforcement pixels across the nuclei.

    The integer allocation is completed before construction, avoiding
    pixel-count repairs or disconnected correction islands.
    """
    capacities = np.asarray(capacities, dtype=np.int64)
    n = len(capacities)

    boundary = np.arange(n) < N_BOUNDARY

    lower = np.where(boundary, 70, 85)

    upper = np.minimum(
        np.floor(0.84 * capacities).astype(np.int64),
        np.where(boundary, 560, 650),
    )

    if np.any(upper < lower):
        raise RuntimeError("Insufficient reinforcement territory")

    if (
        int(lower.sum()) > TARGET_REINFORCEMENT
        or int(upper.sum()) < TARGET_REINFORCEMENT
    ):
        raise RuntimeError("Exact area allocation infeasible")

    weights = (
        np.maximum(capacities, 1) ** 0.53
        * rng.lognormal(0.0, 0.34, n)
    )

    weights[boundary] *= 1.06

    low_scale = 0.0
    high_scale = 1.0

    while (
        np.clip(weights * high_scale, lower, upper).sum()
        < TARGET_REINFORCEMENT
    ):
        high_scale *= 2.0

    for _ in range(55):
        middle = 0.5 * (low_scale + high_scale)

        trial = np.clip(
            weights * middle, lower, upper
        )

        if trial.sum() < TARGET_REINFORCEMENT:
            low_scale = middle
        else:
            high_scale = middle

    continuous = np.clip(
        weights * high_scale, lower, upper
    )

    areas = np.floor(continuous).astype(np.int64)

    deficit = TARGET_REINFORCEMENT - int(areas.sum())

    if deficit < 0:
        raise RuntimeError("Area rounding failure")

    fractional = continuous - areas

    order = np.argsort(
        -(fractional + rng.uniform(0.0, 1e-5, n))
    )

    for index in order:
        if deficit == 0:
            break

        if areas[index] < upper[index]:
            areas[index] += 1
            deficit -= 1

    if (
        deficit != 0
        or int(areas.sum()) != TARGET_REINFORCEMENT
    ):
        raise RuntimeError("Exact area allocation exhausted")

    return areas


def _shape_cost(rng, shape, center):
    """
    Construct an irregular angular growth potential.

    A moderate horizontal axial preference is introduced through a
    von Mises distribution applied to doubled axial angles.

    Angular radial perturbations, local indentations, and correlated
    noise retain dispersed, nonelliptical inclusion boundaries.
    """
    h, w = shape
    cy, cx = center

    yy, xx = np.indices((h, w), dtype=float)

    dx = xx - cx
    dy = yy - cy

    # Axial orientation modulo pi; horizontal is angle zero.
    angle = 0.5 * rng.vonmises(0.0, ORIENTATION_KAPPA)

    ca = np.cos(angle)
    sa = np.sin(angle)

    u = dx * ca + dy * sa
    v = -dx * sa + dy * ca

    aspect = float(
        np.clip(
            rng.lognormal(
                np.log(ASPECT_MEDIAN),
                ASPECT_LOG_STD,
            ),
            1.08,
            ASPECT_MAX,
        )
    )

    elliptical_radius = np.sqrt(
        u * u / aspect
        + v * v * aspect
    )

    n = int(rng.integers(11, 20))

    radial_knots = np.clip(
        1.0 + rng.normal(0.0, 0.19, n),
        0.66,
        1.38,
    )

    radial_knots = (
        0.77 * radial_knots
        + 0.115 * np.roll(radial_knots, 1)
        + 0.115 * np.roll(radial_knots, -1)
    )

    if rng.random() < 0.70:
        for _ in range(int(rng.integers(1, 3))):
            j = int(rng.integers(n))
            radial_knots[j] *= rng.uniform(0.69, 0.87)

    angular_position = (
        (np.arctan2(v, u) + np.pi)
        * n / (2.0 * np.pi)
    )

    sector = np.floor(
        angular_position
    ).astype(np.int32)

    fraction = angular_position - sector

    radial_profile = (
        radial_knots[sector % n] * (1.0 - fraction)
        + radial_knots[(sector + 1) % n] * fraction
    )

    noise = ndi.gaussian_filter(
        rng.standard_normal((h, w)),
        sigma=rng.uniform(0.9, 1.7),
        mode="reflect",
    )

    noise /= max(float(noise.std()), 1e-8)

    cost = (
        elliptical_radius
        / np.maximum(radial_profile, 0.45)
    )

    cost += rng.uniform(0.55, 1.15) * noise

    return cost


def _heap_push(heap, item):
    heap.append(item)
    index = len(heap) - 1

    while index > 0:
        parent = (index - 1) // 2

        if heap[parent] <= item:
            break

        heap[index] = heap[parent]
        index = parent

    heap[index] = item


def _heap_pop(heap):
    result = heap[0]
    last = heap.pop()

    if heap:
        index = 0
        length = len(heap)

        while True:
            child = 2 * index + 1

            if child >= length:
                break

            if (
                child + 1 < length
                and heap[child + 1] < heap[child]
            ):
                child += 1

            if heap[child] >= last:
                break

            heap[index] = heap[child]
            index = child

        heap[index] = last

    return result


def _grow_connected(allowed, cost, seed, target):
    """
    Grow exactly target pixels from one four-connected nucleus.

    Growth uses a minimum-cost frontier. Every accepted pixel is
    connected to the previously accepted region.
    """
    h, w = allowed.shape
    sy, sx = seed

    if (
        not 0 <= sy < h
        or not 0 <= sx < w
        or not allowed[sy, sx]
        or target > int(allowed.sum())
    ):
        raise RuntimeError("Invalid connected-growth territory")

    selected = np.zeros((h, w), dtype=bool)
    queued = np.zeros((h, w), dtype=bool)

    heap = []

    _heap_push(
        heap,
        (float(cost[sy, sx]), sy, sx),
    )

    queued[sy, sx] = True

    for _ in range(int(target)):
        if not heap:
            raise RuntimeError(
                "Connected-growth frontier exhausted"
            )

        _, y, x = _heap_pop(heap)

        selected[y, x] = True

        for dy, dx in (
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1),
        ):
            ny = y + dy
            nx = x + dx

            if (
                0 <= ny < h
                and 0 <= nx < w
                and allowed[ny, nx]
                and not queued[ny, nx]
            ):
                queued[ny, nx] = True

                _heap_push(
                    heap,
                    (float(cost[ny, nx]), ny, nx),
                )

    return selected


def _generate_candidate(rng):
    centers = _centers(rng)
    owner = _territories(centers)

    n = len(centers)

    capacities = np.bincount(
        owner[owner >= 0].ravel(),
        minlength=n,
    )

    areas = _allocate_areas(rng, capacities)

    reinforcement = np.zeros(
        (SIZE, SIZE), dtype=bool
    )

    for index in range(n):
        coordinates = np.argwhere(owner == index)

        if len(coordinates) < areas[index]:
            raise RuntimeError("Particle territory exhausted")

        y0, x0 = coordinates.min(axis=0)
        y1, x1 = coordinates.max(axis=0) + 1

        allowed = (
            owner[y0:y1, x0:x1] == index
        )

        cx, cy = centers[index]

        sx = int(np.rint(cx)) - x0
        sy = int(np.rint(cy)) - y0

        if not (
            0 <= sy < allowed.shape[0]
            and 0 <= sx < allowed.shape[1]
            and allowed[sy, sx]
        ):
            raise RuntimeError(
                "Nucleus outside assigned territory"
            )

        cost = _shape_cost(
            rng,
            allowed.shape,
            (cy - y0, cx - x0),
        )

        particle = _grow_connected(
            allowed,
            cost,
            (sy, sx),
            int(areas[index]),
        )

        reinforcement[y0:y1, x0:x1] |= particle

    if int(reinforcement.sum()) != TARGET_REINFORCEMENT:
        raise RuntimeError(
            "Exact reinforcement composition violated"
        )

    return np.where(
        reinforcement, 5, 1
    ).astype(np.uint8)


def _topology(mask, connectivity=1):
    structure = ndi.generate_binary_structure(
        2, connectivity
    )

    labels, n = ndi.label(mask, structure)

    sizes = np.bincount(
        labels.ravel()
    )[1:]

    left = set(np.unique(labels[:, 0]))
    right = set(np.unique(labels[:, -1]))

    top = set(np.unique(labels[0]))
    bottom = set(np.unique(labels[-1]))

    return {
        "regions": int(n),
        "largest_fraction": (
            float(sizes.max() / mask.sum())
            if sizes.size
            else 0.0
        ),
        "spans_x": bool((left & right) - {0}),
        "spans_y": bool((top & bottom) - {0}),
        "singleton_fraction": (
            float(sizes[sizes == 1].sum() / mask.sum())
            if sizes.size
            else 0.0
        ),
    }


def _limited_gap_run(line, maxgap=2):
    positions = np.flatnonzero(line)

    if len(positions) == 0:
        return 0

    splits = np.r_[
        0,
        np.flatnonzero(
            np.diff(positions) > maxgap + 1
        ) + 1,
        len(positions),
    ]

    return max(
        int(positions[b - 1] - positions[a] + 1)
        for a, b in zip(splits[:-1], splits[1:])
    )


def _shape_statistics(regions):
    """
    Evaluate all observed four-connected regions, including
    boundary-censored regions.

    Aspect ratios use eigenvalues of pixel-coordinate covariance.
    Orientation uses image x right, y up, modulo 180 degrees.
    """
    total = sum(r.area for r in regions)

    if total <= 0:
        return None

    areas = []
    aspects = []
    angles = []
    anisotropies = []

    for region in regions:
        xy = region.coords[:, [1, 0]].astype(float)

        xy[:, 1] *= -1
        xy -= xy.mean(axis=0)

        covariance = (
            xy.T @ xy / len(xy)
        )

        values, vectors = np.linalg.eigh(covariance)

        if values[0] <= 1e-12:
            continue

        aspect = float(
            np.sqrt(values[1] / values[0])
        )

        principal = vectors[:, 1]

        angle = float(
            np.arctan2(
                principal[1], principal[0]
            ) % np.pi
        )

        anisotropy = float(
            (values[1] - values[0])
            / max(values[1] + values[0], 1e-12)
        )

        areas.append(float(region.area))
        aspects.append(aspect)
        angles.append(angle)
        anisotropies.append(anisotropy)

    if not areas:
        return None

    areas = np.asarray(areas)
    aspects = np.asarray(aspects)
    angles = np.asarray(angles)
    anisotropies = np.asarray(anisotropies)

    weights = (
        areas
        * anisotropies
        * (anisotropies >= 0.05)
    )

    if weights.sum() <= 1e-12:
        return None

    z = (
        np.sum(weights * np.exp(2j * angles))
        / weights.sum()
    )

    order = np.argsort(
        aspects, kind="stable"
    )

    cumulative = np.cumsum(
        areas[order]
    )

    index = np.searchsorted(
        cumulative,
        0.95 * areas.sum(),
        side="left",
    )

    p95 = float(
        aspects[order][min(index, len(order) - 1)]
    )

    return {
        "defined_fraction": float(
            areas.sum() / total
        ),
        "weighted_aspect": float(
            np.average(aspects, weights=areas)
        ),
        "weighted_p95": p95,
        "fraction_gt3": float(
            areas[aspects > 3].sum() / total
        ),
        "fraction_gt4": float(
            areas[aspects > 4].sum() / total
        ),
        "axial_order": float(abs(z)),
    }


def _structural_ok(a):
    """
    Verify the registered composition, topology, region populations,
    all-observed shape descriptors, finite correlations, and spacing
    bounds without changing the candidate geometry.
    """
    if (
        a.shape != (SIZE, SIZE)
        or a.dtype != np.uint8
        or not np.array_equal(
            np.unique(a), np.array([1, 5])
        )
        or int(np.count_nonzero(a == 5))
        != TARGET_REINFORCEMENT
    ):
        return False

    reinforcement = a == 5

    matrix = _topology(
        ~reinforcement, 1
    )

    if (
        matrix["largest_fraction"] < 0.95
        or not matrix["spans_x"]
        or not matrix["spans_y"]
    ):
        return False

    for connectivity in (1, 2):
        t = _topology(
            reinforcement, connectivity
        )

        if (
            t["spans_x"]
            or t["spans_y"]
            or t["largest_fraction"] > 0.15
        ):
            return False

        if (
            connectivity == 1
            and t["singleton_fraction"] > 0.001
        ):
            return False

    labels, n = ndi.label(reinforcement)
    regions = regionprops(labels)

    edge_labels = set(
        np.unique(
            np.r_[
                labels[0],
                labels[-1],
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

    if not (
        50 <= n <= 125
        and 40 <= len(complete) <= 75
        and 5 <= len(edge_labels) <= 50
    ):
        return False

    diameters = [
        region.equivalent_diameter_area
        for region in complete
    ]

    aspects = [
        region.axis_major_length
        / region.axis_minor_length
        for region in complete
        if region.axis_minor_length > 0
    ]

    if not diameters or not aspects:
        return False

    if not (
        12 <= np.mean(diameters) <= 20
        and 1.2 <= np.mean(aspects) <= 3.0
    ):
        return False

    shape = _shape_statistics(regions)

    if shape is None:
        return False

    if not (
        shape["defined_fraction"] >= 0.995
        and 1 <= shape["weighted_aspect"] <= 2.59
        and 1 <= shape["weighted_p95"] <= 6.13
        and shape["fraction_gt3"] <= 0.27
        and shape["fraction_gt4"] <= 0.16
        and shape["axial_order"] <= 0.59
    ):
        return False

    # Complete-region centroid nearest-neighbor coefficient of variation.
    centers = np.asarray(
        [region.centroid for region in complete],
        dtype=float,
    )

    if len(centers) < 2:
        return False

    tree = cKDTree(centers)
    distances, _ = tree.query(centers, k=2)

    nearest = distances[:, 1]

    if nearest.mean() <= 0:
        return False

    cv = float(
        nearest.std() / nearest.mean()
    )

    if not 0.10 <= cv <= 0.69:
        return False

    # Finite-window S2: no periodic wrapping.
    differences = []

    for lag in (16, 32, 64):
        sx = np.mean(
            reinforcement[:, :-lag]
            & reinforcement[:, lag:]
        )

        sy = np.mean(
            reinforcement[:-lag, :]
            & reinforcement[lag:, :]
        )

        differences.append(abs(float(sy - sx)))

    if np.mean(differences) > 0.04:
        return False

    # Row and column strip statistics.
    column_fraction = reinforcement.mean(axis=0)
    row_fraction = reinforcement.mean(axis=1)

    for width, bounds in STRIP_BOUNDS.items():
        kernel = np.ones(width, dtype=float) / width

        x = np.convolve(
            column_fraction,
            kernel,
            mode="valid",
        )

        y = np.convolve(
            row_fraction,
            kernel,
            mode="valid",
        )

        column_max, column_std, row_max, row_std = bounds

        if (
            x.max() > column_max
            or x.std() > column_std
            or y.max() > row_max
            or y.std() > row_std
        ):
            return False

    # Long runs bridged across at most two missing pixels.
    longest_x = max(
        _limited_gap_run(reinforcement[y, :])
        for y in range(SIZE)
    ) / SIZE

    longest_y = max(
        _limited_gap_run(reinforcement[:, x])
        for x in range(SIZE)
    ) / SIZE

    if longest_x > 0.60 or longest_y > 0.56:
        return False

    # Diagnostic Euclidean disk dilation; not a specimen modification.
    yy, xx = np.mgrid[-2:3, -2:3]
    disk = (xx * xx + yy * yy) <= 4

    dilated = ndi.binary_dilation(
        reinforcement,
        structure=disk,
        border_value=0,
    )

    gap = _topology(dilated, 2)

    if (
        gap["largest_fraction"] > 0.59
        or gap["spans_x"]
        or gap["spans_y"]
    ):
        return False

    return True


def generate_microstructure(seed, parameters={}):
    """
    Generate one reproducible stochastic P3 microstructure.

    Output:
        ndarray, shape (256, 256), dtype uint8
        label 1: matrix-like solid, exactly 44,805 pixels
        label 5: provisional reinforcement-like solid,
                 exactly 20,731 pixels

    Finite nonperiodic boundaries are retained, including clipped
    inclusions. The morphology is procedural and is not an extracted
    or calibrated physical particle segmentation.

    The revision introduces moderate horizontal inclusion anisotropy
    as a geometry-based attempt to adjust vertical load transfer.
    It does not calculate, fit, or guarantee an elastic modulus.

    A maximum of eight independently constructed candidates is used.
    Failed candidates are discarded without modification.
    """
    rng = np.random.default_rng(seed)

    for _ in range(MAX_CANDIDATES):
        try:
            candidate = _generate_candidate(rng)
        except RuntimeError:
            continue

        if _structural_ok(candidate):
            return candidate

    raise RuntimeError(
        "No structurally feasible microstructure "
        "within eight registered geometry candidates"
    )