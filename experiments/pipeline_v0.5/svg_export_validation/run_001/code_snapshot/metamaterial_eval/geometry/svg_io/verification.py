"""Compare the authoritative source with SVG-derived geometry, never repair it."""
from collections import Counter
import math

import numpy as np
import shapely
from shapely import LineString, Point, STRtree, box

from ..manifold.contacts import inspect_boundary
from ..validation.checks import (area_difference, boundary_distance, boundary_integrity,
                                 line_parts, polygons, region_correspondence, rings, signed_area, topology)


def topology_comparison(source, imported, domain):
    """Compare actual disjoint void faces, including nested solid islands.

    The historical C utility treats each hole ring as a filled disk. Such disks
    overlap for concentric nesting even when the represented geometry is equal.
    Keep that utility unchanged and report its result separately.
    """
    frame = box(0, 0, domain, domain)
    old_void = polygons(frame.difference(source)); new_void = polygons(frame.difference(imported))
    old_pores = [p for p in old_void if not p.intersects(frame.boundary)]
    new_pores = [p for p in new_void if not p.intersects(frame.boundary)]
    solid = region_correspondence(polygons(source), polygons(imported), False)
    void = region_correspondence(old_void, new_void, False)
    holes = region_correspondence(old_pores, new_pores)
    sides = [LineString([(0, 0), (domain, 0)]), LineString([(domain, 0), (domain, domain)]),
             LineString([(domain, domain), (0, domain)]), LineString([(0, domain), (0, 0)])]
    incidence = []
    for r in void["records"]:
        old = old_void[r["source_id"]]; new = new_void[r["candidate_ids"][0]] if len(r["candidate_ids"]) == 1 else None
        before = [bool(old.intersects(side)) for side in sides]
        after = [bool(new.intersects(side)) for side in sides] if new is not None else None
        incidence.append({"source_void": r["source_id"], "before_domain_sides": before, "after_domain_sides": after, "preserved": before == after})
    return {"passed": solid["passed"] and void["passed"] and holes["passed"] and all(r["preserved"] for r in incidence),
            "solid": solid, "void": void, "holes": holes, "exterior_incidence": incidence,
            "method": "Positive-overlap/reciprocal anchors on actual disjoint domain-void faces; enclosed faces exclude every nested solid island.",
            "legacy_C_ring_disk_comparison": topology(source, imported, domain)}


def _point(p):
    return tuple(float(v).hex() for v in p)


def _signature(g):
    vertices, edges = Counter(), Counter()
    for r in rings(g):
        xy = r["xy"]
        vertices.update(_point(p) for p in xy[:-1])
        edges.update(tuple(sorted((_point(a), _point(b)))) for a, b in zip(xy[:-1], xy[1:]))
    return vertices, edges


def compare_geometry(source, imported, *, domain=1024, full=True):
    a, ae = _signature(source); b, be = _signature(imported)
    same_coordinates = a == b; same_segments = ae == be
    area = area_difference(source, imported)
    difference_length = source.boundary.symmetric_difference(imported.boundary).length
    if source.boundary.equals(imported.boundary):
        distance = {"lower": 0., "upper": 0., "method": "Zero boundary line-set difference; exact represented boundary sets coincide."}
    elif full:
        distance = boundary_distance(source, imported)
    else:
        # A deliberately diagnostic path: a lower bound cannot certify a pass.
        distance = {"lower": float(shapely.hausdorff_distance(source.boundary, imported.boundary)), "upper": None, "method": "Diagnostic discrete Hausdorff lower bound only."}
    source_integrity = boundary_integrity(source); imported_integrity = boundary_integrity(imported)
    dedicated = inspect_boundary(imported) if full else None
    topo = topology_comparison(source, imported, domain) if full else None
    arithmetic_allowance = 64 * np.finfo(np.float64).eps * domain**2
    source_shoelace = math.fsum((1 if r["role"] == "shell" else -1) * abs(signed_area(r["xy"])) for r in rings(source))
    imported_shoelace = math.fsum((1 if r["role"] == "shell" else -1) * abs(signed_area(r["xy"])) for r in rings(imported))
    gates = {"exact_binary64_vertices": same_coordinates, "exact_binary64_segments": same_segments,
             "geometric_equals": bool(source.equals(imported)),
             "zero_added_removed_symmetric": all(area[k] == 0 for k in ("added", "removed", "symmetric")),
             "area_arithmetic_only": abs(area["net_area"]) <= arithmetic_allowance and abs(imported_shoelace - source_shoelace) <= arithmetic_allowance,
             "zero_boundary_line_set_difference": difference_length == 0,
             "source_manifold": source_integrity["passed"], "imported_manifold_incidence": imported_integrity["passed"]}
    if full:
        gates.update(dedicated_manifold=dedicated["manifold"], continuous_topology=topo["passed"], zero_displacement=distance["upper"] == 0)
    changed_coordinates = list((a - b).elements())[:8]
    return {"passed": all(gates.values()), "gates": gates, "area": area, "distance": distance,
            "boundary_line_set_difference_length": difference_length,
            "source_shoelace_area": source_shoelace, "imported_shoelace_area": imported_shoelace,
            "area_arithmetic_allowance": arithmetic_allowance,
            "coordinate_comparison": {"exact_vertices": same_coordinates, "exact_segments": same_segments,
                "source_vertices": sum(a.values()), "imported_vertices": sum(b.values()),
                "missing_vertex_instances": sum((a - b).values()), "new_vertex_instances": sum((b - a).values()),
                "source_coordinate_examples_not_recovered": changed_coordinates,
                "method": "Binary64 hex vertex and undirected edge multisets, preserving multiplicity; independent of winding, cyclic start and component order."},
            "source_integrity": source_integrity, "imported_integrity": imported_integrity,
            "dedicated_manifold": dedicated, "topology": topo}


