"""Command-line interface for the resumable, versioned pipeline workflow."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import (
    EVALUATOR_TIMEOUT_SECONDS,
    GENERATOR_TIMEOUT_SECONDS,
    MAX_FEEDBACK_ROUNDS,
    TOPOLOGY_MODES,
    PipelineConfig,
    default_evaluator_path,
    default_runs_root,
)
from .runner import resume_run, start_run, status_message
from .preparation import prepare_reference
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
    rv = subparsers.add_parser("resolution-validate", help="Run a separate matched v0.3/v0.4 native-resolution validation.")
    rv.add_argument("source_run", type=Path)
    rv.add_argument("--output-dir", type=Path, required=True)
    rv.add_argument("--resolutions", type=int, nargs="+", default=[256, 512, 1024])
    rv.add_argument("--designs", type=int, default=5)
    rv.add_argument("--timeout", type=float, default=600)
    rg = subparsers.add_parser("resolution-generate", help="Generate one native-resolution structure with the audited v0.4 model.")
    rg.add_argument("--seed", type=int, required=True)
    rg.add_argument("--solid-fraction-target", type=float, required=True)
    rg.add_argument("--strut-scale", type=float, required=True)
    rg.add_argument("--pore-scale", type=float, required=True)
    rg.add_argument("--resolution", type=int, default=256)
    rg.add_argument("--output-dir", type=Path, required=True)
    explore = subparsers.add_parser("explore-start", help="Plan a separate parametric exploration experiment.")
    explore.add_argument("reference", type=Path)
    explore.add_argument("--output-dir", type=Path, required=True)
    explore.add_argument("--s2-limit", type=float, required=True)
    explore.add_argument("--lineal-limit", type=float, required=True)
    explore.add_argument("--bounds", type=Path, help="JSON object with all three control bounds.")
    explore.add_argument("--designs", type=int, default=10)
    explore.add_argument("--replicates", type=int, default=2)
    explore.add_argument("--design-seed", type=int, default=42)
    explore.add_argument("--seed-start", type=int, default=0)
    explore.add_argument("--prepare-png", action="store_true")
    explore.add_argument("--threshold", type=float)
    explore.add_argument("--generator-timeout", type=float, default=GENERATOR_TIMEOUT_SECONDS)
    er = subparsers.add_parser("explore-resume", help="Execute a reviewed parameterized generator and measure designs.")
    er.add_argument("run_dir", type=Path)
    er.add_argument("--execute", action="store_true", help="Acknowledge execution of reviewed, unsandboxed Python.")
    er.add_argument("--retry-failed", action="store_true")
    es = subparsers.add_parser("explore-status", help="Read an exploration manifest.")
    es.add_argument("run_dir", type=Path)
    prepare = subparsers.add_parser(
        "prepare-reference", help="Save raw/structural references, descriptors and prompt preview."
    )
    prepare.add_argument("reference", type=Path)
    prepare.add_argument("--output-dir", required=True, type=Path)
    prepare.add_argument("--topology-mode", choices=TOPOLOGY_MODES, default="preserve_reference")
    prepare.add_argument("--prepare-png", action="store_true")
    prepare.add_argument("--threshold", type=float)

    start = subparsers.add_parser(
        "start", help="Canonicalize a reference and create the initial I2 prompt."
    )
    start.add_argument("reference", type=Path, help="Strict binary .npy or .png reference.")
    start.add_argument(
        "--prepare-png",
        action="store_true",
        help="Convert a raw PNG to grayscale, threshold, and resize to 256 x 256.",
    )
    start.add_argument("--run-name", help="Run identifier; generated from UTC time if omitted.")
    start.add_argument(
        "--topology-mode", choices=TOPOLOGY_MODES, default="preserve_reference",
        help="single_connected_network keeps the largest reference component and requires "
             "one spanning solid component in every sample; default preserves the reference.",
    )
    start.add_argument(
        "--runs-root",
        type=Path,
        default=default_runs_root(),
        help="Root directory for pipeline runs (default: %(default)s).",
    )
    start.add_argument(
        "--threshold",
        type=float,
        help="PNG threshold in [0,1]; defaults to 0.5 with --prepare-png.",
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
        if args.command == "resolution-validate":
            from .resolution_validation import validate_resolutions
            m = validate_resolutions(args.source_run, args.output_dir, args.resolutions, args.designs, args.timeout)
            print(f"Validation execution: {m['status']}. Read summary/resolution_convergence.md for scientific gates.")
            return 0 if m["status"] == "COMPLETE" else 2
        if args.command == "resolution-generate":
            from .resolution_worker import perform_job
            from .resolution import validate_resolution
            result = perform_job({"seed": args.seed, "resolution": validate_resolution(args.resolution),
                                  "requested": {"solid_fraction_target": args.solid_fraction_target,
                                                "strut_scale": args.strut_scale, "pore_scale": args.pore_scale}},
                                 args.output_dir.resolve())
            print(f"Native generation: {result['status']}. Output: {args.output_dir.resolve()}")
            return 0 if result["status"] == "COMPLETE" else 2
        if args.command.startswith("explore-"):
            import json
            from .exploration import start_exploration, resume_exploration, load_exploration
            from .state import read_json
            if args.command == "explore-start":
                run = start_exploration(
                    args.reference, args.output_dir, s2_limit=args.s2_limit,
                    lineal_limit=args.lineal_limit, bounds=read_json(args.bounds) if args.bounds else None,
                    designs=args.designs, replicates=args.replicates, design_seed=args.design_seed,
                    seed_start=args.seed_start, prepare_png=args.prepare_png, threshold=args.threshold,
                    timeout=args.generator_timeout)
                print(f"Exploration prepared: {run}\nSend prompt.txt and reference/reference_structural.png to the LLM; save response.txt.")
                return 0
            manifest = (load_exploration(args.run_dir) if args.command == "explore-status" else
                        resume_exploration(args.run_dir, execute=args.execute, retry_failed=args.retry_failed))
            print(json.dumps(manifest, indent=2))
            return 2 if manifest["status"] == "FAILED" else 0
        if args.command == "prepare-reference":
            metadata = prepare_reference(
                args.reference, args.output_dir,
                config=PipelineConfig(topology_mode=args.topology_mode),
                threshold=args.threshold, prepare_png=args.prepare_png,
            )
            cleaning = metadata["cleaning"]
            print(f"Prepared reference: {args.output_dir.resolve()}")
            print(f"Solid components: {cleaning['raw_component_count']} raw; "
                  f"{cleaning['retained_component_count']} retained")
            print(f"Removed solid pixels: {cleaning['removed_solid_pixels']}")
            for warning in cleaning["warnings"]:
                print(f"Warning: {warning}")
            return 0
        if args.command == "start":
            config = PipelineConfig(
                topology_mode=args.topology_mode,
                max_feedback_rounds=args.max_feedback_rounds,
                generator_timeout_seconds=args.generator_timeout,
                evaluator_timeout_seconds=args.evaluator_timeout,
            )
            run_dir = start_run(
                args.reference,
                run_name=args.run_name,
                runs_root=args.runs_root,
                threshold=args.threshold,
                prepare_png=args.prepare_png,
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
