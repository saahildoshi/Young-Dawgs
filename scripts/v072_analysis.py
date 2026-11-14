"""Descriptive script-level inference and figures bound to real native measurements."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.collections import PolyCollection
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v072_experiment import RUN,DOC,BASE,OLD,TRIALS,now

ORDER=['BASE','P3_OPT_MF_01','P3_OPT_MF_02','P3_OPT_NF_01','P3_OPT_NF_02']
SHORT=['BASE','MF_01','MF_02','NF_01','NF_02']
COLORS=['#444444','#2563eb','#60a5fa','#b45309','#f59e0b']


def stats(values):
    a=np.asarray([v for v in values if v is not None],dtype=float)
    if not a.size:return {'n':0,'mean':None,'sample_sd':None,'median':None,'minimum':None,'maximum':None}
    return {'n':int(a.size),'mean':float(a.mean()),'sample_sd':float(a.std(ddof=1)) if a.size>1 else None,
        'median':float(np.median(a)),'minimum':float(a.min()),'maximum':float(a.max())}


def paired(candidate,baseline):
    rows=[]
    for seed in sorted(set(candidate)&set(baseline)):
        a,b=candidate[seed],baseline[seed]
        if a is not None and b is not None:
            rows.append({'seed':seed,'delta_E_MPa':a-b,'relative_gain':(a-b)/b})
    gains=[r['relative_gain'] for r in rows]
    return {'pairs':rows,'gain_summary':stats(gains),'positive_gain_fraction':float(np.mean(np.array(gains)>0)) if gains else None}


def csv_table(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader()
        writer.writerows({k:json.dumps(v,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in row.items()} for row in rows)


def native_record(trial,seed,level=1,partition='heldout'):
    path=RUN/f'mechanical_response/{trial}_{partition}_{seed}_H{level}_attempt001.json'
    if not path.exists():return None
    row=read(path);return row if row['accepted'] else None


def analyse():
    assert (RUN/'heldout_mechanics_h1/CAMPAIGN.json').exists()
    assert (RUN/'heldout_mechanics_h2/CAMPAIGN.json').exists()
    partition=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json');rows=[];summaries=[];mesh=[];phase=[]
    E={trial:{} for trial in ORDER};E2={trial:{} for trial in ORDER}
    structural={trial:read(RUN/'heldout_structures'/trial/'SUMMARY.json') for trial in ORDER}
    for trial in ORDER:
        for seed in partition['heldout']:
            s=read(RUN/'heldout_structures'/trial/f'seed_{seed}.json');r=native_record(trial,seed)
            E[trial][seed]=None if r is None else r['effective_modulus_MPa']
            b=native_record('BASE',seed)
            delta=None if r is None or b is None else (r['effective_modulus_MPa']-b['effective_modulus_MPa'])/b['effective_modulus_MPa']
            row={'trial_id':trial,'condition':'BASE' if trial=='BASE' else ('MF' if '_MF_' in trial else 'NF'),
                'seed':seed,'attempted':True,'generation_status':s['status'],'structurally_feasible':s['feasibility']['passed'],
                'constraint_failures':s['feasibility']['failures'],'phase_counts':s.get('phase_counts'),
                'reinforcement_fraction':s.get('descriptors',{}).get('reinforcement_fraction'),
                'generation_seconds':s.get('generation_seconds'),'mechanically_accepted':r is not None,
                'apparent_modulus_MPa':None if r is None else r['effective_modulus_MPa'],
                'normalized_objective':None if r is None else r['normalized_effective_modulus'],
                'baseline_relative_gain':delta,'native_RST_sha256':None if r is None else r['native_result_sha256'],
                'source_array_sha256':s.get('array_file_sha256'),'generator_sha256':s['generator_sha256'],
                'visible_error':s.get('visible_error',{}).get('mean'),'hidden_error':s.get('hidden_error',{}).get('mean')}
            for k in ['complete_regions','diameter_mean_px','diameter_std_px','aspect_mean','nearest_neighbor_mean_px','nearest_neighbor_cv','interface_density','matrix_lcc','S2_x_8','S2_y_8']:
                row[k]=s.get('descriptors',{}).get(k)
            rows.append(row)
            if r is not None:
                for material,values in r['phase_results'].items():phase.append({'trial_id':trial,'seed':seed,'mesh_level':1,'material':material,**values})
        pairing=paired(E[trial],E['BASE'])
        subset=[r for r in rows if r['trial_id']==trial]
        summaries.append({'trial_id':trial,'attempted':10,'structurally_feasible':structural[trial]['feasible'],
            'fully_qualified_generator':structural[trial]['fully_qualified_generator'],
            'modulus':stats(E[trial].values()),'normalized_objective':stats([None if v is None else v/1000 for v in E[trial].values()]),
            'paired_gain':pairing['gain_summary'],'positive_gain_fraction':pairing['positive_gain_fraction'],
            'reinforcement_fraction':stats([r['reinforcement_fraction'] for r in subset]),
            'runtime_seconds':stats([r['generation_seconds'] for r in subset]),'diversity':structural[trial]['diversity']})
        for seed in partition['H2']:
            r=native_record(trial,seed,2);b=native_record('BASE',seed,2);a=native_record(trial,seed);a0=native_record('BASE',seed)
            E2[trial][seed]=None if r is None else r['effective_modulus_MPa']
            if r is None or a is None:
                mesh.append({'trial_id':trial,'seed':seed,'status':'NOT_AVAILABLE_INFEASIBLE_OR_NATIVE_FAILURE','H1_E_MPa':None if a is None else a['effective_modulus_MPa'],'H2_E_MPa':None});continue
            e1,e2=a['effective_modulus_MPa'],r['effective_modulus_MPa']
            data={'trial_id':trial,'seed':seed,'status':'ACCEPTED_NATIVE_H2','H1_E_MPa':e1,'H2_E_MPa':e2,
                'relative_mesh_change':abs(e2-e1)/abs(e2),'same_source_geometry':True,
                'H1_native_RST_sha256':a['native_result_sha256'],'H2_native_RST_sha256':r['native_result_sha256']}
            if b is not None and a0 is not None:
                h1=e1-a0['effective_modulus_MPa'];h2=e2-b['effective_modulus_MPa']
                diagnostic=abs(e2-e1)+abs(b['effective_modulus_MPa']-a0['effective_modulus_MPa'])
                data.update(H1_delta_E_MPa=h1,H2_delta_E_MPa=h2,H1_relative_gain=h1/a0['effective_modulus_MPa'],
                    H2_relative_gain=h2/b['effective_modulus_MPa'],gain_change_MPa=h2-h1,
                    conservative_sum_of_observed_mesh_changes_MPa=diagnostic,
                    positive_direction_persists=bool(h1>0 and h2>0),
                    H2_gain_exceeds_observed_changes=bool(h2>diagnostic),
                    interpretation='Observed two-level sensitivity diagnostic, not a rigorous FE bound or statistical interval')
            mesh.append(data)
    arms={}
    for arm in ['MF','NF']:
        members=[r for r in summaries if '_'+arm+'_' in r['trial_id']]
        values=[r['paired_gain']['mean'] for r in members]
        arms[arm]={'independent_scripts':2,'script_level_mean_paired_gains':values,
            'mean_script_gain':float(np.mean(values)) if all(v is not None for v in values) else None,
            'fully_feasible_scripts':sum(r['fully_qualified_generator'] for r in members),
            'H2_subset_script_mean_gains':[paired(E2[r['trial_id']],E2['BASE'])['gain_summary']['mean'] for r in members]}
    advantage=None if any(arms[a]['mean_script_gain'] is None for a in ['MF','NF']) else arms['MF']['mean_script_gain']-arms['NF']['mean_script_gain']
    comparison={'arms':arms,'MF_minus_NF_mean_script_gain':advantage,
        'primary_unit':'Independent returned LLM script; 2 per arm, stochastic seeds nested. Equal weighting of script-level mean paired gains.',
        'inference':'Small descriptive pilot; no p values, no pooled-seed causal significance claim',
        'composition':'Acceptance within ±64 reference pixels, not exact equality for BASE. Report systematic fraction shifts; no geometry-only attribution or guessed correction.',
        'H2_scope':'First three prospectively selected seeds per script only; do not claim all ten converged from this subset.'}
    write(RUN/'optimization_analysis/HELDOUT_RESULTS.json',rows);csv_table(RUN/'optimization_analysis/HELDOUT_RESULTS.csv',rows)
    write(RUN/'optimization_analysis/SCRIPT_SUMMARIES.json',summaries);csv_table(RUN/'optimization_analysis/SCRIPT_SUMMARIES.csv',summaries)
    write(RUN/'optimization_analysis/MF_VERSUS_NF.json',comparison)
    write(RUN/'mesh_confirmation_h2/COMPARISON.json',mesh);csv_table(RUN/'mesh_confirmation_h2/COMPARISON.csv',mesh)
    write(RUN/'optimization_analysis/PHASE_FIELDS.json',phase);csv_table(RUN/'optimization_analysis/PHASE_FIELDS.csv',phase)
    return rows,summaries,comparison,mesh


def baseline_figures():
    folder=RUN/'figures';folder.mkdir(exist_ok=True)
    records=[native_record('BASE',seed,partition='development') for seed in range(1000,1006)]
    assert all(records)
    fig,ax=plt.subplots(figsize=(8,4.8));values=np.array([r['effective_modulus_MPa'] for r in records])
    ax.plot(range(1000,1006),values,'o',color=COLORS[0]);ax.axhline(values.mean(),label=f'Mean {values.mean():.2f} MPa')
    ax.axhspan(values.mean()-values.std(ddof=1),values.mean()+values.std(ddof=1),alpha=.12,label='Within-generator sample SD')
    ax.set(xlabel='Development seed',ylabel='Apparent vertical modulus (MPa)',title='Six actual ANSYS development specimens · H1')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(folder/'BASELINE_VARIABILITY.png',dpi=180);plt.close(fig)
    fig,ax=plt.subplots(figsize=(8,4.8))
    stresses=[]
    for seed,r in zip(range(1000,1006),records):
        ax.plot(np.array(r['engineering_strains'])*100,r['nominal_stresses_MPa'],'o-',lw=1,label=str(seed));stresses.append(r['nominal_stresses_MPa'])
    ax.plot(np.array(records[0]['engineering_strains'])*100,np.mean(stresses,axis=0),'k--',lw=2,label='Mean of 6 specimens')
    ax.set(xlabel='Engineering compression (%)',ylabel='Nominal compressive stress (MPa)',title='Native solved checkpoints · illustrative E=1000/10000 MPa')
    ax.legend(ncol=2);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(folder/'BASELINE_NATIVE_CURVES.png',dpi=180);plt.close(fig)
    write(folder/'BASELINE_PROVENANCE.json',{'figures':{p.name:sha(p) for p in folder.glob('BASELINE_*.png')},
        'actual_native_sources':[{'specimen_id':r['specimen_id'],'RST_sha256':r['native_result_sha256']} for r in records],
        'native_checkpoints_only':True,'aggregate_mean_is_not_individual_solve':True})


def final_figures(rows,summaries,comparison,mesh):
    folder=RUN/'figures';folder.mkdir(exist_ok=True);partition=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json');seed=partition['H2'][0]
    captions={}
    def save(fig,name,caption):
        fig.tight_layout();fig.savefig(folder/name,dpi=180,bbox_inches='tight');plt.close(fig);captions[name]=caption
    fig,ax=plt.subplots(figsize=(12,3.5));ax.axis('off')
    boxes=[(.02,.48,'Frozen B02\n6 development seeds'),(.27,.48,'Actual ANSYS curves\nMF sees / NF withheld'),(.52,.48,'2 MF + 2 NF chats\nOne response each'),(.77,.48,'Freeze four scripts\n50 held-out attempts')]
    for x,y,text in boxes:ax.text(x,y,text,transform=ax.transAxes,ha='left',va='center',bbox=dict(boxstyle='round',fc='#eef2f7',ec='#64748b'),fontsize=11)
    for x in [.22,.47,.72]:ax.annotate('',xy=(x+.04,.48),xytext=(x,.48),xycoords='axes fraction',arrowprops=dict(arrowstyle='->'))
    ax.text(.5,.1,'Structural qualification → native H1 curves → first-three-seed H2 confirmation → script-level comparison',ha='center',transform=ax.transAxes)
    ax.set_title('Registered experiment workflow · schematic, not mechanical data')
    save(fig,'OPTIMIZATION_WORKFLOW.png','Explicit schematic of the registered single-generation experiment; no hypothetical performance data.')
    fig,axes=plt.subplots(1,6,figsize=(15,3))
    reference=np.load(OLD/'references/P3/evaluation_only_labels.npy',allow_pickle=False)
    for ax,trial,title in zip(axes,['REFERENCE']+ORDER,['P3 reference']+SHORT):
        path=RUN/'heldout_structures'/trial/f'seed_{seed}.npy'
        if trial=='REFERENCE':array=reference;state='annotation'
        elif path.exists():
            array=np.load(path,allow_pickle=False);state='feasible' if read(path.with_suffix('.json'))['feasibility']['passed'] else 'INFEASIBLE'
        else:ax.text(.5,.5,'No output',ha='center');ax.axis('off');continue
        ax.imshow(array==5,cmap=ListedColormap(['#440154','#fde725']),vmin=0,vmax=1,interpolation='nearest')
        ax.set_title(title+'\n'+state,fontsize=10);ax.axis('off')
    fig.suptitle(f'Prospectively selected seed {seed} · native labels 1 matrix / 5 reinforcement · equal pixel scale')
    save(fig,'REFERENCE_AND_GENERATED_GEOMETRY.png','Actual P3 annotation and executed generated arrays at the first confirmation seed. Annotation remains evaluator-only; no physical microscopy calibration.')
    fig,ax=plt.subplots(figsize=(9,5))
    for i,(trial,title,color) in enumerate(zip(ORDER,SHORT,COLORS)):
        values=[r['apparent_modulus_MPa'] for r in rows if r['trial_id']==trial and r['mechanically_accepted']]
        offsets=np.linspace(-.12,.12,len(values)) if values else []
        ax.scatter(i+np.array(offsets),values,color=color,s=35)
        if values:ax.errorbar(i,np.mean(values),yerr=np.std(values,ddof=1) if len(values)>1 else 0,fmt='k_',capsize=5)
        ax.text(i,.02,f'{len(values)}/10',transform=ax.get_xaxis_transform(),ha='center',fontsize=9)
    ax.set_xticks(range(5),SHORT);ax.set(ylabel='Apparent vertical modulus (MPa)',title='Held-out native H1 responses · points are seeds nested within scripts')
    ax.grid(axis='y',alpha=.2);save(fig,'HELDOUT_STIFFNESS.png','Actual accepted H1 measurements only; denominators include all ten attempts per script. Markers show individual seeds, black mean ± sample SD.')
    fig,ax=plt.subplots(figsize=(9,5))
    for trial,color,title in zip(ORDER[1:],COLORS[1:],SHORT[1:]):
        data=[r for r in rows if r['trial_id']==trial and r['baseline_relative_gain'] is not None]
        ax.plot([r['seed'] for r in data],[100*r['baseline_relative_gain'] for r in data],'o-',color=color,label=title)
    ax.axhline(0,color='k',lw=.8);ax.set(xlabel='Common evaluator-only seed',ylabel='Paired apparent-stiffness gain (%)',title='Paired seed-level gain relative to frozen BASE · H1')
    ax.legend();ax.grid(alpha=.2);save(fig,'PAIRED_OBJECTIVE_GAINS.png','Common-seed pairs only when both native measurements are valid; no identical-particle or independent-LLM-trial interpretation.')
    fig,ax=plt.subplots(figsize=(8,4.8))
    for i,(s,color,title) in enumerate(zip(summaries[1:],COLORS[1:],SHORT[1:])):
        value=s['paired_gain']['mean']
        if value is None:ax.text(i,0,'NA',ha='center');continue
        ax.bar(i,100*value,color=color,width=.65)
        ax.text(i,100*value,f'{s["paired_gain"]["n"]} valid pairs\n{s["structurally_feasible"]}/10 feasible',ha='center',va='bottom',fontsize=8)
    ax.set_xticks(range(4),SHORT[1:]);ax.set(ylabel='Mean paired gain (%)',title='Four independent revised scripts · two MF and two NF')
    ax.axhline(0,color='k',lw=.8);ax.grid(axis='y',alpha=.2)
    save(fig,'FEEDBACK_VERSUS_CONTROL.png','One bar per genuine independent response. Means over nested seed pairs are descriptive; no pooled-seed significance or universal feedback effect.')
    fig,ax=plt.subplots(figsize=(9,5))
    for trial,color,title in zip(ORDER,COLORS,SHORT):
        r=native_record(trial,seed)
        if r:ax.plot(np.array(r['engineering_strains'])*100,r['nominal_stresses_MPa'],'o-',color=color,label=title)
    ax.set(xlabel='Engineering compression (%)',ylabel='Nominal compressive stress (MPa)',title=f'Actual native confirmation curves · seed {seed} · H1');ax.legend();ax.grid(alpha=.2)
    save(fig,'FULL_NATIVE_CONFIRMATION_CURVES.png','Five actual solved checkpoints per available selected specimen; no synthetic origin or extrapolated nonlinear curve.')
    fig,axes=plt.subplots(1,2,figsize=(12,4.8))
    for trial,title,color in zip(ORDER,SHORT,COLORS):
        data=[r for r in mesh if r['trial_id']==trial and r['H2_E_MPa'] is not None]
        axes[0].scatter([r['H1_E_MPa'] for r in data],[r['H2_E_MPa'] for r in data],color=color,label=title)
        if trial!='BASE':axes[1].scatter([100*r['H1_relative_gain'] for r in data if 'H1_relative_gain' in r],[100*r['H2_relative_gain'] for r in data if 'H2_relative_gain' in r],color=color,label=title)
    for ax in axes:
        low=min(ax.get_xlim()[0],ax.get_ylim()[0]);high=max(ax.get_xlim()[1],ax.get_ylim()[1]);ax.plot([low,high],[low,high],'k--',lw=.8);ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[0].set(xlabel='H1 apparent modulus (MPa)',ylabel='H2 apparent modulus (MPa)',title='Same categorical geometry')
    axes[1].set(xlabel='H1 paired gain (%)',ylabel='H2 paired gain (%)',title='Prospectively selected first three seeds')
    save(fig,'REFINED_MESH_CONFIRMATION.png','Actual matched H1/H2 data for the registered subset; diagonal is equality, not an error bound or proof of complete convergence.')
    fig,axes=plt.subplots(1,3,figsize=(14,4.4))
    metrics=[('reinforcement_fraction','Reinforcement fraction'),('aspect_mean','Complete-region mean aspect'),('nearest_neighbor_mean_px','Nearest-neighbor spacing (px)')]
    for ax,(metric,label) in zip(axes,metrics):
        for trial,color,title in zip(ORDER,COLORS,SHORT):
            data=[r for r in rows if r['trial_id']==trial and r['mechanically_accepted'] and r[metric] is not None]
            ax.scatter([r[metric] for r in data],[r['apparent_modulus_MPa'] for r in data],label=title,color=color,s=24,alpha=.8)
        ax.set(xlabel=label,ylabel='Apparent E (MPa)');ax.grid(alpha=.2)
    axes[0].axvline(read(RUN/'protocol/PROTOCOL.json')['reference_fraction'],color='k',ls='--',lw=.7)
    axes[-1].legend(fontsize=8);save(fig,'COMPOSITION_MORPHOLOGY_TRADEOFFS.png','Actual H1 mechanics and evaluator morphology. Associations are descriptive, not isolated causal morphology effects; no guessed fraction correction.')
    field_sources=[]
    for trial in ORDER:
        r=native_record(trial,seed,2)
        if r is None:field_sources.append(None);continue
        d=Path(r['independent_readback_directory']);fields=np.loadtxt(d/'fields.csv',delimiter=',');nodes=np.loadtxt(d/'nodes.csv',delimiter=',')
        field_sources.append((r,fields,nodes))
    existing=[x for x in field_sources if x]
    if existing:
        syy_limit=max(float(np.percentile(np.abs(x[1][:,3]),99.5)) for x in existing)
        seq_limit=max(float(np.percentile(x[1][:,5],99.5)) for x in existing)
        umag_limit=max(float(np.linalg.norm(x[2][:,3:5],axis=1).max()) for x in existing)
        fig,axes=plt.subplots(4,5,figsize=(16,11),gridspec_kw={'height_ratios':[1,1,1,.8]})
        images=[None,None,None]
        for i,(item,title) in enumerate(zip(field_sources,SHORT)):
            if item is None:
                for ax in axes[:,i]:ax.axis('off')
                axes[0,i].text(.5,.5,'No accepted H2\nselected specimen',ha='center');continue
            r,f,n=item;ny=int(np.sqrt(len(f)))
            fields=[f[:,3].reshape(ny,ny),f[:,5].reshape(ny,ny),np.linalg.norm(n[:,3:5],axis=1).reshape(ny+1,ny+1)]
            for j,(values,cmap,limits) in enumerate(zip(fields,['coolwarm','magma','viridis'],[(-syy_limit,syy_limit),(0,seq_limit),(0,umag_limit)])):
                images[j]=axes[j,i].imshow(values,origin='lower',extent=[0,1,0,1],interpolation='nearest',cmap=cmap,vmin=limits[0],vmax=limits[1]);axes[j,i].set_xticks([]);axes[j,i].set_yticks([])
            axes[0,i].set_title(title+' · H2',fontsize=10)
            energy=[r['phase_results'][str(k)]['elastic_energy_fraction'] for k in [1,2]]
            axes[3,i].bar(['Matrix','Reinf.'],energy,color=['#440154','#fde725']);axes[3,i].set_ylim(0,1);axes[3,i].tick_params(labelsize=8)
        for j,label in enumerate(['SYY (MPa)','Equivalent stress (MPa)','Native |U| (mm)']):
            axes[j,0].set_ylabel(label,fontsize=9)
            if images[j] is not None:fig.colorbar(images[j],ax=list(axes[j,:]),fraction=.014,pad=.015)
        axes[3,0].set_ylabel('Elastic energy share')
        fig.suptitle(f'Actual native fields · seed {seed} · 0.5% compression · illustrative elastic constituents',y=.995)
        # Explicit axes spacing avoids tight_layout moving shared colorbars into data.
        fig.subplots_adjust(left=.065,right=.91,bottom=.06,top=.955,wspace=.15,hspace=.18)
        fig.savefig(folder/'NATIVE_MECHANICAL_FIELDS.png',dpi=180,bbox_inches='tight');plt.close(fig)
        captions['NATIVE_MECHANICAL_FIELDS.png']='H2 native element-associated SYY/SEQV, native nodal displacement norm, and native phase energy shares. Common stress limits use max per-specimen absolute/SEQV 99.5 percentiles; clipping disclosed, full extremes remain in raw fields. No cross-phase stress averaging, no failure interpretation.'
        fig,axes=plt.subplots(1,5,figsize=(16,3.8));derived=[]
        for ax,item,title in zip(axes,field_sources,SHORT):
            if item is None:ax.text(.5,.5,'No accepted H2',ha='center');ax.axis('off');continue
            r,f,n=item;post=Path(r['independent_readback_directory'])
            connectivity=np.loadtxt(post/'connectivity.csv',delimiter=',')[:,1:].astype(int)-1
            deformed=n[:,1:3]+n[:,3:5]
            out=BASE/'derived_fields'/r['specimen_id'];out.mkdir(parents=True,exist_ok=True)
            np.save(out/'true_scale_deformed_xy.npy',deformed,allow_pickle=False)
            derived.append({'specimen_id':r['specimen_id'],'mesh_level':2,'derived_from_native_nodes_sha256':sha(post/'nodes.csv'),
                'deformation_scale_factor':1,'deformed_coordinate_path':str(out/'true_scale_deformed_xy.npy'),'sha256':sha(out/'true_scale_deformed_xy.npy')})
            poly=PolyCollection(deformed[connectivity],array=f[:,1]-1,cmap=ListedColormap(['#440154','#fde725']),clim=(0,1),edgecolors='none',antialiased=False,rasterized=True)
            ax.add_collection(poly);ax.plot([0,1,1,0,0],[0,0,1,1,0],'k--',lw=.7)
            ax.set(xlim=(-.008,1.008),ylim=(-.008,1.008),aspect='equal',title=title+' · H2',xlabel='Computational x (mm)')
        axes[0].set_ylabel('Computational y (mm)');fig.suptitle('Actual native displacement · deformation scale 1× · dashed = undeformed boundary')
        save(fig,'TRUE_SCALE_DEFORMED_GEOMETRY.png','Actual node coordinates plus native UX/UY, deformation scale1. Computational dimensions are not microscopy calibration. No magnification or large-strain claim.')
        write(folder/'DEFORMED_COORDINATE_PROVENANCE.json',derived)
    write(folder/'FIGURE_MANIFEST.json',{'created_utc':now(),'figures':[{'path':name,'sha256':sha(folder/name),'caption':caption} for name,caption in captions.items()],
        'baseline_figures':'BASELINE_PROVENANCE.json','source_tables':{str(p.relative_to(RUN)):sha(p) for p in (RUN/'optimization_analysis').glob('*.json')},
        'native_RSTs':[{'specimen_id':r['specimen_id'],'mesh_level':r['mesh_level'],'sha256':r['native_result_sha256']} for r in [read(p) for p in (RUN/'mechanical_response').glob('*.json')] if r['accepted']],
        'phase_colors':{'1':'#440154','5':'#fde725'},'illustrative_materials_MPa':[1000,10000],'unknown_microscopy_pixel_scale':True})


if __name__=='__main__':baseline_figures()
