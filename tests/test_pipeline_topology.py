"""Scientific and end-to-end checks for optional single-network policy."""

import json
from pathlib import Path

import numpy as np
import pytest

from metamaterial_eval.pipeline.config import PipelineConfig, default_evaluator_path
from metamaterial_eval.pipeline.evaluator import extract_target_descriptors, load_evaluator
from metamaterial_eval.pipeline.prompts import build_initial_prompt
from metamaterial_eval.pipeline.reference import canonicalize_reference
from metamaterial_eval.pipeline.runner import start_run, resume_run
from metamaterial_eval.pipeline.state import read_json
from metamaterial_eval.pipeline.topology import is_valid, structural_reference

EVALUATOR = default_evaluator_path()


def grid() -> np.ndarray:
    array = np.zeros((256, 256), dtype=np.uint8)
    for i in range(0, 256, 32):
        array[i:i + 3, :] = 1
        array[:, i:i + 3] = 1
    return array


def test_preview_cli_creates_both_descriptor_sets_without_run_manifest(tmp_path):
    from metamaterial_eval.pipeline.cli import main

    raw = grid()
    raw[10, 10] = 1
    source = tmp_path / "raw.npy"
    output = tmp_path / "preview"
    np.save(source, raw)
    args = ["prepare-reference", str(source), "--output-dir", str(output),
            "--topology-mode", "single_connected_network"]
    assert main(args) == 0
    assert read_json(output / "raw_target_metrics.json")["component_count"] == 2
    assert read_json(output / "target_metrics.json")["component_count"] == 1
    assert (output / "prompt_preview.txt").is_file()
    assert not (output / "manifest.json").exists()
    saved = (output / "metadata.json").read_bytes()
    assert main(args) != 0
    assert (output / "metadata.json").read_bytes() == saved


def test_single_network_cannot_use_legacy_prompt_policy():
    with pytest.raises(ValueError, match="requires prompt_version"):
        PipelineConfig(topology_mode="single_connected_network", prompt_version="1.0")


def test_cleaning_retains_only_largest_four_connected_component(tmp_path):
    raw = grid()
    raw[10, 10] = 1
    raw[11, 11] = 1  # diagonal pixels are separate under 4-connectivity
    source = tmp_path / "raw.npy"
    np.save(source, raw)
    binary, metadata = canonicalize_reference(
        source, tmp_path / "reference",
        PipelineConfig(topology_mode="single_connected_network"),
        threshold=None, evaluator_hash="test",
    )
    np.testing.assert_array_equal(binary, grid())
    np.testing.assert_array_equal(np.load(source), raw)
    np.testing.assert_array_equal(np.load(tmp_path / "reference/reference_raw.npy"), raw)
    for name in ("reference_structural", "reference_binary"):
        np.testing.assert_array_equal(np.load(tmp_path / f"reference/{name}.npy"), binary)
    assert (tmp_path / "reference/reference_raw.png").is_file()
    assert (tmp_path / "reference/reference_structural.png").is_file()
    cleaning = metadata["cleaning"]
    assert cleaning["raw_component_count"] == 3
    assert cleaning["removed_component_count"] == 2
    assert cleaning["removed_solid_pixels"] == 2
    assert cleaning["removed_solid_fraction"] == pytest.approx(2 / raw.sum())
    assert cleaning["removed_image_fraction"] == 2 / raw.size
    assert cleaning["retained_solid_fraction"] == binary.mean()


def test_target_descriptors_are_recomputed_from_structural_image(tmp_path):
    raw = grid()
    raw[7:20, 7:20] = 1
    source = tmp_path / "raw.npy"
    np.save(source, raw)
    run = start_run(
        source, run_name="clean", runs_root=tmp_path / "runs",
        config=PipelineConfig(topology_mode="single_connected_network"),
    )
    target = read_json(run / "reference/target_metrics.json")
    direct = extract_target_descriptors(grid(), PipelineConfig(topology_mode="single_connected_network"), EVALUATOR)
    assert target == direct
    assert target["phi_s"] != float(raw.mean())
    assert target["component_count"] == 1 and target["f_largest"] == 1.0
    prompt = (run / "iteration_0/prompt_0.txt").read_text(encoding="utf-8")
    assert "Largest-component fraction: 1.000000" in prompt
    assert "Do not add isolated solid islands merely to match solid volume fraction" in prompt
    context = read_json(run / "iteration_0/prompt_context.json")
    assert context["topology_mode"] == "single_connected_network"
    assert context["heldout_data_included"] is False


def test_preserve_reference_does_not_remove_particles():
    raw = grid()
    raw[10, 10] = 1
    binary, cleaning = structural_reference(raw, "preserve_reference", load_evaluator(str(EVALUATOR)))
    np.testing.assert_array_equal(binary, raw)
    assert cleaning["removed_component_count"] == 0
    assert cleaning["removed_solid_pixels"] == 0


def test_strict_policy_rejects_even_one_pixel_island():
    raw = grid()
    raw[10, 10] = 1
    basic = load_evaluator(str(EVALUATOR)).basic_metrics(raw)
    assert basic["f_largest"] > 0.99
    assert is_valid(basic, "preserve_reference")
    assert not is_valid(basic, "single_connected_network")


