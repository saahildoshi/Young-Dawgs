"""Conservative subdivision proof for a pair of actual quadratic edges."""
import numpy as np
import shapely


def halves(p):
    quarter=.375*p[0]-.125*p[1]+.75*p[2]
    three_quarter=-.125*p[0]+.375*p[1]+.75*p[2]
    return np.array([p[0],p[2],quarter]),np.array([p[2],p[1],three_quarter])


def certify_separated(a,b,*,guard=1e-12,max_depth=20,max_cells=10000):
    """Cover the parameter square with positive chord-distance lower bounds.

    For each quadratic subarc, its exact maximal chord deviation is the
    midside bow. Triangle inequality supplies the separation bound. Only
    positive guarded bounds pass; crossings/touches/exhausted bounds HOLD.
    This is a floating-point calculation with an explicit guard, not formal
    interval arithmetic. No force/contact status is inferred from geometry.
    """
    a,b=np.asarray(a,dtype=float),np.asarray(b,dtype=float)
    if a.shape!=(3,2) or b.shape!=(3,2) or not np.isfinite([a,b]).all():raise ValueError('Require finite I,J,midside edge coordinates')
    guard=max(guard,128*np.finfo(float).eps*max(1,float(np.max(np.abs([a,b])))))
    pending=[(a,b,0)];cells=0;depth=0;minimum=np.inf
    while pending:
        left,right,d=pending.pop();cells+=1;depth=max(depth,d)
        bow_a=float(np.linalg.norm(left[2]-(left[0]+left[1])/2));bow_b=float(np.linalg.norm(right[2]-(right[0]+right[1])/2))
        distance=float(shapely.distance(shapely.LineString(left[:2]),shapely.LineString(right[:2])))
        lower=distance-bow_a-bow_b-guard
        if lower>0:minimum=min(minimum,lower);continue
        if d>=max_depth or cells>=max_cells or max(bow_a,bow_b)<=guard/2:
            return {'passed':False,'status':'INTERSECTING_TOUCHING_OR_UNRESOLVED','processed_cells':cells,'maximum_depth':depth,'guard_mm':guard,'minimum_certified_separation_mm':None}
        if bow_a>=bow_b:
            first,second=halves(left);pending.extend([(first,right,d+1),(second,right,d+1)])
        else:
            first,second=halves(right);pending.extend([(left,first,d+1),(left,second,d+1)])
    return {'passed':True,'status':'CERTIFIED_POSITIVE_QUADRATIC_SEPARATION','processed_cells':cells,'maximum_depth':depth,'guard_mm':guard,'minimum_certified_separation_mm':float(minimum)}
