"""Summarize actual captured scripts; prepared prompts never count as trials."""
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.v070_real_pilot import RUN,DOC
from scripts.v070_protocol import read,write,sha
from scripts.v070_microscopy_review import colorize,PARTICLE_PHASES,FIBER_PHASES
from metamaterial_eval.composites.microscopy import VISIBLE,HIDDEN


def fmt(value):
    return 'NA' if value is None else f'{value:.4g}'


def condition_summary(rows):
    """Average script means, with revisions kept separate from parent trials."""
    groups=[];paired=[]
    for family,condition,revision,partition in sorted({(r['family'],r['condition'],r['revision'],r['partition']) for r in rows}):
        subset=[r for r in rows if (r['family'],r['condition'],r['revision'],r['partition'])==(family,condition,revision,partition)]
        group={'family':family,'condition':condition,'revision':revision,'partition':partition,
               'independent_parent_scripts':len(subset),'scripts':[r['trial_id'] for r in subset],
               'valid_outputs':sum(r['valid_outputs'] for r in subset),
               'requested_outputs':sum(r['requested_seeds'] for r in subset),
               'execution_failures':sum(r['execution_failures'] for r in subset)}
        for key in ['visible_error_mean','hidden_error_mean','categorical_hamming_diversity']:
            values=[r[key] for r in subset if r[key] is not None]
            group[key]=float(np.mean(values)) if len(values)==len(subset) else None
            group[key+'_scored_scripts']=len(values)
            group[key+'_script_sd']=float(np.std(values)) if len(values)==len(subset) else None
        groups.append(group)
    lookup={(r['trial_id'],r['revision'],r['partition']):r for r in rows}
    for r in rows:
        before=lookup.get((r['trial_id'],0,r['partition']))
        if r['revision']!=1 or before is None:continue
        pair={'trial_id':r['trial_id'],'partition':r['partition'],
              'valid_before':before['valid_outputs'],'valid_after':r['valid_outputs']}
        for key in ['visible_error_mean','hidden_error_mean','categorical_hamming_diversity']:
            pair[key+'_delta']=r[key]-before[key] if r[key] is not None and before[key] is not None else None
        paired.append(pair)
    return groups,paired


