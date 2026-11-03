"""Bounded original-mesh expanded-context contact comparison for Track A."""
import argparse
import json
from pathlib import Path
import numpy as np

from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.ansys_adapter import component
from metamaterial_eval.simulation.progressive_compression import run_progressive
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


SOURCE=BASE/'track_A_expanded_fixture_001'


def prepare(label,detection):
    if (label,detection) not in [('track_A_expanded_nodal2_001',2),('track_A_expanded_unified5_001',5)]:
        raise ValueError('Unregistered Track A case')
    spec=read(SOURCE/'fixture_manifest.json')
    if file_hash(SOURCE/'mesh.npz')!=spec['mesh_archive_sha256'] or file_hash(SOURCE/'measured_displacements.npy')!=spec['history_array_sha256']:
        raise ValueError('Altered original-mesh local source')
    with np.load(SOURCE/'mesh.npz',allow_pickle=False) as z:
        xy,tri,boundary,groups,cut=[z[k] for k in ['nodes','triangles','boundary','boundary_groups','cut_nodes_zero_based']]
    measured=np.load(SOURCE/'measured_displacements.npy')
    n,ne=len(xy),len(tri)
    if len(measured)!=15 or measured.shape[1:]!=(n,2):raise ValueError('Incomplete parent history')
    top_edges=boundary[groups=='top']
    if not len(top_edges):raise ValueError('No top platen faces')
    left,right,pilot=n+1,n+2,n+3
    lines=['/BATCH','/CLEAR,START','/FILNAME,compression','/NOPR','/PREP7',
           'ET,1,PLANE183','KEYOPT,1,1,1','KEYOPT,1,3,3','R,1,1',
           'MP,EX,1,1000','MP,PRXY,1,.3','MP,MU,1,0','TYPE,1','REAL,1','MAT,1']
    lines += [f'N,{i},{x:.17g},{y:.17g}' for i,(x,y) in enumerate(xy,1)]
    lines += ['EN,'+str(i)+','+','.join(str(int(k)+1) for k in t) for i,t in enumerate(tri,1)]
    lines += component('CORNERS',np.unique(tri[:,:3])+1)
    lines += component('CUT_NODES',cut+1)
    lines += ['ET,2,TARGE169','KEYOPT,2,2,1','ET,3,CONTA172',
              'KEYOPT,3,2,1','KEYOPT,3,4,2','KEYOPT,3,10,1','R,3,,,100,-1e-5',
              f'N,{left},1.5,10.24',f'N,{right},2.45,10.24',f'N,{pilot},1.975,10.24',
              'TYPE,2','REAL,3','TSHAP,LINE',f'EN,{ne+1},{left},{right}',
              'TSHAP,PILO',f'EN,{ne+2},{pilot}','TYPE,3','MAT,1']
    lines += [f'EN,{ne+3+i},{a+1},{b+1},{mid+1}' for i,(a,b,mid) in enumerate(top_edges)]
    lines += ['ALLSEL,ALL','ESEL,S,TYPE,,1','GCGEN,NEW,42,0,PART,SELECT','GCGEN,SELECT',
              'CM,ALL_GC,ELEM','ALLSEL,ALL']
    lines += component('PHYSICAL_NODES',np.unique(boundary[groups!='artificial_cut'])+1)
    lines += ['CMSEL,S,PHYSICAL_NODES','ESLN,S,1,ALL','CMSEL,R,ALL_GC','CM,INTERNAL_GC,ELEM',
              'CMSEL,S,ALL_GC','CMSEL,U,INTERNAL_GC','EDELE,ALL','ALLSEL,ALL',
              'CMSEL,S,INTERNAL_GC','EMODIF,ALL,TYPE,4','EMODIF,ALL,SECNUM,4','ALLSEL,ALL',
              '*GET,ETMAX,ETYP,0,NUM,MAX','*DO,IT,4,ETMAX','KEYOPT,IT,2,1',
              f'KEYOPT,IT,4,{detection}','KEYOPT,IT,10,0','*ENDDO',
              'R,100,,,100,-1e-5','GCDEF,SYMM,ALL,SELF,1,100',
              f'D,{pilot},UX,0',f'D,{pilot},UY,0',f'D,{pilot},ROTZ,0',
              '/GOPR','/OUTPUT,local_inventory,txt','ETLIST,ALL','RLIST,ALL','GCDEF,LIST',
              'CMSEL,S,INTERNAL_GC','*GET,NGC,ELEM,0,COUNT','*STATUS,NGC','ALLSEL,ALL','/OUTPUT',
              'CMSEL,S,INTERNAL_GC','*CFOPEN,gc_topology,csv','*VWRITE',
              "('element,i,j,mid,type,section')",'IE=0','*DO,KK,1,NGC','IE=ELNEXT(IE)',
              '*GET,NI,ELEM,IE,NODE,1','*GET,NJ,ELEM,IE,NODE,2',
              '*GET,NM,ELEM,IE,NODE,3','*GET,TY,ELEM,IE,ATTR,TYPE',
              '*GET,SC,ELEM,IE,ATTR,SECN','*VWRITE,IE,NI,NJ,NM,TY,SC',
              "(F12.0,5(',',F12.0))",'*ENDDO','*CFCLOS','ALLSEL,ALL',
              'FINISH','SAVE,initial,db','/SOLU','ANTYPE,STATIC','NLGEOM,ON',
              'EQSLV,SPARSE','NROPT,FULL','LNSRCH,ON','CNVTOL,F,,.005,2,1e-8',
              'NEQIT,24','AUTOTS,ON','RESCONTROL,DEFINE,ALL,1,-1,,3',
              'NLDIAG,CONT,ITER','NLDIAG,NRRE,ON,2','NLDIAG,EFLG,ON,2','OUTRES,ALL,ALL']
    times=[s['engineering_strain'] for s in spec['source_snapshots']]
    targets=times+[.009387795,.009504981,.00975,.01]
    if len(set(targets))!=len(targets) or targets!=sorted(targets):raise ValueError('Parent local times changed')
    for j,t in enumerate(targets):
        values=(measured[j] if j<len(times) else measured[-1]+(measured[-1]-measured[-2])*((t-times[-1])/(times[-1]-times[-2])))
        lines += [f'TIME,{t:.17g}','NSUBST,2,240,1,OFF',f'D,{pilot},UY,{-10.24*t:.17g}']
        for i in cut:lines += [f'D,{i+1},UX,{values[i,0]:.17g}',f'D,{i+1},UY,{values[i,1]:.17g}']
        lines += ['SOLVE']
    lines += ['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    d=BASE/label;d.mkdir(parents=True,exist_ok=False)
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    manifest={'schema':'young-dawgs-v068-expanded-local-case','model_variant':'V068_TRACK_A_EXPANDED_LOCAL',
              'source_fixture_sha256':file_hash(SOURCE/'fixture_manifest.json'),
              'source_mesh_sha256':spec['mesh_archive_sha256'],
              'source_history_sha256':spec['history_array_sha256'],
              'ROI_centroid_mm':spec['ROI_centroid_mm'],'detection_keyopt4':detection,
              'FKN':100,'targets':targets,'measured_parent_count':len(times),
              'extrapolated_after':times[-1],'input_sha256':file_hash(d/'input.inp'),
              'model':{'specimen_nodes':n,'specimen_TRI6':ne,'user_model_nodes':n+3,
                       'user_model_elements':ne+2+len(top_edges)+spec['physical_faces'],
                       'controls':{'top':pilot},'general_contact_component':'INTERNAL_GC'},
              'scope':'LOCAL_DIAGNOSTIC_ONLY; no full-specimen performance'}
    write_json(d/'simulation_manifest.json',manifest)
    copy_evidence(d,'track_A_local_fixture')
    print('Prepared Track A',label,n,'nodes',ne,'TRI6',flush=True)


def execute(label):
    d=BASE/label
    r=run_progressive(d,timeout=2400,no_progress_seconds=480,cores=2,disk_reserve=80*1024**3)
    copy_evidence(d,'track_A_unified_detection')
    print('Track A',label,r['status'],r['process']['returncode'],r['converged_steps'][-5:],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute'])
    p.add_argument('label');p.add_argument('--detection',type=int)
    a=p.parse_args();prepare(a.label,a.detection) if a.action=='prepare' else execute(a.label)
