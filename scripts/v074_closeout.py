"""Authenticate the completed registered study and produce concise evidence reports."""
import argparse
import importlib.metadata
import platform
import subprocess
import sys
from pathlib import Path
import numpy as np
from scripts.v070_protocol import read, write, sha
from scripts.v074_experiment import RUN, DOC, BASE, PREV, REPO, ASSETS, now
from scripts.v072_interim import xml_counts


def audit():
    assert (RUN/'performance/FINAL_MECHANICS_COMPLETE.json').exists()
    protected=read(RUN/'audit/PROTECTED_BEFORE.json')
    changed=[name for name,digest in protected.items() if sha(REPO/name)!=digest]
    assert not changed,changed
    write(RUN/'audit/PROTECTED_AFTER_FINAL.json',{'checked_utc':now(),'tracked_files_unchanged':len(protected),'changed':changed,'passed':True})
    previous=read(PREV/'summary/FINAL_PACKAGE_HASHES.json')['files']
    for name,digest in previous.items():assert sha(REPO/name)==digest,name
    frozen=read(RUN/'frozen_scripts/ALL_SIXTEEN_SCRIPTS_FROZEN.json')
    for name,digest in frozen['files'].items():assert sha(REPO/name)==digest,name
    for key,name in [('protocol_sha256','PROTOCOL.json'),('feasibility_sha256','FEASIBILITY_FROZEN.json'),('seed_partition_sha256','EVALUATOR_ONLY_SEEDS.json')]:
        assert sha(RUN/'protocol'/name)==frozen[key]
    assert sha(RUN/'protocol/FEASIBILITY_FROZEN.json')==sha(PREV/'protocol/FEASIBILITY_FROZEN.json')
    for name,digest in read(RUN/'fabrication/DELIVERED_ASSETS.json')['files'].items():assert sha(ASSETS/name)==digest,name
    f1_report=read(RUN/'f1/REPORT_MANIFEST.json')
    for name,digest in f1_report['files'].items():assert sha(RUN/name)==digest,name
    assert sha(DOC/'V0_7_4_F1_MECHANICAL_RESULTS.md')==f1_report['report_sha256']
    hashes={}; unavailable=[]
    for label,root in [('prior_v073',PREV),('v074',RUN)]:
        count=0
        for path in sorted((root/'native_result_manifests').glob('*/NATIVE_ARTIFACTS.json')):
            for item in read(path).values():
                if Path(item['path']).is_file():
                    assert sha(Path(item['path']))==item['sha256'],item['path']
                    count+=1
                else:
                    unavailable.append({'version':label,'model':path.parent.name,
                        'file':item['path'],'recorded_sha256':item['sha256']})
        hashes[label]=count
    tests={name:xml_counts(paths) for name,paths in {
        'active':[RUN/'tests/final_active_software.xml'],
        'archived_replays':sorted((RUN/'tests/archived_replay').glob('*.xml')),
        'licensed_current_heldout_raw':[RUN/'tests/final_native_checks.xml'],
        'fabrication':[RUN/'tests/final_STL_checks.xml'],
    }.items()}
    assert all(v['tests']>0 and v['failures']==v['errors']==v['skipped']==0 for v in tests.values()),tests
    # Compact process records retain the original earlier execution evidence.
    # Counting only presently available raw folders would undercount that work.
    executions=[read(p) for p in sorted((RUN/'native_result_manifests').glob('*/EXECUTION.json'))]
    receipts=[r['process'] for r in executions]
    source=[r for r in executions if r['kind']=='LICENSED_SOURCE_SOLVE']
    post=[r for r in executions if r['kind']=='INDEPENDENT_READ_ONLY_RST_REOPEN']
    assert len(receipts)==len(executions)==len(source)+len(post)
    assert all(r['native_process_ok'] for r in executions)
    p3=[read(p) for p in (RUN/'mechanical_response').glob('*.json')]
    f1=[read(p) for p in (RUN/'f1/mechanical_response').glob('*.json')]
    assert len(p3)+len(f1)==len(source)==len(post)
    assert all(r['accepted'] and all(r['checks'].values()) for r in p3+f1)
    samples=[s for r in receipts for s in r.get('resource_samples',[])]
    perf={'completed_utc':now(),'actual_source_solves':len(source),'independent_readback_processes':len(post),
        'native_processes':len(receipts),'actual_native_checkpoints':5*len(source),
        'accepted_source_models':len(p3)+len(f1),'P3_source_models':len(p3),'F1_source_models':len(f1),
        'source_H1':sum(r['mesh_level']==1 for r in p3+f1),'source_H2':sum(r['mesh_level']==2 for r in p3+f1),
        'total_supervised_native_seconds':sum(r['runtime_seconds'] for r in receipts),
        'source_solve_seconds':sum(r['process']['runtime_seconds'] for r in source),
        'readback_seconds':sum(r['process']['runtime_seconds'] for r in post),
        'peak_process_tree_RSS_bytes':max(r['peak_tree_rss_bytes'] for r in receipts),
        'minimum_available_RAM_bytes':min(s['available_RAM_bytes'] for s in samples),
        'maximum_observed_commit_fraction':max((s['commit_fraction'] for s in samples if s.get('commit_fraction') is not None),default=None),
        'maximum_system_page_reads_per_second':max((s['page_reads_per_second'] for s in samples if s.get('page_reads_per_second') is not None),default=None),
        'raw_artifact_bytes':sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()),
        'native_base':str(BASE),'cores':2,'native_concurrency':1,'RSS_cap':None,
        'performance_evidence':'All retained versioned execution records, including earlier records whose raw folders are currently unavailable',
        'raw_storage_scope':'Currently present raw native files; earlier missing raw folders cannot be remeasured',
        'native_failures':0,'paging_caveat':'System disk hard-fault proxy, not per-process paging or a pagefile-only measurement'}
    limits=read(RUN/'protocol/PROTOCOL.json')['resource_limits']
    assert perf['native_processes']<=limits['maximum_native_jobs']
    assert perf['total_supervised_native_seconds']<=limits['native_campaign_seconds']
    assert perf['raw_artifact_bytes']<=limits['raw_storage_budget_bytes']
    write(RUN/'performance/FINAL_SUMMARY.json',perf)
    write(RUN/'audit/FINAL_RAW_AVAILABILITY.json',{'checked_utc':now(),
        'available_critical_hashes_verified':hashes,'unavailable_critical_files':unavailable,
        'all_recorded_raw_files_available':not unavailable,
        'limitation':'Earlier raw ANSYS folders absent; exact cause/removal time unknown. Retained immutable records/curves and prior passed checks do not replace a current raw-file hash verification.'})
    write(RUN/'audit/FINAL_INTEGRITY.json',{'checked_utc':now(),'passed':not unavailable,
        'available_and_tracked_checks_passed':True,
        'status':'HOLD_EARLIER_RAW_ANSYS_PRESERVATION' if unavailable else 'PASS',
        'passed_scope':'Tracked protected files, frozen inputs, current held-out raw evidence and delivered STL/toolpaths; earlier raw preservation has a separate HOLD',
        'protected_files_unchanged':len(protected),'previous_package_files_verified':len(previous),
        'critical_native_hashes_verified':hashes,'all_sixteen_sources_and_prompts_unchanged':True,
        'test_results':tests,'fabrication_assets_unchanged':True,'pushed':False,
        'all_recorded_raw_files_available':not unavailable,
        'unavailable_critical_native_file_count':len(unavailable)})
    write(RUN/'audit/FINAL_EXECUTION_ENVIRONMENT.json',{'python':sys.version,'platform':platform.platform(),
        'packages':{name:importlib.metadata.version(name) for name in ['numpy','scipy','scikit-image','Pillow','matplotlib','psutil','pytest','trimesh','manifold3d']},
        'qualified_evaluator_sha256':sha(REPO/'scripts/v071_mechanics.py'),
        'composite_mesh_sha256':sha(REPO/'metamaterial_eval/simulation/composite_elastic.py'),
        'three_phase_mesh_sha256':sha(REPO/'metamaterial_eval/simulation/three_phase_elastic.py'),
        'descriptor_sha256':sha(REPO/'metamaterial_eval/composites/morphology_v073.py')})
    print('TRACKED/CURRENT INTEGRITY PASS; EARLIER RAW', 'HOLD' if unavailable else 'PASS',perf['native_processes'],tests,flush=True)


