"""Known geometry checks for the new three-phase transverse observer."""
import numpy as np
import pytest
from metamaterial_eval.composites.transverse import describe_transverse, validate_transverse


def test_known_sections_have_area_equivalent_diameter_and_spacing():
    a = np.zeros((256, 256), np.uint8)
    yy, xx = np.indices(a.shape)
    disk = (xx-40)**2+(yy-40)**2 <= 25
    a[disk | ((xx-70)**2+(yy-40)**2 <= 25)] = 1
    a[100:104, 100:104] = 2
    d = describe_transverse(a)
    r = d['phases']['fiber']['regions']
    assert r['annotation_region_count'] == r['complete_region_count'] == 2
    assert r['complete_region_equivalent_diameter_px']['mean'] == pytest.approx(2*np.sqrt(disk.sum()/np.pi))
    assert r['complete_region_centroid_nearest_neighbor_px']['values'] == pytest.approx([30, 30])
    assert d['phases']['void']['pixel_count'] == 16
    assert sum(p['fraction'] for p in d['phases'].values()) == pytest.approx(1)
    assert d['physical_fiber_instance_count'] is None
    assert d['physical_um_per_pixel'] is None
    assert not any(k in d for k in ['axial_mean_deg', 'component_span_mean_px', 'tortuosity_mean'])


def test_border_components_are_excluded_from_diameter_statistics():
    a = np.zeros((256, 256), np.uint8)
    a[0:8, 0:8] = 1
    a[30:34, 30:34] = 1
    a[-3:, 100:103] = 2
    d = describe_transverse(a)
    r = d['phases']['fiber']['regions']
    assert r['annotation_region_count'] == 2 and r['boundary_censored_region_count'] == 1
    assert r['complete_region_area_px2']['values'] == [16]
    assert d['phases']['void']['regions']['complete_region_count'] == 0
    assert d['phases']['void']['regions']['complete_region_equivalent_diameter_px']['mean'] is None


def test_merged_sections_are_regions_not_physical_fiber_instances():
    a = np.zeros((256, 256), np.uint8)
    a[20:30, 20:30] = 1
    a[25:35, 25:35] = 1
    d = describe_transverse(a)
    assert d['phases']['fiber']['regions']['annotation_region_count'] == 1
    assert d['physical_fiber_instance_count'] is None
    assert 'touching or merged' in d['phases']['fiber']['regions']['instance_interpretation']


def test_phase_interfaces_and_directional_correlations_use_all_three_phases():
    a = np.zeros((256, 256), np.uint8)
    a[:, 80:160] = 1
    a[:, 160:] = 2
    d = describe_transverse(a)
    assert d['phase_pair_interfaces']['matrix__fiber']['internal_pixel_edge_count'] == 256
    assert d['phase_pair_interfaces']['fiber__void']['internal_pixel_edge_count'] == 256
    assert d['phase_pair_interfaces']['matrix__void']['internal_pixel_edge_count'] == 0
    for phase in d['phases'].values():
        assert phase['S2_x'][0] == phase['S2_y'][0] == phase['S2_radial'][0] == phase['fraction']
        assert phase['S2_y'][16] == phase['fraction']
        assert phase['percolates_y'] and not phase['percolates_x']
    assert d['phases']['fiber']['S2_x'][16] == pytest.approx(64/240)
    transposed = describe_transverse(a.T.copy())
    assert transposed['phases']['fiber']['S2_y'] == d['phases']['fiber']['S2_x']


@pytest.mark.parametrize('a', [np.zeros((256,256)), np.zeros((128,128), np.uint8), np.full((256,256), 3, np.uint8)])
def test_contract_rejects_wrong_dtype_shape_or_unknown_phase(a):
    with pytest.raises(ValueError):
        validate_transverse(a)


def test_absent_phase_stays_absent_not_unknown_or_merged():
    d = describe_transverse(np.zeros((256,256), np.uint8))
    assert d['phases']['void']['fraction'] == 0
    assert d['phases']['fiber']['regions']['complete_region_centroid_nearest_neighbor_px']['mean'] is None
    assert d['phases']['matrix']['percolates_x']
