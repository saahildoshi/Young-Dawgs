import numpy as np
from metamaterial_eval.simulation.deformed_boundaries import trace_loops,quadratic_segments,screen,signed_quadratic_edge_areas


def square():
    nodes=np.array([[0.,0],[1,0],[1,1],[0,1],[.5,0],[1,.5],[.5,1],[0,.5]])
    edges=np.array([[0,1,4],[1,2,5],[2,3,6],[3,0,7]])
    return nodes,edges


def test_connected_original_endpoints_are_not_false_overlap():
    nodes,edges=square();r=screen(nodes,edges,np.full(4,'external'),original=nodes)
    assert r['passed'] and r['suspicious_pair_count']==0 and len(trace_loops(edges))==1
    assert np.isclose(signed_quadratic_edge_areas(nodes,edges).sum(),1)


def test_nonadjacent_crossing_is_quarantined():
    nodes,edges=square();deformed=nodes.copy();deformed[[1,2]]=deformed[[2,1]]
    deformed[4:]=((deformed[edges[:,0]]+deformed[edges[:,1]])/2)
    r=screen(deformed,edges,np.full(4,'external'),original=nodes)
    assert not r['passed'] and any(p['sampled_intersection'] for p in r['examples'])


def test_quadratic_chord_error_is_bounded_not_hidden():
    nodes,edges=square();nodes[4,1]=.1
    xy,owners,error=quadratic_segments(nodes,edges,tolerance=1e-4)
    assert len(xy)>4 and np.max(error)<=1e-4*(1+1e-12)
    _,_,coarse=quadratic_segments(nodes,edges,tolerance=1e-9,max_subdivisions=2)
    assert np.max(coarse)>1e-9


def test_near_disjoint_boundaries_are_uncertain_not_certified():
    a,e=square();b=a+np.array([1.000001,0]);nodes=np.concatenate([a,b]);edges=np.concatenate([e,e+8])
    r=screen(nodes,edges,np.full(8,'external'),original=nodes,tolerance=1e-6)
    assert not r['passed'] and r['examples']
