import numpy as np
from scipy import ndimage as ndi
from scipy.special import ndtri
from scipy.spatial.distance import cdist
from skimage.measure import regionprops


SIZE = 256
TARGET_REINFORCEMENT = 20731
TARGET_MATRIX = 44805
N_COMPLETE = 57
D_MEAN = 15.706688295952011
D_STD = 8.893419110493891
MAX_CANDIDATES = 8

# The initial generator's measured development mean was already close
# to the target. Preserve its particle-size distribution, composition,
# packing mechanism, and disconnected-inclusion topology.
#
# Historical geometry comparisons indicate that pronounced vertical
# orientation tends to increase apparent vertical stiffness, whereas
# horizontal orientation tends to decrease it. Introduce only a weak
# vertical orientation preference to avoid overcorrecting.
#
# This is a geometry parameter, not a calibrated mechanical predictor.
ORIENTATION_WARP = 0.022

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


def _disk(radius):
    y, x = np.mgrid[-radius:radius + 1, -radius:radius + 1]
    return x * x + y * y <= radius * radius


def _fragment(rng, area, boundary=False):
    """
    Construct an irregular inclusion from a stochastic angular
    radius field.

    An exactly sized pixel set is obtained by ranking continuous
    geometric scores. No reference raster or fixed coordinates
    are used.

    Boundary fragments are constructed as finite observations
    of geometries whose centers lie outside an image half-plane.
    """
    area = int(area)

    if area < 12:
        raise RuntimeError("Requested fragment area is too small")

    for _ in range(12):
        aspect = float(np.clip(
            rng.lognormal(np.log(1.62), 0.27),
            1.06,
            2.75
        ))

        # Weak axial bias toward the vertical direction.
        # The mapping is monotonic and retains full angular support.
        # No additional RNG draws are introduced.
        base_angle = float(rng.uniform(0, np.pi))
        angle = (
            base_angle
            + ORIENTATION_WARP * np.sin(2.0 * base_angle)
        )

        ca = np.cos(angle)
        sa = np.sin(angle)

        nominal_radius = np.sqrt(area / np.pi)

        extent = int(np.ceil(
            5.0 * nominal_radius * np.sqrt(aspect) + 12
        ))
        extent = max(24, extent)

        if boundary:
            yy, xx = np.mgrid[
                0:extent + 1,
                -extent:extent + 1
            ]
            yc = -nominal_radius * rng.uniform(0.08, 0.23)
            xc = nominal_radius * rng.normal(0, 0.07)
        else:
            yy, xx = np.mgrid[
                -extent:extent + 1,
                -extent:extent + 1
            ]
            yc = 0.0
            xc = 0.0

        x = xx.astype(float) - xc
        y = yy.astype(float) - yc

        u = ca * x + sa * y
        v = -sa * x + ca * y

        u /= np.sqrt(aspect)
        v *= np.sqrt(aspect)

        radial = np.hypot(u, v)
        theta = np.mod(np.arctan2(v, u), 2 * np.pi)

        n = int(rng.integers(11, 19))
        knots = rng.normal(0, 0.18, n)

        if area > 120 and rng.random() < 0.55:
            for _ in range(int(rng.integers(1, 3))):
                j = int(rng.integers(n))
                knots[j] -= rng.uniform(0.11, 0.25)

        knots = np.clip(knots, -0.40, 0.40)

        phase = theta * n / (2 * np.pi)

        i0 = np.floor(phase).astype(int) % n
        i1 = (i0 + 1) % n

        alpha = phase - np.floor(phase)

        modulation = (
            1.0
            + (1.0 - alpha) * knots[i0]
            + alpha * knots[i1]
        )

        score = radial / np.maximum(modulation, 0.55)

        if area >= score.size:
            continue

        selected = np.argpartition(
            score.ravel(), area - 1
        )[:area]

        mask = np.zeros(score.size, dtype=bool)
        mask[selected] = True
        mask = mask.reshape(score.shape)

        if boundary and not mask[0].any():
            continue

        if ndi.label(mask)[1] != 1:
            continue

        rows, cols = np.where(mask)

        result = mask[
            rows.min():rows.max() + 1,
            cols.min():cols.max() + 1
        ]

        if int(result.sum()) == area:
            return result

    raise RuntimeError("Fragment construction exhausted")


