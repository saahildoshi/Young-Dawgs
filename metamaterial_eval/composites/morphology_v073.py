"""Prospective digital P3 morphology: observed regions, finite axes, no physical scale.

Four-connected annotation regions are not verified particle instances. x points right,
y points up; axial angles are modulo180 degrees. Dilation is diagnostic only.
"""
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial.distance import cdist
from skimage.measure import regionprops
from .descriptors import directional_s2

LAGS = (8,16,32,64)
WIDTHS = (1,8,16,32)

def weighted_quantile(values,weights,q):
    if not len(values) or np.sum(weights)<=0: return None
    order=np.argsort(values,kind='stable');v=np.asarray(values)[order];w=np.asarray(weights)[order]
    return float(v[np.searchsorted(np.cumsum(w),q*np.sum(w),side='left')])

def region_shapes(regions):
    total=sum(r.area for r in regions);aspects=[];areas=[];angles=[];anis=[]
    for r in regions:
        xy=r.coords[:,[1,0]].astype(float);xy[:,1]*=-1;xy-=xy.mean(axis=0)
        vals,vecs=np.linalg.eigh(xy.T@xy/len(xy))
        if vals[0]<=1e-12: continue
        aspect=float(np.sqrt(vals[1]/vals[0]));v=vecs[:,1]
        aspects.append(aspect);areas.append(float(r.area))
        angles.append(float(np.arctan2(v[1],v[0])%np.pi));anis.append(float((vals[1]-vals[0])/sum(vals)))
    areas=np.asarray(areas);aspects=np.asarray(aspects);angles=np.asarray(angles);anis=np.asarray(anis)
    # Near-circular digital orientation is undefined, rather than a noisy dominant axis.
    weights=areas*anis*(anis>=.05)
    z=np.sum(weights*np.exp(2j*angles))/sum(weights) if sum(weights)>1e-12 else None
    largest=max(regions,key=lambda r:r.area) if regions else None
    largest_aspect=float(largest.axis_major_length/largest.axis_minor_length) if largest is not None and largest.axis_minor_length>0 else None
    return {'regions':len(regions),'area':int(total),'largest_region_area':int(largest.area) if largest else None,
        'largest_region_aspect':largest_aspect,'defined_aspect_area_fraction':float(sum(areas)/total) if total else None,
        'unweighted_aspect_mean':float(np.mean(aspects)) if len(aspects) else None,
        'area_weighted_aspect':float(np.average(aspects,weights=areas)) if len(aspects) else None,
        'area_weighted_aspect_p90':weighted_quantile(aspects,areas,.90),
        'area_weighted_aspect_p95':weighted_quantile(aspects,areas,.95),
        'area_fraction_aspect_gt3':float(areas[aspects>3].sum()/total) if total else None,
        'area_fraction_aspect_gt4':float(areas[aspects>4].sum()/total) if total else None,
        'axial_order':float(abs(z)) if z is not None else None,
        'preferred_axial_angle_deg':float(np.degrees(np.angle(z))/2%180) if z is not None and abs(z)>1e-8 else None,
        'vertical_alignment':float(-z.real) if z is not None else None,
        'orientation_weight_fraction':float(sum(weights)/total) if total else None}

def topology(mask,connectivity=1):
    lab,n=ndi.label(mask,ndi.generate_binary_structure(2,connectivity));sizes=np.bincount(lab.ravel())[1:]
    def spans(a,b): return bool((set(np.unique(a))&set(np.unique(b)))-{0})
    return {'regions':int(n),'largest_fraction':float(sizes.max()/mask.sum()) if sizes.size else None,
        'spans_x':spans(lab[:,0],lab[:,-1]),'spans_y':spans(lab[0],lab[-1]),
        'singleton_area_fraction':float(sizes[sizes==1].sum()/mask.sum()) if sizes.size else None}

