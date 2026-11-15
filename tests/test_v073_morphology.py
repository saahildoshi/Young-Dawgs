"""Independent digital fixtures establish descriptor meaning, not native evidence."""
import numpy as np
import pytest
from metamaterial_eval.composites.morphology_v073 import describe, region_shapes, limited_gap_run, weighted_quantile
from metamaterial_eval.composites.descriptors import directional_s2
from scipy import ndimage as ndi
from skimage.measure import regionprops

def ellipse(a,cy,cx,ry,rx):
    yy,xx=np.indices(a.shape);a[((yy-cy)/ry)**2+((xx-cx)/rx)**2<=1]=True

def fixture(kind):
    a=np.zeros((256,256),bool)
    if kind=='circles':
        for y in (35,90,145,200):
            for x in (35,90,145,200):ellipse(a,y,x,8,8)
    elif kind in ('horizontal','vertical','balanced'):
        for i,y in enumerate((35,90,145,200)):
            for j,x in enumerate((35,90,145,200)):
                vertical=kind=='vertical' or kind=='balanced' and (i+j)%2==0
                ellipse(a,y,x,18 if vertical else 6,6 if vertical else 18)
    elif kind=='tail':
        for y in (30,70,110):
            for x in range(20,240,30):ellipse(a,y,x,3,3)
        ellipse(a,190,130,10,100)
    elif kind in ('lanes','horizontal_lanes','chain','boundary'):
        xs=(0,40,80,120,160,200,240) if kind=='boundary' else (40,80,120,160,200)
        for x in xs:
            for y in range(0,250,42):a[y:(y+40 if y<210 else 256),max(0,x-3):x+4]=True
        if kind=='horizontal_lanes':a=a.T.copy()
        if kind=='chain':a=a[:,35:46].copy()
    elif kind in ('irregular','clustered'):
        rng=np.random.default_rng(177)
        for y in (35,90,145,200):
            for x in (35,90,145,200):
                if kind=='clustered':x=int(128+(x-128)*.55);y=int(128+(y-128)*.55)
                ellipse(a,y,x,9,13);a[max(y-4,0):y+3,max(x-15,0):x]=False
    return a

@pytest.mark.parametrize('kind',['circles','horizontal','vertical','balanced','tail','irregular','lanes','horizontal_lanes','chain','boundary','clustered'])
def test_deterministic_nonmutating_fixtures(kind):
    a=fixture(kind);before=a.copy();d=describe(a)
    assert describe(a)==d and np.array_equal(a,before)

def test_circle_orientation_is_explicitly_undefined():
    d=describe(fixture('circles'))['all_observed']
    assert d['axial_order'] is None and d['orientation_weight_fraction']==0
    assert d['area_weighted_aspect']==pytest.approx(1)

def test_axial_image_conventions_and_balanced_cancellation():
    h=describe(fixture('horizontal'))['all_observed'];v=describe(fixture('vertical'))['all_observed']
    b=describe(fixture('balanced'))['all_observed']
    assert h['preferred_axial_angle_deg']==pytest.approx(0)
    assert v['preferred_axial_angle_deg']==pytest.approx(90)
    assert h['vertical_alignment']==pytest.approx(-1) and v['vertical_alignment']==pytest.approx(1)
    assert b['axial_order']<1e-12 and b['preferred_axial_angle_deg'] is None

def test_area_weighting_detects_large_shape_tail():
    d=describe(fixture('tail'))['all_observed']
    assert d['area_weighted_aspect']>2*d['unweighted_aspect_mean']
    assert d['area_fraction_aspect_gt4']>.5 and d['area_weighted_aspect_p95']>8
    assert weighted_quantile([1,4],[9,1],.9)==1

def test_finite_pair_normalization_no_wrap():
    a=np.zeros((4,6),bool);a[:,0]=True;a[:,-1]=True
    assert directional_s2(a,1,1)==0
    assert directional_s2(a,5,1)==1
    assert directional_s2(a,1,0)==pytest.approx(1/3)

def test_known_occupancy_and_multiscale():
    a=np.zeros((256,256),bool);a[:,:64]=True;d=describe(a)
    assert d['strips']['1']['column_std']==pytest.approx(np.sqrt(.25*.75))
    assert d['strips']['1']['row_std']==0
    assert len(d['strips'])==4

def test_gap_run_stops_at_three_pixel_gap_and_censors_ends():
    assert limited_gap_run(np.array([0,1,1,0,0,1,0]))==5
    assert limited_gap_run(np.array([1,1,0,0,0,1]))==2

def test_lanes_disconnected_but_gap_connected_without_geometry_change():
    a=fixture('lanes');before=a.copy();d=describe(a)
    assert ndi.label(a)[1]>5
    assert d['limited_gap_run_y']>.95
    assert d['gap_dilation']['2']['spans_y']
    assert np.array_equal(a,before)

def test_boundary_elongation_remains_visible_in_all_field():
    d=describe(fixture('boundary'))
    assert d['boundary_censored_regions']>0
    assert d['all_observed']['area_weighted_aspect']>3
    assert d['limited_gap_run_y']>.95

def test_rotation_and_reflection_covariance():
    a=fixture('irregular');d=describe(a);r=describe(np.rot90(a));f=describe(np.fliplr(a))
    assert d['all_observed']['area_weighted_aspect']==pytest.approx(r['all_observed']['area_weighted_aspect'])
    assert d['all_observed']['axial_order']==pytest.approx(f['all_observed']['axial_order'])
    assert d['limited_gap_run_y']==r['limited_gap_run_x']
    for lag in ('8','16','32','64'):
        assert d['correlation'][lag]['x']==pytest.approx(r['correlation'][lag]['y'])

def test_undefined_empty_and_degenerate_shapes():
    a=np.zeros((256,256),bool);a[10,10]=True
    d=describe(a)['all_observed'];assert d['area_weighted_aspect'] is None
    assert d['defined_aspect_area_fraction']==0
    assert describe(np.zeros_like(a))['all_observed']['area_fraction_aspect_gt3'] is None
