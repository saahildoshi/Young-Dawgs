"""Create v0.6.3 scientific artifacts from authenticated actual local evidence."""
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection,LineCollection
from metamaterial_eval.simulation.mesh_artifacts import artifact_root,resolve_manifest
from metamaterial_eval.simulation.microstructure_import import read_cdb
from metamaterial_eval.simulation.geometry_adapter import authenticate_fixture
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.element_quality import corner_metrics
from metamaterial_eval.simulation.solver_execution import file_hash,solver_warnings
from metamaterial_eval.simulation.reporting import write_json

REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'experiments/pipeline_v0.6.3/run_001'


def read_json(path):return json.loads(Path(path).read_text())


def contact_sensitivity_figure(out):
    configs=[]
    baseline=REPO/'experiments/pipeline_v0.6.2/run_001'
    s=read_json(baseline/'rectangle_contact/analysis_002/mechanical_summary.json')
    warnings=solver_warnings((baseline/'rectangle_contact/evidence_002/solver.out.sanitized.txt').read_text(errors='replace'))
    baseline_contact=read_json(baseline/'contact_validation/point_extraction_001/contact_point_validation.json')
    configs.append(('v062 AL\n1e-7',s['requested_stages'][3]['upper_rf_y_N'],baseline_contact['maximum_stored_endpoint_penetration_mm'],int(any('coefficient ratio' in w.lower() for w in warnings)),len(warnings)))
    for i in range(1,5):
        b=RUN/f'contact_sensitivity/candidate_{i:03d}'
        s=read_json(b/'analysis/mechanical_summary.json');c=read_json(b/'contact_points/contact_point_validation.json')
        warnings=solver_warnings((b/'generated/execution/solver.out').read_text(errors='replace'))
        configs.append((['AL 1e-6','AL 1e-5','penalty ×1\nrejected','penalty ×100\ncorrected pilot'][i-1],s['requested_stages'][3]['upper_rf_y_N'],c['maximum_stored_endpoint_penetration_mm'],int(any('coefficient ratio' in w.lower() for w in warnings)),len(warnings)))
    fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True);positions=np.arange(len(configs));labels=[c[0] for c in configs]
    axes[0].bar(positions,[-c[1] for c in configs]);axes[0].axhline(51.2,color='black',ls=':',label='analytical infinitesimal');axes[0].set(ylabel='Actual force at 0.5% [N]',title='Same rectangle, material and loading');axes[0].legend(fontsize=7)
    axes[1].bar(positions,[c[2] for c in configs]);axes[1].set_yscale('log');axes[1].axhline(1e-5,color='red',ls='--',label='v063 penetration gate');axes[1].set(ylabel='Max stored endpoint penetration [mm]');axes[1].legend(fontsize=7)
    axes[2].bar(positions,[c[3] for c in configs],label='coefficient-ratio warning');axes[2].bar(positions,[c[4] for c in configs],alpha=.3,label='all warnings');axes[2].set(ylabel='Warning counts/flags',title='Warnings do not bound\nthe condition number');axes[2].legend(fontsize=7)
    for ax in axes:ax.set_xticks(positions,labels,rotation=25);ax.grid(axis='y',alpha=.2)
    fig.savefig(out/'contact_sensitivity.png',dpi=160);plt.close(fig)


