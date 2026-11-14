"""Regression checks for prospective optimization constraints and experiment isolation."""
import copy
import numpy as np
from scripts.v072_experiment import RUN,read,topology,feasibility,arrangement_signature


def fixture():
    return read(RUN/'baseline_development/seed_1000.json'),read(RUN/'protocol/FEASIBILITY_FROZEN.json')


def test_frozen_baseline_accepted():
    row,p=fixture();assert feasibility(row,p)['passed']


def test_composition_limit_is_inclusive_and_next_pixel_rejected():
    row,p=fixture();row['phase_counts']['5']=p['target_count']+64
    assert feasibility(row,p)['checks']['phase_count']
    row['phase_counts']['5']+=1
    assert not feasibility(row,p)['checks']['phase_count']


def test_vertical_reinforcement_band_fails_even_at_valid_fraction():
    row,p=fixture();row['topology']['reinforcement_1']['spans_y']=True
    assert 'no_reinforcement_4_spanning' in feasibility(row,p)['failures']


def test_diagonal_point_connections_are_detected():
    a=np.eye(8,dtype=bool)
    assert not topology(a,1)['spans_y'] and topology(a,2)['spans_y']


def test_disconnected_matrix_is_not_accepted():
    row,p=fixture();row['topology']['matrix_1']['spans_y']=False
    assert not feasibility(row,p)['passed']


def test_failed_generation_has_no_valid_objective():
    _,p=fixture();assert not feasibility({'status':'EXECUTION_ERROR'},p)['passed']


def test_noise_and_dominant_components_are_constraints():
    row,p=fixture();row['topology']['reinforcement_1']['one_pixel_area_fraction']=.1
    row['topology']['reinforcement_2']['largest_fraction']=.5
    assert {'single_pixel_noise','no_dominant_8_region'}<=set(feasibility(row,p)['failures'])


def test_rigid_translation_signature_is_invariant():
    a=np.ones((256,256),np.uint8);a[10:16,20:25]=5;a[40:45,60:65]=5
    b=np.ones_like(a);b[20:26,30:35]=5;b[50:55,70:75]=5
    assert arrangement_signature(a)==arrangement_signature(b)


def test_partitions_do_not_overlap_or_enter_old_seed_set():
    p=read(RUN/'protocol/PROTOCOL.json');s=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')
    assert not set(s['development'])&set(s['heldout'])
    assert not set(s['development']+s['heldout'])&set(p['history_seed_collision_check']['historical_P3_seed_ids'])
    assert s['H2']==s['heldout'][:3]
