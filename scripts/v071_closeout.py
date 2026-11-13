"""Close the completed native study; verify evidence and freeze the handoff package."""
from datetime import datetime,timezone
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET
from scripts.v071_register import RUN,BASE,DOC
from scripts.v070_protocol import read,write,sha,REPO
from metamaterial_eval.simulation.solver_execution import file_hash


def xml_counts(paths):
    total=failures=errors=skipped=0
    for path in paths:
        root=ET.parse(path).getroot();suites=[root] if root.tag=='testsuite' else list(root)
        for s in suites:
            total+=int(s.get('tests',0));failures+=int(s.get('failures',0));errors+=int(s.get('errors',0));skipped+=int(s.get('skipped',0))
    return {'tests':total,'failures':failures,'errors':errors,'skipped':skipped}


def closeout():
    assert not (RUN/'summary/FINAL_PACKAGE_HASHES.json').exists(),'Frozen closeout already exists'
    protocol=read(RUN/'protocol/PROTOCOL.json');protected=read(RUN/'audit/PROTECTED_AFTER.json')
    assert protected['status']=='PASS' and protected['files_checked']==16294
    response_files=sorted((RUN/'mechanical_response').glob('*.json'));responses=[read(p) for p in response_files]
    accepted=[r for r in responses if r['accepted']];rejected=[r for r in responses if not r['accepted']]
    assert len(accepted)==14 and len(rejected)==1 and rejected[0]['specimen_id']=='M1_equal'
    native_hash_count=0
    for p in (RUN/'native_result_manifests').glob('*/NATIVE_ARTIFACTS.json'):
        for name,record in read(p).items():
            assert file_hash(record['path'])==record['sha256'],record['path'];native_hash_count+=1
    for r in accepted:
        assert all(r['checks'].values()) and len(r['engineering_strains'])==5
        assert file_hash(Path(r['source_directory'])/'elastic.rst')==r['native_result_sha256']
    figures=read(RUN/'figures/FIGURE_MANIFEST.json');accepted_hashes={r['native_result_sha256'] for r in accepted}
    for f in figures:
        assert sha(REPO/f['path'])==f['sha256']
        assert set(f['source_native_RST_hashes'])<=accepted_hashes
    tests={name:xml_counts(paths) for name,paths in {
        'active':[RUN/'verification/active_tests.xml'],
        'archived_replays':list((RUN/'verification/archive_replay').glob('*.xml')),
        'historical_licensed_artifacts':[RUN/'verification/historical_licensed_checks.xml'],
        'v071_licensed_artifacts':[RUN/'verification/v071_licensed_checks.xml']}.items()}
    assert all(t['failures']==t['errors']==t['skipped']==0 for t in tests.values())
    assert tests['active']['tests']==896 and tests['v071_licensed_artifacts']['tests']==26
    performance=read(RUN/'performance/SUMMARY.json');assert performance['native_processes']==32
    pair=read(RUN/'paired_feedback_comparison/COMPARISON.json')
    joint=read(RUN/'morphology_mechanics/JOINT_RESULTS.json');mesh=read(RUN/'mesh_sensitivity/COMPARISON.json')
    status={key:'PASS_VERIFIED' for key in [
        'V070_REFERENCE_DATA_PRESERVED','V070_LLM_SCRIPTS_PRESERVED','V070_HELDOUT_OUTPUTS_PRESERVED',
        'P3_SOURCE_AUTHENTICATED','STRUCTURED_MESH_QUALIFIED','MATERIAL_ASSIGNMENT_VERIFIED','BONDED_INTERFACE_TOPOLOGY_VERIFIED',
        'HOMOGENEOUS_ANALYTICAL_BENCHMARK','TWO_PHASE_PARALLEL_BENCHMARK','TWO_PHASE_SERIES_BENCHMARK','EQUAL_MATERIAL_CONTROL',
        'BOUNDARY_CONDITIONS_VERIFIED','REACTION_EXTRACTION_VERIFIED','STRAIN_ENERGY_VERIFIED','P3_REFERENCE_NATIVE_SOLVE',
        'P3_REFERENCE_STRESS_STRAIN','P3_REFERENCE_EFFECTIVE_MODULUS','P3_A01_MECHANICALLY_EVALUATED',
        'P3_B02_MECHANICALLY_EVALUATED','P3_C02_R1_MECHANICALLY_EVALUATED','P3_C02_PAIRED_MECHANICAL_COMPARISON',
        'P3_PHASE_STRESS_FIELDS','P3_REFERENCE_RELATIVE_MECHANICAL_COMPARISON']}
    status.update(HISTORICAL_POROUS_MECHANICS_PRESERVED='PASS_TRACKED_HASHES_AND23_APPLICABLE_NATIVE_ARTIFACT_CHECKS__NO_NEW_HISTORICAL_SOLVES',
        P3_PHASE_SEMANTICS_VERIFIED='PASS_TWO_SOLID_MECHANICAL_MAPPING__PHASE5_CHEMISTRY_PROVISIONAL',
        P3_REFERENCE_MESH_SENSITIVITY='PASS_PRELIMINARY_H1_H2_2PERCENT_GATE',
        MORPHOLOGY_MECHANICS_LINK_ESTABLISHED='EXPLORATORY_EXACT_SEED_NATIVE_ASSOCIATION__NO_CAUSAL_OR_POPULATION_CLAIM',
        MECHANICAL_MESH_CONVERGENCE='PRELIMINARY_TWO_LEVEL_SENSITIVITY_ONLY__ASYMPTOTIC_CONVERGENCE_NOT_QUALIFIED',
        PHYSICAL_MATERIAL_CALIBRATION='NOT_CALIBRATED',REPRESENTATIVE_VOLUME_QUALIFICATION='NOT_QUALIFIED',
        F1_MECHANICS='NOT_RUN_DEFERRED',MECHANICAL_FEEDBACK_SCHEMA='FROZEN_AND_POPULATED_WITH_ACTUAL_RESULTS__FUTURE_FEEDBACK_SCHEMA_ONLY',
        LLM_MECHANICAL_FEEDBACK_EXECUTED='NOT_RUN',LLM_MECHANICAL_OPTIMIZATION='NOT_IMPLEMENTED',
        PAPER_READINESS='EXPLORATORY_NUMERICAL_BENCHMARK_ONLY__NO_CALIBRATED_MATERIAL_OR_POPULATION_CLAIMS')
    overall='QUALIFIED_EXPLORATORY_P3_TWO_SOLID_ELASTIC_BENCHMARK__ILLUSTRATIVE_MATERIALS__PRELIMINARY_MESH_SENSITIVITY__NO_CALIBRATION_RVE_OR_OPTIMIZATION'
    write(RUN/'summary/SCIENTIFIC_STATUS.json',{'overall':overall,'independent_statuses':status})
    write(RUN/'verification/FINAL_INTEGRITY.json',{'checked_utc':datetime.now(timezone.utc).isoformat(),'native_artifact_hashes_verified':native_hash_count,
        'accepted_native_source_models':14,'rejected_native_source_models':1,'accepted_actual_native_result_sets':70,
        'exact_selected_source_arrays':5,'generated_seed':0,'figure_hashes_verified':len(figures),'protected_tracked_files_unchanged':16294,
        'test_results':tests,'archived_replay_groups':9,'archive_counts_are_replays_not_additional_unique_tests':True,
        'native_calls':32,'source_solves':15,'independent_readback_processes':17,
        'failed_attempts_preserved':['M1_equal_H1_attempt001','Python result boolean serialization diagnostic'],
        'raw_binaries_outside_Git':True,'all_inputs_and_outputs_authentic':True,'new_historical_contact_jobs':0,'push':False})
    validation=f'''# Validation and scientific acceptance

| Verification | Passed | Scope |
|---|---:|---|
| Active software suite | {tests['active']['tests']} | Includes 11 new phase/mesh/boundary regression checks |
| Archived geometry replays | {tests['archived_replays']['tests']} | Nine original groups; replay counts are not new unique tests |
| Historical licensed artifacts | {tests['historical_licensed_artifacts']['tests']} | Read-only checks of retained v0.6.10 evidence; no old solver campaign restarted |
| New licensed artifacts | {tests['v071_licensed_artifacts']['tests']} | Real RST/DB hashes, connectivity, analytical controls, exact phases, readback and budget |

All groups have zero failures, errors or skips. Native execution comprised 15 source solves and 17 separate read-only processes, within the 32-call limit. Fourteen source models passed all mechanical gates, providing 70 actual accepted native load checkpoints. The first equal-material dense-grid model was rejected, preserved, diagnosed and recovered using exact boundary node IDs. A result-serialization issue was corrected using already saved native data. No failed result was substituted for an accepted result.

The source RSTs were reopened independently; the reference was reopened twice with byte-identical curve, displacement, stress/strain and connectivity exports. Native coordinates, material IDs, every quadrilateral connectivity entry and complete constraint inventories match the intended meshes. Reactions, signed displacements, plane-stress constitutive relations, engineering shear, volume-mean stress and energy checks pass. Native element-averaged fields remain phase associated; they are not globally averaged nodal stresses or physical failure predictions.

The local 2024 R1 installation did not contain a PLANE182 element manual, and the exact R1 online manual was not retrievable. The [official adjacent-release element reference](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_PLANE182.html) and [ETABLE reference](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_ETABLE.html) informed the implementation. Actual R1 ETLIST/RLIST/MPLIST and the licensed analytical/constitutive controls corroborate the executed options and behavior. This documentation limitation is retained explicitly.

All 16,294 previously tracked files authenticate unchanged. This includes the P3/F1 originals and annotations, frozen LLM scripts, 320 prior generated arrays, morphology scores and historical porous research. Raw native files remain under `{BASE}`. No RST was copied for independent readback. Critical native artifacts authenticate against recorded hashes; all ten figure files authenticate against their native provenance manifests.

Supervised native wall time summed across jobs: {performance['total_supervised_native_seconds']:.3f}s ({performance['total_supervised_native_seconds']/60:.3f}min). Peak single-process-tree RSS: {performance['peak_single_process_tree_RSS_bytes']/2**30:.3f}GiB. Minimum observed available RAM: {performance['minimum_available_RAM_bytes']/2**30:.3f}GiB. Raw artifact storage: {performance['raw_artifact_bytes']/2**30:.3f}GiB. One native job ran at a time with two cores, existing system-health supervision and no fixed RSS cap. Paging counters are system hard-fault disk-read proxies, not pagefile-only or per-solver measurements. Full samples and commit/paging availability are retained in process receipts.

Independent acceptance statuses are recorded below. A useful numerical milestone does not imply material calibration, representative volume qualification, asymptotic convergence or optimization.

| Scientific status | Outcome |
|---|---|
'''
    validation+=''.join(f'| {key} | {value} |\n' for key,value in status.items())
    (DOC/'V0_7_1_VALIDATION.md').write_text(validation,encoding='utf-8',newline='\n')
    table='| Specimen, saved held-out seed 0 | H1 modulus (MPa) | Signed reference error |\n|---|---:|---:|\n'
    for r in joint:table+=f"| {r['specimen_id']} | {r['effective_modulus_MPa']:.3f} | {100*r['signed_reference_relative_error']:+.4f}% |\n"
    handoff=f'''# v0.7.1 research handoff

Completed a native-solver-verified P3 morphology-to-mechanics study in `{REPO}`, branch master, starting HEAD `{protocol['starting_head']}`. All previous v0.7.0 and porous research is preserved. No nonlinear contact work, high-strain campaign, F1 mechanical solve or LLM mechanical optimization was performed.

The exact P3 reference and saved P3_A_01/r0, P3_B_02/r0, P3_C_02/r1 and paired P3_C_02/r0 seed 0 arrays were authenticated before mechanics. Native labels 1/5 map to two solid materials. H1 has 65,536 elements and 66,049 nodes; H2 has 262,144 and 263,169. Each actual native material and connectivity entry matches the source; both levels preserve phase fractions exactly and share interface nodes. Image row 0 remains at the physical top.

The illustrative computational square is 1mm by 1mm with 1mm thickness in mm–N–MPa units; it is not a microscopy calibration. PLANE182 uses KEYOPT(1)=0, KEYOPT(3)=3, KEYOPT(6)=0, small-strain linear static analysis and NLGEOM OFF. E=1000/10000MPa, nu=0.30 are idealized matrix-like/reinforcement-like values. Boundaries impose bottom UY=0, five actual top displacements through0.5%, and one bottom-left UX pin, with free lateral motion. These are finite-domain apparent stiffnesses, not RVE homogenized properties.

Homogeneous, parallel-layer, series-layer and equal-material controls pass against1000,5500,1818.181818 and1000MPa respectively. The layered analytical controls use nu=0 only as an explicit benchmark simplification. Source logs, native inventories, independent RST reopening, reaction equilibrium, stress/strain fields, strain energy, mesh topology and complete constraint inventories all qualify. The initially failed dense-grid boundary selection and its recovery are preserved.

{table}

Reference H2 modulus is1682.117418MPa; the H1/H2 change is0.664115%, below the prospectively registered2% gate. All four generated H2 checks pass the same preliminary sensitivity threshold. B02 is the closest selected specimen on both levels, but its difference from the reference is smaller than observed mesh changes. Initial C02/reference agreement is also numerically unresolved under the conservative sensitivity diagnostic. Two levels do not prove asymptotic convergence or sufficient physical image resolution.

The C02 revision raises H1 modulus by{pair['signed_modulus_change_MPa']:.6f}MPa. Its observed absolute stiffness error changes from1.0088% to1.7926% on H1, and from0.8667% to1.8693% on H2. For this exact seed, visible morphology error worsens and hidden error improves; ten-seed means are kept distinct. The observed mechanical-agreement worsening is exploratory, and the error-change magnitude is not certified relative to the conservative mesh-change diagnostic. No causal or condition-average benefit or harm is claimed. Composition varies, and pairing does not imply identical particle identities.

Actual five-point stress–strain/force–displacement curves, shared-scale axial/equivalent stress fields, native nodal displacement components, true-scale deformed geometry, phase load sharing and mesh comparisons are in the figures and machine-readable tables. At0.5%, reference phase-average SYY is approximately−6.783MPa in the matrix and−12.105MPa in reinforcement. Robust percentiles and energy shares are retained; mesh-sensitive maxima are exploratory and imply no yielding or fracture.

P3 phase5 chemistry remains provisional; its supplied HorizontalFlip source and morphology-selection bias remain disclosed. F1 is preserved with matrix0/fiber1/void2 and transverse circle-annotation uncertainty. All physical calibration, representative-volume and experimental-validation claims remain unqualified. Actual mechanics input/output contracts and a future-only feedback schema are frozen and populated. No mechanical measurements were sent to an LLM. A future v0.7.2 can prospectively expand controlled realizations and test a target normalized modulus at fixed reinforcement fraction with new held-out seeds and an equal-attempt control.

Validation:896 active tests,475 archived replay checks across nine groups,23 historical licensed-artifact checks and26 new licensed-artifact checks passed. All16,294 pre-existing tracked files are unchanged. There were32 native processes (15 solves,17 readbacks),14 accepted source models and one preserved rejected source model. Supervised native time was{performance['total_supervised_native_seconds']/60:.3f}min; peak RSS{performance['peak_single_process_tree_RSS_bytes']/2**30:.3f}GiB; raw artifacts{performance['raw_artifact_bytes']/2**30:.3f}GiB outside Git. No push was performed.

Raw artifact root: `{BASE}`. Compact source/field hashes, material/mesh identities, actual checkpoint data and acceptance records are in `experiments/pipeline_v0.7.1/run_001`. Reproduction must use a new registered native run/budget; existing destinations deliberately reject overwrites. Read-only verification is `python -m pytest validation/ansys_v071_integration.py -q`; active tests require `EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py`. Protocol, analytical controls, detailed results, morphology analysis, future contracts and validation have separate reports in this directory.

Scientific status: **{overall}**. Stop this milestone here.
'''
    for old,new in [('1mm','1 mm'),('through0.5%','through 0.5%'),('against1000,5500,1818.181818 and1000MPa','against 1000, 5500, 1818.181818 and 1000 MPa'),('is1682.117418MPa','is 1682.117418 MPa'),('is0.664115%','is 0.664115%'),('registered2%','registered 2%'),('from1.0088% to1.7926%','from 1.0088% to 1.7926%'),('from0.8667% to1.8693%','from 0.8667% to 1.8693%'),('phase5','phase 5'),('At0.5%','At 0.5%'),('approximately−6.783MPa','approximately −6.783 MPa'),('and−12.105MPa','and −12.105 MPa'),('Validation:896','Validation: 896'),('tests,475','tests, 475'),('groups,23','groups, 23'),('and26','and 26'),('All16,294','All 16,294'),('were32','were 32'),('(15 solves,17','(15 solves, 17'),('),14', '), 14'),('E=1000/10000MPa','E = 1000/10000 MPa'),('nu=0.30','nu = 0.30')]:handoff=handoff.replace(old,new)
    (DOC/'V0_7_1_HANDOFF.md').write_text(handoff,encoding='utf-8',newline='\n')
    (DOC/'DR_WANG_SUMMARY.md').write_text('''# Research summary for Dr. Wang

The real-microscopy LLM pilot generated P3 and F1 microstructures from independently returned procedural scripts. We have now connected the selected P3 geometries to a verified two-phase mechanical workflow in licensed ANSYS.

Both P3 phases are solid materials with shared nodes and ideal bonded interfaces. Homogeneous, parallel-layer, series-layer and equal-material controls matched their analytical elastic responses. We obtained five actual stress–strain checkpoints through 0.5% compression for the reference and selected generated specimens, independently reopened the native results, and compared effective stiffness and phase stress distributions.

Using illustrative matrix/reinforcement moduli of 1000/10000 MPa, the reference apparent modulus was 1693.29 MPa. The selected image-only, descriptor-informed and revised-feedback examples gave 1739.04, 1691.41 and 1723.64 MPa. The descriptor-informed example was closest, although its small difference is below observed mesh sensitivity. The same-parent initial C02 example gave 1676.21 MPa; the revision's measured stiffness error increased on both mesh levels. That is an exploratory observation, not a causal conclusion, and the exact-seed morphology results differ from the previous script-average trend.

The study shows that generated geometry can be mechanically evaluated reliably and that morphology scores alone do not establish mechanical agreement. The material values are numerical assumptions, not calibrated Ni–WC properties; the selected augmented crop is not an RVE. A logical next step is a controlled multi-realization mechanical dataset followed by a registered LLM mechanical-feedback experiment at fixed composition, with independent evaluation seeds and a suitable control. No optimization or new high-strain contact campaign was performed here.
''',encoding='utf-8',newline='\n')
    log=subprocess.check_output(['git','log','--reverse','--format=%H %s',protocol['starting_head']+'..HEAD'],cwd=REPO,text=True)
    (DOC/'COMMITS.md').write_text('# v0.7.1 implementation commits\n\nFull hashes and exact messages through the analysis/contract commit are recorded below. The final documentation commit follows this sequence and is identified in the delivered handoff message. Nothing was pushed.\n\n'+''.join('- '+line+'\n' for line in log.splitlines()),encoding='utf-8',newline='\n')
    changed=set(subprocess.check_output(['git','diff','--name-status',protocol['starting_head']],cwd=REPO,text=True).splitlines())
    pending=subprocess.check_output(['git','ls-files','--others','--exclude-standard','-z'],cwd=REPO).decode().split('\0')
    changed.update('A\t'+name for name in pending if name)
    changed.update('A\t'+str((RUN/'summary'/name).relative_to(REPO)).replace('\\','/') for name in ['FILES_CREATED_OR_MODIFIED.txt','FINAL_PACKAGE_HASHES.json'])
    (RUN/'summary/FILES_CREATED_OR_MODIFIED.txt').write_text('\n'.join(sorted(changed))+'\n',encoding='utf-8',newline='\n')
    files={}
    for root in [RUN,DOC]:
        for p in root.rglob('*'):
            if p.is_file():files[str(p.relative_to(REPO)).replace('\\','/')]=sha(p)
    for name in ['scripts/v071_register.py','scripts/v071_mechanics.py','scripts/v071_report.py','scripts/v071_closeout.py',
                 'metamaterial_eval/simulation/composite_elastic.py','tests/test_v071_elastic_mesh.py','validation/ansys_v071_integration.py']:
        files[name]=sha(REPO/name)
    write(RUN/'summary/FINAL_PACKAGE_HASHES.json',{'frozen_utc':datetime.now(timezone.utc).isoformat(),'scientific_status':overall,
          'analysis_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'files':files,
          'native_files_bound_separately':'native_result_manifests/*/NATIVE_ARTIFACTS.json and original process receipts',
          'no_further_solver_or_feedback_jobs':True,'push':False})
    print('CLOSED',overall,'native hashes verified',native_hash_count,'package files frozen',len(files),flush=True)


if __name__=='__main__':closeout()
