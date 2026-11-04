"""Read-only checks against licensed v0.6.8 native artifacts and rejection gates."""
import numpy as np
import pytest
from pathlib import Path

from scripts.v068_common import BASE, RUN, read, file_hash


def test_original_full_restart_still_matches_authenticated_parent():
    audit=read(RUN.parents[1]/'pipeline_v0.6.7/run_001/audit/INITIAL_AUTHENTICATION.json')
    for name,record in audit['parent_native_files'].items():
        assert file_hash(Path(audit['parent_source'])/name)==record['sha256']


@pytest.mark.parametrize('label',['track_A_expanded_nodal2_001','track_A_expanded_unified5_001'])
def test_original_mesh_local_force_proof_does_not_override_parent_hold(label):
    force=read(RUN/'track_A_local_fixture'/(label+'_interface_force.json'))
    assert force['states'] and all(s['passed'] for s in force['states'])
    q=read(RUN/'track_A_local_fixture'/(label+'_qualification.json'))
    assert q['status']=='HOLD_LOCAL_CONTEXT_OR_CONTACT'
    assert not q['parent_match_all_measured_states']


def test_unified_pair_native_fixture_and_installed_model():
    fixture=read(RUN/'track_B_contact_fixture/PAIR_UNIFIED5_FIXTURE_QUALIFICATION.json')
    setup=read(RUN/'track_B_contact_fixture/PAIR_UNIFIED5_SETUP_QUALIFICATION.json')
    assert fixture['status'].startswith('PASS')
    assert setup['status']=='PASS_NATIVE_PAIR_UNIFIED5_SETUP'
    assert setup['installed_pair_detection_keyopt4']==5
    assert file_hash(BASE/'track_B_pair_unified_setup_001/contact_model_pair_unified.db')==setup['native_database_sha256']


def test_complete_unified_pair_restart_is_independently_accepted():
    name='track_B_pair5_to_01200_001'
    q=read(RUN/'track_B_progressive_compression'/(name+'_qualification.json'))
    assert q['accepted'] and q['states'][0]['accepted']
    assert q['max_qualified_strain']==pytest.approx(.012)
    assert q['states'][0]['localized_pair_contact']['force_opposition']=='PASS_TWO_SIDED_NATIVE_STRUCTURAL_FORCE'
    assert file_hash(BASE/name/'execution_receipt.json')==q['source_receipt_sha256']


def test_one_point_five_percent_target_is_native_converged_but_rejected_after_contact_switch():
    name='track_B_pair5_to_01500_001'
    receipt=read(BASE/name/'execution_receipt.json')
    q=read(RUN/'track_B_progressive_compression'/(name+'_qualification.json'))
    assert receipt['process']['returncode']==0
    assert file_hash(BASE/name/'execution_receipt.json')==q['source_receipt_sha256']
    assert q['max_native_converged_strain']==pytest.approx(.015)
    assert not q['accepted'] and len(q['states'])==32
    assert q['max_qualified_strain']==pytest.approx(.012575)
    assert [s['accepted'] for s in q['states']]==[True]*7+[False]*25
    assert 'Crossed selected arc without native pressure-bearing pair' in q['states'][7]['failures']


def test_highest_accepted_native_state_has_complete_fields_and_force_balance():
    q=read(RUN/'track_B_progressive_compression/track_B_pair5_to_01500_001_qualification.json')
    state=q['states'][6]
    assert state['requested_time']==pytest.approx(.012575)
    assert state['measurement']['reaction_balance_relative']<.01
    assert state['fields']['all_native_nodes']==174746
    assert state['fields']['invalid_quadratic_maps']==0
    pair=state['localized_pair_contact']
    assert pair['closed_source_faces']==2 and pair['max_pressure_MPa']>0
    assert pair['max_endpoint_penetration_mm']<=5e-5
    assert pair['force_opposition']=='PASS_TWO_SIDED_NATIVE_STRUCTURAL_FORCE'
    assert state['internal_contact']['closed_skins']==0


def test_native_all_substep_force_scan_and_response_figure_bindings():
    name='track_B_pair5_to_01500_001'
    scan=read(RUN/'track_B_contact_fixture'/(name+'_pair_force_scan.json'))
    assert len(scan['states'])==32 and all(s['passed_when_engaged'] for s in scan['states'])
    inventory=read(RUN/'figures/FIGURE_INVENTORY.json')
    assert inventory['state_source']==name and inventory['selected_substep']==7
    assert inventory['accepted_curve_points']==12 and inventory['curve_branch']=='unified_pair5'
    csv=RUN/'figures/TRACK_B_ACCEPTED_RESPONSE.csv'
    assert file_hash(csv)==inventory['response_csv_sha256']
    data=np.loadtxt(csv,delimiter=',',skiprows=1)
    assert data.shape==(12,4) and data[-1,0]==pytest.approx(.012575)


def test_resource_ledger_is_observed_native_evidence():
    ledger=read(RUN/'performance/PERFORMANCE.json')
    assert ledger['actual_solver_source_process_count']==28
    assert ledger['genuine_restart_continuation_process_count']==19
    assert ledger['native_read_only_POST1_process_count']==38
    assert ledger['raw_artifact_bytes']>40*2**30
    assert all(row['licensed_version']=='2024 R1' for row in ledger['native_processes'])
