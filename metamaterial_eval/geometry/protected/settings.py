"""Prospective protocol, never a production default substituted into old code."""
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PROTOCOL = 'docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_PROTOCOL.json'


def settings():
    return json.loads((ROOT / PROTOCOL).read_text())


def tolerance(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError('Tolerance must be a finite nonnegative real number, not bool.')
    return float(value)
