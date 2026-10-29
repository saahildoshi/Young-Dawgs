"""Build traceable v0.6.2 figures and compact scientific feedback from actual runs."""
import json
from pathlib import Path
import re
import subprocess
from datetime import datetime,timezone
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from metamaterial_eval.simulation.licensed_benchmark import read_numeric_csv,HISTORY,NODAL,STRESS,CONTACT
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'experiments/pipeline_v0.6.2/run_001'


def verified(stage,attempt):
    folder=RUN/stage/'generated'/f'execution_{attempt}'
    receipt=json.loads((folder/'solver_status.json').read_text())
    for name in ['compression.rst','history.csv','nodal_fields.csv','stress_fields.csv','mesh.npz','solver.out']:
        assert file_hash(folder/name)==receipt['outputs'][name],name
    return folder,receipt


def figures():
    directory=RUN/'figures';directory.mkdir(exist_ok=False)
    direct,dr=verified('rectangle_direct','001');contact,cr=verified('rectangle_contact','002')
    with np.load(contact/'mesh.npz') as z:
        xy=z['nodes'];tri=z['triangles'][:,:3];boundary=z['boundary'];labels=z['boundary_groups']
    history=read_numeric_csv(contact/'history.csv',HISTORY)
    fields=read_numeric_csv(contact/'nodal_fields.csv',NODAL)
    stresses=read_numeric_csv(contact/'stress_fields.csv',STRESS)
    contacts=read_numeric_csv(contact/'contact_fields.csv',CONTACT)
    points=read_numeric_csv(RUN/'contact_validation/point_extraction_001/contact_points.csv',
        ['set','pseudo_time','pair','element','pressure_i_MPa','pressure_j_MPa','signed_gap_i_mm','signed_gap_j_mm','contact_force_y_N'])
    assert file_hash(RUN/'contact_validation/point_extraction_001/contact_points.csv')==json.loads((RUN/'contact_validation/point_extraction_001/contact_point_validation.json').read_text())['point_csv_sha256']
    last=history[-1]['set'];nodal=sorted([r for r in fields if r['set']==last],key=lambda r:r['node'])
    solved=np.array([[r['ux_mm'],r['uy_mm']] for r in nodal])
    stress={int(r['node'])-1:r for r in stresses if r['set']==last}
    fig,axes=plt.subplots(2,2,figsize=(10,9),constrained_layout=True)
    ax=axes[0,0];ax.triplot(xy[:,0],xy[:,1],tri,lw=.35);ax.set_title('Actual imported mesh: 617 nodes / 268 TRI6')
    ax=axes[0,1];ax.triplot(xy[:,0],xy[:,1],tri,color='0.8',lw=.3)
    for group,color in [('top','tab:red'),('bottom','tab:blue')]:
        segments=xy[boundary[labels==group,:2]]
        ax.add_collection(LineCollection(segments,colors=color,linewidths=3,label=group+' contact'))
    ax.plot([-.512,10.752],[10.24,10.24],'r-',lw=4);ax.plot([-.512,10.752],[0,0],'b-',lw=4)
    ax.arrow(5.12,11,0,-.6,width=.05,color='r');ax.set_title('Rigid platens; no specimen UY constraints');ax.legend()
    ax=axes[1,0];ax.plot([0,10.24],[0,0],'b-',lw=4);ax.plot([0,10.24],[10.24,10.24],'r-',lw=4)
    ax.text(5.12,5.12,'Actual CNCHECK before loading:\nboth pairs INITIALLY CLOSED\ninitial penetration ≤3.56e-15 mm\n(no solved zero-load field)',ha='center',va='center')
    ax.set_title('Initial contact check from solver log')
    ax=axes[1,1]
    for pair,y in [(1,0),(2,10.24)]:
        vals=[r['status'] for r in contacts if r['set']==last and r['pair']==pair]
        ax.scatter(np.linspace(0,10.24,len(vals)),np.full(len(vals),y),c=vals,vmin=0,vmax=3,cmap='viridis',s=80)
    ax.text(5.12,5.12,'Last achieved 2% compression\n40/40 contact elements closed\nstatus 2 = sliding frictionless contact',ha='center',va='center')
    ax.set_title('Actual contact element status at 2%')
    for ax in axes.flat:ax.set_aspect('equal');ax.set_xlim(-1,11.5);ax.set_ylim(-1,11.5);ax.set_xlabel('x [mm]');ax.set_ylabel('y [mm]')
    fig.suptitle('ANSYS 2024 R1 — actual 2D benchmark setup and contact diagnostics');fig.savefig(directory/'mesh_and_contact.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,3,figsize=(13,8),constrained_layout=True)
    axes[0,0].triplot(xy[:,0],xy[:,1],tri,color='0.8',lw=.35)
    axes[0,0].triplot(*(xy+solved).T,tri,color='tab:blue',lw=.35);axes[0,0].set_title('Deformed mesh: true scale (1×)')
    for ax,values,title in [(axes[0,1],solved[:,1],'Vertical displacement [mm]'),
                             (axes[0,2],np.linalg.norm(solved,axis=1),'Displacement magnitude [mm]')]:
        color=ax.tripcolor(*xy.T,tri,values,shading='gouraud');fig.colorbar(color,ax=ax);ax.set_title(title)
    for ax,key,title in [(axes[1,0],'syy_MPa','Vertical Cauchy stress [MPa]'),
                          (axes[1,1],'seqv_MPa','Equivalent stress [MPa]'),
                          (axes[1,2],'elastic_eyy','Vertical elastic strain')]:
        facevalues=np.array([np.mean([stress[n][key] for n in element]) for element in tri])
        color=ax.tripcolor(*xy.T,tri,facecolors=facevalues);fig.colorbar(color,ax=ax);ax.set_title(title)
    for ax in axes.flat:ax.set_aspect('equal');ax.set_xlabel('x [mm]');ax.set_ylabel('y [mm]')
    fig.suptitle('Actual contact solve at achieved 2% — stress panels average corner-node output per triangle')
    fig.savefig(directory/'deformation_fields.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    for folder,name,style in [(direct,'direct','-'),(contact,'contact (qualified)','--'),
                              (RUN/'rectangle_contact/generated/execution_001','contact (rejected default)','-.')]:
        rows=read_numeric_csv(folder/'history.csv',HISTORY)
        epsilon=np.array([-r['top_uy_mm']/10.24 for r in rows]);force=np.array([-r['upper_rf_y_N'] for r in rows])
        axes[0,0].plot(epsilon*10.24,force,style,label=name)
        axes[0,1].plot(epsilon*100,force/10.24,style,label=name)
        if name!='contact (rejected default)':axes[1,1].plot(epsilon*100,100*(force/(1000*epsilon*10.24)-1),style,label=name)
    eps=np.linspace(0,.02,100)
    axes[0,0].plot(eps*10.24,1000*eps*10.24,':',color='black',label='infinitesimal analytical reference')
    axes[0,1].plot(eps*100,1000*eps,':',color='black',label='infinitesimal analytical reference')
    axes[0,0].set(xlabel='Platen compression [mm]',ylabel='Compressive force magnitude [N]')
    axes[0,1].set(xlabel='Engineering compression [%]',ylabel='Nominal compression stress [MPa]')
    times=np.array([r['pseudo_time'] for r in history])
    axes[1,0].plot(times*100,[-r['upper_rf_y_N'] for r in history],label='−upper native RF')
    axes[1,0].plot(times*100,[r['lower_rf_y_N'] for r in history],'--',label='lower native RF')
    axes[1,0].set(xlabel='Load pseudo-time ×100 (not seconds)',ylabel='Reaction magnitude [N]')
    axes[1,1].axvspan(0,.5,color='green',alpha=.08,label='registered analytical acceptance domain')
    axes[1,1].set(xlabel='Engineering compression [%]',ylabel='Difference from infinitesimal reference [%]')
    for ax in axes.flat:ax.legend(fontsize=7);ax.grid(alpha=.2)
    fig.suptitle('Actual ANSYS responses; rejected attempt retained; higher strain includes finite-deformation effects')
    fig.savefig(directory/'mechanical_curves.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,8),constrained_layout=True)
    for pair,name in [(1,'bottom'),(2,'top')]:
        pressure=[];penetration=[];force=[];status=[]
        for r in history:
            rows=[x for x in points if x['set']==r['set'] and x['pair']==pair]
            pressure.append(max(max(x['pressure_i_MPa'],x['pressure_j_MPa']) for x in rows))
            penetration.append(max(max(0,x['signed_gap_i_mm'],x['signed_gap_j_mm']) for x in rows))
            force.append(abs(sum(x['contact_force_y_N'] for x in rows)))
            status.append(sum(x['status']>=2 for x in contacts if x['set']==r['set'] and x['pair']==pair))
        axes[0,0].plot(times*100,pressure,label=name)
        axes[0,1].semilogy(times*100,np.maximum(penetration,1e-15),label=name)
        axes[1,0].plot(times*100,force,label=name+' contact element force sum')
        axes[1,1].plot(times*100,status,label=name)
    axes[0,0].set(ylabel='Max stored endpoint pressure [MPa]')
    axes[0,1].axhline(1e-7,color='gray',ls=':',label='specified absolute FTOLN')
    axes[0,1].set(ylabel='Max stored endpoint penetration [mm]')
    axes[1,0].set(ylabel='Contact-force magnitude [N]')
    axes[1,1].set(ylabel='Closed contact elements (20 per pair)',ylim=(0,22))
    for ax in axes.flat:ax.set_xlabel('Solver pseudo-time ×100 (not seconds)');ax.legend(fontsize=7);ax.grid(alpha=.2)
    fig.suptitle('Actual RST contact diagnostics — stored endpoints are not a continuous-surface bound')
    fig.savefig(directory/'contact_histories.png',dpi=150);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    for ax,folder,title in zip(axes,[direct,contact],['direct','contact']):
        log=(folder/'solver.out').read_text()
        values=re.findall(r'FORCE CONVERGENCE VALUE\s*=\s*([\d.Ee+\-]+)\s+CRITERION=\s*([\d.Ee+\-]+)',log)
        residual=np.array(values,dtype=float)
        ax.semilogy(np.maximum(residual[:,0],1e-20),label='force residual')
        ax.semilogy(residual[:,1],label='force criterion');ax.set_title(title+' actual iteration history')
        ax.set(xlabel='Logged convergence evaluation index',ylabel='Force norm [N]');ax.legend();ax.grid(alpha=.2)
    fig.suptitle('ANSYS convergence logs — each run completed 36 saved substeps')
    fig.savefig(directory/'solver_convergence.png',dpi=150);plt.close(fig)
    write_json(directory/'figure_manifest.json',{'source_RST_sha256':cr['outputs']['compression.rst'],
        'direct_RST_sha256':dr['outputs']['compression.rst'],
        'panels':{'mesh_and_contact.png':['rectangle mesh','load/support configuration','platen regions','initial CNCHECK','loaded contact status'],
                  'deformation_fields.png':['true-scale deformation','UY','displacement magnitude','SYY','equivalent stress','elastic EYY'],
                  'mechanical_curves.png':['reactions','direct/contact compression','analytical comparison','stress/strain'],
                  'contact_histories.png':['pressure','endpoint penetration','contact force','engagement'],
                  'solver_convergence.png':['actual residual and force-criterion histories']},
        'figures':{p.name:file_hash(p) for p in directory.glob('*.png')}})


def summaries():
    verification=RUN/'verification'
    current={}
    for line in (verification/'collection_final.log').read_text().splitlines():
        if '::' in line:
            name=line.split('::')[0];current[name]=current.get(name,0)+1
    historical=json.loads((ROOT/'experiments/pipeline_v0.6.1/verification/test_reconciliation.json').read_text())
    added={k:v for k,v in current.items() if k not in historical['final_counts_by_module']}
    def xml(path):
        element=ET.parse(path).getroot();suites=list(element.iter('testsuite'))
        return {key:sum(float(s.get(key,0)) for s in suites) for key in ['tests','failures','errors','skipped','time']}
    replay_dir=verification/'archive_fixture_replay_complete'
    replay=json.loads((replay_dir/'replay_manifest.json').read_text())
    write_json(verification/'test_reconciliation.json',{'current_modules':current,'current_collected':sum(current.values()),
        'active':xml(verification/'regression_final.xml'),'licensed_integration':xml(verification/'real_ansys_integration_final.xml'),
        'archive_raw':xml(verification/'archive_raw.xml'),
        'archive_replay_groups':[xml(replay_dir/r['junit']) for r in replay],
        'historical_reported_primary':421,'additional_current_modules':added,
        'interpretation':'198 cases in four pre-existing geometry modules are present now but absent from the historical 421-module inventory; 12 new v0.6.2 unit cases. Do not rewrite the historical report or claim restoration of the absent 457-case inventory.',
        'archive_scope':'current broad archive discovery exceeds the earlier 112-case subset; overlaps are not added to unique active counts',
        'deselected_active':0})
    protected=['experiments/pipeline_v0.6','experiments/pipeline_v0.6.1','metamaterial_eval/generators',
               'validation/evaluators','generated_microstructures','data','metamaterial_eval/geometry']
    diff=subprocess.check_output(['git','diff','--name-only','4e261f3','--',*protected],cwd=ROOT,text=True)
    assert not diff,diff
    write_json(verification/'historical_preservation.json',{'starting_HEAD':'4e261f3',
        'protected_paths':protected,'changed_paths':diff.splitlines(),'status':'PASS_UNCHANGED',
        'source_geometry_authenticated':True,'historical_hold_decisions':'UNCHANGED'})
    states={'WINDOWS_ENVIRONMENT':'PASS','LICENSED_SOLVER':'PASS','AUTOMATION':'PASS_MAPDL_BATCH_AND_WORKBENCH_MECHANICAL_SCRIPTING',
            'MESH_TRANSFER':'PASS_SMALL_RECTANGLE_ONLY','DIRECT_RECTANGLE':'PASS','PLATEN_CONTACT':'PASS_EMPIRICAL_REGISTERED_RECTANGLE',
            'MECHANICAL_RESULTS':'PASS_RECTANGLE_ONLY','MICROSTRUCTURE_IMPORT':'NOT_EXECUTED_MISSING_AUTHENTICATED_MESH_BYTES',
            'MICROSTRUCTURE_RESOURCE':'UNQUALIFIED_NO_FULL_MODEL_MEASUREMENT','MICROSTRUCTURE_PILOT':'BLOCKED_NOT_ATTEMPTED',
            'INTERNAL_SELF_CONTACT':'UNQUALIFIED_NOT_CONFIGURED_NOT_DEMONSTRATED','MECHANICAL_MESH_CONVERGENCE':'UNQUALIFIED',
            'PAPER_READINESS':'UNQUALIFIED_RESEARCH_HOLD','LLM_FEEDBACK_LOOP':'NOT_IMPLEMENTED','MANUFACTURING':'UNQUALIFIED'}
    direct=json.loads((RUN/'rectangle_direct/analysis_001/mechanical_summary.json').read_text())
    contact=json.loads((RUN/'rectangle_contact/analysis_002/mechanical_summary.json').read_text())
    points=json.loads((RUN/'contact_validation/point_extraction_001/contact_point_validation.json').read_text())
    resource=json.loads((RUN/'microstructure_resource_gate/resource_gate.json').read_text())
    environment=json.loads((RUN/'environment/environment.json').read_text())
    receipts=[]
    for p in RUN.glob('**/generated/**/solver_status.json'):
        if 'smoke_package' not in str(p):
            r=json.loads(p.read_text());receipts.append({'path':str(p.relative_to(RUN)),**{k:r.get(k) for k in ['runtime_seconds','peak_tree_rss_bytes','status','solver_version']}})
    start=datetime.fromisoformat(environment['timestamp_utc'])
    elapsed=(datetime.now(timezone.utc)-start).total_seconds()
    commits=subprocess.check_output(['git','log','--reverse','--format=%H %s','4e261f3..HEAD'],cwd=ROOT,text=True).splitlines()
    report={'schema':'young-dawgs-v0.6.2-validation','acceptance':states,'environment':environment,
            'actual_license_product':'Mechanical Enterprise Academic Research','direct':direct,'contact':contact,
            'pointwise_contact_validation':points,'microstructure':resource,'test_reconciliation':json.loads((verification/'test_reconciliation.json').read_text()),
            'performance':{'solver_runs':receipts,'audit_to_report_wall_seconds':elapsed,
                           'scope':'wall window begins at saved environment audit, not whole chat; RSS sampled per process tree'},
            'created_commits_before_report':commits,'final_commit':'commit containing final report; see git history and final response',
            'limitations':['provisional material and dimensions','plane stress','finite benchmark validation domain',
                           'v241 official help unavailable; empirical release verification with v242 comparison references',
                           'tight FTOLN raises automatically computed contact stiffness; coefficient-ratio warning retained',
                           'no formal contact sensitivity study','stress/strain available at corners; no invented midside stress',
                           'stored endpoint penetration is not a continuous-surface bound','prior cumulative small-pore fidelity HOLD',
                           'no experimental calibration','internal self-contact unqualified','mechanical mesh convergence unqualified',
                           'no microstructure mechanical data','no manufacturing qualification','no autonomous LLM optimization']}
    write_json(RUN/'V0_6_2_ANSYS_VALIDATION.json',report)
    write_json(RUN/'mechanical_feedback.json',{
        'schema':'young-dawgs-mechanical-feedback-v0.6.2','automation_controller':'NOT_IMPLEMENTED',
        'rectangle':{'specimen_type':'homogeneous_numerical_benchmark','validity':'VALID_SOLVER_MEASUREMENTS',
                     'design_id':None,'geometry_sha256':None,'mesh_sha256':json.loads((RUN/'rectangle_contact/evidence_002/input_manifest.json').read_text())['mesh_sha256'],
                     'material':{'E_MPa':1000,'nu':.3},'plane_stress_thickness_mm':1,
                     'contact':'two frictionless rigid platen pairs; internal self-contact not configured',
                     'stress_strain_csv':'rectangle_contact/analysis_002/stress_strain.csv','effective_stiffness':contact['effective_stiffness'],
                     'reaction_history_csv':'rectangle_contact/analysis_002/force_displacement.csv',
                     'deformation_fields':'rectangle_contact/evidence_002/nodal_fields.csv',
                     'contact_validation':'contact_validation/point_extraction_001/contact_point_validation.json',
                     'achieved_engineering_strains':[r['engineering_compression_strain'] for r in contact['requested_stages']],
                     'solver_warnings':['Coefficient ratio exceeds 1.0e8 - Check results.'],
                     'eligible_for_microstructure_design_ranking':False},
        'microstructure':{'design_id':9,'seed':1,'resolution':1024,'source_geometry_sha256':resource['source_geometry_sha256'],
                          'recorded_mesh_sha256':resource['recorded_mesh_semantic_sha256'],'mesh_authenticated':False,
                          'solid_fraction':50.0104/(10.24**2),'validity':'MISSING_MESH_INPUT_NOT_PHYSICAL_DESIGN_FAILURE',
                          'solver_convergence':'NOT_EXECUTED','stress_strain':None,'effective_stiffness':None,
                          'achieved_compression_stages':[],'eligible_for_design_ranking':False},
        'limitations':report['limitations']})
    return report


if __name__=='__main__':
    if not (RUN/'figures').exists():figures()
    summaries()
