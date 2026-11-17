import numpy as np
from scipy import ndimage as ndi
from scipy.spatial.distance import cdist
from skimage.draw import polygon
from skimage.measure import regionprops

SIZE = 256
TARGET_REINFORCEMENT = 20731
MAX_CANDIDATES = 8
LAGS = (8, 16, 32, 64)
WIDTHS = (1, 8, 16, 32)

MORPHOLOGY_BOUNDS = {
    "all_observed.area_fraction_aspect_gt3": (0.0, 0.27),
    "all_observed.area_fraction_aspect_gt4": (0.0, 0.16),
    "all_observed.area_weighted_aspect": (1.0, 2.59),
    "all_observed.area_weighted_aspect_p95": (1.0, 6.13),
    "all_observed.axial_order": (0.0, 0.59),
    "all_observed.defined_aspect_area_fraction": (0.995, 1.0),
    "gap_dilation.2.largest_fraction": (0.0, 0.59),
    "limited_gap_run_x": (0.0, 0.60),
    "limited_gap_run_y": (0.0, 0.56),
    "long_range_abs_S2_difference": (0.0, 0.04),
    "nearest_neighbor_cv": (0.10, 0.69),
    "strips.1.column_max": (0.0, 0.79),
    "strips.1.column_std": (0.0, 0.18),
    "strips.1.row_max": (0.0, 0.78),
    "strips.1.row_std": (0.0, 0.20),
    "strips.8.column_max": (0.0, 0.74),
    "strips.8.column_std": (0.0, 0.17),
    "strips.8.row_max": (0.0, 0.75),
    "strips.8.row_std": (0.0, 0.19),
    "strips.16.column_max": (0.0, 0.71),
    "strips.16.column_std": (0.0, 0.16),
    "strips.16.row_max": (0.0, 0.69),
    "strips.16.row_std": (0.0, 0.17),
    "strips.32.column_max": (0.0, 0.64),
    "strips.32.column_std": (0.0, 0.14),
    "strips.32.row_max": (0.0, 0.63),
    "strips.32.row_std": (0.0, 0.16),
}


def _disk(radius):
    y, x = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    return x * x + y * y <= radius * radius


def _particle(rng, target_area):
    """
    Construct an irregular polygonal inclusion with stochastic angular
    indentations, independent orientation, and controlled anisotropy.
    """
    n = int(rng.integers(13, 23))

    theta = (
        np.arange(n) + rng.uniform(-0.30, 0.30, n)
    ) * (2.0 * np.pi / n)

    noise = rng.normal(0.0, 0.20, n)

    radii = np.clip(
        1.0
        + noise
        + 0.18 * np.roll(noise, 1)
        + 0.12 * np.roll(noise, -1),
        0.53,
        1.49,
    )

    if target_area > 85:
        if rng.random() < 0.78:
            for _ in range(int(rng.integers(1, 4))):
                k = int(rng.integers(n))
                radii[k] *= rng.uniform(0.43, 0.78)

    aspect = float(
        np.clip(
            rng.lognormal(np.log(1.55), 0.25),
            1.06,
            2.75,
        )
    )

    x = radii * np.cos(theta) * np.sqrt(aspect)
    y = radii * np.sin(theta) / np.sqrt(aspect)

    angle = rng.uniform(0.0, np.pi)
    ca, sa = np.cos(angle), np.sin(angle)

    xx = x * ca - y * sa
    yy = x * sa + y * ca

    polygon_area = 0.5 * abs(
        np.sum(
            xx * np.roll(yy, -1)
            - yy * np.roll(xx, -1)
        )
    )

    scale = np.sqrt(
        max(float(target_area), 9.0) / max(polygon_area, 0.01)
    )

    mask = None

    for _ in range(5):
        px = xx * scale
        py = yy * scale

        px = px - px.min() + 2.0
        py = py - py.min() + 2.0

        h = int(np.ceil(py.max())) + 3
        w = int(np.ceil(px.max())) + 3

        mask = np.zeros((h, w), dtype=bool)

        rr, cc = polygon(py, px, shape=mask.shape)
        mask[rr, cc] = True

        labels, count = ndi.label(mask)

        if count == 0:
            raise RuntimeError("Degenerate inclusion polygon")

        if count > 1:
            sizes = np.bincount(labels.ravel())
            sizes[0] = 0
            mask = labels == np.argmax(sizes)

        actual = int(mask.sum())

        if actual == 0:
            raise RuntimeError("Empty inclusion polygon")

        scale *= np.sqrt(
            max(float(target_area), 9.0) / actual
        )

    rows, cols = np.where(mask)

    if len(rows) == 0:
        raise RuntimeError("Empty rasterized inclusion")

    return mask[
        rows.min():rows.max() + 1,
        cols.min():cols.max() + 1,
    ]


