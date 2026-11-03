"""Read-only two-sided structural force check for the localized specimen pair."""
import argparse
import numpy as np

from metamaterial_eval.simulation.microstructure_import import component
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.microstructure_results import numeric
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


def prepare(source_name):
    source=BASE/source_name;post=BASE/(source_name+'_post1_last_v2')
    pm=read(post/'simulation_manifest.json');pr=read(post/'execution_receipt.json')
    setup=read(RUN/'track_B_contact_fixture/PAIR_SETUP_QUALIFICATION.json')
    if (len(pm['states'])!=1 or pr['process']['returncode']!=0 or
        file_hash(source/'compression.rst')!=pm['source_RST_sha256'] or
        file_hash(BASE/'track_B_pair_setup_002/contact_model_pair.db')!=setup['pair_database_sha256']):
        raise ValueError('Changed source or pair model for force proof')
    state=pm['states'][0];fields=numeric(post/'stage001_pair_contact.csv',
        ['element','status','pressure_i_MPa','pressure_j_MPa','pen_i_mm','pen_j_mm','fy_N','target_i','target_j'])
    if not len(fields) or not np.any((fields[:,1]>=2)&(fields[:,2:4].max(axis=1)>0)):
        raise ValueError('No engaged native pair for structural force proof')
    d=BASE/(source_name+'_pair_force_001');d.mkdir(parents=True,exist_ok=False)
    paths=[BASE/'track_B_pair_setup_002/target_topology.csv',BASE/'track_B_pair_setup_002/contact_topology.csv']
    nodes=[np.unique(np.loadtxt(p,delimiter=',',skiprows=1,ndmin=2)[:,1:4].astype(int)) for p in paths]
    if np.intersect1d(*nodes).size:raise ValueError('Pair source and target structural patches share nodes')
    key=(state['load_step'],state['substep'])
    with (d/'input.inp').open('w',encoding='utf-8',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n'+database_resume(BASE/'track_B_pair_setup_002/contact_model_pair.db')+
                '/FILNAME,readonly\n/PREP7\n')
        component(f,'PATCH_TARGET',nodes[0]);component(f,'PATCH_SOURCE',nodes[1])
        f.write('FINISH\n/POST1\n'+"FILE,'"+(source/'compression').resolve().as_posix()+"',rst\n"+
                f'SET,{key[0]},{key[1]}\n*CFOPEN,pair_patch_forces,csv\n*VWRITE\n'+
                "('side,solid_fx_N,solid_fy_N,platen_fx_N,platen_fy_N,gc_fx_N,gc_fy_N,pair_fx_N,pair_fy_N')\n")
        for i,label in [(1,'TARGET'),(2,'SOURCE')]:
            f.write('ALLSEL,ALL\nCMSEL,S,PATCH_'+label+'\nESEL,S,TYPE,,1\nFSUM\n'
                    '*GET,SFX,FSUM,0,ITEM,FX\n*GET,SFY,FSUM,0,ITEM,FY\n'
                    'ESEL,S,TYPE,,3\nFSUM,,CONT\n*GET,PFX,FSUM,0,ITEM,FX\n*GET,PFY,FSUM,0,ITEM,FY\n'
                    'CMSEL,S,INTERNAL_GC\nFSUM,,CONT\n*GET,GFX,FSUM,0,ITEM,FX\n*GET,GFY,FSUM,0,ITEM,FY\n'
                    'CMSEL,S,LOCAL_PAIR_CONTACT\nFSUM,,CONT\n*GET,CFX,FSUM,0,ITEM,FX\n*GET,CFY,FSUM,0,ITEM,FY\n'
                    f'*VWRITE,{i},SFX,SFY,PFX,PFY,GFX,GFY,CFX,CFY\n'+
                    "(F4.0,8(',',E24.16))\n")
        f.write('*CFCLOS\nALLSEL,ALL\nFINISH\n/EXIT,NOSAVE\n')
    m={'schema':'young-dawgs-v068-selected-pair-structural-force',
       'source':source_name,'selected_state':state,
       'source_RST_sha256':file_hash(source/'compression.rst'),
       'source_post_receipt_sha256':file_hash(post/'execution_receipt.json'),
       'pair_fields_sha256':file_hash(post/'stage001_pair_contact.csv'),
       'pair_database_sha256':setup['pair_database_sha256'],
       'target_nodes':len(nodes[0]),'source_nodes':len(nodes[1]),
       'input_sha256':file_hash(d/'input.inp'),'read_only':True}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_contact_fixture')
    print('Prepared pair structural force',source_name,flush=True)


def execute(source_name):
    d=BASE/(source_name+'_pair_force_001')
    r=run_progressive(d,timeout=600,solve=False,cores=2,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Pair force POST1',r['status'],r['process']['returncode'],flush=True)


def qualify(source_name):
    d=BASE/(source_name+'_pair_force_001');m=read(d/'simulation_manifest.json');r=read(d/'execution_receipt.json')
    source=BASE/source_name
    if (r['process']['returncode']!=0 or r['solver_version']!='2024 R1' or
        file_hash(source/'compression.rst')!=m['source_RST_sha256'] or
        file_hash(d/'input.inp')!=m['input_sha256'] or
        file_hash(d/'pair_patch_forces.csv')!=r['process']['artifacts']['pair_patch_forces.csv']['sha256']):
        raise ValueError('Changed or failed native pair force readback')
    a=numeric(d/'pair_patch_forces.csv',
        ['side','solid_fx_N','solid_fy_N','platen_fx_N','platen_fy_N','gc_fx_N','gc_fy_N','pair_fx_N','pair_fy_N'])
    if a.shape!=(2,9) or not np.array_equal(a[:,0],[1,2]):raise ValueError('Incomplete pair patch forces')
    solid=a[:,1:3];scale=float(np.linalg.norm(solid,axis=1).max())
    opposition=float(np.linalg.norm(solid.sum(axis=0))/max(scale,1e-12))
    platen=float(np.linalg.norm(a[:,3:5],axis=1).max()/max(scale,1e-12))
    other_gc=float(np.linalg.norm(a[:,5:7],axis=1).max()/max(scale,1e-12))
    passed=bool(scale>1e-8 and opposition<=.01 and platen<=.01 and other_gc<=.01)
    q={'schema':'young-dawgs-v068-selected-pair-two-sided-structural-force',
       'source_name':source_name,'selected_state':m['selected_state'],
       'passed':passed,'status':'PASS_PAIR_STRUCTURAL_FORCE' if passed else 'HOLD_PAIR_STRUCTURAL_FORCE',
       'solid_forces_target_source_N':solid.tolist(),
       'solid_opposition_relative':opposition,'platen_fraction':platen,'other_GC_fraction':other_gc,
       'pair_skin_forces_target_source_N':a[:,7:9].tolist(),
       'source_RST_sha256':m['source_RST_sha256'],
       'native_force_sha256':file_hash(d/'pair_patch_forces.csv'),
       'native_read_only_receipt_sha256':file_hash(d/'execution_receipt.json'),
       'force_interpretation':'All adjacent structural element nodal forces on both original pair arcs; independently checks that platen/other GC carry no material force at these nodes.'}
    write_json(RUN/'track_B_contact_fixture'/(source_name+'_pair_force.json'),q)
    print(q['status'],opposition,platen,other_gc,flush=True)
    return q


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','qualify']);p.add_argument('source_name')
    a=p.parse_args();{'prepare':prepare,'execute':execute,'qualify':qualify}[a.action](a.source_name)
