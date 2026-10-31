"""Contact localization must not excuse unrelated or deep crossings."""
from types import SimpleNamespace
import numpy as np
import pytest
from metamaterial_eval.simulation.nodal_contact_geometry import certify_localized,explain_nodal_pairs


def test_crossing_requires_ball_at_the_actual_intersection():
    a=np.array([[-1.,0],[1,0],[0,0]]);b=np.array([[0.,-1],[0,1],[0,0]])
    assert certify_localized(a,b,[[0,0]])['passed']
    assert not certify_localized(a,b,[[.1,0]])['passed']
    assert not certify_localized(a,b,[])['passed']


def test_every_root_must_be_covered_and_finite_budget_cannot_pass():
    a=np.array([[-1.,1],[1,1],[0,-1]]);b=np.array([[-1.,0],[1,0],[0,0]])
    c=2**-.5
    assert certify_localized(a,b,[[-c,0],[c,0]])['passed']
    assert not certify_localized(a,b,[[-c,0]])['passed']
    assert not certify_localized(a,b,[[-c,0],[c,0]],max_depth=1)['passed']


@pytest.mark.parametrize('variant',['native_shared_node','native_neighbor_target','zero_endpoint_pressure','unrelated_target','deep_crossing'])
def test_only_native_positive_pressure_constraints_can_propagate_at_shared_nodes(variant):
    eps=1e-8
    xy=np.array([[0.,0],[1,0],[.5,0],[1,-eps],[1,1],[1,(1-eps)/2],[2,0],[1.5,0],[2,-eps],[1.5,-eps]])
    edges=np.array([[0,1,2],[3,4,5],[1,6,7],[3,8,9]])
    if variant=='deep_crossing':xy[[3,4,5],0]=.99
    mesh=SimpleNamespace(boundary=edges);eids=np.array([11,12,13,14])
    row=np.array([13.,2,1,0,.5,1e-8,0,1,12,0,2,7,8,0])
    if variant=='native_neighbor_target':row[8]=14
    if variant=='zero_endpoint_pressure':row[2]=0
    if variant=='unrelated_target':row[8]=13
    q={'suspicious_pair_count':1,'examples':[{'edge_a':0,'edge_b':1}]}
    if variant in ['native_shared_node','native_neighbor_target']:
        result=explain_nodal_pairs(q,eids,{2:row},mesh,xy)
        assert result[0]['geometry_proof']['passed']
        assert result[0]['native_constraint_links'][0]['node']==2
    else:
        with pytest.raises(ValueError):explain_nodal_pairs(q,eids,{2:row},mesh,xy)
