"""Measure both sides of the isolated onset interface from native solid forces."""
import argparse
import json
import numpy as np
from metamaterial_eval.simulation.ansys_adapter import component
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import compact
from scripts.v067_fixture import BASE, RUN
from scripts.v067_qualify_fixture import table


def run(label):
    source=BASE/label; post=BASE/(label+'_post001')
    z=np.load(BASE/'source_fixture_001/mesh.npz'); xy=z['nodes']; physical=np.unique(z['boundary'][z['boundary_groups']!='artificial_cut'])
    patches=[]
    for xmin,xmax in [(1.975,1.985),(1.955,1.97)]:
        mask=(xy[physical,0]>=xmin)&(xy[physical,0]<=xmax)&(xy[physical,1]>=10.21)
        patches.append(physical[mask])
    assert all(len(p) for p in patches)
    d=BASE/(label+'_interface001');d.mkdir(parents=True,exist_ok=False)
    provenance=json.loads((post/'provenance.json').read_text(encoding='utf-8'))
    lines=['/BATCH','/CLEAR,START',database_resume(source/'initial.db').strip(),'/FILNAME,readonly','/PREP7']
    for i,ids in enumerate(patches,1):lines+=component(f'PATCH{i}',ids+1)
    lines+=['FINISH','/POST1',"FILE,'"+(source/'compression').as_posix()+"',rst"]
    for state in provenance['states']:
        lines += [f"SET,{state['load_step']},{state['substep']}",f"*CFOPEN,{state['prefix']}_interface,csv",'*VWRITE',"('patch,solid_fx_N,solid_fy_N,platen_fx_N,platen_fy_N,gc_skin_fx_N,gc_skin_fy_N')"]
        for i in [1,2]:
            lines += ['ALLSEL,ALL',f'CMSEL,S,PATCH{i}','ESEL,S,TYPE,,1','FSUM', '*GET,SFX,FSUM,0,ITEM,FX','*GET,SFY,FSUM,0,ITEM,FY',
                      'ESEL,S,TYPE,,3','FSUM,,CONT','*GET,PFX,FSUM,0,ITEM,FX','*GET,PFY,FSUM,0,ITEM,FY',
                      'CMSEL,S,INTERNAL_GC','FSUM,,CONT','*GET,CFX,FSUM,0,ITEM,FX','*GET,CFY,FSUM,0,ITEM,FY',
                      f'*VWRITE,{i},SFX,SFY,PFX,PFY,CFX,CFY',"(F4.0,6(',',E24.16))"]
        lines+=['*CFCLOS','ALLSEL,ALL']
    lines+=['FINISH','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    write_json(d/'provenance.json',{'source_RST_sha256':file_hash(source/'compression.rst'),'source_database_sha256':file_hash(source/'initial.db'),
                                  'patches_original_node_ids':[z['original_nodes_one_based'][p].tolist() for p in patches],
                                  'selection':'Physical boundary nodes only; patchA original x1.975..1.985, patchB1.955..1.970; y>=10.21; no cut nodes',
                                  'states':provenance['states'],'input_sha256':file_hash(d/'input.inp')})
    receipt=run_progressive(d,timeout=180,solve=False,cores=1)
    assert receipt['process']['returncode']==0
    compact(d,RUN/'local_fixture'/d.name)
    results=[]
    for state in provenance['states']:
        data=table(d/(state['prefix']+'_interface.csv'),7)
        solid=data[:,1:3]; platen=data[:,3:5];gc=data[:,5:7]
        scale=float(np.linalg.norm(solid,axis=1).max())
        error=float(np.linalg.norm(solid.sum(axis=0))/max(scale,1e-12))
        platen_fraction=float(np.linalg.norm(platen,axis=1).max()/max(scale,1e-12))
        result={**state,'solid_restoring_forces_A_B_N':solid.tolist(),'platen_patch_forces_A_B_N':platen.tolist(),
                'selected_GC_skin_forces_A_B_N':gc.tolist(),'opposition_relative':error,'platen_fraction':platen_fraction,
                'resolved_interface':scale>1e-6,'opposition_passed':bool(scale>1e-6 and error<=.01 and platen_fraction<=.01)}
        results.append(result)
        (RUN/'local_fixture'/d.name/(state['prefix']+'_interface.csv')).write_bytes((d/(state['prefix']+'_interface.csv')).read_bytes())
    write_json(RUN/'local_fixture'/(label+'_interface_force.json'),{'states':results,'actual_POST1_receipt_sha256':file_hash(d/'execution_receipt.json'),
              'scope':'Native solid force contributions on two free interface patches; require negligible independent platen contribution and1% force opposition. Selected contact-skin FSUM is separately reported, not silently reinterpreted as complete interface balance.'})
    print(label,json.dumps(results[-3:]),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');run(p.parse_args().label)
