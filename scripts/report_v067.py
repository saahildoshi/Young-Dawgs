"""Evidence-driven v0.6.7 HOLD report; no inferred full-model extension."""
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v067_fixture import BASE, RUN, REPO


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def readable(text):
    words='all|with|through|at|of|from|to|under|in|only|one|two|three|four|five|eight|across|than|before|after|remains|time|parameter|LS|SS|type|section|nodes|skins|faces|elements|NEQIT|FKN|KEYOPT|Nodal|Projection|v241|licensed|native|actual|original|registered|limit|criterion|residual|upperRF|lowerRF|UY|EYY|EXX|SEQV|SYY'
    text=re.sub(r'\b('+words+r')(?=\d)',r'\1 ',text)
    text=re.sub(r'\b(is|are|preserves|and|contains|penetration)(?=[\d\[])',r'\1 ',text)
    text=re.sub(r'(?<=\d)(mm|MPa|GiB|N|bytes|nodes|TRI6|groups|iterations|evaluations)\b',r' \1',text)
    text=re.sub(r'[,;](?=\S)',lambda m:m[0]+' ',text)
    return text
def write(name, text):
    lines=[line if re.match(r'^\|[0-9a-f]{40}\|',line) else readable(line) for line in text.splitlines()]
    (RUN/'summary'/name).write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8',newline='\n')
def counts(path):
    suites=list(ET.parse(path).getroot().iter('testsuite'))
    q={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','errors','failures','skipped']}
    return {**q,'passed':q['tests']-q['errors']-q['failures']-q['skipped']}
def git(*args):return subprocess.check_output(['git',*args],cwd=REPO,text=True,encoding='utf-8').strip()


def performance():
    jobs=[]
    for path in sorted(BASE.glob('*/execution_receipt.json')):
        r=read(path);p=r['process']; samples=p['resource_samples']
        jobs.append({'job':path.parent.name,'kind':r['execution_kind'],'returncode':p['returncode'],'status':r['status'],
                     'runtime_seconds':p['runtime_seconds'],'peak_tree_RSS_bytes':p['peak_tree_rss_bytes'],
                     'native_restart':'ANTYPE,STATIC,REST,' in (path.parent/'input.inp').read_text(encoding='utf-8'),
                     'receipt_sha256':file_hash(path),'minimum_available_RAM_bytes':min((s['available_RAM_bytes'] for s in samples),default=None),
                     'max_system_page_reads_per_second':max((s['page_reads_per_second'] for s in samples if s['page_reads_per_second'] is not None),default=0),
                     'severe_paging_samples':sum(s['page_reads_per_second'] is not None and s['page_reads_per_second']>=10000 for s in samples)})
    q={'native_processes':len(jobs),'solver_processes':sum(j['kind']=='LICENSED_PROGRESSIVE_SOLVE' for j in jobs),
       'native_restart_processes':sum(j['native_restart'] for j in jobs),'new_full_solver_attempts':0,
       'sum_native_process_wall_seconds':sum(j['runtime_seconds'] for j in jobs),'peak_tree_RSS_bytes':max(j['peak_tree_RSS_bytes'] for j in jobs),
       'raw_v067_disk_bytes':sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()),
       'severe_paging_samples':sum(j['severe_paging_samples'] for j in jobs),'max_system_page_reads_per_second':max(j['max_system_page_reads_per_second'] for j in jobs),
       'paging_scope':'System hard-fault read proxy, not pagefile-only traffic; sampled observations do not prove absence between samples.',
       'RSS_cap':None,'jobs':jobs}
    write_json(RUN/'performance/PERFORMANCE.json',q);return q


