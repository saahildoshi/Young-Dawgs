"""Register the replication before any conversation or native execution."""
import argparse
from collections import Counter
from pathlib import Path
import re
import shutil
import subprocess

import psutil

from scripts.v070_protocol import REPO, read, sha, write
from scripts.v074_experiment import MICRO, PREV as V073, RUN as V074, now
from metamaterial_eval.simulation.mesh_artifacts import artifact_root

RUN = REPO / 'experiments/pipeline_v0.7.5/run_001'
DOC = REPO / 'docs/pipeline_v0.7.5'
BASE = artifact_root() / 'solver/v075/run_001'
ASSETS = REPO / 'presentation_assets/v0.7.4'
REFERENCE = MICRO / 'references/P3/microscopy_input.png'
TRIALS = tuple(f'V075_T{i:02d}' for i in range(1, 13))


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO)


def register(request):
    if any(path.exists() for path in (RUN, DOC, BASE)):
        raise FileExistsError('Versioned replication already exists')
    starting_head = git('rev-parse', 'HEAD').decode().strip()
    old = read(V074 / 'summary/FINAL_PACKAGE_HASHES.json')['files']
    for name, digest in old.items():
        if sha(REPO / name) != digest:
            raise ValueError(f'Prior package mismatch: {name}')
    prior = read(V074 / 'protocol/PROTOCOL.json')
    initial = read(V074 / 'feedback_packets/INITIAL_FROZEN.json')
    assert sha(REFERENCE) == initial['raw_microscopy_image_sha256']
    policy = V073 / 'protocol/FEASIBILITY_FROZEN.json'
    assert sha(policy) == sha(V074 / 'protocol/FEASIBILITY_FROZEN.json')
    historical = set()
    for path in (REPO / 'experiments').rglob('seed_*.npy'):
        match = re.fullmatch(r'seed_(\d+)', path.stem)
        if match:
            historical.add(int(match[1]))
    for path in (REPO / 'experiments').rglob('EVALUATOR_ONLY_SEEDS.json'):
        for values in read(path).values():
            if isinstance(values, list):
                historical.update(value for value in values if type(value) is int)
    seeds = {'development': list(range(6100, 6103)), 'heldout': list(range(7100, 7106))}
    assert not historical.intersection(seeds['development'] + seeds['heldout'])
    seeds['H2'] = seeds['heldout'][:3]
    free = shutil.disk_usage(artifact_root()).free
    assert free >= (185 + 50) * 2**30
    protected = {n: sha(REPO / n) for n in git('ls-files', '-z').decode().split('\0') if n}
    old_raw = V074 / 'audit/FINAL_RAW_AVAILABILITY.json'
    protocol = {
        **{key: prior[key] for key in ('element', 'material', 'loading', 'strain_checkpoints', 'tolerances',
            'NLGEOM', 'allowed_dependencies', 'exact_reinforcement_count', 'exact_matrix_count',
            'starting_candidate_maximum', 'single_generation_timeout_seconds', 'worker_timeout_seconds')},
        'registered_utc': now(), 'starting_head': starting_head,
        'starting_branch': git('branch', '--show-current').decode().strip(),
        'starting_status': git('status', '--porcelain').decode(), 'request_sha256': sha(request),
        'trial_order': list(TRIALS), 'target_MPa': 1640, 'J_target': 1.64,
        'target_band_MPa': [1607.2, 1672.8], 'target_hit_tolerance': .02,
        'morphology_policy_sha256': sha(policy), 'reference_sha256': sha(REFERENCE),
        'matching': 'Sort by missing mechanical mean last, then ascending uncapped development mean absolute relative target error, descending feasible count, descending accepted count, and trial ID. Pair adjacent ranks.',
        'assignment': 'One PCG64 integer draw in [0,2) per sorted adjacent pair, in pair order. Draw selects IF member by zero-based position. No rerandomization.',
        'randomization_seed': 75016, 'arm_assignment_before_development': False,
        'message_budget': {'user_initial': 1, 'assistant_initial': 1, 'user_revision': 1, 'assistant_revision': 1},
        'context': 'Consistent ordinary persistent ChatGPT context and exposed effort setting; no account-setting changes. Record visible differences and unknown backend routing.',
        'failure_penalties': [.05, .10, .20], 'primary_penalty': .10,
        'primary_loss': 'Mean of six attempted seed losses, capped absolute relative error at 0.10 with failure scored 0.10. Failed modulus remains null.',
        'primary_effect': 'Mean IF minus NF of within-conversation initial minus revised losses. Each conversation has equal weight.',
        'robustness': ['all failure penalties', 'uncapped accepted-only', 'strict 2+2 compliance',
            'all leave-one-conversation-out contrasts', 'all six paired effects', 'matched H1/H2 subset'],
        'H2_selection': 'First three fixed final seeds for every initial/revised script, structurally feasible only; no substitutions.',
        'native_base': str(BASE), 'native_route': 'Qualified five-checkpoint source solve and independent RST readback',
        'resource_limits': {'maximum_native_jobs': 504, 'native_campaign_seconds': 14400,
            'solve_timeout_s': 1800, 'readback_timeout_s': 900, 'cores': 2, 'one_native_job': True,
            'rss_cap': None, 'disk_reserve_bytes': 50 * 2**30, 'raw_storage_budget_bytes': 185 * 2**30},
        'resource_basis': {'available_RAM_bytes': psutil.virtual_memory().available,
            'free_disk_bytes': free, 'max_development_H1': 36, 'max_heldout_H1': 144, 'max_H2': 72,
            'estimated_seconds': 180 * 28 + 72 * 100,
            'estimated_GiB': 180 * .340 + 72 * 1.360,
            'basis': 'Measured v074 held-out solve and readback durations and raw directory sizes. 185 GiB includes headroom above approximately 159 GiB for all three refinements.',
            'v074_performance_sha256': sha(V074 / 'performance/FINAL_SUMMARY.json')},
    }
    # All checks above precede writes. Every new file lives in the versioned scope.
    RUN.mkdir(parents=True)
    DOC.mkdir(parents=True)
    for folder in (RUN, DOC):
        (folder / '.gitattributes').write_text('* -text\n', encoding='utf-8', newline='\n')
    for name, path in [('USER_REQUEST.txt', request), ('FEASIBILITY_FROZEN.json', policy)]:
        destination = RUN / 'protocol' / name
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(path, destination)
    write(RUN / 'protocol/PROTOCOL.json', protocol)
    write(RUN / 'protocol/EVALUATOR_ONLY_SEEDS.json', seeds)
    write(RUN / 'audit/PROTECTED_BEFORE.json', protected)
    write(RUN / 'audit/REGISTRATION.json', {'tracked_files': len(protected),
        'v074_package_files_authenticated': len(old), 'prior_raw_availability_receipt_sha256': sha(old_raw),
        'historical_seed_count': len(historical), 'fresh_seed_collision': False})
    shutil.copyfile(V074 / 'audit/QUALIFIED_EVALUATOR.json', RUN / 'audit/QUALIFIED_EVALUATOR.json')
    old_prompt = V074 / 'feedback_packets/INITIAL_PROMPT.txt'
    assert sha(old_prompt) == initial['prompt_sha256']
    prompt = RUN / 'feedback_packets/INITIAL_PROMPT.txt'
    prompt.parent.mkdir()
    shutil.copyfile(old_prompt, prompt)
    write(RUN / 'feedback_packets/INITIAL_FROZEN.json', {
        'frozen_utc': now(), 'prompt_sha256': sha(prompt), 'raw_image_path': str(REFERENCE),
        'raw_image_sha256': sha(REFERENCE), 'mask_supplied': False, 'identical_prior_initial_task': True,
        'trial_order': list(TRIALS), 'treatment_assignments': None,
        'protocol_sha256': sha(RUN / 'protocol/PROTOCOL.json'),
        'evaluator_seed_sha256': sha(RUN / 'protocol/EVALUATOR_ONLY_SEEDS.json'),
    })
    for trial in TRIALS:
        write(RUN / 'llm_trials' / trial / 'PLAN.json', {
            'trial_id': trial, 'arm': None, 'pair': None, 'initial_prompt_sha256': sha(prompt),
            'raw_image_sha256': sha(REFERENCE), 'registered_user_turns': 2,
            'registered_assistant_turns': 2, 'initial_status': 'NOT_SUBMITTED',
        })
    (DOC / 'V0_7_5_PROTOCOL.md').write_text(
        '# v0.7.5 replication protocol\n\n'
        'Twelve ordinary ChatGPT conversations start from the same authenticated P3 SEM tile and byte-identical initial prompt used in v0.7.4. Each conversation has one initial generation and one revision. Development uses seeds 6100–6102. After every initial trial has three recorded development attempts, sort by availability and uncapped mean absolute target error, breaking ties by feasible count, accepted count and trial ID. Form adjacent pairs and make one PCG64 draw per pair with seed 75016. Preserve failed trials and assignment.\n\n'
        'IF receives its own accepted development measurements and the same v0.7.3 controlled measurements supplied in v0.7.4. Both arms receive the fixed target, physics, geometry policy and structural feedback. Each revision uses its original conversation. Freeze the complete evidence before generating seeds 7100–7105. Refine the first three fixed seeds where eligible.\n\n'
        'The target is 1640 MPa with an inclusive ±2% hit band. The primary script loss averages six attempts with accepted absolute relative errors capped at 10% and failures scored at 10%. Positive initial-minus-revised loss indicates improvement. Compare equal-weight conversation improvements and the six within-pair contrasts. Report the 5% and 20% penalty sensitivities, uncapped accepted-only analysis, strictly compliant subset, every leave-one-out contrast, and matched H1/H2 sensitivity.\n\n'
        'The v0.7.3 policy is copied byte-for-byte. Geometry, material, loading and native acceptance remain as specified in the qualified model. The maximum 252 source solves and their separate readbacks use one job at a time, two cores, a 240-minute aggregate native budget, 185 GiB new raw storage, and a 50 GiB system-disk reserve. The measured v0.7.4 sizes project approximately 159 GiB for the full design.\n',
        encoding='utf-8', newline='\n')
    print(f'Registered {len(TRIALS)} trials, {len(protected)} protected files and {len(old)} verified v0.7.4 package files.')


