"""One registered small-step rescue of the Track B crop-edge contact onset."""
import argparse

from metamaterial_eval.simulation.progressive_compression import authenticated_restart_copy,load_commands,run_progressive
from metamaterial_eval.simulation.nonlinear_diagnostics import telemetry_commands
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


PROTOCOL=RUN/'protocol/TRACK_B_CONTACT_ONSET_RECOVERY_001.json'
CORRECTION=RUN/'protocol/TRACK_B_CONTACT_ONSET_RECOVERY_001_TECHNICAL_CORRECTION.json'


def name(target):return f'track_B_contact_recovery_{round(target*100000):05d}_001'


def prepare(parent_name,target):
    protocol=read(PROTOCOL);schedule=protocol['schedule']
    matching=[(i,x) for i,x in enumerate(schedule) if abs(x['target']-target)<1e-12]
    if len(matching)!=1:raise ValueError('Unregistered recovery target')
    index,control=matching[0]
    expected_parent=protocol['parent_native_job'] if index==0 else name(schedule[index-1]['target'])
    if parent_name!=expected_parent:raise ValueError('Recovery parent sequence differs')
    path=RUN/'track_B_progressive_compression'/(parent_name+'_qualification.json')
    if index==0:path=RUN/'track_B_progressive_compression'/(parent_name+'_qualification.json')
    q=read(path)
    prior=protocol['parent_accepted_state']['engineering_strain'] if index==0 else schedule[index-1]['target']
    accepted=[r for r in q['states'] if r['accepted'] and abs(r['requested_time']-prior)<1e-12]
    if len(accepted)!=1 or (index>0 and not q['accepted']):
        raise ValueError('Cannot continue from missing/unqualified recovery state')
    state=accepted[0];source=BASE/parent_name;d=BASE/name(target)
    if file_hash(source/'execution_receipt.json')!=q['source_receipt_sha256']:
        raise ValueError('Changed native parent execution')
    inherited=authenticated_restart_copy(source,d,expected_mesh=read(RUN/'track_B_mesh/MESH_001.json')['semantic_sha256'])
    model=inherited['model'];top=model['controls']['top'];bottom=model['controls']['bottom']
    ls,ss=state['load_step'],state['substep']
    lines=['/BATCH','/CLEAR,START','RESUME,compression,rdb','/FILNAME,compression',
           '/GOPR','/SOLU',f'ANTYPE,STATIC,REST,{ls},{ss},ENDSTEP',
           'OUTRES,ERASE','OUTRES,ALL,NONE']
    lines+=['OUTRES,'+item+',ALL' for item in ['NSOL','RSOL','STRS','EPEL','CONT','MISC']]
    lines+=['SOLVE']+telemetry_commands(top)+[f'NLHIST,NSOL,RFLOW,F,Y,{bottom}',
                                        'CNVTOL,F,,.005,2,1e-8']
    lines+=load_commands(target,prior,top,2.56,initial=control['initial'],
                         maximum=control['maximum'],minimum=control['minimum'])
    lines.insert(len(lines)-1,'NEQIT,40')
    lines+=['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    manifest={'schema':'young-dawgs-v068-track-b-single-onset-recovery',
              'model_variant':'V068_TRACK_B_CENTRAL256_UNIFIED5',
              'recovery_protocol_sha256':file_hash(PROTOCOL),'recovery_index':index,
              'parent':parent_name,'parent_qualification_sha256':file_hash(path),
              'parent_accepted_state':{'load_step':ls,'substep':ss,'time':prior},
              'parent_RST_sha256':file_hash(source/'compression.rst'),
              'parent_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
              'restart_provenance_sha256':file_hash(d/'restart_provenance.json'),
              'mesh_semantic_sha256':inherited['mesh_semantic_sha256'],
              'source_geometry_sha256':inherited['source_geometry_sha256'],
              'model':model,'target_engineering_strain':target,
              'target_displacement_mm':-2.56*target,
              'controls':control,'input_sha256':file_hash(d/'input.inp'),
              'all_native_fields_all_substeps':True,'mechanical_mesh_convergence':'UNQUALIFIED'}
    write_json(d/'simulation_manifest.json',manifest)
    copy_evidence(d,'track_B_progressive_compression')
    print('Prepared contact-onset recovery',name(target),'from accepted',parent_name,prior,flush=True)


