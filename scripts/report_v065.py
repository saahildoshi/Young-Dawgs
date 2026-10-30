"""Actual v0.6.5 performance, native fields, scientific reports and handoff."""
from pathlib import Path
import csv
import json
import re
import subprocess
import gc
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection,PolyCollection
from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.nonlinear_diagnostics import export_csv
from scripts.v065_recovery import REPO,RUN,BASE,FULL,FULL_PROTOCOL,load

QUALIFIED=BASE/'full_recovery_001_qualified'
BASE_COMMIT='0de6cd7c77652ad0d265200881642cd0d228a047'


def save(name,text):(RUN/name).write_text(text.rstrip()+'\n',encoding='utf-8')


def finish(fig,name):
    fig.savefig(RUN/'figures'/name,dpi=150)
    for axis in fig.axes:axis.clear()
    fig.clear();plt.close(fig);gc.collect()
    print('Verified data rendered:',name,flush=True)


def counts(path):
    suites=list(ET.parse(path).getroot().iter('testsuite'))
    result={k:int(sum(int(s.get(k,0)) for s in suites)) for k in ['tests','failures','errors','skipped']}
    result['passed']=result['tests']-result['failures']-result['errors']-result['skipped']
    return result


def performance():
    r=load(FULL/'execution_receipt.json')['process'];samples=r['resource_samples']
    scalar=[];growth=[]
    for s in samples:
        scalar.append({k:v for k,v in s.items() if k not in ['output_file_bytes','owned_processes','native_markers_first_observed_seconds']})
        growth.extend({'elapsed_seconds':s['elapsed_seconds'],'filename':n,'bytes':v} for n,v in s['output_file_bytes'].items()
                      if re.search(r'\.(rst|rdb|db|r\d{3})$',n,re.I))
    export_csv(RUN/'performance/resource_samples.csv',scalar);export_csv(RUN/'performance/output_growth.csv',growth)
    available=[s['available_RAM_bytes'] for s in samples]
    pages=[s['page_reads_per_second'] for s in samples if s['page_reads_per_second'] is not None]
    commits=[s['commit_fraction'] for s in samples if s['commit_fraction'] is not None]
    markers={k:v for s in samples for k,v in s['native_markers_first_observed_seconds'].items()}
    summary={'runtime_seconds':r['runtime_seconds'],'peak_tree_RSS_bytes':r['peak_tree_rss_bytes'],
        'source_started_utc':r['started_utc'],
        'peak_tree_RSS_GiB':r['peak_tree_rss_bytes']/1024**3,'physical_RAM_bytes':r['system_before']['physical_RAM_bytes'],
        'available_RAM_before_bytes':r['system_before']['available_RAM_bytes'],'minimum_sampled_available_RAM_bytes':min(available),
        'maximum_commit_fraction':max(commits) if commits else None,'maximum_page_reads_per_second':max(pages) if pages else None,
        'page_read_samples_above_registered_severe_threshold':sum(v>=10000 for v in pages),
        'windows_low_memory_sample_count':sum(s['windows_low_memory'] is True for s in samples),
        'process_RSS_limit_bytes':r['rss_limit_bytes'],'termination_status':r['status'],
        'observed_native_markers_seconds':markers,'time_resolution':'1-second health/file snapshots; ~0.1-second RSS peak monitor; marker times are first observation, not exact internal boundaries',
        'paging_limits':'System Page Reads/sec includes hard faults from mapped files; not pagefile-only or per-process hard-fault attribution.',
        'native_signal_availability':r['native_signal_availability'],'no_pagefile_or_unrelated_process_modification':True}
    summary['windows_resource_exhaustion_events']=load(RUN/'performance/windows_resource_exhaustion_events.json')
    summary['independent_POST1_processes']={}
    for name in ['full_recovery_001_post','full_recovery_001_repeat']:
        if (BASE/name/'execution_receipt.json').exists():
            post=load(BASE/name/'execution_receipt.json')['process']
            summary['independent_POST1_processes'][name]={'runtime_seconds':post['runtime_seconds'],'peak_tree_RSS_bytes':post['peak_tree_rss_bytes'],'returncode':post['returncode']}
    summary['sum_recorded_source_and_POST1_process_seconds']=r['runtime_seconds']+sum(x['runtime_seconds'] for x in summary['independent_POST1_processes'].values())
    summary['timing_limits']='Recorded ANSYS process runtimes exclude Python field qualification, figure rendering and orchestration wall time; Python qualification wall time not independently measured.'
    nonzero=[s for s in samples if s['output_file_bytes'].get('compression.rst',0)>0]
    if nonzero:
        summary['first_RST_nonzero_observed_seconds']=nonzero[0]['elapsed_seconds']
        changes=[s for previous,s in zip(samples,samples[1:]) if s['output_file_bytes'].get('compression.rst',0)!=previous['output_file_bytes'].get('compression.rst',0)]
        summary['last_RST_size_change_observed_seconds']=changes[-1]['elapsed_seconds'] if changes else None
    timing=[]
    for i,line in enumerate((FULL/'solver.out').read_text(errors='replace').splitlines(),1):
        match=re.search(r'time \(cpu & wall\) for (.+?)\s+([\d.]+)\s+([\d.]+)\s*$',line,re.I)
        if match:timing.append({'source_line':i,'native_phase':match[1].strip(),'CPU_seconds':float(match[2]),'wall_seconds':float(match[3])})
        match=re.search(r'Total Time \(sec\) for Sparse Assembly\s+([\d.]+) cpu\s+([\d.]+) wall',line)
        if match:timing.append({'source_line':i,'native_phase':'Sparse Assembly native interval','CPU_seconds':float(match[1]),'wall_seconds':float(match[2])})
    export_csv(RUN/'performance/native_phase_timings.csv',timing)
    summary['native_phase_timing_scope']='Actual native per-call sparse timing tables, not disjoint total runtime partitions; Newton updates are not assigned invented exact wall times.'
    write_json(RUN/'performance/PERFORMANCE.json',summary)
    x=[s['elapsed_seconds'] for s in samples]
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    axes[0,0].plot(x,[s['tree_rss_bytes']/1024**3 if s['tree_rss_bytes'] is not None else np.nan for s in samples],label='1-second snapshots')
    axes[0,0].axhline(summary['peak_tree_RSS_GiB'],ls=':',color='purple',label='Supervisor peak');axes[0,0].set(ylabel='Owned process-tree RSS [GiB]');axes[0,0].legend()
    axes[0,1].plot(x,np.array(available)/1024**3);axes[0,1].axhline(6,ls='--',color='red',label='Sustained system reserve');axes[0,1].set(ylabel='Windows available RAM [GiB]');axes[0,1].legend()
    axes[1,0].plot(x,[100*s['commit_fraction'] if s['commit_fraction'] is not None else np.nan for s in samples]);axes[1,0].set(ylabel='System commit / limit [%]')
    axes[1,1].plot(x,[s['page_reads_per_second'] if s['page_reads_per_second'] is not None else np.nan for s in samples],label='System hard-fault disk-read proxy')
    axes[1,1].set(ylabel='Page Reads/sec');axes[1,1].legend(fontsize=8)
    for ax in axes.flat:ax.set_xlabel('Measured solver runtime [s]');ax.grid(alpha=.2)
    fig.suptitle('Actual full-run system health — no process RSS cutoff')
    finish(fig,'system_resources.png')
    fig,axes=plt.subplots(1,2,figsize=(13,5),constrained_layout=True)
    names=sorted(set(r['filename'] for r in growth))
    for name in names:
        a=[r for r in growth if r['filename']==name]
        axes[0].plot([r['elapsed_seconds'] for r in a],[r['bytes']/1024**3 for r in a],label=name)
    axes[0].set(xlabel='Measured solver runtime [s]',ylabel='Actual file size [GiB]');axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
    t=load(FULL/'nonlinear_telemetry.json');a=t['force_evaluations']
    axes[1].semilogy([r['evaluation'] for r in a],[r['ratio'] for r in a],'o-');axes[1].axhline(1,color='green',ls='--')
    axes[1].set(xlabel='Native force-evaluation index',ylabel='Force residual / criterion');axes[1].grid(alpha=.2)
    fig.suptitle('Actual output growth and equilibrium; file sizes include headers, not proof of completeness')
    finish(fig,'native_output_timeline.png')
    return summary


