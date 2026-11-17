"""Unedited ordinary-chat capture ingestion and bounded evaluator-only generation."""
import argparse
import hashlib
import importlib.util
import shutil
import subprocess
import sys
import time
import numpy as np
from scripts.v070_protocol import REPO, read, write, sha
from scripts.v070_experiment import audit
from scripts.v074_experiment import RUN, now
from scripts.v072_experiment import observe, diversity
from scripts.v073_envelope import feasibility
from metamaterial_eval.composites.morphology_v073 import describe
from scripts.v073_prepare import save_array


def ingest(trial, revision):
    d = RUN/'llm_trials'/trial
    assert trial in read(RUN/'protocol/PROTOCOL.json')['trial_order']
    receipt = d/f'RECEIPT_r{revision}.json'
    assert not receipt.exists()
    raw = d/f'returned_code_r{revision}.txt'
    source = d/f'generator_r{revision}.py'
    assert not source.exists()
    # The original UTF8 editor capture is retained byte-for-byte. Only CRLF is
    # normalized for executable Python, with no researcher logic edits.
    code = raw.read_text(encoding='utf-8-sig')
    source.write_text(code, encoding='utf-8', newline='\n')
    try:
        review = audit(code)
    except Exception as error:
        review = {'passed':False, 'failures':[repr(error)]}
    submission = read(d/f'SUBMISSION_r{revision}.json')
    prompt = d/('initial_prompt.txt' if revision == 0 else 'followup_prompt.txt')
    assert sha(prompt) == submission['prompt_sha256']
    if revision:
        assert submission['chat_url'] == read(d/'SUBMISSION_r0.json')['chat_url']
    write(receipt, {**submission, 'captured_utc':now(),
        'response_capture_sha256':sha(raw), 'code_sha256':sha(source),
        'normalization':'UTF8 text; CRLF to LF only; original capture retained',
        'audit':review, 'researcher_repairs':False,
        'status':'CODE_AUDIT_PASS' if review['passed'] else 'CODE_AUDIT_FAILED',
        'independent_unit':trial, 'revision':revision, 'backend_version':None,
        'tokens':None, 'cost':None})
    print(trial, revision, review, flush=True)


