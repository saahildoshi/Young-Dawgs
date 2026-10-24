"""Positive-compression definitions and validity gates; no solver emulation."""
import numpy as np


def compression_metrics(top_uy, upper_rf, lower_rf, config):
    uy,upper,lower=np.broadcast_arrays(np.asarray(top_uy,float),np.asarray(upper_rf,float),np.asarray(lower_rf,float))
    if not np.isfinite([uy,upper,lower]).all():raise ValueError('Nonfinite mechanical data')
    if np.any(uy>1e-10) or np.any(upper<-1e-8) or np.any(lower>1e-8):
        raise ValueError('Unexpected displacement or reaction sign; do not silently take absolute values')
    strain=-uy/config.height
    stress=upper/(config.width*config.thickness)
    balance=np.abs(upper+lower)/np.maximum(np.maximum(np.abs(upper),np.abs(lower)),1e-12)
    return {'compression_displacement_mm':-uy,'engineering_compression_strain':strain,
            'nominal_compression_stress_MPa':stress,'force_balance_relative':balance,
            'force_balance_pass':bool(np.all(balance<=.01))}


def effective_stiffness(strain,stress,base_modulus):
    strain,stress=np.asarray(strain,float),np.asarray(stress,float)
    if strain.shape!=stress.shape or not np.isfinite([strain,stress]).all():raise ValueError('Invalid curve arrays')
    chosen=(strain>0)&(strain<=.005+1e-12)
    if chosen.sum()<2:return {'value_MPa':None,'normalized':None,'status':'INSUFFICIENT_ACHIEVED_SMALL_STRAIN_POINTS'}
    x,y=strain[chosen],stress[chosen]
    slope=float(x@y/(x@x))
    return {'value_MPa':slope,'normalized':slope/base_modulus,'status':'COMPUTED',
            'method':'least_squares_through_origin','strain_interval':[0,.005],
            'points':int(chosen.sum())}


def selected_snapshots(achieved_strains):
    values=np.asarray(achieved_strains,float)
    if not len(values):return {}
    result={'first_nonzero':next((int(i) for i,v in enumerate(values) if v>0),None),'last_converged':len(values)-1}
    for name,target in [('one_percent',.01),('two_percent',.02)]:
        ids=np.flatnonzero(np.isclose(values,target,atol=1e-6,rtol=0))
        result[name]=int(ids[-1]) if len(ids) else None
    return result


def convergence_report(curves, tolerance=.05):
    """Compare matched achieved strains; never interpolate through failed stages."""
    if len(curves)<3:return {'status':'NOT_QUALIFIED','reason':'Require three actual solved refinement levels'}
    records=[]
    for a,b in zip(curves[:-1],curves[1:]):
        if a.get('validity')!='VALID_SOLVER_MEASUREMENTS' or b.get('validity')!='VALID_SOLVER_MEASUREMENTS':
            return {'status':'NOT_QUALIFIED','reason':'Invalid or unexecuted curve'}
        if a['model_fingerprint']!=b['model_fingerprint']:
            return {'status':'NOT_QUALIFIED','reason':'Geometry, material, contact or loading changed'}
        x,y=np.asarray(a['strain']),np.asarray(a['stress']);xx,yy=np.asarray(b['strain']),np.asarray(b['stress'])
        if x.shape!=xx.shape or not np.allclose(x,xx,atol=1e-8,rtol=0):
            return {'status':'NOT_QUALIFIED','reason':'Unmatched achieved strain stages'}
        if not len(x) or np.any(x<=0):return {'status':'NOT_QUALIFIED','reason':'Need nonzero achieved stages'}
        change=float(np.max(np.abs(y-yy)/np.maximum(np.abs(yy),1e-12)))
        records.append({'max_relative_stress_change':change,'passed':change<=tolerance})
    return {'status':'PASS_GLOBAL_RESPONSE' if all(r['passed'] for r in records) else 'HOLD_GLOBAL_RESPONSE',
            'pairs':records,'tolerance':tolerance,'peak_local_stress':'SEPARATE_UNQUALIFIED'}
