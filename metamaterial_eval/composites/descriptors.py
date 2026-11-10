"""Finite-field composite descriptors with explicit object-identification limits.

Lengths are pixels. Axial angles are counterclockwise from image+x, with y up,
modulo180. Touching/branched fiber unions are not assigned physical fiber IDs.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial.distance import cdist
from skimage.measure import regionprops
from skimage.morphology import skeletonize
from metamaterial_eval.metrics import compute_basic_metrics,compute_s2_correlation,compute_lineal_path

FOUR=ndi.generate_binary_structure(2,1)


def validate(a):
    if not isinstance(a,np.ndarray) or a.shape!=(256,256) or a.dtype!=np.uint8:raise ValueError('Expected256x256 uint8')
    if not np.isin(a,[0,1]).all():raise ValueError('Unknown phase label;0=matrix,1=reinforcement')
    return a


def axial_error(a,b):return float(abs((a-b+90)%180-90))


def directional_s2(a,r,axis):
    if not 0<=r<a.shape[axis]:raise ValueError('Lag outside finite image')
    if r==0:return float(np.mean(a))
    lo=[slice(None)]*2;hi=lo.copy();lo[axis]=slice(None,-r);hi[axis]=slice(r,None)
    return float(np.mean(a[tuple(lo)].astype(float)*a[tuple(hi)]))


def skeleton_geometry(mask):
    sk=skeletonize(mask);p=np.pad(sk,1);deg=np.zeros_like(sk,dtype=int);length=0.;h,w=sk.shape
    for dy in [-1,0,1]:
        for dx in [-1,0,1]:
            if not(dx or dy):continue
            link=sk&p[1+dy:1+dy+h,1+dx:1+dx+w]
            # Remove diagonal shortcuts where an orthogonal path already exists.
            if dx and dy:link&=~(p[1:1+h,1+dx:1+dx+w]|p[1+dy:1+dy+h,1:1+w])
            deg+=link;length+=float(link.sum())*np.hypot(dx,dy)/2
    endpoints=np.argwhere(sk&(deg==1));branched=bool(np.any(sk&(deg>2)))
    chord=float(np.linalg.norm(endpoints[0]-endpoints[1])) if len(endpoints)==2 else 0
    return {'branched':branched,'endpoints':len(endpoints),'skeleton_length_px':length,'tortuosity':length/chord if chord>0 and not branched else None}


def describe(a,family):
    validate(a)
    if family not in ['particle','fiber']:raise ValueError('Unknown composite family')
    rein=compute_basic_metrics(a);matrix=compute_basic_metrics(1-a);labels,n=ndi.label(a,FOUR);props=regionprops(labels)
    edge=set(np.unique(np.r_[labels[0],labels[-1],labels[:,0],labels[:,-1]]))-{0}
    complete=[p for p in props if p.label not in edge]
    # Digital interface: internal phase-changing4-neighbor pixel edges / image area.
    interface=(np.count_nonzero(a[:,1:]!=a[:,:-1])+np.count_nonzero(a[1:]!=a[:-1]))/a.size
    centers=np.array([p.centroid for p in complete]);nn=[]
    if len(centers)>1:
        distances=cdist(centers,centers);np.fill_diagonal(distances,np.inf);nn=distances.min(axis=1).tolist()
    diameters=[float(p.equivalent_diameter_area) for p in complete]
    aspects=[float(p.axis_major_length/p.axis_minor_length) for p in complete if p.axis_minor_length>0]
    data={'family':family,'fraction':float(a.mean()),'object_count':int(n),'number_density_per_pixel2':n/a.size,'matrix_lcc':matrix['largest_component_fraction'],
        'matrix_percolates_x':matrix['percolates_x'],'matrix_percolates_y':matrix['percolates_y'],'reinforcement_percolates_x':rein['percolates_x'],
        'reinforcement_percolates_y':rein['percolates_y'],'interface_density':float(interface),'boundary_censored_objects':len(edge),'complete_objects':len(complete),
        'diameter_mean_px':float(np.mean(diameters)) if diameters else None,'diameter_std_px':float(np.std(diameters)) if diameters else None,
        'aspect_mean':float(np.mean(aspects)) if aspects else None,'nearest_neighbor_mean_px':float(np.mean(nn)) if nn else None,
        'nearest_neighbor_cv':float(np.std(nn)/np.mean(nn)) if nn and np.mean(nn)>0 else None,'diameters_px':diameters,'nearest_neighbors_px':nn,
        'S2_x_8':directional_s2(a,8,1),'S2_y_8':directional_s2(a,8,0),
        'S2_radial':compute_s2_correlation(a,16)['s2'].tolist(),'lineal_x':compute_lineal_path(a,16)['l_x'].tolist(),
        'lineal_y':compute_lineal_path(a,16)['l_y'].tolist()}
    if family=='fiber':
        angles=[];weights=[];spans=[];widths=[];tort=[];branched=0;ambiguous=0
        for p in complete:
            geom=skeleton_geometry(p.image);branched+=int(geom['branched'])
            if geom['branched'] or geom['endpoints']!=2 or p.axis_minor_length==0:
                ambiguous+=1;continue
            coords=p.coords[:,[1,0]].astype(float);coords[:,1]*=-1;coords-=coords.mean(axis=0)
            vals,vecs=np.linalg.eigh(coords.T@coords/len(coords));v=vecs[:,-1]
            if vals[-1]<=vals[0]*1.01:ambiguous+=1;continue
            theta=float(np.rad2deg(np.arctan2(v[1],v[0]))%180)
            span=float(np.ptp(coords@v)+abs(v[0])+abs(v[1]))
            angles.append(theta);weights.append(p.area);spans.append(span);widths.append(float(p.area/span))
            if geom['tortuosity'] is not None:tort.append(geom['tortuosity'])
        z=np.average(np.exp(2j*np.deg2rad(angles)),weights=weights) if angles else None
        data.update(axial_mean_deg=float(np.rad2deg(np.angle(z))/2%180) if z is not None and abs(z)>1e-8 else None,
            alignment=float(abs(z)) if z is not None else None,component_span_mean_px=float(np.mean(spans)) if spans else None,
            component_width_mean_px=float(np.mean(widths)) if widths else None,branched_component_fraction=branched/len(complete) if complete else None,
            ambiguous_complete_components=ambiguous,measurable_complete_components=len(angles),component_angles_deg=angles,
            component_spans_px=spans,component_widths_px=widths,tortuosity_mean=float(np.mean(tort)) if tort else None,
            fiber_instance_status='UNIDENTIFIABLE_FOR_TOUCHING_UNIONS; isolated unbranched component geometry proxies only',
            length_width_definition='Span along principal axis including pixel support; width=component area/span,not independently recovered curved fiber contour length or material thickness')
    return data


def validity(a,family,metrics=None):
    try:validate(a)
    except ValueError as e:return {'passed':False,'failures':[str(e)]}
    if family not in ['particle','fiber']:raise ValueError('Unknown composite family')
    d=metrics if metrics is not None else describe(a,family);fail=[]
    if not 0<d['fraction']<1:fail.append('Both material phases must be nonempty')
    if d['matrix_lcc']<.99:fail.append('Matrix largest-component fraction below0.99')
    if not d['matrix_percolates_x'] or not d['matrix_percolates_y']:fail.append('Matrix fails directional spanning')
    if d['object_count']<2:fail.append('Expected multiple discrete reinforcements')
    return {'passed':not fail,'failures':fail}


def normalized_errors(metrics,target,names,scales):
    errors={}
    for name in names:
        a=metrics.get(name);b=target.get(name)
        errors[name]=None if a is None or b is None else (axial_error(a,b) if name=='axial_mean_deg' else abs(a-b))/scales[name]
    available=[v for v in errors.values() if v is not None]
    return {'per_metric':errors,'coverage':len(available)/len(names),'mean':float(np.mean(available)) if len(available)==len(names) else None,
            'available_metric_mean_diagnostic':float(np.mean(available)) if available else None}