def doc(name,text):
    (DOC/name).write_text(text.rstrip()+'\n',encoding='utf-8',newline='\n')


def percent(value):return 'unavailable' if value is None else f'{value*100:.4f}%'


def reports():
    p=read(RUN/'protocol/PROTOCOL.json')
    integrity=read(RUN/'audit/FINAL_INTEGRITY.json');perf=read(RUN/'performance/FINAL_SUMMARY.json')
    availability=read(RUN/'audit/FINAL_RAW_AVAILABILITY.json')
    a=RUN/'target_property_analysis'
    summaries=read(a/'SCRIPT_SUMMARIES.json');changes=read(a/'WITHIN_CONVERSATION_CHANGES.json')
    comparison=read(a/'IF_VERSUS_NF.json');sensitivity=read(a/'SENSITIVITY_WITHOUT_NF01.json')
    mesh=read(a/'MESH_CONFIRMATION.json');meshpaired=read(a/'MESH_PAIRED_CHANGES.json')
    mesh_arms=read(a/'MESH_ARM_COMPARISON.json')
    results=read(a/'HELDOUT_RESULTS.json');generation=read(RUN/'audit/HELDOUT_GENERATION_COMPLETE.json')
    h1=[r for r in results if r['mesh_level']==1];h2=[r for r in results if r['mesh_level']==2]
    table='| Conversation | Initial valid/native | Revised valid/native | Initial mean absolute error | Revised mean absolute error | Initial minus revised (percentage points) |\n|---|---:|---:|---:|---:|---:|\n'
    for c in changes:
        pair=[next(r for r in summaries if r['trial_id']==c['trial_id'] and r['revision']==rev) for rev in (0,1)]
        table+=f"| {c['trial_id']} | {pair[0]['mechanically_accepted']}/6 | {pair[1]['mechanically_accepted']}/6 | {percent(c['initial_mean_error'])} | {percent(c['revised_mean_error'])} | {100*c['initial_minus_revised_mean_error']:.4f} |\n"
    arm='| Arm | Independent conversations | Initial mean script error | Revised mean script error | Mean within-conversation reduction (pp) |\n|---|---:|---:|---:|---:|\n'
    for label,r in comparison['arms'].items():
        arm+=f"| {label} | {r['registered_conversations_in_analysis']} | {percent(r['initial_script_errors']['mean'])} | {percent(r['revised_script_errors']['mean'])} | {100*r['within_conversation_error_reduction']['mean']:.4f} |\n"
    observed=[]
    for label,r in comparison['arms'].items():
        reduction=r['within_conversation_error_reduction']['mean']
        direction='decreased' if reduction>0 else 'increased' if reduction<0 else 'was unchanged'
        observed.append(f"{label} mean script target error {direction}: {percent(r['initial_script_errors']['mean'])} initial to {percent(r['revised_script_errors']['mean'])} revised.")
    observedtext='H1 descriptive result: '+' '.join(observed)
    initialhits=sum(r['target_hit'] is True for r in h1 if r['revision']==0)
    revisedhits=sum(r['target_hit'] is True for r in h1 if r['revision']==1)
    hittext=f'Initial scripts already produced {initialhits}/48 attempted target-band hits; revised scripts produced {revisedhits}/48. Failed attempts stay in these denominators. The initial hit rate and low initial errors limit the remaining margin for improvement; the target and scoring rule were preserved.'
    limitations='P3 remains one morphology-selected, supplied horizontally flipped SEM crop, a genuine geometry-preserving augmentation with provisional label 5 carbide identity. Labels 1 and 5 are retained in arrays and explicitly mapped to native MAT1/MAT2. Pixel units provide no micrometer calibration. No display overlay or displayed 64-pixel scale bar enters the source geometry or model image. The 1 mm computational square/thickness, E = 1000/10000 MPa, nu = 0.30, ideal shared-node bonding and small-strain plane stress are illustrative. These finite-domain apparent moduli do not establish a physical material prediction, RVE, isotropic tensor, yield, damage or fracture.'
    continuity='All eight initial generators and eight revisions are genuine ordinary-ChatGPT responses. Every revision used the original /c/conversation ID, without reattaching an old script or starting a replacement chat. The exposed interface setting was High; exact backend identity/version, tokens and cost were not exposed. The first four chats displayed a Pipeline Tests project path on reopening, while the last four displayed normal conversation paths. Project/account memory and personalization were not isolated. NF_01 contains one unintended extra user turn consisting only of the ChatGPT root URL and a nonscientific assistant link reply; it received no extra code or scientific feedback. Thus each trial has one scientific revision, but the strict equal total-message budget fails for NF_01. Chronological UI captures, canonical/observed URLs, exact prompt files, raw returned code and hashes preserve this deviation. The registered trial is retained and a descriptive analysis excluding NF_01 is reported; it does not repair the protocol deviation.'
    contrast=f"Revised script-error contrast NF minus IF = {100*comparison['revised_error_advantage_NF_minus_IF']:.4f} percentage points (positive favors IF). The contrast of within-conversation improvements IF minus NF = {100*comparison['improvement_advantage_IF_minus_NF']:.4f} pp. Excluding NF_01 leaves four IF and three NF conversations: revised-error contrast {100*sensitivity['revised_error_advantage_NF_minus_IF']:.4f} pp and improvement contrast {100*sensitivity['improvement_advantage_IF_minus_NF']:.4f} pp. These are unweighted means of script-level results; stochastic seeds are nested observations, never independent LLM trials. NF_03 initial has only four accepted outputs, so its conditional six-versus-four comparison is supplemented by the common-accepted-seed analysis in the data tables. No failure penalty, significance test, confidence claim or generalized causal advantage is inferred."
    acceptedmesh=[r for r in mesh if r['relative_mesh_change'] is not None]
    maxchange=max(r['relative_mesh_change'] for r in acceptedmesh)
    meshtext=f"All {len(h2)} registered H2 slots are accounted for: {len(acceptedmesh)} actual refined source solves and one unsolved structurally failed NF_03 initial seed 5001, with no replacement. Every script uses the preselected seeds 5000 and 5001. Observed relative modulus changes range from {percent(min(r['relative_mesh_change'] for r in acceptedmesh))} to {percent(maxchange)}; {sum(r['within_2pct_mesh_tolerance'] for r in acceptedmesh)}/{len(acceptedmesh)} meet the registered 2% tolerance. The paired H1/H2 table records whether each initial-to-revised error reduction persists and whether it exceeds the sum of the two observed mesh shifts divided by target. This conservative comparison is a sensitivity diagnostic, not a rigorous error bound or full convergence proof. It tests two seeds per script, not the whole six-seed mean."
    meshtable='| Conversation | Matched refined seeds | H1 error reduction (pp) | H2 error reduction (pp) | Positive at both levels | H2 reduction exceeds combined observed shifts |\n|---|---:|---:|---:|---:|---:|\n'
    for r in meshpaired:
        valid=[v for v in r['paired_checks'] if v['H2_initial_minus_revised_error'] is not None]
        meshtable+=f"| {r['trial_id']} | {len(valid)} | {100*r['H1_error_reduction']['mean']:.4f} | {100*r['H2_error_reduction']['mean']:.4f} | {sum(v['improvement_persists'] for v in valid)}/{len(valid)} | {sum(v['H2_improvement_exceeds_combined_observed_changes'] for v in valid)}/{len(valid)} |\n"
    meshcontrast=f"On only mutually accepted preselected refined seeds, the unweighted conversation-level H2 improvement contrast IF minus NF is {100*mesh_arms['all_registered']['H2_improvement_advantage_IF_minus_NF']:.4f} pp; excluding NF_01 gives {100*mesh_arms['without_NF01']['H2_improvement_advantage_IF_minus_NF']:.4f} pp. NF_03 contributes one paired seed. This restricted sensitivity comparison is not confirmation of the full six-seed primary arm estimate."
    preservation=('Earlier raw ANSYS folders are currently absent from their recorded local paths. The original committed results, native execution/readback receipts, compact curves, expected hashes, figures and earlier passing test records are preserved, but current rehashing/reopening of those earlier raw files is unavailable. The cause and removal time are unknown. The current held-out raw files were verified directly. No old scientific case was rerun to conceal the gap. Generic slicer G-code was independently reproduced byte-for-byte from the same engine/settings/STLs and its original hashes verified; recovery receipts distinguish those new deterministic slices from the original executions. This is a raw-preservation limitation, not a new native solve failure.') if availability['unavailable_critical_files'] else 'All recorded raw native files are currently available and their critical hashes authenticate.'
    states={key:'PASS' for key in ['P3_TARGET_FROZEN','P3_MORPHOLOGY_POLICY_PRESERVED','P3_STARTING_GENERATOR_QUALIFIED',
        'GENUINE_INITIAL_CHATGPT_SCRIPTS_CAPTURED','SAME_CONVERSATION_FEEDBACK_VERIFIED','GENUINE_IF_REVISIONS_CAPTURED','GENUINE_NF_REVISIONS_CAPTURED',
        'P3_HELDOUT_STRUCTURAL_EVALUATION','P3_HELDOUT_NATIVE_MECHANICS','SCIENTIFIC_REVISION_BUDGET_ONE_PER_CONVERSATION',
        'F1_REFERENCE_AUTHENTICATED','F1_THREE_PHASE_SEMANTICS_VERIFIED','F1_VOID_GEOMETRY_QUALIFIED','F1_NATIVE_CONTROLS_PASSED',
        'F1_REFERENCE_STRESS_STRAIN','F1_GENERATED_STRESS_STRAIN','F1_PRELIMINARY_MESH_SENSITIVITY',
        'STL_SOURCE_AUTHENTICATED','STL_EXPORTED','STL_WATERTIGHT','STL_MANIFOLD','STL_SINGLE_SOLID','STL_PRINTABILITY_CHECKED',
        'STL_SLICER_VERIFIED','STL_PREVIEW_CREATED','STL_PRINTING_INSTRUCTIONS_CREATED']}
    states.update(EQUAL_REVISION_BUDGET_VERIFIED='FAIL',P3_TARGET_ERROR_IMPROVEMENT='HOLD',INFORMATIVE_FEEDBACK_ADVANTAGE='HOLD',
        P3_H2_MESH_CONFIRMATION='PASS' if maxchange<=.02 else 'FAIL',PHYSICAL_MATERIAL_CALIBRATION='NOT_VERIFIED',ACTUAL_PHYSICAL_PRINT='NOT_RUN',
        EARLIER_RAW_ANSYS_PRESERVATION='HOLD' if availability['unavailable_critical_files'] else 'PASS')
    for label,r in comparison['arms'].items():
        states[f'OBSERVED_H1_{label}_MEAN_TARGET_ERROR_REDUCTION']='PASS' if r['within_conversation_error_reduction']['mean']>0 else 'FAIL'
    write(RUN/'summary/FINAL_SCIENTIFIC_STATUS.json',{'created_utc':now(),'states':states,
        'status':'REGISTERED_GENUINE_SAME_CONVERSATION_PILOT_COMPLETE__DESCRIPTIVE_RESULTS_WITH_PROTOCOL_AND_GENERALIZATION_LIMITS',
        'state_scope':{'P3_TARGET_ERROR_IMPROVEMENT':'HOLD for an unqualified capability claim; actual positive/negative descriptive results are reported per script and arm',
            'INFORMATIVE_FEEDBACK_ADVANTAGE':'HOLD for an unqualified causal advantage; numerical descriptive contrasts retained',
            'EQUAL_REVISION_BUDGET_VERIFIED':'FAIL strict total message equality due NF01; one scientific revision per conversation PASS',
            'STL_states':'Qualified P3 simplified relief and framed porous presentation model; exact P3 relief fails manifold check',
            'F1_PRELIMINARY_MESH_SENSITIVITY':'PASS execution/evidence, not full convergence; observed 2.54–3.24% changes'}})
    doc('V0_7_4_P3_INVERSE_DESIGN_RESULTS.md','# P3 same-conversation target-matching pilot\n\n'+observedtext+'\n\n'+hittext+'\n\n'
        'The registered target was 1640 MPa (J = 1.640), with a ±2% hit band of 1607.2–1672.8 MPa. Four IF and four NF initial/revised script pairs were frozen together before final generation. No script was manually repaired or revised after held-out evaluation. IF received its own three actual development curves/moduli/errors and authenticated v0.7.3 controlled geometry–mechanics; NF received matched structural information and unchanged physics/target without measured mechanics. The final seeds and evaluation masks were withheld from every generator conversation.\n\n'
        f'All 96 held-out attempts are preserved. {generation["generated"]} generated arrays have exact 20,731/44,805 phase composition and pass the complete unchanged morphology envelope; two NF_03 initial attempts exhausted the eight-candidate bound. All 16 generated cohorts pass their observed diversity diagnostics, but only 15/16 initial/revised generators meet the full six-of-six structural criterion. All eight revised scripts pass six-of-six. The two failed initial outputs have null mechanics and remain in denominators.\n\n'+table+'\n'+arm+'\n'+contrast+'\n\n'
        f'Actual accepted H1 source solves: {sum(r["apparent_modulus_MPa"] is not None for r in h1)}/96 attempted slots. Actual H2 source solves: {len(acceptedmesh)}/32 slots. Every accepted case contains five solved strain checkpoints and a separate native result-file reopening. Full per-seed moduli, bias, mean/median errors, sample SD, target hits, timing, diversity and failure records are in `target_property_analysis/`; `COMPACT_SCRIPT_TABLE.csv` is the flat sixteen-row comparison.\n\n'+meshtext+'\n\n'+meshtable+'\n'+meshcontrast+'\n\n'
        'The fixed first-seed figures show dispersed inclusions without the earlier continuous reinforcement lanes. They also show visible differences from the selected reference: some scripts use narrower size populations or more even spacing, and revisions can change orientation. Passing the frozen envelope is not equivalence to the natural image distribution. All successful arrays are unique within each cohort and their rigid-invariant diversity diagnostics pass; these diagnostics do not establish coverage of the true material distribution. Initial/revised paired array differences are recorded separately.\n\n'+continuity+'\n\n'+preservation+'\n\n'+limitations+'\n\n'
        'See [figures](V0_7_4_FIGURES.md), [validation](V0_7_4_VALIDATION.md), [F1](V0_7_4_F1_MECHANICAL_RESULTS.md) and [handoff](V0_7_4_HANDOFF.md).')
    doc('DR_WANG_SUMMARY.md','# Research summary for Dr. Wang\n\n'
        'The project has demonstrated genuine LLM generation of multiple microscopy-based microstructure families and actual ANSYS stress–strain evaluation of P3 composites. Earlier stiffness maximization produced large gains by creating artificial reinforcement lanes, which motivated stronger shape, orientation and spatial-organization constraints.\n\n'
        'This study used a prescribed 1640 MPa apparent-modulus target under the same illustrative elastic model. Eight ordinary-ChatGPT conversations each produced an initial generator and one genuine revision in that same conversation. Four received measured mechanical feedback; four received structural information without measured mechanics. All sixteen scripts were frozen before evaluating six new seeds per script.\n\n'+observedtext+'\n\n'+arm+'\n'+contrast+'\n\n'+hittext+'\n\n'
        f'Of 96 final attempts, 94 generated exact-composition, morphology-feasible specimens and received actual five-checkpoint ANSYS solves with independent readback. Two bounded generator failures were retained. {len(acceptedmesh)} predetermined H2 refinements quantify mesh sensitivity. The study remains a small descriptive pilot: initial scripts differ, account/project context was not isolated, and one control conversation had an extra nonscientific URL turn.\n\n'
        'For the distinct F1 family, the explicit matrix/fiber/void reference and an authenticated LLM-generated structure were solved with void regions omitted from the mesh. H1 apparent moduli were 2230.45 and 2147.60 MPa, respectively; H2 gave 2158.15 and 2093.08 MPa. Approximate circular fiber annotations and illustrative isotropic properties limit interpretation.\n\n'
        'Validated presentation models include an enlarged P3 raised-relief plaque and a separate historical porous through-hole model. Both passed geometric re-import and actual generic slicer checks. They are educational 2D-derived extrusions, not measured 3D reconstructions or calibrated material specimens; no physical print has been completed.\n\n'+preservation+'\n\n'+limitations)
    validation='| Category | Passed checks | Failures / errors / skips |\n|---|---:|---:|\n'
    for label,t in integrity['test_results'].items():validation+=f"| {label} | {t['tests']} | {t['failures']} / {t['errors']} / {t['skipped']} |\n"
    validation+=f"\nActual native execution totals: {perf['actual_source_solves']} source solves + {perf['independent_readback_processes']} independent readbacks = {perf['native_processes']} processes, {perf['actual_native_checkpoints']} solved checkpoints. Supervised native time {perf['total_supervised_native_seconds']:.3f} s ({perf['total_supervised_native_seconds']/60:.3f} min), comprising {perf['source_solve_seconds']:.3f} s source and {perf['readback_seconds']:.3f} s reopening. Peak process-tree RSS {perf['peak_process_tree_RSS_bytes']/2**30:.3f} GiB; minimum observed available RAM {perf['minimum_available_RAM_bytes']/2**30:.3f} GiB. Raw native artifacts occupy {perf['raw_artifact_bytes']/2**30:.3f} GiB under `{BASE}`. One job, two cores, health monitoring and no imposed RSS cap were retained. Process receipts preserve memory/system paging measurements; these are not per-process pagefile measurements. No native execution/acceptance failure occurred.\n\n"
    validation+=f"All {integrity['protected_files_unchanged']:,} originally tracked files and {integrity['previous_package_files_verified']} prior package records authenticate unchanged. Currently available critical native files verified: {integrity['critical_native_hashes_verified']}; {integrity['unavailable_critical_native_file_count']} recorded earlier critical files are unavailable. All sixteen frozen source/prompt records, protocol, seed partitions, original morphology policy and delivered fabrication assets authenticate. Raw native binaries and diagnostic G-code remain outside Git; compact source/result/readback manifests and native CSV curves are included.\n\n"+preservation+'\n\n'
    validation+='The active suite is the explicitly scoped `tests/` suite. An initial root collection invocation produced duplicate archived-module collection errors and is retained in `tests/root_collection_failed.xml`; the final active suite has no excluded active tests. A later native-artifact check found three earlier development folders absent (3 FileNotFoundError failures, 16 current held-out checks passed); that XML remains in `tests/NF01_complete_native_checks.xml`. Final licensed raw checks explicitly cover the current held-out cohort; earlier raw checks are not silently skipped or represented as newly passed. Original earlier checks and their passing XML remain preserved as historical execution evidence. Archived software checks replay immutable historical test groups and are not new independent physical experiments. Fabrication checks re-import the actual meshes and inspect the actual qualified generic toolpaths. Raw UI captures retain their original whitespace and CRLF where applicable; executable generator copies normalize newlines only.\n\n'+continuity+'\n\n'
    validation+='| Required scientific state | State |\n|---|---|\n'+''.join(f'| {k} | {v} |\n' for k,v in states.items())
    validation+='\n`HOLD` marks unsupported unqualified capability/causal claims, not missing numerical measurements. F1 mesh sensitivity passed as a performed diagnostic, with 2.54–3.24% modulus shifts; it is not full convergence. STL PASS states apply to the qualified simplified/framed models under disclosed generic assumptions, not the nonmanifold exact P3 mesh or an actual printer.\n'
    doc('V0_7_4_VALIDATION.md','# Final validation and separate scientific acceptance states\n\n'+validation)
    gallery='# Actual v0.7.4 figures\n\nFixed specimen selection is first registered held-out seed 5000 for every initial/revised module. Native detailed fields use the first registered conversation in each arm, first held-out seed, and final solved checkpoint. Masks are shown for evaluation only and were never model inputs. No physical microscopy calibration is inferred.\n\n'
    for path in sorted((RUN/'figures').glob('*.png')):
        gallery+=f'## {path.stem.replace("_"," ")}\n\n![{path.stem}]({path.as_posix()})\n\n'
    gallery+='F1 actual phases, curves, native stresses and true-scale deformation: see [F1 results](V0_7_4_F1_MECHANICAL_RESULTS.md). Fabrication previews and real generic toolpaths: see [presentation models](V0_7_4_STL_PRESENTATION_PROP.md).'
    doc('V0_7_4_FIGURES.md',gallery)
    answers=[
        f'Authoritative repository `{REPO}`, master, starting HEAD `{p["starting_head"]}`.',
        f'All {integrity["protected_files_unchanged"]:,} initial tracked-file hashes and {integrity["previous_package_files_verified"]} v0.7.3 package records pass. Earlier raw external ANSYS folders are currently unavailable; preservation is HOLD for those files.',
        '1640 MPa, J = 1.640; ±2% band 1607.2–1672.8 MPa; no old difficulty gate reapplied.',
        'Yes. The v0.7.3 morphology-policy file remains byte-identical; six-output cohort qualification was prospectively registered.',
        'P3_B02_EXACT_BOUNDED_MORPHOLOGY_RESEARCHER_ADAPTATION_V074, SHA 190d01bd8af82af6a2682d290b93ef11de8db047218fecd12af1d33e12adef11. Researcher-prepared common template, not a trial.',
        'Yes: six calibration arrays and every generated development/verification/held-out array preserve exactly 20,731 label-5 and 44,805 label-1 pixels.',
        'Starting common generator: zero of six registered calibration failures, exact replay and diversity PASS; not a universal reliability proof.',
        'Eight distinct initial ordinary-ChatGPT conversations, four assigned IF and four NF before responses.',
        'Yes. Eight actual initial response captures with original URLs, raw code and source receipts.',
        'Yes. All eight scientific revisions have the same original conversation ID and chronological source/continuation evidence.',
        'No. No fresh feedback chats or reattached old scripts were used.',
        'Canonical/observed URLs, conversation IDs, before/submission/response/full chronology UI text, exact prompts and SHA256 receipts. Project redirects and NF01 deviation preserved.',
        'Four genuine IF revisions.', 'Four genuine NF revisions.',
        'Same exposed High interface setting; actual backend version unavailable. Account memory/project context not isolated and varied on reopening.',
        'No researcher source repairs. Raw UTF8 captures retained; executable copies only normalize CRLF to LF.',
        'Yes for explicit prompt contents: matched structural schema, IF-only actual measured mechanics/historical curves, no held-out or mask leakage. Shared account context is a limitation.',
        '96 attempted held-out outputs; 94 generated; two NF03 initial bounded-construction failures retained.',
        '94/94 generated arrays, or 94/96 attempted outputs.',
        '94/94 generated arrays; 15/16 scripts qualify six-of-six; all eight revised scripts qualify.',
        'See the per-conversation before/after error table above and `target_property_analysis/SCRIPT_SUMMARIES.csv`.',
        observed[0]+' Descriptive only; not a general capability claim.',
        observed[1]+' Descriptive only; one initial script has two missing outputs.',
        contrast,
        'No generated field violates the frozen constraints; visible size-population/spacing/orientation differences remain. Constraint pass does not establish natural-image equivalence. All observed within-cohort diversity diagnostics pass.',
        meshtext,
        'Unqualified causal/generalization claims, exact backend/context independence, full mesh convergence, physical calibration and RVE validity remain unresolved; NF01 strict total-message equality fails. Earlier raw ANSYS availability is a separate HOLD.',
        'Yes: prepared original C/PEEK microscopy and its evaluator annotation authenticate; source file hashes in f1/source_manifests/.',
        'Yes: native source phases matrix 0, transverse carbon-fiber-like cross-section 1 and void 2 remain distinct; explicit MAT1/MAT2/no-element mapping.',
        'Yes: matrix, nu=0 parallel two-solid and explicit two-strip void controls give 1000, 5500 and 500 MPa with independent readbacks.',
        'Yes, actual F1 reference H1 and H2.',
        'Yes, genuine archived F1_B_02/r0/evaluator seed 0 H1 and H2; not a newly authored baseline.',
        'Five checkpoints each: F1 reference H1 2230.4453 / H2 2158.1510 MPa; generated H1 2147.6014 / H2 2093.0766 MPa. Actual CSVs and figures in f1/.',
        'Unknown microscopy scale, approximate circular fiber annotations, illustrative isotropic cross-sectional properties, shared-node bonds, finite 2D loading and observed 2.54–3.24% mesh shifts; no calibrated anisotropic fiber law or full convergence.',
        'P3 native reference annotation for the relief. Additional porous source: authenticated v0.4.1 Design 009/seed 001/1024; central [384:640,384:640] crop recommended.',
        'P3_REFERENCE_EXACT_RELIEF.stl (retained nonmanifold); P3_REFERENCE_PRINT_READY.stl; POROUS_METAMATERIAL_FULL1024_ORIGINAL.stl; POROUS_METAMATERIAL_ORIGINAL.stl; POROUS_METAMATERIAL_PRINT_READY.stl under presentation_assets/v0.7.4/.',
        'P3 relief 168×168×3.6 mm, 160 mm field, 4 mm border, 2.4 mm base/1.2 mm relief. Porous full/original crop 160×160×5 mm; framed crop 165×165×5 mm. Enlarged presentation dimensions only.',
        'Qualified P3 simplified relief and all porous meshes: yes. Exact P3 mesh is retained but fails its manifold qualification.',
        'Qualified delivered models: yes. Exact P3 has 14 diagonal-only nonmanifold contacts and is not print-qualified.',
        'Qualified models are one connected positive-volume solid with flat base. Generic slicer first-layer connectivity also passed.',
        'Yes: pixel/skeleton width diagnostics and actual toolpaths; proxies are not exact global neck guarantees. Full1024 porous source has sub-nozzle features; framed central crop is recommended.',
        'P3 display-only 3×3 opening/closing plus documented diagonal-contact fills; porous crop adds only a 2.5 mm external frame and no internal pixel edits.',
        'P3 1383 changed pixels = 880 removed + 503 added, phase-5 area 20731→20354; original source unchanged. Porous frame is 1625 mm² outside the field, encloses 16 edge pockets while preserving all 19 internal pores.',
        'Yes: independent mesh re-import, topology, sections, projected source geometry, volume and bounds.',
        'Yes: installed Dremel DigiLab CuraEngine actual generic preview; qualified attempts 003 P3 and 004 porous. Earlier failed/off-bed attempts preserved. Actual printer unknown, no physical print.',
        'Actual STL and toolpath PNGs under presentation_assets/v0.7.4/; P3_VS_POROUS_PRESENTATION_MODELS.png compares both.',
        'PRINTING_INSTRUCTIONS.md and POROUS_METAMATERIAL_PRINTING_INSTRUCTIONS.md beside the STL files.',
        'Yes. P3 is an enlarged 2D presentation relief; porous model is a straight through-hole extrusion; neither is an authentic 3D reconstruction or calibrated specimen.',
        f"{perf['actual_source_solves']} actual new source solves, plus {perf['independent_readback_processes']} independent reopening processes ({perf['native_processes']} native processes total).",
        f"{perf['total_supervised_native_seconds']:.3f} supervised native seconds total; source {perf['source_solve_seconds']:.3f} s, readback {perf['readback_seconds']:.3f} s. Wall-clock workflow time is different.",
        f"Peak native process-tree RSS {perf['peak_process_tree_RSS_bytes']/2**30:.3f} GiB; minimum observed available RAM {perf['minimum_available_RAM_bytes']/2**30:.3f} GiB; sampled, not an exact instantaneous maximum.",
        str(integrity['test_results'])+'; detailed validation and retained failed initial root-collection invocation are documented.',
        f"All {integrity['test_results']['licensed_current_heldout_raw']['tests']} final current held-out raw-native checks passed, including field, energy, reactions, constraints, connectivity and independent reopening; {integrity['critical_native_hashes_verified']} currently available critical hashes authenticate. Earlier raw-file revalidation is unavailable, and the discovered missing-file failures remain recorded.",
        'Versioned run evidence in experiments/pipeline_v0.7.4/run_001/, required reports in docs/pipeline_v0.7.4/, presentation assets in presentation_assets/v0.7.4/, additive scripts and focused tests. See final package manifest for exact files/hashes.',
        'Full hashes and messages in COMMITS.md; final sealing commit reported in delivery because a commit cannot contain its own hash.',
        'Final clean status is verified after the sealing commit and reported in delivery; the package records the preceding staged delivery state.',
        'Nothing was pushed; all commits remain local.',
        'The registered actual small pilot, F1 native benchmark and validated generic presentation models are complete; scientific states are separated in FINAL_SCIENTIFIC_STATUS.json. No unqualified causal advantage, physical calibration or universal generation claim.',
        'Actual reference/generated geometry, genuine same-chat protocol, conditional target-error tables with failures, native curves/H2 sensitivity, F1 three-phase benchmark, and validated presentation models with the stated limitations.',
        'A separately registered replication with more independent conversations, isolated/common context, equal total messages, richer reference-fidelity checks and larger paired H2 coverage; do not start another revision round in this completed study.',
    ]
    assert len(answers)==60
    questions=[]
    request=(RUN/'protocol/USER_REQUEST.txt').read_text(encoding='utf-8-sig')
    section=request.split('# 63. FINAL HANDOFF QUESTIONS',1)[1].split('# 64.',1)[0]
    import re
    questions=re.findall(r'^\d+\. (.+)$',section,re.M)
    assert len(questions)==60
    handoff='# v0.7.4 completed registered study\n\nThe actual eight-conversation initial/revision experiment, held-out evaluations, F1 mechanics and both presentation-model deliverables are complete. Descriptive outcomes and protocol limitations are reported without a generalized feedback claim. No further model call, old compression campaign or 3D mechanical solve is authorized by this closeout. Nothing was pushed.\n\n'+table+'\n'+arm+'\n'+contrast+'\n\n'
    handoff+='## Requested handoff answers\n\n'+''.join(f'{i}. **{q}** {answer}\n\n' for i,(q,answer) in enumerate(zip(questions,answers),1))
    handoff+='See [P3 results](V0_7_4_P3_INVERSE_DESIGN_RESULTS.md), [F1 results](V0_7_4_F1_MECHANICAL_RESULTS.md), [presentation models](V0_7_4_STL_PRESENTATION_PROP.md), [validation](V0_7_4_VALIDATION.md), [actual figures](V0_7_4_FIGURES.md), [Dr. Wang summary](DR_WANG_SUMMARY.md) and [commits](COMMITS.md).'
    doc('V0_7_4_HANDOFF.md',handoff)
    commits=subprocess.check_output(['git','log',p['starting_head']+'..HEAD','--reverse','--format=%H%x09%s'],cwd=REPO,text=True).strip()
    doc('COMMITS.md','# v0.7.4 local commits\n\nStarting HEAD `'+p['starting_head']+'`. No push or history rewrite. Final sealing commit follows these documents; its hash is reported in delivery.\n\n'+'\n'.join('- `'+line.split('\t')[0]+'` — '+line.split('\t',1)[1] for line in commits.splitlines()))
    print('REPORTS AND ALL60 ANSWERS COMPLETE',flush=True)


def freeze():
    destination=RUN/'summary/FINAL_PACKAGE_HASHES.json'
    assert not destination.exists()
    roots=[RUN,DOC,ASSETS]
    files={str(p.relative_to(REPO)).replace('\\','/'):sha(p) for root in roots for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    for p in sorted((REPO/'scripts').glob('v074*.py')):files[str(p.relative_to(REPO)).replace('\\','/')]=sha(p)
    for p in sorted((REPO/'tests').glob('test_v074*.py')):files[str(p.relative_to(REPO)).replace('\\','/')]=sha(p)
    for name in ['metamaterial_eval/simulation/three_phase_elastic.py','validation/ansys_v074_integration.py','validation/stl_v074_integration.py',
            'scripts/.gitattributes','tests/.gitattributes','validation/.gitattributes','metamaterial_eval/simulation/.gitattributes']:
        files[name]=sha(REPO/name)
    write(destination,{'frozen_utc':now(),'files':files,'manifest_excludes_itself':True,
        'no_further_model_calls_or_scientific_revisions':True,'pushed':False})
    print('FINAL PACKAGE FROZEN',len(files),'files',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['audit','reports','freeze']);a=p.parse_args()
    {'audit':audit,'reports':reports,'freeze':freeze}[a.action]()
