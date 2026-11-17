
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree
from scipy.spatial.distance import cdist
from skimage.measure import regionprops

SIZE = 256
TARGET_REINFORCEMENT = 20731
TARGET_MATRIX = 44805
MAX_CANDIDATES = 8

MIN_SITE_SEPARATION = 18.5
VORONOI_CLEARANCE = 6.8

# The initial generator's three measured development moduli were
# 1636.705, 1647.957, and 1650.549 MPa (mean 1645.070 MPa).
# All three were feasible and inside the target band.
#
# The revision therefore retains the successful geometric model.
# A weak horizontal orientation bias is introduced to modestly
# reduce vertical reinforcement efficiency. The perturbation is
# deliberately small because the measured mean is already only
# about 0.31% above the 1640 MPa target.
#
# This is a geometry-only hypothesis, not a calibrated mechanical
# prediction. No solver, mechanical surrogate, or result cache
# is used during generation.
HORIZONTAL_ANGLE_WARP = 0.014

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


def _generate_sites(rng):
    """
    Generate independently randomized inclusion sites using sequential
    spatial inhibition, without a lattice or periodic continuation.

    Boundary centers remain inside the finite field, while their
    inclusion geometries may be clipped by its edges.
    """
    sites = []
    minimum_squared = MIN_SITE_SEPARATION ** 2

    def acceptable(point):
        if not sites:
            return True

        existing = np.asarray(sites)
        squared = np.sum((existing - point) ** 2, axis=1)

        return bool(np.all(squared >= minimum_squared))

    for side in range(4):
        for _ in range(6):
            for trial in range(600):
                along = rng.uniform(6.0, 250.0)
                offset = rng.uniform(0.1, 5.8)

                if side == 0:
                    point = np.array([offset, along])
                elif side == 1:
                    point = np.array([SIZE - offset, along])
                elif side == 2:
                    point = np.array([along, offset])
                else:
                    point = np.array([along, SIZE - offset])

                if acceptable(point):
                    sites.append(point)
                    break
            else:
                raise RuntimeError(
                    "Boundary site placement exhausted its fixed bound"
                )

    required_interior = int(rng.integers(66, 71))
    target_total = len(sites) + required_interior

    for trial in range(18000):
        if len(sites) == target_total:
            break

        point = rng.uniform(
            12.0, SIZE - 12.0, size=2
        )

        if acceptable(point):
            sites.append(point)

    if len(sites) != target_total:
        raise RuntimeError(
            "Interior site placement exhausted its fixed bound"
        )

    return np.asarray(sites, dtype=np.float64)


