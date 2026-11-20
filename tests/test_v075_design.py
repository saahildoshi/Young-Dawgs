"""The matched design uses conversations as units and retains failed seeds."""
import pytest

from scripts.v075_design import assign, improvement, paired_effect, score


def test_pairs_use_only_pretreatment_and_are_reproducible():
    rows = [{'trial_id': f'T{i:02d}', 'initial_mean_target_error': i / 1000 if i < 10 else None,
             'feasible': 3 if i != 11 else 0, 'mechanically_accepted': 3 if i < 10 else 0,
             'post_revision_error': 1 - i / 100} for i in range(12)]
    pairs = assign(rows, 75016)
    assert [[r['trial_id'] for r in pair['pretreatment_members']] for pair in pairs] == [
        [f'T{i:02d}', f'T{i+1:02d}'] for i in range(0, 12, 2)]
    for row in rows:
        row['post_revision_error'] = -row['post_revision_error']
    assert assign(list(reversed(rows)), 75016) == pairs
    assert {p[a] for p in pairs for a in ('IF', 'NF')} == {r['trial_id'] for r in rows}


def test_failure_penalty_preserves_attempt_denominator():
    assert score([1640, None, 1968], .10) == pytest.approx(.20 / 3)
    assert score([1640, None, 1968], None) == pytest.approx(.10)
    assert score([None, None], None) is None
    assert improvement([1640, None], [1640, 1640], .10) == pytest.approx(.05)


def test_randomization_uses_pair_sign_flips():
    pairs = [{'pair_id': i, 'IF': f'A{i}', 'NF': f'B{i}'} for i in range(6)]
    rows = [{'trial_id': p[a], 'improvement': .01 if a == 'IF' else 0}
            for p in pairs for a in ('IF', 'NF')]
    result = paired_effect(pairs, rows)
    assert result['favor_IF'] == 6
    assert result['mean'] == pytest.approx(.01)
    assert result['exploratory_exact_two_sided_p'] == 2 / 64


def test_control_and_feedback_share_structure_but_only_feedback_contains_measurements():
    from scripts.v075_packets import MEASURED_MARKER, compose
    geometry = {'development_structures': [{'seed': 6100, 'status': 'GENERATED'}]}
    control = compose('Same task', geometry)
    feedback = compose('Same task', geometry, {'own_initial': [{'apparent_modulus_MPa': 1623.456}]})
    assert control.startswith(feedback.split(MEASURED_MARKER)[0])
    assert '1623.456' not in control and MEASURED_MARKER not in control
    assert '1623.456' in feedback


def test_chronology_preserves_extra_turns_and_rejects_a_different_chat():
    from scripts.v075_trials import capture_identity
    url = 'https://chatgpt.com/c/6b0079c1-ae18-83e9-87f0-b8440e82d82a'
    sub = {'chat_url': url, 'observed_chat_url': url, 'ordinary_ChatGPT': True,
           'Work_or_Codex': False, 'model_calls': 1}
    turn = 'text (heading) You said:\ntext (heading) ChatGPT said:\n'
    assert capture_identity(sub, turn * 2, 1, url)['strict_turn_count']
    assert not capture_identity(sub, turn * 3, 1, url)['strict_turn_count']
    with pytest.raises(ValueError, match='differs from the original'):
        capture_identity(sub, turn * 2, 1, url[:-1] + 'b')


def test_invalid_categorical_array_is_preserved_as_failed_attempt(tmp_path):
    import numpy as np
    from scripts.v070_protocol import read, sha
    from scripts.v075_trials import worker

    source = tmp_path / 'invalid.py'
    source.write_text('import numpy as np\ndef generate_microstructure(seed, parameters):\n    return np.array([1, 7])\n')
    dest = tmp_path / 'attempt'
    worker(source, dest, 6100)
    result = read(dest / 'seed_6100.json')
    assert result['status'] == 'OUTPUT_CONTRACT_FAILED'
    raw = dest / 'returned_seed_6100.npy'
    assert np.array_equal(np.load(raw, allow_pickle=False), [1, 7])
    assert result['returned_array']['sha256'] == sha(raw)
    assert not (dest / 'seed_6100.npy').exists()
