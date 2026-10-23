"""Indexed boundary intersections, local links and exact source provenance."""
from collections import defaultdict
from fractions import Fraction
import math

import numpy as np
import shapely
from scipy import ndimage as ndi
from shapely import LineString, LinearRing, Polygon, STRtree

from ..boundaries import decompose_pinched_loops


def polygon_rings(geometry):
    polygons = list(geometry.geoms) if geometry.geom_type == 'MultiPolygon' else [geometry]
    rings = []
    for pi, polygon in enumerate(polygons):
        for role, coords in [('shell', polygon.exterior.coords)] + [('hole', h.coords) for h in polygon.interiors]:
            rings.append({'xy':np.asarray(coords).tolist(), 'role':role, 'polygon':pi})
    return rings


def _point_parts(geometry):
    if geometry.is_empty:
        return []
    if geometry.geom_type == 'Point':
        return [tuple(geometry.coords[0])]
    if hasattr(geometry, 'geoms'):
        return [p for g in geometry.geoms for p in _point_parts(g)]
    return []


def _ray_key(delta):
    # Exact binary-rational direction normalization, no coincidence tolerance.
    a,b = map(Fraction.from_float, map(float,delta))
    scale = abs(a) if a else abs(b)
    return (a/scale,b/scale)


def inspect_boundary(geometry=None, *, rings=None, near_distance=0.0):
    """Qualify the assembled boundary, not merely OGC validity/vertex counts.

    Exact contacts use GEOS robust predicates without snapping. A positive
    near_distance is an explicit diagnostic search radius, never a merge rule.
    """
    if not math.isfinite(near_distance) or near_distance < 0:
        raise ValueError('near_distance must be finite and nonnegative.')
    if rings is None:
        rings = polygon_rings(geometry)
    segments, owners, local_indices, sizes = [],[],[],[]
    zero, unclosed = [],[]
    for ri, ring in enumerate(rings):
        xy = np.asarray(ring['xy'], dtype=float)
        if not np.isfinite(xy).all() or xy.ndim != 2 or xy.shape[1] != 2 or len(xy) < 2:
            raise ValueError('Require finite two-dimensional ring coordinates.')
        if not np.array_equal(xy[0],xy[-1]):
            unclosed.append(ri)
        sizes.append(len(xy)-1)
        for si,(a,b) in enumerate(zip(xy[:-1],xy[1:])):
            if np.array_equal(a,b):
                zero.append({'ring':ri,'segment':si,'xy':a.tolist()})
            else:
                segments.append([a,b]); owners.append(ri); local_indices.append(si)
    coords = np.asarray(segments,dtype=float)
    if len(coords) == 0:
        return {'manifold':False,'contacts':[],'overlaps':[],'zero_length_segments':zero,
                'unclosed_rings':unclosed,'reason':'No nonzero boundary segments'}
    lines = shapely.linestrings(coords)
    tree = STRtree(lines)
    pairs = tree.query(lines,predicate='intersects').T
    owners = np.asarray(owners); local_indices=np.asarray(local_indices)
    pairs = pairs[pairs[:,0] < pairs[:,1]]
    # Ordinary adjacent edges at a proper noncollinear corner need no GEOS
    # intersection construction. All non-adjacent/overlapping pairs remain.
    if len(pairs):
        i,j=pairs.T; same=owners[i]==owners[j]
        delta=np.abs(local_indices[i]-local_indices[j])
        adjacent=same & ((delta==1)|(delta==np.asarray(sizes)[owners[i]]-1))
        u=coords[i,1]-coords[i,0];v=coords[j,1]-coords[j,0]
        cross=u[:,0]*v[:,1]-u[:,1]*v[:,0]
        pairs=pairs[~(adjacent & (cross!=0))]
    events=defaultdict(set); overlaps=[]
    for i,j in pairs:
        intersection=lines[i].intersection(lines[j])
        if intersection.length > 0:
            identical=lines[i].equals(lines[j])
            overlaps.append({'segments':[int(i),int(j)],'rings':[int(owners[i]),int(owners[j])],
                             'kind':'duplicate_segment' if identical else 'overlapping_segments',
                             'length':float(intersection.length),'geometry':shapely.to_wkt(intersection)})
        for p in _point_parts(intersection):
            events[p].update((int(i),int(j)))
    contacts=[]
    for p,indices in sorted(events.items()):
        # Include all incident segments, including a vertex on another edge.
        point=shapely.Point(p)
        indices=set(map(int,tree.query(point,predicate='intersects')))
        rays=set()
        for i in indices:
            for end in coords[i]:
                if tuple(end)!=p:
                    rays.add(_ray_key(end-np.asarray(p)))
        degree=len(rays)
        rs=sorted(set(int(owners[i]) for i in indices));roles=[rings[r]['role'] for r in rs]
        if degree==2 and len(rs)==1:
            continue  # harmless collinear subdivision
        if len(rs)>2:
            kind='multi_ring_contact_cluster'
        elif len(rs)==1:
            # Endpoint-only incidence is a self-touch; an interior intersection
            # is a crossing, even if the same ring happens to repeat a vertex.
            kind='self_touching_loop' if all(any(tuple(e)==p for e in coords[i]) for i in indices) else 'self_intersection'
        elif all(role=='hole' for role in roles):
            kind='pore_pore_point'
        elif 'hole' in roles:
            kind='hole_shell_point'
        else:
            kind='diagonal_solid_point'
        contacts.append({'contact_id':f'contact_{len(contacts):04d}','xy':list(p),'kind':kind,
                         'incident_rings':rs,'incident_ring_roles':roles,
                         'incident_polygons':sorted(set(rings[r].get('polygon',0) for r in rs)),
                         'incident_segments':sorted(indices),'boundary_link_degree':degree,
                         'blocks_manifold':degree!=2 or len(rs)>1,
                         'inherent_in_source':None,'representation_only_resolution':False,
                         'geometric_change_required':True})
    near=[]
    if near_distance:
        pairs=tree.query(lines,predicate='dwithin',distance=near_distance).T
        pairs=pairs[pairs[:,0]<pairs[:,1]]
        if len(pairs):
            i,j=pairs.T
            delta=np.abs(local_indices[i]-local_indices[j])
            adjacent=(owners[i]==owners[j]) & ((delta==1)|(delta==np.asarray(sizes)[owners[i]]-1))
            pairs=pairs[~adjacent]
        distances=shapely.distance(lines[pairs[:,0]],lines[pairs[:,1]]) if len(pairs) else []
        best={}
        for (i,j),distance in zip(pairs,distances):
            a,b=int(owners[i]),int(owners[j])
            if 0 < distance <= near_distance:
                key=(min(a,b),max(a,b))
                best[key]=min(best.get(key,math.inf),float(distance))
        near=[{'rings':list(key),'kind':'numerical_near_contact','distance':distance,
               'exact_contact':False,'blocks_manifold':False} for key,distance in sorted(best.items())]
    simple=all(len(r['xy'])>=4 and LinearRing(r['xy']).is_simple for r in rings)
    manifold=not contacts and not overlaps and not zero and not unclosed and simple
    return {'manifold':bool(manifold),'ogc_valid':bool(geometry.is_valid) if geometry is not None else None,
            'all_rings_simple':simple,'ring_count':len(rings),'segment_count':len(lines),
            'contacts':contacts,'overlaps':overlaps,'zero_length_segments':zero,
            'unclosed_rings':unclosed,'near_contacts':near,'near_distance':near_distance,
            'exact_contact_tolerance':0,'method':'STRtree segment intersections plus unique incident boundary rays/local links'}


