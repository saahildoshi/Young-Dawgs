"""Frozen P3/F1 categorical pilot observations; no physical calibration."""
import itertools
import numpy as np
from .descriptors import describe as describe_binary
from .diversity import diversity
from .transverse import describe_transverse

LABELS = {'P3': (1, 5), 'F1': (0, 1, 2)}
SCALES = {
    'P3': {'reinforcement_fraction': .2, 'complete_regions': 60, 'diameter_mean_px': 20,
           'diameter_std_px': 15, 'aspect_mean': 1.5, 'nearest_neighbor_mean_px': 20,
           'nearest_neighbor_cv': 1, 'interface_density': .15, 'S2_x_8': .2, 'S2_y_8': .2, 'matrix_lcc': .25},
    'F1': {'fiber_fraction': .2, 'void_fraction': .05, 'complete_fiber_regions': 600,
           'fiber_diameter_mean_px': 6, 'fiber_diameter_std_px': 6, 'fiber_nearest_neighbor_mean_px': 10,
           'fiber_S2_x_8': .2, 'fiber_S2_y_8': .2, 'matrix_fiber_interface': .25,
           'matrix_lcc': .25, 'void_regions': 10, 'void_diameter_mean_px': 20, 'void_S2_x_8': .05}}
VISIBLE = {'P3': list(SCALES['P3'])[:5], 'F1': list(SCALES['F1'])[:5]}
HIDDEN = {f: [k for k in SCALES[f] if k not in VISIBLE[f]] for f in LABELS}


def validate(a, family):
    if family not in LABELS:
        raise ValueError('Unknown reference family')
    if not isinstance(a, np.ndarray) or a.shape != (256,256) or a.dtype != np.uint8:
        raise ValueError('Expected256x256 uint8 ndarray')
    if not np.isin(a, LABELS[family]).all():
        raise ValueError(f'Unexpected categorical labels; required schema {LABELS[family]}')
    return a


def validity(a, family):
    try:
        validate(a, family)
    except ValueError as e:
        return {'passed':False, 'failures':[str(e)]}
    absent = [k for k in LABELS[family] if not np.any(a == k)]
    return {'passed':not absent, 'failures':[f'Expected nonempty phase absent: {k}' for k in absent],
            'definition':'Output schema and presence of target phases only; connectivity, size and fraction mismatches are observations, not hard failures'}


def describe(a, family):
    validate(a, family)
    if family == 'P3':
        # Explicit derived working map: native1->0 matrix, native5->1 provisional carbide.
        d = describe_binary((a == 5).astype(np.uint8), 'particle')
        return {'reinforcement_fraction':d['fraction'], 'complete_regions':d['complete_objects'],
                **{k:d[k] for k in ['diameter_mean_px','diameter_std_px','aspect_mean','nearest_neighbor_mean_px',
                                    'nearest_neighbor_cv','interface_density','S2_x_8','S2_y_8','matrix_lcc']},
                'all_regions':d['object_count'], 'boundary_censored_regions':d['boundary_censored_objects'],
                'working_map':{'1':0,'5':1}, 'detail':d}
    d = describe_transverse(a)
    fiber, void, matrix = [d['phases'][k] for k in ['fiber','void','matrix']]
    fr, vr = fiber['regions'], void['regions']
    return {'fiber_fraction':fiber['fraction'], 'void_fraction':void['fraction'],
            'complete_fiber_regions':fr['complete_region_count'],
            'fiber_diameter_mean_px':fr['complete_region_equivalent_diameter_px']['mean'],
            'fiber_diameter_std_px':fr['complete_region_equivalent_diameter_px']['std'],
            'fiber_nearest_neighbor_mean_px':fr['complete_region_centroid_nearest_neighbor_px']['mean'],
            'fiber_S2_x_8':fiber['S2_x'][8], 'fiber_S2_y_8':fiber['S2_y'][8],
            'matrix_fiber_interface':d['phase_pair_interfaces']['matrix__fiber']['edge_count_per_pixel2'],
            'matrix_lcc':matrix['largest_component_fraction_of_phase'], 'void_regions':vr['annotation_region_count'],
            'void_diameter_mean_px':vr['complete_region_equivalent_diameter_px']['mean'],
            'void_S2_x_8':void['S2_x'][8], 'detail':d}


def errors(observed, target, family, names):
    per_metric = {k: None if observed.get(k) is None or target.get(k) is None
                  else float(abs(observed[k]-target[k])/SCALES[family][k]) for k in names}
    values = [v for v in per_metric.values() if v is not None]
    return {'per_metric':per_metric, 'coverage':len(values)/len(names),
            'mean':float(np.mean(values)) if len(values)==len(names) else None,
            'available_mean_diagnostic':float(np.mean(values)) if values else None}


def categorical_diversity(arrays, family):
    for a in arrays:
        validate(a, family)
    pairs = [float(np.mean(a != b)) for a,b in itertools.combinations(arrays,2)]
    return {'outputs':len(arrays), 'mean_categorical_hamming':float(np.mean(pairs)) if pairs else None,
            'by_phase':{str(k):diversity([(a==k).astype(np.uint8) for a in arrays]) for k in LABELS[family]},
            'interpretation':'Seed realizations are nested within one script; neither outputs nor phase masks count as independent LLM trials'}
