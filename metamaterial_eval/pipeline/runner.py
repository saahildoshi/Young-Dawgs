"""Resumable deterministic orchestration for the manual I2F1 workflow."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from .config import PipelineConfig, default_evaluator_path, default_runs_root
from .evaluator import (
    PipelineEvaluationError,
    evaluator_hash,
    extract_target_descriptors,
    run_v1_1_evaluation,
)
from .execution import ExecutionResult, run_generator
from .prompts import (
    build_execution_repair_prompt,
    build_feedback_prompt,
    build_initial_prompt,
)
from .providers import make_provider
from .reference import array_sha256, canonicalize_reference
from .reporting import build_final_summary, compare_to_target
from .scripts import (
    ScriptExtractionError,
    extract_python_script,
    script_sha256,
    sha256_file,
    write_new_script,
)
from .state import (
    COMPLETE,
    CREATED,
    DEVELOPMENT_EVALUATED,
    DEVELOPMENT_GENERATED,
    FAILED,
    FINAL_GENERATOR_FROZEN,
    HELDOUT_EVALUATED,
    HELDOUT_GENERATED,
    REFERENCE_READY,
    TARGET_EVALUATED,
    WAITING_FOR_EXECUTION_REPAIR,
    WAITING_FOR_INITIAL_LLM,
    WAITING_FOR_REVISION,
    advance,
    fail,
    load_manifest,
    read_json,
    save_manifest,
    utc_now,
    write_json,
)


SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _safe_name(value: str, label: str) -> str:
    if not SAFE_NAME.fullmatch(value):
        raise ValueError(
            f"{label} must start with an alphanumeric character and contain "
            "only letters, numbers, '.', '_', or '-'."
        )
    return value


def _reference_name(source: Path) -> str:
    """Create a stable filesystem-safe label without restricting input paths."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", source.stem).strip("._-")
    if not name:
        raise ValueError("Reference filename must contain at least one letter or number.")
    return name


def _iteration_dir(run_dir: Path, iteration: int) -> Path:
    return run_dir / f"iteration_{iteration}"


def _reference_path(run_dir: Path) -> Path:
    return run_dir / "reference" / "reference_binary.npy"


def _target_path(run_dir: Path) -> Path:
    return run_dir / "reference" / "target_metrics.json"


def _read_target(run_dir: Path) -> dict[str, Any]:
    return read_json(_target_path(run_dir))


def _protected_hashes(
    run_dir: Path, manifest: dict[str, Any], script_path: Path | None = None
) -> dict[str, str]:
    hashes = {
        "evaluator": sha256_file(Path(manifest["evaluator_path"])),
        "reference": array_sha256(
            np.load(_reference_path(run_dir), allow_pickle=False)
        ),
    }
    if script_path is not None:
        hashes["script"] = sha256_file(script_path)
    return hashes


def _verify_protected_assets(
    run_dir: Path, manifest: dict[str, Any], script_path: Path | None = None
) -> None:
    current = _protected_hashes(run_dir, manifest, script_path)
    if current["evaluator"] != manifest["evaluator_sha256"]:
        raise RuntimeError("Frozen evaluator v1.1 hash changed during the run.")
    if current["reference"] != manifest["reference_sha256"]:
        raise RuntimeError("Canonical reference hash changed during the run.")
    if script_path is not None:
        expected = manifest["iterations"][str(manifest["current_iteration"])][
            "active_generator_sha256"
        ]
        if current["script"] != expected:
            raise RuntimeError("Active model-generated script was modified after extraction.")


