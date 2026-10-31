"""Checks against actual licensed v241 artifacts, separate from synthetic unit tests."""
from pathlib import Path
import json
import re
import numpy as np
import pytest
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.solver_execution import file_hash

REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'experiments/pipeline_v0.6.6/run_001';BASE=artifact_root()/'solver/v066'
def read(p):return json.loads(Path(p).read_text())


@pytest.mark.parametrize('fixture',['rectangle','compliant'])
def test_actual_native_restart_preserves_both_loadsteps(fixture):
    q=read(RUN/'restart_validation/RESTART_VALIDATION.json')
    row=next(x for x in q['fixtures'] if x['fixture']==fixture)
    assert row['actual_rst_reopened'] and row['after_restart']['load_step']==2
    assert row['native_restart_point']['load_step']==1
    source=BASE/(fixture+'_restart_002')
    assert 'ANTYPE,STATIC,REST,1,' in (source/'input.inp').read_text()
    assert read(source/'execution_receipt.json')['process']['returncode']==0
    assert read(source/'restart_provenance.json')['source_never_modified']


@pytest.mark.parametrize('fixture',['rectangle','compliant'])
@pytest.mark.parametrize('field',['history','contact','displacements','stress'])
def test_actual_continuous_and_restarted_fields_agree(fixture,field):
    a=BASE/(fixture+'_continuous_002_post003');b=BASE/(fixture+'_restart_002_post003')
    for i in [1,2]:
        x=np.loadtxt(a/f'stage{i:03d}_{field}.csv',delimiter=',',skiprows=1,ndmin=2)
        y=np.loadtxt(b/f'stage{i:03d}_{field}.csv',delimiter=',',skiprows=1,ndmin=2)
        assert x.shape==y.shape and np.all(np.max(abs(x-y),axis=0)/np.maximum(np.max(abs(x),axis=0),1e-12)<1e-5)


@pytest.mark.parametrize('fixture',['rectangle','compliant'])
def test_actual_cumulative_displacement_and_native_gate(fixture):
    model=read(BASE/(fixture+'_restart_002/simulation_manifest.json'))['model']
    for i,t in [(1,.0025),(2,.005)]:
        folder=BASE/(fixture+'_restart_002_post003')
        x=np.loadtxt(folder/f'stage{i:03d}_history.csv',delimiter=',',skiprows=1,ndmin=2)[0]
        assert abs(x[3]+model['config']['height']*t)<1e-10
        assert float((folder/f'stage{i:03d}_gate.txt').read_text().split(',')[0])==0


QUALIFICATIONS=sorted((RUN/'mechanical_results').glob('fine*_qualified*/state*/qualification.json'))
ACCEPTED=[p for p in QUALIFICATIONS if read(p)['accepted']]


@pytest.mark.parametrize('path',ACCEPTED,ids=lambda p:p.parent.parent.name+'_'+p.parent.name)
def test_actual_fine_checkpoint_all_fields_equilibrium_mapping_and_overlap(path):
    q=read(path);m=q['measurement'];assert q['accepted']
    assert m['reaction_balance_relative']<=.01 and m['upper_rf_y_N']<0<m['lower_rf_y_N']
    assert len(q['contacts'])==2
    for c in q['contacts']:
        assert c['closed_elements']>0 and c['max_stored_endpoint_pressure_MPa']>0
        assert c['max_stored_endpoint_penetration_mm']<=1e-5 and c['signed_opposition_residual_relative']<=.01
    assert q['actual_nodes']==2766505 and q['actual_TRI6']==1261670 and q['actual_native_corner_nodes']==752212
    assert q['invalid_deformed_mappings']==0 and q['minimum_deformed_determinant_mm2']>0
    assert q['boundary_screen_summary']['pore_loops']==412
    assert q['boundary_screen_summary']['passed'] or q.get('general_contact',{}).get('status')=='PASS_FULL_NATIVE_GENERAL_CONTACT_CHECKS'
    if q.get('actual_postsolution_general_contact_detection_keyopt4') is not None:assert q['actual_postsolution_general_contact_detection_keyopt4']==2
    export=Path(q['export'])
    for name,digest in q['raw_native_field_hashes'].items():assert file_hash(export/name)==digest
    assert read(export/'execution_receipt.json')['process']['returncode']==0


@pytest.mark.parametrize('path',QUALIFICATIONS,ids=lambda p:p.parent.parent.name+'_'+p.parent.name)
def test_rejected_states_cannot_enter_accepted_curve(path):
    q=read(path)
    assert not q['eligible_for_LLM_performance_ranking']
    if not q['accepted']:assert q['failures']


@pytest.mark.parametrize('name',['input.inp','compression.rst','compression.rdb','compression.r001','compression.ldhi','checkpoint.db'])
def test_authenticated_v065_parent_remains_byte_identical(name):
    expected=read(RUN/'audit/initial.json')['native_v065_authenticated_files'][name]
    p=artifact_root()/'solver/v065/full_recovery_001'/name
    assert p.stat().st_size==expected['bytes'] and file_hash(p)==expected['sha256']