def _particle_fields(rng, sites):
    """
    Construct irregular, angular, separated inclusions with independent
    particle-scale random morphology.

    The only mechanical-feedback-informed geometric adjustment is
    a small smooth axial orientation perturbation toward horizontal.

    All spatial positions, scales, and fine shapes remain stochastic.
    """
    count = len(sites)

    radii = np.clip(
        rng.lognormal(np.log(12.5), 0.30, count),
        7.5,
        21.5,
    )

    aspect = np.clip(
        rng.lognormal(np.log(1.43), 0.23, count),
        1.03,
        2.35,
    )

    raw_orientation = rng.uniform(
        0.0, np.pi, count
    )

    # Smooth transformation of the original uniform orientation
    # distribution. Horizontal axes (0 and pi) are weakly favored,
    # while vertical axes (pi/2) are weakly disfavored.
    #
    # The maximum angular displacement is 0.014 radians.
    # No preferred particle positions or artificial lanes are added.
    orientation = (
        raw_orientation
        - HORIZONTAL_ANGLE_WARP
        * np.sin(2.0 * raw_orientation)
    ) % np.pi

    phase3 = rng.uniform(-np.pi, np.pi, count)
    phase5 = rng.uniform(-np.pi, np.pi, count)
    phase8 = rng.uniform(-np.pi, np.pi, count)
    phase11 = rng.uniform(-np.pi, np.pi, count)

    notch_angle = rng.uniform(-np.pi, np.pi, count)
    notch_width = rng.uniform(0.16, 0.30, count)
    notch_depth = rng.uniform(0.11, 0.26, count)

    coarse = ndi.gaussian_filter(
        rng.normal(size=(SIZE, SIZE)),
        sigma=32.0,
        mode="reflect",
    )

    coarse /= max(float(coarse.std()), 1e-10)

    sample_x = np.clip(
        np.rint(sites[:, 0]).astype(int),
        0,
        SIZE - 1,
    )

    sample_y = np.clip(
        np.rint(sites[:, 1]).astype(int),
        0,
        SIZE - 1,
    )

    radii *= np.clip(
        1.0 + 0.075 * coarse[sample_y, sample_x],
        0.82,
        1.18,
    )

    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    points = np.column_stack(
        (xx.ravel(), yy.ravel())
    )

    tree = cKDTree(sites)
    distances, assignments = tree.query(
        points, k=2
    )

    owner = assignments[:, 0]
    nearest = distances[:, 0]
    second = distances[:, 1]

    dx = points[:, 0] - sites[owner, 0]
    dy = points[:, 1] - sites[owner, 1]

    cos_a = np.cos(orientation[owner])
    sin_a = np.sin(orientation[owner])

    u = cos_a * dx + sin_a * dy
    v = -sin_a * dx + cos_a * dy

    stretch = np.sqrt(aspect[owner])

    ex = u / stretch
    ey = v * stretch

    radial = np.hypot(ex, ey)
    theta = np.arctan2(ey, ex)

    modulation = (
        1.0
        + 0.130 * np.sin(
            3.0 * theta + phase3[owner]
        )
        + 0.080 * np.sin(
            5.0 * theta + phase5[owner]
        )
        + 0.055 * np.cos(
            8.0 * theta + phase8[owner]
        )
        + 0.028 * np.sin(
            11.0 * theta + phase11[owner]
        )
    )

    difference = theta - notch_angle[owner]

    difference = np.arctan2(
        np.sin(difference),
        np.cos(difference),
    )

    indentation = notch_depth[owner] * np.exp(
        -0.5
        * (
            difference / notch_width[owner]
        ) ** 2
    )

    modulation = np.clip(
        modulation - indentation,
        0.58,
        1.43,
    )

    score = radii[owner] * modulation - radial

    # Distance-difference clearance separates independently owned
    # inclusion regions and inhibits artificial connected networks.
    # The finite field is never periodically wrapped.
    safe = (
        second - nearest
    ) >= VORONOI_CLEARANCE

    score[~safe] = -np.inf

    return score


def _construct_candidate(seed):
    """
    Construct a finite categorical field with exact native composition.

    Exact-count selection uses stochastic geometric growth scores.
    It does not evaluate mechanics or match stored reference pixels.
    """
    rng = np.random.default_rng(seed)

    sites = _generate_sites(rng)
    score = _particle_fields(rng, sites)

    if (
        np.count_nonzero(np.isfinite(score))
        < TARGET_REINFORCEMENT
    ):
        raise RuntimeError(
            "Insufficient admissible pixels for exact composition"
        )

    cutoff_index = (
        score.size - TARGET_REINFORCEMENT
    )

    selected = np.argpartition(
        score, cutoff_index
    )[cutoff_index:]

    if not np.all(np.isfinite(score[selected])):
        raise RuntimeError(
            "Exact composition selection exhausted admissible geometry"
        )

    reinforcement = np.zeros(
        SIZE * SIZE, dtype=bool
    )

    reinforcement[selected] = True

    reinforcement = reinforcement.reshape(
        SIZE, SIZE
    )

    output = np.where(
        reinforcement, 5, 1
    ).astype(np.uint8)

    if int(np.count_nonzero(output == 5)) != TARGET_REINFORCEMENT:
        raise RuntimeError(
            "Exact reinforcement count failed"
        )

    if int(np.count_nonzero(output == 1)) != TARGET_MATRIX:
        raise RuntimeError(
            "Exact matrix count failed"
        )

    return output


def _topology(mask, connectivity):
    structure = ndi.generate_binary_structure(
        2, connectivity
    )

    labels, count = ndi.label(
        mask, structure=structure
    )

    sizes = np.bincount(labels.ravel())[1:]
    total = int(np.count_nonzero(mask))

    if total == 0:
        return {
            "regions": 0,
            "largest_fraction": 0.0,
            "singleton_fraction": 0.0,
            "spans_x": False,
            "spans_y": False,
        }

    left = set(np.unique(labels[:, 0]))
    right = set(np.unique(labels[:, -1]))
    top = set(np.unique(labels[0, :]))
    bottom = set(np.unique(labels[-1, :]))

    return {
        "regions": int(count),
        "largest_fraction": float(
            sizes.max() / total
        ),
        "singleton_fraction": float(
            sizes[sizes == 1].sum() / total
        ),
        "spans_x": bool(
            (left & right) - {0}
        ),
        "spans_y": bool(
            (top & bottom) - {0}
        ),
    }


