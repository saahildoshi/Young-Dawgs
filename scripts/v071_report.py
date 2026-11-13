"""Evidence-bound tables, native field figures and research handoff for v0.7.1."""
from pathlib import Path
from datetime import datetime,timezone
import csv
import subprocess
import shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from scripts.v071_register import RUN,BASE,DOC
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v071_mechanics import model,CURVE

ORDER=['M2_reference','M3_A01','M4_B02','M5_C02_r1','M6_C02_r0']
COLORS=['#292d32','#d97706','#2563eb','#059669','#a855f7']


def table(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if not rows:return
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)


def records():
    rows=[read(p) for p in sorted((RUN/'mechanical_response').glob('*.json'))]
    selected={}
    for r in rows:
        if r['accepted']:selected[(r['specimen_id'],r['mesh_level'])]=r
    return rows,selected


def native_arrays(r):
    d=Path(r['independent_readback_directory'])
    return (np.loadtxt(d/'nodes.csv',delimiter=','),np.loadtxt(d/'fields.csv',delimiter=','),np.loadtxt(d/'connectivity.csv',delimiter=',')[:,1:].astype(int)-1)


def report():
    rows,selected=records();protocol=read(RUN/'protocol/PROTOCOL.json');figure_records=[]
    sensitivity=[]
    for sid in ORDER:
        if (sid,1) in selected and (sid,2) in selected:
            a,b=selected[sid,1],selected[sid,2]
            delta=abs(a['effective_modulus_MPa']-b['effective_modulus_MPa'])/b['effective_modulus_MPa']
            sensitivity.append({'specimen_id':sid,'H1_E_MPa':a['effective_modulus_MPa'],'H2_E_MPa':b['effective_modulus_MPa'],
                                'relative_modulus_difference':delta,'preliminary_2percent_gate':delta<=.02,
                                'H1_energy_Nmm':a['native_curve'][-1][8],'H2_energy_Nmm':b['native_curve'][-1][8],
                                'H1_reaction_N':a['native_curve'][-1][5],'H2_reaction_N':b['native_curve'][-1][5],
                                'H1_phases':a['phase_results'],'H2_phases':b['phase_results'],
                                'interpretation':'same frozen staircase geometry, preliminary FE sensitivity only'})
    write(RUN/'mesh_sensitivity/COMPARISON.json',sensitivity)
    production=read(RUN/'protocol/PRODUCTION_MESH.json')['level'] if (RUN/'protocol/PRODUCTION_MESH.json').exists() else 1
    reference=selected.get(('M2_reference',production))
    chosen=[selected[sid,production] for sid in ORDER if (sid,production) in selected]
    benchmarks=[]
    for r in rows:
        if r['analytical_modulus_MPa'] is not None:
            benchmarks.append({'specimen':r['specimen_id'],'native_directory':Path(r['source_directory']).name,'analytical_E_MPa':r['analytical_modulus_MPa'],
                               'native_E_MPa':r['effective_modulus_MPa'],'relative_error':r['analytical_relative_error'],
                               'force_balance':r['max_reaction_imbalance'],'energy_error':r['max_energy_relative_error'],'accepted':r['accepted']})
    joint=[];responses=[];provenance=[];contracts=[]
    ref_sensitivity=next((r['relative_modulus_difference'] for r in sensitivity if r['specimen_id']=='M2_reference'),None)
    for r in chosen:
        sid=r['specimen_id'];s=read(RUN/'specimen_manifests'/f'{sid}.json')
        error=(r['effective_modulus_MPa']-reference['effective_modulus_MPa'])/reference['effective_modulus_MPa']
        own_sensitivity=next((v['relative_modulus_difference'] for v in sensitivity if v['specimen_id']==sid),None)
        unresolved=bool(sid!='M2_reference' and ref_sensitivity is not None and abs(error)<=ref_sensitivity+(own_sensitivity or 0))
        row={'specimen_id':sid,'mesh_level':production,'reinforcement_fraction':s['phase_fractions']['5'],
             'effective_modulus_MPa':r['effective_modulus_MPa'],'normalized_modulus':r['normalized_effective_modulus'],
             'signed_reference_relative_error':error,'absolute_reference_relative_error':abs(error),
             'visible_morphology_error':s['visible_morphology_error']['mean'] if s['visible_morphology_error'] else None,
             'hidden_morphology_error':s['hidden_morphology_error']['mean'] if s['hidden_morphology_error'] else None,
             'reference_H1_H2_sensitivity':ref_sensitivity,'own_H1_H2_sensitivity':own_sensitivity,
             'difference_resolution':'SELF_REFERENCE' if sid=='M2_reference' else ('MECHANICAL_DIFFERENCE_NOT_RESOLVED_RELATIVE_TO_MESH_SENSITIVITY' if unresolved else 'DIFFERENCE_EXCEEDS_OBSERVED_REFERENCE_PLUS_AVAILABLE_SPECIMEN_MESH_DIFFERENCES__NOT_A_CONFIDENCE_INTERVAL'),
             'elastic_energy_Nmm':r['native_curve'][-1][8],'matrix_mean_syy_MPa':r['phase_results']['1']['mean_syy_MPa'],
             'reinforcement_mean_syy_MPa':r['phase_results']['2']['mean_syy_MPa'],'accepted':r['accepted']}
        for metric in ['reinforcement_fraction','complete_regions','diameter_mean_px','diameter_std_px','aspect_mean','nearest_neighbor_mean_px','nearest_neighbor_cv','interface_density','S2_x_8','S2_y_8','matrix_lcc']:
            row['morphology_'+metric]=s['exact_seed_descriptors'][metric]
        joint.append(row)
        provenance.append({key:s.get(key) for key in ['specimen_id','source_kind','source_array_path','source_array_sha256','generator_trial_id','generator_script_sha256','revision','seed'] }|{'reinforcement_fraction':s['phase_fractions']['5'],'mesh_id':r['mesh_id'],'mesh_level':production})
        for native,eps,stress in zip(r['native_curve'],r['engineering_strains'],r['nominal_stresses_MPa']):
            responses.append({'specimen_id':sid,'load_step':native[0],'strain':eps,'top_displacement_mm':native[2],
                              'top_reaction_N':native[5],'bottom_reaction_N':native[6],'nominal_stress_MPa':stress,
                              'elastic_energy_Nmm':native[8],'native_result_sha256':r['native_result_sha256'],'accepted':r['accepted']})
        contracts.append({'specimen_id':sid,'mesh_id':r['mesh_id'],'material_protocol_id':s['material_protocol_id'],
             'boundary_condition_id':s['boundary_condition_id'],'loading_direction':'y','solver_identity':'ANSYS MAPDL2024R1, licensed native execution',
             'native_result_hash':r['native_result_sha256'],'requested_strains':protocol['strain_checkpoints'],'achieved_strains':r['engineering_strains'],
             'signed_top_reactions':[v[5] for v in r['native_curve']],'signed_bottom_reactions':[v[6] for v in r['native_curve']],
             'nominal_stresses':r['nominal_stresses_MPa'],'force_balance_errors':[abs(v[5]+v[6])/abs(v[5]) for v in r['native_curve']],
             'effective_modulus':r['effective_modulus_MPa'],'normalized_effective_modulus':r['normalized_effective_modulus'],
             'fit_intercept':r['fit_intercept_MPa'],'fit_quality':{'R_squared':r['R_squared'],'relative_max_residual':r['relative_fit_max_residual']},
             'strain_energy':[v[8] for v in r['native_curve']],'phase_average_stress':r['phase_results'],
             'phase_stress_percentiles':{k:v['equivalent_percentiles_MPa'] for k,v in r['phase_results'].items()},
             'mechanical_validity':r['checks'],'mesh_sensitivity_status':row['difference_resolution'],'material_calibration_status':'ILLUSTRATIVE_UNCALIBRATED',
             'uncertainty_notes':['finite selected augmented field, provisional phase5','pixel staircase geometry','one selected realization per generator','no RVE or experimental material validation']})
    out=RUN/'morphology_mechanics';write(out/'JOINT_RESULTS.json',joint);table(out/'JOINT_RESULTS.csv',joint)
    table(RUN/'summary/BENCHMARKS.csv',benchmarks);table(RUN/'summary/PROVENANCE.csv',provenance);table(RUN/'summary/MECHANICAL_RESPONSE.csv',responses)
    write(RUN/'summary/MECHANICS_OUTPUT_CONTRACT.json',contracts)
    table(RUN/'summary/MESH_COMPARISON.csv',[{'specimen_id':r['specimen_id'],'mesh_level':r['mesh_level'],'nodes':r['mesh']['nodes'],'elements':r['mesh']['elements'],
                  'E_MPa':r['effective_modulus_MPa'],'runtime_s':r['execution']['runtime_seconds'],'peak_RSS_bytes':r['execution']['peak_tree_rss_bytes'],'accepted':r['accepted']} for r in rows])
    figures=RUN/'figures';figures.mkdir(exist_ok=True)
    def save(fig,name,sources,description):
        path=figures/name;fig.savefig(path,dpi=160,bbox_inches='tight');plt.close(fig)
        figure_records.append({'path':str(path.relative_to(REPO)).replace('\\','/'),'sha256':sha(path),'source_native_RST_hashes':[r['native_result_sha256'] for r in sources],
                               'source_native_fields_hashes':[r['native_fields_sha256'] for r in sources],'description':description})
    if chosen:
        fig,axes=plt.subplots(1,2,figsize=(11,4))
        for r,color in zip(chosen,COLORS):
            axes[0].plot(100*np.array(r['engineering_strains']),r['nominal_stresses_MPa'],'o-',color=color,label=r['specimen_id'])
            c=np.array(r['native_curve']);axes[1].plot(-c[:,2],-c[:,5],'o-',color=color,label=r['specimen_id'])
        axes[0].set(xlabel='Engineering compression (%)',ylabel='Nominal compression stress (MPa)')
        axes[1].set(xlabel='Actual shortening (mm)',ylabel='Top compressive force magnitude (N)')
        for ax in axes:ax.grid(alpha=.25);ax.legend(fontsize=8)
        fig.suptitle(f'Actual licensed ANSYS checkpoints; H{production}; illustrative E=1000/10000 MPa, nu=0.30')
        fig.tight_layout();save(fig,'NATIVE_CURVES.png',chosen,'Five native solved points per curve; connecting segments are visual interpolation. No synthesized origin or scaled single-point curve.')
        fig,axes=plt.subplots(1,2,figsize=(11,4.6));x=np.arange(len(joint))
        axes[0].bar(x,[v['effective_modulus_MPa'] for v in joint],color=COLORS[:len(joint)])
        axes[1].bar(x,100*np.array([v['signed_reference_relative_error'] for v in joint]),color=COLORS[:len(joint)])
        for ax in axes:ax.set_xticks(x,[r['specimen_id'] for r in chosen],rotation=25,ha='right');ax.grid(axis='y',alpha=.2)
        axes[0].set_ylabel('Effective modulus (MPa)');axes[1].set_ylabel('Difference from reference (%)')
        if ref_sensitivity is not None:axes[1].axhspan(-100*ref_sensitivity,100*ref_sensitivity,color='gray',alpha=.15,label='Reference H1/H2 difference, not CI');axes[1].legend(fontsize=8)
        fig.suptitle('Selected seed 0 specimens: fixed illustrative material and boundary assumptions');fig.tight_layout(rect=[0,0,1,.94]);save(fig,'EFFECTIVE_MODULI.png',chosen,'Fits to five native points; shaded reference sensitivity is a diagnostic, not a statistical interval.')
        fig,axes=plt.subplots(1,len(chosen),figsize=(3*len(chosen),3.5),squeeze=False)
        for ax,r,j in zip(axes[0],chosen,joint):
            m,_,_=model(r['specimen_id'],production);ax.imshow(np.flipud(m['materials'].reshape(m['ny'],m['nx'])),cmap='viridis',vmin=1,vmax=2,extent=[0,1,0,1],interpolation='nearest')
            ax.set_title(f"{r['specimen_id']}\nf={j['reinforcement_fraction']:.5f}; E={j['effective_modulus_MPa']:.1f}",fontsize=10);ax.set_xlabel('Computational x (mm)')
        axes[0,0].set_ylabel('Computational y (mm)');fig.suptitle('Exact categorical geometry; both phases solid; no physical microscopy calibration')
        fig.text(.5,.015,'Purple: raw 1 / material 1, matrix-like solid. Yellow: raw 5 / material 2, provisional reinforcement-like solid.',ha='center',fontsize=9)
        fig.tight_layout(rect=[0,.06,1,.94]);save(fig,'GEOMETRY_COMPARISON.png',chosen,'Categorical arrays used for the authenticated mechanical specimens; image row0 is physical top.')
        arrays={r['specimen_id']:native_arrays(r) for r in chosen}
        seqmax=max(np.percentile(arrays[r['specimen_id']][1][:,5],99.5) for r in chosen)
        for column,name,label,limits in [(5,'EQUIVALENT_STRESS.png','Element-associated equivalent stress (MPa)',(0,seqmax)),(3,'AXIAL_STRESS.png','Element-associated SYY (MPa)',None)]:
            if limits is None:
                values=np.concatenate([arrays[r['specimen_id']][1][:,column] for r in chosen]);bound=np.percentile(np.abs(values),99.5);limits=(-bound,bound)
            fig,axes=plt.subplots(1,len(chosen),figsize=(3.1*len(chosen),3.5),squeeze=False)
            for ax,r in zip(axes[0],chosen):
                nodes,fields,q=arrays[r['specimen_id']];ny=int(np.sqrt(len(fields)))
                im=ax.imshow(np.flipud(fields[:,column].reshape(ny,ny)),extent=[0,1,0,1],origin='upper',cmap='magma' if column==5 else 'coolwarm',vmin=limits[0],vmax=limits[1],interpolation='nearest')
                ax.set_title(r['specimen_id'],fontsize=10);ax.set_xlabel('Computational x (mm)')
            fig.colorbar(im,ax=list(axes[0]),shrink=.7,label=label,extend='max' if column==5 else 'both')
            fig.suptitle('Native fields at 0.5%; shared scales; disclosed 99.5% display clipping, all values retained')
            save(fig,name,chosen,'Native ETABLE element-associated averages; common displayed scale with disclosed percentile clipping, original extremes retained in tables.')
            figure_records[-1]['display_limits_MPa']=list(map(float,limits))
            figure_records[-1]['display_limit_method']='Maximum of individual-specimen99.5th percentiles' if column==5 else 'Pooled99.5th percentile of absolute SYY, symmetric signed range'
        fig,axes=plt.subplots(1,len(chosen),figsize=(3.1*len(chosen),3.5),squeeze=False)
        for ax,r in zip(axes[0],chosen):
            n,f,q=arrays[r['specimen_id']];deformed=n[:,1:3]+n[:,3:5]
            collection=PolyCollection(deformed[q],array=f[:,1],cmap='viridis',clim=(1,2),edgecolors='none',linewidths=0,antialiased=False,rasterized=True)
            ax.add_collection(collection);ax.set(xlim=(-.025,1.025),ylim=(-.025,1.025),aspect='equal',title=r['specimen_id']);ax.set_xlabel('Computational x (mm)')
            ax.plot([0,1,1,0,0],[0,0,1,1,0],color='black',ls='--',lw=.7)
        fig.suptitle('Native displacement, true scale 1x at 0.5%; dashed undeformed boundary; phase colors')
        fig.text(.5,.01,'Purple: matrix-like solid (native 1). Yellow: provisional reinforcement-like solid (native 5).',ha='center',fontsize=9)
        fig.subplots_adjust(bottom=.2)
        save(fig,'TRUE_SCALE_DISPLACEMENT.png',chosen,'Actual native UX/UY added once to native node coordinates; deformation scale1.')
        n,f,q=arrays[reference['specimen_id']];nx=int(np.sqrt(len(n)))-1
        fig,axes=plt.subplots(1,3,figsize=(12,3.7))
        for ax,values,title in zip(axes,[n[:,3],n[:,4],np.hypot(n[:,3],n[:,4])],['Native UX (mm)','Native UY (mm)','Magnitude from native UX/UY (mm)']):
            im=ax.imshow(np.flipud(values.reshape(nx+1,nx+1)),extent=[0,1,0,1],interpolation='nearest',cmap='viridis');ax.set_title(title,fontsize=10);fig.colorbar(im,ax=ax,shrink=.7)
        fig.suptitle('P3 reference actual displacement components, 0.5% compression');fig.tight_layout()
        save(fig,'REFERENCE_DISPLACEMENT_COMPONENTS.png',[reference],'Actual native nodal UX/UY; magnitude is their Euclidean norm, not an independent native result quantity.')
        fig,ax=plt.subplots(figsize=(8,4));x=np.arange(len(chosen));w=.35
        for phase,offset,color in [('1',-w/2,'#52525b'),('2',w/2,'#7c3aed')]:
            ax.bar(x+offset,[-r['phase_results'][phase]['mean_syy_MPa'] for r in chosen],width=w,color=color,label='matrix-like' if phase=='1' else 'reinforcement-like')
        ax.set_xticks(x,[r['specimen_id'] for r in chosen],rotation=20);ax.set_ylabel('Area-weighted mean axial compression stress (MPa)');ax.legend();fig.tight_layout();save(fig,'PHASE_LOAD_SHARING.png',chosen,'Native element-associated axial stress, weighted by actual native element volumes.')
        r=reference;n,f,q=arrays[r['specimen_id']];centers=n[q,1:3].mean(axis=1);keep=(centers[:,0]<.08)&(centers[:,1]>.92)
        fig,ax=plt.subplots(figsize=(6,5));poly=PolyCollection(n[q[keep],1:3],array=f[keep,1],cmap='viridis',clim=(1,2),edgecolors='black',linewidth=.4)
        ax.add_collection(poly);ax.set(xlim=(0,.08),ylim=(.92,1),aspect='equal',xlabel='Computational x (mm)',ylabel='Computational y (mm)',title=f'Actual native P3 mesh, H{production}, upper-left zoom')
        save(fig,'NATIVE_MESH_ZOOM.png',[r],'Actual RST/database node coordinates, quadrilateral connectivity and material IDs; shared-node interfaces verified.')
    if sensitivity:
        fig,ax=plt.subplots(figsize=(8,4))
        for s in sensitivity:ax.plot([1,2],[s['H1_E_MPa'],s['H2_E_MPa']],'o-',label=s['specimen_id'])
        ax.set(xticks=[1,2],xticklabels=['H1:1 quad/pixel','H2:4 quads/pixel'],ylabel='Effective modulus (MPa)',title='Same pixel geometry: preliminary FE sensitivity');ax.legend(fontsize=8);ax.grid(alpha=.2)
        save(fig,'MESH_SENSITIVITY.png',[r for r in rows if r['accepted'] and r['specimen_id'] in ORDER],'Two-level discretization comparison, not asymptotic convergence or pixel-resolution qualification.')
    write(RUN/'figures/FIGURE_MANIFEST.json',figure_records)
    return rows,selected,joint,sensitivity,benchmarks


