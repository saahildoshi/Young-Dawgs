"""Independent simplification, separate baselines and sensitivity failure detection."""
import hashlib
import json
from pathlib import Path
import numpy as np
import pytest
import shapely
from shapely import Polygon,MultiPolygon,box

from metamaterial_eval.geometry.sensitivity.simplification import simplify_diagnostic,validate_epsilon
from metamaterial_eval.geometry.sensitivity.metrics import area_comparison,continuous_topology,raster_comparison,complexity,void_partition
from metamaterial_eval.geometry.sensitivity.distance import BoundaryIndex,compare_boundaries
from metamaterial_eval.geometry.sensitivity.features import prepare_features,evaluate_features,chord_profile
from metamaterial_eval.geometry.sensitivity.analysis import evaluate_candidate
from metamaterial_eval.geometry.sensitivity.records import save_candidate,threshold_scan
from metamaterial_eval.geometry.sensitivity.sources import digest,load_fixture
from metamaterial_eval.geometry.manifold.contacts import inspect_boundary
from metamaterial_eval.geometry.planar import rasterize_exact_geometry

ROOT=Path(__file__).resolve().parents[1]
CONFIG=json.loads((ROOT/'docs/pipeline_v0.5/V0_5B1_PROTOCOL.json').read_text())


def toy():
    exact=Polygon([(0,0),(48,0),(48,48),(0,48)],
                  [[(8,8),(12,8),(12,12),(8,12)],[(12,12),(16,12),(16,16),(12,16)]])
    baseline=exact.union(Polygon([(11.75,12),(12,11.75),(12.25,12),(12,12.25)]))
    mask=rasterize_exact_geometry(exact,48)
    q={'changes':[{'contact_id':'repair0','xy':[12,12],'L1_radius':.25,'predicted_local_clearance':np.sqrt(2)/4}],
       'contact_report':{'contacts':[{'contact_id':'repair0','kind':'pore_pore_point','local_cells_NW_NE_SW_SE':[0,1,1,0]}]},
       'metrics':{'hausdorff_certified_for_registered_family':True,'boundary_hausdorff_distance':np.sqrt(2)/8}}
    fixture={'baseline':baseline,'exact':exact,'mask':mask,'qualification':q,
             'input_manifest':{'saved_topology_repair':{'bridges':[]}},'provenance':{'sha256':{'qualification':'toy'}}}
    config={**CONFIG,'resolution':48}
    features=prepare_features(fixture,config)
    context={'baseline_complexity':complexity(baseline),'baseline_index':BoundaryIndex(baseline),
             'exact_index':BoundaryIndex(exact),'baseline_void':void_partition(baseline,48),
             'baseline_raster':mask,'features':features,'baseline_repair_clearances':{'repair0':np.sqrt(2)/4}}
    return fixture,context,config


def test_zero_epsilon_is_byte_identical_clone():
    f,_,_=toy();g=f['baseline'];copy=simplify_diagnostic(g,0)
    assert copy is not g and shapely.to_wkb(copy)==shapely.to_wkb(g)


@pytest.mark.parametrize('epsilon',[-1,-.01,np.nan,np.inf,-np.inf,True,'0.1'])
def test_invalid_epsilon_rejected(epsilon):
    with pytest.raises(ValueError,match='finite nonnegative'):validate_epsilon(epsilon)


def test_independent_generation_and_immutable_sources():
    angles=np.linspace(0,2*np.pi,81)[:-1];g=Polygon(np.column_stack((10*np.cos(angles),10*np.sin(angles))))
    original=shapely.to_wkb(g)
    for epsilon in CONFIG['primary']['tolerances']:
        candidate=simplify_diagnostic(g,epsilon)
        expected=shapely.simplify(g,epsilon,preserve_topology=True) if epsilon else g
        assert shapely.to_wkb(candidate)==shapely.to_wkb(expected)
        assert shapely.to_wkb(g)==original


def test_identical_diagnostics_and_serialization_are_deterministic():
    f,context,c=toy();g=simplify_diagnostic(f['baseline'],.2)
    a,_=evaluate_candidate(f,g,context,c);b,_=evaluate_candidate(f,g,context,c)
    a.pop('timing');b.pop('timing');assert a==b
    assert shapely.to_wkb(g,byte_order=1)==shapely.to_wkb(simplify_diagnostic(f['baseline'],.2),byte_order=1)


