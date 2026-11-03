"""One registered unified-detection correction for the explicit specimen pair."""
import argparse

from metamaterial_eval.simulation.progressive_compression import run_progressive,load_commands,authenticated_restart_copy
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.nonlinear_diagnostics import telemetry_commands
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence
from scripts.v068_pair_fixture import execute as execute_fixture,qualify as qualify_fixture


FIXTURE='pair_internal_unified_fixture_001'
SETUP='track_B_pair_unified_setup_001'


def prepare_fixture():
    parent=BASE/'pair_internal_fixture_001';m=read(parent/'simulation_manifest.json')
    if file_hash(parent/'input.inp')!=m['input_sha256']:
        raise ValueError('Changed original licensed pair fixture')
    d=BASE/FIXTURE;d.mkdir(parents=True,exist_ok=False)
    deck=(parent/'input.inp').read_text(encoding='utf-8')
    if deck.count('KEYOPT,3,4,2\n')!=1:raise ValueError('Original pair detection command missing or duplicated')
    deck=deck.replace('KEYOPT,3,4,2\n','KEYOPT,3,4,5\n')
    (d/'input.inp').write_text(deck,encoding='utf-8',newline='\n')
    manifest={**m,'schema':'young-dawgs-v068-compliant-unified-explicit-pair-fixture',
              'parent_fixture_input_sha256':m['input_sha256'],'detection_keyopt4':5,
              'technical_correction_protocol_sha256':file_hash(RUN/'protocol/TRACK_B_PAIR_UNIFIED5_TECHNICAL_CORRECTION_003.json'),
              'input_sha256':file_hash(d/'input.inp')}
    write_json(d/'simulation_manifest.json',manifest)
    copy_evidence(d,'track_B_contact_fixture')
    print('Prepared licensed unified explicit-pair fixture',flush=True)


def prepare_setup():
    fixture=read(RUN/'track_B_contact_fixture/PAIR_UNIFIED5_FIXTURE_QUALIFICATION.json')
    original=read(RUN/'track_B_contact_fixture/PAIR_SETUP_QUALIFICATION.json')
    if not fixture['passed'] or original['status']!='PASS_NATIVE_TRACK_B_LOCAL_PAIR_SETUP':
        raise ValueError('Native pair foundation failed')
    parent=BASE/'track_B_pair_setup_002/contact_model_pair.db'
    if file_hash(parent)!=original['pair_database_sha256']:
        raise ValueError('Corrected original pair database changed')
    d=BASE/SETUP;d.mkdir(parents=True,exist_ok=False)
    deck=('/BATCH\n/CLEAR,START\n'+f"RESUME,'{parent.with_suffix('').as_posix()}',db\n"+
         '/FILNAME,compression\n/PREP7\nKEYOPT,6,4,5\n'+
         '/OUTPUT,contact_types,txt\nETLIST,ALL\nRLIST,ALL\nGCDEF,LIST\n/OUTPUT\n'+
         'FINISH\nSAVE,contact_model_pair_unified,db,,MODEL\n/EXIT,NOSAVE\n')
    (d/'input.inp').write_text(deck,encoding='utf-8',newline='\n')
    m={'schema':'young-dawgs-v068-unified-explicit-pair-native-setup',
       'source_database_sha256':original['pair_database_sha256'],
       'source_setup_qualification_sha256':file_hash(RUN/'track_B_contact_fixture/PAIR_SETUP_QUALIFICATION.json'),
       'fixture_qualification_sha256':file_hash(RUN/'track_B_contact_fixture/PAIR_UNIFIED5_FIXTURE_QUALIFICATION.json'),
       'technical_correction_protocol_sha256':file_hash(RUN/'protocol/TRACK_B_PAIR_UNIFIED5_TECHNICAL_CORRECTION_003.json'),
       'input_sha256':file_hash(d/'input.inp'),'setup_only':True}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_contact_fixture')
    print('Prepared native unified pair specimen setup',flush=True)


def execute_setup():
    d=BASE/SETUP
    r=run_progressive(d,timeout=900,no_progress_seconds=300,cores=2,disk_reserve=80*1024**3)
    r['execution_kind']='LICENSED_PAIR_DETECTION_TECHNICAL_CORRECTION_SETUP_ONLY'
    write_json(d/'execution_receipt.json',r)
    copy_evidence(d,'track_B_native_results')
    print('Unified pair setup',r['status'],r['process']['returncode'],flush=True)