def worker(source, destination, seed):
    destination.mkdir(parents=True, exist_ok=False)
    spec = importlib.util.spec_from_file_location('v074_actual_generator', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    row = {'seed':seed, 'generator_sha256':sha(source), 'status':'EXECUTION_ERROR'}
    try:
        started = time.perf_counter()
        a = module.generate_microstructure(seed, {})
        elapsed = time.perf_counter()-started
        b = module.generate_microstructure(seed, {})
        if not (isinstance(a,np.ndarray) and a.shape==(256,256)
                and a.dtype==np.uint8 and set(np.unique(a))=={1,5}):
            raise ValueError('Categorical output contract violated')
        save_array(destination/f'seed_{seed}.npy', a)
        row.update(status='GENERATED', generation_seconds=elapsed,
            deterministic=bool(np.array_equal(a,b)),
            array_file_sha256=sha(destination/f'seed_{seed}.npy'),
            array_semantic_sha256=hashlib.sha256(a.tobytes()).hexdigest(),
            **observe(a), morphology_v073=describe(a==5))
    except Exception as error:
        row['error'] = repr(error)
    write(destination/f'seed_{seed}.json',row)


def evaluate(trial, revision, partition):
    d = RUN/'llm_trials'/trial
    r = read(d/f'RECEIPT_r{revision}.json')
    source = d/f'generator_r{revision}.py'
    assert sha(source)==r['code_sha256']
    if partition=='heldout':
        frozen=read(RUN/'frozen_scripts/ALL_SIXTEEN_SCRIPTS_FROZEN.json')
        assert frozen['scripts'][f'{trial}/r{revision}']['code_sha256']==sha(source)
        assert frozen['protocol_sha256']==sha(RUN/'protocol/PROTOCOL.json')
        assert frozen['feasibility_sha256']==sha(RUN/'protocol/FEASIBILITY_FROZEN.json')
        assert frozen['seed_partition_sha256']==sha(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')
        for name,digest in frozen['files'].items():assert sha(REPO/name)==digest,name
    else:
        assert revision==0
    destination = RUN/'structures'/trial/f'r{revision}'/partition
    assert not destination.exists()
    destination.mkdir(parents=True)
    seeds = read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')[partition]
    policy = read(RUN/'protocol/FEASIBILITY_FROZEN.json')
    rows=[]; arrays=[]
    for seed in seeds:
        row={'seed':seed, 'generator_sha256':sha(source), 'status':'CODE_AUDIT_FAILED'}
        if r['audit']['passed']:
            output=destination/'workers'/str(seed)
            try:
                result=subprocess.run([sys.executable,'-m','scripts.v074_trials','worker',str(source),str(output),str(seed)],
                    cwd=REPO,capture_output=True,text=True,timeout=75)
                write(destination/f'WORKER_{seed}.json',{'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr,'timeout_seconds':75})
                if (output/f'seed_{seed}.json').exists():
                    row=read(output/f'seed_{seed}.json')
                    for suffix in ['npy','png']:
                        path=output/f'seed_{seed}.{suffix}'
                        if path.exists():shutil.copyfile(path,destination/path.name)
                else:row.update(status='WORKER_FAILED',error='No seed record returned')
            except subprocess.TimeoutExpired:
                row.update(status='WORKER_TIMEOUT',error='75-second bound for generation, exact replay and descriptors')
                write(destination/f'WORKER_{seed}.json',{'timeout':True,'timeout_seconds':75})
        row.update(trial_id=trial,revision=revision,partition=partition)
        row['feasibility']=feasibility(row,policy)
        if row['status']=='GENERATED':arrays.append(np.load(destination/f'seed_{seed}.npy',allow_pickle=False))
        write(destination/f'seed_{seed}.json',row);rows.append(row)
        print(trial,revision,partition,seed,row['status'],row['feasibility']['passed'],row['feasibility']['failures'],flush=True)
    div=diversity(arrays,policy)
    write(destination/'SUMMARY.json',{'trial_id':trial,'revision':revision,'partition':partition,
        'attempted':len(seeds),'generated':len(arrays),'feasible':sum(r['feasibility']['passed'] for r in rows),
        'fully_qualified_generator':all(r['feasibility']['passed'] for r in rows) and div['passed'],
        'rows':rows,'diversity':div,'no_repair_or_substitution':True})


def freeze():
    destination=RUN/'frozen_scripts/ALL_SIXTEEN_SCRIPTS_FROZEN.json'
    assert not destination.exists() and not any((RUN/'structures').glob('*/r*/heldout'))
    initial=read(RUN/'feedback_packets/INITIAL_FROZEN.json')
    assert sha(RUN/'protocol/PROTOCOL.json')==initial['protocol_sha256']
    assert sha(RUN/'protocol/FEASIBILITY_FROZEN.json')==initial['feasibility_sha256']
    inventory={};urls=[];deviations={};files={}
    for trial in initial['trial_order']:
        d=RUN/'llm_trials'/trial;url=read(d/'SUBMISSION_r0.json')['chat_url'];urls.append(url)
        for revision in [0,1]:
            r=read(d/f'RECEIPT_r{revision}.json');sub=read(d/f'SUBMISSION_r{revision}.json')
            assert r['ordinary_ChatGPT'] and not r['Work_or_Codex'] and not r['researcher_repairs']
            assert r['chat_url']==url==sub['chat_url'] and r['model_calls']==1
            assert sha(d/f'generator_r{revision}.py')==r['code_sha256']
            assert sha(d/f'returned_code_r{revision}.txt')==r['response_capture_sha256']
            prompt=d/('initial_prompt.txt' if revision==0 else 'followup_prompt.txt')
            assert sha(prompt)==r['prompt_sha256']
            if revision==0:assert sha(prompt)==initial['prompt_sha256']
            else:assert sha(prompt)==read(d/'FOLLOWUP_PACKET_FROZEN.json')['prompt_sha256']
            inventory[f'{trial}/r{revision}']=r
            for path in [d/f'generator_r{revision}.py',d/f'returned_code_r{revision}.txt',d/f'RECEIPT_r{revision}.json',prompt]:
                files[str(path.relative_to(REPO)).replace('\\','/')]=sha(path)
        if (d/'PROTOCOL_DEVIATION.json').exists():deviations[trial]=read(d/'PROTOCOL_DEVIATION.json')
    assert len(set(urls))==8 and len(inventory)==16
    write(destination,{'frozen_utc':now(),'scripts':inventory,'files':files,'distinct_initial_chat_URLs':urls,
        'registered_initial_and_revision_sources':16,'independent_conversations':8,
        'same_conversation_for_all_registered_revisions':True,'no_manual_repairs_or_extra_scientific_revisions':True,
        'protocol_deviations':deviations,'strict_equal_message_budget_verified':not deviations,
        'deviation_analysis':'Retain all registered trials; separately flag any nonconforming conversation and report a descriptive sensitivity analysis without it. Do not replace trials or infer an unqualified causal advantage.',
        'protocol_sha256':sha(RUN/'protocol/PROTOCOL.json'),'feasibility_sha256':sha(RUN/'protocol/FEASIBILITY_FROZEN.json'),
        'seed_partition_sha256':sha(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json'),
        'adapter_sha256':sha(REPO/'scripts/v074_mechanics.py'),'heldout_started':False,
        'no_additional_model_calls_after_freeze':True})
    print('ALL16 AUTHENTIC MODULES FROZEN; final evaluation eligible. Protocol deviations:',list(deviations),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action');p.add_argument('args',nargs='*');a=p.parse_args()
    if a.action=='ingest':ingest(a.args[0],int(a.args[1]))
    elif a.action=='evaluate':evaluate(a.args[0],int(a.args[1]),a.args[2])
    elif a.action=='worker':
        from pathlib import Path
        worker(Path(a.args[0]),Path(a.args[1]),int(a.args[2]))
    elif a.action=='freeze':freeze()
