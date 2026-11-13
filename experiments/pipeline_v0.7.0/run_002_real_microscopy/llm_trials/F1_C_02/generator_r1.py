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
    for scale in (13.0, 10.0, 6.0, 3.8):
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
    radii = np.clip(rng.normal(radius_mean, 0.43, proposals.size), 2.35, 4.75)
    offsets = rng.uniform(-0.5, 0.5, (proposals.size, 2))
    area, misses = 0, 0
    want_contact = False

    for k, index in enumerate(proposals):
        cy, cx = divmod(int(index), N - 12)
        cy, cx = cy + 6, cx + 6
        sl = np.s_[cy - 6:cy + 7, cx - 6:cx + 7]
        ox, oy = offsets[k]
        dist2 = (dx - ox)**2 + (dy - oy)**2
        disk = dist2 <= radii[k]**2
        local = fiber[sl]
        disk_area = np.count_nonzero(disk)
        misses += 1

        if np.count_nonzero(disk & local) > 0.12 * disk_area:
            continue
        if np.count_nonzero(disk & void[sl]) > 0.12 * disk_area:
            continue
        disk &= ~void[sl]
        contact = (
            np.any(disk & local)
            or np.any(disk[1:, :] & local[:-1, :])
            or np.any(disk[:-1, :] & local[1:, :])
            or np.any(disk[:, 1:] & local[:, :-1])
            or np.any(disk[:, :-1] & local[:, 1:])
        )
        if contact != want_contact and misses < 90:
            continue

        fresh = disk & ~local & inner[sl]
        gain = np.count_nonzero(fresh)
        remaining = TARGET_AREA - area

        # Adjust only the terminal section to avoid area overshoot.
        if gain > remaining:
            indices = np.flatnonzero(fresh)
            order = np.argsort(dist2.ravel()[indices], kind="stable")
            disk.ravel()[indices[order[remaining:]]] = False
            gain = remaining

        local |= disk
        area += gain
        misses = 0
        want_contact = rng.random() < contact_rate
        if area >= TARGET_AREA:
            break

    return fiber[PAD:PAD + SIZE, PAD:PAD + SIZE].copy()


def _measure(fiber):
    labels, _ = ndi.label(fiber)
    areas = np.bincount(labels.ravel())
    border = np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1]))
    areas[np.unique(border)] = 0
    areas[0] = 0
    d = 2 * np.sqrt(areas[areas > 0] / np.pi)
    if not d.size:
        return 0, 0.0, 0.0, int(fiber.sum())
    return d.size, d.mean(), d.std(), int(fiber.sum())


def _score(metrics):
    count, mean, std, area = metrics
    return (
        ((count - TARGET_COUNT) / 12.0)**2
        + ((mean - TARGET_MEAN) / 0.18)**2
        + ((std - TARGET_STD) / 0.20)**2
        + ((area - TARGET_AREA) / 100.0)**2
    )


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    void = _make_voids(rng)
    best, best_score = None, np.inf
    best_metrics, best_params = None, None

    # Development feedback: increase region count and reduce
    # equivalent-diameter mean and dispersion through weaker merging.
    candidates = (
        (3.40, 0.20), (3.45, 0.20), (3.50, 0.20),
        (3.40, 0.26), (3.45, 0.26), (3.50, 0.26),
        (3.35, 0.29), (3.55, 0.16), (3.45, 0.16),
    )

    for k in range(12):
        if k < len(candidates):
            radius, contact = candidates[k]
        else:
            count, mean, std, _ = best_metrics
            r, c = best_params
            radius = np.clip(
                r + 0.002 * (count - TARGET_COUNT)
                + 0.15 * (TARGET_MEAN - mean)
                + rng.normal(0, 0.035), 3.25, 3.70
            )
            contact = np.clip(
                c + 0.10 * (TARGET_STD - std)
                + rng.normal(0, 0.025), 0.10, 0.36
            )

        fiber = _pack_fibers(rng, void, radius, contact)
        metrics = _measure(fiber)
        score = _score(metrics)
        if best is None or score < best_score:
            best, best_score = fiber, score
            best_metrics = metrics
            best_params = (radius, contact)
        if best_score < 0.12:
            break

    result = best.astype(np.uint8)
    result[void[PAD:PAD + SIZE, PAD:PAD + SIZE]] = 2
    return result
