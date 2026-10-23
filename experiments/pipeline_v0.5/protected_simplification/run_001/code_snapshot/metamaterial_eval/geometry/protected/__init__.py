"""Explicit opt-in, experimentally qualified feature-protected geometry."""
from .engine import simplify_protected
from .guards import build_guards, prepare_risks

__all__ = ['simplify_protected', 'build_guards', 'prepare_risks']
