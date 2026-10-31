"""Conditional full fine-mesh general-contact repair after confirmed self-crossing."""
from pathlib import Path
import argparse
import re
import numpy as np
from metamaterial_eval.simulation.mesh_artifacts import artifact_root,resolve_manifest
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.progressive_compression import run_progressive,load_commands
from metamaterial_eval.simulation.nonlinear_diagnostics import telemetry_commands
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import REPO,RUN,BASE,load,compact
from scripts.v065_recovery import committed

PROTOCOL=RUN/'protocol/FULL_GENERAL_CONTACT_014.json'


def prepare():
    assert load(RUN/'internal_contact/QUALIFIED_SHORT_GAP.json')['status']=='PASS_SMALL_NATIVE_INTERNAL_CONTACT_ONLY'
    assert load(RUN/'deformation/EXACT_CROSSING_DIAGNOSIS_013.json')['status']=='CONFIRMED_UNMODELED_FREE_BOUNDARY_CROSSING'
    original=load(artifact_root()/'solver/v065/full_recovery_001/simulation_manifest.json')
    source=artifact_root()/'solver/v063/contact_setup_002/contact_model.db'
    assert file_hash(source)==original['source_contact_database_sha256']
    d=BASE/'fine_gc_setup_001';d.mkdir(parents=True,exist_ok=False)
    model={**original['model'],'model_variant':'FINE_FULL_SELF_CONTACT_V066_GC014','contact_scope':'PLATEN_AND_GENERAL_SELF_CONTACT',
        'internal_self_contact':'GENERAL_CONTACT_ALL_EXPOSED_SURFACES','general_contact_elements':243576,
        'general_contact_component':'INTERNAL_GC','user_model_elements':original['model']['user_model_elements']+243576}
    protocol={'schema':'young-dawgs-v0.6.6-conditional-full-self-contact','reason':'Actual quadratic self-crossing at1% on external/top faces; platen-only state rejected, highest accepted0.809375%. Small connected general-contact fixture independently passed.',
        'scope':'One corrective same-geometry/fine-mesh model, not a batch across designs. New contact topology requires a fresh model; do not disguise it as v065 native-state continuation.',
        'source_database_sha256':file_hash(source),'source_geometry_sha256':original['source_geometry_sha256'],'mesh_semantic_sha256':original['mesh_semantic_sha256'],
        'mesh_preserved':True,'structural_nodes':2766505,'TRI6':1261670,'surface_edges':243576,'pore_edges':213150,
        'surface_selection':'ALL exposed deformable faces including original top/bottom pair-contact faces; first collision involves top/external faces. Rigid platen pair definitions retained; no general rigid target added.',
        'general_contact':'GCGEN NEW42,0,PART,SELECT on PLANE183; GCDEF SYMM ALL SELF,mat1,real100; pure penalty/default general-contact options as validated on fixture; FKN100,FTOLN-1e-5,MU0',
        'connected_exclusions':'Native general-contact topology/normal exclusions; verify exact generated exposed-face coverage and baseline no spurious force coupling. No explicit same-body SELF exclusion that would disable required folding contact.',
        'setup_gate':'Actual full native skin inventory equals all243576 oriented quadratic exposed edges, unchanged nodes/structural elements/platen pairs, normal native exit and readable model DB.',
        'first_mechanical_stage':.001,'initial_response_check':'At0.1%, independently require force within0.5% of accepted platen-only reference1.199313799677024N, no unmodeled geometry crossing and all standard equilibrium/mapping/output gates. Do not splice response branches.',
        'next_targets':[.01,.05,.1,.2,.3,.4],'primary_target':.3,'stretch_target':.4,
        'material':'Unchanged provisional E1000MPa,nu0.3,t1mm,plane stress,NLGEOM ON; no plasticity/stabilization/geometry edits',
        'resource_budget':'Original six-hour campaign clock retained,90min/stage,30min no-progress; one native job,twoSMP,noRSS cap,HealthPolicy,40GiB disk reserve',
        'contact_acceptance':'Full native whole-element contact availability, positive actual engagement when closure occurs; stored endpoint penetration<=1e-5mm, equal/opposite native internal forces, explanatory target/skin IDs for boundary contact; uncertain or unexplained crossing unqualified.',
        'fallback':'If full setup/cost/initial response/contact/geometric gates fail, retain original valid branch and document precise HOLD. Do not manufacture30% fields.'}
    write_json(PROTOCOL,protocol)
    lines=['/BATCH','/CLEAR,START',database_resume(source).strip(),'/PREP7','/GOPR',
        'KEYOPT,3,2,1','KEYOPT,3,4,2','KEYOPT,3,10,1','RMODIF,2,3,100','RMODIF,3,3,100',
        'ESEL,S,TYPE,,1','GCGEN,NEW,42,0,PART,SELECT','GCGEN,SELECT','CM,INTERNAL_GC,ELEM','ALLSEL,ALL',
        'R,100,,,100,-1e-5','GCDEF,SYMM,ALL,SELF,1,100',
        '/OUTPUT,gc_definition,txt','GCDEF,LIST','ETLIST,ALL','RLIST,100','MPLIST,ALL','DLIST,ALL','/OUTPUT',
        '*GET,NN,NODE,0,COUNT','*GET,NE,ELEM,0,COUNT','CMSEL,S,INTERNAL_GC','*GET,NGC,ELEM,0,COUNT',
        '*CFOPEN,gc_inventory,csv','*VWRITE',"('model_nodes,model_elements,general_contact_skins')",'*VWRITE,NN,NE,NGC',"(F16.0,2(',',F16.0))",'*CFCLOS',
        '*CFOPEN,gc_topology,csv','*VWRITE',"('element,i_node,j_node,midside_node')",'EID=0','*DO,KK,1,NGC','EID=ELNEXT(EID)',
        '*GET,NI,ELEM,EID,NODE,1','*GET,NJ,ELEM,EID,NODE,2','*GET,NM,ELEM,EID,NODE,3','*VWRITE,EID,NI,NJ,NM',"(F12.0,3(',',F12.0))",'*ENDDO','*CFCLOS',
        'ALLSEL,ALL','FINISH','SAVE,contact_model_gc,db,,MODEL','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n')
    write_json(d/'simulation_manifest.json',{**original,'model':model,'input_sha256':file_hash(d/'input.inp'),'protocol_sha256':file_hash(PROTOCOL),
        'source_contact_database_sha256':file_hash(source),'execution_scope':'GENERAL_CONTACT_SETUP_NO_SOLVE'})
    compact(d,RUN/'internal_contact/prepared_full_gc_setup001')
    print(d,flush=True)