def test_empty_and_tied_components_are_handled_deterministically():
    evaluator = load_evaluator(str(EVALUATOR))
    raw = np.zeros((256, 256), dtype=np.uint8)
    with pytest.raises(ValueError, match="no solid pixels"):
        structural_reference(raw, "single_connected_network", evaluator)
    raw[10, 10] = raw[30, 30] = 1
    selected, _ = structural_reference(raw, "single_connected_network", evaluator)
    assert selected.sum() == 1 and selected[10, 10] == 1


def test_nonspanning_target_is_reported_without_fabricated_percolation():
    raw = np.zeros((256, 256), dtype=np.uint8)
    raw[10:20, 10:20] = 1
    selected, cleaning = structural_reference(raw, "single_connected_network", load_evaluator(str(EVALUATOR)))
    target = extract_target_descriptors(selected, PipelineConfig(topology_mode="single_connected_network"), EVALUATOR)
    assert not target["valid"] and target["Px"] == target["Py"] == 0
    assert cleaning["warnings"]
    prompt = build_initial_prompt(target)
    assert "Left-right percolation: false" in prompt
    assert "generated design must span both axes" in prompt
    assert target["median_pore_diameter"] is None
    json.dumps(target, allow_nan=False)


def test_old_manifest_keeps_legacy_prompt_and_policy():
    legacy = PipelineConfig().to_dict()
    legacy.pop("topology_mode")
    legacy["prompt_version"] = "1.0"
    legacy["pipeline_version"] = "0.1.0"
    config = PipelineConfig.from_dict(legacy)
    assert config.topology_mode == "preserve_reference"
    target = extract_target_descriptors(grid(), config, EVALUATOR)
    assert "Topology policy:" not in build_initial_prompt(target)
    assert "one dominant 4-connected solid network" in build_initial_prompt(target)


RESPONSE = '''```python
from pathlib import Path
import argparse
import numpy as np
from PIL import Image
p = argparse.ArgumentParser()
p.add_argument('--seed-start', type=int, default=0)
p.add_argument('--num-samples', type=int, default=20)
p.add_argument('--output-dir', type=Path, default=Path('generated'))
a = p.parse_args()
a.output_dir.mkdir(parents=True, exist_ok=True)
for seed in range(a.seed_start, a.seed_start + a.num_samples):
    binary = np.zeros((256, 256), dtype=np.uint8)
    for i in range(0, 256, 32):
        binary[i:i+3, :] = 1
        binary[:, i:i+3] = 1
    binary[10, 7 + seed % 20] = 1
    name = a.output_dir / f'microstructure_seed_{seed:03d}'
    np.save(name.with_suffix('.npy'), binary)
    Image.fromarray(binary * 255).save(name.with_suffix('.png'))
```'''


def test_full_run_uses_policy_in_feedback_resume_and_final_summary(tmp_path):
    source = tmp_path / "source.npy"
    np.save(source, grid())
    run = start_run(
        source, run_name="policy-e2e", runs_root=tmp_path / "runs",
        config=PipelineConfig(topology_mode="single_connected_network", max_feedback_rounds=1),
    )
    (run / "iteration_0/response_0.txt").write_bytes(RESPONSE.encode("utf-8"))
    manifest = resume_run(run)
    assert manifest["status"] == "WAITING_FOR_REVISION", manifest.get("failure_reason")
    prompt = (run / "iteration_1/prompt_1.txt").read_text(encoding="utf-8")
    assert "Valid samples: 0 / 20" in prompt
    assert "component_count: 2 +/- 0" in prompt
    assert "20 generated structures contain disconnected solid components" in prompt
    assert "Do not add isolated solid islands" in prompt
    legacy_path = run / "iteration_0/evaluation/evaluation_summary.json"
    legacy_bytes = legacy_path.read_bytes()
    legacy = read_json(legacy_path)
    assert legacy["valid_sample_count"] == 20
    policy = read_json(run / "iteration_0/evaluation/pipeline_evaluation_summary.json")
    assert policy["valid_sample_count"] == 0
    assert policy["legacy_valid_sample_count"] == 20
    assert policy["valid_ensemble_summary"]["component_count"]["mean"] is None
    assert not policy["samples"][0]["valid"] and policy["samples"][0]["legacy_valid"]
    assert policy["ensemble_summary"]["E_S2"] == legacy["ensemble_summary"]["E_S2"]
    # Pause/resume with no new response leaves all existing artifacts intact.
    assert resume_run(run)["status"] == "WAITING_FOR_REVISION"
    assert legacy_path.read_bytes() == legacy_bytes
    (run / "iteration_1/response_1.txt").write_bytes(RESPONSE.encode("utf-8"))
    manifest = resume_run(run)
    assert manifest["status"] == "COMPLETE", manifest.get("failure_reason")
    summary = read_json(run / "final/summary.json")
    for key in ("final_development_performance", "heldout_performance"):
        assert summary[key]["valid_sample_count"] == 0
        assert summary[key]["component_count"] == 2
        assert summary[key]["legacy_valid_sample_count"] == 20
    assert summary["warnings"]
    heldout_sample = np.load(run / "final/heldout/generated/microstructure_seed_100.npy")
    assert load_evaluator(str(EVALUATOR)).basic_metrics(heldout_sample)["component_count"] == 2
    assert summary["reference_cleaning"]["removed_solid_pixels"] == 0