def documents():
    rows,selected,joint,sensitivity,benchmarks=report()
    assert len(joint)==5 and len(sensitivity)==5,'Complete required sources and targeted H2 checks before final reporting'
    names={r['specimen_id']:r for r in joint}
    ref=selected['M2_reference',1]
    r0,r1=names['M6_C02_r0'],names['M5_C02_r1']
    pair={'parent':'P3_C_02','seed':0,'pairing':'Same parent and seed, not identical particle identities or random-number consumption',
          'initial':r0,'revised':r1,'absolute_mechanical_error_change':r1['absolute_reference_relative_error']-r0['absolute_reference_relative_error'],
          'signed_modulus_change_MPa':r1['effective_modulus_MPa']-r0['effective_modulus_MPa'],
          'visible_morphology_error_change':r1['visible_morphology_error']-r0['visible_morphology_error'],
          'hidden_morphology_error_change':r1['hidden_morphology_error']-r0['hidden_morphology_error'],
          'fraction_change':r1['reinforcement_fraction']-r0['reinforcement_fraction'],
          'mechanical_agreement':'WORSENED' if r1['absolute_reference_relative_error']>r0['absolute_reference_relative_error'] else 'IMPROVED'}
    e2=selected['M2_reference',2]['effective_modulus_MPa']
    pair['H2_initial_absolute_error']=abs(selected['M6_C02_r0',2]['effective_modulus_MPa']-e2)/e2
    pair['H2_revised_absolute_error']=abs(selected['M5_C02_r1',2]['effective_modulus_MPa']-e2)/e2
    conservative_error_change_scale=2*r0['reference_H1_H2_sensitivity']+r0['own_H1_H2_sensitivity']+r1['own_H1_H2_sensitivity']
    pair['agreement_error_change_sensitivity_diagnostic']=conservative_error_change_scale
    pair['agreement_error_change_resolution']='NOT_RESOLVED_BY_CONSERVATIVE_OBSERVED_MESH_CHANGE_DIAGNOSTIC' if abs(pair['absolute_mechanical_error_change'])<=conservative_error_change_scale else 'EXCEEDS_CONSERVATIVE_OBSERVED_CHANGES_NOT_A_RIGOROUS_ERROR_BOUND'
    write(RUN/'paired_feedback_comparison/COMPARISON.json',pair)
    phase_rows=[]
    for (sid,k),r in selected.items():
        if sid not in ORDER:continue
        for phase,p in r['phase_results'].items():
            phase_rows.append({'specimen_id':sid,'mesh_level':k,'material_id':phase,
                'mean_syy_MPa':p['mean_syy_MPa'],'mean_equivalent_MPa':p['mean_equivalent_MPa'],
                'p95_equivalent_MPa':p['equivalent_percentiles_MPa']['p95'],'p99_equivalent_MPa':p['equivalent_percentiles_MPa']['p99'],
                'max_equivalent_MPa':p['equivalent_percentiles_MPa']['max'],'elastic_energy_Nmm':p['elastic_energy_Nmm'],
                'energy_fraction':p['elastic_energy_fraction'],'mean_axial_strain':p['mean_axial_strain']})
    table(RUN/'phase_fields/PHASE_STRESS_SUMMARY.csv',phase_rows)
    receipts=[read(p) for p in BASE.glob('*/process_receipt.json')]
    samples=[s for r in receipts for s in r.get('resource_samples',[])];files=[p for p in BASE.rglob('*') if p.is_file()]
    performance={'native_processes':len(receipts),'total_supervised_native_seconds':sum(r['runtime_seconds'] for r in receipts),
                 'peak_single_process_tree_RSS_bytes':max(r['peak_tree_rss_bytes'] for r in receipts),
                 'minimum_available_RAM_bytes':min(s['available_RAM_bytes'] for s in samples),
                 'maximum_observed_commit_fraction':max([s['commit_fraction'] for s in samples if s.get('commit_fraction') is not None],default=None),
                 'maximum_observed_page_reads_per_second':max([s['page_reads_per_second'] for s in samples if s.get('page_reads_per_second') is not None],default=None),
                 'raw_artifact_root':str(BASE),'raw_artifact_bytes':sum(p.stat().st_size for p in files),
                 'RSS_cap':None,'native_concurrency':1,'raw_RST_files_not_copied_for_readback':True}
    write(RUN/'performance/SUMMARY.json',performance)
    # Explicit input schema supports phase roles, but this implementation rejects all families except P3.
    input_fields=['specimen_id','source_array_path','source_array_sha256','reference_id','family_id','generator_trial_id','generator_script_sha256',
                  'revision','seed','shape','dtype','raw_phase_labels','phase_roles','phase_to_material_id','width_mm','height_mm','thickness_mm',
                  'scale_provenance','mesh_level','mesh_id','element_formulation','constitutive_model','material_parameters','boundary_condition_id','loading_direction','requested_strains']
    inputs=[]
    for j in joint:
        sid=j['specimen_id'];s=read(RUN/'specimen_manifests'/f'{sid}.json');r=selected[sid,1]
        inputs.append(s|{'mesh_level':1,'mesh_id':r['mesh_id'],'length_units':'mm','constitutive_model':'isotropic small-strain linear elasticity',
                         'material_parameters':r['material_properties'],'requested_strains':r['engineering_strains']})
    write(RUN/'protocol/MECHANICS_INPUT_SCHEMA.json',{'schema_id':'v071-P3-two-solid-input','required':input_fields,'family_supported':'P3',
          'native_phase_contract':{'1':{'role':'matrix_like_solid','material_id':1},'5':{'role':'reinforcement_like_solid_provisional','material_id':2}},
          'unknown_labels':'REJECT','future_void_extension':'Explicit role void with no material/element; not implemented or implicitly inferred'})
    write(RUN/'summary/MECHANICS_INPUT_CONTRACT.json',inputs)
    output_fields=list(read(RUN/'summary/MECHANICS_OUTPUT_CONTRACT.json')[0])
    write(RUN/'protocol/MECHANICS_OUTPUT_SCHEMA.json',{'schema_id':'v071-native-elastic-output','required':output_fields,'field_units':{'effective_modulus':'MPa','nominal_stresses':'MPa','strain_energy':'N mm','reactions':'N'},'missing_values':'null or explicit NOT_RUN, never invented zero'})
    write(RUN/'protocol/FUTURE_FEEDBACK_SCHEMA.json',{'status':'FUTURE_SCHEMA_ONLY__NO_LLM_MECHANICAL_FEEDBACK_EXECUTED',
          'required':['objective','generator_identity','material_protocol','mesh_protocol','boundary_conditions','fixed_fraction_constraint',
                      'registered_development_seed_ids','accepted_per_seed_measurements','execution_and_validity_failures',
                      'development_aggregate_modulus_and_variation','revision_budget','equal_attempt_control','withheld_evaluation_policy'],
          'withheld_evaluation_policy':'Do not disclose final evaluation measurements or masks. Reclassify any currently observed or feedback-exposed selected seed as development/selection evidence; register a new heldout mechanical cohort.'})
    for m in inputs:assert all(k in m for k in input_fields)
    write(RUN/'protocol/MECHANICS_SCHEMA_HASHES.json',{name:sha(RUN/'protocol'/name) for name in ['MECHANICS_INPUT_SCHEMA.json','MECHANICS_OUTPUT_SCHEMA.json','FUTURE_FEEDBACK_SCHEMA.json']})
    def doc(name,text):
        for old,new in [('1000/10000MPa','1000/10000 MPa'),('1mm','1 mm'),('0.1–0.5%','0.1–0.5%'),('phase5','phase 5'),('seed0','seed 0'),('at0.5%','at 0.5%'),('actual0.1','actual 0.1'),('native2024R1','native 2024 R1'),('Native2024R1','Native 2024 R1'),('by+','by +'),('by-','by -'),('isWORSENED','is WORSENED'),('isIMPROVED','is IMPROVED'),('from1.','from 1.'),('to1.','to 1.'),('are0.','are 0.'),('and1.','and 1.'),('of0.','of 0.'),('with0.','with 0.'),('E=1000/10000','E = 1000/10000'),('nu=0.30','nu = 0.30')]:text=text.replace(old,new)
        (DOC/name).write_text(text,encoding='utf-8',newline='\n')
    mechanics='| Specimen | Reinforcement fraction | H1 E (MPa) | E/E_matrix | Signed reference error | Resolution diagnostic |\n|---|---:|---:|---:|---:|---|\n'
    for r in joint:
        label='Reference' if r['specimen_id']=='M2_reference' else ('Unresolved vs mesh changes' if r['difference_resolution'].startswith('MECHANICAL_DIFFERENCE_NOT') else 'Exceeds observed mesh changes')
        mechanics+=f"| {r['specimen_id']} | {r['reinforcement_fraction']:.8f} | {r['effective_modulus_MPa']:.6f} | {r['normalized_modulus']:.6f} | {100*r['signed_reference_relative_error']:+.4f}% | {label} |\n"
    mesh='| Specimen | H1 E (MPa) | H2 E (MPa) | Difference relative to H2 |\n|---|---:|---:|---:|\n'
    for r in sensitivity:mesh+=f"| {r['specimen_id']} | {r['H1_E_MPa']:.6f} | {r['H2_E_MPa']:.6f} | {100*r['relative_modulus_difference']:.5f}% |\n"
    bench='| Native control/attempt | Analytical E (MPa) | Native E (MPa) | Relative error | Accepted |\n|---|---:|---:|---:|---|\n'
    for r in benchmarks:bench+=f"| {r['native_directory']} | {r['analytical_E_MPa']:.8f} | {r['native_E_MPa']:.8f} | {r['relative_error']:.5g} | {r['accepted']} |\n"
    limitations='''The phase properties are illustrative E=1000/10000MPa and nu=0.30, with ideal perfectly bonded interfaces. The1mm square and1mm thickness are computational scaling choices, not measured microscopy scale. Native1/5 roles are explicit, but phase5 chemical identity remains provisional. P3 is a morphology-selected HorizontalFlip augmented SEM crop, not an unbiased RVE. Pixel interfaces are staircase boundaries; refinement changes finite elements within each unchanged pixel, not segmentation resolution. There is one selected seed per generator, not a prompting-condition mean or population estimate. Script selection used prior morphology outcomes. Composition and morphology both vary. No experimental validation, nonlinear contact, failure law, physical yielding, energy absorption, F1 mechanics,3D analysis or LLM mechanical optimization is claimed.
'''
    doc('V0_7_1_ANALYTICAL_BENCHMARKS.md','# Licensed analytical benchmarks\n\n'+bench+'''
All accepted controls use five actual native result sets and independent read-only RST export. The nu=0 parallel/series controls isolate analytically tractable load sharing; they do not replace nu=0.30 in the P3 comparison. Native2024R1 ETLIST/RLIST/MPLIST, exact connectivity, material IDs, constraints, displacement fields, constitutive stress/strain relations, reactions and integrated energy are verified.

The first dense equal-material attempt is rejected. Default coordinate NSEL tolerance included an interior row, producing771 UY constraints instead of514. The corrected exact node-ID boundary sets and native DLIST gate recovered the control without changing morphology, materials or tolerances. The failed input, RST, exports and rejection remain preserved. A separate Python boolean-serialization failure was fixed by reprocessing existing native data; no fabricated solver output or unnecessary rerun was used.
''')
    doc('V0_7_1_MESH_AND_PHASE_VALIDATION.md',f'''# Mesh and phase validation

H1:66049 nodes and65536 counterclockwise PLANE182 quads. H2:263169 nodes and262144 quads. Every native element connectivity and material ID matches the authenticated categorical source, and every native coordinate matches the structured grid. No holes, duplicate interface nodes, removed matrix pixels or separate contact bodies occur. Native1→material1 and native5→material2 are both solids. Shared nodes enforce ideal bonded displacement compatibility. Exact native boundary inventories contain only top/bottom UY and one bottom-left UX pin.

Image row0 stays at the physical top. Refinement subdivides each pixel without averaging labels. All exact phase fractions survive H1/H2. The reference H1/H2 difference is{100*ref_sensitivity if (ref_sensitivity:=next(r['relative_modulus_difference'] for r in sensitivity if r['specimen_id']=='M2_reference')) else 0:.6f}%, below the prospectively fixed2% gate. H1 is the common initial production mesh.

'''+mesh+'\nNative tables compare phase-average stress, stress percentiles, energy, reactions, runtime and memory at both levels. This is preliminary two-level FE sensitivity; asymptotic convergence, pixel-resolution adequacy and physical interface geometry remain unqualified.\n')
    doc('V0_7_1_P3_MECHANICAL_RESULTS.md','# P3 native mechanical responses\n\n'+mechanics+'''
Every row uses the same normalized dimensions, constitutive properties, PLANE182 options, direct displacement boundary conditions and five actual0.1–0.5% native checkpoints. Modulus is an unconstrained slope/intercept fit; secant modulus, residuals and R² are retained. The unloaded origin was not solved and is not plotted as a native result. Independent source RST/database hashes, source logs, per-element fields and reaction exports are bound to each accepted record. Positive engineering compression uses shortening/H and absolute top reaction/(width*thickness).

Element-associated native ETABLE averages retain phase identity; no averaging across material nodes is used. Phase stress means, robust equivalent-stress percentiles, axial strains and energy shares are in phase_fields/PHASE_STRESS_SUMMARY.csv. Element SENE is summed once and agrees with0.5*F*delta. Native engineering shear is checked against SXY/G. Volume-mean axial stress agrees with the structural boundary reaction.

![Native curves](../../experiments/pipeline_v0.7.1/run_001/figures/NATIVE_CURVES.png)

![Common-scale native stresses](../../experiments/pipeline_v0.7.1/run_001/figures/AXIAL_STRESS.png)

![True-scale native displacement](../../experiments/pipeline_v0.7.1/run_001/figures/TRUE_SCALE_DISPLACEMENT.png)

'''+limitations)
    morph='| Specimen | Exact seed visible error | Exact seed hidden error | E error magnitude |\n|---|---:|---:|---:|\n'
    for j in joint:
        v='NA' if j['visible_morphology_error'] is None else f"{j['visible_morphology_error']:.6g}"
        h='NA' if j['hidden_morphology_error'] is None else f"{j['hidden_morphology_error']:.6g}"
        morph+=f"| {j['specimen_id']} | {v} | {h} | {100*j['absolute_reference_relative_error']:.4f}% |\n"
    doc('V0_7_1_MORPHOLOGY_MECHANICS_ANALYSIS.md','# Morphology and mechanical response\n\n'+mechanics+'\n'+morph+f'''
These are the actual mechanically evaluated seed0 descriptors, not ten-seed script means. Reinforcement fraction is reported alongside stiffness; it was never adjusted after generation. A01 has a lower reinforcement fraction yet is stiffer than the target in this selected realization, so fraction alone does not explain the observed ordering. This does not isolate which spatial descriptor causes the response.

The C02 revision changes visible morphology error by {pair['visible_morphology_error_change']:+.6g}, hidden error by {pair['hidden_morphology_error_change']:+.6g}, reinforcement fraction by {pair['fraction_change']:+.8f}, and modulus by {pair['signed_modulus_change_MPa']:+.6f} MPa. Measured mechanical agreement is {pair['mechanical_agreement']} on H1: absolute reference-relative error changes from {100*r0['absolute_reference_relative_error']:.4f}% to {100*r1['absolute_reference_relative_error']:.4f}%. On H2 those errors are {100*pair['H2_initial_absolute_error']:.4f}% and {100*pair['H2_revised_absolute_error']:.4f}%. Pairing identifies the parent script and stochastic seed, not individual particles or an identical RNG stream.

For this exact seed, the supplied-descriptor error worsens while the withheld-descriptor error improves. That differs from the prior ten-seed mean supplied-descriptor improvement; those levels must remain distinct. The direction of observed stiffness-agreement change persists across both meshes, but its absolute-error change is smaller than a conservative diagnostic combining twice the reference mesh change and the two specimen mesh changes. Therefore its improvement/worsening is descriptive and is not a numerically certified or causal feedback effect. In particular, the initial C02/reference difference is itself unresolved under the registered sensitivity interpretation.

Observed H1/H2 changes are numerical-sensitivity diagnostics, not rigorous error bounds or confidence intervals. The resolution flag conservatively compares the generated/reference modulus difference against the sum of observed reference and available specimen relative mesh changes. Results flagged unresolved cannot support a resolved morphology-effect claim. No p-values, causal feedback benefit, condition-average ranking or broad generalization is inferred.

![Effective properties](../../experiments/pipeline_v0.7.1/run_001/figures/EFFECTIVE_MODULI.png)

'''+limitations)
    doc('V0_7_1_FUTURE_OPTIMIZATION_INTERFACE.md','''# Mechanics input/output contract and future work

protocol/MECHANICS_INPUT_SCHEMA.json and MECHANICS_OUTPUT_SCHEMA.json define required fields; MECHANICS_SCHEMA_HASHES.json freezes their identities. summary/MECHANICS_INPUT_CONTRACT.json and MECHANICS_OUTPUT_CONTRACT.json populate those contracts with actual accepted results. Inputs bind source array, generator/revision/seed, phase semantics, constitutive properties, computational scale, mesh and loading. Outputs bind native result hashes, full accepted curves, reactions/equilibrium, effective modulus, fit diagnostics, energy, phase stress summaries and qualification limits.

Future feedback should use only registered development realizations and report accepted measurements and failures separately. Hold material, loading, mesh, computational effort and reinforcement fraction fixed where possible. Reserve independent seeds and use a suitable equal-attempt control. Reconstruction scripts with internal target fitting must remain immutable historical evidence; any optimization generator needs a new identity and explicit parameter domain.

FUTURE_FEEDBACK_SCHEMA.json is a data contract only; no mechanical feedback prompt was sent to an LLM. Once a measured realization is disclosed or used for design selection, treat it as development/selection evidence and register a new held-out mechanical cohort. The prior morphology held-out scores remain unchanged.

A suitable first candidate objective is matching a registered normalized effective modulus at fixed reinforcement fraction. It uses the currently qualified primary scalar and is easier to interpret than optimizing mesh-sensitive corner maxima. This is a proposed future objective, not an executed optimization. Establish variability across more scripts and seeds, tighter mesh-error control, and a prospective feedback/control design first. Pipeline v0.7.2 may build a controlled mechanical-property dataset and first LLM mechanical-feedback experiment; no such loop was executed here.

F1 remains deferred. Its original matrix0/fiber1/void2 contract must preserve void explicitly. Carbon-fiber transverse properties and anisotropy, polymer behavior, circle-annotation uncertainty, merged regions, interface behavior and the appropriate2D idealization require separate qualification. Do not assign longitudinal fiber stiffness to this transverse section or map an unknown phase to void automatically.

Physical material predictions need authenticated phase identities, physical microscopy calibration, measured or appropriately sourced constitutive/interface data and experimental validation. An RVE/homogenized-property claim additionally needs representative sampling, finite-size and boundary-condition studies. This finite selected crop provides an apparent axial modulus under the stated boundary conditions.
''')
    return pair,performance


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--documents',action='store_true');a=p.parse_args()
    documents() if a.documents else report()
