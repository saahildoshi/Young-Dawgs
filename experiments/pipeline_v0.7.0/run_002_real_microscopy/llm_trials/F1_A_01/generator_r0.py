import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt

def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    n, pad = 276, 10
    yy, xx = np.mgrid[:n, :n]

    def smooth_noise(sigma):
        z = gaussian_filter(rng.standard_normal((n, n)), sigma,
                            mode="reflect")
        return (z - z.mean()) / max(z.std(), 1e-8)

    # Spatially varying packing density and matrix-rich pockets.
    density = 0.85 * smooth_noise(13.0) + 0.35 * smooth_noise(4.5)
    roughness = 0.65 * smooth_noise(1.0) + 0.35 * smooth_noise(2.5)
    roughness = np.tanh(roughness)

    # Irregular, occasionally clustered voids with lobed boundaries.
    void = np.zeros((n, n), dtype=bool)
    parents = rng.uniform(pad, n - pad, (rng.integers(3, 5), 2))

    def ellipse_field(cx, cy, a, b, angle):
        dx, dy = xx - cx, yy - cy
        c, s = np.cos(angle), np.sin(angle)
        return ((c * dx + s * dy) / a)**2 + ((-s * dx + c * dy) / b)**2

    def void_patch(cx, cy, radius, lobes):
        angle = rng.uniform(0, np.pi)
        field = ellipse_field(cx, cy, radius,
                              radius * rng.uniform(0.60, 1.05), angle)
        for _ in range(lobes):
            theta = rng.uniform(0, 2 * np.pi)
            offset = radius * rng.uniform(0.45, 1.05)
            r = radius * rng.uniform(0.25, 0.65)
            q = ellipse_field(cx + offset * np.cos(theta),
                              cy + offset * np.sin(theta),
                              r, r * rng.uniform(0.45, 1.1),
                              rng.uniform(0, np.pi))
            field = np.minimum(field, q)
        return field < (1.0 + 0.38 * roughness)

    for cx, cy in parents:
        radius = rng.uniform(6.5, 11.5)
        void |= void_patch(cx, cy, radius, rng.integers(3, 6))

    for _ in range(rng.integers(6, 12)):
        if rng.random() < 0.65:
            cx, cy = parents[rng.integers(len(parents))]
            cx, cy = np.array([cx, cy]) + rng.normal(0, 16, 2)
        else:
            cx, cy = rng.uniform(0, n, 2)
        void |= void_patch(cx, cy, rng.uniform(1.5, 4.5),
                           rng.integers(1, 4))

    clearance = distance_transform_edt(~void)

    # Inhomogeneous hard-core packing of transverse fiber sections.
    # Distances and radii are inferred image-space scales, not physical units.
    spacing = 5.15 - 0.65 * np.tanh(density)
    acceptance = 0.12 + 0.88 / (1.0 + np.exp(-1.7 * density))
    cell = 7.0
    grid = {}
    centers = []
    target = int(rng.integers(1580, 1701))
    proposals = rng.uniform(0, n, (65000, 2))
    probabilities = rng.random(len(proposals))

    for (x, y), p in zip(proposals, probabilities):
        ix, iy = int(x), int(y)
        if p > acceptance[iy, ix] or clearance[iy, ix] < 2.8:
            continue
        d = spacing[iy, ix]
        gx, gy = int(x / cell), int(y / cell)
        valid = True
        for a in range(gx - 1, gx + 2):
            for b in range(gy - 1, gy + 2):
                for px, py, pd in grid.get((a, b), ()):
                    if (x - px)**2 + (y - py)**2 < ((d + pd) / 2)**2:
                        valid = False
                        break
                if not valid:
                    break
            if not valid:
                break
        if valid:
            grid.setdefault((gx, gy), []).append((x, y, d))
            centers.append((x, y))
            if len(centers) >= target:
                break

    # Nearly uniform circular annotations, with occasional touching fibers.
    result = np.zeros((n, n), dtype=np.uint8)
    for x, y in centers:
        r = np.clip(rng.normal(2.45, 0.15), 2.10, 2.85)
        x0, x1 = max(0, int(x - 3)), min(n, int(x + 4))
        y0, y1 = max(0, int(y - 3)), min(n, int(y + 4))
        disk = (xx[y0:y1, x0:x1] - x)**2 + (yy[y0:y1, x0:x1] - y)**2 <= r*r
        result[y0:y1, x0:x1][disk] = 1

    result[void] = 2
    return result[pad:pad + 256, pad:pad + 256].copy()
