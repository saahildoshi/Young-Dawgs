"""Quantitative evaluation tools for 2-D binary mechanical metamaterials."""

from .evaluation import evaluate_generator_output, make_target_dict
from .io import load_binary, prepare_target
from .metrics import (
    compute_basic_metrics,
    compute_lineal_path,
    compute_local_dimensions,
    compute_s2_correlation,
)

__all__ = [
    "prepare_target",
    "load_binary",
    "compute_basic_metrics",
    "compute_s2_correlation",
    "compute_lineal_path",
    "compute_local_dimensions",
    "make_target_dict",
    "evaluate_generator_output",
]

__version__ = "0.1.0"