def _initial_manifest(
    *,
    run_id: str,
    reference_name: str,
    config: PipelineConfig,
    evaluator_path: Path,
    provider: str,
    model: str | None,
    run_dir: Path,
) -> dict[str, Any]:
    created = utc_now()
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "run_directory": str(run_dir),
        "reference_name": reference_name,
        "reference_hash": None,
        "pipeline_version": config.pipeline_version,
        "evaluator_version": config.evaluator_version,
        "evaluator_path": str(evaluator_path.resolve()),
        "evaluator_sha256": evaluator_hash(evaluator_path),
        "prompt_version": config.prompt_version,
        "prompt_strategy": "I2F1",
        "llm_provider": provider,
        "model_name": model,
        "reasoning_configuration": None,
        "created_at_utc": created,
        "updated_at_utc": created,
        "configuration": config.to_dict(),
        "development_seeds": list(config.development_seeds),
        "heldout_seeds": list(config.heldout_seeds),
        "maximum_revisions": config.max_feedback_rounds,
        "actual_revisions_completed": 0,
        "current_iteration": 0,
        "execution_repairs": {},
        "iteration_generator_hashes": {},
        "iteration_execution_times_seconds": {},
        "valid_sample_counts": {},
        "iterations": {},
        "final_generator_hash": None,
        "final_development_metrics": None,
        "final_heldout_metrics": None,
        "completion_status": "incomplete",
        "status": CREATED,
        "failure_reason": None,
        "recoverable_state": None,
    }


def _write_prompt_context(
    iteration_dir: Path,
    *,
    target: dict[str, Any],
    iteration: int,
    development_report: str | None,
    comparison: str | None,
) -> None:
    # This object can contain target and development data only. Held-out data is
    # structurally unavailable until after the final generator has been frozen.
    write_json(
        iteration_dir / "prompt_context.json",
        {
            "data_classification": [
                "target_descriptors",
                *( ["development_metrics"] if development_report else [] ),
            ],
            "iteration": iteration,
            "target_metrics_path": str(_target_path(iteration_dir.parent)),
            "development_report_path": development_report,
            "comparison_path": comparison,
            "heldout_data_included": False,
            "target_information_available_to_generator": {
                "solid_fraction": True,
                "largest_component_fraction": True,
                "S2": True,
                "lineal_path": True,
                "thickness": True,
                "pore_diameter": True,
            },
        },
    )


def _prepare_initial_boundary(
    run_dir: Path, manifest: dict[str, Any], target: dict[str, Any]
) -> None:
    iteration_dir = _iteration_dir(run_dir, 0)
    iteration_dir.mkdir(parents=True, exist_ok=False)
    prompt_path = iteration_dir / "prompt_0.txt"
    prompt_path.write_text(build_initial_prompt(target), encoding="utf-8")
    _write_prompt_context(
        iteration_dir,
        target=target,
        iteration=0,
        development_report=None,
        comparison=None,
    )
    manifest["iterations"]["0"] = {
        "prompt_path": str(prompt_path),
        "prompt_context_path": str(iteration_dir / "prompt_context.json"),
        "response_path": str(iteration_dir / "response_0.txt"),
        "generator_path": None,
        "active_generator_path": None,
        "active_generator_sha256": None,
        "generated_development_path": None,
        "evaluation_path": None,
        "comparison_path": None,
    }
    advance(
        run_dir,
        manifest,
        WAITING_FOR_INITIAL_LLM,
        waiting_for=str(iteration_dir / "response_0.txt"),
    )


def start_run(
    reference: Path,
    *,
    run_name: str | None = None,
    runs_root: Path | None = None,
    threshold: float | None = None,
    provider_name: str = "manual-file",
    model_name: str | None = None,
    config: PipelineConfig | None = None,
    evaluator_path: Path | None = None,
) -> Path:
    """Create a run and advance deterministically to the first LLM boundary."""
    config = config or PipelineConfig()
    evaluator_path = (evaluator_path or default_evaluator_path()).resolve()
    runs_root = (runs_root or default_runs_root()).resolve()
    make_provider(provider_name)  # validate before creating files
    reference_name = _reference_name(reference)
    generated_run_name = (
        "run-" + utc_now().replace("+00:00", "Z").replace(":", "").replace("-", "")
    )
    run_id = _safe_name(
        run_name or generated_run_name,
        "run name",
    )
    run_dir = runs_root / reference_name / run_id
    if run_dir.exists():
        raise FileExistsError(f"Run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    manifest = _initial_manifest(
        run_id=run_id,
        reference_name=reference_name,
        config=config,
        evaluator_path=evaluator_path,
        provider=provider_name,
        model=model_name,
        run_dir=run_dir,
    )
    save_manifest(run_dir, manifest)
    try:
        binary, metadata = canonicalize_reference(
            reference,
            run_dir / "reference",
            config,
            threshold=threshold,
            evaluator_hash=manifest["evaluator_sha256"],
        )
        manifest["reference_hash"] = metadata["sha256_canonical_binary"]
        manifest["reference_sha256"] = metadata["sha256_canonical_binary"]
        advance(run_dir, manifest, REFERENCE_READY)

        target = extract_target_descriptors(binary, config, evaluator_path)
        write_json(_target_path(run_dir), target)
        advance(run_dir, manifest, TARGET_EVALUATED)
        _prepare_initial_boundary(run_dir, manifest, target)
        return run_dir
    except Exception as error:
        fail(run_dir, manifest, f"{type(error).__name__}: {error}")
        raise


