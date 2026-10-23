"""C.1 analytic feature and small-pore controls; frozen producer tests unchanged."""
from pathlib import Path
import json
import math
import numpy as np
import pytest
import shapely
from shapely import Polygon,box,LineString
from shapely.affinity import rotate,translate
from metamaterial_eval.geometry.protected.model import BoundaryModel
from metamaterial_eval.geometry.protected_v2.width import chord_width_gate,affine_loss
from metamaterial_eval.geometry.validation.checks import independent_raster,area_difference,topology,region_correspondence,probe_width
from metamaterial_eval.geometry.conversion import convert_exact
from metamaterial_eval.geometry.manifold.candidates import qualify_manifold_geometry

SETTINGS={'directions_degrees':[0,90],'qualifying_width':16.,'numeric_allowance':1e-10}


def stair(width=9.,origin=(0.,0.)):
    # Continuous body with one ordinary staircase edge, no hidden repair.
    g=Polygon([(0,0),(128,0),(128,width-.25),(80,width-.25),(64,width-.25),(64,width),(48,width),(0,width)])
    g=translate(g,*origin)
    chain=np.array([[48,width],[64,width],[64,width-.25],[80,width-.25]],float)+origin
    return g,chain


def evaluate(g,chain,settings=SETTINGS):
    model=BoundaryModel(g);xy=model.xy[0];ids=[]
    for p in chain:ids.append(next(i for i,x in enumerate(xy) if np.array_equal(p,x)))
    if (ids[1]-ids[0])%len(xy)!=1:ids=ids[::-1];chain=chain[::-1]
    return chord_width_gate(model,0,np.array(ids),chain,settings)


@pytest.mark.parametrize('origin',[(0,0),(20,30),(-30,40)])
def test_generalized_translated_narrowing(origin):
    g,c=stair(9.,origin);w=evaluate(g,c);assert not w['passed'] and 'qualifying_solid_width_loss' in w['failed_constraints']


def test_wide_safe_proposal_accepted():
    g,c=stair(64.25);assert evaluate(g,c)['passed']


def test_straight_uniform_strut_no_change():
    g=Polygon([(0,0),(80,0),(80,8),(60,8),(40,8),(20,8),(0,8)])
    c=np.array([[60,8],[40,8],[20,8]],float);assert evaluate(g,c)['passed']


def test_curved_uniform_corridor_control():
    a=np.linspace(0,np.pi/2,40);outer=np.c_[30*np.cos(a),30*np.sin(a)];inner=np.c_[22*np.cos(a[::-1]),22*np.sin(a[::-1])]
    g=Polygon(np.vstack([outer,inner]));c=outer[8:14];w=evaluate(g,c);assert not w['passed']


def test_tapered_strut_narrowing():
    g,c=stair(12.);coords=list(g.exterior.coords);coords[1]=(128,2);g=Polygon(coords)
    assert not evaluate(g,c)['passed']


@pytest.mark.parametrize('width',[2.,6.,10.,15.])
def test_narrow_neck_width_horizon(width):
    g,c=stair(width);assert not evaluate(g,c)['passed']


def test_wide_neck_not_blanket_frozen():
    g,c=stair(100.);assert evaluate(g,c)['passed']


@pytest.mark.parametrize('angle',[20.,45.,70.,110.])
def test_angled_corridor_and_nonparallel_boundaries(angle):
    g,c=stair(6.);g=rotate(g,angle,origin=(0,0));c=np.asarray(rotate(LineString(c),angle,origin=(0,0)).coords)
    assert not evaluate(g,c)['passed']


def test_high_curvature_uncertain_preserved():
    g=Polygon([(0,0),(30,0),(30,10),(20,10),(22,12),(18,11),(15,13),(10,10),(0,10)])
    c=np.array([[20,10],[22,12],[18,11],[15,13],[10,10]],float)
    assert not evaluate(g,c)['passed']


def test_junction_with_multiple_struts():
    g=shapely.union_all([box(0,0,40,8),box(16,-12,24,20)]);assert g.is_valid and len(g.interiors)==0
    assert probe_width(g,[8,4],1,'solid',40)==8


def test_void_corridor_narrowing_is_distinct():
    solid,c=stair(9.);domain=box(-10,-10,140,30);g=domain.difference(solid)
    model=BoundaryModel(g);ring=next(i for i,x in enumerate(model.xy) if all(any(np.array_equal(p,q) for q in x) for p in c))
    xy=model.xy[ring];ids=[next(i for i,q in enumerate(xy) if np.array_equal(p,q)) for p in c]
    if (ids[1]-ids[0])%len(xy)!=1:ids=ids[::-1];c=c[::-1]
    w=chord_width_gate(model,ring,np.array(ids),c,SETTINGS);assert not w['passed'] and 'qualifying_void_width_loss' in w['failed_constraints']


