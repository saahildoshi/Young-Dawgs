import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from skimage.measure import regionprops

SIZE = 256
TARGET_REINFORCEMENT = 20731
N_INTERIOR = 60
N_EDGE_PER_SIDE = 5
MIN_CENTER_DISTANCE = 19.5
CELL_GAP = 6.5
MAX_CANDIDATES = 8

LAGS = (8, 16, 32, 64)
WIDTHS = (1, 8, 16, 32)

MORPHOLOGY_BOUNDS = {
    "all_observed.area_fraction_aspect_gt3": (0, 0.27),
    "all_observed.area_fraction_aspect_gt4": (0, 0.16),
    "all_observed.area_weighted_aspect": (1, 2.59),
    "all_observed.area_weighted_aspect_p95": (1, 6.13),
    "all_observed.axial_order": (0, 0.59),
    "all_observed.defined_aspect_area_fraction": (0.995, 1),
    "gap_dilation.2.largest_fraction": (0, 0.59),
    "limited_gap_run_x": (0, 0.60),
    "limited_gap_run_y": (0, 0.56),
    "long_range_abs_S2_difference": (0, 0.04),
    "nearest_neighbor_cv": (0.10, 0.69),
    "strips.1.column_max": (0, 0.79),
    "strips.1.column_std": (0, 0.18),
    "strips.1.row_max": (0, 0.78),
    "strips.1.row_std": (0, 0.20),
    "strips.8.column_max": (0, 0.74),
    "strips.8.column_std": (0, 0.17),
    "strips.8.row_max": (0, 0.75),
    "strips.8.row_std": (0, 0.19),
    "strips.16.column_max": (0, 0.71),
    "strips.16.column_std": (0, 0.16),
    "strips.16.row_max": (0, 0.69),
    "strips.16.row_std": (0, 0.17),
    "strips.32.column_max": (0, 0.64),
    "strips.32.column_std": (0, 0.14),
    "strips.32.row_max": (0, 0.63),
    "strips.32.row_std": (0, 0.16),
}


def _generate_centers(rng):
    """
    Generate a finite, irregular point process with independently
    sampled boundary-intersecting and interior populations.

    A minimum center distance controls crowding without imposing
    horizontal or vertical rows, columns, or reinforcement lanes.
    """
    centers = []

    for side in range(4):
        for k in range(N_EDGE_PER_SIDE):
            position = (
                (k + 0.5) * SIZE / N_EDGE_PER_SIDE
                + rng.uniform(-12.0, 12.0)
            )
            position = float(np.clip(position, 12.0, SIZE - 13.0))
            offset = float(rng.uniform(4.0, 7.5))

            if side == 0:
                point = (offset, position)
            elif side == 1:
                point = (SIZE - 1 - offset, position)
            elif side == 2:
                point = (position, offset)
            else:
                point = (position, SIZE - 1 - offset)

            centers.append(point)

    # A weak, smoothly varying point-process intensity produces
    # natural local clustering without constructing aligned bands.
    intensity = ndi.gaussian_filter(
        rng.normal(size=(64, 64)),
        sigma=7.0,
        mode="reflect",
    )
    intensity /= max(float(intensity.std()), 1e-12)

    for _ in range(N_INTERIOR):
        placed = False

        for _ in range(12):
            samples = rng.uniform(
                17.0, SIZE - 18.0, size=(64, 2)
            )

            existing = np.asarray(centers, dtype=float)
            distances = cKDTree(existing).query(samples, k=1)[0]

            valid = distances >= MIN_CENTER_DISTANCE

            if not np.any(valid):
                continue

            iy = np.clip((samples[:, 0] / 4).astype(int), 0, 63)
            ix = np.clip((samples[:, 1] / 4).astype(int), 0, 63)

            scores = (
                rng.gumbel(size=len(samples))
                + 0.075 * np.minimum(distances, 42.0)
                + 0.45 * intensity[iy, ix]
            )
            scores[~valid] = -np.inf

            chosen = int(np.argmax(scores))
            centers.append(tuple(samples[chosen]))
            placed = True
            break

        if not placed:
            raise RuntimeError(
                "Interior point-process construction exhausted"
            )

    return np.asarray(centers, dtype=float)


