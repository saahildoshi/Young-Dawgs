"""Categorical transverse-section observations; no physical fiber instance inference.

Phase IDs are author-defined: 0 polymer matrix, 1 carbon fiber, 2 void.
All distances/areas are pixels/pixels squared. Connected annotation regions may
contain touching circles; their geometry and centroids are region proxies only.
Historical binary/longitudinal descriptors deliberately remain unchanged.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial.distance import cdist
from skimage.measure import regionprops

from metamaterial_eval.metrics import compute_basic_metrics, compute_s2_correlation
from .descriptors import directional_s2

PHASES = {0: "matrix", 1: "fiber", 2: "void"}
FOUR = ndi.generate_binary_structure(2, 1)


def validate_transverse(a):
    if not isinstance(a, np.ndarray) or a.shape != (256, 256) or a.dtype != np.uint8:
        raise ValueError("Expected 256x256 uint8 categorical transverse section")
    if not np.isin(a, list(PHASES)).all():
        raise ValueError("Allowed labels: 0 matrix, 1 fiber, 2 void; unknown labels rejected")
    return a


def _summary(values):
    return {"values": values, "mean": float(np.mean(values)) if values else None,
            "std": float(np.std(values)) if values else None}


def _regions(mask):
    labels, n = ndi.label(mask, FOUR)
    edge = set(np.unique(np.r_[labels[0], labels[-1], labels[:, 0], labels[:, -1]])) - {0}
    complete = [p for p in regionprops(labels) if p.label not in edge]
    centers = np.array([p.centroid for p in complete])
    nn = []
    if len(centers) > 1:
        distances = cdist(centers, centers)
        np.fill_diagonal(distances, np.inf)
        nn = distances.min(axis=1).tolist()
    return {"connectivity": 4, "annotation_region_count": int(n),
            "boundary_censored_region_count": len(edge), "complete_region_count": len(complete),
            "complete_region_area_px2": _summary([float(p.area) for p in complete]),
            "complete_region_equivalent_diameter_px": _summary([float(p.equivalent_diameter_area) for p in complete]),
            "complete_region_aspect_ratio": _summary([float(p.axis_major_length / p.axis_minor_length)
                                                       for p in complete if p.axis_minor_length > 0]),
            "complete_region_centroid_nearest_neighbor_px": _summary(nn),
            "instance_interpretation": "Connected annotation regions, not recovered physical fiber/void instances; touching or merged contours remain unresolved"}


def describe_transverse(a):
    """Observe each phase separately, with finite boundaries and no binarization."""
    validate_transverse(a)
    phases = {}
    for k, name in PHASES.items():
        onehot = (a == k).astype(np.uint8)
        basic = compute_basic_metrics(onehot)
        phases[name] = {"label": k, "pixel_count": int(onehot.sum()), "fraction": float(onehot.mean()),
                        "largest_component_fraction_of_phase": basic["largest_component_fraction"],
                        "percolates_x": basic["percolates_x"], "percolates_y": basic["percolates_y"],
                        "S2_x": [directional_s2(onehot, r, 1) for r in range(17)],
                        "S2_y": [directional_s2(onehot, r, 0) for r in range(17)],
                        "S2_radial": compute_s2_correlation(onehot, 16)["s2"].tolist()}
        if k in (1, 2):
            phases[name]["regions"] = _regions(onehot)
    interfaces = {}
    for p, q in [(0, 1), (0, 2), (1, 2)]:
        count = 0
        for left, right in [(a[:, :-1], a[:, 1:]), (a[:-1], a[1:])]:
            count += int(np.count_nonzero(((left == p) & (right == q)) | ((left == q) & (right == p))))
        interfaces[f"{PHASES[p]}__{PHASES[q]}"] = {"internal_pixel_edge_count": count,
                                                         "edge_count_per_pixel2": count / a.size}
    return {"family": "fiber_transverse", "schema": "CFRP_0_matrix_1_fiber_2_void_v1",
            "shape": list(a.shape), "physical_um_per_pixel": None, "boundary": "finite_nonperiodic",
            "phase_roles": {"matrix": "solid", "fiber": "solid", "void": "void"},
            "phases": phases, "phase_pair_interfaces": interfaces,
            "physical_fiber_instance_count": None,
            "annotation_limit": "Fiber contours were annotated as perfect circles around detected centers with an average radius; voids by minimum threshold. Region diameters and spacing are annotation proxies, not exact physical contours or instance statistics.",
            "interpretation": "Cross-sectional packing, area-equivalent diameter and spacing; no longitudinal length, curvature or in-plane fiber-axis orientation. No physical calibration inferred."}
