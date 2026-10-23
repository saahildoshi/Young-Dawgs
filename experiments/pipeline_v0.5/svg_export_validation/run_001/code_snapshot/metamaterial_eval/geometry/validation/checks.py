"""Layered geometry checks independent of the guarded DP and its certificates.

GEOS remains a shared dependency for parsing, spatial predicates and Booleans.
Coordinates, incidence, translated shoelace and sample selection are separate.
"""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
import shapely
from shapely import Polygon, MultiPolygon, LineString, Point, STRtree, box

ALLOWANCE = 1e-10


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def authenticate(path, expected):
    if not expected or digest(path) != expected:
        raise ValueError('Missing or tampered provenance: '+str(path))


def polygons(g):
    if g.geom_type == 'Polygon': return [g]
    if hasattr(g, 'geoms'): return [p for part in g.geoms for p in polygons(part)]
    return []


def rings(g):
    return [{'polygon':i, 'role':role, 'xy':list(map(list, r.coords))}
            for i,p in enumerate(polygons(g)) for role,r in
            [('shell',p.exterior)]+[('hole',h) for h in p.interiors]]


def signed_area(xy):
    a=np.asarray(xy,dtype=float); a=a-a[0]
    return math.fsum(float(x[0]*y[1]-x[1]*y[0]) for x,y in zip(a[:-1],a[1:]))/2


def coordinate_geometry(records):
    parts=[]
    for i in sorted(set(r['polygon'] for r in records)):
        selected=[r for r in records if r['polygon']==i]
        shell=[r for r in selected if r['role']=='shell']; holes=[r['xy'] for r in selected if r['role']=='hole']
        if len(shell)!=1: raise ValueError('Ambiguous ring ownership')
        for r in selected:
            xy=np.asarray(r['xy'],float)
            if len(xy)<4 or not np.isfinite(xy).all() or not np.array_equal(xy[0],xy[-1]):
                raise ValueError('Malformed/open/nonfinite coordinate ring')
        parts.append(Polygon(shell[0]['xy'],holes))
    if not parts:raise ValueError('Missing polygon records')
    return parts[0] if len(parts)==1 else MultiPolygon(parts)


def serialization_check(g, folder=None, name='geometry', reloaded=None):
    records=rings(g); payload=shapely.to_wkb(g,byte_order=1)
    q=shapely.from_wkb(payload) if reloaded is None else reloaded
    rebuilt=coordinate_geometry(records)
    area=math.fsum((1 if r['role']=='shell' else -1)*abs(signed_area(r['xy'])) for r in records)
    oriented=[{'role':r['role'],'polygon':r['polygon'],'signed_area':signed_area(r['xy'])} for r in records]
    exact_coordinates=records==rings(q) and records==rings(rebuilt)
    if folder is not None:
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        (folder/(name+'.wkb')).write_bytes(payload)
        (folder/(name+'.coordinates.json')).write_text(json.dumps(records,separators=(',',':'))+'\n')
        persisted=json.loads((folder/(name+'.coordinates.json')).read_text())
        exact_coordinates=exact_coordinates and rings(coordinate_geometry(persisted))==records
    return {'passed':bool(exact_coordinates and g.equals(q) and g.equals(rebuilt) and abs(area-g.area)<=ALLOWANCE),
            'coordinate_order_orientation_precision_preserved':exact_coordinates,
            'wkb_sha256':hashlib.sha256(payload).hexdigest(),'shoelace_area':area,'geos_area':g.area,
            'area_discrepancy':area-g.area,'components':len(polygons(g)),
            'rings':len(records),'holes':sum(r['role']=='hole' for r in records),
            'vertices':sum(len(r['xy'])-1 for r in records),'orientations':oriented}


def independent_raster(g,n):
    """Point predicates, not the frozen scanline algorithm. Closed solid set."""
    shapely.prepare(g); out=np.zeros((n,n),np.uint8); ties=0
    for row in range(0,n,32):
        y,x=np.mgrid[row:min(n,row+32),0:n];x=x+.5;y=y+.5
        interior=shapely.contains_xy(g,x,y); closed=shapely.intersects_xy(g,x,y)
        ties+=int(np.count_nonzero(closed & ~interior));out[row:row+32]=closed
    return out,ties


