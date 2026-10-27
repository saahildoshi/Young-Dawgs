"""Independent analytic triangle/map controls; these are not FEM solver runs."""
import json
from pathlib import Path
import numpy as np
import pytest
from metamaterial_eval.simulation.element_quality import corner_metrics,quadratic_mapping,quality_summary


def tri6(corners):
    p=np.asarray(corners,float)
    return np.vstack([p,(p+np.roll(p,-1,axis=0))/2])


def test_valid_first_order_and_quadratic_triangle():
    p=tri6([[0,0],[1,0],[0,1]])
    c=corner_metrics(p[:3]);q=quadratic_mapping(p)
    np.testing.assert_allclose(c['angles_deg'],[[90,45,45]])
    assert c['signed_area'][0]==.5
    assert q['positive_over_reference_triangle'][0]
    assert q['determinant_min'][0]==q['determinant_max'][0]==1
    assert q['max_midpoint_error'][0]==0


@pytest.mark.parametrize('angle,accepted',[(8,False),(8.27513422,False),(10,True),(12,True)])
def test_frozen_angle_threshold(angle,accepted):
    r=np.deg2rad(angle);p=[[0,0],[1,0],[np.cos(r),np.sin(r)]]
    c=corner_metrics(p)
    assert c['minimum_angle_deg'][0]==pytest.approx(angle)
    assert (quality_summary(c)['below_angle_gate']==0)==accepted


@pytest.mark.parametrize('p',[[[0,0],[0,1],[1,0]], [[0,0],[1,0],[2,0]]])
def test_inverted_and_zero_area_rejected(p):
    c=corner_metrics(p);q=quadratic_mapping(tri6(p))
    assert not c['positive_orientation'][0]
    assert not q['positive_over_reference_triangle'][0]


def test_acceptable_corners_invalid_midside_map():
    p=tri6([[0,0],[1,0],[0,1]]);p[3]=[0,1]
    assert corner_metrics(p[:3])['minimum_angle_deg'][0]==45
    q=quadratic_mapping(p)
    assert q['max_midpoint_error'][0]>0
    assert q['determinant_min'][0]<0
    assert not q['positive_over_reference_triangle'][0]


def test_swapped_midside_node_order_invalid():
    p=tri6([[0,0],[1,0],[0,1]]);p[[3,4]]=p[[4,3]]
    assert not quadratic_mapping(p)['positive_over_reference_triangle'][0]


def test_small_valid_curvature_is_reported_separately():
    p=tri6([[0,0],[1,0],[0,1]]);p[3]+=[0,.02]
    q=quadratic_mapping(p)
    assert q['positive_over_reference_triangle'][0]
    assert q['max_midpoint_error'][0]==pytest.approx(.02)
    assert q['determinant_min'][0]>0


def test_translation_and_scale_of_mapping():
    p=tri6([[0,0],[1,0],[0,1]])
    q=quadratic_mapping(p*2+[12,14])
    assert q['determinant_min'][0]==pytest.approx(4)
    assert q['positive_over_reference_triangle'][0]


def test_whole_domain_extrema_against_independent_dense_control():
    # Dense evaluation is a test oracle, not the production positivity method.
    p=tri6([[0,0],[1,0],[0,1]]);p[3]+=[.12,.08];p[4]+=[-.08,.05];p[5]+=[.07,-.02]
    q=quadratic_mapping(p)
    points=np.array([(r,s) for r in np.linspace(0,1,101) for s in np.linspace(0,1-r,101)])
    r,s=points.T
    dr=np.stack([4*r+4*s-3,4*r-1,np.zeros_like(r),4-8*r-4*s,4*s,-4*s],axis=1)
    ds=np.stack([4*r+4*s-3,np.zeros_like(r),4*s-1,-4*r,4*r,4-4*r-8*s],axis=1)
    a=dr@p;b=ds@p;d=a[:,0]*b[:,1]-a[:,1]*b[:,0]
    assert q['determinant_min'][0]<=d.min()+1e-12
    assert q['determinant_min'][0]==pytest.approx(d.min(),abs=1e-4)


def test_actual_historical_worst_element_fixture():
    p=Path(__file__).parent/'fixtures/simulation/worst_fine_TRI6.json'
    data=json.loads(p.read_text());coords=np.asarray(data['coordinates_mm'])
    c=corner_metrics(coords[:3]);q=quadratic_mapping(coords)
    assert c['minimum_angle_deg'][0]==pytest.approx(8.275134219999781)
    assert quality_summary(c,q)['below_angle_gate']==1
    assert q['positive_over_reference_triangle'][0]