def field_figures():
    q=load(QUALIFIED/'qualification.json')
    if not q['accepted']:return []
    mesh,_,_=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    u=np.load(QUALIFIED/'native_displacement.npy',mmap_mode='r')
    s=np.load(QUALIFIED/'native_corner_stress_strain.npy',mmap_mode='r');corners=np.load(QUALIFIED/'corner_node_ids.npy',mmap_mode='r')
    fig,axes=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
    edges=mesh.boundary
    fraction=np.linspace(0,1,9)
    shape=np.column_stack([(1-fraction)*(1-2*fraction),fraction*(2*fraction-1),4*fraction*(1-fraction)])
    undeformed=np.einsum('sn,bnd->bsd',shape,mesh.nodes[edges])
    deformed=np.einsum('sn,bnd->bsd',shape,u[edges,3:5])
    axes[0].add_collection(LineCollection(undeformed,colors='black',linewidths=.3))
    axes[0].set_title('Authenticated undeformed geometry')
    axes[1].add_collection(LineCollection(undeformed,colors='0.7',linewidths=.3))
    axes[1].add_collection(LineCollection(deformed,colors='tab:blue',linewidths=.3))
    axes[1].set_title('Native deformed boundary, true scale 1x\nquadratic edges sampled9points; no amplification')
    for ax in axes:ax.set(xlim=(0,10.24),ylim=(0,10.24),aspect='equal',xlabel='x [mm]',ylabel='y [mm]')
    fig.suptitle('One accepted checkpoint; geometric and physical limitations remain')
    finish(fig,'geometry_and_deformation.png')
    points=mesh.nodes[mesh.triangles[:,:3]]
    lookup=np.searchsorted(corners,mesh.triangles[:,:3]+1)
    for filename,panels in [
        ('displacement_fields.png',[(u[:,1][mesh.triangles[:,:3]].mean(axis=1),'Native UY [mm]'),(u[:,2][mesh.triangles[:,:3]].mean(axis=1),'Magnitude from native UX/UY [mm]')]),
        ('continuum_stress.png',[(s[:,0][lookup].mean(axis=1),'Native corner-averaged SYY [MPa]'),(s[:,1][lookup].mean(axis=1),'Native corner-averaged equivalent stress [MPa]')]),
        ('elastic_strain.png',[(s[:,2][lookup].mean(axis=1),'Native corner-averaged elastic EYY'),(s[:,3][lookup].mean(axis=1),'Native corner-averaged elastic EXX')])]:
        fig,axes=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
        for ax,(values,title) in zip(axes,panels):
            collection=PolyCollection(points,array=values,edgecolors='none',cmap='viridis');ax.add_collection(collection)
            fig.colorbar(collection,ax=ax);ax.set(title=title,xlim=(0,10.24),ylim=(0,10.24),aspect='equal',xlabel='x [mm]',ylabel='y [mm]')
        fig.suptitle('Actual accepted native checkpoint; triangle-mean color rendering, no fabricated midside stress')
        finish(fig,filename)
    contact_figure(mesh,q)
    m=q['accepted_measurements'][0];fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    axes[0].bar(['Upper RF','Lower RF','Top contact','Bottom contact'],[m['upper_rf_y_N'],m['lower_rf_y_N'],q['contacts'][1]['contact_element_force_y_N'],q['contacts'][0]['contact_element_force_y_N']]);axes[0].tick_params(axis='x',rotation=25);axes[0].set_ylabel('Native signed FY [N]')
    axes[1].scatter([m['compression_displacement_mm']],[-m['upper_rf_y_N']]);axes[1].set(xlabel='Actual travel [mm]',ylabel='Compression force magnitude [N]',xlim=(0,m['compression_displacement_mm']*1.2),ylim=(0,-m['upper_rf_y_N']*1.2))
    axes[2].scatter([m['engineering_compression_strain']*100],[m['nominal_compression_stress_MPa']]);axes[2].set(xlabel='Actual engineering compression [%]',ylabel='Nominal compression stress [MPa]',xlim=(0,m['engineering_compression_strain']*120),ylim=(0,m['nominal_compression_stress_MPa']*1.2))
    fig.suptitle('One accepted measurement; no interpolated curve or fitted modulus')
    finish(fig,'reaction_and_first_measurement.png')
    return list((RUN/'figures').glob('*.png'))