def test_fine_restart_has_actual_native_lineage_and_no_memory_cap():
    source=BASE/'fine_stage01_001';r=read(source/'execution_receipt.json')
    assert 'ANTYPE,STATIC,REST,1,1,CONTINUE' in (source/'input.inp').read_text()
    assert r['solver_version']=='2024 R1' and r['converged_steps']
    assert r['process']['rss_limit_bytes'] is None
    prov=read(source/'restart_provenance.json')
    assert prov['source_never_modified'] and prov['copied_native_files']['compression.rst']['sha256']==read(RUN/'audit/initial.json')['native_v065_authenticated_files']['compression.rst']['sha256']


def test_smaller_mesh_is_not_misrepresented_as_qualified():
    c=read(RUN/'mesh_strategy/candidate_001.json')
    assert not c['quality']['accepted'] and c['quality']['min_angle_deg']<10
    assert c['status']=='REJECTED_ORIGINAL_GEOMETRY_GATES'


def test_actual_nodal_fixture_supports_contact_transmission():
    q=read(RUN/'internal_contact/NODAL_FIXTURE_QUALIFICATION.json')
    assert q['status']=='PASS_ACTUAL_NODAL_GC_INTERFACE_FORCE_PEN_MAPPING'
    assert q['actual_type_after_solution_verified'] and q['independent_RST_reopened']
    assert q['closed_GC_skins']==114 and q['native_pressure_max_MPa']>0
    assert q['all_quadratic_maps_positive']
    assert q['reaction_balance_relative']<=.01 and q['assembled_GC_force_residual_relative']<=.01
    assert q['stored_endpoint_penetration_max_mm']<=1e-5


def test_actual_full_general_contact_covers_every_exposed_face():
    q=read(RUN/'internal_contact/FULL_GC_SETUP_QUALIFICATION.json')
    assert q['status']=='PASS_NATIVE_FULL_GC_SETUP__MECHANICS_PENDING'
    assert q['native_skin_rows']==243576 and q['oriented_faces_matched']==243576
    assert q['missing_exposed_faces']==0 and q['actual_fine_structural_geometry_preserved']
    assert file_hash(BASE/'fine_gc_setup_001/gc_topology.csv')==q['native_gc_topology_sha256']


def test_actual_numeric_restart_retention_corrected_legacy_deviation():
    q=read(RUN/'restart_validation/RETENTION_QUALIFICATION.json')
    assert q['status']=='PASS_ACTUAL_FRESH_FIVE_SUBSTEP_NUMERIC_FREQUENCY'
    assert q['command']=='RESCONTROL,DELETE,ALL then RESCONTROL,DEFINE,ALL,1,-1,,3'


def test_actual_eight_core_license_and_fields_qualified():
    q=read(RUN/'performance/SMP_QUALIFICATION.json')
    assert q['selected_cores']==8
    assert any(a['requested_cores']==8 and a['passed'] for a in q['attempts'])


def test_gauss_one_percent_endpoint_crossings_are_quarantined():
    q=read(RUN/'mechanical_results/fine_gc_stage02_001_qualification001.json')
    assert not q['last_state_accepted'] and q['last_accepted']['state']['time']==pytest.approx(.00859375)
    assert not q['results'][-1]['accepted'] and q['results'][-1]['failures']
    d=read(RUN/'deformation/FULL_GC_ONE_PERCENT_EXACT_DIAGNOSIS.json')
    assert d['status']=='CONFIRMED_UNMODELED_CROSSING'


def test_actual_nodal_fixture_geometry_uses_native_constraints_and_rejects_known_crossings():
    q=read(RUN/'internal_contact/NODAL_FIXTURE_GEOMETRY_QUALIFICATION_002.json')
    assert q['status']=='PASS_ACTUAL_NODAL_FIXTURE_BOUNDED_CONTACT_GEOMETRY'
    assert q['candidate_records']==148 and len(q['explanations'])==148
    for name,digest in q['actual_native_field_hashes'].items():assert file_hash(BASE/'internal_fixture_enabled_003_post001'/name)==digest
    for record in q['explanations']:
        assert record.get('geometry_proof',{}).get('passed') or record.get('native_target_link_a_to_b') or record.get('native_target_link_b_to_a')
    protocol=read(RUN/'protocol/NODAL_CONTACT_INTERPRETATION_023.json')
    assert protocol['fixture_sha256']==file_hash(RUN/'internal_contact/NODAL_FIXTURE_GEOMETRY_QUALIFICATION_002.json')
    assert read(RUN/'internal_contact/NODAL_INTERPRETER_REJECTS_KNOWN_GP_CROSSINGS.json')['rejected']
