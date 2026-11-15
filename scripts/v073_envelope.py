"""Freeze stronger prospective rules from explicitly observed calibration data."""
import argparse
import math
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v073_experiment import RUN,DOC,PREV,REFERENCE,now
from scripts.v073_prepare import generate, module
from scripts.v072_experiment import feasibility as inherited_feasibility
from metamaterial_eval.composites.morphology_v073 import flattened,describe

def feasibility(row,policy):
    old=inherited_feasibility(row,policy)
    checks=old.get('checks',{})
    if row.get('status')!='GENERATED':return old
    values=flattened(row['morphology_v073'])
    for key,(lo,hi) in policy['new_descriptor_bounds'].items():
        value=values.get(key);checks[key]=value is not None and lo<=value<=hi
    for key in policy['must_be_false']:
        checks[key]=values.get(key) is False
    return {'passed':all(checks.values()),'checks':checks,'failures':[k for k,v in checks.items() if not v]}

def freeze():
    assert not (RUN/'protocol/FEASIBILITY_FROZEN.json').exists()
    calibration=read(RUN/'envelope_calibration/SUMMARY.json')['rows']
    reference=read(RUN/'envelope_calibration/REFERENCE.json')
    # Refresh only new descriptor records after adding largest-region diagnostics.
    for r in calibration:
        r['morphology_v073']=describe(np.load(RUN/'envelope_calibration'/f"seed_{r['seed']}.npy")==5)
    reference['morphology_v073']=describe(np.load(REFERENCE)==5)
    values=[flattened(r['morphology_v073']) for r in [reference]+calibration]
    def upper(key,margin,scale=1):return math.ceil((max(r[key] for r in values)*scale+margin)*100)/100
    bounds={'all_observed.area_weighted_aspect':[1,upper('all_observed.area_weighted_aspect',0,1.25)],
        'all_observed.area_weighted_aspect_p95':[1,upper('all_observed.area_weighted_aspect_p95',0,1.2)],
        'all_observed.area_fraction_aspect_gt3':[0,upper('all_observed.area_fraction_aspect_gt3',.15)],
        'all_observed.area_fraction_aspect_gt4':[0,upper('all_observed.area_fraction_aspect_gt4',.08)],
        'all_observed.defined_aspect_area_fraction':[.995,1],
        'all_observed.axial_order':[0,upper('all_observed.axial_order',.30)],
        'long_range_abs_S2_difference':[0,upper('long_range_abs_S2_difference',.02)],
        'limited_gap_run_x':[0,upper('limited_gap_run_x',.20)],
        'limited_gap_run_y':[0,upper('limited_gap_run_y',.20)],
        'gap_dilation.2.largest_fraction':[0,upper('gap_dilation.2.largest_fraction',.25)],
        'nearest_neighbor_cv':[.10,upper('nearest_neighbor_cv',.20)]}
    for width in (1,8,16,32):
        for direction in ('column','row'):
            bounds[f'strips.{width}.{direction}_std']=[0,upper(f'strips.{width}.{direction}_std',.06)]
            bounds[f'strips.{width}.{direction}_max']=[0,min(.80,upper(f'strips.{width}.{direction}_max',.15))]
    policy=read(PREV/'protocol/FEASIBILITY_FROZEN.json')
    for key in ['selection','selection_basis','guardrail_rationale','composition_claim_limit','composition_rationale']:policy.pop(key,None)
    policy.update(frozen_utc=now(),target_count=20731,absolute_pixel_tolerance=0,absolute_fraction_tolerance=0,
        new_descriptor_bounds=bounds,must_be_false=['gap_dilation.2.spans_x','gap_dilation.2.spans_y'],
        calibration='One reference +12 prospective baseline seeds, independent fixtures and already-observed historical controls; not blind natural-family validation',
        threshold_rationale={'area_weighted_aspect':'max(reference,baseline)*1.25','p95':'max*1.20',
            'tail_gt3':'max+.15 area fraction','tail_gt4':'max+.08','axial_order':'max+.30 to permit moderate orientation',
            'long_range_S2':'max+.02','strip_std':'max+.06','strip_max':'min(.8,max+.15)',
            'gap_lcc':'max+.25; no 2px disk-dilation spanning','limited_gap_runs':'max+.20',
            'spacing_CV':'[.10,max+.20]','rounding':'upper thresholds round upward to hundredth; coverage>=.995 prevents undefined-region evasion'},
        diagnostic_only=['complete-region new shape/orientation','largest-region shape','S2 individual lags','1px dilation','interface density','NNmean','old reference-relative reconstruction errors'],
        boundary_policy='New shape/tail/alignment limits include all observed regions, never exclude boundary-clipped features. Complete/all statistics both retained. Pixel-region geometry is not a recovered physical particle.')
    assert all(feasibility({**r,'status':'GENERATED','deterministic':True,'generation_seconds':r.get('generation_seconds',0)},policy)['passed'] for r in [reference]+calibration)
    write(RUN/'protocol/FEASIBILITY_FROZEN.json',policy)
    for r in calibration:
        r['feasibility']=feasibility(r,policy);write(RUN/'envelope_calibration'/f"seed_{r['seed']}.json",r)
    write(RUN/'envelope_calibration/REFERENCE.json',reference)
    comparisons=[]
    for r in read(RUN/'historical_lane_controls/OBSERVATIONS.json'):
        flat=flattened(r['morphology_v073'])
        violations=[key for key,(lo,hi) in bounds.items() if flat[key] is None or not lo<=flat[key]<=hi]
        violations += [key for key in policy['must_be_false'] if flat[key] is not False]
        comparisons.append({**r,'new_morphology_violations':violations,'detected':bool(violations),
            'historical_acceptance_unchanged':True})
    write(RUN/'historical_lane_controls/CHALLENGE_RESULTS.json',comparisons)
    summary={trial:{'n':sum(r['trial_id']==trial for r in comparisons),'detected':sum(r['detected'] and r['trial_id']==trial for r in comparisons)} for trial in sorted({r['trial_id'] for r in comparisons})}
    write(RUN/'morphology_descriptor_validation/CHALLENGE_SUMMARY.json',summary)
    body='# Prospective P3-like morphology envelope\n\nAll12 exact baseline calibration outputs and the authenticated target pass. Known lane challenge detection is shown below; it is design-set performance, not blind validation. Historical v0.7.2 acceptance is unchanged.\n\n'
    body+='| Historical cohort | Detected by new rules | Total |\n|---|---:|---:|\n'+''.join(f"| {k} | {v['detected']} | {v['n']} |\n" for k,v in summary.items())
    body+='\n| New hard descriptor | Lower | Upper |\n|---|---:|---:|\n'+''.join(f'| {k} | {v[0]} | {v[1]} |\n' for k,v in bounds.items())
    body+='\nNo x/y spanning after2px disk dilation; this detects near organization and does not alter the specimen or establish physical bonding. Inherited phase/topology/population rules remain, with composition tolerance replaced by exact count. Shape statistics cover all observed regions; complete-region statistics remain separately available. Axial orientation weights use area×eigenvalue anisotropy, suppressing nearly circular axes. Correlations and strip windows use finite support with no wrapping. Threshold margins permit moderate shape/orientation/dispersion changes and are empirical P3-family choices, not universal material bounds. Full limits and algorithms are in FEASIBILITY_FROZEN.json and the descriptor source. Independent digital fixtures test circles, orthogonal/balanced ellipses, large shape tails, segmented lanes, gaps, censoring, occupancy, clustering, rotation/reflection and undefined metrics. Passing this envelope cannot establish full natural-material identity.\n'
    (DOC/'V0_7_3_MORPHOLOGY_ENVELOPE.md').write_text(body,encoding='utf-8',newline='\n')
    print(summary,flush=True)

