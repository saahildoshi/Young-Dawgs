"""Read-only native parent-field readback for the expanded original-mesh fixture."""
import argparse
import re
import numpy as np

from metamaterial_eval.simulation.microstructure_pilot import database_resume,vector_fields
from metamaterial_eval.simulation.general_contact_output import general_contact_vectors
from metamaterial_eval.simulation.progressive_compression import run_progressive
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


def prepare(label):
    if label not in ['track_A_expanded_nodal2_001','track_A_expanded_unified5_001']:
        raise ValueError('Unregistered expanded original-mesh case')
    source=BASE/label;manifest=read(source/'simulation_manifest.json')
    receipt=read(source/'execution_receipt.json')
    if (receipt['solver_version']!='2024 R1' or
        receipt['input_sha256']!=manifest['input_sha256'] or
        file_hash(source/'input.inp')!=manifest['input_sha256']):
        raise ValueError('Changed or nonnative local source')
    telemetry=read(source/'nonlinear_telemetry.json')
    last={}
    for row in telemetry['converged_substeps']:
        if 'pseudo_time' in row and row['substep']!=999999:last[row['load_step']]=row
    if not last:raise ValueError('No native states')
    with np.load(BASE/'track_A_expanded_fixture_001/mesh.npz',allow_pickle=False) as z:
        cut=z['cut_nodes_zero_based']+1
    d=BASE/(label+'_post1_002');d.mkdir(parents=True,exist_ok=False)
    topo=np.loadtxt(source/'gc_topology.csv',delimiter=',',skiprows=1,ndmin=2)
    model={**manifest['model'],'user_model_elements':max(manifest['model']['user_model_elements'],int(topo[:,0].max()))}
    lines=['/BATCH','/CLEAR,START',database_resume(source/'initial.db').strip(),
           '/FILNAME,readonly','/POST1',"FILE,'"+(source/'compression').as_posix()+"',rst",
           '/OUTPUT,result_sets,txt','SET,LIST','/OUTPUT']
    states=[]
    for idx,(ls,row) in enumerate(sorted(last.items()),1):
        prefix=f'state{idx:03d}'
        lines += [f"SET,{ls},{row['substep']}",'*GET,NTIME,ACTIVE,0,SET,TIME',
                  f'*CFOPEN,{prefix}_time,csv','*VWRITE',"('pseudo_time')",
                  '*VWRITE,NTIME','(E24.16)','*CFCLOS']
        lines += vector_fields(model['specimen_nodes'],prefix)
        lines += ['ALLSEL,ALL','ETABLE,ERAS','ETABLE,CNSTAT,NMISC,19']
        lines += general_contact_vectors(model,prefix,chunk_size=10000)
        lines += [f'*CFOPEN,{prefix}_reactions,csv','*VWRITE',"('node,rx_N,ry_N')"]
        for node in list(cut)+[manifest['model']['controls']['top']]:
            lines += [f'*GET,RX,NODE,{node},RF,FX',f'*GET,RY,NODE,{node},RF,FY',
                      f'*VWRITE,{node},RX,RY',"(F12.0,2(',',E24.16))"]
        lines += ['*CFCLOS']
        states.append({'prefix':prefix,'load_step':ls,'substep':row['substep'],'time':row['pseudo_time']})
    lines += ['FINISH','/EXIT,NOSAVE']
    deck='\n'.join(lines)+'\n'
    if re.search(r'^\s*(?:SOLVE|SAVE\s*,)',deck,re.M|re.I):raise ValueError('POST1 must be read only')
    (d/'input.inp').write_text(deck,encoding='utf-8',newline='\n')
    provenance={'schema':'young-dawgs-v068-expanded-local-read-only-post1',
                'source_RST_sha256':file_hash(source/'compression.rst'),
                'source_database_sha256':file_hash(source/'initial.db'),
                'source_receipt_sha256':file_hash(source/'execution_receipt.json'),
                'states':states,'input_sha256':file_hash(d/'input.inp'),'mode':'READ_ONLY_NATIVE_POST1'}
    write_json(d/'simulation_manifest.json',provenance)
    copy_evidence(d,'track_A_local_fixture')
    print('Prepared Track A POST1',label,len(states),flush=True)


def execute(label):
    d=BASE/(label+'_post1_002')
    r=run_progressive(d,timeout=1800,solve=False,cores=2,disk_reserve=80*1024**3)
    copy_evidence(d,'track_A_unified_detection')
    print('Track A POST1',label,r['status'],r['process']['returncode'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute']);p.add_argument('label')
    a=p.parse_args()
    {'prepare':prepare,'execute':execute}[a.action](a.label)
