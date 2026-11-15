"""Focused exact-composition, registration and no-repair contract checks."""
import numpy as np
from scripts.v070_protocol import read,sha
from scripts.v073_experiment import RUN,PREV
from scripts.v073_prepare import module
from scripts.v073_envelope import feasibility

def test_registered_seed_partitions_and_equal_trials():
    s=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json');p=read(RUN/'protocol/PROTOCOL.json')
    assert not set(s['calibration'])&set(s['development'])
    assert not set(s['heldout'])&(set(s['calibration'])|set(s['development']))
    history=read(RUN/'audit/HISTORICAL_SEED_INVENTORY.json')['unique_seed_ids']
    assert not set(history)&set(s['heldout']+s['development']+s['calibration'])
    assert sum(t.startswith('IF') for t in p['trial_order'])==sum(t.startswith('NF') for t in p['trial_order'])==4
    assert p['repair_calls']==0 and p['response_budget_per_trial']==1

def test_exact_generator_provenance_and_no_import_generation():
    record=read(RUN/'starting_generator/AUTHENTICATION.json')
    assert sha(PREV/'starting_generator/generator.py')==record['original_sha256']
    assert record['researcher_adapted'] and record['not_independent_LLM_trial']
    assert sha(RUN/'starting_generator/generator.py')==record['adapted_sha256']

def test_count_adaptation_is_small_non_noise_deterministic_and_preserves_topology():
    adapted=module(RUN/'starting_generator/generator.py');original=module(PREV/'starting_generator/generator.py')
    from scipy import ndimage as ndi
    for seed in [3000,3005,3011]:
        a=adapted.generate_microstructure(seed,{});b=original.generate_microstructure(seed,{})
        assert a.shape==(256,256) and a.dtype==np.uint8 and set(np.unique(a))=={1,5}
        assert int((a==5).sum())==20731 and int((a==1).sum())==44805
        assert np.array_equal(a,adapted.generate_microstructure(seed,{}))
        assert np.count_nonzero(a!=b)==abs(int((b==5).sum())-20731)
        assert ndi.label(a==5)[1]==ndi.label(b==5)[1]
        assert ndi.label(a==1)[1]==ndi.label(b==1)[1]

def test_evaluator_rejects_one_wrong_pixel_without_repair():
    row=read(RUN/'envelope_calibration/seed_3000.json');policy=read(RUN/'protocol/FEASIBILITY_FROZEN.json')
    assert feasibility(row,policy)['passed']
    row['phase_counts']['5']+=1
    assert 'phase_count' in feasibility(row,policy)['failures']

def test_historical_challenges_all_detected_without_historical_reclassification():
    r=read(RUN/'historical_lane_controls/CHALLENGE_RESULTS.json')
    assert len(r)==50
    assert all(v['detected'] for v in r if v['trial_id']!='BASE')
    assert all(v['historical_acceptance_unchanged'] for v in r)

def test_target_rule_precedes_mechanics_and_rewards_accuracy():
    p=read(RUN/'protocol/PROTOCOL.json');rule=p['target_selection']
    assert rule['fraction_toward_variant']==.6 and rule['rounding']=='none'
    assert p['feedback_advantage_sign'].startswith('mean independent NF')
    assert 'mean absolute relative target error' in p['primary_metric']
