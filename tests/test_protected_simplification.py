"""Analytic and adversarial constraints, independent of real holdout outcomes."""
import copy
import json
import numpy as np
import pytest
import shapely
from shapely import Polygon, MultiPolygon, LineString, box, STRtree
from metamaterial_eval.geometry.planar import rasterize_exact_geometry
from metamaterial_eval.geometry.conversion import convert_exact
from metamaterial_eval.geometry.manifold.candidates import qualify_manifold_geometry
from metamaterial_eval.geometry.manifold.contacts import inspect_boundary
from metamaterial_eval.geometry.sensitivity.study import context_for
from metamaterial_eval.geometry.sensitivity.morphology import DescriptorCache
from metamaterial_eval.geometry.protected.settings import settings
from metamaterial_eval.geometry.protected.model import BoundaryModel
from metamaterial_eval.geometry.protected.guards import prepare_risks, build_guards
from metamaterial_eval.geometry.protected.engine import (simplify_protected, chord_constraints,
    vertex_distances, fan_bounds, fan_contains_cell_center)
from metamaterial_eval.geometry.protected.qualification import protected_integrity, qualify
from metamaterial_eval.geometry.protected.study import fallback_engine


def fixture(g, n=256):
    return {'id':'synthetic','baseline':g,'exact':g,'mask':rasterize_exact_geometry(g,n),
            'qualification':{'contact_report':{'contacts':[]},'changes':[],
                             'metrics':{'hausdorff_certified_for_registered_family':True,'boundary_hausdorff_distance':0.}},
            'input_manifest':{'saved_topology_repair':{'bridges':[]}},
            'provenance':{'sha256':{'qualification':'synthetic'}}}


def manual_risks(g, shapes=()):
    model=BoundaryModel(g);features={'repairs':[],'natural_neck_probes':[],'saved_boundary_necks':[]}
    risks={'model':model,'features':features,'dense':[],'proximity':[]}
    records=[{'guard_id':f'g{i}','kind':'synthetic','geometry':p,'protected_segments':[],'protected_vertices':[]} for i,p in enumerate(shapes)]
    tree=STRtree(list(shapes)); protected=np.zeros(len(model.lines),dtype=bool)
    if shapes:
        hits=tree.query(model.lines,predicate='intersects');protected[hits[0]]=True
        for si,gi in zip(*hits):records[gi]['protected_segments'].append(int(si))
    return risks,{'records':records,'tree':tree,'union':shapely.union_all(list(shapes)), 'protected':protected}


def stairs():
    diagonal=[]
    for i in range(16):diagonal += [(28-i,12+i),(27-i,12+i)]
    return Polygon([(4,4),(28,4),*diagonal,(12,28),(4,28)])


@pytest.mark.parametrize('epsilon',[None,True,-.1,float('nan'),float('inf'),'0.5'])
def test_invalid_tolerances(epsilon):
    with pytest.raises(ValueError):simplify_protected(box(2,2,12,12),epsilon,None,None,settings())


@pytest.mark.parametrize('g',[Polygon(),LineString([(0,0),(1,1)]),Polygon([(0,0),(2,2),(0,2),(2,0)])])
def test_unsupported_inputs(g):
    assert simplify_protected(g,.5,None,None,settings())['disposition']=='UNSUPPORTED_INPUT'


def test_zero_clone_and_simple_square():
    g=box(2,2,20,20);r,guards=manual_risks(g);before=g.wkb
    a=simplify_protected(g,0,r,guards,settings());b=simplify_protected(g,.75,r,guards,settings())
    assert a['geometry'] is not g and a['geometry'].wkb==before
    assert b['geometry'].equals(g) and g.wkb==before


def test_staircase_reduces_without_changing_cell_centers():
    g=stairs();r,guards=manual_risks(g);a=simplify_protected(g,.5,r,guards,settings())
    assert len(a['geometry'].exterior.coords)<len(g.exterior.coords)
    assert np.array_equal(rasterize_exact_geometry(g,32),rasterize_exact_geometry(a['geometry'],32))
    assert inspect_boundary(a['geometry'])['manifold']


