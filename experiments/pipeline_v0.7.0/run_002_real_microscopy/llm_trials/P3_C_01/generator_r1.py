import numpy as np
from scipy import ndimage as ndi

N = 256
FRACTION = 0.3163299560546875
COUNT = 57

# Internal parameter corrections from the registered development summary.
D_MEAN = 15.76
D_STD = 9.20
ASPECT = 1.8765
AREA_BIAS = 12


def _largest(mask):
    labels, n = ndi.label(mask)
    if n <= 1:
        return mask
    counts = np.bincount(labels.ravel())
    counts[0] = 0
    return labels == counts.argmax()


def _particle(rng, diameter, angle):
    aspect = np.clip(rng.lognormal(np.log(ASPECT)-0.065, 0.36), 1.1, 4.0)
    area = max(8, int(round(np.pi * diameter**2 / 4)))
    a = diameter * np.sqrt(aspect) / 2
    b = diameter / (2 * np.sqrt(aspect))
    r = int(np.ceil(1.7 * a)) + 2
    y, x = np.mgrid[-r:r+1, -r:r+1]
    u = (x*np.cos(angle) + y*np.sin(angle)) / a
    v = (-x*np.sin(angle) + y*np.cos(angle)) / b
    theta = np.mod(np.arctan2(v, u), 2*np.pi)
    k = int(rng.integers(10, 19))
    phi = np.linspace(0, 2*np.pi, k, endpoint=False)
    radii = rng.uniform(0.72, 1.26, k)
    radii += 0.12*np.cos(3*phi + rng.uniform(0, 2*np.pi))
    if rng.random() < 0.45:
        j = rng.integers(k)
        radii[j] *= rng.uniform(0.48, 0.75)
        radii[(j+1) % k] *= rng.uniform(0.8, 0.95)
    profile = np.interp(theta, np.r_[phi, 2*np.pi], np.r_[radii, radii[0]])
    score = np.hypot(u, v) / profile
    mask = score <= np.partition(score.ravel(), area-1)[area-1]
    mask = _largest(mask)
    yy, xx = np.where(mask)
    return mask[yy.min():yy.max()+1, xx.min():xx.max()+1]


def _place(solid, blocked, p, y, x, border=False, limit=65536):
    h, w = p.shape
    y0, x0 = max(0, y), max(0, x)
    y1, x1 = min(N, y+h), min(N, x+w)
    if y1 <= y0 or x1 <= x0:
        return 0
    q = _largest(p[y0-y:y1-y, x0-x:x1-x])
    if not q.any() or q.sum() > limit or np.any(q & blocked[y0:y1, x0:x1]):
        return 0
    if border and not ((y0 == 0 and q[0].any()) or (y1 == N and q[-1].any())
                       or (x0 == 0 and q[:, 0].any()) or (x1 == N and q[:, -1].any())):
        return 0
    solid[y0:y1, x0:x1] |= q
    ndi.binary_dilation(solid, output=blocked)
    return int(q.sum())


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    solid = np.zeros((N, N), dtype=bool)
    blocked = solid.copy()
    sizes = rng.lognormal(0, 0.53, COUNT)
    sizes = np.clip(D_MEAN + D_STD*(sizes-sizes.mean())/sizes.std(), 3.5, 48)
    remaining = int(round(FRACTION*N*N + AREA_BIAS
                          - np.pi/4*np.sum(sizes**2)))

    # Boundary-clipped annotations with size-biased sampling.
    for _ in range(40):
        if remaining < 70:
            break
        d = np.clip(rng.lognormal(np.log(25), 0.32), 12, 43)
        d = min(d, np.sqrt(8*remaining/np.pi))
        p = _particle(rng, d, rng.uniform(0, np.pi))
        h, w = p.shape
        for _ in range(45):
            side = rng.integers(4)
            y, x = rng.integers(N)-h//2, rng.integers(N)-w//2
            if side < 2:
                y = -int(h*rng.uniform(0.23, 0.65))
                if side == 1:
                    y = N-h-y
            else:
                x = -int(w*rng.uniform(0.23, 0.65))
                if side == 3:
                    x = N-w-x
            added = _place(solid, blocked, p, y, x, True, remaining+50)
            if added:
                remaining -= added
                break

    # Heterogeneous dispersion of independent irregular annotations.
    field = ndi.gaussian_filter(rng.normal(size=(N, N)), 15)
    field = np.clip(0.55 + 0.22*(field-field.mean())/field.std(), 0.12, 1)
    for d in sorted(sizes, reverse=True):
        p = _particle(rng, d, rng.uniform(0, np.pi))
        h, w = p.shape
        for attempt in range(400):
            y, x = rng.integers(1, N-h), rng.integers(1, N-w)
            if attempt < 180 and rng.random() > field[y+h//2, x+w//2]:
                continue
            if _place(solid, blocked, p, y, x):
                break

    # Native material-region IDs: 1 = matrix, 5 = provisional carbide.
    return np.where(solid, 5, 1).astype(np.uint8)