def _particle_parameters(rng, n):
    """
    Independently randomized angular morphology.

    Shapes are approximately star-convex angular inclusions, with
    moderate elongation, multiscale lobes, and occasional shallow
    concavities. A mixed axial distribution introduces a modest
    horizontal tendency without prescribed reinforcement lanes.
    """
    radius = np.clip(
        rng.lognormal(np.log(10.8), 0.22, n),
        7.5,
        15.5,
    )

    # Border particles begin partly within the observed field.
    # Their outside portions are naturally censored by the image.
    radius[:4 * N_EDGE_PER_SIDE] *= 1.10

    aspect = np.clip(
        rng.lognormal(np.log(1.58), 0.20, n),
        1.12,
        2.30,
    )

    orientation = rng.uniform(0.0, np.pi, n)

    preferred = rng.random(n) < 0.45
    orientation[preferred] = (
        rng.normal(0.0, 0.36, preferred.sum()) % np.pi
    )

    phase = rng.uniform(0.0, 2.0 * np.pi, (n, 4))
    amplitude = rng.uniform(
        (0.065, 0.045, 0.025, 0.015),
        (0.135, 0.105, 0.075, 0.045),
        size=(n, 4),
    )

    return radius, aspect, orientation, phase, amplitude


def _generate_candidate(rng):
    """
    Construct independent dispersed inclusions within buffered
    nearest-center cells.

    The buffered cell geometry prevents neighboring inclusions from
    coalescing under the specified two-pixel diagnostic dilation.

    Exact composition is obtained by selecting a common signed
    radial-level threshold. This changes the geometric extent of
    the particles directly, rather than adding disconnected pixels
    or performing evaluator-side repairs.
    """
    centers = _generate_centers(rng)
    n = len(centers)

    radius, aspect, orientation, phase, amplitude = (
        _particle_parameters(rng, n)
    )

    yy, xx = np.indices((SIZE, SIZE))
    points = np.column_stack(
        (yy.ravel(), xx.ravel())
    ).astype(float)

    distances, assignments = cKDTree(centers).query(
        points, k=2
    )

    nearest = assignments[:, 0]
    allowed = (
        distances[:, 1] - distances[:, 0] >= CELL_GAP
    )

    scores = np.full(SIZE * SIZE, -np.inf, dtype=float)

    for i in range(n):
        indices = np.flatnonzero(
            allowed & (nearest == i)
        )

        if not len(indices):
            raise RuntimeError("Particle cell contains no pixels")

        # Physical image coordinates: x right and y up.
        dx = points[indices, 1] - centers[i, 1]
        dy = centers[i, 0] - points[indices, 0]

        ca = np.cos(orientation[i])
        sa = np.sin(orientation[i])

        u = ca * dx + sa * dy
        v = -sa * dx + ca * dy

        a = aspect[i]

        elliptical_distance = np.sqrt(
            u * u / a + v * v * a
        )

        theta = np.arctan2(v, u)

        wave = (
            1.0
            + amplitude[i, 0]
            * np.sin(3.0 * theta + phase[i, 0])
            + amplitude[i, 1]
            * np.sin(5.0 * theta + phase[i, 1])
            + amplitude[i, 2]
            * np.cos(8.0 * theta + phase[i, 2])
            + amplitude[i, 3]
            * np.sin(11.0 * theta + phase[i, 3])
        )

        scores[indices] = (
            radius[i] * wave - elliptical_distance
        )

    if np.count_nonzero(np.isfinite(scores)) < TARGET_REINFORCEMENT:
        raise RuntimeError(
            "Insufficient feasible particle-cell area"
        )

    # Distinct continuous radial scores permit an exact global
    # count without introducing isolated correction pixels.
    selected = np.argpartition(
        scores, -TARGET_REINFORCEMENT
    )[-TARGET_REINFORCEMENT:]

    mask = np.zeros(SIZE * SIZE, dtype=bool)
    mask[selected] = True
    mask = mask.reshape(SIZE, SIZE)

    if int(mask.sum()) != TARGET_REINFORCEMENT:
        raise RuntimeError("Exact phase allocation failed")

    return np.where(mask, 5, 1).astype(np.uint8)


def _topology(mask, connectivity=1):
    structure = ndi.generate_binary_structure(2, connectivity)
    labels, count = ndi.label(mask, structure)

    sizes = np.bincount(labels.ravel())[1:]

    def spans(a, b):
        shared = (
            set(np.unique(a))
            & set(np.unique(b))
        ) - {0}
        return bool(shared)

    total = int(np.count_nonzero(mask))

    return {
        "regions": int(count),
        "largest_fraction": (
            float(sizes.max() / total)
            if sizes.size and total else None
        ),
        "spans_x": spans(labels[:, 0], labels[:, -1]),
        "spans_y": spans(labels[0], labels[-1]),
        "singleton_area_fraction": (
            float(sizes[sizes == 1].sum() / total)
            if sizes.size and total else None
        ),
    }


def _weighted_quantile(values, weights, q):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)

    if not len(values) or weights.sum() <= 0:
        return None

    order = np.argsort(values, kind="stable")
    values = values[order]
    weights = weights[order]

    index = np.searchsorted(
        np.cumsum(weights),
        q * weights.sum(),
        side="left",
    )

    return float(values[min(index, len(values) - 1)])