def _paint(canvas, blocked, shape, x, y, exclusion):
    """
    Add an inclusion and update the local packing exclusion mask.

    The exclusion mask is used only for subsequent placement.
    It does not change the final reinforcement geometry.
    """
    h, w = shape.shape

    canvas[y:y + h, x:x + w] |= shape

    radius = (exclusion.shape[0] - 1) // 2

    x0 = max(0, x - radius)
    x1 = min(SIZE, x + w + radius)
    y0 = max(0, y - radius)
    y1 = min(SIZE, y + h + radius)

    local = np.zeros(
        (y1 - y0, x1 - x0),
        dtype=bool
    )

    local[
        y - y0:y - y0 + h,
        x - x0:x - x0 + w
    ] = shape

    blocked[y0:y1, x0:x1] |= ndi.binary_dilation(
        local,
        structure=exclusion,
        border_value=0
    )


def _place_fragment(
    rng, canvas, blocked, shape, field, exclusion,
    edge=None
):
    """
    Bounded stochastic placement of one observed inclusion.

    Complete regions remain inside the image.
    Boundary regions are censored by exactly one selected edge.

    Placement uses a weak correlated field, stochastic ranking,
    and a local geometric exclusion constraint.
    """
    h, w = shape.shape

    if h >= SIZE - 3 or w >= SIZE - 3:
        return False

    best = None
    best_score = -np.inf
    valid = 0

    maximum_trials = 750 if edge is not None else 1400

    for _ in range(maximum_trials):
        if edge is None:
            x = int(rng.integers(2, SIZE - w - 1))
            y = int(rng.integers(2, SIZE - h - 1))

        elif edge == 0:
            x = int(rng.integers(1, SIZE - w))
            y = 0

        elif edge == 1:
            x = int(rng.integers(1, SIZE - w))
            y = SIZE - h

        elif edge == 2:
            x = 0
            y = int(rng.integers(1, SIZE - h))

        else:
            x = SIZE - w
            y = int(rng.integers(1, SIZE - h))

        if np.any(
            blocked[y:y + h, x:x + w] & shape
        ):
            continue

        cy = min(SIZE - 1, y + h // 2)
        cx = min(SIZE - 1, x + w // 2)

        score = (
            0.32 * field[cy, cx]
            + 0.70 * rng.gumbel()
        )

        if score > best_score:
            best_score = score
            best = (x, y)

        valid += 1

        if valid >= 8:
            break

    if best is None:
        return False

    _paint(
        canvas,
        blocked,
        shape,
        best[0],
        best[1],
        exclusion
    )

    return True


def _complete_areas(rng):
    """
    Generate a broad, stratified inclusion-size population.
    Preserve the initial generator's diameter allocation.
    """
    q = (
        np.arange(N_COMPLETE)
        + rng.uniform(0.20, 0.80, N_COMPLETE)
    ) / N_COMPLETE

    z = ndtri(q)

    diameters = np.clip(
        D_MEAN + 0.94 * D_STD * z,
        6.5,
        35.0
    )

    areas = np.rint(
        np.pi * diameters * diameters / 4.0
    ).astype(int)

    rng.shuffle(areas)

    return areas


def _boundary_areas(rng, remaining, count):
    """
    Allocate the remaining exact area to boundary-censored regions.
    """
    weights = rng.lognormal(0, 0.33, count)
    proportions = weights / weights.sum()

    raw = remaining * proportions
    areas = np.floor(raw).astype(int)

    residual = int(remaining - areas.sum())

    if residual:
        order = np.argsort(raw - areas)[::-1]
        areas[order[:residual]] += 1

    if np.min(areas) < 40:
        raise RuntimeError(
            "Infeasible boundary area allocation"
        )

    return areas


def _generate_candidate(seed, parameters):
    """
    Generate one independent procedural geometry candidate.

    Composition is exact by construction. All region placement
    occurs within finite, nonperiodic image coordinates.
    """
    rng = np.random.default_rng(seed)

    canvas = np.zeros((SIZE, SIZE), dtype=bool)
    blocked = np.zeros_like(canvas)

    exclusion = _disk(5)

    coarse = ndi.gaussian_filter(
        rng.normal(size=(SIZE, SIZE)),
        19,
        mode="reflect"
    )
    coarse /= max(float(coarse.std()), 1e-10)

    fine = ndi.gaussian_filter(
        rng.normal(size=(SIZE, SIZE)),
        8,
        mode="reflect"
    )
    fine /= max(float(fine.std()), 1e-10)

    field = coarse + 0.30 * fine

    complete_areas = _complete_areas(rng)

    remaining = (
        TARGET_REINFORCEMENT - int(complete_areas.sum())
    )

    if remaining <= 0:
        raise RuntimeError(
            "Infeasible reinforcement composition allocation"
        )

    n_boundary = int(rng.integers(20, 25))

    boundary_areas = _boundary_areas(
        rng,
        remaining,
        n_boundary
    )

    boundary_areas = np.sort(boundary_areas)[::-1]

    edge_offset = int(rng.integers(4))

    # Boundary inclusions are placed first to preserve censored
    # features and avoid forcing them into residual packing gaps.
    for i, area in enumerate(boundary_areas):
        edge = (i + edge_offset) % 4

        shape = _fragment(
            rng,
            int(area),
            boundary=True
        )

        if edge == 1:
            shape = np.flipud(shape)
        elif edge == 2:
            shape = np.rot90(shape, 1)
        elif edge == 3:
            shape = np.rot90(shape, 3)

        success = _place_fragment(
            rng,
            canvas,
            blocked,
            shape,
            field,
            exclusion,
            edge=edge
        )

        if not success:
            raise RuntimeError(
                "Boundary-region packing exhausted"
            )

    # Largest-first packing preserves the specified broad diameter
    # distribution while retaining stochastic placement and shape.
    for area in sorted(complete_areas, reverse=True):
        shape = _fragment(
            rng,
            int(area),
            boundary=False
        )

        success = _place_fragment(
            rng,
            canvas,
            blocked,
            shape,
            field,
            exclusion,
            edge=None
        )

        if not success:
            raise RuntimeError(
                "Complete-region packing exhausted"
            )

    if int(canvas.sum()) != TARGET_REINFORCEMENT:
        raise RuntimeError(
            "Exact reinforcement composition was not achieved"
        )

    return np.where(canvas, 5, 1).astype(np.uint8)


def directional_s2(a, r, axis):
    """
    Directional two-point probability on finite overlapping support.
    No periodic wrapping is permitted.
    """
    if not 0 <= r < a.shape[axis]:
        raise ValueError("Lag outside finite image")

    if r == 0:
        return float(np.mean(a))

    lo = [slice(None)] * 2
    hi = lo.copy()

    lo[axis] = slice(None, -r)
    hi[axis] = slice(r, None)

    return float(np.mean(
        a[tuple(lo)].astype(float)
        * a[tuple(hi)]
    ))


def weighted_quantile(values, weights, q):
    if not len(values) or np.sum(weights) <= 0:
        return None

    order = np.argsort(values, kind="stable")

    v = np.asarray(values)[order]
    w = np.asarray(weights)[order]

    index = np.searchsorted(
        np.cumsum(w),
        q * np.sum(w),
        side="left"
    )

    return float(v[min(index, len(v) - 1)])


def region_shapes(regions):
    """
    Compute shape and axial statistics for supplied observed regions.

    Orientation conventions:
      x increases rightward;
      y increases upward;
      angles are axial, modulo pi;
      weights are area times eigenvalue anisotropy;
      anisotropy below 0.05 has zero orientation weight.

    Boundary-censored regions remain included whenever the caller
    supplies all observed regions.
    """
    total = sum(r.area for r in regions)

    aspects = []
    areas = []
    angles = []
    anisotropies = []

    for region in regions:
        xy = region.coords[:, [1, 0]].astype(float)

        xy[:, 1] *= -1
        xy -= xy.mean(axis=0)

        covariance = xy.T @ xy / len(xy)

        eigenvalues, eigenvectors = np.linalg.eigh(
            covariance
        )

        if eigenvalues[0] <= 1e-12:
            continue

        aspect = float(np.sqrt(
            eigenvalues[1] / eigenvalues[0]
        ))

        major = eigenvectors[:, 1]

        angle = float(
            np.arctan2(major[1], major[0]) % np.pi
        )

        anisotropy = float(
            (eigenvalues[1] - eigenvalues[0])
            / eigenvalues.sum()
        )

        aspects.append(aspect)
        areas.append(float(region.area))
        angles.append(angle)
        anisotropies.append(anisotropy)

    aspects = np.asarray(aspects)
    areas = np.asarray(areas)
    angles = np.asarray(angles)
    anisotropies = np.asarray(anisotropies)

    weights = (
        areas
        * anisotropies
        * (anisotropies >= 0.05)
    )

    if weights.sum() > 1e-12:
        z = np.sum(
            weights * np.exp(2j * angles)
        ) / weights.sum()
    else:
        z = None

    return {
        "regions": len(regions),
        "area": int(total),
        "defined_aspect_area_fraction": (
            float(areas.sum() / total)
            if total else None
        ),
        "unweighted_aspect_mean": (
            float(np.mean(aspects))
            if len(aspects) else None
        ),
        "area_weighted_aspect": (
            float(np.average(aspects, weights=areas))
            if len(aspects) else None
        ),
        "area_weighted_aspect_p95": weighted_quantile(
            aspects, areas, 0.95
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
            float(abs(z)) if z is not None else None
        ),
        "vertical_alignment": (
            float(-z.real) if z is not None else None
        ),
    }


def topology(mask, connectivity=1):
    structure = ndi.generate_binary_structure(
        2, connectivity
    )

    labels, count = ndi.label(
        mask,
        structure=structure
    )

    sizes = np.bincount(labels.ravel())[1:]

    def spans(a, b):
        return bool(
            (
                set(np.unique(a))
                & set(np.unique(b))
            ) - {0}
        )

    total = int(np.count_nonzero(mask))

    return {
        "regions": int(count),
        "largest_fraction": (
            float(sizes.max() / total)
            if total else None
        ),
        "spans_x": spans(
            labels[:, 0],
            labels[:, -1]
        ),
        "spans_y": spans(
            labels[0],
            labels[-1]
        ),
        "singleton_area_fraction": (
            float(sizes[sizes == 1].sum() / total)
            if total else None
        ),
    }


def limited_gap_run(line, maxgap=2):
    """
    Longest observed occupied span allowing internal unoccupied
    gaps of at most maxgap pixels.

    No extension beyond the first or last occupied pixel.
    """
    positions = np.flatnonzero(line)

    if not len(positions):
        return 0

    splits = np.r_[
        0,
        np.flatnonzero(
            np.diff(positions) > maxgap + 1
        ) + 1,
        len(positions)
    ]

    return max(
        int(positions[b - 1] - positions[a] + 1)
        for a, b in zip(splits[:-1], splits[1:])
    )


def describe(mask):
    a = np.asarray(mask, dtype=bool)

    labels, _ = ndi.label(a)
    regions = regionprops(labels)

    edge_labels = set(np.unique(np.r_[
        labels[0],
        labels[-1],
        labels[:, 0],
        labels[:, -1]
    ])) - {0}

    complete = [
        r for r in regions
        if r.label not in edge_labels
    ]

    centers = np.array([
        r.centroid for r in complete
    ])

    nearest = []

    if len(centers) > 1:
        distances = cdist(centers, centers)
        np.fill_diagonal(distances, np.inf)
        nearest = distances.min(axis=1)

    out = {
        "complete": region_shapes(complete),
        "all_observed": region_shapes(regions),
        "boundary_censored_regions": len(edge_labels),
        "correlation": {},
        "strips": {},
        "gap_dilation": {},
        "nearest_neighbor_cv": (
            float(np.std(nearest) / np.mean(nearest))
            if len(nearest) else None
        ),
    }

    differences = []

    for lag in LAGS:
        sx = directional_s2(a, lag, 1)
        sy = directional_s2(a, lag, 0)

        out["correlation"][str(lag)] = {
            "x": sx,
            "y": sy,
            "y_minus_x": sy - sx
        }

        if lag >= 16:
            differences.append(abs(sy - sx))

    out["long_range_abs_S2_difference"] = float(
        np.mean(differences)
    )

    for width in WIDTHS:
        kernel = np.ones(width) / width

        columns = np.convolve(
            a.mean(axis=0),
            kernel,
            mode="valid"
        )

        rows = np.convolve(
            a.mean(axis=1),
            kernel,
            mode="valid"
        )

        out["strips"][str(width)] = {
            "column_max": float(columns.max()),
            "column_std": float(columns.std()),
            "row_max": float(rows.max()),
            "row_std": float(rows.std())
        }

    # Diagnostic dilation is evaluated separately.
    # The actual reinforcement mask is never dilated.
    for radius in (1, 2):
        dilated = ndi.binary_dilation(
            a,
            structure=_disk(radius),
            border_value=0
        )

        out["gap_dilation"][str(radius)] = topology(
            dilated, 2
        )

    out["limited_gap_run_x"] = (
        max(limited_gap_run(row) for row in a)
        / SIZE
    )

    out["limited_gap_run_y"] = (
        max(
            limited_gap_run(a[:, i])
            for i in range(SIZE)
        )
        / SIZE
    )

    return out


def flattened(description):
    result = {}

    for group in ("complete", "all_observed"):
        for key, value in description[group].items():
            result[f"{group}.{key}"] = value

    for key in (
        "long_range_abs_S2_difference",
        "limited_gap_run_x",
        "limited_gap_run_y",
        "nearest_neighbor_cv"
    ):
        result[key] = description[key]

    for width, values in description["strips"].items():
        for key, value in values.items():
            result[f"strips.{width}.{key}"] = value

    for radius, values in description["gap_dilation"].items():
        for key, value in values.items():
            result[f"gap_dilation.{radius}.{key}"] = value

    return result


def _structural_ok(a):
    """
    Enforce the frozen per-array composition, topology, shape,
    orientation, spacing, finite-window and dilation constraints.

    Candidate acceptance is geometry-only; no elastic solver,
    surrogate mechanical outcome or cached response is used.
    """
    if a.shape != (SIZE, SIZE):
        return False

    if a.dtype != np.uint8:
        return False

    if set(np.unique(a)) != {1, 5}:
        return False

    reinforcement = a == 5

    if int(reinforcement.sum()) != TARGET_REINFORCEMENT:
        return False

    if int((a == 1).sum()) != TARGET_MATRIX:
        return False

    matrix = topology(~reinforcement, 1)

    if matrix["largest_fraction"] < 0.95:
        return False

    if not (
        matrix["spans_x"]
        and matrix["spans_y"]
    ):
        return False

    for connectivity in (1, 2):
        result = topology(
            reinforcement,
            connectivity
        )

        if result["spans_x"] or result["spans_y"]:
            return False

        if result["largest_fraction"] > 0.15:
            return False

        if connectivity == 1:
            if result["singleton_area_fraction"] > 0.001:
                return False

    labels, count = ndi.label(reinforcement)
    regions = regionprops(labels)

    edge_labels = set(np.unique(np.r_[
        labels[0],
        labels[-1],
        labels[:, 0],
        labels[:, -1]
    ])) - {0}

    complete = [
        r for r in regions
        if r.label not in edge_labels
    ]

    if not 50 <= count <= 125:
        return False

    if not 40 <= len(complete) <= 75:
        return False

    if not 5 <= len(edge_labels) <= 50:
        return False

    diameters = [
        r.equivalent_diameter_area
        for r in complete
    ]

    if not diameters:
        return False

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

    metrics = flattened(describe(reinforcement))

    for key, (minimum, maximum) in MORPHOLOGY_BOUNDS.items():
        value = metrics.get(key)

        if value is None:
            return False

        if not np.isfinite(value):
            return False

        if not minimum <= value <= maximum:
            return False

    dilation_fraction = metrics[
        "gap_dilation.2.largest_fraction"
    ]

    if dilation_fraction is None or dilation_fraction > 0.59:
        return False

    if metrics["gap_dilation.2.spans_x"]:
        return False

    if metrics["gap_dilation.2.spans_y"]:
        return False

    return True


def generate_microstructure(seed, parameters={}):
    """
    Return one stochastic P3 microstructure with exact composition.

    Output:
        shape: (256, 256)
        dtype: numpy.uint8
        matrix label: 1, exactly 44,805 pixels
        reinforcement label: 5, exactly 20,731 pixels

    Only local numpy.random.default_rng instances are used.
    Identical seeds produce identical arrays.

    The modest axial adjustment retains random angles, sizes,
    irregular shapes, clipped boundary features, finite support,
    dispersed inclusions, and independent seed variation.

    At most eight full geometry candidates are attempted.
    Exhaustion raises an explicit error without returning an
    invalid specimen or applying evaluator-side corrections.
    """
    if parameters is None:
        parameters = {}

    if parameters:
        raise ValueError(
            "This registered generator accepts empty parameters only"
        )

    rng = np.random.default_rng(seed)

    for _ in range(MAX_CANDIDATES):
        candidate_seed = int(
            rng.integers(0, 2**63)
        )

        try:
            candidate = _generate_candidate(
                candidate_seed,
                parameters
            )
        except RuntimeError:
            continue

        if _structural_ok(candidate):
            return candidate

    raise RuntimeError(
        "No structurally feasible P3 microstructure "
        "within eight registered geometry candidates"
    )