def test_signed_fan_internal_diagonal_is_not_false_raster_change():
    xy=np.array([[0.,0.],[1.,0.],[1.,1.],[2.,1.]])
    assert fan_contains_cell_center(xy)==(False,None)
    assert vertex_distances(xy).max()==pytest.approx(1/np.sqrt(5))
    assert fan_bounds(xy,1)==(.5,.5)


def test_cell_center_on_replacement_or_in_change_is_rejected():
    hit,reason=fan_contains_cell_center(np.array([[0.,0.],[1.,0.],[1.,1.]]))
    assert hit and reason
    assert fan_contains_cell_center(np.array([[0.,0.],[100.,0.],[100.,100.]]),maximum=8)[1]=='local_raster_work_limit'


def test_hull_guard_protects_indirect_geometry_even_chord_misses():
    g=Polygon([(0,0),(4,4),(8,0),(8,8),(0,8)])
    r,guards=manual_risks(g,[box(3,1,4,2)])
    xy=np.asarray(g.exterior.coords)[:3]
    assert not LineString([xy[0],xy[-1]]).intersects(guards['union'])
    report=chord_constraints(r['model'],guards,0,np.arange(3),xy,settings())
    assert 'chord_or_change_support_enters_guard' in report['failed_constraints']


def test_crossing_guard_and_protected_coordinates_remain_exact():
    g=stairs();r,guards=manual_risks(g,[box(18,18,23,23)])
    out=simplify_protected(g,.75,r,guards,settings())
    integrity=protected_integrity(g,out['geometry'],r,guards)
    assert integrity['passed'] and not integrity['coordinate_failures']
    for p in out['proposals']:
        if p['entered_guards']:assert not p['applied'] and p['restored_geometry']==p['original_chain']


def test_free_chain_partition_covers_each_original_edge_once():
    g=stairs();r,guards=manual_risks(g,[box(18,18,23,23)]);m=r['model']
    seen=[]
    for c in m.chains(guards['protected']):seen.extend((m.offsets[c['ring']]+c['vertices'][:-1]).tolist())
    assert sorted(seen)==np.flatnonzero(~guards['protected']).tolist()
    assert len(seen)==len(set(seen))


def test_all_protected_is_noop_and_unprotected_arcs_cannot_bypass():
    g=stairs();r,guards=manual_risks(g,[box(0,0,32,32)])
    out=simplify_protected(g,.75,r,guards,settings())
    assert out['geometry'].equals_exact(g,0) and not out['chains']
    assert out['protected_segment_count']==len(g.exterior.coords)-1


def test_chord_crossing_hole_boundary_is_rejected():
    g=Polygon([(2,2),(2,26),(26,26),(26,2)],holes=[[(8,10),(12,10),(12,18),(8,18)]])
    r,guards=manual_risks(g);xy=np.asarray(g.exterior.coords)[:3]
    q=chord_constraints(r['model'],guards,0,np.arange(3),xy,settings())
    assert 'collision_with_original_boundary' in q['failed_constraints']


def test_zero_area_budget_locally_restores_rejected_source_chains():
    g=stairs();r,guards=manual_risks(g);cfg=settings()
    cfg['limits']['max_added_fraction']=0;cfg['limits']['max_removed_fraction']=0
    out=simplify_protected(g,.5,r,guards,cfg)
    assert out['geometry'].equals(g) and out['rejected_chord_count']>0
    assert any('global_fan_material_budget' in p['failed_constraints'] for p in out['proposals'])
    assert all(not p['further_tolerance_retry'] for p in out['proposals'])


