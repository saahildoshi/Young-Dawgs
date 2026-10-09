"""Execution-grid scaling, never a new morphology control."""

from numbers import Integral
import numpy as np

BASE_RESOLUTION = 256
BASE_RADII = (0, 1, 2, 4, 8, 16, 32, 64)


def validate_resolution(resolution):
    if isinstance(resolution, bool) or not isinstance(resolution, Integral):
        raise ValueError("resolution must be an integer, not bool or a fractional value")
    if resolution < BASE_RESOLUTION or resolution > 4096:
        raise ValueError("Supported square resolution range is 256..4096; validated levels are 256, 512, 1024.")
    return int(resolution)


def resolution_scale(resolution):
    return validate_resolution(resolution) / BASE_RESOLUTION


def length_pixels(length_at_256, resolution):
    return float(length_at_256) * resolution_scale(resolution)


def area_pixels(area_at_256, resolution):
    return float(area_at_256) * resolution_scale(resolution) ** 2


def normalized_radii(resolution, base_radii=BASE_RADII):
    """Requested rho plus nearest native radii (half-up, not banker rounding).

    Curves can instead be interpolated from all native integer radii onto exact
    requested rho. Rounding error is reported, never silently treated as zero.
    """
    n = validate_resolution(resolution)
    rho = np.asarray(base_radii, dtype=float) / BASE_RESOLUTION
    if np.any(~np.isfinite(rho)) or np.any(rho < 0) or np.any(rho >= .5):
        raise ValueError("Radii must be finite, nonnegative, and below half the domain.")
    pixels = np.floor(rho * n + .5).astype(int)
    return {"rho": rho.tolist(), "pixel_radii": pixels.tolist(),
            "actual_rho": (pixels / n).tolist(), "rho_rounding_error": (pixels / n - rho).tolist()}


def normalized_dimensions(metrics, resolution):
    n = validate_resolution(resolution)
    return {"normalized_" + k: None if metrics[k] is None else metrics[k] / n for k in
            ("mean_strut_thickness", "p10_strut_thickness", "median_pore_diameter")}


def block_reduce(binary, target=BASE_RESOLUTION):
    """Secondary correspondence ONLY: block area fractions then majority >=0.5.

    Generation never calls this function. Requires exact integer block sizes;
    arbitrary N remains generatable but this diagnostic is unavailable for it.
    """
    n = binary.shape[0]
    if binary.shape != (n, n) or n % target:
        raise ValueError("Area/block comparison requires a square integer multiple of target.")
    factor = n // target
    fractions = binary.reshape(target, factor, target, factor).mean(axis=(1, 3))
    return (fractions >= .5).astype(np.uint8)
