"""Qualify vector GC field/target-ID readback on the passed connected fixture."""
import numpy as np
import argparse
from metamaterial_eval.simulation.general_contact_output import general_contact_vectors,GC_COLUMNS
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.microstructure_results import observed_native_result,unsupported_result_queries
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import BASE,RUN,load,compact


def main(revision='002'):
    source=BASE/'internal_fixture_enabled_002';original=np.loadtxt(source/'internal_contact.csv',delimiter=',',skiprows=1,ndmin=2)
    d=BASE/('gc_output_vector_probe_'+revision);d.mkdir(parents=True,exist_ok=False)
    native,observation=observed_native_result(source,load(source/'simulation_manifest.json'),load(source/'execution_receipt.json'),(source/'solver.out').read_text(errors='replace'))
    model={'user_model_elements':int(original[:,0].max()),'general_contact_component':'INTERNAL_GC'}
    lines=['/BATCH','/CLEAR,START',database_resume(source/'checkpoint.db').strip(),'/FILNAME,readonly','/GOPR','/POST1',
        "FILE,'"+native.with_suffix('').as_posix()+"',rst",'SET,LAST','ESEL,S,ENAME,,172','ETABLE,ERAS','ETABLE,CNSTAT,NMISC,19']
    lines+=general_contact_vectors(model,'probe',chunk_size=1000)+['CMSEL,S,INTERNAL_GC','*CFOPEN,direct_fx,csv','*VWRITE',"('element,fx_N')",'EID=0','*GET,NC,ELEM,0,COUNT','*DO,KK,1,NC','EID=ELNEXT(EID)','*GET,FXV,ELEM,EID,NMISC,21','*VWRITE,EID,FXV',"(F12.0,',',E24.16)",'*ENDDO','*CFCLOS','FINISH','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n')
    write_json(d/'provenance.json',{'source_RST_sha256':file_hash(native),'native_filename_observation':observation,'input_sha256':file_hash(d/'input.inp'),'purpose':'Actual native GC vectors and target segment IDs, no solve/source mutation'})
    r=run_progressive(d,timeout=180,solve=False,cores=1);compact(d,RUN/'internal_contact'/d.name)
    for name in ['probe_gc_status.csv','probe_gc_fields.csv','probe_gc_balance.csv','direct_fx.csv']:(RUN/'internal_contact'/d.name/name).write_bytes((d/name).read_bytes())
    text=(d/'solver.out').read_text(errors='replace')
    assert r['process']['returncode']==0 and not unsupported_result_queries(text)
    status=np.loadtxt(d/'probe_gc_status.csv',delimiter=',',skiprows=1,ndmin=2)
    fields=np.loadtxt(d/'probe_gc_fields.csv',delimiter=',',skiprows=1,ndmin=2)
    assert (d/'probe_gc_fields.csv').read_text().splitlines()[0].strip().split(',')==GC_COLUMNS
    assert np.array_equal(status,original[:,:2])
    for a,b in [(0,0),(1,1),(2,2),(3,3),(5,4),(6,5),(7,6),(10,7)]:assert np.array_equal(fields[:,a],original[:,b]),(a,b)
    direct=np.loadtxt(d/'direct_fx.csv',delimiter=',',skiprows=1,ndmin=2);assert np.array_equal(fields[:,[0,13]],direct)
    balance=np.loadtxt(d/'probe_gc_balance.csv',delimiter=',',skiprows=1,ndmin=2);norm=float(np.linalg.norm(fields[:,[13,7]],axis=1).sum());residual=float(np.linalg.norm(balance[0])/norm)
    assert residual<=.01
    targets=np.unique(fields[:,8:10].astype(int));positive=targets[targets>0]
    q={'status':'PASS_ACTUAL_NATIVE_GC_VECTOR_OUTPUT','rows':len(fields),'native_fields_identical_to_direct_queries':True,
        'native_target_ids':targets.tolist(),'positive_target_ids_are_actual_GC_skin_elements':bool(np.isin(positive,status[:,0]).all()),
        'columns':GC_COLUMNS,'read_only_receipt_sha256':file_hash(d/'execution_receipt.json')}
    q.update(native_FX_direct_query_match=True,native_assembled_XY_balance_N=balance[0].tolist(),native_assembled_contact_force_residual=residual)
    write_json(RUN/'internal_contact'/('GC_VECTOR_OUTPUT_QUALIFICATION_'+revision+'.json'),q);print(q['status'],q['native_target_ids'][:12],q['positive_target_ids_are_actual_GC_skin_elements'],residual,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--revision',default='002');a=p.parse_args();main(a.revision)