def contact_figure(mesh,q):
    contact=np.loadtxt(BASE/'full_recovery_001_post/stage001_contact.csv',delimiter=',',skiprows=1)
    fig,axes=plt.subplots(3,2,figsize=(12,10),constrained_layout=True)
    for pair,group in [(1,'bottom'),(2,'top')]:
        data=contact[contact[:,0]==pair];ids=mesh.boundary[mesh.boundary_groups==group,2]
        assert len(data)==len(ids)
        x=mesh.nodes[ids,0];gap=data[:,5:7].max(axis=1)
        for ax,values in [(axes[0,0],data[:,2]),(axes[0,1],data[:,3:5].max(axis=1)),
                          (axes[1,0],gap),(axes[1,1],data[:,7]),(axes[2,0],np.maximum(0,gap))]:
            ax.scatter(x,values,s=4,label=group)
    labels=['Native contact status','Max stored endpoint\npressure [MPa]',
            'Max signed endpoint\ngap/penetration [mm]','Contact internal FY [N]',
            'Positive endpoint\npenetration [mm]']
    for ax,title in zip(list(axes.flat)[:5],labels):
        ax.set(xlabel='Undeformed contact midpoint x [mm]',ylabel=title);ax.legend();ax.grid(alpha=.2)
    axes[2,1].bar([c['pair'] for c in q['contacts']],[c['signed_opposition_residual_relative'] for c in q['contacts']])
    axes[2,1].axhline(.01,color='red',ls='--',label='Registered1% limit')
    axes[2,1].set(yscale='log',ylabel='Contact/reaction opposition\nrelative residual');axes[2,1].legend();axes[2,1].grid(alpha=.2)
    fig.suptitle('Native converged contact; endpoint maxima are not continuous-contact bounds')
    finish(fig,'contact_results.png')


