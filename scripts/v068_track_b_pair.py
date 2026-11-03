"""Fresh selected-specimen branch with one localized deformable contact pair."""
import argparse
import re
import numpy as np

from metamaterial_eval.simulation.progressive_compression import run_progressive,load_commands,authenticated_restart_copy
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.nonlinear_diagnostics import telemetry_commands
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence
from scripts.v068_track_b import mesh_and_plan
from scripts.v068_pair_common import face_owners,overlay,native_skin_ids_by_face


def selection():
    mesh,_,_,_=mesh_and_plan()
    p=read(RUN/'protocol/TRACK_B_LOCAL_PAIR_002.json')
    source=np.array(p['source_contact_faces_zero_based'],dtype=int)
    target=np.array(p['target_contact_faces_zero_based'],dtype=int)
    if (len(np.unique(np.r_[source,target]))!=len(source)+len(target) or
        np.intersect1d(mesh.boundary[source].ravel(),mesh.boundary[target].ravel()).size):
        raise ValueError('Contact pair arcs share a source node or face')
    return mesh,source,target,p


def prepare_setup():
    fixture=read(RUN/'track_B_contact_fixture/PAIR_FIXTURE_QUALIFICATION.json')
    original=read(RUN/'track_B_contact_fixture/SETUP_QUALIFICATION.json')
    if not fixture['passed'] or original['status']!='PASS_NATIVE_TRACK_B_CONTACT_SETUP':
        raise ValueError('Small licensed fixture or original setup not qualified')
    mesh,source,target,protocol=selection()
    original_db=BASE/'track_B_setup_001/contact_model.db'
    if file_hash(original_db)!=original['native_database_sha256']:
        raise ValueError('Original native model changed')
    original_model=read(BASE/'track_B_setup_001/simulation_manifest.json')
    original_gc=np.loadtxt(BASE/'track_B_setup_001/gc_topology.csv',delimiter=',',skiprows=1)
    face_eid=native_skin_ids_by_face(mesh,original_gc)
    d=BASE/'track_B_pair_setup_002';d.mkdir(parents=True,exist_ok=False)
    owners=face_owners(mesh)
    with (d/'input.inp').open('w',encoding='utf-8',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n'+f"RESUME,'{original_db.with_suffix('')}',db\n"+
                '/FILNAME,compression\n/PREP7\n')
        for eid in face_eid[np.r_[source,target]]:
            f.write(f'EDELE,{eid}\n')
        f.write('ALLSEL,ALL\nESEL,S,TYPE,,4\nCM,INTERNAL_GC,ELEM\nALLSEL,ALL\n'
                'ET,5,TARGE169\nKEYOPT,5,2,0\n'
                'ET,6,CONTA172\nKEYOPT,6,2,1\nKEYOPT,6,4,2\nKEYOPT,6,10,0\n'
                'R,6,,,10,-5e-5\n')
        overlay(f,mesh,owners,target,5,6)
        f.write('ESEL,S,TYPE,,5\nCM,LOCAL_PAIR_TARGET,ELEM\nALLSEL,ALL\n')
        overlay(f,mesh,owners,source,6,6)
        f.write('ESEL,S,TYPE,,6\nCM,LOCAL_PAIR_CONTACT,ELEM\nALLSEL,ALL\n')
        for group,label in [('INTERNAL_GC','gc'),('LOCAL_PAIR_TARGET','target'),('LOCAL_PAIR_CONTACT','contact')]:
            f.write(f'CMSEL,S,{group}\n*GET,NFACE,ELEM,0,COUNT\n'
                    f'*CFOPEN,{label}_topology,csv\n*VWRITE\n'
                    "('element,i,j,mid,type,section,real')\n"
                    'IE=0\n*DO,KK,1,NFACE\nIE=ELNEXT(IE)\n'
                    '*GET,NI,ELEM,IE,NODE,1\n*GET,NJ,ELEM,IE,NODE,2\n'
                    '*GET,NM,ELEM,IE,NODE,3\n*GET,TY,ELEM,IE,ATTR,TYPE\n'
                    '*GET,SC,ELEM,IE,ATTR,SECN\n*GET,RC,ELEM,IE,ATTR,REAL\n'
                    '*VWRITE,IE,NI,NJ,NM,TY,SC,RC\n'
                    "(F12.0,6(',',F12.0))\n*ENDDO\n*CFCLOS\nALLSEL,ALL\n")
        f.write('/OUTPUT,contact_types,txt\nETLIST,ALL\nRLIST,ALL\nGCDEF,LIST\n/OUTPUT\n'
                'FINISH\nSAVE,contact_model_pair,db,,MODEL\n/EXIT,NOSAVE\n')
    m={'schema':'young-dawgs-v068-track-b-local-pair-native-setup',
       'source_original_database_sha256':original['native_database_sha256'],
       'source_original_setup_receipt_sha256':original['setup_receipt_sha256'],
       'fixture_qualification_sha256':file_hash(RUN/'track_B_contact_fixture/PAIR_FIXTURE_QUALIFICATION.json'),
       'pair_protocol_sha256':file_hash(RUN/'protocol/TRACK_B_LOCAL_PAIR_002.json'),
       'mesh_semantic_sha256':original['source_mesh_semantic_sha256'],
       'source_faces':source.tolist(),'target_faces':target.tolist(),
       'removed_gc_element_ids':face_eid[np.r_[source,target]].tolist(),
       'expected_remaining_gc':len(mesh.boundary)-len(source)-len(target),
       'model':original_model,'input_sha256':file_hash(d/'input.inp'),'setup_only':True}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_contact_fixture')
    print('Prepared native pair setup',len(source),len(target),m['expected_remaining_gc'],flush=True)