def raster_metrics(mask,other):
    a=mask.astype(bool);b=other.astype(bool);lab,num=ndi.label(b)
    sizes=np.bincount(lab.ravel())[1:];den=int(np.count_nonzero(a|b))
    return {'source_solid_pixels':int(a.sum()),'reconstructed_solid_pixels':int(b.sum()),
            'false_positive':int(np.count_nonzero(b&~a)),'false_negative':int(np.count_nonzero(a&~b)),
            'xor':int(np.count_nonzero(a!=b)),'iou':float(np.count_nonzero(a&b)/den) if den else 1.,
            'components':int(num),'largest_component_fraction':float(max(sizes,default=0)/b.sum()) if b.any() else 0.,
            'horizontal_percolation':bool(set(lab[:,0])&set(lab[:,-1])-{0}),
            'vertical_percolation':bool(set(lab[0,:])&set(lab[-1,:])-{0})}


def boundary_integrity(g):
    rr=rings(g); incidents=Counter(); edges=Counter(); zero=0
    lines=[]; bounds=[]
    for r in rr:
        xy=r['xy'];line=LineString(xy);lines.append(line);bounds.append(r['role'])
        for a,b in zip(xy[:-1],xy[1:]):
            a,b=tuple(a),tuple(b);incidents[a]+=1;incidents[b]+=1
            edges[tuple(sorted((a,b)))]+=1;zero+=int(a==b)
    bad=[list(p) for p,d in incidents.items() if d!=2]
    cross=[]
    if lines:
        tree=STRtree(lines)
        for i,line in enumerate(lines):
            cross.extend([i,int(j)] for j in tree.query(line,predicate='intersects') if j>i)
    simple=all(line.is_simple for line in lines)
    return {'passed':bool(g.is_valid and simple and not bad and not cross and not zero and not any(v>1 for v in edges.values())),
            'ogc_valid':bool(g.is_valid),'simple_rings':simple,'nondegree_two_vertices':bad,
            'cross_ring_intersections':cross,'zero_edges':zero,'duplicate_edges':sum(v-1 for v in edges.values() if v>1),
            'components':len(polygons(g)),'holes':sum(len(p.interiors) for p in polygons(g)),
            'exterior_length':math.fsum(p.exterior.length for p in polygons(g)),
            'internal_length':math.fsum(h.length for p in polygons(g) for h in p.interiors),
            'minimum_component_area':min((p.area for p in polygons(g)),default=0.)}


def area_difference(a,b):
    added=b.difference(a).area; removed=a.difference(b).area
    direct=a.symmetric_difference(b).area
    return {'reference_area':a.area,'candidate_area':b.area,'net_area':b.area-a.area,
            'added':added,'removed':removed,'symmetric':direct,'relative_symmetric':direct/a.area if a.area else None,
            'boolean_identity_error':direct-(added+removed),
            'net_identity_error':(b.area-a.area)-(added-removed)}


def region_correspondence(old,new,include_shapes=True):
    """Positive-area graph plus reciprocal representative-point identities.

    Exact anchor loss is reported separately; robust bijection requires overlap
    and reciprocal anchors to agree rather than matching by similar area.
    """
    old=list(old);new=list(new);tree=STRtree(new);rows=[];reverse=[[] for _ in new]
    for i,p in enumerate(old):
        matches=[]
        for j in tree.query(p,predicate='intersects'):
            if p.intersection(new[j]).area>0:matches.append(int(j));reverse[j].append(i)
        q=new[matches[0]] if len(matches)==1 else None
        anchor=bool(q is not None and q.covers(p.representative_point()) and p.covers(q.representative_point()))
        row={'source_id':i,'candidate_ids':matches,'reciprocal_anchors':anchor,
             'source_area':p.area,'candidate_area':q.area if q is not None else None,
             'relative_area_distortion':abs(q.area-p.area)/p.area if q is not None and p.area else None}
        if q is not None and include_shapes:
            row.update(source_perimeter=p.length,candidate_perimeter=q.length,
                       symmetric_area=p.symmetric_difference(q).area,
                       source_covers_candidate=bool(p.covers(q)),candidate_covers_source=bool(q.covers(p)),
                       intersection_area=p.intersection(q).area,
                       boundary_sampled_hausdorff=float(shapely.hausdorff_distance(p.boundary,q.boundary,densify=.5)))
        rows.append(row)
    passed=len(old)==len(new) and all(len(r['candidate_ids'])==1 and r['reciprocal_anchors'] for r in rows) and all(len(v)==1 for v in reverse)
    return {'passed':bool(passed),'source_count':len(old),'candidate_count':len(new),'records':rows,'reverse_matches':reverse,
            'ambiguous_or_missing':sum(len(r['candidate_ids'])!=1 or not r['reciprocal_anchors'] for r in rows)}


