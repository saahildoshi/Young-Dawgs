"""Repeated independent full-field readback of the inherited accepted crop maximum."""
import argparse
import numpy as np
from scripts.v069_study import BASE,RUN,OLD,read,write_json,file_hash
from scripts.v069_local import export_fields,execute
from scripts.v068_track_b import mesh_and_plan
from metamaterial_eval.simulation.microstructure_import import component
from metamaterial_eval.simulation.microstructure_pilot import database_resume


def prepare(index):
    mesh,_,_,_=mesh_and_plan();d=BASE/f'final_readback_{index:03d}';d.mkdir(exist_ok=False)
    q=read(RUN.parent.parent/'pipeline_v0.6.8/run_001/track_B_progressive_compression/track_B_pair5_to_01500_001_qualification.json')
    assert q['states'][6]['accepted'] and q['states'][6]['requested_time']==.012575
    with (d/'input.inp').open('w',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n'+database_resume(OLD/'track_B_pair_unified_setup_001/contact_model_pair_unified.db')+f'/FILNAME,finalread{index:03d}\n/PREP7\n')
        component(f,'LOCAL_NODES',np.arange(1,len(mesh.nodes)+1));component(f,'LOCAL_CORNERS',np.unique(mesh.triangles[:,:3])+1)
        f.write('FINISH\n/POST1\n'+"FILE,'"+(OLD/'track_B_pair5_to_01500_001/compression').as_posix()+"',rst\nSET,6,7\n*GET,NTIME,ACTIVE,0,SET,TIME\n*CFOPEN,native_time,csv\n*VWRITE,NTIME\n(E24.16)\n*CFCLOS\n")
        export_fields(f,'final');f.write('FINISH\n/EXIT,NOSAVE\n')
    write_json(d/'simulation_manifest.json',{'state':[6,7],'strain':.012575,'inherited_not_new_compression':True,
       'source_RST_sha256':file_hash(OLD/'track_B_pair5_to_01500_001/compression.rst'),'input_sha256':file_hash(d/'input.inp')})


def compare():
    hashes=[]
    for index in [1,2]:
        d=BASE/f'final_readback_{index:03d}';r=read(d/'execution_receipt.json')
        assert r['process']['returncode']==0 and abs(float((d/'native_time.csv').read_text().strip())-.012575)<1e-12
        hashes.append({name:file_hash(d/name) for name in ['final_u.csv','final_fields.csv']})
    assert hashes[0]==hashes[1]
    a=np.loadtxt(BASE/'final_readback_001/final_u.csv',delimiter=',');s=np.loadtxt(BASE/'final_readback_001/final_fields.csv',delimiter=',')
    assert len(a)==174746 and len(s)==47525 and np.isfinite(a).all() and np.isfinite(s).all()
    write_json(RUN/'fields/REPEAT_READBACK.json',{'status':'PASS_REPEAT_NATIVE_FULL_FIELD_READBACK','hashes':hashes,
       'nodes':len(a),'corners':len(s),'stress_columns':['SXX','SYY','SXY','SEQV'],'strain_columns':['EPEL_XX','EPEL_YY','EPEL_XY'],
       'inherited_accepted_strain':.012575,'new_strain_achieved':False})
    print('PASS repeated native fields',len(a),len(s),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','compare']);p.add_argument('--index',type=int,default=1);a=p.parse_args()
    if a.action=='prepare':prepare(a.index)
    elif a.action=='execute':execute(f'final_readback_{a.index:03d}')
    else:compare()