def _spatial_field(rng):
    """
    Smooth stochastic intensity variation encourages modest local
    clustering without introducing prescribed columns or rows.
    """
    coarse = ndi.gaussian_filter(
        rng.normal(size=(SIZE, SIZE)),
        sigma=19.0,
        mode="reflect",
    )

    intermediate = ndi.gaussian_filter(
        rng.normal(size=(SIZE, SIZE)),
        sigma=8.0,
        mode="reflect",
    )

    coarse /= max(float(coarse.std()), 1e-10)
    intermediate /= max(float(intermediate.std()), 1e-10)

    return 0.65 * coarse + 0.35 * intermediate


def _place(rng, canvas, shape, field, boundary=False, target=None):
    """
    Place one connected inclusion using bounded randomized proposals.

    Existing regions receive a three-pixel Euclidean exclusion zone.
    Boundary particles are genuinely clipped by the finite image.
    """
    h, w = shape.shape

    if h >= SIZE - 3 or w >= SIZE - 3:
        return 0

    blocked = ndi.binary_dilation(
        canvas,
        structure=_disk(3),
        border_value=0,
    )

    best = None
    best_score = -np.inf

    trials = 340 if boundary else 320

    for _ in range(trials):
        if boundary:
            edge = int(rng.integers(4))

            if edge < 2:
                cut = max(
                    1,
                    int(rng.uniform(0.12, 0.68) * h),
                )

                y = -cut if edge == 0 else SIZE - h + cut

                low = -w // 4
                high = SIZE - 3 * w // 4 + 1

                if high <= low:
                    continue

                x = int(rng.integers(low, high))

            else:
                cut = max(
                    1,
                    int(rng.uniform(0.12, 0.68) * w),
                )

                x = -cut if edge == 2 else SIZE - w + cut

                low = -h // 4
                high = SIZE - 3 * h // 4 + 1

                if high <= low:
                    continue

                y = int(rng.integers(low, high))

        else:
            x = int(rng.integers(2, SIZE - w - 1))
            y = int(rng.integers(2, SIZE - h - 1))

        x0 = max(0, x)
        x1 = min(SIZE, x + w)

        y0 = max(0, y)
        y1 = min(SIZE, y + h)

        if x0 >= x1 or y0 >= y1:
            continue

        part = shape[
            y0 - y:y1 - y,
            x0 - x:x1 - x,
        ]

        area = int(part.sum())

        if area < 12:
            continue

        if np.any(
            blocked[y0:y1, x0:x1] & part
        ):
            continue

        if boundary:
            touches = (
                (x0 == 0 and part[:, 0].any())
                or (x1 == SIZE and part[:, -1].any())
                or (y0 == 0 and part[0].any())
                or (y1 == SIZE and part[-1].any())
            )

            if not touches:
                continue

            if ndi.label(part)[1] != 1:
                continue

        score = (
            0.35 * field[
                (y0 + y1 - 1) // 2,
                (x0 + x1 - 1) // 2,
            ]
            + rng.normal(0.0, 0.75)
        )

        if boundary:
            desired = max(float(target), 1.0)

            score -= 5.0 * abs(
                np.log(area / desired)
            )

        if score > best_score:
            best_score = score
            best = (y0, y1, x0, x1, part.copy())

    if best is None:
        return 0

    y0, y1, x0, x1, part = best

    canvas[y0:y1, x0:x1] |= part

    return int(part.sum())


