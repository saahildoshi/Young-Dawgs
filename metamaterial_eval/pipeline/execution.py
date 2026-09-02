"""Isolated subprocess execution with durable logs and bounded runtime."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from .state import utc_now, write_json


@dataclass(frozen=True)
class ExecutionResult:
    command: list[str]
    return_code: int | None
    timed_out: bool
    started_at_utc: str
    ended_at_utc: str
    duration_seconds: float
    stdout_path: str
    stderr_path: str

    @property
    def succeeded(self) -> bool:
        return not self.timed_out and self.return_code == 0

    def to_dict(self) -> dict[str, object]:
        value = asdict(self)
        value["succeeded"] = self.succeeded
        return value


def _decode(value: str | bytes | None) -> str:
    if value is None:
        return ""
    return value.decode("utf-8", errors="replace") if isinstance(value, bytes) else value


def run_subprocess(
    command: Sequence[str],
    *,
    cwd: Path,
    log_dir: Path,
    timeout_seconds: float,
) -> ExecutionResult:
    """Run a command and always persist stdout, stderr, and metadata."""
    log_dir.mkdir(parents=True, exist_ok=True)
    started_at = utc_now()
    start = time.monotonic()
    return_code: int | None = None
    timed_out = False
    stdout = ""
    stderr = ""
    environment = os.environ.copy()
    environment["PYTHONNOUSERSITE"] = "1"
    try:
        completed = subprocess.run(
            list(command),
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except subprocess.TimeoutExpired as error:
        timed_out = True
        stdout = _decode(error.stdout)
        stderr = _decode(error.stderr)
        stderr += (
            "\n" if stderr and not stderr.endswith("\n") else ""
        ) + f"Process exceeded timeout of {timeout_seconds:.3f} seconds.\n"

    duration = time.monotonic() - start
    stdout_path = log_dir / "stdout.txt"
    stderr_path = log_dir / "stderr.txt"
    stdout_path.write_text(stdout, encoding="utf-8")
    stderr_path.write_text(stderr, encoding="utf-8")
    result = ExecutionResult(
        command=list(command),
        return_code=return_code,
        timed_out=timed_out,
        started_at_utc=started_at,
        ended_at_utc=utc_now(),
        duration_seconds=duration,
        stdout_path=str(stdout_path),
        stderr_path=str(stderr_path),
    )
    write_json(log_dir / "metadata.json", result.to_dict())
    return result


def run_generator(
    script_path: Path,
    *,
    seed_start: int,
    num_samples: int,
    output_dir: Path,
    log_dir: Path,
    timeout_seconds: float,
) -> ExecutionResult:
    """Execute a generated script under the Pipeline Prompt v1.0 CLI contract."""
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(script_path.resolve()),
        "--seed-start",
        str(seed_start),
        "--num-samples",
        str(num_samples),
        "--output-dir",
        str(output_dir.resolve()),
    ]
    return run_subprocess(
        command,
        cwd=script_path.parent,
        log_dir=log_dir,
        timeout_seconds=timeout_seconds,
    )