def compare_repairs(source, imported, exact, qualification):
    rows = []
    for change in qualification.get("changes", []):
        x, y = change["xy"]; window = box(x - .5, y - .5, x + .5, y + .5)
        before_boundary = source.boundary.intersection(window); after_boundary = imported.boundary.intersection(window)
        def clearance(boundary):
            pp = line_parts(shapely.line_merge(boundary))
            return pp[0].distance(pp[1]) if len(pp) == 2 else None
        first, last = clearance(before_boundary), clearance(after_boundary)
        first_patch = source.difference(exact).intersection(window); last_patch = imported.difference(exact).intersection(window)
        row = {"contact_id": change["contact_id"], "xy": [x, y], "registered_radius": change["L1_radius"],
               "before_clearance": first, "after_clearance": last,
               "clearance_change": last - first if first is not None and last is not None else None,
               "local_symmetric_area": source.symmetric_difference(imported).intersection(window).area,
               "local_boundary_difference_length": before_boundary.symmetric_difference(after_boundary).length,
               "source_added_solid_footprint_area": first_patch.area,
               "imported_added_solid_footprint_area": last_patch.area,
               "added_footprint_difference_area": first_patch.symmetric_difference(last_patch).area,
               "source_boundary_xy": [list(p.coords) for p in line_parts(before_boundary)],
               "imported_boundary_xy": [list(p.coords) for p in line_parts(after_boundary)]}
        row["passed"] = bool(first is not None and last is not None and first > 0 and last == first and row["local_symmetric_area"] == 0 and row["local_boundary_difference_length"] == 0 and row["added_footprint_difference_area"] == 0)
        rows.append(row)
    return {"passed": all(r["passed"] for r in rows), "registered_count": len(rows), "records": rows,
            "minimum_before_clearance": min((r["before_clearance"] for r in rows if r["before_clearance"] is not None), default=None),
            "minimum_after_clearance": min((r["after_clearance"] for r in rows if r["after_clearance"] is not None), default=None)}


def compare_protected(source, imported, guard=None, natural_probes=()):
    records = []
    for p in natural_probes:
        center = Point(p["center_xy"]); ends = np.asarray(p["candidate_chord"]["segment_xy"])
        direction = ends[1] - ends[0]; direction /= np.linalg.norm(direction)
        line = LineString([np.asarray(center.coords[0]) - 2048 * direction, np.asarray(center.coords[0]) + 2048 * direction])
        values = []
        for g in (source, imported):
            pp = [part for part in line_parts(g.intersection(line)) if part.distance(center) <= 1e-10]
            values.append(pp[0].length if len(pp) == 1 else None)
        records.append({"probe_id": p["probe_id"], "center_xy": p["center_xy"], "before": values[0], "after": values[1],
                        "passed": values[0] is not None and values[1] == values[0]})
    solid_difference = source.symmetric_difference(imported).intersection(guard).area if guard is not None else None
    boundary_difference = source.boundary.symmetric_difference(imported.boundary).intersection(guard).length if guard is not None else None
    return {"passed": all(r["passed"] for r in records) and (guard is None or solid_difference == boundary_difference == 0),
            "guard_solid_difference": solid_difference, "guard_boundary_difference": boundary_difference,
            "natural_widths": records, "coordinate_preservation": "Full-source exact segment/vertex comparison is additionally mandatory."}

