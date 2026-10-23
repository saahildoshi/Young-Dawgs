"""Small deterministic orchestration layer; profiling belongs to the runner."""
import json
from shapely.errors import GEOSException
from .inputs import validate_mask, COORDINATES
from .boundaries import extract_cell_boundaries, trace_boundary_loops
from .planar import build_exact_planar_geometry, validate_planar_geometry, rasterize_exact_geometry
from .raster import rasterize_boundary_loops, compare_binary_masks


def geometry_bytes(document):
    return (json.dumps(document, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def convert_exact(mask):
    validate_mask(mask)
    edges = extract_cell_boundaries(mask)
    loops, boundary = trace_boundary_loops(edges)
    document = {"schema": "young-dawgs-exact-cell-boundaries-v0.5A", "resolution": mask.shape[0],
                "coordinates": {**COORDINATES, "domain": [0, mask.shape[0], 0, mask.shape[0]]}, "loops": loops}
    geometry, error = None, None
    try:
        geometry = build_exact_planar_geometry(loops)
    except (ValueError, GEOSException) as exc:
        error = str(exc)
    validity = validate_planar_geometry(geometry, loops, boundary)
    validity["construction_error"] = error
    reconstructed = rasterize_boundary_loops(loops, mask.shape[0])
    comparison = compare_binary_masks(mask, reconstructed)
    validity['multipart_geometry'] = validity['polygon_count'] > 1
    validity['unexpected_polygon_component_count'] = validity['polygon_count'] != comparison['input_topology']['component_count']
    validity['disconnected_geometrical_interiors'] = validity['polygon_count'] > 1
    validity['hole_loop_count_matches_void_8'] = validity['hole_loop_count'] == comparison['input_topology']['void_8']['enclosed_count']
    validity['polygon_hole_count_matches_void_4'] = validity['hole_count'] == comparison['input_topology']['void_4_frozen_convention']['enclosed_count']
    validity["area_equals_occupied_cells"] = validity["signed_loop_area"] == int(mask.sum()) and validity["geometry_area"] == int(mask.sum())
    comparison["polygon_roundtrip"] = None
    if validity["ogc_valid"]:
        comparison["polygon_roundtrip"] = compare_binary_masks(mask, rasterize_exact_geometry(geometry, mask.shape[0]))
    exact = comparison["exact_equal"] and comparison["topology_unchanged"] and validity["area_equals_occupied_cells"]
    passed = exact and not validity["cad_conversion_blocked"] and comparison["polygon_roundtrip"] is not None and comparison["polygon_roundtrip"]["exact_equal"]
    return {"document": document, "edges": edges, "boundaries": boundary,
            "geometry": geometry, "validity": validity, "reconstructed": reconstructed,
            "comparison": comparison, "status": "PASS_EXACT_BASELINE" if passed else "HOLD_GEOMETRY",
            "exact_boundary_reconstruction": bool(exact)}
