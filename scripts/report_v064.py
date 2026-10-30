"""Evidence-only v0.6.4 figures, acceptance records and scientific handoff."""
from pathlib import Path
import csv
import json
import re
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection,PolyCollection
from shapely import from_wkt
from metamaterial_eval.simulation.mesh_artifacts import artifact_root,resolve_manifest
from metamaterial_eval.simulation.nonlinear_diagnostics import parse_solver_log,parse_contact,contact_summary,localize_residual,export_csv
from metamaterial_eval.simulation.microstructure_results import postprocess,force_metrics,contact_metrics
from metamaterial_eval.simulation.geometry_adapter import authenticate_fixture
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v064_small_study import REPO,RUN,BASE,load

PRIMARY=BASE/'full_recovery_001'
FULL=BASE/'full_recovery_002'
POST=BASE/'postprocess_converged_002'
ACTUAL=RUN/'full_model_retry/actual_002'
MECHANICS=RUN/'mechanical_results/attempt_002'


def save(name,text):(RUN/name).write_text(text.rstrip()+'\n',encoding='utf-8')


def finish(fig,name):
    fig.savefig(RUN/'figures'/name,dpi=160);plt.close(fig)


def foundation_figures():
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for i,color in [(1,'tab:blue'),(2,'tab:orange')]:
        r=load(RUN/f'historical_failure_forensics/attempt_{i:03d}_reconstruction.json')
        vals=r['force_evaluations'];axes[0,0].semilogy([x['evaluation'] for x in vals],[x['ratio'] for x in vals],'o-',label=f'v063 attempt{i}',color=color)
        axes[0,1].semilogy([x['evaluation'] for x in vals],[x['value_N'] for x in vals],'o-',label=f'v063 attempt{i}',color=color)
        a=r['observed_wall_stamp_differences_seconds'];axes[1,0].plot(np.arange(1,len(a)+1),a,'o-',label=f'attempt{i}',color=color)
    axes[0,0].axhline(1,ls='--',color='green');axes[0,0].set(ylabel='Force residual / criterion',xlabel='Force-evaluation index, not a converged substep')
    axes[0,1].set(ylabel='Native global force residual [N]',xlabel='Force-evaluation index')
    axes[1,0].set(ylabel='Observed stamp difference [s]',xlabel='Between-factorization note interval')
    axes[1,1].axis('off');axes[1,1].text(0,.95,'Historical facts:\n9 / 14 completed Newton updates\n0 converged substeps\n0 observed cutbacks before stopping\nNEQIT30 not reached\n\nNot recorded historically:\ncontact activation / gaps / chatter by iteration\nspatial residual snapshots\n\nNo missing histories are reconstructed as measurements.',va='top')
    for ax in [axes[0,0],axes[0,1],axes[1,0]]:ax.legend(loc='upper right',fontsize=8);ax.grid(alpha=.2)
    fig.suptitle('Actual historical nonlinear failure evidence — numerical diagnostics only')
    finish(fig,'historical_failures.png')
    geom=from_wkt((RUN/'synthetic_models/compliant_zigzag_001/source.wkt').read_text())
    fig,axes=plt.subplots(1,3,figsize=(13,5),constrained_layout=True)
    for ax in axes:
        for ring in [geom.exterior,*geom.interiors]:
            xy=np.asarray(ring.coords);ax.plot(xy[:,0],xy[:,1],color='0.5',lw=.7)
        ax.set(xlim=(-.1,4.1),ylim=(-.1,4.1),aspect='equal',xlabel='x [mm]',ylabel='y [mm]')
    axes[0].set_title('Deterministic compliant synthetic fixture\nnot the Design9 specimen')
    for ax,label in zip(axes[1:],['pp_base','pp_nodal_target']):
        snapshots=load(BASE/label/'residual_localization.json');a=max(snapshots,key=lambda x:x['specimen_translation_L2_N'])
        points=a['top_residual_nodes'];xy=np.array([p['xy_mm'] for p in points]);values=[p['translation_residual_norm_N'] for p in points]
        q=ax.scatter(xy[:,0],xy[:,1],c=values,cmap='magma',s=22);fig.colorbar(q,ax=ax,label='Translation residual magnitude [N]')
        ax.set_title(label+'\nretained NR snapshot, diagnostic only')
    finish(fig,'synthetic_fixture_and_residuals.png')
    fig,axes=plt.subplots(2,2,figsize=(12,8),constrained_layout=True)
    for label,color in [('pp_base','tab:red'),('pp_nodal_target','tab:blue')]:
        a=load(BASE/label/'contact_telemetry.json')['records']
        for pair,ls in [(2,'-'),(3,'--')]:
            subset=[r for r in a if r['pair']==pair];x=[r['block_sequence'] for r in subset]
            for ax,key in [(axes[0,0],'active_elements'),(axes[0,1],'chattering_level'),(axes[1,0],'penetration_or_gap_mm'),(axes[1,1],'max_normal_stiffness')]:
                ax.plot(x,[r[key] for r in subset],ls,color=color,label=f'{label}, pair{pair}')
    for ax,title in zip(axes.flat,['Elements in contact','Native maximum chattering level','Native penetration / gap [mm]','Native maximum normal stiffness']):
        ax.set(xlabel='CND block sequence across iterations / trials',ylabel=title);ax.legend(loc='upper right',fontsize=7);ax.grid(alpha=.2)
    fig.suptitle('Actual contact iteration telemetry; trial forces are not mechanical measurements')
    finish(fig,'small_contact_iteration_diagnostics.png')
    labels=['pp_base','direct','pp_linearized_monitorfix','pp_early_cutback','pp_initial8','pp_update100','pp_fkn1','pp_nodal_target','pp_nodal_cutback8','pp_nodal_recovery_controls']
    fig,axes=plt.subplots(2,2,figsize=(14,8),constrained_layout=True)
    count=[];cost=[];cuts=[]
    for label in labels:
        r=load(BASE/label/'execution_receipt.json');t=load(BASE/label/'nonlinear_telemetry.json');count.append(len(r['converged_steps']));cost.append(r['process']['runtime_seconds']);cuts.append(len(t['cutback_events']))
    x=np.arange(len(labels))
    for ax,y,title in [(axes[0,0],count,'Actual converged substeps'),(axes[0,1],cost,'Actual runtime [s]'),(axes[1,0],cuts,'Observed cutbacks')]:
        ax.bar(x,y);ax.set_xticks(x,labels,rotation=45,ha='right',fontsize=7);ax.set_title(title)
    for label in ['pp_base','direct','pp_nodal_target']:
        t=load(BASE/label/'nonlinear_telemetry.json');v=t['force_evaluations'];axes[1,1].semilogy([r['evaluation'] for r in v],[r['ratio'] for r in v],label=label)
    axes[1,1].axhline(1,color='green',ls='--');axes[1,1].set(xlabel='Source-order evaluation index',ylabel='Force residual / criterion');axes[1,1].legend(loc='upper right')
    fig.suptitle('Controlled diagnostic comparisons — direct and linearized models change assumptions')
    finish(fig,'controlled_small_experiments.png')