def classify_contacts(mask, exact, *, near_distance=0.0):
    result=inspect_boundary(exact['geometry'],near_distance=near_distance)
    solid_labels,_=ndi.label(mask,structure=ndi.generate_binary_structure(2,1))
    void4,_=ndi.label(mask==0,structure=ndi.generate_binary_structure(2,1))
    void8,_=ndi.label(mask==0,structure=np.ones((3,3)))
    exterior=set(np.unique(np.concatenate((void8[0],void8[-1],void8[:,0],void8[:,-1]))))-{0}
    cycles=decompose_pinched_loops(exact['document']['loops'])
    source_incidence=defaultdict(list)
    for i,r in enumerate(exact['document']['loops']):
        for p in r['xy'][:-1]:
            source_incidence[tuple(p)].append(i)
    checks={tuple(p) for p in exact['comparison']['input_topology']['checkerboard_vertices_xy']}
    for contact in result['contacts']:
        px,py=contact['xy'];x,y=int(px),int(py)
        inherent=px==x and py==y and (x,y) in checks
        contact['inherent_in_source']=inherent
        contact['source_walks']=sorted(set(source_incidence[(px,py)]))
        contact['source_walk_repeats_vertex']=len(source_incidence[(px,py)])>len(contact['source_walks'])
        contact['at_domain_corner']=(px in (0,len(mask))) and (py in (0,len(mask)))
        if 0<x<len(mask) and 0<y<len(mask):
            cells=mask[y-1:y+1,x-1:x+1]
            s=solid_labels[y-1:y+1,x-1:x+1];v4=void4[y-1:y+1,x-1:x+1];v8=void8[y-1:y+1,x-1:x+1]
            contact['local_cells_NW_NE_SW_SE']=cells.ravel().tolist()
            contact['solid_global_4_labels']=s.ravel().tolist()
            contact['void_global_4_labels']=v4.ravel().tolist()
            contact['void_global_8_labels']=v8.ravel().tolist()
            contact['local_solid_4_components']=int(ndi.label(cells,structure=ndi.generate_binary_structure(2,1))[1])
            contact['local_void_4_components']=int(ndi.label(cells==0,structure=ndi.generate_binary_structure(2,1))[1])
            contact['local_void_8_components']=int(ndi.label(cells==0,structure=np.ones((3,3)))[1])
            contact['void_connects_exterior_8']=any(int(label) in exterior for label in v8.ravel() if label)
            contact['solid_sectors']=2 if inherent else None
            contact['void_sectors']=2 if inherent else None
            contact['diagonal_solid_cell_contact']=bool(inherent)
            contact['diagonal_void_cell_contact']=bool(inherent)
            contact['neighbor_solid_cells_share_edge']=False if inherent else None
            contact['local_positive_width_solid_connection']=False if inherent else None
        contact['pinched_exterior_boundary']=contact['kind']=='hole_shell_point'
        contact['possible_effects']={'solid_side':'adds a positive-width local solid connection and separates void closures',
                                     'void_side':'may merge pores or open an exterior channel; must test topology'}
    found={tuple(c['xy']) for c in result['contacts'] if c['inherent_in_source']}
    result['source_checkerboard_count']=len(checks)
    result['source_classifier_agreement']=checks==found
    # Adjacent lattice defects are reported as clusters, even though default
    # radius-0.25 supports are disjoint.
    pending={tuple(c['xy']):c['contact_id'] for c in result['contacts']}
    clusters=[]
    while pending:
        start=min(pending);queue=[start];members=[]
        while queue:
            p=queue.pop()
            if p not in pending: continue
            members.append(pending.pop(p))
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    q=(p[0]+dx,p[1]+dy)
                    if q in pending: queue.append(q)
        clusters.append(sorted(members))
    result['contact_clusters']=clusters
    result['classification_pass']=bool(result['source_classifier_agreement'] and not result['overlaps'] and not result['zero_length_segments'])
    return result


def inspect_patches(patches):
    """Explicit assembly semantics: interior patch seams are not boundary defects."""
    assembled=shapely.union_all(patches)
    seams=shapely.union_all([p.boundary for p in patches]).difference(assembled.boundary)
    return {'assembled_geometry':assembled,'boundary':inspect_boundary(assembled),
            'internal_shared_edge_length':float(seams.length),
            'kind':'valid_shared_decomposition_edges' if not seams.is_empty else 'no_internal_seams',
            'representation_only_correction':not seams.is_empty,'blocks_manifold':not inspect_boundary(assembled)['manifold']}
