"""Command-line interface for the resumable Pipeline v0.1 workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import (
    EVALUATOR_TIMEOUT_SECONDS,
    GENERATOR_TIMEOUT_SECONDS,
    MAX_FEEDBACK_ROUNDS,
    PipelineConfig,
    default_evaluator_path,
    default_runs_root,
)
from .runner import resume_run, start_run, status_message
from .state import FAILED


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="young-dawgs-pipeline",
        description=(
            "Create and resume reproducible I2F1 binary-microstructure runs "
            "using frozen evaluator v1.1."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser(
        "start", help="Canonicalize a reference and create the initial I2 prompt."
    )
    start.add_argument("reference", type=Path, help="Strict binary .npy or .png reference.")
    start.add_argument("--run-name", help="Run identifier; generated from UTC time if omitted.")
    start.add_argument(
        "--runs-root",
        type=Path,
        default=default_runs_root(),
        help="Root directory for pipeline runs (default: %(default)s).",
    )
    start.add_argument(
        "--threshold",
        type=float,
        help="Explicit [0,1] threshold for an ambiguous grayscale PNG.",
    )
    start.add_argument(
        "--provider",
        default="manual-file",
        choices=("manual-file",),
        help="LLM response provider (default: %(default)s).",
    )
    start.add_argument("--model", help="Optional model name recorded in the manifest.")
    start.add_argument(
        "--max-feedback-rounds",
        type=int,
        default=MAX_FEEDBACK_ROUNDS,
        help="Maximum revisions after iteration 0 (default: %(default)s).",
    )
    start.add_argument(
        "--generator-timeout",
        type=float,
        default=GENERATOR_TIMEOUT_SECONDS,
        help="Generator timeout in seconds (default: %(default)s).",
    )
    start.add_argument(
        "--evaluator-timeout",
        type=float,
        default=EVALUATOR_TIMEOUT_SECONDS,
        help="Evaluator timeout in seconds (default: %(default)s).",
    )
    start.add_argument(
        "--evaluator",
        type=Path,
        default=default_evaluator_path(),
        help="Frozen evaluator v1.1 path (default: %(default)s).",
    )

    status = subparsers.add_parser("status", help="Show the next action for an existing run.")
    status.add_argument("run_dir", type=Path, help="Run directory containing manifest.json.")

    resume = subparsers.add_parser(
        "resume", help="Advance an existing run to its next manual boundary."
    )
    resume.add_argument("run_dir", type=Path, help="Run directory containing manifest.json.")
    resume.add_argument(
        "--retry-failed",
        action="store_true",
        help="Retry a recoverable failed stage after correcting its recorded cause.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            config = PipelineConfig(
                max_feedback_rounds=args.max_feedback_rounds,
                generator_timeout_seconds=args.generator_timeout,
                evaluator_timeout_seconds=args.evaluator_timeout,
            )
            run_dir = start_run(
                args.reference,
                run_name=args.run_name,
                runs_root=args.runs_root,
                threshold=args.threshold,
                provider_name=args.provider,
                model_name=args.model,
                config=config,
                evaluator_path=args.evaluator,
            )
            print(status_message(run_dir))
            print(f"Run directory: {run_dir}")
            return 0
        if args.command == "status":
            print(status_message(args.run_dir))
            return 0
        manifest = resume_run(args.run_dir, retry_failed=args.retry_failed)
        print(status_message(args.run_dir))
        return 2 if manifest["status"] == FAILED else 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"pipeline error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
