"""Descriptive script-level pilot analysis and mechanics-ready design records."""
import csv,itertools
import numpy as np
from scripts.v070_protocol import REPO,RUN,write,read,sha
from metamaterial_eval.composites.diversity import diversity


def mean(values):
    a=[x for x in values if x is not None]
    return float(np.mean(a)) if a else None


def analyze():
    summary=[];individual=[];designs=[];p=read(RUN/'protocol/PROTOCOL.json')
    for d in sorted((RUN/'llm_trials').iterdir()):
        if not (d/'manifest.json').exists():continue
        m=read(d/'manifest.json')
        for e in sorted(d.glob('evaluation_r*_held')):
            if not (e/'EXECUTION.json').exists():continue
            report=read(e/'EXECUTION.json');revision=report.get('revision',int(e.name.split('_')[1][1:]));records=report['records'];successful=[r for r in records if r['status']=='OK']
            images=[np.load(e/f"seed_{r['seed']:03d}.npy",allow_pickle=False) for r in successful];div=diversity(images)
            visible=[r['visible_error']['mean'] for r in successful];hidden=[r['holdout_error']['mean'] for r in successful]
            condition=m['condition']+('_initial' if m['condition']=='C' and revision==0 else '')
            summary.append({'trial_id':d.name,'family':m['family'],'condition':condition,'revision':revision,'script_sha256':sha(d/f'generator_r{revision}.py'),
                'independent_trial':m.get('independent_trial'),'executed_seeds':len(records),'planned_heldout_seeds':10,'valid_outputs':report.get('valid_outputs',0),
                'validity_rate':report.get('valid_outputs',0)/10,'visible_error_mean':mean(visible),'visible_error_within_script_std':float(np.std([v for v in visible if v is not None])) if any(v is not None for v in visible) else None,
                'holdout_error_mean':mean(hidden),'visible_error_coverage_mean':mean([r['visible_error']['coverage'] for r in successful]),
                'holdout_error_coverage_mean':mean([r['holdout_error']['coverage'] for r in successful]),'runtime_seconds':report.get('wall_seconds'),**div})
            for r in records:
                record={'trial_id':d.name,'family':m['family'],'condition':condition,'revision':revision,'seed':r['seed'],'status':r['status'],
                    'valid':r.get('validity',{}).get('passed',False),'source_sha256':r['source_sha256'],'output_array_sha256':r.get('array_sha256'),
                    'visible_error':r.get('visible_error',{}).get('mean'),'holdout_error':r.get('holdout_error',{}).get('mean'),'runtime_seconds':r['generation_repeat_and_evaluation_seconds']}
                individual.append(record)
                if r['status']=='OK':
                    descriptors=r['descriptors'];designs.append({'design_id':f'{d.name}_r{revision}_seed{r["seed"]:03d}','family':m['family'],'reference_id':m['family']+'_synthetic_001',
                        'generator_code_sha256':r['source_sha256'],'llm_trial_id':d.name if m['condition']!='BASELINE' else None,'origin':'EXPERIMENTAL_CHATGPT' if m['condition']!='BASELINE' else 'RESEARCHER_BASELINE',
                        'seed':r['seed'],'array_sha256':r['array_sha256'],'array_path':str((e/f"seed_{r['seed']:03d}.npy").relative_to(REPO)),
                        'phase_schema':{'0':{'role':'matrix','physical_solid':True,'material_parameters':None},'1':{'role':'reinforcement','physical_solid':True,'material_parameters':None}},
                        'geometry':{'shape':[256,256],'units':'pixel','pixel_to_length':None,'boundary':'finite_nonperiodic'},'validity':r['validity'],'descriptors':descriptors,
                        'connected_components':{'matrix_largest_fraction':descriptors['matrix_lcc'],'reinforcement_count':descriptors['object_count']},
                        'interfaces':{'type':'matrix_reinforcement','density_pixel_edges_per_pixel2':descriptors['interface_density'],'assumed_bonding':None},
                        'meshing_status':'NOT_MESHED','meshing_readiness':'PHASE_LABELED_2D_ARRAY_ONLY;interface/scale/mesh checks pending','mechanical_model_status':'NOT_IMPLEMENTED','mechanically_validated':False})
    out=RUN/'results';out.mkdir(exist_ok=True)
    for filename,rows in [('SCRIPT_SUMMARY.csv',summary),('INDIVIDUAL_HELDOUT.csv',individual)]:
        if rows:
            with (out/filename).open('w',newline='',encoding='utf-8') as f:
                writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    groups=[]
    for family in ['particle','fiber']:
        for condition in ['BASELINE','A','B','C_initial','C']:
            rows=[r for r in summary if r['family']==family and r['condition']==condition]
            groups.append({'family':family,'condition':condition,'status':'EXECUTED' if rows else 'NOT_RUN','independent_LLM_initial_trials':len(rows) if condition not in ['BASELINE','C_initial'] else (len(rows) if condition=='C_initial' else 0),
                'scripts':len(rows),'stochastic_outputs':sum(r['executed_seeds'] for r in rows),'valid_outputs':sum(r['valid_outputs'] for r in rows),
                'validity_rate':mean([r['validity_rate'] for r in rows]),'visible_error_script_mean':mean([r['visible_error_mean'] for r in rows]),
                'visible_error_between_script_std':float(np.std([r['visible_error_mean'] for r in rows if r['visible_error_mean'] is not None],ddof=1)) if sum(r['visible_error_mean'] is not None for r in rows)>1 else None,
                'holdout_error_script_mean':mean([r['holdout_error_mean'] for r in rows]),'mean_jaccard_diversity':mean([r['mean_jaccard_distance'] for r in rows]),
                'mean_hamming_diversity':mean([r['mean_hamming_fraction'] for r in rows]),'mean_unique_hashes':mean([r['unique_hashes'] for r in rows]),'token_cost':'NOT_AVAILABLE'})
    feedback=[]
    for row in summary:
        if row['condition']!='C':continue
        before=next(x for x in summary if x['trial_id']==row['trial_id'] and x['revision']==0)
        feedback.append({'trial_id':row['trial_id'],'family':row['family'],'independent_initial_trial_shared_with_C_initial':True,
            'visible_error_before':before['visible_error_mean'],'visible_error_after':row['visible_error_mean'],
            'visible_improvement':before['visible_error_mean']-row['visible_error_mean'] if before['visible_error_mean'] is not None and row['visible_error_mean'] is not None else None,
            'hidden_error_before':before['holdout_error_mean'],'hidden_error_after':row['holdout_error_mean'],
            'validity_before':before['validity_rate'],'validity_after':row['validity_rate'],'diversity_before':before['mean_jaccard_distance'],'diversity_after':row['mean_jaccard_distance']})
    write(out/'SCRIPT_SUMMARY.json',summary);write(out/'CONDITION_SUMMARY.json',groups);write(out/'FEEDBACK_COMPARISON.json',feedback)
    write(out/'MECHANICS_READY_DESIGNS.json',{'schema':'young-dawgs-phase-labeled-composite-design-v070','mechanics_executed':False,'designs':designs})
    print('Analyzed',len(summary),'held-out script versions and',len(individual),'nested stochastic outputs',flush=True)
    return summary,groups,feedback


if __name__=='__main__':analyze()
