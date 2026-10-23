"""Fixed repair ROIs and explicitly limited neck probes; no feature protection."""
import math
import numpy as np
import shapely
from shapely import Point, LineString, Polygon, STRtree, box
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

from .metrics import polygons, void_partition
from .distance import BoundaryIndex, directed_distance, line_components


def local_link(geometry,window,anchors):
    local=geometry.intersection(window)
    if not local.is_valid:return {'connected':False,'reason':'Invalid clipped local solid region'}
    if not all(geometry.contains(Point(p)) for p in anchors):
        return {'connected':False,'reason':'At least one fixed solid anchor is no longer in solid interior'}
    for part in polygons(local):
        if all(part.contains(Point(p)) for p in anchors):
            return {'connected':True,'local_positive_area_components':len(polygons(local))}
    return {'connected':False,'reason':'Fixed solid anchors are in different positive-area local components'}


def chord_profile(geometry,center,normal,half_length=8):
    center=np.asarray(center,dtype=float);normal=np.asarray(normal,dtype=float)
    normal=normal/np.linalg.norm(normal);point=Point(center)
    if not geometry.contains(point):return {'width':None,'reason':'Fixed probe center is outside solid interior'}
    ends=[center-normal*half_length,center+normal*half_length]
    intersection=shapely.line_merge(geometry.intersection(LineString(ends)))
    matches=[line for line in line_components(intersection) if line.distance(point)<=1e-10]
    if len(matches)!=1:return {'width':None,'reason':'No unique contiguous chord through fixed center'}
    part=matches[0]
    if any(part.distance(Point(end))<=1e-10 for end in ends):
        return {'width':None,'reason':'Chord reaches analysis endpoint; width is clipped','clipped_length':float(part.length)}
    return {'width':float(part.length),'segment_xy':list(map(list,part.coords)),
            'interpretation':'Contiguous normal chord at a fixed diagnostic probe, not a proven global minimum or strength measure.'}


def boundary_depths(geometry,columns,resolution):
    values=[]
    for x in columns:
        line=LineString([(x,0),(x,min(32,resolution))]);origin=Point(x,0)
        parts=line_components(shapely.line_merge(geometry.intersection(line)))
        matches=[p for p in parts if p.distance(origin)<=1e-10]
        depth=float(matches[0].length) if len(matches)==1 else None
        values.append({'x':x,'inward_solid_depth':depth})
    return values


def prepare_features(fixture,config):
    baseline,exact,mask=fixture['baseline'],fixture['exact'],fixture['mask'];n=len(mask)
    q=fixture['qualification'];contacts={c['contact_id']:c for c in q['contact_report']['contacts']}
    repairs=[]
    added=baseline.difference(exact)
    for change in q['changes']:
        c=contacts[change['contact_id']];x,y=change['xy'];r=change['L1_radius'];half=r+config['repair_roi_margin']
        diamond=Polygon([(x-r,y),(x,y-r),(x+r,y),(x,y+r)])
        quadrants=[(-.5,-.5),(.5,-.5),(-.5,.5),(.5,.5)]
        phases=c['local_cells_NW_NE_SW_SE']
        probes=[[x+dx,y+dy] for (dx,dy),solid in zip(quadrants,phases) if not solid]
        ratio=config['repair_solid_anchor_offset']/.5
        anchors=[[x+dx*ratio,y+dy*ratio] for (dx,dy),solid in zip(quadrants,phases) if solid]
        roi=box(max(0,x-half),max(0,y-half),min(n,x+half),min(n,y+half))
        material=added.intersection(diamond)
        repairs.append({'contact_id':change['contact_id'],'xy':[x,y],'original_contact_type':c['kind'],
                        'L1_radius':r,'roi_bounds':list(roi.bounds),'roi_safety_margin':config['repair_roi_margin'],
                        'void_probes_xy':probes,'solid_anchors_xy':anchors,'added_material':material,
                        'original_added_area':float(material.area),'baseline_recorded_clearance':change['predicted_local_clearance']})
    probes=natural_probes(mask,baseline,repairs,config)
    saved=fixture['input_manifest']['saved_topology_repair']
    boundary=[]
    for bridge in saved.get('bridges',[]):
        a,b=bridge['start_yx'],bridge['end_yx']
        if a[0]==b[0]==0:
            columns=[x+.5 for x in range(min(a[1],b[1])+1,max(a[1],b[1]))]
            anchors=[[a[1]+.5,.5],[b[1]+.5,.5]]
            radius=saved['bridge_width_normalized']*(n-1)/2
            window=box(max(0,min(a[1],b[1])-radius-1),0,min(n,max(a[1],b[1])+radius+2),radius+6)
            boundary.append({'kind':'saved_generator_top_boundary_connector','columns':columns,'solid_anchors_xy':anchors,
                             'roi_bounds':list(window.bounds),'baseline_depths':boundary_depths(baseline,columns,n),
                             'historical_context':'v0.4.2 saved local neck inspection; repair not regenerated or recomputed.'})
    return {'repairs':repairs,'natural_neck_probes':probes,'saved_boundary_necks':boundary}


