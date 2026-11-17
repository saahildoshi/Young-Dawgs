"""Scientific estimands: bias cancellation, failed attempts, independent units."""
import pytest
from scripts.v073_analysis import target_metrics
from scripts.v074_analysis import summarize, arm_comparison


def case(modulus):
    return {'apparent_modulus_MPa': modulus, **target_metrics(modulus, 1640, .02)}


def test_target_error_cannot_cancel_opposite_signed_errors():
    result = summarize([case(1476), case(1804)], 2)
    assert result['target_error']['mean'] == pytest.approx(.1)
    assert result['mean_property_bias'] == 0
    assert result['target_hits'] == 0


def test_failed_attempt_remains_in_hit_denominator_without_fake_score():
    result = summarize([case(1640), case(None)], 2)
    assert result['mechanically_accepted'] == 1
    assert result['target_error']['n'] == 1
    assert result['target_error']['mean'] == 0
    assert result['target_hits_per_accepted'] == 1
    assert result['target_hits_per_attempt'] == .5
    empty = summarize([case(None)] * 6, 6)
    assert empty['target_error']['mean'] is None
    assert empty['target_hits_per_accepted'] is None


def test_arm_estimate_weights_scripts_equally_and_pairs_their_own_initial():
    summaries, changes = [], []
    for trial, initial, revised in [('IF_01', .20, .10), ('IF_02', .02, .02), ('NF_01', .10, .08)]:
        for revision, error in enumerate((initial, revised)):
            summaries.append({'trial_id': trial, 'arm': trial[:2], 'revision': revision,
                'target_error': {'mean': error}, 'fully_qualified_generator': True})
        changes.append({'trial_id': trial, 'arm': trial[:2], 'initial_minus_revised_mean_error': initial - revised})
    result = arm_comparison(summaries, changes)
    assert result['arms']['IF']['revised_script_errors']['mean'] == pytest.approx(.06)
    assert result['revised_error_advantage_NF_minus_IF'] == pytest.approx(.02)
    assert result['improvement_advantage_IF_minus_NF'] == pytest.approx(.03)
    sensitivity = arm_comparison(summaries, changes, ('NF_01',))
    assert sensitivity['arms']['NF']['registered_conversations_in_analysis'] == 0
    assert sensitivity['revised_error_advantage_NF_minus_IF'] is None