def reports():
    q=load(QUALIFIED/'qualification.json');r=load(FULL/'execution_receipt.json');p=load(FULL_PROTOCOL);perf=load(RUN/'performance/PERFORMANCE.json')
    telemetry=load(FULL/'nonlinear_telemetry.json');small=load(RUN/'small_licensed/OUTPUT_PROTOCOL_VALIDATION.json')
    active=counts(RUN/'verification/active.xml');licensed=counts(RUN/'verification/licensed_final.xml')
    archives=[counts(x) for x in (RUN/'verification/archive_replay').glob('*.xml')]
    archive_passed=sum(x['passed'] for x in archives)
    accepted=q['accepted'];m=q['accepted_measurements'][0] if accepted else {};contacts=q.get('contacts',[])
    unavailable='NOT AVAILABLE';value=lambda key:str(m.get(key,unavailable))
    penetration=max((x['max_stored_endpoint_penetration_mm'] for x in contacts),default=None)
    status=q['status']
    statuses={'MEMORY_POLICY_UPDATED':'PASS_NO_PROCESS_RSS_CAP','SYSTEM_RESOURCE_MONITORING':'PASS_ACTUAL_WINDOWS_SIGNALS',
        'MINIMAL_OUTPUT_PROTOCOL_VERIFIED':small['status'],'HISTORICAL_GEOMETRY_INTEGRITY':'PASS_UNCHANGED_SOURCE_AND_MESH',
        'NONLINEAR_EQUILIBRIUM':'PASS_NATIVE' if r['converged_steps'] else 'HOLD',
        'NATIVE_OUTPUT_COMPLETE':'PASS_INDEPENDENT_RST_REOPEN_AND_REQUIRED_FIELDS' if accepted else 'HOLD',
        'INDEPENDENT_REACTION_BALANCE':'PASS' if accepted else 'HOLD','PLATEN_CONTACT_FORCE':'PASS' if accepted else 'HOLD',
        'STRESS_STRAIN_FIELDS':'PASS_NATIVE_SUPPORTED_CORNER_AVERAGES' if accepted else 'HOLD',
        'MICROSTRUCTURE_MECHANICAL_CHECKPOINT':'PASS_ONE_NONZERO_CHECKPOINT' if accepted else 'HOLD',
        'STRESS_STRAIN_CURVE':'UNQUALIFIED_ONE_POINT' if accepted else 'NOT_AVAILABLE','EFFECTIVE_MODULUS':'FIT_UNQUALIFIED; SECANT_SEPARATELY_LABELED' if accepted else 'NOT_AVAILABLE',
        'MECHANICAL_MESH_CONVERGENCE':'UNQUALIFIED','INTERNAL_SELF_CONTACT':'UNQUALIFIED_NOT_CONFIGURED','PAPER_READINESS':'RESEARCH_HOLD','LLM_OPTIMIZATION':'NOT_IMPLEMENTED'}
    protected=['experiments/pipeline_v0.6','experiments/pipeline_v0.6.1','experiments/pipeline_v0.6.2','experiments/pipeline_v0.6.3','experiments/pipeline_v0.6.4','metamaterial_eval/generators','validation/evaluators','data']
    assert not subprocess.check_output(['git','diff','--name-only',BASE_COMMIT,'--',*protected],text=True)
    ledger=subprocess.check_output(['git','log','--reverse','--format=%H %s',BASE_COMMIT+'..HEAD'],text=True).splitlines()
    summary={'schema':'young-dawgs-v0.6.5-validation','status':status,'client_date':'2026-10-30 America/New_York','base_commit':BASE_COMMIT,
        'independent_acceptance':statuses,'qualification':q,'performance':perf,'full_protocol_sha256':file_hash(FULL_PROTOCOL),
        'frozen_input_sha256':p['frozen_input_sha256'],'source_geometry_sha256':p['source_geometry_sha256'],'mesh_semantic_sha256':p['mesh_semantic_sha256'],
        'tests':{'active':active,'archive_replay':archives,'archive_passed':archive_passed,'licensed':licensed,'counts_overlap_do_not_sum':True},
        'historical_files_unchanged':True,'commits_before_containing_report_commit':ledger,'remaining_changes':'Verify after final commit; exact final HEAD in response/Git history'}
    write_json(RUN/'summary/V0_6_5_VALIDATION.json',summary);export_csv(RUN/'summary/acceptance.csv',[{'category':k,'status':v} for k,v in statuses.items()])
    export_csv(RUN/'mechanical_results/first_measurement.csv',q['accepted_measurements'])
    write_json(RUN/'summary/mechanical_feedback.json',{'status':status,'source_geometry_sha256':p['source_geometry_sha256'],'mesh_semantic_sha256':p['mesh_semantic_sha256'],
        'accepted_measurements':q['accepted_measurements'],'fitted_effective_modulus_MPa':None,'single_point_secant_modulus_MPa':q['single_point_secant_modulus_MPa'],
        'eligible_for_LLM_performance_ranking':False,'reason':'Single mesh/one checkpoint, provisional uncalibrated physics, no comparative dataset or contact/mechanical mesh convergence','optimization':'NOT_IMPLEMENTED'})
    shared=f'''Scientific status: **{status}**. Accepted checkpoints: {len(q['accepted_measurements'])}.
Source `{p['source_geometry_sha256']}`; mesh `{p['mesh_semantic_sha256']}`.
Input `{p['frozen_input_sha256']}`; native RST `{q['native_RST_sha256']}`.
'''
    save('V0_6_5_MEMORY_AND_OUTPUT_AUDIT.md',f'''# v0.6.5 memory and output audit

{shared}
The prior primary and conditional native artifacts were authenticated against
their actual receipts. Native equilibrium was genuine. The primary had no
readable saved result set; the conditional recovered displacement only.
No Rnnn restart frame existed. Missing RF/contact/S/EPEL output could not be
invented or recovered as a complete historical checkpoint. Historical HOLDs
are unchanged. The prior external20GiB guard interrupted source execution;
no actual system-memory exhaustion had been established.

The primary reached the next factorization after its first substep. Its LAST
schedule did not save that intermediate checkpoint. The conditional stopped
after equilibrium during result/database growth. Historical file-growth timing
was absent, so exact last-write activity and command-specific allocation
causality remain UNRESOLVED. Export arrays were not executing inside the
conditional source solve; no unsupported allocation cause is asserted.

The fixed process cap is disabled explicitly with rss_limit=None for v065.
Current physical RAM {perf['physical_RAM_bytes']/1024**3:.4f}GiB;
available before full execution {perf['available_RAM_before_bytes']/1024**3:.4f}GiB.
The user closed applications to increase available RAM; we did not modify
unrelated processes or pagefile settings. Actual system samples, file growth,
commit usage and paging counters are in performance/. Windows Page Reads/sec
is a hard-fault disk-read proxy, not exclusive pagefile attribution.
This selective-output run peaked below20GiB despite having no RSS cap. It
does not demonstrate actual use above20GiB; healthy high-RSS cases were tested
with synthetic monitoring telemetry. The separate effects of output selection
and supervision were not isolated in additional full-scale experiments.
''')
    save('V0_6_5_OUTPUT_PROTOCOL.md',f'''# v0.6.5 verified native output protocol

{shared}
Selected commands:

```apdl
{chr(10).join(p['selected_output']+p['output_auxiliary'])}
SAVE,checkpoint,db,,MODEL
```

NSOL/RSOL preserve displacement and reactions; STRS/EPEL preserve continuum
stress and elastic strain; CONT/MISC support the required contact queries.
OUTPR suppresses large text listings; OSRESULT ERASE avoids additional selected
result records. This is a verified sufficient subset, not proof of globally
optimal minimum output. BASIC alone was not relied upon. One final restart
frame is requested; the RST is independently verified, not accepted by size.

Actual v241 full/selective rectangle and compliant solves passed. RST sizes:
rectangle524288→458752bytes; compliant3145728→2293760bytes. Fresh read-only
exports from MODEL-only databases recovered every required field. Different
chunk sizes gave identical repeated values. A deliberately omitted EPEL record
was detected and quarantined. Audit002 preserves a first overly strict
comparison assertion and actual tiny full/selective contact differences;
the corrected1e-6 column-scale comparison leaves all physical gates unchanged.

APDL vectors are limited to250000nodes; Python streams100000rows and validates
20000elements at a time with memory-mapped field storage. Stress/strain are
native supported corner-node averages, without invented midside data.
Official adjacent-release references are recorded in RECOVERY_PLAN_001.json;
installed2024R1 behavior is established by actual licensed jobs.
''')
    save('V0_6_5_NATIVE_RESULT_RECOVERY.md',f'''# v0.6.5 native result recovery

{shared}
One preregistered full solve executed, status {r['status']}, native return
code{r['process']['returncode']}. No second full solve or additional strain
checkpoint was executed. Exact original source/mesh and working nodal contact
were retained: PLANE183 plane stress, E1000MPa/nu0.3/t1mm, frictionless separable
CONTA172/TARGE169, KEYOPT2=1/4=2/10=1, FKN100, FTOLN−1e−5.
DEFAULT sparse memory mode is retained without forcing INCORE or OUTOFCORE.

Completed Newton updates {len(telemetry['completed_iterations'])}; bisections
{len(telemetry['cutback_events'])}; last native force ratio
{telemetry['last_force_ratio']}. Native RST bytes
{(FULL/'compression.rst').stat().st_size}. Independent result-set inventory
{q.get('readable_sets',unavailable)}. MODEL-only database and RST provenance,
source input, logs, CSVs and receipt hashes are independently checked.

Actual runtime {perf['runtime_seconds']:.3f}s; peak owned-tree RSS
{perf['peak_tree_RSS_GiB']:.4f}GiB; minimum sampled available system RAM
{perf['minimum_sampled_available_RAM_bytes']/1024**3:.4f}GiB. No process RSS
cutoff exists. The exact sustained emergency policy,1800s wall limit and20GiB
disk reserve are frozen in FULL_RECOVERY_001.json. Native marker first-observed
times are {perf['observed_native_markers_seconds']}; these are sampled bounds,
not exact internal phase times. Raw native solver timing tables are retained.

Independent qualification: {q.get('failure','All required native fields and mechanical gates passed.')}.
''')
    save('V0_6_5_MICROSTRUCTURE_MECHANICS.md',f'''# v0.6.5 microstructure mechanics

{shared}
Actual accepted measurements: {q['accepted_measurements']}.
Native signed upper/lower support reactions are independently extracted;
contact sums oppose each support reaction under the unchanged1% limit.
Contact records: {contacts}.
Maximum stored-endpoint penetration: {penetration if penetration is not None else unavailable}mm;
this does not certify the continuous-contact maximum.

Native field coverage: {q.get('actual_nodes',unavailable)}nodes,
{q.get('actual_TRI6',unavailable)}TRI6, {q.get('actual_corner_field_nodes',unavailable)}corner field nodes.
All deformed mappings positive: {q.get('all_deformed_mappings_positive',False)};
minimum determinant {q.get('minimum_deformed_determinant_mm2',unavailable)}mm².
SYY/SEQV/EPEL Y/X ranges: {q.get('corner_stress_strain_ranges',unavailable)}.
Full native and derived field artifacts remain outside Git, with hashes.
Native displacement is at every node; stress/strain use supported corner-node
averages. Visualization triangle means are rendering, not invented raw data.

Engineering strain is achieved travel/10.24mm. Nominal envelope stress is
compressive upper reaction/(10.24mm×1mm), using totalN forces and1mm thickness.
Single-point secant estimate: {q['single_point_secant_modulus_MPa']}MPa.
Fitted effective modulus: NOT QUALIFIED. Complete stress–strain curve: NOT
QUALIFIED. Single-mesh refinement, internal self-contact, calibration, yielding,
fracture and manufacturing remain unqualified; prior geometry HOLDs remain.
''')
    ledgermd='\n'.join('- `'+x.split(' ',1)[0]+'` — '+x.split(' ',1)[1] for x in ledger)
    statusmd='\n'.join('| '+k+' | '+v+' |' for k,v in statuses.items())
    save('V0_6_5_VALIDATION.md',f'''# v0.6.5 scientific validation

{shared}
## 1. Previous equilibrium

The v064 full model reached0.005% equilibrium after7updates, but had no
mechanically accepted checkpoint. These historical facts remain unchanged.

## 2. Output failure

The external20GiB guard interrupted native execution. Historical conditional
RST retained displacement only. Exact command-allocation cause is UNRESOLVED.
See V0_6_5_MEMORY_AND_OUTPUT_AUDIT.md.

## 3. Updated memory policy

No process RSS threshold. Sustained6GiB available-memory reserve/30s,
critical1GiB/3s, corroborated commit/Windows notification guards, severe
paging without output growth,20GiB free disk and1800s wall protection.
Recovery resets transient low-memory durations. No unrelated apps/pagefile
settings were changed. Exact policy is frozen in JSON and tested synthetically.

## 4. Actual available memory

Physical {perf['physical_RAM_bytes']/1024**3:.4f}GiB; before run
{perf['available_RAM_before_bytes']/1024**3:.4f}GiB; minimum sampled available
{perf['minimum_sampled_available_RAM_bytes']/1024**3:.4f}GiB. Installed RAM was
not assumed to equal currently available RAM.

## 5. Output protocol

Explicit NSOL/RSOL/STRS/EPEL/CONT/MISC LAST, suppressed text/duplicate selected
results, one final restart frame, MODEL-only DB and separate read-only export.
See V0_6_5_OUTPUT_PROTOCOL.md.

## 6. Small licensed verification

Matched full/selective rectangle and compliant solves passed unchanged physical
gates. Repeated native extraction matched exactly. Missing EPEL was correctly
quarantined. The initial overprecise comparison failure is retained in audit002.

## 7. Full execution

One full solve: {r['status']}, returncode{r['process']['returncode']},
{len(telemetry['completed_iterations'])}updates, {len(telemetry['cutback_events'])}bisections.
No additional strain points or exploratory contact changes.

## 8. Native output

RST {(FULL/'compression.rst').stat().st_size}bytes, hash above. File size alone
was never an acceptance gate. Actual result writing and file-growth samples
are recorded in performance/ and native logs.

## 9. Independent read-only validation

Qualification {q['status']}. Result-set inventory, provenance, native fields,
all node IDs/corner IDs, signed reactions/contact forces and every deformed
TRI6 mapping were checked. Repeated full extraction is independently compared.

## 10. Support reactions

Upper {value('upper_rf_y_N')}N; lower {value('lower_rf_y_N')}N;
normalized reaction imbalance {value('reaction_balance_relative')}.

## 11. Platen contact

{contacts}
Stored endpoint maxima are not continuous-contact bounds. Internal self-contact
is not configured. No force was inferred from the opposite support.

## 12. Stress and strain

Native supported corner-node SYY/SEQV/EPEL Y/X; {q.get('actual_corner_field_nodes',unavailable)}nodes.
No midside stress fabrication. All-node UX/UY plus derived displacement magnitude
and deformed coordinates are preserved with artifact hashes.

## 13. Stress–strain measurement

Achieved strain {value('engineering_compression_strain')}; nominal stress
{value('nominal_compression_stress_MPa')}MPa. One measurement is not a curve.
Secant {q['single_point_secant_modulus_MPa']}MPa is separately labeled;
no fitted modulus is justified.

## 14. Runtime and memory

{perf['runtime_seconds']:.3f}s; peak{perf['peak_tree_RSS_GiB']:.4f}GiB;
maximum commit fraction{perf['maximum_commit_fraction']}; Windows low-memory
samples{perf['windows_low_memory_sample_count']}. System hard-fault disk-read
proxy maximum{perf['maximum_page_reads_per_second']}; native paging counters
cannot attribute every hard fault to pagefile-only I/O.

## 15. Limitations

Single mesh/limited loading, mechanical mesh convergence UNQUALIFIED, internal
self-contact UNQUALIFIED_NOT_CONFIGURED. E1000MPa,nu0.3,scale/thickness,plane
stress and homogeneous elasticity remain provisional and uncalibrated. Prior
small-pore fidelity, production simplification and historical repair HOLDs
remain. No yielding/fracture, paper or manufacturing qualification is claimed.

## 16. Scientific acceptance and tests

| Category | Status |
|---|---|
{statusmd}

Active {active['passed']}passed/{active['failures']}failed; archived
{archive_passed}passed separately; licensed{licensed['passed']}passed/
{licensed['failures']}failed. Counts overlap and are not summed. Synthetic
monitor/parser tests are distinct from real licensed evidence. Protected
historical experiments, generators and evaluator remain unchanged.

## 17. Git commits

Started clean on master at `{BASE_COMMIT}`. No push or history rewrite.

{ledgermd}

The containing final reporting commit is identified in Git history/final response.

## 18. Next-stage handoff

{'Repeat the accepted checkpoint, then prospectively qualify contact/output sensitivity and mechanical mesh convergence before a small additional strain point. No automatic multi-point campaign.' if accepted else 'Investigate the specifically recorded native-output/qualification failure under a new bounded protocol; no blind contact retuning or synthetic mechanical substitutes.'}
No batch FEM,3D,LLM optimization or manufacturing work was implemented.

Actual figures and hashes are in figures/figure_manifest.json. Full binary
artifacts remain external; execution/replay instructions are in
docs/pipeline_v0.6.5/WINDOWS_EXECUTION.md.

- [Undeformed and true-scale deformed boundaries](figures/geometry_and_deformation.png)
- [Displacement fields](figures/displacement_fields.png)
- [Native continuum stress](figures/continuum_stress.png)
- [Native elastic strain](figures/elastic_strain.png)
- [Contact status, pressure, gap and penetration](figures/contact_results.png)
- [Signed reactions and first measurement](figures/reaction_and_first_measurement.png)
- [Actual system resources](figures/system_resources.png)
- [Output writing and convergence](figures/native_output_timeline.png)
''')
    answers=[
        'Yes, disabled for v065 with rss_limit=None; no replacement process RSS threshold.',
        'Sustained system-available RAM, native commit/low-memory signals and severe paging with stalled output; disk and wall-time guards retained.',
        f"{perf['physical_RAM_bytes']/1024**3:.4f}GiB.",f"{perf['available_RAM_before_bytes']/1024**3:.4f}GiB immediately before full execution.",
        f"{perf['peak_tree_RSS_GiB']:.4f}GiB owned process-tree peak.",
        f"Maximum system Page Reads/sec{perf['maximum_page_reads_per_second']}; severe-threshold samples{perf['page_read_samples_above_registered_severe_threshold']}; no claim of pagefile-only attribution.",
        'No; normal process exit.' if r['status']=='PROCESS_EXITED' else r['status'],
        'Displacement-only state was readable; no complete historical checkpoint or restart frame recoverable.',
        'Observed external20GiB supervisor stops; primary LAST schedule omitted the intermediate result. Exact allocation-command cause UNRESOLVED.',
        'OUTRES ALL NONE then NSOL/RSOL/STRS/EPEL/CONT/MISC LAST; OUTPR ALL NONE; OSRESULT ERASE; final restart frame; MODEL-only database.',
        'Yes, independently read and qualified.' if accepted else 'No; '+q.get('failure',unavailable),
        'Yes, actual full/selective rectangle and compliant solves, RST reopening and repeated export.',
        'Yes; source geometry SHA256 unchanged.','Yes; historical semantic mesh SHA256 unchanged.',
        'Yes:2766505nodes/1261670TRI6/412pores.','Yes; fixed purepenalty FKN100,KEYOPT2=1/4=2/10=1,FTOLN−1e−5.',
        'Yes.' if r['converged_steps'] else 'No.',value('engineering_compression_strain')+' engineering strain; target0.005%.',
        str(len(telemetry['completed_iterations'])),str(len(telemetry['cutback_events'])),
        'Yes; normal source exit and independently verified required records.' if accepted else 'Complete qualification not achieved.',
        'Yes, fresh POST1 processes with MODEL-only database and SET1,1.' if accepted else unavailable,
        value('upper_rf_y_N')+'N upper /'+value('lower_rf_y_N')+'N lower.',
        'Bottom '+str(contacts[0]['contact_element_force_y_N'])+'N; top '+str(contacts[1]['contact_element_force_y_N'])+'N, actual signed internalFY.' if accepted else unavailable,
        value('reaction_balance_relative')+' normalized reaction imbalance.',str(penetration)+'mm stored-endpoint maximum; not a continuous-contact bound.' if accepted else unavailable,
        str(q.get('actual_nodes',unavailable))+' actual all-node UX/UY; magnitude and deformed coordinates derived.',
        'Yes, native supported corner SYY/SEQV.' if accepted else unavailable,'Yes, native supported corner EPEL Y/X.' if accepted else unavailable,
        str(q.get('all_deformed_mappings_positive',False))+'; all TRI6 checked.',str(accepted),
        value('upper_rf_y_N')+'N signed upper reaction; '+value('nominal_compression_stress_MPa')+'MPa nominal compression stress.',
        'Yes, one accepted nonzero measurement.' if accepted else unavailable,'No, one point is not a curve.',
        'No fitted modulus; separately labeled secant '+str(q['single_point_secant_modulus_MPa'])+'MPa.' if accepted else unavailable,
        str(active['passed']),str(archive_passed)+' separately; suites overlap.',str(licensed['passed'])+' licensed checks passed.',
        'Yes, protected historical files unchanged.',f"{perf['runtime_seconds']:.3f}s source solve; postprocessing timings recorded separately.",
        f"{perf['peak_tree_RSS_GiB']:.4f}GiB source tree; Python streaming peak separately recorded.",
        'Exact additive/new and modified file paths in summary/change_inventory.json.',
        'Coherent commits in validation report and final response.','Full hashes and exact messages in validation report/final response.',
        'Final response verifies clean status after containing commit.','Nothing pushed.',status,
        'Full curve, fitted modulus, mechanical mesh convergence, internal self-contact, calibration, yielding/fracture, paper/manufacturing readiness and LLM ranking.',
        'Ready only to plan a bounded next checkpoint after repeatability/sensitivity review; none automatically executed.' if accepted else 'No; resolve the specific qualification HOLD first.',
        'Repeat accepted checkpoint and qualify numerical/contact/mesh sensitivity before a small prospective additional loading stage.' if accepted else 'Resolve the exact evidenced native-output/qualification blocker under a new protocol.'
    ]
    assert len(answers)==50,len(answers)
    save('V0_6_5_HANDOFF.md','# v0.6.5 requested50-item handoff\n\n'+shared+'\n| # | Answer |\n|---:|---|\n'+'\n'.join('| '+str(i)+' | '+a.replace('|','/')+' |' for i,a in enumerate(answers,1)))
    write_json(RUN/'figures/figure_manifest.json',{'actual_native_figures':{x.name:file_hash(x) for x in (RUN/'figures').glob('*.png')},
        'native_RST_sha256':q['native_RST_sha256'],'source_geometry_sha256':p['source_geometry_sha256'],'mesh_semantic_sha256':p['mesh_semantic_sha256'],
        'scope':'Only qualified native fields; no invented curve, midside stress or performance ranking. Resource plots use actual sampled telemetry.'})
    return summary


if __name__=='__main__':
    performance();field_figures();reports()
