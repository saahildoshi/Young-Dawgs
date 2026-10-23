"""v0.5A.1 source-link classification, candidate accounting and fail-closed gates."""
import hashlib
from pathlib import Path

import numpy as np
import pytest
import shapely
from shapely import Polygon, MultiPolygon, box

from metamaterial_eval.geometry import convert_exact
from metamaterial_eval.geometry.conversion import geometry_bytes
from metamaterial_eval.geometry.manifold import (
    CandidateSettings, classify_contacts, inspect_boundary, inspect_patches, qualify_manifold_geometry,
)
from metamaterial_eval.geometry.manifold.candidates import measure_candidate


def masks():
    solid=np.ones((48,48),dtype=np.uint8)
    square=solid.copy();square[8:12,8:12]=0;square[12:16,12:16]=0
    irregular=square.copy();irregular[7:10,7:10]=0;irregular[14:18,14:19]=0
    exterior=solid.copy();exterior[:12,:12]=0;exterior[12:16,12:16]=0
    one=solid.copy();one[8:16,8:16]=0;one[8:16,17:25]=0
    two=solid.copy();two[8:16,8:16]=0;two[8:16,18:26]=0
    diagonal=solid.copy();diagonal[8:16,8:16]=0;diagonal[16:24,17:25]=0
    concave=solid.copy();concave[8:20,8:12]=0;concave[16:20,8:22]=0
    ligament=solid.copy();ligament[5:43,5:22]=0;ligament[5:43,23:43]=0
    multiple=square.copy();multiple[30:34,30:34]=0;multiple[34:38,34:38]=0
    cluster=solid.copy();cluster[12,12]=0;cluster[13,13]=0;cluster[14,12]=0
    near_border=solid.copy();near_border[:2,:2]=0;near_border[2:5,2:5]=0
    return {'square_pores':square,'irregular_pores':irregular,'alternating_sectors':square,
            'hole_exterior':exterior,'one_pixel_separation':one,'two_pixel_separation':two,
            'diagonal_strut':diagonal,'pinched_exterior':exterior,'concave_hole':concave,
            'long_thin_ligament':ligament,'multiple_defects':multiple,'adjacent_cluster':cluster,
            'near_border':near_border,'domain_corner_valid':solid,'ordinary_manifold':one}


@pytest.mark.parametrize('name,mask',masks().items())
def test_synthetic_preserve_and_optional_candidates(name,mask):
    original=mask.copy();exact=convert_exact(mask)
    original_doc=geometry_bytes(exact['document']);wkb=shapely.to_wkb(exact['geometry'],byte_order=1)
    contacts=classify_contacts(mask,exact)
    assert contacts['classification_pass']
    preserve=qualify_manifold_geometry(mask,exact)
    assert preserve['state']=='exact_geometry'
    assert preserve['metrics']['symmetric_difference_area']==0
    assert preserve['metrics']['continuous_equivalent']
    assert preserve['comparison']['exact_equal']
    assert preserve['status']==('exact_nonmanifold' if contacts['contacts'] else 'exact_manifold')
    result=qualify_manifold_geometry(mask,exact,'solid_separate_contacts')
    assert result['accepted'],(name,result['failed_gates'])
    assert result['boundary']['manifold'] and result['geometry'].is_valid
    assert result['comparison']['xor_pixels']==0
    assert result['metrics']['geometry_before']['holes']==result['metrics']['geometry_after']['holes']
    n=len(contacts['contacts'])
    assert result['metrics']['symmetric_difference_area']==pytest.approx(.0625*n)
    assert result['metrics']['signed_area_change']==pytest.approx(.0625*n)
    assert result['metrics']['maximum_local_boundary_displacement']==pytest.approx(.25/np.sqrt(2) if n else 0)
    if n:
        assert result['state']=='manifold_candidate'
        assert not result['metrics']['continuous_equivalent']
        assert all(f['local_minimum_clearance']==pytest.approx(.25*np.sqrt(2)) for f in result['metrics']['features'])
        assert all(f['subpixel_feature_introduced'] for f in result['metrics']['features'])
    else:
        assert result['status']=='ACCEPT_NOOP'
        assert shapely.to_wkb(result['geometry'],byte_order=1)==wkb
    repeat=qualify_manifold_geometry(mask,exact,'solid_separate_contacts')
    assert shapely.to_wkb(repeat['geometry'],byte_order=1)==shapely.to_wkb(result['geometry'],byte_order=1)
    assert result['metrics']==repeat['metrics']
    assert geometry_bytes(exact['document'])==original_doc
    assert shapely.to_wkb(exact['geometry'],byte_order=1)==wkb
    np.testing.assert_array_equal(mask,original)


def test_inherent_sectors_and_ogc_valid_nonmanifold():
    mask=masks()['square_pores'];exact=convert_exact(mask);c=classify_contacts(mask,exact)['contacts'][0]
    assert exact['geometry'].is_valid
    assert c['kind']=='pore_pore_point' and c['boundary_link_degree']==4
    assert c['local_cells_NW_NE_SW_SE']==[0,1,1,0]
    assert c['local_solid_4_components']==2
    assert c['local_void_4_components']==2 and c['local_void_8_components']==1
    assert c['inherent_in_source'] and not c['representation_only_resolution']
    assert c['geometric_change_required'] and c['source_walk_repeats_vertex']