def topology(a,b,n=1024):
    oldholes=[Polygon(h) for p in polygons(a) for h in p.interiors]
    newholes=[Polygon(h) for p in polygons(b) for h in p.interiors]
    domain=box(0,0,n,n)
    holes=region_correspondence(oldholes,newholes)
    solid=region_correspondence(polygons(a),polygons(b),False)
    oldvoid=polygons(domain.difference(a));newvoid=polygons(domain.difference(b))
    void=region_correspondence(oldvoid,newvoid,False)
    sides=[LineString([(0,0),(n,0)]),LineString([(n,0),(n,n)]),LineString([(n,n),(0,n)]),LineString([(0,n),(0,0)])]
    outer=[]
    for row in void['records']:
        i=row['source_id'];j=row['candidate_ids'][0] if len(row['candidate_ids'])==1 else None
        before=[bool(oldvoid[i].intersects(s)) for s in sides]
        after=[bool(newvoid[j].intersects(s)) for s in sides] if j is not None else None
        outer.append({'source_void':i,'before_domain_sides':before,'after_domain_sides':after,'preserved':before==after})
    return {'passed':bool(holes['passed'] and solid['passed'] and void['passed'] and all(r['preserved'] for r in outer)),
            'holes':holes,'solid':solid,'void':void,'exterior_incidence':outer,
            'limitation':'Component/side incidence does not certify unchanged channel width.'}


def line_parts(g):
    if g.is_empty:return []
    if g.geom_type in ('LineString','LinearRing'):return [g]
    if hasattr(g,'geoms'):return [p for c in g.geoms for p in line_parts(c)]
    return []


def directed_bound(a,b,spacing=.025):
    # Changes are computed as line-set difference, independent of producer's
    # source-index/chord certificates. Shared segments have distance exactly0.
    changed=a.difference(b)
    if changed.is_empty:return {'lower':0.,'upper':0.,'samples':0,'gap':0.,'worst_xy':None}
    target=np.concatenate([np.stack((np.asarray(p.coords)[:-1],np.asarray(p.coords)[1:]),axis=1) for p in line_parts(b)])
    tree=STRtree(shapely.linestrings(target)); maximum=0.;worst=None;count=0;gap=0.
    for part in line_parts(changed):
        xy=np.asarray(part.coords)
        for start in range(0,len(xy)-1,256):
            samples=[]
            for u,v in zip(xy[start:-1][:256],xy[start+1:][:256]):
                length=float(np.linalg.norm(v-u));steps=max(1,math.ceil(length/spacing));gap=max(gap,length/steps)
                samples.append(u+(v-u)*np.linspace(0,1,steps+1)[:,None])
            if not samples:continue
            samples=np.concatenate(samples);pts=shapely.points(samples)
            ix,dist=tree.query_nearest(pts,return_distance=True,all_matches=False)
            k=int(np.argmax(dist));d=float(dist[k]);count+=len(dist)
            if d>maximum:maximum=d;worst=samples[ix[0,k]].tolist()
    return {'lower':maximum,'upper':maximum+gap/2,'samples':count,'gap':gap,'worst_xy':worst}


def boundary_distance(a,b,spacing=.025):
    ab=directed_bound(a.boundary,b.boundary,spacing);ba=directed_bound(b.boundary,a.boundary,spacing)
    return {'lower':max(ab['lower'],ba['lower']),'upper':max(ab['upper'],ba['upper']),
            'source_to_candidate':ab,'candidate_to_source':ba,'sample_spacing':spacing,
            'method':'Endpoints and gap<=spacing on changed line-set pieces; exact nearest segments; distance is1-Lipschitz, add gap/2. Floating GEOS, no interval claim.'}


def area_gates(a,b,limits):
    d=area_difference(a,b)
    return {key:d[field]<=a.area*limits[limit]+limits['area_allowance'] for key,field,limit in
            [('added','added','max_added_fraction'),('removed','removed','max_removed_fraction'),('symmetric','symmetric','max_symmetric_fraction')]}


def probe_width(g,xy,axis,phase,n):
    x,y=xy
    line=LineString([(0,y),(n,y)]) if axis==0 else LineString([(x,0),(x,n)])
    part=line.intersection(g) if phase=='solid' else line.difference(g)
    pieces=[p for p in line_parts(part) if p.distance(Point(xy))<=ALLOWANCE]
    return float(pieces[0].length) if len(pieces)==1 else None


