"""Bound contact geometry to actual positive-pressure nodal constraints."""
import numpy as np
import shapely
from .quadratic_separation import halves,certify_separated


def controls(edge):
    return np.array([edge[0],edge[1],2*edge[2]-(edge[0]+edge[1])/2])


def certify_localized(a,b,centers,*,radius=5e-6,guard=1e-12,max_depth=44,max_cells=100000):
    """Cover every possible intersection by a ball of diameter <= native pen limit.

    A quadratic lies in its Bezier control hull. Positive chord-distance
    bounds discard separated cells; a subarc hull inside a constrained-node
    ball covers all potential intersections in that cell. Every remaining
    cell must be split or held. Explicit floating-point guard, no inferred
    pressure/force and no exemption for a crossing outside these balls.
    """
    a,b=np.asarray(a,float),np.asarray(b,float);centers=np.asarray(centers,float).reshape(-1,2)
    if a.shape!=(3,2) or b.shape!=(3,2) or not np.isfinite([a,b]).all() or not np.isfinite(centers).all() or radius<=0:raise ValueError('Invalid contact geometry')
    guard=max(guard,128*np.finfo(float).eps*max(1,float(np.max(np.abs([a,b])))))
    stack=[(a,b,0)];cells=0;covered=0;depth=0
    while stack:
        left,right,d=stack.pop();cells+=1;depth=max(depth,d)
        bow_a=float(np.linalg.norm(left[2]-(left[0]+left[1])/2));bow_b=float(np.linalg.norm(right[2]-(right[0]+right[1])/2))
        distance=float(shapely.distance(shapely.LineString(left[:2]),shapely.LineString(right[:2])))
        if distance-bow_a-bow_b-guard>0:continue
        lc,rc=controls(left),controls(right)
        if any(min(np.linalg.norm(lc-c,axis=1).max(),np.linalg.norm(rc-c,axis=1).max())+guard<radius for c in centers):
            covered+=1;continue
        if d>=max_depth or cells>=max_cells:
            return {'passed':False,'status':'CONTACT_REGION_OUTSIDE_NATIVE_NODE_BALLS_OR_UNRESOLVED','cells':cells,'maximum_depth':depth,'guard_mm':guard,'radius_mm':radius}
        size_a=float(np.linalg.norm(lc[:,None]-lc[None,:],axis=2).max());size_b=float(np.linalg.norm(rc[:,None]-rc[None,:],axis=2).max())
        if max(size_a,size_b)<=guard:return {'passed':False,'status':'UNRESOLVED_GUARDED_CONTACT','cells':cells,'guard_mm':guard,'radius_mm':radius}
        if size_a>=size_b:
            first,second=halves(left);stack.extend([(first,right,d+1),(second,right,d+1)])
        else:
            first,second=halves(right);stack.extend([(left,first,d+1),(left,second,d+1)])
    return {'passed':True,'status':'ALL_POTENTIAL_CONTACT_LOCALIZED_TO_NATIVE_NODE_BALLS' if covered else 'CERTIFIED_POSITIVE_SEPARATION','cells':cells,'maximum_depth':depth,'contact_cells':covered,'guard_mm':guard,'radius_mm':radius}


def explain_nodal_pairs(overlap,eids,fields,mesh,xy,*,radius=5e-6):
    if overlap['suspicious_pair_count']!=len(overlap['examples']):raise ValueError('Truncated boundary candidates')
    if not overlap['examples']:return []
    xy=np.asarray(xy);by_eid={int(eid):edge for edge,eid in enumerate(eids) if eid>0};constraints={}
    for edge,row in fields.items():
        if row[1]<2:continue
        for end in [0,1]:
            target=by_eid.get(int(row[8+end]));node=int(mesh.boundary[edge,end])
            if target is not None and row[2+end]>0:
                constraints.setdefault(node,[]).append({'node':node,'source_edge':edge,'target_edge':target,'native_pressure_MPa':float(row[2+end])})
    cache={};explained=[];unexplained=[]
    for pair in overlap['examples']:
        a,b=pair['edge_a'],pair['edge_b'];key=tuple(sorted([a,b]))
        if key in cache:explained.append({**pair,**cache[key]});continue
        fa,fb=fields.get(a),fields.get(b)
        direct_a=fa is not None and fa[1]>=2 and eids[b]>0 and eids[b] in fa[8:10] and max(fa[2:5])>0
        direct_b=fb is not None and fb[1]>=2 and eids[a]>0 and eids[a] in fb[8:10] and max(fb[2:5])>0
        if direct_a or direct_b:
            detail={'explanation':'DIRECT_NATIVE_ENGAGED_TARGET_FACET_LINK','native_element_a':int(eids[a]),'native_element_b':int(eids[b]),'native_target_link_a_to_b':bool(direct_a),'native_target_link_b_to_a':bool(direct_b)}
            cache[key]=detail;explained.append({**pair,**detail});continue
        pa,pb=xy[mesh.boundary[a]],xy[mesh.boundary[b]]
        separated=certify_separated(pa,pb)
        if separated['passed']:
            detail={'explanation':'GUARDED_POSITIVE_QUADRATIC_SEPARATION_NO_CONTACT_INFERRED','geometry_proof':separated};cache[key]=detail;explained.append({**pair,**detail});continue
        allowed=[]
        for current,other in [(a,b),(b,a)]:
            for node in mesh.boundary[current,:2]:
                for link in constraints.get(int(node),[]):
                    target=link['target_edge']
                    common=np.intersect1d(mesh.boundary[target,:2],mesh.boundary[other,:2])
                    if target==other or any(np.linalg.norm(xy[int(node)]-xy[int(vertex)])+1e-12<radius for vertex in common):allowed.append(link)
        centers=np.array([xy[c['node']] for c in allowed]).reshape(-1,2)
        proof=certify_localized(pa,pb,centers,radius=radius) if len(centers) else {'passed':False,'status':'NO_NATIVE_ENDPOINT_PRESSURE_TARGET_CONSTRAINT'}
        detail={'explanation':'NATIVE_POSITIVE_PRESSURE_NODE_AND_BOUNDED_CONTACT_NEIGHBORHOOD','native_constraint_links':[{**c,'node':c['node']+1,'native_source_element':int(eids[c['source_edge']]),'native_target_element':int(eids[c['target_edge']])} for c in allowed],'geometry_proof':proof}
        if proof['passed']:cache[key]=detail;explained.append({**pair,**detail})
        else:unexplained.append({**pair,**detail})
    if unexplained:raise ValueError('Nodal boundary contact not geometrically localized to actual native constraints: '+str(unexplained[:2]))
    return explained
