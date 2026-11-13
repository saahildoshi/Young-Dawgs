import numpy as np
from skimage.draw import polygon


def _particle(rng, cx, cy, angle, shape):
    # Broad size distribution: small fragments, irregular bodies,
    # and occasional elongated carbide regions.
    kind = rng.random()
    if kind < 0.22:
        a = rng.uniform(3.0, 6.5)
        b = a * rng.uniform(0.55, 1.0)
    elif kind < 0.84:
        a = np.clip(rng.lognormal(np.log(10.0), 0.30), 5.5, 18.0)
        b = a * rng.uniform(0.45, 0.95)
    else:
        a = rng.uniform(15.0, 25.0)
        b = a * rng.uniform(0.23, 0.58)

    # Irregular, partly angular outlines with occasional concavities.
    n = int(rng.integers(10, 23))
    t = (np.arange(n) + rng.uniform(-0.28, 0.28, n)) * 2 * np.pi / n
    radial = np.ones(n)
    for k in (2, 3, 5):
        radial += rng.uniform(0.05, 0.16) * np.cos(
            k * t + rng.uniform(0, 2 * np.pi)
        )
    radial += rng.normal(0, 0.10, n)

    if rng.random() < 0.45:
        j = int(rng.integers(n))
        radial[j] *= rng.uniform(0.35, 0.65)
        radial[(j + 1) % n] *= rng.uniform(0.65, 0.90)
    if rng.random() < 0.30:
        j = int(rng.integers(n))
        radial[j] *= rng.uniform(1.15, 1.45)

    radial = np.clip(radial, 0.30, 1.65)
    x = a * radial * np.cos(t)
    y = b * radial * np.sin(t)

    c, s = np.cos(angle), np.sin(angle)
    xx = cx + c * x - s * y
    yy = cy + s * x + c * y

    return polygon(yy, xx, shape=shape)


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    shape = (256, 256)
    carbide = np.zeros(shape, dtype=bool)

    # Spatially heterogeneous dispersion with carbide-rich clusters
    # separated by comparatively large matrix-rich regions.
    n_clusters = int(rng.integers(9, 15))
    centers = rng.uniform(-10, 266, size=(n_clusters, 2))
    spreads = rng.uniform(15, 33, size=(n_clusters, 2))
    directions = rng.uniform(0, np.pi, n_clusters)
    weights = rng.uniform(0.5, 1.5, n_clusters)
    weights /= weights.sum()

    # Approximate image-scale annotation fraction, not physical calibration.
    target = int(rng.uniform(0.27, 0.32) * np.prod(shape))
    occupied = 0

    for _ in range(1200):
        if occupied >= target:
            break

        if rng.random() < 0.72:
            j = rng.choice(n_clusters, p=weights)
            dx, dy = rng.normal(0, spreads[j])
            c, s = np.cos(directions[j]), np.sin(directions[j])
            cx = centers[j, 0] + c * dx - s * dy
            cy = centers[j, 1] + s * dx + c * dy
            angle = directions[j] + rng.normal(0, 0.65)
        else:
            cx, cy = rng.uniform(-8, 264, 2)
            angle = rng.uniform(0, np.pi)

        if not (-15 <= cx <= 271 and -15 <= cy <= 271):
            continue

        rr, cc = _particle(rng, cx, cy, angle, shape)
        if rr.size < 5:
            continue

        overlap = int(np.count_nonzero(carbide[rr, cc]))
        # Mostly distinct regions, with occasional coalesced shapes.
        limit = 0.35 if rng.random() < 0.24 else 0.10
        if overlap > limit * rr.size:
            continue

        carbide[rr, cc] = True
        occupied += rr.size - overlap

    if occupied == 0:
        rr, cc = _particle(rng, 128, 128, 0.0, shape)
        carbide[rr, cc] = True

    result = np.ones(shape, dtype=np.uint8)
    result[carbide] = 5
    return result