def variants():
    destination=RUN/'controlled_variants/generator.py';assert not destination.exists()
    original=(RUN/'starting_generator/generator.py').read_text()
    code=original.replace('def _particle(rng, area):','def _particle(rng, area, aspect_scale=1., orientation_kappa=0., orientation_angle=0.):')
    code=code.replace('1.05, 3.8)','1.05, 3.8) * aspect_scale')
    code=code.replace('a = rng.uniform(0, np.pi)','a = rng.uniform(0, np.pi) if orientation_kappa == 0 else (rng.vonmises(2*orientation_angle, orientation_kappa)/2) % np.pi')
    code=code.replace('    rng = np.random.default_rng(seed)','    rng = np.random.default_rng(seed)\n    shape_args = (parameters.get("aspect_scale",1.), parameters.get("orientation_kappa",0.), parameters.get("orientation_angle",0.))')
    code=code.replace('particles = [_particle(rng, np.pi * v*v / 4)', 'particles = [_particle(rng, np.pi * v*v / 4, *shape_args)')
    code=code.replace('_particle(rng, target * rng.uniform(1.45, 1.95))','_particle(rng, target * rng.uniform(1.45, 1.95), *shape_args)')
    code=code.replace('    # Sample the complete-region diameter distribution.','    field *= parameters.get("placement_field_scale",1.)\n\n    # Sample the complete-region diameter distribution.')
    destination.parent.mkdir(exist_ok=True);destination.write_text(code,encoding='utf-8',newline='\n')
    matrix={'BASE':{},'V1_ELONGATION':{'aspect_scale':1.2},'V2_VERTICAL':{'orientation_kappa':1.,'orientation_angle':float(np.pi/2)},
        'V3_HORIZONTAL':{'orientation_kappa':1.,'orientation_angle':0.},'V4_DISPERSION':{'placement_field_scale':0.}}
    # Definitions and seeds are frozen before geometry generation and any mechanics.
    write(RUN/'controlled_variants/VARIANTS_FROZEN.json',{'frozen_utc':now(),'generator_sha256':sha(destination),
        'baseline_sha256':sha(RUN/'starting_generator/generator.py'),'matrix':matrix,
        'seeds':read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['development'],'source':'researcher designed probes, not LLM responses',
        'confounding':'Changing sampling changes random trajectories, sizes/placement can covary; measured associations are not single-descriptor causal effects'})
    policy=read(RUN/'protocol/FEASIBILITY_FROZEN.json');rows=[]
    for trial,params in matrix.items():
        seeds=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['development'][:6 if trial=='BASE' else 3]
        source=RUN/'starting_generator/generator.py' if trial=='BASE' else destination
        for seed in seeds:
            row=generate(source,seed,RUN/'controlled_variants'/trial/f'seed_{seed}.npy',params)
            row.update(trial_id=trial,feasibility=feasibility(row,policy))
            write(RUN/'controlled_variants'/trial/f'seed_{seed}.json',row);rows.append(row)
            print(trial,seed,row['feasibility']['passed'],row['feasibility']['failures'],flush=True)
    write(RUN/'controlled_variants/GEOMETRY_DATASET_FROZEN.json',{'frozen_utc':now(),'rows':rows,'no_mechanics_seen':True,
        'variant_manifest_sha256':sha(RUN/'controlled_variants/VARIANTS_FROZEN.json'),'feasibility_sha256':sha(RUN/'protocol/FEASIBILITY_FROZEN.json')})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','variants']);args=p.parse_args()
    freeze() if args.action=='freeze' else variants()
