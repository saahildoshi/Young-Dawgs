"""Close the single registered experiment with native hashes and separate scientific statuses."""
import subprocess
from pathlib import Path
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v072_experiment import RUN,DOC,BASE,TRIALS,now
from scripts.v072_analysis import ORDER,SHORT,stats,native_record,csv_table
from scripts.v072_interim import xml_counts
from metamaterial_eval.simulation.solver_execution import file_hash


def closeout():
    assert not (RUN/'summary/FINAL_PACKAGE_HASHES.json').exists(),'Final package is already frozen'
    h1=read(RUN/'heldout_mechanics_h1/CAMPAIGN.json');h2=read(RUN/'heldout_mechanics_h2/CAMPAIGN.json')
    assert len(h1['cases'])==50 and len(h2['cases'])==15
    assert h1['accepted']==50 and h2['accepted']==15
    frozen=read(RUN/'frozen_scripts/ALL_OPTIMIZATION_SCRIPTS_FROZEN.json')
    assert sha(RUN/'protocol/PROTOCOL.json')==frozen['common_protocol_sha256']
    assert sha(RUN/'protocol/FEASIBILITY_FROZEN.json')==frozen['feasibility_sha256']
    assert sha(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')==frozen['seed_partition_sha256']
    for trial,r in frozen['scripts'].items():
        assert sha(RUN/'llm_trials'/trial/'generator.py')==r['code_sha256']
        assert sha(RUN/'llm_trials'/trial/'response.txt')==r['response_sha256']
        assert sha(RUN/'llm_trials'/trial/'prompt.txt')==r['prompt_sha256']
    assert sha(RUN/'starting_generator/generator.py')==frozen['BASE_sha256']
    protected=read(RUN/'audit/PROTECTED_BEFORE.json');changed=[name for name,digest in protected.items() if sha(REPO/name)!=digest]
    assert not changed,changed
    write(RUN/'audit/PROTECTED_AFTER_FINAL.json',{'checked_utc':now(),'tracked_files_unchanged':len(protected),'changed_files':changed,'passed':True})
    native_count=0
    for path in (RUN/'native_result_manifests').glob('*/NATIVE_ARTIFACTS.json'):
        for item in read(path).values():assert file_hash(Path(item['path']))==item['sha256'];native_count+=1
    assert native_count==497
    tests={name:xml_counts(paths) for name,paths in {
        'active':[RUN/'verification/final_active_tests.xml'],
        'archived_replays':list((RUN/'verification/archive_replay').glob('*.xml')),
        'historical_licensed_artifacts':[RUN/'verification/historical_licensed_checks.xml'],
        'new_v072_licensed_artifacts':[RUN/'verification/final_licensed_checks.xml']}.items()}
    assert tests['active']['tests']==912 and tests['archived_replays']['tests']==475
    assert tests['historical_licensed_artifacts']['tests']==49 and tests['new_v072_licensed_artifacts']['tests']==76
    assert all(r['failures']==r['errors']==r['skipped']==0 for r in tests.values())
    receipts=[read(path) for path in BASE.glob('*/process_receipt.json')];assert len(receipts)==142
    samples=[s for r in receipts for s in r.get('resource_samples',[])]
    limits=read(RUN/'protocol/PROTOCOL.json')['resource_limits']
    performance={'native_processes':len(receipts),'source_solves':71,'independent_readbacks':71,'accepted_source_models':71,'accepted_native_checkpoints':355,
        'total_supervised_native_seconds':sum(r['runtime_seconds'] for r in receipts),
        'peak_process_tree_RSS_bytes':max(r['peak_tree_rss_bytes'] for r in receipts),
        'minimum_available_RAM_bytes':min(s['available_RAM_bytes'] for s in samples),
        'maximum_observed_commit_fraction':max([s['commit_fraction'] for s in samples if s.get('commit_fraction') is not None],default=None),
        'maximum_observed_system_page_reads_per_second':max([s['page_reads_per_second'] for s in samples if s.get('page_reads_per_second') is not None],default=None),
        'raw_artifact_bytes':sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()),'native_base':str(BASE),'cores':2,'concurrency':1,'RSS_cap':None,
        'page_read_limitations':'System hard-fault disk-read proxy, not per-solver or pagefile-only paging'}
    assert performance['native_processes']<=limits['maximum_native_jobs'] and performance['total_supervised_native_seconds']<=limits['native_campaign_seconds']
    assert performance['raw_artifact_bytes']<=limits['raw_storage_budget_bytes']
    write(RUN/'performance/FINAL_SUMMARY.json',performance)
    summaries=read(RUN/'optimization_analysis/SCRIPT_SUMMARIES.json');comparison=read(RUN/'optimization_analysis/MF_VERSUS_NF.json');mesh=read(RUN/'mesh_confirmation_h2/COMPARISON.json')
    rows=read(RUN/'optimization_analysis/HELDOUT_RESULTS.json');phase=read(RUN/'optimization_analysis/PHASE_FIELDS.json')
    assert len(rows)==50 and all(r['mechanically_accepted'] and r['structurally_feasible'] for r in rows)
    assert all(s['fully_qualified_generator'] for s in summaries)
    assert all(r['phase_counts']['5']==20731 for r in rows if r['trial_id']!='BASE')
    contracts=read(RUN/'summary/MECHANICAL_RESULT_CONTRACT.json')['records'];assert len(contracts)==65
    assert all(r['native_result_sha256'] and r['apparent_modulus_MPa']>0 and len(r['actual_strains'])==5 for r in contracts)
    figure_manifest=read(RUN/'figures/FIGURE_MANIFEST.json')
    for item in figure_manifest['figures']:assert sha(RUN/'figures'/item['path'])==item['sha256']
    for name in ['BASELINE_PROVENANCE.json','HELDOUT_STRUCTURE_PREVIEW_PROVENANCE.json','POSTHOC_FAMILY_DIAGNOSTICS_PROVENANCE.json']:
        record=read(RUN/'figures'/name)
        if 'figures' in record:
            for filename,digest in record['figures'].items():assert sha(RUN/'figures'/filename)==digest
        else:
            filename='HELDOUT_STRUCTURE_PREVIEW.png' if name.startswith('HELDOUT') else 'POSTHOC_FAMILY_DIAGNOSTICS.png'
            assert sha(RUN/'figures'/filename)==record['figure_sha256']
    effects=[r for r in mesh if r['trial_id']!='BASE']
    assert len(effects)==12
    all_refined_positive=all(r['positive_direction_persists'] and r['H2_gain_exceeds_observed_changes'] for r in effects)
    maximum_relative_mesh_change=max(r['relative_mesh_change'] for r in mesh)
    mean_gains={s['trial_id']:s['paired_gain']['mean'] for s in summaries if s['trial_id']!='BASE'}
    feedback_sign='MF_HIGHER' if comparison['MF_minus_NF_mean_script_gain']>0 else 'NF_HIGHER_OR_EQUAL'
    status={key:'PASS_VERIFIED' for key in ['STARTING_GENERATOR_AUTHENTICATED','COMMON_STARTING_POINT_FROZEN','COMPOSITION_CONSTRAINT_REGISTERED',
        'MORPHOLOGY_CONSTRAINTS_REGISTERED','BASELINE_STRUCTURAL_FEASIBILITY','BASELINE_MECHANICAL_VARIABILITY_MEASURED','BASELINE_NATIVE_STRESS_STRAIN_AVAILABLE',
        'MF_NF_PROMPTS_MATCHED','MECHANICAL_FEEDBACK_PACKET_AUTHENTICATED','GENUINE_MF_RESPONSES_CAPTURED','GENUINE_NF_RESPONSES_CAPTURED',
        'EQUAL_REVISION_BUDGET_VERIFIED','ALL_OPTIMIZATION_SCRIPTS_FROZEN','HELDOUT_SEED_ISOLATION_VERIFIED','MF_STRUCTURAL_FEASIBILITY',
        'NF_STRUCTURAL_FEASIBILITY','STOCHASTIC_DIVERSITY_PRESERVED','HELDOUT_MECHANICAL_EVALUATION','NATIVE_FULL_CURVE_CONFIRMATION','LLM_MECHANICAL_FEEDBACK_EXECUTED']}
    status.update(FIXED_COMPOSITION_PRESERVED='PASS_REGISTERED64_PIXEL_TOLERANCE__REVISED40_OF40_EXACT20731__BASE_NOT_EXACT',
        DISPERSED_MORPHOLOGY_PRESERVED='PASS_FROZEN_NUMERIC_ENVELOPE__STRONG_NATURAL_PARTICLE_FAMILY_PRESERVATION_NOT_ESTABLISHED',
        BASELINE_RELATIVE_IMPROVEMENT='ALL_FOUR_SCRIPT_MEAN_GAINS_POSITIVE' if all(v>0 for v in mean_gains.values()) else 'MIXED_OR_NONPOSITIVE',
        FEEDBACK_VERSUS_CONTROL_COMPARISON='COMPLETED_DESCRIPTIVE_'+feedback_sign,
        SCREENING_MODULUS_VERIFIED='FINAL_POINT_SECANT_AGREES_WITH_FULL_CURVE_FIT__NO_ONE_POINT_ONLY_NATIVE_ROUTE',
        H2_MESH_CONFIRMATION='15_PROSPECTIVELY_SELECTED_GEOMETRIES_EXECUTED__OTHER35_H1_ONLY',
        H2_PRELIMINARY_2PERCENT_GATE='PASS_FOR_ALL15' if maximum_relative_mesh_change<=.02 else 'SOME_REFINED_GEOMETRIES_EXCEED_REGISTERED_PRELIMINARY_THRESHOLD',
        OPTIMIZATION_EFFECT_NUMERICALLY_RESOLVED='ALL12_REFINED_REVISION_PAIRS_PERSIST_ABOVE_OBSERVED_CHANGE_DIAGNOSTIC' if all_refined_positive else 'MIXED_OR_UNRESOLVED_REFINED_EFFECTS',
        COMPOSITION_CONFOUNDING_ASSESSED='EXACT_MF_VS_NF__BASE_TOLERANCE_ONLY__NO_GUESSED_CORRECTION_OR_STRONG_GEOMETRY_ONLY_ATTRIBUTION',
        PRELIMINARY_LLM_MECHANICAL_OPTIMIZATION_SUPPORTED='CONSTRAINED_NUMERICAL_STIFFENING_OBSERVED__STRONG_PHYSICAL_PARTICLE_COMPOSITE_OPTIMIZATION_NOT_QUALIFIED',
        PRELIMINARY_FEEDBACK_ADVANTAGE_SUPPORTED='DESCRIPTIVE_MF_ADVANTAGE_ONLY__TWO_SCRIPTS_PER_ARM' if feedback_sign=='MF_HIGHER' else 'NOT_SUPPORTED__NO_FEEDBACK_ARM_MEAN_IS_HIGHER_OR_EQUAL',
        PHYSICAL_MATERIAL_CALIBRATION='NOT_CALIBRATED',REPRESENTATIVE_VOLUME_QUALIFICATION='NOT_QUALIFIED',CROSS_FAMILY_MECHANICAL_OPTIMIZATION='NOT_RUN',
        PAPER_READINESS='CONTROLLED_SMALL_NUMERICAL_PILOT__NO_PHYSICAL_OR_GENERAL_LLM_TREATMENT_EFFECT_CLAIM')
    overall='CONTROLLED_LLM_MECHANICAL_FEEDBACK_EXPERIMENT_COMPLETE__NUMERICAL_STIFFENING_UNDER_FROZEN_ENVELOPE__'+feedback_sign+'__MORPHOLOGY_FAMILY_DRIFT__ILLUSTRATIVE_MATERIALS'
    write(RUN/'summary/FINAL_SCIENTIFIC_STATUS.json',{'overall':overall,'completed_utc':now(),'independent_statuses':status,
        'all_refined_revision_gains_exceed_observed_mesh_change_diagnostic':all_refined_positive,
        'maximum_relative_mesh_change':maximum_relative_mesh_change})
    write(RUN/'verification/FINAL_INTEGRITY.json',{'checked_utc':now(),'test_results':tests,'native_critical_hashes_verified':native_count,
        'protected_original_tracked_files_unchanged':len(protected),'genuine_independent_LLM_trials':4,'MF':2,'NF':2,'repair_calls':0,
        'heldout_attempted':50,'heldout_feasible':50,'native_H1_heldout':50,'native_H2_confirmation':15,'accepted_source_models':71,
        'native_processes':142,'actual_native_checkpoints':355,'result_contract_records':65,'all_returned_code_unchanged':True,
        'no_new_generation_or_F1_or_contact_campaign':True,'push':False})
    validation='# Final v0.7.2 validation\n\n| Verification | Passed | Scope |\n|---|---:|---|\n'+''.join(f"| {name} | {r['tests']} | Zero failures, errors or skips |\n" for name,r in tests.items())
    validation+='\nThe active suite includes16 new optimization tests. Archived475 checks are replays across nine groups, not additional unique tests. Historical49 licensed-artifact checks comprise26 v0.7.1 and23 older checks, with no old native jobs. Final76 new licensed checks supersede the earlier nine baseline-only checks; do not add both as independent evidence. All71 source models were independently reopened; each has five actual solved checkpoints, complete mesh/material/constraint readback, reaction balance, strain-energy/work and native field acceptance. H1 uses65,536 elements/66,049 nodes; H2 uses262,144/263,169 while preserving the same labels and geometry.\n\n'
    validation+=f"Actual native processes142 =71 solves +71 readbacks, below the150-call limit. Supervised native wall-time sum {performance['total_supervised_native_seconds']:.3f}s ({performance['total_supervised_native_seconds']/60:.3f}min), peak single process-tree RSS {performance['peak_process_tree_RSS_bytes']/2**30:.3f}GiB, minimum available RAM {performance['minimum_available_RAM_bytes']/2**30:.3f}GiB; raw artifact storage {performance['raw_artifact_bytes']/2**30:.3f}GiB at `{BASE}`. Two cores, one native job at a time, existing system-health supervision, no arbitrary RSS cap or pagefile change. Paging values are system proxies, not per-solver/pagefile-only rates. Native outputs and derived true-scale coordinates stay outside Git.\n\n"
    validation+='All16,596 originally tracked files are unchanged; all497 critical new native artifacts authenticate. Prompts, code, seed partition, material/BC/element/mesh policy and morphology constraints retain their frozen identities. All50 held-out structures satisfy the registered limits and diversity diagnostics. No researcher repairs, seed substitutions, hidden result access before collective freeze or extra model calls occurred. One Windows display-capture failure delayed the fourth capture and was resolved by user display reconnection; it caused no model resubmission or scientific-data substitution.\n\n'
    validation+='The source evaluator and actual R1 configuration are inherited unchanged from v0.7.1. Its exact-release manual-access limitation remains documented there; actual R1 inventories and analytical/constitutive controls establish the executed behavior. No new claim of experimental material validation follows from this software/native verification.\n\n| Independent scientific status | Outcome |\n|---|---|\n'+''.join(f'| {key} | {value} |\n' for key,value in status.items())
    (DOC/'V0_7_2_VALIDATION.md').write_text(validation,encoding='utf-8',newline='\n')
    table='| Script | H1 mean ± sample SD (MPa) | Mean J | Mean paired gain | Positive pairs |\n|---|---:|---:|---:|---:|\n'
    for s,title in zip(summaries,SHORT):table+=f"| {title} | {s['modulus']['mean']:.3f} ± {s['modulus']['sample_sd']:.3f} | {s['normalized_objective']['mean']:.6f} | {100*s['paired_gain']['mean']:+.3f}% | {s['positive_gain_fraction']:.0%} |\n"
    p=read(RUN/'protocol/PROTOCOL.json');base=summaries[0];dev=read(RUN/'baseline_mechanical_results/SUMMARY.json')
    feedback_sentence=(f"The MF arm's mean script-level gain is {100*comparison['arms']['MF']['mean_script_gain']:.3f}%, versus {100*comparison['arms']['NF']['mean_script_gain']:.3f}% for NF; MF minus NF is {100*comparison['MF_minus_NF_mean_script_gain']:+.3f} percentage points. "+('MF has a descriptive arm-average advantage in this small pilot.' if feedback_sign=='MF_HIGHER' else 'Measured mechanical feedback does not show an arm-average advantage in this pilot.'))
    phase_summary=[]
    for trial in ORDER:
        for material in ['1','2']:
            group=[r for r in phase if r['trial_id']==trial and r['material']==material]
            phase_summary.append({'trial_id':trial,'material':material,'raw_label':1 if material=='1' else 5,'n':len(group),'mean_phase_syy_MPa':float(np.mean([r['mean_syy_MPa'] for r in group])),
                'mean_p99_equivalent_over_nominal':float(np.mean([r['equivalent_percentiles_over_nominal']['p99'] for r in group])),
                'mean_elastic_energy_share':float(np.mean([r['elastic_energy_fraction'] for r in group]))})
    write(RUN/'optimization_analysis/PHASE_TRADEOFF_SUMMARY.json',phase_summary);csv_table(RUN/'optimization_analysis/PHASE_TRADEOFF_SUMMARY.csv',phase_summary)
    base_energy=next(r['mean_elastic_energy_share'] for r in phase_summary if r['trial_id']=='BASE' and r['material']=='2')
    revised_energy=[r['mean_elastic_energy_share'] for r in phase_summary if r['trial_id']!='BASE' and r['material']=='2']
    load_sharing_sentence=f"Reinforcement elastic-energy share rises from {100*base_energy:.2f}% in BASE to {100*min(revised_energy):.2f}–{100*max(revised_energy):.2f}% across the revisions, under the same prescribed strain."
    tradeoff_path=DOC/'V0_7_2_MORPHOLOGY_MECHANICS_TRADEOFFS.md'
    tradeoff_text=tradeoff_path.read_text(encoding='utf-8')+'\n## Measured H1 cohort summaries\n\n| Script | Visible descriptor error | Hidden descriptor error | Mean diameter (px) | Mean aspect | NN distance (px) | NN CV | Interface density |\n|---|---:|---:|---:|---:|---:|---:|---:|\n'
    for trial,title in zip(ORDER,SHORT):
        group=[r for r in rows if r['trial_id']==trial]
        values=[float(np.mean([r[key] for r in group])) for key in ['visible_error','hidden_error','diameter_mean_px','aspect_mean','nearest_neighbor_mean_px','nearest_neighbor_cv','interface_density']]
        tradeoff_text+='| '+title+' | '+' | '.join(f'{value:.5f}' for value in values)+' |\n'
    tradeoff_text+='\nDescriptor errors use the unchanged v0.7.0 normalization, not percentage accuracy. Nearest-neighbor statistics describe complete connected annotations, not recovered particle instances or a complete clustering characterization.\n\n| Script | Matrix mean SYY (MPa) | Reinforcement mean SYY (MPa) | Matrix p99 equivalent / nominal | Reinforcement p99 equivalent / nominal | Matrix energy share | Reinforcement energy share |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for trial,title in zip(ORDER,SHORT):
        matrix=next(r for r in phase_summary if r['trial_id']==trial and r['material']=='1')
        reinforcement=next(r for r in phase_summary if r['trial_id']==trial and r['material']=='2')
        values=[matrix['mean_phase_syy_MPa'],reinforcement['mean_phase_syy_MPa'],matrix['mean_p99_equivalent_over_nominal'],reinforcement['mean_p99_equivalent_over_nominal'],matrix['mean_elastic_energy_share'],reinforcement['mean_elastic_energy_share']]
        tradeoff_text+='| '+title+' | '+' | '.join(f'{value:.5f}' for value in values)+' |\n'
    tradeoff_text+='\nThese are equal-weight means of each script\'s ten accepted H1 specimens at0.5% compression. Native MAT1 maps to raw matrix label1; native MAT2 maps to raw reinforcement label5. Phase p99/nominal is a stress-localization diagnostic, not a failure prediction. Energy shares are from native element strain energies.\n'
    tradeoff_path.write_text(tradeoff_text,encoding='utf-8',newline='\n')
    (DOC/'V0_7_2_HANDOFF.md').write_text(f'''# v0.7.2 completed research handoff

Repository `{REPO}`, master, initial HEAD `{p['starting_head']}`; resumed from the preserved capture-gate commit07ec7ff1171173f13b4f24d501faef02fc757936. All16,596 pre-existing tracked files, P3/F1 references, v0.7.0 scripts/320 outputs, v0.7.1 native evidence and archived porous work remain unchanged. Earlier v0.7.2 checkpoint reports are preserved in `interim_checkpoint_001`. Nothing was pushed.

The common starting generator is unchanged captured **P3_B_02/r0**, SHA-256 `{frozen['BASE_sha256']}`. Its historical seed0 replay matched exactly; no fallback or manual adaptation was needed. Parameters are an empty dictionary. The exact reference reinforcement count is20,731 of65,536 pixels, fraction0.3163299560546875. Before mechanics/model calls, six new development observations established the common **±64-pixel tolerance**, equivalent to0.0009765625 absolute fraction. The hard envelope requires both phases, finite256² uint8 labels1/5, four-connected matrix spanning both axes/LCC≥0.95, reinforcement nonspanning under four/eight connectivity, largest reinforcement fraction≤0.15 under both, complete/all/censored annotation counts40–75/50–125/5–50, complete mean equivalent diameter12–20px, mean aspect1.2–3.0 and singleton area fraction≤0.001. Final diversity requires ten unique arrays, median pairwise Hamming≥0.1 and at least five distinct rigid-invariant area/centroid-distance signatures; source review and boundary limitations remain explicit.

The objective is **maximize J=apparent vertical E/1000MPa** under the unchanged illustrative E1000/10000MPa, nu0.30, small-strain plane-stress model. PLANE182 KEYOPT1=0/3=3/6=0, shared-node perfect bonding, bottom UY0/top negative UY and one bottom-left UX pin, free lateral motion, NLGEOM OFF. The1mm square/thickness are computational conventions, not microscopy calibration. Six development seeds1000–1005 produced actual five-checkpoint curves through0.5% and independently verified native outputs: mean E={dev['mean_modulus_MPa']:.3f}MPa, sample SD={dev['sample_standard_deviation_MPa']:.3f}MPa, J={dev['mean_normalized_objective']:.6f}. Final-point secants agree with fitted slopes; no one-point-only solve route or synthetic curve was used.

Four genuine independent ordinary-ChatGPT revisions, two MF and two NF, were captured unedited at the same exposed High setting. Exact backend/version, tokens/cost and account routing are unavailable; personalization/memory were not independently controlled. Both arms received identical B02 source, phase definitions, objective, constraints, physical assumptions and development structural summaries. Only MF received the authentic six ANSYS curves, moduli and variability. Hidden morphology errors and final seeds never entered prompts. All sources and protocols froze before the ten new evaluator-only seeds2000–2009 were opened. No repair calls, researcher generator edits or additional model attempts occurred. The fourth response's display-capture delay was resolved by copying the existing response, not regenerating it.

All50 held-out attempts are structurally feasible, deterministic and diverse: ten BASE and ten per revision. All40 revised outputs have exactly20,731 reinforcement pixels; BASE varies within its frozen tolerance. Every one of the50 H1 specimens has a qualified actual five-point response and independent RST reopening. The observed results are:

{table}

{feedback_sentence} Scripts are the independent units, two per arm; realizations are nested. Equal seed IDs identify paired numerical comparisons, not matched particles or identical RNG streams. Phase counts are identical between MF and NF, eliminating count variation in that direct comparison. BASE-relative comparisons retain the narrow residual composition difference; no guessed correction or strong geometry-only causal attribution is supplied. Mean fraction and all individual counts accompany the results.

H2 was executed on the prospectively fixed first three final seeds for all five generators:15 actual refinements, no outcome-based selection or expansion. The same categorical geometry and phase fractions are preserved by2×2 pixel subdivision. All12 revised/BASE confirmation pairs {'retain positive gains exceeding' if all_refined_positive else 'were compared against'} the sum of observed candidate and BASE H1/H2 modulus changes. This is a conservative sensitivity diagnostic, not a rigorous error bound or statistical confidence interval. Matched-subset MF-minus-NF mean gains change from {100*comparison['MF_minus_NF_H1_confirmation_subset_mean_script_gain']:+.3f} percentage points on H1 to {100*comparison['MF_minus_NF_H2_confirmation_subset_mean_script_gain']:+.3f} on H2. Strong refinement statements apply only to these actual15 geometries; the remaining35 are H1-only. Full native curves and true-scale displacement/stress fields are shown for the preselected first confirmation seed, not a favorable post-hoc seed.

**Morphology-family limitation:** all four revised scripts arrange inclusions into strongly vertical segmented lanes separated by thin matrix ligaments. They pass the frozen numerical population/mean/size/connectivity rules, yet depart substantially from the irregular reference. A complete-region mean aspect rule can hide high-area elongated regions among many small inclusions. Post-hoc area-weighted shape, alignment and column-occupancy diagnostics describe this drift; they were not sent to the model or retrofitted as acceptance rules. This experiment therefore demonstrates numerical stiffening under the registered envelope, not strong preservation/optimization of an experimentally established natural particle-composite family. Apparent stiffness, reconstruction descriptor accuracy and family plausibility remain distinct outcomes.

{load_sharing_sentence} Actual phase-average axial stress, equivalent-stress percentiles normalized by nominal stress, and energy shares are retained for all H1 specimens. Matrix/reinforcement trade-offs are compared at fixed applied strain and normalized loading; cross-material stress averaging is not used. Pixel-corner maxima are exploratory and imply no failure, yielding or damage. The selected augmented P3 field remains morphology-biased, provisional phase5 chemistry and unknown microscopy scale persist, interfaces are ideal bonds and artificial corner connections are not verified physical bonds. There is no material calibration, RVE qualification, full homogenized tensor, isotropic improvement or cross-family mechanical claim.

Validation:912 active tests,475 archived replay checks,49 historical licensed-artifact checks and76 final new licensed-artifact checks passed. All497 critical native artifact hashes authenticate. The142 actual native processes comprise71 solves and71 independent readbacks, yielding355 accepted solved checkpoints. Supervised native time summed to {performance['total_supervised_native_seconds']/60:.3f}min, peak tree RSS {performance['peak_process_tree_RSS_bytes']/2**30:.3f}GiB, raw artifacts {performance['raw_artifact_bytes']/2**30:.3f}GiB under `{BASE}`. No unsuccessful native solves or invalid structures were concealed. The earlier Windows display-capture failure and recovery remain documented; no unrelated applications/pagefile settings were changed.

The most useful next experiment is to prospectively strengthen the material-family envelope with shape-tail/spatial-organization controls and exact composition, then replicate the matched MF/NF comparison with more independent scripts and informative geometry–mechanics feedback. Preserve an objective-only control and a separately registered refined-mesh plan. Do not reinterpret this small sample as a general causal feedback benefit. No extra generation, F1 mechanics, old contact solve,3D work or new optimization milestone was initiated.

Scientific status: **{overall}**. The single registered experiment is complete. Stop here.
''',encoding='utf-8',newline='\n')
    (DOC/'DR_WANG_SUMMARY.md').write_text(f'''# Research summary for Dr. Wang

We completed the first controlled LLM mechanical-feedback pilot using the qualified two-solid-phase P3 evaluator. Starting from the same captured B02 generator, two independent ordinary-ChatGPT revisions received actual ANSYS development stress–strain data; two matched revisions received the same stiffness objective, code and structural constraints without measured mechanical feedback. Each had one revision opportunity, with no researcher repair.

All50 held-out structures passed the registered composition, topology and diversity checks. Every revised structure preserved exactly20,731 reinforcement pixels. The BASE apparent vertical modulus averaged {base['modulus']['mean']:.2f}MPa; revised script means ranged from {min(s['modulus']['mean'] for s in summaries[1:]):.2f} to {max(s['modulus']['mean'] for s in summaries[1:]):.2f}MPa under illustrative E1000/10000MPa constituent assumptions. {feedback_sentence}

All specimens had actual native curves and independent result reopening. The preselected15-case refined-mesh subset {'retained the positive revision-versus-BASE gains above the observed sensitivity diagnostic' if all_refined_positive else 'provided preliminary numerical-sensitivity comparisons'}. These checks apply to the executed subset, not complete asymptotic convergence.

The visual outcome limits the interpretation: all revisions favor aligned, segmented reinforcement lanes. These pass the frozen numerical envelope but depart from the original irregular particle morphology. Thus the study establishes controlled numerical stiffness changes and tests feedback against an equal-attempt control; it does not establish calibrated material optimization or a general causal advantage of mechanical feedback. The next step should strengthen family-preserving constraints and replicate the controlled experiment at exact composition.
''',encoding='utf-8',newline='\n')
    # Formatting only; preserve IDs/hashes and all scientific values.
    import re
    for path in [DOC/'V0_7_2_HANDOFF.md',DOC/'DR_WANG_SUMMARY.md',DOC/'V0_7_2_VALIDATION.md']:
        text=path.read_text(encoding='utf-8');text=re.sub(r'(?<=\d)(MPa|GiB|mm|px)\b',r' \1',text)
        for old,new in [('All50','All 50'),('all50','all 50'),('All40','All 40'),('all40','all 40'),('All71','All 71'),('All16,596','All 16,596'),
            ('All497','All 497'),('all497','all 497'),('The142','The 142'),('comprise71','comprise 71'),('and71','and 71'),('yielding355','yielding 355'),
            ('Validation:912','Validation: 912'),('tests,475','tests, 475'),('checks,49','checks, 49'),('and76','and 76'),('seeds1000','seeds 1000'),('seeds2000','seeds 2000'),
            ('count is20,731 of65,536','count is 20,731 of 65,536'),('exactly20,731','exactly 20,731'),('fraction0.316','fraction 0.316'),('to0.000','to 0.000'),
            ('finite256','finite 256'),('counts40','counts 40'),('diameter12','diameter 12'),('aspect1.2','aspect 1.2'),('through0.5','through 0.5'),
            ('E1000/10000','E = 1000/10000'),('nu0.30','nu = 0.30'),('The1 mm','The 1 mm'),('by2×2','by 2×2'),
            ('actual15','actual 15'),('remaining35','remaining 35'),('executed15','executed 15'),('preselected15','preselected 15'),
            ('includes16','includes 16'),('Archived475','Archived 475'),('Historical49','Historical 49'),('comprise26','comprise 26'),('and23','and 23'),('Final76','Final 76')]:text=text.replace(old,new)
        path.write_text(text,encoding='utf-8',newline='\n')
    commits=subprocess.check_output(['git','log','--reverse','--format=%H %s',p['starting_head']+'..HEAD'],cwd=REPO,text=True)
    (DOC/'COMMITS.md').write_text('# v0.7.2 completed commits\n\nFull hashes and exact messages through the analysis/native-evidence commits follow. The final closeout commit is identified in the delivered response. Nothing was pushed.\n\n'+''.join('- '+line+'\n' for line in commits.splitlines()),encoding='utf-8',newline='\n')
    changed=set(subprocess.check_output(['git','diff','--name-status',p['starting_head']],cwd=REPO,text=True).splitlines())
    changed.update('A\t'+s for s in subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=REPO).decode().split('\0') if s)
    for name in ['FILES_CREATED_OR_MODIFIED.txt','FINAL_PACKAGE_HASHES.json']:changed.add('A\t'+str((RUN/'summary'/name).relative_to(REPO)).replace('\\','/'))
    (RUN/'summary/FILES_CREATED_OR_MODIFIED.txt').write_text('\n'.join(sorted(changed))+'\n',encoding='utf-8',newline='\n')
    files={str(path.relative_to(REPO)).replace('\\','/'):sha(path) for root in [RUN,DOC] for path in root.rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    for path in list((REPO/'scripts').glob('v072_*.py'))+[REPO/'tests/test_v072_optimization.py',REPO/'validation/ansys_v072_integration.py']:files[str(path.relative_to(REPO)).replace('\\','/')]=sha(path)
    write(RUN/'summary/FINAL_PACKAGE_HASHES.json',{'frozen_utc':now(),'scientific_status':overall,'files':files,'native_files_bound_separately':'native_result_manifests/*/NATIVE_ARTIFACTS.json and process receipts',
        'no_further_model_or_solver_jobs_this_registered_experiment':True,'push':False})
    print('CLOSED',overall,'frozen files',len(files),'native critical hashes',native_count,'mean gains',mean_gains,'MF-NF',comparison['MF_minus_NF_mean_script_gain'],flush=True)


if __name__=='__main__':closeout()
