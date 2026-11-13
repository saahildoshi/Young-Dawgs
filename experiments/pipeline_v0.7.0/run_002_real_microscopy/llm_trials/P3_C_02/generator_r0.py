import numpy as np
from scipy import ndimage as ndi
from scipy.special import gammaincinv

SIZE = 256
FRACTION = 0.3163299560546875
COUNT = 57
DIAMETER_MEAN = 15.706688295952011
DIAMETER_STD = 8.893419110493891
ASPECT_MEAN = 1.9159686370225526


def _particle(rng, diameter, aspect, angle):
    r = diameter / 2
    a, b = r * np.sqrt(aspect), r / np.sqrt(aspect)
    h = int(np.ceil(1.65 * a)) + 3
    y, x = np.mgrid[-h:h+1, -h:h+1].astype(float)
    c, s = np.cos(angle), np.sin(angle)
    u, v = (c*x + s*y)/a, (-s*x + c*y)/b
    theta = np.arctan2(v, u)
    outline = np.ones_like(theta)
    for k, amplitude in ((3, .19), (4, .12), (5, .09), (7, .05)):
        outline += rng.uniform(.55, 1.35)*amplitude * np.cos(
            k*theta + rng.uniform(0, 2*np.pi))
    noise = ndi.gaussian_filter(rng.normal(size=x.shape), 1.0)
    score = np.hypot(u, v)/outline + .065*noise
    area = max(5, int(round(np.pi*r*r)))
    mask = np.zeros(score.size, dtype=bool)
    mask[np.argpartition(score.ravel(), area-1)[:area]] = True
    mask = ndi.binary_fill_holes(mask.reshape(score.shape))
    labels, _ = ndi.label(mask)
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    mask = labels == counts.argmax()
    yy, xx = np.nonzero(mask)
    return np.pad(mask[yy.min():yy.max()+1, xx.min():xx.max()+1], 1)


def _place(out, blocked, mask, cy, cx, complete):
    h, w = mask.shape
    y, x = int(cy)-h//2, int(cx)-w//2
    if complete and (y < 0 or x < 0 or y+h > SIZE or x+w > SIZE):
        return 0
    y0, y1 = max(0, y), min(SIZE, y+h)
    x0, x1 = max(0, x), min(SIZE, x+w)
    if y0 >= y1 or x0 >= x1:
        return 0
    sy, sx = slice(y0-y, y1-y), slice(x0-x, x1-x)
    m = mask[sy, sx]
    if not m.any() or np.any(blocked[y0:y1, x0:x1] & m):
        return 0
    if not complete:
        touches = ((y0 == 0 and m[0].any()) or
                   (y1 == SIZE and m[-1].any()) or
                   (x0 == 0 and m[:, 0].any()) or
                   (x1 == SIZE and m[:, -1].any()))
        if not touches or ndi.label(m)[1] != 1:
            return 0
    out[y0:y1, x0:x1][m] = 5
    halo = ndi.binary_dilation(mask, structure=np.ones((3, 3), bool))
    blocked[y0:y1, x0:x1] |= halo[sy, sx]
    return int(m.sum())


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    out = np.ones((SIZE, SIZE), dtype=np.uint8)
    blocked = np.zeros(out.shape, dtype=bool)
    p = (np.arange(COUNT) + rng.uniform(.12, .88, COUNT))/COUNT
    d = gammaincinv(2.7, p)
    for _ in range(12):
        d = DIAMETER_MEAN + DIAMETER_STD*(d-d.mean())/d.std()
        d = np.clip(d, 3.5, 48.0)
    aspects = np.clip(rng.lognormal(np.log(ASPECT_MEAN)-.065, .36, COUNT),
                      1.08, 3.8)
    centers = rng.uniform(8, SIZE-8, (8, 2))
    directions = rng.uniform(0, np.pi, len(centers))
    groups = rng.integers(len(centers), size=COUNT)
    particles = [_particle(rng, di, ar, directions[g]+rng.normal(0, .65))
                 for di, ar, g in zip(d, aspects, groups)]
    remaining = round(FRACTION*SIZE**2) - sum(m.sum() for m in particles)
    for _ in range(600):
        if remaining <= 65:
            break
        di = min(rng.lognormal(np.log(23), .37),
                 1.2*np.sqrt(8*remaining/np.pi), 48)
        mask = _particle(rng, max(4, di), rng.uniform(1.2, 2.8),
                         rng.uniform(0, np.pi))
        side, along = rng.integers(4), rng.uniform(0, SIZE-1)
        depth = rng.uniform(-.32, .32)*di
        cy, cx = [(depth, along), (SIZE-1-depth, along),
                  (along, depth), (along, SIZE-1-depth)][side]
        remaining -= _place(out, blocked, mask, cy, cx, False)
    for i in np.argsort(d)[::-1]:
        for attempt in range(700):
            if attempt < 90 and rng.random() < .78:
                cy, cx = centers[groups[i]] + rng.normal(0, 22, 2)
            else:
                cy, cx = rng.uniform(0, SIZE, 2)
            if _place(out, blocked, particles[i], cy, cx, True):
                break
    return out
