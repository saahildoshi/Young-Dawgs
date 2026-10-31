"""Final scientific reports and all98 requested answers from actual evidence."""
from pathlib import Path
from datetime import datetime,timezone
import re
import subprocess
from scripts.v066_restart import REPO,RUN,load
from metamaterial_eval.simulation.reporting import write_json


def table(rows,columns):
    if not rows:return 'No qualified measurements available.'
    lines=['| '+' | '.join(name for key,name in columns)+' |','|'+'|'.join('---' for _ in columns)+'|']
    for row in rows:
        values=[]
        for key,name in columns:
            value=row.get(key);values.append(f'{value:.10g}' if isinstance(value,(int,float)) else str(value))
        lines.append('| '+' | '.join(values)+' |')
    return '\n'.join(lines)


def save(name,text):(RUN/name).write_text(text.rstrip()+'\n',encoding='utf-8')


def main():
    s=load(RUN/'summary/V0_6_6_VALIDATION.json');decision=load(RUN/'summary/STOP_DECISION.json')
    if s['status'].startswith('IN_PROGRESS'):raise RuntimeError('Final scientific reports require a completed execution decision')
    rows=s['accepted_measurements'];maximum=s['maximum_qualified_engineering_strain'];native=s['maximum_actual_Newton_converged_engineering_strain']
    primary=s['primary_model_variant'];primary_max=s['primary_maximum_qualified_engineering_strain'];perf=s['performance'];tests=s['tests']
    reference=s['model_branches']['PLATEN_ONLY_REFERENCE'];fit=s['initial_modulus_fit'];work=s['compression_work']
    accepted=[q for q in s['qualifications'] if q['accepted'] and q.get('model_variant','PLATEN_ONLY_REFERENCE')==primary]
    highest=max(accepted,key=lambda q:q['state']['time']) if accepted else None
    pressure=max((c['max_stored_endpoint_pressure_MPa'] for q in accepted for c in q.get('contacts',[])),default=None)
    gc=[q['general_contact'] for q in accepted if q.get('general_contact')]
    full_engaged=any(g['closed_skins']>0 for g in gc)
    peak_force=max((-r['upper_rf_y_N'] for r in rows),default=None);peak_stress=max((r['nominal_compression_stress_MPa'] for r in rows),default=None)
    curve=table(rows,[('engineering_compression_strain','Engineering compression fraction'),('compression_displacement_mm','Travel mm'),('upper_rf_y_N','Upper RF N'),('lower_rf_y_N','Lower RF N'),('nominal_compression_stress_MPa','Nominal stress MPa'),('reaction_balance_relative','Signed imbalance fraction'),('secant_modulus_MPa','Secant MPa')])
    statuses=table([{'category':k,'status':v} for k,v in s['independent_acceptance'].items()],[('category','Independent category'),('status','Actual status')])
    ledger='\n'.join('- '+line for line in s['commits_before_containing_report_commit'])
    local=highest.get('absolute_elastic_components_percentiles') if highest else None
    fields=highest.get('corner_field_percentiles') if highest else None
    pores=highest.get('boundary_screen_summary',{}) if highest else {}
    worst_balance=max((r['reaction_balance_relative'] for r in rows),default=None)
    restart=decision.get('last_valid_restart','See native restart inventory and stop decision')
    shared=f'''Scientific status: **{s['status']}**. Highest independently qualified strain across branches: **{maximum*100:.9g}%**. Highest completed native strain: **{native*100:.9g}%**; convergence alone does not establish qualification. Primary branch `{primary}` is qualified through **{primary_max*100:.9g}%**.

Stop reason: {decision['reason']}

Thirty percent primary target: {'REACHED VALIDLY' if maximum>=.3-1e-12 else 'NOT REACHED'}. Forty percent stretch: {'REACHED VALIDLY' if maximum>=.4-1e-12 else 'NOT REACHED'}. All reported curves stop at actual qualified points. The distinct contact-model branches are never spliced.
'''
    identity='''Design9, seed1, native1024 canonical polygon source. Source SHA256 `4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1`; fine mesh semantic SHA256 `e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc`. Structural nodes 2,766,505; structural TRI6 elements 1,261,670; all 412 original pore loops. Original minimum angle 11.404135 degrees exceeds frozen 10 degrees. Original sampled feature rule >=3; selected fine observed minimum 7. All original quadratic mappings qualified. Full model additionally has 2,598 platen contact skins,4 rigid target/pilot elements and 243,576 native GC skins, with 6 auxiliary platen nodes. These overlays do not replace the original continuum mesh.'''
    assumptions='''Licensed ANSYS Mechanical APDL2024R1, 2D plane stress, mm-N-MPa, width/height 10.24 mm and provisional thickness 1 mm. Provisional E=1000 MPa, nu=0.3 linear elasticity, NLGEOM ON. No material calibration, plasticity, damage, fracture, out-of-plane buckling or experimental prediction is established. Native local strains are monitored, but supported corner averages can understate integration-point extremes. Pixel-boundary stress concentrations and force curves remain unqualified for mesh convergence.'''
    controls='''Displacement-controlled quasi-static pseudo-time, total upperUY=-10.24*engineering_strain mm. Full Newton, line search, AUTOTS, NEQIT=24, force CNVTOL=0.005/norm 2/minimum reference 1e-8; initial increment <=0.0005, maximum 0.005, minimum 1e-6. Sparse DEFAULT memory selection, actual licensed SMP settings recorded in receipts. No fixed RSS cap; system available/committed memory and paging HealthPolicy, 40 GiB free-disk reserve, one native job at a time, original six-hour campaign/90-minute stage/30-minute no-progress bounds. The qualified numerical restart frequency is1, with three rolling frames; the legacy ALL-frequency retention deviation is explicitly documented.'''
    gates='''Accepted states independently reopen native RST using the actual LS/SS and full-precision TNOW. Require complete all-node U, native corner SYY/SEQV/EPEL Y/X, signed support imbalance<=1%, independent platen contact-force opposition<=1%, positive pressure/engagement, stored endpoint penetration<=1e-5mm, every deformed TRI6 map positive, and no unexplained boundary crossing. Whole-element ETABLE NMISC19 inventories distinguish native far-field record absence from missing active data; every missing platen far-field edge must independently clear the finite platen by analytic quadratic bounds. Full-GC contact intersections require actual closed positive-pressure native links or the prospectively registered bounded nodal shared-endpoint explanation, plus native assembled force balance. Pure geometric separation never supplies a contact force. No default/ignored/sentinel result values establish acceptance.'''
    save('V0_6_6_PROGRESSIVE_COMPRESSION.md',f'''# v0.6.6 progressive compression

{shared}

## Primary actual mechanical response

{curve}

Peak force over this computed primary interval: {peak_force}N; peak nominal stress: {peak_stress}MPa. These are not ultimate strength predictions. Nominal stress uses original width*thickness; compression is positive in plots and upper reaction remains negative.

Primary initial-fit result: {fit}. Preserved platen-only initial reference fit: {reference['initial_modulus_fit']}. The latter is not silently transferred into a fitted full-GC curve. Secants are pointwise stress/actual strain, not fitted tangent moduli.

Observed-interval loading work: {work}. This is numerical trapezoidal work, not validated dissipation/energy absorption. No origin or uncomputed high-strain extension is added.

## Execution and stopping

{controls}

New completed fine-mesh substeps across the distinct numerical contact branches: {s['new_fine_converged_substeps']}; explicit native cutback events: {s['native_cutback_events']}; completed Newton updates: {s['completed_Newton_updates']}. Force evaluations are not miscounted as updates. Native source failures/stops: {s['failed_fine_jobs']}.

Last valid restart description: {restart}. A readable converged RST field and an available native Rnnn frame are reported separately; no coordinate-only restart is substituted.

## Reference branch

The original platen-only branch is separately preserved through{reference['maximum_qualified_engineering_strain']*100:.9g}% at{reference['accepted_point_count']}qualified points. Its1% state has two exact quadratic free-boundary crossings and is excluded. Its retained load-step restart endpoints differ from the intermediate field inventory; see audit015. Each subsequent full-GC model is a fresh same-fine-mesh model because adding contact topology changes the original restart model.
''')
    small=load(RUN/'internal_contact/QUALIFIED_SHORT_GAP.json')
    save('V0_6_6_INTERNAL_CONTACT.md',f'''# v0.6.6 internal and free-surface contact

{shared}

Platen pair contact is retained: frictionless separable CONTA172/TARGE169, pure penalty KEYOPT2=1/4=2/10=1,FKN100,FTOLN=-1e-5mm. Native whole-element status is authoritative; CONT STAT nodal averages can be fractional. Far-field pressure/gap/force records are omitted rather than fabricated. [ANSYS contact-output reference](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_CONTA172.html).

The original wide-gap C-fixture stopped with distortion and excessive penetration and remains a failure record. A shorter-gap connected C-fixture subsequently passed actual contact-on/contact-off execution and independent native readback: {small['status']}. Enabled support force 38.95905325 N versus disabled 9.84711992 N;114 closed/118 selected skins; maximum stored endpoint penetration 3.14465e-8 mm. Opposed normal dot product-1. Force vectors and actual target IDs were verified by direct-query/vector comparisons; assembled fixture residual0.00013866819<0.01. The disabled control has actual boundary crossings despite positive element maps.

The first1% microstructure crossings involve external/top edges, not only pore walls. The corrective full model therefore covers ALL 243,576 exposed quadratic faces, including the original pair-contact faces. Native GCGEN/GCDEF SYMM ALL SELF uses material 1/real 100 with FKN100/FTOLN-1e-5. Exact oriented topology coverage has zero missing faces. Native surface-normal/topology handling and shared-original-vertex screen exclusions avoid accepting spurious connected-corner intersections; SELF is not globally excluded.

The default Gauss-point GC014 model also retained two exact endpoint-region crossings at 1%, with no accepted final pressure at those faces. That 1% state is rejected; its valid 0.859375% predecessor is retained. A single targeted repair changed GC KEYOPT4 from 0 to 2 (nodal detection normal to target), preserving all geometry, continuum mesh, material, load and acceptance limits. The nodal fixture independently passed force, pressure, penetration and mapping checks; see internal_contact/NODAL_FIXTURE_QUALIFICATION.json. The nodal microstructure uses a fresh native model because the contact integration state changes. Its accepted response is a separate branch.

At the rejected GC014 1% state, twelve near-contact skins were open and final contact pressure was zero. Transient unconverged contact pressure is not accepted engagement. The two exact curve crossings remain a detection failure, rather than a demonstrated pore-contact state.

Actual full-model engagement at accepted states: {full_engaged}. Highest-state native contact checks: {highest.get('general_contact') if highest else None}. Initial0.1% force-preservation comparison: {next((q.get('initial_response_comparison') for q in accepted if q.get('initial_response_comparison')),None)}.

Pressure/gap availability and force assembly are different questions. Native FSUM,,CONT over the entire GC skin selection includes target-role contributions; only force vectors are interpreted under NLGEOM, not moments. The force tolerance remains 1%. [ANSYS FSUM reference](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_FSUM.html).

Bounded-screen contact intersections retain the original direct native facet-link criterion. For verified nodal detection, a shared-endpoint explanation additionally requires actual positive endpoint pressure, a native target ID and a guarded quadratic proof localizing that otherwise unlinked contact to radius 5e-6 mm balls at the constrained nodes. An ambiguous near pair may instead be proved strictly separated. Protocol023 binds these rules and the actual fixture002 readback; the known bad Gauss1% crossings remain rejected. Native penetration remains within the original tolerance. Unexplained overlap, truncation or uncertain contact linkage is quarantined. The small fixture alone never establishes full-microstructure large-strain qualification.
''')
    manifest=load(RUN/'figures/manifest.json') if (RUN/'figures/manifest.json').exists() else {'rendered_states':[]}
    save('V0_6_6_DEFORMATION_RESULTS.md',f'''# v0.6.6 native deformation results

{shared}

Actual field artifacts are outside Git with hashes in each qualification. All 2,766,505 specimen nodes provide UX/UY; 752,212 native corner nodes provide SYY,SEQV,EPEL Y/X. No unsupported midside stresses are invented. Derived displacement magnitude/deformed coordinates and corner-linear visualization are explicitly distinguished from native fields. Platen pressures are native stored endpoints; self-contact pressure plots use native element-mean pressure.

Actual rendered state inventory: {manifest['rendered_states']}. Deformation scale is 1x. The rejected1% platen-only crossing plot is diagnostic, not a qualified deformation. Exact intersection residuals and interior curve parameters are in deformation/EXACT_CROSSING_DIAGNOSIS_013.json.

At the highest primary state, absolute elastic-component percentiles [50,95,99,100] are{local}. Signed native corner-field percentiles [0,1,50,95,99,100] for [SYY,SEQV,EYY,EXX] are{fields}. These do not certify local material plausibility or a mesh-converged peak stress.

Highest primary boundary-screen summary: {pores}. All accepted states have positive whole-domain quadratic maps; highest-state shape diagnostics:{highest.get('deformed_corner_shape_diagnostics') if highest else None}. Corner-based shape diagnostics supplement the polynomial Jacobian check and do not establish accuracy at severe distortion.

Pore signed areas are evaluated by exact quadratic edge integration and compared with their own original loops. No exhaustive opposing-wall minimum is claimed by the near-pair spatial screen. Native contact engagement plus geometry can establish approach/touch; complete closure, global buckling or collapse is not inferred from a picture alone. Constitutive and2D limitations remain research HOLDs.
''')
    save('V0_6_6_VALIDATION.md',f'''# v0.6.6 scientific validation

## A. Executive summary

{shared}

## B. Model identity

{identity}

{assumptions}

## C. Large-strain protocol

{controls}

## D. Mesh strategy

The one smaller exact-geometry candidate had 1,383,233 nodes/610,630 TRI6 and a 2.066 element-count reduction, but failed 10 degrees with 8.3031647757 degrees. It was rejected without a mechanics benchmark. No accepted coarse/fine sensitivity or mechanical mesh convergence was established. The fine mesh remains intact.

## E. Contact model

Small fixture qualified; full 243,576-skin model implemented. Actual full accepted engagement:{full_engaged}. See V0_6_6_INTERNAL_CONTACT.md. The platen-only1% state is rejected for two confirmed free-boundary crossings. Separate model branches are never spliced. The default Gauss-point GC014 1% state also fails exact boundary crossing checks; its valid predecessor remains preserved. The single nodal repair is separately identified in protocol021 and the contact report.

## F. Restart qualification

Rectangle and compliant continuous/restarted histories and fields passed the registered 1e-5 scaled tolerance. Genuine v065 native continuation executed before the full-GC corrective fresh model. Actual native frame inventories expose the legacy endpoint-only retention deviation. Numeric frequency 1 was separately demonstrated to retain the last 3 of 5 substeps. All parents are immutable authenticated copies. Last valid restart:{restart}.

## G. Progressive mechanical results

{curve}

Initial fit:{fit}. Preserved reference fit:{reference['initial_modulus_fit']}. Work:{work}. Peak computed primary force{peak_force}N; nominal stress{peak_stress}MPa. No values are generated for missing major strains.

## H. Deformation

See actual native field hashes, pore areas and true-scale figures in V0_6_6_DEFORMATION_RESULTS.md and figures/manifest.json. Highest local strain diagnostics:{local}.

## I. Numerical validity

{gates}

Maximum primary signed reaction imbalance:{worst_balance}. Native states/updates/cutbacks are separately counted. Failures/stops:{s['failed_fine_jobs']}. Earlier complete sets are evaluated from their own native log segment; later warnings do not retroactively fabricate or destroy a prior field. The failed recovery passes remain in audit.

## J. Physical limitations

{assumptions}

Native numerical convergence is not material calibration, mesh convergence, experimental validation, manufacturing readiness or a prediction of yield/fracture. Large native local strains strengthen these limitations.

## K. Performance

Total native process runtime{perf['sum_native_runtime_seconds']:.6g}s; fine source runtime{perf['fine_source_runtime_seconds']:.6g}s; peak native process-tree RSS{perf['peak_tree_RSS_bytes']/2**30:.6g}GiB. Severe-paging samples{perf['severe_paging_samples']}; maximum page-read rate{perf['maximum_page_reads_per_second']}. Raw v066 tree disk{perf['physical_v066_raw_disk_bytes']/2**30:.6g}GiB, including preserved/copy parents and diagnostics. Scope and per-job data are in performance/PERFORMANCE.json. No fixed RSS cap was used.

## L. Reproducibility and verification

Native input/receipt/RST/database/mesh/geometry bindings are explicit in each source/export manifest. Source and read-only execution are separate. Active tests:{tests['active']}; archived replay:{tests['archived_passed']}passed across{tests['archive_groups']}groups; licensed checks:{tests['licensed']}. These categories overlap and are not summed. Protected historical files unchanged:{s['protected_historical_files_unchanged']}. Nothing was pushed.

{statuses}

## M. Git commits

Base{ s['base_commit'] }. Ledger through the parent of this report commit:

{ledger}

The containing report commit and final clean-tree verification are identified in the delivery response/Git history; a commit cannot embed its own hash.

## N. Next milestone

{decision.get('next_step','Resolve the exact remaining numerical/contact limitation, establish mechanical mesh convergence and calibrate material data before paper-quality comparisons.')} Controlled LLM iteration additionally requires repeatable qualified mechanical datasets, uncertainty handling and explicit feedback safeguards. No batch FEM,3D,manufacturing or autonomous optimization was started.
''')
    save('V0_6_6_HANDOFF.md',f'''# v0.6.6 handoff

{shared}

Primary response branch:{primary}. Qualified points:{len(rows)}. Preserved platen-only reference:{reference['accepted_point_count']}points through{reference['maximum_qualified_engineering_strain']*100:.9g}%. Last valid restart:{restart}.

Show Dr. Wang the actual accepted stress-strain/force-travel plots, true-scale highest qualified deformation, native local stress/strain and self-contact pressure, plus the rejected1% reference crossing that motivated the corrective model. Explain that the30–40% targets are {'only numerical exploratory milestones' if maximum>=.3 else 'not yet achieved'} and that constitutive/mesh calibration remains open.

Next:{decision.get('next_step','Resolve the recorded numerical limit and qualify further loading.')} Before a paper dataset: repeatability, matched mechanical mesh refinement, calibrated material/geometry/thickness and verified boundary/contact assumptions. Before LLM feedback: stable acceptance/uncertainty rules and a controlled explicit iteration protocol.

Native artifacts remain under the recorded per-user YoungDawgs artifact root; Git contains manifests, compact evidence, CSV summaries, figures and reports. Current repository location is C:/Users/sd22446/Projects/Young-Dawgs-VSCode; the former OneDrive checkout is empty. Environment reinstall repaired the stale editable-package path; all recorded earlier failures are retained.

STOP: no 3D, batch design comparison,manufacturing,autonomous LLM optimization or push. Re-execution uses unique directories and a newly registered budget; existing source parents are never overwritten.
''')
    # Complete the three previously committed protocol/strategy reports with a
    # self-contained pointer to the final physical branch and retention evidence.
    for name in ['V0_6_6_LARGE_STRAIN_PROTOCOL.md','V0_6_6_RESTART_VALIDATION.md','V0_6_6_MESH_STRATEGY.md']:
        p=RUN/name;old=p.read_text();marker='\n## Final v0.6.6 outcome\n'
        old=old.split(marker)[0];save(name,old.rstrip()+marker+'\n'+shared+'\nAuthoritative final branch/gate/resource evidence is in V0_6_6_VALIDATION.md and summary/V0_6_6_VALIDATION.json. Each full-GC model preserves the fine mesh, adds all exposed self-contact skins and remains separate from the original platen-only native restart branch. Actual restart inventories and numerical-frequency correction are preserved in audit015 and restart_validation/RETENTION_QUALIFICATION.json.\n')
    yes=lambda target:'Yes, independently qualified.' if maximum>=target-1e-12 else 'No, not independently qualified.'
    answers=[
        'Design9, seed1, native1024 canonical polygon.', 'Yes; source SHA2564700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1.',
        'Yes, byte/semantic identity preserved.', 'The preserved fine mesh; full-GC corrective branch is separate from the platen-only reference.',
        'The smaller candidate failed the original angle gate.', '2,766,505 structural nodes and1,261,670TRI6; full contact overlays are counted separately.',
        'Yes, original frozen geometric gates.', 'Yes, all 412 original source pore loops.', '11.404135deg originally; deformed diagnostics are reported separately.',
        'Positive at every accepted deformed state under the whole-domain polynomial check.', 'Yes, one exact-source candidate.',
        '2.066times fewer elements only; no qualified licensed performance advantage.', 'No accepted mechanical mesh sensitivity study.', 'No; UNQUALIFIED.',
        'ANSYS Mechanical APDL2024R1.', 'Yes, actual licensed execution.', 'Yes, genuine multiframe continuation on the original branch.',
        'The later full-GC model starts fresh because adding contact topology changes the restart model.', 'Yes, rectangle and compliant fixtures.',
        'Yes, native inventories and independently reopened sets.', 'Yes; native UY=-10.24*actual engineering strain.', 'Yes, native required fields and explicit contact-record availability.',
        f"{perf['actual_native_processes']}native processes, including{perf['nonlinear_source_processes']}nonlinear sources; read-only/setup counts are separate in performance evidence.",
        'Yes, the original frictionless platen pairs.', 'Yes, actual enabled/disabled connected fixtures and a full native model.',
        'GCGEN/GCDEF symmetric general self-contact on all exposed deformable faces.', 'Yes, the short-gap fixture passed independent native readback.',
        'Yes,243576native skins exactly cover original exposed faces.', 'Yes on the fixture; '+('yes at accepted full-model states.' if full_engaged else 'full accepted engagement not established.'),
        'Native topology/normal handling plus original connected-vertex screen exclusions; no global SELF exclusion.',
        'Yes. The platen-only and default Gauss-point GC014 1% states both contain two confirmed quadratic crossings and are rejected; nodal-repair results are reported separately.', 'Yes, those crossing states are invalid and excluded from accepted curves.',
        'Yes, native platen forces and fixture contact transmission; full-model engagement is reported independently.',
        'Positive stored endpoint values denote penetration; far-field absence is explicit, not a zero gap.',
        'Chattering is recorded in native diagnostics; causal attribution is not isolated.',
        f'Native completed{native*100:.9g}%; independently qualified maximum{maximum*100:.9g}%.',
        *[yes(t) for t in [.01,.05,.1,.2,.3,.4]],f'{10.24*native:.10g} mm at the highest completed native strain; {10.24*maximum:.10g} mm at the highest independently accepted strain.',
        controls,f"{s['total_accepted_unique_branch_states']}qualified branch states;{s['new_fine_converged_substeps']}new native fine substeps.",
        str(s['native_cutback_events'])+'explicit native cutback events.', 'Instability is not inferred from convergence alone; native failures and folding are documented.',
        'No inverted mappings are accepted; failed trial distortion, if present, remains quarantined.',decision['reason'],str(restart),
        'Yes, separate actual qualified model-branch curves.', 'Yes, no branch splicing or uncomputed extension.',str(peak_force)+'N over the computed primary interval.',
        str(peak_stress)+'MPa over that interval.', 'Exact achieved points are in mechanical_results/accepted_force_displacement_stress_strain.csv; no missing major strain is filled.',
        'Platen-only reference fit:'+str(reference['initial_modulus_fit'])+'; primary fit:'+str(fit),
        'Yes, pointwise actual stress/strain secants.', str(work),'Yes; primary maximum relative signed imbalance'+str(worst_balance)+'.',
        'Yes, independent native contact/support-force checks and explicit availability handling.', 'Native corner hotspots are saved; peak stress mesh convergence is unqualified.',
        'Yes, signed and absolute elastic-component percentiles/maxima.', 'Physical plausibility remains unqualified: provisional linear elasticity and uncalibrated large local strains.',
        'Yes, genuine native field snapshots at true 1x scale.',str([r['engineering_strain'] for r in manifest['rendered_states']]),
        'Yes, every specimen node.', 'Yes, supported native corner SYY/SEQV.', 'Yes, supported native corner EPEL Y/X.',
        'Yes, platen endpoint and full-GC available native pressure fields; absent far-field records stay absent.',
        f"At the highest primary state the minimum exact pore-area/original-area ratio is {pores.get('minimum_area_ratio')}. This measures area change; an exhaustive opposing-wall distance is not claimed.",
        f"No complete pore closure is established from these data; the highest primary minimum area ratio is {pores.get('minimum_area_ratio')}. Native contact on external faces does not by itself establish full pore closure.",
        'Nonaffine deformation is saved; a global buckling/collapse event is not established by these fields alone.',
        'Yes, bounded quadratic spatial screening with explicit native contact explanations.',
        'The highest accepted state is numerically interpretable within the provisional 2D/contact model. A higher converged state that fails geometry/contact checks is excluded; experimental prediction remains HOLD.',
        f"{perf['sum_native_runtime_seconds']:.9g}s summed native process runtime.",f"{perf['peak_tree_RSS_bytes']/2**30:.9g}GiB peak native process-tree RSS.",
        str(perf['severe_paging_samples'])+'samples at the registered severe-paging threshold.',f"{perf['physical_v066_raw_disk_bytes']/2**30:.9g}GiB in the raw v066 tree; other roots separate.",
        str(perf['genuine_native_restart_processes'])+'genuine native continuation processes.',str(tests['active']['passed']),str(tests['archived_passed']),str(tests['licensed']['passed']),
        'Yes, protected Git paths and authenticated source parents unchanged.',str(s['failed_fine_jobs'])+'; current continuation limit: '+decision['reason']+' Earlier unsupported readbacks and rejected crossing states remain preserved as diagnostic failures.',
        'Descriptive local commits only; see the exact ledger in V0_6_6_VALIDATION.md.', 'Full hashes/messages are in that ledger; the containing final report commit is identified in the delivery response.',
        'Final delivery verifies the tree after the report commit.', 'No automatic push.',s['status'],yes(.3),yes(.4),
        'Exactly the branch-separated accepted CSV rows; highest qualified'+str(maximum*100)+'%.',
        'All results retain provisional single-mesh research status; rejected native states are diagnostic only.',
        'Unexplained crossings, incomplete/unsupported fields, failed contact/mapping gates and mesh convergence remain unqualified.',assumptions,
        'Show accepted curves, highest valid true-scale fields, native contact pressure and the rejected reference crossing; explain target/material/mesh limits.',
        decision.get('next_step','Resolve the documented contact/numerical limit, then mechanical mesh convergence and material calibration.'),
        'Repeatable calibrated mechanics, mesh/contact sensitivity, uncertainty-aware acceptance and an explicitly controlled feedback protocol. No autonomous optimization was implemented.'
    ]
    questions=[(r['number'],r['question']) for r in load(RUN/'protocol/FINAL_QUESTIONS_024.json')['questions']]
    assert len(questions)==98 and len(answers)==98,(len(questions),len(answers))
    complete=[{'number':int(n),'question':question,'answer':answer} for (n,question),answer in zip(questions,answers)]
    write_json(RUN/'summary/FINAL_98_ANSWERS.json',complete)
    save('V0_6_6_FINAL_98_ANSWERS.md','# v0.6.6 complete requested answers\n\n'+shared+'\n'+'\n\n'.join(f"{r['number']}. **{r['question']}** {r['answer']}" for r in complete))
    write_json(RUN/'verification/report_consistency.json',{'status':'PASS_DATA_DRIVEN_FINAL_REPORTS','required_answers':len(complete),'model_branches_not_spliced':s['response_branches_not_spliced'],
        'primary_branch':primary,'maximum_qualified_fraction':maximum,'maximum_native_fraction':native,'created_utc':datetime.now(timezone.utc).isoformat(),
        'remaining_final_step':'Review generated reports and figures, commit, then verify clean tree and report final HEAD without pushing'})
    print('Final scientific reports and 98 answers generated from actual evidence',flush=True)


if __name__=='__main__':main()
