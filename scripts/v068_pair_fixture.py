"""Licensed deformable/deformable pair fixture before the Track B pair branch."""
import json
from pathlib import Path
import numpy as np

from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.microstructure_import import component
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.microstructure_results import numeric
from metamaterial_eval.simulation.reporting import mesh_hash
from scripts.v064_small_study import direct_post
from scripts.v068_pair_common import face_owners,overlay
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


def prepare():
    original=artifact_root()/'solver/v066/internal_fixture_enabled_003'
    prior=read(original/'simulation_manifest.json')
    path=artifact_root()/'solver/v066/internal_fixture_geometry_003/mesh.npz'
    with np.load(path,allow_pickle=False) as z:
        mesh=Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])
    if mesh_hash(mesh)!=prior['mesh_semantic_sha256']:raise ValueError('Altered historical compliant fixture')
    source=(original/'import.inp').read_text(encoding='utf-8')
    source=source[:source.index('ALLSEL,ALL\nCHECK')].replace('/FILNAME,model','/FILNAME,compression',1)
    faces=mesh.boundary;p=mesh.nodes[faces[:,:2]]
    target=np.flatnonzero(np.all(np.isclose(p[:,:,1],.15,atol=1e-12),axis=1)&
                          np.all(p[:,:,0]>=.12-1e-10,axis=1))
    contact=np.flatnonzero(np.all(np.isclose(p[:,:,1],.16,atol=1e-12),axis=1)&
                           np.all(p[:,:,0]>=.12-1e-10,axis=1))
    if not len(target) or len(target)!=len(contact):raise ValueError('Fixture pair faces absent')
    owners=face_owners(mesh)
    lower=np.unique(faces[target])+1;upper=np.unique(faces[contact])+1
    bottom=np.unique(faces[mesh.boundary_groups=='bottom'])
    anchor=int(bottom[np.argmin(mesh.nodes[bottom,0])])+1
    d=BASE/'pair_internal_fixture_001';d.mkdir(parents=True,exist_ok=False)
    with (d/'input.inp').open('w',encoding='utf-8',newline='\n') as f:
        f.write(source)
        component(f,'CORNERS',np.unique(mesh.triangles[:,:3])+1)
        component(f,'INNER_LOW',lower);component(f,'INNER_UP',upper)
        f.write('/GOPR\nET,2,TARGE169\nKEYOPT,2,2,0\n'
                'ET,3,CONTA172\nKEYOPT,3,2,1\nKEYOPT,3,4,2\nKEYOPT,3,10,0\n'
                'R,3,,,10,-5e-5\n')
        overlay(f,mesh,owners,target,2,3)
        f.write('ESEL,S,TYPE,,2\nCM,PAIR_TARGET,ELEM\nALLSEL,ALL\n')
        overlay(f,mesh,owners,contact,3,3)
        f.write('ESEL,S,TYPE,,3\nCM,PAIR_CONTACT,ELEM\nALLSEL,ALL\n'
                '/OUTPUT,pair_inventory,txt\nETLIST,ALL\nRLIST,ALL\n'
                'CMSEL,S,PAIR_TARGET\n*GET,NTARG,ELEM,0,COUNT\n'
                'CMSEL,S,PAIR_CONTACT\n*GET,NCONT,ELEM,0,COUNT\n'
                '*VWRITE,NTARG,NCONT\n'
                "('PAIR_COUNTS ',F12.0,1X,F12.0)\n/OUTPUT\n"
                'CMSEL,S,BOTTOM_FACE\nD,ALL,UY,0\nALLSEL,ALL\n'
                f'D,{anchor},UX,0\nCMSEL,S,TOP_FACE\nD,ALL,UY,-.02\nALLSEL,ALL\n'
                'FINISH\n/SOLU\nANTYPE,STATIC\nNLGEOM,ON\nEQSLV,SPARSE\n'
                'NROPT,FULL\nAUTOTS,ON\nNSUBST,20,1000,10\nNEQIT,40\n'
                'LNSRCH,ON\nCNVTOL,F,,.005,2,1e-8\nOUTRES,ALL,ALL\n'
                'RESCONTROL,DEFINE,ALL,1,-1,,3\nNLDIAG,CONT,ITER\n'
                'TIME,0.064516129032258063\nSOLVE\n')
        f.write('\n'.join(direct_post({'specimen_nodes':len(mesh.nodes)},.064516129032258063))+'\n')
        f.write('CMSEL,S,PAIR_CONTACT\n*GET,NC,ELEM,0,COUNT\n'
                '*CFOPEN,pair_contact,csv\n*VWRITE\n'
                "('element,status,pressure_i_MPa,pressure_j_MPa,pen_i_mm,pen_j_mm,fy_N')\n"
                'EID=0\n*DO,KK,1,NC\nEID=ELNEXT(EID)\n'
                '*GET,STV,ELEM,EID,NMISC,19\n*GET,PI,ELEM,EID,SMISC,1\n'
                '*GET,PJ,ELEM,EID,SMISC,2\n*GET,GI,ELEM,EID,NMISC,5\n'
                '*GET,GJ,ELEM,EID,NMISC,6\n*GET,FYV,ELEM,EID,NMISC,22\n'
                '*VWRITE,EID,STV,PI,PJ,GI,GJ,FYV\n'
                "(F12.0,',',F4.0,5(',',E24.16))\n*ENDDO\n*CFCLOS\n"
                '*CFOPEN,patch_forces,csv\n*VWRITE\n'
                "('patch,solid_fx_N,solid_fy_N,pair_fx_N,pair_fy_N')\n")
        for i,group in enumerate(['INNER_LOW','INNER_UP'],1):
            f.write('ALLSEL,ALL\nCMSEL,S,'+group+'\nESEL,S,TYPE,,1\nFSUM\n'
                    '*GET,SFX,FSUM,0,ITEM,FX\n*GET,SFY,FSUM,0,ITEM,FY\n'
                    'ESEL,S,TYPE,,3\nFSUM,,CONT\n'
                    '*GET,CFX,FSUM,0,ITEM,FX\n*GET,CFY,FSUM,0,ITEM,FY\n'
                    f'*VWRITE,{i},SFX,SFY,CFX,CFY\n'
                    "(F4.0,4(',',E24.16))\n")
        f.write('*CFCLOS\nALLSEL,ALL\nFINISH\nSAVE,checkpoint,db,,MODEL\n/EXIT,NOSAVE\n')
    m={'schema':'young-dawgs-v068-compliant-explicit-pair-fixture',
       'source_mesh_semantic_sha256':prior['mesh_semantic_sha256'],
       'source_mesh_archive_sha256':file_hash(path),
       'source_import_input_sha256':file_hash(original/'import.inp'),
       'target_original_face_indices':target.tolist(),'contact_original_face_indices':contact.tolist(),
       'target_faces':len(target),'contact_faces':len(contact),
       'target_native_element_type':2,'contact_native_element_type':3,
       'input_sha256':file_hash(d/'input.inp'),'gap_mm':.01,'travel_mm':.02,
       'scope':'Connected small compliant internal-contact fixture, not Design9 specimen'}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_contact_fixture')
    print('Prepared pair fixture',len(target),len(contact),flush=True)


