"""Acceptance-focused tests for the Pipeline v0.1 orchestration layer."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from metamaterial_eval.pipeline.config import PipelineConfig, default_evaluator_path
from metamaterial_eval.pipeline.evaluator import extract_target_descriptors
from metamaterial_eval.pipeline.execution import run_subprocess
from metamaterial_eval.pipeline.prompts import (
    build_feedback_prompt,
    build_initial_prompt,
    format_sampled_curve,
)
from metamaterial_eval.pipeline.reporting import build_final_summary
from metamaterial_eval.pipeline.runner import (
    _freeze_final_generator,
    _write_or_reuse_script,
    resume_run,
    start_run,
)
from metamaterial_eval.pipeline.scripts import (
    ScriptExtractionError,
    extract_python_script,
    sha256_file,
    write_new_script,
)
from metamaterial_eval.pipeline.state import (
    CREATED,
    FAILED,
    FINAL_GENERATOR_FROZEN,
    WAITING_FOR_INITIAL_LLM,
    advance,
    fail,
    load_manifest,
    save_manifest,
)


REPOSITORY = Path(__file__).resolve().parents[1]
REFERENCE = REPOSITORY / "data" / "reference" / "reference_binary.npy"


def target_fixture() -> dict:
    radii = [0, 1, 2, 4, 8, 16, 32, 64]
    return {
        "phi_s": 0.4,
        "f_largest": 0.99,
        "Px": 1,
        "Py": 1,
        "mean_strut_thickness": 6.2,
        "p10_strut_thickness": 4.0,
        "median_pore_diameter": 17.0,
        "sampled_descriptors": {
            "radii": radii,
            "s2_text": ", ".join(f"r={r}: {0.4 / (r + 1):.6f}" for r in radii),
            "lineal_path_text": ", ".join(
                f"r={r}: {0.4 / (r + 2):.6f}" for r in radii
            ),
        },
    }


def report_fixture(*, valid_count: int = 17, offset: float = 0.0) -> dict:
    values = {
        "phi_s": 0.41 + offset,
        "f_largest": 0.985,
        "mean_strut_thickness": 6.4 + offset,
        "p10_strut_thickness": 4.1,
        "median_pore_diameter": 16.5 + offset,
        "E_S2": 0.0612 + offset,
        "E_L": 0.0341 + offset,
    }
    return {
        "sample_count": 20,
        "valid_sample_count": valid_count,
        "ensemble_summary": {
            key: {"mean": value, "std": 0.0123, "min": value, "max": value}
            for key, value in values.items()
        },
        "diversity": {"D_pair": 0.25 + offset, "healthy": True},
        "novelty": {"flagged_files": []},
    }


def minimal_manifest(run_dir: Path, config: PipelineConfig) -> dict:
    return {
        "run_id": "unit-run",
        "run_directory": str(run_dir),
        "reference_name": "unit-reference",
        "pipeline_version": config.pipeline_version,
        "evaluator_version": config.evaluator_version,
        "prompt_version": config.prompt_version,
        "configuration": config.to_dict(),
        "current_iteration": 0,
        "iterations": {},
        "execution_repairs": {},
        "status": CREATED,
        "failure_reason": None,
        "recoverable_state": None,
    }


def test_01_target_descriptor_extraction_uses_current_evaluator_values() -> None:
    array = np.load(REFERENCE, allow_pickle=False)
    modified = array.copy()
    solid_y, solid_x = np.argwhere(modified == 1)[0]
    modified[solid_y, solid_x] = 0
    first = extract_target_descriptors(array, PipelineConfig(), default_evaluator_path())
    second = extract_target_descriptors(modified, PipelineConfig(), default_evaluator_path())
    assert first["phi_s"] == pytest.approx(float(array.mean()))
    assert second["phi_s"] == pytest.approx(float(modified.mean()))
    assert first["phi_s"] != second["phi_s"]


def test_02_initial_i2_prompt_inserts_descriptor_values() -> None:
    prompt = build_initial_prompt(target_fixture())
    assert "Solid volume fraction: 0.4" in prompt
    assert "Mean local strut thickness: 6.2 pixels" in prompt
    assert "r=64:" in prompt
    assert "--seed-start" in prompt and "--output-dir" in prompt


def test_03_sampled_curve_formatting_is_deterministic() -> None:
    result = format_sampled_curve([0, 1, 2], [0.4, 0.25, 0.125], [2, 0])
    assert result == "r=2: 0.125000, r=0: 0.400000"


def test_04_feedback_prompt_contains_generated_population_statistics() -> None:
    prompt = build_feedback_prompt(
        target_fixture(),
        report_fixture(),
        {"summary_lines": ["Mean thickness differs."]},
        round_number=1,
        max_rounds=3,
        development_count=20,
    )
    assert "phi_s: 0.41 +/- 0.0123" in prompt
    assert "E_S2: 0.0612 +/- 0.0123" in prompt


def test_05_feedback_prompt_contains_valid_sample_count() -> None:
    prompt = build_feedback_prompt(
        target_fixture(),
        report_fixture(valid_count=17),
        {"summary_lines": ["Topology remains imperfect."]},
        round_number=2,
        max_rounds=3,
        development_count=20,
    )
    assert "Valid samples: 17 / 20" in prompt


def test_06_feedback_builder_has_no_heldout_input_channel() -> None:
    parameters = inspect.signature(build_feedback_prompt).parameters
    assert not any("held" in name.lower() for name in parameters)


def test_07_start_creates_versioned_run_directories(tmp_path: Path) -> None:
    run_dir = start_run(REFERENCE, runs_root=tmp_path)
    manifest = load_manifest(run_dir)
    assert run_dir.name.startswith("run-")
    assert manifest["status"] == WAITING_FOR_INITIAL_LLM
    assert (run_dir / "reference" / "reference_binary.npy").is_file()
    assert (run_dir / "reference" / "target_metrics.json").is_file()
    assert (run_dir / "iteration_0" / "prompt_0.txt").is_file()
    assert manifest["waiting_for"].endswith("iteration_0/response_0.txt")


def test_08_historical_iteration_script_is_never_overwritten(tmp_path: Path) -> None:
    destination = tmp_path / "iteration_0.py"
    response = "```python\nimport sys\nprint(sys.version)\n```"
    write_new_script(response, destination)
    original = destination.read_bytes()
    with pytest.raises(FileExistsError):
        write_new_script(response, destination)
    assert destination.read_bytes() == original
    # A crash-recovery path may adopt the exact same immutable artifact, but it
    # still does not rewrite it.
    _write_or_reuse_script(response, destination)
    assert destination.read_bytes() == original


def test_09_normal_fenced_python_response_is_extracted() -> None:
    response = "Explanation.\n```python\nimport numpy as np\nprint(np.__version__)\n```\nDone."
    source = extract_python_script(response)
    assert source.startswith("import numpy as np")
    assert "Explanation" not in source


def test_10_ambiguous_script_response_fails_safely() -> None:
    response = "```python\nimport os\n```\n```python\nimport sys\n```"
    with pytest.raises(ScriptExtractionError, match="multiple"):
        extract_python_script(response)


def test_11_subprocess_stdout_and_stderr_are_captured(tmp_path: Path) -> None:
    result = run_subprocess(
        [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"],
        cwd=tmp_path,
        log_dir=tmp_path / "logs",
        timeout_seconds=5,
    )
    assert result.succeeded
    assert Path(result.stdout_path).read_text().strip() == "out"
    assert Path(result.stderr_path).read_text().strip() == "err"
    assert json.loads((tmp_path / "logs" / "metadata.json").read_text())["return_code"] == 0


def test_12_generator_timeout_is_recorded(tmp_path: Path) -> None:
    result = run_subprocess(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        cwd=tmp_path,
        log_dir=tmp_path / "timeout",
        timeout_seconds=0.05,
    )
    assert result.timed_out and not result.succeeded
    assert "exceeded timeout" in Path(result.stderr_path).read_text()


def test_13_manifest_state_advances_atomically(tmp_path: Path) -> None:
    manifest = minimal_manifest(tmp_path, PipelineConfig())
    save_manifest(tmp_path, manifest)
    advance(tmp_path, manifest, WAITING_FOR_INITIAL_LLM, waiting_for="response_0.txt")
    reloaded = load_manifest(tmp_path)
    assert reloaded["status"] == WAITING_FOR_INITIAL_LLM
    assert reloaded["waiting_for"] == "response_0.txt"


def test_14_recoverable_failed_state_can_resume(tmp_path: Path) -> None:
    run_dir = start_run(REFERENCE, run_name="resume-test", runs_root=tmp_path)
    manifest = load_manifest(run_dir)
    fail(
        run_dir,
        manifest,
        "researcher must replace malformed response",
        recoverable_state=WAITING_FOR_INITIAL_LLM,
    )
    assert resume_run(run_dir)["status"] == FAILED
    assert resume_run(run_dir, retry_failed=True)["status"] == WAITING_FOR_INITIAL_LLM


def test_15_final_generator_is_hashed_and_frozen_before_heldout(tmp_path: Path) -> None:
    config = PipelineConfig()
    iteration_dir = tmp_path / "iteration_0"
    iteration_dir.mkdir()
    source = iteration_dir / "iteration_0.py"
    source.write_text("import sys\nprint(sys.version)\n", encoding="utf-8")
    digest = sha256_file(source)
    manifest = minimal_manifest(tmp_path, config)
    manifest.update(
        {
            "iterations": {
                "0": {
                    "active_generator_path": str(source),
                    "active_generator_sha256": digest,
                    "generated_development_path": str(iteration_dir / "generated"),
                    "evaluation_path": str(iteration_dir / "evaluation.json"),
                    "sample_audit_path": str(iteration_dir / "audit.json"),
                }
            },
            "iteration_generator_hashes": {"0": {"generator": digest}},
            "final_generator_hash": None,
        }
    )
    save_manifest(tmp_path, manifest)
    with patch("metamaterial_eval.pipeline.runner._run_heldout") as heldout:
        _freeze_final_generator(
            tmp_path, manifest, config, 0, report_fixture(), {"passed": True}
        )
    frozen = tmp_path / "final" / "final_generator.py"
    assert sha256_file(frozen) == digest
    assert manifest["status"] == FINAL_GENERATOR_FROZEN
    heldout.assert_called_once()


def test_16_development_seed_contract_is_zero_through_nineteen() -> None:
    assert PipelineConfig().development_seeds == tuple(range(20))


def test_17_heldout_seed_contract_is_one_hundred_through_one_nineteen() -> None:
    assert PipelineConfig().heldout_seeds == tuple(range(100, 120))


def test_18_final_summary_contains_development_and_heldout_metrics(tmp_path: Path) -> None:
    script = tmp_path / "final_generator.py"
    script.write_text("import sys\nprint(sys.version)\n", encoding="utf-8")
    reports = {0: report_fixture(), 1: report_fixture(offset=0.01)}
    audits = {"iteration_0": {"passed": True}, "heldout": {"passed": True}}
    manifest = {
        "run_id": "summary-test",
        "reference_name": "reference",
        "pipeline_version": "0.1.0",
        "evaluator_version": "1.1",
        "execution_repairs": {"0": False, "1": False},
    }
    summary = build_final_summary(
        run_dir=tmp_path,
        manifest=manifest,
        target=target_fixture(),
        iteration_reports=reports,
        heldout_report=report_fixture(offset=0.02),
        audits=audits,
        final_script=script,
        final_hash=sha256_file(script),
        final_iteration=1,
        final_runtime_seconds=1.25,
    )
    assert len(summary["development_trajectory"]) == 2
    assert summary["heldout_performance"]["E_S2"] == pytest.approx(0.0812)
    assert "development_vs_heldout" in summary
    assert (tmp_path / "final" / "summary.json").is_file()
    assert (tmp_path / "final" / "summary.md").is_file()
