"""Frozen solid definitions plus explicitly separate digital void diagnostics."""
import numpy as np
from scipy import ndimage as ndi

from ..pipeline.evaluator import load_evaluator
from ..pipeline.config import default_evaluator_path
from .inputs import sha256_file

FROZEN_SHA256 = "5f28ed1f77f95fd23a517cd223bbe6c6b5edc7d5508093f36f523b2d4f85cebb"


def void_regions(mask, connectivity):
    labels, count = ndi.label(mask == 0, structure=ndi.generate_binary_structure(2, connectivity))
    exterior = set(np.unique(np.concatenate((labels[0], labels[-1], labels[:, 0], labels[:, -1])))) - {0}
    return {"component_count": int(count), "exterior_count": len(exterior),
            "enclosed_count": int(count - len(exterior)),
            "exterior_labels": sorted(map(int, exterior))}


def analyze_raster_topology(mask):
    path = default_evaluator_path()
    if sha256_file(path) != FROZEN_SHA256:
        raise RuntimeError("Frozen evaluator v1.1 hash mismatch.")
    basic = load_evaluator(str(path.resolve())).basic_metrics(mask)
    a, b, c, d = mask[:-1, :-1], mask[:-1, 1:], mask[1:, :-1], mask[1:, 1:]
    yy, xx = np.nonzero((a == d) & (b == c) & (a != b))
    return {"component_count": int(basic["component_count"]),
            "percolates_x": bool(basic["Px"]), "percolates_y": bool(basic["Py"]),
            "intended_network": bool(basic["component_count"] == 1 and basic["Px"] and basic["Py"]),
            "void_8": void_regions(mask, 2), "void_4_frozen_convention": void_regions(mask, 1),
            "checkerboard_vertices_xy": np.column_stack((xx + 1, yy + 1)).tolist()}