def natural_probes(mask,geometry,repairs,config):
    skeleton=skeletonize(mask.astype(bool));edt=ndi.distance_transform_edt(mask)
    degree=ndi.convolve(skeleton.astype(np.int16),np.ones((3,3),dtype=np.int16))-skeleton
    margin=12;eligible=skeleton&(degree==2)
    eligible[:margin]=False;eligible[-margin:]=False;eligible[:,:margin]=False;eligible[:,-margin:]=False
    yx=np.argwhere(eligible)
    order=sorted(range(len(yx)),key=lambda i:(float(edt[tuple(yx[i])]),int(yx[i,0]),int(yx[i,1])))
    chosen=[]
    for i in order:
        row,col=map(int,yx[i]);center=np.array([col+.5,row+.5])
        if any(np.linalg.norm(center-np.array(p['center_xy']))<config['natural_neck_probe_separation'] for p in chosen):continue
        if any(np.linalg.norm(center-np.array(p['xy']))<8 for p in repairs):continue
        around=np.argwhere(skeleton[row-2:row+3,col-2:col+3])[:,::-1].astype(float)
        if len(around)<3:continue
        values,vectors=np.linalg.eigh(np.cov(around.T))
        if values[-1]<=3*max(values[0],1e-12):continue
        tangent=vectors[:,-1]
        if tangent[0]<0 or (tangent[0]==0 and tangent[1]<0):tangent=-tangent
        normal=np.array([-tangent[1],tangent[0]])
        anchors=[(center-2*tangent).tolist(),(center+2*tangent).tolist()]
        half=config['natural_neck_roi_half_width'];window=box(*(center-half),*(center+half))
        baseline=chord_profile(geometry,center,normal,config['natural_neck_cross_section_half_length'])
        if baseline['width'] is None or not local_link(geometry,window,anchors)['connected']:continue
        chosen.append({'probe_id':f'natural_{len(chosen):02d}','center_xy':center.tolist(),'normal_xy':normal.tolist(),
                       'tangent_xy':tangent.tolist(),'solid_anchors_xy':anchors,'roi_bounds':list(window.bounds),
                       'baseline_chord':baseline,'source_skeleton_edt_diameter':float(2*edt[row,col]),
                       'selection':'Row-major tie-break among lowest-EDT degree-two skeleton points, separated by fixed distance; PCA anisotropy >3.'})
        if len(chosen)>=config['natural_neck_probe_count']:break
    return chosen


def serializable_features(features):
    return {**features,'repairs':[{k:v for k,v in p.items() if k!='added_material'} for p in features['repairs']]}


def _local_displacement(reference,candidate,window,reference_index,candidate_index,equal=False):
    if equal:return {'measured_max':0.0,'upper_bound':0.0}
    old=BoundaryIndex(reference.boundary.intersection(window),spacing=.0625,boundary_input=True)
    new=BoundaryIndex(candidate.boundary.intersection(window),spacing=.0625,boundary_input=True)
    a=directed_distance(old,candidate_index);b=directed_distance(new,reference_index)
    if a['measured_max'] is None or b['measured_max'] is None:
        return {'measured_max':None,'upper_bound':None,'reason':'Missing local boundary samples'}
    return {'measured_max':max(a['measured_max'],b['measured_max']),
            'upper_bound':max(a['upper_bound'],b['upper_bound']),
            'definition':'Samples inside the fixed ROI to entire opposing boundary, so clipping endpoints do not manufacture distance.'}