def test_ogc_valid_contact_return_is_nonmanifold_and_repair_damage():
    f,context,c=toy();g=f['exact']
    assert g.is_valid and not inspect_boundary(g)['manifold']
    report,_=evaluate_candidate(f,g,context,c)
    assert report['events']['nonmanifold']
    assert report['events']['repair_unresolved'] and report['events']['repair_clearance_below_baseline']
    repair=report['features']['repairs'][0]
    assert repair['clearance']==0 and not repair['local_solid_link']['connected']
    assert repair['retained_added_fraction']==0
    assert report['raster_from_canonical']['xor_pixels']==0


def test_hole_loss_and_merge_correspondences():
    source=Polygon(box(0,0,20,20).exterior,[box(3,3,6,6).exterior,box(8,3,11,6).exterior])
    lost=Polygon(box(0,0,20,20).exterior,[box(3,3,6,6).exterior])
    merged=Polygon(box(0,0,20,20).exterior,[box(3,3,11,6).exterior])
    a=continuous_topology(source,lost,20);b=continuous_topology(source,merged,20)
    assert a['hole_correspondence']['lost_reference_regions']==[1]
    assert b['hole_correspondence']['merged_candidate_regions']==[0]
    assert not a['preserved'] and not b['preserved']


def test_component_split_and_exterior_channel_closure():
    source=box(0,0,20,20)
    split=MultiPolygon([box(0,0,9,20),box(11,0,20,20)])
    t=continuous_topology(source,split,20)
    assert t['solid_correspondence']['split_reference_regions']==[0]
    open_channel=source.difference(box(8,0,12,12))
    closed=Polygon(source.exterior,[box(8,3,12,12).exterior])
    t=continuous_topology(open_channel,closed,20)
    assert t['exterior_channel_closures']


def test_narrow_ligament_damage_and_local_width_measurement():
    base=box(0,0,20,4);narrow=box(0,0,20,2)
    assert chord_profile(base,[10,1],[0,1])['width']==4
    assert chord_profile(narrow,[10,1],[0,1])['width']==2
    f,context,c=toy();report,_=evaluate_candidate(f,f['exact'],context,c)
    assert report['features']['any_material_repair_risk']


def test_actual_added_removed_symmetric_areas_and_distinct_baselines():
    a=box(0,0,2,2);b=box(1,0,3,2);d=area_comparison(a,b)
    assert d['signed_area_change']==0 and d['added_solid_area']==2 and d['removed_solid_area']==2
    assert d['symmetric_difference_area']==4
    f,context,c=toy();report,_=evaluate_candidate(f,f['baseline'],context,c)
    assert report['area_from_manifold']['symmetric_difference_area']==0
    assert report['area_from_exact']['symmetric_difference_area']==.0625


def test_indexed_boundary_distance_bounds():
    a=BoundaryIndex(box(0,0,3,3));b=BoundaryIndex(box(.2,0,3.2,3))
    result=compare_boundaries(a,b)
    assert result['measured_hausdorff_lower']==pytest.approx(.2)
    assert result['continuous_hausdorff_upper']>=.2
    assert result['continuous_hausdorff_upper']-result['measured_hausdorff_lower']<=.125+1e-12
    assert compare_boundaries(a,a,equal=True)['continuous_hausdorff_upper']==0


def test_raster_coordinates_fp_fn_and_xor():
    source=np.zeros((16,16),dtype=np.uint8);source[2:5,9:13]=1
    rec=rasterize_exact_geometry(box(9,2,13,5),16)
    assert np.array_equal(source,rec)
    rec=rec.copy();rec[0,0]=1;rec[2,9]=0
    d=raster_comparison(source,rec)
    assert d['false_positive_pixels']==d['false_negative_pixels']==1 and d['xor_pixels']==2


def test_invalid_candidate_is_saved_without_repair(tmp_path):
    f,context,c=toy();bad=Polygon([(2,2),(6,6),(2,6),(6,2)])
    report,rec=evaluate_candidate(f,bad,context,c)
    assert not report['validity']['ogc_valid'] and not report['area_from_manifold']['defined']
    saved=save_candidate(tmp_path/'bad',bad,report,rec)
    assert (tmp_path/'bad/diagnostic_candidate.wkb').exists()
    assert (tmp_path/'bad/DIAGNOSTIC_FLAGS.json').exists()
    assert not shapely.from_wkb((tmp_path/'bad/diagnostic_candidate.wkb').read_bytes()).is_valid
    assert rec is None and saved['production_accepted'] is False


def test_missing_candidate_file_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError,match='Required saved geometry/provenance artifact missing'):
        digest(tmp_path/'manifold_candidate.wkb')


