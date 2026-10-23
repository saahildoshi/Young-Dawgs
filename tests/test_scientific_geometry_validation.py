"""Analytic and adversarial controls for C; no producer gate expectations changed."""
import hashlib
import json
import math
import numpy as np
import pytest
import shapely
from shapely import Polygon, MultiPolygon, box, LineString
from shapely.affinity import translate
from metamaterial_eval.geometry.validation.checks import (
    serialization_check, coordinate_geometry, rings, independent_raster, raster_metrics,
    boundary_integrity, area_difference, boundary_distance, topology,
    region_correspondence, probe_width, select_probes, feature_audit,
    authenticate, provenance_check, area_gates, acceptance)
from metamaterial_eval.geometry.manifold.candidates import qualify_manifold_geometry
from metamaterial_eval.geometry.conversion import convert_exact

LIMITS={'max_added_fraction':.0025,'max_removed_fraction':.0025,'max_symmetric_fraction':.005,'area_allowance':1e-10}


def perforated(holes):return Polygon(box(0,0,10,10).exterior.coords,[h.exterior.coords for h in holes])


def checker():
    a=np.ones((256,256),np.uint8);a[2:4,2:4]=0;a[4:6,4:6]=0
    e=convert_exact(a);q=qualify_manifold_geometry(a,e,'solid_separate_contacts')
    return a,e,q


def test_exact_raster_cell():
    m,t=independent_raster(box(1,2,2,3),5);assert m.sum()==1 and m[2,1]==1 and t==0


def test_ordinary_manifold_roundtrip(tmp_path):
    g=box(0,0,10,10);assert serialization_check(g,tmp_path)['passed'] and boundary_integrity(g)['passed']


@pytest.mark.parametrize('holes',[[box(2,2,3,3)],[box(2,2,3,3),box(6,6,7,7)]])
def test_enclosed_holes(holes):
    g=perforated(holes);assert serialization_check(g)['holes']==len(holes) and topology(g,g,10)['passed']


def test_inherent_contact_not_manifold():
    a,e,q=checker();assert not boundary_integrity(e['geometry'])['passed']


def test_correct_regularization():
    a,e,q=checker();assert q['accepted'] and boundary_integrity(q['geometry'])['passed']


def test_removed_regularization_detected():
    a,e,q=checker();assert area_difference(q['geometry'],e['geometry'])['removed']>0
    assert not boundary_integrity(e['geometry'])['passed']


def test_narrow_bridge():
    g=shapely.union_all([box(0,0,3,3),box(5,0,8,3),box(3,1.4,5,1.6)])
    assert probe_width(g,[4,1.5],1,'solid',8)==pytest.approx(.2)


def test_subpixel_severance_same_raster():
    g=box(0,0,8,8);b=g.difference(box(3.9,0,4.1,8))
    assert not topology(g,b,8)['passed']
    assert np.array_equal(independent_raster(g,8)[0],independent_raster(b,8)[0])


def test_pore_merge():
    g=perforated([box(2,2,4,4),box(5,2,7,4)]);b=perforated([box(2,2,7,4)])
    assert not topology(g,b,10)['holes']['passed']


def test_pore_split():
    assert not topology(perforated([box(2,2,7,4)]),perforated([box(2,2,4,4),box(5,2,7,4)]),10)['passed']


def test_small_pore_deletion():
    assert not topology(perforated([box(2,2,2.1,2.1)]),box(0,0,10,10),10)['passed']


def test_pore_addition():
    assert not topology(box(0,0,10,10),perforated([box(2,2,2.1,2.1)]),10)['passed']


def test_external_channel_closed():
    g=box(0,0,10,10).difference(box(4,0,6,8));b=g.union(box(4,1,6,2))
    assert not topology(g,b,10)['passed']


def test_external_channel_narrowed():
    a=box(0,0,10,10).difference(box(4,0,6,8));b=a.union(box(4,2,4.2,7))
    assert topology(a,b,10)['passed']
    assert probe_width(b,[5,4],0,'void',10)<probe_width(a,[5,4],0,'void',10)


def test_equal_net_large_redistribution():
    d=area_difference(box(0,0,10,10),box(1,0,11,10));assert d['net_area']==0 and d['symmetric']==20


def test_zero_xor_nonzero_vector_difference():
    a=box(0,0,10,10);b=box(.1,0,10.1,10)
    assert np.array_equal(independent_raster(a,12)[0],independent_raster(b,12)[0])
    assert area_difference(a,b)['symmetric']>0


@pytest.mark.parametrize('shift,pass_limit',[(.25,True),(.8,False)])
def test_known_displaced_edge_limit(shift,pass_limit):
    a=box(1,1,5,5);b=translate(a,xoff=shift);d=boundary_distance(a,b)
    assert d['lower']==pytest.approx(shift)
    assert (d['upper']<=math.sqrt(.5)+1e-10)==pass_limit


def test_parallel_shifted_segments():
    from metamaterial_eval.geometry.validation.checks import directed_bound
    d=directed_bound(LineString([(0,0),(4,0)]),LineString([(0,.4),(4,.4)]))
    assert d['lower']==pytest.approx(.4) and d['upper']>=.4