def test_independent_displacement_budget_blocks_even_large_trial_epsilon():
    g=stairs();r,guards=manual_risks(g);cfg=settings();cfg['limits']['max_displacement']=.1
    out=simplify_protected(g,.75,r,guards,cfg)
    assert out['geometry'].equals(g)
    assert any('continuous_displacement_budget' in p['failed_constraints'] for p in out['proposals'])


def test_registry_cannot_be_reused_on_different_source():
    r,guards=manual_risks(box(1,1,8,8))
    assert simplify_protected(box(1,1,9,9),.5,r,guards,settings())['disposition']=='UNSUPPORTED_INPUT'


def test_disconnected_patches_supported_without_merging():
    g=MultiPolygon([box(2,2,10,10),box(15,15,25,25)]);r,guards=manual_risks(g)
    out=simplify_protected(g,.75,r,guards,settings())
    assert len(out['geometry'].geoms)==2 and out['geometry'].equals(g)


def analytic_case(name):
    mask=np.ones((32,32),dtype=np.uint8);mask[:2]=0;mask[-2:]=0;mask[:,:2]=0;mask[:,-2:]=0
    if name in ('central_hole','multiple_pores','close_pores','concave_pore'):
        mask[8:14,8:14]=0
        if name=='multiple_pores':mask[18:24,18:24]=0
        if name=='close_pores':mask[8:14,15:21]=0
        if name=='concave_pore':mask[12:18,12:20]=0
    elif name in ('one_pixel_neck','two_pixel_neck','diagonal_neck','protected_junction'):
        mask[:]=0;mask[8:18,2:12]=1;mask[8:18,20:30]=1
        width=2 if name=='two_pixel_neck' else 1
        mask[12:12+width,12:20]=1
        if name=='diagonal_neck':
            mask[12:16,11:13]=1;mask[14:16,12:22]=1
        if name=='protected_junction':mask[3:14,15:17]=1
    elif name=='exterior_channel':mask[2:18,15:16]=0
    elif name=='repair_next_strut':mask[8:16,8:16]=0;mask[16:24,16:24]=0;mask[24:29,15:16]=0
    elif name=='repair_next_exterior':mask[2:12,2:12]=0;mask[12:22,12:22]=0;mask[12:20,2:12]=0
    elif name=='multiple_repairs':
        mask[6:12,6:12]=0;mask[12:18,12:18]=0;mask[18:24,18:24]=0
    else:raise AssertionError(name)
    exact=convert_exact(mask);q=qualify_manifold_geometry(mask,exact,'solid_separate_contacts')
    assert q['geometry'] is not None
    g=q['geometry'];f=fixture(g);f.update(exact=exact['geometry'],mask=mask,qualification=q)
    return f


@pytest.mark.parametrize('name',['central_hole','multiple_pores','close_pores','concave_pore',
    'one_pixel_neck','two_pixel_neck','diagonal_neck','protected_junction','exterior_channel',
    'repair_next_strut','repair_next_exterior','multiple_repairs'])
def test_real_guard_detection_preserves_analytic_features(name):
    f=analytic_case(name);cfg=settings();risks=prepare_risks(f,cfg)
    guards=build_guards(risks,.75,cfg,32)
    assert guards['records']
    out=simplify_protected(f['baseline'],.75,risks,guards,cfg)
    assert out['geometry'] is not None and inspect_boundary(out['geometry'])['manifold']
    assert protected_integrity(f['baseline'],out['geometry'],risks,guards)['passed']
    assert np.array_equal(f['mask'],rasterize_exact_geometry(out['geometry'],32))
    assert len(out['geometry'].interiors)==len(f['baseline'].interiors)