def verify_setup():
    import re
    d=BASE/SETUP;r=read(d/'execution_receipt.json');m=read(d/'simulation_manifest.json')
    parent=read(RUN/'track_B_contact_fixture/PAIR_SETUP_QUALIFICATION.json')
    if (r['solver_version']!='2024 R1' or r['process']['returncode']!=0 or
        file_hash(d/'input.inp')!=m['input_sha256'] or
        file_hash(d/'contact_model_pair_unified.db')!=r['process']['artifacts']['contact_model_pair_unified.db']['sha256'] or
        file_hash(BASE/'track_B_pair_setup_002/contact_model_pair.db')!=parent['pair_database_sha256']):
        raise ValueError('Native unified pair setup failed or changed')
    types=(d/'contact_types.txt').read_text(errors='replace')
    if not re.search(r'ELEMENT TYPE\s+6 IS CONTA172[\s\S]*?KEYOPT\( 1- 6\)=\s*0\s+1\s+0\s+5',types):
        raise ValueError('Native explicit pair did not install KEYOPT(4)=5')
    if 'NUMBER OF ERROR   MESSAGES ENCOUNTERED=          0' not in (d/'solver.out').read_text(errors='replace'):
        raise ValueError('Native unified pair setup had errors')
    q={'status':'PASS_NATIVE_PAIR_UNIFIED5_SETUP','native_solver_version':r['solver_version'],
       'installed_pair_detection_keyopt4':5,'source_database_sha256':m['source_database_sha256'],
       'native_database_sha256':file_hash(d/'contact_model_pair_unified.db'),
       'native_contact_inventory_sha256':file_hash(d/'contact_types.txt'),
       'setup_receipt_sha256':file_hash(d/'execution_receipt.json'),
       'face_topology':'Unchanged from qualified corrected pair setup 002; no face regeneration or duplicate contact',
       'scope':'Native setup only; fresh specimen mechanical fields still required.'}
    write_json(RUN/'track_B_contact_fixture/PAIR_UNIFIED5_SETUP_QUALIFICATION.json',q)
    print(q['status'],flush=True)
    return q


def prepare_first():
    q=verify_setup()
    base=read(BASE/'track_B_setup_001/simulation_manifest.json')
    topology=read(RUN/'track_B_contact_fixture/PAIR_SETUP_QUALIFICATION.json')
    d=BASE/'track_B_pair5_first_001';d.mkdir(parents=True,exist_ok=False)
    top=base['controls']['top'];bottom=base['controls']['bottom']
    lines=['/BATCH','/CLEAR,START',database_resume(BASE/SETUP/'contact_model_pair_unified.db').strip(),
           '/FILNAME,compression','/GOPR','/SOLU','ANTYPE,STATIC','NLGEOM,ON','EQSLV,SPARSE',
           'NROPT,FULL','LNSRCH,ON','CNVTOL,F,,.005,2,1e-8',f'NLHIST,NSOL,RFLOW,F,Y,{bottom}']
    lines+=telemetry_commands(top)
    controls=load_commands(.005,0,top,2.56,initial=.0005,maximum=.0025,minimum=1e-6)
    i=controls.index('OUTRES,ERASE');j=controls.index('OUTPR,ALL,NONE')
    controls[i:j]=['OUTRES,ALL,ALL','OUTRES,NLOAD,ALL']
    controls.insert(controls.index('SOLVE'),'NEQIT,40')
    lines+=controls+['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    m={'schema':'young-dawgs-v068-unified-pair-first','model_variant':'V068_TRACK_B_CENTRAL256_LOCAL_PAIR_UNIFIED5_003',
       'source_pair_setup_receipt_sha256':q['setup_receipt_sha256'],
       'source_pair_database_sha256':q['native_database_sha256'],
       'mesh_semantic_sha256':topology['source_mesh_semantic_sha256'],
       'model':{**base,'user_model_elements':read(RUN/'track_B_contact_fixture/SETUP_QUALIFICATION.json')['native_elements'],
                'general_contact_elements':topology['native_exact_face_counts']['gc'],
                'pair_contact_elements':topology['native_exact_face_counts']['contact']},
       'target_engineering_strain':.005,'target_displacement_mm':-.0128,
       'all_native_fields_all_substeps':True,'input_sha256':file_hash(d/'input.inp'),
       'mechanical_mesh_convergence':'UNQUALIFIED'}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_progressive_compression')
    print('Prepared fresh unified-pair 0.5% stage',flush=True)


