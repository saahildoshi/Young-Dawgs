"""One evidence-directed iteration-limit recovery, using actual native frames."""
import argparse
import json
import numpy as np
from metamaterial_eval.simulation.progressive_compression import authenticated_restart_copy, run_progressive
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import compact
from scripts.v067_fixture import BASE, RUN

LABEL='local_fkn1_neqit64_001'


def prepare():
    source=BASE/'local_fkn1_001'; d=BASE/LABEL
    manifest=authenticated_restart_copy(source,d)
    source_provenance=json.loads((BASE/'local_fkn1_001_post001/provenance.json').read_text(encoding='utf-8'))
    state=source_provenance['states'][-1]
    assert (state['load_step'],state['substep'])==(18,8)
    z=np.load(BASE/'source_fixture_001/mesh.npz'); history=np.load(BASE/'source_fixture_001/measured_displacements.npy')
    spec=json.loads((BASE/'source_fixture_001/fixture_manifest.json').read_text(encoding='utf-8'))
    times=[s['engineering_strain'] for s in spec['source_snapshots']]
    values=history[-1]+(history[-1]-history[-2])*((.01-times[-1])/(times[-1]-times[-2]))
    lines=['/BATCH','/CLEAR,START','RESUME,compression,rdb','/FILNAME,compression','/GOPR','/SOLU',
           '/OUTPUT,restart_sets,txt','RESCONTROL,FILE_SUMMARY','/OUTPUT',
           'ANTYPE,STATIC,REST,18,8,CONTINUE','NEQIT,64','NLDIAG,CONT,ITER','NLDIAG,NRRE,ON,2','NLDIAG,EFLG,ON,2',
           'OUTRES,ALL,ALL','RESCONTROL,DEFINE,ALL,1,-1,,3','SOLVE','TIME,.01','NSUBST,2,240,1,OFF',
           f"D,{manifest['model']['controls']['top']},UY,-.1024"]
    for i in z['cut_nodes_zero_based']:
        lines += [f'D,{i+1},UX,{values[i,0]:.17g}',f'D,{i+1},UY,{values[i,1]:.17g}']
    lines+=['SOLVE','FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    # Read-only extraction resumes the exact original model, not a synthetic replacement.
    (d/'initial.db').write_bytes((source/'initial.db').read_bytes())
    manifest.update(input_sha256=file_hash(d/'input.inp'),NEQIT=64,source_local_restart=str(source),
                    restart_state=state,physical_contact_settings_unchanged=True)
    write_json(d/'simulation_manifest.json',manifest)
    compact(d,RUN/'local_fixture'/('prepared_'+LABEL))
    print(d,flush=True)


def execute():
    d=BASE/LABEL
    r=run_progressive(d,timeout=1200,no_progress_seconds=240,cores=2)
    compact(d,RUN/'local_fixture'/LABEL)
    print(LABEL,r['status'],r['process']['returncode'],r['converged_steps'][-3:],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute']);a=p.parse_args()
    prepare() if a.action=='prepare' else execute()
