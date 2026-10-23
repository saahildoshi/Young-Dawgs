"""Original/corrected regression comparison, using saved authenticated B2 leaves."""
from pathlib import Path
import json
from collections import Counter
import shapely
from metamaterial_eval.geometry.protected_v2.study import ROOT,OUT,C,fixture_from_source,settings
from metamaterial_eval.geometry.protected.guards import prepare_risks,build_guards
from metamaterial_eval.geometry.protected.engine import simplify_protected
from metamaterial_eval.geometry.validation.checks import digest,rings,area_difference
from metamaterial_eval.geometry.sensitivity.records import write_json


def key(p):return (p['ring'],tuple(p['original_vertex_indices']))


def main():
    protocol,cfg=settings();summary=json.loads((OUT/'summary/regression.json').read_text());prior=json.loads((C/'summary/SCIENTIFIC_GEOMETRY_VALIDATION.json').read_text());lookup={(r['fixture'],r['epsilon']):r for r in prior['rows']};records=[];cache={}
    for r in summary['rows']:
        name=r['fixture'];eps=r['epsilon'];result_path=ROOT/r['result_path'];revised=json.loads(result_path.with_name('engine.json').read_text())
        if (name,eps) in lookup:
            old_result=json.loads((ROOT/lookup[(name,eps)]['result_path']).read_text());oldpath=ROOT/old_result['provenance']['candidate_input_path'];oldengine=json.loads(oldpath.with_name('engine.json').read_text());oldg=shapely.from_wkb(oldpath.read_bytes())
        else:
            # Only the ten C-derived .35 regressions lack a stored original
            # candidate. Reproduce from immutable G2; never generate a mask.
            existing=lookup[(name,.2)];d=json.loads((ROOT/existing['result_path']).read_text());guess=(ROOT/d['provenance']['candidate_input_path']).parent.parent/'epsilon_0p35/candidate.wkb'
            if guess.exists():oldpath=guess;oldengine=json.loads(guess.with_name('engine.json').read_text());oldg=shapely.from_wkb(guess.read_bytes())
            else:
                if name not in cache:
                    f=fixture_from_source(name);risk=prepare_risks(f,cfg);cache[name]=(f,risk)
                f,risk=cache[name];guards=build_guards(risk,eps,cfg);e=simplify_protected(f['baseline'],eps,risk,guards,cfg);oldg=e['geometry'];oldengine={k:v for k,v in e.items() if k not in ('geometry','keeps')}
                oldpath=result_path.with_name('original_B2_candidate.wkb');oldpath.write_bytes(shapely.to_wkb(oldg,byte_order=1));write_json(result_path.with_name('original_B2_engine.json'),oldengine)
        newg=shapely.from_wkb(result_path.with_name('candidate.wkb').read_bytes());old_accepted={key(p) for p in oldengine['proposals'] if p['applied']};new_accepted={key(p) for p in revised['proposals'] if p['applied']}
        width_rejected={key(p) for p in revised['proposals'] if p.get('width_qualification') is not None and not p['width_qualification']['passed']}
        baseline=r['baseline_vertices'];oldvertices=sum(len(x['xy'])-1 for x in rings(oldg))
        records.append({'fixture':name,'epsilon':eps,'original_vertices':oldvertices,'revised_vertices':r['vertices'],
            'original_reduction_percent':100*(1-oldvertices/baseline),'revised_reduction_percent':r['vertex_reduction_percent'],
            'width_rejections':r['width_counters']['width_rejections'],'formerly_accepted_now_width_rejected':len(old_accepted&width_rejected),
            'formerly_accepted_now_not_applied':len(old_accepted-new_accepted),'formerly_not_accepted_now_accepted':len(new_accepted-old_accepted),
            'original_candidate_path':str(oldpath.relative_to(ROOT)),'original_sha256':digest(oldpath),'revised_sha256':digest(result_path.with_name('candidate.wkb')),
            'direct_original_vs_revised':area_difference(oldg,newg),'original_record_reused':(name,eps) in lookup or 'protected_simplification' in str(oldpath)})
    write_json(OUT/'summary/REGRESSION_COMPARISON.json',{'records':records,'newly_prevented_previously_accepted':sum(r['formerly_accepted_now_width_rejected'] for r in records),
        'width_rejections_total':sum(r['width_rejections'] for r in records),'counter_scope':'Leaf proposals across configurations, not unique physical features. Width flags include conservative uncertainty and can overlap original material-budget failures.'})
    print('Compared',len(records),'regression configurations')


if __name__=='__main__':main()
