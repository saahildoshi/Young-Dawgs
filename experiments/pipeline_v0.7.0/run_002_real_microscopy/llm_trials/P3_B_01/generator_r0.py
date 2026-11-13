import numpy as np
from scipy import ndimage as ndi

SIZE = 256
FRACTION = 0.3163299560546875
COUNT = 57
DIAMETER_MEAN = 15.706688295952011
DIAMETER_STD = 8.893419110493891


def _particle(rng, diameter):
    aspect = np.clip(rng.lognormal(np.log(1.78), 0.38), 1.05, 4.2)
    a = 0.5 * diameter * np.sqrt(aspect)
    b = 0.5 * diameter / np.sqrt(aspect)
    n = int(np.ceil(1.65 * a)) + 3
    y, x = np.mgrid[-n:n+1, -n:n+1]
    angle = rng.uniform(0, np.pi)
    u = (x * np.cos(angle) + y * np.sin(angle)) / a
    v = (-x * np.sin(angle) + y * np.cos(angle)) / b
    v -= rng.normal(0, 0.19) * (u*u - 0.3)
    theta = np.arctan2(v, u)
    contour = np.ones_like(theta)
    for k, amplitude in [(2, .07), (3, .16), (4, .12),
                         (5, .09), (7, .055), (11, .035)]:
        contour += rng.uniform(.35, 1.65) * amplitude * np.cos(
            k * theta + rng.uniform(0, 2*np.pi))
    roughness = ndi.gaussian_filter(rng.normal(size=x.shape), .85)
    score = np.hypot(u, v) / np.maximum(contour, .35) + .11 * roughness
    area = max(5, int(round(np.pi * diameter**2 / 4)))
    threshold = np.partition(score.ravel(), area - 1)[area - 1]
    mask = _largest(score <= threshold)
    mask = ndi.binary_fill_holes(mask)
    yy, xx = np.where(mask)
    return mask[yy.min():yy.max()+1, xx.min():xx.max()+1]


def _largest(mask):
    labels, count = ndi.label(mask)
    if count <= 1:
        return mask
    sizes = np.bincount(labels.ravel())[1:]
    return labels == (1 + np.argmax(sizes))


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    out = np.ones((SIZE, SIZE), dtype=np.uint8)
    blocked = np.zeros((SIZE+2, SIZE+2), dtype=bool)
    # Broad stochastic clustering leaves irregular matrix-rich corridors.
    field = ndi.gaussian_filter(rng.normal(size=out.shape), 18)
    field = (field - field.mean()) / (field.std() + 1e-12)
    weights = np.exp(np.clip(.85 * field, -2.5, 2.5))
    probabilities = weights.ravel() / weights.sum()
    edge_weights = np.concatenate((weights[0], weights[-1],
                                   weights[:, 0], weights[:, -1]))
    edge_weights /= edge_weights.sum()

    def place(mask, top, left, boundary=False, budget=SIZE*SIZE):
        h, w = mask.shape
        y0, y1 = max(0, top), min(SIZE, top+h)
        x0, x1 = max(0, left), min(SIZE, left+w)
        if y0 >= y1 or x0 >= x1:
            return 0
        if not boundary and (y0 == 0 or x0 == 0 or y1 == SIZE or x1 == SIZE):
            return 0
        m = _largest(mask[y0-top:y1-top, x0-left:x1-left])
        area = int(m.sum())
        if area < 5 or area > budget:
            return 0
        if boundary and not ((y0 == 0 and m[0].any()) or
                             (y1 == SIZE and m[-1].any()) or
                             (x0 == 0 and m[:, 0].any()) or
                             (x1 == SIZE and m[:, -1].any())):
            return 0
        if np.any(blocked[y0+1:y1+1, x0+1:x1+1] & m):
            return 0
        out[y0:y1, x0:x1][m] = 5
        blocked[y0:y1+2, x0:x1+2] |= ndi.binary_dilation(np.pad(m, 1))
        return area

    diameters = rng.lognormal(np.log(13.5), .53, COUNT)
    for _ in range(4):
        diameters = DIAMETER_MEAN + DIAMETER_STD * (
            diameters - diameters.mean()) / (diameters.std() + 1e-12)
        diameters = np.clip(diameters, 3.5, 48)
    filled = 0
    for d in sorted(diameters, reverse=True):
        mask = _particle(rng, d)
        h, w = mask.shape
        candidates = np.concatenate((rng.choice(SIZE*SIZE, 220, p=probabilities),
                                     rng.integers(SIZE*SIZE, size=300)))
        for pos in candidates:
            y, x = divmod(int(pos), SIZE)
            added = place(mask, y-h//2, x-w//2)
            if added:
                filled += added
                break
    target = int(round(FRACTION * SIZE * SIZE))
    # Boundary-clipped regions account for the remaining annotated area.
    for _ in range(180):
        remaining = target - filled
        if remaining < 15:
            break
        d = min(rng.lognormal(np.log(22), .39), 48,
                2*np.sqrt(remaining / (.72*np.pi)))
        mask = _particle(rng, max(4, d))
        h, w = mask.shape
        for pos in rng.choice(4*SIZE, 36, p=edge_weights):
            side, t = divmod(int(pos), SIZE)
            fy, fx = rng.uniform(.46, .85, size=2)
            if side == 0:
                top, left = -int(h*fy), t-w//2
            elif side == 1:
                top, left = SIZE-int(h*(1-fy)), t-w//2
            elif side == 2:
                top, left = t-h//2, -int(w*fx)
            else:
                top, left = t-h//2, SIZE-int(w*(1-fx))
            added = place(mask, top, left, True, remaining)
            if added:
                filled += added
                break
    return out
