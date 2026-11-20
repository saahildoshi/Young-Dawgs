"""All-attempt loss, matched randomization and numerical sensitivity."""
from statistics import mean, stdev

from scripts.v070_protocol import read, sha, write
from scripts.v073_analysis import csv_table
from scripts.v075_design import arm_effect, paired_effect, score, target_error
from scripts.v075_protocol import RUN, TRIALS, now
from scripts.v075_trials import ASSIGNMENT, FROZEN, verify_freeze


def compare(assignment, rows, exact_test=False):
    paired = paired_effect(assignment['pairs'], rows)
    if not exact_test:
        paired['exploratory_exact_two_sided_p'] = None
    return {'unweighted_conversations': arm_effect(rows), 'matched_pairs': paired}


def analyses(assignment, records, penalty, level, seeds=None, eligible=None, exact_test=False):
    rows = []
    for trial in TRIALS:
        if eligible is not None and trial not in eligible:
            continue
        versions = []
        for r in (0, 1):
            selected = [row for row in records if row['trial_id'] == trial and row['revision'] == r
                        and row['mesh_level'] == level and (seeds is None or row['seed'] in seeds)]
            values = [row['apparent_modulus_MPa'] for row in selected]
            valid = [v for v in values if v is not None]
            versions.append({'loss': score(values, penalty), 'attempted': len(values), 'accepted': len(valid),
                'conditional_error': score(values, None), 'feasible': sum(row['structural_feasible'] for row in selected),
                'target_hits': sum(target_error(v) <= .02 for v in valid),
                'mean_modulus_MPa': mean(valid) if valid else None,
                'sample_SD_MPa': stdev(valid) if len(valid) > 1 else None})
        initial, revised = versions
        value = None if any(r['loss'] is None for r in versions) else initial['loss'] - revised['loss']
        rows.append({'trial_id': trial, 'arm': assignment['arms'][trial], 'initial': initial,
            'revised': revised, 'improvement': value})
    return {'script_rows': rows, **compare(assignment, rows, exact_test)}


