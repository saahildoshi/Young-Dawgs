"""v0.4.1 topology policy, diagnostics, and frozen-history contracts."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from scipy import ndimage as ndi

from metamaterial_eval.generators import native_resolution as old
from metamaterial_eval.generators import stabilized_resolution as new
from metamaterial_eval.pipeline import stabilization as workflow
from metamaterial_eval.pipeline.resolution_worker import perform_job
from metamaterial_eval.pipeline.state import write_json

NORMAL = dict(solid_fraction_target=.47949869779450194, strut_scale=3.8117182167728196,
              pore_scale=8.405665555093796)
CORNER = dict(solid_fraction_target=.47692251183925727, strut_scale=4.340345305340277,
              pore_scale=6.148748802851207)


@pytest.mark.parametrize("n", [256, 512, 1024])
def test_connected_outputs_unchanged(n):
    a = old.generate_microstructure(0, **NORMAL, resolution=n)
    b, record = new.generate_with_metadata(0, **NORMAL, resolution=n)
    np.testing.assert_array_equal(a, b)
    assert record["added_pixels"] == record["removed_pixels"] == 0


@pytest.mark.parametrize("n,added", [(256, 0), (512, 4), (1024, 15)])
def test_corner_repair_explicit_deterministic_and_bounded(n, added):
    a, record = new.generate_with_metadata(1, **CORNER, resolution=n)
    np.testing.assert_array_equal(a, new.generate_microstructure(1, **CORNER, resolution=n))
    assert old._valid(a)
    assert record["added_pixels"] == added and record["removed_pixels"] == 0
    assert record["added_area_fraction"] == added / n**2
    assert record["bridge_width_normalized"] == 2 / 255
    if n == 256:
        np.testing.assert_array_equal(a, old.generate_microstructure(1, **CORNER))
    else:
        with pytest.raises(RuntimeError, match="fails single-component"):
            old.generate_microstructure(1, **CORNER, resolution=n)


def test_capsules_handle_multiple_components_and_diagonal_gaps():
    a = np.zeros((256, 256), dtype=np.uint8)
    a[100:104, 100:104] = 1
    a[105:107, 105:107] = 1
    a[108:110, 108:110] = 1
    before = a.copy()
    b, record = new.connect_short_gaps(a)
    np.testing.assert_array_equal(a, before)
    assert ndi.label(b)[1] == 1 and record["components_before"] == 3
    assert np.all(b >= a) and len(record["bridges"]) == 2
    np.testing.assert_array_equal(b, new.connect_short_gaps(a)[0])


def test_large_gap_rejected_without_modifying_input():
    a = np.zeros((256, 256), dtype=np.uint8)
    a[10:15, 10:15] = 1; a[100:105, 100:105] = 1
    before = a.copy()
    with pytest.raises(RuntimeError, match="exceeds normalized repair limit"):
        new.connect_short_gaps(a)
    np.testing.assert_array_equal(a, before)


@pytest.mark.parametrize("a", [np.zeros((256, 256), dtype=np.uint8), np.ones((256, 255), dtype=np.uint8),
                               np.ones((256, 256), dtype=float), np.full((256, 256), 2, dtype=np.uint8)])
def test_invalid_masks_rejected(a):
    with pytest.raises(ValueError):
        new.connect_short_gaps(a)


def test_material_budget_fails_closed(monkeypatch):
    a = np.zeros((256, 256), dtype=np.uint8)
    a[100:103, 100:103] = 1; a[100:103, 104:107] = 1
    monkeypatch.setattr(new, "MAX_ADDED_AREA_FRACTION", 0)
    with pytest.raises(RuntimeError, match="added-area budget"):
        new.connect_short_gaps(a)


def test_no_final_resize(monkeypatch):
    from PIL import Image
    def fail(*args, **kwargs):
        raise AssertionError("Production binary interpolation forbidden")
    monkeypatch.setattr(Image.Image, "resize", fail)
    assert new.generate_microstructure(1, **CORNER, resolution=512).shape == (512, 512)


@pytest.mark.parametrize("n", [256, 512, 1024])
def test_synthetic_bar_exact_dimensions(n):
    for width in (4, 6):
        a = workflow.synthetic_shape(n, "bar_x", width)
        assert a.dtype == np.uint8
        assert np.count_nonzero(a[:, n // 2]) == width * n // 256
        assert np.count_nonzero(a[n // 2]) == n // 2
    with pytest.raises(ValueError):
        workflow.synthetic_shape(n, "unknown", 4)


def test_component_distance_is_pixel_center_distance():
    a = np.zeros((256, 256), dtype=np.uint8)
    a[:2, :2] = 1; a[:5, 4:8] = 1
    result, main, labels = workflow.component_diagnostic(a)
    assert result["component_count"] == 2
    assert result["fragments"][0]["pixels"] == 4
    assert result["fragments"][0]["min_pixel_center_distance"] == 3
    assert result["fragments"][0]["min_normalized_center_distance"] == 3 / 255


def test_successive_rows_excludes_failed_cohort_and_preserves_sign():
    jobs = []
    for design in (0, 1):
        for n, value in ((256, 1), (512, .9), (1024, .85)):
            jobs.append({"design_id": design, "seed": 0, "resolution": n,
                         "status": "FAILED" if design == 1 and n == 512 else "COMPLETE",
                         "evaluation": {"normalized": {"normalized_" + k: value for k in workflow.DIMENSIONS}}})
    rows = workflow.successive_rows(jobs)
    assert len(rows) == 2 and rows[0]["mean_strut_thickness"] == pytest.approx(-10)
    assert workflow.signed_change(0, 1) is None


def test_worker_opt_in_records_repair_and_freezes_evaluator(tmp_path):
    record = perform_job({"seed": 1, "resolution": 512, "requested": CORNER, "generator_version": "0.4.1"}, tmp_path / "sample")
    assert record["status"] == "COMPLETE"
    assert record["pipeline_version"] == "0.4.1" and record["topology_repair"]["added_pixels"] == 4
    assert record["evaluator_sha256"] == workflow.FROZEN_SHA
    assert record["generator_sha256"] != record["native_renderer_sha256"]
    with pytest.raises(ValueError, match="Unsupported generator"):
        perform_job({"generator_version": "bad"}, tmp_path / "invalid")


def test_cli_requires_evidence_and_supports_version_selection():
    from metamaterial_eval.pipeline.cli import _parser
    args = _parser().parse_args(["resolution-generate", "--seed", "0", "--solid-fraction-target", ".5",
                                "--strut-scale", "4", "--pore-scale", "7", "--generator-version", "0.4.1",
                                "--output-dir", "x"])
    assert args.generator_version == "0.4.1"
    with pytest.raises(SystemExit):
        workflow.main(["validate", "--output-dir", "unused"])
