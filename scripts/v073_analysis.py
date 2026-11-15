"""Target accuracy and feasibility are separate; invalid attempts have null mechanics."""
import csv
import itertools
from pathlib import Path
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v073_experiment import RUN,DOC,TRIALS,now

ORDER=['BASE']+TRIALS

def statistics(values):
    values=np.asarray(values,dtype=float)
    if not len(values):return {'n':0,'mean':None,'sample_SD':None,'CV':None,'min':None,'max':None,'median':None}
    mean=float(values.mean());sd=float(values.std(ddof=1)) if len(values)>1 else None
    return {'n':len(values),'mean':mean,'sample_SD':sd,'CV':sd/abs(mean) if sd is not None and mean else None,
        'min':float(values.min()),'max':float(values.max()),'median':float(np.median(values))}

def target_metrics(modulus,target,tolerance):
    if modulus is None:return {'J':None,'signed_target_error':None,'absolute_target_error':None,'target_hit':None}
    signed=(modulus-target)/target
    return {'J':modulus/1000,'signed_target_error':signed,'absolute_target_error':abs(signed),'target_hit':bool(abs(signed)<=tolerance)}

def csv_table(path,rows):
    if not rows:return
    path.parent.mkdir(parents=True,exist_ok=True)
    names=list(dict.fromkeys(k for r in rows for k in r))
    import json
    with path.open('w',encoding='utf-8',newline='') as f:
        out=csv.DictWriter(f,fieldnames=names);out.writeheader()
        for row in rows:out.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in row.items()})

def analyse():
    target=read(RUN/'target_selection/TARGET_FROZEN.json');assert target['qualified_target']
    h1=read(RUN/'heldout_mechanics_h1/CAMPAIGN.json')['cases'];h2=read(RUN/'heldout_mechanics_h2/CAMPAIGN.json')['cases']
    rows=[];summaries=[]
    for trial in ORDER:
        structural=read(RUN/'heldout_structural_evaluation'/trial/'SUMMARY.json');local=[]
        for result in [r for r in h1 if r['trial_id']==trial]:
            row={**result,**target_metrics(result['apparent_modulus_MPa'],target['target_MPa'],target['target_hit_relative_tolerance'])}
            s=read(RUN/'heldout_structural_evaluation'/trial/f"seed_{row['seed']}.json")
            row.update(exact_composition=s.get('phase_counts',{}).get('5')==20731,phase_counts=s.get('phase_counts'),
                generation_seconds=s.get('generation_seconds'),generation_status=s['status'])
            rows.append(row);local.append(row)
        accepted=[r for r in local if r['apparent_modulus_MPa'] is not None]
        mods=[r['apparent_modulus_MPa'] for r in accepted];errors=[r['absolute_target_error'] for r in accepted]
        base={r['seed']:r for r in rows if r['trial_id']=='BASE' and r['absolute_target_error'] is not None}
        improvements=[base[r['seed']]['absolute_target_error']-r['absolute_target_error'] for r in accepted if r['seed'] in base]
        summaries.append({'trial_id':trial,'arm':trial[:2] if trial!='BASE' else 'BASE','attempted':10,
            'structurally_feasible':structural['feasible'],'mechanically_accepted':len(accepted),
            'fully_qualified_generator':structural['fully_qualified_generator'] and len(accepted)==10,
            'modulus':statistics(mods),'target_error':statistics(errors),
            'mean_property_bias':abs(np.mean(mods)-target['target_MPa'])/target['target_MPa'] if mods else None,
            'mean_signed_bias':float(np.mean([r['signed_target_error'] for r in accepted])) if accepted else None,
            'target_hits':sum(r['target_hit'] for r in accepted),'target_hits_per_attempt':sum(r['target_hit'] for r in accepted)/10,
            'target_hits_per_accepted':sum(r['target_hit'] for r in accepted)/len(accepted) if accepted else None,
            'paired_BASE_error_reduction':statistics(improvements),'fraction_positive_paired_reduction':float(np.mean(np.array(improvements)>0)) if improvements else None,
            'runtime':statistics([r['generation_seconds'] for r in local if r.get('generation_seconds') is not None]),
            'diversity':structural['diversity'],'metric_scope':'Conditional on structural and native acceptance; attempted denominator and qualification always retained'})
    arms={arm:{'registered_scripts':4,'fully_qualified_scripts':sum(r['fully_qualified_generator'] for r in summaries if r['arm']==arm),
        'conditional_script_errors':statistics([r['target_error']['mean'] for r in summaries if r['arm']==arm and r['target_error']['mean'] is not None]),
        'qualified_script_errors':statistics([r['target_error']['mean'] for r in summaries if r['arm']==arm and r['fully_qualified_generator']])} for arm in ['IF','NF']}
    # Equal independent-unit weighting, never pool stochastic outputs as LLM trials.
    IF,NF=[arms[a]['conditional_script_errors'] for a in ['IF','NF']]
    advantage=NF['mean']-IF['mean'] if IF['n']==NF['n']==4 else None
    comparison={'arms':arms,'conditional_feedback_advantage_NF_minus_IF':advantage,
        'all_eight_fully_qualified':all(r['fully_qualified_generator'] for r in summaries if r['trial_id']!='BASE'),
        'primary_claim_policy':'Conditional performance cannot rescue infeasible generators; unequal survivors and tiny script count preclude general causal claims',
        'independent_unit':'Returned script, four per arm; seeds nested; no significance claim'}
    mesh=[]
    for result in h2:
        first=next(r for r in rows if r['trial_id']==result['trial_id'] and r['seed']==result['seed'])
        second=target_metrics(result['apparent_modulus_MPa'],target['target_MPa'],target['target_hit_relative_tolerance'])
        row={**result,'H1_modulus_MPa':first['apparent_modulus_MPa'],'H1_target_error':first['absolute_target_error'],
            'H2_target_error':second['absolute_target_error'],'H1_hit':first['target_hit'],'H2_hit':second['target_hit']}
        if first['apparent_modulus_MPa'] is not None and result['apparent_modulus_MPa'] is not None:
            row['absolute_mesh_change_MPa']=abs(result['apparent_modulus_MPa']-first['apparent_modulus_MPa'])
            row['relative_mesh_change']=row['absolute_mesh_change_MPa']/first['apparent_modulus_MPa']
        mesh.append(row)
    for row in mesh:
        base=next(r for r in mesh if r['trial_id']=='BASE' and r['seed']==row['seed'])
        valid=all(r.get('absolute_mesh_change_MPa') is not None for r in [row,base])
        row['H1_BASE_error_reduction']=base['H1_target_error']-row['H1_target_error'] if valid else None
        row['H2_BASE_error_reduction']=base['H2_target_error']-row['H2_target_error'] if valid else None
        row['combined_observed_change_over_target']=(base['absolute_mesh_change_MPa']+row['absolute_mesh_change_MPa'])/target['target_MPa'] if valid else None
        row['improvement_persists']=bool(row['H1_BASE_error_reduction']>0 and row['H2_BASE_error_reduction']>0) if valid else None
        row['H2_improvement_exceeds_observed_changes']=bool(row['H2_BASE_error_reduction']>row['combined_observed_change_over_target']) if valid else None
    for name,data in [('HELDOUT_RESULTS',rows),('SCRIPT_SUMMARIES',summaries),('IF_VERSUS_NF',comparison),('MESH_CONFIRMATION',mesh)]:
        write(RUN/'target_property_analysis'/f'{name}.json',data)
        if isinstance(data,list):csv_table(RUN/'target_property_analysis'/f'{name}.csv',data)
    return rows,summaries,comparison,mesh

if __name__=='__main__':analyse()
