"""Assemble numerical evidence without extending computed mechanical curves."""
from pathlib import Path
import csv
import argparse
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import psutil
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import REPO,RUN,BASE,load

BASE_COMMIT='ce6f601da40784621f3324b7e5805983704973b9'


def csv_out(path,rows):
    if not rows:return
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with Path(path).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)


def counts(path):
    suites=list(ET.parse(path).getroot().iter('testsuite'))
    d={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']};d['passed']=d['tests']-d['failures']-d['errors']-d['skipped'];return d


def performance():
    jobs=[];resources=[];fine=[]
    for path in sorted(BASE.glob('*/execution_receipt.json')):
        r=load(path);p=r['process'];samples=p['resource_samples']
        row={'job':path.parent.name,'execution_kind':r['execution_kind'],'status':r['status'],'returncode':p['returncode'],
            'runtime_seconds':p['runtime_seconds'],'peak_tree_RSS_bytes':p['peak_tree_rss_bytes'],'started_utc':p['started_utc'],
            'receipt_sha256':file_hash(path),'native_restart':bool('ANTYPE,STATIC,REST,' in (path.parent/'input.inp').read_text()),
            'accepted_native_substeps':len(r['converged_steps']),
            'native_recorded_artifact_bytes':sum(a['bytes'] for a in p['artifacts'].values()),
            'minimum_sampled_available_RAM_bytes':min([s['available_RAM_bytes'] for s in samples],default=None),
            'maximum_sampled_page_reads_per_second':max([s['page_reads_per_second'] for s in samples if s['page_reads_per_second'] is not None],default=None),
            'severe_paging_samples':sum(s['page_reads_per_second'] is not None and s['page_reads_per_second']>=10000 for s in samples),
            'rss_limit_bytes':p['rss_limit_bytes']}
        if row['job'].startswith('fine_') and r['execution_kind']=='LICENSED_PROGRESSIVE_SOLVE':fine.append(row)
        jobs.append(row)
        # Full samples remain in raw receipt; keep compact scalar CSV for figures/review.
        for s in samples:
            resources.append({'job':path.parent.name,**{k:v for k,v in s.items() if k not in ['output_file_bytes','owned_processes','native_markers_first_observed_seconds']}})
    csv_out(RUN/'performance/jobs.csv',jobs);csv_out(RUN/'performance/resource_samples.csv',resources)
    disk=sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())
    summary={'actual_native_processes':len(jobs),'nonlinear_source_processes':sum(j['execution_kind']=='LICENSED_PROGRESSIVE_SOLVE' for j in jobs),
        'independent_POST1_processes':sum(j['execution_kind']=='INDEPENDENT_READ_ONLY_POST1' for j in jobs),
        'genuine_native_restart_processes':sum(j['native_restart'] for j in jobs),'fine_native_restart_processes':sum(j['native_restart'] for j in fine),
        'sum_native_runtime_seconds':sum(j['runtime_seconds'] for j in jobs),'fine_source_runtime_seconds':sum(j['runtime_seconds'] for j in fine),
        'peak_tree_RSS_bytes':max(j['peak_tree_RSS_bytes'] for j in jobs),'peak_fine_tree_RSS_bytes':max((j['peak_tree_RSS_bytes'] for j in fine),default=0),
        'maximum_page_reads_per_second':max((j['maximum_sampled_page_reads_per_second'] for j in jobs if j['maximum_sampled_page_reads_per_second'] is not None),default=None),
        'severe_paging_samples':sum(j['severe_paging_samples'] for j in jobs),'physical_v066_raw_disk_bytes':disk,
        'disk_scope':'All files in current v066 raw artifact tree, including copied immutable parents and diagnostics; baseline/mesh durable store separate',
        'jobs':jobs,'fixed_RSS_cap':None,'health_criteria':'Registered actual available/committed memory, paging and reserve conditions'}
    write_json(RUN/'performance/PERFORMANCE.json',summary);return summary


