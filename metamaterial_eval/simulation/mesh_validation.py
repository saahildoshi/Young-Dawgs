"""Independent full-domain, topology, quality and sampled feature screens."""
import numpy as np
import shapely
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from .element_quality import corner_metrics,quadratic_mapping


def validate_mesh(mesh, geometry, config):
    nodes, tri = mesh.nodes, mesh.triangles
    if nodes.ndim != 2 or nodes.shape[1] != 2 or not np.isfinite(nodes).all():
        raise ValueError('Require finite 2D nodes')
    if tri.ndim != 2 or tri.shape[1] != 6 or not len(tri) or tri.min()<0 or tri.max()>=len(nodes):
        raise ValueError('Invalid TRI6 connectivity')
    if len(np.unique(tri)) != len(nodes):
        raise ValueError('Mesh contains orphan nodes')
    points = nodes[tri[:,:3]]
    ab, ac = points[:,1]-points[:,0], points[:,2]-points[:,0]
    determinant = ab[:,0]*ac[:,1]-ab[:,1]*ac[:,0]
    if np.any(determinant <= 0):
        raise ValueError('Nonpositive element Jacobian')
    lengths = np.linalg.norm(points-np.roll(points,-1,axis=1),axis=2)
    midpoints=(points+np.roll(points,-1,axis=1))/2
    if not np.allclose(nodes[tri[:,3:]],midpoints,atol=1e-10,rtol=0):
        raise ValueError('Curved/misordered TRI6 midsides unsupported')
    mapping=quadratic_mapping(nodes[tri])
    if not np.all(mapping['positive_over_reference_triangle']):
        raise ValueError('Nonpositive or uncertified quadratic element Jacobian')
    quality = 2*np.sqrt(3)*determinant/np.sum(lengths**2,axis=1)
    aspect = np.max(lengths,axis=1)**2/determinant
    angles=corner_metrics(points)['angles_deg']
    edges=np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]])
    unique,counts=np.unique(np.sort(edges,axis=1),axis=0,return_counts=True)
    if counts.max()>2:
        raise ValueError('Nonmanifold mesh edge')
    # Midside ownership must also agree on shared edges.
    side_nodes=np.concatenate([tri[:,3],tri[:,4],tri[:,5]])
    ix=np.lexsort((np.sort(edges,axis=1)[:,1],np.sort(edges,axis=1)[:,0]))
    se=np.sort(edges,axis=1)[ix]; sm=side_nodes[ix]
    repeated=np.all(se[1:]==se[:-1],axis=1)
    if np.any(sm[1:][repeated]!=sm[:-1][repeated]):
        raise ValueError('Nonconforming midside connectivity')
    boundary=unique[counts==1]
    supplied=np.sort(mesh.boundary[:,:2],axis=1)
    if len(supplied)!=len(boundary) or set(map(tuple,supplied))!=set(map(tuple,boundary)):
        raise ValueError('Boundary inventory mismatch')
    midside_map={tuple(e):int(m) for e,m in zip(se,sm)}
    if any(midside_map[tuple(sorted(e[:2]))]!=e[2] for e in mesh.boundary):
        raise ValueError('Wrong boundary midside')
    corner_ids=np.unique(tri[:,:3]); idx=np.searchsorted(corner_ids,unique)
    graph=coo_matrix((np.ones(len(unique)),(idx[:,0],idx[:,1])),shape=(len(corner_ids),len(corner_ids)))
    components=connected_components(graph,directed=False,return_labels=False)
    euler=len(corner_ids)-len(unique)+len(tri)
    holes=int(components-euler)
    # GEOS coverage checks catch overlaps; union supplies independent domain/hole evidence.
    polygons=shapely.polygons(points)
    coverage_valid=bool(shapely.coverage_is_valid(polygons))
    if not coverage_valid:
        raise ValueError('Triangle coverage has overlaps or nonconforming edges')
    # Reconstruct the domain from the complete, independently checked boundary.
    # With valid nonoverlapping coverage, exact edge inventory and matching
    # total element area, this avoids unioning hundreds of thousands of cells.
    region=shapely.build_area(shapely.multilinestrings(nodes[mesh.boundary[:,:2]]))
    area_error=abs(float(determinant.sum()/2)-geometry.area)/geometry.area
    difference=float(region.symmetric_difference(geometry).area)
    # Each straight mesh edge must lie on one original straight segment, and
    # the lengths assigned to every source segment must reproduce it fully.
    # A global Hausdorff call is quadratic in tens of thousands of pixel edges.
    source_segments=np.concatenate([np.stack([np.asarray(r.coords)[:-1],np.asarray(r.coords)[1:]],axis=1)
                                    for r in [geometry.exterior,*geometry.interiors]])
    source_lines=shapely.linestrings(source_segments)
    source_ring=np.concatenate([np.full(len(r.coords)-1,i) for i,r in
                                enumerate([geometry.exterior,*geometry.interiors])])
    boundary_xy=nodes[mesh.boundary[:,:2]]
    nearest=shapely.STRtree(source_lines).nearest(shapely.points(boundary_xy.mean(axis=1)))
    distances=np.maximum(shapely.distance(shapely.points(boundary_xy[:,0]),source_lines[nearest]),
                         shapely.distance(shapely.points(boundary_xy[:,1]),source_lines[nearest]))
    boundary_error=float(distances.max())
    assigned_lengths=np.bincount(nearest,weights=np.linalg.norm(boundary_xy[:,1]-boundary_xy[:,0],axis=1),
                                minlength=len(source_lines))
    source_lengths=np.linalg.norm(source_segments[:,1]-source_segments[:,0],axis=1)
    segment_length_error=float(np.max(np.abs(assigned_lengths-source_lengths)))
    groups=set(mesh.boundary_groups)
    # Verify group locations and outward orientation geometrically, independent of Gmsh tags.
    a,b=nodes[mesh.boundary[:,0]],nodes[mesh.boundary[:,1]]
    centers=(a+b)/2
    right=np.column_stack((b[:,1]-a[:,1],a[:,0]-b[:,0]))
    step=np.minimum(np.linalg.norm(right,axis=1)*.01,1e-7)
    outside=centers+right/np.linalg.norm(right,axis=1)[:,None]*step[:,None]
    outward=bool(np.all(~shapely.contains_xy(geometry,outside[:,0],outside[:,1])))
    group_valid=True
    for label in groups:
        selected=mesh.boundary_groups==label
        if label=='top': valid=np.allclose(nodes[mesh.boundary[selected,:2],1],config.height,atol=1e-8,rtol=0)
        elif label=='bottom':valid=np.allclose(nodes[mesh.boundary[selected,:2],1],0,atol=1e-8,rtol=0)
        elif label=='pore':valid=np.all(source_ring[nearest[selected]]>0)
        elif label=='external':valid=np.all(source_ring[nearest[selected]]==0)
        else:valid=False
        group_valid=group_valid and bool(valid)
    gates={'one_component':int(components)==1,'holes_preserved':holes==len(geometry.interiors),
           'area':area_error<=1e-9,'domain_difference':difference<=1e-9*geometry.area,
           'boundary':boundary_error<=1e-8 and segment_length_error<=1e-8,'quality':float(quality.min())>=.1,
           'angles':float(np.min(angles))>=10,'aspect':float(aspect.max())<=20,
           'boundary_groups':{'top','bottom'}.issubset(groups) and group_valid,
           'outward_normals':outward,'quadratic_mapping':bool(np.all(mapping['positive_over_reference_triangle']))}
    return {'accepted':all(gates.values()),'gates':gates,'nodes':len(nodes),'elements':len(tri),
            'element_type':'quadratic_TRI6','order_distribution':{'2':len(tri)},
            'min_quality':float(quality.min()),'max_aspect_ratio':float(aspect.max()),
            'min_angle_deg':float(np.min(angles)),'min_jacobian_det_mm2':float(determinant.min()),
            'components':int(components),'holes':holes,'mesh_area_mm2':float(determinant.sum()/2),
            'relative_area_error':area_error,'symmetric_difference_mm2':difference,
            'boundary_error_mm':boundary_error,'max_source_segment_length_error_mm':segment_length_error,
            'boundary_counts':{g:int(sum(mesh.boundary_groups==g)) for g in sorted(groups)},
            'quadratic_mapping':{'method':mapping['method'],'limitation':mapping['limitation'],
                'minimum_determinant_mm2':float(mapping['determinant_min'].min()),
                'maximum_midpoint_error_mm':float(mapping['max_midpoint_error'].max()),
                'invalid_or_uncertified':int(sum(~mapping['positive_over_reference_triangle']))},
            'generation_seconds':mesh.generation_seconds},quality