def test_hole_shell_and_pore_only_policy_quarantine():
    mask=masks()['hole_exterior'];exact=convert_exact(mask)
    c=classify_contacts(mask,exact)['contacts'][0]
    assert c['kind']=='hole_shell_point' and c['void_connects_exterior_8']
    assert c['pinched_exterior_boundary']
    result=qualify_manifold_geometry(mask,exact,'solid_separate_pores')
    assert result['status']=='REJECT_UNSUPPORTED_CONTACT'
    assert result['geometry'] is None


def test_diagonal_solids_do_not_silently_merge_components():
    mask=np.zeros((48,48),dtype=np.uint8);mask[8:16,8:16]=1;mask[16:24,16:24]=1
    exact=convert_exact(mask);contact=classify_contacts(mask,exact)['contacts'][0]
    assert contact['kind']=='diagonal_solid_point'
    assert contact['diagonal_solid_cell_contact'] and contact['diagonal_void_cell_contact']
    result=qualify_manifold_geometry(mask,exact,'solid_separate_contacts')
    assert result['status']=='REJECT_UNSUPPORTED_CONTACT' and result['geometry'] is None


def test_three_rings_and_six_boundary_branches():
    holes=[[(0,0),(2,0),(1,1),(0,0)],[(0,0),(-1,1),(-2,0),(0,0)],[(0,0),(0,-2),(1,-1),(0,0)]]
    geometry=Polygon([(-4,-4),(4,-4),(4,4),(-4,4),(-4,-4)],holes)
    result=inspect_boundary(geometry)
    c=next(c for c in result['contacts'] if c['xy']==[0,0])
    assert c['kind']=='multi_ring_contact_cluster'
    assert len(c['incident_rings'])==3 and c['boundary_link_degree']==6
    assert not result['manifold']


def test_self_touch_crossing_overlap_zero_and_duplicate_segments():
    rings=[{'role':'shell','xy':[(0,0),(2,0),(2,2),(0,2),(0,0),(-2,0),(-2,-2),(0,-2),(0,0)]}]
    result=inspect_boundary(rings=rings)
    assert any(c['kind']=='self_touching_loop' for c in result['contacts'])
    bowtie=Polygon([(0,0),(2,2),(0,2),(2,0),(0,0)])
    assert any(c['kind']=='self_intersection' for c in inspect_boundary(bowtie)['contacts'])
    ordinary={'role':'shell','xy':[(0,0),(3,0),(3,3),(0,3),(0,0)]}
    duplicates=inspect_boundary(rings=[ordinary,ordinary])
    assert len(duplicates['overlaps'])==4
    assert all(x['kind']=='duplicate_segment' for x in duplicates['overlaps'])
    overlapping={'role':'shell','xy':[(1,0),(4,0),(4,-2),(1,-2),(1,0)]}
    assert any(x['kind']=='overlapping_segments' for x in inspect_boundary(rings=[ordinary,overlapping])['overlaps'])
    zero={'role':'shell','xy':[(0,0),(3,0),(3,0),(3,3),(0,3),(0,0)]}
    result=inspect_boundary(rings=[zero]);assert result['zero_length_segments'] and not result['manifold']


def test_valid_shared_patch_edges_are_not_assembled_defects():
    parts=[box(0,0,2,2),box(2,0,4,2)]
    result=inspect_patches(parts)
    assert result['kind']=='valid_shared_decomposition_edges'
    assert result['internal_shared_edge_length']==2
    assert result['representation_only_correction'] and not result['blocks_manifold']
    assert result['assembled_geometry'].equals(box(0,0,4,2))


def test_numerical_near_contact_is_not_exact_contact():
    geometry=MultiPolygon([box(0,0,2,2),box(2+1e-7,0,4,2)])
    result=inspect_boundary(geometry,near_distance=1e-6)
    assert result['manifold'] and not result['contacts']
    assert result['near_contacts'][0]['distance']==pytest.approx(1e-7)
    assert result['exact_contact_tolerance']==0


def test_domain_corner_contact_in_general_geometry():
    geometry=MultiPolygon([Polygon([(0,0),(3,0),(1,1)]),Polygon([(0,0),(1,3),(0,3)])])
    result=inspect_boundary(geometry)
    assert any(c['xy']==[0,0] and c['boundary_link_degree']==4 for c in result['contacts'])


def test_adjacent_cluster_discovery():
    mask=masks()['adjacent_cluster'];contacts=classify_contacts(mask,convert_exact(mask))
    assert len(contacts['contacts'])==2
    assert len(contacts['contact_clusters'])==1
    assert len(contacts['contact_clusters'][0])==2


def test_area_budget_rejection_keeps_candidate_evidence():
    mask=masks()['square_pores'];exact=convert_exact(mask)
    result=qualify_manifold_geometry(mask,exact,'solid_separate_contacts',CandidateSettings(max_symmetric_difference_fraction=0))
    assert result['status']=='REJECT_CANDIDATE'
    assert 'area_budget' in result['failed_gates']
    assert result['geometry'] is not None and result['metrics']['added_solid_area']>0