def evaluate_features(reference,candidate,features,config,manifold,reference_index,candidate_index,*,baseline_clearances=None,candidate_void=None):
    if not candidate.is_valid or candidate.is_empty:
        return {'defined':False,'reason':'Invalid/empty candidate; local Boolean/clearance metrics undefined.',
                'repairs':[{'contact_id':p['contact_id'],'clearance':None,'reason':'Invalid/empty candidate'} for p in features['repairs']],
                'natural_necks':[],'boundary_necks':[]}
    n=1024 if config.get('resolution') is None else config['resolution']
    parts,_=candidate_void if candidate_void is not None else void_partition(candidate,n)
    tree=STRtree(parts);equal=reference.equals(candidate);records=[]
    for p in features['repairs']:
        window=box(*p['roi_bounds']);local_before=reference.intersection(window);local_after=candidate.intersection(window)
        delta=float(local_before.symmetric_difference(local_after).area)
        matches=[list(map(int,tree.query(Point(probe),predicate='within'))) for probe in p['void_probes_xy']]
        reason=None;clearance=None
        if not all(len(ids)==1 for ids in matches):reason='A registered void-cell anchor is not in one candidate void interior'
        elif matches[0][0]==matches[1][0]:reason='Registered void regions merged';clearance=0.0
        else:
            arcs=[parts[ids[0]].boundary.intersection(candidate.boundary).intersection(window) for ids in matches]
            if any(a.is_empty for a in arcs):reason='Relevant interface missing from fixed ROI'
            else:clearance=float(arcs[0].distance(arcs[1]))
        retained=float(p['added_material'].intersection(candidate).area)
        fraction=retained/p['original_added_area'] if p['original_added_area'] else None
        link=local_link(candidate,window,p['solid_anchors_xy'])
        events=[c for c in manifold.get('contacts',[]) if window.covers(Point(c['xy']))]
        overlaps=[v for v in manifold.get('overlaps',[]) if shapely.from_wkt(v['geometry']).intersects(window)]
        base_clear=(baseline_clearances or {}).get(p['contact_id'],p['baseline_recorded_clearance'])
        width_loss=clearance is not None and clearance<base_clear-config['numeric_length_allowance']
        resolved=clearance is not None and clearance>config['numeric_length_allowance'] and link['connected'] and not events and not overlaps
        risk_fraction=config['material_repair_risk_fraction'];area0=p['original_added_area']
        material_risk=(not resolved or fraction is None or fraction<1-risk_fraction or
                       (clearance is not None and clearance<(1-risk_fraction)*base_clear) or delta>=risk_fraction*area0)
        records.append({'contact_id':p['contact_id'],'xy':p['xy'],'roi_bounds':p['roi_bounds'],
                        'local_symmetric_difference_area':delta,'original_added_area':area0,
                        'retained_original_added_area':retained,'retained_added_fraction':fraction,
                        'baseline_clearance':base_clear,'clearance':clearance,'clearance_undefined_reason':reason,
                        'clearance_below_baseline':bool(width_loss),'contact_remains_resolved':bool(resolved),
                        'local_solid_link':link,'local_manifold':not events and not overlaps and local_after.is_valid,
                        'new_contact_events':events,'overlapping_boundary_events':overlaps,
                        'new_narrow_feature_flag':clearance is not None and 0<clearance<.25,
                        'material_repair_risk_flag':bool(material_risk),
                        'boundary_displacement':_local_displacement(reference,candidate,window,reference_index,candidate_index,equal=equal),
                        'interpretation':'Relevant interface separation in a fixed registered contact ROI; not a material strength or universal neck-width measurement.'})
    natural=[]
    for p in features['natural_neck_probes']:
        chord=chord_profile(candidate,p['center_xy'],p['normal_xy'],config['natural_neck_cross_section_half_length'])
        link=local_link(candidate,box(*p['roi_bounds']),p['solid_anchors_xy']);old=p['baseline_chord']['width'];width=chord['width']
        window=box(*p['roi_bounds'])
        local_delta=float(reference.intersection(window).symmetric_difference(candidate.intersection(window)).area)
        natural.append({'probe_id':p['probe_id'],'center_xy':p['center_xy'],'baseline_width':old,'candidate_chord':chord,
                        'local_symmetric_difference_area':local_delta,
                        'boundary_displacement':_local_displacement(reference,candidate,window,reference_index,candidate_index,equal=equal),
                        'local_solid_link':link,'width_change':width-old if width is not None else None,
                        'narrowed':bool(width is not None and width<old-config['numeric_length_allowance']),
                        'material_risk_flag':bool(not link['connected'] or width is None or width<.9*old)})
    boundary=[]
    for p in features['saved_boundary_necks']:
        depths=boundary_depths(candidate,p['columns'],n)
        link=local_link(candidate,box(*p['roi_bounds']),p['solid_anchors_xy'])
        narrowed=any(b['inward_solid_depth'] is None or (a['inward_solid_depth'] is not None and b['inward_solid_depth']<a['inward_solid_depth']-config['numeric_length_allowance']) for a,b in zip(p['baseline_depths'],depths))
        window=box(*p['roi_bounds'])
        boundary.append({'kind':p['kind'],'baseline_depths':p['baseline_depths'],'candidate_depths':depths,
                         'local_symmetric_difference_area':float(reference.intersection(window).symmetric_difference(candidate.intersection(window)).area),
                         'boundary_displacement':_local_displacement(reference,candidate,window,reference_index,candidate_index,equal=equal),
                         'local_solid_link':link,'narrowed':bool(narrowed)})
    return {'defined':True,'repairs':records,'natural_necks':natural,'boundary_necks':boundary,
            'minimum_repair_clearance':min((p['clearance'] for p in records if p['clearance'] is not None),default=None),
            'undefined_repair_clearance_count':sum(p['clearance'] is None for p in records),
            'any_repair_unresolved':any(not p['contact_remains_resolved'] for p in records),
            'any_material_repair_risk':any(p['material_repair_risk_flag'] for p in records),
            'any_clearance_below_baseline':any(p['clearance_below_baseline'] for p in records),
            'any_monitored_neck_link_lost':any(not p['local_solid_link']['connected'] for p in natural+boundary),
            'any_monitored_neck_narrowed':any(p['narrowed'] for p in natural+boundary),
            'coverage':'Registered repairs, saved boundary connector, and up to three deterministic natural probes; not exhaustive network-neck or mechanical qualification.'}
