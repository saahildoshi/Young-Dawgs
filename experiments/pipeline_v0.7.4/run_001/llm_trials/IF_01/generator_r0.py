import numpy as np
from scipy import ndimage as ndi
from scipy.special import ndtri
from scipy.spatial.distance import cdist
from skimage.draw import polygon
from skimage.measure import regionprops

SIZE = 256
TARGET_PIXELS = 20731
N_COMPLETE = 57
N_BOUNDARY = 22
D_MEAN = 15.706688295952011
D_STD = 8.893419110493891
MAX_CANDIDATES = 8

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


def _disk(radius):
    y, x = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    return x * x + y * y <= radius * radius


def _particle(rng, target_area):
    """Construct a stochastic angular, irregular, simply connected inclusion."""
    n = int(rng.integers(14, 25))

    angles = (
        np.arange(n) + rng.uniform(-0.22, 0.22, n)
    ) * (2.0 * np.pi / n)

    noise = rng.normal(0.0, 0.19, n)
    noise = (
        0.70 * noise
        + 0.15 * np.roll(noise, 1)
        + 0.15 * np.roll(noise, -1)
    )

    radii = np.clip(1.0 + noise, 0.55, 1.45)

    if target_area > 100:
        for _ in range(int(rng.integers(1, 4))):
            j = int(rng.integers(n))
            radii[j] *= rng.uniform(0.52, 0.86)

    aspect = float(
        np.clip(
            rng.lognormal(np.log(1.52), 0.27),
            1.04,
            2.85,
        )
    )

    x = radii * np.cos(angles) * np.sqrt(aspect)
    y = radii * np.sin(angles) / np.sqrt(aspect)

    theta = rng.uniform(0.0, np.pi)
    ct, st = np.cos(theta), np.sin(theta)

    xr = ct * x - st * y
    yr = st * x + ct * y

    base_area = 0.5 * abs(
        np.sum(xr * np.roll(yr, -1) - yr * np.roll(xr, -1))
    )

    scale = np.sqrt(target_area / max(base_area, 0.01))
    mask = None

    for _ in range(4):
        xx = xr * scale
        yy = yr * scale

        xx = xx - xx.min() + 3.0
        yy = yy - yy.min() + 3.0

        height = int(np.ceil(yy.max())) + 4
        width = int(np.ceil(xx.max())) + 4

        mask = np.zeros((height, width), dtype=bool)
        rr, cc = polygon(yy, xx, shape=mask.shape)
        mask[rr, cc] = True

        labels, count = ndi.label(mask)

        if count:
            sizes = np.bincount(labels.ravel())[1:]
            mask = labels == (1 + np.argmax(sizes))

        mask = ndi.binary_fill_holes(mask)
        scale *= np.sqrt(target_area / max(int(mask.sum()), 1))

    if mask is None or not mask.any():
        raise RuntimeError("Particle rasterization failed")

    rows, cols = np.where(mask)
    return mask[
        rows.min():rows.max() + 1,
        cols.min():cols.max() + 1,
    ]


def _placement_field(rng):
    """Moderate isotropic clustering without preferred straight corridors."""
    coarse = ndi.gaussian_filter(
        rng.normal(size=(SIZE, SIZE)), 19.0, mode="reflect"
    )
    fine = ndi.gaussian_filter(
        rng.normal(size=(SIZE, SIZE)), 7.0, mode="reflect"
    )

    coarse /= max(float(coarse.std()), 1e-10)
    fine /= max(float(fine.std()), 1e-10)

    return 0.70 * coarse + 0.28 * fine