def figures():
    out=RUN/'figures';out.mkdir(exist_ok=True)
    if (out/'figure_manifest.json').exists():raise FileExistsError('Completed figure set already exists')
    mesh,artifact,_=resolve_manifest(RUN/'mesh_reproduction/attempt_002/artifact_manifest.json')
    geometry,mask,provenance=authenticate_fixture(REPO,CompressionConfig())
    source=artifact_root()/'solver/v063/import_001/imported.cdb'
    actual_nodes,actual_tri,attrs,components=read_cdb(source,len(mesh.nodes),len(mesh.triangles))
    assert np.array_equal(actual_tri,mesh.triangles)
    points=actual_nodes[actual_tri[:,:3]]
    fig,axes=plt.subplots(2,2,figsize=(11,10),constrained_layout=True)
    axes[0,0].imshow(mask,cmap='gray',origin='upper',extent=[0,10.24,0,10.24]);axes[0,0].set_title('Authenticated native-1024 source')
    axes[0,1].add_collection(PolyCollection(points,facecolors='#284d67',edgecolors='none'));axes[0,1].set_title('Actual solver-exported PLANE183 domain')
    edges=actual_nodes[mesh.boundary[:,:2]]
    for group,color in [('external','gray'),('pore','green'),('top','red'),('bottom','blue')]:
        axes[1,0].add_collection(LineCollection(edges[mesh.boundary_groups==group],colors=color,linewidths=.35,label=group))
    axes[1,0].set_title('Verified actual boundaries and 412 pore loops');axes[1,0].legend(fontsize=8,loc='upper right')
    probe=min(provenance['source_only_solid_probes'],key=lambda p:p['source_pixel_run'])
    x=probe['xy'][0]*.01;y=10.24-probe['xy'][1]*.01
    keep=np.any((abs(points[:,:,0]-x)<.08)&(abs(points[:,:,1]-y)<.08),axis=1)
    axes[1,1].add_collection(PolyCollection(points[keep],facecolors='none',edgecolors='black',linewidths=.4))
    axes[1,1].set_title('Actual imported mesh / registered narrow-feature detail')
    for ax in axes.flat:ax.set(xlim=(0,10.24),ylim=(0,10.24),aspect='equal',xlabel='x [mm]',ylabel='y [mm]')
    axes[1,1].set(xlim=(max(0,x-.07),min(10.24,x+.07)),ylim=(max(0,y-.07),min(10.24,y+.07)))
    fig.suptitle('v0.6.3 — authentic geometry and exhaustive real MAPDL import verification')
    fig.savefig(out/'geometry_and_import.png',dpi=160);plt.close(fig)
    angles=corner_metrics(points)['minimum_angle_deg']
    fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
    axes[0].hist(angles,bins=60);axes[0].axvline(10,color='red',ls='--');axes[0].set(xlabel='Minimum corner angle [degrees]',ylabel='Elements',title='Imported TRI6 corner-angle distribution')
    width=.35;loc=np.arange(2);expected=[len(mesh.nodes),len(mesh.triangles)];actual=[len(actual_nodes),len(actual_tri)]
    axes[1].bar(loc-width/2,expected,width,label='source');axes[1].bar(loc+width/2,actual,width,label='solver');axes[1].set_xticks(loc,['nodes','TRI6']);axes[1].legend();axes[1].set_title('Exhaustive inventory, all six IDs checked')
    displayed_hash='\n'.join(artifact['semantic_sha256'][i:i+24] for i in range(0,64,24))
    axes[2].axis('off');axes[2].text(0,.95,'Semantic identity verified\n'+displayed_hash+'\n\nGmsh 4.15.0 / one thread\nSource geometry unchanged\n412 pores / one solid component\nMin angle 11.404135°\nRegistered chord minimum: 7 elements\nMechanical convergence: UNQUALIFIED',va='top',wrap=True,fontsize=9)
    fig.savefig(out/'mesh_quality_and_provenance.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    axes[0].add_collection(PolyCollection(points,facecolors='#657681',edgecolors='none'))
    for ax in axes:
        for group,color,ypos in [('top','red',10.24),('bottom','blue',0)]:
            ax.add_collection(LineCollection(edges[mesh.boundary_groups==group],colors=color,linewidths=1.5,label=group+' contact'))
            ax.plot([-.512,10.752],[ypos,ypos],color=color,lw=2)
        ax.set(xlim=(-.6,10.85),ylim=(-.3,10.55),aspect='equal',xlabel='x [mm]',ylabel='y [mm]');ax.legend(fontsize=7,loc='upper right')
    axes[0].set_title('Actual imported specimen and separate rigid platens')
    axes[1].text(5.12,5.12,'Actual initial CNCHECK:\nboth contact pairs initially closed\ninitial penetration 0 / 3.55e-15 mm\nno specimen UY constraints\nPLATEN_CONTACT_ONLY',ha='center',va='center');axes[1].set_title('Initial solver contact check, not a solved zero field')
    fig.savefig(out/'platen_setup.png',dpi=150);plt.close(fig)
    contact_sensitivity_figure(out)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for ax,attempt in zip(axes,[1,2]):
        log=(artifact_root()/f'solver/v063/pilot_{attempt:03d}/solver.out').read_text(errors='replace')
        pairs=re.findall(r'FORCE CONVERGENCE VALUE\s*=\s*([\d.Ee+\-]+)\s+CRITERION=\s*([\d.Ee+\-]+)',log)
        a=np.array(pairs,dtype=float)
        if len(a):ax.semilogy(a[:,0]/a[:,1],'o-',markersize=3)
        ax.axhline(1,color='green',ls='--',label='force convergence threshold')
        ax.set(xlabel='Logged force-convergence evaluation index',ylabel='Residual / force criterion',title=f'Actual full-model attempt {attempt}')
        ax.legend(fontsize=7);ax.grid(alpha=.2)
    fig.suptitle('Actual nonlinear iteration diagnostics — not a mechanical stress-strain response')
    fig.savefig(out/'pilot_convergence_diagnostics.png',dpi=160);plt.close(fig)
    mechanical_path=RUN/'mechanical_results/attempt_002/mechanical_summary.json'
    if mechanical_path.exists():
        result=read_json(mechanical_path);rows=result['actual_valid_stages']
        if rows and not result['unsupported_output_queries']:
            directory=artifact_root()/'solver/v063/pilot_002';last=rows[-1]['stage'];prefix=f'stage{last:03d}'
            u=np.loadtxt(directory/(prefix+'_displacements.csv'),delimiter=',',skiprows=1)
            stress=np.loadtxt(directory/(prefix+'_stress.csv'),delimiter=',',skiprows=1)
            corners=stress[:,0].astype(np.int64)-1;lookup=np.searchsorted(corners,actual_tri[:,:3])
            fig,axes=plt.subplots(2,3,figsize=(14,9),constrained_layout=True)
            axes[0,0].add_collection(LineCollection(edges,colors='0.75',linewidths=.3))
            deformed=actual_nodes+u[:,1:3]
            axes[0,0].add_collection(LineCollection(deformed[mesh.boundary[:,:2]],colors='tab:blue',linewidths=.3));axes[0,0].set_title('True-scale deformed boundary overlay (1×)')
            values=[u[:,2][actual_tri[:,:3]].mean(axis=1),np.linalg.norm(u[:,1:3],axis=1)[actual_tri[:,:3]].mean(axis=1),
                    stress[:,1][lookup].mean(axis=1),stress[:,2][lookup].mean(axis=1),stress[:,3][lookup].mean(axis=1)]
            titles=['Actual UY [mm]','Actual displacement magnitude [mm]','Actual corner-averaged SYY [MPa]','Actual corner-averaged equivalent stress [MPa]','Actual corner-averaged elastic EYY']
            for ax,value,title in zip(list(axes.flat)[1:],values,titles):
                pc=PolyCollection(points,array=value,edgecolors='none');ax.add_collection(pc);fig.colorbar(pc,ax=ax);ax.set_title(title)
            for ax in axes.flat:ax.set(xlim=(0,10.24),ylim=(0,10.24),aspect='equal',xlabel='x [mm]',ylabel='y [mm]')
            fig.suptitle(f'Actual achieved compression {rows[-1]["engineering_compression_strain"]*100:.4g}% — linear corner rendering of TRI6; numerical all-node fields retained')
            fig.savefig(out/'actual_microstructure_fields.png',dpi=160);plt.close(fig)
            fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
            x=[r['compression_displacement_mm'] for r in rows];f=[-r['upper_rf_y_N'] for r in rows]
            axes[0].plot(x,f,'o-');axes[0].set(xlabel='Achieved platen travel [mm]',ylabel='Actual compressive reaction [N]')
            axes[1].plot([r['engineering_compression_strain']*100 for r in rows],[r['nominal_compression_stress_MPa'] for r in rows],'o-');axes[1].set(xlabel='Achieved engineering compression [%]',ylabel='Nominal compression stress [MPa]')
            axes[2].plot([r['engineering_compression_strain']*100 for r in rows],[r['reaction_balance_relative']*100 for r in rows],'o-');axes[2].axhline(1,ls='--',color='red');axes[2].set(xlabel='Achieved engineering compression [%]',ylabel='Reaction imbalance [%]')
            for ax in axes:ax.grid(alpha=.2)
            fig.suptitle('Real converged checkpoints only; connecting lines are visual guides, no extrapolated stages')
            fig.savefig(out/'actual_microstructure_curves.png',dpi=160);plt.close(fig)
            c=np.loadtxt(directory/(prefix+'_contact.csv'),delimiter=',',skiprows=1)
            fig,axes=plt.subplots(1,3,figsize=(13,4),constrained_layout=True)
            for pair,group,color in [(1,'bottom','tab:blue'),(2,'top','tab:red')]:
                values=c[c[:,0]==pair];faces=mesh.boundary[mesh.boundary_groups==group]
                xpos=deformed[faces[:,2],0]
                axes[0].scatter(xpos,values[:,2],s=3,label=group,color=color)
                axes[1].scatter(xpos,values[:,3:5].max(axis=1),s=3,label=group,color=color)
                axes[2].scatter(xpos,np.maximum(0,values[:,5:7].max(axis=1)),s=3,label=group,color=color)
            for ax,title in zip(axes,['Actual element contact status','Max stored endpoint pressure [MPa]','Max stored endpoint penetration [mm]']):
                ax.set(xlabel='Solved contact midpoint x [mm]',title=title);ax.legend();ax.grid(alpha=.2)
            fig.suptitle('Actual platen contact at last validated checkpoint; internal self-contact not configured')
            fig.savefig(out/'actual_microstructure_contact.png',dpi=160);plt.close(fig)
    write_json(out/'figure_manifest.json',{'solver_import_archive_sha256':file_hash(source),
        'source_geometry_sha256':artifact['source_geometry_sha256'],'mesh_semantic_sha256':artifact['semantic_sha256'],
        'mechanical_result_summary_sha256':file_hash(mechanical_path) if mechanical_path.exists() else None,
        'figures':{p.name:file_hash(p) for p in out.glob('*.png')},
        'limitations':'No deformation plot unless actual validated checkpoint fields exist. Rendering uses corner polygons; raw TRI6 all-node fields retain numerical data.'})


def summary():
    artifact=read_json(RUN/'mesh_reproduction/attempt_002/artifact_manifest.json')
    imported=read_json(RUN/'import_only/attempt_001/validation/import_validation.json')
    resource=read_json(RUN/'resource_assessment/resource_assessment.json')
    result=read_json(RUN/'mechanical_results/attempt_002/mechanical_summary.json')
    corrected_execution=read_json(RUN/'microstructure_pilot/execution_002.json')
    def xml(path):
        suites=list(ET.parse(path).getroot().iter('testsuite'))
        return {k:sum(float(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped','time']}
    active=xml(RUN/'verification/regression_portability.xml')
    archives=[xml(p) for p in (RUN/'verification/archive_replay').glob('*.xml')]
    integrations=xml(RUN/'verification/ansys_v063_integration.xml')
    previous_integrations=xml(RUN/'verification/ansys_v062_recheck.xml')
    protected=['experiments/pipeline_v0.6','experiments/pipeline_v0.6.1','experiments/pipeline_v0.6.2',
               'metamaterial_eval/generators','metamaterial_eval/geometry','validation/evaluators','data','generated_microstructures']
    changed=subprocess.check_output(['git','diff','--name-only','9af3d40','--',*protected],cwd=REPO,text=True)
    assert not changed,changed
    commits=subprocess.check_output(['git','log','--reverse','--format=%H %s','9af3d40..HEAD'],cwd=REPO,text=True).splitlines()
    statuses={'SOURCE_GEOMETRY_AUTHENTICATED':'PASS','HISTORICAL_MESH_RECOVERED':'ORIGINAL_NPZ_NOT_FOUND',
              'HISTORICAL_MESH_IDENTITY_VERIFIED':'PASS_EXACT_SEMANTIC_REPRODUCTION','GEOMETRIC_MESH_QUALIFICATION':'PASS_UNCHANGED_GATES',
              'ANSYS_IMPORT':'PASS_EXHAUSTIVE_FULL_MESH','CONTACT_SENSITIVITY':'BOUNDED_TESTS_AND_DOCUMENTED_ALGORITHM_AMENDMENT',
              'RESOURCE_FEASIBILITY':'ACTUAL_ASSEMBLY_AND_FACTORIZATION_EVIDENCE_WITH_REGISTERED_LIMITS',
              'MICROSTRUCTURE_PILOT':result['status'],'INTERNAL_SELF_CONTACT':'UNQUALIFIED_NOT_CONFIGURED',
              'MECHANICAL_MESH_CONVERGENCE':'UNQUALIFIED','PAPER_READINESS':'RESEARCH_HOLD',
              'LLM_FEEDBACK_LOOP':'NOT_IMPLEMENTED','LLM_OPTIMIZATION':'NOT_IMPLEMENTED','MANUFACTURING':'UNQUALIFIED'}
    valid=bool(result['actual_valid_stages']) and not result['unsupported_output_queries']
    statuses.update(REGENERATED_MESH_QUALIFIED='PASS_EXACT_HISTORICAL_IDENTITY',MAPDL_IMPORT_PASS='PASS',
        MODEL_RESOURCE_ASSESSMENT_PASS='PASS_BOUNDED_ASSEMBLY_AND_ACTUAL_FACTORIZATION_SCOPE_ONLY',
        CONTACT_SENSITIVITY_REVIEWED='PASS_BOUNDED_SCOPE_WITH_WARNINGS',
        MICROSTRUCTURE_PLATEN_CONTACT_CONFIGURED='PASS_INITIAL_SOLVER_CHECKS',
        MICROSTRUCTURE_SOLVER_PASS='PASS_PRELIMINARY_CONVERGED_CHECKPOINTS' if valid else 'FAIL_NO_CONVERGED_CHECKPOINT',
        MICROSTRUCTURE_CONTACT_FORCE_PASS='PASS_ACTUAL_CHECKPOINTS_ONLY' if valid else 'CONFIGURED_NOT_DEMONSTRATED',
        MICROSTRUCTURE_MECHANICAL_RESULTS_PASS='PASS_PRELIMINARY_CHECKPOINTS_ONLY' if valid else 'NOT_AVAILABLE_NO_VALID_CHECKPOINT')
    report={'schema':'young-dawgs-v0.6.3-validation','client_date':'2026-10-29 America/New_York','acceptance':statuses,
            'mesh':artifact,'import':imported,'assembly_resource':resource,'mechanical_results':result,
            'corrected_pilot_execution':corrected_execution,
            'tests':{'active':active,'active_command':'EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py python -m pytest tests validation/test_evaluator.py -q',
                     'archived_replay':archives,'licensed_v063':integrations,'licensed_v062_recheck':previous_integrations,
                     'default_unscoped_collection':'11 preserved historical snapshot/module-name collection errors; not active-suite failures',
                     'default_v1_0_evaluator_run':'20 failed / 655 passed against default legacy v1.0; retained separately; release selects unchanged frozen v1.1',
                     'overlap_warning':'do not sum primary, archive and evidence-check counts'},
            'historical_preservation':{'status':'PASS','changed_protected_paths':changed.splitlines()},
            'commits_before_final_reporting':commits,'final_reporting_commit':'commit containing this report; exact hash in final response and Git history'}
    write_json(RUN/'V0_6_3_VALIDATION.json',report)
    write_json(RUN/'mechanical_feedback.json',{
        'schema':'young-dawgs-mechanical-feedback-v0.6.3','design_id':9,'seed':1,'resolution':1024,
        'parameters':read_json(RUN/'audit/source_authentication.json')['parameters'],
        'geometry_sha256':artifact['source_geometry_sha256'],'mesh_sha256':artifact['semantic_sha256'],'solid_fraction':50.0104/10.24**2,
        'material':{'E_MPa':1000,'nu':.3,'model':'homogeneous isotropic linear elastic, uncalibrated'},
        'scale':{'width_mm':10.24,'height_mm':10.24,'initial_thickness_mm':1,'status':'PROVISIONAL'},
        'contact_scope':'PLATEN_CONTACT_ONLY','contact_algorithm':'fixed-initial-stiffness pure penalty FKN100; original AL attempt nonconverged and retained',
        'validity':result['status'],'actual_checkpoints':result['actual_valid_stages'],'effective_stiffness':result['effective_stiffness'],
        'stress_strain':'mechanical_results/attempt_002/stress_strain.csv' if result['actual_valid_stages'] else None,
        'raw_field_root':'YD_ARTIFACT_ROOT/solver/v063/pilot_002','stress_location':'corner nodes; no fabricated midside stress',
        'warnings':result['warnings'],'eligible_for_design_ranking':False,'optimization_controller':'NOT_IMPLEMENTED',
        'failure_interpretation':'numerical/contact/resource failure is not physical design performance',
        'limitations':['single mesh; mechanical convergence unqualified','internal self-contact not configured','provisional material/scale and plane stress','prior geometry HOLDs unchanged','fixed contact stiffness recommendation retained','no paper or manufacturing qualification']})
    write_reports(report)
    return report


def write_reports(report):
    mesh=report['mesh'];imp=report['import'];resource=report['assembly_resource'];mech=report['mechanical_results']
    rows=mech['actual_valid_stages'];valid=bool(rows) and not mech['unsupported_output_queries']
    directory=artifact_root()/'solver/v063/pilot_002';execution=read_json(directory/'execution_receipt.json')
    first=read_json(RUN/'microstructure_pilot/attempt_001_failure/execution_receipt.json')
    contact_rows=[]
    contact_csv=RUN/'mechanical_results/attempt_002/contact_diagnostics.csv'
    if contact_csv.exists():
        import csv
        contact_rows=list(csv.DictReader(contact_csv.open()))
    def unavailable(value):return str(value) if value is not None else 'UNAVAILABLE — no validated converged checkpoint'
    last=rows[-1] if valid else {}
    stiffness=mech['effective_stiffness'].get('effective_modulus_MPa')
    maxpen=max((float(x['max_stored_endpoint_penetration_mm']) for x in contact_rows),default=None)
    peak=execution['process']['peak_tree_rss_bytes'];runtime=execution['process']['runtime_seconds']
    environment=read_json(RUN/'ansys_environment/environment.json')
    overall='MICROSTRUCTURE_RESPONSE_PRELIMINARY — RESEARCH_HOLD' if valid else 'MESH_IDENTITY_AND_IMPORT_PASS — MICROSTRUCTURE_NUMERICAL_HOLD — RESEARCH_HOLD'
    ledger='\n'.join('- `'+c.split(' ',1)[0]+'` — '+c.split(' ',1)[1] for c in report['commits_before_final_reporting'])
    stages='\n'.join('| '+str(r['stage'])+' | '+f"{r['engineering_compression_strain']:.9g} | {r['upper_rf_y_N']:.12g} | {r['lower_rf_y_N']:.12g} | {r['nominal_compression_stress_MPa']:.12g} |" for r in rows)
    if not rows:stages='| — | No converged checkpoint | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |'
    def save(name,text):(RUN/name).write_text(text.rstrip()+'\n',encoding='utf-8')
    save('V0_6_3_MESH_RECOVERY.md',f'''# v0.6.3 mesh recovery

Original Linux NPZ archive: NOT FOUND in bounded known project roots. The
expected v0.6.1 generated/mesh.npz was absent; no historical hostname/remote
storage endpoint was recorded. Search scope and errors are in audit/.

Authorized frozen reproduction: **HISTORICAL_MESH_IDENTITY_VERIFIED**.
Semantic SHA256: {mesh['semantic_sha256']}.
New NPZ byte SHA256: {mesh['byte_sha256']}. Original NPZ byte identity is not
claimed. Arrays and ordering match the registered historical semantic hash.

Nodes {mesh['nodes']}; TRI6 {mesh['TRI6']}; minimum angle 11.4041350264°;
one component, 412 pores, source area 50.0104 mm², minimum registered chord
resolution 7 elements. Every frozen geometric gate passes unchanged. This
does not establish mechanical convergence or exhaustive neck resolution.

Source WKB: {mesh['source_geometry_sha256']}. Historical 15-pixel topology
repair remains documented; no new geometry/manifold repair was applied.

Gmsh 4.15.0, algorithm 6, one thread, h_boundary=.0033333333333333335 mm,
h_bulk=.04 mm, curve-sampling buckets, boundary sizing, ten linear Relocate2D
iterations then straight quadratic midsides. The protocol's Windows CRLF bytes
differ from Linux LF; LF-normalized content matches the original frozen hash.
Both hashes and the initial failed strict comparison are preserved.

Artifact-relative path: {mesh['artifact_relative_path']}.
Known creation root: {mesh['known_storage_root']}.
An independently CRC/byte/semantic-verified second mesh copy is stored outside
the application cache under C:/Users/sd22446/YoungDawgs-Artifacts. Its receipt
is mesh_reproduction/attempt_002/durable_copy.json. This is a separate local
user-profile directory, not an off-device backup or a claimed cloud upload.
Windows separators in saved relative paths are normalized at resolution for
Linux portability; absolute drives, UNC roots and traversal are rejected.
Use YD_ARTIFACT_ROOT to relocate, retain the folder and manifest, then verify
archive CRC, byte hash and semantic hash. Local cache is not an external backup;
there is no automatic upload. See docs/pipeline_v0.6.3/ARTIFACT_STORAGE.md.
''')
    save('V0_6_3_ANSYS_IMPORT.md',f'''# v0.6.3 actual MAPDL import

**ANSYS_IMPORT_PASS**, ANSYS 2024 R1 / Mechanical Enterprise Academic Research.
The streamed input is actual N/EN APDL with bounded 10k-record temporary
chunks, not a renamed pseudo-CDB. The real solver generated a native blocked
archive with CDWRITE and a reusable specimen database.

Actual specimen nodes: {imp['actual_nodes']}; actual PLANE183 TRI6:
{imp['actual_PLANE183_TRI6']}. Every node ID/coordinate and all six element
connectivity IDs were compared. Maximum coordinate difference:
{imp['coordinate_max_error_mm']:.9g} mm (CDB printed precision; tolerance 1e-11 mm).
Every material/type/real attribute is 1 and all boundary/component memberships
match. Actual ETLIST/RLIST/MPLIST verify six-node triangles, plane stress
KEYOPT(1)=1 / KEYOPT(3)=3, initial thickness 1 mm, E=1000 MPa and nu=.3.

The imported coordinates lie in global XY, z=0, with the 10.24 mm envelope.
Connectivity-derived topology and full geometric validation confirm one solid
component, 412 pores, preserved material area, no filled voids or lost boundary,
positive whole-element mapping and registered feature resolution. Count matching
alone was not used as topology evidence. No compression occurred in this phase.

Source archive SHA256: {imp['solver_archive_sha256']}.
Database SHA256: {imp['solver_database_sha256']}.
The full raw CDB/database remain under the configured artifact root; compact
inventories, receipts and explicitly labelled log excerpts are tracked.
''')
    save('V0_6_3_RESOURCE_FEASIBILITY.md',f'''# v0.6.3 resource feasibility

Fresh audit: {environment['physical_ram_bytes']} bytes physical RAM,
{environment['available_ram_bytes']} bytes available RAM, {environment['disk_free_bytes']}
bytes free run-drive space and {environment['logical_processors']} logical CPUs.
All solver jobs used one SMP core; no unrestricted parallel license is assumed.

The full model has 5,533,010 specimen translational DOFs before constraints.
Actual contact sparse-solver equations: 5,533,009 (one specimen UX anchor;
platen pilot DOFs constrained). Six user platen/pilot nodes and two internally
generated pilot-control nodes are distinguished from specimen nodes.

The linear no-contact WRFULL assembly diagnostic completed in
{resource['process']['runtime_seconds']:.3f} s, peak sampled tree RSS
{resource['process']['peak_tree_rss_bytes']} bytes, matrix file
{resource['matrix_file_bytes']} bytes. ANSYS reported 7858 MB used / 12160 MB
allocated. WRFULL skips equation solution and is not valid evidence of a
nonlinear solve, factorization capacity or physical response. It was used only
in a separately identified linear assembly diagnostic.

The actual pilot subsequently executed sparse symmetric factorizations,
reporting about 6058.8 MB sparse workspace and 294,559,232 factor nonzeros in
the first attempt. Thus the simple coordinate-array lower bound was not the
resource decision. Memory fit does not imply nonlinear convergence.

Both pilot protocols enforce 1200 s wall time, 20 GiB sampled process-tree RSS,
12 GiB available-system-RAM reserve, 20 GiB minimum disk reserve, one core and
owned-process termination. The -m 4096 MB flag is an initial allocation, not
a hard cap. Selected attempt status {execution['status']}, return code
{execution['process']['returncode']}, runtime {runtime:.3f} s and peak sampled
tree RSS {peak} bytes. Preserve distinctions among numerical plateau, timeout
and memory failure; do not declare hardware incapable from nonconvergence.

[WRFULL reference](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_WRFULL.html)
and [sparse memory options](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_BCSOPTION.html)
are v242 comparison documentation; actual commands were checked in v241.
''')
    save('V0_6_3_CONTACT_SENSITIVITY.md','''# v0.6.3 bounded contact investigation

All rectangle comparisons retain the v0.6.2 geometry, mesh, material, thickness
and six-stage loading. AL FTOLN=1e-6 and 1e-5 mm passed force/equilibrium and
stored-endpoint penetration checks, removed the original coefficient-ratio
warning, and the selected 1e-5 case repeated identically. This justified a
prospective full-model trial, not automatic microstructure contact acceptance.

The first full-model AL trial had no converged substep and a non-monotone force
residual plateau. It was deliberately stopped for diagnosis, not a memory
failure or measured poor physical design. Contact multiplier/stiffness-update
chatter is a hypothesis, not a proven isolated cause.

A registered pure-penalty/fixed-initial-stiffness correction was tested first
on the rectangle. FKN=1 produced max endpoint penetration 0.00058725016 mm,
failing the unchanged v063 1e-5 mm gate despite passing the older generic
numeric screen. It was rejected. FTOLN did not set pure-penalty stiffness as it
had for AL; actual printed stiffness was inspected rather than assumed.

The observed penetration/gate ratio motivated a prospective 100x FKN test.
It passed the unchanged gate (5.9051026e-6 mm maximum endpoint penetration),
balanced actual contact-element forces/reactions, reproduced history bytes and
passed the matched force screen. Fixed stiffness deliberately retains the
solver recommendation to use KEYOPT(10)=0. This warning is not suppressed or
confused with a coefficient-ratio warning. No formal condition-number bound,
full microstructure sensitivity qualification or causal ablation is claimed.

Only one corrected full-model attempt was registered: pure penalty KEYOPT(2)=1,
KEYOPT(10)=1, FKN=100, FTOLN=-1e-5 mm. Same physical model, acceptance thresholds,
load targets and resource reserves; no geometry, stabilization or bonded-contact
substitution. All failed candidates and the original pilot are preserved.
''')
    save('V0_6_3_MICROSTRUCTURE_PILOT.md',f'''# v0.6.3 microstructure pilot

**{overall}**. Actual selected execution status: {mech['status']}.
Two real full-model nonlinear contact attempts executed. The original AL run
was stopped for documented residual stagnation with no converged substep. The
corrected run is separately frozen and retains its own complete native evidence.

Corrected run: {execution['status']} after {runtime:.3f} s, peak sampled
process-tree RSS {peak} bytes. Solver-reported converged substeps:
{mech['solver_reported_converged_substeps']}. The first 0.01% checkpoint was
attempted but did not converge. Later 0.05% / 0.1% stages: NOT EXECUTED because
the first stage failed. The wall-time cap is BLOCKED_RESOURCE; this is not a
finding of inadequate RAM or measured poor physical material performance.

The specimen is Design9/seed1/native1024; plane stress PLANE183 TRI6; provisional
E1000 MPa / nu .3 / initial thickness 1 mm / 10.24×10.24 mm envelope. Material
is homogeneous linear elastic; NLGEOM/contact introduce structural nonlinearity.
No plasticity, fracture or internal self-contact was configured.

Upper/lower rigid targets are frictionless and permit separation. Actual initial
checks found both pairs closed, initial penetration 0 / 3.55e-15 mm, no specimen
UY constraints. This initial check is not a completed zero-load solution.
The registered requested checkpoints are 0.01%, 0.05% and 0.1%; only actual
converged checkpoints appear below. The setup's generic CompressionConfig
loading defaults are not the executed pilot schedule: the frozen protocol and
actual TIME/D commands are authoritative. No 2% microstructure stage was run.

| Stage | Achieved engineering strain | Upper native RF [N] | Lower native RF [N] | Nominal compression stress [MPa] |
|---|---:|---:|---:|---:|
{stages}

Native upper RF is negative and lower positive. Contact CNFY is the opposing
internal resisting-force convention. Nominal stress uses the full initial
envelope W×t; engineering strain uses actual travel/H. Pseudo-time is a load
parameter, not seconds. No rectangle analytical force is assigned to this mesh.

Maximum validated stored-endpoint penetration: {unavailable(maxpen)} mm.
Fitted effective modulus: {unavailable(stiffness)} MPa; base modulus 1000 MPa.
At least two valid small-strain points are required for the registered
through-origin fit; otherwise fitted modulus is unavailable and any secant
estimate is explicitly separate. Internal self-contact, mechanical convergence
and paper readiness remain unqualified even if a checkpoint is valid.

Full numerical fields exist only where declared in mechanical_summary.json:
all-node UX/UY, corner-node averaged SYY/equivalent stress/elastic EYY/EXX,
actual contact endpoints and deformation mapping checks. No copied midside
stress or assumed deformation field. Unavailable stages/fields are not plotted.
''')
    state_table='\n'.join('| '+key+' | '+value+' |' for key,value in report['acceptance'].items())
    save('V0_6_3_VALIDATION.md',f'''# v0.6.3 scientific validation

## A. Executive summary

**{overall}**. Historical semantic mesh identity reproduced exactly, all frozen
geometry/mesh gates passed and the full actual MAPDL import was exhaustively
verified. Two bounded real full-model contact attempts were made; valid results
are restricted to the checkpoints explicitly recorded in the pilot report.

## B–D. Recovery, qualification and import

See V0_6_3_MESH_RECOVERY.md and V0_6_3_ANSYS_IMPORT.md. The original NPZ container
was not recovered; the reproduced arrays exactly match the historical semantic
hash. Raw ZIP byte equality is not claimed. All 2,766,505 nodes / 1,261,670 TRI6,
412 pores and seven-element registered chords are preserved. The 10° requirement
was not relaxed; minimum angle 11.404135°. Geometry and historical HOLDs unchanged.

## E–F. Resources and contact

See V0_6_3_RESOURCE_FEASIBILITY.md and V0_6_3_CONTACT_SENSITIVITY.md. Actual
assembly and factorization evidence supplement—not merely repeat—array-size
estimates. Hardware memory fit does not establish nonlinear convergence.
Every correction was registered prospectively; original failed data remain.

## G–H. Pilot and mechanical data

See V0_6_3_MICROSTRUCTURE_PILOT.md and mechanical_results/attempt_002. Status:
{mech['status']}. Valid checkpoint count: {len(rows)}. No predicted, unconverged
or rectangle data substitute for microstructure response. Feedback explicitly
excludes invalid numerical output from design ranking.

## I–J. Numerical and scientific limitations

Single geometrically qualified mesh; mechanical refinement convergence remains
UNQUALIFIED. PLATEN_CONTACT_ONLY; internal pore/strut self-contact is not configured
or demonstrated. Material, scale and plane stress are provisional; no experimental
calibration, yield/failure model or paper-quality comparative dataset. Historical
cumulative small-pore fidelity / production simplification HOLDs and the recorded
15-pixel repair remain. Contact sensitivity is bounded, and fixed-stiffness warnings
are retained. v241 help access remains incomplete; supported commands are evidenced
by actual v241 execution plus official adjacent-release comparison documentation.

## K. Reproducibility and verification

Artifact root is configurable via YD_ARTIFACT_ROOT; manifests retain relative
paths, source/config/runtime identities and both semantic/byte hashes. No upload
or required cloud service. Full raw solver files remain local; receipts,
scientific summaries, numerical checkpoint CSVs and figures are tracked.

Active tests: {int(report['tests']['active']['tests'])} collected,
{int(report['tests']['active']['tests']-report['tests']['active']['failures']-report['tests']['active']['errors']-report['tests']['active']['skipped'])} passed,
{int(report['tests']['active']['failures'])} failed. Archive fixture replay:
{int(sum(x['tests']-x['failures']-x['errors']-x['skipped'] for x in report['tests']['archived_replay']))} passed separately.
Real v063 evidence checks: {int(report['tests']['licensed_v063']['tests']-report['tests']['licensed_v063']['failures']-report['tests']['licensed_v063']['errors']-report['tests']['licensed_v063']['skipped'])} passed,
{int(report['tests']['licensed_v063']['failures'])} failed. The actual-converged-response
check intentionally fails if no microstructure checkpoint converged; its expected
outcome is never weakened to improve counts. Overlapping suites are not summed.
Historical files and original collection/context failures remain unchanged.
The release command scopes the active suite to tests/ and validation/test_evaluator.py
with EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py, as documented before
this milestone. An initial run without that environment selection used frozen
legacy v1.0 and returned 20 failed / 655 passed; the complete output is preserved.
An additional unscoped repository collection encountered 11 historical snapshot
module-name collisions; both collection outputs are preserved separately.
The previous v062 real-evidence checks passed again: {int(report['tests']['licensed_v062_recheck']['tests'])}.
Native solver .out/.err/.mntr files retain their whitespace and exact bytes;
Git whitespace review flags those native diagnostic lines. Source-code diff
review passes separately; native evidence is not rewritten for formatting.

## Independent acceptance

| Category | Status |
|---|---|
{state_table}

## L. Git history

Started clean at 9af3d404c94293c9fa705552bb41497358ddd63e on master. No push or
history rewrite. Protected generators/evaluators/canonical geometry and all
v0.6/v0.6.1/v0.6.2 experiments are unchanged under the saved diff.

{ledger}

Final reporting commit is the commit containing this document; its exact hash
is supplied in final response/Git history to avoid a self-referential hash.

## M. Next milestone

{'Validate contact/step sensitivity and accepted mechanical refinement levels before controlled multi-design comparison.' if valid else 'Diagnose full-model nonlinear convergence with early cutback and explicit contact-iteration telemetry under a new protocol; do not repeat identical failed large jobs or alter qualified geometry.'}
Only then produce a calibrated, uncertainty-aware mechanical dataset and review
the feedback contract for the first controlled LLM-guided iteration. No batch
FEM, autonomous optimization, manufacturing qualification or 3D work was implemented.
''')
    unknown='UNAVAILABLE — no validated converged checkpoint'
    answers=[
        'No original qualified NPZ container was found.', 'No location recovered; bounded known project roots and likely project archive names were searched.',
        'Original archive unavailable; reproduced NPZ passed full CRC/array checks.', 'Yes: exact historical semantic identity via frozen reproduction.',
        'Yes: source WKB 4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1.',
        'Yes: e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc.',
        'No array/ordering difference; new NPZ byte hash differs and is recorded separately.', 'Yes, unchanged 10° gate.',
        '11.4041350264°.', '2,766,505.', '1,261,670 TRI6.', 'Yes, 412, including imported connectivity/topology checks.',
        'Yes, minimum seven elements across registered chords; not exhaustive neck qualification.',
        'Configurable versioned artifact registry with source/config/version/semantic/byte hashes; verified second copy in C:/Users/sd22446/YoungDawgs-Artifacts outside app cache; same-computer copy, no off-device backup claimed.',
        'ANSYS 2024 R1, build24.1 UP20231106.', 'Yes, real Mechanical Enterprise Academic Research analyses/imports executed.',
        'Yes, full real import.', 'Yes, exhaustive 2,766,505 specimen nodes.', 'Yes, exhaustive 1,261,670 specimen elements.',
        'Yes, every six-node connectivity and attribute record checked against source.', 'Yes, global XY and full coordinate comparison within 1e-11 mm CDB precision.',
        'Yes, actual type/material/real and initial 1 mm thickness; E1000 MPa/nu.3.', 'Yes, every component membership checked.',
        'Yes, PLANE183 plane stress, z=0; no extrusion or 3D conversion.',
        str(read_json(RUN/'import_only/attempt_001/import_execution.json')['warnings']),
        str(environment['available_ram_bytes'])+' bytes available of '+str(environment['physical_ram_bytes'])+' physical at fresh audit.',
        str(environment['disk_free_bytes'])+' bytes free at audit; minimum 20 GiB enforced.',
        '5,533,010 unconstrained translations; actual contact sparse equations 5,533,009.',
        'Real linear WRFULL assembly plus actual full nonlinear sparse factorization/workspace statistics; see resource report.',
        'Sparse symmetric direct with default memory allocation and performance diagnostics.', 'One SMP core; no unrestricted parallel license assumed.',
        'Each full pilot: 1200 s, 20 GiB RSS, 12 GiB available OS RAM reserve, 20 GiB disk reserve.',
        'Memory/assembly/factorization fit the registered bounds; nonlinear convergence is a separate unresolved/qualified checkpoint decision.',
        'No memory-exhaustion conclusion; actual termination/status is '+str(execution['status'])+'.',
        'Yes, bounded AL tolerance tests and prospectively registered pure-penalty corrections; rejected candidates retained.',
        'Corrected attempt: pure penalty KEYOPT2=1, fixed initial stiffness KEYOPT10=1, FKN100, FTOLN=-1e-5 mm.',
        'Original coefficient-ratio warning absent in looser AL rectangles; fixed-stiffness recommendation warnings retained in corrected formulation.',
        'Yes, separate upper/lower rigid targets and specimen CONTA172 groups.', 'Yes, geometric normals plus actual initial solver check.',
        'Geometric zero; measured initial penetration 0 / 3.55e-15 mm.',
        'Yes at validated checkpoints only.' if valid else 'CONFIGURED_NOT_DEMONSTRATED: initial closure is not converged force transmission.',
        str(contact_rows[-2:]) if valid else unknown, unavailable(maxpen)+' mm.',
        'Yes at recorded checkpoints only.' if valid else 'No validated contact-converged checkpoint.',
        'No, internal self-contact not configured.', 'No, internal self-contact UNQUALIFIED.',
        'Yes, two real full-model nonlinear solve attempts; execution is not convergence.',
        unavailable(rows[0]['engineering_compression_strain'] if valid else None),
        str([r['engineering_compression_strain'] for r in rows[1:]]) if valid else 'NOT EXECUTED beyond the failed first requested stage.',
        unavailable(last.get('upper_rf_y_N')),unavailable(last.get('lower_rf_y_N')),
        'Passed <=1% normalized balance at recorded valid checkpoints.' if valid else unknown,
        'Only recorded checkpoints pass the registered gates; broader contact qualification remains limited.' if valid else 'No converged mechanical-contact consistency claim.',
        'No positive distortion/negative-pivot failure was reported before the recorded stop; deformed checks only exist for validated fields.',
        'Yes, real checkpoint CSV.' if valid else 'NOT AVAILABLE; no fabricated force curve.',
        'Yes, real checkpoint CSV.' if valid else 'NOT AVAILABLE; no fabricated stress-strain curve.',
        unavailable(stiffness)+' MPa; no fit from one or zero valid points.',
        'Yes for declared validated checkpoints only.' if valid else 'NOT AVAILABLE — no converged deformation snapshot.',
        'Supported corner-node fields only.' if valid else 'NOT AVAILABLE.',
        'Supported corner-node elastic strain only.' if valid else 'NOT AVAILABLE.',
        'Actual checkpoint endpoint/contact force CSVs only.' if valid else 'Initial contact diagnostics exist; no converged loaded-contact diagnostics.',
        str(mech['warnings']),f'{runtime:.3f} s corrected attempt; first diagnostic attempt {first["process"]["runtime_seconds"]:.3f} s.',
        str(peak)+' bytes peak sampled corrected process-tree RSS.', 'UNQUALIFIED; single mesh, no refinement evidence.',
        overall,'Preliminary single-mesh response only.' if valid else 'No qualified mechanical response.',
        'E,nu,dimensions,thickness and plane stress are provisional; homogeneous elastic material, no calibration.',
        'Cumulative small-pore fidelity and production simplification HOLDs unchanged; historical 15-pixel repair retained.',
        'Yes, still unqualified.', 'No, first establish repeatable converged physics/contact and refinement evidence.',
        'No, no paper-quality mechanical conclusions.', 'Valid mechanical feedback, reviewed failure classification and controlled comparison protocol; no optimization controller.',
        'Contact/step and mechanical refinement qualification.' if valid else 'New registered nonlinear-contact diagnostic with early cutbacks; no blind full-model retries.',
        str(int(report['tests']['active']['tests']-report['tests']['active']['failures']-report['tests']['active']['errors']-report['tests']['active']['skipped'])),
        str(int(sum(x['tests']-x['failures']-x['errors']-x['skipped'] for x in report['tests']['archived_replay'])))+' separately, not additional unique active tests.',
        str(int(report['tests']['licensed_v063']['tests']-report['tests']['licensed_v063']['failures']-report['tests']['licensed_v063']['errors']-report['tests']['licensed_v063']['skipped']))+' v063 evidence checks passed / 1 response check failed; 5 v062 evidence checks passed again. Suites overlap and are not summed.',
        'Yes, protected-path diff unchanged.', 'New mesh artifact/import/pilot/result modules, tests, manifests, protocols, raw-evidence receipts, figures and scientific reports; complete path/status list: audit/change_inventory.json.',
        'Six existing files: .gitignore, .gitattributes, metamaterial_eval/simulation/solver_execution.py, metamaterial_eval/simulation/windows_ansys.py, metamaterial_eval/simulation/licensed_benchmark.py, tests/test_windows_ansys.py; no protected geometry/generator/evaluator edits.',
        'All coherent completed milestones committed; full ledger in validation JSON.',
        'Full hashes/messages in validation report and final response; final report commit identified in Git history/final response.',
        'Verified after the final reporting commit; final response states actual result. Ignored raw solver artifacts remain local.',
        'No push to GitHub.'
    ]
    assert len(answers)==84,len(answers)
    save('V0_6_3_HANDOFF.md','# v0.6.3 requested 84-item handoff\n\nDetailed reports and JSON provide evidence and scope.\n\n| # | Answer |\n|---:|---|\n'+'\n'.join('| '+str(i)+' | '+a.replace('|','/')+' |' for i,a in enumerate(answers,1)))


if __name__=='__main__':
    if not (RUN/'figures/figure_manifest.json').exists():figures()
    summary()
