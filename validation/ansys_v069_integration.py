"""Licensed evidence checks; a held scientific branch must remain held."""
from pathlib import Path
import numpy as np
import pytest
from scripts.v069_study import BASE,RUN,OLD,PREVIOUS,read,file_hash
from scripts.v068_track_b import mesh_and_plan


@pytest.mark.parametrize('subdir',['','expanded'])
def test_local_tri6_and_coordinates_are_exact_original_id_subsets(subdir):
    mesh,_,_,_=mesh_and_plan();z=np.load(BASE/subdir/'local_source_001/source.npz')
    assert np.array_equal(z['triangles'],mesh.triangles[z['eids']-1])
    assert set(z['nodes'])==set(np.unique(z['triangles'])+1)


@pytest.mark.parametrize('subdir',['','expanded'])
def test_both_local_native_solves_really_completed_72_histories(subdir):
    d=BASE/subdir/'local_baseline_001';r=read(d/'execution_receipt.json')
    assert r['solver_version']=='2024 R1' and r['process']['returncode']==0
    assert file_hash(d/'input.inp')==r['input_sha256']
    assert len({s[0] for s in r['converged_steps']})==72
    assert 'NLGEOM,ON' in (d/'input.inp').read_text()


@pytest.mark.parametrize('subdir,failed',[('',[35,36,37]),('expanded',[35,36])])
def test_all_measured_histories_are_checked_and_mismatch_prevents_continuation(subdir,failed):
    q=read(RUN/subdir/'local/BASELINE_FIELD_COMPARISON.json')
    assert len(q['states'])==72 and q['complete_measured_history']
    assert [s['index'] for s in q['states'] if not s['field_match']]==failed
    assert not q['all_fields_pass'] and not q['crop_continuation_authorized']


def test_individual_opening_skin_is_preserved_without_inferring_total_force_loss():
    a=np.loadtxt(RUN/'diagnostics/ELEMENT_CONTACT_HISTORY.csv',delimiter=',',skiprows=1)
    before=a[(a[:,0]==7)&(a[:,2]==95927)][0];after=a[(a[:,0]==8)&(a[:,2]==95927)][0]
    neighbor=a[(a[:,0]==8)&(a[:,2]==95928)][0]
    assert before[3]==2 and after[3]==1 and neighbor[3]==2
    assert max(neighbor[4:6])>39


def test_expanded_native_structural_components_are_elements():
    deck=(BASE/'expanded/local_baseline_readback_001/input.inp').read_text()
    assert 'CMBLOCK,LOCAL_SOLIDS,ELEM,' in deck
    force=np.loadtxt(BASE/'expanded/local_baseline_readback_001/state047_patch_forces.csv',delimiter=',')
    assert force.shape==(2,3) and np.isfinite(force).all()


def test_parent_sources_still_match_registered_hashes():
    a=read(RUN/'audit/AUTHENTICATION.json')
    for p,r in a['native_files'].items():assert file_hash(Path(p))==r['sha256']


def test_inherited_accepted_maximum_has_complete_native_repeatable_tensor_fields():
    q=read(RUN/'fields/REPEAT_READBACK.json')
    assert q['status']=='PASS_REPEAT_NATIVE_FULL_FIELD_READBACK'
    assert q['hashes'][0]==q['hashes'][1] and q['corners']==47525 and q['nodes']==174746
    assert not q['new_strain_achieved']


def test_accepted_and_rejected_original_crop_states_remain_separate():
    q=read(PREVIOUS/'track_B_progressive_compression/track_B_pair5_to_01500_001_qualification.json')
    assert q['states'][6]['accepted'] and not q['states'][7]['accepted']
    assert q['states'][6]['fields']['invalid_quadratic_maps']==0
    assert q['states'][6]['measurement']['reaction_balance_relative']<.01
    assert q['states'][6]['localized_pair_contact']['max_endpoint_penetration_mm']<5e-5


def test_prospective_limits_and_system_health_supervision_remain_fixed():
    p=read(RUN/'protocol/PROTOCOL.json')
    assert p['arbitrary_RSS_cap'] is None and p['mechanics']['native_penetration_mm']==5e-5
    assert p['parent_matching']['S_and_EPEL_relative_RMS']==.10
    assert not p['track_A_full_solve_authorized']