def execute():
    committed(PROTOCOL);committed(RUN/'internal_contact/prepared_full_gc_setup001/input.inp')
    d=BASE/'fine_gc_setup_001';r=run_progressive(d,timeout=900,solve=False,cores=2)
    r['execution_kind']='LICENSED_GENERAL_CONTACT_SETUP_NO_SOLVE';write_json(d/'execution_receipt.json',r)
    compact(d,RUN/'internal_contact'/d.name)
    for name in ['gc_inventory.csv','gc_definition.txt']:
        p=d/name
        if p.exists():(RUN/'internal_contact'/d.name/name).write_text('\n'.join(s.rstrip() for s in p.read_text(errors='replace').splitlines())+'\n')
    print(r['status'],r['process']['returncode'],flush=True)


def qualify():
    d=BASE/'fine_gc_setup_001';r=load(d/'execution_receipt.json');manifest=load(d/'simulation_manifest.json')
    result={'status':'HOLD','mesh_semantic_sha256':manifest['mesh_semantic_sha256'],'source_geometry_sha256':manifest['source_geometry_sha256'],'model':manifest['model']}
    try:
        if r['process']['returncode']!=0 or re.search(r'\*\*\*\s*(?:ERROR|FATAL)\s*\*\*',(d/'solver.out').read_text(errors='replace'),re.I):raise ValueError('Native setup failed')
        inventory=np.loadtxt(d/'gc_inventory.csv',delimiter=',',skiprows=1,ndmin=2)[0]
        topology=np.loadtxt(d/'gc_topology.csv',delimiter=',',skiprows=1,ndmin=2).astype(np.int64)
        mesh,_,_=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
        expected=mesh.boundary+1;actual=topology[:,1:4]
        original={tuple(e):i for i,e in enumerate(expected)}
        mapped=np.array([original.get(tuple(e),-1) for e in actual])
        missing=np.setdiff1d(np.arange(len(expected)),mapped)
        result.update(actual_inventory=inventory.tolist(),native_skin_rows=len(topology),oriented_faces_matched=int(np.sum(mapped>=0)),missing_exposed_faces=len(missing),
            missing_face_groups={str(g):int(np.sum(mesh.boundary_groups[missing]==g)) for g in np.unique(mesh.boundary_groups[missing])},
            native_gc_topology_sha256=file_hash(d/'gc_topology.csv'),native_MODEL_database_sha256=file_hash(d/'contact_model_gc.db'))
        if not np.array_equal(inventory,[2766511,manifest['model']['user_model_elements'],243576]) or len(topology)!=243576 or len(np.unique(topology[:,0]))!=len(topology) or np.any(mapped<0) or len(np.unique(mapped))!=len(expected):raise ValueError('Full general-contact skin coverage/inventory mismatch')
        np.save(d/'gc_edge_indices.npy',mapped)
        result.update(status='PASS_NATIVE_FULL_GC_SETUP__MECHANICS_PENDING',actual_fine_structural_geometry_preserved=True,
            next_step='Fresh same-fine-mesh GC solve to0.1%, match original force within0.5%, independently reopen all fields and contact inventories before further loading')
    except (ValueError,FileNotFoundError) as exc:result['failure']=str(exc)
    write_json(RUN/'internal_contact/FULL_GC_SETUP_QUALIFICATION.json',result);print(result['status'],result.get('failure'),flush=True)