def _place_particle(rng, canvas, shape, field, boundary=False, target=None):
    """Place one region with a four-pixel exclusion neighborhood."""
    h, w = shape.shape

    if h >= SIZE - 4 or w >= SIZE - 4:
        return 0

    blocked = ndi.binary_dilation(
        canvas, structure=_disk(4), border_value=0
    )

    best = None
    best_score = -np.inf

    for _ in range(320):
        if boundary:
            edge = int(rng.integers(4))

            if edge < 2:
                x = int(rng.integers(1, SIZE - w))
                cut = int(rng.uniform(0.08, 0.62) * h) + 1
                y = -cut if edge == 0 else SIZE - h + cut
            else:
                y = int(rng.integers(1, SIZE - h))
                cut = int(rng.uniform(0.08, 0.62) * w) + 1
                x = -cut if edge == 2 else SIZE - w + cut

        else:
            x = int(rng.integers(2, SIZE - w - 1))
            y = int(rng.integers(2, SIZE - h - 1))

        x0 = max(0, x)
        x1 = min(SIZE, x + w)
        y0 = max(0, y)
        y1 = min(SIZE, y + h)

        if x0 >= x1 or y0 >= y1:
            continue

        piece = shape[y0 - y:y1 - y, x0 - x:x1 - x]
        area = int(piece.sum())

        if area == 0:
            continue

        if np.any(blocked[y0:y1, x0:x1] & piece):
            continue

        if boundary:
            touches = (
                (x0 == 0 and piece[:, 0].any())
                or (x1 == SIZE and piece[:, -1].any())
                or (y0 == 0 and piece[0].any())
                or (y1 == SIZE and piece[-1].any())
            )

            if not touches:
                continue

            if area < max(35, 0.48 * target):
                continue

            if ndi.label(piece)[1] != 1:
                continue

            rows, cols = np.where(piece)
            if rows.max() - rows.min() < 3:
                continue
            if cols.max() - cols.min() < 3:
                continue

            score = (
                -6.0 * abs(np.log(area / max(target, 1.0)))
                + 0.20 * field[(y0 + y1) // 2, (x0 + x1) // 2]
                + 0.20 * rng.gumbel()
            )

        else:
            score = (
                0.55 * field[(y0 + y1) // 2, (x0 + x1) // 2]
                + rng.gumbel()
            )

        if score > best_score:
            best_score = score
            best = (y0, y1, x0, x1, piece.copy(), area)

    if best is None:
        return 0

    y0, y1, x0, x1, piece, area = best
    canvas[y0:y1, x0:x1] |= piece

    return area


def _exact_count(canvas, rng):
    """Adjust existing region boundaries without connecting distinct regions.

    Every addition belongs to an existing 4-connected inclusion and remains
    farther than four pixels from other inclusions. Local simple-point tests
    protect foreground connectivity and matrix connectivity. Boundary pixels
    are fixed, preserving the generated censored-region population.
    """
    delta = TARGET_PIXELS - int(canvas.sum())

    if abs(delta) > 2048:
        raise RuntimeError("Count correction exceeds bounded allowance")

    if delta == 0:
        return canvas

    adding = delta > 0
    remaining = abs(delta)

    cross = ndi.generate_binary_structure(2, 1)
    disk4 = _disk(4)

    labels, _ = ndi.label(canvas, structure=cross)

    for iteration in range(8):
        if remaining == 0:
            break

        if adding:
            boundary = (
                ndi.binary_dilation(canvas, structure=cross)
                & ~canvas
            )
        else:
            boundary = (
                canvas
                & ~ndi.binary_erosion(canvas, structure=cross)
            )

        boundary[0, :] = False
        boundary[-1, :] = False
        boundary[:, 0] = False
        boundary[:, -1] = False

        sites = np.argwhere(boundary)
        rng.shuffle(sites)

        changed = 0

        for y, x in sites:
            y = int(y)
            x = int(x)

            if bool(canvas[y, x]) == adding:
                continue

            patch = canvas[y - 1:y + 2, x - 1:x + 2].copy()

            neighbor_ids = np.array(
                [
                    labels[y - 1, x],
                    labels[y + 1, x],
                    labels[y, x - 1],
                    labels[y, x + 1],
                ],
                dtype=np.int32,
            )

            occupied_ids = neighbor_ids[neighbor_ids > 0]

            if adding:
                if occupied_ids.size == 0:
                    continue

                if np.any(occupied_ids != occupied_ids[0]):
                    continue

                region_id = int(occupied_ids[0])

                if occupied_ids.size < 2 and iteration < 2:
                    continue

                ya = max(0, y - 4)
                yb = min(SIZE, y + 5)
                xa = max(0, x - 4)
                xb = min(SIZE, x + 5)

                neighborhood = labels[ya:yb, xa:xb]
                disk = disk4[
                    ya - y + 4:yb - y + 4,
                    xa - x + 4:xb - x + 4,
                ]

                foreign = (
                    (neighborhood != 0)
                    & (neighborhood != region_id)
                    & disk
                )

                if np.any(foreign):
                    continue

            else:
                if occupied_ids.size < 2:
                    continue

                region_id = int(labels[y, x])

                if region_id == 0:
                    continue

            patch[1, 1] = adding

            foreground_count = ndi.label(
                patch, structure=cross
            )[1]

            background_count = ndi.label(
                ~patch, structure=cross
            )[1]

            if foreground_count != 1:
                continue

            if background_count > 1:
                continue

            canvas[y, x] = adding
            labels[y, x] = region_id if adding else 0

            remaining -= 1
            changed += 1

            if remaining == 0:
                break

        if changed == 0:
            break

    if remaining:
        raise RuntimeError(
            "Topology-preserving exact-count calibration exhausted"
        )

    return canvas


def _generate_candidate(candidate_seed):
    rng = np.random.default_rng(candidate_seed)
    canvas = np.zeros((SIZE, SIZE), dtype=bool)

    field = _placement_field(rng)

    q = (
        np.arange(N_COMPLETE)
        + rng.uniform(0.15, 0.85, N_COMPLETE)
    ) / N_COMPLETE

    raw = np.exp(0.53 * ndtri(q))
    diameters = (
        D_MEAN
        + D_STD * (raw - raw.mean()) / max(raw.std(), 1e-8)
    )
    diameters = np.clip(diameters, 5.0, 43.0)

    particles = [
        _particle(rng, np.pi * float(d) ** 2 / 4.0)
        for d in diameters
    ]

    particles.sort(key=lambda p: p.sum(), reverse=True)

    estimated_complete_area = sum(int(p.sum()) for p in particles)

    boundary_budget = TARGET_PIXELS - estimated_complete_area

    if not 2500 <= boundary_budget <= 12500:
        raise RuntimeError("Infeasible boundary area allocation")

    weights = rng.lognormal(0.0, 0.42, N_BOUNDARY)
    boundary_targets = boundary_budget * weights / weights.sum()

    boundary_particles = []

    for target in boundary_targets:
        full_area = target * rng.uniform(1.40, 1.80)
        shape = _particle(rng, full_area)
        boundary_particles.append((shape, float(target)))

    boundary_particles.sort(
        key=lambda item: item[1], reverse=True
    )

    # Introduce large interior regions before allocating the edge population.
    for shape in particles[:16]:
        _place_particle(rng, canvas, shape, field)

    # Edge-censored features are actual clipped polygons, not labels assigned
    # retrospectively to complete inclusions.
    for shape, target in boundary_particles:
        _place_particle(
            rng, canvas, shape, field,
            boundary=True, target=target
        )

    # Remaining interior fragments fill the open field without regular lanes.
    for shape in particles[16:]:
        _place_particle(rng, canvas, shape, field)

    if not canvas.any():
        raise RuntimeError("Empty candidate")

    canvas = _exact_count(canvas, rng)

    return np.where(canvas, 5, 1).astype(np.uint8)


def _topology(mask, connectivity=1):
    structure = ndi.generate_binary_structure(2, connectivity)
    labels, count = ndi.label(mask, structure=structure)

    sizes = np.bincount(labels.ravel())[1:]
    total = int(mask.sum())

    left = set(np.unique(labels[:, 0]))
    right = set(np.unique(labels[:, -1]))
    top = set(np.unique(labels[0, :]))
    bottom = set(np.unique(labels[-1, :]))

    return {
        "regions": count,
        "largest_fraction": (
            float(sizes.max() / total) if sizes.size and total else 0.0
        ),
        "singleton_fraction": (
            float(sizes[sizes == 1].sum() / total)
            if sizes.size and total else 0.0
        ),
        "spans_x": bool((left & right) - {0}),
        "spans_y": bool((top & bottom) - {0}),
    }


def _weighted_quantile(values, weights, quantile):
    order = np.argsort(values, kind="stable")
    values = np.asarray(values)[order]
    weights = np.asarray(weights)[order]

    cumulative = np.cumsum(weights)
    index = np.searchsorted(
        cumulative, quantile * cumulative[-1], side="left"
    )

    return float(values[min(index, len(values) - 1)])


def _shape_descriptors(regions):
    total = float(sum(r.area for r in regions))

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

        major = eigenvectors[:, 1]

        angle = float(
            np.arctan2(major[1], major[0]) % np.pi
        )

        anisotropy = float(
            (eigenvalues[1] - eigenvalues[0])
            / max(eigenvalues.sum(), 1e-12)
        )

        aspects.append(aspect)
        areas.append(float(region.area))
        angles.append(angle)
        anisotropies.append(anisotropy)

    if not aspects or total <= 0:
        return None

    aspects = np.asarray(aspects)
    areas = np.asarray(areas)
    angles = np.asarray(angles)
    anisotropies = np.asarray(anisotropies)

    orientation_weights = (
        areas * anisotropies * (anisotropies >= 0.05)
    )

    if orientation_weights.sum() > 1e-12:
        z = np.sum(
            orientation_weights * np.exp(2j * angles)
        ) / orientation_weights.sum()
        axial_order = float(abs(z))
    else:
        axial_order = 0.0

    return {
        "area_fraction_aspect_gt3": float(
            areas[aspects > 3.0].sum() / total
        ),
        "area_fraction_aspect_gt4": float(
            areas[aspects > 4.0].sum() / total
        ),
        "area_weighted_aspect": float(
            np.average(aspects, weights=areas)
        ),
        "area_weighted_aspect_p95": _weighted_quantile(
            aspects, areas, 0.95
        ),
        "defined_aspect_area_fraction": float(
            areas.sum() / total
        ),
        "axial_order": axial_order,
    }


def _directional_s2(mask, lag, axis):
    lo = [slice(None), slice(None)]
    hi = [slice(None), slice(None)]

    lo[axis] = slice(None, -lag)
    hi[axis] = slice(lag, None)

    return float(
        np.mean(
            mask[tuple(lo)] & mask[tuple(hi)]
        )
    )


def _limited_gap_run(line, maxgap=2):
    positions = np.flatnonzero(line)

    if positions.size == 0:
        return 0

    split = np.r_[
        0,
        np.flatnonzero(np.diff(positions) > maxgap + 1) + 1,
        len(positions),
    ]

    return max(
        int(positions[b - 1] - positions[a] + 1)
        for a, b in zip(split[:-1], split[1:])
    )


def _descriptor_values(mask, regions, complete):
    values = {}

    shapes = _shape_descriptors(regions)

    if shapes is None:
        return None

    for key, value in shapes.items():
        values["all_observed." + key] = value

    centers = np.asarray(
        [r.centroid for r in complete], dtype=float
    )

    if len(centers) <= 1:
        return None

    distances = cdist(centers, centers)
    np.fill_diagonal(distances, np.inf)

    nearest = distances.min(axis=1)

    values["nearest_neighbor_cv"] = float(
        nearest.std() / max(nearest.mean(), 1e-12)
    )

    differences = []

    for lag in (16, 32, 64):
        sx = _directional_s2(mask, lag, 1)
        sy = _directional_s2(mask, lag, 0)
        differences.append(abs(sy - sx))

    values["long_range_abs_S2_difference"] = float(
        np.mean(differences)
    )

    column_fraction = mask.mean(axis=0)
    row_fraction = mask.mean(axis=1)

    for width in (1, 8, 16, 32):
        kernel = np.ones(width, dtype=float) / width

        columns = np.convolve(
            column_fraction, kernel, mode="valid"
        )
        rows = np.convolve(
            row_fraction, kernel, mode="valid"
        )

        prefix = "strips." + str(width) + "."

        values[prefix + "column_max"] = float(columns.max())
        values[prefix + "column_std"] = float(columns.std())
        values[prefix + "row_max"] = float(rows.max())
        values[prefix + "row_std"] = float(rows.std())

    values["limited_gap_run_x"] = (
        max(_limited_gap_run(mask[y, :]) for y in range(SIZE))
        / SIZE
    )

    values["limited_gap_run_y"] = (
        max(_limited_gap_run(mask[:, x]) for x in range(SIZE))
        / SIZE
    )

    dilation = ndi.binary_dilation(
        mask, structure=_disk(2), border_value=0
    )

    dilation_topology = _topology(dilation, 2)

    values["gap_dilation.2.largest_fraction"] = (
        dilation_topology["largest_fraction"]
    )

    values["gap_dilation.2.spans_x"] = (
        dilation_topology["spans_x"]
    )
    values["gap_dilation.2.spans_y"] = (
        dilation_topology["spans_y"]
    )

    return values


def _structural_ok(array):
    if array.shape != (SIZE, SIZE):
        return False

    if array.dtype != np.uint8:
        return False

    if set(np.unique(array)) != {1, 5}:
        return False

    reinforcement = array == 5

    if int(reinforcement.sum()) != TARGET_PIXELS:
        return False

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
        result = _topology(reinforcement, connectivity)

        if result["spans_x"] or result["spans_y"]:
            return False

        if result["largest_fraction"] > 0.15:
            return False

        if (
            connectivity == 1
            and result["singleton_fraction"] > 0.001
        ):
            return False

    labels, count = ndi.label(reinforcement)

    if not 50 <= count <= 125:
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

    n_boundary = len(edge_labels)

    if not 5 <= n_boundary <= 50:
        return False

    complete = [
        region for region in regions
        if region.label not in edge_labels
    ]

    if not 40 <= len(complete) <= 75:
        return False

    diameters = [
        region.equivalent_diameter_area
        for region in complete
    ]

    diameter_mean = float(np.mean(diameters))

    if not 12.0 <= diameter_mean <= 20.0:
        return False

    complete_aspects = [
        region.axis_major_length / region.axis_minor_length
        for region in complete
        if region.axis_minor_length > 0
    ]

    if not complete_aspects:
        return False

    aspect_mean = float(np.mean(complete_aspects))

    if not 1.2 <= aspect_mean <= 3.0:
        return False

    values = _descriptor_values(
        reinforcement, regions, complete
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
    """Generate a deterministic stochastic two-phase P3 microstructure.

    Labels:
        1: matrix-like solid
        5: provisional reinforcement-like solid

    The procedure generates at most eight independent geometry candidates.
    It uses no mechanical simulation, reference raster, or cached results.
    """
    rng = np.random.default_rng(seed)

    for _ in range(MAX_CANDIDATES):
        candidate_seed = int(
            rng.integers(0, np.iinfo(np.int64).max)
        )

        try:
            candidate = _generate_candidate(candidate_seed)
        except RuntimeError:
            continue

        if _structural_ok(candidate):
            return candidate

    raise RuntimeError(
        "No structurally feasible P3 microstructure "
        "within eight registered geometry candidates"
    )