"""Independent Douglas–Peucker experiments with immutable saved baselines."""
import math
import numbers
import shapely


def validate_epsilon(value):
    if isinstance(value,bool) or not isinstance(value,numbers.Real) or not math.isfinite(value) or value < 0:
        raise ValueError('epsilon must be a finite nonnegative real in native cell units.')
    return float(value)


def simplify_diagnostic(baseline,epsilon,*,preserve_topology=True):
    epsilon=validate_epsilon(epsilon)
    if not isinstance(preserve_topology,bool):
        raise ValueError('preserve_topology must be explicit bool.')
    if epsilon==0:
        return shapely.from_wkb(shapely.to_wkb(baseline,byte_order=1))
    return shapely.simplify(baseline,tolerance=epsilon,preserve_topology=preserve_topology)
