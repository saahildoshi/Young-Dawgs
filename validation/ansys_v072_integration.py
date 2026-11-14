"""Read-only qualification of actual v0.7.2 licensed native evidence; no solver calls."""
from pathlib import Path
import numpy as np
import pytest
from scripts.v070_protocol import REPO,read,sha
from scripts.v072_experiment import RUN,BASE,TRIALS
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.composite_elastic import structured_mesh

CASES=sorted((RUN/'mechanical_response').glob('*.json'))


@pytest.mark.parametrize('record_path',CASES,ids=lambda p:p.stem)
def test_actual_native_fields_mesh_reactions_and_independent_results(record_path):
    r=read(record_path);assert r['accepted'] and all(r['checks'].values())
    source=Path(r['source_directory']);post=Path(r['independent_readback_directory'])
    execution=read(source/'EXECUTION.json')
    assert execution['solver_release']=='2024 R1' and execution['native_process_ok']
    assert file_hash(source/'elastic.rst')==r['native_result_sha256']==execution['process']['artifacts']['elastic.rst']['sha256']
    assert file_hash(source/'model.db')==r['native_database_sha256']
    assert file_hash(post/'fields.csv')==r['native_fields_sha256']
    assert all(read(post/'READBACK.json')['identical_exports_to_solve'].values())
    assert not any(line.startswith(('SOLVE','SAVE,')) for line in (post/'input.inp').read_text().splitlines())
    specimen=read(RUN/'specimen_manifests'/f"{r['specimen_id']}.json")
    array=REPO/specimen['source_array_path'];assert sha(array)==specimen['source_array_sha256']
    m=structured_mesh(np.load(array,allow_pickle=False),r['mesh_level'])
    fields=np.loadtxt(post/'fields.csv',delimiter=',');connectivity=np.loadtxt(post/'connectivity.csv',delimiter=',')
    assert np.array_equal(fields[:,1],m['materials'])
    assert np.array_equal(connectivity[:,1:],m['quads']+1)
    curve=np.loadtxt(post/'curve.csv',delimiter=',');assert curve.shape==(5,12)
    assert -curve[:,2]==pytest.approx([.001,.002,.003,.004,.005],abs=1e-9)
    assert np.max(np.abs(curve[:,5]+curve[:,6])/np.abs(curve[:,5]))<=.001
    assert curve[:,8]==pytest.approx(.5*np.abs(curve[:,5]*curve[:,2]),rel=.001)
    assert np.polyfit(-curve[:,2],-curve[:,5],1)[0]==pytest.approx(r['effective_modulus_MPa'],rel=1e-10)
    assert read(source/'SECANT_CONFIRMATION.json')['passed']


def test_six_new_baseline_curves_are_actual_accepted_cases():
    for seed in range(1000,1006):
        assert read(RUN/f'mechanical_response/BASE_development_{seed}_H1_attempt001.json')['accepted']
    assert read(RUN/'baseline_mechanical_results/SUMMARY.json')['n']==6


def test_native_campaign_respects_registered_time_and_job_limits():
    receipts=[read(p) for p in BASE.glob('*/process_receipt.json')]
    limits=read(RUN/'protocol/PROTOCOL.json')['resource_limits']
    assert len(receipts)<=limits['maximum_native_jobs']
    assert sum(r['runtime_seconds'] for r in receipts)<=limits['native_campaign_seconds']


def test_inherited_qualified_evaluator_is_unchanged():
    for name,digest in read(RUN/'audit/QUALIFIED_EVALUATOR.json').items():assert sha(REPO/name)==digest


def test_frozen_genuine_revisions_have_unique_chat_receipts_and_equal_attempts():
    frozen=read(RUN/'frozen_scripts/ALL_OPTIMIZATION_SCRIPTS_FROZEN.json')
    records=frozen['scripts'];assert set(records)==set(TRIALS)
    assert len({r['chat_url'] for r in records.values()})==4
    for trial,r in records.items():
        assert r['model_calls']==1 and r['repair_calls']==0 and not r['researcher_repairs']
        assert sha(RUN/'llm_trials'/trial/'response.txt')==r['response_sha256']
        if r['code_sha256']:assert sha(RUN/'llm_trials'/trial/'generator.py')==r['code_sha256']


def test_h2_uses_same_geometry_and_prospective_seed_subset():
    partition=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')
    for path in (RUN/'mechanical_response').glob('*_H2_*.json'):
        b=read(path);specimen=read(RUN/'specimen_manifests'/f"{b['specimen_id']}.json")
        assert specimen['seed'] in partition['H2']==partition['heldout'][:3]
        a=read(RUN/'mechanical_response'/path.name.replace('_H2_','_H1_'))
        assert a['mesh']['material_area_fractions']==b['mesh']['material_area_fractions']
        assert b['mesh']['elements']==4*a['mesh']['elements']