def limited_gap_run(line,maxgap=2):
    """Longest span of observed true pixels bridged only across <=maxgap zeros.

    No extension beyond first/last occupied pixel; no periodic wrap or mutation.
    """
    pos=np.flatnonzero(line)
    if not len(pos):return 0
    splits=np.r_[0,np.flatnonzero(np.diff(pos)>maxgap+1)+1,len(pos)]
    return max(int(pos[b-1]-pos[a]+1) for a,b in zip(splits[:-1],splits[1:]))

def describe(mask):
    a=np.asarray(mask,dtype=bool)
    if a.ndim!=2:raise ValueError('Expected two-dimensional finite mask')
    lab,n=ndi.label(a);props=regionprops(lab)
    edge=set(np.unique(np.r_[lab[0],lab[-1],lab[:,0],lab[:,-1]]))-{0}
    complete=[r for r in props if r.label not in edge]
    centers=np.array([r.centroid for r in complete]);nn=[]
    if len(centers)>1:
        distances=cdist(centers,centers);np.fill_diagonal(distances,np.inf);nn=distances.min(axis=1)
    out={'complete':region_shapes(complete),'all_observed':region_shapes(props),
        'boundary_censored_regions':len(edge),'correlation':{},'strips':{},'gap_dilation':{},
        'nearest_neighbor_mean_px':float(np.mean(nn)) if len(nn) else None,
        'nearest_neighbor_cv':float(np.std(nn)/np.mean(nn)) if len(nn) else None,
        'interface_density':float((np.count_nonzero(a[1:]!=a[:-1])+np.count_nonzero(a[:,1:]!=a[:,:-1]))/a.size)}
    for lag in LAGS:
        if lag>=min(a.shape):continue
        sx=directional_s2(a,lag,1);sy=directional_s2(a,lag,0)
        out['correlation'][str(lag)]={'x':sx,'y':sy,'y_minus_x':sy-sx}
    values=[abs(v['y_minus_x']) for k,v in out['correlation'].items() if int(k)>=16]
    out['long_range_abs_S2_difference']=float(np.mean(values)) if values else None
    for width in WIDTHS:
        if width>min(a.shape):continue
        x=np.convolve(a.mean(axis=0),np.ones(width)/width,mode='valid')
        y=np.convolve(a.mean(axis=1),np.ones(width)/width,mode='valid')
        out['strips'][str(width)]={'column_std':float(x.std()),'row_std':float(y.std()),
            'column_max':float(x.max()),'row_max':float(y.max()),'column_fraction_ge08':float(np.mean(x>=.8)),
            'row_fraction_ge08':float(np.mean(y>=.8))}
    for radius in (1,2):
        yy,xx=np.mgrid[-radius:radius+1,-radius:radius+1];disk=xx*xx+yy*yy<=radius*radius
        dil=ndi.binary_dilation(a,structure=disk,border_value=0)
        out['gap_dilation'][str(radius)]={**topology(dil,2),'fraction':float(dil.mean())}
    out['limited_gap_run_y']=max(limited_gap_run(a[:,i]) for i in range(a.shape[1]))/a.shape[0]
    out['limited_gap_run_x']=max(limited_gap_run(a[i]) for i in range(a.shape[0]))/a.shape[1]
    out['conventions']='Observed 4-connected regions; complete/all separately; x right,y up; axial modulo180; area×eigenvalue-anisotropy weights with anisotropy>=.05; finite pair/strip support; diagnostic dilation never specimen modification'
    return out

def flattened(d):
    result={f'{group}.{key}':value for group in ('complete','all_observed') for key,value in d[group].items() if key!='preferred_axial_angle_deg'}
    for key in ['long_range_abs_S2_difference','limited_gap_run_y','limited_gap_run_x','nearest_neighbor_cv','nearest_neighbor_mean_px','interface_density']:
        result[key]=d[key]
    for width,row in d['strips'].items():
        for key in ['column_std','row_std','column_max','row_max']:result[f'strips.{width}.{key}']=row[key]
    for radius,row in d['gap_dilation'].items():
        for key in ['largest_fraction','spans_x','spans_y']:result[f'gap_dilation.{radius}.{key}']=row[key]
    return result