def _weighted_quantile(values, weights, q):
    values = np.asarray(
        values, dtype=float
    )

    weights = np.asarray(
        weights, dtype=float
    )

    if (
        len(values) == 0
        or weights.sum() <= 0
    ):
        return None

    order = np.argsort(
        values, kind="stable"
    )

    sorted_values = values[order]
    sorted_weights = weights[order]

    index = np.searchsorted(
        np.cumsum(sorted_weights),
        q * sorted_weights.sum(),
        side="left",
    )

    return float(
        sorted_values[
            min(index, len(values) - 1)
        ]
    )


def _region_shapes(regions):
    """
    Compute shape and orientation descriptors over all observed
    regions, including boundary-censored regions.

    x increases rightward and y increases upward.
    Orientations are axial, modulo pi.
    """
    total = float(
        sum(region.area for region in regions)
    )

    if total == 0:
        return None

    areas = []
    aspects = []
    angles = []
    anisotropies = []

    for region in regions:
        xy = region.coords[:, [1, 0]].astype(float)

        xy[:, 1] *= -1.0
        xy -= xy.mean(axis=0)

        covariance = (
            xy.T @ xy
        ) / len(xy)

        eigenvalues, eigenvectors = np.linalg.eigh(
            covariance
        )

        if eigenvalues[0] <= 1e-12:
            continue

        aspect = float(
            np.sqrt(
                eigenvalues[1] / eigenvalues[0]
            )
        )

        anisotropy = float(
            (eigenvalues[1] - eigenvalues[0])
            / max(eigenvalues.sum(), 1e-12)
        )

        direction = eigenvectors[:, 1]

        angle = float(
            np.arctan2(
                direction[1],
                direction[0],
            ) % np.pi
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

    if weights.sum() > 1e-12:
        axial = np.sum(
            weights * np.exp(2j * angles)
        ) / weights.sum()

        axial_order = float(abs(axial))
    else:
        axial_order = None

    return {
        "defined_aspect_area_fraction": float(
            areas.sum() / total
        ),
        "area_weighted_aspect": float(
            np.average(
                aspects, weights=areas
            )
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


def _limited_gap_run(line, maximum_gap=2):
    positions = np.flatnonzero(line)

    if len(positions) == 0:
        return 0

    divisions = np.flatnonzero(
        np.diff(positions) > maximum_gap + 1
    ) + 1

    starts = np.r_[0, divisions]
    ends = np.r_[divisions, len(positions)]

    return max(
        int(
            positions[b - 1]
            - positions[a]
            + 1
        )
        for a, b in zip(starts, ends)
    )


def _finite_s2(mask, lag, axis):
    if axis == 1:
        return float(
            np.mean(
                mask[:, :-lag]
                & mask[:, lag:]
            )
        )

    return float(
        np.mean(
            mask[:-lag, :]
            & mask[lag:, :]
        )
    )


def _descriptors(mask, complete, regions):
    """
    Compute the registered structural acceptance descriptors.

    Two-pixel dilation is used only for diagnostics.
    It never modifies the specimen returned by the generator.
    """
    result = {}

    all_shapes = _region_shapes(regions)

    if all_shapes is None:
        return None

    for key, value in all_shapes.items():
        result[
            "all_observed." + key
        ] = value

    centers = np.asarray(
        [
            region.centroid
            for region in complete
        ],
        dtype=float,
    )

    if len(centers) < 2:
        return None

    distances = cdist(
        centers, centers
    )

    np.fill_diagonal(
        distances, np.inf
    )

    nearest = distances.min(axis=1)

    if nearest.mean() <= 0:
        return None

    result["nearest_neighbor_cv"] = float(
        nearest.std() / nearest.mean()
    )

    correlation_differences = []

    for lag in (16, 32, 64):
        sx = _finite_s2(
            mask, lag, axis=1
        )
        sy = _finite_s2(
            mask, lag, axis=0
        )

        correlation_differences.append(
            abs(sy - sx)
        )

    result["long_range_abs_S2_difference"] = float(
        np.mean(correlation_differences)
    )

    column_fraction = mask.mean(axis=0)
    row_fraction = mask.mean(axis=1)

    for width in (1, 8, 16, 32):
        kernel = (
            np.ones(width, dtype=float)
            / width
        )

        column = np.convolve(
            column_fraction,
            kernel,
            mode="valid",
        )

        row = np.convolve(
            row_fraction,
            kernel,
            mode="valid",
        )

        prefix = (
            "strips."
            + str(width)
            + "."
        )

        result[prefix + "column_max"] = float(
            column.max()
        )

        result[prefix + "column_std"] = float(
            column.std()
        )

        result[prefix + "row_max"] = float(
            row.max()
        )

        result[prefix + "row_std"] = float(
            row.std()
        )

    yy, xx = np.mgrid[-2:3, -2:3]

    disk = (
        xx * xx + yy * yy
    ) <= 4

    dilated = ndi.binary_dilation(
        mask,
        structure=disk,
        border_value=0,
    )

    dilation_topology = _topology(
        dilated, 2
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
        ) / SIZE
    )

    result["limited_gap_run_y"] = (
        max(
            _limited_gap_run(mask[:, x])
            for x in range(SIZE)
        ) / SIZE
    )

    return result


def _structural_ok(output):
    """
    Enforce unchanged composition, connectivity, region populations,
    and all registered hard morphology thresholds.
    """
    if output.shape != (SIZE, SIZE):
        return False

    if output.dtype != np.uint8:
        return False

    if not np.array_equal(
        np.unique(output),
        np.array([1, 5], dtype=np.uint8),
    ):
        return False

    reinforcement = output == 5

    if int(reinforcement.sum()) != TARGET_REINFORCEMENT:
        return False

    if int(np.count_nonzero(output == 1)) != TARGET_MATRIX:
        return False

    matrix = ~reinforcement
    matrix_topology = _topology(
        matrix, 1
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
            reinforcement, connectivity
        )

        if reinforcement_topology["spans_x"]:
            return False

        if reinforcement_topology["spans_y"]:
            return False

        if (
            reinforcement_topology["largest_fraction"]
            > 0.15
        ):
            return False

        if connectivity == 1:
            if (
                reinforcement_topology["singleton_fraction"]
                > 0.001
            ):
                return False

    labels, count = ndi.label(
        reinforcement
    )

    regions = regionprops(labels)

    if not (50 <= count <= 125):
        return False

    boundary_labels = np.unique(
        np.concatenate(
            (
                labels[0, :],
                labels[-1, :],
                labels[:, 0],
                labels[:, -1],
            )
        )
    )

    boundary_labels = set(
        int(value)
        for value in boundary_labels
        if value != 0
    )

    complete = [
        region
        for region in regions
        if region.label not in boundary_labels
    ]

    if not (40 <= len(complete) <= 75):
        return False

    if not (
        5 <= len(boundary_labels) <= 50
    ):
        return False

    diameters = np.asarray(
        [
            region.equivalent_diameter_area
            for region in complete
        ]
    )

    if not (
        12.0 <= diameters.mean() <= 20.0
    ):
        return False

    complete_aspects = [
        region.axis_major_length
        / region.axis_minor_length
        for region in complete
        if region.axis_minor_length > 0
    ]

    if not complete_aspects:
        return False

    aspect_mean = float(
        np.mean(complete_aspects)
    )

    if not (
        1.2 <= aspect_mean <= 3.0
    ):
        return False

    descriptors = _descriptors(
        reinforcement,
        complete,
        regions,
    )

    if descriptors is None:
        return False

    if descriptors["gap_dilation.2.spans_x"]:
        return False

    if descriptors["gap_dilation.2.spans_y"]:
        return False

    for key, bounds in MORPHOLOGY_BOUNDS.items():
        value = descriptors.get(key)

        if value is None:
            return False

        if not np.isfinite(value):
            return False

        if not (
            bounds[0] <= value <= bounds[1]
        ):
            return False

    return True


def generate_microstructure(seed, parameters={}):
    """
    Return one finite, independently randomized P3-like microstructure.

    Shape: (256, 256)
    Dtype: uint8
    Native labels:
        1 = matrix-like solid
        5 = provisional reinforcement-like solid

    Exact composition:
        label 1 = 44,805 pixels
        label 5 = 20,731 pixels

    Each input seed initializes a local RNG. The same seed reproduces
    the same candidate sequence, while distinct seeds generate new
    site arrangements and independently varying particle geometries.

    At most eight candidate geometries are attempted. Only structural
    feasibility is used for acceptance. No modulus prediction or
    mechanical solver is evaluated during generation.

    Failure to produce a feasible candidate is explicit.
    """
    rng = np.random.default_rng(seed)

    for attempt in range(MAX_CANDIDATES):
        candidate_seed = int(
            rng.integers(
                0,
                2**63,
                dtype=np.int64,
            )
        )

        try:
            candidate = _construct_candidate(
                candidate_seed
            )
        except RuntimeError:
            continue

        if _structural_ok(candidate):
            return candidate

    raise RuntimeError(
        "No structurally feasible stochastic P3 microstructure "
        "was generated within eight registered geometry candidates"
    )
