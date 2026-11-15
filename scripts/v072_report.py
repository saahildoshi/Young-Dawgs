"""Actual-data research reporting; secondary diagnostics never change frozen acceptance."""
import argparse
import shutil
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from skimage.measure import regionprops
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v072_experiment import RUN,DOC,BASE,OLD,TRIALS,now
from scripts.v072_analysis import ORDER,SHORT,COLORS,stats,csv_table,native_record,analyse,final_figures


def morphology_diagnostics():
    destination=RUN/'optimization_analysis/POSTHOC_FAMILY_DIAGNOSTICS.json'
    if destination.exists():return read(destination)
    partition=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json');rows=[]
    specimens=[('REFERENCE',None,OLD/'references/P3/evaluation_only_labels.npy')]
    specimens += [(trial,seed,RUN/'heldout_structures'/trial/f'seed_{seed}.npy') for trial in ORDER for seed in partition['heldout']]
    for trial,seed,path in specimens:
        if not path.exists():continue
        a=np.load(path,allow_pickle=False);mask=a==5;regions=regionprops(ndi.label(mask)[0])
        valid=[r for r in regions if r.axis_minor_length>1e-12]
        areas=np.array([r.area for r in valid]);aspects=np.array([r.axis_major_length/r.axis_minor_length for r in valid])
        orientation=np.array([r.orientation for r in valid]);column_fraction=mask.mean(axis=0)
        rows.append({'trial_id':trial,'seed':seed,'array_path':str(path.relative_to(REPO)).replace('\\','/'),'array_sha256':sha(path),
            'all_annotation_regions':len(regions),'defined_aspect_regions':len(valid),'defined_aspect_area_fraction':float(areas.sum()/mask.sum()),
            'area_weighted_annotation_aspect':float(np.average(aspects,weights=areas)),
            'maximum_defined_annotation_aspect':float(aspects.max()),
            'area_fraction_aspect_gt3_among_defined':float(areas[aspects>3].sum()/areas.sum()),
            'area_weighted_vertical_alignment_cos2theta':float(np.average(np.cos(2*orientation),weights=areas)),
            'maximum_column_reinforcement_occupancy':float(column_fraction.max()),
            'fraction_columns_with_occupancy_at_least_point8':float(np.mean(column_fraction>=.8))})
    payload={'calculated_utc':now(),'status':'POST_HOC_SECONDARY_DIAGNOSTICS_NOT_REGISTERED_ACCEPTANCE_RULES',
        'reason':'Inspect visible drift toward aligned segmented reinforcement lanes despite passing the frozen complete-region mean envelope',
        'definitions':'4-connected annotation regions including boundary-censored regions; undefined minor-axis aspect excluded with coverage reported. Orientation is relative to the image vertical axis; cos(2theta)=+1 vertical and -1 horizontal. These are image descriptors, not physical material anisotropy.',
        'thresholds':'Aspect>3 and column occupancy>=0.8 are descriptive post-hoc diagnostics, not retrospective qualification gates or model inputs',
        'rows':rows}
    write(destination,payload);csv_table(RUN/'optimization_analysis/POSTHOC_FAMILY_DIAGNOSTICS.csv',rows)
    fig,axes=plt.subplots(1,3,figsize=(13,4.5));metrics=[('area_weighted_annotation_aspect','Area-weighted annotation aspect'),('area_weighted_vertical_alignment_cos2theta','Area-weighted vertical alignment'),('fraction_columns_with_occupancy_at_least_point8','Fraction of columns >=80% reinforcement')]
    reference=rows[0]
    for ax,(key,label) in zip(axes,metrics):
        for i,(trial,color) in enumerate(zip(ORDER,COLORS)):
            values=[r[key] for r in rows if r['trial_id']==trial]
            if values:ax.scatter(i+np.linspace(-.1,.1,len(values)),values,color=color,s=24)
        ax.axhline(reference[key],color='k',ls='--',lw=.9,label='Reference annotation')
        ax.set_xticks(range(5),SHORT,rotation=25);ax.set_ylabel(label);ax.grid(axis='y',alpha=.2)
    axes[-1].legend(fontsize=8);fig.suptitle('Post-hoc morphology diagnostics · no change to registered acceptance')
    fig.tight_layout();figure=RUN/'figures/POSTHOC_FAMILY_DIAGNOSTICS.png';fig.savefig(figure,dpi=180);plt.close(fig)
    write(RUN/'figures/POSTHOC_FAMILY_DIAGNOSTICS_PROVENANCE.json',{'figure_sha256':sha(figure),'source_table_sha256':sha(destination),
        'actual_arrays':True,'post_hoc_not_used_for_selection_or_feedback':True,'source_array_hashes':[r['array_sha256'] for r in rows]})
    return payload


