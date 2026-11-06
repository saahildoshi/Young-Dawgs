"""Exact Track B original-element local replay; measured histories, no remeshing."""
import argparse
import numpy as np
from scripts.v069_study import RUN,BASE,OLD,PREVIOUS,DOC,read,write_json,file_hash
from scripts.v068_track_b import mesh_and_plan
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.microstructure_import import component
from scripts.v066_restart import compact

ROI=[2.35,2.56,2.05,2.45]


def extract():
    mesh,_,_,spec=mesh_and_plan();xy=mesh.nodes
    centers=xy[mesh.triangles[:,:3]].mean(axis=1)
    keep=(centers[:,0]>=ROI[0])&(centers[:,0]<=ROI[1])&(centers[:,1]>=ROI[2])&(centers[:,1]<=ROI[3])
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
        component(f,'LOCAL_NODES',nodes);component(f,'LOCAL_CORNERS',corners);component(f,'LOCAL_SOLIDS',eids,entity='ELEM');component(f,'CUT_NODES',cutnodes)
        f.write('FINISH\n/POST1\n')
        for i,s in enumerate(states,1):
            prefix=f'state{i:03d}'
            f.write("FILE,'"+(OLD/s['source']/'compression').as_posix()+f"',rst\nSET,{s['load_step']},{s['substep']}\n")
            export_fields(f,prefix)
            f.write('CMSEL,S,CUT_NODES\nCMSEL,S,LOCAL_SOLIDS,ELEM\nFSUM\n*GET,FX,FSUM,0,ITEM,FX\n*GET,FY,FSUM,0,ITEM,FY\n'+f'*CFOPEN,{prefix}_force,csv\n*VWRITE,FX,FY\n(2(E24.16,\',\'))\n*CFCLOS\nALLSEL,ALL\n')
        f.write('FINISH\n/EXIT,NOSAVE\n')
    manifest={'schema':'v069-exact-original-mesh-local-history','states':states,'nodes':len(nodes),'elements':len(eids),
       'cut_nodes':len(cutnodes),'source_archive_sha256':file_hash(local/'source.npz'),'mesh_semantic_sha256':spec['semantic_sha256'],
       'ROI_mm':ROI,'native_sources':{name:file_hash(OLD/name/'compression.rst') for name in sorted({s['source'] for s in states})},'input_sha256':file_hash(d/'input.inp')}
    write_json(d/'simulation_manifest.json',manifest);write_json(RUN/'local/SOURCE.json',manifest)
    print('Prepared',len(nodes),len(eids),len(states),'native local-history readback')


def export_fields(f,prefix):
    for comp,label,quantities in [('LOCAL_NODES','u',[('UX','U','X'),('UY','U','Y')]),
      ('LOCAL_CORNERS','fields',[('SX','S','X'),('SY','S','Y'),('SXY','S','XY'),('SEQ','S','EQV'),('EX','EPEL','X'),('EY','EPEL','Y'),('EXY','EPEL','XY')])]:
        f.write(f'ALLSEL,ALL\n*GET,NMAX,NODE,0,NUM,MAX\nCMSEL,S,{comp}\n')
        arrays=['IDS','MASKV']+[q[0]+'V' for q in quantities]
        for a in arrays:f.write(f'*DIM,{a},ARRAY,NMAX\n')
        f.write('*VFILL,IDS(1),RAMP,1,1\n*VGET,MASKV(1),NODE,1,NSEL\n')
        for var,item,sub in quantities:f.write(f'*VLEN,NMAX\n*VMASK,MASKV(1)\n*VGET,{var}V(1),NODE,1,{item},{sub}\n')
        f.write(f'*CFOPEN,{prefix}_{label},csv\n*VLEN,NMAX\n*VMASK,MASKV(1)\n*VWRITE,IDS(1),'+','.join(q[0]+'V(1)' for q in quantities)+'\n'+f"(F12.0,{len(quantities)}(',',E24.16))\n*CFCLOS\nALLSEL,ALL\n")
        for a in arrays:f.write(f'*DEL,{a}\n')


