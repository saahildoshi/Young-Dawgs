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
    assert q['boundary_screen_summary']['passed'] and q['boundary_screen_summary']['pore_loops']==412
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
