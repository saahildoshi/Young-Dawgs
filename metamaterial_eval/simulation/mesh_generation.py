"""Conforming native-2D quadratic triangles with all exact holes retained."""
from dataclasses import dataclass
import time
import numpy as np


@dataclass
class Mesh:
    nodes: np.ndarray             # zero-based contiguous IDs, x/y in mm
    triangles: np.ndarray         # Gmsh TRI6: I,J,K,IJ,JK,KI, all CCW
    boundary: np.ndarray          # oriented I,J,midside, solid on left
    boundary_groups: np.ndarray   # top/bottom/pore/external
    generation_seconds: float = 0.0


def generate_mesh(geometry, config):
    import gmsh
    from ..geometry.manifold.contacts import inspect_boundary
    from shapely.geometry.polygon import orient
    if geometry.geom_type != 'Polygon' or not geometry.is_valid or not inspect_boundary(geometry)['manifold']:
        raise ValueError('Only valid single manifold polygons are supported; no repair')
    geometry = orient(geometry, 1)
    started = time.perf_counter()
    gmsh.initialize()
    try:
        gmsh.option.setNumber('General.Terminal', 0)
        gmsh.option.setNumber('General.NumThreads', 1)
        gmsh.model.add('young_dawgs_2d')
        groups, loops, all_curves = {}, [], []
        for index, ring in enumerate([geometry.exterior, *geometry.interiors]):
            xy = np.asarray(ring.coords)[:-1]
            pts = [gmsh.model.geo.addPoint(float(x), float(y), 0) for x,y in xy]
            lines = [gmsh.model.geo.addLine(pts[i], pts[(i+1)%len(pts)]) for i in range(len(pts))]
            for i, tag in enumerate(lines):
                a, b = xy[i], xy[(i+1)%len(pts)]
                group = ('pore' if index else 'top' if np.allclose([a[1], b[1]], config.height, atol=1e-10,rtol=0)
                         else 'bottom' if np.allclose([a[1],b[1]],0,atol=1e-10,rtol=0) else 'external')
                groups[tag] = group
            loops.append(gmsh.model.geo.addCurveLoop(lines))
            all_curves.extend(lines)
        gmsh.model.geo.addPlaneSurface(loops)
        gmsh.model.geo.synchronize()
        distance = gmsh.model.mesh.field.add('Distance')
        gmsh.model.mesh.field.setNumbers(distance, 'CurvesList', all_curves)
        gmsh.model.mesh.field.setNumber(distance, 'Sampling', 3)
        threshold = gmsh.model.mesh.field.add('Threshold')
        for key, value in [('InField',distance), ('SizeMin',config.boundary_size), ('SizeMax',config.bulk_size),
                           ('DistMin',.005), ('DistMax',.02)]:
            gmsh.model.mesh.field.setNumber(threshold,key,value)
        gmsh.model.mesh.field.setAsBackgroundMesh(threshold)
        for key, value in [('Mesh.Algorithm',6), ('Mesh.MeshSizeFromPoints',0),
                           ('Mesh.MeshSizeExtendFromBoundary',0), ('Mesh.MeshSizeFromCurvature',0),
                           ('Mesh.MeshSizeMin',config.boundary_size), ('Mesh.MeshSizeMax',config.bulk_size),
                           ('Mesh.SecondOrderLinear',1), ('Mesh.ElementOrder',2)]:
            gmsh.option.setNumber(key,value)
        gmsh.model.mesh.generate(2)
        tags, xyz, _ = gmsh.model.mesh.getNodes()
        order = np.argsort(tags)
        sorted_tags = tags[order]
        nodes = xyz.reshape(-1,3)[order,:2]
        types, _, connectivity = gmsh.model.mesh.getElements(2)
        if list(types) != [9]:
            raise ValueError(f'Unsupported Gmsh element types: {types}; require TRI6 (9)')
        triangles = np.searchsorted(sorted_tags, connectivity[0]).reshape(-1,6)
        boundary, labels = [], []
        for tag, label in groups.items():
            types, _, con = gmsh.model.mesh.getElements(1,tag)
            if list(types) != [8]:
                raise ValueError('Require three-node straight quadratic boundary edges')
            edge = np.searchsorted(sorted_tags,con[0]).reshape(-1,3)
            boundary.extend(edge.tolist()); labels.extend([label]*len(edge))
        return Mesh(nodes,triangles,np.asarray(boundary,dtype=np.int64),np.asarray(labels),time.perf_counter()-started)
    finally:
        gmsh.finalize()


def save_mesh(mesh, path):
    np.savez_compressed(path,nodes=mesh.nodes,triangles=mesh.triangles,boundary=mesh.boundary,
                        boundary_groups=mesh.boundary_groups)