def execute_setup():
    d=BASE/'track_B_pair_setup_002'
    r=run_progressive(d,timeout=900,no_progress_seconds=300,cores=2,disk_reserve=80*1024**3)
    r['execution_kind']='LICENSED_SELECTED_SPECIMEN_PAIR_SETUP_ONLY'
    write_json(d/'execution_receipt.json',r)
    target=copy_evidence(d,'track_B_native_results')
    for name in ['gc_topology.csv','target_topology.csv','contact_topology.csv','contact_types.txt']:
        p=d/name
        if p.exists() and p.stat().st_size<2**20:(target/name).write_bytes(p.read_bytes())
    print('Native pair setup',r['status'],r['process']['returncode'],flush=True)


def verify_setup():
    mesh,source,target,p=selection()
    d=BASE/'track_B_pair_setup_002';m=read(d/'simulation_manifest.json');r=read(d/'execution_receipt.json')
    if (r['process']['returncode']!=0 or r['solver_version']!='2024 R1' or
        r['input_sha256']!=m['input_sha256'] or file_hash(d/'input.inp')!=m['input_sha256'] or
        file_hash(d/'contact_model_pair.db')!=r['process']['artifacts']['contact_model_pair.db']['sha256']):
        raise ValueError('Native pair setup or identity failed')
    out=(d/'solver.out').read_text(errors='replace')
    if 'NUMBER OF ERROR   MESSAGES ENCOUNTERED=          0' not in out:
        raise ValueError('Native pair setup has errors')
    excluded=set(np.r_[source,target].tolist())
    expected={'gc':{tuple((mesh.boundary[i]+1).tolist()) for i in range(len(mesh.boundary)) if i not in excluded}}
    expected['target']={tuple((mesh.boundary[i]+1).tolist()) for i in target}
    expected['contact']={tuple((mesh.boundary[i]+1).tolist()) for i in source}
    counts={};hashes={}
    for label,typ in [('gc',4),('target',5),('contact',6)]:
        path=d/(label+'_topology.csv')
        a=np.loadtxt(path,delimiter=',',skiprows=1,ndmin=2)
        faces=[tuple(row) for row in a[:,1:4].astype(int)]
        if len(faces)!=len(expected[label]) or set(faces)!=expected[label] or len(set(faces))!=len(faces) or not np.all(a[:,4]==typ):
            raise ValueError('Native '+label+' topology differs from exact original face selection')
        if label!='gc' and not np.all(a[:,6]==6):raise ValueError('Native pair real set differs')
        if label=='gc' and not np.all(a[:,5]==4):raise ValueError('Native GC section differs')
        counts[label]=len(a);hashes[label]=file_hash(path)
    types=(d/'contact_types.txt').read_text(errors='replace')
    for pattern in [
        r'ELEMENT TYPE\s+5 IS TARGE169[\s\S]*?KEYOPT\( 1- 6\)=\s*0\s+0\s+0',
        r'ELEMENT TYPE\s+6 IS CONTA172[\s\S]*?KEYOPT\( 1- 6\)=\s*0\s+1\s+0\s+2',
        r'REAL CONSTANT SET\s+6\s+ITEMS\s+1 TO\s+6[\s\S]*?10\.000\s+-0\.50000E-04',
        r'ALL\s+SELF\s+SYMM\s+1\s+100']:
        if not re.search(pattern,types):
            raise ValueError('Native installed contact property differs: '+pattern)
    q={'status':'PASS_NATIVE_TRACK_B_LOCAL_PAIR_SETUP','native_solver_version':r['solver_version'],
       'source_database_sha256':m['source_original_database_sha256'],
       'pair_database_sha256':file_hash(d/'contact_model_pair.db'),
       'setup_receipt_sha256':file_hash(d/'execution_receipt.json'),
       'source_mesh_semantic_sha256':m['mesh_semantic_sha256'],
       'native_exact_face_counts':counts,'native_topology_sha256':hashes,
       'removed_gc_faces':len(excluded),'no_duplicate_face_exposure':True,
       'scope':'Native setup only; mechanical contact and strain remain unqualified.'}
    write_json(RUN/'track_B_contact_fixture/PAIR_SETUP_QUALIFICATION.json',q)
    print(q['status'],counts,flush=True)
    return q


