import numpy as np

SIZE = 256
TARGET_COUNT = 20731
N_PRIMARY = 5


def _allocate(total, minimum, weights):
    """Allocate an integer total proportionally, respecting lower bounds."""
    weights = np.asarray(weights, dtype=float)
    n = weights.size
    lower = np.broadcast_to(minimum, (n,)).astype(int).copy()

    remainder = int(total) - int(lower.sum())
    ideal = remainder * weights / weights.sum()
    additions = np.floor(ideal).astype(int)

    missing = remainder - int(additions.sum())
    order = np.argsort(-(ideal - additions), kind="stable")
    additions[order[:missing]] += 1

    return lower + additions


def _primary_particle(rng, height, width, clipped_top, clipped_bottom):
    """
    Construct a vertically elongated, approximately prismatic inclusion.

    Small randomized corner bevels and shallow side irregularities
    preserve a broad axial load-transfer section.
    """
    particle = np.ones((height, width), dtype=bool)

    # Boundary-censored ends represent inclusions extending outside
    # the finite observation window.
    if not clipped_top:
        for side in range(2):
            bevel = int(rng.integers(0, 3))
            for row in range(bevel):
                cut = bevel - row
                if side == 0:
                    particle[row, :cut] = False
                else:
                    particle[row, width - cut:] = False

    if not clipped_bottom:
        for side in range(2):
            bevel = int(rng.integers(0, 3))
            for row in range(bevel):
                cut = bevel - row
                if side == 0:
                    particle[height - 1 - row, :cut] = False
                else:
                    particle[height - 1 - row, width - cut:] = False

    # Shallow, bounded side irregularities avoid splitting the inclusion
    # or substantially reducing its vertical cross-section.
    for side in range(2):
        if rng.random() < 0.75:
            length = int(rng.integers(2, 7))
            start = int(rng.integers(3, height - length - 2))
            col = 0 if side == 0 else width - 1
            particle[start:start + length, col] = False

    return particle


def _compact_particle(rng, area):
    """
    Generate a compact, four-connected rounded polygonal inclusion
    containing exactly the requested number of reinforcement pixels.
    """
    axis_ratio = rng.uniform(1.0, 1.65)
    exponent = rng.uniform(2.6, 5.0)

    cy = rng.uniform(-0.4, 0.4)
    cx = rng.uniform(-0.4, 0.4)

    coords = np.arange(-16, 17, dtype=float)
    y = (coords[:, None] - cy) / np.sqrt(axis_ratio)
    x = (coords[None, :] - cx) * np.sqrt(axis_ratio)

    distance = np.abs(y) ** exponent + np.abs(x) ** exponent

    order = np.argsort(distance.ravel(), kind="stable")
    particle = np.zeros(distance.size, dtype=bool)
    particle[order[:area]] = True
    particle = particle.reshape(distance.shape)

    rows, cols = np.where(particle)
    return particle[
        rows.min():rows.max() + 1,
        cols.min():cols.max() + 1
    ]


def _primary_layout(rng):
    """
    Randomly distribute five separated axial reinforcement corridors.

    Corridor widths, positions and separations vary between realizations.
    Reserved matrix passages accommodate independent smaller inclusions.
    """
    total_width = int(rng.integers(73, 76))

    widths = _allocate(
        total_width,
        12,
        rng.uniform(0.55, 1.55, N_PRIMARY)
    )

    gap_minimum = np.array([7, 21, 21, 21, 21, 7])

    gaps = _allocate(
        SIZE - int(widths.sum()),
        gap_minimum,
        rng.gamma(1.5, 1.0, N_PRIMARY + 1)
    )

    starts = np.empty(N_PRIMARY, dtype=int)

    position = int(gaps[0])
    for i in range(N_PRIMARY):
        starts[i] = position
        position += int(widths[i]) + int(gaps[i + 1])

    return starts, widths


