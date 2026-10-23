"""v0.4.1: unchanged native morphology plus an explicit bounded topology pass.

No pixels are removed, no seeds are retried, and already connected arrays are
bitwise unchanged. Short gaps are joined by Euclidean nearest-point capsules
in endpoint-normalized coordinates, not a fixed number of output pixels.
This is a generator operation, never an evaluator or validation repair.
"""
from copy import deepcopy
import hashlib

import numpy as np
from scipy import ndimage as ndi

from . import native_resolution as native
from ..pipeline.resolution import validate_resolution

GENERATOR_VERSION = "0.4.1"
SOURCE_V03_SHA256 = native.SOURCE_V03_SHA256
_select = native._select
# v0.3's two-sided interface is two baseline pixels wide. Retain that physical
# neck scale, and refuse gaps longer than twice it. These are geometry policy
# constants, not parameters optimized against evaluation results.
BRIDGE_WIDTH = 2 / 255
MAX_BRIDGE_LENGTH = 4 / 255
MAX_ADDED_AREA_FRACTION = .001
FOUR = ndi.generate_binary_structure(2, 1)


def connect_short_gaps(binary):
    """Return a new mask and an auditable record, or reject an excessive repair.

    Principal component = largest (lowest label on ties). The next endpoint is
    the globally nearest nonprincipal solid pixel (row-major on ties). SciPy
    EDT supplies its nearest principal point. A native-grid capsule joins the
    pair, then components are relabeled. Distances refer to pixel centers.
    Large gaps and material additions fail closed, retaining no partial result.
    Connectivity does not imply percolation; the generator checks that next.
    """
    a = np.asarray(binary)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or a.dtype != np.uint8 or not np.isin(a, [0, 1]).all():
        raise ValueError("Require a square uint8 binary array.")
    n = validate_resolution(a.shape[0])
    result = a.copy()
    labels, count = ndi.label(result, structure=FOUR)
    if count == 0:
        raise ValueError("Cannot connect an empty phase.")
    record = {"policy": "nearest-point normalized capsule; addition only",
              "bridge_width_normalized": BRIDGE_WIDTH, "max_length_normalized": MAX_BRIDGE_LENGTH,
              "max_added_area_fraction": MAX_ADDED_AREA_FRACTION,
              "components_before": int(count), "bridges": [],
              "raw_pixel_sha256": hashlib.sha256(a.tobytes()).hexdigest()}
    while count > 1:
        sizes = np.bincount(labels.ravel()); sizes[0] = 0
        main = labels == np.argmax(sizes)
        distance, nearest = ndi.distance_transform_edt(~main, return_indices=True)
        candidates = np.argwhere((labels > 0) & ~main)
        start = candidates[np.argmin(distance[tuple(candidates.T)])]
        end = nearest[:, start[0], start[1]]
        length = float(np.linalg.norm(end - start)) / (n - 1)
        if length > MAX_BRIDGE_LENGTH:
            raise RuntimeError(f"Topology gap {length:.8g} exceeds normalized repair limit {MAX_BRIDGE_LENGTH:.8g}.")
        radius = BRIDGE_WIDTH * (n - 1) / 2
        lower = np.maximum(0, np.floor(np.minimum(start, end) - radius).astype(int))
        upper = np.minimum(n, np.ceil(np.maximum(start, end) + radius).astype(int) + 1)
        yy, xx = np.mgrid[lower[0]:upper[0], lower[1]:upper[1]]
        points = np.stack((yy, xx), axis=-1)
        delta = end - start
        t = np.clip(np.sum((points - start) * delta, axis=-1) / np.dot(delta, delta), 0, 1)
        capsule = np.sum((points - (start + t[..., None] * delta))**2, axis=-1) <= radius**2
        region = result[lower[0]:upper[0], lower[1]:upper[1]]
        added = int(np.count_nonzero(capsule & ~region.astype(bool)))
        region[capsule] = 1
        if np.count_nonzero(result != a) / a.size > MAX_ADDED_AREA_FRACTION:
            raise RuntimeError("Topology repair exceeds normalized added-area budget.")
        record["bridges"].append({"start_yx": start.tolist(), "end_yx": end.tolist(),
                                  "start_normalized_yx": (start / (n - 1)).tolist(),
                                  "end_normalized_yx": (end / (n - 1)).tolist(),
                                  "centerline_length_normalized": length, "added_pixels": added})
        previous = count
        labels, count = ndi.label(result, structure=FOUR)
        if count >= previous:
            raise RuntimeError("Capsule failed to reduce 4-connected component count.")
    record.update(components_after=int(count), added_pixels=int(np.count_nonzero(result != a)),
                  added_area_fraction=float(np.mean(result != a)), removed_pixels=0,
                  repaired_pixel_sha256=hashlib.sha256(result.tobytes()).hexdigest())
    return result, record


def generate_with_metadata(seed, solid_fraction_target, strut_scale, pore_scale, resolution=256):
    """Generate the same accepted latent realization and report explicit repairs."""
    n = validate_resolution(resolution)
    phi, strut, pore = map(float, (solid_fraction_target, strut_scale, pore_scale))
    if not all(np.isfinite([phi, strut, pore])) or not (0 < phi < 1 and strut > 0 and pore > 0):
        raise ValueError("Require finite 0 < solid fraction < 1 and positive scales.")
    state, baseline, attempt = _select(seed, phi, strut, pore)
    if n == 256:
        raw = baseline.copy()
    else:
        rng = np.random.default_rng()
        rng.bit_generator.state = deepcopy(state)
        raw = native._render_native(rng, phi, strut, pore, n)
    result, metadata = connect_short_gaps(raw)
    metadata["candidate_index"] = attempt
    if not native._valid(result):
        raise RuntimeError("Connected output does not span both axes; no artificial perimeter is added.")
    return result, metadata


def generate_microstructure(seed, solid_fraction_target, strut_scale, pore_scale, resolution=256):
    """Drop-in generator; use generate_with_metadata for the repair audit trail."""
    return generate_with_metadata(seed, solid_fraction_target, strut_scale, pore_scale, resolution)[0]


generate_microstructure_at_resolution = generate_microstructure