def prepare_first():
    q=verify_setup()
    model=read(BASE/'track_B_setup_001/simulation_manifest.json')
    d=BASE/'track_B_pair_first_002';d.mkdir(parents=True,exist_ok=False)
    top=model['controls']['top'];bottom=model['controls']['bottom']
    lines=['/BATCH','/CLEAR,START',database_resume(BASE/'track_B_pair_setup_002/contact_model_pair.db').strip(),
           '/FILNAME,compression','/GOPR','/SOLU','ANTYPE,STATIC','NLGEOM,ON','EQSLV,SPARSE',
           'NROPT,FULL','LNSRCH,ON','CNVTOL,F,,.005,2,1e-8',
           'NLHIST,NSOL,RFLOW,F,Y,'+str(bottom)]
    lines+=telemetry_commands(top)
    controls=load_commands(.005,0,top,2.56,initial=.0005,maximum=.0025,minimum=1e-6)
    i=controls.index('OUTRES,ERASE');j=controls.index('OUTPR,ALL,NONE')
    controls[i:j]=['OUTRES,ALL,ALL','OUTRES,NLOAD,ALL']
    controls.insert(controls.index('SOLVE'),'NEQIT,40')
    lines+=controls+['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    manifest={'schema':'young-dawgs-v068-track-b-pair-first',
              'model_variant':'V068_TRACK_B_CENTRAL256_LOCAL_PAIR_002',
              'source_pair_setup_receipt_sha256':q['setup_receipt_sha256'],
              'source_pair_database_sha256':q['pair_database_sha256'],
              'mesh_semantic_sha256':q['source_mesh_semantic_sha256'],
              'model':{**model,'user_model_elements':model['user_model_elements_before_GC']+len(mesh_and_plan()[0].boundary),
                       'general_contact_elements':q['native_exact_face_counts']['gc'],
                       'pair_contact_elements':q['native_exact_face_counts']['contact']},
              'target_engineering_strain':.005,'target_displacement_mm':-.0128,
              'all_native_fields_all_substeps':True,'input_sha256':file_hash(d/'input.inp'),
              'mechanical_mesh_convergence':'UNQUALIFIED'}
    write_json(d/'simulation_manifest.json',manifest)
    copy_evidence(d,'track_B_progressive_compression')
    print('Prepared fresh pair 0.5% stage',flush=True)


