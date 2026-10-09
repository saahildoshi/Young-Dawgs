"""Reproducible exploration plans; requested controls are not achieved metrics."""

from __future__ import annotations

import math
from typing import Any

from scipy.stats import qmc

CONTROLS = {
    "solid_fraction_target": ("phi_s", 0.10),
    "strut_scale": ("mean_strut_thickness", 0.15),
    "pore_scale": ("median_pore_diameter", 0.20),
}


def make_plan(target: dict[str, Any], *, bounds: dict | None = None,
              designs: int = 10, replicates: int = 2, design_seed: int = 42,
              seed_start: int = 0, s2_limit: float, lineal_limit: float) -> dict:
    """Latin hypercube with common random seeds across designs.

    The fractional widths are development heuristics, not scientific acceptance
    standards. Explicit bounds must provide all three controls. Morphology-family
    error limits must be supplied by the operator, not inferred from the target.
    """
    if designs < 2 or replicates < 1 or seed_start < 0 or design_seed < 0:
        raise ValueError("Require >=2 designs, >=1 replicate, and nonnegative seeds.")
    for limit in (s2_limit, lineal_limit):
        if not math.isfinite(limit) or limit < 0:
            raise ValueError("Family limits must be finite and nonnegative.")
    if bounds is None:
        bounds = {}
        for name, (metric, width) in CONTROLS.items():
            center = target[metric]
            if center is None or not math.isfinite(center) or center <= 0:
                raise ValueError(f"Undefined/nonpositive {metric}; supply explicit bounds JSON.")
            bounds[name] = [center * (1 - width), center * (1 + width)]
        bounds["solid_fraction_target"][1] = min(bounds["solid_fraction_target"][1], 0.999)
    if set(bounds) != set(CONTROLS):
        raise ValueError(f"Bounds must contain exactly: {list(CONTROLS)}")
    for name, limits in bounds.items():
        if (not isinstance(limits, (list, tuple)) or len(limits) != 2
                or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in limits)
                or not 0 < limits[0] < limits[1]):
            raise ValueError(f"Invalid positive [lower, upper] bounds for {name}.")
    if bounds["solid_fraction_target"][1] >= 1:
        raise ValueError("Solid fraction bounds must be strictly between 0 and 1.")
    unit = qmc.LatinHypercube(d=len(CONTROLS), seed=design_seed).random(n=designs)
    rows = []
    for i, values in enumerate(unit):
        params = {name: float(bounds[name][0] + u * (bounds[name][1] - bounds[name][0]))
                  for name, u in zip(CONTROLS, values)}
        for rep in range(replicates):
            rows.append({"sample_id": f"design_{i:03d}_rep_{rep:02d}",
                         "design_id": i, "replicate": rep, "seed": seed_start + rep,
                         "requested": params.copy()})
    return {"schema_version": 1, "sampler": "scipy.stats.qmc.LatinHypercube",
            "design_seed": design_seed, "design_count": designs,
            "replicates": replicates, "bounds": bounds,
            "seed_policy": "common random seeds across designs; distinct seeds within design",
            "bounds_interpretation": "development envelope, not independently guaranteed feasible",
            "family_limits": {"E_S2": s2_limit, "E_L": lineal_limit}, "samples": rows}
