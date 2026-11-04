"""Exact Track B original-element local replay; measured histories, no remeshing."""
import argparse
import numpy as np
from scripts.v069_study import RUN,BASE,OLD,PREVIOUS,DOC,read,write_json,file_hash
from scripts.v068_track_b import mesh_and_plan
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.microstructure_import import component
from scripts.v066_restart import compact


def extract():
    mesh,_,_,spec=mesh_and_plan();xy=mesh.nodes
    centers=xy[mesh.triangles[:,:3]].mean(axis=1)
    keep=(centers[:,0]>=2.35)&(centers[:,1]>=2.05)&(centers[:,1]<=2.45)
    vertices=np.unique(mesh.triangles[keep]);keep|=np.any(np.isin(mesh.triangles,vertices),axis=1)
    eids=np.flatnonzero(keep)+1;tri=mesh.triangles[keep];nodes=np.unique(tri)+1
    edges={}
    for t in tri:
        for a,b,m in [(t[0],t[1],t[3]),(t[1],t[2],t[4]),(t[2],t[0],t[5])]:
            edges.setdefault(tuple(sorted((a,b))),[]).append([a,b,m])
    boundary=np.array([v[0] for v in edges.values() if len(v)==1])
    physical={tuple(sorted(f[:2])):i for i,f in enumerate(mesh.boundary)}
    cut=np.array([f for f in boundary if tuple(sorted(f[:2])) not in physical])
    cutnodes=np.unique(cut)+1;corners=np.unique(tri[:,:3])+1
    local=BASE/'local_source_001';local.mkdir(exist_ok=False)
    np.savez(local/'source.npz',nodes=nodes,eids=eids,triangles=tri,boundary=boundary,cut=cut,cutnodes=cutnodes,corners=corners)
    states=[]
    for name in ['track_B_pair5_first_001','track_B_pair5_to_01000_001','track_B_pair5_to_01100_001','track_B_pair5_to_01150_001','track_B_pair5_to_01200_001','track_B_pair5_to_01500_001']:
        for s in read(OLD/name/'nonlinear_telemetry.json')['converged_substeps']:
            if 'pseudo_time' in s and s['substep']!=999999:
                states.append({'source':name,'load_step':s['load_step'],'substep':s['substep'],'time':s['pseudo_time']})
    assert all(states[i]['time']<states[i+1]['time'] for i in range(len(states)-1))
    d=BASE/'parent_local_readback_001';d.mkdir(exist_ok=False)
    with (d/'input.inp').open('w',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n'+database_resume(OLD/'track_B_pair_unified_setup_001/contact_model_pair_unified.db')+'/FILNAME,readonly\n/PREP7\n')
        component(f,'LOCAL_NODES',nodes);component(f,'LOCAL_CORNERS',corners);component(f,'LOCAL_SOLIDS',eids);component(f,'CUT_NODES',cutnodes)
        f.write('FINISH\n/POST1\n')
        for i,s in enumerate(states,1):
            prefix=f'state{i:03d}'
            f.write("FILE,'"+(OLD/s['source']/'compression').as_posix()+f"',rst\nSET,{s['load_step']},{s['substep']}\n")
            export_fields(f,prefix)
            f.write('CMSEL,S,CUT_NODES\nCMSEL,S,LOCAL_SOLIDS,ELEM\nFSUM\n*GET,FX,FSUM,0,ITEM,FX\n*GET,FY,FSUM,0,ITEM,FY\n'+f'*CFOPEN,{prefix}_force,csv\n*VWRITE,FX,FY\n(2(E24.16,\',\'))\n*CFCLOS\nALLSEL,ALL\n')
        f.write('FINISH\n/EXIT,NOSAVE\n')
    manifest={'schema':'v069-exact-original-mesh-local-history','states':states,'nodes':len(nodes),'elements':len(eids),
       'cut_nodes':len(cutnodes),'source_archive_sha256':file_hash(local/'source.npz'),'mesh_semantic_sha256':spec['semantic_sha256'],
       'native_sources':{s['source']:file_hash(OLD/s['source']/'compression.rst') for s in states},'input_sha256':file_hash(d/'input.inp')}
    write_json(d/'simulation_manifest.json',manifest);write_json(RUN/'local/SOURCE.json',manifest)
    print('Prepared',len(nodes),len(eids),len(states),'native local-history readback')


def export_fields(f,prefix):
    for comp,label,quantities in [('LOCAL_NODES','u',[('UX','U','X'),('UY','U','Y')]),
      ('LOCAL_CORNERS','fields',[('SX','S','X'),('SY','S','Y'),('SXY','S','XY'),('SEQ','S','EQV'),('EX','EPEL','X'),('EY','EPEL','Y'),('EXY','EPEL','XY')])]:
        f.write(f'ALLSEL,ALL\nCMSEL,S,{comp}\n*GET,NN,NODE,0,COUNT\n*CFOPEN,{prefix}_{label},csv\nNI=0\n*DO,J,1,NN\nNI=NDNEXT(NI)\n')
        for var,item,sub in quantities:f.write(f'*GET,{var},NODE,NI,{item},{sub}\n')
        f.write('*VWRITE,NI,'+','.join(q[0] for q in quantities)+'\n'+f"(F12.0,{len(quantities)}(',',E24.16))\n*ENDDO\n*CFCLOS\nALLSEL,ALL\n")


def execute(name):
    d=BASE/name
    import psutil,shutil
    active=[p.info for p in psutil.process_iter(['pid','name']) if (p.info['name'] or '').lower().startswith('ansys')]
    if active:raise ValueError('Native process already active')
    write_json(d/'preflight.json',{'available_RAM':psutil.virtual_memory().available,'free_disk':shutil.disk_usage(BASE).free,
       'estimated_RSS_bytes':2*2**30,'estimated_disk_bytes':3*2**30,'native_processes':active,'timeout_s':5400})
    r=run_progressive(d,timeout=5400,no_progress_seconds=1200,solve='readback' not in name,cores=2,disk_reserve=80*2**30)
    target=RUN/'native'/name;target.mkdir(parents=True,exist_ok=True);compact(d,target)
    print(name,r['status'],r['process']['returncode'],flush=True)


def baseline():
    mesh,_,_,_=mesh_and_plan();source=BASE/'local_source_001/source.npz';z=np.load(source)
    manifest=read(BASE/'parent_local_readback_001/simulation_manifest.json')
    assert read(BASE/'parent_local_readback_001/execution_receipt.json')['process']['returncode']==0
    d=BASE/'local_baseline_001';d.mkdir(exist_ok=False)
    topo=np.loadtxt(OLD/'track_B_pair_setup_002/contact_topology.csv',delimiter=',',skiprows=1).astype(int)
    target=np.loadtxt(OLD/'track_B_pair_setup_002/target_topology.csv',delimiter=',',skiprows=1).astype(int)
    assert np.isin(np.r_[topo[:,1:4].ravel(),target[:,1:4].ravel()],z['nodes']).all()
    with (d/'input.inp').open('w',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n/FILNAME,compression\n/NOPR\n/PREP7\nET,1,PLANE183\nKEYOPT,1,1,1\nKEYOPT,1,3,3\nR,1,1\nMP,EX,1,1000\nMP,PRXY,1,.3\nMP,MU,1,0\nTYPE,1\nREAL,1\nMAT,1\n')
        for n in z['nodes']:f.write(f'N,{n},{mesh.nodes[n-1,0]:.17g},{mesh.nodes[n-1,1]:.17g}\n')
        for eid,t in zip(z['eids'],z['triangles']):f.write(f'EN,{eid},'+','.join(str(n+1) for n in t)+'\n')
        component(f,'LOCAL_NODES',z['nodes']);component(f,'LOCAL_CORNERS',z['corners']);component(f,'LOCAL_SOLIDS',z['eids']);component(f,'CUT_NODES',z['cutnodes'])
        f.write('ALLSEL,ALL\nGCGEN,NEW,42,0,PART,SELECT\nGCGEN,SELECT\nCM,ALL_GC,ELEM\nALLSEL,ALL\n')
        for face in np.vstack([z['cut']+1,topo[:,1:4],target[:,1:4]]):
            f.write('NSEL,NONE\n'+''.join(f'NSEL,A,NODE,,{n}\n' for n in face)+'ESLN,S,1,ALL\nCMSEL,R,ALL_GC\nEDELE,ALL\nALLSEL,ALL\n')
        f.write('CMSEL,S,ALL_GC\nCM,INTERNAL_GC,ELEM\nEMODIF,ALL,TYPE,4\nEMODIF,ALL,SECNUM,4\nALLSEL,ALL\nKEYOPT,4,2,1\nKEYOPT,4,4,5\nKEYOPT,4,10,0\nR,100,,,100,-5e-5\nGCDEF,SYMM,ALL,SELF,1,100\nET,5,TARGE169\nKEYOPT,5,2,0\nET,6,CONTA172\nKEYOPT,6,2,1\nKEYOPT,6,4,5\nKEYOPT,6,10,0\nR,6,,,10,-5e-5\n')
        # Local contact IDs are kept distinct from GC-generated IDs.
        for typ,rows,label in [(5,target,'LOCAL_PAIR_TARGET'),(6,topo,'LOCAL_PAIR_CONTACT')]:
            f.write(f'TYPE,{typ}\nREAL,6\nMAT,1\n')
            for row in rows:f.write('E,'+','.join(str(n) for n in row[1:4])+'\n')
            f.write(f'ESEL,S,TYPE,,{typ}\nCM,{label},ELEM\nALLSEL,ALL\n')
        f.write('/GOPR\n/OUTPUT,inventory,txt\nETLIST,ALL\nRLIST,ALL\nGCDEF,LIST\n/OUTPUT\nFINISH\nSAVE,initial,db\n/SOLU\nANTYPE,STATIC\nNLGEOM,ON\nEQSLV,SPARSE\nNROPT,FULL\nLNSRCH,ON\nCNVTOL,F,,.005,2,1e-8\nNEQIT,40\nAUTOTS,ON\nOUTRES,ALL,ALL\nOUTRES,NLOAD,ALL\nNLDIAG,CONT,ITER\nRESCONTROL,DEFINE,ALL,1,-1,,3\n')
        for i,s in enumerate(manifest['states'],1):
            u=np.loadtxt(BASE/f'parent_local_readback_001/state{i:03d}_u.csv',delimiter=',');assert np.array_equal(u[:,0],z['nodes'])
            values={int(r[0]):r[1:] for r in u}
            f.write(f'TIME,{s["time"]:.17g}\nNSUBST,1,128,1\n')
            for n in z['cutnodes']:f.write(f'D,{n},UX,{values[n][0]:.17g}\nD,{n},UY,{values[n][1]:.17g}\n')
            f.write('SOLVE\n')
        f.write('FINISH\nSAVE,checkpoint,db\n/EXIT,NOSAVE\n')
    write_json(d/'simulation_manifest.json',{**manifest,'scope':'LOCAL_BASELINE_NOT_CROP_RESULT','input_sha256':file_hash(d/'input.inp')})
    compact(d,RUN/'local/local_baseline_001');print('Prepared exact-element baseline',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['extract','execute','baseline']);p.add_argument('--name');a=p.parse_args()
    if a.action=='execute':execute(a.name)
    else:globals()[a.action]()
