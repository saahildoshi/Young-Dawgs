"""Close a truthful registered target-feasibility stop, never imply an LLM trial."""
import argparse
import importlib.metadata
import platform
import re
import subprocess
import sys
from pathlib import Path
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v072_interim import xml_counts
from scripts.v073_experiment import RUN,DOC,BASE,PREV,REFERENCE,TRIALS,now
from scripts.v073_analysis import csv_table

STATUS='MORPHOLOGY_ENVELOPE_AND_CONTROLLED_DEVELOPMENT_MECHANICS_COMPLETE__NO_TARGET_PASSES_REGISTERED_DIFFICULTY_GATE__LLM_INVERSE_DESIGN_NOT_EXECUTED'

def audit():
    assert not read(RUN/'target_selection/TARGET_FROZEN.json')['qualified_target']
    protected=read(RUN/'audit/PROTECTED_BEFORE.json')
    changed=[name for name,digest in protected.items() if sha(REPO/name)!=digest];assert not changed,changed
    write(RUN/'audit/PROTECTED_AFTER_FINAL.json',{'checked_utc':now(),'tracked_files_unchanged':len(protected),'changed':changed,'passed':True})
    old=read(PREV/'summary/FINAL_PACKAGE_HASHES.json')['files']
    for name,digest in old.items():assert sha(REPO/name)==digest,name
    totals={}
    for label,root in [('v072',PREV),('v073',RUN)]:
        total=0
        for path in (root/'native_result_manifests').glob('*/NATIVE_ARTIFACTS.json'):
            for item in read(path).values():assert sha(Path(item['path']))==item['sha256'];total+=1
        totals[label]=total
    assert totals=={'v072':497,'v073':154},totals
    target=read(RUN/'target_selection/TARGET_FROZEN.json');p=read(RUN/'protocol/PROTOCOL.json')
    assert sha(RUN/'protocol/PROTOCOL.json')==target['rule_sha256']
    assert sha(RUN/'protocol/FEASIBILITY_FROZEN.json')==target['feasibility_sha256']
    adaptation=read(RUN/'starting_generator/AUTHENTICATION.json')
    assert sha(RUN/'starting_generator/generator.py')==adaptation['adapted_sha256']
    assert sha(PREV/'starting_generator/generator.py')==adaptation['original_sha256']
    dataset=read(RUN/'controlled_variants/GEOMETRY_DATASET_FROZEN.json')
    for row in dataset['rows']:
        a=RUN/'controlled_variants'/row['trial_id']/f"seed_{row['seed']}.npy"
        assert sha(a)==row['source_array_sha256'] and int((np.load(a)==5).sum())==20731
    variants=read(RUN/'controlled_variants/VARIANTS_FROZEN.json')
    assert variants['generator_sha256']==sha(RUN/'controlled_variants/generator.py')
    assert variants['baseline_sha256']==sha(RUN/'starting_generator/generator.py')
    assert not (RUN/'heldout_structural_evaluation').exists()
    assert not list((RUN/'llm_trials').glob('*/response.txt'))
    tests={name:xml_counts(paths) for name,paths in {
        'active':[RUN/'verification/final_active_tests.xml'],
        'archived_replays':list((RUN/'verification/archive_replay').glob('*.xml')),
        'historical_licensed_artifacts':[RUN/'verification/historical_licensed_checks.xml'],
        'new_v073_licensed_artifacts':[RUN/'verification/new_licensed_checks.xml']}.items()}
    assert [tests[k]['tests'] for k in tests]==[945,475,125,27],tests
    assert all(v['failures']==v['errors']==v['skipped']==0 for v in tests.values()),tests
    receipts=[read(path) for path in BASE.glob('*/process_receipt.json')];assert len(receipts)==44
    samples=[sample for r in receipts for sample in r.get('resource_samples',[])]
    perf={'native_processes':44,'actual_source_models':22,'source_H1_development':17,'source_H2_development':5,
        'independent_readbacks':22,'actual_native_checkpoints':110,'unique_source_geometries_solved':17,
        'total_supervised_native_seconds':sum(r['runtime_seconds'] for r in receipts),
        'peak_process_tree_RSS_bytes':max(r['peak_tree_rss_bytes'] for r in receipts),
        'minimum_available_RAM_bytes':min(s['available_RAM_bytes'] for s in samples),
        'maximum_observed_commit_fraction':max(s['commit_fraction'] for s in samples if s.get('commit_fraction') is not None),
        'maximum_system_page_reads_per_second':max(s['page_reads_per_second'] for s in samples if s.get('page_reads_per_second') is not None),
        'raw_artifact_bytes':sum(path.stat().st_size for path in BASE.rglob('*') if path.is_file()),
        'native_base':str(BASE),'cores':2,'native_concurrency':1,'RSS_cap':None,
        'paging_caveat':'System hard-fault disk-read proxy; not per-solver or pagefile-only',
        'failures':'No native execution/acceptance failure; one unsolved infeasible development source and one initial historical workflow test file-lock failure preserved'}
    assert perf['total_supervised_native_seconds']<=p['resource_limits']['native_campaign_seconds']
    assert perf['raw_artifact_bytes']<=p['resource_limits']['raw_storage_budget_bytes']
    write(RUN/'performance/FINAL_SUMMARY.json',perf)
    write(RUN/'verification/FINAL_INTEGRITY.json',{'checked_utc':now(),'test_results':tests,'native_critical_hashes_verified':totals,
        'protected_initial_tracked_files_unchanged':len(protected),'v072_final_package_files_verified':len(old),
        'source_geometries_attempted':18,'exact_composition':18,'structurally_feasible':17,'H1_accepted':17,'H2_accepted':5,
        'genuine_independent_IF_trials':0,'genuine_independent_NF_trials':0,'heldout_attempts':0,'model_submissions':0,
        'frozen_rule_envelope_sources_and_arrays_unchanged':True,'pushed':False,'passed':True})
    write(RUN/'audit/FINAL_EXECUTION_ENVIRONMENT.json',{'python':sys.version,'platform':platform.platform(),
        'packages':{name:importlib.metadata.version(name) for name in ['numpy','scipy','scikit-image','Pillow','matplotlib','psutil','pytest']},
        'qualified_evaluator_sha256':sha(REPO/'scripts/v071_mechanics.py'),'mesh_APDL_source_sha256':sha(REPO/'metamaterial_eval/simulation/composite_elastic.py'),
        'descriptor_sha256':sha(REPO/'metamaterial_eval/composites/morphology_v073.py')})
    print('FINAL AUDIT PASS',len(protected),'protected files;',totals,'native hashes',flush=True)

