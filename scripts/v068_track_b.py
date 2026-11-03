"""Registered central-crop native contact model and first progressive stage."""
import argparse
import json
from pathlib import Path
import re
import numpy as np

from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.contact_setup import platen_plan
from metamaterial_eval.simulation.microstructure_import import component
from metamaterial_eval.simulation.progressive_compression import run_progressive, load_commands
from metamaterial_eval.simulation.reporting import mesh_hash
from scripts.v068_common import RUN, BASE, read, write_json, file_hash, copy_evidence


def mesh_and_plan():
    spec=read(RUN/'track_B_mesh/MESH_001.json')
    if not spec['accepted'] or file_hash(spec['mesh_path'])!=spec['byte_sha256']:
        raise ValueError('Unaccepted or altered Track B mesh')
    with np.load(spec['mesh_path'],allow_pickle=False) as z:
        mesh=Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])
    if mesh_hash(mesh)!=spec['semantic_sha256']:
        raise ValueError('Track B mesh semantics changed')
    cfg=CompressionConfig(width=2.56,height=2.56,boundary_size=.01/3,bulk_size=.04)
    return mesh,platen_plan(mesh,cfg),cfg,spec


def prepare_setup():
    mesh,plan,cfg,spec=mesh_and_plan()
    protocol=read(RUN/'protocol/TRACK_B.json')
    fixture=read(RUN/'track_A_unified_detection/unified_internal_fixture_001/execution_receipt.json')
    inventory=(RUN/'track_A_unified_detection/unified_internal_fixture_001/native_type_after.txt').read_text(encoding='utf-8')
    cnd=read((BASE/'unified_internal_fixture_001')/'contact_telemetry.json')
    final=[r for r in cnd['records'] if r['load_step']==1 and r['substep']==14 and r['pair']==-2]
    if (fixture['solver_version']!='2024 R1' or fixture['process']['returncode']!=0 or
        not re.search(r'KEYOPT\( 1- 6\)=\s*0\s+1\s+0\s+5',inventory) or
        not final or final[-1]['active_elements']<1 or final[-1]['max_pressure_MPa']<=0 or
        final[-1]['penetration_or_gap_mm']>5e-5):
        raise ValueError('Unified contact not qualified on actual small fixture')
    detection=5
    directory=BASE/'track_B_setup_001';directory.mkdir(parents=True,exist_ok=False)
    n=len(mesh.nodes);ne=len(mesh.triangles);eid=ne
    bottom=np.asarray(plan['bottom']['nodes']);anchor=int(bottom[np.argmin(mesh.nodes[bottom,0])])+1
    controls={}
    with (directory/'input.inp').open('w',encoding='utf-8',newline='\n',buffering=1024**2) as f:
        f.write('/BATCH\n/CLEAR,START\n/FILNAME,compression\n/NOPR\n/PREP7\n'
                'ET,1,PLANE183\nKEYOPT,1,1,1\nKEYOPT,1,3,3\nR,1,1\n'
                'MP,EX,1,1000\nMP,PRXY,1,.3\nMP,MU,1,0\nTYPE,1\nREAL,1\nMAT,1\n')
        for offset in range(0,n,10000):
            f.writelines(f'N,{i+1},{x:.17g},{y:.17g},0\n' for i,(x,y) in enumerate(mesh.nodes[offset:offset+10000],offset))
        for offset in range(0,ne,10000):
            f.writelines('EN,'+str(i+1)+','+','.join(str(int(k)+1) for k in t)+'\n' for i,t in enumerate(mesh.triangles[offset:offset+10000],offset))
        f.write('ESEL,S,TYPE,,1\nCM,SPECIMEN,ELEM\nALLSEL,ALL\n')
        component(f,'CORNERS',np.unique(mesh.triangles[:,:3])+1)
        component(f,'PHYSICAL_NODES',np.unique(mesh.boundary)+1)
        for group in ['top','bottom','pore','external']:
            edges=mesh.boundary[mesh.boundary_groups==group]
            if len(edges):component(f,group.upper()+'_FACE',np.unique(edges)+1)
        f.write('ET,2,TARGE169\nKEYOPT,2,2,1\nET,3,CONTA172\n'
                'KEYOPT,3,2,1\nKEYOPT,3,4,2\nKEYOPT,3,10,1\n')
        for index,group in enumerate(['bottom','top']):
            real=index+2;y=0 if group=='bottom' else cfg.height
            left,right,pilot=n+index*3+1,n+index*3+2,n+index*3+3
            controls[group]=pilot
            f.write(f'R,{real},,,100,-1e-5\nN,{left},{-cfg.width*.05:.17g},{y:.17g},0\n'
                    f'N,{right},{cfg.width*1.05:.17g},{y:.17g},0\n'
                    f'N,{pilot},{cfg.width/2:.17g},{y:.17g},0\nTYPE,2\nREAL,{real}\nTSHAP,LINE\n')
            a,b=(right,left) if group=='bottom' else (left,right)
            eid+=1;f.write(f'EN,{eid},{a},{b}\n')
            eid+=1;f.write(f'TSHAP,PILO\nEN,{eid},{pilot}\nTYPE,3\nREAL,{real}\nMAT,1\n')
            first=eid+1
            for a,b,mid in plan[group]['edges']:
                eid+=1;f.write(f'EN,{eid},{a+1},{b+1},{mid+1}\n')
            f.write(f'ESEL,S,ELEM,,{first},{eid}\nCM,{group.upper()}_CONTACT,ELEM\nALLSEL,ALL\n')
            component(f,group.upper()+'_PILOT',[pilot])
        f.write('ALLSEL,ALL\nESEL,S,TYPE,,1\nGCGEN,NEW,42,0,PART,SELECT\n'
                'GCGEN,SELECT\nCM,ALL_GC,ELEM\nALLSEL,ALL\n'
                'CMSEL,S,PHYSICAL_NODES\nESLN,S,1,ALL\nCMSEL,R,ALL_GC\n'
                'CM,INTERNAL_GC,ELEM\nCMSEL,S,ALL_GC\nCMSEL,U,INTERNAL_GC\n'
                'EDELE,ALL\nALLSEL,ALL\nCMSEL,S,INTERNAL_GC\n'
                'EMODIF,ALL,TYPE,4\nEMODIF,ALL,SECNUM,4\nALLSEL,ALL\n'
                '*GET,ETMAX,ETYP,0,NUM,MAX\n*DO,IT,4,ETMAX\n'
                f'KEYOPT,IT,2,1\nKEYOPT,IT,4,{detection}\nKEYOPT,IT,10,0\n*ENDDO\n'
                f'R,100,,,10,-{protocol["acceptance"]["penetration_max_mm"]:.17g}\n'
                'GCDEF,SYMM,ALL,SELF,1,100\n'
                f'D,{controls["bottom"]},UX,0\nD,{controls["bottom"]},UY,0\n'
                f'D,{controls["bottom"]},ROTZ,0\nD,{controls["top"]},UX,0\n'
                f'D,{controls["top"]},ROTZ,0\nD,{anchor},UX,0\n'
                '/GOPR\n/OUTPUT,model_inventory,txt\nETLIST,ALL\nRLIST,ALL\nMPLIST,ALL\nCMLIST,ALL\n'
                '*GET,NNCHK,NODE,0,COUNT\n*GET,NECHK,ELEM,0,COUNT\n'
                '*VWRITE,NNCHK,NECHK\n'
                "('TRANSFER_COUNTS ',F16.0,1X,F16.0)\n/OUTPUT\n"
                'CMSEL,S,INTERNAL_GC\n*GET,NGC,ELEM,0,COUNT\n'
                '*CFOPEN,gc_topology,csv\n*VWRITE\n'
                "('element,i,j,mid,type,section')\n"
                'IE=0\n*DO,KK,1,NGC\nIE=ELNEXT(IE)\n'
                '*GET,NI,ELEM,IE,NODE,1\n*GET,NJ,ELEM,IE,NODE,2\n'
                '*GET,NM,ELEM,IE,NODE,3\n*GET,TY,ELEM,IE,ATTR,TYPE\n'
                '*GET,SC,ELEM,IE,ATTR,SECN\n*VWRITE,IE,NI,NJ,NM,TY,SC\n'
                "(F12.0,5(',',F12.0))\n*ENDDO\n*CFCLOS\nALLSEL,ALL\n"
                '/OUTPUT,contact_types,txt\nETLIST,ALL\nGCDEF,LIST\n/OUTPUT\n'
                'FINISH\nSAVE,contact_model,db,,MODEL\n/EXIT,NOSAVE\n')
    model={'schema':'young-dawgs-v068-track-b','specimen_nodes':n,'specimen_TRI6':ne,
           'user_model_nodes':n+6,'user_model_elements_before_GC':eid,
           'controls':controls,'anchor_UX_node':anchor,
           'platen_contact_elements':{g:len(plan[g]['edges']) for g in ['top','bottom']},
           'config':cfg.manifest(),'general_contact_component':'INTERNAL_GC',
           'general_contact_detection_keyopt4':detection,'general_contact_FKN':10,
           'platen_detection_keyopt4':2,'platen_FKN':100,
           'source_mesh_semantic_sha256':spec['semantic_sha256'],
           'source_mesh_archive_sha256':spec['byte_sha256'],
           'source_geometry_sha256':spec['source_geometry_sha256'],
           'fixture_receipt_sha256':file_hash(RUN/'track_A_unified_detection/unified_internal_fixture_001/execution_receipt.json'),
           'fixture_final_active_elements':final[-1]['active_elements'],
           'fixture_final_pressure_MPa':final[-1]['max_pressure_MPa'],
           'fixture_final_native_penetration_mm':final[-1]['penetration_or_gap_mm'],
           'input_sha256':file_hash(directory/'input.inp'),'setup_only':True,
           'mechanical_mesh_convergence':'UNQUALIFIED'}
    write_json(directory/'simulation_manifest.json',model)
    copy_evidence(directory,'track_B_contact_fixture')
    print(json.dumps({'directory':str(directory),'nodes':n,'TRI6':ne,
                      'boundary_faces':len(mesh.boundary),'contact_detection':detection}),flush=True)


def execute_setup():
    d=BASE/'track_B_setup_001'
    receipt=run_progressive(d,timeout=900,no_progress_seconds=300,cores=2,disk_reserve=80*1024**3)
    receipt['execution_kind']='LICENSED_CONTACT_SETUP_ONLY'
    write_json(d/'execution_receipt.json',receipt)
    copy_evidence(d,'track_B_contact_fixture')
    print('Track B setup',receipt['status'],receipt['process']['returncode'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare-setup','execute-setup'])
    a=p.parse_args()
    prepare_setup() if a.action=='prepare-setup' else execute_setup()
