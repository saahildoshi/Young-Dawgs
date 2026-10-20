# Verification record

- Full package regression suite: **100 passed**.
- Frozen evaluator scientific acceptance suite: **56 passed**.
- Three unit-regression fixtures match saved v0.3 Windows pixel hashes exactly.
- Full experiment regression: **10/10** selected 256 arrays match both old
  generator and saved historical images bitwise.
- Exact repeatability checked at every successfully generated design/seed/N.
- Historical experiment file inventory is unchanged before/after validation.
- Frozen evaluator SHA-256 remains
  `5f28ed1f77f95fd23a517cd223bbe6c6b5edc7d5508093f36f523b2d4f85cebb`.
- `git diff --check` found no whitespace errors in changed source/documentation.
- Native montage/crop, normalized-metric and parameter-control plots were
  visually inspected.

Local verification used an isolated macOS Python 3.10 environment with NumPy
1.26.4 and SciPy 1.13.1. Exact per-output library versions are in manifests.
The earlier macOS SciPy 1.15.3 wheel could not load; the user's Windows environment
was not modified. No new Windows run or Windows CI result is claimed.

Tests passing mean the code honors its contracts, including rejecting an invalid
native realization. They do NOT mean all convergence acceptance criteria passed.
The real experiment has two rejected topology cases and failed thickness
targets; see `resolution_convergence.md` and `IMPLEMENTATION_HANDOFF.md`.
