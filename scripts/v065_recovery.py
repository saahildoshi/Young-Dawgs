"""Prospective v0.6.5 jobs: system-health supervision, native output, read-only export."""
import argparse
from dataclasses import asdict
from pathlib import Path
import json
import re
import shutil
import subprocess
import psutil
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.native_output import SELECTIVE_OUTPUT,OUTPUT_AUXILIARY,read_only_input
from metamaterial_eval.simulation.system_health import HealthPolicy
from metamaterial_eval.simulation.windows_ansys import bounded_run
from metamaterial_eval.simulation.nonlinear_diagnostics import DiagnosticBudget,telemetry_commands,diagnostic_stop,parse_solver_log,parse_contact,contact_summary
from metamaterial_eval.simulation.solver_execution import discover_solver,file_hash,solver_release,solver_warnings
from metamaterial_eval.simulation.reporting import write_json

REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'experiments/pipeline_v0.6.5/run_001'
BASE=artifact_root()/'solver/v065'
OLD=artifact_root()/'solver/v064'
FULL=BASE/'full_recovery_001'
FULL_PROTOCOL=RUN/'protocol/FULL_RECOVERY_001.json'


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def committed(path):
    path=Path(path).relative_to(REPO).as_posix()
    subprocess.run(['git','ls-files','--error-unmatch',path],check=True,stdout=subprocess.DEVNULL)
    subprocess.run(['git','diff','--exit-code','HEAD','--',path],check=True,stdout=subprocess.DEVNULL)


def run_job(directory,*,timeout=180,cores=2,solve=True):
    directory=Path(directory)
    active=[p.pid for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() in ['ansys.exe','ansys241.exe']]
    if active:raise RuntimeError('Another solver is active: '+str(active))
    budget=DiagnosticBudget(completed_iterations_cap=32,cutbacks_cap=3)
    receipt=bounded_run([str(discover_solver()),'-b','-smp','-np',str(cores),'-m','4096','-j','compression',
        '-i','input.inp','-o','solver.out'],directory,prepared=True,timeout=timeout,rss_limit=None,
        min_disk_free=20*1024**3,min_available_ram=0,resource_sample_seconds=1,health_policy=HealthPolicy(),
        stop_check=(lambda p:diagnostic_stop(p,budget)) if solve else None)
    log=(directory/'solver.out').read_text(errors='replace') if (directory/'solver.out').exists() else ''
    t=parse_solver_log(log)
    warnings=solver_warnings(log)
    result={'status':receipt['status'],'process':receipt,'solver_version':solver_release(log),
        'input_sha256':file_hash(directory/'input.inp'),'converged_steps':[(r['load_step'],r['substep']) for r in t['converged_substeps']],
        'warnings':list(dict.fromkeys(warnings)),'warning_occurrences':len(warnings),'native_jobname':'compression' if solve else 'readonly',
        'execution_kind':'LICENSED_NONLINEAR_SOLVE' if solve else 'READ_ONLY_POST1_NO_SOLVE'}
    write_json(directory/'execution_receipt.json',result)
    write_json(directory/'nonlinear_telemetry.json',t)
    if solve:
        path=directory/'compression.cnd'
        c=parse_contact(path.read_text(errors='replace')) if path.exists() else {'records':[],'issues':['MISSING_FILE']}
        write_json(directory/'contact_telemetry.json',c);write_json(directory/'contact_summary.json',contact_summary(c['records']))
    return result