def execute():
    d=BASE/'pair_internal_fixture_001'
    r=run_progressive(d,timeout=300,no_progress_seconds=180,cores=2,disk_reserve=80*1024**3)
    target=copy_evidence(d,'track_B_native_results')
    for name in ['pair_inventory.txt','pair_contact.csv','patch_forces.csv','direct_history.csv']:
        p=d/name
        if p.exists() and p.stat().st_size<1024**2:
            (target/name).write_bytes(p.read_bytes())
    print('Pair fixture',r['status'],r['process']['returncode'],r['converged_steps'][-3:],flush=True)


def qualify():
    d=BASE/'pair_internal_fixture_001';m=read(d/'simulation_manifest.json');r=read(d/'execution_receipt.json')
    if r['solver_version']!='2024 R1' or r['process']['returncode']!=0 or file_hash(d/'input.inp')!=m['input_sha256']:
        raise ValueError('Native pair fixture failed')
    inventory=(d/'pair_inventory.txt').read_text(errors='replace')
    import re
    c=re.search(r'PAIR_COUNTS\s+(\d+)\.\s+(\d+)\.',inventory)
    if not c or list(map(int,c.groups()))!=[m['target_faces'],m['contact_faces']]:
        raise ValueError('Native pair overlay face counts differ')
    h=numeric(d/'direct_history.csv',['pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'])
    contact=numeric(d/'pair_contact.csv',['element','status','pressure_i_MPa','pressure_j_MPa','pen_i_mm','pen_j_mm','fy_N'])
    forces=numeric(d/'patch_forces.csv',['patch','solid_fx_N','solid_fy_N','pair_fx_N','pair_fy_N'])
    if h.shape!=(1,6) or len(contact)!=m['contact_faces'] or forces.shape!=(2,5):
        raise ValueError('Incomplete actual pair fixture data')
    balance=abs(h[0,4]+h[0,5])/max(abs(h[0,4]),abs(h[0,5]),1e-12)
    solid=forces[:,1:3];scale=float(np.linalg.norm(solid,axis=1).max())
    opposition=float(np.linalg.norm(solid.sum(axis=0))/max(scale,1e-12))
    pressure=float(contact[:,2:4].max());penetration=max(0,float(contact[:,4:6].max()))
    closed=int(np.sum(contact[:,1]>=2))
    passed=bool(closed>0 and pressure>0 and penetration<=5e-5 and
                h[0,4]<0<h[0,5] and balance<=.01 and scale>1e-8 and opposition<=.01)
    result={'status':'PASS_LICENSED_COMPLIANT_DEFORMABLE_PAIR' if passed else 'HOLD_PAIR_FIXTURE',
            'passed':passed,'native_solver_version':r['solver_version'],
            'native_converged_substeps':r['converged_steps'],
            'native_target_faces':m['target_faces'],'native_contact_faces':m['contact_faces'],
            'closed_contact_faces':closed,'max_pressure_MPa':pressure,
            'max_endpoint_penetration_mm':penetration,
            'signed_reaction_balance_relative':balance,
            'two_sided_structural_force_opposition_relative':opposition,
            'upper_rf_y_N':float(h[0,4]),'lower_rf_y_N':float(h[0,5]),
            'source_execution_receipt_sha256':file_hash(d/'execution_receipt.json'),
            'native_pair_inventory_sha256':file_hash(d/'pair_inventory.txt'),
            'native_pair_contact_sha256':file_hash(d/'pair_contact.csv'),
            'native_structural_force_sha256':file_hash(d/'patch_forces.csv'),
            'scope':'Validates explicit deformable pair formulation on small connected C-cell only; selected demonstrator still requires its own setup/solve gates.'}
    write_json(RUN/'track_B_contact_fixture/PAIR_FIXTURE_QUALIFICATION.json',result)
    print(result['status'],closed,pressure,penetration,opposition,flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','qualify']);a=p.parse_args()
    {'prepare':prepare,'execute':execute,'qualify':qualify}[a.action]()