def _exact_count(canvas, rng):
    """
    Adjust inclusion boundaries without creating new disconnected
    particles or joining existing particles.

    Changes are confined to interior pixels. Each accepted addition
    has a four-connected parent and cannot join different original
    or growing eight-connected regions.

    Local foreground/background connectivity guards reject bridges
    and topology-damaging deletions.
    """
    delta = TARGET_REINFORCEMENT - int(canvas.sum())

    if delta == 0:
        return canvas

    if abs(delta) > 2048:
        raise RuntimeError(
            "Count correction exceeds registered bound"
        )

    adding = delta > 0
    remaining = abs(delta)

    structure4 = ndi.generate_binary_structure(2, 1)

    labels, _ = ndi.label(canvas, structure4)

    for _ in range(5):
        if remaining == 0:
            break

        if adding:
            frontier = (
                ndi.binary_dilation(
                    canvas,
                    structure=np.ones((3, 3), dtype=bool),
                )
                & ~canvas
            )
        else:
            frontier = (
                canvas
                & ~ndi.binary_erosion(
                    canvas,
                    structure=np.ones((3, 3), dtype=bool),
                )
            )

        frontier[0, :] = False
        frontier[-1, :] = False
        frontier[:, 0] = False
        frontier[:, -1] = False

        sites = np.argwhere(frontier)
        rng.shuffle(sites)

        progress = 0

        for y, x in sites:
            y, x = int(y), int(x)

            if bool(canvas[y, x]) == adding:
                continue

            old = canvas[
                y - 1:y + 2,
                x - 1:x + 2,
            ].copy()

            new = old.copy()
            new[1, 1] = adding

            if adding:
                neighborhood = labels[
                    y - 1:y + 2,
                    x - 1:x + 2,
                ]

                ids = np.unique(neighborhood)
                ids = ids[ids != 0]

                if len(ids) != 1:
                    continue

                parent = int(ids[0])

                four = (
                    neighborhood[0, 1],
                    neighborhood[1, 0],
                    neighborhood[1, 2],
                    neighborhood[2, 1],
                )

                if parent not in four:
                    continue

                before_background = ndi.label(
                    ~old, structure4
                )[1]

                after_background = ndi.label(
                    ~new, structure4
                )[1]

                if after_background > before_background:
                    continue

                labels[y, x] = parent

            else:
                old_count = ndi.label(
                    old, structure4
                )[1]

                new_count = ndi.label(
                    new, structure4
                )[1]

                if new_count > old_count:
                    continue

                if (
                    int(new[0, 1])
                    + int(new[1, 0])
                    + int(new[1, 2])
                    + int(new[2, 1])
                ) < 2:
                    continue

                labels[y, x] = 0

            canvas[y, x] = adding

            remaining -= 1
            progress += 1

            if remaining == 0:
                break

        if progress == 0:
            break

    if remaining:
        raise RuntimeError(
            "Bounded topology-preserving count calibration exhausted"
        )

    if int(canvas.sum()) != TARGET_REINFORCEMENT:
        raise RuntimeError("Exact pixel count not achieved")

    return canvas


def _generate_candidate(seed, parameters):
    """
    Generate an independent finite-field dispersed microstructure.

    Boundary-censored and complete inclusions are constructed
    separately. Interior inclusion areas are adaptively budgeted
    against the exact remaining reinforcement count.
    """
    rng = np.random.default_rng(seed)

    canvas = np.zeros((SIZE, SIZE), dtype=bool)
    field = _spatial_field(rng)

    n_boundary = int(rng.integers(17, 23))
    n_complete = int(rng.integers(59, 65))

    boundary_budget = float(
        rng.integers(3000, 4101)
    )

    boundary_weights = rng.lognormal(
        mean=0.0,
        sigma=0.36,
        size=n_boundary,
    )

    boundary_targets = (
        boundary_budget
        * boundary_weights
        / boundary_weights.sum()
    )

    boundary_targets = np.sort(
        boundary_targets
    )[::-1]

    for desired in boundary_targets:
        placed = 0

        for factor in (1.0, 0.92, 0.84):
            full_area = (
                float(desired)
                * float(rng.uniform(1.65, 1.95))
                * factor
            )

            shape = _particle(rng, full_area)

            placed = _place(
                rng,
                canvas,
                shape,
                field,
                boundary=True,
                target=desired,
            )

            if placed:
                break

        if not placed:
            raise RuntimeError(
                "Boundary inclusion placement exhausted"
            )

    if int(canvas.sum()) >= TARGET_REINFORCEMENT:
        raise RuntimeError(
            "Boundary inclusion area exceeds target"
        )

    diameter_weights = np.clip(
        rng.lognormal(
            mean=0.0,
            sigma=0.36,
            size=n_complete,
        ),
        0.42,
        1.90,
    )

    area_weights = np.sort(
        diameter_weights ** 2
    )[::-1]

    for i in range(n_complete):
        remaining_area = (
            TARGET_REINFORCEMENT - int(canvas.sum())
        )

        remaining_weight = float(
            area_weights[i:].sum()
        )

        desired = (
            remaining_area
            * float(area_weights[i])
            / remaining_weight
        )

        if not 24 <= desired <= 1600:
            raise RuntimeError(
                "Infeasible interior inclusion area allocation"
            )

        placed = 0

        for factor in (1.0, 0.92, 0.84):
            shape = _particle(
                rng,
                desired * factor,
            )

            placed = _place(
                rng,
                canvas,
                shape,
                field,
                boundary=False,
            )

            if placed:
                break

        if not placed:
            raise RuntimeError(
                "Complete inclusion placement exhausted"
            )

    canvas = _exact_count(canvas, rng)

    return np.where(
        canvas, 5, 1
    ).astype(np.uint8)