def feature_resolution(mesh, probes, config, resolution=1024):
    """Count distinct intersected element interiors across source-only axial chords.

    Three quadratic elements per sampled chord is a feasibility screen; no
    exhaustive minimum-neck or response convergence claim follows from it.
    """
    from shapely import LineString
    points=mesh.nodes[mesh.triangles[:,:3]]
    polys=shapely.polygons(points);tree=shapely.STRtree(polys)
    records=[]
    for p in probes:
        x,y=p['xy'];width=p['source_pixel_run'];axis=p['axis']
        a=[x,y];b=[x,y];a[axis]-=width/2;b[axis]+=width/2
        def transform(v):return [v[0]*config.width/resolution,config.height-v[1]*config.height/resolution]
        chord=LineString([transform(a),transform(b)])
        ids=tree.query(chord,predicate='intersects')
        # Quadratic midside nodes do not create extra elements across a ligament.
        # Clip positive-length intersections and count intervals to avoid double
        # counting when the chord lies on a mesh edge.
        parts=shapely.intersection(polys[ids],chord)
        intervals=[]
        for part in parts:
            if part.length>1e-10:
                distances=sorted(chord.project(shapely.Point(v)) for v in part.coords)
                intervals.append((round(distances[0],10),round(distances[-1],10)))
        count=len(set(intervals))
        covered=float(shapely.union_all(parts).length) if len(parts) else 0.0
        records.append({**p,'elements_across':count,'chord_mm':chord.length,
                        'covered_mm':covered,'passed':count>=3 and abs(covered-chord.length)<1e-8})
    return {'accepted':bool(records) and all(p['passed'] for p in records),
            'criterion':'at least 3 distinct TRI6 elements across each sampled solid axial chord',
            'exhaustive_neck_certification':'UNQUALIFIED','records':records,
            'minimum_elements_across':min((p['elements_across'] for p in records),default=0)}
