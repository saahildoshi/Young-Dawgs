"""Supplement registered C orientation, repair and repeat checks from disk."""
import json
from pathlib import Path
import numpy as np
import shapely
from shapely import Polygon,STRtree,Point
from metamaterial_eval.geometry.validation.checks import rings,signed_area,boundary_distance,area_difference,topology,digest
from metamaterial_eval.geometry.sensitivity.records import write_json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/pipeline_v0.5/scientific_validation/run_001'


def inspect_record(path):
    d=json.loads(path.read_text());p=d['provenance'];src=json.loads((OUT/'source_manifests'/(d['fixture']+'.json')).read_text())['source_provenance']
    a=shapely.from_wkb((ROOT/src['paths']['manifold']).read_bytes());b=shapely.from_wkb((ROOT/p['candidate_input_path']).read_bytes())
    old=rings(a);new=rings(b)
    orientation=len(old)==len(new) and all(r['polygon']==s['polygon'] and r['role']==s['role'] and signed_area(r['xy'])*signed_area(s['xy'])>0 for r,s in zip(old,new))
    # Direct unguarded cross-ring separation screening, separately from medial
    # support and axial chords. STRtree avoids quadratic global pair scans.
    guard=shapely.from_wkb((ROOT/p['guard_input_path']).read_bytes())
    unguarded=[]
    for r in new:
        line=shapely.LineString(r['xy']).difference(guard)
        if not line.is_empty:unguarded.append(line)
    pairs=[];tree=STRtree(unguarded)
    for i,line in enumerate(unguarded):
        for j in tree.query(line,predicate='dwithin',distance=2):
            if j>i:pairs.append({'ring_i':i,'ring_j':int(j),'distance':float(line.distance(unguarded[j]))})
    return {'fixture':d['fixture'],'epsilon':d['epsilon'],'orientation_ownership':bool(orientation),
            'unguarded_cross_ring_pairs_within2':pairs,
            'scope':'Cross-ring portions outside guard union; same-ring self-approach is not exhaustive. GEOS distance shared.',
            'input_sha256':digest(path)}


def main():
    results=[];repeat=[]
    for section in ['development_reference','parameter_holdouts']:
        paths=sorted((OUT/section).glob('*/*/independent_validation.json'))
        results.extend(inspect_record(p) for p in paths)
        first=next((p for p in paths if 'epsilon_0p50' in str(p)),None)
        if first is None:continue
        d=json.loads(first.read_text());src=json.loads((OUT/'source_manifests'/(d['fixture']+'.json')).read_text())['source_provenance']
        a=shapely.from_wkb((ROOT/src['paths']['manifold']).read_bytes());b=shapely.from_wkb((ROOT/d['provenance']['candidate_input_path']).read_bytes())
        metrics={'area':area_difference(a,b),'distance':boundary_distance(a,b),'topology':topology(a,b)}
        expected={'area':d['areas']['G2_G3'],'distance':d['distances']['G2_G3'],'topology':d['continuous_topology']}
        repeat.append({'cohort':section,'fixture':d['fixture'],'epsilon':.5,'identical':metrics==expected,'input_sha256':digest(first)})
    write_json(OUT/'verification/SUPPLEMENTAL_CHECKS.json',{'records':results,'metric_repeats':repeat,
        'all_orientation_ownership_preserved':all(r['orientation_ownership'] for r in results),'all_repeats_identical':all(r['identical'] for r in repeat)})
    print('orientation',sum(r['orientation_ownership'] for r in results),'of',len(results),'repeat',repeat)


if __name__=='__main__':main()
