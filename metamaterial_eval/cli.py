"""Command-line interface for the metamaterial evaluation package."""

from __future__ import annotations

import argparse
from pathlib import Path

from .evaluation import evaluate_generator_output, make_target_dict
from .io import load_binary, prepare_target


def _shape(value: str) -> tuple[int, int]:
    try:
        height, width = (int(part) for part in value.lower().split("x", maxsplit=1))
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("Shape must use HEIGHTxWIDTH.") from exc
    if height <= 0 or width <= 0:
        raise argparse.ArgumentTypeError("Shape dimensions must be positive.")
    return height, width


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="metamaterial-eval",
        description="Evaluate 2-D binary procedural metamaterial generators.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Prepare a binary target.")
    prepare.add_argument("image", type=Path)
    prepare.add_argument("--threshold", type=float, default=0.5)
    prepare.add_argument("--shape", type=_shape, default=(256, 256))

    evaluate = subparsers.add_parser(
        "evaluate", help="Evaluate a sample folder or a single sample file."
    )
    evaluate.add_argument("target", type=Path, help="Target PNG or NPY file.")
    evaluate.add_argument("samples_folder", type=Path, help="Sample file or folder.")
    evaluate.add_argument("--threshold", type=float, default=0.5)
    evaluate.add_argument("--shape", type=_shape, default=(256, 256))
    evaluate.add_argument("--max-r", type=int, default=64)
    evaluate.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "directory for metrics_report.json and metrics_report.txt; "
            "defaults to the sample directory"
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "prepare":
        binary = prepare_target(args.image, args.threshold, args.shape)
        output_stem = args.image.with_name(f"{args.image.stem}_binary")
        print(f"Prepared {binary.shape[0]}x{binary.shape[1]} target.")
        print(f"PNG: {output_stem.with_suffix('.png')}")
        print(f"NPY: {output_stem.with_suffix('.npy')}")
        return

    target = load_binary(
        args.target, threshold=args.threshold, expected_shape=args.shape
    )
    target_dict = make_target_dict(target, max_r=args.max_r)
    report = evaluate_generator_output(
        target_dict,
        args.samples_folder,
        output_dir=args.output_dir,
    )
    output_dir = args.output_dir or (
        args.samples_folder.parent
        if args.samples_folder.is_file()
        else args.samples_folder
    )
    print(
        f"Evaluated {report['evaluated_sample_count']} samples; "
        f"{report['valid_sample_count']} valid."
    )
    print(f"JSON: {output_dir / 'metrics_report.json'}")
    print(f"Text: {output_dir / 'metrics_report.txt'}")


if __name__ == "__main__":
    main()