def test_subpixel_diamond_and_multiple_influence_guards_keep_both_interfaces():
    f=analytic_case('multiple_repairs');cfg=settings();r=prepare_risks(f,cfg)
    assert len(r['features']['repairs'])==2
    g1=build_guards(r,.2,cfg,32);g2=build_guards(r,.75,cfg,32)
    repairs1=[g for g in g1['records'] if g['kind']=='repair'];repairs2=[g for g in g2['records'] if g['kind']=='repair']
    assert all(a['geometry'].covered_by(b['geometry']) for a,b in zip(repairs1,repairs2))
    out=simplify_protected(f['baseline'],.75,r,g2,cfg)
    for guard in repairs2:
        assert f['baseline'].boundary.intersection(guard['geometry']).equals(out['geometry'].boundary.intersection(guard['geometry']))


def test_full_qualification_and_corrupt_candidate_rejection(tmp_path):
    f=fixture(box(2,2,28,28));cfg=settings();cache=DescriptorCache(tmp_path/'cache')
    cfg['b1_config']['resolution']=256
    context=context_for(f,cfg['b1_config'],cache);r,guards=manual_risks(f['baseline'])
    engine=simplify_protected(f['baseline'],0,r,guards,cfg)
    good,_=qualify(f,engine['geometry'],context,r,guards,engine,cfg,cache)
    assert good['accepted_geometric_screen'] and good['disposition']=='ACCEPTED_NOOP'
    bad,_=qualify(f,box(3,3,27,27),context,r,guards,engine,cfg,cache)
    assert not bad['accepted_geometric_screen']
    assert {'ring_chain_certificate','raster_exact','removed_material'} <= set(bad['failed_constraints'])
    restored=fallback_engine(engine,r)
    again,_=qualify(f,f['baseline'],context,r,guards,restored,cfg,cache)
    assert again['accepted_geometric_screen']


@pytest.mark.parametrize('damage',['delete_hole','merge_holes','sever_corridor','point_contact'])
def test_global_hard_constraints_reject_topological_damage(damage,tmp_path):
    cfg=settings();cfg['b1_config']['resolution']=256
    if damage in ('delete_hole','merge_holes'):
        g=Polygon(box(2,2,30,30).exterior.coords,[box(6,8,12,14).exterior.coords,box(14,8,20,14).exterior.coords])
        bad=box(2,2,30,30) if damage=='delete_hole' else Polygon(box(2,2,30,30).exterior.coords,[box(6,8,20,14).exterior.coords])
    elif damage=='sever_corridor':
        g=shapely.union_all([box(2,8,12,18),box(12,12,20,14),box(20,8,30,18)])
        bad=shapely.union_all([box(2,8,12,18),box(20,8,30,18)])
    else:
        g=box(2,2,30,30);bad=Polygon(g.exterior.coords,[box(6,6,12,12).exterior.coords,box(12,12,18,18).exterior.coords])
    f=fixture(g);cache=DescriptorCache(tmp_path/'cache');ctx=context_for(f,cfg['b1_config'],cache)
    r,guards=manual_risks(g);engine=simplify_protected(g,0,r,guards,cfg)
    report,_=qualify(f,bad,ctx,r,guards,engine,cfg,cache)
    assert report['disposition']=='REJECTED_CANDIDATE'
    assert not report['gates']['continuous_topology'] or not report['gates']['manifold']


def test_deterministic_independent_nonmonotonic_trial_order():
    g=stairs();r,guards=manual_risks(g);cfg=settings();before=g.wkb
    first={epsilon:simplify_protected(g,epsilon,r,guards,cfg)['geometry'].wkb for epsilon in (.75,.2,.5)}
    second={epsilon:simplify_protected(g,epsilon,r,guards,cfg)['geometry'].wkb for epsilon in (.5,.75,.2)}
    assert first==second and g.wkb==before


def test_positive_width_link_without_raster_equivalence_cannot_pass(tmp_path):
    f=analytic_case('one_pixel_neck');f['mask']=np.pad(f['mask'],((0,224),(0,224)))
    cfg=settings();cfg['b1_config']['resolution']=256
    r=prepare_risks(f,cfg);guards=build_guards(r,.5,cfg,256)
    engine=simplify_protected(f['baseline'],0,r,guards,cfg)
    cache=DescriptorCache(tmp_path/'cache');ctx=context_for(f,cfg['b1_config'],cache)
    candidate=f['baseline'].difference(box(15,12,16,13))
    report,_=qualify(f,candidate,ctx,r,guards,engine,cfg,cache)
    assert not report['gates']['guard_exact'] and not report['accepted_geometric_screen']