def _populate_primary(rng, canvas, starts, widths):
    """
    Populate each corridor with distinct vertically aligned inclusions.

    Every consecutive pair has a positive matrix ligament. No corner
    contacts, connected reinforcement columns or periodic wrapping
    are introduced.

    Long inclusions and short axial matrix gaps are geometry-only
    design choices intended to improve vertical load transfer.
    """
    for x, width in zip(starts, widths):
        x = int(x)
        width = int(width)

        # Vary the number and lengths of inclusions independently.
        n = int(rng.choice([4, 5], p=[0.75, 0.25]))

        gaps = np.ones(n - 1, dtype=int)
        gaps += (rng.random(n - 1) < 0.12).astype(int)

        available = SIZE - int(gaps.sum())

        heights = _allocate(
            available,
            40 if n == 4 else 32,
            rng.uniform(0.55, 1.55, n)
        )

        y = 0
        previous_offset = int(rng.integers(-1, 2))

        for i, height in enumerate(heights):
            height = int(height)

            # Small lateral offsets preserve broad axial overlap while
            # avoiding identical straight-edged particle arrangements.
            if i > 0 and rng.random() < 0.45:
                previous_offset = int(rng.integers(-1, 2))

            xx = x + previous_offset

            particle = _primary_particle(
                rng,
                height,
                width,
                clipped_top=(i == 0),
                clipped_bottom=(i == n - 1)
            )

            canvas[y:y + height, xx:xx + width] |= particle

            y += height
            if i < n - 1:
                y += int(gaps[i])


def _secondary_vertical_gaps(rng, heights):
    """
    Allocate stochastic vertical spacings for smaller inclusions.

    Short intragroup ligaments are combined with longer intergroup
    matrix-rich intervals. All particles remain inside the domain.
    """
    n = len(heights)

    minimum = np.ones(n + 1, dtype=int)
    minimum[0] = 2
    minimum[-1] = 2

    minimum[1:-1] += rng.integers(0, 2, n - 1)

    free = SIZE - int(sum(heights)) - int(minimum.sum())

    # Two or three independently positioned groups in each corridor.
    n_breaks = int(rng.integers(1, 3))
    breaks = rng.choice(
        np.arange(2, n - 1),
        size=n_breaks,
        replace=False
    )

    active = np.concatenate((
        np.array([0, n], dtype=int),
        breaks
    ))

    weights = rng.gamma(1.4, 1.0, active.size)
    extras = _allocate(free, 0, weights)

    gaps = minimum.copy()
    gaps[active] += extras

    return gaps


def _populate_secondary(rng, canvas, starts, widths):
    """
    Fill the residual reinforcement budget with independent compact
    inclusions distributed in the matrix corridors.

    Exact integer area allocation avoids pixelwise composition repair
    and the creation of disconnected singleton noise.
    """
    n_corridors = len(starts) - 1

    counts = rng.integers(8, 11, n_corridors)
    n_particles = int(counts.sum())

    remaining = TARGET_COUNT - int(canvas.sum())

    areas = _allocate(
        remaining,
        30,
        rng.uniform(0.45, 1.65, n_particles)
    )

    particles = [
        _compact_particle(rng, int(area))
        for area in areas
    ]

    offset = 0

    for corridor, count in enumerate(counts):
        count = int(count)

        group = particles[offset:offset + count]
        offset += count

        heights = [p.shape[0] for p in group]
        max_width = max(p.shape[1] for p in group)

        # Account for the primary inclusions' possible one-pixel
        # lateral offsets, leaving uninterrupted matrix passages.
        left = int(starts[corridor] + widths[corridor] + 3)
        right = int(starts[corridor + 1] - 3)

        center_min = left + max_width // 2
        center_max = right - (max_width - max_width // 2)

        center = int(rng.integers(center_min, center_max + 1))

        gaps = _secondary_vertical_gaps(rng, heights)

        y = int(gaps[0])

        for j, particle in enumerate(group):
            height, width = particle.shape

            if j > 0 and gaps[j] > 5:
                center = int(
                    rng.integers(center_min, center_max + 1)
                )

            shift = int(rng.integers(-1, 2))
            x = center - width // 2 + shift

            x = max(left, min(right - width, x))

            canvas[y:y + height, x:x + width] |= particle

            y += height + int(gaps[j + 1])


def generate_microstructure(seed, parameters):
    """
    Generate a finite, nonperiodic two-phase P3 microstructure.

    Native labels:
        1: continuous matrix-like solid
        5: dispersed reinforcement-like solid

    The design concentrates reinforcement into separated axial
    inclusions with narrow, nonzero matrix ligaments. Smaller
    inclusions preserve the dispersed-region population and provide
    independent stochastic variation.

    No mechanical solver or mechanical-result information is used.
    """
    rng = np.random.default_rng(seed)

    canvas = np.zeros((SIZE, SIZE), dtype=bool)

    starts, widths = _primary_layout(rng)

    _populate_primary(rng, canvas, starts, widths)
    _populate_secondary(rng, canvas, starts, widths)

    result = np.ones((SIZE, SIZE), dtype=np.uint8)
    result[canvas] = 5

    return result