def _provider_response(
    run_dir: Path, manifest: dict[str, Any], iteration: int
) -> str | None:
    provider = make_provider(manifest["llm_provider"])
    iteration_info = manifest["iterations"][str(iteration)]
    prompt_path = Path(iteration_info["prompt_path"])
    context = read_json(Path(iteration_info["prompt_context_path"]))
    context.update(
        {
            "response_path": iteration_info["response_path"],
            "model": manifest.get("model_name"),
        }
    )
    prompt = prompt_path.read_text(encoding="utf-8")
    if iteration == 0:
        response = provider.generate(prompt, run_dir / "reference" / "reference.png", context)
    else:
        response = provider.revise(prompt, context)
    if response is None:
        return None
    response_path = Path(iteration_info["response_path"])
    if not response_path.exists():
        # Future API-backed providers must preserve the raw model response just
        # as the manual-file provider does.
        response_path.write_text(response.text, encoding="utf-8")
    return response.text


def _record_generator(
    manifest: dict[str, Any], iteration: int, path: Path, digest: str, label: str
) -> None:
    info = manifest["iterations"][str(iteration)]
    info[f"{label}_path"] = str(path)
    info[f"{label}_sha256"] = digest
    info["active_generator_path"] = str(path)
    info["active_generator_sha256"] = digest
    hashes = manifest["iteration_generator_hashes"].setdefault(str(iteration), {})
    hashes[label] = digest


def _write_or_reuse_script(response: str, destination: Path) -> tuple[str, str]:
    """Recover an interrupted extraction only when every byte still agrees."""
    if not destination.exists():
        return write_new_script(response, destination)
    source = extract_python_script(response)
    digest = script_sha256(source)
    if destination.read_text(encoding="utf-8") != source:
        raise FileExistsError(
            f"Historical script differs from the current response: {destination}"
        )
    sidecar = destination.with_name(destination.stem + "_sha256.txt")
    if not sidecar.is_file() or sidecar.read_text(encoding="utf-8").strip() != digest:
        raise RuntimeError(f"Existing script hash record is missing or inconsistent: {sidecar}")
    return source, digest


def _completed_execution(log_dir: Path) -> dict[str, Any] | None:
    """Return a durable successful subprocess record, if one exists."""
    metadata_path = log_dir / "metadata.json"
    if not metadata_path.is_file():
        return None
    metadata = read_json(metadata_path)
    return metadata if metadata.get("succeeded") is True else None


def _make_repair_boundary(
    run_dir: Path,
    manifest: dict[str, Any],
    iteration: int,
    result: ExecutionResult,
) -> None:
    iteration_dir = _iteration_dir(run_dir, iteration)
    repair_prompt = iteration_dir / "repair_prompt.txt"
    if repair_prompt.exists():
        raise FileExistsError(f"Repair prompt already exists: {repair_prompt}")
    stderr = Path(result.stderr_path).read_text(encoding="utf-8")
    repair_prompt.write_text(build_execution_repair_prompt(stderr), encoding="utf-8")
    info = manifest["iterations"][str(iteration)]
    info["repair_prompt_path"] = str(repair_prompt)
    info["repair_response_path"] = str(iteration_dir / "repair_response.txt")
    manifest["execution_repairs"].setdefault(str(iteration), False)
    advance(
        run_dir,
        manifest,
        WAITING_FOR_EXECUTION_REPAIR,
        waiting_for=str(iteration_dir / "repair_response.txt"),
    )


