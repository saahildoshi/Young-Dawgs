"""Small licensed restart/multi-checkpoint qualification and reusable export."""
from pathlib import Path
import argparse
import re
import shutil
import numpy as np
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.progressive_compression import (
    load,load_commands,authenticated_restart_copy,continuation_input,multi_export_input,run_progressive)
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.reporting import write_json
from scripts.v065_recovery import prepare_job

REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'experiments/pipeline_v0.6.6/run_001'
BASE=artifact_root()/'solver/v066'
PLAN=RUN/'protocol/LARGE_STRAIN_PLAN_001.json'


def compact(source,target):
    target.mkdir(parents=True,exist_ok=False)
    for name in ['input.inp','simulation_manifest.json','execution_receipt.json','nonlinear_telemetry.json','contact_summary.json',
                 'restart_provenance.json','provenance.json','result_sets.txt','restart_sets.txt']:
        path=source/name
        if not path.exists():continue
        if name=='execution_receipt.json' and path.stat().st_size>1024**2:
            receipt=load(path);samples=receipt['process'].pop('resource_samples',[])
            receipt.update(derived_compact_copy=True,raw_receipt_sha256=file_hash(path),resource_samples_stored_externally=len(samples))
            write_json(target/name,receipt)
        elif path.suffix=='.txt':(target/name).write_text('\n'.join(s.rstrip() for s in path.read_text(errors='replace').splitlines())+'\n',encoding='utf-8')
        else:shutil.copy2(path,target/name)
    for path in source.glob('stage*_history.csv'):shutil.copy2(path,target/path.name)
    for path in source.glob('stage*_gate.txt'):shutil.copy2(path,target/path.name)
    for path in source.glob('stage*_contact.csv'):
        if path.stat().st_size<1024**2:shutil.copy2(path,target/path.name)
    for path in source.glob('stage*_contact_status.csv'):
        if path.stat().st_size<1024**2:shutil.copy2(path,target/path.name)


def endpoint_states(directory,targets):
    rows=load(Path(directory)/'nonlinear_telemetry.json')['converged_substeps']
    states=[]
    for target in targets:
        candidates=[r for r in rows if abs(r.get('pseudo_time',-1)-target)<1e-12]
        if len(candidates)!=1:raise ValueError('Missing/duplicate actual endpoint '+str(target))
        r=candidates[0];states.append({'time':r['pseudo_time'],'load_step':r['load_step'],'substep':r['substep']})
    return states


def export(directory,label,states,*,chunk_size=250000,farfield=False):
    directory=Path(directory);out=BASE/label;out.mkdir(parents=True,exist_ok=False)
    manifest=load(directory/'simulation_manifest.json')
    database=directory/'checkpoint.db' if (directory/'checkpoint.db').exists() else directory/'compression.rdb'
    text=multi_export_input(database,directory/'compression',manifest['model'],states,chunk_size=chunk_size,farfield=farfield)
    (out/'input.inp').write_text(text,encoding='utf-8')
    write_json(out/'provenance.json',{'source':str(directory.resolve()),'source_execution_receipt_sha256':file_hash(directory/'execution_receipt.json'),
        'source_RST_sha256':file_hash(directory/'compression.rst'),'source_database_filename':database.name,'source_database_sha256':file_hash(database),
        'source_manifest_sha256':file_hash(directory/'simulation_manifest.json'),'states':states,'input_sha256':file_hash(out/'input.inp'),
        'mode':'READ_ONLY_NATIVE_MULTI_SET_NO_SOLVE_OR_SAVE','native_farfield_status_inventory':farfield})
    r=run_progressive(out,timeout=1800,solve=False,cores=1)
    print(label,r['status'],r['process']['returncode'],flush=True)
    return out


def prepare_small(name,setup,targets):
    directory=BASE/name;model=load(setup/'model_manifest.json')
    prepare_job(directory,setup,model,strain=targets[0],protocol=PLAN)
    text=(directory/'input.inp').read_text()
    text=text.replace('NSUBST,1,1,1','NSUBST,2,200,1,OFF').replace('RESCONTROL,DEFINE,ALL,LAST,1','RESCONTROL,DEFINE,ALL,ALL,-1,,3')
    if len(targets)>1:
        text=text[:text.index('SAVE,checkpoint,db,,MODEL')]
        assert text.rstrip().endswith('FINISH')
        text=text.rstrip()[:-len('FINISH')]
        for previous,target in zip(targets,targets[1:]):
            text+='\n'.join(load_commands(target,previous,model['controls']['top'],model['config']['height'],initial=.00125,all_fields=False))+'\n'
        text+='FINISH\nSAVE,checkpoint,db,,MODEL\n/EXIT,NOSAVE\n'
    (directory/'input.inp').write_text(text,encoding='utf-8')
    manifest=load(directory/'simulation_manifest.json');manifest.update(input_sha256=file_hash(directory/'input.inp'),targets=targets,target_strain=targets[-1])
    write_json(directory/'simulation_manifest.json',manifest)
    return directory


