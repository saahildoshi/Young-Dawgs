"""Synthetic scalar unit cases only; none represent licensed mechanical evidence."""
import pytest
from scripts.v073_target import choose
from scripts.v073_analysis import target_metrics,statistics

def row(trial,seed,E):
    return {'trial_id':trial,'seed':seed,'apparent_modulus_MPa':E,'status':'ACCEPTED_NATIVE_RESULT'}

def data(variant):
    return ([row('BASE',s,E) for s,E in zip([1,2,3],[1690,1700,1710])]+[row('V1',s,variant) for s in [1,2,3]],
        [row('BASE',1,1688),row('V1',1,variant-2)])

def test_rule_selects_supported_interior_target():
    a,b=data(1900);r=choose(a,b)
    assert r['qualified_target'] and r['target_MPa']==1820
    assert r['target_hit_relative_tolerance']==.02

def test_no_target_when_baseline_variability_overwhelms_difference():
    a,b=data(1720);r=choose(a,b)
    assert not r['qualified_target'] and r['target_MPa'] is None

def test_mesh_effect_reversal_excludes_variant():
    a,b=data(1900);b[1]['apparent_modulus_MPa']=1600;r=choose(a,b)
    assert not r['qualified_target']

def test_infeasible_variant_not_used_for_attainability():
    a,b=data(1900);a[-1].update(status='NOT_SOLVED_STRUCTURALLY_INFEASIBLE',apparent_modulus_MPa=None)
    assert not choose(a,b)['qualified_target']

def test_error_rewards_matching_and_reports_signed_excess():
    assert target_metrics(2000,2000,.02)['absolute_target_error']==0
    assert target_metrics(2400,2000,.02)['signed_target_error']==.2
    assert target_metrics(1600,2000,.02)['signed_target_error']==-.2
    assert target_metrics(None,2000,.02)['target_hit'] is None

def test_hit_inclusive_boundary_and_sample_variability():
    assert target_metrics(2040,2000,.02)['target_hit']
    assert not target_metrics(2040.01,2000,.02)['target_hit']
    assert statistics([1,3])['sample_SD']==pytest.approx(2**.5)
    assert statistics([])['mean'] is None