def archive_interim_reports():
    destination=DOC/'interim_checkpoint_001'
    if destination.exists():
        for name,digest in read(destination/'ARCHIVE_MANIFEST.json')['files'].items():assert sha(destination/name)==digest
        return
    destination.mkdir();files={}
    for path in DOC.glob('*.md'):
        shutil.copyfile(path,destination/path.name);files[path.name]=sha(path)
    write(destination/'ARCHIVE_MANIFEST.json',{'archived_utc':now(),'source_state_commit':'07ec7ff1171173f13b4f24d501faef02fc757936',
        'files':files,'reason':'Preserve capture-blocked checkpoint reports before delivering completed experiment reports'})


def result_contracts():
    rows=[];p=read(RUN/'protocol/PROTOCOL.json')
    for trial in ORDER:
        for level in [1,2]:
            seeds=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['heldout' if level==1 else 'H2']
            for seed in seeds:
                s=read(RUN/'heldout_structures'/trial/f'seed_{seed}.json');r=native_record(trial,seed,level)
                b=native_record('BASE',seed,level)
                rows.append({'experiment_id':'pipeline_v0.7.2/run_001','specimen_id':f'{trial}_heldout_{seed}',
                    'trial_id':trial,'condition':'BASE' if trial=='BASE' else ('MF' if '_MF_' in trial else 'NF'),
                    'starting_generator_id':'P3_B_02/r0','generator_sha256':s['generator_sha256'],'seed':seed,'seed_partition':'heldout',
                    'source_array_sha256':s.get('array_file_sha256'),'phase_counts':s.get('phase_counts'),
                    'reinforcement_fraction':s.get('descriptors',{}).get('reinforcement_fraction'),
                    'structural_feasibility':s['feasibility'],'morphology_descriptors':s.get('descriptors'),
                    'mesh_id':None if r is None else r['mesh_id'],'mesh_level':level,'material_protocol_id':p['material']['id'],
                    'boundary_condition_id':'VERTICAL_FREE_TANGENTIAL_ONE_UX_PIN','native_result_sha256':None if r is None else r['native_result_sha256'],
                    'actual_strains':None if r is None else r['engineering_strains'],
                    'signed_upper_reactions_N':None if r is None else [x[5] for x in r['native_curve']],
                    'signed_lower_reactions_N':None if r is None else [x[6] for x in r['native_curve']],
                    'nominal_stresses_MPa':None if r is None else r['nominal_stresses_MPa'],
                    'maximum_relative_force_balance_error':None if r is None else r['max_reaction_imbalance'],
                    'native_strain_energy_Nmm':None if r is None else [x[8] for x in r['native_curve']],
                    'apparent_modulus_MPa':None if r is None else r['effective_modulus_MPa'],
                    'normalized_objective':None if r is None else r['normalized_effective_modulus'],
                    'mechanical_acceptance':None if r is None else r['checks'],
                    'baseline_relative_gain':None if r is None or b is None else (r['effective_modulus_MPa']-b['effective_modulus_MPa'])/b['effective_modulus_MPa'],
                    'mesh_sensitivity_status':'REGISTERED_H2_CONFIRMATION_SUBSET' if level==2 else 'H1_ACTUAL_NATIVE',
                    'failure_reason':None if r is not None else ('STRUCTURAL_INFEASIBILITY' if not s['feasibility']['passed'] else 'NATIVE_RESULT_UNAVAILABLE_OR_REJECTED')})
    write(RUN/'summary/MECHANICAL_RESULT_CONTRACT.json',{'actual_measurements_only':True,'unavailable_values_are_null_not_zero':True,'records':rows})


