"""Post-study diagnostic: confirm flagged chords directly from coordinate edges.

No GEOS intersections are used in width calculation; WKB parsing alone shares
GEOS. This does not alter prospective screens or rescue any candidate.
"""
from pathlib import Path
import json
import shapely
from metamaterial_eval.geometry.validation.checks import rings,digest
from metamaterial_eval.geometry.sensitivity.records import write_json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/pipeline_v0.5/scientific_validation/run_001'


def axial_interval(geometry,xy,axis):
    # axis0 means horizontal chord (vary x); axis1 vertical (vary y).
    fixed=1-axis;cut=xy[fixed];crossings=[];segments=[]
    for ring in rings(geometry):
        for u,v in zip(ring['xy'][:-1],ring['xy'][1:]):
            if min(u[fixed],v[fixed])<=cut<max(u[fixed],v[fixed]):
                t=(cut-u[fixed])/(v[fixed]-u[fixed]);value=u[axis]+t*(v[axis]-u[axis])
                crossings.append(value);segments.append({'coordinate':value,'edge':[u,v]})
    lower=max((v for v in crossings if v<=xy[axis]),default=None)
    upper=min((v for v in crossings if v>=xy[axis]),default=None)
    return {'lower':lower,'upper':upper,'width':upper-lower if lower is not None and upper is not None else None,
            'crossing_edges':[s for s in segments if s['coordinate'] in [lower,upper]]}


def main():
    rows=[]
    for section in ['development_reference','parameter_holdouts']:
        for path in (OUT/section).glob('*/*/independent_validation.json'):
            d=json.loads(path.read_text());flagged=[p for p in d['features']['independent_probes'] if p['narrowed']]
            if not flagged:continue
            source=json.loads((OUT/'source_manifests'/(d['fixture']+'.json')).read_text())['source_provenance']
            a=shapely.from_wkb((ROOT/source['paths']['manifold']).read_bytes());b=shapely.from_wkb((ROOT/d['provenance']['candidate_input_path']).read_bytes())
            for p in flagged:
                before=axial_interval(a,p['xy'],p['axis']);after=axial_interval(b,p['xy'],p['axis'])
                rows.append({'fixture':d['fixture'],'epsilon':d['epsilon'],'probe':p,'source_coordinate_intersections':before,
                    'candidate_coordinate_intersections':after,'direct_width_change':after['width']-before['width'],
                    'agrees_with_GE0S_widths':abs(before['width']-p['before'])<=1e-10 and abs(after['width']-p['after'])<=1e-10,
                    'input_record_sha256':digest(path)})
    write_json(OUT/'feature_audit/AXIAL_COORDINATE_CONFIRMATION.json',{'kind':'post_study_independent_diagnostic_no_gate_changes','records':rows,
        'all_confirmed':all(r['agrees_with_GE0S_widths'] for r in rows),'method':'Half-open edge crossings, affine coordinate interpolation; closest bracketing crossings around the fixed phase point. No geometry Boolean/intersection predicate for width.'})
    print('Flagged widths independently confirmed',len(rows),all(r['agrees_with_GE0S_widths'] for r in rows))


if __name__=='__main__':main()