def main():
    audit=read(RUN/'audit/INITIAL_AUTHENTICATION.json'); perf=performance()
    tests={'active':counts(RUN/'verification/active.xml'),'archive_passed':sum(counts(p)['passed'] for p in (RUN/'verification/archive_replay').glob('*.xml')),
           'archive_groups':len(list((RUN/'verification/archive_replay').glob('*.xml'))),'licensed_evidence':counts(RUN/'verification/licensed.xml'),
           'licensed_scope':'Existing v066 actual-artifact checks plus v067 native evidence checks; checks are not new solver invocations.'}
    assert tests['active']['passed']==794 and tests['archive_passed']==475
    assert not tests['licensed_evidence']['failures'] and not tests['licensed_evidence']['errors']
    old=read(REPO/'experiments/pipeline_v0.6.6/run_001/summary/V0_6_6_VALIDATION.json')
    baseline=read(RUN/'local_fixture/local_baseline_003_qualification.json')
    projection=read(RUN/'local_fixture/local_projection3_001_qualification.json')
    recovery=read(RUN/'local_fixture/local_fkn1_neqit64_001_qualification.json')
    local=recovery['states'][-1]; parent=baseline['states'][14]
    protected=['experiments/pipeline_v0.5','experiments/pipeline_v0.6','experiments/pipeline_v0.6.1','experiments/pipeline_v0.6.2','experiments/pipeline_v0.6.3',
               'experiments/pipeline_v0.6.4','experiments/pipeline_v0.6.5','experiments/pipeline_v0.6.6','metamaterial_eval/generators','validation/evaluators','data']
    changes=git('diff','--name-only',audit['base_commit'],'--',*protected)
    assert not changes
    write_json(RUN/'verification/HISTORICAL_PRESERVATION.json',{'base_commit':audit['base_commit'],'protected_paths':protected,'git_diff_name_only':changes,'passed':True})
    native_parent=read(RUN/'restart_validation/PARENT_NATIVE_READBACK.json');assert native_parent['status']=='PASS'
    cases=['local_baseline_003','local_fkn10_002','local_fkn1_001','local_projection3_001','local_fkn1_neqit64_001']
    cuts=sum(len(read(BASE/j/'nonlinear_telemetry.json')['cutback_events']) for j in cases)
    raw_contact=[r for p in BASE.glob('*/contact_telemetry.json') for r in read(p)['records'] if r['pair']<0]
    raw_pen=max([0.]+[r['penetration_or_gap_mm'] for r in raw_contact])
    raw_chatter=max([0.]+[r['chattering_level'] for r in raw_contact])
    raw_active=max([0]+[r['active_elements'] for r in raw_contact])
    stress=np.loadtxt(BASE/'local_fkn1_neqit64_001_post001/state001_stress.csv',delimiter=',',skiprows=1)
    local_strain=np.max(abs(stress[:,3:5]),axis=0).tolist()
    qstates={
        'A_SOURCE_GEOMETRY_AUTHENTICATED':'PASS', 'B_FINE_MESH_AUTHENTICATED':'PASS', 'C_LAST_VALID_RESTART_AUTHENTICATED':'PASS_FRESH_POST1_AND_BYTE_HASHES',
        'D_CONTACT_ONSET_REGION_LOCALIZED':'PASS_CORRELATED_NATIVE_RESIDUAL_AND_GEOMETRY_EVIDENCE; FAILED_TRIAL_ELEMENT_TRANSITIONS_UNAVAILABLE',
        'E_LOCAL_FIXTURE_GEOMETRY_FAITHFUL':'EXACT_SOURCE_SUBSET; LATE_PARENT_FIELD_MATCH; EARLY_STRESS_AND_NANOGAP_CONTEXT_MISMATCH',
        'F_LOCAL_FAILURE_REPRODUCED':'QUALITATIVE_CONTACT_CYCLING_AND_NONCONVERGENCE; EXACT_FULL_THRESHOLD_NOT_REPRODUCED',
        'G_CONTACT_CORRECTION_VALIDATED':'HOLD_NONE_PASSED_COMPLETE_REQUIRED_LOCAL_PATH',
        'H_RESTART_COMPATIBILITY_VERIFIED':'PARTIAL_NATIVE_NEQIT_CONTINUE_WORKED; FKN_CHANGE_FROM_FULL_PARENT_NOT_TESTED',
        'I_FULL_FINE_MESH_RECOVERY':'NOT_ATTEMPTED_LOCAL_GATE_FAILED',
        **{f'{letter}_FULL_MODEL_{label}':'NOT_REACHED' for letter,label in zip('JKLMNO',['ONE_PERCENT','FIVE_PERCENT','TEN_PERCENT','TWENTY_PERCENT','THIRTY_PERCENT','FORTY_PERCENT'])},
        'P_INTERNAL_CONTACT_ACTIVE':'NO_ACCEPTED_FULL_MODEL_INTERNAL_CONTACT; LOCAL_EXTERNAL_WALL_CONTACT_PROVEN',
        'Q_FULL_STRESS_STRAIN_RESPONSE':'INHERITED_15_PRIMARY_POINTS_ONLY', 'R_DEFORMATION_FIELDS':'INHERITED_FULL_NATIVE_FIELDS_AND_NEW_LOCAL_DIAGNOSTIC_FIELDS',
        'S_MECHANICAL_MESH_CONVERGENCE':'UNQUALIFIED','T_MATERIAL_CALIBRATION':'UNQUALIFIED','U_PAPER_READINESS':'HOLD',
        'V_LLM_OPTIMIZATION':'NOT_IMPLEMENTED','W_REDUCED_DOMAIN_DEMONSTRATION':'NOT_EXECUTED'}
    commits=[{'hash':line.split('\t',1)[0],'message':line.split('\t',1)[1]} for line in git('log','--reverse','--format=%H%x09%s',audit['base_commit']+'..HEAD').splitlines()]
    summary={'status':'CONTACT_ONSET_LOCALIZED__NO_QUALIFIED_CORRECTION__FULL_RETRY_NOT_JUSTIFIED',
             'generated_utc':datetime.now(timezone.utc).isoformat(),'base_commit':audit['base_commit'],'independent_statuses':qstates,
             'maximum_qualified_full_engineering_strain':.009270608836206897,'maximum_qualified_full_compression_percent':.9270608836206897,
             'full_displacement_mm':.09493103448275862,'upper_RF_N':-10.90307046622248,'nominal_stress_MPa':1.064752975217039,
             'new_full_accepted_states':0,'inherited_primary_points':15,'full_recovery_attempts':0,'local_solver_processes':8,
             'local_valid_mechanical_variants':5,'invalid_setup_cases':3,'local_native_cutbacks_five_valid_variants':cuts,
             'last_local_diagnostic_native_state':local,'local_recovery_maximum_abs_EYY_EXX':local_strain,
             'max_raw_local_GC_penetration_mm_unconverged_included':raw_pen,'max_raw_local_chattering':raw_chatter,'max_raw_local_GC_active_count':raw_active,
             'native_parent_readback':native_parent,'performance':perf,'tests':tests,'commits_before_containing_report_commit':commits,
             'protected_historical_files_unchanged':True,'no_push':True,'no_3D_batch_or_LLM_optimization':True,
             'next_milestone':'Validate contact coverage on the exact curved onset geometry, then one justified full-model1% recovery before substantial compression.'}
    write_json(RUN/'summary/V0_6_7_VALIDATION.json',summary)
    write('V0_6_7_LOCAL_FIXTURE.md',f'''# v0.6.7 local fixture

The fixture preserves5527 original nodes,2499 original TRI6 elements and498 original physical faces exactly. It is an extracted submodel, not a remesh or a large-strain specimen demonstration. Original centroids lie in x1.70–2.24mm, y9.95–10.24mm. All six nodes and original connectivity are retained. Original-ID maps and the full local mesh are bound by SOURCE_EXTRACTION.json; raw arrays remain outside Git. This region contains external/top faces and no pore faces; it diagnoses the observed external-corner interaction.

Twenty-nine artificial cut faces are excluded from contact because they represent removed continuum, not physical free surfaces. Sixty cut nodes receive both measured displacement components from15 accepted nodal-branch fields. The top rigid platen remains at its original coordinates with UY=−10.24×loading parameter. E1000MPa,nu0.3,t1mm,plane stress and NLGEOM are unchanged. Beyond the parent, cut motion follows the secant of the last two measured fields; this is a diagnostic hypothesis.

The first three setup trials are invalid comparisons: one omitted the second automatically generated contact type; two retained all physical faces but split the original body's section identity. Actual source readback proves the relevant original skins use type4/section4. Corrected trials explicitly retain that identity on all498 physical skins; native inventories verify it. No source mesh or full restart was changed.

At the final measured parent, corrected FKN100 core displacement RMS relative error is{parent['core_U_RMS_relative']:.9g}; core SYY/SEQV/EYY/EXX RMS errors are{parent['core_SYY_SEQV_EYY_EXX_RMS_relative']}. Prescribed cut errors are{parent['cut_displacement_max_error_mm']:.9g}mm. These pass the registered field gates. Early low-load stress matching fails: the first state's relative errors are{baseline['states'][0]['core_SYY_SEQV_EYY_EXX_RMS_relative']}. This is reported, not removed from the history.

The nanogap/contact context is not identical: the full accepted parent has open GC, while the corrected local equilibrium develops tiny contact penetration{parent['maximum_penetration_mm']:.9g}mm. Agreement of bulk displacement and stress does not establish identical near-touch geometry. The cut boundaries remove global compliance and shift the observed failure threshold. The fixture reproduces the qualitative onset mechanism, not the exact full-model failed displacement field.

Native baseline self-contact is supported by opposing patch forces. The local recovery's final valid force vectors are{local['independent_two_sided_interface']['solid_restoring_forces_A_B_N']}N. Its opposition error is{local['independent_two_sided_interface']['opposition_relative']:.9g}; independent platen force on those patches is zero. The old selected-GC-skin FSUM quantity omits the target-side structural contribution and is retained as a diagnostic, not labeled a complete interface balance.
''')
    rows=[]
    for label in cases:
        r=read(BASE/label/'execution_receipt.json');tele=read(BASE/label/'nonlinear_telemetry.json');last=tele['converged_substeps'][-1]
        rows.append(f"|{label}|{r['process']['returncode']}|{last['load_step']}/{last['substep']}|{last['pseudo_time']:.10g}|{len(tele['cutback_events'])}|")
    write('V0_6_7_CONTACT_CORRECTION.md',f'''# v0.6.7 contact correction

No correction is selected for a full-model retry. Eight small solver processes comprise three invalid setup comparisons, four controlled contact variants and one native iteration-limit recovery. Each addition was registered and committed before execution. The initial limits were prospectively amended for documented extraction defects and one evidence-directed NEQIT recovery; clocks and physical gates were unchanged.

|Actual local variant|Native return|Last converged LS/SS|Printed boundary-load parameter|Native cutbacks|
|---|---:|---|---:|---:|
{chr(10).join(rows)}

Nodal target-normal detection with FKN100,10 and1 all develops onset cycling and fails before the complete registered local path. Penalty scaling alone is insufficient. FKN1's terminal residual decreases from0.002921 to0.002628N against0.002603N, justifying one bounded64-iteration continuation. It gains LS18SS9 at native time{local['time']:.16g}, then fails LS18SS10 with residual0.003722N against0.002604N after64 iterations. No further parameter trial is authorized by the final registered stopping rule.

Standard projection KEYOPT4=3 is accepted by actual licensed2024R1 and converges to boundary parameter0.01. It is rejected mechanically: unexplained quadratic crossings remain, including original faces28506/27837 and28505/27838. Native converged contact diagnostics report penetration1.433883e−6mm at the endpoint, while endpoint-only sequence outputs are zero. Zero endpoint output does not establish zero penetration at projection integration points. The unchanged direct target-facet/positive-separation checks fail. No enlarged neighborhood or relaxed overlap criterion is introduced.

All independently screened converged TRI6 mappings remain positive. The corrected nodal baseline and the one recovered local state pass force, penetration and native-linked contact geometry checks; they remain local diagnostic states under prescribed cut motion. A valid lower local state does not establish a robust correction through the required onset path.

Force extraction correction: selected contact elements do not represent both sides of this interface. Fresh POST1 sums original structural element force contributions on both localized physical boundary patches and independently checks zero platen contribution there. Equal/opposite force transmission passes the unchanged1% gate. This establishes local transmission, not full-model internal contact or global performance.

Official syntax/context: [CONTA172](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_CONTA172.html), [GCDEF section rules](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_GCDEF.html), [FSUM selected-element scope](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_FSUM.html). These adjacent-release references guide interpretation; actualv241 decks, listings and licensed outputs establish installed behavior.
''')
    write('V0_6_7_RESTART_AND_BRANCH_COMPATIBILITY.md',f'''# v0.6.7 restart and branch compatibility

The exact full parent remains LS3SS6,time0.009270608836206897 on FINE_FULL_SELF_CONTACT_NODAL_V066_021. Initial and final authentication covers RDB,LDHI,R001,RST. Fresh independent POST1 returns UY−0.09493103448275862mm, upperRF−10.90307046622248N and lowerRF+10.90287635833509N. Sampled native U/S/EPEL agrees with retained qualified fields; original files are unchanged.

One genuine local native restart copied and authenticated the FKN1 RDB/LDHI/R001–R003/RST, resumed LS18SS8 with CONTINUE and increased NEQIT24→64. Actual native inventory identifies the selected frame. It converged LS18SS9, then failed the next substep. This proves that the control change executes on this local restart; it does not prove that an FKN change from the full FKN100 parent is qualified.

ANSYS ignored RESCONTROL,DEFINE during CONTINUE and warned explicitly. Existing frame retention remained available; this warning did not cause the subsequent64-iteration nonconvergence. The warning and error are preserved. Any future controller should set retention after native ENDSTEP or use the supported restart modification route.

No full-parent clone was solved or modified. A pure numerical stiffness/control correction would require actual FKN-change qualification plus the already validated native ENDSTEP route before a full retry. Projection changes the integration/detection layout and requires a fresh same-fine-mesh branch with independent precontact response reproduction. Projection failed local geometry, so no such branch is launched. No result curves are spliced.
''')
    write('V0_6_7_PROGRESSIVE_COMPRESSION.md',f'''# v0.6.7 progressive compression

Maximum qualified full-model compression remains0.9270608836206897%, displacement0.09493103448275862mm, signed upperRF−10.90307046622248N and nominal compression stress1.064752975217039MPa. All15 inherited primary-branch points remain accepted. There are zero new full-model accepted states and zero v0.6.7 full recovery attempts.

The registered schedule was0.95%,1%,1.1%,1.5%,2%,5%,10%,20%,30%,40%, using actual adaptive substeps after qualification. No local candidate passed the complete onset path under unchanged geometry gates, so the full-retry entry gate did not open. None of1%,2%,5%,10%,20%,30% or40% is newly qualified. The six-hour historical clock was replaced by a finite12-hour new campaign, with three hours for diagnosis/local work,90min/stage and30min without full converged progress. Stopping here follows the scientific gate and registered case cap, not a memory or elapsed-time failure.

The final local native success is boundary-loading parameter{local['time']:.16g} under secant-extrapolated cut motion. This parameter is not a measured full-specimen strain, a reduced-domain compression result or an extension of the full stress–strain curve. The projection's native0.01 endpoint is quarantined for geometry. No smaller mesh or reduced-domain demonstrator is substituted for the specimen.
''')
    write('V0_6_7_DEFORMATION_RESULTS.md',f'''# v0.6.7 deformation results

No new full-model deformation field is claimed beyond the inherited0.9270608836206897% state. The existing15 primary snapshots, full all-node U and native corner S/EPEL fields remain authenticated. Full peak SEQV is92.7209898MPa; maximum absolute EYY0.066973865607 and EXX0.046433799385. Minimum accepted pore-area ratio0.96562185745 shows approach to closure without observed full pore-wall engagement or collapse. Mechanical mesh convergence and material calibration remain unqualified.

New native local all-node displacements, corner stresses/strains, contact status/pressure and signed patch forces are independently reopened for reported states. The final valid local recovered state's maximum absolute EYY/EXX is{local_strain}. It is a diagnostic submodel under transferred/extrapolated boundary motion, not a prediction for the full specimen. Its penetration is{local['maximum_penetration_mm']:.10g}mm and all2499 deformed quadratic maps are positive.

Figures: ../figures/contact_onset_closeup.png maps failed residual nodes onto the actual accepted full geometry; ../figures/local_candidate_comparison.png compares actual local native diagnostics; ../figures/local_projection_geometry_hold.png shows the rejected projection boundary geometry at true scale. The inherited highest full-specimen true-scale image remains in ../../../../pipeline_v0.6.6/run_001/figures; no fabricated high-strain full image is generated.

Pressure/penetration sequence outputs are formulation-dependent. For projection, zero stored endpoint penetration is not accepted as a global contact gap measurement; actual CND and unexplained quadratic crossings retain the HOLD. Native debug substep999999 is never used for accepted mechanics.
''')
    sections={
        'A. Historical foundation':'Source WKB, exact fine mesh, immutable full restart and fresh POST1 checks pass. Historical rejected1% states and15 accepted primary points retain their prior classifications.',
        'B. Contact-onset diagnosis':'Native residual maxima localize to original nodes98184/99405/99399/4990 at the upper external corner. Individual full failed-trial skin transitions remain unavailable; pair-level chattering and penetration are observed.',
        'C. Geometry-faithful local fixture':'Exact original TRI6 extraction, physical/cut-face separation and15 measured cut histories are preserved. Late parent bulk fields match; earliest stress and nanogap contexts do not match exactly.',
        'D. Contact correction':'Nodal FKN100/10/1 fail the complete local path. Projection3 converges but fails geometry. NEQIT64 gains one local state then fails. No correction is selected.',
        'E. Restart compatibility':'Native local CONTINUE with NEQIT64 executes. Modified-FKN full-parent restart is not qualified; projection would require a fresh branch and is rejected before full use.',
        'F. Full-model recovery':'Zero full retries: the local mechanical gate did not open. Prior valid full restart remains unchanged and independently readable.',
        'G. Large-strain progression':'No new accepted full1%,2%,5%,10%,20%,30% or40% state. Highest qualified full compression remains0.9270608836206897%.',
        'H. Mesh strategy':'Fine source semantic identity is unchanged. No smaller mesh attempted; the historical failed10degree coarse candidate is not reused. Local extraction does not establish mesh convergence.',
        'I. Contact behavior':'Local external-wall transmission is demonstrated by independent opposing structural patch forces. No accepted full-model internal pore contact is established. Projection crossing states are rejected.',
        'J. Mechanical validity':'Signed reaction, two-sided contact force, penetration, complete native fields, positive quadratic mapping and exact/native-linked boundary geometry are assessed separately. Full tolerance limits are preserved.',
        'K. Physical limitations':'Uncalibrated E1000MPa,nu0.3,t1mm plane-stress elastic material. Large local strains are not experimental material validation; full mesh convergence remains unqualified.',
        'L. Computational performance':f"{perf['native_processes']} actual native processes,8 small solver processes,1 genuine local restart,zero full retries. Native process runtime sum{perf['sum_native_process_wall_seconds']:.3f}s; peak process-tree RSS{perf['peak_tree_RSS_bytes']/1024**3:.4f}GiB; raw disk{perf['raw_v067_disk_bytes']/1024**3:.4f}GiB. Severe paging samples{perf['severe_paging_samples']}; proxy is system hard-fault reads, not pagefile-only traffic.",
        'M. Reproducibility':f"794 current tests,475 archived replay checks in9groups and{tests['licensed_evidence']['passed']} actual licensed-artifact evidence checks pass. Native logs/receipts, request/questions hashes, original-ID maps and prospective protocols are retained. Historical protected Git diff is empty.",
        'N. Git history':'Descriptive local commits accompany coherent changes. The table below lists commits present when this report was generated. The final post-commit delivery ledger records the containing documentation/final verification commits and clean tree without a self-referential file hash. Nothing was pushed.',
        'O. Next milestone':'Develop a robust contact treatment that covers the actual curved onset geometry and passes all local force/penetration/crossing gates. Then qualify one full1% recovery and continue adaptively toward30%, with40% as stretch. Paper readiness also needs mesh convergence and physical calibration; autonomous LLM optimization remains deferred.'}
    validation=['# v0.6.7 validation','',f"Status: **{summary['status']}**.",'']
    for title,body in sections.items():validation += ['## '+title,'',body,'']
    validation += ['## Independent scientific acceptance states','']+[f'- **{key}:** {value}' for key,value in qstates.items()]
    validation += ['','## Local commits recorded before this report commit','','|Full hash|Message|','|---|---|']+[f"|{c['hash']}|{c['message']}|" for c in commits]
    write('V0_6_7_VALIDATION.md','\n'.join(validation))
    answers={
        1:f"Yes; WKB SHA256{audit['source_sha256']}.",2:f"Yes; semantic SHA256{audit['fine_mesh']['semantic_sha256']},2766505nodes/1261670TRI6.",
        3:'Yes; exact LS3SS6,time0.009270608836206897; all four native file hashes match.',4:'Yes; initial and final hashes plus fresh read-only native POST1 verify unchanged files.',
        5:'Prior platen-only and Gauss-GC1% states remain rejected.',6:'Two exact quadratic nonadjacent boundary crossings near the upper external corner, missed by the corresponding contact treatment.',
        7:'All15 original nodal primary-branch points through0.9270608836206897%; reference branches remain separate.',8:'Yes; protected historical Git diff is empty.',
        9:'The approaching upper external free/top-corner surfaces accompany the residual concentration and contact cycling; exact global causality remains qualified.',
        10:'Accepted deformed location approximately x1.934mm,y10.130–10.133mm; original x1.96–1.98mm,y10.227–10.240mm.',
        11:'Principal full skins1295993,1494296,1494295; adjacent1285266/1383913; actual source type4/section4.',12:'Zero-based original boundary27837,28505,28506, with adjacent27838/28504.',
        13:'General self-contact of external specimen faces near the upper corner, not demonstrated internal pore-wall engagement; platen contact coexists elsewhere.',
        14:'Yes; native aggregate GC counts/chattering change. The accepted full parent remains open with zero GC pressure.',
        15:'Not in the full failed trial: CND is aggregate. Local converged fields identify actual skins/status/targets; no missing trial transitions are invented.',
        16:'Yes; top64 nodes in both retained NR snapshots, led by98184/99405 and nearby original nodes.',17:'Approximate accepted-geometry opposing normal dot product−0.999406; complete failed-trial normals are unavailable.',
        18:'Yes; prior full unconverged trial reports3.178046e−6mm. New local native penetration is reported separately by state and formulation.',
        19:'Yes; full terminal native chattering level4 and local switching diagnostics. Pair records do not identify every individual transition.',
        20:'Near-endpoint contact switching is supported; original-body section identity matters in the submodel. Penalty scaling alone did not resolve onset.',
        21:'Global compliance/path effects, earliest submodel stress mismatch, nanogap/contact-state mismatch and a robust geometry-valid detection treatment remain unresolved.',
        22:'Yes;5527 exact original nodes and2499 original TRI6.',23:'Original element centroids in x1.70–2.24mm,y>=9.95mm; all six nodes/connectivity retained with original-ID maps.',
        24:'Measured15-state cut-displacement history on60 cut nodes, original rigid platen motion; final-two-state secant extrapolation is diagnostic only.',
        25:'Final parent core U/S/EPEL matches registered field tolerances; earliest stress states and the nanogap/contact status do not match exactly.',
        26:'Corrected section-preserving baseline reproduces qualitative residual cycling/cutbacks and nonconvergence; exact full threshold differs.',
        27:'Removed global compliance and connected-body context; section identity was corrected, but full cut-force feedback and future cut motion remain absent.',
        28:'Nodal2 FKN100,10,1; projection3 FKN1; one FKN1 native NEQIT24→64 control recovery. Three earlier setup comparisons are invalid.',
        29:'None passed the complete registered local onset path with all gates; no full correction selected.',
        30:f"Final valid local recovery patch forces{local['independent_two_sided_interface']['solid_restoring_forces_A_B_N']}N; opposition error{local['independent_two_sided_interface']['opposition_relative']:.9g},zero platen patch force.",
        31:f"Final valid local recovery penetration{local['maximum_penetration_mm']:.10g}mm. Projection endpoint native CND penetration1.433883e−6mm does not cure its geometry failure.",
        32:'Projection states show unexplained crossings and are rejected. Accepted nodal local crossings are covered only by existing native-linked contact interpretations.',
        33:'Yes for independently screened converged local states; all2499 deformed maps positive. Failed/debug fields are not accepted.',
        34:'Yes; actual licensed Ansys MAPDL2024R1 native solves and independent POST1 readbacks.',
        35:'Preserved and reopened read-only; no new full solve used it because no local correction passed.',36:'No fresh full branch was launched. Projection would require one, but failed local geometry.',
        37:'Native local NEQIT CONTINUE executes; FKN modification of the accepted full parent was not verified or attempted.',
        38:'No new full formulation selected; inherited full nodal target-normal general contact remains the historical baseline.',39:'No full physical assumptions changed; all local material, thickness and plane-stress assumptions retained.',
        40:'Local NEQIT24→64 in one authenticated restart; full controls unchanged. Projection was a separately registered local variant.',41:'Yes; CNVTOL.005,norm2,minref1e−8,1% force opposition,1e−5mm penetration and existing crossing criteria preserved.',
        42:'Zero full recovery attempts;8 small native solver processes,including1 genuine local restart.',43:'No new full state crosses the prior limit.',44:'No;1% remains unqualified.',
        45:f"None for the full model. One additional locally accepted diagnostic restart state has native boundary parameter{local['time']:.16g}; not full compression strain.",
        46:'No accepted full internal-contact engagement; local external-wall engagement is demonstrated.',47:'New local two-sided structural interface forces are independently verified; inherited full acceptance remains unchanged.',
        48:f"Full inherited balance remains1.7803048048850376e−5 relative; final local recovery reaction-sum error{local['reaction_sum_relative']:.9g}.",
        49:'No excessive penetration in the reported mechanically accepted local recovery; failed/setup/projection records remain separate and retain their diagnostics.',
        50:'Yes in projection diagnostics; rejected. No new full state is accepted with crossing.',51:'No inversion in independently screened converged states; failed trial fields are not qualified.',
        52:'Nodal contact-onset convergence exhaustion. The64-iteration restart gains one state, then residual rises to0.003722N versus0.002604N; projection instead fails geometry.',
        53:'0.9270608836206897% full-model compression, unchanged.',54:'No.',55:'No.',56:'No.',57:'No.',58:'No.',59:'No.',60:'0.09493103448275862mm.',
        61:'Zero new full accepted substeps; the local control restart contributes one preserved mechanically valid diagnostic state.',
        62:f"{cuts} native cutback events across the five valid local mechanical/control variants; full retry cutbacks0. Invalid setup cases are separately retained.",
        63:f"New accepted full self-contact count0. Local whole-field projection closed-skin maximum4 is geometrically quarantined; raw trial GC count maximum{raw_active} is not an accepted full count.",
        64:f"Raw local trial GC penetration maximum{raw_pen:.10g}mm,including unconverged/setup cases. Final valid local recovery{local['maximum_penetration_mm']:.10g}mm; no new full-model maximum.",
        65:'Original full LS3SS6,R001,time0.009270608836206897; preserved unchanged.',66:'No candidate passed the complete geometry-valid local onset path, so the full-entry gate remained closed.',
        67:'No new full-model curve;15 inherited primary points remain the qualified branch.',68:'Inherited full upper reaction magnitude10.90307046622248N.',69:'Inherited full nominal compression stress1.064752975217039MPa.',
        70:'At the maximum qualified full0.9270608836206897%,1.064752975217039MPa. No new major full checkpoint stress exists.',
        71:'Yes; inherited full snapshots and new actual local diagnostic snapshots/fields.',72:'Full15 historical primary strains through0.9270608836206897%; local measured-history checkpoints and explicitly secant-extrapolated states, not new full strains.',
        73:'Yes; inherited full native corner S and independently reopened local S.',74:'Yes; inherited full native EPEL and independently reopened local EPEL.',
        75:'Local native GC pressure fields are extracted; accepted full GC remains open/zero. No full pore-contact pressure field is invented.',76:'Inherited minimum pore-area ratio0.96562185745; no observed full pore closure.',
        77:'No accepted full pore-wall engagement. The proven local interaction is on external upper-edge surfaces.',78:'Unexplained projection crossings are rejected; historical invalid1% states remain rejected.',
        79:f"Inherited full maxabs EYY0.066973865607,EXX0.046433799385. Final valid local recovery maxabs EYY/EXX{local_strain}; local context only.",
        80:'Provisional and uncalibrated; these numerical results do not validate elastic material behavior at substantial compression.',81:'No; mechanical mesh convergence remains unqualified.',
        82:'No new smaller mesh investigated.',83:'Not applicable; historical failed-angle coarse mesh is not reused.',84:'Full fine2766505nodes/1261670TRI6; extracted diagnostic5527nodes/2499TRI6,not a smaller full specimen mesh.',
        85:'No new mesh comparison or convergence study.',86:'No separately loaded reduced-domain compression demonstrator.',87:'Not applicable; local cut-field load parameter is not demonstrator compression strain.',
        88:'Yes; all local diagnostics remain explicitly separate from the full specimen.',
        89:f"Native process wall-time sum{perf['sum_native_process_wall_seconds']:.3f}s across{perf['native_processes']} processes; includes read-only postprocessing,not physical loading time.",
        90:f"Peak native process-tree RSS{perf['peak_tree_RSS_bytes']/1024**3:.6f}GiB.",91:f"{perf['severe_paging_samples']} sampled severe paging events; maximum system hard-fault read proxy{perf['max_system_page_reads_per_second']:.4g}/s,not pagefile-only traffic.",
        92:f"Raw v067 disk{perf['raw_v067_disk_bytes']}bytes ({perf['raw_v067_disk_bytes']/1024**3:.6f}GiB); inherited raw artifacts and durable fine mesh are separate.",
        93:'One genuine local native restart process; no full native restart solve.',94:'794 current tests passed.',95:'475 archived replay checks across9groups passed.',
        96:f"{tests['licensed_evidence']['passed']} actual licensed-artifact evidence checks passed; includes104 inherited v066 checks and27 new v067 checks,not that many new solves.",
        97:'All three invalid setup cases,three failed nodal stiffness cases,projection geometry rejection and64-iteration restart failure/debug outputs are preserved externally with compact tracked evidence.',
        98:'New v067 experiment/protocol/verification/report/figure files, v067 scripts andvalidation/ansys_v067_integration.py; see FILE_CHANGES.json. Historical files and existing solver implementation are unchanged.',
        99:'Descriptive local commits are listed in this handoff and the final delivery Git ledger.',100:'Full actual hashes/messages are in the Git table below; the post-commit external delivery ledger adds the containing final commits.',
        101:'Final clean-tree check is recorded after all documentation/verification commits in the delivery ledger.',102:'No; no push command was issued.',
        103:summary['status']+'.',104:'No; the full numerical barrier remains unresolved. It is localized and reproduced qualitatively in an exact-mesh submodel.',
        105:'No.',106:'No.',107:'Inherited15 qualified full primary points; corrected nodal local states passing their own gates,including one recovered local state,remain diagnostic only.',
        108:'All new local results,secant extrapolation,invalid setup cases and projection/debug results. They establish diagnostics,not extended full performance.',
        109:'Full internal pore contact,mechanical mesh convergence,material calibration and paper readiness remain unresolved; local early stress/nanogap context mismatch is explicit.',
        110:'Show the genuine0.927060884% full response/fields,the onset close-up,residual localization,source-section audit and local candidate/force/geometry comparisons. Do not show an unqualified1% or30% result as accepted.',
        111:'A contact treatment that passes exact geometry/force gates through onset,qualified full1% progression then30–40%,mechanical mesh convergence and physical material/experimental calibration.',
        112:'Resolve exact curved-surface contact coverage at the localized upper external corner; qualify the correction locally before one full-model recovery.'}
    questions=read(RUN/'protocol/HANDOFF_QUESTIONS.json')['questions'];assert set(answers)==set(range(1,113))
    write_json(RUN/'summary/HANDOFF_ANSWERS.json',{'status':summary['status'],'answers':[dict(q,answer=answers[q['number']]) for q in questions]})
    handoff=['# v0.6.7 handoff','',f"**{summary['status']}**. Full maximum remains0.9270608836206897%;30%/40% were not reached. No full retry was scientifically justified.",'',
             'All eight requested reports and independent statuses are retained. Local convergence,valid local substeps and full specimen acceptance are distinct. The final registered stopping rule has been followed.','']
    for q in questions:handoff += [f"## {q['number']}. {q['question']}",'',answers[q['number']],'']
    handoff+=['## Git commits available before this report commit','','|Full hash|Message|','|---|---|']+[f"|{c['hash']}|{c['message']}|" for c in commits]
    handoff += ['', '[Final post-commit Git history and clean-tree verification]('+str(BASE/'DELIVERY_GIT_HISTORY.md').replace('\\','/')+')', '']
    write('V0_6_7_HANDOFF.md','\n'.join(handoff))
    forensic=RUN/'summary/V0_6_7_CONTACT_ONSET_FORENSICS.md'
    text=forensic.read_text(encoding='utf-8').split('\n## Final diagnostic findings',1)[0]
    text+='\n## Final diagnostic findings\n\nActual licensed source readback confirms the principal skins use section4. All five reported original faces belong to original mesh loop0, among413 total boundary loops. Original and accepted quadratic coordinates are retained in ORIGINAL_BOUNDARY_LOOPS_AND_FACES.json. Automatic local body partitioning must not change that identity. With section identity preserved, FKN100/10/1 all reproduce onset difficulty; penalty scale alone is insufficient. Projection3 removes Newton failure locally but fails unchanged quadratic contact geometry and is rejected. The NEQIT64 local restart gains one mechanically valid state then fails; no full retry is selected. The local parent bulk-field match is good at the final accepted state, but early stress and tiny-gap/contact-state mismatches limit exact causal inference. Two-sided native structural patch forces prove local force transmission; selected-skin FSUM alone was not a complete interface balance.\n'
    write('V0_6_7_CONTACT_ONSET_FORENSICS.md',text)
    files=git('diff','--name-only',audit['base_commit']).splitlines()+git('ls-files','--others','--exclude-standard').splitlines()
    write_json(RUN/'verification/FILE_CHANGES.json',{'base_commit':audit['base_commit'],'files':sorted(set(files)),'raw_artifact_root':str(BASE),'no_historical_changes':True})
    print(json.dumps({'status':summary['status'],'tests':tests,'performance':{k:v for k,v in perf.items() if k!='jobs'},'reports':8,'handoff_answers':len(answers)}),flush=True)


if __name__=='__main__':main()
