"""Evidence-grounded checkpoint at an actual display/capture blocker, never a final optimization claim."""
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v072_experiment import RUN,DOC,BASE,TRIALS,now
from scripts.v072_analysis import csv_table


def xml_counts(paths):
    totals={k:0 for k in ['tests','failures','errors','skipped']}
    for path in paths:
        root=ET.parse(path).getroot();suites=[root] if root.tag=='testsuite' else root.findall('.//testsuite')
        for suite in suites:
            for key in totals:totals[key]+=int(suite.get(key,0))
    return totals


def checkpoint():
    assert not (RUN/'frozen_scripts/ALL_OPTIMIZATION_SCRIPTS_FROZEN.json').exists()
    assert not (RUN/'heldout_structures').exists()
    captures=[trial for trial in TRIALS if (RUN/'llm_trials'/trial/'RECEIPT.json').exists()]
    assert len(captures)==3
    submitted=[read(RUN/'llm_trials'/trial/'SUBMISSION.json') for trial in TRIALS]
    assert len({r['chat_url'] for r in submitted})==4
    tests={name:xml_counts(paths) for name,paths in {
        'active':[RUN/'verification/active_tests.xml'],
        'archived_replays':list((RUN/'verification/archive_replay').glob('*.xml')),
        'historical_licensed_artifacts':[RUN/'verification/historical_licensed_checks.xml'],
        'new_v072_baseline_licensed_artifacts':[RUN/'verification/baseline_licensed_checks.xml']}.items()}
    assert tests['active']['tests']==909 and tests['archived_replays']['tests']==475
    assert tests['historical_licensed_artifacts']['tests']==49 and tests['new_v072_baseline_licensed_artifacts']['tests']==9
    assert all(t['failures']==t['errors']==t['skipped']==0 for t in tests.values())
    native_verified=0
    for path in (RUN/'native_result_manifests').glob('*/NATIVE_ARTIFACTS.json'):
        for item in read(path).values():
            assert sha(Path(item['path']))==item['sha256'];native_verified+=1
    assert native_verified==42
    protected=read(RUN/'audit/PROTECTED_AFTER_INTERIM.json');assert protected['passed'] and protected['tracked_files']==16596
    p=read(RUN/'protocol/PROTOCOL.json');frozen=read(RUN/'starting_generator/COMMON_STARTING_POINT_FROZEN.json')
    assert sha(RUN/'starting_generator/generator.py')==frozen['common_copy_sha256']
    receipts=[read(path) for path in BASE.glob('*/process_receipt.json')]
    assert len(receipts)==12
    samples=[s for r in receipts for s in r.get('resource_samples',[])]
    performance={'native_processes':len(receipts),'actual_source_solves':6,'independent_readback_processes':6,
        'accepted_source_models':6,'actual_accepted_native_checkpoints':30,
        'total_supervised_native_seconds':sum(r['runtime_seconds'] for r in receipts),
        'peak_process_tree_RSS_bytes':max(r['peak_tree_rss_bytes'] for r in receipts),
        'minimum_available_RAM_bytes':min(s['available_RAM_bytes'] for s in samples),
        'maximum_observed_commit_fraction':max([s['commit_fraction'] for s in samples if s.get('commit_fraction') is not None],default=None),
        'maximum_observed_system_page_reads_per_second':max([s['page_reads_per_second'] for s in samples if s.get('page_reads_per_second') is not None],default=None),
        'raw_artifact_bytes':sum(path.stat().st_size for path in BASE.rglob('*') if path.is_file()),
        'native_base':str(BASE),'native_concurrency':1,'cores':2,'RSS_cap':None,
        'page_reads_note':'System hard-fault disk-read proxy, not pagefile-only or per-solver paging'}
    write(RUN/'performance/INTERIM_SUMMARY.json',performance)
    summary=read(RUN/'baseline_mechanical_results/SUMMARY.json')
    inventory=[]
    for trial in TRIALS:
        d=RUN/'llm_trials'/trial;r=read(d/'RECEIPT.json') if (d/'RECEIPT.json').exists() else None
        submission=read(d/'SUBMISSION.json')
        inventory.append({'trial_id':trial,'condition':'MF' if '_MF_' in trial else 'NF',**submission,
            'response_capture_status':r['status'] if r else 'SUBMITTED_CAPTURE_BLOCKED_BY_DISPLAY',
            'response_sha256':r['response_sha256'] if r else None,'source_sha256':r['code_sha256'] if r else None,
            'static_audit_passed':r['audit']['passed'] if r else None,'execution_runtime_per_seed':None,
            'heldout_realizations_attempted':0,'repair_calls':0})
    write(RUN/'summary/INTERIM_GENUINE_TRIAL_INVENTORY.json',inventory);csv_table(RUN/'summary/INTERIM_GENUINE_TRIAL_INVENTORY.csv',inventory)
    status={k:'PASS_VERIFIED' for k in ['STARTING_GENERATOR_AUTHENTICATED','COMMON_STARTING_POINT_FROZEN','COMPOSITION_CONSTRAINT_REGISTERED',
        'MORPHOLOGY_CONSTRAINTS_REGISTERED','BASELINE_STRUCTURAL_FEASIBILITY','BASELINE_MECHANICAL_VARIABILITY_MEASURED',
        'BASELINE_NATIVE_STRESS_STRAIN_AVAILABLE','MF_NF_PROMPTS_MATCHED','MECHANICAL_FEEDBACK_PACKET_AUTHENTICATED','EQUAL_REVISION_BUDGET_VERIFIED']}
    status.update(GENUINE_MF_RESPONSES_CAPTURED='ONE_OF_TWO_CAPTURED__BOTH_SUBMITTED__SECOND_SOURCE_CAPTURE_BLOCKED',
        GENUINE_NF_RESPONSES_CAPTURED='TWO_OF_TWO_CAPTURED_UNEDITED',ALL_OPTIMIZATION_SCRIPTS_FROZEN='NOT_YET__FOURTH_SOURCE_REQUIRED',
        HELDOUT_SEED_ISOLATION_VERIFIED='FROZEN_DISJOINT_AND_UNOPENED__NO_HELDOUT_GENERATION',
        MF_STRUCTURAL_FEASIBILITY='NOT_EVALUATED',NF_STRUCTURAL_FEASIBILITY='NOT_EVALUATED',
        FIXED_COMPOSITION_PRESERVED='DEVELOPMENT6_OF6_WITHIN64_PIXELS__FINAL_NOT_EVALUATED__NOT_EXACT_COUNT',
        DISPERSED_MORPHOLOGY_PRESERVED='DEVELOPMENT6_OF6__FINAL_NOT_EVALUATED',
        STOCHASTIC_DIVERSITY_PRESERVED='DEVELOPMENT6_UNIQUE_AND_DIVERSE__FINAL_NOT_EVALUATED',
        HELDOUT_MECHANICAL_EVALUATION='NOT_STARTED',BASELINE_RELATIVE_IMPROVEMENT='NOT_TESTED',FEEDBACK_VERSUS_CONTROL_COMPARISON='NOT_TESTED',
        SCREENING_MODULUS_VERIFIED='FINAL_POINT_SECANT_VERIFIED_AGAINST_SIX_FULL_NATIVE_CURVES__NO_ONE_POINT_ONLY_ROUTE',
        NATIVE_FULL_CURVE_CONFIRMATION='SIX_DEVELOPMENT_CURVES_QUALIFIED__FINAL_CONFIRMATION_PENDING',H2_MESH_CONFIRMATION='NOT_RUN',
        OPTIMIZATION_EFFECT_NUMERICALLY_RESOLVED='NOT_TESTED',COMPOSITION_CONFOUNDING_ASSESSED='DEVELOPMENT_COUNTS_REPORTED__FINAL_NOT_TESTED__NO_GEOMETRY_ONLY_CLAIM',
        LLM_MECHANICAL_FEEDBACK_EXECUTED='TWO_GENUINE_MF_SUBMISSIONS__ONE_RESPONSE_SOURCE_CAPTURED__FINAL_EVALUATION_PENDING',
        PRELIMINARY_LLM_MECHANICAL_OPTIMIZATION_SUPPORTED='NOT_TESTED',PRELIMINARY_FEEDBACK_ADVANTAGE_SUPPORTED='NOT_TESTED',
        PHYSICAL_MATERIAL_CALIBRATION='NOT_CALIBRATED',REPRESENTATIVE_VOLUME_QUALIFICATION='NOT_QUALIFIED',
        CROSS_FAMILY_MECHANICAL_OPTIMIZATION='NOT_RUN',PAPER_READINESS='BASELINE_AND_PARTIAL_RESPONSE_EVIDENCE_ONLY__OPTIMIZATION_EXPERIMENT_INCOMPLETE')
    overall='BASELINE_MECHANICS_COMPLETE__THREE_AUTHENTIC_REVISIONS_CAPTURED__FOURTH_SUBMITTED_CAPTURE_BLOCKED__HELDOUT_NOT_STARTED'
    write(RUN/'summary/INTERIM_SCIENTIFIC_STATUS.json',{'recorded_utc':now(),'overall':overall,'independent_statuses':status})
    write(RUN/'verification/INTERIM_INTEGRITY.json',{'checked_utc':now(),'test_results':tests,'native_critical_artifact_hashes_verified':42,
        'protected_files_unchanged':16596,'actual_source_solves':6,'actual_native_readbacks':6,'actual_model_submissions':4,
        'captured_exact_returned_modules':3,'heldout_arrays_generated':0,'H2_jobs':0,'optimization_outcomes_available':False,
        'generators_manually_repaired':False,'push':False})
    fourth=read(RUN/'llm_trials/P3_OPT_MF_02/SUBMISSION.json')['chat_url']
    gate=f'''# Existing-response capture gate — do not resubmit

The six development ANSYS curves are qualified. All four registered prompts were genuinely submitted in distinct ordinary ChatGPT chats at the same exposed High setting. Three complete returned modules are preserved and audited. The existing fourth chat is [{fourth}]({fourth}).

Windows graphics capture failed twice with `IGraphicsCaptureItemInterop.CreateForMonitor ... 0x80070057`. Read-only accessibility remained available, but reliable source-copy interaction could not continue. No fourth module is fabricated; its capture remains pending. Restoring the display/session and leaving Chrome visible is the only user action currently needed. No new permission or extra model attempt is required.

After display recovery, capture the **existing completed P3_OPT_MF_02 response** via its Copy code control, paste into a separate empty Notepad tab, read complete accessibility document_text, and save the exact unedited text as `llm_trials/P3_OPT_MF_02/response.txt`. Preserve the UI capture/method metadata. If the final response includes narrative, preserve it too. Do not click regenerate, send a repair prompt or submit these packets again.

Then run `python -m scripts.v072_trials ingest P3_OPT_MF_02`, review the original source, and `python -m scripts.v072_trials freeze`. Only after that collective freeze, use `python -m scripts.v072_trials heldout TRIAL` for BASE and each of the four registered trial IDs. The workers retain failures and do not replace seeds. Run `python -m scripts.v072_campaign 1` and `python -m scripts.v072_campaign 2` sequentially for the feasible registered cases. Each geometry receives five actual checkpoints plus native reopening, not a fabricated curve from one point. Finish the registered analysis/figures and actual-result report, verify evidence and commit. Stop after this single-generation experiment.

Do not alter the frozen objective, ±64-pixel composition tolerance, morphology envelope, partitions, H2 subset, prompts or returned code. Independent conversations are the experimental units; stochastic realizations are nested. The final held-out seed list is evaluator-only. It has not been used or sent to the model. There are no held-out arrays, gains or H2 outcomes at this checkpoint.
'''
    (DOC/'BROWSER_CAPTURE_GATE.md').write_text(gate,encoding='utf-8',newline='\n')
    (DOC/'V0_7_2_LLM_REVISION_EXPERIMENT.md').write_text('# Genuine revision experiment — capture incomplete\n\nFour genuine independent ordinary-ChatGPT submissions, two MF and two NF, in the preregistered MF01/NF01/NF02/MF02 order. All used the same visible High setting; exact backend/version, tokens and cost are unavailable. Fresh chats were created outside the project; account memory, personalization and hidden routing are not independently controlled. No settings were changed.\n\nMF prompt SHA-256 `'+read(RUN/'feedback_packets/PROMPTS_FROZEN.json')['prompt_hashes']['P3_OPT_MF_01']+'`; NF prompt SHA-256 `'+read(RUN/'feedback_packets/PROMPTS_FROZEN.json')['prompt_hashes']['P3_OPT_NF_01']+'`. NF is byte-for-byte the common prefix of MF; the only substantive addition is the authentic development mechanical packet. Both contain identical source code and baseline structural summaries, without hidden morphology error scores or held-out seeds.\n\n'+
        '| Trial | Complete source captured | Source SHA-256 |\n|---|---|---|\n'+''.join(f"| {r['trial_id']} | {'Yes, unedited' if r['source_sha256'] else 'No, display capture blocked'} | {r['source_sha256'] or 'Unavailable'} |\n" for r in inventory)+
        '\nAll three captured modules passed static screening and full source review; none has been executed on final seeds. MF01 contains a bounded 20-candidate geometry-only selection; the two NF modules use constructive geometry. These are source observations, not measured runtime or optimization results. Preferred <=250-line response length was not a hard acceptance rule. No researcher repair or extra call occurred. See BROWSER_CAPTURE_GATE.md for recovery of the already submitted fourth response.\n',encoding='utf-8',newline='\n')
    validation='# v0.7.2 interim validation\n\n| Category | Passed | Scope |\n|---|---:|---|\n'+''.join(f"| {name} | {r['tests']} | Zero failures/errors/skips |\n" for name,r in tests.items())
    validation+='\nArchived counts are 475 replay checks across nine historical groups, not additional unique tests. Historical licensed checks combine 26 v0.7.1 and 23 older evidence checks; they launch no solver. The nine new licensed checks qualify six actual v0.7.2 baseline source models and their independent readbacks. The unexecuted fourth-source/final-H2 checks were deselected, not claimed as passes. All 42 critical native artifact hashes and all 16,596 pre-existing tracked files authenticate. No final held-out experiment was run.\n\n'
    validation+=f"Twelve new native processes: six solves and six readbacks, 30 accepted checkpoints. Native supervised wall-time sum {performance['total_supervised_native_seconds']:.3f} s; peak tree RSS {performance['peak_process_tree_RSS_bytes']/2**30:.3f} GiB; minimum available RAM {performance['minimum_available_RAM_bytes']/2**30:.3f} GiB; raw storage {performance['raw_artifact_bytes']/2**30:.3f} GiB. Native root `{BASE}`. The unchanged launcher retains its v071 job-name prefix; distinct v072 directories, inputs, receipts, timestamps and native hashes identify these new runs. No RST copies were made for reopening.\n\n"
    validation+='| Independent scientific status | Outcome |\n|---|---|\n'+''.join(f'| {key} | {value} |\n' for key,value in status.items())
    (DOC/'V0_7_2_VALIDATION.md').write_text(validation,encoding='utf-8',newline='\n')
    (DOC/'V0_7_2_HANDOFF.md').write_text(f'''# v0.7.2 interim research handoff — experiment incomplete

Repository `{REPO}`, branch master, starting HEAD `{p['starting_head']}`. All 16,596 previously tracked files authenticate unchanged, including v0.7.0 originals, scripts and held-out arrays, v0.7.1 mechanics and archived porous work. No push, F1 mechanics, old contact solve or multigeneration optimization occurred.

The common starting point is **unchanged captured P3_B_02/r0**, SHA-256 `{sha(RUN/'starting_generator/generator.py')}`. Its saved seed0 output replayed exactly. Six new development seeds1000–1005 passed registered structural feasibility and deterministic replay; all six arrays and arrangement signatures are unique, median pairwise categorical Hamming0.4191. Exact target reinforcement count **20,731/65,536**, fraction0.3163299560546875. The unchanged generator does not enforce exact counts; its development range20717–20784 supports a prospectively frozen tolerance **±64 pixels**, fraction±0.0009765625. No geometry is corrected after generation. Final revisions use identical acceptance; residual fraction confounding forbids a strong geometry-only attribution without separate confirmation.

The registered objective is maximize **J=apparent vertical elastic modulus/1000MPa**. Four/eight-connected reinforcement spanning is prohibited. Largest reinforcement component≤0.15 under both connectivities; four-connected matrix LCC≥0.95 and spans both axes. Complete/all/border-censored region counts40–75/50–125/5–50, complete mean diameter12–20px, mean aspect1.2–3.0 and singleton reinforcement-area fraction≤0.001. Final diversity requires ten unique arrays, median pairwise Hamming≥0.1 and at least five unique rigid-invariant area/centroid-distance signatures, a diagnostic with boundary-clipping limitations. These constraints froze before new mechanics or model calls. Both phases remain solids and interfaces share nodes.

Six actual licensed ANSYS baseline models passed the unchanged v0.7.1 qualifier and independent RST reopening. Five native checkpoints0.1–0.5% per specimen yielded mean apparent modulus **{summary['mean_modulus_MPa']:.6f}MPa**, sample SD**{summary['sample_standard_deviation_MPa']:.6f}MPa**, range{summary['minimum_modulus_MPa']:.6f}–{summary['maximum_modulus_MPa']:.6f}MPa and normalized mean**{summary['mean_normalized_objective']:.6f}**. Actual curves, reactions, displacement, strain energy and phase fields are retained. Final-point secants agree with fitted slopes; no one-point-only route was used. Materials remain illustrative E1000/10000MPa, nu0.30; 1mm dimensions/thickness are computational conventions, not microscopy calibration. P3 chemistry, augmented provenance, crop selection, ideal bonding, pixel-corner load transfer, finite-domain/plane-stress and RVE limitations persist.

The exact four revision prompts were submitted in independent ordinary ChatGPT chats: two MF, two NF, one opportunity each, visible High setting throughout. NF receives identical starting code, objective, constraints, model assumptions and baseline structure table; only MF receives the authentic development mechanical curves, moduli and variability. No hidden morphology scores or final seed values were sent. Exact model backend, token/cost and routing are unavailable; personalization/memory remain uncontrolled.

**Three genuine unedited returned modules are captured and audited. The fourth trial, P3_OPT_MF_02, was already submitted but its source could not be copied after Windows graphics capture failed twice with0x80070057.** All submission receipts and prompt hashes are preserved. No additional attempts or researcher repairs occurred. See BROWSER_CAPTURE_GATE.md: restore display access and capture the existing response, without resubmitting. The complete frozen-script gate is deliberately still closed. Final attempted structures, feasible counts, runtime/diversity, BASE/MF/NF held-out means, gains, feedback advantage, phase-stress trade-offs and H2 effects are **not yet available**, not zero and not successful optimization evidence.

After source capture and collective freeze, the prospectively held-out ten-seed partition must be evaluated for BASE and all four revisions, then the same first-three-seed H2 subset for all scripts. No held-out arrays have been generated. All feasible cases use actual five-point curves and readback; failures remain in denominators with no replacement seeds. Compare script-level paired gains, MF versus NF, phase-count shifts and observed H1/H2 differences without pooled-seed significance or causal overstatement. Complete the existing registered experiment before recommending an extension.

Validation passed909 active tests,475 archived replay checks,49 historical licensed-artifact checks and9 new baseline licensed-artifact checks. Twelve actual native processes consumed{performance['total_supervised_native_seconds']:.3f}s supervised wall time; peak tree RSS{performance['peak_process_tree_RSS_bytes']/2**30:.3f}GiB; raw artifacts{performance['raw_artifact_bytes']/2**30:.3f}GiB under `{BASE}`. Captured browser UI metadata is retained outside Git where it contains unrelated chrome; tracked excerpts preserve only response/code controls. Exact native source hashes and compact receipts are in the experiment.

Scientific status: **{overall}**. This checkpoint completes baseline measurement and four genuine submissions, **not the controlled optimization experiment**. Supported statements to Dr.Wang are baseline variability, authentic feedback preparation/submission and the current capture limitation. No held-out improvement, feedback benefit, physical calibration, RVE or cross-family optimization claim is supported. Do not start a new generation or change constraints while awaiting capture.
''',encoding='utf-8',newline='\n')
    (DOC/'DR_WANG_SUMMARY_INTERIM.md').write_text(f'''# Research update for Dr. Wang — baseline complete, optimization evaluation pending

Following the real-microscopy P3/F1 LLM-generation pilot and qualified P3 mechanical benchmark, we established a controlled single-generation mechanical-feedback experiment. An unchanged captured B02 generator supplied six new, structurally valid development specimens. Actual licensed ANSYS curves through0.5% compression, with independent native-result reopening, gave mean apparent vertical modulus {summary['mean_modulus_MPa']:.2f}MPa and sample SD {summary['sample_standard_deviation_MPa']:.2f}MPa under illustrative E1000/10000MPa constituent assumptions.

We froze a narrow ±64-pixel reinforcement-count tolerance and dispersed-inclusion morphology limits before mechanics and model revision. Two genuine ordinary-ChatGPT mechanical-feedback prompts received these actual measurements; two matched no-feedback prompts received identical code, objective, constraints and structural summaries. All four independent prompts were submitted with one revision opportunity each. Three returned modules are captured unedited; a Windows display-capture failure currently prevents copying the already-submitted fourth response.

Held-out generation and mechanics have deliberately not begun before all four sources are frozen. Therefore we cannot yet say whether any revision improves stiffness or whether measured feedback outperforms the matched control. The next step is to recover the existing fourth response and complete the registered held-out and refined-mesh evaluation. Material calibration, physical scale and representative-volume qualification remain absent.
''',encoding='utf-8',newline='\n')
    import re
    for filename in ['V0_7_2_HANDOFF.md','DR_WANG_SUMMARY_INTERIM.md','V0_7_2_VALIDATION.md']:
        path=DOC/filename;text=path.read_text(encoding='utf-8')
        text=re.sub(r'(?<=\d)(MPa|GiB|mm|px)\b',r' \1',text)
        for old,new in [('seeds1000','seeds 1000'),('fraction0.316','fraction 0.316'),('Hamming0.4191','Hamming 0.4191'),
            ('range20717','range 20717'),('counts40','counts 40'),('diameter12','diameter 12'),('aspect1.2','aspect 1.2'),
            ('checkpoints0.1','checkpoints 0.1'),('sample SD**','sample SD **'),('twice with0x','twice with 0x'),
            ('passed909','passed 909'),('tests,475','tests, 475'),('checks,49','checks, 49'),('and9','and 9'),
            ('consumed165','consumed 165'),('RSS0.973','RSS 0.973'),('artifacts2.040','artifacts 2.040'),
            ('through0.5%','through 0.5%'),('nu0.30','nu = 0.30'),('E1000/10000','E = 1000/10000')]:text=text.replace(old,new)
        path.write_text(text,encoding='utf-8',newline='\n')
    commits=subprocess.check_output(['git','log','--reverse','--format=%H %s',p['starting_head']+'..HEAD'],cwd=REPO,text=True)
    (DOC/'COMMITS_INTERIM.md').write_text('# v0.7.2 commits before the checkpoint documentation commit\n\n'+''.join('- '+line+'\n' for line in commits.splitlines())+'\nThe checkpoint documentation commit is identified with full hash/message in the delivered response. Nothing was pushed.\n',encoding='utf-8',newline='\n')
    print(overall,'baseline E',summary['mean_modulus_MPa'],'native hashes verified',native_verified,'performance',performance,flush=True)


if __name__=='__main__':checkpoint()