def execute_first():
    d=BASE/'track_B_pair_first_002'
    r=run_progressive(d,timeout=5400,no_progress_seconds=1200,cores=8,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Pair first',r['status'],r['process']['returncode'],r['converged_steps'][-5:],flush=True)


def next_name(target):return f'track_B_pair_to_{round(target*100000):05d}_001'


def prepare_next(parent_name,target):
    protocol=read(RUN/'protocol/TRACK_B_LOCAL_PAIR_002.json')
    targets=protocol['first_targets']+protocol['continuation_targets']
    if target not in targets[1:]:raise ValueError('Unregistered pair target')
    qpath=RUN/'track_B_progressive_compression'/(parent_name+'_qualification.json')
    q=read(qpath)
    if not q['accepted'] or len(q['states'])!=1 or not q['states'][0]['accepted']:
        raise ValueError('Cannot advance from unqualified pair parent')
    previous=q['states'][0]['measurement']['engineering_compression_strain']
    if targets.index(target)!=targets.index(previous)+1:
        raise ValueError('Pair loading checkpoint skipped')
    source=BASE/parent_name;name=next_name(target);d=BASE/name
    inherited=authenticated_restart_copy(source,d,expected_mesh=read(RUN/'track_B_mesh/MESH_001.json')['semantic_sha256'])
    if file_hash(source/'execution_receipt.json')!=q['source_receipt_sha256']:
        raise ValueError('Qualified pair parent receipt changed')
    model=inherited['model'];top=model['controls']['top'];bottom=model['controls']['bottom']
    state=q['states'][0]
    lines=['/BATCH','/CLEAR,START','RESUME,compression,rdb','/FILNAME,compression',
           '/GOPR','/SOLU',f'ANTYPE,STATIC,REST,{state["load_step"]},{state["substep"]},CONTINUE',
           'NLGEOM,ON','EQSLV,SPARSE','CNVTOL,F,,.005,2,1e-8',
           f'NLHIST,NSOL,RFLOW,F,Y,{bottom}']
    lines+=telemetry_commands(top)
    initial=.00005 if previous>=.01 and target<=.02 else .0005
    maximum=.0001 if previous>=.01 and target<=.02 else .0025
    controls=load_commands(target,previous,top,2.56,initial=initial,maximum=maximum,minimum=1e-6)
    i=controls.index('OUTRES,ERASE');j=controls.index('OUTPR,ALL,NONE')
    controls[i:j]=['OUTRES,ALL,ALL','OUTRES,NLOAD,ALL']
    controls.insert(controls.index('SOLVE'),'NEQIT,40')
    lines+=controls+['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    manifest={'schema':'young-dawgs-v068-track-b-pair-continuation',
              'model_variant':'V068_TRACK_B_CENTRAL256_LOCAL_PAIR_002',
              'parent':parent_name,'parent_qualification_sha256':file_hash(qpath),
              'parent_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
              'parent_RST_sha256':file_hash(source/'compression.rst'),
              'restart_provenance_sha256':file_hash(d/'restart_provenance.json'),
              'previous_engineering_strain':previous,'target_engineering_strain':target,
              'target_displacement_mm':-2.56*target,
              'mesh_semantic_sha256':inherited['mesh_semantic_sha256'],
              'model':model,'input_sha256':file_hash(d/'input.inp'),
              'all_native_fields_all_substeps':True,'mechanical_mesh_convergence':'UNQUALIFIED'}
    write_json(d/'simulation_manifest.json',manifest)
    copy_evidence(d,'track_B_progressive_compression')
    print('Prepared pair continuation',name,'from',parent_name,'to',target,flush=True)


def execute_next(target):
    name=next_name(target);d=BASE/name
    r=run_progressive(d,timeout=5400,no_progress_seconds=1200,cores=8,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Pair continuation',name,r['status'],r['process']['returncode'],r['converged_steps'][-5:],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare-setup','execute-setup','verify-setup','prepare-first','execute-first','prepare-next','execute-next'])
    p.add_argument('--parent');p.add_argument('--target',type=float)
    a=p.parse_args()
    {'prepare-setup':prepare_setup,'execute-setup':execute_setup,'verify-setup':verify_setup,
     'prepare-first':prepare_first,'execute-first':execute_first,
     'prepare-next':lambda:prepare_next(a.parent,a.target),
     'execute-next':lambda:execute_next(a.target)}[a.action]()