def audit_history():
    counts = Counter()
    rows = []
    for run in (V073, V074):
        for manifest in sorted((run / 'native_result_manifests').glob('*/NATIVE_ARTIFACTS.json')):
            for name, item in read(manifest).items():
                recorded = Path(item['path'])
                candidates = [recorded]
                parts = recorded.parts
                if 'solver' in parts:
                    candidates.append(artifact_root().joinpath(*parts[parts.index('solver'):]))
                actual = next((p for p in candidates if p.is_file()), None)
                digest = sha(actual) if actual else None
                state = 'UNAVAILABLE' if actual is None else ('AUTHENTICATED' if digest == item['sha256'] else 'HASH_MISMATCH')
                counts[state] += 1
                rows.append({'study': run.parent.name, 'manifest': manifest.relative_to(REPO).as_posix(),
                    'file': name, 'recorded_path': str(recorded), 'actual_path': str(actual) if actual else None,
                    'expected_sha256': item['sha256'], 'actual_sha256': digest, 'state': state})
    write(RUN / 'audit/HISTORICAL_RAW_AVAILABILITY.json', {'checked_utc': now(),
        'configured_root': str(artifact_root()), 'counts': dict(counts), 'rows': rows,
        'non_solver_assets_raw_native_state': 'NOT_APPLICABLE'})
    print(dict(counts), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=['register', 'audit-history'])
    parser.add_argument('--request', type=Path)
    args = parser.parse_args()
    if args.operation == 'register':
        parser.error('--request is required') if args.request is None else register(args.request)
    else:
        audit_history()
