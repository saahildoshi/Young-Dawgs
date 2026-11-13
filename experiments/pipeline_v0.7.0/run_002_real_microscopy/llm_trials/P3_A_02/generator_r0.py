import numpy as np
from scipy import ndimage as ndi
from skimage.draw import polygon


def _paint_particle(mask, rng, x, y, a, b, theta):
    """Rasterize an irregular, angular carbide region."""
    n = int(rng.integers(7, 15))
    angles = np.arange(n) * (2 * np.pi / n)
    angles += rng.uniform(-0.22, 0.22, n)
    radial = rng.uniform(0.72, 1.25, n)

    if rng.random() < 0.45:
        radial[rng.integers(n)] *= rng.uniform(0.48, 0.75)

    u = a * radial * np.cos(angles)
    v = b * radial * np.sin(angles)
    c, s = np.cos(theta), np.sin(theta)
    xx = x + c * u - s * v
    yy = y + s * u + c * v
    rr, cc = polygon(yy, xx, shape=mask.shape)
    mask[rr, cc] = True


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    size = 256
    pad = 24
    extent = size + 2 * pad
    carbide = np.zeros((extent, extent), dtype=bool)
    interior = np.s_[pad:pad + size, pad:pad + size]

    # Visually inferred image-scale statistics, not physical calibration.
    target_fraction = rng.uniform(0.255, 0.315)
    n_clusters = int(rng.integers(12, 19))
    parents = rng.uniform(pad - 10, pad + size + 10,
                          (n_clusters, 2))
    directions = rng.uniform(0, np.pi, n_clusters)
    cluster_long = rng.uniform(13, 29, n_clusters)
    cluster_short = rng.uniform(6, 17, n_clusters)
    weights = rng.uniform(0.6, 1.5, n_clusters)
    weights /= weights.sum()

    centers = []
    radii = []

    for _ in range(2500):
        # Locally clustered regions interspersed with isolated particles.
        if rng.random() < 0.73:
            k = rng.choice(n_clusters, p=weights)
            phi = directions[k]
            u = rng.normal(0, cluster_long[k])
            v = rng.normal(0, cluster_short[k])
            x = parents[k, 0] + u * np.cos(phi) - v * np.sin(phi)
            y = parents[k, 1] + u * np.sin(phi) + v * np.cos(phi)
            theta = phi + rng.normal(0, 0.85)
        else:
            x, y = rng.uniform(pad - 14, pad + size + 14, 2)
            theta = rng.uniform(0, np.pi)

        if not (pad - 16 <= x < pad + size + 16 and
                pad - 16 <= y < pad + size + 16):
            continue

        r = np.clip(rng.lognormal(np.log(7.4), 0.46), 2.4, 16.5)
        aspect = np.clip(rng.lognormal(np.log(1.65), 0.42), 1, 3.8)
        a, b = r * np.sqrt(aspect), r / np.sqrt(aspect)

        if centers:
            delta = np.asarray(centers) - (x, y)
            distance = np.sqrt(np.sum(delta**2, axis=1))
            separation = rng.uniform(0.68, 1.04)
            if np.any(distance < separation * (r + np.asarray(radii))):
                continue

        _paint_particle(carbide, rng, x, y, a, b, theta)
        centers.append((x, y))
        radii.append(r)

        # Some regions have attached angular lobes or branched outlines.
        if rng.random() < 0.26 and r > 5:
            beta = theta + rng.uniform(-np.pi, np.pi)
            offset = rng.uniform(0.45, 0.85) * a
            lx = x + offset * np.cos(beta)
            ly = y + offset * np.sin(beta)
            q = rng.uniform(0.40, 0.72) * r
            _paint_particle(carbide, rng, lx, ly, q * 1.3, q,
                            beta + rng.uniform(-0.8, 0.8))

        if carbide[interior].mean() >= target_fraction:
            break

    # Correlated boundary roughness without reproducing SEM intensity noise.
    signed = ndi.distance_transform_edt(carbide)
    signed -= ndi.distance_transform_edt(~carbide)
    signed -= 0.5 * np.sign(signed)
    roughness = ndi.gaussian_filter(rng.standard_normal(carbide.shape), 0.9)
    roughness /= max(roughness.std(), 1e-8)
    carbide = (signed + 0.65 * roughness > 0)[interior]

    return np.where(carbide, 5, 1).astype(np.uint8)