def native_evidence(full,out):
    """Bind finished native outputs. Never edit frozen deck/protocol or raw receipts."""
    receipt=load(full/'execution_receipt.json')
    if receipt['process']['returncode'] is None:raise RuntimeError('Full process not complete')
    text=(full/'solver.out').read_text(errors='replace');t=parse_solver_log(text)
    observed=re.findall(r'CURRENT JOBNAME REDEFINED AS\s+([A-Za-z0-9_]+)',text)[-1]
    c=parse_contact((full/(observed+'.cnd')).read_text(errors='replace'))
    manifest=REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json'
    mesh,m,where=resolve_manifest(manifest,root=Path.home()/'YoungDawgs-Artifacts')
    snapshots=[localize_residual(p,mesh.nodes,mesh.boundary,mesh.boundary_groups) for p in sorted(full.glob(observed+'.nr[0-9]*'))]
    out.mkdir(exist_ok=False)
    write_json(out/'nonlinear_telemetry.json',t);write_json(out/'contact_telemetry.json',c);write_json(out/'contact_summary.json',contact_summary(c['records']));write_json(out/'residual_localization.json',snapshots)
    export_csv(out/'force_iterations.csv',t['force_evaluations']);export_csv(out/'contact_iterations.csv',c['records']);export_csv(out/'resources.csv',receipt['process'].get('resource_samples',[]))
    native_files=[p for p in full.iterdir() if re.search(r'\.(?:nr\d+|nd\d+|cnd|nlh)$',p.name)]
    write_json(out/'native_diagnostic_inventory.json',{'observed_jobname':observed,'requested_jobname':receipt.get('native_jobname'),'filename_warning_retained':observed!=receipt.get('native_jobname_requested',receipt.get('native_jobname')),'bytes':sum(p.stat().st_size for p in native_files),'files':{p.name:{'bytes':p.stat().st_size,'sha256':file_hash(p)} for p in native_files},'scope':'retained final ring files only; intermediate snapshots rotated within unique new run; full file hashes in native process receipt'})
    for name in ['execution_receipt.json','simulation_manifest.json','corrected_inventory.txt','initial_contact.txt']:
        if (full/name).exists():
            if name.endswith('.txt'):(out/name).write_text('\n'.join(s.rstrip() for s in (full/name).read_text(errors='replace').splitlines()).rstrip()+'\n',encoding='utf-8')
            else:(out/name).write_bytes((full/name).read_bytes())
    # Retain compact actual relevant log excerpts; raw full native log stays local.
    lines=text.splitlines();matches=[i for i,s in enumerate(lines) if re.search(r'CONVERGENCE VALUE|EQUIL ITER|BISECTION|SOLUTION CONVERGED|\*\*\* (?:WARNING|ERROR)|CURRENT JOBNAME REDEFINED|USE NODAL|Nodal detection',s,re.I)]
    selected=sorted({j for i in matches for j in range(i,min(len(lines),i+4))})
    (out/'solver_excerpt.txt').write_text('\n'.join(f'{i+1}: {lines[i].rstrip()}'.rstrip() for i in selected)+'\n',encoding='utf-8')


def finalize_full():
    if not (RUN/'full_model_retry/actual_001').exists():native_evidence(PRIMARY,RUN/'full_model_retry/actual_001')
    native_evidence(FULL,ACTUAL)
    manifest=REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json'
    return postprocess(FULL,manifest,RUN/'protocol/FULL_RECOVERY_002.json',MECHANICS,field_directory=POST if (POST/'execution_receipt.json').exists() else None)


def full_figures():
    t=load(ACTUAL/'nonlinear_telemetry.json');c=load(ACTUAL/'contact_telemetry.json')['records'];r=load(FULL/'execution_receipt.json')
    fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
    a=t['force_evaluations'];axes[0,0].semilogy([x['evaluation'] for x in a],[x['ratio'] for x in a],'o-');axes[0,0].axhline(1,color='green',ls='--');axes[0,0].set(xlabel='Force-evaluation index',ylabel='Residual / criterion')
    for pair in [2,3]:
        a=[x for x in c if x['pair']==pair];x=[v['block_sequence'] for v in a]
        axes[0,1].plot(x,[v['active_elements'] for v in a],label=f'pair{pair}')
        axes[0,2].plot(x,[v['chattering_level'] for v in a],label=f'pair{pair}')
        axes[1,0].plot(x,[v['penetration_or_gap_mm'] for v in a],label=f'pair{pair}')
    for ax,title in [(axes[0,1],'Active contact elements'),(axes[0,2],'Native chattering level'),(axes[1,0],'Trial penetration / gap [mm]')]:ax.set(xlabel='CND block sequence',ylabel=title);ax.legend(loc='upper right',fontsize=8)
    samples=r['process'].get('resource_samples',[])
    axes[1,1].plot([s['elapsed_seconds'] for s in samples],[s['tree_rss_bytes']/1024**3 if s['tree_rss_bytes'] is not None else np.nan for s in samples],label='1-second snapshots');axes[1,1].axhline(20,color='red',ls='--',label='20-GiB guard');axes[1,1].axhline(r['process']['peak_tree_rss_bytes']/1024**3,color='purple',ls=':',label='0.1-second supervisor peak');axes[1,1].legend(loc='lower right',fontsize=7);axes[1,1].set(xlabel='Measured runtime [s]',ylabel='Sampled process-tree RSS [GiB]')
    axes[1,2].axis('off');m=load(MECHANICS/'mechanical_summary.json');axes[1,2].text(0,.95,f"Actual status: {r['status']}\nRuntime {r['process']['runtime_seconds']:.3f}s\nPeak {r['process']['peak_tree_rss_bytes']/1024**3:.3f}GiB\nCompleted updates {len(t['completed_iterations'])}\nCutbacks {len(t['cutback_events'])}\nEquilibrium announced: iteration7\nCompleted-substep markers {len(t['converged_substeps'])}\nAccepted mechanics {len(m['actual_valid_stages'])}\n\nGauss0 → nodal target normal2\nFixedPP100 / original full mesh\nPlane stress / platen contact only",va='top',fontsize=10)
    fig.suptitle('Actual full-model recovery: trial telemetry is separate from accepted mechanics')
    finish(fig,'full_recovery_diagnostics.png')
    geometry,mask,prov=authenticate_fixture(REPO,CompressionConfig())
    snapshots=load(ACTUAL/'residual_localization.json')
    fig,axes=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
    for ax,s in zip(axes,snapshots):
        ax.imshow(mask,cmap='gray',origin='upper',extent=[0,10.24,0,10.24]);p=s['top_residual_nodes'];xy=np.array([v['xy_mm'] for v in p]);q=ax.scatter(xy[:,0],xy[:,1],c=[v['translation_residual_norm_N'] for v in p],s=20,cmap='magma');fig.colorbar(q,ax=ax,label='Residual magnitude [N]')
        ax.set(title=f"Native residual iteration {s['iteration']}\nDIAGNOSTIC_ONLY; mechanics incomplete",xlabel='x [mm]',ylabel='y [mm]',aspect='equal')
    finish(fig,'full_residual_localization.png')
    if m['actual_valid_stages'] and not m['unsupported_output_queries']:mechanical_figures(m)


