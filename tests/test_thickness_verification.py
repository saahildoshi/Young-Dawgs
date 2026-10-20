"""Validation-only v0.4.2: prospective gates and physical-grid diagnostics."""
import numpy as np
import pytest

from metamaterial_eval.pipeline import thickness_verification as study
from metamaterial_eval.pipeline.stabilization import evaluator


@pytest.mark.parametrize("family", study.FAMILIES)
def test_analytic_geometry_binary_and_nonempty(family):
    a = study.analytic_mask(256, family, 4, .37)
    assert a.shape == (256, 256) and a.dtype == np.uint8
    assert 0 < a.mean() < 1
    np.testing.assert_array_equal(a, study.analytic_mask(256, family, 4, .37))


@pytest.mark.parametrize("n", study.LEVELS)
def test_independent_bar_width_scales_exactly(n):
    a = study.analytic_mask(n, "bar_0", 4, 0)
    assert np.count_nonzero(a[:, n // 2]) == 4 * n // 256
    assert np.count_nonzero(a[n // 2]) == n // 2


def control_rows(step):
    return [{"family": family, "width": width, "phase": phase, "resolution": n,
             "normalized": {"p10_strut_thickness": .01 * (1 + step if n == 2048 else 1)}}
            for family in study.FAMILIES for width in study.WIDTHS for phase in study.PHASES for n in study.LEVELS]


def test_p10_limit_comes_from_controls_not_native_results():
    c = study.calibrate_p10(control_rows(.06))
    assert c["control_count"] == 48
    assert c["effective_limit"] == pytest.approx(.06)
    assert c["calibration_qualified"]
    with pytest.raises(ValueError, match="Incomplete"):
        study.calibrate_p10(control_rows(.06)[:-1])


def test_control_outlier_does_not_relax_old_ceiling():
    c = study.calibrate_p10(control_rows(.15))
    assert c["effective_limit"] == .10
    assert not c["calibration_qualified"]


def test_single_pixel_connector_is_fragile_and_inputs_unchanged():
    raw = np.zeros((256, 256), dtype=np.uint8)
    raw[:5, :5] = 1; raw[:5, 6:12] = 1
    repaired = raw.copy(); repaired[0, 5] = 1
    before = repaired.copy()
    audit = {"bridge_width_normalized": 2 / 255,
             "bridges": [{"start_yx": [0, 4], "end_yx": [0, 6]}]}
    r = study.repair_fragility(raw, repaired, audit)
    assert [0, 5] in r["single_pixel_articulations_yx"]
    assert not r["local_neck_screen_pass"]
    np.testing.assert_array_equal(repaired, before)


def test_wider_boundary_connection_has_no_single_pixel_cut():
    raw = np.zeros((256, 256), dtype=np.uint8)
    raw[:5, :5] = 1; raw[:5, 6:12] = 1
    repaired = raw.copy(); repaired[:3, 5] = 1
    audit = {"bridge_width_normalized": 2 / 255,
             "bridges": [{"start_yx": [0, 4], "end_yx": [0, 6]}]}
    r = study.repair_fragility(raw, repaired, audit)
    assert not r["single_pixel_articulations_yx"] and r["local_neck_screen_pass"]
    assert r["cross_sections"][0]["min_depth_normalized"] == 3 / 255


def test_unknown_cross_section_is_not_assumed_safe():
    raw = np.zeros((256, 256), dtype=np.uint8)
    raw[20:30, 20:25] = 1; raw[20:30, 26:31] = 1
    repaired = raw.copy(); repaired[20:30, 25] = 1
    audit = {"bridge_width_normalized": 2 / 255,
             "bridges": [{"start_yx": [20, 24], "end_yx": [20, 26]}]}
    r = study.repair_fragility(raw, repaired, audit)
    assert not r["local_neck_screen_pass"]


def test_high_pair_preserves_denominator_and_gates():
    def record(n, value):
        return {"design_id": 0, "seed": 1, "status": "COMPLETE", "resolution": n,
                "evaluation": {"normalized": {"normalized_" + k: value for k in study.DIMENSIONS},
                               "raw": {"phi_s": .5}, "common_curves": {"s2": [.5, .25], "lineal_path": [.5, .1]}}}
    low, high = record(1024, .01), record(2048, .0102)
    result = study.high_pair(low, high, evaluator(), .015)
    assert result["errors"]["mean_strut_thickness"] == pytest.approx(.02)
    assert result["checks"]["mean_strut_thickness"] and not result["checks"]["p10_strut_thickness"]
    assert not result["pass"]
    high["status"] = "FAILED"
    assert not study.high_pair(low, high, evaluator(), .10)["pass"]


def test_run_requires_prepared_evidence_and_cli_rejects_bad_timeout(tmp_path):
    with pytest.raises(FileNotFoundError):
        study.run(tmp_path)
    with pytest.raises(SystemExit):
        study.main(["run", str(tmp_path), "--timeout", "nan"])


@pytest.mark.parametrize("n", [1024, 2048])
def test_posthoc_endpoint_audit_preserves_frozen_whole_mask_p10(n):
    from metamaterial_eval.pipeline.thickness_control_audit import bar_end_audit
    row, samples, ends = bar_end_audit(n)
    frozen = evaluator().local_dimensions(study.analytic_mask(n, "bar_30", 6, .37))
    assert row["whole_p10"] == frozen["p10_strut_thickness"] / n
    assert row["fraction_of_thin_samples_near_ends"] == 1
    assert len(samples) == row["skeleton_samples"] == len(ends)