def test_raster_change_rejection_independent_of_descriptor_similarity():
    mask=masks()['square_pores'];exact=convert_exact(mask);support=box(25,25,26,26)
    candidate=exact['geometry'].difference(support)
    result=measure_candidate(exact['geometry'],candidate,mask,support,[],CandidateSettings(),'diagnostic')
    assert not result['accepted'] and 'raster_exact' in result['failed_gates']
    assert result['comparison']['false_negative_pixels']==1


def test_new_narrow_ligament_is_measured_and_rejected_below_registered_floor():
    mask=masks()['square_pores'];exact=convert_exact(mask)
    result=qualify_manifold_geometry(mask,exact,'solid_separate_contacts',CandidateSettings(radius=.125))
    assert result['status']=='REJECT_CANDIDATE'
    assert 'clearance_floor' in result['failed_gates']
    assert result['metrics']['features'][0]['local_minimum_clearance']==pytest.approx(.125*np.sqrt(2))
    assert result['physical_feature_qualification']=='UNQUALIFIED'


def test_void_side_merges_pores_and_is_rejected():
    mask=masks()['square_pores'];result=qualify_manifold_geometry(mask,convert_exact(mask),'void_side_probe')
    assert result['geometry'].is_valid and result['boundary']['manifold']
    assert result['status']=='REJECT_CANDIDATE'
    assert 'hole_count_preserved' in result['failed_gates']
    assert result['metrics']['signed_area_change']==pytest.approx(-.0625)
    assert result['metrics']['geometry_after']['holes']==result['metrics']['geometry_before']['holes']-1


@pytest.mark.parametrize('settings',[CandidateSettings(radius=0),CandidateSettings(radius=.5),CandidateSettings(radius=float('nan')),
                                     CandidateSettings(max_displacement=-1)])
def test_invalid_configuration_rejected(settings):
    with pytest.raises(ValueError):settings.validate()


def test_exhaustive_small_mask_classification_and_unchanged_exact_behavior():
    for bits in range(1,512):
        mask=np.array([(bits>>i)&1 for i in range(9)],dtype=np.uint8).reshape(3,3)
        exact=convert_exact(mask);diagnosis=classify_contacts(mask,exact)
        assert exact['comparison']['xor_pixels']==0
        assert diagnosis['source_classifier_agreement'],bits
        assert diagnosis['manifold']==exact['validity']['manifold_boundary'],bits


def test_real_primary_contact_and_pass_through():
    root=Path(__file__).resolve().parents[1]
    for name,count in [('design_000/seed_000',1),('design_009/seed_001',0)]:
        path=root/'experiments/pipeline_v0.4.1/resolution_validation'/name/'1024/microstructure.npy'
        mask=np.load(path,allow_pickle=False);exact=convert_exact(mask)
        result=qualify_manifold_geometry(mask,exact,'solid_separate_contacts')
        assert result['accepted'],result['failed_gates']
        assert len(result['contact_report']['contacts'])==count
        assert result['metrics']['symmetric_difference_area']==.0625*count
        if count: assert result['contact_report']['contacts'][0]['xy']==[31,296]
        else: assert result['status']=='ACCEPT_NOOP' and result['metrics']['continuous_equivalent']


def test_geometry_serialization_preserves_candidate_and_exact_identity():
    mask=masks()['square_pores'];exact=convert_exact(mask)
    result=qualify_manifold_geometry(mask,exact,'solid_separate_contacts')
    payload=shapely.to_wkb(result['geometry'],byte_order=1)
    decoded=shapely.from_wkb(payload)
    from metamaterial_eval.geometry.planar import rasterize_exact_geometry
    np.testing.assert_array_equal(rasterize_exact_geometry(decoded,len(mask)),mask)
    assert decoded.equals(result['geometry'])
    assert not decoded.equals(exact['geometry'])


def test_historical_exact_source_hashes_remain_frozen():
    import json
    root=Path(__file__).resolve().parents[1]
    protocol=json.loads((root/'experiments/pipeline_v0.5/baseline_vectorization/run_003/protocol.json').read_text())
    for name,digest in protocol['sources_sha256'].items():
        assert hashlib.sha256((root/name).read_bytes()).hexdigest()==digest,name


def test_study_refuses_overwrites_and_nonstudy_paths(tmp_path):
    from metamaterial_eval.geometry.manifold.study import prepare,run
    root=tmp_path/'repository';output=root/'experiments/pipeline_v0.5/manifold_qualification/existing'
    output.mkdir(parents=True);marker=output/'sentinel';marker.write_text('preserve')
    with pytest.raises(FileExistsError):prepare(output,root)
    assert marker.read_text()=='preserve'
    with pytest.raises(ValueError):prepare(root/'experiments/pipeline_v0.4',root)


def test_policy_requires_explicit_known_name():
    mask=masks()['square_pores']
    with pytest.raises(ValueError,match='Unknown explicit'):
        qualify_manifold_geometry(mask,convert_exact(mask),'repair_automatically')
