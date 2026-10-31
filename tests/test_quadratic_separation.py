"""Crossings/touch/uncertainty must never be certified as positive gap."""
import numpy as np
import pytest
from metamaterial_eval.simulation.quadratic_separation import certify_separated


def test_resolves_small_positive_gap_without_assigning_contact_force():
    a=np.array([[0.,0.],[1,0],[.5,0]])
    r=certify_separated(a,a+[0,1e-8]);assert r['passed'] and 0<r['minimum_certified_separation_mm']<1e-8


def test_curvature_uncertainty_can_be_refined_to_prove_separation():
    a=np.array([[-1.,0.],[1,0],[0,1]])
    b=np.array([[0.,.2],[0,.8],[0,.5]])
    r=certify_separated(a,b);assert r['passed'] and r['processed_cells']>1


@pytest.mark.parametrize('kind',['straight_cross','curved_cross','touch','below_guard'])
def test_never_accepts_intersection_or_unresolved_touch(kind):
    a=np.array([[-1.,0.],[1,0],[0,0]])
    b=np.array([[0.,-1],[0,1],[0,0]])
    if kind=='curved_cross':a=np.array([[-1.,1.],[1,1],[0,-1]])
    if kind in ['touch','below_guard']:b=a+[0,0 if kind=='touch' else 1e-14]
    assert not certify_separated(a,b)['passed']