def prepare_job(directory,setup,model,*,strain=.00005,selective=True,omit=None,protocol=None):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    lines=['/BATCH','/CLEAR,START',database_resume(Path(setup)/'contact_model.db').strip(),'/GOPR','/PREP7',
        'KEYOPT,3,2,1','KEYOPT,3,4,2','KEYOPT,3,10,1','RMODIF,2,3,100','RMODIF,3,3,100',
        '/OUTPUT,model_inventory,txt','ETLIST,ALL','RLIST,ALL','MPLIST,ALL','DLIST,ALL','/OUTPUT','FINISH',
        '/SOLU','NEQIT,24','NSUBST,1,1,1','KBC,0']
    output=SELECTIVE_OUTPUT if selective else ['OUTRES,ERASE','OUTRES,ALL,LAST']
    lines += [x for x in output if not (omit and x.startswith('OUTRES,'+omit+','))]
    lines += OUTPUT_AUXILIARY+telemetry_commands(model['controls']['top'])
    lines += [f'TIME,{strain:.17g}',f'D,{model["controls"]["top"]},UY,{-strain*model["config"]["height"]:.17g}',
              'SOLVE','FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    (directory/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    model={**model,'contact_algorithm_keyopt2':1,'contact_detection_keyopt4':2,'contact_stiffness_update_keyopt10':1,'FKN':100}
    write_json(directory/'simulation_manifest.json',{'model':model,'source_contact_database_sha256':file_hash(Path(setup)/'contact_model.db'),
        'input_sha256':file_hash(directory/'input.inp'),'protocol_sha256':file_hash(protocol or RUN/'protocol/RECOVERY_PLAN_001.json'),
        'output_selection':output,'omitted_required_category_negative_control':omit,'target_strain':strain})


def extract(source,label,*,chunk_size=250000):
    source=Path(source);target=BASE/label;target.mkdir(parents=True,exist_ok=False)
    m=load(source/'simulation_manifest.json');strain=m['target_strain']
    text=read_only_input(source/'checkpoint.db',source/'compression',m['model'],strain,chunk_size=chunk_size)
    (target/'input.inp').write_text(text,encoding='utf-8')
    bindings={'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
        'source_RST_sha256':file_hash(source/'compression.rst'),'source_checkpoint_database_sha256':file_hash(source/'checkpoint.db'),
        'source_database_filename':'checkpoint.db','source_manifest_sha256':file_hash(source/'simulation_manifest.json'),
        'source_protocol_sha256':m['protocol_sha256'],'input_sha256':file_hash(target/'input.inp'),
        'scope':'Independent fresh POST1 process, MODEL-only database and SET1,1 from native RST; no SOLVE or SAVE commands'}
    write_json(target/'provenance.json',bindings)
    r=run_job(target,timeout=600,cores=1,solve=False)
    print(label,r['status'],r['process']['returncode'],flush=True)
    return target


def copy_compact(source,target):
    target.mkdir(parents=True,exist_ok=False)
    for name in ['input.inp','simulation_manifest.json','execution_receipt.json','nonlinear_telemetry.json','contact_telemetry.json','contact_summary.json',
                 'provenance.json','stage001_history.csv','stage001_gate.txt','stage001_contact.csv','result_sets.txt','model_inventory.txt']:
        path=source/name
        if path.exists():
            if path.suffix=='.txt':(target/name).write_text('\n'.join(s.rstrip() for s in path.read_text(errors='replace').splitlines())+'\n',encoding='utf-8')
            else:shutil.copy2(path,target/name)


def small_study():
    committed(RUN/'protocol/RECOVERY_PLAN_001.json')
    for name,setup in [('rectangle',artifact_root()/'solver/v063/staged_control_setup_001'),('compliant',OLD/'compliant_setup_001')]:
        model=load(setup/'model_manifest.json')
        for choice in ['full','selective']:
            label=name+'_'+choice+'_001';directory=BASE/label
            prepare_job(directory,setup,model,strain=.005,selective=choice=='selective')
            r=run_job(directory)
            print(label,r['status'],r['process']['returncode'],r['converged_steps'],flush=True)
            copy_compact(directory,RUN/'small_licensed'/label)
            if r['process']['returncode']!=0:raise RuntimeError('Small licensed solve failed; preserve and inspect '+label)
            post=extract(directory,label+'_post',chunk_size=128)
            copy_compact(post,RUN/'small_licensed'/(label+'_post'))
        post=extract(BASE/(name+'_selective_001'),name+'_selective_001_repeat',chunk_size=257)
        copy_compact(post,RUN/'small_licensed'/(name+'_selective_001_repeat'))


def prepare_full():
    from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest
    committed(RUN/'small_licensed/OUTPUT_PROTOCOL_VALIDATION.json')
    assert load(RUN/'small_licensed/OUTPUT_PROTOCOL_VALIDATION.json')['full_model_launch_eligible']
    prior=load(REPO/'experiments/pipeline_v0.6.4/run_001/audit/initial.json')
    mesh,artifact,_=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    assert artifact['semantic_sha256']==prior['mesh_semantic_sha256']
    geometry=REPO/'experiments/pipeline_v0.5/baseline_vectorization/run_003/fixture_B_design009_seed001/polygon_candidate.wkb'
    assert file_hash(geometry)==prior['source_geometry_sha256']
    assert (len(mesh.nodes),len(mesh.triangles))==(2766505,1261670)
    del mesh
    setup=artifact_root()/'solver/v063/contact_setup_002';m=load(setup/'model_manifest.json')
    accepted=load(setup/'contact_setup_validation.json')
    assert accepted['status']=='CONTACT_SETUP_PASS' and file_hash(setup/'contact_model.db')==accepted['process']['artifacts']['contact_model.db']['sha256']
    assert m['FKN']==100 and m['contact_algorithm_keyopt2']==1 and m['contact_stiffness_update_keyopt10']==1
    assert m['FTOLN_absolute_mm']==-1e-5 and m['config']['mode']=='plane_stress'
    protocol={'schema':'young-dawgs-v0.6.5-full-output-recovery','strains':[.00005],'target_travel_mm':.000512,
        'source_geometry_sha256':prior['source_geometry_sha256'],'mesh_semantic_sha256':prior['mesh_semantic_sha256'],
        'source_mesh_bytes_sha256':prior['mesh_bytes_sha256'],'nodes':2766505,'TRI6':1261670,'pores':412,
        'source_contact_database_sha256':file_hash(setup/'contact_model.db'),
        'selected_output':SELECTIVE_OUTPUT,'output_auxiliary':OUTPUT_AUXILIARY,
        'read_only_export':'Fresh process, MODEL-only checkpoint.db, native SET1,1, bounded APDL250000-node vectors; streamed Python/memmap arrays,20000-element mapping chunks',
        'system_health_policy':asdict(HealthPolicy()),'process_RSS_limit_bytes':None,'timeout_seconds':1800,'post_timeout_seconds':600,
        'disk_reserve_bytes':20*1024**3,'cores':2,'solver_memory_mode':'Retain inherited EQSLV SPARSE /BCSOPTION DEFAULT; no forced INCORE change',
        'nonlinear_controls':{'NSUBST':[1,1,1],'NEQIT':24,'NLGEOM':'ON','AUTOTS':'ON','NROPT':'FULL','LNSRCH':'ON','CNVTOL_F_relative':.005,'CNVTOL_F_minref_N':1e-8},
        'contact':{'KEYOPT2':1,'KEYOPT4':2,'KEYOPT10':1,'FKN':100,'FTOLN':-1e-5,'friction':'FRICTIONLESS_SEPARABLE','scope':'PLATEN_CONTACT_ONLY'},
        'acceptance':load(RUN/'protocol/RECOVERY_PLAN_001.json')['acceptance'],
        'small_output_validation_sha256':file_hash(RUN/'small_licensed/OUTPUT_PROTOCOL_VALIDATION.json'),
        'resource_at_freeze':{'available_RAM_bytes':psutil.virtual_memory().available,'physical_RAM_bytes':psutil.virtual_memory().total,'disk_free_bytes':shutil.disk_usage(BASE).free},
        'primary_runs_max':1,'conditional_local_technical_repair_max':1,'additional_strain_targets':'NOT_PLANNED; stop after one accepted point',
        'no_geometry_mesh_or_physical_model_change':True,'frozen_input_sha256':None}
    write_json(FULL_PROTOCOL,protocol)
    prepare_job(FULL,setup,m,protocol=FULL_PROTOCOL)
    protocol['frozen_input_sha256']=file_hash(FULL/'input.inp');write_json(FULL_PROTOCOL,protocol)
    manifest=load(FULL/'simulation_manifest.json');manifest.update(protocol_sha256=file_hash(FULL_PROTOCOL),
        source_geometry_sha256=prior['source_geometry_sha256'],mesh_semantic_sha256=prior['mesh_semantic_sha256'])
    write_json(FULL/'simulation_manifest.json',manifest)
    copy_compact(FULL,RUN/'full_recovery/prepared_001')
    print('Full input frozen',protocol['frozen_input_sha256'],'available GiB',protocol['resource_at_freeze']['available_RAM_bytes']/1024**3)


def execute_full():
    committed(FULL_PROTOCOL)
    p=load(FULL_PROTOCOL)
    assert file_hash(FULL/'input.inp')==p['frozen_input_sha256']
    assert psutil.virtual_memory().available>p['system_health_policy']['available_reserve_bytes']
    assert shutil.disk_usage(BASE).free>p['disk_reserve_bytes']
    write_json(RUN/'performance/prelaunch.json',{'available_RAM_bytes':psutil.virtual_memory().available,
        'physical_RAM_bytes':psutil.virtual_memory().total,'disk_free_bytes':shutil.disk_usage(BASE).free,
        'process_RSS_limit_bytes':None,'system_health_policy':p['system_health_policy']})
    r=run_job(FULL,timeout=p['timeout_seconds'],cores=p['cores'])
    copy_compact(FULL,RUN/'full_recovery/actual_001')
    print('Full recovery',r['status'],r['process']['returncode'],r['converged_steps'],flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['small','prepare-full','execute-full','extract-full'])
    args=parser.parse_args()
    if args.action=='small':small_study()
    elif args.action=='prepare-full':prepare_full()
    elif args.action=='execute-full':execute_full()
    else:
        p=extract(FULL,'full_recovery_001_post')
        copy_compact(p,RUN/'mechanical_results/read_only_001')
