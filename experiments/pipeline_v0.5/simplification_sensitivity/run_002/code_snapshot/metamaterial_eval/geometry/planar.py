"""Build unmodified polygon candidates and report OGC/manifold limitations."""
from collections import defaultdict
import numpy as np
import shapely
from shapely import Polygon, MultiPolygon, LinearRing, STRtree
from shapely.validation import explain_validity
from .boundaries import decompose_pinched_loops


def build_exact_planar_geometry(loops):
    loops = decompose_pinched_loops(loops)
    shells = [r for r in loops if r["role"] == "shell"]
    holes = [r for r in loops if r["role"] == "hole"]
    containers = [Polygon(r["xy"]) for r in shells]
    tree = STRtree(containers)
    assigned = [[] for _ in shells]
    for hole in holes:
        candidate = Polygon(hole["xy"])
        # Full region containment prevents assignment to a nested solid island.
        possible = [int(i) for i in tree.query(candidate) if containers[int(i)].covers(candidate)]
        if not possible:
            raise ValueError("Hole has no containing shell; original loops retained.")
        parent = min(possible, key=lambda i: (containers[i].area, i))
        assigned[parent].append(hole["xy"])
    polygons = [Polygon(shell["xy"], inner) for shell, inner in zip(shells, assigned)]
    return polygons[0] if len(polygons) == 1 else MultiPolygon(polygons)


def validate_planar_geometry(geometry, loops, boundaries):
    cycles = decompose_pinched_loops(loops)
    rings = [LinearRing(r['xy']) for r in cycles]
    traced_simple = all(LinearRing(r['xy']).is_simple for r in loops)
    repeated = []
    for i, r in enumerate(loops):
        p = r["xy"][:-1]
        if len(set(map(tuple, p))) != len(p):
            repeated.append(i)
    simple = all(r.is_simple for r in rings)
    contacts = defaultdict(list)
    for i, loop in enumerate(cycles):
        for p in loop['xy'][:-1]:
            contacts[tuple(p)].append(i)
    touching = []
    for p in boundaries['nonmanifold_vertices_xy']:
        indices = contacts[tuple(p)]
        roles = [cycles[i]['role'] for i in indices]
        kind = ('self_pinched_ring' if len(set(indices)) < len(indices) else
                'holes_touch' if roles and all(role == 'hole' for role in roles) else
                'hole_touches_shell' if 'hole' in roles else 'solid_point_contact')
        touching.append({'xy':p,'loop_indices':indices,'kind':kind})
    valid = bool(geometry is not None and geometry.is_valid)
    manifold = not boundaries["nonmanifold_vertices_xy"] and simple
    polygons = list(geometry.geoms) if geometry is not None and geometry.geom_type == "MultiPolygon" else ([geometry] if geometry is not None else [])
    return {
        "ogc_valid": valid,
        "validity_reason": explain_validity(geometry) if geometry is not None else "Polygon construction failed",
        "geometry_type": geometry.geom_type if geometry is not None else None,
        "polygon_count": len(polygons),
        "hole_count": sum(len(p.interiors) for p in polygons),
        "shell_loop_count": sum(r["role"] == "shell" for r in loops),
        "hole_loop_count": sum(r["role"] == "hole" for r in loops),
        "all_rings_closed": all(r.is_closed for r in rings),
        "all_rings_simple": simple, "repeated_vertex_loop_indices": repeated,
        "traced_loops_simple":traced_simple,
        "polygon_ring_count":len(cycles),
        "polygon_holes_from_exterior_walk":sum(r['role']=='hole' and not r['digital_enclosed_pore'] for r in cycles),
        "exact_ring_decomposition_applied":len(cycles) != len(loops),
        "orientation_consistent": all((r["signed_area2"] > 0) == (r["role"] == "shell") and r["signed_area2"] != 0 for r in loops),
        "manifold_boundary": manifold,
        "cad_conversion_blocked": not (valid and manifold),
        "point_contact_vertices_xy": boundaries["nonmanifold_vertices_xy"],
        "boundary_contact_diagnostics": touching,
        "geometry_area": float(geometry.area) if geometry is not None else None,
        "signed_loop_area": sum(r["signed_area2"] for r in loops) / 2,
        "repair_applied": False,
    }


def rasterize_exact_geometry(geometry, resolution):
    if not geometry.is_valid:
        raise ValueError("Cannot certify polygon rasterization of invalid geometry.")
    shapely.prepare(geometry)
    result = np.empty((resolution, resolution), dtype=np.uint8)
    x = np.arange(resolution, dtype=float) + 0.5
    for row in range(0, resolution, 64):
        y = np.arange(row, min(row + 64, resolution), dtype=float) + 0.5
        result[row:row + len(y)] = shapely.contains_xy(geometry, x[None, :], y[:, None])
    return result
