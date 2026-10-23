"""C.1 audit sections independent of proposal event locations and decisions."""
import math
import numpy as np
import shapely
from shapely import LineString,Point
from ..validation.checks import line_parts,rings,select_probes


def oblique_width(g,xy,angle,phase,n=1024):
    d=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle))]);p=np.asarray(xy,float)
    endpoints=np.array([p-2*n*d,p+2*n*d]);line=LineString(endpoints)
    cut=line.intersection(g) if phase=='solid' else line.difference(g)
    parts=[part for part in line_parts(cut) if part.distance(Point(p))<=1e-10]
    if len(parts)!=1:return None
    part=parts[0]
    if any(np.linalg.norm(np.asarray(q)-endpoints[0])<1e-8 or np.linalg.norm(np.asarray(q)-endpoints[1])<1e-8 for q in [part.coords[0],part.coords[-1]]):return None
    return float(part.length)


def coordinate_width(g,xy,angle):
    d=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle))]);n=np.array([-d[1],d[0]]);p=np.asarray(xy,float);u=float(np.dot(p,n));v=float(np.dot(p,d));cross=[]
    for r in rings(g):
        a=np.asarray(r['xy']);us=a[:,0]*n[0]+a[:,1]*n[1];vs=a[:,0]*d[0]+a[:,1]*d[1]
        active=(np.minimum(us[:-1],us[1:])<=u)&(u<np.maximum(us[:-1],us[1:]));ids=np.flatnonzero(active)
        cross.extend((vs[ids]+(u-us[ids])*(vs[ids+1]-vs[ids])/(us[ids+1]-us[ids])).tolist())
    lower=max((q for q in cross if q<=v),default=None);upper=min((q for q in cross if q>=v),default=None)
    return upper-lower if lower is not None and upper is not None else None


def select_oblique(g,mask,count=48):
    candidates=select_probes(mask,maximum=192);selected=[];excluded=0;angles=[22.5,67.5,112.5,157.5]
    # Even/odd traversal interleaves both phases before reaching the cap.
    solid=[p for p in candidates if p['phase']=='solid'];void=[p for p in candidates if p['phase']=='void'];ordered=[]
    for i in range(max(len(solid),len(void))):
        for pp in [solid,void]:
            if i<len(pp):ordered.append(pp[i])
    for i,p in enumerate(ordered):
        angle=angles[i%4];width=oblique_width(g,p['xy'],angle,p['phase'],len(mask))
        if width is None or not 0<width<=16 or g.boundary.distance(Point(p['xy']))<=1e-10:excluded+=1;continue
        selected.append({'probe_id':f'oblique_{len(selected):03d}','xy':p['xy'],'phase':p['phase'],'angle_degrees':angle,'baseline_width':width,
                         'selection':'Source-only interleaved shortest axial-run midpoint candidates; complementary22.5deg directions, bounded width<=16.'})
        if len(selected)>=count:break
    return {'probes':selected,'source_exclusions':excluded,'maximum':count,'qualifying_width':16.}


def audit_oblique(a,b,definition,guard):
    records=[]
    for p in definition['probes']:
        before=oblique_width(a,p['xy'],p['angle_degrees'],p['phase']);after=oblique_width(b,p['xy'],p['angle_degrees'],p['phase'])
        delta=after-before if before is not None and after is not None else None
        row={**p,'before':before,'after':after,'delta':delta,'relative_delta':delta/before if delta is not None and before else None,
             'guarded_center':bool(guard.covers(Point(p['xy']))),'narrowed':delta is not None and delta < -1e-10,'defined':delta is not None}
        if row['narrowed']:
            old=coordinate_width(a,p['xy'],p['angle_degrees']);new=coordinate_width(b,p['xy'],p['angle_degrees'])
            row.update(coordinate_before=old,coordinate_after=new,coordinate_change=new-old if new is not None and old is not None else None,
                       coordinate_confirmation=old is not None and new is not None and abs(old-before)<=1e-10 and abs(new-after)<=1e-10)
        records.append(row)
    return {'method':'Independent source-selected oblique GEOS line-component intersections, not proposal event cuts; flagged widths also use separate coordinate interpolation.',
            'records':records,'narrowing_count':sum(p['narrowed'] for p in records),'undefined_count':sum(not p['defined'] for p in records),
            'maximum_narrowing':max([-p['delta'] for p in records if p['delta'] is not None]+[0.]),
            'all_flagged_confirmed':all(p.get('coordinate_confirmation',True) for p in records),
            'passed':all(p['defined'] and not p['narrowed'] for p in records),'exhaustive_width':'UNQUALIFIED'}