def displacement_diagnostic_figure():
    proof=load(RUN/'mechanical_results/displacement_only_validation.json')
    if not proof['all_node_ids_and_finite_values_verified'] or not proof['all_deformed_TRI6_mappings_positive']:raise ValueError('Displacement-only diagnostic not verified')
    mesh,m,where=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    u=np.loadtxt(POST/'stage001_displacements.csv',delimiter=',',skiprows=1);deformed=mesh.nodes+u[:,1:3];faces=mesh.boundary[:,:2]
    fig,axes=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
    axes[0].add_collection(LineCollection(mesh.nodes[faces],colors='0.65',linewidths=.3));axes[0].add_collection(LineCollection(deformed[faces],colors='tab:blue',linewidths=.3));axes[0].set_title('Native displacement-only boundary overlay\ntrue scale (1×), no magnification')
    pc=PolyCollection(mesh.nodes[mesh.triangles[:,:3]],array=u[:,2][mesh.triangles[:,:3]].mean(axis=1),edgecolors='none');axes[1].add_collection(pc);fig.colorbar(pc,ax=axes[1],label='Actual native UY [mm]');axes[1].set_title('Native UY only / corner-mean rendering\nstress, strain and reactions incomplete')
    for ax in axes:ax.set(xlim=(0,10.24),ylim=(0,10.24),aspect='equal',xlabel='x [mm]',ylabel='y [mm]')
    fig.suptitle('Converged native displacement diagnostic — NO accepted mechanical performance result')
    finish(fig,'displacement_only_diagnostic.png')


def mechanical_figures(result):
    mesh,artifact,where=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    fields=Path(result.get('field_export_directory',str(FULL)))
    u=np.loadtxt(fields/'stage001_displacements.csv',delimiter=',',skiprows=1);stress=np.loadtxt(fields/'stage001_stress.csv',delimiter=',',skiprows=1)
    pts=mesh.nodes[mesh.triangles[:,:3]];edges=mesh.boundary[:,:2];deformed=mesh.nodes+u[:,1:3]
    fig,axes=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
    axes[0].add_collection(LineCollection(mesh.nodes[edges],colors='0.6',linewidths=.3));axes[0].add_collection(LineCollection(deformed[edges],colors='tab:blue',linewidths=.3));axes[0].set_title('True-scale solved boundary overlay (1×)')
    q=PolyCollection(pts,array=u[:,2][mesh.triangles[:,:3]].mean(axis=1),edgecolors='none');axes[1].add_collection(q);fig.colorbar(q,ax=axes[1],label='Actual UY [mm]');axes[1].set_title('Actual vertical displacement / corner rendering')
    for ax in axes:ax.set(xlim=(0,10.24),ylim=(0,10.24),aspect='equal',xlabel='x [mm]',ylabel='y [mm]')
    finish(fig,'actual_deformation_displacement.png')
    corners=stress[:,0].astype(int)-1;lookup=np.searchsorted(corners,mesh.triangles[:,:3])
    fig,axes=plt.subplots(1,2,figsize=(12,6),constrained_layout=True)
    for ax,column,title in [(axes[0],1,'Actual corner-averaged SYY [MPa]'),(axes[1],3,'Actual corner-averaged elastic EYY')]:
        q=PolyCollection(pts,array=stress[:,column][lookup].mean(axis=1),edgecolors='none');ax.add_collection(q);fig.colorbar(q,ax=ax);ax.set(title=title,xlim=(0,10.24),ylim=(0,10.24),aspect='equal',xlabel='x [mm]',ylabel='y [mm]')
    fig.suptitle('Actual converged checkpoint; no midside stress invented; refinement unqualified')
    finish(fig,'actual_stress_strain_fields.png')
    row=result['actual_valid_stages'][0];fig,axes=plt.subplots(1,2,figsize=(10,4),constrained_layout=True)
    axes[0].scatter([row['compression_displacement_mm']],[-row['upper_rf_y_N']]);axes[0].set(xlabel='Achieved platen travel [mm]',ylabel='Actual compressive RF [N]')
    axes[1].scatter([row['engineering_compression_strain']*100],[row['nominal_compression_stress_MPa']]);axes[1].set(xlabel='Achieved engineering compression [%]',ylabel='Nominal compression stress [MPa]')
    for ax in axes:ax.set_xlim(left=0);ax.set_ylim(bottom=0);ax.grid(alpha=.2)
    fig.suptitle('One measured nonzero checkpoint; no interpolated curve or fitted modulus')
    finish(fig,'actual_single_checkpoint_measurements.png')
    c=np.loadtxt(fields/'stage001_contact.csv',delimiter=',',skiprows=1);fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    for pair,group in [(1,'bottom'),(2,'top')]:
        values=c[c[:,0]==pair];faces=mesh.boundary[mesh.boundary_groups==group];x=deformed[faces[:,2],0]
        for ax,y in [(axes[0],values[:,2]),(axes[1],values[:,3:5].max(axis=1)),(axes[2],np.maximum(0,values[:,5:7].max(axis=1)))]:ax.scatter(x,y,s=3,label=group)
    for ax,title in zip(axes,['Actual contact status','Stored endpoint pressure [MPa]','Stored endpoint penetration [mm]']):ax.set(xlabel='Solved contact midpoint x [mm]',title=title);ax.legend(loc='upper right',fontsize=8)
    finish(fig,'actual_loaded_contact.png')


