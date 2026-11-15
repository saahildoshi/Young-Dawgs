"""Join actual geometry and native mechanics and render the development evidence."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v073_experiment import RUN,DOC,PREV,REFERENCE,now
from scripts.v073_analysis import statistics,csv_table
from metamaterial_eval.composites.morphology_v073 import flattened
from scripts.v073_figures import COLORS as PHASE_COLORS

FAMILIES=['BASE','V1_ELONGATION','V2_VERTICAL','V3_HORIZONTAL','V4_DISPERSION']
COLORS=['#365a7d','#9d5935','#b36c16','#497f62','#80568b']

def report():
    h1=read(RUN/'development_mechanics_h1/CAMPAIGN.json')['cases'];h2=read(RUN/'development_mechanics_h2/CAMPAIGN.json')['cases']
    rows=[];curves=[];models=[]
    for r in h1:
        source=RUN/'controlled_variants'/r['trial_id']/f"seed_{r['seed']}.json";s=read(source)
        row={**r,'phase_counts':s['phase_counts'],'generator_sha256':s['generator_sha256'],
            'source_array_sha256':s['source_array_sha256'],'generation_seconds':s['generation_seconds'],
            **{k:v for k,v in s['descriptors'].items() if k not in ['detail','working_map']},**flattened(s['morphology_v073'])}
        ref=next((v for v in h2 if v['trial_id']==r['trial_id'] and v['seed']==r['seed']),None)
        row['H2_modulus_MPa']=ref['apparent_modulus_MPa'] if ref else None
        row['relative_mesh_change']=abs(row['H2_modulus_MPa']-r['apparent_modulus_MPa'])/r['apparent_modulus_MPa'] if row['H2_modulus_MPa'] is not None and r['apparent_modulus_MPa'] is not None else None
        row['J']=r['apparent_modulus_MPa']/1000 if r['apparent_modulus_MPa'] is not None else None
        rows.append(row)
    for path in sorted((RUN/'mechanical_response').glob('*.json')):
        native=read(path);models.append(native)
        for curve in native['native_curve']:
            curves.append({'specimen_id':native['specimen_id'],'mesh_level':native['mesh_level'],
                **dict(zip(native['curve_columns'],curve)),'achieved_compression':abs(curve[2]),'nominal_compressive_stress_MPa':abs(curve[5])})
    summaries={t:{'attempted':sum(r['trial_id']==t for r in rows),
        'accepted':sum(r['trial_id']==t and r['status']=='ACCEPTED_NATIVE_RESULT' for r in rows),
        'modulus':statistics([r['apparent_modulus_MPa'] for r in rows if r['trial_id']==t and r['apparent_modulus_MPa'] is not None])} for t in FAMILIES}
    write(RUN/'development_mechanics/GEOMETRY_MECHANICS.json',rows);csv_table(RUN/'development_mechanics/GEOMETRY_MECHANICS.csv',rows)
    write(RUN/'development_mechanics/SUMMARIES.json',summaries);csv_table(RUN/'development_mechanics/ACTUAL_NATIVE_CURVES.csv',curves)
    accepted=[r for r in rows if r['apparent_modulus_MPa'] is not None]
    metrics=['all_observed.area_weighted_aspect','all_observed.vertical_alignment','long_range_abs_S2_difference','nearest_neighbor_cv']
    associations={key:{'n':len(accepted),'Pearson_diagnostic':float(np.corrcoef([r[key] for r in accepted],[r['apparent_modulus_MPa'] for r in accepted])[0,1]),
        'interpretation':'Pooled descriptive association across a small controlled probe matrix; covarying geometry/RNG prevents isolated causal interpretation; no significance claim'} for key in metrics}
    write(RUN/'development_mechanics/ASSOCIATIONS.json',associations)
    body='# Controlled geometry–mechanics development dataset\n\nEighteen registered source arrays were generated: six baseline and three each in four researcher-designed probe families. Every source has exactly20,731 reinforcement pixels. One baseline seed3104 fails the frozen2px diagnostic-dilation x-spanning rule; its source is preserved, not repaired or replaced, and no mechanics is assigned. All12 variant sources pass. These are researcher probes, not genuine LLM revision trials.\n\n'
    body+='| Family | Accepted native H1 / attempts | Mean MPa | Sample SD MPa | Min–max MPa |\n|---|---:|---:|---:|---|\n'
    for trial,r in summaries.items():
        s=r['modulus'];body+=f"| {trial} | {r['accepted']}/{r['attempted']} | {s['mean']:.6f} | {s['sample_SD']:.6f} | {s['min']:.6f}–{s['max']:.6f} |\n"
    body+='\nAll accepted cases use five actual solved strain levels0.1–0.5% and independent RST readbacks. The first registered development seed in all five families also receives H2. The original qualified source/evaluator is unchanged. Shapes, spatial placement and RNG trajectories covary, so the measured relationships are not isolated single-variable causal estimates. Horizontal loading was not registered/executed. H1/H2 preserve exact categorical geometry; observed changes are not an asymptotic error bound. Baseline mechanics describe5/6 feasible survivors and cannot establish perfect baseline reliability.\n'
    body+='\n| Descriptor | Pooled Pearson diagnostic | n |\n|---|---:|---:|\n'+''.join(f"| {k} | {r['Pearson_diagnostic']:+.4f} | {r['n']} |\n" for k,r in associations.items())
    (DOC/'V0_7_3_CONTROLLED_GEOMETRY_MECHANICS.md').write_text(body,encoding='utf-8',newline='\n')
    folder=RUN/'figures';manifest=[]
    def save(fig,name,caption):
        fig.tight_layout();fig.savefig(folder/name,dpi=160);plt.close(fig)
        manifest.append({'path':name,'caption':caption,'sha256':sha(folder/name)})
    fig,axes=plt.subplots(2,3,figsize=(12,7))
    for ax,seed in zip(axes.flat,range(3000,3006)):
        ax.imshow(np.load(RUN/'envelope_calibration'/f'seed_{seed}.npy')==5,cmap=PHASE_COLORS,vmin=0,vmax=1,interpolation='nearest')
        ax.set(title=f'Exact baseline seed{seed} · count20,731');ax.set_xticks([]);ax.set_yticks([])
    save(fig,'EXACT_COMPOSITION_BASELINE.png','First six of twelve registered calibration seeds; unchanged finite pixel scale, no physical scale inference.')
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    challenge=read(RUN/'historical_lane_controls/CHALLENGE_RESULTS.json');ref=read(RUN/'envelope_calibration/REFERENCE.json')
    for ax,key,title in zip(axes,['all_observed.area_weighted_aspect','all_observed.axial_order','limited_gap_run_y'],['Area-weighted aspect','Anisotropy-weighted axial order','Limited-gap vertical run / height']):
        for i,trial in enumerate(['BASE','P3_OPT_MF_01','P3_OPT_MF_02','P3_OPT_NF_01','P3_OPT_NF_02']):
            vals=[flattened(r['morphology_v073'])[key] for r in challenge if r['trial_id']==trial]
            ax.scatter(np.full(len(vals),i),vals,s=15,alpha=.6)
        ax.axhline(flattened(ref['morphology_v073'])[key],color='k',ls='--',label='P3 annotation')
        ax.axhline(read(RUN/'protocol/FEASIBILITY_FROZEN.json')['new_descriptor_bounds'][key][1],color='r',ls=':',label='New upper limit')
        ax.set(title=title,xticks=range(5),xticklabels=['Old BASE','Old MF1','Old MF2','Old NF1','Old NF2']);ax.tick_params(axis='x',rotation=35)
    axes[0].legend(fontsize=8);save(fig,'HISTORICAL_CHALLENGE_DIAGNOSTICS.png','Already-observed historical challenge set; new prospective diagnostics do not reclassify historical acceptance.')
    fig,axes=plt.subplots(2,3,figsize=(13,7))
    for ax,trial,color in zip(axes.flat,FAMILIES,COLORS):
        for model in models:
            if model['mesh_level']!=1 or not model['specimen_id'].startswith(trial+'_development_'):continue
            seed=int(model['specimen_id'].split('_')[-1]);marker={3100:'o',3101:'s',3102:'^',3103:'D',3105:'x'}[seed]
            ax.plot(np.array(model['engineering_strains'])*100,model['nominal_stresses_MPa'],marker=marker,color=color,alpha=.8,label=str(seed))
        ymax=max(max(r['nominal_stresses_MPa']) for r in models if r['mesh_level']==1)*1.05
        ax.set(title=trial,xlabel='Actual engineering compression (%)',ylabel='Nominal compressive stress (MPa)',ylim=(0,ymax),xlim=(.08,.52));ax.legend(title='Seed',fontsize=8);ax.grid(alpha=.2)
    axes.flat[-1].axis('off');axes.flat[-1].text(.05,.7,'Actual native solved checkpoints only.\n17 H1 curves; one infeasible BASE omitted\nfrom mechanics with denominator preserved.\nNo synthetic origin or extrapolated curve.',va='top')
    save(fig,'ACTUAL_DEVELOPMENT_CURVES.png','All17 accepted H1 five-checkpoint responses, individually identified by family and seed; illustrative linear elasticity.')
    fig,axes=plt.subplots(1,3,figsize=(13,4))
    for ax,key,label in zip(axes,metrics[:3],['Area-weighted aspect','Vertical axial alignment','Long-range absolute S2 difference']):
        for trial,color in zip(FAMILIES,COLORS):
            local=[r for r in accepted if r['trial_id']==trial]
            ax.scatter([r[key] for r in local],[r['apparent_modulus_MPa'] for r in local],color=color,label=trial)
        ax.set(xlabel=label,ylabel='Native H1 apparent E (MPa)');ax.grid(alpha=.2)
    axes[-1].legend(fontsize=7);save(fig,'GEOMETRY_MECHANICS_ASSOCIATIONS.png','Actual17 accepted measurements; descriptive associations, not controlled single-descriptor causal effects.')
    target=read(RUN/'target_selection/TARGET_FROZEN.json')
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for i,(trial,color) in enumerate(zip(FAMILIES,COLORS)):
        vals=[r['apparent_modulus_MPa'] for r in accepted if r['trial_id']==trial]
        axes[0].scatter(np.full(len(vals),i),vals,color=color);axes[0].plot(i,np.mean(vals),'k_',ms=20)
    axes[0].set(xticks=range(5),xticklabels=['BASE','Elongation','Vertical','Horizontal','Dispersion'],ylabel='Actual native H1 E (MPa)',title='Measured development range');axes[0].tick_params(axis='x',rotation=20)
    b=target['baseline_mean_MPa'];g=target['difficulty_threshold_MPa']
    axes[0].axhline(b,color='k',ls='--',lw=.8);axes[0].axhspan(b-g,b+g,color='grey',alpha=.1,label='Registered difficulty separation')
    proposal=target['proposed_target_MPa']
    if proposal is not None:axes[0].axhline(proposal,color='r',ls=':',label='Proposed target '+('accepted' if target['qualified_target'] else 'rejected'))
    axes[0].legend(fontsize=8)
    for pair,color in zip(target['development_mesh_pairs'],COLORS):
        axes[1].plot([1,2],[pair['H1'],pair['H2']],'o-',label=pair['trial_id'],color=color)
    axes[1].set(xticks=[1,2],xticklabels=['H1','H2'],ylabel='Actual E (MPa)',title='Same first-seed geometries, refined mesh');axes[1].legend(fontsize=8)
    save(fig,'TARGET_SELECTION_AND_MESH_CHECKS.png','Actual development distributions, prospectively required separation and all five first-seed H2 checks; no target invented if gate fails.')
    write(folder/'DEVELOPMENT_FIGURE_MANIFEST.json',{'created_utc':now(),'figures':manifest,
        'geometry_mechanics_table_sha256':sha(RUN/'development_mechanics/GEOMETRY_MECHANICS.json'),
        'native_results':{p.name:sha(p) for p in (RUN/'mechanical_response').glob('*.json')}})

if __name__=='__main__':report()