def _region_shapes(regions):
    total = sum(r.area for r in regions)

    aspects = []
    areas = []
    angles = []
    anisotropies = []

    for region in regions:
        xy = region.coords[:, [1, 0]].astype(float)
        xy[:, 1] *= -1.0
        xy -= xy.mean(axis=0)

        covariance = xy.T @ xy / len(xy)
        eigenvalues, eigenvectors = np.linalg.eigh(covariance)

        if eigenvalues[0] <= 1e-12:
            continue

        aspect = float(
            np.sqrt(eigenvalues[1] / eigenvalues[0])
        )

        direction = eigenvectors[:, 1]

        angle = float(
            np.arctan2(direction[1], direction[0]) % np.pi
        )

        anisotropy = float(
            (eigenvalues[1] - eigenvalues[0])
            / eigenvalues.sum()
        )

        aspects.append(aspect)
        areas.append(float(region.area))
        angles.append(angle)
        anisotropies.append(anisotropy)

    aspects = np.asarray(aspects, dtype=float)
    areas = np.asarray(areas, dtype=float)
    angles = np.asarray(angles, dtype=float)
    anisotropies = np.asarray(anisotropies, dtype=float)

    weights = (
        areas
        * anisotropies
        * (anisotropies >= 0.05)
    )

    if weights.sum() > 1e-12:
        order = abs(
            np.sum(weights * np.exp(2j * angles))
            / weights.sum()
        )
    else:
        order = None

    return {
        "regions": len(regions),
        "area": int(total),
        "defined_aspect_area_fraction": (
            float(areas.sum() / total)
            if total else None
        ),
        "unweighted_aspect_mean": (
            float(aspects.mean())
            if len(aspects) else None
        ),
        "area_weighted_aspect": (
            float(np.average(aspects, weights=areas))
            if len(aspects) else None
        ),
        "area_weighted_aspect_p95": (
            _weighted_quantile(aspects, areas, 0.95)
        ),
        "area_fraction_aspect_gt3": (
            float(areas[aspects > 3].sum() / total)
            if total else None
        ),
        "area_fraction_aspect_gt4": (
            float(areas[aspects > 4].sum() / total)
            if total else None
        ),
        "axial_order": (
            float(order) if order is not None else None
        ),
    }


def _directional_s2(mask, lag, axis):
    if lag == 0:
        return float(mask.mean())

    if axis == 0:
        a = mask[:-lag, :]
        b = mask[lag:, :]
    else:
        a = mask[:, :-lag]
        b = mask[:, lag:]

    return float(np.mean(a & b))


def _limited_gap_run(line, maxgap=2):
    positions = np.flatnonzero(line)

    if not len(positions):
        return 0

    breaks = np.flatnonzero(
        np.diff(positions) > maxgap + 1
    ) + 1

    starts = np.r_[0, breaks]
    ends = np.r_[breaks, len(positions)]

    return max(
        int(positions[b - 1] - positions[a] + 1)
        for a, b in zip(starts, ends)
    )


def _describe(mask):
    """
    Finite-window descriptors using all observed four-connected
    reinforcement components, with complete regions separately
    identified.

    Axial orientation uses area times eigenvalue anisotropy,
    excludes anisotropy below 0.05, and treats angles modulo pi.
    """
    mask = np.asarray(mask, dtype=bool)

    labels, count = ndi.label(mask)
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
        r for r in regions
        if r.label not in edge_labels
    ]

    result = {
        "all_observed": _region_shapes(regions),
        "complete": _region_shapes(complete),
        "boundary_censored_regions": len(edge_labels),
    }

    if len(complete) > 1:
        centers = np.array(
            [r.centroid for r in complete],
            dtype=float,
        )
        distances = cKDTree(centers).query(
            centers, k=2
        )[0][:, 1]

        result["nearest_neighbor_cv"] = float(
            distances.std() / distances.mean()
        )
    else:
        result["nearest_neighbor_cv"] = None

    differences = []

    for lag in LAGS:
        sx = _directional_s2(mask, lag, 1)
        sy = _directional_s2(mask, lag, 0)

        if lag >= 16:
            differences.append(abs(sy - sx))

    result["long_range_abs_S2_difference"] = float(
        np.mean(differences)
    )

    column_fraction = mask.mean(axis=0)
    row_fraction = mask.mean(axis=1)

    for width in WIDTHS:
        kernel = np.ones(width) / width

        columns = np.convolve(
            column_fraction, kernel, mode="valid"
        )
        rows = np.convolve(
            row_fraction, kernel, mode="valid"
        )

        result[f"strips.{width}.column_max"] = float(
            columns.max()
        )
        result[f"strips.{width}.column_std"] = float(
            columns.std()
        )
        result[f"strips.{width}.row_max"] = float(
            rows.max()
        )
        result[f"strips.{width}.row_std"] = float(
            rows.std()
        )

    yy, xx = np.mgrid[-2:3, -2:3]
    disk = xx * xx + yy * yy <= 4

    dilated = ndi.binary_dilation(
        mask,
        structure=disk,
        border_value=0,
    )

    dilation_topology = _topology(dilated, 2)

    result["gap_dilation.2.largest_fraction"] = (
        dilation_topology["largest_fraction"]
    )
    result["gap_dilation.2.spans_x"] = (
        dilation_topology["spans_x"]
    )
    result["gap_dilation.2.spans_y"] = (
        dilation_topology["spans_y"]
    )

    result["limited_gap_run_x"] = (
        max(_limited_gap_run(row) for row in mask)
        / SIZE
    )

    result["limited_gap_run_y"] = (
        max(
            _limited_gap_run(mask[:, x])
            for x in range(SIZE)
        )
        / SIZE
    )

    for group in ("all_observed", "complete"):
        for key, value in result[group].items():
            result[f"{group}.{key}"] = value

    return result


