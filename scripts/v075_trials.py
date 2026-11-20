"""Capture and evaluate authentic responses with versioned evidence paths."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import shutil
from statistics import mean
import subprocess
import sys
import time

import numpy as np

from scripts.v070_protocol import REPO, read, sha, write
from scripts.v070_experiment import audit
from scripts.v073_envelope import feasibility
from scripts.v072_experiment import diversity, observe
from scripts.v073_prepare import save_array
from metamaterial_eval.composites.morphology_v073 import describe
from scripts.v074_trials import conversation_id
from scripts.v075_design import assign, target_error
from scripts.v075_protocol import BASE, DOC, RUN, TRIALS, now

FROZEN = RUN / 'frozen_scripts/ALL_V075_SCRIPTS_AND_CONVERSATIONS_FROZEN.json'
ASSIGNMENT = RUN / 'assignment/MATCHED_ASSIGNMENT_FROZEN.json'


def capture_identity(submission, ui, revision, initial_url=None):
    url = submission['observed_chat_url']
    identity = conversation_id(url)
    if identity != conversation_id(submission['chat_url']):
        raise ValueError('Observed and recorded conversation IDs differ')
    if revision and identity != conversation_id(initial_url):
        raise ValueError('Revision conversation differs from the original')
    if not submission['ordinary_ChatGPT'] or submission['Work_or_Codex'] or submission['model_calls'] != 1:
        raise ValueError('Expected one ordinary ChatGPT response')
    if ' button Stop' in ui:
        raise ValueError('Response may still be streaming')
    users = ui.count('text (heading) You said:')
    assistants = ui.count('text (heading) ChatGPT said:')
    if users < revision + 1 or assistants < revision + 1:
        raise ValueError('The captured chronology omits a registered turn')
    return {'conversation_id': identity, 'observed_user_turns': users,
        'observed_assistant_turns': assistants, 'strict_turn_count': users == assistants == revision + 1}


def ingest(trial, revision):
    directory = RUN / 'llm_trials' / trial
    receipt = directory / f'RECEIPT_r{revision}.json'
    source = directory / f'generator_r{revision}.py'
    if receipt.exists() or source.exists() or FROZEN.exists():
        raise FileExistsError('Source already captured or study frozen')
    submission = read(directory / f'SUBMISSION_r{revision}.json')
    assert submission['trial_id'] == trial
    prompt = directory / 'followup_prompt.txt' if revision else RUN / 'feedback_packets/INITIAL_PROMPT.txt'
    if revision:
        assignment = read(ASSIGNMENT)
        assert submission['arm'] == assignment['arms'][trial]
        assert sha(prompt) == read(directory / 'FOLLOWUP_PACKET_FROZEN.json')['prompt_sha256']
    else:
        assert submission['arm'] is None
        assert submission['raw_image_sha256'] == read(RUN/'feedback_packets/INITIAL_FROZEN.json')['raw_image_sha256']
    assert sha(prompt) == submission['prompt_sha256']
    chronology = directory / f'chronology_r{revision}.txt'
    initial_url = read(directory / 'SUBMISSION_r0.json')['chat_url'] if revision else None
    identity = capture_identity(submission, chronology.read_text(encoding='utf-8'), revision, initial_url)
    raw = directory / f'returned_code_r{revision}.txt'
    code = raw.read_text(encoding='utf-8-sig')
    try:
        result = audit(code)
    except Exception as error:
        result = {'passed': False, 'failures': [repr(error)]}
    source.write_text(code, encoding='utf-8', newline='\n')
    write(receipt, {**submission, **identity, 'revision': revision, 'captured_utc': now(),
        'response_capture_sha256': sha(raw), 'chronology_sha256': sha(chronology),
        'code_sha256': sha(source), 'audit': result, 'researcher_repairs': False,
        'normalization': 'UTF-8 and LF executable copy; original capture retained'})
    print(trial, revision, result, flush=True)


def verify_freeze():
    frozen = read(FROZEN)
    for name, digest in frozen['files'].items():
        assert sha(REPO / name) == digest, name
    return frozen


def worker(source, destination, seed):
    destination.mkdir(parents=True, exist_ok=False)
    row = {'seed': seed, 'status': 'EXECUTION_ERROR', 'generator_sha256': sha(source)}
    try:
        spec = importlib.util.spec_from_file_location('v075_generator', source)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        start = time.perf_counter()
        array = module.generate_microstructure(seed, {})
        elapsed = time.perf_counter() - start
        row['generation_seconds'] = elapsed
        if isinstance(array, np.ndarray):
            row['returned_array'] = {'shape': list(array.shape), 'dtype': str(array.dtype), 'nbytes': array.nbytes}
            if not array.dtype.hasobject and array.nbytes <= 2**20:
                raw_array = destination / f'returned_seed_{seed}.npy'
                np.save(raw_array, array, allow_pickle=False)
                row['returned_array']['sha256'] = sha(raw_array)
        if not (isinstance(array, np.ndarray) and array.shape == (256, 256)
                and array.dtype == np.uint8 and set(np.unique(array)) == {1, 5}):
            row['status'] = 'OUTPUT_CONTRACT_FAILED'
            raise ValueError('Required 256 by 256 uint8 array with labels 1 and 5')
        if elapsed > 30:
            row['status'] = 'GENERATION_TIME_EXCEEDED'
            raise TimeoutError('First generation exceeded the registered 30-second bound')
        start = time.perf_counter()
        replay = module.generate_microstructure(seed, {})
        row['replay_seconds'] = time.perf_counter() - start
        # Preserve the v074 eligibility rule used for trial one. Replay timing
        # is retained for diagnosis under the same 75-second worker deadline.
        deterministic = np.array_equal(array, replay)
        path = destination / f'seed_{seed}.npy'
        save_array(path, array)
        row.update(status='GENERATED', deterministic=bool(deterministic),
            array_file_sha256=sha(path), array_semantic_sha256=hashlib.sha256(array.tobytes()).hexdigest(),
            **observe(array), morphology_v073=describe(array == 5))
        if raw_array.exists():
            row['returned_array']['validated_copy_sha256'] = sha(path)
    except Exception as error:
        row['error'] = repr(error)
    write(destination / f'seed_{seed}.json', row)


def evaluate(trial, revision, partition):
    directory = RUN / 'llm_trials' / trial
    receipt = read(directory / f'RECEIPT_r{revision}.json')
    source = directory / f'generator_r{revision}.py'
    assert sha(source) == receipt['code_sha256']
    if partition == 'heldout':
        verify_freeze()
    else:
        assert revision == 0
    initial = read(RUN / 'feedback_packets/INITIAL_FROZEN.json')
    assert initial['evaluator_seed_sha256'] == sha(RUN / 'protocol/EVALUATOR_ONLY_SEEDS.json')
    seeds = read(RUN / 'protocol/EVALUATOR_ONLY_SEEDS.json')[partition]
    destination = RUN / 'structures' / trial / f'r{revision}' / partition
    destination.mkdir(parents=True, exist_ok=False)
    policy = read(RUN / 'protocol/FEASIBILITY_FROZEN.json')
    rows, arrays = [], []
    for seed in seeds:
        record = {'seed': seed, 'status': 'CODE_AUDIT_FAILED', 'generator_sha256': sha(source)}
        if receipt['audit']['passed']:
            worker = destination / 'workers' / str(seed)
            try:
                result = subprocess.run([sys.executable, '-m', 'scripts.v075_trials', 'worker',
                    str(source), str(worker), str(seed)], cwd=REPO, capture_output=True,
                    text=True, timeout=75)
                write(destination / f'WORKER_{seed}.json', {'returncode': result.returncode,
                    'stdout': result.stdout, 'stderr': result.stderr})
                path = worker / f'seed_{seed}.json'
                if result.returncode == 0 and path.exists():
                    record = read(path)
                    if record['status'] == 'GENERATED':
                        for ext in ('npy', 'png'):
                            shutil.copyfile(worker / f'seed_{seed}.{ext}', destination / f'seed_{seed}.{ext}')
                        arrays.append(np.load(destination / f'seed_{seed}.npy', allow_pickle=False))
                else:
                    record.update(status='WORKER_FAILED', error='Worker did not return a signed-off output record')
            except subprocess.TimeoutExpired:
                record.update(status='WORKER_TIMEOUT', error='Registered 75-second worker timeout')
        record['feasibility'] = feasibility(record, policy)
        record.update(trial_id=trial, revision=revision, partition=partition)
        write(destination / f'seed_{seed}.json', record)
        rows.append(record)
    cohort = diversity(arrays, policy)
    write(destination / 'SUMMARY.json', {'trial_id': trial, 'revision': revision, 'partition': partition,
        'attempted': len(seeds), 'generated': len(arrays),
        'feasible': sum(r['feasibility']['passed'] for r in rows), 'diversity': cohort,
        'fully_qualified_generator': all(r['feasibility']['passed'] for r in rows) and cohort['passed'], 'rows': rows})


def native(trial, revision, partition, level):
    if partition == 'heldout':
        verify_freeze()
    else:
        assert revision == 0 and level == 1
    from scripts import v074_mechanics as mechanics
    mechanics.RUN, mechanics.BASE, mechanics.DOC = RUN, BASE, DOC
    BASE.mkdir(parents=True, exist_ok=True)
    campaign = RUN / 'mechanical_campaigns' / f'{trial}_r{revision}_{partition}_H{level}.json'
    if campaign.exists():
        raise FileExistsError('Campaign already started. Review preserved evidence before resumption.')
    mechanics.campaign(trial, revision, partition, level)


def match():
    if ASSIGNMENT.exists():
        raise FileExistsError('Assignment is already frozen')
    rows = []
    identities = set()
    for trial in TRIALS:
        d = RUN / 'llm_trials' / trial
        if (d / 'SUBMISSION_r1.json').exists():
            raise ValueError('A revision was submitted before assignment')
        receipt = read(d / 'RECEIPT_r0.json')
        identities.add(receipt['conversation_id'])
        structure = RUN / 'structures' / trial / 'r0/development/SUMMARY.json'
        native_results = RUN / 'mechanical_campaigns' / f'{trial}_r0_development_H1.json'
        structural, mechanical = read(structure), read(native_results)
        seeds = read(RUN / 'protocol/EVALUATOR_ONLY_SEEDS.json')['development']
        assert [r['seed'] for r in structural['rows']] == [r['seed'] for r in mechanical['cases']] == seeds
        moduli = [r['apparent_modulus_MPa'] for r in mechanical['cases'] if r['status'] == 'ACCEPTED_NATIVE_RESULT']
        rows.append({'trial_id': trial, 'conversation_id': receipt['conversation_id'],
            'initial_script_sha256': receipt['code_sha256'], 'initial_execution_success': structural['generated'] > 0,
            'feasible': structural['feasible'], 'feasibility_rate': structural['feasible'] / 3,
            'mechanically_accepted': len(moduli), 'initial_mean_target_error': mean(map(target_error, moduli)) if moduli else None,
            'structural_summary_sha256': sha(structure), 'native_campaign_sha256': sha(native_results)})
    assert len(identities) == len(TRIALS)
    seed = read(RUN / 'protocol/PROTOCOL.json')['randomization_seed']
    pairs = assign(rows, seed)
    arms = {pair[arm]: arm for pair in pairs for arm in ('IF', 'NF')}
    balance = {}
    for arm in ('IF', 'NF'):
        group = [r for r in rows if arms[r['trial_id']] == arm]
        errors = [r['initial_mean_target_error'] for r in group if r['initial_mean_target_error'] is not None]
        balance[arm] = {'trials': len(group), 'mean_available_target_error': mean(errors) if errors else None,
            'missing_baseline_errors': len(group) - len(errors), 'mean_feasibility': mean(r['feasibility_rate'] for r in group)}
    write(RUN / 'assignment/PRETREATMENT_FROZEN.json', rows)
    write(ASSIGNMENT, {'frozen_utc': now(), 'algorithm': 'adjacent pairs, one independent PCG64 integer draw per pair',
        'seed': seed, 'pretreatment_sha256': sha(RUN / 'assignment/PRETREATMENT_FROZEN.json'),
        'pairs': pairs, 'arms': arms, 'balance': balance})


def freeze():
    assert not FROZEN.exists() and not list((RUN / 'structures').glob('*/r*/heldout'))
    files = [ASSIGNMENT, RUN / 'assignment/PRETREATMENT_FROZEN.json',
        RUN / 'feedback_packets/INITIAL_PROMPT.txt', RUN / 'feedback_packets/INITIAL_FROZEN.json',
        *sorted((RUN / 'protocol').glob('*.json')),
        *(REPO / 'scripts' / name for name in ('v075_trials.py', 'v075_design.py', 'v075_analysis.py',
            'v075_packets.py', 'v074_mechanics.py', 'v071_mechanics.py'))]
    assignment = read(ASSIGNMENT)
    identities = set()
    receipts = []
    for trial in TRIALS:
        d = RUN / 'llm_trials' / trial
        old, new = [read(d / f'RECEIPT_r{rev}.json') for rev in (0, 1)]
        assert old['conversation_id'] == new['conversation_id'] and new['arm'] == assignment['arms'][trial]
        identities.add(old['conversation_id'])
        for rev, record in enumerate((old, new)):
            for name, key in [(f'generator_r{rev}.py', 'code_sha256'), (f'returned_code_r{rev}.txt', 'response_capture_sha256'),
                              (f'chronology_r{rev}.txt', 'chronology_sha256')]:
                assert sha(d / name) == record[key]
                files.append(d / name)
            files += [d / f'RECEIPT_r{rev}.json', d / f'SUBMISSION_r{rev}.json']
            receipts.append(record)
        assert sha(d / 'followup_prompt.txt') == new['prompt_sha256']
        files += [d / 'followup_prompt.txt', d / 'FOLLOWUP_PACKET_FROZEN.json']
    assert len(identities) == 12
    write(FROZEN, {'frozen_utc': now(), 'conversations': 12, 'responses': receipts,
        'files': {p.relative_to(REPO).as_posix(): sha(p) for p in files}})


if __name__ == '__main__':
    if len(sys.argv) == 5 and sys.argv[1] == 'worker':
        worker(Path(sys.argv[2]), Path(sys.argv[3]), int(sys.argv[4]))
        sys.exit(0)
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['ingest', 'evaluate', 'native', 'match', 'freeze'])
    parser.add_argument('--trial', choices=TRIALS)
    parser.add_argument('--revision', type=int, choices=(0, 1), default=0)
    parser.add_argument('--partition', choices=['development', 'heldout'], default='development')
    parser.add_argument('--level', type=int, choices=(1, 2), default=1)
    args = parser.parse_args()
    if args.action in ('ingest', 'evaluate', 'native') and not args.trial:
        parser.error('--trial is required')
    actions = {
        'ingest': lambda: ingest(args.trial, args.revision),
        'evaluate': lambda: evaluate(args.trial, args.revision, args.partition),
        'native': lambda: native(args.trial, args.revision, args.partition, args.level),
        'match': match, 'freeze': freeze,
    }
    actions[args.action]()
