"""Indexed sample-to-segment distances with explicit continuous error bounds."""
import numpy as np
import shapely
from shapely import STRtree
from ..manifold.contacts import polygon_rings


def line_components(geometry):
    if geometry.is_empty:return []
    if geometry.geom_type in ('LineString','LinearRing'):return [geometry]
    if hasattr(geometry,'geoms'):
        return [line for part in geometry.geoms for line in line_components(part)]
    return []


class BoundaryIndex:
    def __init__(self,geometry,spacing=.25,chunk=8192,role=None,boundary_input=False):
        self.spacing=spacing;self.chunk=chunk
        if not np.isfinite(spacing) or spacing<=0:raise ValueError('Boundary sample spacing must be positive.')
        if boundary_input:
            parts=[np.asarray(p.coords,dtype=float) for p in line_components(geometry)]
            roles=['local']*len(parts)
        else:
            selected=[r for r in polygon_rings(geometry) if role is None or r['role']==role]
            parts=[np.asarray(r['xy'],dtype=float) for r in selected];roles=[r['role'] for r in selected]
        self.parts=parts
        segments=[np.stack((p[:-1],p[1:]),axis=1) for p in parts if len(p)>1]
        coords=np.concatenate(segments) if segments else np.empty((0,2,2))
        segment_roles=np.concatenate([np.repeat(r,len(p)-1) for p,r in zip(parts,roles)]) if len(coords) else np.array([],dtype=str)
        if len(coords):
            keep=np.any(coords[:,0]!=coords[:,1],axis=1);coords=coords[keep];segment_roles=segment_roles[keep]
        self.segments=coords
        self.segment_roles=segment_roles
        self.keys=[tuple(sorted((tuple(a),tuple(b)))) for a,b in coords]
        self.key_set=set(self.keys)
        self.lines=shapely.linestrings(coords) if len(coords) else np.array([],dtype=object)
        self.tree=STRtree(self.lines)
        self._samples=None
        self.max_gap=0.0
        self.sample_segments=None

    @property
    def samples(self):
        if self._samples is None:
            pieces=[];owners=[]
            for i,(a,b) in enumerate(self.segments):
                length=float(np.linalg.norm(b-a));n=max(1,int(np.ceil(length/self.spacing)))
                self.max_gap=max(self.max_gap,length/n)
                pieces.append(a+(b-a)*np.linspace(0,1,n+1)[:,None])
                owners.append(np.full(n+1,i,dtype=np.int32))
            self._samples=np.concatenate(pieces) if pieces else np.empty((0,2))
            self.sample_segments=np.concatenate(owners) if owners else np.empty(0,dtype=np.int32)
        return self._samples

    def distances(self,points):
        if len(points)==0:return np.empty(0)
        if not len(self.lines):return np.full(len(points),np.nan)
        result=np.empty(len(points))
        for start in range(0,len(points),self.chunk):
            p=shapely.points(points[start:start+self.chunk])
            indices,dist=self.tree.query_nearest(p,return_distance=True,all_matches=False)
            block=np.empty(len(p));block[indices[0]]=dist;result[start:start+len(p)]=block
        return result


def directed_distance(source,target):
    points=source.samples
    matched=np.array([key in target.key_set for key in source.keys],dtype=bool)
    known_zero=matched[source.sample_segments]
    values=np.zeros(len(points));values[~known_zero]=target.distances(points[~known_zero])
    if len(values)==0 or not np.isfinite(values).all():
        return {'measured_max':None,'upper_bound':None,'samples':len(points),'reason':'Missing source or target boundary'}
    index=int(np.argmax(values));maximum=float(values[index])
    labels=source.segment_roles[source.sample_segments]
    return {'measured_max':maximum,'upper_bound':maximum+(source.max_gap/2 if not known_zero.all() else 0),
            'by_source_ring_role':{str(role):float(values[labels==role].max()) for role in sorted(set(labels))},
            'known_zero_samples_on_identical_segments':int(known_zero.sum()),
            'sample_gap':source.max_gap,'samples':len(points),'worst_sample_xy':points[index].tolist()}


def compare_boundaries(source,target,*,equal=False):
    if equal:
        return {'measured_hausdorff_lower':0.0,'continuous_hausdorff_upper':0.0,'exact_equality':True,
                'definition':'Set-equal boundaries; exact zero.'}
    a=directed_distance(source,target);b=directed_distance(target,source)
    lower=max(a['measured_max'],b['measured_max']) if a['measured_max'] is not None and b['measured_max'] is not None else None
    upper=max(a['upper_bound'],b['upper_bound']) if lower is not None else None
    return {'measured_hausdorff_lower':lower,'continuous_hausdorff_upper':upper,
            'source_to_target':a,'target_to_source':b,'exact_equality':False,
            'definition':'Bidirectional exact sampled point-to-segment maxima (lower bound); Lipschitz upper bound adds half maximum source sample gap. Not an exact continuous maximum.'}
