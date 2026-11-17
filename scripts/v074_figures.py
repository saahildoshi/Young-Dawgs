"""Actual specimen comparisons and native-result plots; fixed first-seed selection."""
import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.collections import PolyCollection
from PIL import Image
from scripts.v070_protocol import read, write, sha
from scripts.v074_experiment import RUN, MICRO, now

COLORS = ListedColormap(['#2d4664', '#ebaa37'])
DEST = RUN / 'figures'


def geometry():
    DEST.mkdir(exist_ok=True)
    refpath = MICRO / 'references/P3/evaluation_only_labels.npy'
    rawpath = MICRO / 'references/P3/microscopy_input.png'
    reference = np.load(refpath) == 5
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.7))
    axes[0].imshow(Image.open(rawpath)); axes[0].set_title('Supplied horizontally flipped SEM tile')
    axes[1].imshow(reference, cmap=COLORS, vmin=0, vmax=1, interpolation='nearest')
    axes[1].set_title('Evaluator-only native labels 1 / 5')
    for ax in axes: ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle('P3 · microscopy input and evaluation annotation')
    fig.text(.5, .025, 'Morphology-selected crop; provisional label 5 chemistry; no physical pixel calibration.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.94)); fig.savefig(DEST / 'P3_RAW_REFERENCE_AND_MASK.png', dpi=170); plt.close(fig)
    sources = {str(p): sha(p) for p in (refpath, rawpath)}
    for arm in ('IF', 'NF'):
        fig, axes = plt.subplots(4, 3, figsize=(10, 13))
        for i in range(4):
            trial = f'{arm}_{i+1:02d}'
            arrays = [reference]
            captions = ['Reference annotation']
            for revision in (0, 1):
                path = RUN / 'structures' / trial / f'r{revision}' / 'heldout/seed_5000.npy'
                s = read(path.with_suffix('.json'))
                arrays.append(np.load(path) == 5 if path.exists() else None)
                captions.append(f'{trial} {"initial" if revision == 0 else "revised"} · 5000\n' + ('Morphology PASS' if s['feasibility']['passed'] else 'FAIL: preserved attempt'))
                if path.exists(): sources[str(path)] = sha(path)
            for ax, a, caption in zip(axes[i], arrays, captions):
                if a is not None: ax.imshow(a, cmap=COLORS, vmin=0, vmax=1, interpolation='nearest')
                else: ax.text(.5,.5,'Generation failed',ha='center',va='center')
                ax.set_title(caption, fontsize=10); ax.set_xticks([]); ax.set_yticks([])
        fig.suptitle(f'P3 {arm} · actual reference and genuine initial/revised held-out outputs', fontsize=13)
        fig.text(.5,.012,'Fixed first held-out seed for every script; identical field/pixel scale. Matrix 1 blue; provisional reinforcement 5 gold.',ha='center',fontsize=9)
        fig.tight_layout(rect=(0,.03,1,.965)); fig.savefig(DEST / f'P3_{arm}_REFERENCE_INITIAL_REVISED.png', dpi=170); plt.close(fig)
    write(DEST / 'GEOMETRY_FIGURE_PROVENANCE.json', {
        'created_utc': now(), 'selection': 'First registered held-out seed 5000 for every initial/revised module; no outcome-based selection',
        'source_files': sources, 'masks_supplied_to_LLM': False,
        'no_physical_scale_inferred': True, 'no_reference_or_generated_array_modifications': True})


def mechanical():
    analysis = RUN / 'target_property_analysis'
    summaries = read(analysis / 'SCRIPT_SUMMARIES.json')
    changes = read(analysis / 'WITHIN_CONVERSATION_CHANGES.json')
    mesh = read(analysis / 'MESH_CONFIRMATION.json')
    curves = read(analysis / 'NATIVE_CURVES.json')
    morphology = read(analysis / 'MORPHOLOGY.json')
    descriptor_summary = read(analysis / 'MORPHOLOGY_REFERENCE_COMPARISON.json')
    order = read(RUN / 'protocol/PROTOCOL.json')['trial_order']
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    for ax, arm, color in zip(axes, ('IF', 'NF'), ('#355f8a', '#b7772e')):
        trials = [t for t in order if t.startswith(arm)]
        for i, trial in enumerate(trials):
            pair = [next(s for s in summaries if s['trial_id'] == trial and s['revision'] == rev) for rev in (0,1)]
            errors = [s['target_error']['mean'] * 100 if s['target_error']['mean'] is not None else np.nan for s in pair]
            ax.plot((i-.15,i+.15), errors, '-', color=color, alpha=.7)
            ax.scatter(i-.15, errors[0], marker='o', color=color)
            ax.scatter(i+.15, errors[1], marker='s', color=color)
            for x, y, s in zip((i-.15,i+.15),errors,pair):
                ax.annotate(f"{s['mechanically_accepted']}/6",(x,y),xytext=(0,8),textcoords='offset points',ha='center',fontsize=8)
        ax.set_xticks(range(4), trials); ax.set_title(arm + ' · circle initial / square revised')
        ax.set_ylabel('Mean absolute relative target error (%)'); ax.grid(axis='y', alpha=.2)
        ax.set_ylim(bottom=0)
    fig.suptitle('P3 target 1640 MPa · each connected pair is one conversation')
    fig.text(.5,.015,'Conditional on accepted outputs; full attempted denominator shown. NF_01 includes a recorded extra nonscientific turn.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.93)); fig.savefig(DEST / 'P3_PAIRED_SCRIPT_TARGET_ERRORS.png',dpi=170);plt.close(fig)
    fig, axes = plt.subplots(2,2,figsize=(12,8))
    descriptors = [('diameter_std_px','Complete-region diameter SD (pixels)'),
        ('all_observed.area_weighted_aspect','All-observed area-weighted aspect'),
        ('nearest_neighbor_cv','Complete-region nearest-neighbor CV'),
        ('all_observed.axial_order','All-observed anisotropy-weighted axial order')]
    for ax,(key,label) in zip(axes.flat,descriptors):
        reference=next(r['reference_value'] for r in descriptor_summary if r['descriptor']==key)
        ax.axhline(reference,ls='--',color='#555555',lw=1,label='Reference annotation')
        for i,trial in enumerate(order):
            for revision,offset,marker in [(0,-.14,'o'),(1,.14,'s')]:
                values=[r[key] for r in morphology if r['trial_id']==trial and r['revision']==revision and r['feasible']]
                if values:
                    color='#355f8a' if trial.startswith('IF') else '#b7772e'
                    ax.scatter(i+offset+np.linspace(-.035,.035,len(values)),values,marker=marker,color=color,alpha=.45,s=17)
                    ax.plot([i+offset-.06,i+offset+.06],[np.mean(values)]*2,color=color,lw=2)
        ax.set_xticks(range(8),order,rotation=45);ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
        ax.legend(fontsize=8)
    fig.suptitle('Actual held-out morphology · circle initial / square revised · blue IF / ochre NF')
    fig.text(.5,.01,'All generated arrays pass the fixed envelope; reference differences remain. Pixel descriptors do not imply a physical scale.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(DEST/'P3_MORPHOLOGY_REFERENCE_COMPARISON.png',dpi=170);plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 9), sharex=True, sharey=True)
    for i, arm in enumerate(('IF','NF')):
        for revision in (0,1):
            ax = axes[i,revision]
            trials = [t for t in order if t.startswith(arm)]
            for trial, color in zip(trials, plt.get_cmap('tab10').colors[:4]):
                selected = [r for r in curves if r['trial_id'] == trial and r['revision'] == revision and r['mesh_level'] == 1]
                for seed in range(5000,5006):
                    cs = [r for r in selected if r['seed'] == seed]
                    if cs: ax.plot([r['engineering_compression']*100 for r in cs],[r['nominal_compression_MPa'] for r in cs],color=color,alpha=.22,lw=.8)
                if selected:
                    means = [np.mean([r['nominal_compression_MPa'] for r in selected if r['step'] == step]) for step in range(1,6)]
                    ax.plot(np.arange(1,6)*.1,means,color=color,label=trial,lw=1.7)
            ax.plot(np.arange(1,6)*.1,1640*np.arange(1,6)*.001,'k--',lw=1,label='1640 MPa target')
            ax.set_title(f'{arm} {"initial" if revision == 0 else "revised"} · accepted H1 only')
            ax.set_xlabel('Engineering compression (%)');ax.set_ylabel('Nominal compression stress (MPa)')
            ax.legend(fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Actual five-checkpoint ANSYS stress–strain curves · faint specimens, solid script means')
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(DEST/'P3_ACTUAL_HELDOUT_STRESS_STRAIN.png',dpi=170);plt.close(fig)
    fig, axes = plt.subplots(1,2,figsize=(13,5))
    for i,trial in enumerate(order):
        for revision,offset,marker in [(0,-.14,'o'),(1,.14,'s')]:
            local = [r for r in mesh if r['trial_id'] == trial and r['revision'] == revision and r['relative_mesh_change'] is not None]
            for r in local:
                axes[0].scatter(i+offset,100*r['relative_mesh_change'],marker=marker,color='#355f8a' if trial.startswith('IF') else '#b7772e',alpha=.7)
            if local:
                h1 = np.mean([r['H1_target_error'] for r in local])*100
                h2 = np.mean([r['H2_target_error'] for r in local])*100
                axes[1].plot((i+offset-.04,i+offset+.04),(h1,h2),'-',color='#555555')
                axes[1].scatter(i+offset-.04,h1,facecolors='none',edgecolors='#355f8a',marker=marker)
                axes[1].scatter(i+offset+.04,h2,color='#b7772e',marker=marker)
    axes[0].axhline(2,color='red',ls='--',lw=1,label='Registered 2% tolerance');axes[0].legend(fontsize=8)
    axes[0].set_ylabel('|H2 − H1| / H1 (%)');axes[0].set_title('Every preselected refinement · circle initial / square revised')
    axes[1].set_ylabel('Mean absolute target error on refined seeds (%)');axes[1].set_title('Open H1 / filled H2 · same available seeds only')
    for ax in axes:
        ax.set_xticks(range(8),order,rotation=45);ax.grid(axis='y',alpha=.2);ax.set_ylim(bottom=0)
    fig.suptitle('P3 balanced first-two-seed mesh sensitivity · no replacement of failed NF_03 initial seed 5001')
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(DEST/'P3_H1_H2_TARGET_SENSITIVITY.png',dpi=170);plt.close(fig)
    # Native fields use fixed first conversation in each arm and first seed.
    records=[]
    for trial in ('IF_01','NF_01'):
        for revision in (0,1):
            r=read(RUN/'mechanical_response'/f'{trial}_r{revision}_heldout_5000_H1_attempt001.json')
            path=Path(r['independent_readback_directory'])
            f=np.loadtxt(path/'fields.csv',delimiter=',');n=np.loadtxt(path/'nodes.csv',delimiter=',')
            q=np.loadtxt(path/'connectivity.csv',delimiter=',').astype(int)[:,1:]-1
            records.append((trial,revision,r,f,n,q))
    equivalent=max(float(np.percentile(f[:,5],99.5)) for _,_,_,f,_,_ in records)
    axial=max(float(np.percentile(np.abs(f[:,7]),99.5)) for _,_,_,f,_,_ in records)
    fig,axes=plt.subplots(2,4,figsize=(14,7))
    images=[None,None]
    for i,(trial,revision,r,f,n,q) in enumerate(records):
        for j,values,cmap,vmin,vmax in [(0,f[:,5],'magma',0,equivalent),(1,f[:,7],'coolwarm',-axial,axial)]:
            images[j]=axes[j,i].imshow(values.reshape(256,256),origin='lower',extent=(0,1,0,1),cmap=cmap,vmin=vmin,vmax=vmax,interpolation='nearest')
            axes[j,i].set_xticks([]);axes[j,i].set_yticks([])
        axes[0,i].set_title(f'{trial} {"initial" if revision == 0 else "revised"}',fontsize=10)
    axes[0,0].set_ylabel('Equivalent stress (MPa)');axes[1,0].set_ylabel('Signed axial strain EYY')
    fig.suptitle('Actual native H1 element fields · first trial in each arm / seed 5000 / 0.5% compression')
    fig.subplots_adjust(left=.05,right=.91,top=.90,bottom=.06,wspace=.12,hspace=.15)
    for j in (0,1):
        pos=axes[j,-1].get_position();cax=fig.add_axes([.935,pos.y0,.012,pos.height]);fig.colorbar(images[j],cax=cax)
    fig.savefig(DEST/'P3_ACTUAL_NATIVE_STRESS_AND_STRAIN.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(1,4,figsize=(14,4))
    for ax,(trial,revision,r,f,n,q) in zip(axes,records):
        displaced=n[:,1:3]+n[:,3:5]
        coll=PolyCollection(displaced[q],facecolors=np.array(['#2d4664','#ebaa37'])[f[:,1].astype(int)-1],edgecolors='none',rasterized=True)
        ax.add_collection(coll);ax.plot([0,1,1,0,0],[0,0,1,1,0],'k--',lw=.6)
        ax.set(xlim=(-.01,1.01),ylim=(-.01,1.01),aspect='equal',title=f'{trial} r{revision}')
        ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('Native deformed phase mesh · true 1× displacement · dashed undeformed envelope')
    fig.text(.5,.03,'1 mm computational convention; no microscopy calibration. Small displacements are intentionally barely visible.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,.93));fig.savefig(DEST/'P3_NATIVE_TRUE_SCALE_DEFORMATION.png',dpi=170);plt.close(fig)
    write(DEST/'MECHANICAL_FIGURE_PROVENANCE.json',{'created_utc':now(),
        'native_field_selection':'First registered conversation in each arm; first held-out seed 5000; H1 final checkpoint',
        'native_sources':[{'trial_id':t,'revision':v,'RST_sha256':r['native_result_sha256'],
            'fields_sha256':r['native_fields_sha256'],'nodes_sha256':sha(Path(r['independent_readback_directory'])/'nodes.csv')} for t,v,r,_,_,_ in records],
        'common_clipped_limits':{'equivalent_stress_MPa':[0,equivalent],'axial_strain':[-axial,axial]},
        'clipping':'Maximum of per-specimen 99.5th percentiles; actual extremes retained in native data; no cross-material averaging',
        'displacement_magnification':1,'plotting_zero_origin':'No unsolved origin counted as a native checkpoint',
        'analysis_source_hashes':{p.name:sha(p) for p in analysis.glob('*.json')}})
    write(DEST/'FIGURE_MANIFEST.json',{'created_utc':now(),'files':{p.name:sha(p) for p in sorted(DEST.glob('*.png'))}})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['geometry','mechanical']);a=p.parse_args()
    geometry() if a.stage=='geometry' else mechanical()