def results():
    archive_interim_reports();rows,summaries,comparison,mesh=analyse();final_figures(rows,summaries,comparison,mesh)
    morphology=morphology_diagnostics();result_contracts()
    policy=read(RUN/'protocol/FEASIBILITY_FROZEN.json')
    original_protocol=(DOC/'interim_checkpoint_001/V0_7_2_PROTOCOL.md').read_text(encoding='utf-8')
    (DOC/'V0_7_2_PROTOCOL.md').write_text(original_protocol+'\n## Frozen-envelope documentation addendum\n\n'+
        'This section documents the operative JSON frozen BEFORE the first new mechanical solve and all model calls; it changes no registered rule. The original Markdown registration is retained in `interim_checkpoint_001/`.\n\n'+
        f"Feasibility JSON frozen UTC: `{policy['frozen_utc']}`; SHA-256 `{sha(RUN/'protocol/FEASIBILITY_FROZEN.json')}`. Common start is unchanged captured P3_B_02/r0, parameters={{}}. Target count20,731; allowed deviation±64 pixels (fraction±0.0009765625). Four-connected matrix must span both axes and have LCC≥0.95. Reinforcement may not span either axis under4 or8 connectivity; largest connected fraction≤0.15 under both. Complete/all/censored counts40–75/50–125/5–50; complete mean equivalent diameter12–20px; mean aspect1.2–3.0; singleton reinforcement-area fraction≤0.001.\n\n"+
        'All ten held-out outputs must pass for full generator qualification. Diversity requires ten unique arrays, median pairwise categorical Hamming≥0.1 and at least five rigid-invariant area/centroid-distance signatures, with boundary-clipping limitations reported. Every arm uses an empty parameter dict, local seeded RNG, the same dependency whitelist,30-second single-output ceiling and1000-full-domain-candidate ceiling. No returned-code repair, geometry correction, mechanical cache/solver inside generators, extra attempt or invalid-seed replacement is permitted. Post-hoc family diagnostics are descriptive, never replacement gates.\n\n'+
        'Six development seeds1000–1005 and ten disjoint held-out seeds2000–2009 were frozen before responses; only development data entered model prompts. First-three-seed H2 confirmation uses2000–2002 for BASE and all four revisions. Actual full five-checkpoint curves are used throughout. Native raw labels1/5 map to matrix/reinforcement solids, native MAT1/MAT2; no void phase is introduced. P3 label5 chemistry remains provisional; the selected HorizontalFlip augmentation is not an unaugmented original or an unbiased RVE. No physical microscopy pixel scale is inferred.\n',encoding='utf-8',newline='\n')
    inventory=[]
    for trial in TRIALS:
        r=read(RUN/'llm_trials'/trial/'RECEIPT.json');source_review=read(RUN/'llm_trials'/trial/'SOURCE_REVIEW.json')
        summary=next(s for s in summaries if s['trial_id']==trial)
        inventory.append({key:r.get(key) for key in ['trial_id','condition','chat_url','exposed_model','exposed_effort','prompt_sha256','response_sha256','code_sha256','submitted_utc','captured_utc','status','researcher_repairs','model_calls','repair_calls']}|
            {'source_review':source_review,'generation_runtime_seconds':summary['runtime_seconds'],'backend_version':None,'tokens':None,'cost':None})
    write(RUN/'summary/GENUINE_REVISION_INVENTORY.json',inventory);csv_table(RUN/'summary/GENUINE_REVISION_INVENTORY.csv',inventory)
    simple=[]
    for s in summaries:
        simple.append({'script':s['trial_id'],'attempted':s['attempted'],'feasible':s['structurally_feasible'],'mechanically_valid':s['modulus']['n'],
            'mean_E_MPa':s['modulus']['mean'],'sample_SD_E_MPa':s['modulus']['sample_sd'],
            'mean_J':s['normalized_objective']['mean'],'mean_paired_gain':s['paired_gain']['mean'],
            'positive_paired_gain_fraction':s['positive_gain_fraction'],'mean_phase_fraction':s['reinforcement_fraction']['mean'],
            'diversity_passed':s['diversity']['passed']})
    csv_table(RUN/'summary/GENERATOR_COMPARISON.csv',simple)
    response_table=[]
    for path in sorted((RUN/'mechanical_response').glob('*.json')):
        r=read(path)
        if not r['accepted']:continue
        for native,epsilon,stress in zip(r['native_curve'],r['engineering_strains'],r['nominal_stresses_MPa']):
            response_table.append({'specimen_id':r['specimen_id'],'mesh_level':r['mesh_level'],'load_step':native[0],'strain':epsilon,
                'top_UY_mm':native[2],'signed_upper_RF_N':native[5],'signed_lower_RF_N':native[6],'nominal_stress_MPa':stress,
                'strain_energy_Nmm':native[8],'native_RST_sha256':r['native_result_sha256']})
    csv_table(RUN/'summary/ACTUAL_NATIVE_STRESS_STRAIN.csv',response_table)
    table='| Script | Feasible / attempted | Native H1 mean E ± sample SD (MPa) | Mean paired gain | Positive pairs |\n|---|---:|---:|---:|---:|\n'
    for s,title in zip(summaries,SHORT):
        E,sd,g=s['modulus']['mean'],s['modulus']['sample_sd'],s['paired_gain']['mean']
        table+=f"| {title} | {s['structurally_feasible']}/10 | {E:.3f} ± {sd:.3f} | {100*g:+.3f}% | {s['positive_gain_fraction']:.0%} ({s['paired_gain']['n']} pairs) |\n"
    (DOC/'V0_7_2_HELDOUT_OPTIMIZATION_RESULTS.md').write_text('# Held-out apparent-stiffness results\n\n'+table+
        '\nEvery scalar uses five actual licensed native checkpoints and independent RST reopening. J=E/1000 MPa. The BASE self-comparison is zero by definition; it is not an LLM revision. All ten attempts per script remain in the denominator. Individual results, native hashes, paired gains and exact fractions are in `optimization_analysis/HELDOUT_RESULTS.csv`; script means/spreads and runtime are in `SCRIPT_SUMMARIES.json`.\n\n'+
        f"MF script-average paired gain={100*comparison['arms']['MF']['mean_script_gain']:+.3f}%; NF={100*comparison['arms']['NF']['mean_script_gain']:+.3f}%; MF minus NF={100*comparison['MF_minus_NF_mean_script_gain']:+.3f} percentage points. Each arm has TWO independent LLM responses; ten seeds are nested replicates per response, not ten model trials. There are no pooled-seed p values or universal causal claims.\n\n"+
        'All 40 revised outputs have exactly20,731 reinforcement pixels. BASE varies within the prospectively registered ±64-pixel policy; report individual counts and distinguish tolerance-constrained comparisons from exact-composition comparisons. No guessed phase-fraction correction is applied. All revisions produce aligned segmented lanes, a strong visual departure from the irregular reference. Passing the numerical envelope does not establish strong preservation of the intended natural particle family.\n',encoding='utf-8',newline='\n')
    mesh_table='| Script | Seed | H1 E (MPa) | H2 E (MPa) | Mesh change | H1 paired gain | H2 paired gain | H2 gain > observed-change diagnostic |\n|---|---:|---:|---:|---:|---:|---:|---|\n'
    for r in mesh:
        if r['H2_E_MPa'] is None:mesh_table+=f"| {r['trial_id']} | {r['seed']} | NA | NA | NA | NA | NA | Unavailable |\n";continue
        mesh_table+=f"| {r['trial_id']} | {r['seed']} | {r['H1_E_MPa']:.3f} | {r['H2_E_MPa']:.3f} | {100*r['relative_mesh_change']:.3f}% | {100*r.get('H1_relative_gain',0):+.3f}% | {100*r.get('H2_relative_gain',0):+.3f}% | {r.get('H2_gain_exceeds_observed_changes')} |\n"
    (DOC/'V0_7_2_MESH_CONFIRMATION.md').write_text('# Prospective mesh confirmation\n\n'+mesh_table+
        '\nThe first three held-out seeds for EVERY script were registered before H1 outcomes. H2 subdivides each unchanged source pixel into2×2 elements, preserving material assignments, source shape and phase fractions. Candidate-minus-BASE gains are compared at matched mesh levels. The sum of observed candidate and BASE absolute H1/H2 modulus changes is a conservative screening diagnostic, not a rigorous FE error bound or statistical confidence interval.\n\n'+
        f"Matched-subset MF-minus-NF mean script gains: H1={100*comparison['MF_minus_NF_H1_confirmation_subset_mean_script_gain']:+.3f} percentage points; H2={100*comparison['MF_minus_NF_H2_confirmation_subset_mean_script_gain']:+.3f} percentage points. Compare these matched subsets, not all-ten H1 against three-seed H2. Refinement evidence applies to these fifteen geometries only; it does not certify asymptotic convergence or all unrefined realizations.\n",encoding='utf-8',newline='\n')
    public=read(RUN/'feedback_packets/PROMPTS_FROZEN.json')
    (DOC/'V0_7_2_LLM_REVISION_EXPERIMENT.md').write_text('# Authentic matched LLM revision experiment\n\nFour independent ordinary-ChatGPT conversations, two MF and two NF, one returned module each, no researcher repairs or additional model attempts. All original code bytes, complete code-only responses, submission URLs and capture receipts are preserved. The fourth source was recovered from its existing completed chat after display reconnection; the earlier failure checkpoint remains archived.\n\n'+
        'All trials used the same visible High configuration. The exact model/backend version, token count, cost, account-memory and routing conditions are unavailable. Fresh initial chats were outside the project; personalization was not independently controlled. No privacy settings were changed.\n\n'+
        f"MF prompt SHA-256 `{public['prompt_hashes']['P3_OPT_MF_01']}`; NF `{public['prompt_hashes']['P3_OPT_NF_01']}`. NF is the byte-identical common prefix; MF adds only actual six-development-specimen curves, moduli, variability and acceptance. Common code, objective, phase definitions, structural summaries and runtime/search budgets are identical. Held-out seeds and hidden morphology error scores never entered prompts.\n\n"+
        '| Trial | Original code SHA-256 | Actual conversation |\n|---|---|---|\n'+''.join(f"| {r['trial_id']} | `{r['code_sha256']}` | {r['chat_url']} |\n" for r in inventory)+
        '\nAll four sources were collectively frozen before final generation. Static audits and full source review precede execution. MF01 searches20 geometry candidates (with a constructive fallback); MF02 has a12-candidate bound with early stopping. NF generators construct one configuration directly. Actual per-seed runtime is reported separately; equal revision opportunities and common ceilings do not imply equal consumed procedural computation. Model-provided scientific claims are not treated as measured outcomes.\n',encoding='utf-8',newline='\n')
    morph_summary=[]
    for trial in ['REFERENCE']+ORDER:
        group=[r for r in morphology['rows'] if r['trial_id']==trial]
        morph_summary.append({'trial_id':trial,**{key:stats([r[key] for r in group]) for key in ['area_weighted_annotation_aspect','area_weighted_vertical_alignment_cos2theta','area_fraction_aspect_gt3_among_defined','fraction_columns_with_occupancy_at_least_point8']}})
    write(RUN/'optimization_analysis/FAMILY_DIAGNOSTIC_SUMMARIES.json',morph_summary)
    trade='# Morphology, composition and mechanical trade-offs\n\nThe independent scripts all shift toward aligned axial inclusion chains separated by thin matrix ligaments. This was not a researcher-authored procedural baseline or an edit to returned code. It emerges in both measured-feedback and objective-only responses. All outputs pass the frozen complete-region mean, size, population and topology guardrails. Nevertheless, the strong lane organization departs visibly from the original irregular dispersed field. **Numerical-envelope feasibility and strong material-family preservation must remain separate.** Do not retrofit a new rejection threshold, repair the outputs or hide this result.\n\n'
    trade+='The complete-region mean aspect rule permits a mixture of a few long, high-area inclusions with many small inclusions. Additional post-hoc area-weighted shape-tail and directional-organization diagnostics quantify this limitation. These new metrics are explicitly descriptive and were not used for feedback, selection or acceptance. Four-connected annotation regions include censored regions; undefined aspect coverage is reported. No annotation descriptor is a physical particle-instance measurement.\n\n'
    trade+='| Script | Area-weighted annotation aspect | Vertical alignment cos2theta | Area fraction aspect >3 (defined) | Columns ≥80% reinforcement |\n|---|---:|---:|---:|---:|\n'
    for r in morph_summary:trade+=f"| {r['trial_id']} | {r['area_weighted_annotation_aspect']['mean']:.3f} | {r['area_weighted_vertical_alignment_cos2theta']['mean']:.3f} | {r['area_fraction_aspect_gt3_among_defined']['mean']:.3f} | {r['fraction_columns_with_occupancy_at_least_point8']['mean']:.3f} |\n"
    trade+='\nAll MF and NF realizations have identical exact phase counts, so their direct arm comparison has no count variation. BASE counts vary under the registered policy; a purely geometry-only BASE-relative causal attribution is not certified without separate exact-composition confirmation or numerical fraction sensitivity. Report observed counts rather than a guessed correction. Previously visible/hidden reconstruction errors remain distinct from feasibility and the stiffness objective.\n\n'
    trade+='Phase-specific element-associated SYY means, equivalent-stress percentiles normalized by each specimen nominal stress, and elastic-energy shares are retained in `optimization_analysis/PHASE_FIELDS.csv`. Compare these under fixed strain and also normalized stress; increased raw stress alone can reflect increased nominal loading. Pixel-corner maxima remain exploratory. No plasticity, damage, yielding, fracture or calibrated failure response is modeled.\n'
    (DOC/'V0_7_2_MORPHOLOGY_MECHANICS_TRADEOFFS.md').write_text(trade,encoding='utf-8',newline='\n')
    (DOC/'BROWSER_CAPTURE_GATE.md').write_text('# Capture gate resolved\n\nThe existing fourth response was recovered without resubmission, regeneration or repair. All four scripts were frozen before held-out evaluation. The original capture-blocked instructions and checkpoint reports are preserved in `interim_checkpoint_001/`; recovery evidence is in `response_capture/DISPLAY_RECOVERY.json`.\n',encoding='utf-8',newline='\n')
    figure_entries=[('BASELINE_VARIABILITY.png','Six actual development specimens; within-generator sample variation.'),
        ('BASELINE_NATIVE_CURVES.png','Five actual solved checkpoints per development specimen; aggregate mean is labeled separately.')]
    figure_entries += [(r['path'],r['caption']) for r in read(RUN/'figures/FIGURE_MANIFEST.json')['figures']]
    figure_entries += [('HELDOUT_STRUCTURE_PREVIEW.png','Actual first confirmation-seed arrays; no mechanical result is inferred from appearance.'),
        ('POSTHOC_FAMILY_DIAGNOSTICS.png','Supplemental image diagnostics, not retrospective acceptance criteria.')]
    gallery='# v0.7.2 scientific figure gallery\n\nAll data figures use executed arrays or licensed native results. Violet/yellow denote matrix1/reinforcement5 in categorical plots. Computational millimeters do not calibrate microscopy pixels. Each image has retained source tables and a provenance record in the experiment figure directory.\n\n'
    for name,caption in figure_entries:
        gallery+='## '+name.removesuffix('.png').replace('_',' ').title()+'\n\n'+caption+'\n\n!['+name+']('+str((RUN/'figures'/name).resolve()).replace('\\','/')+')\n\n'
    (DOC/'V0_7_2_FIGURES.md').write_text(gallery,encoding='utf-8',newline='\n')
    print('ACTUAL RESULT REPORTS WRITTEN',[(s['trial_id'],s['modulus']['mean'],s['paired_gain']['mean']) for s in summaries],comparison,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['posthoc','results']);a=p.parse_args()
    if a.action=='posthoc':morphology_diagnostics()
    else:results()
