"""Manifest persistence and pipeline states."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CREATED = "CREATED"
REFERENCE_READY = "REFERENCE_READY"
TARGET_EVALUATED = "TARGET_EVALUATED"
WAITING_FOR_INITIAL_LLM = "WAITING_FOR_INITIAL_LLM"
WAITING_FOR_REVISION = "WAITING_FOR_REVISION"
WAITING_FOR_EXECUTION_REPAIR = "WAITING_FOR_EXECUTION_REPAIR"
DEVELOPMENT_GENERATED = "DEVELOPMENT_GENERATED"
DEVELOPMENT_EVALUATED = "DEVELOPMENT_EVALUATED"
FINAL_GENERATOR_FROZEN = "FINAL_GENERATOR_FROZEN"
HELDOUT_GENERATED = "HELDOUT_GENERATED"
HELDOUT_EVALUATED = "HELDOUT_EVALUATED"
COMPLETE = "COMPLETE"
FAILED = "FAILED"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def manifest_path(run_dir: Path) -> Path:
    return run_dir / "manifest.json"


def write_json(path: Path, value: Any) -> None:
    """Atomically write strict, indented JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return value


def load_manifest(run_dir: Path) -> dict[str, Any]:
    path = manifest_path(run_dir)
    if not path.is_file():
        raise FileNotFoundError(f"Run manifest not found: {path}")
    return read_json(path)


def save_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at_utc"] = utc_now()
    write_json(manifest_path(run_dir), manifest)


def advance(
    run_dir: Path,
    manifest: dict[str, Any],
    status: str,
    **updates: Any,
) -> None:
    manifest.update(updates)
    manifest["status"] = status
    manifest["failure_reason"] = None
    manifest["recoverable_state"] = None
    save_manifest(run_dir, manifest)


def fail(
    run_dir: Path,
    manifest: dict[str, Any],
    reason: str,
    *,
    recoverable_state: str | None = None,
) -> None:
    manifest["status"] = FAILED
    manifest["completion_status"] = "failed"
    manifest["failure_reason"] = reason
    manifest["recoverable_state"] = recoverable_state
    save_manifest(run_dir, manifest)