def prepare_first_solve(nodal=False):
    q=load(RUN/'internal_contact/FULL_GC_SETUP_QUALIFICATION.json')
    assert q['status']=='PASS_NATIVE_FULL_GC_SETUP__MECHANICS_PENDING'
    setup=BASE/'fine_gc_setup_001';source=setup/'contact_model_gc.db'
    assert file_hash(source)==q['native_MODEL_database_sha256']
    label='fine_nodal_stage01_001' if nodal else 'fine_gc_stage01_001'
    d=BASE/label;d.mkdir(parents=True,exist_ok=False)
    model=dict(q['model'])
    protocol=RUN/'protocol/NODAL_CONTACT_REPAIR_021.json' if nodal else PROTOCOL
    if nodal:
        assert load(RUN/'internal_contact/NODAL_FIXTURE_QUALIFICATION.json')['status']=='PASS_ACTUAL_NODAL_GC_INTERFACE_FORCE_PEN_MAPPING'
        model.update(model_variant='FINE_FULL_SELF_CONTACT_NODAL_V066_021',general_contact_detection_keyopt4=2)
    lines=['/BATCH','/CLEAR,START',database_resume(source).strip(),'/GOPR']
    if nodal:lines+=['/PREP7','KEYOPT,4,4,2','/OUTPUT,nodal_type_before,txt','ETLIST,4','/OUTPUT','FINISH']
    lines+=['/SOLU','ANTYPE,STATIC','NLGEOM,ON',
        'EQSLV,SPARSE','BCSOPTION,,DEFAULT,,,,PERFORMANCE','CNVTOL,F,,.005,2,1e-8','RESCONTROL,DELETE,ALL']
    lines+=telemetry_commands(model['controls']['top'])+[f'NLHIST,NSOL,RFLOW,F,Y,{model["controls"]["bottom"]}']
    lines+=load_commands(.001,0,model['controls']['top'],model['config']['height'])
    (d/'input.inp').write_text('\n'.join(lines+['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE'])+'\n')
    manifest=load(setup/'simulation_manifest.json');manifest.update(model=model,input_sha256=file_hash(d/'input.inp'),protocol_sha256=file_hash(protocol),
        execution_cores=8 if nodal else 2,targets=[.001],target_strain=.001,previous_strain=0,execution_scope='FRESH_FINE_MODEL_WITH_GENERAL_SELF_CONTACT',
        source_general_contact_database_sha256=file_hash(source),source_setup_receipt_sha256=file_hash(setup/'execution_receipt.json'))
    if nodal:
        assert load(RUN/'performance/SMP_QUALIFICATION.json')['selected_cores']==8
        manifest.update(resource_protocol_sha256=file_hash(RUN/'protocol/SMP_RESOURCE_018.json'),parallel_qualification_sha256=file_hash(RUN/'performance/SMP_QUALIFICATION.json'),nodal_fixture_qualification_sha256=file_hash(RUN/'internal_contact/NODAL_FIXTURE_QUALIFICATION.json'))
    write_json(d/'simulation_manifest.json',manifest);compact(d,RUN/'progressive_compression'/('prepared_'+label))
    print(d,flush=True)


def run_first_solve(nodal=False):
    label='fine_nodal_stage01_001' if nodal else 'fine_gc_stage01_001'
    protocol=RUN/'protocol/NODAL_CONTACT_REPAIR_021.json' if nodal else PROTOCOL
    d=BASE/label;committed(protocol);committed(RUN/'progressive_compression'/('prepared_'+label)/'input.inp')
    m=load(d/'simulation_manifest.json');assert file_hash(d/'input.inp')==m['input_sha256'] and file_hash(protocol)==m['protocol_sha256']
    from scripts.v066_campaign import remaining_solver_budget
    if nodal:
        assert m['resource_protocol_sha256']==file_hash(RUN/'protocol/SMP_RESOURCE_018.json') and m['parallel_qualification_sha256']==file_hash(RUN/'performance/SMP_QUALIFICATION.json')
    r=run_progressive(d,timeout=remaining_solver_budget(),no_progress_seconds=1800,cores=m.get('execution_cores',2));compact(d,RUN/'progressive_compression'/d.name)
    print(r['status'],r['process']['returncode'],r['converged_steps'][-1:],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','qualify','prepare-first','run-first']);p.add_argument('--nodal',action='store_true');a=p.parse_args()
    {'prepare':prepare,'execute':execute,'qualify':qualify,'prepare-first':lambda:prepare_first_solve(a.nodal),'run-first':lambda:run_first_solve(a.nodal)}[a.action]()
