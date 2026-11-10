"""Licensed artifact checks; passing tests preserve the failed scientific gates."""
from pathlib import Path
import numpy as np
import pytest
from scripts.v0610_common import BASE,RUN,read,file_hash
from scripts.v0610_polymer import qualified_onset_prefix


@pytest.mark.parametrize('strain',[.01,.1,.2,.3,.4])
def test_native_coupon_agrees_with_finite_strain_reference(strain):
    q=read(RUN/'material_coupon/QUALIFICATION.json');s=next(s for s in q['states'] if s['compression']==strain)
    assert q['status']=='PASS' and not q['calibrated'] and s['passed']
    assert s['relative_force_error']<3e-7 and abs(s['native_SZ_MPa'])<1e-8
    assert abs(s['native_EPEL_Y']-np.log(1-strain))<1e-5
    assert s['reference']['J']>0


@pytest.mark.parametrize('branch,source,count,rc',[('', 'track_B_pair5_arc_trial_001',34,15),('', 'track_B_pair5_arc_strict_001',91,0),('reverse','track_B_pair5_arc_trial_001',94,1)])
def test_actual_crop_source_states_and_native_exit_are_preserved(branch,source,count,rc):
    d=BASE/branch/source;r=read(d/'execution_receipt.json')
    assert r['solver_version']=='2024 R1' and r['process']['returncode']==rc
    assert len(r['converged_steps'])==count and file_hash(d/'input.inp')==r['input_sha256']
    deck=(d/'input.inp').read_text()
    assert 'SOLVE\n' in deck and 'NLGEOM,ON' in deck and 'OUTRES,ALL,ALL' in deck


@pytest.mark.parametrize('branch,source_faces,target_faces',[('',24,22),('reverse',22,24)])
def test_native_arc_coverage_excludes_exactly_the_partitioned_faces(branch,source_faces,target_faces):
    q=read(RUN/branch/'track_B_contact_fixture/PAIR_SETUP_QUALIFICATION.json')
    assert q['no_duplicate_face_exposure'] and q['removed_gc_faces']==46
    assert q['native_exact_face_counts']=={'contact':source_faces,'target':target_faces,'gc':15362}
    assert q['source_mesh_semantic_sha256']==read(RUN/'track_B_mesh/MESH_001.json')['semantic_sha256']


@pytest.mark.parametrize('branch,source,extent',[('', 'track_B_pair5_arc_strict_001',.012575),('reverse','track_B_pair5_arc_trial_001',.0115455)])
def test_final_gates_preserve_first_contact_failure_and_prohibit_polymer(branch,source,extent):
    p=RUN/branch/'track_B_progressive_compression';q=read(p/(source+'_mechanical_qualification.json'))
    assert not q['accepted'] and q['max_qualified_strain']==extent and qualified_onset_prefix(q) is None
    first=next(i for i,s in enumerate(q['states']) if not s['accepted'])
    assert all(s['accepted'] for s in q['states'][:first]) and not any(s['accepted'] for s in q['states'][first:])
    assert any('without native pressure-bearing pair' in f for f in q['states'][first]['failures'])
    g=read(p/(source+'_continuous_geometry.json'))
    assert file_hash(p/(source+'_continuous_geometry.json'))==q['continuous_geometry_sha256']
    assert len(g['states'])==len(q['states']) and all(s['passed'] for s in g['states'])
    assert all(s['fields']['invalid_quadratic_maps']==0 for s in q['states'])


def test_last_forward_state_has_independent_force_and_geometry_proof():
    q=read(RUN/'track_B_progressive_compression/track_B_pair5_arc_strict_001_mechanical_qualification.json')
    s=[s for s in q['states'] if s['accepted']][-1]
    assert s['measurement']['reaction_balance_relative']<1e-8
    assert s['localized_pair_contact']['force_opposition']=='PASS_TWO_SIDED_NATIVE_STRUCTURAL_FORCE'
    assert s['localized_pair_contact']['max_endpoint_penetration_mm']<5e-5
    g=read(RUN/'track_B_progressive_compression/track_B_pair5_arc_strict_001_continuous_geometry.json')['states'][61]
    assert g['maximum_continuous_bound_mm']<5e-5


@pytest.mark.parametrize('name',['final_u.csv','final_fields.csv','final_pair.csv','stage001_history.csv','stage001_contact.csv','stage001_contact_status.csv','stage001_gc_status.csv','stage001_gc_fields.csv'])
def test_repeat_native_readback_is_identical_and_bound(name):
    q=read(RUN/'fields/REPEAT_READBACK.json')
    assert q['status']=='PASS_REPEAT_NATIVE_FULL_FIELD_READBACK' and q['hashes'][0]==q['hashes'][1]
    for index in [1,2]:
        d=BASE/f'final_readback_{index:03d}';r=read(d/'execution_receipt.json')
        assert r['process']['returncode']==0 and r['solver_version']=='2024 R1'
        assert file_hash(d/name)==q['hashes'][index-1][name]
        assert 'SOLVE\n' not in (d/'input.inp').read_text()


def test_original_native_baseline_files_still_authenticate():
    for path,record in read(RUN/'audit/BASELINE.json')['native_files'].items():
        assert file_hash(Path(path))==record['sha256']


def test_only_coupon_and_reference_crop_solves_exist_and_no_invalid_restart():
    sources=[]
    for p in BASE.rglob('execution_receipt.json'):
        deck=(p.parent/'input.inp').read_text(errors='replace')
        if '\nSOLVE\n' in deck:sources.append(p.parent)
    assert len(sources)==4 and sum('coupon' in p.name for p in sources)==1
    assert not any('polymer' in str(p) for p in sources)
    assert all('ANTYPE,STATIC,REST' not in (p/'input.inp').read_text() for p in sources)
