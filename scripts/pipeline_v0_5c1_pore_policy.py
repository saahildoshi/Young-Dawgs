"""Separate small-pore investigation; never revises the A1 regularizer."""
from pathlib import Path
import json
import numpy as np
import shapely
from shapely import Polygon,box
from metamaterial_eval.geometry.validation.checks import polygons,rings,region_correspondence,topology,area_difference,digest
from metamaterial_eval.geometry.conversion import convert_exact
from metamaterial_eval.geometry.manifold.candidates import qualify_manifold_geometry
from metamaterial_eval.geometry.sensitivity.records import write_json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/pipeline_v0.5/scientific_requalification/run_001'
C=ROOT/'experiments/pipeline_v0.5/scientific_validation/run_001'


def diagnose(old,new,name):
    match=region_correspondence(old,new);rows=[]
    for p in match['records']:
        absolute=abs(p['source_area']-p['candidate_area']) if p['candidate_area'] is not None else None
        relative=p['relative_area_distortion'];ap=absolute is not None and absolute<=.03125+1e-10;rp=relative is not None and relative<=.005+1e-10
        rows.append({**p,'absolute_error':absolute,'relative_error':relative,'absolute_diagnostic':ap,'relative_diagnostic':rp,'AND_diagnostic_with_identity':match['passed'] and ap and rp,'OR_diagnostic_with_identity':match['passed'] and (ap or rp)})
    return {'case':name,'identity_preserved':match['passed'],'source_count':len(old),'candidate_count':len(new),'pores':rows,
            'policy':'Diagnostics only. No prospective fidelity amendment adopted; topology/identity are mandatory independently of area.'}


def main():
    records=[]
    for area in [1,2,100]:
        m=np.ones((256,256),np.uint8)
        if area==1:m[50,50]=0;m[51:53,51:53]=0
        elif area==2:m[50,50:52]=0;m[51:53,52:54]=0
        else:m[50:60,50:60]=0;m[60:62,60:62]=0
        exact=convert_exact(m);q=qualify_manifold_geometry(m,exact,'solid_separate_contacts');assert q['accepted']
        folder=OUT/'pore_policy'/f'synthetic_pore_{area}';folder.mkdir(exist_ok=True)
        for key,g in [('G1',exact['geometry']),('G2',q['geometry'])]:(folder/(key+'.wkb')).write_bytes(g.wkb)
        old=[Polygon(h) for p in polygons(exact['geometry']) for h in p.interiors];new=[Polygon(h) for p in polygons(q['geometry']) for h in p.interiors]
        r=diagnose(old,new,f'contact_regularized_{area}');r['A1_accepted']=q['accepted'];records.append(r)
    for area,delta,name in [(100,.01,'both_area_screens_pass'),(40,.04,'absolute_limit_exceeded'),(1,.01,'relative_limit_exceeded'),(1,.04,'both_limits_exceeded'),(1,0,'unaffected'),(1,.03125,'historical_triangle_scale')]:
        old=box(10,10,10+area,11);new=box(10,10,10+area-delta,11);records.append(diagnose([old],[new],name))
        folder=OUT/'pore_policy'/name;folder.mkdir(exist_ok=True);(folder/'source_pore.wkb').write_bytes(old.wkb);(folder/'candidate_pore.wkb').write_bytes(new.wkb)
    cases=[('shape_equal_area',[box(10,10,11,11)],[box(10,10,10.5,12)]),
           ('pore_merge',[box(10,10,10.1,10.1),box(10.101,10,10.201,10.1)],[box(10,10,10.201,10.1)]),
           ('pore_split',[box(10,10,10.201,10.1)],[box(10,10,10.1,10.1),box(10.101,10,10.201,10.1)]),
           ('pore_deletion',[box(10,10,10.1,10.1)],[]),('pore_addition',[],[box(10,10,10.1,10.1)])]
    for name,old,new in cases:records.append(diagnose(old,new,name))
    a=box(0,0,256,256).difference(box(10,10,11,11));b=a.difference(box(10.49,0,10.51,10.5));records.append({'case':'pore_connected_to_exterior','topology':topology(a,b,256),'absolute_change':b.symmetric_difference(a).area})
    source=json.loads((C/'source_manifests/design_007_seed_000.json').read_text())['source_provenance'];a=shapely.from_wkb((ROOT/source['paths']['exact']).read_bytes());b=shapely.from_wkb((ROOT/source['paths']['manifold']).read_bytes())
    q=json.loads((ROOT/source['paths']['qualification']).read_text());old=[Polygon(h) for p in polygons(a) for h in p.interiors];new=[Polygon(h) for p in polygons(b) for h in p.interiors];matches=region_correspondence(old,new);target=matches['records'][1];j=target['candidate_ids'][0]
    contacts=[c for c in q['contact_report']['contacts'] if old[1].boundary.distance(shapely.Point(c['xy']))<1e-10]
    reproduction={'fixture':'design_007_seed_000','source_pore_id':1,'candidate_pore_id':j,'source_xy':rings(old[1]),'candidate_xy':rings(new[j]),
        'source_area':old[1].area,'manifold_area':new[j].area,'absolute_change':old[1].area-new[j].area,'relative_change':(old[1].area-new[j].area)/old[1].area,
        'source_perimeter':old[1].length,'candidate_perimeter':new[j].length,'identity':target,'contacts':contacts,
        'actual_removed_pore_footprint':rings(old[1].difference(new[j])),'source_provenance':source,
        'A1_scope':'Global≤0.0001*G1 occupied area; supported local diamond r=.25; no removals of solid, valid manifold, same hole count, raster equality, displacement≤.25, positive clearance≥.25. No G1-based per-pore0.5% gate.',
        'B2_scope':'Each pore area distortion≤0.005 uses its G2 area for G2→G3. Historical regularization is separately reported.',
        'disposition':'Existing policy applied correctly within its geometric scope; cumulative scientific pore-fidelity policy remains UNQUALIFIED. No amendment adopted.'}
    assert reproduction['source_area']==1 and reproduction['manifold_area']==.96875
    write_json(OUT/'pore_policy/HISTORICAL_RECONSTRUCTION.json',reproduction)
    write_json(OUT/'pore_policy/SYNTHETIC_CONTROLS.json',{'cases':records,'candidate_absolute_threshold':.03125,'candidate_relative_threshold':.005,
        'rationale':'r²/2 for r=.25 is one regularization triangle; per-pore absolute loss is bounded by incident contact count times this scale. A construction envelope is not a fidelity allowance.',
        'adopted_amendment':False,'scientific_policy':'UNQUALIFIED','all_original_criteria_unchanged':True})
    print('Small-pore reproduction',reproduction['source_area'],'→',reproduction['manifold_area'],'synthetic cases',len(records))


if __name__=='__main__':main()
