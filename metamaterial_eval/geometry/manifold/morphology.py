"""Unchanged frozen-v1.1 descriptors, kept separate from continuous metrics."""
import numpy as np
from ...pipeline.resolution_worker import evaluate_native


def compare_frozen(original,reconstructed):
    # Evaluate both arrays independently even when their occupancy is identical.
    a=evaluate_native(original);b=evaluate_native(reconstructed)
    scalars=('phi_s','component_count','f_largest','Px','Py','mean_strut_thickness','p10_strut_thickness','median_pore_diameter')
    values={}
    for k in scalars:
        x,y=a['raw'][k],b['raw'][k]
        equal=x==y or (x is None and y is None)
        values[k]={'original':x,'candidate':y,'difference':float(y-x) if x is not None and y is not None else None,'equal':bool(equal)}
    curves={}
    for k in ('s2','lineal_path','l_x','l_y','l_45','l_135'):
        x=np.asarray(a['raw']['curves'][k]);y=np.asarray(b['raw']['curves'][k])
        curves[k]={'maximum_absolute_difference':float(np.max(np.abs(y-x))), 'exact_equal':bool(np.array_equal(x,y)),
                   'original':x.tolist(),'candidate':y.tolist()}
    return {'status':'PASS' if all(x['equal'] for x in values.values()) and all(x['exact_equal'] for x in curves.values()) else 'FAIL',
            'scalars':values,'curves':curves,'evaluator_sha256':a['raw']['evaluator_sha256'],
            'raster_exact':bool(np.array_equal(original,reconstructed)),
            'continuous_equivalence_established':False,
            'p10_caveat':'Frozen whole-mask P10 is unchanged. v0.4.3 qualification applies only within its tested tail/neck domain; original v0.4.2 calibration remains FAILED.'}