def test_prospective_development_and_holdouts_are_disjoint_and_frozen():
    cfg=settings()
    assert len(cfg['development'])==len(cfg['holdouts'])==5
    assert not set(cfg['development']) & set(cfg['holdouts'])
    assert cfg['limits']['max_displacement']!=.5
    assert cfg['limits']['max_width_loss']==0


def test_positive_but_too_close_pores_fail_clearance_floor(tmp_path):
    g=Polygon(box(2,2,30,30).exterior.coords,[box(6,8,12,14).exterior.coords,box(14,8,20,14).exterior.coords])
    bad=Polygon(box(2,2,30,30).exterior.coords,[box(6,8,13.9,14).exterior.coords,box(14,8,20,14).exterior.coords])
    cfg=settings();cfg['b1_config']['resolution']=256;f=fixture(g)
    cache=DescriptorCache(tmp_path/'cache');ctx=context_for(f,cfg['b1_config'],cache)
    r,guards=manual_risks(g);engine=simplify_protected(g,0,r,guards,cfg)
    report,_=qualify(f,bad,ctx,r,guards,engine,cfg,cache)
    assert report['gates']['manifold'] and report['gates']['continuous_topology']
    assert not report['gates']['near_contact_floor']


def test_manifold_but_narrowed_diamond_fails_repair_clearance(tmp_path):
    from metamaterial_eval.geometry.manifold.candidates import CandidateSettings
    f=analytic_case('multiple_repairs');original=convert_exact(f['mask'])
    bad=qualify_manifold_geometry(f['mask'],original,'solid_separate_contacts',CandidateSettings(radius=.125))['geometry']
    f['mask']=np.pad(f['mask'],((0,224),(0,224)));cfg=settings();cfg['b1_config']['resolution']=256
    cache=DescriptorCache(tmp_path/'cache');ctx=context_for(f,cfg['b1_config'],cache)
    r=prepare_risks(f,cfg,ctx['features']);guards=build_guards(r,.5,cfg,256)
    engine=simplify_protected(f['baseline'],0,r,guards,cfg)
    report,_=qualify(f,bad,ctx,r,guards,engine,cfg,cache)
    assert report['gates']['manifold']
    assert not report['gates']['repair_patch_and_clearance'] and not report['gates']['guard_exact']


def test_undefined_repair_tracking_is_rejection_not_pass(tmp_path):
    f=analytic_case('multiple_repairs');f['mask']=np.pad(f['mask'],((0,224),(0,224)))
    cfg=settings();cfg['b1_config']['resolution']=256;cache=DescriptorCache(tmp_path/'cache')
    ctx=context_for(f,cfg['b1_config'],cache);r=prepare_risks(f,cfg,ctx['features']);guards=build_guards(r,.5,cfg,256)
    engine=simplify_protected(f['baseline'],0,r,guards,cfg)
    report,_=qualify(f,box(2,2,30,30),ctx,r,guards,engine,cfg,cache)
    assert report['metrics']['features']['undefined_repair_clearance_count']==2
    assert not report['gates']['repairs_defined_resolved'] and report['disposition']=='REJECTED_CANDIDATE'


def test_large_native_coordinate_raster_projection_has_no_floating_warnings():
    xy=np.asarray([point for i in range(25) for point in [(306.+i,960.-i),(306.+i,959.-i)]])
    with np.errstate(all='raise'):
        distances=vertex_distances(xy)
        hit,reason=fan_contains_cell_center(xy)
    assert np.isfinite(distances).all() and isinstance(hit,(bool,np.bool_))
