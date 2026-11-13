import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

SIZE = 256
FIBER_FRACTION = 0.45269775390625
VOID_FRACTION = 0.0195770263671875
TARGET = (464, 7.9049316424275915, 2.8121048146429577)


def _voids(rng, x, y):
    field = np.full((SIZE, SIZE), np.inf)
    for _ in range(rng.integers(4, 9)):
        cx, cy = rng.uniform(-5, SIZE + 5, 2)
        a = np.clip(rng.lognormal(np.log(8.0), 0.55), 3, 22)
        b = a * rng.uniform(0.45, 0.95)
        t = rng.uniform(0, 2 * np.pi)
        u = ((x - cx) * np.cos(t) + (y - cy) * np.sin(t)) / a
        v = (-(x - cx) * np.sin(t) + (y - cy) * np.cos(t)) / b
        angle = np.arctan2(v, u)
        boundary = 1 + 0.20 * np.sin(3 * angle + rng.uniform(0, 6.28))
        boundary += 0.14 * np.sin(5 * angle + rng.uniform(0, 6.28))
        field = np.minimum(field, np.hypot(u, v) / boundary)
    noise = ndi.gaussian_filter(rng.normal(size=field.shape), 1.2)
    field += 0.08 * noise / (noise.std() + 1e-8)
    fraction = np.clip(rng.normal(VOID_FRACTION, 0.0010), 0.016, 0.024)
    k = int(round(fraction * SIZE**2))
    return field <= np.partition(field.ravel(), k - 1)[k - 1]


def _pack(rng, clearance, density, separation):
    points = rng.uniform(-5, SIZE + 5, (18000, 2))
    ij = np.clip(np.rint(points).astype(int), 0, SIZE - 1)
    local = density[ij[:, 1], ij[:, 0]]
    keep = ((clearance[ij[:, 1], ij[:, 0]] > 3.5) &
            (rng.random(len(points)) < 0.75 - 0.18 * local))
    points, local = points[keep], local[keep]
    spacing = separation * (1 + 0.12 * local)
    tree = cKDTree(points)
    blocked = np.zeros(len(points), dtype=bool)
    chosen = []
    for i, p in enumerate(points):
        if blocked[i]:
            continue
        chosen.append(i)
        neighbors = np.asarray(tree.query_ball_point(p, separation * 1.12))
        delta = points[neighbors] - p
        limit = 0.5 * (spacing[i] + spacing[neighbors])
        blocked[neighbors[np.sum(delta**2, axis=1) < limit**2]] = True
        if len(chosen) >= 1100:
            break
    return points[chosen]


def _fiber_field(points, scales):
    offsets = np.arange(-7, 8)
    oy, ox = np.meshgrid(offsets, offsets, indexing="ij")
    ix = np.floor(points[:, 0, None]).astype(int) + ox.ravel()
    iy = np.floor(points[:, 1, None]).astype(int) + oy.ravel()
    d2 = ((ix - points[:, 0, None])**2 +
          (iy - points[:, 1, None])**2) / scales[:, None]**2
    valid = (ix >= 0) & (ix < SIZE) & (iy >= 0) & (iy < SIZE)
    field = np.full(SIZE**2, np.inf)
    np.minimum.at(field, iy[valid] * SIZE + ix[valid], d2[valid])
    return field.reshape(SIZE, SIZE)


def _score(fiber):
    labels, n = ndi.label(fiber)
    areas = np.bincount(labels.ravel(), minlength=n + 1)
    border = np.unique(np.concatenate(
        (labels[0], labels[-1], labels[:, 0], labels[:, -1], [0])))
    areas[border] = 0
    diameters = 2 * np.sqrt(areas[areas > 0] / np.pi)
    if not len(diameters):
        return np.inf
    observed = np.array([len(diameters), diameters.mean(), diameters.std()])
    error = (observed - TARGET) / np.asarray(TARGET)
    # Increase emphasis on region count, which was biased upward.
    return np.sum(np.array([5.0, 2.0, 2.0]) * error**2)


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[:SIZE, :SIZE]
    void = _voids(rng, x, y)
    clearance = ndi.distance_transform_edt(~void)
    density = ndi.gaussian_filter(rng.normal(size=(SIZE, SIZE)), 10)
    density = np.tanh(density / (density.std() + 1e-8))
    fraction = np.clip(rng.normal(FIBER_FRACTION, 0.0025), 0.445, 0.460)
    k = int(round(SIZE**2 * fraction))
    best, best_score = None, np.inf

    # Finer sampling of packing density and center count permits
    # fewer complete regions without imposing artificial connections.
    for separation in (5.7, 5.9, 6.1, 6.3, 6.5, 6.7, 6.9):
        points = _pack(rng, clearance, density, separation)
        scales = np.clip(rng.normal(1, 0.055, len(points)), 0.85, 1.15)
        counts = np.unique(np.minimum(np.arange(760, 1021, 20), len(points)))
        field = np.full((SIZE, SIZE), np.inf)
        previous = 0
        for count in counts:
            field = np.minimum(field, _fiber_field(
                points[previous:count], scales[previous:count]))
            previous = count
            field[void] = np.inf
            threshold = np.partition(field.ravel(), k - 1)[k - 1]
            if not np.isfinite(threshold):
                continue
            fiber = field <= threshold
            score = _score(fiber)
            if score < best_score:
                best, best_score = fiber, score

    # Defensive fallback for an unusually sparse candidate packing.
    if best is None:
        points = rng.uniform(-4, SIZE + 4, (850, 2))
        distances = cKDTree(points).query(
            np.column_stack((x.ravel(), y.ravel())))[0]
        field = distances.reshape(SIZE, SIZE)
        field[void] = np.inf
        best = field <= np.partition(field.ravel(), k - 1)[k - 1]

    result = best.astype(np.uint8)
    result[void] = 2
    return result
