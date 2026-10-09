"""v0.4 native rendering, exact v0.3 regression, normalized validation contracts."""
from pathlib import Path
import hashlib

import numpy as np
import pytest
from PIL import Image

from metamaterial_eval.generators import native_resolution as native, v03_baseline
from metamaterial_eval.pipeline.resolution import (
    validate_resolution, resolution_scale, length_pixels, area_pixels,
    normalized_dimensions, normalized_radii, block_reduce,
)
from metamaterial_eval.pipeline.resolution_worker import evaluate_native, perform_job
from metamaterial_eval.pipeline.resolution_validation import select_designs, inventory
from metamaterial_eval.pipeline.resolution_report import build_report, compare_pair
from metamaterial_eval.pipeline.evaluator import load_evaluator
from metamaterial_eval.pipeline.config import default_evaluator_path
from metamaterial_eval.pipeline.state import read_json

# Existing LHS designs 0, 1, 2 at seed 0; hashes from saved Windows v0.3 arrays.
REGRESSION = [
    ((.47949869779450194, 3.8117182167728196, 8.405665555093796), "cc783532135af3651a87a50a73e0c84535eef79352dbb522b33fa54a9eb7f0ec"),
    ((.432495799544353, 3.6074895607218114, 6.641245935745653), "a360e59ef492cebf94641266bcd93886fce89b84725148548bdbaa1263d3ff19"),
    ((.5178083089302478, 4.632533891188587, 6.020372521043691), "5df425d0e1a2fc8b8519abaeb4caaeafbcd9a977035810f4340fe4a5c70be857"),
]
PARAMS = dict(zip(("solid_fraction_target", "strut_scale", "pore_scale"), REGRESSION[0][0]))


@pytest.mark.parametrize("params,digest", REGRESSION)
def test_256_matches_original_and_saved_windows_hash(params, digest):
    new = native.generate_microstructure(0, *params)
    old = v03_baseline.generate_microstructure(0, *params)
    assert new.shape == (256, 256)
    np.testing.assert_array_equal(new, old)
    assert hashlib.sha256(new.tobytes()).hexdigest() == digest


@pytest.mark.parametrize("n", [256, 512, 1024])
def test_native_shape_contract_repeat_topology_and_unchanged_controls(n):
    a = native.generate_microstructure(0, **PARAMS, resolution=n)
    b = native.generate_microstructure(0, **PARAMS, resolution=n)
    assert a.shape == (n, n) and a.dtype == np.uint8
    assert set(np.unique(a)) == {0, 1}
    np.testing.assert_array_equal(a, b)
    e = load_evaluator(str(default_evaluator_path()))
    basic = e.basic_metrics(a)
    assert basic["component_count"] == basic["Px"] == basic["Py"] == 1
    assert abs(basic["phi_s"] - PARAMS["solid_fraction_target"]) <= 1 / n**2


def test_distinct_root_seeds():
    assert not np.array_equal(native.generate_microstructure(0, **PARAMS, resolution=512),
                              native.generate_microstructure(1, **PARAMS, resolution=512))


@pytest.mark.parametrize("n", [0, -1, 1, 255, 256.0, 512.5, True, "512", 5000])
def test_invalid_resolution_rejected(n):
    with pytest.raises(ValueError):
        native.generate_microstructure(0, **PARAMS, resolution=n)


def test_scaling_radius_and_normalized_dimensions():
    assert resolution_scale(1024) == 4
    assert length_pixels(4, 1024) == 16
    assert area_pixels(4, 1024) == 64
    assert normalized_radii(512)["pixel_radii"] == [0, 2, 4, 8, 16, 32, 64, 128]
    assert normalized_radii(1024)["pixel_radii"] == [0, 4, 8, 16, 32, 64, 128, 256]
    arbitrary = normalized_radii(300)
    assert max(abs(x) for x in arbitrary["rho_rounding_error"]) <= .5/300
    m = normalized_dimensions(dict(mean_strut_thickness=16, p10_strut_thickness=8, median_pore_diameter=None), 1024)
    assert m["normalized_mean_strut_thickness"] == 4/256
    assert m["normalized_p10_strut_thickness"] == 2/256
    assert m["normalized_median_pore_diameter"] is None