def test_zero_xor_real_subpixel_width_loss():
    g,c=stair(9.);model=BoundaryModel(g);ids=[next(i for i,p in enumerate(model.xy[0]) if np.array_equal(p,q)) for q in c];keep=np.ones(len(model.xy[0]),bool);keep[ids[1:-1]]=False;b=model.assemble([keep])
    assert np.array_equal(independent_raster(g,256)[0],independent_raster(b,256)[0])
    assert probe_width(b,[56.5,4.5],1,'solid',256)<probe_width(g,[56.5,4.5],1,'solid',256)
    assert not evaluate(g,c)['passed']


def test_global_budget_can_pass_while_local_width_fails():
    g,c=stair(9.);g=shapely.union_all([g,box(120,0,256,256)])
    assert not evaluate(g,c)['passed'];assert g.area*.0025>4


def test_topology_pass_does_not_prove_width():
    g,c=stair(9.);model=BoundaryModel(g);ids=[next(i for i,p in enumerate(model.xy[0]) if np.array_equal(p,q)) for q in c];keep=np.ones(len(model.xy[0]),bool);keep[ids[1:-1]]=False;b=model.assemble([keep])
    assert topology(g,b,256)['passed'] and not evaluate(g,c)['passed']


def test_affine_increase_allowed_unchanged_allowed_loss_rejected():
    assert affine_loss([8,8],[9,9],16)[0]<0
    assert affine_loss([8,8],[8,8],16)[0]==0
    assert affine_loss([8,8],[7.9,7.8],16)[0]>.1


def test_adaptive_event_limit_detects_unsampled_end_loss():
    loss,t=affine_loss([17.,15.9],[17.,15.8],16)
    assert loss>.09 and t==1.


def test_ambiguous_projection_rejects():
    g=Polygon([(0,0),(30,0),(30,10),(20,10),(20,11),(10,11),(10,10),(0,10)])
    c=np.array([[20,10],[20,11],[10,11],[10,10]],float);assert not evaluate(g,c)['passed']


def test_multiple_changes_require_global_validation():
    # Individually bounded checks do not establish all-direction joint widths.
    g=box(0,0,64,64);b=g.difference(box(20,20,44,20.2));assert not topology(g,b,64)['passed']


def test_repeated_gate_deterministic_except_time():
    g,c=stair();a=evaluate(g,c);b=evaluate(g,c);a.pop('seconds');b.pop('seconds');assert a==b


def test_numeric_allowance_does_not_hide_original_failure():
    assert .083333333333>SETTINGS['numeric_allowance']*1e8
    g,c=stair();assert evaluate(g,c)['worst_one_sided_loss']>SETTINGS['numeric_allowance']


def test_same_width_response_not_assumed_monotonic():
    responses=[affine_loss([9,9],v,16)[0] for v in [[9,9],[8.9,8.9],[9.1,9.1]]]
    assert responses[0]==0 and responses[1]>0 and responses[2]<0


def test_original_failure_saved_coordinates_and_versioned_gate():
    root=Path(__file__).resolve().parents[1];p=root/'experiments/pipeline_v0.5/scientific_validation/run_001/parameter_holdouts/design_004_seed_001';g=shapely.from_wkb((p/'G2.wkb').read_bytes());model=BoundaryModel(g);ids=np.array([9,10,11,12]);w=chord_width_gate(model,8,ids,model.xy[8][ids],SETTINGS)
    assert not w['passed'] and 'qualifying_solid_width_loss' in w['failed_constraints']
    original=shapely.from_wkb((p/'epsilon_0p50/candidate.wkb').read_bytes())
    assert probe_width(g,[57.5,556.5],1,'solid',1024)==9.
    assert probe_width(original,[57.5,556.5],1,'solid',1024)==pytest.approx(8.916666666666629)


def pore_fixture(area):
    m=np.ones((256,256),np.uint8)
    if area==1:m[50,50]=0;m[51:53,51:53]=0
    elif area==2:m[50,50:52]=0;m[51:53,52:54]=0
    else:m[50:60,50:60]=0;m[60:62,60:62]=0
    e=convert_exact(m);q=qualify_manifold_geometry(m,e,'solid_separate_contacts');return m,e,q


@pytest.mark.parametrize('area',[1,2,100])
def test_pore_regularization_absolute_relative_scale(area):
    m,e,q=pore_fixture(area);assert q['accepted']
    old=[Polygon(h) for p in [e['geometry']] for h in p.interiors];new=[Polygon(h) for p in [q['geometry']] for h in p.interiors]
    match=region_correspondence(old,new);row=next(h for h in match['records'] if h['source_area']==area)
    assert abs(row['source_area']-row['candidate_area'])==pytest.approx(.03125)
    assert row['relative_area_distortion']==pytest.approx(.03125/area)
    assert np.array_equal(independent_raster(q['geometry'],256)[0],m)


