"""Exact CDF integration and scoped geometry contracts; not holdout tuning."""
import numpy as np
import pytest

from metamaterial_eval.pipeline import p10_qualification as study


def test_point_masses_have_exact_cdf_area():
    r = study.cdf_distance([.002], [.005], upper=.01)
    assert r["area_normalized_length"] == pytest.approx(.003)
    assert r["max_cdf_gap_diagnostic"] == 1


def test_identity_symmetry_and_unequal_sample_counts():
    a, b = [.001, .006, .006], [.003, .004]
    assert study.cdf_distance(a, a)["area_normalized_length"] == 0
    assert study.cdf_distance(a, b)["area_normalized_length"] == study.cdf_distance(b, a)["area_normalized_length"]
    assert study.cdf_distance([.005], [.005, .005])["area_normalized_length"] == 0


def test_interval_clipping_does_not_renormalize_the_tail():
    r = study.cdf_distance([.002, .020], [.004, .020], upper=.01)
    assert r["area_normalized_length"] == pytest.approx(.001)
    assert r["tail_mass_first"] == r["tail_mass_second"] == .5
    assert study.cdf_distance([.02], [.03], upper=.01)["area_normalized_length"] == 0


def test_exact_threshold_inclusive_and_no_plot_grid_dependency():
    assert study.cdf_distance([0.], [study.AREA_LIMIT])["pass"]
    assert not study.cdf_distance([0.], [study.AREA_LIMIT * 1.01])["pass"]
    # Includes a zero-width repeated knot and both interval endpoints.
    assert study.cdf_distance([0., 0., study.UPPER], [0., study.UPPER])["area_normalized_length"] == pytest.approx(study.UPPER / 6)


@pytest.mark.parametrize("samples", [[], [-.1], [np.nan], [np.inf], [[.1]]])
def test_invalid_samples_fail_closed(samples):
    with pytest.raises(ValueError):
        study.cdf_distance(samples, [.1])


@pytest.mark.parametrize("upper", [0, -1, np.nan, np.inf])
def test_invalid_interval_rejected(upper):
    with pytest.raises(ValueError):
        study.cdf_distance([0.], [0.], upper)


def test_axis_aligned_neck_minimum_and_discontinuous_section_rejected():
    a = np.zeros((1024, 1024), dtype=np.uint8)
    a[500:503, :] = 1
    assert study.neck_measurement(a)["pass"]
    a[502] = 0
    assert not study.neck_measurement(a)["pass"]
    a[505] = 1
    with pytest.raises(ValueError, match="non-contiguous"):
        study.neck_measurement(a)


def test_holdout_manifest_not_reusing_previous_parameters():
    cases = study.independent_cases()
    assert len(cases) == len({c["id"] for c in cases}) == 10
    assert all(c["width"] not in (2, 3, 4, 6) and c["phase"] not in (0, .37) for c in cases)


def test_missing_registration_and_unknown_family_fail(tmp_path):
    with pytest.raises(FileNotFoundError):
        study.evaluate(tmp_path)
    with pytest.raises(ValueError):
        study.shape(64, dict(family="unknown", angle=0, width=5, phase=0))