def execute_first():
    d=BASE/'track_B_pair5_first_001'
    r=run_progressive(d,timeout=5400,no_progress_seconds=1200,cores=8,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Unified pair first',r['status'],r['process']['returncode'],r['converged_steps'][-5:],flush=True)


def next_name(target):return f'track_B_pair5_to_{round(target*100000):05d}_001'


def prepare_next(parent_name,target):
    p=read(RUN/'protocol/TRACK_B_LOCAL_PAIR_002.json');targets=p['first_targets']+p['continuation_targets']
    if target not in targets[1:]:raise ValueError('Unregistered unified pair target')
    qpath=RUN/'track_B_progressive_compression'/(parent_name+'_qualification.json');q=read(qpath)
    if not q['accepted'] or len(q['states'])!=1 or not q['states'][0]['accepted']:
        raise ValueError('Cannot advance from unqualified unified-pair parent')
    previous=q['states'][0]['measurement']['engineering_compression_strain']
    if targets.index(target)!=targets.index(previous)+1:raise ValueError('Pair checkpoint skipped')
    source=BASE/parent_name;name=next_name(target);d=BASE/name
    inherited=authenticated_restart_copy(source,d,expected_mesh=read(RUN/'track_B_mesh/MESH_001.json')['semantic_sha256'])
    if file_hash(source/'execution_receipt.json')!=q['source_receipt_sha256']:
        raise ValueError('Qualified parent receipt changed')
    model=inherited['model'];top=model['controls']['top'];bottom=model['controls']['bottom'];state=q['states'][0]
    lines=['/BATCH','/CLEAR,START','RESUME,compression,rdb','/FILNAME,compression','/GOPR','/SOLU',
           f'ANTYPE,STATIC,REST,{state["load_step"]},{state["substep"]},CONTINUE',
           'NLGEOM,ON','EQSLV,SPARSE','CNVTOL,F,,.005,2,1e-8',f'NLHIST,NSOL,RFLOW,F,Y,{bottom}']
    lines+=telemetry_commands(top)
    initial=.00005 if previous>=.01 and target<=.02 else .0005
    maximum=.0001 if previous>=.01 and target<=.02 else .0025
    controls=load_commands(target,previous,top,2.56,initial=initial,maximum=maximum,minimum=1e-6)
    i=controls.index('OUTRES,ERASE');j=controls.index('OUTPR,ALL,NONE')
    controls[i:j]=['OUTRES,ALL,ALL','OUTRES,NLOAD,ALL']
    controls.insert(controls.index('SOLVE'),'NEQIT,40')
    lines+=controls+['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    m={'schema':'young-dawgs-v068-unified-pair-continuation',
       'model_variant':'V068_TRACK_B_CENTRAL256_LOCAL_PAIR_UNIFIED5_003',
       'parent':parent_name,'parent_qualification_sha256':file_hash(qpath),
       'parent_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
       'parent_RST_sha256':file_hash(source/'compression.rst'),
       'restart_provenance_sha256':file_hash(d/'restart_provenance.json'),
       'previous_engineering_strain':previous,'target_engineering_strain':target,
       'target_displacement_mm':-2.56*target,'mesh_semantic_sha256':inherited['mesh_semantic_sha256'],
       'model':model,'input_sha256':file_hash(d/'input.inp'),
       'all_native_fields_all_substeps':True,'mechanical_mesh_convergence':'UNQUALIFIED'}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_progressive_compression')
    print('Prepared unified pair continuation',name,'from',parent_name,flush=True)


def execute_next(target):
    name=next_name(target);d=BASE/name
    r=run_progressive(d,timeout=5400,no_progress_seconds=1200,cores=8,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Unified pair continuation',name,r['status'],r['process']['returncode'],r['converged_steps'][-5:],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare-fixture','execute-fixture','qualify-fixture',
                                                                  'prepare-setup','execute-setup','verify-setup',
                                                                  'prepare-first','execute-first','prepare-next','execute-next'])
    p.add_argument('--parent');p.add_argument('--target',type=float)
    a=p.parse_args()
    {'prepare-fixture':prepare_fixture,
     'execute-fixture':lambda:execute_fixture(FIXTURE),
     'qualify-fixture':lambda:qualify_fixture(FIXTURE),
     'prepare-setup':prepare_setup,'execute-setup':execute_setup,'verify-setup':verify_setup,
     'prepare-first':prepare_first,'execute-first':execute_first,
     'prepare-next':lambda:prepare_next(a.parent,a.target),
     'execute-next':lambda:execute_next(a.target)}[a.action]()
