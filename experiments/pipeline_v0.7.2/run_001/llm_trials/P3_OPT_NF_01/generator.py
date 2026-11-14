import numpy as np

SIZE = 256
TARGET_COUNT = 20731

N_PRIMARY = 4
N_SECONDARY = 2
PRIMARY_SEGMENTS = 4
SECONDARY_SEGMENTS = 21

PRIMARY_WIDTH_MIN = 16
PRIMARY_WIDTH_MAX = 22
PRIMARY_WIDTH_SUM = 73
SECONDARY_WIDTH = 5

MIN_LANE_GAP = 4
VERTICAL_GAP = 1


def _primary_widths(rng):
    """Randomize primary inclusion widths at fixed total nominal width."""
    widths = np.full(N_PRIMARY, PRIMARY_WIDTH_SUM // N_PRIMARY, dtype=int)
    remainder = PRIMARY_WIDTH_SUM - int(widths.sum())

    for i in rng.permutation(N_PRIMARY)[:remainder]:
        widths[i] += 1

    for _ in range(24):
        i, j = rng.choice(N_PRIMARY, size=2, replace=False)
        if widths[i] > 17 and widths[j] < 20:
            widths[i] -= 1
            widths[j] += 1

    return widths


def _segment_lengths(rng, n, primary, shift=0.0):
    """
    Partition a vertical lane into separated inclusions.

    Primary gaps are staggered between lanes. Secondary inclusions
    retain a smaller characteristic size and moderate aspect ratio.
    """
    available = SIZE - VERTICAL_GAP * (n - 1)

    cuts = np.arange(1, n, dtype=float) * available / n

    if primary:
        cuts += shift
        cuts += rng.uniform(-3.0, 3.0, size=n - 1)
    else:
        cuts += rng.uniform(-0.75, 0.75, size=n - 1)

    cuts = np.rint(cuts).astype(int)
    return np.diff(np.concatenate(([0], cuts, [available])))


def _primary_profile(rng, length, nominal_width):
    """
    Construct a compact, vertically elongated angular inclusion.

    Width perturbations are limited to preserve substantial axial
    overlap between successive inclusions in the same lane.
    """
    width = int(np.clip(
        nominal_width + rng.integers(-1, 2),
        PRIMARY_WIDTH_MIN,
        PRIMARY_WIDTH_MAX
    ))

    profile = np.full(length, width, dtype=int)

    # Shallow, stochastic side steps rather than deep constrictions.
    for _ in range(int(rng.integers(1, 4))):
        extent = int(rng.integers(3, max(4, length // 3 + 1)))
        start = int(rng.integers(0, length - extent + 1))
        change = int(rng.choice([-1, 1]))

        profile[start:start + extent] = np.clip(
            profile[start:start + extent] + change,
            PRIMARY_WIDTH_MIN,
            PRIMARY_WIDTH_MAX
        )

    return profile


def _make_lane(rng, nominal_width, primary, shift=0.0):
    """
    Produce a finite, nonperiodic sequence of disconnected inclusions.

    The first and last inclusions intersect the specimen boundary.
    Every internal gap contains a complete empty reinforcement row.
    """
    n = PRIMARY_SEGMENTS if primary else SECONDARY_SEGMENTS
    lengths = _segment_lengths(rng, n, primary, shift)

    segments = []
    y = 0

    for length in lengths:
        length = int(length)

        if primary:
            widths = _primary_profile(rng, length, nominal_width)

            # Maintain nearly coaxial load-transfer faces.
            offset = int(rng.choice(
                [-1, 0, 1],
                p=[0.20, 0.60, 0.20]
            ))
        else:
            widths = np.full(length, nominal_width, dtype=int)

            # Independent small-particle placement variability.
            offset = int(rng.integers(-2, 3))

        segments.append((y, widths, offset))
        y += length + VERTICAL_GAP

    return segments


def _match_count(rng, primary_lanes, secondary_lanes):
    """
    Enforce exact composition through bounded side-width adjustments.

    Adjustments preserve each inclusion's vertical extent, connected
    interior, and separation from all other inclusions.
    """
    primary_parts = [
        widths
        for lane in primary_lanes
        for _, widths, _ in lane
    ]

    secondary_parts = [
        widths
        for lane in secondary_lanes
        for _, widths, _ in lane
    ]

    total = sum(int(w.sum()) for w in primary_parts)
    total += sum(int(w.sum()) for w in secondary_parts)
    delta = TARGET_COUNT - total

    # The attainable primary-width interval brackets the target.
    # Six passes suffice to traverse the entire permitted width range.
    for _ in range(PRIMARY_WIDTH_MAX - PRIMARY_WIDTH_MIN):
        if delta == 0:
            break

        for k in rng.permutation(len(primary_parts)):
            if delta == 0:
                break

            widths = primary_parts[k]
            step = 1 if delta > 0 else -1

            if step > 0:
                eligible = np.flatnonzero(widths < PRIMARY_WIDTH_MAX)
            else:
                eligible = np.flatnonzero(widths > PRIMARY_WIDTH_MIN)

            count = min(abs(delta), eligible.size)
            if count == 0:
                continue

            # Prefer contiguous side adjustments over pixel noise.
            if count < eligible.size:
                start = int(rng.integers(
                    0, eligible.size - count + 1
                ))
                selected = eligible[start:start + count]
            else:
                selected = eligible

            widths[selected] += step
            delta -= step * count

    if delta != 0:
        raise RuntimeError("Exact composition allocation failed")


def _lane_span(lane):
    """Reserve sufficient horizontal space for every inclusion."""
    max_width = max(int(widths.max()) for _, widths, _ in lane)
    max_offset = max(abs(offset) for _, _, offset in lane)
    return max_width + 2 * max_offset + 2


def _lane_positions(rng, lanes):
    """
    Randomize nonoverlapping lane positions across the finite domain.

    Positive inter-lane clearances prevent diagonal contacts and
    retain uninterrupted vertical matrix corridors.
    """
    spans = np.array([_lane_span(lane) for lane in lanes], dtype=int)
    n = len(lanes)

    free = SIZE - int(spans.sum()) - MIN_LANE_GAP * (n + 1)

    probabilities = rng.dirichlet(np.full(n + 1, 1.7))
    gaps = MIN_LANE_GAP + rng.multinomial(free, probabilities)

    centers = []
    x = int(gaps[0])

    for i, span in enumerate(spans):
        centers.append(x + int(span) // 2)
        x += int(span) + int(gaps[i + 1])

    return centers


def _rasterize(lanes, centers):
    """
    Rasterize contiguous horizontal row intervals.

    Each individual inclusion is four-connected. Empty rows between
    successive inclusions prohibit both four- and eight-connected
    reinforcement paths along a lane.
    """
    reinforcement = np.zeros((SIZE, SIZE), dtype=bool)
    columns = np.arange(SIZE)[None, :]

    for lane, center in zip(lanes, centers):
        for y, widths, offset in lane:
            left = center + offset - widths // 2
            right = left + widths

            region = (
                (columns >= left[:, None]) &
                (columns < right[:, None])
            )

            reinforcement[y:y + len(widths), :] |= region

    return reinforcement


def generate_microstructure(seed, parameters):
    """
    Generate an anisotropic dispersed-inclusion microstructure.

    Geometry-only design rationale:
    - Concentrate reinforcement area in vertically elongated regions.
    - Align successive large inclusions to increase axial overlap.
    - Minimize intervening compliant matrix thickness without joining
      reinforcement regions.
    - Stagger axial interruptions between independently positioned lanes.
    - Retain smaller inclusions to satisfy complete-region morphology
      constraints without introducing isolated-pixel noise.

    This construction targets vertical load-transfer efficiency.
    No elastic solver or mechanical-result calibration is used.
    """
    rng = np.random.default_rng(seed)

    nominal_widths = _primary_widths(rng)

    # Distinct stochastic gap offsets avoid a common interruption plane.
    shifts = rng.permutation(
        np.array([-15.0, -5.0, 5.0, 15.0])
    )
    shifts += rng.uniform(-2.0, 2.0, size=N_PRIMARY)

    primary_lanes = [
        _make_lane(
            rng,
            int(nominal_widths[i]),
            primary=True,
            shift=float(shifts[i])
        )
        for i in range(N_PRIMARY)
    ]

    secondary_lanes = [
        _make_lane(
            rng,
            SECONDARY_WIDTH,
            primary=False
        )
        for _ in range(N_SECONDARY)
    ]

    _match_count(rng, primary_lanes, secondary_lanes)

    # Randomly intersperse the two size families across the specimen.
    lanes = primary_lanes + secondary_lanes
    lanes = [lanes[i] for i in rng.permutation(len(lanes))]

    centers = _lane_positions(rng, lanes)
    reinforcement = _rasterize(lanes, centers)

    # Construction produces:
    #   58 disconnected reinforcement regions;
    #   46 complete regions and 12 boundary-censored regions;
    #   exact reinforcement area of 20,731 pixels;
    #   separated reinforcement regions under eight-connectivity.
    #
    # Inter-lane matrix corridors span vertically. Full-width matrix
    # gaps within every lane connect these corridors horizontally,
    # retaining a single continuous four-connected matrix network.

    result = np.full((SIZE, SIZE), 1, dtype=np.uint8)
    result[reinforcement] = 5
    return result