def summarize():
    rows=[];metrics=[]
    for path in sorted(RUN.glob('llm_trials/*/evaluation_r*_*/*EXECUTION.json')):
        report=read(path);d=path.parent.parent;m=read(d/'manifest.json');family=m['family'];ok=[r for r in report['records'] if r['status']=='OK']
        expected=len(report.get('seeds',read(RUN/'protocol/PROTOCOL.json')['development_seeds']))
        row={'trial_id':m['trial_id'],'family':family,'condition':m['condition'],'revision':report['revision'],
             'partition':report['partition'],'status':report['status'],'requested_seeds':expected,'valid_outputs':report['valid_outputs'],
             'execution_failures':report['execution_failures'],'returned_script_sha256':sha(d/f"generator_r{report['revision']}.py")}
        for group in ['visible','hidden']:
            values=[r[group+'_error']['mean'] for r in ok if r[group+'_error']['mean'] is not None]
            row[group+'_error_mean']=float(np.mean(values)) if len(values)==expected else None
            row[group+'_scored_outputs']=len(values)
        div=report.get('diversity',{});row['categorical_hamming_diversity']=div.get('mean_categorical_hamming')
        row['phase_unique_realizations']={k:v['unique_hashes'] for k,v in div.get('by_phase',{}).items()}
        target=read(RUN/'references'/family/'descriptors.json')
        for name in VISIBLE[family]+HIDDEN[family]:
            values=[r['descriptors'][name] for r in ok if r['descriptors'].get(name) is not None]
            metrics.append({'trial_id':m['trial_id'],'revision':report['revision'],'partition':report['partition'],'metric':name,
                            'visibility':'visible' if name in VISIBLE[family] else 'hidden','target':target[name],
                            'generated_seed_mean':float(np.mean(values)) if values else None,'generated_seed_std':float(np.std(values)) if values else None,
                            'available_outputs':len(values),'requested_outputs':expected})
        rows.append(row)
    submissions=list(RUN.glob('llm_trials/*/SUBMISSION_r*.json'));receipts=list(RUN.glob('llm_trials/*/RECEIPT_r*.json'))
    inventory={'genuine_submission_events':len(submissions),'genuinely_returned_initial_scripts':sum(p.name=='RECEIPT_r0.json' for p in receipts),
               'returned_feedback_revisions':sum(p.name!='RECEIPT_r0.json' for p in receipts),'prepared_initial_packets':len(list(RUN.glob('llm_trials/*/prompt.txt'))),
               'evaluated_seed_outputs':sum(r['requested_seeds']-r['execution_failures'] for r in rows),
               'independent_unit':'Returned initial script; seed realizations and paired feedback revisions are not additional independent trials'}
    out=RUN/'analysis';out.mkdir(exist_ok=True);DOC.mkdir(parents=True,exist_ok=True)
    groups,paired=condition_summary(rows)
    write(out/'SCRIPT_LEVEL_COMPARISON.json',rows);write(out/'METRIC_COMPARISON.json',metrics);write(out/'GENUINE_TRIAL_INVENTORY.json',inventory)
    write(out/'CONDITION_COMPARISON.json',groups);write(out/'PAIRED_FEEDBACK_COMPARISON.json',paired)
    figures=[]
    for family in ['P3','F1']:
        for partition in ['dev','held']:
            subset=[r for r in rows if r['family']==family and r['partition']==partition]
            if not subset:continue
            figures.append(render(family,partition,subset))
    text='# P3 + F1 real microscopy LLM pilot\n\n'
    text+=f"Actual independently returned initial scripts: **{inventory['genuinely_returned_initial_scripts']}**; paired feedback revisions: **{inventory['returned_feedback_revisions']}**. Submission events: {inventory['genuine_submission_events']}. Prepared initial packets: {inventory['prepared_initial_packets']}; unexecuted packets are not trials.\n\n"
    text+='| Script | Revision | Seeds | Valid / requested | Failures | Visible error | Hidden error | Hamming diversity |\n|---|---:|---|---:|---:|---:|---:|---:|\n'
    for r in rows:
        text+=f"| {r['trial_id']} | {r['revision']} | {r['partition']} | {r['valid_outputs']}/{r['requested_seeds']} | {r['execution_failures']} | {fmt(r['visible_error_mean'])} | {fmt(r['hidden_error_mean'])} | {fmt(r['categorical_hamming_diversity'])} |\n"
    text+='\nErrors are absolute descriptor differences divided by prospectively fixed scales, averaged equally within each group; lower is closer, not percentage accuracy. A script mean is NA unless every requested output has a complete group score. Validity and execution failures remain separate. Hamming distance measures variation among nested seeds, not reference accuracy.\n\n'
    text+='## Descriptive condition comparison\n\n| Family | Condition/revision | Partition | Parent scripts | Valid/requested | Visible error | Hidden error | Hamming diversity |\n|---|---|---|---:|---:|---:|---:|---:|\n'
    for r in groups:
        text+=f"| {r['family']} | {r['condition']}/r{r['revision']} | {r['partition']} | {r['independent_parent_scripts']} | {r['valid_outputs']}/{r['requested_outputs']} | {fmt(r['visible_error_mean'])} | {fmt(r['hidden_error_mean'])} | {fmt(r['categorical_hamming_diversity'])} |\n"
    text+='\nCondition values average script means equally. C/r0 and C/r1 share the same parent trials; they cannot be added as independent samples. Any missing script score makes its condition score unavailable. JSON tables retain scoring coverage and descriptive between-script SD; this small pilot does not support significance claims.\n\n'
    if paired:
        text+='| Paired parent | Partition | Valid before/after | Visible error change | Hidden error change | Diversity change |\n|---|---|---:|---:|---:|---:|\n'
        for r in paired:
            text+=f"| {r['trial_id']} | {r['partition']} | {r['valid_before']}/{r['valid_after']} | {fmt(r['visible_error_mean_delta'])} | {fmt(r['hidden_error_mean_delta'])} | {fmt(r['categorical_hamming_diversity_delta'])} |\n"
        text+='\nChanges are revised minus initial script means. Negative error change is closer agreement; diversity change has no reference-accuracy interpretation.\n\n'
    for family in ['P3','F1']:
        text+=f'## {family} descriptor comparison\n\n| Script/revision/partition | Descriptor | Target | Generated seed mean ± SD | Available outputs |\n|---|---|---:|---:|---:|\n'
        for r in metrics:
            if r['trial_id'].startswith(family+'_'):
                text+=f"| {r['trial_id']}/r{r['revision']}/{r['partition']} | {r['metric']} ({r['visibility']}) | {fmt(r['target'])} | {fmt(r['generated_seed_mean'])} ± {fmt(r['generated_seed_std'])} | {r['available_outputs']}/{r['requested_outputs']} |\n"
        text+='\n'
    text+='## Figures and interpretation\n\n'
    for name in figures:text+=f'![{name}](../../../experiments/pipeline_v0.7.0/run_002_real_microscopy/analysis/{name})\n\n'
    text+='Each figure shows the fixed first seed of its partition (development100 or heldout0), chosen prospectively rather than for appearance. The original microscopy image is the model input; phase-colored target panels are evaluator-only. Generated panels come from captured ChatGPT scripts, without researcher repairs.\n\n'
    text+='The small pilot supports descriptive comparisons between independent scripts on two selected fields. Seeds are nested, not independent LLM trials. Condition C receives extra interaction; there is no equal-attempt control for a causal feedback-only claim. Fresh initial ordinary chats were used, but account personalization, memory, connected context and hidden model routing are not controlled; the home screen surfaced project-related suggestions. Only ChatGPT and High effort are exposed; exact backend/version, tokens and cost are unavailable.\n\n'
    text+='P3 is a morphology-selected, horizontally flipped SEM augmentation. Native IDs1/5 are retained; label5 is only provisionally reprecipitated carbide. This is not an unbiased RVE or fully verified chemical map. F1 is original C/PEEK transverse microscopy with distinct matrix0/fiber1/void2; mean-radius circle and void-threshold annotation uncertainty limits region geometry and physical instance interpretation. Both targets lack physical pixel calibration. No mechanical properties, ANSYS results, cross-material generalization, p-values or optimization claims are inferred. Heldout results remain locked until all scripts/revisions are frozen.\n'
    (DOC/'RESULTS.md').write_text(text,encoding='utf-8',newline='\n')
    print(inventory)