def test_no_final_binary_resize(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Final image resize is forbidden")
    monkeypatch.setattr(Image.Image, "resize", forbidden)
    original_zoom = v03_baseline.ndi.zoom
    shapes = []
    def zoom_continuous_only(array, *args, **kwargs):
        shapes.append(array.shape)
        assert array.dtype.kind == 'f' and array.shape[0] in (15, 20, 34, 42)
        return original_zoom(array, *args, **kwargs)
    monkeypatch.setattr(v03_baseline.ndi, "zoom", zoom_continuous_only)
    high = native.generate_microstructure(0, **PARAMS, resolution=512)
    low = native.generate_microstructure(0, **PARAMS)
    enlarged = np.repeat(np.repeat(low, 2, axis=0), 2, axis=1)
    assert not np.array_equal(high, enlarged) and shapes


def test_arbitrary_native_resolution_and_evaluator():
    a = native.generate_microstructure(0, **PARAMS, resolution=300)
    m = evaluate_native(a)
    assert m["raw"]["shape"] == [300, 300]
    assert len(m["common_curves"]["s2"]) == 65
    assert m["common_curves"]["s2"][0] == m["raw"]["phi_s"]
    with pytest.raises(ValueError): block_reduce(a)


def test_block_reduction_is_area_majority():
    a = np.array([[1, 1, 0, 0], [0, 0, 1, 0], [1, 1, 0, 0], [1, 0, 0, 0]], dtype=np.uint8)
    np.testing.assert_array_equal(block_reduce(a, target=2), [[1,0],[1,0]])


def test_job_manifest_timing_failure_and_summary_preserve_history(tmp_path, monkeypatch):
    history = tmp_path / "history"
    history.mkdir()
    saved = native.generate_microstructure(0, **PARAMS)
    np.save(history / "saved.npy", saved)
    before = inventory(history)
    job = {"design_id": 0, "seed": 0, "requested": PARAMS, "historical_sample": str(history / "saved.npy")}
    base = perform_job({**job, "resolution": 256}, tmp_path / "256")
    assert base["status"] == "COMPLETE" and base["regression"]["saved_output_bitwise_equal"]
    assert base["generation_seconds"] > 0 and base["evaluation_seconds"] > 0
    assert base["files"]["microstructure.npy"]["bytes"] > 0
    assert read_json(tmp_path / "256/timing.json")["peak_traced_generation_bytes"] > 0
    assert base["generator_sha256"] and base["evaluator_sha256"]
    def fail(*args, **kwargs): raise RuntimeError("deliberate native failure")
    monkeypatch.setattr(native, "generate_microstructure", fail)
    bad = perform_job({**job, "resolution": 1024}, tmp_path / "1024")
    assert bad["status"] == "FAILED" and "deliberate native failure" in bad["error"]
    base["relative_directory"], bad["relative_directory"] = "256", "1024"
    manifest = {"jobs": [base,bad], "source_run": str(history), "source_v03_sha256": native.SOURCE_V03_SHA256,
                "native_generator_sha256": base["generator_sha256"], "resolutions": [256,1024], "historical_unchanged": True}
    selected = {"design_ids": [0], "samples": [job], "selection_reasons": {"0": "test"}}
    report = build_report(tmp_path, manifest, selected)
    assert report["successful_outputs"] == 1 and report["expected_outputs"] == 2
    assert not report["comparisons"][0]["available"] and not report["ready_for_v05"]
    assert (tmp_path / "summary/resolution_convergence.csv").is_file()
    assert before == inventory(history)


def test_selection_reuses_existing_rows_only():
    from metamaterial_eval.pipeline.design_space import make_plan
    plan = make_plan(dict(phi_s=.4, mean_strut_thickness=4, median_pore_diameter=8), s2_limit=.25, lineal_limit=.25)
    chosen = select_designs(plan)
    assert len(chosen["design_ids"]) == 5 and len(chosen["samples"]) == 10
    assert all(row in plan["samples"] for row in chosen["samples"])
