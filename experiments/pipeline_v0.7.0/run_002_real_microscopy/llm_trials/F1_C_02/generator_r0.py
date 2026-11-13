import numpy as np
from scipy import ndimage as ndi

SIZE = 256
PAD = 12
N = 280
TARGET_AREA = 29668
TARGET_VOID = 1283
TARGET_COUNT = 464
TARGET_MEAN = 7.9049316424275915
TARGET_STD = 2.8121048146429577


def _make_voids(rng):
    y, x = np.ogrid[:N, :N]
    field = np.full((N, N), -1e6)
    scales = np.array([13.0, 10.0, 6.0, 3.8])
    for scale in scales:
        cx, cy = rng.uniform(8, N - 8, 2)
        scale *= rng.uniform(0.8, 1.2)
        for _ in range(rng.integers(3, 6)):
            dx, dy = rng.normal(0, scale * 0.45, 2)
            a = scale * rng.uniform(0.65, 1.15)
            b = a * rng.uniform(0.45, 0.95)
            angle = rng.uniform(0, 2 * np.pi)
            xx, yy = x - cx - dx, y - cy - dy
            u = xx * np.cos(angle) + yy * np.sin(angle)
            v = -xx * np.sin(angle) + yy * np.cos(angle)
            field = np.maximum(field, 1 - (u / a)**2 - (v / b)**2)
    noise = ndi.gaussian_filter(rng.normal(size=(N, N)), 1.25)
    field += 0.24 * noise / (noise.std() + 1e-12)
    core = field[PAD:PAD + SIZE, PAD:PAD + SIZE]
    threshold = np.partition(core.ravel(), -TARGET_VOID)[-TARGET_VOID]
    return field >= threshold


def _pack_fibers(rng, void, radius_mean, contact_rate):
    fiber = np.zeros((N, N), dtype=bool)
    inner = np.zeros_like(fiber)
    inner[PAD:PAD + SIZE, PAD:PAD + SIZE] = True
    dy, dx = np.mgrid[-6:7, -6:7]

    density = ndi.gaussian_filter(rng.normal(size=(N, N)), 12)
    density = np.exp(0.33 * density / (density.std() + 1e-12))
    weights = density[6:-6, 6:-6].ravel()
    proposals = rng.choice(weights.size, 22000, p=weights / weights.sum())
    radii = np.clip(rng.normal(radius_mean, 0.48, proposals.size), 2.35, 4.75)
    offsets = rng.uniform(-0.5, 0.5, (proposals.size, 2))

    area, misses = 0, 0
    want_contact = False
    for k, index in enumerate(proposals):
        cy, cx = divmod(int(index), N - 12)
        cy, cx = cy + 6, cx + 6
        sl = np.s_[cy - 6:cy + 7, cx - 6:cx + 7]
        ox, oy = offsets[k]
        disk = (dx - ox)**2 + (dy - oy)**2 <= radii[k]**2
        local = fiber[sl]
        misses += 1

        if np.count_nonzero(disk & local) > 0.13 * disk.sum():
            continue
        if np.count_nonzero(disk & void[sl]) > 0.12 * disk.sum():
            continue
        disk &= ~void[sl]
        touching = ndi.binary_dilation(disk)
        contact = np.any(touching & local)
        if contact != want_contact and misses < 65:
            continue

        fresh = disk & ~local
        area += np.count_nonzero(fresh & inner[sl])
        local |= disk
        misses = 0
        want_contact = rng.random() < contact_rate
        if area >= TARGET_AREA:
            break

    return fiber[PAD:PAD + SIZE, PAD:PAD + SIZE].copy()


def _score(fiber):
    labels, _ = ndi.label(fiber)
    areas = np.bincount(labels.ravel())
    border = np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
    areas[np.unique(border)] = 0
    areas[0] = 0
    diameters = 2 * np.sqrt(areas[areas > 0] / np.pi)
    if not diameters.size:
        return np.inf
    return (
        ((diameters.size - TARGET_COUNT) / 22)**2
        + ((diameters.mean() - TARGET_MEAN) / 0.35)**2
        + ((diameters.std() - TARGET_STD) / 0.40)**2
        + ((fiber.sum() - TARGET_AREA) / 250)**2
    )


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    void = _make_voids(rng)
    best, best_score = None, np.inf
    for radius, contact in ((3.50, 0.25), (3.50, 0.34), (3.65, 0.25),
                            (3.65, 0.34), (3.40, 0.37), (3.55, 0.30)):
        fiber = _pack_fibers(rng, void, radius, contact)
        score = _score(fiber)
        if best is None or score < best_score:
            best, best_score = fiber, score
    result = best.astype(np.uint8)
    result[void[PAD:PAD + SIZE, PAD:PAD + SIZE]] = 2
    return result