def select_probes(mask,maximum=96):
    rows=[];n=len(mask)
    for phase in ['solid','void']:
        binary=(mask==1) if phase=='solid' else (mask==0)
        candidates=[]
        for axis in [0,1]:
            arr=binary if axis==0 else binary.T
            for j in range(n):
                edges=np.flatnonzero(np.diff(np.r_[False,arr[j],False].astype(int)))
                for l,r in zip(edges[::2],edges[1::2]):
                    if 1<=r-l<=16 and 0<l and r<n:
                        xy=[float((l+r)/2),j+.5] if axis==0 else [j+.5,float((l+r)/2)]
                        candidates.append((int(r-l),j,int(l),axis,xy))
        selected=[]
        for width,j,l,axis,xy in sorted(candidates,key=lambda t:t[:4]):
            if all((xy[0]-p['xy'][0])**2+(xy[1]-p['xy'][1])**2>=64 for p in selected):
                selected.append({'phase':phase,'xy':xy,'axis':axis,'source_pixel_run':width})
                if len(selected)>=maximum:break
        rows.extend(selected)
    return rows


def feature_audit(a,b,mask,guard,probes,registered=None):
    from skimage.morphology import medial_axis
    # This medial-axis definition is separate from B2 skeletonize/PCA. rng
    # fixed to0; coverage denominator explicitly raster support, not all necks.
    skeleton,edt=medial_axis(mask.astype(bool),return_distance=True,rng=0)
    yy,xx=np.nonzero(skeleton & (2*edt<=8));pts=shapely.points(np.column_stack((xx+.5,yy+.5)))
    covered=shapely.covers(guard,pts) if len(pts) else np.array([],bool)
    diff=a.symmetric_difference(b);bc=a.boundary.symmetric_difference(b.boundary)
    records=[]
    for p in probes:
        before=probe_width(a,p['xy'],p['axis'],p['phase'],len(mask));after=probe_width(b,p['xy'],p['axis'],p['phase'],len(mask))
        records.append({**p,'before':before,'after':after,'delta':after-before if before is not None and after is not None else None,
                        'guarded_center':bool(guard.covers(Point(p['xy']))),
                        'narrowed':before is not None and after is not None and after<before-ALLOWANCE})
    local_solid=diff.intersection(guard).area; local_boundary=bc.intersection(guard).length
    repairs=[]
    for r in (registered or {}).get('repairs',[]):
        x,y=r['xy'];window=box(x-.5,y-.5,x+.5,y+.5)
        def clearance(g):
            lines=shapely.line_merge(g.boundary.intersection(window));parts=line_parts(lines)
            return float(parts[0].distance(parts[1])) if len(parts)==2 else None
        first=clearance(a);last=clearance(b)
        repairs.append({'contact_id':r['contact_id'],'xy':[x,y],'original_contact_type':r['original_contact_type'],
                        'before_clearance':first,'after_clearance':last,'local_difference':diff.intersection(window).area,
                        'local_boundary_difference':bc.intersection(window).length,
                        'preserved':first is not None and last is not None and last>=first-ALLOWANCE and diff.intersection(window).is_empty})
    near=diff.buffer(1).intersection(a.boundary).difference(guard)
    return {'guard_boundary_fraction':float(a.boundary.intersection(guard).length/a.boundary.length),
            'potentially_narrow_medial_pixels':len(pts),'guarded_narrow_medial_pixels':int(covered.sum()),
            'guarded_narrow_fraction':float(covered.mean()) if len(pts) else None,
            'uncovered_narrow_xy':np.column_stack((xx[~covered]+.5,yy[~covered]+.5)).tolist(),
            'independent_probes':records,'narrowed_probes':sum(p['narrowed'] for p in records),
            'undefined_probes':sum(p['before'] is None or p['after'] is None for p in records),
            'guard_solid_difference':local_solid,'guard_boundary_difference':local_boundary,
            'guard_exact':bool(local_solid==0 and local_boundary==0),'repairs':repairs,
            'unguarded_boundary_near_change_length':near.length,
            'exhaustive_continuous_width_certification':'UNQUALIFIED',
            'interpretation':'Finite axis chords and raster medial support; a shorter axial chord is a geometric flag, not a mechanical neck strength estimate.'}


def provenance_check(record):
    required=('source_path','source_sha256','parameters','seed','resolution','geometry_hashes','algorithm_versions')
    return all(k in record and record[k] is not None for k in required) and record.get('resolution')==1024 and bool(record.get('geometry_hashes'))


def acceptance(gates,feature_flags=0):
    failed=sorted(k for k,v in gates.items() if not v)
    return {'hard_gate_pass':not failed,'failed_gates':failed,
            'scientific_status':'HOLD' if failed or feature_flags else 'PASS_SAMPLED_DOMAIN',
            'production_policy':'HOLD_UNQUALIFIED','cad_manufacturing':'UNQUALIFIED'}
