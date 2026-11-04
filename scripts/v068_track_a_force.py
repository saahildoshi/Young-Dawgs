"""Native two-sided local force evidence at the original curved-contact hotspot."""
import argparse
import numpy as np

from metamaterial_eval.simulation.ansys_adapter import component
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.progressive_compression import run_progressive
from scripts.v067_qualify_fixture import table
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


def prepare(label):
    if label not in ['track_A_expanded_nodal2_001','track_A_expanded_unified5_001']:
        raise ValueError('Unregistered original-mesh local case')
    source=BASE/label;post=BASE/(label+'_post1_002')
    provenance=read(post/'simulation_manifest.json')
    q=read(RUN/'track_A_local_fixture'/(label+'_qualification.json'))
    if (file_hash(source/'compression.rst')!=provenance['source_RST_sha256'] or
        file_hash(source/'initial.db')!=provenance['source_database_sha256']):
        raise ValueError('Changed original-mesh local source')
    with np.load(BASE/'track_A_expanded_fixture_001/mesh.npz',allow_pickle=False) as z:
        xy=z['nodes'];physical=np.unique(z['boundary'][z['boundary_groups']!='artificial_cut'])
        original=z['original_nodes_one_based']
    patches=[]
    for xmin,xmax in [(1.975,1.985),(1.955,1.97)]:
        mask=(xy[physical,0]>=xmin)&(xy[physical,0]<=xmax)&(xy[physical,1]>=10.21)
        patches.append(physical[mask])
    if not all(len(p) for p in patches) or np.intersect1d(*patches).size:
        raise ValueError('Hotspot two-sided structural patches invalid')
    states=[s for s in provenance['states'] if next(x for x in q['states'] if x['load_step']==s['load_step'])['closed_GC_skins']>0]
    if not states:raise ValueError('No closed original-mesh local contact state')
    d=BASE/(label+'_interface_force_001');d.mkdir(parents=True,exist_ok=False)
    lines=['/BATCH','/CLEAR,START',database_resume(source/'initial.db').strip(),'/FILNAME,readonly','/PREP7']
    for i,ids in enumerate(patches,1):lines+=component(f'PATCH{i}',ids+1)
    lines+=['FINISH','/POST1',"FILE,'"+(source/'compression').as_posix()+"',rst"]
    for state in states:
        prefix=state['prefix']
        lines += [f"SET,{state['load_step']},{state['substep']}",f'*CFOPEN,{prefix}_interface,csv','*VWRITE',
                  "('patch,solid_fx_N,solid_fy_N,platen_fx_N,platen_fy_N,gc_skin_fx_N,gc_skin_fy_N')"]
        for i in [1,2]:
            lines += ['ALLSEL,ALL',f'CMSEL,S,PATCH{i}','ESEL,S,TYPE,,1','FSUM',
                      '*GET,SFX,FSUM,0,ITEM,FX','*GET,SFY,FSUM,0,ITEM,FY',
                      'ESEL,S,TYPE,,3','FSUM,,CONT','*GET,PFX,FSUM,0,ITEM,FX',
                      '*GET,PFY,FSUM,0,ITEM,FY','CMSEL,S,INTERNAL_GC','FSUM,,CONT',
                      '*GET,CFX,FSUM,0,ITEM,FX','*GET,CFY,FSUM,0,ITEM,FY',
                      f'*VWRITE,{i},SFX,SFY,PFX,PFY,CFX,CFY',"(F4.0,6(',',E24.16))"]
        lines+=['*CFCLOS','ALLSEL,ALL']
    lines+=['FINISH','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    m={'schema':'young-dawgs-v068-original-mesh-local-two-sided-interface-force',
       'source':label,'source_RST_sha256':file_hash(source/'compression.rst'),
       'source_database_sha256':file_hash(source/'initial.db'),
       'source_post_receipt_sha256':file_hash(post/'execution_receipt.json'),
       'patches_original_node_ids':[original[x].tolist() for x in patches],
       'selection':'Original physical boundary nodes only; x1.975..1.985 vs x1.955..1.970, y>=10.21mm',
       'states':states,'input_sha256':file_hash(d/'input.inp'),'read_only':True}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_A_local_fixture')
    print('Prepared Track A native two-sided force',label,len(states),flush=True)


def execute(label):
    d=BASE/(label+'_interface_force_001')
    r=run_progressive(d,timeout=600,solve=False,cores=2,disk_reserve=80*1024**3)
    copy_evidence(d,'track_A_unified_detection')
    print('Track A interface readback',label,r['status'],r['process']['returncode'],flush=True)


def qualify(label):
    d=BASE/(label+'_interface_force_001');m=read(d/'simulation_manifest.json');r=read(d/'execution_receipt.json')
    source=BASE/label
    if (r['solver_version']!='2024 R1' or r['process']['returncode']!=0 or
        file_hash(source/'compression.rst')!=m['source_RST_sha256'] or
        file_hash(d/'input.inp')!=m['input_sha256']):
        raise ValueError('Changed original-mesh force proof')
    states=[]
    for state in m['states']:
        path=d/(state['prefix']+'_interface.csv')
        if file_hash(path)!=r['process']['artifacts'][path.name]['sha256']:
            raise ValueError('Changed native interface force field')
        a=table(path,7);solid=a[:,1:3];platen=a[:,3:5];skin=a[:,5:7]
        scale=float(np.linalg.norm(solid,axis=1).max())
        opposition=float(np.linalg.norm(solid.sum(axis=0))/max(scale,1e-12))
        platen_fraction=float(np.linalg.norm(platen,axis=1).max()/max(scale,1e-12))
        states.append({**state,'solid_target_source_N':solid.tolist(),
                       'selected_GC_skin_forces_N':skin.tolist(),
                       'opposition_relative':opposition,'platen_fraction':platen_fraction,
                       'passed':bool(scale>1e-6 and opposition<=.01 and platen_fraction<=.01)})
    q={'schema':'young-dawgs-v068-original-mesh-local-native-force',
       'label':label,'states':states,'native_receipt_sha256':file_hash(d/'execution_receipt.json'),
       'scope':'Local original-mesh patch only; does not fix full-parent early stress mismatch or establish a full-original state.'}
    write_json(RUN/'track_A_local_fixture'/(label+'_interface_force.json'),q)
    print('Track A native force',label,[(x['load_step'],x['passed']) for x in states[-4:]],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','qualify']);p.add_argument('label')
    a=p.parse_args();{'prepare':prepare,'execute':execute,'qualify':qualify}[a.action](a.label)