def vector_readback():
    manifest=read(BASE/'parent_local_readback_001/simulation_manifest.json');z=np.load(BASE/'local_source_001/source.npz')
    d=BASE/'parent_local_readback_002';d.mkdir(exist_ok=False)
    with (d/'input.inp').open('w',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n'+database_resume(OLD/'track_B_pair_unified_setup_001/contact_model_pair_unified.db')+'/FILNAME,readonly\n/PREP7\n')
        for comp,key in [('LOCAL_NODES','nodes'),('LOCAL_CORNERS','corners'),('LOCAL_SOLIDS','eids'),('CUT_NODES','cutnodes')]:component(f,comp,z[key],entity='ELEM' if key=='eids' else 'NODE')
        f.write('FINISH\n/POST1\n')
        for i,s in enumerate(manifest['states'],1):
            f.write("FILE,'"+(OLD/s['source']/'compression').as_posix()+f"',rst\nSET,{s['load_step']},{s['substep']}\n")
            export_fields(f,f'state{i:03d}')
        f.write('FINISH\n/EXIT,NOSAVE\n')
    write_json(d/'simulation_manifest.json',{**manifest,'input_sha256':file_hash(d/'input.inp'),'extraction':'masked-native-vector-v2','boundary_force_comparison':'pending separate native patch extraction'})


def execute(name):
    d=BASE/name
    import psutil,shutil
    active=[p.info for p in psutil.process_iter(['pid','name']) if (p.info['name'] or '').lower().startswith('ansys')]
    if active:raise ValueError('Native process already active')
    write_json(d/'preflight.json',{'available_RAM':psutil.virtual_memory().available,'free_disk':shutil.disk_usage(BASE).free,
       'estimated_RSS_bytes':2*2**30,'estimated_disk_bytes':3*2**30,'native_processes':active,'timeout_s':5400})
    r=run_progressive(d,timeout=5400,no_progress_seconds=1200,solve='readback' not in name,cores=2,disk_reserve=80*2**30)
    target=RUN/'native'/name
    if target.exists():target=target/'evidence'
    compact(d,target)
    print(name,r['status'],r['process']['returncode'],flush=True)


def baseline():
    mesh,_,_,_=mesh_and_plan();source=BASE/'local_source_001/source.npz';z=np.load(source)
    manifest=read(BASE/'parent_local_readback_002/simulation_manifest.json')
    assert read(BASE/'parent_local_readback_002/execution_receipt.json')['process']['returncode']==0
    d=BASE/'local_baseline_001';d.mkdir(exist_ok=False)
    topo=np.loadtxt(OLD/'track_B_pair_setup_002/contact_topology.csv',delimiter=',',skiprows=1).astype(int)
    target=np.loadtxt(OLD/'track_B_pair_setup_002/target_topology.csv',delimiter=',',skiprows=1).astype(int)
    assert np.isin(np.r_[topo[:,1:4].ravel(),target[:,1:4].ravel()],z['nodes']).all()
    with (d/'input.inp').open('w',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n/FILNAME,compression\n/NOPR\n/PREP7\nET,1,PLANE183\nKEYOPT,1,1,1\nKEYOPT,1,3,3\nR,1,1\nMP,EX,1,1000\nMP,PRXY,1,.3\nMP,MU,1,0\nTYPE,1\nREAL,1\nMAT,1\n')
        for n in z['nodes']:f.write(f'N,{n},{mesh.nodes[n-1,0]:.17g},{mesh.nodes[n-1,1]:.17g}\n')
        for eid,t in zip(z['eids'],z['triangles']):f.write(f'EN,{eid},'+','.join(str(n+1) for n in t)+'\n')
        component(f,'LOCAL_NODES',z['nodes']);component(f,'LOCAL_CORNERS',z['corners']);component(f,'LOCAL_SOLIDS',z['eids'],entity='ELEM');component(f,'CUT_NODES',z['cutnodes'])
        f.write('ET,2,TARGE169\nET,3,CONTA172\nALLSEL,ALL\nGCGEN,NEW,42,0,PART,SELECT\nGCGEN,SELECT\nCM,ALL_GC,ELEM\nALLSEL,ALL\n')
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
            u=np.loadtxt(BASE/f'parent_local_readback_002/state{i:03d}_u.csv',delimiter=',');assert np.array_equal(u[:,0],z['nodes'])
            values={int(r[0]):r[1:] for r in u}
            f.write(f'TIME,{s["time"]:.17g}\nNSUBST,1,128,1\n')
            for n in z['cutnodes']:f.write(f'D,{n},UX,{values[n][0]:.17g}\nD,{n},UY,{values[n][1]:.17g}\n')
            f.write('SOLVE\n')
        f.write('FINISH\nSAVE,checkpoint,db\n/EXIT,NOSAVE\n')
    write_json(d/'simulation_manifest.json',{**manifest,'scope':'LOCAL_BASELINE_NOT_CROP_RESULT','input_sha256':file_hash(d/'input.inp')})
    compact(d,RUN/'local/local_baseline_001');print('Prepared exact-element baseline',flush=True)


def post():
    source=BASE/'local_baseline_001';r=read(source/'execution_receipt.json')
    states=read(source/'simulation_manifest.json')['states'];available={}
    for s in read(source/'nonlinear_telemetry.json')['converged_substeps']:
        if s.get('substep')!=999999:available[s['load_step']]=s
    d=BASE/'local_baseline_readback_001';d.mkdir(exist_ok=False)
    with (d/'input.inp').open('w',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n'+database_resume(source/'initial.db')+'/FILNAME,readonly\n/PREP7\n')
        z=np.load(BASE/'local_source_001/source.npz');component(f,'LOCAL_SOLIDS',z['eids'],entity='ELEM')
        for name,filename in [('PATCH_SOURCE','contact'),('PATCH_TARGET','target')]:
            topo=np.loadtxt(OLD/f'track_B_pair_setup_002/{filename}_topology.csv',delimiter=',',skiprows=1).astype(int)
            component(f,name,np.unique(topo[:,1:4]))
        f.write('/OUTPUT,inventory,txt\nETLIST,ALL\nRLIST,ALL\nGCDEF,LIST\n/OUTPUT\nFINISH\n/POST1\n'+"FILE,'"+(source/'compression').as_posix()+"',rst\n")
        selected=[]
        for i,s in enumerate(states,1):
            if i not in available:continue
            a=available[i]
            if abs(a.get('pseudo_time',-1)-s['time'])>1e-9:continue
            selected.append({'index':i,**a})
            f.write(f'SET,{i},{a["substep"]}\n');export_fields(f,f'state{i:03d}')
            f.write('ESEL,S,ENAME,,172\nETABLE,ERAS\nETABLE,CST,NMISC,19\nCMSEL,S,LOCAL_PAIR_CONTACT\n*GET,NC,ELEM,0,COUNT\n'+f'*CFOPEN,state{i:03d}_contact,csv\nIE=0\n*DO,K,1,NC\nIE=ELNEXT(IE)\n'+
                '*GET,NI,ELEM,IE,NODE,1\n*GET,NJ,ELEM,IE,NODE,2\n*GET,NM,ELEM,IE,NODE,3\n*GET,ST,ELEM,IE,ETAB,CST\nPI=0\nPJ=0\nGI=0\nGJ=0\n*IF,ST,GT,0,THEN\n*GET,PI,ELEM,IE,SMISC,1\n*GET,PJ,ELEM,IE,SMISC,2\n*GET,GI,ELEM,IE,NMISC,5\n*GET,GJ,ELEM,IE,NMISC,6\n*ENDIF\n*VWRITE,IE,NI,NJ,NM,ST,PI,PJ,GI,GJ\n'+"(5(F12.0,','),4(E24.16,','))\n*ENDDO\n*CFCLOS\nALLSEL,ALL\n")
            f.write(f'*CFOPEN,state{i:03d}_patch_forces,csv\n')
            for side,comp in [(1,'PATCH_TARGET'),(2,'PATCH_SOURCE')]:
                f.write(f'CMSEL,S,{comp}\nCMSEL,S,LOCAL_SOLIDS,ELEM\nFSUM\n*GET,FX,FSUM,0,ITEM,FX\n*GET,FY,FSUM,0,ITEM,FY\n*VWRITE,{side},FX,FY\n'+"(F4.0,2(',',E24.16))\nALLSEL,ALL\n")
            f.write('*CFCLOS\n')
        f.write('FINISH\n/EXIT,NOSAVE\n')
    write_json(d/'simulation_manifest.json',{'states':selected,'source_RST_sha256':file_hash(source/'compression.rst'),
       'input_sha256':file_hash(d/'input.inp'),'source_receipt_sha256':file_hash(source/'execution_receipt.json')})
    print('Prepared baseline independent readback',len(selected),flush=True)


def qualify():
    mesh,_,_,_=mesh_and_plan();z=np.load(BASE/'local_source_001/source.npz')
    d=BASE/'local_baseline_readback_001';m=read(d/'simulation_manifest.json');r=read(d/'execution_receipt.json')
    assert r['process']['returncode']==0 and file_hash(BASE/'local_baseline_001/compression.rst')==m['source_RST_sha256']
    rows=[]
    cutxy=mesh.nodes[z['cutnodes']-1]
    for state in m['states']:
        i=state['index'];local=np.loadtxt(d/f'state{i:03d}_u.csv',delimiter=',');parent=np.loadtxt(BASE/f'parent_local_readback_002/state{i:03d}_u.csv',delimiter=',')
        sf=np.loadtxt(d/f'state{i:03d}_fields.csv',delimiter=',');pf=np.loadtxt(BASE/f'parent_local_readback_002/state{i:03d}_fields.csv',delimiter=',')
        assert np.array_equal(local[:,0],parent[:,0]) and np.array_equal(sf[:,0],pf[:,0])
        def core(ids):
            pts=mesh.nodes[ids.astype(int)-1]
            return np.min(np.linalg.norm(pts[:,None,:]-cutxy[None,:,:],axis=2),axis=1)>.025
        cm=core(local[:,0]);sm=core(sf[:,0])
        def error(a,b,floor):return float(np.sqrt(np.mean((a-b)**2))/max(np.sqrt(np.mean(b*b)),floor))
        ur=error(local[cm,1:],parent[cm,1:],1e-12)
        sr=[error(sf[sm,j],pf[sm,j],1e-8 if j<=4 else 1e-11) for j in range(1,8)]
        rows.append({'index':i,'time':state['pseudo_time'],'U_RMS_relative':ur,'SXX_SYY_SXY_SEQV_EXX_EYY_EXY_RMS_relative':sr,
                     'field_match':ur<=.02 and max(sr)<=.10})
    q={'schema':'v069-local-parent-field-comparison','states':rows,'all_fields_pass':bool(rows) and all(s['field_match'] for s in rows),
       'complete_measured_history':len(rows)==72,'full_local_gate':'HOLD_PENDING_REACTIONS_CONTACT_GAPS_NORMALS_MAPPING_AND_PATH',
       'crop_continuation_authorized':False,'source_post_receipt_sha256':file_hash(d/'execution_receipt.json')}
    write_json(RUN/'local/BASELINE_FIELD_COMPARISON.json',q)
    print('Field match',q['all_fields_pass'],'states',len(rows),'first failures',[(s['index'],s['SXX_SYY_SXY_SEQV_EXX_EYY_EXY_RMS_relative']) for s in rows if not s['field_match']][:3],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['extract','execute','baseline','vector_readback','post','qualify']);p.add_argument('--name');a=p.parse_args()
    if a.action=='execute':execute(a.name)
    else:globals()[a.action]()