def _topology(mask, connectivity=1):
    structure = ndi.generate_binary_structure(
        2, connectivity
    )

    labels, n = ndi.label(mask, structure)

    sizes = np.bincount(labels.ravel())[1:]

    def spans(first, second):
        a = set(np.unique(first))
        b = set(np.unique(second))
        return bool((a & b) - {0})

    return {
        "regions": int(n),
        "largest_fraction": (
            float(sizes.max() / mask.sum())
            if sizes.size else 0.0
        ),
        "spans_x": spans(
            labels[:, 0], labels[:, -1]
        ),
        "spans_y": spans(
            labels[0, :], labels[-1, :]
        ),
        "singleton_area_fraction": (
            float(sizes[sizes == 1].sum() / mask.sum())
            if sizes.size else 0.0
        ),
    }


def _weighted_quantile(values, weights, q):
    values = np.asarray(values, dtype=float)
    weights = np.asarray(weights, dtype=float)

    if len(values) == 0 or weights.sum() <= 0:
        return None

    order = np.argsort(values, kind="stable")

    v = values[order]
    w = weights[order]

    index = np.searchsorted(
        np.cumsum(w),
        q * w.sum(),
        side="left",
    )

    return float(v[min(index, len(v) - 1)])


def _region_shapes(regions):
    total = sum(r.area for r in regions)

    if total == 0:
        return None

    aspects = []
    areas = []
    angles = []
    anisotropies = []

    for region in regions:
        xy = region.coords[:, [1, 0]].astype(float)

        xy[:, 1] *= -1.0
        xy -= xy.mean(axis=0)

        covariance = xy.T @ xy / len(xy)

        values, vectors = np.linalg.eigh(covariance)

        if values[0] <= 1e-12:
            continue

        aspect = float(
            np.sqrt(values[1] / values[0])
        )

        vector = vectors[:, 1]

        angle = float(
            np.arctan2(
                vector[1], vector[0]
            ) % np.pi
        )

        anisotropy = float(
            (values[1] - values[0])
            / max(values.sum(), 1e-12)
        )

        aspects.append(aspect)
        areas.append(float(region.area))
        angles.append(angle)
        anisotropies.append(anisotropy)

    if not aspects:
        return None

    aspects = np.asarray(aspects)
    areas = np.asarray(areas)
    angles = np.asarray(angles)
    anisotropies = np.asarray(anisotropies)

    orientation_weights = (
        areas
        * anisotropies
        * (anisotropies >= 0.05)
    )

    weight_sum = float(orientation_weights.sum())

    if weight_sum > 1e-12:
        z = (
            np.sum(
                orientation_weights
                * np.exp(2j * angles)
            )
            / weight_sum
        )
        axial_order = float(abs(z))
    else:
        axial_order = None

    return {
        "defined_aspect_area_fraction": float(
            areas.sum() / total
        ),
        "area_weighted_aspect": float(
            np.average(aspects, weights=areas)
        ),
        "area_weighted_aspect_p95": _weighted_quantile(
            aspects, areas, 0.95
        ),
        "area_fraction_aspect_gt3": float(
            areas[aspects > 3.0].sum() / total
        ),
        "area_fraction_aspect_gt4": float(
            areas[aspects > 4.0].sum() / total
        ),
        "axial_order": axial_order,
    }


def _directional_s2(mask, lag, axis):
    if lag == 0:
        return float(mask.mean())

    if axis == 0:
        return float(
            np.mean(
                mask[:-lag, :] & mask[lag:, :]
            )
        )

    return float(
        np.mean(
            mask[:, :-lag] & mask[:, lag:]
        )
    )


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


