"""Synthetic geometry certificate checks; these are not licensed mechanical evidence."""
import numpy as np
import pytest
from shapely.geometry import Polygon,MultiLineString,LineString
from scripts.v0610_geometry import sampled_curve,directional_bound,CHORD,SPACING,LIMIT


def test_exact_quadratic_sampling_has_registered_chord_and_arclength_bounds():
    v=np.array([[0,0],[.003,0],[.0015,.0002]])
    p,gap,error=sampled_curve(v,SPACING)
    assert gap<=SPACING and error<=CHORD
    assert np.array_equal(p[0],v[0]) and np.array_equal(p[-1],v[1])
    assert sampled_curve(v)[2]<=CHORD


def test_continuous_margin_bounds_shallow_flat_penetration():
    box=Polygon([(0,0),(1,0),(1,1),(0,1)]);boundary=MultiLineString([box.exterior.coords])
    xy=np.array([[.499,2e-6],[.501,2e-6],[.5,2e-6]])
    q=directional_bound(xy,np.array([[0,1,2]]),(box.buffer(CHORD),boundary,None))
    assert q['sampled_max_inside_depth_mm']==pytest.approx(2e-6)
    assert 2e-6<q['continuous_depth_upper_bound_mm']<LIMIT


def test_deep_crossing_cannot_pass_from_small_native_endpoint_values():
    box=Polygon([(0,0),(1,0),(1,1),(0,1)]);boundary=MultiLineString([box.exterior.coords])
    xy=np.array([[.499,.001],[.501,.001],[.5,.001]])
    assert directional_bound(xy,np.array([[0,1,2]]),(box,boundary,None))['continuous_depth_upper_bound_mm']>LIMIT


def test_near_artificial_cut_is_uncertified_instead_of_assumed_separated():
    box=Polygon([(0,0),(1,0),(1,1),(0,1)]);boundary=MultiLineString([box.exterior.coords]);xy=np.array([[.499,2e-6],[.501,2e-6],[.5,2e-6]])
    with pytest.raises(ValueError,match='artificial'):
        directional_bound(xy,np.array([[0,1,2]]),(box,boundary,LineString([(.4,2.1e-6),(.6,2.1e-6)])))