def small_study(revision='002'):
    records=[]
    for fixture,setup in [('rectangle',artifact_root()/'solver/v063/staged_control_setup_001'),
                          ('compliant',artifact_root()/'solver/v064/compliant_setup_001')]:
        continuous=BASE/(fixture+'_continuous_'+revision)
        if continuous.exists():r=load(continuous/'execution_receipt.json')
        else:
            continuous=prepare_small(continuous.name,setup,[.0025,.005]);r=run_progressive(continuous,timeout=180)
        print(continuous.name,r['status'],r['process']['returncode'],r['converged_steps'],flush=True)
        if not (RUN/'restart_validation'/continuous.name).exists():compact(continuous,RUN/'restart_validation'/continuous.name)
        if r['process']['returncode']!=0:raise RuntimeError('Continuous fixture failed: '+fixture)
        states=endpoint_states(continuous,[.0025,.005])
        post=export(continuous,continuous.name+'_post003',states,chunk_size=128)
        compact(post,RUN/'restart_validation'/post.name)
        initial=BASE/(fixture+'_pause_'+revision)
        if initial.exists():r=load(initial/'execution_receipt.json')
        else:
            initial=prepare_small(initial.name,setup,[.0025]);r=run_progressive(initial,timeout=180)
        print(initial.name,r['status'],r['process']['returncode'],flush=True)
        if not (RUN/'restart_validation'/initial.name).exists():compact(initial,RUN/'restart_validation'/initial.name)
        if r['process']['returncode']!=0:raise RuntimeError('Pause fixture failed: '+fixture)
        previous=endpoint_states(initial,[.0025])[0]
        restart=BASE/(fixture+'_restart_'+revision)
        if restart.exists():r=load(restart/'execution_receipt.json')
        else:
            manifest=authenticated_restart_copy(initial,restart)
            text=continuation_input(previous['load_step'],previous['substep'],[.005],.0025,manifest['model'],all_fields=False,initial=.00125)
            (restart/'input.inp').write_text(text,encoding='utf-8');manifest.update(input_sha256=file_hash(restart/'input.inp'),targets=[.005],target_strain=.005)
            write_json(restart/'simulation_manifest.json',manifest);r=run_progressive(restart,timeout=180)
        print(restart.name,r['status'],r['process']['returncode'],r['converged_steps'],flush=True)
        if not (RUN/'restart_validation'/restart.name).exists():compact(restart,RUN/'restart_validation'/restart.name)
        if r['process']['returncode']!=0:raise RuntimeError('Actual native restart failed: '+fixture)
        after=endpoint_states(restart,[.005])[0]
        repeat=export(restart,restart.name+'_post003',[previous,after],chunk_size=257)
        compact(repeat,RUN/'restart_validation'/repeat.name)
        comparisons={}
        for stage in [1,2]:
            for field in ['history','contact','displacements','stress']:
                filename=f'stage{stage:03d}_{field}.csv'
                a=np.loadtxt(post/filename,delimiter=',',skiprows=1,ndmin=2);b=np.loadtxt(repeat/filename,delimiter=',',skiprows=1,ndmin=2)
                assert a.shape==b.shape
                scale=np.maximum(abs(a).max(axis=0),1e-12);error=abs(a-b).max(axis=0)/scale
                comparisons[filename]={'max_column_scaled_difference':error.tolist(),'passed':bool(np.all(error<1e-5))}
                assert np.all(error<1e-5),(fixture,filename,error)
            assert float((post/f'stage{stage:03d}_gate.txt').read_text().split(',')[0])==0
            assert float((repeat/f'stage{stage:03d}_gate.txt').read_text().split(',')[0])==0
        records.append({'fixture':fixture,'states':states,'native_restart_point':previous,'after_restart':after,'comparisons':comparisons,
            'restart_manifest_sha256':file_hash(restart/'restart_provenance.json'),'actual_rst_reopened':True})
    write_json(RUN/'restart_validation/RESTART_VALIDATION.json',{'status':'PASS_ACTUAL_LICENSED_NATIVE_RESTART','fixtures':records,
        'not_coordinate_only_restart':True,'cumulative_displacement_verified':True,'required_fields_read_after_restart':True})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['small']);args=parser.parse_args()
    if args.action=='small':small_study()
