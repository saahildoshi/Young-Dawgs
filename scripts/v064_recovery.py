"""Explicit prepare/execute entry points for the single registered full retry."""
from dataclasses import asdict
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import psutil
from metamaterial_eval.simulation.mesh_artifacts import artifact_root,resolve_manifest
from metamaterial_eval.simulation.microstructure_pilot import prepare_pilot
from metamaterial_eval.simulation.nonlinear_diagnostics import DiagnosticBudget,telemetry_commands,run_diagnostic
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.reporting import write_json
from scripts.v064_small_study import RUN,BASE,REPO,load

PROTOCOL=RUN/'protocol/FULL_RECOVERY_001.json'
DIRECTORY=BASE/'full_recovery_001'
JOB='v064r001'


def prepare():
    from validation.ansys_v064_integration import validated_contact
    for label in ['pp_nodal_recovery_controls','rectangle_pp_nodal','rectangle_pp_nodal_2cores']:validated_contact(label)
    assert not DIRECTORY.exists() and not PROTOCOL.exists()
    mesh,artifact,path=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    protocol=load(REPO/'experiments/pipeline_v0.6.3/run_001/protocol/PILOT_PROTOCOL_002.json')
    budget=DiagnosticBudget(completed_iterations_cap=32,cutbacks_cap=3,trend_window=6,stop_stagnation=True,minimum_iterations_before_stagnation=24,minimum_cutbacks_before_stagnation=1)
    protocol.update(schema='young-dawgs-v0.6.4-full-recovery',revision=1,strains=[.0001],contact_detection_keyopt4=2,
        corrective_action='Nodal contact detection with target normal; no specimen/physical model changes',
        root_cause_hypothesis='Gauss contact-detection sensitivity with native chatter and platen-local FY residual. Causal small control passes only after key4=2; historical full causality still requires this retry.',
        predecessor_status='V063 no converged substeps; unchanged exact mesh/import reused',
        max_additional_full_model_attempts=0,primary_full_model_attempts_max=1,native_jobname=JOB,
        accepted_small_recovery_receipt_sha256=file_hash(BASE/'pp_nodal_recovery_controls/execution_receipt.json'),
        correction_amendment_sha256=file_hash(RUN/'protocol/SMALL_AMENDMENT_003.json'),
        telemetry=['NLDIAG CONT ITER','NLDIAG NRRE ON2','NLDIAG EFLG ON2','NLHIST UY/RF at upper pilot','1s actual resource samples'],
        diagnostic_budget=asdict(budget),
        early_stop_rationale='NEQIT8 failed corrected compliant control; tested24/NSUBST2,20,1 with2SMP converged after actual cutback. Allow first24 updates, then six-evaluation stagnant/oscillating/increasing current-trial history after>=1cutback; cap32 total completed updates or3cutbacks. First large residual alone is never a stop.',
        concurrency='one owned MAPDL tree',
        resource_at_freeze={'available_RAM_bytes':psutil.virtual_memory().available,'disk_free_bytes':shutil.disk_usage(artifact_root()).free},
        parallel_scope='Actual2SMP licensed rectangle and compliant controls passed; no total license entitlement/all20core or full-model speedup claim',
        full_trial_vs_mechanical='All CND/NR trial records UNCONVERGED_DIAGNOSTIC_ONLY; native convergence, signedRF/contact, full fields and mapping gates required',
        eligibility='Single accepted checkpoint gives only secant response, never fitted modulus or design ranking')
    protocol['resource']['cores']=2;protocol['controls']['NEQIT']=24
    write_json(PROTOCOL,protocol)
    setup=artifact_root()/'solver/v063/contact_setup_002'
    model=prepare_pilot(DIRECTORY,setup,PROTOCOL)
    # Run001's committed deck attempted FILNAME in PREP7; that harmless command
    # was ignored and native compression.* outputs are bound by observed hashes.
    # Future preparation must rename at Begin level. Never rewrite frozen input.
    commands=['/GOPR',f'/FILNAME,{JOB}','/PREP7','KEYOPT,3,4,2','/OUTPUT,corrected_inventory,txt','ETLIST,ALL','RLIST,ALL','MPLIST,ALL','DLIST,ALL','/OUTPUT','FINISH','/SOLU','NEQIT,24','NSUBST,2,20,1','KBC,0','OUTRES,ALL,LAST']+telemetry_commands(model['controls']['top'])+['/OUTPUT,initial_contact,txt','CNCHECK,DETAIL','/OUTPUT']
    p=DIRECTORY/'input.inp';text=p.read_text();text=text.replace('/NOPR','\n'.join(commands),1);p.write_text(text)
    protocol['frozen_input_sha256']=file_hash(p);write_json(PROTOCOL,protocol)
    manifest=load(DIRECTORY/'simulation_manifest.json');manifest['model']['contact_detection_keyopt4']=2
    manifest.update(result_jobname=JOB,input_sha256=file_hash(p),protocol_sha256=file_hash(PROTOCOL),diagnostic_protocol='FULL_RECOVERY_001',source_specimen_import_receipt_sha256=file_hash(REPO/'experiments/pipeline_v0.6.3/run_001/import_only/attempt_001/import_execution.json'))
    write_json(DIRECTORY/'simulation_manifest.json',manifest)
    out=RUN/'full_model_retry/prepared_001';out.mkdir(exist_ok=False)
    for name in ['input.inp','simulation_manifest.json']:shutil.copy2(DIRECTORY/name,out/name)
    print('Prepared immutable single full-model recovery input',file_hash(p))


def execute():
    relative=PROTOCOL.relative_to(REPO).as_posix()
    subprocess.run(['git','ls-files','--error-unmatch',relative],cwd=REPO,check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['git','diff','--exit-code','HEAD','--',relative],cwd=REPO,check=True,stdout=subprocess.DEVNULL)
    p=load(PROTOCOL)
    if file_hash(DIRECTORY/'input.inp')!=p['frozen_input_sha256']:raise ValueError('Frozen solver input changed')
    active=[q.pid for q in psutil.process_iter(['name']) if q.info['name'] and q.info['name'].lower() in ['ansys.exe','ansys241.exe']]
    if active:raise RuntimeError('Another MAPDL job is active; no concurrent full retry')
    if psutil.virtual_memory().available<12*1024**3:raise RuntimeError('OS RAM reserve unavailable')
    r=run_diagnostic(DIRECTORY,cores=2,timeout=1200,rss_GiB=20,budget=DiagnosticBudget(**p['diagnostic_budget']),jobname=JOB)
    write_json(RUN/'full_model_retry/execution_001.json',r)
    print(r['status'],r['process']['returncode'],r['converged_steps'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['prepare','execute']);a=parser.parse_args()
    prepare() if a.action=='prepare' else execute()
