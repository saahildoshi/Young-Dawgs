"""New bounded common template and prospective target contracts."""
import numpy as np
import pytest
from scripts.v070_protocol import read,sha
from scripts.v074_experiment import RUN,PREV
from scripts.v073_prepare import module
from scripts.v070_experiment import audit

def test_policy_is_byte_identical_and_target_is_new():
    p=read(RUN/'protocol/PROTOCOL.json')
    assert p['target_MPa']==1640 and p['target_hit_tolerance']==.02
    assert sha(RUN/'protocol/FEASIBILITY_FROZEN.json')==sha(PREV/'protocol/FEASIBILITY_FROZEN.json')
    assert p['same_conversation_required'] and p['independent_conversations_per_arm']==4
    assert sum(t.startswith('IF') for t in p['trial_order'])==4
    assert sum(t.startswith('NF') for t in p['trial_order'])==4

def test_common_calibration_is_exact_deterministic_feasible_and_diverse():
    r=read(RUN/'starting_generator/COMMON_STARTING_POINT_FROZEN.json')
    assert r['fully_qualified_calibration'] and r['diversity']['passed']
    assert all(v['phase_counts']['5']==20731 and v['deterministic'] and v['feasibility']['passed'] for v in r['rows'])
    assert r['common_generator_sha256']==sha(RUN/'starting_generator/generator.py')
    assert audit((RUN/'starting_generator/generator.py').read_text())['passed']

def test_candidate_exhaustion_is_bounded_and_explicit():
    m=module(RUN/'starting_generator/generator.py');calls=[]
    def invalid(seed,parameters):calls.append(seed);return np.ones((256,256),dtype=np.uint8)
    m._generate_candidate=invalid
    with pytest.raises(RuntimeError,match='eight'):m.generate_microstructure(4333,{})
    assert len(calls)==8
    assert len(set(calls))==8

def test_replay_and_source_identity():
    m=module(RUN/'starting_generator/generator.py')
    a=m.generate_microstructure(4300,{})
    assert np.array_equal(a,np.load(RUN/'starting_generator/calibration/seed_4300.npy'))
    assert not np.array_equal(a,m.generate_microstructure(4301,{}))

def test_partitions_disjoint_and_no_observed_or_registered_collision():
    seeds=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')
    groups=[set(seeds[k]) for k in ['common_calibration','verification','development','heldout']]
    assert sum(map(len,groups))==len(set.union(*groups))
    assert not set.union(*groups)&set(read(RUN/'audit/HISTORICAL_AUTHENTICATION.json')['registered_and_observed_historical_seed_ids'])
