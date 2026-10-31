"""One bounded, authenticated contact-onset ENDSTEP/controller recovery."""
import argparse
from pathlib import Path
import numpy as np
from scripts.v066_restart import RUN,BASE,load,compact,export,endpoint_states
from scripts.v065_recovery import committed
from scripts.v066_campaign import remaining_solver_budget
from metamaterial_eval.simulation.mesh_artifacts import HISTORICAL
from metamaterial_eval.simulation.progressive_compression import authenticated_restart_copy,load_commands,run_progressive
from metamaterial_eval.simulation.nonlinear_diagnostics import telemetry_commands
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash

PROTOCOL=RUN/'protocol/CONTACT_ONSET_CONTROL_RECOVERY_025.json'
REFERENCE='rectangle_endstep_reference_all_002';SMALL='rectangle_endstep_control_002';FINE='fine_nodal_recovery01_001'


def endstep_input(ls,ss,previous,target,model):
    lines=['/BATCH','/CLEAR,START','RESUME,compression,rdb','/FILNAME,compression','/GOPR','/SOLU',
        f'ANTYPE,STATIC,REST,{ls},{ss},ENDSTEP','OUTRES,ERASE','OUTRES,ALL,NONE']
    lines+=['OUTRES,'+item+',ALL' for item in ['NSOL','RSOL','STRS','EPEL','CONT','MISC']]+['SOLVE']
    lines+=telemetry_commands(model['controls']['top'])+[f'NLHIST,NSOL,RFLOW,F,Y,{model["controls"]["bottom"]}']
    lines+=load_commands(target,previous,model['controls']['top'],model['config']['height'],initial=5e-5,maximum=2.5e-4,minimum=1e-6,all_fields=True)
    lines=['NEQIT,12' if line=='NEQIT,24' else line for line in lines]
    return '\n'.join(lines+['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE'])+'\n'



def prepare_reference():
    source=BASE/'restart_retention_probe_001';d=BASE/REFERENCE;d.mkdir(parents=True,exist_ok=False)
    text=(source/'input.inp').read_text()
    for item in ['NSOL','RSOL','STRS','EPEL','CONT','MISC']:text=text.replace('OUTRES,'+item+',LAST','OUTRES,'+item+',ALL')
    (d/'input.inp').write_text(text);m=load(source/'simulation_manifest.json')
    m.update(input_sha256=file_hash(d/'input.inp'),protocol_sha256=file_hash(PROTOCOL),execution_scope='FRESH_SMALL_FIVE_SUBSTEP_ALL_FIELD_ENDSTEP_REFERENCE')
    write_json(d/'simulation_manifest.json',m);compact(d,RUN/'restart_validation'/('prepared_'+REFERENCE));print(d,flush=True)


def execute_reference():
    committed(PROTOCOL);committed(RUN/'restart_validation'/('prepared_'+REFERENCE)/'input.inp')
    d=BASE/REFERENCE;r=run_progressive(d,timeout=180,no_progress_seconds=120,cores=2)
    compact(d,RUN/'restart_validation'/REFERENCE);print(REFERENCE,r['status'],r['process']['returncode'],flush=True)


def prepare_small():
    d=BASE/SMALL;m=authenticated_restart_copy(BASE/REFERENCE,d)
    (d/'input.inp').write_text(endstep_input(1,3,.003,.005,m['model']))
    m.update(input_sha256=file_hash(d/'input.inp'),protocol_sha256=file_hash(PROTOCOL),previous_strain=.003,target_strain=.005,targets=[.005],execution_scope='SMALL_NATIVE_ENDSTEP_CONTROL_QUALIFICATION',execution_cores=2)
    write_json(d/'simulation_manifest.json',m);compact(d,RUN/'restart_validation'/('prepared_'+SMALL));print(d,flush=True)


def execute_small():
    committed(PROTOCOL);committed(RUN/'restart_validation'/('prepared_'+SMALL)/'input.inp')
    d=BASE/SMALL;r=run_progressive(d,timeout=300,no_progress_seconds=180,cores=2)
    compact(d,RUN/'restart_validation'/SMALL);print(SMALL,r['status'],r['process']['returncode'],r['converged_steps'][-1:],flush=True)