def _structural_ok(array):
    """
    Apply the supplied hard structural constraints directly to
    each generated candidate.

    The actual phase array is never diagnostically dilated or
    modified by this verification function.
    """
    if array.shape != (SIZE, SIZE):
        return False

    if array.dtype != np.uint8:
        return False

    if int(np.count_nonzero(array == 5)) != TARGET_REINFORCEMENT:
        return False

    if not np.all((array == 1) | (array == 5)):
        return False

    reinforcement = array == 5
    matrix = ~reinforcement

    matrix_topology = _topology(matrix, 1)

    if matrix_topology["largest_fraction"] < 0.95:
        return False

    if not (
        matrix_topology["spans_x"]
        and matrix_topology["spans_y"]
    ):
        return False

    for connectivity in (1, 2):
        topology = _topology(
            reinforcement, connectivity
        )

        if topology["spans_x"] or topology["spans_y"]:
            return False

        if topology["largest_fraction"] > 0.15:
            return False

        if connectivity == 1:
            if topology["singleton_area_fraction"] > 0.001:
                return False

    labels, n_regions = ndi.label(reinforcement)

    if not 50 <= n_regions <= 125:
        return False

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

    if not 5 <= len(edge_labels) <= 50:
        return False

    complete = [
        r for r in regions
        if r.label not in edge_labels
    ]

    if not 40 <= len(complete) <= 75:
        return False

    diameters = [
        r.equivalent_diameter_area
        for r in complete
    ]

    if not 12 <= np.mean(diameters) <= 20:
        return False

    aspects = [
        r.axis_major_length / r.axis_minor_length
        for r in complete
        if r.axis_minor_length > 0
    ]

    if not aspects:
        return False

    if not 1.2 <= np.mean(aspects) <= 3.0:
        return False

    descriptors = _describe(reinforcement)

    for key, (lower, upper) in MORPHOLOGY_BOUNDS.items():
        value = descriptors.get(key)

        if value is None:
            return False

        if not np.isfinite(value):
            return False

        if not lower <= value <= upper:
            return False

    if descriptors["gap_dilation.2.spans_x"]:
        return False

    if descriptors["gap_dilation.2.spans_y"]:
        return False

    return True


def generate_microstructure(seed, parameters={}):
    """
    Generate one stochastic, finite, nonperiodic P3 microstructure.

    Native phases:
        1: matrix-like solid
        5: provisional reinforcement-like solid

    Returns:
        (256, 256) uint8 array with exactly 20731 pixels of
        label 5 and 44805 pixels of label 1.

    Each seed determines an independent local random stream.
    At most eight geometry candidates are constructed.
    No mechanical solver, cached mechanical response, or
    reference raster is used.
    """
    if parameters is None:
        parameters = {}

    if not isinstance(parameters, dict):
        raise TypeError("parameters must be a dictionary")

    if parameters:
        raise ValueError(
            "No adjustable parameters are registered"
        )

    master_rng = np.random.default_rng(seed)

    for attempt in range(MAX_CANDIDATES):
        candidate_seed = int(
            master_rng.integers(0, 2**63 - 1)
        )

        rng = np.random.default_rng(candidate_seed)

        try:
            candidate = _generate_candidate(rng)
        except RuntimeError:
            continue

        if _structural_ok(candidate):
            return candidate

    raise RuntimeError(
        "No structurally feasible P3 microstructure "
        "within eight registered geometry candidates"
    )