def xml_counts(path):
    suites=list(ET.parse(path).getroot().iter('testsuite'))
    return {key:sum(float(s.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped','time']}


def write_reports():
    mechanics=load(MECHANICS/'mechanical_summary.json');receipt=load(FULL/'execution_receipt.json')
    telemetry=load(ACTUAL/'nonlinear_telemetry.json');contact=load(ACTUAL/'contact_summary.json');inventory=load(ACTUAL/'native_diagnostic_inventory.json')
    rows=mechanics['actual_valid_stages'];valid=bool(rows) and not mechanics['unsupported_output_queries'];last=rows[-1] if valid else {}
    accepted_contacts=list(csv.DictReader((MECHANICS/'contact_diagnostics.csv').open())) if rows else []
    maximum_pen=max((float(r['max_stored_endpoint_penetration_mm']) for r in accepted_contacts),default=None)
    secant=mechanics['effective_stiffness'].get('secant_modulus_MPa')
    first_times=mechanics['logged_converged_substep_times'];first_strain=first_times[0][2] if first_times else None
    if not first_times:
        first_times=[(r['load_step'],r['substep'],r['pseudo_time']) for r in load(RUN/'full_model_retry/actual_001/nonlinear_telemetry.json')['converged_substeps'] if 'pseudo_time' in r]
        first_strain=first_times[0][2] if first_times else None
    displacement=load(RUN/'mechanical_results/displacement_only_validation.json');contact_evidence=load(RUN/'summary/converged_contact_diagnostic.json')
    active=xml_counts(RUN/'verification/active_complete.xml');licensed=xml_counts(RUN/'verification/licensed_final.xml');archives=[xml_counts(p) for p in (RUN/'verification/archive_replay').glob('*.xml')]
    passed=lambda s:int(s['tests']-s['failures']-s['errors']-s['skipped'])
    ap=passed(active);lp=passed(licensed);arp=sum(passed(s) for s in archives)
    old=[load(RUN/f'historical_failure_forensics/attempt_{i:03d}_reconstruction.json') for i in [1,2]]
    protocol=load(RUN/'protocol/FULL_RECOVERY_002.json');audit=load(RUN/'audit/initial.json');primary=load(PRIMARY/'execution_receipt.json')
    increments=[r['time_increment'] for r in telemetry['converged_substeps'] if 'time_increment' in r]+[r['new_time_increment'] for r in telemetry['cutback_events'] if 'new_time_increment' in r]
    if not increments and protocol['controls']['NSUBST']==[1,1,1]:increments=[min(r['pseudo_time'] for r in load(ACTUAL/'contact_telemetry.json')['records'])]
    minimum_increment=min(increments) if increments else None
    protected=['experiments/pipeline_v0.6','experiments/pipeline_v0.6.1','experiments/pipeline_v0.6.2','experiments/pipeline_v0.6.3','metamaterial_eval/generators','metamaterial_eval/geometry','validation/evaluators','data','generated_microstructures']
    changed=subprocess.check_output(['git','diff','--name-only','224741c','--',*protected],cwd=REPO,text=True);assert not changed,changed
    ledger=subprocess.check_output(['git','log','--reverse','--format=%H %s','224741c..HEAD'],cwd=REPO,text=True).splitlines()
    status='FIRST_NONZERO_MICROSTRUCTURE_CHECKPOINT_VALIDATED__PRELIMINARY_RESEARCH_HOLD' if valid else 'NATIVE_NONZERO_EQUILIBRIUM_RECOVERED__RESOURCE_AND_OUTPUT_QUALIFICATION_HOLD'
    acceptance={'SOURCE_GEOMETRY_INTEGRITY':'PASS_UNCHANGED','MESH_IDENTITY_AND_QUALITY':'PASS_EXACT_HISTORICAL_SEMANTIC_IDENTITY','ANSYS_IMPORT':'PASS_REUSED_EXHAUSTIVE_V063_NATIVE_IMPORT',
        'HISTORICAL_FAILURE_DIAGNOSED':'FORCE_STAGNATION_AND_ITERATION_COST_OBSERVED; HISTORICAL_CONTACT_CAUSE_UNRESOLVED',
        'NONLINEAR_TELEMETRY_VERIFIED':'PASS_ACTUAL_V241','CONTACT_ITERATION_DIAGNOSTICS':'PASS_NATIVE_PAIR_COUNTS_CHATTER_STIFFNESS_GAP_AND_FORCE',
        'STRUCTURAL_STABILITY_DIAGNOSTICS':'RIGID_SUBSPACE_INVESTIGATED; FLEXIBLE_MODES_NOT_EIGENQUALIFIED','SMALL_MODEL_VALIDATION':'PASS_BOUNDED_CAUSAL_DIAGNOSTICS_WITH_FAILED_CONTROLS_RETAINED',
        'CORRECTION_JUSTIFIED':'PASS_SMALL_CONTACT_DETECTION_CONTROL_AND_MATCHED_RECTANGLE','FULL_MODEL_RECOVERY_ATTEMPT':receipt['status'],
        'PRIMARY_RETRY_RESOURCE_STATUS':primary['status'],'CONDITIONAL_TECHNICAL_REPAIR':'PREREGISTERED_DIRECT_CHECKPOINT_RETENTION_REPAIR; NOT_PARAMETER_SEARCH',
        'MICROSTRUCTURE_NONZERO_CONVERGENCE':'PASS_NATIVE_NONZERO_SUBSTEP' if first_times else 'NO_CONVERGED_CHECKPOINT',
        'MICROSTRUCTURE_PLATEN_FORCE':'PASS_REGISTERED_CHECKPOINT' if valid else 'NATIVE_PAIR_FORCE_EVIDENCE; INDEPENDENT_PILOT_RF_VALIDATION_INCOMPLETE',
        'MICROSTRUCTURE_MECHANICAL_OUTPUT':mechanics['status'],'FULL_STRESS_STRAIN_CURVE':'UNQUALIFIED_SINGLE_REGISTERED_CHECKPOINT_ONLY' if valid else 'UNAVAILABLE',
        'MECHANICAL_MESH_CONVERGENCE':'UNQUALIFIED','INTERNAL_SELF_CONTACT':'UNQUALIFIED_NOT_CONFIGURED','PAPER_READINESS':'RESEARCH_HOLD','LLM_FEEDBACK_LOOP':'NOT_IMPLEMENTED','MANUFACTURING':'UNQUALIFIED'}
    hypotheses=[
        {'id':'A','hypothesis':'Contact chattering','finding':'Measured in synthetic and prospective full CND; historical v063 iteration contact file absent. Changing detection enabled the small control and '+('the full checkpoint.' if valid else 'not an accepted full checkpoint.'),'certainty':'SUPPORTED_DETECTION_SENSITIVITY; exclusive microscopic cause not proven'},
        {'id':'B','hypothesis':'Inadequate initial contact constraint','finding':'Both prospective full pairs retain active elements in recorded CND; no observed total support loss. Initial closure alone was never used as proof.','certainty':'GLOBAL_PAIR_LOSS_NOT_OBSERVED; unrecorded historical states unresolved'},
        {'id':'C','hypothesis':'Flexible structural modes','finding':'No negative pivots reported; residual snapshots localize actual nodes, not eigenmodes. Direct synthetic model converges with changed boundary conditions.','certainty':'FULL_FLEXIBLE_MODES_NOT_EIGENQUALIFIED'},
        {'id':'D','hypothesis':'Excessive/inappropriate stiffness','finding':'Printed native stiffness inspected. Updating PP100 and reducing fixed FKN to1 did not cure synthetic failure; correction retainsFKN100. No formal condition number measured.','certainty':'STIFFNESS_ALONE_NOT_SUFFICIENT_EXPLANATION'},
        {'id':'E','hypothesis':'Load increments','finding':'Gauss contact failed across real cutbacks and smaller initial increments. Aggressive NEQIT8 also prevented corrected fixture convergence; exact24 control passed with automatic increment prediction.','certainty':'STEP_SIZE_ALONE_NOT_A_CURE'},
        {'id':'F','hypothesis':'Geometric nonlinearity','finding':'Linearized synthetic contact also failed; direct nonlinear fixture converged. Full NLGEOM retainedON.','certainty':'NLGEOM_ALONE_CONTRADICTED_IN_FIXTURE'},
        {'id':'G','hypothesis':'Boundary implementation','finding':'Analytical distributed closed-contact rigid-motion rank3; no extra specimen restraints introduced; actual corrected inventory verifies supports.','certainty':'INTENDED_CONSTRAINTS_VERIFIED; contact state still necessary'},
        {'id':'H','hypothesis':'Resource-limited progress','finding':'Historical9/14 completedupdates with approximately minute-scale note intervals. Full sampled runtime and memory retained; twoSMP actual capability verified, no guaranteed speedup claim.','certainty':'HISTORICAL_ITERATION_COST_SUPPORTED; not RAM exhaustion'}]
    report={'schema':'young-dawgs-v0.6.4-validation','status':status,'base_commit':'224741cfec6f0fa4021f18e2f38624ce4210700d','client_date':'2026-10-30 America/New_York','audit':audit,'acceptance':acceptance,'hypotheses':hypotheses,'full_protocol':protocol,'full_execution':receipt,'primary_full_execution':primary,'technical_amendment':load(RUN/'protocol/TECHNICAL_RECOVERY_AMENDMENT_009.json'),'native_diagnostic_inventory':inventory,'mechanical_results':mechanics,'displacement_only_diagnostic':displacement,'native_contact_force_evidence':contact_evidence,'tests':{'active':active,'licensed_diagnostic':licensed,'archived_replay':archives,'overlap':'Counts are separate, not unique-test totals; synthetic parser fixtures are never licensed tests.'},'protected_paths_unchanged':True,'commits_before_final_reporting':ledger,'final_reporting_commit':'Containing this report; exact hash in final response/Git history','remaining_changes':'Final response verifies actual clean tree after commit'}
    write_json(RUN/'summary/V0_6_4_VALIDATION.json',report);write_json(RUN/'summary/hypotheses.json',hypotheses);export_csv(RUN/'summary/hypotheses.csv',hypotheses)
    export_csv(RUN/'summary/acceptance.csv',[{'category':k,'status':v} for k,v in acceptance.items()])
    write_json(RUN/'summary/mechanical_feedback.json',{'schema':'young-dawgs-v0.6.4-mechanical-feedback','design_id':9,'seed':1,'native_resolution':1024,'source_geometry_sha256':audit['source_geometry_sha256'],'mesh_semantic_sha256':audit['mesh_semantic_sha256'],'validity':mechanics['status'],'registered_checkpoint_measurements':rows,'first_native_converged_strain':first_strain,'effective_modulus_fit_MPa':None,'single_point_secant_modulus_MPa':secant,'eligible_for_LLM_performance_ranking':False,'reason':'single geometrically qualified mesh, provisional uncalibrated physics, no contact/mechanical refinement qualification or comparative dataset','optimization_controller':'NOT_IMPLEMENTED','contact_scope':'PLATEN_CONTACT_ONLY','warnings':mechanics['warnings'],'failure_is_not_poor_material_performance':True})
    ledgermd='\n'.join('- `'+s.split(' ',1)[0]+'` — '+s.split(' ',1)[1] for s in ledger)
    save('V0_6_4_FAILURE_FORENSICS.md',f'''# v0.6.4 historical failure forensics

Both v063 failures were independently reconstructed from actual saved inputs,
native solver/monitor files, manifests and receipts. Each input hash agrees
with its original receipt and simulation manifest. Original files are unchanged.
The source/mesh hashes are unchanged; full qualification and import are reused.

Attempt1 completed9 Newton updates, with10 started factorizations and no
converged substep; it was manually stopped for recorded numerical diagnosis
after704.208s. Attempt2 completed14 updates and14 logged pivot summaries,
with no converged substep; it reached1200.102s. Both inherited NSUBST2,20,1,
AUTOTS ON, NEQIT30, full Newton and line search. No bisection was observed
before either termination: neither reached its iteration ceiling.

Requested first strain0.0001 / travel0.001024mm. Initial trial strain0.00005 /
travel0.000512mm is inferred from the inherited stepping prescription, not an
independently recorded historical trial-time/contact history. Actual v063
monitor files contain headers and no completed-substep rows. Source-ordered
force/displacement/line-search/pivot records and printed factorization-note
CPU/wall stamps are retained in historical_failure_forensics/.

Force residuals plateaued/oscillated while displacement convergence often
passed. Printed wall-stamp differences demonstrate expensive iterations;
they are not invented exact iteration timings. No logged negative pivot or
distortion failure was found before stopping, and no RAM-cap failure occurred.

Historical contact activation, transitions, chatter, gap/stiffness changes
and residual-node fields were not recorded. Historical contact causality is
UNRESOLVED. Prospective small and full diagnostics provide new evidence;
they do not retrospectively fill missing histories.
''')
    save('V0_6_4_NONLINEAR_DIAGNOSTICS.md',f'''# v0.6.4 actual nonlinear telemetry

Actual ANSYS2024R1 accepted NLDIAG,CONT,ITER; NLDIAG,NRRE,ON,2;
NLDIAG,EFLG,ON,2; and NLHIST NSOL upper-pilot UY/RF. Contact CND identifies
42 native columns, each load/substep/iteration/time block, pair2/3 active
counts, native chatter, penetration/gap, computed normal stiffness and force.
Pair counts do not identify which individual elements switched. Positive
penetration / negative gap and far-field pinball meanings remain distinguished.

Native v241 NR files are ASCII, with node IDs and DOF codes1,2,6 (FX,FY,MZ).
Streaming localization checks unique complete node IDs and finite values,
excludes platen/internal nodes from specimen localization, and retains32
largest translational residuals. Native component magnitudes do not establish
signed physical forces. The independent rectangle norm agrees within half
the CNVV header's last printed digit. An initial overprecise assertion failed
and is retained separately; mechanical tolerances were not relaxed.

NR/EFLG ring limits are2 each. ANSYS rotates these within each new job; the
last surviving snapshots are retained with metadata/hashes. Historical files
are never rotated. Full retained diagnostic size: {inventory['bytes']}bytes,
within the2GiB diagnostic budget. Small cap256MiB. Actual1s resource samples
are separate from nonlinear history; NLHIST data are converged-substep data,
not per-iteration mechanical results. Trial CND/NR output is explicitly
NONLINEAR_DIAGNOSTIC_ONLY and ineligible for LLM ranking. A native equilibrium
announcement does not turn an iteration record into a qualified field export.

The native file-rotation race exposed in an early small control is preserved
as an operationally invalid receipt. The monitor now tolerates disappearing
ring files and safely terminates owned processes on monitor exceptions or
cancellation. Its unique linearized repeat was executed. The primary full job-name
command warning is retained: the frozen deck attempted FILNAME in PREP7;
actual compression.* outputs are bound using the native current-jobname log
and exact receipt hashes. No native result was renamed, no frozen input was
rewritten and no full job was relaunched for this naming issue. The later
conditional repair addresses the separately evidenced checkpoint/memory
problem and correctly assigns its jobname at Begin level.

Official references are adjacent-release syntax references; installed-release
support is established by the actual small v241 runs:
[NLDIAG](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_NLDIAG.html),
[NLHIST](https://ansyshelp.ansys.com/public/Views/Secured/corp/v252/en/ans_cmd/Hlp_C_NLHIST.html).
''')
    hypothesis_md='\n'.join('| '+h['id']+' | '+h['hypothesis']+' | '+h['finding']+' | '+h['certainty']+' |' for h in hypotheses)
    save('V0_6_4_CONTACT_AND_CONSTRAINT_ANALYSIS.md',f'''# v0.6.4 contact and constraint analysis

| Hypothesis | Mechanism | Evidence | Certainty |
|---|---|---|---|
{hypothesis_md}

The deterministic synthetic fixture has two0.12mm zigzag bending struts and
separate caps. It is explicitly different from Design9. Direct imposed-face
compression changes boundary conditions and cannot be treated as an equivalent
frictionless separable-contact physical reference. Its convergence does not
prove full-domain stiffness or eliminate every compliant mode.

The Gauss PP100 fixture measured chatter15/12 with both pairs still active;
peak residuals were FY at contact boundaries. Update100 and fixedFKN1 did not
cure it. Nodal target-normal detection alone enabled a valid checkpoint with
unchanged physical assumptions and unchanged penetration/equilibrium gates.
Some native chatter remains even in converged runs; zero chatter was never
an acceptance prerequisite. This is evidence of detection sensitivity, not
proof of a unique microscopic explanation or a universal contact policy.

There are no new specimen UY restraints, arbitrary springs, stabilization,
bonded/no-separation replacements, friction changes or internal self-contact.
Analytical rank3 concerns planar rigid motions under distributed active
normal constraints, not an unrestricted full FE eigenanalysis. If both pairs
opened, the lone UX anchor would not suppress all rigid modes. Flexible
full-domain modes are not independently eigenqualified.

[CONTA172 detection and real constants](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_CONTA172.html)
is an adjacent-release reference; actual v241 listings corroborate the applied
options. FTOLN−1e−5 is the absolute penetration tolerance; it is not a prescribed
pure-penalty stiffness. Native computed stiffness was inspected directly.
''')
    save('V0_6_4_RECOVERY_EXPERIMENT.md',f'''# v0.6.4 full recovery experiment

**{status}**. One primary full-model retry and one conditional technical
repair executed, each after its input/protocol were committed. User section21
allows this exception for a directly correctable implementation error;
it is not another contact or stiffness search. Final native input SHA256:
{receipt['input_sha256']}.

Original native1024 source/mesh,412pores,PLANE183 TRI6 plane stress,E1000MPa,
nu0.3,t1mm,10.24mm envelope and frictionless separable platen contact retained.
No geometry/mesh changes, no repeated full import and no extra restraints.
Correction: KEYOPT4=2 nodal target-normal detection, with purepenalty1,
fixed KEYOPT10=1,FKN100 and FTOLN−1e−5 retained. NEQIT24 / NSUBST2,20,1 and
twoSMP were verified on the compliant recovery control. Aggressive NEQIT8
failed and was rejected. Two-core capability does not establish total license
entitlement or guarantee full-model speedup.

The primary reached native0.005% after7updates, then hit20.0424GiB during
the next factorization at422.151s. Its nativeRST had no readable data set,
and no restart frame was saved; actual read-only SET1,1 failed. This loss is
preserved. The conditional repair ends at that same known first increment,
with NSUBST1,1,1, OUTRES ALL ALL and a request for one explicit restart frame.
The conditional run stopped before that restart frame was written. A separate
8GiB POST1 process exports fields after solver exit. Small licensed testing
proved these output commands before the amended run.

Primary0.01% target remains unmet. Conditional target0.005% /0.000512mm.
Actual conditional process status{receipt['status']},
runtime{receipt['process']['runtime_seconds']:.3f}s,
peak sampled RSS{receipt['process']['peak_tree_rss_bytes']}bytes.
Completed Newton updates{len(telemetry['completed_iterations'])};
started factorizations{telemetry['factorizations_started']};
cutbacks{len(telemetry['cutback_events'])};
best force ratio{telemetry['best_force_ratio']};
last force ratio{telemetry['last_force_ratio']}.
Native converged records: {mechanics['logged_converged_substep_times']}.

The conditional log explicitly declares equilibrium convergence after7updates,
with native force ratio{telemetry['last_force_ratio']}. Its ordinary completed-
substep printout is absent because the memory stop occurred during output,
as the resident database grew from2048to4096MB. Read-only SET1,1 recovered
time0.00005 and actual nodal displacements. It did not recover reactions,
contact element results, stress or elastic strain. Ignored GET/VGET requests
left zero/sentinel arrays; these are unavailable data, not physical zeros.
The unchanged scientific gate failed and quarantined them.

Actual displacement-only diagnostics cover{displacement['actual_nodes']}nodes;
all deformed TRI6 mappings positive:{displacement['all_deformed_TRI6_mappings_positive']}.
This is not an accepted mechanical checkpoint. Native CND iteration7 reports
bottom internalFY{contact_evidence['bottom_contact_internal_y_N']}N and top
internalFY{contact_evidence['top_contact_internal_y_N']}N, with pair-force
imbalance{contact_evidence['pair_force_imbalance_relative']}. That is partial
force-transmission evidence, not an independent support-reaction check.
Primary NLHIST upperRF−0.06043442N is a genuine converged scalar, but the missing
lowerRF/fields prevent full mechanical qualification or stiffness assignment.

Accepted native checkpoints: {rows}.
Accepted endpoint maximum penetration: {str(maximum_pen)+' mm' if maximum_pen is not None else 'UNAVAILABLE'}.
Field and all-element deformed mapping checks: {mechanics['stage_fields']}.
These are actual native results only. Unavailable data remain unavailable.

Single-point preliminary secant modulus: {str(secant)+' MPa' if secant is not None else 'UNAVAILABLE'}.
Fitted initial modulus: {mechanics['effective_stiffness'].get('effective_modulus_MPa')}.
One nonzero accepted point does not establish an initial fitted modulus or a
complete stress–strain curve. The earlier converged substep history is retained
as native history; only checkpoints with complete validation enter mechanics.

The original1200s/20GiB caps,12GiB OS reserve and20GiB disk reserve were not
increased. Diagnostic cap2GiB /4native snapshots;32completed-update cap and
three-cutback cap. Stagnation requires24updates,onecutback and six current-trial
force evaluations; the first large residual cannot trigger it. Complete native
receipts, computed contact histories, residual localization and actual resource
samples are retained. The one conditional repair is the final full-model
attempt; no third run or additional parameter search was launched.
''')
    table='\n'.join('| '+k+' | '+v+' |' for k,v in acceptance.items())
    save('V0_6_4_VALIDATION.md',f'''# v0.6.4 scientific validation

## A. Executive summary

**{status}**. The evidence supports a contact-detection correction in the
compliant fixture. Full accepted checkpoint count:{len(rows)}. Native equilibrium at0.005%
was recovered, but full RF/contact/stress/strain writing failed under the20GiB
cap. Actual displacement-only diagnostics are quarantined from performance. Historical
contact trajectories remain unknown; current results do not rewrite them.

## B. Historical reconstruction

Both v063 runs reconstructed from actual saved evidence:9/14completedupdates,
no converged substep and no observed cutback before stop. Expensive iterations
and force stagnation were observed. Missing contact/residual telemetry was not
invented. See V0_6_4_FAILURE_FORENSICS.md.

## C. Root-cause hypotheses

All eight registered hypotheses and evidence limits are recorded in the
contact/constraint report and summary/hypotheses.json. Contact-detection
sensitivity is supported prospectively; the exclusive historical cause remains
UNRESOLVED. Resources now prevent complete output, rather than equilibrium.

## D. Diagnostic instrumentation

Native v241 telemetry was tested on the accepted rectangle and compliant
synthetic fixture. Native CND, NRRE, EFLG, NLHIST, logs and actual resource
samples were parsed with version-specific checks. See
V0_6_4_NONLINEAR_DIAGNOSTICS.md for commands, hashes and limitations.

## E. Contact analysis

Gauss detection reproduced failure with native chatter and platen-local FY
residuals. Both pairs retained active elements; total support loss was not
observed. Nodal detection passed the small fixture while retaining fixed PP100.
Some chatter persisted even in successful runs. Historical contact trajectories
were not recorded. Pair-level counts do not identify individual transitions.

## F. Structural and constraint analysis

Analytical rigid-motion rank and actual support listings were checked.
Distributed active normal constraints give rank3 on planar rigid motions;
both-open contact would leave insufficient support. No arbitrary springs or
extra specimen restraints were added. Full flexible modes remain unqualified;
absence of logged negative pivots does not prove their absence.

## G. Controlled experiments

Direct compression converged with different physical supports. Linearized
contact, smaller increments, updated stiffness and fixed FKN1 did not cure
the Gauss fixture. NEQIT8 failed even with nodal detection. All failed controls
are retained. The exact NEQIT24 recovery control passed with automatic
increment prediction and zero failed-trial bisections.

## H. Corrective action

Nodal target-normal detection passed the compliant fixture and matched
rectangle with the original physical assumptions and acceptance limits.
This justified KEYOPT4=2 while retaining fixed PP100, frictionless separable
contact and NLGEOM ON. Actual two-SMP controls preserved the rectangle response.

## I. Full-model retry

The primary reached equilibrium at 0.005% after seven updates, then stopped
at 20.0424 GiB and 422.151 s. Its RST had no readable data set. The conditional
technical repair repeated that known increment and announced equilibrium
after seven updates, then stopped during output at 20.3953 GiB and 333.559 s.
Neither run had a bisection. The memory guard was enforced with sampled
overshoot; the peak was not within the 20-GiB cap. Geometry, mesh and physical
assumptions were preserved. See V0_6_4_RECOVERY_EXPERIMENT.md and native receipts.

## J. Mechanical results

Status:{mechanics['status']}. Qualified registered checkpoints:{len(rows)}.
No fabricated midside stress, trial-state force curve or extrapolated loading.
There is no accepted point; both secant and fitted initial modulus are null.
The full stress–strain curve remains unavailable.

## K. Scientific limitations

Single geometrically qualified mesh; mechanical refinement convergence is
UNQUALIFIED. Internal self-contact is UNQUALIFIED_NOT_CONFIGURED. E,nu,scale,
thickness and plane stress are provisional and uncalibrated. No yielding,
fracture or pore-closure qualification. Historical small-pore fidelity and
production simplification HOLDs and documented15pixelrepair remain. This
milestone does not qualify paper conclusions, manufacturing or LLM ranking.

## L. Reproducibility and verification

{ap} active tests passed; {arp} archived fixture replay tests passed separately;
{lp} licensed diagnostic/evidence checks passed, {int(licensed['failures'])} failed.
Counts overlap and are not summed. Synthetic parser controls are not licensed
integration evidence. Historical files/protected paths remain unchanged.
Failed small controls, the monitor race and the initial header-rounding check
remain preserved. Native diagnostic bytes and all solver binaries remain in
the configurable local artifact root; tracked copies are explicitly normalized
text excerpts/receipts/compacttelemetry. Frozen full input/protocol are unchanged.

Execution commands and portable artifact-root handling are documented in
`docs/pipeline_v0.6.4/WINDOWS_EXECUTION.md`. The licensed failure is the actual
full mechanical-acceptance assertion; it is retained without weakening it.

Actual diagnostic figures (hashes in figures/figure_manifest.json):

- [Historical residuals and timing](figures/historical_failures.png)
- [Synthetic fixture and residual localization](figures/synthetic_fixture_and_residuals.png)
- [Small contact iteration diagnostics](figures/small_contact_iteration_diagnostics.png)
- [Controlled small experiments](figures/controlled_small_experiments.png)
- [Full convergence and resources](figures/full_recovery_diagnostics.png)
- [Full residual localization](figures/full_residual_localization.png)
- [Displacement-only diagnostic](figures/displacement_only_diagnostic.png)

Stress/strain fields, accepted contact fields and force/stress–strain curves
are unavailable and are not plotted.

## Independent acceptance

| Category | Status |
|---|---|
{table}

## M. Git commits

Started clean on master at224741cfec6f0fa4021f18e2f38624ce4210700d.
No push or history rewrite.

{ledgermd}

The final reporting commit contains this document; its exact hash is in the
final response/Git history, avoiding self-reference.

## N. Next milestone

{'Repeat the verified checkpoint under a new protocol, examine contact/increment sensitivity and independently accepted mechanical refinement levels, then build a sufficiently sampled small-strain response.' if valid else 'Register a memory/output diagnostic using a minimal required result set and separately reviewed one-SMP memory behavior; prove complete RF/contact/stress/strain writing and read-only extraction before another full study. Do not retune geometry/contact blindly or raise caps automatically.'}
Only after credible numerical/physical qualification should a controlled
multi-design dataset and reviewed LLM feedback protocol be considered. No
batch FEM, autonomous optimization,3D or manufacturing workflow was implemented.
''')
    unavailable='UNAVAILABLE — no accepted converged checkpoint'
    def value(key):return str(last[key]) if key in last else unavailable
    answers=[
        'Yes, independently from native inputs/logs/manifests/receipts; input hashes checked.',
        '9 and14 completed Newton updates; all force/displacement/line-search records retained in source order.',
        'Large initial reduction followed by force stagnation/oscillation; displacement criterion often passed.',
        'No historical cutback before stopping; neither reached NEQIT30.',
        'Initial trial strain0.00005/travel0.000512mm inferred from prescribed NSUBST2; independent historical trial telemetry absent.',
        'Yes, nonmonotone force stagnation/oscillation was observed.',
        'UNRESOLVED historically; native prospective small/full CND measures chatter/active counts, not individual element identities.',
        'Historical per-iteration values absent; actual prospective computed stiffness is captured; fixed baseline stays constant.',
        'No logged negative pivot/distortion before stop. Full flexible eigenmodes UNRESOLVED/not qualified.',
        'Rank3 on rigid-motion subspace when distributed contacts active; both-open support would be insufficient. No extra restraint added.',
        'No reported historical distortion failure before stop; accepted fields are independently checked where available.',
        'Historical force nonconvergence plus expensive iterations; exclusive historical contact cause UNRESOLVED. Prospective detection sensitivity supported.',
        'No observed RAM-cap failure; NLGEOM, step size or fixed stiffness alone do not explain/cure the fixture. Not every physical mode is ruled out.',
        'Per-iteration contact/chatter/gap/stiffness and spatial residual fields; monitor files had no completed-substep rows.',
        'NLDIAG CONT ITER, NRRE ON2, EFLG ON2; NLHIST pilot UY/RF; native logs/monitor and actual resource samples.',
        'Yes, actual ANSYS2024R1 small licensed jobs generated supported output; adjacent docs alone were not acceptance.',
        'Two retained native NR ring snapshots per run, original bytes local and compact spatial summaries tracked.',
        'Native CND pair iteration blocks, NR/EFLG, NLHIST and solver monitor/logs.',
        'Yes, native pair-level iteration counts/chatter/stiffness/gap/pressure/force; not exact per-element transition identities.',
        'Yes: true bisections in forced/failed controls; successful recovery control used prediction, not bisection. Correction audit012 retained.',
        'Yes, actual native node IDs/components associated with source mesh coordinates; internal/platen nodes excluded from specimen map.',
        'Primary354131439bytes; conditional'+str(inventory['bytes'])+'bytes retained diagnostics; per-file byte/hash inventories recorded.',
        'Diagnostic logging stayed below2GiB. Full process memory exceeded20GiB and was stopped by the guard; no budget-fit PASS is claimed.',
        'Yes; native rectangle residual norm checked against printed CNVV precision; initial rounding assertion failure retained.',
        'Accepted rectangle and deterministic compliant two-zigzag-strut fixture; reduced original specimen NOT EXECUTED/not necessary.',
        'Yes, instrumented rectangle and corrected matched rectangle passed unchanged force/contact gates.',
        'Yes, native contact chatter/platen-local FY residual and failure reproduced by Gauss PP100.',
        'Direct nonlinear synthetic compression converged; boundary conditions changed, so force magnitudes are not equivalent physics.',
        'Linearized synthetic contact also failed; NLGEOM alone was not a cure.',
        'Smaller increments alone failed; NEQIT8 harmed corrected convergence; tested24 permitted predicted increments and convergence.',
        'Fixed FKN100/update100/FKN1 were bounded negative controls; selected correction changes detection0to2 and retains fixedPP100.',
        'Actual chatter, residual localization and one-variable nodal-detection success, followed by matched rectangle/control validation.',
        'Only explicit direct diagnostic variant changes specimen restraints; full physical supports unchanged.',
        'Selected full correction changes numerical contact detection/iteration control/core count, not frictionless separable physical model.',
        'Gauss failed; nodal target-normal correction alone passed fixture, then rectangle and exact recovery controls.',
        'Yes: one primary plus one prospectively amended technical repair allowed by user section21; no third full run.',
        'Committed causal small evidence and prospectively frozen FULL_RECOVERY_001 input/protocol.',
        'Yes, exact historical semantic hash preserved.', 'Yes, original412pores retained.', 'Yes, plane-stress six-node PLANE183 retained.',
        'Frictionless separable CONTA172/TARGE169, purepenalty1, fixed KEYOPT10=1,FKN100,FTOLN−1e−5,KEYOPT4=2.',
        'Primary0.01% target unmet; conditional known-state checkpoint0.005% /0.000512mm.',
        str(minimum_increment)+' smallest actual conditional pseudo-time increment; native increment records retained.',
        str(len(telemetry['completed_iterations']))+' completed Newton updates; final force/convergence evaluations separately recorded.',
        str(len(telemetry['cutback_events'])),'Force0.0004086N / criterion0.0004287N = '+str(telemetry['best_force_ratio'])+'.',
        'Yes, native nonzero substeps '+str(first_times)+'.' if first_times else 'No converged nonzero substep.',
        'Registered checkpoint accepted; broader qualification remains limited.' if valid else 'Native equilibrium reached, but output-memory stop left RF/contact/stress/strain unavailable; gate rejected zero/sentinel exports.',
        f"{receipt['process']['runtime_seconds']:.3f}s conditional run; primary422.151s.",str(receipt['process']['peak_tree_rss_bytes'])+'bytes conditional tree RSS; primary20.0424GiB triggered20GiB guard.',
        'Memory caps were crossed:20.0424/20.3953GiB peaks triggered guarded stops; sampled overshoot retained. Diagnostic output stayed below2GiB; time caps were not reached.',
        'Yes, accepted checkpoint contact-element forces oppose actual support reactions.' if valid else 'Native CND shows both nonzero pair forces; independent support-RF/endpoint checks remain incomplete.',
        str([last.get('upper_rf_y_N'),last.get('lower_rf_y_N')]) if valid else 'Primary NLHIST upperRF−0.06043442N available; independently verified lowerRF unavailable. RST zero defaults quarantined.',
        'Independent support-reaction balance UNAVAILABLE; native contact-pair force imbalance0.5104% is diagnostic only.' if not valid else value('reaction_balance_relative')+' normalized reaction imbalance.',
        str(maximum_pen)+'mm accepted stored-endpoint maximum; no continuous-surface bound claimed.' if valid else 'Native iteration7 penetration1.320076e−9mm; qualified RST endpoint penetration UNAVAILABLE.',
        'Every deformed TRI6 mapping positive under analytic floating-point check.' if valid else 'Actual displacement-only diagnostic has positive mapping for every TRI6; full mechanical validation remains incomplete.',
        'Yes, complete all-node UX/UY.' if valid else 'Actual all-node displacement recovered/checked, explicitly diagnostic-only; no fully qualified mechanical checkpoint.',
        'Yes, supported corner-node averages; no fabricated midside stress.' if valid else unavailable,
        'Yes, supported corner-node elastic strain.' if valid else unavailable,
        str(first_strain)+' first native converged engineering strain; registered accepted checkpoint '+value('engineering_compression_strain')+'.',
        'Yes, one accepted registered force/travel measurement.' if valid else unavailable,
        'Yes, one accepted registered nominal stress/engineering strain measurement.' if valid else unavailable,
        'No fitted initial modulus from one accepted point; preliminary secant '+str(secant)+'MPa.' if valid else 'No modulus justified.',
        'Yes. Native equilibrium is distinct from accepted mechanics; both secant and fitted modulus are null.',
        'UNQUALIFIED; single mesh.', 'UNQUALIFIED_NOT_CONFIGURED; platen contact only.',
        str(ap),str(arp)+' separately; suites overlap.',str(lp)+'passed /'+str(int(licensed['failures']))+'failed licensed checks; synthetic parser tests excluded.',
        'Yes, all historical failures preserved.', 'Yes, source/semantic hashes unchanged.',
        'Additive diagnostic modules/scripts/tests/protocols/evidence/reports/figures; exact inventory in summary/change_inventory.json.',
        'Coherent commits listed in validation JSON/report; final report commit in Git history/final response.',
        'Actual hashes and exact messages listed in validation report and final response.',
        'Verified after final commit; final response states actual result.', 'No push to GitHub.',
        status,
        'Historical exclusive cause UNRESOLVED; prospective detection sensitivity isolated in fixture and native full equilibrium recovered, but mechanics unqualified.',
        'Resolved at one registered nonzero checkpoint only.' if valid else 'Native equilibrium recovered at0.005%; complete mechanical result recovery NOT resolved.',
        'No full-curve/refinement qualification; memory/result-output completion and field qualification remain.' if valid else '20GiB output-phase memory stop and missing native RF/contact/stress/strain prevent acceptance, despite readable displacement and native convergence.',
        'Yes, preliminary single-mesh checkpoint data with provisional assumptions.' if valid else 'Convergence/contact/displacement diagnostics only; no accepted mechanical-performance dataset.',
        'No, not yet eligible for LLM performance ranking.', 'No, first repeat/check sensitivity/refinement before complete stress–strain study.',
        'Single mesh, bounded contact sensitivity, flexible modes not eigenqualified, limited loading, no internal contact.',
        'E1000MPa,nu0.3,scale/thickness,plane stress and homogeneous elasticity remain provisional; no experimental calibration/yield/fracture.',
        'Repeat/checkpoint-contact sensitivity and accepted-mesh mechanical refinement before a sampled stress–strain study.' if valid else 'Bounded minimal-output/memory verification, then complete native-field capture under a new protocol; no third run in this milestone.'
    ]
    assert len(answers)==86,len(answers)
    save('V0_6_4_HANDOFF.md','# v0.6.4 requested86-item scientific handoff\n\nAll values are actual evidence or explicitly unavailable.\n\n| # | Answer |\n|---:|---|\n'+'\n'.join('| '+str(i)+' | '+a.replace('|','/')+' |' for i,a in enumerate(answers,1)))
    write_json(RUN/'figures/figure_manifest.json',{'actual_figures':{p.name:file_hash(p) for p in (RUN/'figures').glob('*.png')},'native_result_RST_sha256':mechanics['result_RST_sha256'],'source_geometry_sha256':audit['source_geometry_sha256'],'mesh_semantic_sha256':audit['mesh_semantic_sha256'],'limits':'Only accepted checkpoint fields render as mechanics; NR/CND trial figures explicitly diagnostic. No invented intermediate stress-strain data.'})
    return report


if __name__=='__main__':foundation_figures()