def execute(target):
    d=BASE/name(target);m=read(d/'simulation_manifest.json')
    if file_hash(PROTOCOL)!=m['recovery_protocol_sha256'] or file_hash(d/'input.inp')!=m['input_sha256']:
        raise ValueError('Registered recovery input changed')
    r=run_progressive(d,timeout=5400,no_progress_seconds=1200,cores=8,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Track B recovery',name(target),r['status'],r['process']['returncode'],r['converged_steps'][-5:],flush=True)


def clean_name(target):return f'track_B_contact_clean_{round(target*100000):05d}_001'


def prepare_clean(parent_name,target):
    protocol=read(CORRECTION);schedule=protocol['registered_schedule']
    matches=[(i,r) for i,r in enumerate(schedule) if abs(r['target']-target)<1e-12]
    if len(matches)!=1:raise ValueError('Unregistered corrected recovery target')
    index,control=matches[0]
    expected_parent=protocol['parent_native_job'] if index==0 else clean_name(schedule[index-1]['target'])
    if parent_name!=expected_parent:raise ValueError('Corrected recovery sequence differs')
    path=RUN/'track_B_progressive_compression'/(parent_name+'_qualification.json')
    q=read(path);prior=protocol['parent_qualified_strain'] if index==0 else schedule[index-1]['target']
    accepted=[r for r in q['states'] if r['accepted'] and abs(r['requested_time']-prior)<1e-12]
    if not q['accepted'] or len(accepted)!=1:raise ValueError('Corrected recovery parent is not qualified')
    state=accepted[0];source=BASE/parent_name;d=BASE/clean_name(target)
    if file_hash(source/'execution_receipt.json')!=q['source_receipt_sha256']:
        raise ValueError('Changed corrected-recovery native parent')
    inherited=authenticated_restart_copy(source,d,expected_mesh=read(RUN/'track_B_mesh/MESH_001.json')['semantic_sha256'])
    model=inherited['model'];top=model['controls']['top'];bottom=model['controls']['bottom']
    lines=['/BATCH','/CLEAR,START','RESUME,compression,rdb','/FILNAME,compression',
           '/GOPR','/SOLU',f'ANTYPE,STATIC,REST,{state["load_step"]},{state["substep"]},CONTINUE']
    lines+=telemetry_commands(top)+[f'NLHIST,NSOL,RFLOW,F,Y,{bottom}',
                               'CNVTOL,F,,.005,2,1e-8']
    lines+=load_commands(target,prior,top,2.56,initial=control['initial'],
                         maximum=control['maximum'],minimum=control['minimum'])
    lines.insert(lines.index('SOLVE'),'NEQIT,40')
    lines+=['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    m={'schema':'young-dawgs-v068-track-b-corrected-single-recovery',
       'model_variant':'V068_TRACK_B_CENTRAL256_UNIFIED5',
       'original_recovery_protocol_sha256':file_hash(PROTOCOL),
       'technical_correction_sha256':file_hash(CORRECTION),
       'recovery_index':index,'parent':parent_name,'parent_qualification_sha256':file_hash(path),
       'parent_accepted_state':{'load_step':state['load_step'],'substep':state['substep'],'time':prior},
       'parent_RST_sha256':file_hash(source/'compression.rst'),
       'parent_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
       'restart_provenance_sha256':file_hash(d/'restart_provenance.json'),
       'mesh_semantic_sha256':inherited['mesh_semantic_sha256'],
       'source_geometry_sha256':inherited['source_geometry_sha256'],
       'model':model,'target_engineering_strain':target,'target_displacement_mm':-2.56*target,
       'controls':control,'input_sha256':file_hash(d/'input.inp'),
       'all_native_fields_all_substeps':True,'mechanical_mesh_convergence':'UNQUALIFIED'}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_progressive_compression')
    print('Prepared corrected contact-onset recovery',clean_name(target),'from qualified',parent_name,prior,flush=True)


def execute_clean(target):
    d=BASE/clean_name(target);m=read(d/'simulation_manifest.json')
    if file_hash(CORRECTION)!=m['technical_correction_sha256'] or file_hash(d/'input.inp')!=m['input_sha256']:
        raise ValueError('Corrected recovery protocol/input changed')
    r=run_progressive(d,timeout=5400,no_progress_seconds=1200,cores=8,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Track B corrected recovery',clean_name(target),r['status'],r['process']['returncode'],r['converged_steps'][-5:],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','prepare-clean','execute-clean'])
    p.add_argument('--parent');p.add_argument('--target',type=float,required=True)
    a=p.parse_args()
    {'prepare':lambda:prepare(a.parent,a.target),'execute':lambda:execute(a.target),
     'prepare-clean':lambda:prepare_clean(a.parent,a.target),
     'execute-clean':lambda:execute_clean(a.target)}[a.action]()