def test_saved_ordinary_and_regularized_sources_and_historical_hashes():
    for name in ('design_000_seed_000','design_009_seed_001'):
        f=load_fixture(ROOT,CONFIG,name)
        before=shapely.to_wkb(f['baseline']);exact=shapely.to_wkb(f['exact'])
        assert inspect_boundary(f['baseline'])['manifold']
        _=simplify_diagnostic(f['baseline'],.5)
        assert shapely.to_wkb(f['baseline'])==before and shapely.to_wkb(f['exact'])==exact
    p=ROOT/'experiments/pipeline_v0.5/manifold_qualification/run_001/protocol.json'
    for name,h in json.loads(p.read_text())['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==h,name


def test_threshold_report_no_failures_and_nonmonotonicity():
    rows=[{'epsilon':e,'events':{'never':False,'damage':v}} for e,v in [(0,False),(.1,True),(.2,False),(.35,True)]]
    report=threshold_scan(rows)
    assert report['never']['first_tested_failure'] is None
    assert report['damage']['observed_failure_bracket']==[0,.1]
    assert report['damage']['non_monotonic_observed'] and report['damage']['recovery_tolerances']==[.2]


def test_descriptor_cache_reuses_only_verified_identical_rasters(tmp_path):
    from metamaterial_eval.geometry.sensitivity.morphology import DescriptorCache
    calls=[]
    def fake(mask):calls.append(mask.copy());return {'raw':{'shape':list(mask.shape)}}
    cache=DescriptorCache(tmp_path,max_entries=2,evaluate=fake)
    mask=np.ones((8,8),dtype=np.uint8)
    _,a=cache.get(mask);_,b=cache.get(mask.copy())
    assert not a['reused'] and b['reused'] and len(calls)==1
    changed=mask.copy();changed[0,0]=0;cache.get(changed)
    assert len(calls)==2 and cache.evaluator_hash


def test_persisted_descriptor_cache_reuse_has_provenance(tmp_path):
    from metamaterial_eval.geometry.sensitivity.morphology import DescriptorCache
    calls=[]
    def fake(mask):calls.append(1);return {'raw':{'shape':list(mask.shape)}}
    mask=np.ones((8,8),dtype=np.uint8)
    DescriptorCache(tmp_path,evaluate=fake).get(mask)
    _,p=DescriptorCache(tmp_path,evaluate=fake).get(mask.copy())
    assert len(calls)==1 and p['reuse_kind']=='verified_disk_raster_and_configuration_hash'


def test_empty_valid_polygon_records_collapse_hole_and_raster_losses():
    f,context,c=toy();result,rec=evaluate_candidate(f,Polygon(),context,c)
    assert result['validity']['ogc_valid'] and result['events']['geometry_collapse']
    assert result['events']['hole_topology_change'] and result['events']['continuous_connectivity_change']
    assert result['raster_from_canonical']['component_count']==0
    assert not rec.any() and result['area_from_manifold']['removed_solid_area']==f['baseline'].area


def test_fixed_roi_and_unchanged_feature_diagnostics():
    f,context,c=toy();p=context['features']['repairs'][0]
    assert p['roi_bounds']==[11,11,13,13]
    result,_=evaluate_candidate(f,f['baseline'],context,c)
    feature=result['features']['repairs'][0]
    assert feature['retained_added_fraction']==1 and feature['local_symmetric_difference_area']==0
    assert feature['contact_remains_resolved'] and not feature['material_repair_risk_flag']


def test_complexity_keeps_exterior_and_hole_vertices_separate():
    g=Polygon(box(0,0,10,10).exterior,[box(2,2,4,4).exterior]);c=complexity(g)
    assert c['exterior_vertices']==4 and c['hole_vertices']==4 and c['vertices']==8
    assert c['total_rings']==2


def test_study_refuses_historical_locations_and_overwrites(tmp_path):
    from metamaterial_eval.geometry.sensitivity.study import register
    root=tmp_path/'repo';existing=root/'experiments/pipeline_v0.5/simplification_sensitivity/old'
    existing.mkdir(parents=True);marker=existing/'sentinel';marker.write_text('preserve')
    with pytest.raises(FileExistsError):register(existing,root)
    with pytest.raises(ValueError):register(root/'experiments/pipeline_v0.4',root)
    assert marker.read_text()=='preserve'


def test_unknown_threshold_metrics_are_not_recovered_passes():
    rows=[{'epsilon':e,'events':{'damage':v}} for e,v in [(0,False),(.1,True),(.2,None),(.35,True)]]
    report=threshold_scan(rows)
    assert not report['damage']['non_monotonic_observed']
