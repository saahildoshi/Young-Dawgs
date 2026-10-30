"""Spatial-index screening of actual quadratic exposed boundaries."""
import math
import numpy as np
import shapely


def trace_loops(boundary):
    boundary=np.asarray(boundary,dtype=np.int64)
    outgoing={int(e[0]):i for i,e in enumerate(boundary)}
    if len(outgoing)!=len(boundary):raise ValueError('Nonmanifold outgoing boundary vertex')
    visited=np.zeros(len(boundary),dtype=bool);loops=[]
    for start in range(len(boundary)):
        if visited[start]:continue
        loop=[];current=start
        while not visited[current]:
            visited[current]=True;loop.append(current)
            nxt=int(boundary[current,1])
            if nxt not in outgoing:raise ValueError('Open boundary loop')
            current=outgoing[nxt]
        if current!=start:raise ValueError('Boundary loop merges into another loop')
        loops.append(np.array(loop,dtype=np.int64))
    return loops


def quadratic_segments(coordinates,boundary,tolerance=1e-6,max_subdivisions=64):
    p=np.asarray(coordinates)[boundary]
    bow=np.linalg.norm(p[:,2]-(p[:,0]+p[:,1])/2,axis=1)
    subdivisions=np.maximum(1,np.ceil(np.sqrt(bow/tolerance)).astype(int))
    subdivisions=np.minimum(max_subdivisions,subdivisions)
    actual_error=bow/subdivisions**2
    segments=[];owners=[]
    for n in np.unique(subdivisions):
        ids=np.flatnonzero(subdivisions==n);t=np.linspace(0,1,int(n)+1)
        shape=np.column_stack([(1-t)*(1-2*t),t*(2*t-1),4*t*(1-t)])
        xy=np.einsum('sn,bnd->bsd',shape,p[ids])
        segments.append(np.stack([xy[:,:-1],xy[:,1:]],axis=2).reshape(-1,2,2))
        owners.append(np.repeat(ids,n))
    return np.concatenate(segments),np.concatenate(owners),actual_error


def signed_quadratic_edge_areas(coordinates,boundary):
    p=np.asarray(coordinates)[boundary];c=p[:,0];a=2*(p[:,0]+p[:,1]-2*p[:,2]);b=4*p[:,2]-3*p[:,0]-p[:,1]
    cross=lambda x,y:x[:,0]*y[:,1]-x[:,1]*y[:,0]
    return .5*(cross(c,b)+cross(c,a)+cross(b,a)/3)


def screen(coordinates,boundary,groups,*,original=None,tolerance=1e-6,record_limit=32):
    """Conservative diagnostic: crossings/uncertain near contact are not PASS.

    Exact quadratic chord error is recorded. Connected original endpoint-only
    intersections are excluded; adjacent edges crossing elsewhere are retained.
    A zero finding is a bounded approximation screen, not an exact global proof.
    """
    coordinates=np.asarray(coordinates);boundary=np.asarray(boundary);groups=np.asarray(groups)
    loops=trace_loops(boundary)
    xy,owners,error=quadratic_segments(coordinates,boundary,tolerance)
    lines=shapely.linestrings(xy);tree=shapely.STRtree(lines)
    suspicious=[];tested=0;minimum_near=np.inf
    for offset in range(0,len(lines),20000):
        pairs=tree.query(lines[offset:offset+20000],predicate='dwithin',distance=2*max(tolerance,float(error.max())))
        i,j=pairs;i=i+offset;keep=(i<j)&(owners[i]!=owners[j]);i,j=i[keep],j[keep]
        if not len(i):continue
        left,right=boundary[owners[i]],boundary[owners[j]]
        shared=(left[:,0]==right[:,0])|(left[:,0]==right[:,1])|(left[:,1]==right[:,0])|(left[:,1]==right[:,1])
        intersection=shapely.intersection(lines[i],lines[j]);intersects=~shapely.is_empty(intersection)
        common=np.where((left[:,0]==right[:,0])|(left[:,0]==right[:,1]),left[:,0],left[:,1])
        endpoint_only=shared&intersects&(shapely.hausdorff_distance(intersection,shapely.points(coordinates[common]))<=2*tolerance)
        # Neighboring pieces within the same connected corner neighborhood are
        # ignored only for near-distance queries; proper off-vertex crossings remain.
        keep=~endpoint_only&(~shared|intersects)
        i,j=i[keep],j[keep];intersects=intersects[keep]
        if not len(i):continue
        distances=shapely.distance(lines[i],lines[j]);minimum_near=min(minimum_near,float(distances.min()))
        tested+=len(i)
        for k in range(min(len(i),max(0,record_limit-len(suspicious)))):
            suspicious.append({'edge_a':int(owners[i[k]]),'edge_b':int(owners[j[k]]),
                'sampled_intersection':bool(intersects[k]),'sampled_distance_mm':float(distances[k]),
                'quadratic_chord_error_bound_mm':float(error[owners[i[k]]]+error[owners[j[k]]]),
                'classification':'POTENTIAL_UNMODELED_CROSSING' if intersects[k] else 'NEAR_CONTACT_REQUIRES_VERIFICATION'})
    areas=signed_quadratic_edge_areas(coordinates,boundary)
    original_areas=signed_quadratic_edge_areas(original,boundary) if original is not None else areas
    pores=[];inverted=[]
    for number,loop in enumerate(loops):
        area=float(areas[loop].sum());before=float(original_areas[loop].sum())
        if area*before<=0:inverted.append(number)
        if np.all(groups[loop]=='pore'):
            pores.append({'mesh_loop_id':number,'signed_area_mm2':area,'initial_signed_area_mm2':before,
                          'area_ratio':area/before if before else None})
    uncertain_edges=int(np.sum(error>tolerance*(1+1e-12)))
    valid=not suspicious and not inverted and not uncertain_edges
    return {'status':'PASS_BOUNDED_QUADRATIC_BOUNDARY_SCREEN' if valid else 'OVERLAP_OR_NEAR_CONTACT_UNQUALIFIED',
        'passed':valid,'original_edges':len(boundary),'subdivided_segments':len(lines),'boundary_loops':len(loops),
        'pore_loops':len(pores),'tolerance_mm':tolerance,'maximum_exact_chord_error_bound_mm':float(error.max()),
        'edges_exceeding_requested_tolerance':uncertain_edges,'suspicious_pair_count':tested,
        'examples':suspicious,'orientation_inverted_loops':inverted,'pore_area_records':pores,
        'minimum_area_ratio':min((p['area_ratio'] for p in pores),default=None),
        'minimum_separation_scope':'Only near pairs inside twice chord-error tolerance are queried; no exhaustive opposing-wall minimum claimed',
        'minimum_near_sampled_distance_mm':float(minimum_near) if np.isfinite(minimum_near) else None,
        'limitation':'Conservative spatial-index polygonal screen with exact quadratic chord-deviation bounds; uncertain near-contact points need separate native-contact/exact-curve verification.'}