def test_staircase_triangle_bound():
    a=Polygon([(0,0),(4,0),(4,4),(3,4),(3,3),(2,3),(2,2),(1,2),(1,1),(0,1)])
    b=Polygon([(0,0),(4,0),(4,4)])
    d=boundary_distance(a,b);assert d['lower']>0 and d['upper']>=d['lower']


def test_area_budget_exceeded():
    assert not all(area_gates(box(0,0,10,10),box(1,0,11,10),LIMITS).values())


def test_protected_coordinate_change_detected():
    g=box(0,0,10,10); assert not serialization_check(g,reloaded=translate(g,xoff=.001))['passed']


def test_missing_repair_metadata_gate():
    assert acceptance({'repair_metadata_complete':False})['scientific_status']=='HOLD'


def test_invalid_serialization():
    with pytest.raises(shapely.errors.GEOSException):shapely.from_wkb(b'not geometry')


def test_orientation_reversal():
    g=box(0,0,10,10);b=Polygon(list(g.exterior.coords)[::-1])
    assert g.equals(b) and not serialization_check(g,reloaded=b)['passed']


def test_duplicate_edges():
    g=Polygon([(0,0),(2,0),(2,2),(0,2),(0,0),(2,0),(0,0)])
    assert boundary_integrity(g)['duplicate_edges']>0 and not boundary_integrity(g)['passed']


def test_unexpected_component():
    a=box(0,0,8,8);b=MultiPolygon([a,box(9,9,10,10)])
    assert not topology(a,b,12)['solid']['passed']


def test_pore_shape_changes_even_area_equal():
    a=perforated([box(2,2,4,4)]);b=perforated([box(2,2,3,6)])
    t=topology(a,b,10);assert t['holes']['passed']
    assert t['holes']['records'][0]['relative_area_distortion']==0 and t['holes']['records'][0]['symmetric_area']>0


def test_wrong_similar_area_pore_identity():
    p=[box(1,1,2,2),box(5,5,6,6)];q=[box(3,1,4,2),box(7,5,8,6)]
    assert not region_correspondence(p,q)['passed']


def test_narrow_feature_outside_guards():
    a=box(0,0,10,10).difference(box(4,0,6,8));b=a.union(box(4,2,4.2,7))
    m=independent_raster(a,10)[0];probes=[{'xy':[5,4],'axis':0,'phase':'void'}]
    f=feature_audit(a,b,m,box(0,0,1,1),probes)
    assert f['narrowed_probes']==1 and not f['independent_probes'][0]['guarded_center']


def test_unsupported_contact_quarantined():
    mask=np.zeros((8,8),np.uint8);mask[1:3,1:3]=1;mask[3:5,3:5]=1
    q=qualify_manifold_geometry(mask,convert_exact(mask),'solid_separate_contacts')
    assert not q['accepted']


def test_already_manifold_no_repair():
    mask=np.ones((8,8),np.uint8);q=qualify_manifold_geometry(mask,convert_exact(mask),'solid_separate_contacts')
    assert q['accepted'] and q['geometry'].area==64


def test_accepted_noop():
    a=box(0,0,10,10);assert area_difference(a,a)['symmetric']==0 and acceptance({'identity':True})['hard_gate_pass']


def test_valid_changed_candidate():
    a=box(0,0,100,100);b=box(.001,0,100.001,100)
    assert all(area_gates(a,b,LIMITS).values()) and boundary_integrity(b)['passed']


def test_failed_candidate_aggregation():
    assert acceptance({'raster':True,'continuous':False})['failed_gates']==['continuous']


def test_nonmonotonic_settings_no_best_of_selection():
    # Each independently requested configuration survives aggregation, including
    # stress configurations with smaller reduction than the lower tolerance.
    rows=[{'epsilon':.5,'reduction':9.},{'epsilon':.75,'reduction':6.}]
    assert [acceptance({'reduction_positive':r['reduction']>0})['hard_gate_pass'] for r in rows]==[True,True]
    assert rows[1]['reduction']<rows[0]['reduction']


def test_deterministic_metric_repeat():
    a=box(1,1,4,4);b=translate(a,xoff=.2)
    assert boundary_distance(a,b)==boundary_distance(a,b)


def test_tampered_source_hash(tmp_path):
    p=tmp_path/'mask.npy';p.write_bytes(b'original');h=hashlib.sha256(p.read_bytes()).hexdigest();authenticate(p,h)
    p.write_bytes(b'tampered')
    with pytest.raises(ValueError):authenticate(p,h)


def test_missing_provenance():
    assert not provenance_check({'source_path':'x','resolution':1024})


def test_malformed_coordinate_ownership():
    records=rings(box(0,0,10,10));records[0]['role']='hole'
    with pytest.raises(ValueError):coordinate_geometry(records)


def test_unclosed_coordinate_serialization():
    records=rings(box(0,0,10,10));records[0]['xy']=records[0]['xy'][:-1]
    with pytest.raises(ValueError):coordinate_geometry(records)


def test_raster_topology_and_iou():
    m=np.ones((8,8),np.uint8);q=raster_metrics(m,m)
    assert q['xor']==0 and q['components']==1 and q['horizontal_percolation'] and q['iou']==1


def test_axis_probes_source_determinism():
    m=np.ones((16,16),np.uint8);m[2:14,7:9]=0
    assert select_probes(m)==select_probes(m) and len(select_probes(m))>0
