"""One conditional technical repair: end at known converged state and flush it."""
from dataclasses import asdict
import argparse
import re
import shutil
import subprocess
import psutil
from scripts.v064_recovery import RUN,BASE,REPO,load
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.microstructure_pilot import prepare_pilot,database_resume,stage_block,run_input
from metamaterial_eval.simulation.nonlinear_diagnostics import DiagnosticBudget,telemetry_commands,run_diagnostic
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash

FULL=BASE/'full_recovery_002';PROTOCOL=RUN/'protocol/FULL_RECOVERY_002.json';JOB='v064r002';POST=BASE/'postprocess_converged_002'


def prepare():
    io=load(RUN/'diagnostic_validation/checkpoint_IO_control.json')
    assert io['readable_result'] and io['one_restart_frame'] and not FULL.exists()
    p=load(RUN/'protocol/FULL_RECOVERY_001.json');p.update(revision=2,strains=[.00005],native_jobname=JOB,
        conditional_exception='User section21 specific directly correctable implementation error; not another parameter search. See TECHNICAL_RECOVERY_AMENDMENT_009.',
        primary_outcome='First native0.005% substep converged, memorycap during next factorization, nativeRST0 readable sets and no saved restart frame; POST1 failed. Preserve all evidence.',
        target_reason='Exactly the already achieved first increment; original0.01% endpoint remains unmet.',
        technical_amendment_sha256=file_hash(RUN/'protocol/TECHNICAL_RECOVERY_AMENDMENT_009.json'),
        checkpoint_IO_control_sha256=file_hash(RUN/'diagnostic_validation/checkpoint_IO_control.json'),
        output='OUTRES ALL ALL; RESCONTROL DEFINE ALL,1,1; one end-of-step native state; separate POST1 process after solver exit',
        no_more_full_runs=True,primary_full_model_attempts_max=1,conditional_technical_repair_attempts_max=1)
    p['controls']['NSUBST']=[1,1,1]
    budget=DiagnosticBudget(completed_iterations_cap=32,cutbacks_cap=3,trend_window=6,stop_stagnation=True,checkpoint_bytes_cap=4*1024**3)
    p['diagnostic_budget']=asdict(budget);p.pop('frozen_input_sha256',None);write_json(PROTOCOL,p)
    model=prepare_pilot(FULL,artifact_root()/'solver/v063/contact_setup_002',PROTOCOL)
    commands=['/BATCH','/CLEAR,START',database_resume(artifact_root()/'solver/v063/contact_setup_002/contact_model.db').strip(),f'/FILNAME,{JOB}','/GOPR','/PREP7','KEYOPT,3,4,2','/OUTPUT,corrected_inventory,txt','ETLIST,ALL','RLIST,ALL','MPLIST,ALL','DLIST,ALL','/OUTPUT','FINISH','/SOLU','NEQIT,24','NSUBST,1,1,1','KBC,0','OUTRES,ALL,ALL','RESCONTROL,DEFINE,ALL,1,1']+telemetry_commands(model['controls']['top'])+['/OUTPUT,initial_contact,txt','CNCHECK,DETAIL','/OUTPUT','TIME,.00005',f'D,{model["controls"]["top"]},UY,-.000512','SOLVE','FINISH','SAVE,checkpoint,db','/EXIT,NOSAVE']
    (FULL/'input.inp').write_text('\n'.join(commands)+'\n');p['frozen_input_sha256']=file_hash(FULL/'input.inp');write_json(PROTOCOL,p)
    m=load(FULL/'simulation_manifest.json');m['model']['contact_detection_keyopt4']=2;m.update(result_jobname=JOB,protocol_sha256=file_hash(PROTOCOL),input_sha256=p['frozen_input_sha256']);write_json(FULL/'simulation_manifest.json',m)
    out=RUN/'full_model_retry/prepared_002';out.mkdir(exist_ok=False)
    for name in ['input.inp','simulation_manifest.json']:shutil.copy2(FULL/name,out/name)
    print('Frozen conditional direct repair',p['frozen_input_sha256'])


def execute():
    subprocess.run(['git','diff','--exit-code','HEAD','--',PROTOCOL.relative_to(REPO).as_posix()],cwd=REPO,check=True)
    subprocess.run(['git','ls-files','--error-unmatch',PROTOCOL.relative_to(REPO).as_posix()],cwd=REPO,check=True,stdout=subprocess.DEVNULL)
    p=load(PROTOCOL);assert file_hash(FULL/'input.inp')==p['frozen_input_sha256']
    assert not [q.pid for q in psutil.process_iter(['name']) if q.info['name'] and q.info['name'].lower() in ['ansys.exe','ansys241.exe']],'Another MAPDL job is active'
    r=run_diagnostic(FULL,cores=2,timeout=1200,rss_GiB=20,jobname=JOB,budget=DiagnosticBudget(**p['diagnostic_budget']))
    write_json(RUN/'full_model_retry/execution_002.json',r);print(r['status'],r['process']['returncode'],r['converged_steps'],flush=True)


def extract():
    source=load(FULL/'execution_receipt.json');p=load(PROTOCOL)
    assert source['process']['returncode']==0 and source['converged_steps']==[[1,1]]
    m=load(FULL/'simulation_manifest.json')['model'];POST.mkdir(exist_ok=False)
    block=stage_block(1,.00005,m,{})
    block=block[block.index('SOLVE')+1:]
    lines=['/BATCH','/CLEAR,START',database_resume(FULL/'checkpoint.db').strip(),'/FILNAME,v064post002']
    for line in block:
        if line=='SET,LAST':lines.extend(["FILE,'"+str((FULL/JOB).resolve()).replace('\\','/')+"',rst",'SET,1,1'])
        elif line=='SAVE,pilot_partial,db':lines.append('/COM,READ_ONLY_CHECKPOINT_GATE_FAILED')
        else:lines.append(line)
    lines+=['/EXIT,NOSAVE'];text='\n'.join(lines)+'\n';assert not re.search(r'^\s*SOLVE\s*$',text,re.M|re.I)
    (POST/'input.inp').write_text(text)
    write_json(POST/'provenance.json',{'mode':'READ_ONLY_POST1_ZERO_SOLVE_COMMANDS','source_execution_receipt_sha256':file_hash(FULL/'execution_receipt.json'),'source_RST_sha256':file_hash(FULL/(JOB+'.rst')),'source_protocol_sha256':file_hash(PROTOCOL),'source_checkpoint_database_sha256':file_hash(FULL/'checkpoint.db'),'input_sha256':file_hash(POST/'input.inp')})
    r=run_input(POST,timeout=300,rss_GiB=8,reserve_GiB=12)
    out=RUN/'mechanical_results/read_only_extraction_002';out.mkdir(exist_ok=False)
    for name in ['input.inp','execution_receipt.json','provenance.json','stage001_gate.txt','stage001_history.csv','stage001_contact.csv']:
        if (POST/name).exists():shutil.copy2(POST/name,out/name)
    print(r['status'],r['process']['returncode'],(POST/'stage001_gate.txt').read_text() if (POST/'stage001_gate.txt').exists() else 'No gate')


if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['prepare','execute','extract']);arg=a.parse_args()
    {'prepare':prepare,'execute':execute,'extract':extract}[arg.action]()
