"""Reopen the immutable full parent and compare native fields and reactions."""
import json
import numpy as np
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import compact
from scripts.v067_fixture import BASE, RUN


def main():
    source=artifact_root()/'solver/v066/fine_nodal_recovery01_001'
    fields=source.with_name(source.name+'_qualified001')/'state006'
    d=BASE/'qualified_full_parent_readback001';d.mkdir(parents=True,exist_ok=False)
    ids=np.load(fields/'corner_node_ids.npy'); chosen=[n for n in [98184,99399,4990] if n in ids]
    assert len(chosen)==3
    lines=['/BATCH','/CLEAR,START',database_resume(source/'compression.rdb').strip(),'/FILNAME,readonly','/POST1',
           "FILE,'"+(source/'compression').as_posix()+"',rst",'SET,3,6','*GET,TT,ACTIVE,0,SET,TIME',
           '*GET,UYTOP,NODE,2766511,U,Y','*GET,RFUP,NODE,2766511,RF,FY','*GET,RFLOW,NODE,2766508,RF,FY',
           '*CFOPEN,parent_history,csv','*VWRITE',"('pseudo_time,top_uy_mm,upper_rf_y_N,lower_rf_y_N')",'*VWRITE,TT,UYTOP,RFUP,RFLOW',"(E24.16,3(',',E24.16))",'*CFCLOS',
           '*CFOPEN,parent_fields,csv','*VWRITE',"('node,ux,uy,syy,seqv,eyy,exx')"]
    for node in chosen:
        for variable,item,comp in [('UXV','U','X'),('UYV','U','Y'),('SY','S','Y'),('SE','S','EQV'),('EY','EPEL','Y'),('EX','EPEL','X')]:
            lines.append(f'*GET,{variable},NODE,{node},{item},{comp}')
        lines += [f'*VWRITE,{node},UXV,UYV,SY,SE,EY,EX',"(F12.0,6(',',E24.16))"]
    lines+=['*CFCLOS','FINISH','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    expected=json.loads((RUN/'audit/INITIAL_AUTHENTICATION.json').read_text(encoding='utf-8'))['parent_native_files']
    write_json(d/'provenance.json',{'source':str(source),'native_files':expected,'read_only':True,'input_sha256':file_hash(d/'input.inp')})
    receipt=run_progressive(d,timeout=600,solve=False,cores=1)
    assert receipt['process']['returncode']==0
    h=np.loadtxt(d/'parent_history.csv',delimiter=',',skiprows=1)
    values=np.loadtxt(d/'parent_fields.csv',delimiter=',',skiprows=1,ndmin=2)
    u=np.load(fields/'native_displacement.npy',mmap_mode='r'); stress=np.load(fields/'native_corner_stress_strain.npy',mmap_mode='r')
    wanted=np.column_stack([u[np.array(chosen)-1,:2],stress[np.searchsorted(ids,chosen)]])
    assert np.allclose(values[:,1:],wanted,rtol=1e-11,atol=1e-12)
    assert np.allclose(h,[.009270608836206897,-.09493103448275862,-10.90307046622248,10.90287635833509],rtol=1e-11,atol=1e-12)
    unchanged={name:file_hash(source/name)==entry['sha256'] for name,entry in expected.items()}
    assert all(unchanged.values())
    compact(d,RUN/'restart_validation'/d.name)
    for name in ['parent_history.csv','parent_fields.csv']:(RUN/'restart_validation'/d.name/name).write_bytes((d/name).read_bytes())
    write_json(RUN/'restart_validation/PARENT_NATIVE_READBACK.json',{'status':'PASS','history':h.tolist(),'sampled_corner_nodes':chosen,
               'sampled_U_S_EPEL_match_existing_qualified_fields':True,'maximum_sampled_absolute_error':float(abs(values[:,1:]-wanted).max()),
               'all_four_immutable_native_files_reauthenticated_after_readback':unchanged,'native_receipt_sha256':file_hash(d/'execution_receipt.json'),
               'scope':'Fresh independent full-parent POST1 atLS3SS6; sampled fields plus signed pilots; complete fields remain bound to v066 qualification, not newly re-exported or reclassified.'})
    print('PASS full parent native readback',h.tolist(),flush=True)


if __name__=='__main__':main()