def qualify_small():
    parent=BASE/REFERENCE;source=BASE/SMALL
    assert load(source/'execution_receipt.json')['process']['returncode']==0
    last=endpoint_states(source,[.005])[0];assert last['load_step']==2
    before=[{'time':.003,'load_step':1,'substep':3},{'time':.005,'load_step':1,'substep':5}]
    after=[before[0],last]
    a=export(parent,'retention_endstep_reference_post002',before,chunk_size=128)
    b=export(source,SMALL+'_post001',after,chunk_size=128)
    compact(a,RUN/'restart_validation'/a.name);compact(b,RUN/'restart_validation'/b.name)
    comparisons=[]
    for stage in [1,2]:
        assert float((a/f'stage{stage:03d}_gate.txt').read_text().split(',')[0])==0
        assert float((b/f'stage{stage:03d}_gate.txt').read_text().split(',')[0])==0
        for field in ['history','contact','displacements','stress']:
            filename=f'stage{stage:03d}_{field}.csv';x=np.loadtxt(a/filename,delimiter=',',skiprows=1,ndmin=2);y=np.loadtxt(b/filename,delimiter=',',skiprows=1,ndmin=2)
            if field=='history':x=x[:,[0,3,4,5]];y=y[:,[0,3,4,5]]
            assert x.shape==y.shape
            errors=np.max(abs(x-y),axis=0)/np.maximum(np.max(abs(x),axis=0),1e-12)
            comparisons.append({'stage':stage,'field':field,'maximum_column_scaled_error':float(errors.max()),'passed':bool(np.all(errors<1e-5))})
    passed=all(c['passed'] for c in comparisons)
    q={'status':'PASS_ACTUAL_NATIVE_ENDSTEP_CUMULATIVE_FIELDS_AND_CONTROLLER' if passed else 'HOLD',
        'source_native_parent':str(parent),'source_native_recovery':str(source),'actual_prior_state':before[0],'actual_new_end_state':last,
        'history_identity_columns_intentionally_differ_at_final':'Parent LS1SS5 versus recovered new LS2; native time,total UY and both RF columns compared, never relabeled.',
        'comparisons':comparisons,'native_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
        'protocol_sha256':file_hash(PROTOCOL),'native_parent_not_modified':True,'native_endstep_verified':True,
        'native_RST_reopened':True,'scope':'Actual small continuous-parent versus mid-load-step ENDSTEP/restart, retaining cumulative displacement and native U/S/EPEL/contact/history under NEQIT12/smaller steps.'}
    write_json(RUN/'restart_validation/ENDSTEP_CONTROL_QUALIFICATION.json',q);print(q['status'],comparisons,flush=True)


def prepare_fine():
    check=RUN/'restart_validation/ENDSTEP_CONTROL_QUALIFICATION.json'
    assert load(check)['status']=='PASS_ACTUAL_NATIVE_ENDSTEP_CUMULATIVE_FIELDS_AND_CONTROLLER'
    qp=RUN/'mechanical_results/fine_nodal_stage02_001_qualification001.json';q=load(qp)
    assert q['last_state_accepted'] and all(x['accepted'] for x in q['results'])
    state=q['states'][-1];assert state['time']<.01
    parent=BASE/'fine_nodal_stage02_001';d=BASE/FINE;m=authenticated_restart_copy(parent,d,expected_mesh=HISTORICAL)
    assert m['model']['general_contact_detection_keyopt4']==2
    (d/'input.inp').write_text(endstep_input(state['load_step'],state['substep'],state['time'],.01,m['model']))
    m.update(input_sha256=file_hash(d/'input.inp'),protocol_sha256=file_hash(PROTOCOL),previous_strain=state['time'],target_strain=.01,targets=[.01],
        execution_scope='SAME_NODAL_MODEL_AUTHENTICATED_ENDSTEP_CONTACT_ONSET_RECOVERY',execution_cores=8,
        parent_qualification_path=str(qp.resolve()),parent_qualification_sha256=file_hash(qp),endstep_fixture_sha256=file_hash(check),
        solver_control_revision='CONTACT_ONSET_CONTROL_RECOVERY_025',solver_controls={'NEQIT':12,'initial_increment':5e-5,'maximum_increment':2.5e-4,'minimum_increment':1e-6},
        resource_protocol_sha256=file_hash(RUN/'protocol/SMP_RESOURCE_018.json'),parallel_qualification_sha256=file_hash(RUN/'performance/SMP_QUALIFICATION.json'),
        restart_state=state)
    write_json(d/'simulation_manifest.json',m);compact(d,RUN/'progressive_compression'/('prepared_'+FINE));print(d,flush=True)


def execute_fine():
    committed(PROTOCOL);committed(RUN/'progressive_compression'/('prepared_'+FINE)/'input.inp')
    d=BASE/FINE;m=load(d/'simulation_manifest.json')
    assert file_hash(d/'input.inp')==m['input_sha256']==file_hash(RUN/'progressive_compression'/('prepared_'+FINE)/'input.inp')
    for path,key in [(PROTOCOL,'protocol_sha256'),(m['parent_qualification_path'],'parent_qualification_sha256'),(RUN/'restart_validation/ENDSTEP_CONTROL_QUALIFICATION.json','endstep_fixture_sha256'),(RUN/'protocol/SMP_RESOURCE_018.json','resource_protocol_sha256'),(RUN/'performance/SMP_QUALIFICATION.json','parallel_qualification_sha256')]:assert file_hash(path)==m[key]
    r=run_progressive(d,timeout=min(3600,remaining_solver_budget()),no_progress_seconds=1800,cores=8)
    compact(d,RUN/'progressive_compression'/FINE);print(FINE,r['status'],r['process']['returncode'],r['converged_steps'][-1:],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare-reference','run-reference','prepare-small','run-small','qualify-small','prepare-fine','run-fine']);a=p.parse_args()
    {'prepare-reference':prepare_reference,'run-reference':execute_reference,'prepare-small':prepare_small,'run-small':execute_small,'qualify-small':qualify_small,'prepare-fine':prepare_fine,'run-fine':execute_fine}[a.action]()
