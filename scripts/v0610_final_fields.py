"""Two authenticated read-only extractions of the final accepted v0610 crop state."""
import argparse
import io
import shutil
import numpy as np
from scripts.v0610_common import BASE,RUN,read,write_json,file_hash,execute,copy_evidence
from scripts.v068_track_b import mesh_and_plan
from scripts.v069_local import export_fields
from metamaterial_eval.simulation.microstructure_import import component
from metamaterial_eval.simulation.progressive_compression import multi_export_input
from metamaterial_eval.simulation.microstructure_results import unsupported_result_queries

SOURCE='track_B_pair5_arc_strict_001'
PROOF=RUN/'track_B_progressive_compression'/f'{SOURCE}_mechanical_qualification.json'


def prepare(index):
    q=read(PROOF);accepted=[s for s in q['states'] if s['accepted']]
    if not accepted:raise ValueError('No final accepted crop state')
    state=accepted[-1];source=BASE/SOURCE;receipt=read(source/'execution_receipt.json')
    if file_hash(source/'execution_receipt.json')!=q['source_receipt_sha256']:raise ValueError('Changed source receipt')
    rst_sha=file_hash(source/'compression.rst')
    if rst_sha!=receipt['process']['artifacts']['compression.rst']['sha256']:raise ValueError('Changed native RST')
    database=BASE/'track_B_pair_unified_setup_001/contact_model_pair_unified.db'
    if file_hash(database)!=read(RUN/'track_B_contact_fixture/PAIR_UNIFIED5_SETUP_QUALIFICATION.json')['native_database_sha256']:raise ValueError('Changed native setup')
    model=read(BASE/'track_B_setup_001/simulation_manifest.json')
    model.update(user_model_elements=read(RUN/'track_B_contact_fixture/SETUP_QUALIFICATION.json')['native_elements'],
                 general_contact_elements=15362,contact_elements=model['platen_contact_elements'])
    deck=multi_export_input(database,source/'compression',model,[{'load_step':state['load_step'],'substep':state['substep'],'time':state['requested_time']}],chunk_size=50000,farfield=True)
    mesh,_,_,_=mesh_and_plan();f=io.StringIO();f.write('/PREP7\n')
    component(f,'LOCAL_NODES',np.arange(1,len(mesh.nodes)+1));component(f,'LOCAL_CORNERS',np.unique(mesh.triangles[:,:3])+1)
    f.write('FINISH\n');deck=deck.replace('/POST1',f.getvalue()+'/POST1',1)
    f=io.StringIO();export_fields(f,'final')
    f.write('ALLSEL,ALL\nCMSEL,S,LOCAL_PAIR_CONTACT\n*GET,NP,ELEM,0,COUNT\nETABLE,CNSTAT,NMISC,19\n*CFOPEN,final_pair,csv\n*VWRITE\n')
    f.write("('element,status,pressure_i_MPa,pressure_j_MPa,pen_i_mm,pen_j_mm,fy_N,target_i,target_j')\n")
    f.write('EID=0\n*DO,KK,1,NP\nEID=ELNEXT(EID)\n*GET,STV,ELEM,EID,ETAB,CNSTAT\nPI=0\nPJ=0\nGI=0\nGJ=0\nFYV=0\nTI=0\nTJ=0\n*IF,STV,GT,0,THEN\n')
    for var,item,seq in [('PI','SMISC',1),('PJ','SMISC',2),('GI','NMISC',5),('GJ','NMISC',6),('FYV','NMISC',22),('TI','NMISC',23),('TJ','NMISC',24)]:f.write(f'*GET,{var},ELEM,EID,{item},{seq}\n')
    f.write('*ENDIF\n*VWRITE,EID,STV,PI,PJ,GI,GJ,FYV,TI,TJ\n'+"(F12.0,',',F4.0,5(',',E24.16),2(',',F12.0))\n*ENDDO\n*CFCLOS\nALLSEL,ALL\n")
    deck=deck.removesuffix('FINISH\n/EXIT,NOSAVE\n')+f.getvalue()+'FINISH\n/EXIT,NOSAVE\n'
    deck=deck.replace('/FILNAME,readonly',f'/FILNAME,v610_final_{index:03d}')
    d=BASE/f'final_readback_{index:03d}';d.mkdir(exist_ok=False)
    (d/'input.inp').write_text(deck,encoding='utf-8',newline='\n')
    write_json(d/'simulation_manifest.json',{'source':SOURCE,'material_identity':'CROP_LINEAR_ELASTIC_E1000_V068','state':[state['load_step'],state['substep']],
        'strain':state['measurement']['engineering_compression_strain'],'source_RST_sha256':rst_sha,'source_receipt_sha256':file_hash(source/'execution_receipt.json'),
        'master_qualification_sha256':file_hash(PROOF),'setup_database_sha256':file_hash(database),'input_sha256':file_hash(d/'input.inp'),'read_only':True})
    copy_evidence(d,'fields');print('Prepared accepted-state readback',index,flush=True)