def render(family,partition,rows):
    palette=PARTICLE_PHASES if family=='P3' else FIBER_PHASES
    source=RUN/'references'/family;seed=100 if partition=='dev' else 0
    panels=[(np.asarray(Image.open(source/'microscopy_input.png')),'Model input: raw microscopy'),
            (colorize(np.load(source/'evaluation_only_labels.npy',allow_pickle=False),palette),'Target annotation: evaluator only')]
    for r in rows:
        path=RUN/'llm_trials'/r['trial_id']/f"evaluation_r{r['revision']}_{partition}"/f'seed_{seed:03d}.npy'
        if path.exists():panels.append((colorize(np.load(path,allow_pickle=False),palette),f"{r['trial_id']} r{r['revision']} seed{seed}"))
    cols=min(4,len(panels));nr=int(np.ceil(len(panels)/cols))
    fig,axes=plt.subplots(nr,cols,figsize=(3.1*cols,3.1*nr+.7),squeeze=False)
    for ax in axes.ravel():ax.axis('off')
    for ax,(picture,title) in zip(axes.ravel(),panels):ax.imshow(picture,interpolation='nearest');ax.set_title(title,fontsize=10)
    fig.suptitle(f'{family}: actual independent LLM scripts — {partition} comparison',fontsize=14)
    fig.text(.5,.025,'Native256px grids; physical scale unknown. Phase displays are evaluation figures, never model inputs.\n'+('P3 native1 matrix /5 provisional secondary carbide; microscopy source is HorizontalFlip.' if family=='P3' else 'F1 matrix0 / transverse fiber1 / void2; circle-based contours are approximate.'),ha='center',fontsize=9)
    fig.tight_layout(rect=[0,.08,1,.94]);fig.subplots_adjust(hspace=.28)
    name=f'{family}_{partition}_REFERENCE_GENERATED.png';fig.savefig(RUN/'analysis'/name,dpi=150);plt.close(fig)
    return name


if __name__=='__main__':summarize()
