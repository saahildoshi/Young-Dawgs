"""Exact integer scanline reconstruction independent of the input mask."""
import numpy as np
from .topology import analyze_raster_topology


def rasterize_boundary_loops(loops, resolution):
    crossings = [[] for _ in range(resolution)]
    for ring in loops:
        for (x0, y0), (x1, y1) in zip(ring["xy"][:-1], ring["xy"][1:]):
            if x0 == x1:
                for row in range(min(y0, y1), max(y0, y1)):
                    if not 0 <= row < resolution or not 0 <= x0 <= resolution:
                        raise ValueError("Boundary outside original domain.")
                    crossings[row].append(x0)
            elif y0 != y1:
                raise ValueError("Exact baseline edges must be axis-aligned.")
    result = np.zeros((resolution, resolution), dtype=np.uint8)
    for row, xs in enumerate(crossings):
        xs.sort()
        if len(xs) % 2:
            raise ValueError("Odd scanline crossing count: open or malformed boundary.")
        for left, right in zip(xs[::2], xs[1::2]):
            result[row, left:right] = 1
    return result


def compare_binary_masks(original, reconstructed):
    if original.shape != reconstructed.shape:
        raise ValueError("Comparison masks must share the original grid.")
    fp = int(np.count_nonzero((original == 0) & (reconstructed == 1)))
    fn = int(np.count_nonzero((original == 1) & (reconstructed == 0)))
    intersection = int(np.count_nonzero(original & reconstructed))
    union = int(np.count_nonzero(original | reconstructed))
    before, after = analyze_raster_topology(original), analyze_raster_topology(reconstructed)
    return {"input_solid_pixels": int(original.sum()), "reconstructed_solid_pixels": int(reconstructed.sum()),
            "false_positive_pixels": fp, "false_negative_pixels": fn, "xor_pixels": fp + fn,
            "iou": intersection / union if union else 1.0, "exact_equal": bool(np.array_equal(original, reconstructed)),
            "input_solid_area": int(original.sum()), "input_void_area": int(original.size - original.sum()),
            "reconstructed_solid_area": int(reconstructed.sum()),
            "reconstructed_void_area": int(reconstructed.size - reconstructed.sum()),
            "input_topology": before, "reconstructed_topology": after, "topology_unchanged": before == after}