def build():
    frozen = verify_freeze()
    assignment = read(ASSIGNMENT)
    p = read(RUN / 'protocol/PROTOCOL.json')
    seeds = read(RUN / 'protocol/EVALUATOR_ONLY_SEEDS.json')
    records, curves, refined = [], [], []
    for trial in TRIALS:
        for revision in (0, 1):
            folder = RUN / 'structures' / trial / f'r{revision}/heldout'
            structure = read(folder / 'SUMMARY.json')
            descriptors = {r['seed']: r for r in structure['rows']}
            by_mesh = {}
            for level, partition in ((1, 'heldout'), (2, 'H2')):
                campaign = read(RUN / 'mechanical_campaigns' / f'{trial}_r{revision}_heldout_H{level}.json')
                assert [r['seed'] for r in campaign['cases']] == seeds[partition]
                by_mesh[level] = {}
                for case in campaign['cases']:
                    seed = case['seed']
                    d = descriptors[seed]
                    assert case['structural_feasible'] == d['feasibility']['passed']
                    e = case['apparent_modulus_MPa']
                    eligible = case['status'] == 'ACCEPTED_NATIVE_RESULT'
                    assert (e is not None) == eligible
                    row = {**case, 'arm': assignment['arms'][trial], 'generation_status': d['status'],
                        'exact_composition': d.get('phase_counts') == {'1': 44805, '5': 20731},
                        'generation_seconds': d.get('generation_seconds'), 'deterministic': d.get('deterministic'),
                        'diversity_pass': structure['diversity']['passed'], 'mechanical_accepted': eligible,
                        'target_error': target_error(e), 'target_hit': target_error(e) <= .02 if eligible else None,
                        'attempt_loss_10pct': score([e], .10), 'array_sha256': d.get('array_file_sha256')}
                    records.append(row)
                    by_mesh[level][seed] = row
                    if eligible:
                        result = read(RUN / 'mechanical_response' / f'{trial}_r{revision}_heldout_{seed}_H{level}_attempt001.json')
                        assert result['accepted'] and all(result['checks'].values())
                        assert result['effective_modulus_MPa'] == e
                        for step, (strain, stress) in enumerate(zip(result['engineering_strains'], result['nominal_stresses_MPa']), 1):
                            curves.append({'trial_id': trial, 'revision': revision, 'seed': seed, 'mesh_level': level,
                                'step': step, 'engineering_compression': strain, 'nominal_compression_MPa': stress,
                                'native_RST_sha256': result['native_result_sha256']})
            for seed in seeds['H2']:
                h1, h2 = by_mesh[1][seed], by_mesh[2][seed]
                assert h1['array_sha256'] == h2['array_sha256']
                a, b = h1['apparent_modulus_MPa'], h2['apparent_modulus_MPa']
                shift = abs(b - a) / a if a is not None and b is not None else None
                refined.append({'trial_id': trial, 'revision': revision, 'seed': seed,
                    'array_sha256': h1['array_sha256'], 'H1_MPa': a, 'H2_MPa': b,
                    'H1_error': h1['target_error'], 'H2_error': h2['target_error'], 'H1_hit': h1['target_hit'],
                    'H2_hit': h2['target_hit'], 'relative_modulus_shift': shift,
                    'classification': 'UNAVAILABLE' if shift is None else ('WITHIN_2_PERCENT' if shift <= .02 else 'ABOVE_2_PERCENT')})
    primary = analyses(assignment, records, p['primary_penalty'], 1, exact_test=True)
    compliant = {r['trial_id'] for r in frozen['responses'] if r['revision'] == 1 and r['strict_turn_count']}
    strict = analyses(assignment, records, p['primary_penalty'], 1, eligible=compliant)
    penalties = {str(k): analyses(assignment, records, k, 1) for k in p['failure_penalties']}
    conditional = analyses(assignment, records, None, 1)
    loo = [{'excluded_trial': omitted, **compare(assignment, [r for r in primary['script_rows']
          if r['trial_id'] != omitted])} for omitted in TRIALS]
    mesh_comparison = {f'H{level}': analyses(assignment, records, .10, level, seeds=seeds['H2'])
                       for level in (1, 2)}
    deltas = []
    for trial in TRIALS:
        a, b = [next(r['improvement'] for r in mesh_comparison[f'H{level}']['script_rows']
                     if r['trial_id'] == trial) for level in (1, 2)]
        deltas.append({'trial_id': trial, 'H1_refined_subset_improvement': a,
            'H2_refined_subset_improvement': b, 'same_direction': (a > 0) == (b > 0) and (a < 0) == (b < 0)})
    output = RUN / 'script_level_analysis'
    for path, data in [('HELDOUT_ATTEMPTS', records), ('NATIVE_CURVES', curves), ('MESH_CONFIRMATION', refined),
                       ('SCRIPT_LEVEL_OUTCOMES', primary['script_rows']),
                       ('MATCHED_PAIR_OUTCOMES', primary['matched_pairs']['pairs']),
                       ('H1_H2_IMPROVEMENT', deltas)]:
        write(output / f'{path}.json', data)
        csv_table(output / f'{path}.csv', data)
    write(output / 'PRIMARY_ANALYSIS.json', primary)
    write(output / 'SENSITIVITY.json', {'penalty': penalties, 'uncapped_accepted_only': conditional,
        'strict_counts': strict, 'leave_one_conversation_out': loo, 'fixed_H1_H2_subset': mesh_comparison})
    write(output / 'PROVENANCE.json', {'created_utc': now(), 'collective_freeze_sha256': sha(FROZEN),
        'independent_units': 12, 'randomized_pairs': 6, 'stochastic_seeds_nested': True,
        'H1_attempts': 144, 'H2_slots': 72, 'actual_accepted_native_models': len(curves) // 5})


if __name__ == '__main__':
    build()