def assemble(in_progress=False):
    if not in_progress and any((p.info['name'] or '').lower() in ['ansys.exe','ansys241.exe'] for p in psutil.process_iter(['name'])):raise RuntimeError('Cannot finalize while native ANSYS is active')
    baseline=load(REPO/'experiments/pipeline_v0.6.5/run_001/mechanical_results/qualification.json')
    assert baseline['accepted']
    measurements=[{**baseline['accepted_measurements'][0],'source':'v065 authenticated accepted parent'}]
    snapshots=[{'directory':str(artifact_root()/'solver/v065/full_recovery_001_qualified'),'label':'baseline_000005','engineering_strain':.00005}]
    qualifications=[];all_converged=[];cuts=0;updates=0;failure_jobs=[]
    for path in sorted((RUN/'mechanical_results').glob('fine*_qualification[0-9][0-9][0-9].json')):
        data=load(path)
        revision=path.stem[-3:]
        for i,q in enumerate(data['results'],1):
            qualifications.append(q)
            if q['accepted']:
                measurements.append({**q['measurement'],'source':str(q['source']),'load_step':q['state']['load_step'],'substep':q['state']['substep']})
                snapshots.append({'directory':str(BASE/(Path(q['source']).name+'_qualified'+revision)/f'state{i:03d}'),
                    'label':Path(q['source']).name+f'_state{i:03d}','engineering_strain':q['state']['time']})
    for path in sorted(BASE.glob('fine_stage*/execution_receipt.json')):
        r=load(path)
        if r['execution_kind']!='LICENSED_PROGRESSIVE_SOLVE':continue
        t=load(path.parent/'nonlinear_telemetry.json');all_converged.extend({'job':path.parent.name,**s} for s in t['converged_substeps']);cuts+=len(t['cutback_events']);updates+=len(t['completed_iterations'])
        if r['status']!='PROCESS_EXITED' or r['process']['returncode']!=0:failure_jobs.append({'job':path.parent.name,'status':r['status'],'returncode':r['process']['returncode'],'last_converged':t['converged_substeps'][-1] if t['converged_substeps'] else None})
    # Exact parent state may be independently exported repeatedly: count it once.
    unique={round(m['engineering_compression_strain'],12):m for m in measurements};measurements=[unique[k] for k in sorted(unique)]
    maximum=max(m['engineering_compression_strain'] for m in measurements)
    maximum_converged=max([.00005]+[s['pseudo_time'] for s in all_converged])
    fit_points=[m for m in measurements if .00005-1e-12<=m['engineering_compression_strain']<=.001+1e-12]
    fit={'status':'INSUFFICIENT_POINTS','effective_modulus_MPa':None,'minimum_points':3,'registered_interval':[.00005,.001]}
    if len(fit_points)>=3:
        x=np.array([m['engineering_compression_strain'] for m in fit_points]);y=np.array([m['nominal_compression_stress_MPa'] for m in fit_points]);slope=float(x@y/(x@x));sst=float(np.sum((y-y.mean())**2))
        fit.update(status='PRELIMINARY_SINGLE_MESH_THROUGH_ORIGIN_FIT',effective_modulus_MPa=slope,points=len(x),normalized_modulus=slope/1000,R_squared=1-float(np.sum((y-slope*x)**2))/sst if sst else None)
    for m in measurements:m['secant_modulus_MPa']=m['nominal_compression_stress_MPa']/m['engineering_compression_strain']
    work={'status':'INSUFFICIENT_POINTS','work_N_mm':None}
    if len(measurements)>=3:
        x=np.array([m['compression_displacement_mm'] for m in measurements]);f=-np.array([m['upper_rf_y_N'] for m in measurements]);value=float(np.trapezoid(f,x))
        work={'status':'OBSERVED_INTERVAL_TRAPEZOIDAL_ESTIMATE','work_N_mm':value,'work_J':value*.001,'travel_interval_mm':[float(x[0]),float(x[-1])],
            'points':len(x),'limitation':'Only accepted sampled forces on observed interval; sparse quadrature is not an energy/dissipation convergence study. No origin extrapolation.'}
    statuses={'A_GEOMETRY_AUTHENTICATED':'PASS','B_MESH_QUALIFIED':'PASS_ORIGINAL_FINE_GATES','C_RESTART_VERIFIED':'PASS_ACTUAL_LICENSED',
        'D_MULTI_POINT_OUTPUT_VERIFIED':'PASS_ACTUAL_LICENSED','E_PLATEN_CONTACT_QUALIFIED':'PASS_ACCEPTED_STATES',
        'F_INTERNAL_CONTACT_IMPLEMENTED':'SMALL_FIXTURE_ONLY; FULL_MICROSTRUCTURE_NOT_CONFIGURED',
        'G_INTERNAL_CONTACT_DEMONSTRATED':'SMALL_FIXTURE_ONLY' if (RUN/'internal_contact/QUALIFIED_SHORT_GAP.json').exists() and load(RUN/'internal_contact/QUALIFIED_SHORT_GAP.json')['status']=='PASS_SMALL_NATIVE_INTERNAL_CONTACT_ONLY' else 'PENDING_OR_HOLD',
        'H_INTERNAL_OVERLAP_SCREENED':'PASS_BOUNDED_SCREEN_ACCEPTED_STATES','I_PROGRESSIVE_COMPRESSION_EXECUTED':'PASS' if maximum>.00005 else 'HOLD'}
    for letter,target,name in [('J',.01,'FIRST_ONE_PERCENT'),('K',.05,'FIRST_FIVE_PERCENT'),('L',.1,'FIRST_TEN_PERCENT'),('M',.2,'FIRST_TWENTY_PERCENT'),('N',.3,'THIRTY_PERCENT_TARGET'),('O',.4,'FORTY_PERCENT_STRETCH')]:statuses[letter+'_'+name]='ACHIEVED_VALIDLY' if maximum>=target-1e-12 else 'NOT_ACHIEVED'
    statuses.update(P_MULTI_POINT_STRESS_STRAIN='PASS' if len(measurements)>1 else 'INSUFFICIENT_POINTS',Q_DEFORMATION_FIELDS='PASS_ACTUAL_NATIVE_FIELDS',R_MECHANICAL_MESH_CONVERGENCE='UNQUALIFIED',S_MATERIAL_CALIBRATION='UNQUALIFIED',T_PAPER_READINESS='RESEARCH_HOLD',U_LLM_OPTIMIZATION='NOT_IMPLEMENTED')
    perf=performance();active=counts(RUN/'verification/active.xml');archives=[counts(p) for p in (RUN/'verification/archive_replay').glob('*.xml')]
    licensed=counts(RUN/'verification/licensed_final.xml') if (RUN/'verification/licensed_final.xml').exists() else counts(RUN/'verification/licensed_stage01.xml')
    protected=['experiments/pipeline_v0.5','experiments/pipeline_v0.6','experiments/pipeline_v0.6.1','experiments/pipeline_v0.6.2','experiments/pipeline_v0.6.3','experiments/pipeline_v0.6.4','experiments/pipeline_v0.6.5','metamaterial_eval/generators','validation/evaluators','data']
    changed=subprocess.check_output(['git','diff','--name-only',BASE_COMMIT,'--',*protected],text=True);assert not changed
    commits=subprocess.check_output(['git','log','--reverse','--format=%H %s',BASE_COMMIT+'..HEAD'],text=True).splitlines()
    summary={'schema':'young-dawgs-v0.6.6-validation','status':'IN_PROGRESS_COMPLETED_JOBS_ONLY' if in_progress else ('PROGRESSIVE_FINE_MESH_RESEARCH_HOLD__TARGET_REACHED' if maximum>=.3 else 'PROGRESSIVE_FINE_MESH_RESEARCH_HOLD__TARGET_NOT_REACHED'),
        'maximum_qualified_engineering_strain':maximum,'maximum_actual_Newton_converged_engineering_strain':maximum_converged,
        'accepted_measurements':measurements,'accepted_point_count':len(measurements),'new_fine_converged_substeps':len(all_converged),'native_cutback_events':cuts,'completed_Newton_updates':updates,
        'actual_fine_converged_states':all_converged,'failed_fine_jobs':failure_jobs,'qualifications':qualifications,'snapshot_artifacts':snapshots,
        'initial_modulus_fit':fit,'compression_work':work,'independent_acceptance':statuses,'performance':perf,
        'tests':{'active':active,'archived_passed':sum(c['passed'] for c in archives),'archive_groups':len(archives),'licensed':licensed,'counts_overlap_do_not_sum':True},
        'protected_historical_files_unchanged':True,'base_commit':BASE_COMMIT,'commits_before_containing_report_commit':commits,
        'material':'Provisional linear-elastic E1000MPa,nu0.3,plane stress,t1mm. Native local elastic strains tracked; no calibrated polymer/yield/fracture model.',
        'contact_scope':'Main fine continuation remains PLATEN_ONLY_EXPLORATORY; no unmodeled pore-wall crossings accepted',
        'no_automatic_push':True,'no_3D_batch_or_LLM_optimization':True}
    write_json(RUN/'summary/V0_6_6_VALIDATION.json',summary)
    csv_out(RUN/'mechanical_results/accepted_force_displacement_stress_strain.csv',measurements)
    csv_out(RUN/'summary/independent_acceptance.csv',[{'category':k,'status':v} for k,v in statuses.items()])
    csv_out(RUN/'progressive_compression/converged_native_states.csv',all_converged)
    write_json(RUN/'verification/historical_preservation.json',{'base_commit':BASE_COMMIT,'paths':protected,'git_diff_name_only':changed,'passed':not changed})
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--in-progress',action='store_true');a=p.parse_args()
    q=assemble(a.in_progress);print(q['status'],q['maximum_qualified_engineering_strain'],q['accepted_point_count'])