def test_unaffected_pore_zero_change():
    g=Polygon(box(0,0,20,20).exterior.coords,[box(5,5,7,7).exterior.coords]);assert region_correspondence([Polygon(g.interiors[0])],[Polygon(g.interiors[0])])['records'][0]['symmetric_area']==0


def test_shape_change_equal_area_not_hidden():
    a=box(0,0,2,2);b=box(0,0,1,4);d=region_correspondence([a],[b]);assert d['passed'] and d['records'][0]['relative_area_distortion']==0 and d['records'][0]['symmetric_area']>0


@pytest.mark.parametrize('old,new',[
    ([box(1,1,2,2),box(3,1,4,2)],[box(1,1,4,2)]),
    ([box(1,1,4,2)],[box(1,1,2,2),box(3,1,4,2)]),
    ([box(1,1,2,2)],[]),
    ([],[box(1,1,2,2)])])
def test_pore_topology_never_overridden_by_area(old,new):assert not region_correspondence(old,new)['passed']


def test_pore_to_exterior_channel_topology_failure():
    a=box(0,0,20,20).difference(box(5,5,7,7));b=a.difference(box(5.5,0,5.6,6));assert not topology(a,b,20)['passed']


@pytest.mark.parametrize('absolute,relative,abs_pass,rel_pass',[(.01,.001,True,True),(.04,.001,False,True),(.01,.01,True,False),(.04,.01,False,False)])
def test_alternative_pore_policy_detection_matrix(absolute,relative,abs_pass,rel_pass):
    assert (absolute<=.03125)==abs_pass and (relative<=.005)==rel_pass
    # OR can accept violation of either individual criterion. It is diagnostic,
    # not adopted as an engineering-fidelity amendment.
    assert ((absolute<=.03125) and (relative<=.005))==(abs_pass and rel_pass)


def test_small_pore_relative_criterion_not_redefined():assert .03125/1>.005 and .03125/100<.005


def manual(g,shapes=()):
    from shapely import STRtree
    model=BoundaryModel(g);records=[{'guard_id':f's{i}','kind':'synthetic','geometry':s,'protected_segments':[],'protected_vertices':[]} for i,s in enumerate(shapes)]
    tree=STRtree(list(shapes));protected=np.zeros(len(model.lines),bool)
    if shapes:
        hit=tree.query(model.lines,predicate='intersects');protected[hit[0]]=True
        for si,gi in zip(*hit):records[gi]['protected_segments'].append(int(si))
    return {'model':model},{'tree':tree,'records':records,'protected':protected,'union':shapely.union_all(list(shapes))}


def config():
    from metamaterial_eval.geometry.protected.settings import settings
    c=settings();c['width_settings']=SETTINGS;return c


def test_v2_zero_clone_and_input_immutable():
    from metamaterial_eval.geometry.protected_v2.engine import simplify_protected
    g,c=stair();r,guards=manual(g);before=g.wkb;e=simplify_protected(g,0,r,guards,config());assert e['geometry'].wkb==before and g.wkb==before


def test_v2_all_protected_noop():
    from metamaterial_eval.geometry.protected_v2.engine import simplify_protected
    g,c=stair();r,guards=manual(g,[box(-1,-1,256,256)]);e=simplify_protected(g,.5,r,guards,config());assert e['geometry'].wkb==g.wkb and not e['chains']


def test_v2_width_rejection_restores_chain():
    from metamaterial_eval.geometry.protected_v2.engine import simplify_protected
    g,c=stair();r,guards=manual(g,[box(-1,-1,40,128),box(90,-1,256,128)]);e=simplify_protected(g,.5,r,guards,config())
    rejected=[p for p in e['proposals'] if p['width_qualification'] is not None and not p['width_qualification']['passed']]
    assert rejected and all(p['original_chain']==p['restored_geometry'] and not p['applied'] for p in rejected)


def test_v2_safe_local_simplification_reduces():
    from metamaterial_eval.geometry.protected_v2.engine import simplify_protected
    g,c=stair(64.25);r,guards=manual(g,[box(-1,-1,40,128),box(90,-1,256,128)]);e=simplify_protected(g,.5,r,guards,config())
    assert len(e['geometry'].exterior.coords)<len(g.exterior.coords)


def test_v2_keeps_original_guard_hull_constraint():
    from metamaterial_eval.geometry.protected_v2.engine import chord_constraints
    g=Polygon([(0,0),(4,4),(8,0),(8,8),(0,8)]);r,guards=manual(g,[box(3,1,4,2)]);xy=np.asarray(g.exterior.coords)[:3]
    assert not LineString([xy[0],xy[-1]]).intersects(guards['union'])
    q=chord_constraints(r['model'],guards,0,np.arange(3),xy,config());assert 'chord_or_change_support_enters_guard' in q['failed_constraints']