def reports():
    target=read(RUN/'target_selection/TARGET_FROZEN.json');assert not target['qualified_target']
    summaries=read(RUN/'development_mechanics/SUMMARIES.json');perf=read(RUN/'performance/FINAL_SUMMARY.json');integrity=read(RUN/'verification/FINAL_INTEGRITY.json')
    auth=read(RUN/'starting_generator/AUTHENTICATION.json');p=read(RUN/'protocol/PROTOCOL.json')
    models=[read(path) for path in (RUN/'mechanical_response').glob('*.json')]
    def doc(name,text):
        # Report typography only; never apply normalization to source/native evidence.
        for old,new in {'exactly20':'exactly 20','All12':'All 12','all12':'all 12','all40':'all 40','All40':'All 40',
            'all22':'all 22','All90':'All 90','of10':'of 10','Calibration12':'Calibration 12','calibration12':'calibration 12',
            'BASE5/6':'BASE 5/6','phase5':'phase 5','labels1/5':'labels 1/5','MAT1/MAT2':'MAT1/MAT2',
            'displayed64':'displayed 64','the1mm':'the 1 mm','E1000/10000':'E = 1000/10000','nu0.30':'nu = 0.30',
            'from1636':'from 1636','to1753':'to 1753','baseline1691':'baseline 1691','SD34':'SD 34','and12':'and 12',
            'were0.547':'were 0.547','validation945':'validation 945','Validation945':'Validation 945',
            'Final validation945':'Final validation 945','evidence:17':'evidence: 17','All18,313':'All 18,313',
            'The33':'The 33','of945':'of 945','Archived475':'Archived 475','Historical125':'Historical 125',
            'comprise76':'comprise 76','New27':'New 27','comprise22':'comprise 22','Initial full validation had944':'Initial full validation had 944',
            'passed945':'passed 945','across9':'across 9','processes44':'processes 44',
            'models,22':'models, 22','readbacks,44':'readbacks, 44','and110':'and 110','on17':'on 17','at0.5':'at 0.5',
            'All17':'All 17','all17':'all 17','all93':'all 93'}.items():text=text.replace(old,new)
        text=re.sub(r'(\d)(MPa|GiB|px|mm)\b',r'\1 \2',text)
        (DOC/name).write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')
    table='| Family | Accepted H1 / attempted | Mean MPa | Sample SD MPa |\n|---|---:|---:|---:|\n'
    for t,r in summaries.items():table+=f"| {t} | {r['accepted']}/{r['attempted']} | {r['modulus']['mean']:.3f} | {r['modulus']['sample_SD']:.3f} |\n"
    difference=abs(target['proposed_target_MPa']-target['baseline_mean_MPa'])
    gate=f"The registered rule proposes {target['proposed_target_MPa']:.6f}MPa toward {target['selected_variant']}, but rejects it: baseline separation {difference:.6f}MPa is below the required {target['difficulty_threshold_MPa']:.6f}MPa. The ±{100*target['target_hit_relative_tolerance']:.1f}% proposal band contains the baseline mean. No actual target or J_target was frozen; their machine-readable values are null."
    limitations='P3 is one morphology-selected, supplied horizontally flipped SEM crop with provisional phase5 chemistry and unknown microscopy calibration. Both labels1/5 are solids; native MAT1/MAT2 is an explicit derived map. No overlay or displayed64px scale bar is included as geometry; pixels imply no micrometer calibration. E1000/10000MPa, nu0.30 and the1mm computational square/thickness are illustrative conventions. Perfect shared-node bonding, pixel corners, finite-domain loading, segmentation and a small observed family limit interpretation. No RVE, calibrated material prediction, isotropic tensor, damage/yield/fracture or manufacturing claim follows.'
    nextstep='The next separately registered study should establish a more reliable constrained generator and paired geometry–mechanics probes on enough seeds to distinguish family effects from placement noise, then select a demonstrably nontrivial target. Do not relax this envelope, replace failed seeds or change this target rule after outcomes. This limited matrix does not prove that the entire reference-like design space lacks useful mechanical variability.'
    status={key:'PASS_VERIFIED' for key in ['HISTORICAL_V072_EVIDENCE_PRESERVED','P3_REFERENCE_AUTHENTICATED','COMMON_STARTING_GENERATOR_AUTHENTICATED',
        'AREA_WEIGHTED_SHAPE_DESCRIPTORS_VALIDATED','ORIENTATION_DESCRIPTORS_VALIDATED','SPATIAL_ORGANIZATION_DESCRIPTORS_VALIDATED','GAP_TOLERANT_LANE_DIAGNOSTICS_VALIDATED',
        'HISTORICAL_LANE_CONTROLS_CHARACTERIZED','NEW_MORPHOLOGY_ENVELOPE_REGISTERED','CONTROLLED_VARIANTS_REGISTERED',
        'GEOMETRY_MECHANICS_DATASET_EXECUTED','NATIVE_DEVELOPMENT_CURVES_AVAILABLE','DEVELOPMENT_MESH_SENSITIVITY_ASSESSED','HELDOUT_ISOLATION_VERIFIED']}
    status.update(EXACT_COMPOSITION_BASELINE_QUALIFIED='EXACT_COUNT_DETERMINISM_DIVERSITY_PASS__12_OF12_CALIBRATION__NOT_FULL_MORPHOLOGY_RELIABILITY',
        REFERENCE_LIKE_BASELINE_FEASIBLE='REFERENCE_AND12_OF12_CALIBRATION_PASS__5_OF6_DEVELOPMENT_PASS',
        CONTROLLED_VARIANTS_STRUCTURALLY_FEASIBLE='ALL12_VARIANT_OUTPUTS_PASS__ONE_OF6_BASELINE_FAILS',
        MECHANICAL_TARGET_ATTAINABILITY_SUPPORTED='FEASIBLE_MODULI_MEASURED__NO_NONTRIVIAL_TARGET_PASSES_REGISTERED_GATE',
        TARGET_MODULUS_FROZEN='NOT_FROZEN__TARGET_DIFFICULTY_GATE_FAILED',
        INFORMATIVE_MECHANICAL_FEEDBACK_AUTHENTICATED='NATIVE_PAIRED_DATA_AVAILABLE__NO_EXPERIMENTAL_PACKET_SUBMITTED',
        EQUAL_REVISION_BUDGET_VERIFIED='FOUR_PER_ARM_ONE_RESPONSE_REGISTERED__ZERO_SUBMISSIONS',
        PHYSICAL_MATERIAL_CALIBRATION='NOT_CALIBRATED',REPRESENTATIVE_VOLUME_QUALIFICATION='NOT_QUALIFIED',
        AUTONOMOUS_MULTIGENERATION_OPTIMIZATION='NOT_STARTED',PAPER_READINESS='QUALIFIED_DEVELOPMENT_FEASIBILITY_RESULT__NO_INVERSE_DESIGN_OR_FEEDBACK_EFFECT_CLAIM')
    for key in ['MATCHED_IF_NF_PROMPTS_VERIFIED','GENUINE_IF_RESPONSES_CAPTURED','GENUINE_NF_RESPONSES_CAPTURED','FINAL_SCRIPTS_FROZEN',
        'EXACT_COMPOSITION_PRESERVED','MORPHOLOGY_ENVELOPE_PRESERVED','STOCHASTIC_DIVERSITY_PRESERVED','HELDOUT_NATIVE_MECHANICS_COMPLETE',
        'BASELINE_RELATIVE_TARGET_IMPROVEMENT','TARGET_MODULUS_MATCHING_SUPPORTED','TARGET_MATCHING_REFINEMENT_CONFIRMED','INFORMATIVE_FEEDBACK_ADVANTAGE_SUPPORTED',
        'CONSTRAINED_LLM_INVERSE_DESIGN_EXECUTED','REFERENCE_LIKE_MECHANICAL_OPTIMIZATION_SUPPORTED']:
        status[key]='NOT_EXECUTED_OR_ESTABLISHED__TARGET_GATE_FAILED'
    for key in ['F1_SOURCE_AUTHENTICATED','F1_VOID_PHASE_HANDLING_VERIFIED','F1_MECHANICAL_CONTROLS_QUALIFIED','F1_REFERENCE_NATIVE_MECHANICS',
        'F1_GENERATED_NATIVE_MECHANICS','F1_PRELIMINARY_MESH_SENSITIVITY','CROSS_FAMILY_MECHANICS']:status[key]='NOT_EXECUTED_IN_V073__OPTIONAL_TRACK_OMITTED'
    write(RUN/'summary/FINAL_SCIENTIFIC_STATUS.json',{'overall':STATUS,'completed_utc':now(),'independent_statuses':status,
        'registered_stop_reason':'User brief section36 and frozen prospective target-difficulty rule; valid feasibility-study outcome',
        'target_MPa':None,'J_target':None,'genuine_IF_responses':0,'genuine_NF_responses':0,'heldout_outputs':0})
    inventory=[{'trial_id':trial,'arm':trial[:2],'registered_opportunities':1,'actual_invocations':0,'status':'NOT_SUBMITTED_TARGET_GATE_FAILED',
        'model_interface':None,'reasoning':None,'prompt_sha256':None,'response_sha256':None,'module_sha256':None} for trial in TRIALS]
    write(RUN/'summary/LLM_TRIAL_INVENTORY.json',inventory);csv_table(RUN/'summary/LLM_TRIAL_INVENTORY.csv',inventory)
    write(RUN/'summary/UNEXECUTED_STAGES.json',{'matched_packets':False,'genuine_responses':False,'heldout_generation':False,'heldout_mechanics':False,
        'target_error':None,'target_hit_rate':None,'feedback_advantage':None,'F1_mechanics':False,'reason':STATUS})
    write(RUN/'audit/MODEL_INTERFACE_PREFLIGHT.json',{'ordinary_browser_ChatGPT_visible':True,'model_invocations':0,
        'temporary_chat_observed':True,'observed_notice':'This chat can reference memory, plugins, and custom instructions, but it won’t appear in your history',
        'memory_isolation_established':False,'exposed_model_or_reasoning_used':None,'browser_was_not_the_stop_reason':True})
    contracts=[]
    for r in models:
        s=read(RUN/'specimen_manifests'/f"{r['specimen_id']}.json")
        contracts.append({'specimen_id':r['specimen_id'],'partition':'development','mesh_level':r['mesh_level'],
            'phase_counts':s['phase_counts'],'source_array_sha256':s['source_array_sha256'],'mechanical_acceptance':r['accepted'],
            'actual_strains':r['engineering_strains'],'actual_nominal_stress_MPa':r['nominal_stresses_MPa'],
            'native_curve_columns':r['curve_columns'],'native_curve':r['native_curve'],'apparent_modulus_MPa':r['effective_modulus_MPa'],
            'target_MPa':None,'target_error':None,'native_result_sha256':r['native_result_sha256'],'native_fields_sha256':r['native_fields_sha256']})
    write(RUN/'summary/MECHANICAL_RESULT_CONTRACT.json',{'records':contracts,'missing_value_convention':'JSON null / CSV empty field means unavailable, never zero; all target scores unexecuted',
        'native_material_map':{'1':1,'5':2},'phase_properties_illustrative':True})
    h2table='| Family / seed3100 | H1 MPa | H2 MPa | Relative change |\n|---|---:|---:|---:|\n'
    for r in target['development_mesh_pairs']:h2table+=f"| {r['trial_id']} | {r['H1']:.6f} | {r['H2']:.6f} | {100*r['relative_mesh_change']:.4f}% |\n"
    doc('V0_7_3_MESH_CONFIRMATION.md','# Development mesh confirmation\n\n'+h2table+'\nAll five first-seed geometries were selected before outcomes and independently reopened. H2 subdivides each unchanged source pixel into2×2 quads, preserving count and phase geometry. No final held-out H2 cases exist. Largest observed relative change is'+f" {100*target['largest_relative_mesh_change']:.6f}%."+' The horizontal-bias first-seed reduction persists beyond combined observed H1/H2 changes. Elongation, vertical-bias and dispersion means do not receive the required first-seed effect support under the registered rule; this is not proof their true effects are zero.\n\n'+gate+'\n\nThere is no target-hit classification or target improvement to confirm. These differences are observed sensitivity diagnostics, not rigorous FE error bounds, complete mesh convergence or segmentation-resolution convergence.')
    phase=[]
    for t in summaries:
        records=[r for r in models if r['mesh_level']==1 and r['specimen_id'].startswith(t+'_development_')]
        phase.append({'family':t,'n':len(records),'matrix_p99_equivalent_over_nominal_mean':float(np.mean([r['phase_results']['1']['equivalent_percentiles_over_nominal']['p99'] for r in records])),
            'reinforcement_elastic_energy_fraction_mean':float(np.mean([r['phase_results']['2']['elastic_energy_fraction'] for r in records])),
            'matrix_mean_SYY_MPa':float(np.mean([r['phase_results']['1']['mean_syy_MPa'] for r in records])),
            'reinforcement_mean_SYY_MPa':float(np.mean([r['phase_results']['2']['mean_syy_MPa'] for r in records]))})
    write(RUN/'development_mechanics/PHASE_TRADEOFFS.json',phase);csv_table(RUN/'development_mechanics/PHASE_TRADEOFFS.csv',phase)
    trade='| Family | n | Matrix p99 equivalent / nominal | Reinforcement energy share | Matrix mean SYY MPa | Reinforcement mean SYY MPa |\n|---|---:|---:|---:|---:|---:|\n'
    for r in phase:trade+=f"| {r['family']} | {r['n']} | {r['matrix_p99_equivalent_over_nominal_mean']:.4f} | {r['reinforcement_elastic_energy_fraction_mean']:.4f} | {r['matrix_mean_SYY_MPa']:.4f} | {r['reinforcement_mean_SYY_MPa']:.4f} |\n"
    doc('V0_7_3_MORPHOLOGY_AND_MECHANICAL_TRADEOFFS.md','# Development morphology and mechanical trade-offs\n\nThe reference and all12 exact baseline calibration fields pass the prospective envelope. All40 known historical lanes violate new rules; none of10 historical BASE controls do. This is observed challenge-set discrimination, not blind validation. All12 new controlled variants pass, while one new baseline source fails near-spanning. Thus the baseline is not a universally reliable constrained generator.\n\nArea-weighted aspects/tails and anisotropy-weighted axial order include all observed regions; complete and boundary-censored populations remain separate. Finite correlations, multiscale strips, gap runs and diagnostic dilation cover full-field organization. The actual review remains visually compatible with irregular dispersed particles, but scalar acceptance alone cannot establish natural-material identity. No new LLM morphology exists to assess.\n\n'+trade+'\nActual H1 values at0.5% prescribed strain; normalized equivalent-stress percentiles distinguish concentration from nominal load. Phase stress/strain and energy share are element-associated, without cross-material nodal averaging. Selected first-seed H2 stress, strain, displacement and phase energy fields are shown with common disclosed color limits. Pixel-corner maxima are exploratory and imply no yielding, damage or fracture.\n\n'+limitations)
    doc('V0_7_3_LLM_INVERSE_DESIGN_EXPERIMENT.md','# Registered revision experiment — not submitted\n\nFour independent IF and four NF ordinary-ChatGPT trials, one response each and no repairs/BF arm, were registered before new mechanics. Common source, exact composition, morphology limits, physics, target and development structural information would be identical; only IF would receive actual paired curves/moduli and numerical sensitivity.\n\n'+gate+'\n\nUser brief section36 permits a valid feasibility-study stop when no useful target is established. Accordingly no prompts were submitted, no experimental responses/scripts were captured and no held-out seeds were opened. No matched prompt packet is claimed complete, and this is not a human-submission or browser-permission gate. Browser preflight succeeded; a temporary-chat notice explicitly allowed memory/plugin/custom-instruction context, so no isolation or backend identity is inferred. Actual model/interface/reasoning usage, prompt/response hashes, costs and tokens are unavailable because there were zero calls. Researcher probes and prepared analysis modules count as zero LLM trials.')
    doc('V0_7_3_HELDOUT_TARGET_RESULTS.md','# Held-out inverse design — unexecuted\n\n'+gate+'\n\nAll90 planned held-out structures and their mechanical evaluations remain unexecuted. Attempted BASE/IF/NF final outputs=0; genuine IF/NF responses=0. Exact-composition success, morphology feasibility, diversity, target errors/hits, BASE-relative improvements and IF/NF advantage are unavailable for final outputs, represented as null rather than zero performance. No final seed was replaced or sampled. The independent-unit comparison remains registered but untested. The development evidence does not establish target-property LLM capability or failure, or the value of informative feedback.')
    tests=integrity['test_results']
    validation='| Verification category | Passed |\n|---|---:|\n'+''.join(f"| {k} | {v['tests']} |\n" for k,v in tests.items())
    validation+='\nAll final categories have zero failures/errors/skips. The33 new focused tests are part of945 active tests, not additional evidence. Archived475 checks are unchanged-test replays across9 groups, not additional unique tests. Historical125 checks comprise76 v072,26 v071 and23 older artifact checks; no old solver ran. New27 checks comprise22 actual native source cases and5 campaign/provenance checks. Initial full validation had944 passes and one failure: an unchanged older exploration worker encountered WinError5 during atomic JSON replacement. Original XML/log/stderr/metadata remain preserved; a fresh full rerun passed945 without source changes, weakened tests or exclusions.\n\n'
    validation+=f"Actual native processes44=22 source solves+22 independent readbacks, 110 actual checkpoints on17 unique categorical geometries (five additional refinements). Supervised native time {perf['total_supervised_native_seconds']:.3f}s ({perf['total_supervised_native_seconds']/60:.3f}min), peak tree RSS {perf['peak_process_tree_RSS_bytes']/2**30:.3f}GiB, minimum available RAM {perf['minimum_available_RAM_bytes']/2**30:.3f}GiB; raw artifact bytes {perf['raw_artifact_bytes']} ({perf['raw_artifact_bytes']/2**30:.3f}GiB). Two cores/one native job, health supervision, no fixed RSS cap/pagefile changes/unrelated termination. Raw native binaries remain outside Git under `{BASE}`. The inherited job-name prefix v071 does not denote historical execution; versioned directories, inputs, timestamps and receipts identify these new jobs.\n\n"
    validation+=f"All {integrity['protected_initial_tracked_files_unchanged']:,} initially tracked files, {integrity['v072_final_package_files_verified']} prior package records,497 prior native hashes and154 new critical native hashes authenticate. Native source inputs/results, complete constraints, phase areas, materials, connectivity, reaction balance, energy/work and constitutive fields qualify through the unchanged evaluator. Local text exports received a follow-up Git normalization commit; raw native evidence and original failure logs remain intact. The inherited exact-release manual-access limitation remains documented in v071; no claim of new experimental or independent physical validation is made.\n\n"
    validation+='| Scientific acceptance state | Outcome |\n|---|---|\n'+''.join(f'| {k} | {v} |\n' for k,v in status.items())
    doc('V0_7_3_VALIDATION.md','# Final validation and independent scientific states\n\n'+validation)
    summary='We established a morphology-constrained development study for P3, building on genuine microscopy-based LLM generation in v0.7.0 and verified native stress–strain evaluation in v0.7.1. The v0.7.2 revisions roughly doubled apparent stiffness by forming segmented vertical lanes; measured baseline feedback did not outperform the equal-attempt control.\n\n'
    summary+='The new common generator is an explicitly researcher-adapted version of captured B02. Every new calibration/development source preserves exactly20,731 reinforcement pixels. Independently checked shape-tail, orientation and spatial-organization measures distinguish all40 known historical lanes while accepting the reference and12 calibration realizations. One of six additional baseline development fields fails the near-spanning rule and remains unsolved.\n\n'
    summary+='Seventeen feasible geometries received actual five-point ANSYS curves with independent readback. Four controlled morphology probes produced family means from1636.45 to1753.01MPa, compared with baseline1691.64MPa and sample SD34.92MPa across five feasible outputs. All five predetermined H2 cases passed; observed modulus changes were0.547–0.624%.\n\n'+gate+'\n\n'
    summary+='We therefore stopped before the planned model revisions and held-out evaluation, as registered. This is a qualified development-feasibility result, not a completed LLM inverse-design comparison. It neither establishes nor refutes an informative-feedback advantage. '+nextstep+'\n\n'+limitations
    doc('DR_WANG_SUMMARY.md','# Research summary for Dr. Wang\n\n'+summary)
    commits=subprocess.check_output(['git','log',p['starting_head']+'..HEAD','--reverse','--format=%H%x09%s'],cwd=REPO,text=True).strip()
    doc('COMMITS.md','# v0.7.3 commits\n\nStarting HEAD `'+p['starting_head']+'` on master. No push, reset, amendment or history rewrite.\n\n'+ '\n'.join('- `'+line.split('\t')[0]+'` — '+line.split('\t',1)[1] for line in commits.splitlines())+'\n\nThe final closeout commit is created after these reports are frozen; its full hash and exact message are supplied in the final delivery. A commit cannot embed its own full hash.')
    handoff='# v0.7.3 completed development-feasibility handoff\n\n**'+STATUS+'**\n\n'+gate+'\n\n'+table+'\nNo genuine IF/NF trial, matched packet submission, held-out output, final target error or feedback-effect comparison was executed. This is the registered target-feasibility stop, not successful inverse design or an unavailable-interface gate.\n\n'
    handoff+=f"The authenticated original B02 hash is `{auth['original_sha256']}`. The common researcher adaptation hash is `{auth['adapted_sha256']}`. Its only baseline change is bounded topology-safe internal boundary count adjustment; historical captured code remains unchanged. Calibration12/12 pass exact count, determinism, morphology and diversity; development BASE5/6 pass morphology. All12 controlled probe outputs pass with exact count. All40 historical lane controls are detected by the new envelope while retaining their original accepted status.\n\n"
    handoff+=f"Native evidence:17 H1+5 H2 source models,22 independent readbacks,44 processes and110 actual checkpoints; {perf['total_supervised_native_seconds']/60:.3f} native min, peak tree RSS {perf['peak_process_tree_RSS_bytes']/2**30:.3f}GiB, raw {perf['raw_artifact_bytes']/2**30:.3f}GiB. Final validation945 active /475 archived replays /125 historical licensed /27 new licensed checks passed. The initial unrelated Windows file-lock test failure and one morphology-infeasible source are preserved. All18,313 initially tracked files remain byte-identical.\n\n"
    handoff+=limitations+'\n\n'+nextstep+'\n\nOptional BF, horizontal mechanics, conventional target control and F1 mechanics were omitted to keep this study within the registered primary scope. No old porous/contact,3D, manufacturing or autonomous generation was started. Nothing was pushed. Stop here.\n\nSee [target decision](V0_7_3_TARGET_SELECTION.md), [actual development mechanics](V0_7_3_CONTROLLED_GEOMETRY_MECHANICS.md), [mesh evidence](V0_7_3_MESH_CONFIRMATION.md), [figures](V0_7_3_FIGURES.md), [validation](V0_7_3_VALIDATION.md), [all93 requested handoff answers](V0_7_3_HANDOFF_ANSWERS.md), and [commits](COMMITS.md).\n'
    doc('V0_7_3_HANDOFF.md',handoff)
    gallery='# Actual v0.7.3 figure package\n\nNo final LLM-generated or held-out figures exist because no target passed. Geometry panels below are authenticated reference annotations or explicitly researcher-prepared development/calibration sources. Synthetic fixtures and diagnostic dilation are labeled. Native fields/curves derive from actual results. Pixel axes establish no physical microscopy scale.\n\n'
    captions={r['path']:r['caption'] for r in read(RUN/'figures/DEVELOPMENT_FIGURE_MANIFEST.json')['figures']}
    captions.update({'MORPHOLOGY_ENVELOPE_REVIEW.png':'Reference, first two calibration seeds, historical first-seed lanes and first-seed variants; actual identical phase colors and pixel scale.',
        'INDEPENDENT_DESCRIPTOR_FIXTURES.png':'Thirteen synthetic descriptor fixtures; not microscopy or native mechanical evidence.',
        'INFEASIBLE_BASELINE_DIAGNOSTIC.png':'Preserved actual failed baseline source and evaluator-only dilation; never a modified mechanical specimen.',
        'NATIVE_DEVELOPMENT_FIELDS.png':'Preselected first development seed of each family, actual H2 fields/energy shares. Common stress/strain limits use max specimen99.5percentiles with clipping; raw extremes remain. No cross-material averaging; native nodal norm is derived from UX/UY.'})
    for name,caption in captions.items():gallery+=f'## {name}\n\n{caption}\n\n![{caption}]({(RUN/"figures"/name).as_posix()})\n\n'
    doc('V0_7_3_FIGURES.md',gallery)
    write(RUN/'figures/FINAL_FIGURE_MANIFEST.json',{'figures':[{'path':name,'sha256':sha(RUN/'figures'/name),'caption':caption} for name,caption in captions.items()],
        'visual_QA':'Actual geometry review, gate/mesh plot, curves and native field layout visually inspected; fixed selection and common geometry colors retained'})
    print('REPORTS COMPLETE',STATUS,flush=True)