def _morphology_descriptors(mask, regions, complete):
    result = {}

    shapes = _region_shapes(regions)

    if shapes is None:
        return None

    for key, value in shapes.items():
        result["all_observed." + key] = value

    centers = np.asarray(
        [r.centroid for r in complete],
        dtype=float,
    )

    if len(centers) < 2:
        return None

    distances = cdist(centers, centers)

    np.fill_diagonal(distances, np.inf)

    nearest = distances.min(axis=1)

    if nearest.mean() <= 0:
        return None

    result["nearest_neighbor_cv"] = float(
        nearest.std() / nearest.mean()
    )

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
        kernel = np.ones(width, dtype=float) / width

        columns = np.convolve(
            column_fraction,
            kernel,
            mode="valid",
        )

        rows = np.convolve(
            row_fraction,
            kernel,
            mode="valid",
        )

        prefix = "strips." + str(width) + "."

        result[prefix + "column_max"] = float(
            columns.max()
        )

        result[prefix + "column_std"] = float(
            columns.std()
        )

        result[prefix + "row_max"] = float(
            rows.max()
        )

        result[prefix + "row_std"] = float(
            rows.std()
        )

    dilated = ndi.binary_dilation(
        mask,
        structure=_disk(2),
        border_value=0,
    )

    dilation_topology = _topology(
        dilated, connectivity=2
    )

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
        max(
            _limited_gap_run(mask[y, :])
            for y in range(SIZE)
        )
        / SIZE
    )

    result["limited_gap_run_y"] = (
        max(
            _limited_gap_run(mask[:, x])
            for x in range(SIZE)
        )
        / SIZE
    )

    return result


def _structural_ok(array):
    if array.shape != (SIZE, SIZE):
        return False

    if array.dtype != np.uint8:
        return False

    if set(np.unique(array)) != {1, 5}:
        return False

    mask = array == 5

    if int(mask.sum()) != TARGET_REINFORCEMENT:
        return False

    matrix_topology = _topology(
        ~mask, connectivity=1
    )

    if matrix_topology["largest_fraction"] < 0.95:
        return False

    if not (
        matrix_topology["spans_x"]
        and matrix_topology["spans_y"]
    ):
        return False

    for connectivity in (1, 2):
        reinforcement_topology = _topology(
            mask,
            connectivity=connectivity,
        )

        if (
            reinforcement_topology["spans_x"]
            or reinforcement_topology["spans_y"]
        ):
            return False

        if reinforcement_topology["largest_fraction"] > 0.15:
            return False

        if (
            connectivity == 1
            and reinforcement_topology[
                "singleton_area_fraction"
            ] > 0.001
        ):
            return False

    labels, count = ndi.label(mask)

    if not 50 <= count <= 125:
        return False

    regions = regionprops(labels)

    boundary_labels = set(
        np.unique(
            np.r_[
                labels[0, :],
                labels[-1, :],
                labels[:, 0],
                labels[:, -1],
            ]
        )
    ) - {0}

    if not 5 <= len(boundary_labels) <= 50:
        return False

    complete = [
        region
        for region in regions
        if region.label not in boundary_labels
    ]

    if not 40 <= len(complete) <= 75:
        return False

    diameters = np.asarray(
        [
            region.equivalent_diameter_area
            for region in complete
        ]
    )

    if not 12.0 <= float(diameters.mean()) <= 20.0:
        return False

    complete_aspects = [
        region.axis_major_length / region.axis_minor_length
        for region in complete
        if region.axis_minor_length > 0
    ]

    if not complete_aspects:
        return False

    if not 1.2 <= float(np.mean(complete_aspects)) <= 3.0:
        return False

    values = _morphology_descriptors(
        mask, regions, complete
    )

    if values is None:
        return False

    for key, (lower, upper) in MORPHOLOGY_BOUNDS.items():
        value = values.get(key)

        if value is None:
            return False

        if not np.isfinite(value):
            return False

        if not lower <= value <= upper:
            return False

    if values["gap_dilation.2.spans_x"]:
        return False

    if values["gap_dilation.2.spans_y"]:
        return False

    return True


def generate_microstructure(seed, parameters={}):
    """
    Generate a stochastic 256x256 P3 microstructure.

    Labels:
        1: matrix-like solid
        5: provisional reinforcement-like solid

    Exactly 20731 pixels have label 5.

    Uses at most eight independent geometry candidates, without
    mechanical simulation or external data. An explicit exception
    is raised if no candidate satisfies all feasibility limits.
    """
    if parameters is None:
        parameters = {}

    if parameters:
        raise ValueError(
            "This registered generator uses empty parameters"
        )

    rng = np.random.default_rng(seed)

    for _ in range(MAX_CANDIDATES):
        candidate_seed = int(
            rng.integers(0, 2**63)
        )

        try:
            candidate = _generate_candidate(
                candidate_seed, parameters
            )
        except RuntimeError:
            continue

        if _structural_ok(candidate):
            return candidate

    raise RuntimeError(
        "No structurally feasible microstructure within "
        "eight registered geometry candidates"
    )