"""Read-only checks of actual v073 native evidence; never launch a solver."""
from pathlib import Path
import numpy as np
import pytest
from scripts.v070_protocol import REPO,read,sha
from scripts.v073_experiment import RUN,BASE
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.composite_elastic import structured_mesh

CASES=sorted((RUN/'mechanical_response').glob('*.json'))

@pytest.mark.parametrize('path',CASES,ids=lambda p:p.stem)
def test_native_geometry_materials_curves_fields_and_readback(path):
    r=read(path);assert r['accepted'] and all(r['checks'].values())
    source=Path(r['source_directory']);post=Path(r['independent_readback_directory'])
    assert read(source/'EXECUTION.json')['solver_release']=='2024 R1'
    assert file_hash(source/'elastic.rst')==r['native_result_sha256']
    assert file_hash(source/'model.db')==r['native_database_sha256']
    assert file_hash(post/'fields.csv')==r['native_fields_sha256']
    assert all(read(post/'READBACK.json')['identical_exports_to_solve'].values())
    assert not any(line.startswith(('SOLVE','SAVE,')) for line in (post/'input.inp').read_text().splitlines())
    s=read(RUN/'specimen_manifests'/f"{r['specimen_id']}.json");path=REPO/s['source_array_path']
    assert sha(path)==s['source_array_sha256'];a=np.load(path)
    assert int((a==5).sum())==20731 and int((a==1).sum())==44805
    m=structured_mesh(a,r['mesh_level']);f=np.loadtxt(post/'fields.csv',delimiter=',')
    conn=np.loadtxt(post/'connectivity.csv',delimiter=',')
    assert np.array_equal(f[:,1],m['materials']) and np.array_equal(conn[:,1:],m['quads']+1)
    curve=np.loadtxt(post/'curve.csv',delimiter=',');assert curve.shape==(5,12)
    assert -curve[:,2]==pytest.approx([.001,.002,.003,.004,.005],abs=1e-9)
    assert curve[:,5].max()<0 and curve[:,6].min()>0
    assert np.max(np.abs(curve[:,5]+curve[:,6])/np.abs(curve[:,5]))<=.001
    assert curve[:,8]==pytest.approx(.5*np.abs(curve[:,5]*curve[:,2]),rel=.001)
    assert np.polyfit(-curve[:,2],-curve[:,5],1)[0]==pytest.approx(r['effective_modulus_MPa'],rel=1e-10)
    assert abs(r['effective_modulus_MPa']-r['secant_modulus_MPa'])/r['effective_modulus_MPa']<=1e-5

def test_new_development_campaign_counts_and_no_invalid_solve():
    h1=read(RUN/'development_mechanics_h1/CAMPAIGN.json');h2=read(RUN/'development_mechanics_h2/CAMPAIGN.json')
    assert h1['planned']==18 and h1['accepted']==17
    assert h2['planned']==h2['accepted']==5
    invalid=next(r for r in h1['cases'] if r['trial_id']=='BASE' and r['seed']==3104)
    assert invalid['status']=='NOT_SOLVED_STRUCTURALLY_INFEASIBLE' and invalid['apparent_modulus_MPa'] is None
    assert not list((RUN/'mechanical_response').glob('BASE_development_3104*'))

def test_all_refinements_same_source_geometry_and_registered_subset():
    for path in (RUN/'mechanical_response').glob('*H2*.json'):
        b=read(path);a=read(path.with_name(path.name.replace('_H2_','_H1_')))
        assert b['mesh']['material_area_fractions']==a['mesh']['material_area_fractions']
        assert b['mesh']['elements']==4*a['mesh']['elements']
        s=read(RUN/'specimen_manifests'/f"{b['specimen_id']}.json")
        assert s['seed']==3100 and s['partition']=='development'

def test_qualified_source_evaluator_unchanged():
    for name,digest in read(RUN/'audit/QUALIFIED_EVALUATOR.json').items():assert sha(REPO/name)==digest

def test_native_resource_budget_actual_processes():
    receipts=[read(path) for path in BASE.glob('*/process_receipt.json')]
    limits=read(RUN/'protocol/PROTOCOL.json')['resource_limits']
    assert len(receipts)==44<=limits['maximum_native_jobs']
    assert sum(r['runtime_seconds'] for r in receipts)<=limits['native_campaign_seconds']
    assert all(r['status']=='PROCESS_EXITED' and r['returncode']==0 for r in receipts)

def test_no_mechanics_or_responses_past_failed_target_gate():
    decision=read(RUN/'target_selection/TARGET_FROZEN.json')
    if not decision['qualified_target']:
        assert not list((RUN/'llm_trials').glob('*/response.txt'))
        assert not (RUN/'heldout_structural_evaluation').exists()
        assert not (RUN/'heldout_mechanics_h1').exists()
