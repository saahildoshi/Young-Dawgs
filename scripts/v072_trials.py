"""Authentic response ingestion and evaluator-only execution after collective freeze."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v070_experiment import audit
from scripts.v072_experiment import RUN,TRIALS,now,feasibility,diversity,OLD
from metamaterial_eval.pipeline.scripts import extract_python_script
from metamaterial_eval.composites.microscopy import errors,VISIBLE,HIDDEN


def ingest(trial):
    d=RUN/'llm_trials'/trial;assert trial in TRIALS
    assert not (d/'RECEIPT.json').exists()
    submission=read(d/'SUBMISSION.json');assert submission['prompt_sha256']==sha(d/'prompt.txt')
    capture=d/'response.txt';assert capture.is_file()
    source=d/'generator.py';assert not source.exists()
    try:
        code=extract_python_script(capture.read_text(encoding='utf-8-sig'))
        source.write_text(code,encoding='utf-8',newline='\n');review=audit(code)
        status='RECEIVED_CODE_AUDIT_PASS' if review['passed'] else 'RECEIVED_CODE_AUDIT_FAILED'
    except Exception as e:review={'passed':False,'failures':[repr(e)]};status='RESPONSE_EXTRACTION_FAILED'
    write(d/'RECEIPT.json',{'trial_id':trial,'condition':'MF' if '_MF_' in trial else 'NF',**submission,
        'captured_utc':now(),'response_sha256':sha(capture),'code_sha256':sha(source) if source.exists() else None,
        'status':status,'audit':review,'researcher_repairs':False,'model_calls':1,'repair_calls':0,
        'capture':'Complete ordinary ChatGPT response captured through Windows UI accessibility/code-copy controls; method details and original UI evidence retained separately',
        'tokens':None,'cost':None,'backend_version':None,'normalization':'Python extraction only, no logic changes; original captured bytes preserved'})
    print(trial,status,review,flush=True)


def freeze():
    destination=RUN/'frozen_scripts/ALL_OPTIMIZATION_SCRIPTS_FROZEN.json';assert not destination.exists()
    packet=read(RUN/'feedback_packets/PROMPTS_FROZEN.json')
    assert sha(RUN/'protocol/PROTOCOL.json')==packet['protocol_sha256']
    assert sha(RUN/'protocol/FEASIBILITY_FROZEN.json')==packet['feasibility_sha256']
    assert sha(RUN/'feedback_packets/MF_ACTUAL_MECHANICS.json')==packet['feedback_sha256']
    inventory={};urls=[]
    for trial in TRIALS:
        d=RUN/'llm_trials'/trial;r=read(d/'RECEIPT.json')
        assert r['model_calls']==1 and not r['researcher_repairs'] and r['ordinary_ChatGPT'] and not r['Work_or_Codex']
        assert sha(d/'prompt.txt')==packet['prompt_hashes'][trial]==r['prompt_sha256']
        assert sha(d/'response.txt')==r['response_sha256']
        if r['code_sha256']:assert sha(d/'generator.py')==r['code_sha256']
        inventory[trial]=r;urls.append(r['chat_url'])
    assert len(set(urls))==4,'Trials are not independent conversations'
    write(destination,{'frozen_utc':now(),'scripts':inventory,'BASE_sha256':sha(RUN/'starting_generator/generator.py'),
        'prompts_sha256':sha(RUN/'feedback_packets/PROMPTS_FROZEN.json'),'common_protocol_sha256':sha(RUN/'protocol/PROTOCOL.json'),
        'seed_partition_sha256':sha(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json'),'feasibility_sha256':sha(RUN/'protocol/FEASIBILITY_FROZEN.json'),
        'qualified_evaluator_sha256':sha(REPO/'scripts/v071_mechanics.py'),'no_future_calls_or_repairs_this_experiment':True,
        'independent_MF':2,'independent_NF':2,'heldout_started':False})
    print('ALL FOUR AUTHENTIC RESPONSES FROZEN; heldout generation now eligible',flush=True)


def heldout(trial):
    frozen=read(RUN/'frozen_scripts/ALL_OPTIMIZATION_SCRIPTS_FROZEN.json')
    assert sha(RUN/'protocol/PROTOCOL.json')==frozen['common_protocol_sha256']
    assert sha(RUN/'protocol/FEASIBILITY_FROZEN.json')==frozen['feasibility_sha256']
    seed_file=RUN/'protocol/EVALUATOR_ONLY_SEEDS.json';assert sha(seed_file)==frozen['seed_partition_sha256']
    source=RUN/'starting_generator/generator.py' if trial=='BASE' else RUN/'llm_trials'/trial/'generator.py'
    expected=frozen['BASE_sha256'] if trial=='BASE' else frozen['scripts'][trial]['code_sha256']
    destination=RUN/'heldout_structures'/trial;destination.mkdir(parents=True,exist_ok=False)
    policy=read(RUN/'protocol/FEASIBILITY_FROZEN.json');target=read(OLD/'references/P3/descriptors.json')
    source_ok=expected is not None and source.exists() and sha(source)==expected
    review=audit(source.read_text()) if source_ok else {'passed':False,'failures':['No captured executable module']}
    write(destination/'CODE_AUDIT.json',review);rows=[];arrays=[]
    for seed in read(seed_file)['heldout']:
        worker=destination/'workers'/str(seed)
        row={'seed':seed,'status':'CODE_AUDIT_FAILED','generator_sha256':expected}
        if review['passed']:
            try:
                result=subprocess.run([sys.executable,'-m','scripts.v072_experiment','generate',str(source),str(worker),str(seed)],
                    cwd=REPO,capture_output=True,text=True,timeout=70)
                write(destination/f'worker_{seed}_receipt.json',{'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'timeout_seconds':70})
                if (worker/f'seed_{seed}.json').exists():
                    row=read(worker/f'seed_{seed}.json')
                    for suffix in ['npy','png']:
                        path=worker/f'seed_{seed}.{suffix}'
                        if path.exists():shutil.copyfile(path,destination/path.name)
                else:row.update(status='WORKER_ERROR',error='Worker returned no seed record')
            except subprocess.TimeoutExpired as e:
                row.update(status='WORKER_TIMEOUT',error='70-second bound for two deterministic runs plus evaluation exceeded')
                write(destination/f'worker_{seed}_receipt.json',{'timeout':True,'timeout_seconds':70})
        row['feasibility']=feasibility(row,policy)
        if row['status']=='GENERATED':
            row['visible_error']=errors(row['descriptors'],target,'P3',VISIBLE['P3'])
            row['hidden_error']=errors(row['descriptors'],target,'P3',HIDDEN['P3'])
            arrays.append(np.load(destination/f'seed_{seed}.npy',allow_pickle=False))
        write(destination/f'seed_{seed}.json',row);rows.append(row)
        print(trial,seed,row['status'],row['feasibility']['passed'],row['feasibility']['failures'],flush=True)
    div=diversity(arrays,policy) if len(arrays)>=2 else {'passed':False,'outputs':len(arrays)}
    write(destination/'DIVERSITY.json',div)
    write(destination/'SUMMARY.json',{'trial_id':trial,'attempted':10,'generated':len(arrays),
        'feasible':sum(r['feasibility']['passed'] for r in rows),'fully_qualified_generator':all(r['feasibility']['passed'] for r in rows) and div['passed'],
        'diversity':div,'rows':rows,'no_invalid_seed_replacement':True})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action');p.add_argument('trial',nargs='?');a=p.parse_args()
    if a.action=='ingest':ingest(a.trial)
    elif a.action=='freeze':freeze()
    elif a.action=='heldout':heldout(a.trial)
