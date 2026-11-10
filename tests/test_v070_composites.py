"""Independent digital/analytical controls; these are not LLM trials."""
import numpy as np
import pytest
from scipy import ndimage as ndi
from metamaterial_eval.composites.descriptors import *


def particles():
    y,x=np.mgrid[:256,:256];return (((x-70)**2+(y-100)**2<=100)|((x-110)**2+(y-100)**2<=100)).astype(np.uint8)


def test_two_circles_count_area_spacing_and_matrix_semantics():
    a=particles();d=describe(a,'particle');area=int(a.sum())/2
    assert d['object_count']==2 and d['fraction']==a.mean() and d['matrix_lcc']==1
    assert d['nearest_neighbor_mean_px']==40 and d['nearest_neighbor_cv']==0
    assert d['diameter_mean_px']==pytest.approx(2*np.sqrt(area/np.pi))
    assert validity(a,'particle',d)['passed'] and not d['reinforcement_percolates_x']


def test_circle_diameter_converges_to_analytical_diameter():
    y,x=np.mgrid[:256,:256]
    for r in [5,10,20]:
        d=describe(((x-128)**2+(y-128)**2<=r*r).astype(np.uint8),'particle')
        assert abs(d['diameter_mean_px']-2*r)<.3


def test_ellipse_aspect_is_not_particle_diameter():
    y,x=np.mgrid[:256,:256];a=(((x-100)/40)**2+((y-100)/20)**2<=1).astype(np.uint8)
    assert describe(a,'particle')['aspect_mean']==pytest.approx(2,abs=.025)


@pytest.mark.parametrize('vertical',[False,True])
def test_known_rectangular_fiber_axis_length_and_area_width(vertical):
    a=np.zeros((256,256),np.uint8);a[80:85,50:100]=1
    if vertical:a=a.T.copy()
    d=describe(a,'fiber')
    assert axial_error(d['axial_mean_deg'],90 if vertical else 0)<1e-10
    assert d['alignment']==pytest.approx(1)
    assert d['component_span_mean_px']==pytest.approx(50)
    assert d['component_width_mean_px']==pytest.approx(5)


def test_crossed_union_does_not_become_one_physical_fiber():
    a=np.zeros((256,256),np.uint8);a[120:125,70:180]=1;a[70:180,120:125]=1
    d=describe(a,'fiber');assert d['branched_component_fraction']==1 and d['component_span_mean_px'] is None


def test_parallel_fibers_and_rotation_equivalence():
    a=np.zeros((256,256),np.uint8);a[60:65,50:120]=1;a[100:105,70:140]=1
    d=describe(a,'fiber');assert d['alignment']==pytest.approx(1) and d['object_count']==2
    assert axial_error(179,1)==2 and axial_error(0,180)==0


def test_balanced_orthogonal_axes_have_no_defined_mean():
    a=np.zeros((256,256),np.uint8);a[40:45,30:80]=1;a[100:150,120:125]=1
    d=describe(a,'fiber');assert d['alignment']<1e-10 and d['axial_mean_deg'] is None


def test_finite_directional_correlation_agrees_with_direct_count_and_is_anisotropic():
    a=np.zeros((256,256),np.uint8);a[40:45,30:100]=1
    assert directional_s2(a,8,1)==np.count_nonzero(a[:,:-8]&a[:,8:])/(256*248)
    assert directional_s2(a,8,1)>directional_s2(a,8,0)
    assert directional_s2(a,0,1)==a.mean()


def test_finite_boundaries_do_not_wrap_particles_or_correlations():
    a=np.zeros((256,256),np.uint8);a[20:30,0:3]=1;a[20:30,253:]=1
    d=describe(a,'particle');assert d['object_count']==2 and d['boundary_censored_objects']==2
    assert d['diameter_mean_px'] is None and directional_s2(a,8,1)==0


def test_digital_interface_has_known_pixel_edge_units():
    a=np.zeros((256,256),np.uint8);a[40:50,40:60]=1
    assert describe(a,'particle')['interface_density']==60/65536


def test_cluster_nearest_neighbor_changes_with_spread():
    a=np.zeros((256,256),np.uint8);a[50:53,50:53]=1;a[50:53,60:63]=1
    b=np.zeros_like(a);b[50:53,50:53]=1;b[50:53,150:153]=1
    assert describe(a,'particle')['nearest_neighbor_mean_px']==10
    assert describe(b,'particle')['nearest_neighbor_mean_px']==100


@pytest.mark.parametrize('bad',[np.zeros((255,256),np.uint8),np.zeros((256,256),float),np.full((256,256),2,np.uint8)])
def test_strict_shape_dtype_and_phase_contract(bad):assert not validity(bad,'particle')['passed']


def test_empty_material_and_disconnected_matrix_fail_separately():
    a=np.zeros((256,256),np.uint8);assert not validity(a,'fiber')['passed']
    a[:,125:130]=1;a[20:25,20:25]=1
    assert not validity(a,'particle')['passed']


def test_missing_measure_is_not_zero_and_normalization_avoids_tiny_target_division():
    e=normalized_errors({'fraction':.01,'alignment':None},{'fraction':0,'alignment':1},['fraction','alignment'],{'fraction':.2,'alignment':1})
    assert e['mean'] is None and e['coverage']==.5 and e['per_metric']['fraction']==pytest.approx(.05)
