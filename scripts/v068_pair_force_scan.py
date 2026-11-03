"""Read-only two-sided structural force scan for all retained onset substeps."""
import argparse
import numpy as np

from metamaterial_eval.simulation.microstructure_import import component
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.microstructure_results import numeric
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


def prepare(source_name):
    source=BASE/source_name;post=BASE/(source_name+'_post1_all_v2')
    pm=read(post/'simulation_manifest.json');pr=read(post/'execution_receipt.json')
    setup=read(RUN/'track_B_contact_fixture/PAIR_SETUP_QUALIFICATION.json')
    if (pr['process']['returncode']!=0 or pm['selection']!='all' or
        file_hash(source/'compression.rst')!=pm['source_RST_sha256'] or
        file_hash(BASE/'track_B_pair_setup_002/contact_model_pair.db')!=setup['pair_database_sha256']):
        raise ValueError('Changed or incomplete native all-state source')
    paths=[BASE/'track_B_pair_setup_002/target_topology.csv',BASE/'track_B_pair_setup_002/contact_topology.csv']
    nodes=[np.unique(np.loadtxt(p,delimiter=',',skiprows=1,ndmin=2)[:,1:4].astype(int)) for p in paths]
    if np.intersect1d(*nodes).size:raise ValueError('Source and target structural patches overlap')
    d=BASE/(source_name+'_pair_force_scan_001');d.mkdir(parents=True,exist_ok=False)
    with (d/'input.inp').open('w',encoding='utf-8',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n'+database_resume(BASE/'track_B_pair_setup_002/contact_model_pair.db')+
                '/FILNAME,readonly\n/PREP7\n')
        component(f,'PATCH_TARGET',nodes[0]);component(f,'PATCH_SOURCE',nodes[1])
        f.write('FINISH\n/POST1\n'+"FILE,'"+(source/'compression').resolve().as_posix()+"',rst\n"+
                '*CFOPEN,pair_patch_forces_all,csv\n*VWRITE\n'+
                "('load_step,substep,time,side,solid_fx_N,solid_fy_N,platen_fx_N,platen_fy_N,gc_fx_N,gc_fy_N')\n")
        for state in pm['states']:
            ls,ss=state['load_step'],state['substep']
            f.write(f'ALLSEL,ALL\nSET,{ls},{ss}\n*GET,NTIME,ACTIVE,0,SET,TIME\n')
            for side,label in [(1,'TARGET'),(2,'SOURCE')]:
                f.write('ALLSEL,ALL\nCMSEL,S,PATCH_'+label+'\nESEL,S,TYPE,,1\nFSUM\n'
                        '*GET,SFX,FSUM,0,ITEM,FX\n*GET,SFY,FSUM,0,ITEM,FY\n'
                        'ESEL,S,TYPE,,3\nFSUM,,CONT\n*GET,PFX,FSUM,0,ITEM,FX\n*GET,PFY,FSUM,0,ITEM,FY\n'
                        'CMSEL,S,INTERNAL_GC\nFSUM,,CONT\n*GET,GFX,FSUM,0,ITEM,FX\n*GET,GFY,FSUM,0,ITEM,FY\n'
                        f'*VWRITE,{ls},{ss},NTIME,{side},SFX,SFY,PFX,PFY,GFX,GFY\n'+
                        "(2(F6.0,','),E24.16,',',F4.0,6(',',E24.16))\n")
        f.write('*CFCLOS\nALLSEL,ALL\nFINISH\n/EXIT,NOSAVE\n')
    m={'schema':'young-dawgs-v068-all-onset-pair-structural-forces','source':source_name,
       'source_RST_sha256':file_hash(source/'compression.rst'),
       'source_post_receipt_sha256':file_hash(post/'execution_receipt.json'),
       'pair_database_sha256':setup['pair_database_sha256'],
       'states':pm['states'],'target_nodes':len(nodes[0]),'source_nodes':len(nodes[1]),
       'input_sha256':file_hash(d/'input.inp'),'read_only':True}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_contact_fixture')
    print('Prepared all-state structural-force scan',len(pm['states']),flush=True)


def execute(source_name):
    d=BASE/(source_name+'_pair_force_scan_001')
    r=run_progressive(d,timeout=900,solve=False,cores=2,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Pair force scan',r['status'],r['process']['returncode'],flush=True)


def qualify(source_name):
    d=BASE/(source_name+'_pair_force_scan_001');m=read(d/'simulation_manifest.json')
    r=read(d/'execution_receipt.json');source=BASE/source_name
    if (r['process']['returncode']!=0 or r['solver_version']!='2024 R1' or
        file_hash(source/'compression.rst')!=m['source_RST_sha256'] or
        file_hash(d/'input.inp')!=m['input_sha256'] or
        file_hash(d/'pair_patch_forces_all.csv')!=r['process']['artifacts']['pair_patch_forces_all.csv']['sha256']):
        raise ValueError('Native scan process or evidence changed')
    a=numeric(d/'pair_patch_forces_all.csv',
        ['load_step','substep','time','side','solid_fx_N','solid_fy_N','platen_fx_N','platen_fy_N','gc_fx_N','gc_fy_N'])
    if len(a)!=2*len(m['states']):raise ValueError('Incomplete selected native state forces')
    states=[]
    for state in m['states']:
        ls,ss=state['load_step'],state['substep']
        rows=a[(a[:,0]==ls)&(a[:,1]==ss)]
        if len(rows)!=2 or not np.array_equal(rows[:,3],[1,2]):raise ValueError('Missing target/source force row')
        solid=rows[:,4:6];scale=float(np.linalg.norm(solid,axis=1).max())
        opposition=float(np.linalg.norm(solid.sum(axis=0))/max(scale,1e-12))
        platen=float(np.linalg.norm(rows[:,6:8],axis=1).max()/max(scale,1e-12))
        gc=float(np.linalg.norm(rows[:,8:10],axis=1).max()/max(scale,1e-12))
        states.append({'load_step':ls,'substep':ss,'native_time':float(rows[0,2]),
                       'solid_target_source_N':solid.tolist(),'scale_N':scale,
                       'opposition_relative':opposition,'platen_fraction':platen,'other_GC_fraction':gc,
                       'passed_when_engaged':bool(scale>1e-8 and opposition<=.01 and platen<=.01 and gc<=.01)})
    q={'schema':'young-dawgs-v068-all-onset-pair-force-readback','source_name':source_name,
       'source_RST_sha256':m['source_RST_sha256'],'native_receipt_sha256':file_hash(d/'execution_receipt.json'),
       'native_force_sha256':file_hash(d/'pair_patch_forces_all.csv'),
       'states':states,'scope':'Proof only for pressure-bearing paired faces; each geometric state separately qualified.'}
    write_json(RUN/'track_B_contact_fixture'/(source_name+'_pair_force_scan.json'),q)
    print('Qualified native pair force scan',len(states),'states',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','qualify']);p.add_argument('source_name')
    a=p.parse_args();{'prepare':prepare,'execute':execute,'qualify':qualify}[a.action](a.source_name)