def _execute_iteration(
    run_dir: Path,
    manifest: dict[str, Any],
    config: PipelineConfig,
    iteration: int,
    script_path: Path,
    *,
    repaired: bool,
) -> None:
    info = manifest["iterations"][str(iteration)]
    attempt = "repair" if repaired else "initial"
    manifest["execution_repairs"].setdefault(str(iteration), False)
    output_dir = _iteration_dir(run_dir, iteration) / "generated" / (
        "development_repair" if repaired else "development"
    )
    log_dir = _iteration_dir(run_dir, iteration) / "execution" / attempt
    _verify_protected_assets(run_dir, manifest, script_path)
    completed = _completed_execution(log_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        if completed is None:
            raise FileExistsError(
                "Generated output exists without a successful execution checkpoint; "
                f"refusing overwrite: {output_dir}"
            )
        info.setdefault("execution", {})[attempt] = completed
        manifest["iteration_execution_times_seconds"].setdefault(
            str(iteration), {}
        )[attempt] = completed["duration_seconds"]
        info["generated_development_path"] = str(output_dir)
        advance(run_dir, manifest, DEVELOPMENT_GENERATED, waiting_for=None)
        _evaluate_iteration(run_dir, manifest, config, iteration)
        return
    result = run_generator(
        script_path,
        seed_start=config.development_seeds[0],
        num_samples=len(config.development_seeds),
        output_dir=output_dir,
        log_dir=log_dir,
        timeout_seconds=config.generator_timeout_seconds,
    )
    _verify_protected_assets(run_dir, manifest, script_path)
    manifest["iteration_execution_times_seconds"].setdefault(str(iteration), {})[
        attempt
    ] = result.duration_seconds
    info.setdefault("execution", {})[attempt] = result.to_dict()
    save_manifest(run_dir, manifest)
    if not result.succeeded:
        if not repaired and not manifest["execution_repairs"].get(str(iteration), False):
            _make_repair_boundary(run_dir, manifest, iteration, result)
            return
        fail(
            run_dir,
            manifest,
            f"Generator iteration {iteration} failed after the allowed repair attempt.",
        )
        return
    info["generated_development_path"] = str(output_dir)
    advance(run_dir, manifest, DEVELOPMENT_GENERATED, waiting_for=None)
    _evaluate_iteration(run_dir, manifest, config, iteration)


def _evaluate_iteration(
    run_dir: Path,
    manifest: dict[str, Any],
    config: PipelineConfig,
    iteration: int,
) -> None:
    info = manifest["iterations"][str(iteration)]
    samples_dir = Path(info["generated_development_path"])
    evaluation_dir = _iteration_dir(run_dir, iteration) / "evaluation"
    try:
        report_path = evaluation_dir / "evaluation_summary.json"
        audit_path = evaluation_dir / "pipeline_seed_audit.json"
        if report_path.is_file() and audit_path.is_file():
            report = read_json(report_path)
            audit = read_json(audit_path)
            if not audit.get("passed") or report.get("sample_count") != len(
                config.development_seeds
            ):
                raise PipelineEvaluationError(
                    "Existing development evaluation checkpoint is inconsistent."
                )
        else:
            report, audit = run_v1_1_evaluation(
                samples_dir=samples_dir,
                reference_path=_reference_path(run_dir),
                output_dir=evaluation_dir,
                expected_seeds=config.development_seeds,
                config=config,
                evaluator_path=Path(manifest["evaluator_path"]),
            )
    except Exception as error:
        fail(
            run_dir,
            manifest,
            f"Development evaluation failed: {type(error).__name__}: {error}",
            recoverable_state=DEVELOPMENT_GENERATED,
        )
        return
    comparison = compare_to_target(_read_target(run_dir), report, len(config.development_seeds))
    comparison_path = evaluation_dir / "target_comparison.json"
    write_json(comparison_path, comparison)
    info["evaluation_path"] = str(evaluation_dir / "evaluation_summary.json")
    info["sample_audit_path"] = str(evaluation_dir / "pipeline_seed_audit.json")
    info["comparison_path"] = str(comparison_path)
    manifest["valid_sample_counts"][str(iteration)] = report["valid_sample_count"]
    manifest["actual_revisions_completed"] = iteration
    advance(run_dir, manifest, DEVELOPMENT_EVALUATED, waiting_for=None)

    if iteration < config.max_feedback_rounds:
        _prepare_revision_boundary(
            run_dir, manifest, config, iteration + 1, report, comparison
        )
    else:
        _freeze_final_generator(run_dir, manifest, config, iteration, report, audit)


def _prepare_revision_boundary(
    run_dir: Path,
    manifest: dict[str, Any],
    config: PipelineConfig,
    iteration: int,
    previous_report: dict[str, Any],
    comparison: dict[str, Any],
) -> None:
    iteration_dir = _iteration_dir(run_dir, iteration)
    iteration_dir.mkdir(parents=True, exist_ok=False)
    prompt_path = iteration_dir / f"prompt_{iteration}.txt"
    prompt_path.write_text(
        build_feedback_prompt(
            _read_target(run_dir),
            previous_report,
            comparison,
            round_number=iteration,
            max_rounds=config.max_feedback_rounds,
            development_count=len(config.development_seeds),
        ),
        encoding="utf-8",
    )
    previous_info = manifest["iterations"][str(iteration - 1)]
    _write_prompt_context(
        iteration_dir,
        target=_read_target(run_dir),
        iteration=iteration,
        development_report=previous_info["evaluation_path"],
        comparison=previous_info["comparison_path"],
    )
    manifest["iterations"][str(iteration)] = {
        "prompt_path": str(prompt_path),
        "prompt_context_path": str(iteration_dir / "prompt_context.json"),
        "response_path": str(iteration_dir / f"response_{iteration}.txt"),
        "generator_path": None,
        "active_generator_path": None,
        "active_generator_sha256": None,
        "generated_development_path": None,
        "evaluation_path": None,
        "comparison_path": None,
    }
    manifest["current_iteration"] = iteration
    advance(
        run_dir,
        manifest,
        WAITING_FOR_REVISION,
        waiting_for=str(iteration_dir / f"response_{iteration}.txt"),
    )


def _freeze_final_generator(
    run_dir: Path,
    manifest: dict[str, Any],
    config: PipelineConfig,
    iteration: int,
    development_report: dict[str, Any],
    development_audit: dict[str, Any],
) -> None:
    info = manifest["iterations"][str(iteration)]
    source = Path(info["active_generator_path"])
    expected_hash = info["active_generator_sha256"]
    if sha256_file(source) != expected_hash:
        raise RuntimeError("Final iteration script changed before freeze.")
    final_dir = run_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    destination = final_dir / "final_generator.py"
    if destination.exists():
        if sha256_file(destination) != expected_hash:
            raise FileExistsError("Existing frozen generator has a different hash.")
    else:
        shutil.copy2(source, destination)
    (final_dir / "generator_sha256.txt").write_text(expected_hash + "\n", encoding="utf-8")
    development_reference = final_dir / "development" / "reference.json"
    write_json(
        development_reference,
        {
            "generated_path": info["generated_development_path"],
            "evaluation_path": info["evaluation_path"],
            "sample_audit_path": info["sample_audit_path"],
            "source_iteration": iteration,
            "note": "Referenced rather than duplicated to preserve storage and provenance.",
        },
    )
    manifest["final_generator_hash"] = expected_hash
    manifest["final_generator_path"] = str(destination)
    manifest["final_generator_iteration"] = iteration
    manifest["final_development_metrics"] = development_report["ensemble_summary"]
    manifest["final_development_audit"] = development_audit
    advance(run_dir, manifest, FINAL_GENERATOR_FROZEN, waiting_for=None)
    _run_heldout(run_dir, manifest, config)


def _run_heldout(
    run_dir: Path, manifest: dict[str, Any], config: PipelineConfig
) -> None:
    final_script = Path(manifest["final_generator_path"])
    if sha256_file(final_script) != manifest["final_generator_hash"]:
        fail(run_dir, manifest, "Frozen generator hash changed before held-out execution.")
        return
    _verify_protected_assets(run_dir, manifest)
    output_dir = run_dir / "final" / "heldout" / "generated"
    log_dir = run_dir / "final" / "heldout" / "execution"
    completed = _completed_execution(log_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        if completed is None:
            fail(
                run_dir,
                manifest,
                "Held-out output exists without a successful execution checkpoint: "
                f"{output_dir}",
            )
            return
        result_record = completed
    else:
        result = run_generator(
            final_script,
            seed_start=config.heldout_seeds[0],
            num_samples=len(config.heldout_seeds),
            output_dir=output_dir,
            log_dir=log_dir,
            timeout_seconds=config.generator_timeout_seconds,
        )
        result_record = result.to_dict()
        if not result.succeeded:
            fail(run_dir, manifest, "Frozen generator failed on held-out seeds.")
            return
    if sha256_file(final_script) != manifest["final_generator_hash"]:
        fail(run_dir, manifest, "Frozen generator modified itself during held-out execution.")
        return
    manifest["heldout_execution"] = result_record
    manifest["heldout_execution_time_seconds"] = result_record["duration_seconds"]
    advance(run_dir, manifest, HELDOUT_GENERATED)
    _evaluate_heldout(run_dir, manifest, config)


def _evaluate_heldout(
    run_dir: Path, manifest: dict[str, Any], config: PipelineConfig
) -> None:
    output_dir = run_dir / "final" / "heldout" / "evaluation"
    try:
        report_path = output_dir / "evaluation_summary.json"
        audit_path = output_dir / "pipeline_seed_audit.json"
        if report_path.is_file() and audit_path.is_file():
            report = read_json(report_path)
            audit = read_json(audit_path)
            if not audit.get("passed") or report.get("sample_count") != len(
                config.heldout_seeds
            ):
                raise PipelineEvaluationError(
                    "Existing held-out evaluation checkpoint is inconsistent."
                )
        else:
            report, audit = run_v1_1_evaluation(
                samples_dir=run_dir / "final" / "heldout" / "generated",
                reference_path=_reference_path(run_dir),
                output_dir=output_dir,
                expected_seeds=config.heldout_seeds,
                config=config,
                evaluator_path=Path(manifest["evaluator_path"]),
            )
    except Exception as error:
        fail(
            run_dir,
            manifest,
            f"Held-out evaluation failed: {type(error).__name__}: {error}",
            recoverable_state=HELDOUT_GENERATED,
        )
        return
    manifest["final_heldout_metrics"] = report["ensemble_summary"]
    manifest["final_heldout_valid_sample_count"] = report["valid_sample_count"]
    manifest["heldout_audit"] = audit
    advance(run_dir, manifest, HELDOUT_EVALUATED)
    _finish_summary(run_dir, manifest, config, report, audit)


def _finish_summary(
    run_dir: Path,
    manifest: dict[str, Any],
    config: PipelineConfig,
    heldout_report: dict[str, Any],
    heldout_audit: dict[str, Any],
) -> None:
    reports: dict[int, dict[str, Any]] = {}
    audits: dict[str, dict[str, Any]] = {"heldout": heldout_audit}
    for iteration in range(config.max_feedback_rounds + 1):
        info = manifest["iterations"][str(iteration)]
        reports[iteration] = read_json(Path(info["evaluation_path"]))
        audits[f"iteration_{iteration}"] = read_json(Path(info["sample_audit_path"]))
    summary = build_final_summary(
        run_dir=run_dir,
        manifest=manifest,
        target=_read_target(run_dir),
        iteration_reports=reports,
        heldout_report=heldout_report,
        audits=audits,
        final_script=Path(manifest["final_generator_path"]),
        final_hash=manifest["final_generator_hash"],
        final_iteration=manifest["final_generator_iteration"],
        final_runtime_seconds=manifest["heldout_execution_time_seconds"],
    )
    manifest["final_summary_json"] = str(run_dir / "final" / "summary.json")
    manifest["final_summary_markdown"] = str(run_dir / "final" / "summary.md")
    manifest["completion_status"] = "complete"
    manifest["summary_warning_count"] = len(summary["warnings"])
    advance(run_dir, manifest, COMPLETE, waiting_for=None)


def _resume_waiting_for_model(
    run_dir: Path, manifest: dict[str, Any], config: PipelineConfig
) -> None:
    iteration = int(manifest["current_iteration"])
    response = _provider_response(run_dir, manifest, iteration)
    if response is None:
        return
    iteration_dir = _iteration_dir(run_dir, iteration)
    script_path = iteration_dir / f"iteration_{iteration}.py"
    try:
        _, digest = _write_or_reuse_script(response, script_path)
    except (ScriptExtractionError, FileExistsError) as error:
        fail(
            run_dir,
            manifest,
            f"Script extraction failed: {error}",
            recoverable_state=manifest["status"],
        )
        return
    _record_generator(manifest, iteration, script_path, digest, "generator")
    save_manifest(run_dir, manifest)
    _execute_iteration(
        run_dir, manifest, config, iteration, script_path, repaired=False
    )


def _resume_repair(
    run_dir: Path, manifest: dict[str, Any], config: PipelineConfig
) -> None:
    iteration = int(manifest["current_iteration"])
    info = manifest["iterations"][str(iteration)]
    response_path = Path(info["repair_response_path"])
    if not response_path.is_file():
        return
    script_path = _iteration_dir(run_dir, iteration) / "generator_repair.py"
    try:
        _, digest = _write_or_reuse_script(
            response_path.read_text(encoding="utf-8"), script_path
        )
    except (ScriptExtractionError, FileExistsError) as error:
        fail(
            run_dir,
            manifest,
            f"Repair script extraction failed: {error}",
            recoverable_state=WAITING_FOR_EXECUTION_REPAIR,
        )
        return
    manifest["execution_repairs"][str(iteration)] = True
    _record_generator(manifest, iteration, script_path, digest, "repair_generator")
    save_manifest(run_dir, manifest)
    _execute_iteration(
        run_dir, manifest, config, iteration, script_path, repaired=True
    )


def resume_run(run_dir: Path, *, retry_failed: bool = False) -> dict[str, Any]:
    """Advance a run from its durable manifest state until the next boundary."""
    run_dir = run_dir.resolve()
    manifest = load_manifest(run_dir)
    config = PipelineConfig.from_dict(manifest["configuration"])
    if manifest["status"] == COMPLETE:
        return manifest
    if manifest["status"] == FAILED:
        if not retry_failed or manifest.get("recoverable_state") is None:
            return manifest
        manifest["status"] = manifest["recoverable_state"]
        manifest["failure_reason"] = None
        manifest["recoverable_state"] = None
        save_manifest(run_dir, manifest)

    try:
        _verify_protected_assets(run_dir, manifest)
        status = manifest["status"]
        if status in (WAITING_FOR_INITIAL_LLM, WAITING_FOR_REVISION):
            _resume_waiting_for_model(run_dir, manifest, config)
        elif status == WAITING_FOR_EXECUTION_REPAIR:
            _resume_repair(run_dir, manifest, config)
        elif status == DEVELOPMENT_GENERATED:
            _evaluate_iteration(
                run_dir, manifest, config, int(manifest["current_iteration"])
            )
        elif status == FINAL_GENERATOR_FROZEN:
            _run_heldout(run_dir, manifest, config)
        elif status == HELDOUT_GENERATED:
            _evaluate_heldout(run_dir, manifest, config)
        elif status == HELDOUT_EVALUATED:
            heldout_path = run_dir / "final" / "heldout" / "evaluation"
            _finish_summary(
                run_dir,
                manifest,
                config,
                read_json(heldout_path / "evaluation_summary.json"),
                read_json(heldout_path / "pipeline_seed_audit.json"),
            )
        else:
            raise RuntimeError(f"Run cannot resume from state {status!r}.")
    except Exception as error:
        fail(
            run_dir,
            manifest,
            f"{type(error).__name__}: {error}",
            recoverable_state=manifest.get("status")
            if manifest.get("status") not in (FAILED, COMPLETE)
            else None,
        )
    return load_manifest(run_dir)


def status_message(run_dir: Path) -> str:
    manifest = load_manifest(run_dir.resolve())
    lines = [
        f"Run: {manifest['run_id']}",
        f"Status: {manifest['status']}",
        f"Current iteration: {manifest['current_iteration']}",
    ]
    waiting = manifest.get("waiting_for")
    if waiting:
        lines.extend(["Waiting for LLM response:", f"  {waiting}"])
    if manifest.get("failure_reason"):
        lines.append(f"Failure: {manifest['failure_reason']}")
        if manifest.get("recoverable_state"):
            lines.append(
                "Recoverable after correcting the recorded problem; use "
                "resume --retry-failed."
            )
    if manifest["status"] == COMPLETE:
        lines.append(f"Summary: {manifest['final_summary_markdown']}")
    return "\n".join(lines)