def freeze():
    path=RUN/'summary/FINAL_PACKAGE_HASHES.json';assert not path.exists()
    # Authenticate the actual pre-mechanics Git snapshots, not merely current files.
    snapshots={
        'experiments/pipeline_v0.7.3/run_001/protocol/PROTOCOL.json':'88e72bf2c70b596c7232d3d256ae463e1353d826',
        'experiments/pipeline_v0.7.3/run_001/protocol/EVALUATOR_ONLY_SEEDS.json':'88e72bf2c70b596c7232d3d256ae463e1353d826',
        'experiments/pipeline_v0.7.3/run_001/protocol/FEASIBILITY_FROZEN.json':'d917ead2bd6df4acc9309956a3a06285f0ae2df5',
        'experiments/pipeline_v0.7.3/run_001/starting_generator/generator.py':'d917ead2bd6df4acc9309956a3a06285f0ae2df5',
        'experiments/pipeline_v0.7.3/run_001/controlled_variants/VARIANTS_FROZEN.json':'d917ead2bd6df4acc9309956a3a06285f0ae2df5',
        'experiments/pipeline_v0.7.3/run_001/controlled_variants/GEOMETRY_DATASET_FROZEN.json':'d917ead2bd6df4acc9309956a3a06285f0ae2df5',
        'metamaterial_eval/composites/morphology_v073.py':'d917ead2bd6df4acc9309956a3a06285f0ae2df5'}
    verified=[]
    for name,commit in snapshots.items():
        raw=subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=REPO)
        assert raw==(REPO/name).read_bytes(),name
        verified.append({'path':name,'pre_mechanics_commit':commit,'current_sha256':sha(REPO/name),'byte_identical':True})
    write(RUN/'audit/FROZEN_INPUT_COMMIT_AUTHENTICATION.json',{'checked_utc':now(),'records':verified,'passed':True})
    files=sorted([p for root in [RUN,DOC] for p in root.rglob('*') if p.is_file()]+[p for p in (REPO/'scripts').glob('v073_*.py')]+[REPO/'metamaterial_eval/composites/morphology_v073.py',REPO/'validation/ansys_v073_integration.py']+list((REPO/'tests').glob('test_v073_*.py')))
    inventory=RUN/'summary/FILES_CREATED_OR_MODIFIED.txt'
    inventory.write_text('\n'.join(str(p.relative_to(REPO)).replace('\\','/') for p in sorted(set(files+[inventory,path])))+'\n',encoding='utf-8',newline='\n')
    files.append(inventory)
    write(path,{'frozen_utc':now(),'status':STATUS,'files':{str(p.relative_to(REPO)).replace('\\','/'):sha(p) for p in files},'final_commit_record':'Final response supplies the post-freeze closeout commit; no push'})
    print('FINAL PACKAGE FROZEN',len(files),'files',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','reports','freeze']);a=p.parse_args()
    {'audit':audit,'reports':reports,'freeze':freeze}[a.action]()
