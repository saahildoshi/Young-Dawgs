import numpy as np
from scipy import ndimage as ndi
from scipy.spatial import cKDTree


def _void_field(rng, x, y):
    field = np.full(x.shape, np.inf)
    rough = ndi.gaussian_filter(rng.normal(size=x.shape), 1.4)
    rough /= rough.std() + 1e-8
    for _ in range(rng.integers(3, 6)):
        cx, cy = rng.uniform(-5, 269, 2)
        a, b = rng.uniform(7, 15), rng.uniform(4, 10)
        theta = rng.uniform(0, 2 * np.pi)
        for j in range(rng.integers(2, 5)):
            dx, dy = rng.normal(0, 0.35 * a, 2) if j else (0, 0)
            scale = rng.uniform(0.45, 0.85) if j else 1.0
            u = (x - cx - dx) * np.cos(theta) + (y - cy - dy) * np.sin(theta)
            v = -(x - cx - dx) * np.sin(theta) + (y - cy - dy) * np.cos(theta)
            q = np.sqrt((u / (a * scale))**2 + (v / (b * scale))**2)
            field = np.minimum(field, q)
    field += 0.13 * rough
    fraction = np.clip(rng.normal(0.019577, 0.0025), 0.013, 0.027)
    return field <= np.quantile(field[4:260, 4:260], fraction)


def _pack(rng, allowed, density, separation, count):
    # Random sequential inhibition with spatially varying packing intensity.
    cells, points = {}, []
    d2 = separation**2
    proposals = rng.uniform(0, 264, size=(45000, 3))
    proposals[:, 2] /= 264
    for x, y, u in proposals.tolist():
        ix, iy = int(x), int(y)
        if not allowed[iy, ix] or u > density[iy, ix]:
            continue
        gx, gy = int(x / separation), int(y / separation)
        if any((x-px)**2 + (y-py)**2 < d2
               for a in range(gx-1, gx+2)
               for b in range(gy-1, gy+2)
               for px, py in cells.get((a, b), ())):
            continue
        cells.setdefault((gx, gy), []).append((x, y))
        points.append((x, y))
        if len(points) >= count:
            break
    return np.asarray(points)


def _region_error(mask):
    labels, _ = ndi.label(mask)
    areas = np.bincount(labels.ravel())
    border = np.unique(np.concatenate(
        (labels[0], labels[-1], labels[:, 0], labels[:, -1])))
    keep = np.ones(len(areas), dtype=bool)
    keep[border] = False
    keep[0] = False
    diameters = 2 * np.sqrt(areas[keep] / np.pi)
    if not diameters.size:
        return np.inf
    return ((diameters.size - 464) / 35)**2 + \
           ((diameters.mean() - 7.90493) / 0.45)**2 + \
           ((diameters.std() - 2.81210) / 0.45)**2


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[:264, :264]
    crop = np.s_[4:260, 4:260]
    void = _void_field(rng, x, y)
    allowed = ndi.distance_transform_edt(~void) > 2.2
    noise = ndi.gaussian_filter(rng.normal(size=x.shape), 10)
    noise /= noise.std() + 1e-8
    density = np.clip(0.72 + 0.24 * noise, 0.12, 1.0)
    coordinates = np.column_stack((x[crop].ravel(), y[crop].ravel()))
    fraction = np.clip(rng.normal(0.452698, 0.006), 0.435, 0.470)
    best, best_error = None, np.inf

    # Bounded sampling conditioned on connected annotation descriptors.
    for separation in (5.35, 5.55, 5.75, 5.95, 6.10, 6.25, 6.40):
        count = int(rng.integers(990, 1081))
        points = _pack(rng, allowed, density, separation, count)
        distances = cKDTree(points).query(coordinates)[0].reshape(256, 256)
        available = ~void[crop]
        # Equal-radius sections may merge into larger annotation regions.
        radius = np.quantile(distances[available], fraction / available.mean())
        fiber = (distances <= radius) & available
        error = _region_error(fiber) + ((radius - 3.15) / 0.65)**2
        if error < best_error:
            best, best_error = fiber, error

    result = best.astype(np.uint8)
    result[void[crop]] = 2
    return result