def compare():
    names=['final_u.csv','final_fields.csv','final_pair.csv','stage001_history.csv','stage001_contact.csv','stage001_contact_status.csv','stage001_gc_status.csv','stage001_gc_fields.csv']
    hashes=[]
    for index in [1,2]:
        d=BASE/f'final_readback_{index:03d}';r=read(d/'execution_receipt.json');m=read(d/'simulation_manifest.json')
        assert r['process']['returncode']==0 and r['solver_version']=='2024 R1'
        assert file_hash(d/'input.inp')==r['input_sha256']==m['input_sha256']
        assert file_hash(PROOF)==m['master_qualification_sha256']
        assert file_hash(BASE/SOURCE/'compression.rst')==m['source_RST_sha256']
        assert not unsupported_result_queries((d/'solver.out').read_text(errors='replace'))
        hashes.append({name:file_hash(d/name) for name in names})
    assert hashes[0]==hashes[1]
    d=BASE/'final_readback_001';u=np.loadtxt(d/'final_u.csv',delimiter=',');s=np.loadtxt(d/'final_fields.csv',delimiter=',')
    mesh,_,_,_=mesh_and_plan();corners=np.unique(mesh.triangles[:,:3])+1
    assert u.shape==(174746,3) and s.shape==(47525,8) and np.isfinite(u).all() and np.isfinite(s).all()
    assert np.array_equal(u[:,0],np.arange(1,174747)) and np.array_equal(s[:,0],corners)
    q=read(PROOF);idx,state=[(i,s) for i,s in enumerate(q['states'],1) if s['accepted']][-1]
    original=BASE/(SOURCE+'_post1_all_v2');old=np.loadtxt(original/f'stage{idx:03d}_displacements.csv',delimiter=',',skiprows=1)
    assert np.array_equal(u,old)
    assert file_hash(d/'final_pair.csv')==file_hash(original/f'stage{idx:03d}_pair_contact.csv')
    for name in names:
        if (d/name).stat().st_size<200000:shutil.copyfile(d/name,RUN/'fields'/name)
    write_json(RUN/'fields/REPEAT_READBACK.json',{'status':'PASS_REPEAT_NATIVE_FULL_FIELD_READBACK','hashes':hashes,'nodes':len(u),'corners':len(s),
        'accepted_strain':state['measurement']['engineering_compression_strain'],'state':[state['load_step'],state['substep']],'source':SOURCE,
        'source_RST_sha256':m['source_RST_sha256'],'master_qualification_sha256':file_hash(PROOF),'material_identity':'CROP_LINEAR_ELASTIC_E1000_V068',
        'stress_columns':['SXX','SYY','SXY','SEQV'],'strain_columns':['native_EPEL_XX','native_EPEL_YY','native_EPEL_XY'],
        'original_all_state_displacements_and_pair_identical':True,'new_strain_beyond_historical_maximum':False,'midside_stress_invented':False})
    print('PASS two native extractions including contact',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run','compare']);p.add_argument('--index',type=int,choices=[1,2],default=1);a=p.parse_args()
    if a.action=='prepare':prepare(a.index)
    elif a.action=='run':execute(f'final_readback_{a.index:03d}',solve=False,timeout=1200)
    else:compare()
