"""Pretreatment assignment and registered conversation-level scoring."""
from itertools import product
from statistics import mean, median, stdev

import numpy as np


def assign(rows, seed):
    """Rank exclusively by registered pretreatment fields before randomization."""
    if len(rows) != 12 or len({row['trial_id'] for row in rows}) != 12:
        raise ValueError('Exactly twelve distinct pretreatment rows are required')

    def rank(row):
        error = row['initial_mean_target_error']
        return (error is None, error if error is not None else 0,
                -row['feasible'], -row['mechanically_accepted'], row['trial_id'])

    ordered = sorted(rows, key=rank)
    rng = np.random.Generator(np.random.PCG64(seed))
    pairs = []
    for i in range(6):
        members = ordered[2*i:2*i+2]
        draw = int(rng.integers(0, 2))
        pairs.append({'pair_id': f'PAIR_{i+1:02d}',
            'pretreatment_members': [{k: row[k] for k in (
                'trial_id', 'initial_mean_target_error', 'feasible', 'mechanically_accepted')}
                for row in members],
            'draw': draw, 'IF': members[draw]['trial_id'], 'NF': members[1-draw]['trial_id']})
    return pairs


def target_error(modulus, target=1640):
    return None if modulus is None else abs(modulus - target) / target


def score(moduli, penalty):
    errors = [target_error(v) for v in moduli]
    if penalty is None:
        finite = [e for e in errors if e is not None]
        return mean(finite) if finite else None
    return mean(penalty if e is None else min(e, penalty) for e in errors)


def improvement(initial, revised, penalty):
    first, second = score(initial, penalty), score(revised, penalty)
    return None if first is None or second is None else first - second


def arm_effect(rows):
    arms = {arm: [r['improvement'] for r in rows if r['arm'] == arm
                  and r['improvement'] is not None] for arm in ('IF', 'NF')}
    averages = {arm: mean(values) if values else None for arm, values in arms.items()}
    return {'means': averages, 'n': {arm: len(v) for arm, v in arms.items()},
        'IF_minus_NF': averages['IF'] - averages['NF'] if all(v is not None for v in averages.values()) else None}


def paired_effect(pairs, rows):
    by_id = {r['trial_id']: r['improvement'] for r in rows}
    out = []
    for pair in pairs:
        a, b = by_id.get(pair['IF']), by_id.get(pair['NF'])
        out.append({'pair_id': pair['pair_id'], 'IF': pair['IF'], 'NF': pair['NF'],
            'IF_improvement': a, 'NF_improvement': b,
            'pair_effect': a - b if a is not None and b is not None else None})
    values = [r['pair_effect'] for r in out if r['pair_effect'] is not None]
    observed = mean(values) if values else None
    randomization = None
    if len(values) == len(pairs):
        reference = [mean(sign * v for sign, v in zip(signs, values))
                     for signs in product((-1, 1), repeat=len(values))]
        randomization = sum(abs(x) >= abs(observed)-1e-15 for x in reference) / len(reference)
    return {'pairs': out, 'mean': observed, 'median': median(values) if values else None,
        'sample_SD': stdev(values) if len(values) > 1 else None,
        'favor_IF': sum(v > 0 for v in values), 'favor_NF': sum(v < 0 for v in values),
        'ties': sum(v == 0 for v in values), 'paired_n': len(values),
        'exploratory_exact_two_sided_p': randomization,
        'randomization_assumption': 'Sharp null of no assignment effect, no interference, registered independent within-pair assignments; small paired sample.'}
