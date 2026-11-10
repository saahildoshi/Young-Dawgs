import numpy as np
from scipy.ndimage import binary_dilation


def generate_microstructure(seed, parameters):
    rng = np.random.default_rng(seed)
    size = 256
    image = np.zeros((size, size), dtype=np.uint8)
    forbidden = np.zeros((size, size), dtype=bool)

    target_count = int(rng.integers(42, 50))
    placed = 0
    attempts = 0
    max_attempts = 1500

    while placed < target_count and attempts < max_attempts:
        attempts += 1

        # Random particle dimensions, orientation, and position.
        major = float(np.clip(rng.normal(8.0, 2.0), 4.5, 12.5))
        minor = major * rng.uniform(0.62, 0.98)
        angle = rng.uniform(0.0, np.pi)

        cx = rng.uniform(15.0, size - 15.0)
        cy = rng.uniform(15.0, size - 15.0)

        # Local bounding box with clearance for irregularity.
        radius = int(np.ceil(1.15 * major + 3))
        x0 = max(0, int(cx) - radius)
        x1 = min(size, int(cx) + radius + 2)
        y0 = max(0, int(cy) - radius)
        y1 = min(size, int(cy) + radius + 2)

        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx = xx - cx
        dy = yy - cy

        c, s = np.cos(angle), np.sin(angle)
        u = (c * dx + s * dy) / major
        v = (-s * dx + c * dy) / minor

        # Small smooth contour variations produce natural particles.
        theta = np.arctan2(v, u)
        phase1, phase2 = rng.uniform(0, 2 * np.pi, 2)
        amp1 = rng.uniform(0.01, 0.055)
        amp2 = rng.uniform(0.005, 0.025)

        boundary = (
            1.0
            + amp1 * np.sin(3 * theta + phase1)
            + amp2 * np.sin(5 * theta + phase2)
        )
        particle = (u * u + v * v) <= boundary * boundary

        # Keep reinforcement particles separate and matrix continuous.
        region = forbidden[y0:y1, x0:x1]
        if np.any(particle & region):
            continue

        image[y0:y1, x0:x1] |= particle.astype(np.uint8)

        # Exclude neighboring pixels to preserve matrix channels.
        exclusion = binary_dilation(particle, iterations=2)
        region |= exclusion
        placed += 1

    return image
