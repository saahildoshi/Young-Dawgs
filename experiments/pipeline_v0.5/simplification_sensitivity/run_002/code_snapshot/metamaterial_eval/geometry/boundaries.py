"""Integer exposed edges and iterative deterministic walks; no cell polygons."""
from collections import defaultdict
import numpy as np


def extract_cell_boundaries(mask):
    solid = np.pad(mask.astype(bool), 1)
    center = solid[1:-1, 1:-1]
    parts = []
    # solid on right in y-down raster display
    for neighbor, start, end in (
        (solid[:-2, 1:-1], (0, 0), (1, 0)),
        (solid[1:-1, 2:], (1, 0), (1, 1)),
        (solid[2:, 1:-1], (1, 1), (0, 1)),
        (solid[1:-1, :-2], (0, 1), (0, 0)),
    ):
        y, x = np.nonzero(center & ~neighbor)
        xy = np.column_stack((x, y)).astype(np.int32)
        parts.append(np.stack((xy + start, xy + end), axis=1))
    edges = np.concatenate(parts).astype(np.int32)
    order = np.lexsort((edges[:, 1, 1], edges[:, 1, 0], edges[:, 0, 1], edges[:, 0, 0]))
    return edges[order]


def signed_area2(ring):
    p = np.asarray(ring, dtype=np.int64)
    return int(np.sum(p[:-1, 0] * p[1:, 1] - p[1:, 0] * p[:-1, 1]))


def coalesce_collinear(ring):
    p = np.asarray(ring[:-1], dtype=np.int32)
    before, after = p - np.roll(p, 1, axis=0), np.roll(p, -1, axis=0) - p
    turns = before[:, 0] * after[:, 1] - before[:, 1] * after[:, 0]
    same_direction = np.sum(before * after, axis=1) > 0
    p = p[(turns != 0) | ~same_direction]
    # Canonical start; preserve signed winding and repeated non-manifold vertices.
    start = np.lexsort((p[:, 1], p[:, 0]))[0]
    p = np.roll(p, -int(start), axis=0)
    return np.vstack((p, p[0]))


def trace_boundary_loops(edges):
    outgoing, incoming = defaultdict(list), defaultdict(list)
    directions = {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}
    direction = []
    for i, (a, b) in enumerate(edges):
        outgoing[tuple(a)].append(i)
        incoming[tuple(b)].append(i)
        direction.append(directions[tuple(b - a)])
    if set(outgoing) != set(incoming) or any(len(v) != len(incoming[k]) for k, v in outgoing.items()):
        raise ValueError("Boundary graph has an unbalanced/open vertex.")
    # A fixed bijective successor map avoids order-dependent walks at pinches.
    successor = np.empty(len(edges), dtype=np.int64)
    for i, (_, end) in enumerate(edges):
        options = outgoing[tuple(end)]
        successor[i] = min(options, key=lambda j: ({1: 0, 0: 1, 3: 2, 2: 3}[(direction[j] - direction[i]) % 4], j))
    if len(set(successor.tolist())) != len(edges):
        raise ValueError("Ambiguous boundary pairing is not bijective.")
    used = np.zeros(len(edges), dtype=bool)
    loops = []
    for start in range(len(edges)):
        if used[start]:
            continue
        walk, current = [], start
        while not used[current]:
            used[current] = True
            walk.append(edges[current, 0])
            current = int(successor[current])
        if current != start:
            raise ValueError("Boundary walk merged into a previously traced loop.")
        raw = np.vstack((walk, walk[0]))
        ring = coalesce_collinear(raw)
        area2 = signed_area2(ring)
        loops.append({"xy": ring.tolist(), "signed_area2": area2,
                      "role": "shell" if area2 > 0 else "hole",
                      "unit_edge_count": len(walk)})
    loops.sort(key=lambda r: (r["xy"][0], r["role"], r["xy"]))
    return loops, {
        "exposed_edge_count": len(edges), "loop_count": len(loops),
        "vertices_before_coalescing": len(edges),
        "vertices_after_coalescing": sum(len(r["xy"]) - 1 for r in loops),
        "nonmanifold_vertices_xy": [list(map(int, p)) for p in sorted(outgoing) if len(outgoing[p]) > 1],
        "duplicate_edge_count": len(edges) - len(set(map(tuple, edges.reshape(-1, 4).tolist()))),
        "zero_length_edge_count": int(np.count_nonzero(np.all(edges[:, 0] == edges[:, 1], axis=1))),
        "all_edges_traced_once": bool(used.all()),
    }


def decompose_pinched_loops(loops):
    """Partition walks at repeated vertices without adding/removing any edge.

    This exact graph bookkeeping produces simple cycles for OGC construction;
    contacts remain in the boundary graph and still block manifold suitability.
    """
    cycles = []
    for source_index, loop in enumerate(loops):
        stack, positions = [], {}
        for raw in loop['xy']:
            vertex = tuple(raw)
            if vertex in positions:
                index = positions[vertex]
                ring = coalesce_collinear(stack[index:] + [vertex])
                area2 = signed_area2(ring)
                if area2 == 0:
                    raise ValueError('Zero-area cycle in boundary decomposition.')
                cycles.append({'xy':ring.tolist(),'signed_area2':area2,
                               'role':'shell' if area2 > 0 else 'hole',
                               'source_loop':source_index,'source_loop_role':loop['role'],
                               'digital_enclosed_pore':area2 < 0 and loop['role'] == 'hole'})
                for old in stack[index+1:]:
                    del positions[old]
                stack = stack[:index+1]
            else:
                positions[vertex] = len(stack)
                stack.append(vertex)
        if len(stack) != 1:
            raise ValueError('Unclosed residual walk in boundary decomposition.')
    cycles.sort(key=lambda r:(r['xy'][0],r['role'],r['xy']))
    return cycles
