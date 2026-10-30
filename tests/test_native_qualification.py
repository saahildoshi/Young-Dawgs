"""Synthetic malformed-export rejection controls, never licensed evidence."""
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from metamaterial_eval.simulation.native_qualification import qualify,stream_csv
from metamaterial_eval.simulation.solver_execution import file_hash


def dump(path,value):path.write_text(json.dumps(value),encoding='utf-8')
def load(path):return json.loads(Path(path).read_text())


@pytest.fixture
def synthetic(tmp_path):
    source=tmp_path/'source';post=tmp_path/'post';source.mkdir();post.mkdir()
    nodes=np.array([[0.,0.],[1,0],[0,1],[.5,0],[.5,.5],[0,.5]])
    mesh=SimpleNamespace(nodes=nodes,triangles=np.array([[0,1,2,3,4,5]]))
    model={'specimen_nodes':6,'specimen_TRI6':1,'contact_elements':{'top':1,'bottom':1},'config':{'width':10.24,'height':10.24,'thickness':1}}
    (source/'input.inp').write_text('SOLVE\n');(source/'compression.rst').write_text('synthetic unit control, not native');(source/'checkpoint.db').write_text('synthetic model only')
    (source/'solver.out').write_text('synthetic convergence evidence')
    manifest={'input_sha256':file_hash(source/'input.inp'),'protocol_sha256':'unit-protocol','target_strain':.00005}
    dump(source/'simulation_manifest.json',manifest)
    receipt={'process':{'returncode':0},'status':'PROCESS_EXITED','input_sha256':file_hash(source/'input.inp'),'converged_steps':[[1,1]]}
    receipt['process']['artifacts']={p.name:{'sha256':file_hash(p)} for p in source.iterdir()}
    dump(source/'execution_receipt.json',receipt)
    (post/'input.inp').write_text('SET,1,1\n');(post/'solver.out').write_text('synthetic unit control')
    (post/'result_sets.txt').write_text('1 0.00005 1 1 7\n')
    (post/'stage001_gate.txt').write_text('0,0\n')
    (post/'stage001_history.csv').write_text('pseudo_time,load_step,substep,top_uy_mm,upper_rf_y_N,lower_rf_y_N\n0.00005,1,1,-0.000512,-1,1\n')
    (post/'stage001_contact.csv').write_text('pair,element,status,pressure_i_MPa,pressure_j_MPa,gap_i_mm,gap_j_mm,contact_force_y_N\n1,2,2,1,1,1e-7,1e-7,-1\n2,3,2,1,1,1e-7,1e-7,1\n')
    (post/'stage001_displacements.csv').write_text('node,ux_mm,uy_mm\n'+''.join(f'{i},0,-0.000512\n' for i in range(1,7)))
    (post/'stage001_stress.csv').write_text('node,syy_MPa,seqv_MPa,elastic_eyy,elastic_exx\n'+''.join(f'{i},-1,1,-0.001,0.0003\n' for i in [1,2,3]))
    def bind():
        prov={'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
              'source_RST_sha256':file_hash(source/'compression.rst'),'source_checkpoint_database_sha256':file_hash(source/'checkpoint.db'),
              'source_manifest_sha256':file_hash(source/'simulation_manifest.json'),'source_protocol_sha256':'unit-protocol','input_sha256':file_hash(post/'input.inp')}
        dump(post/'provenance.json',prov)
        r={'process':{'returncode':0,'artifacts':{p.name:{'sha256':file_hash(p)} for p in post.iterdir() if p.name!='execution_receipt.json'}},'status':'PROCESS_EXITED','input_sha256':file_hash(post/'input.inp')}
        dump(post/'execution_receipt.json',r)
    bind()
    return source,post,model,mesh,bind


@pytest.mark.parametrize('variant',['valid','truncated_rst','missing_set','wrong_time','debug_substep','missing_reaction',
    'reaction_imbalance','missing_stress','missing_strain','missing_contact','partial_nodes','duplicate_nodes',
    'partial_corners','wrong_geometry','stale_export','source_failure','read_only_solve','negative_mapping'])
def test_incomplete_or_untrusted_exports_are_quarantined(synthetic,tmp_path,variant):
    source,post,model,mesh,bind=synthetic
    if variant=='truncated_rst':(source/'compression.rst').write_text('truncated')
    if variant=='missing_set':(post/'result_sets.txt').write_text('No Data Sets')
    if variant=='wrong_time':(post/'result_sets.txt').write_text('1 0.0001 1 1 7')
    if variant=='debug_substep':(post/'result_sets.txt').write_text('1 0.00005 1 999999 7')
    if variant in ['missing_reaction','reaction_imbalance']:
        p=post/'stage001_history.csv';p.write_text(p.read_text().replace(',-1,1',',0,0' if variant=='missing_reaction' else ',-1,2'))
    if variant in ['missing_stress','missing_strain','missing_contact']:
        (post/'solver.out').write_text({'missing_stress':'The requested S data is not available.','missing_strain':'The requested EPEL data is not available.','missing_contact':'Item NMIS has not been stored in the database.'}[variant])
    if variant in ['partial_nodes','duplicate_nodes']:
        p=post/'stage001_displacements.csv';s=p.read_text();p.write_text(s.rsplit('\n',2)[0]+'\n' if variant=='partial_nodes' else s.replace('6,0,','5,0,'))
    if variant=='partial_corners':
        p=post/'stage001_stress.csv';p.write_text(p.read_text().rsplit('\n',2)[0]+'\n')
    if variant=='stale_export':
        p=post/'stage001_stress.csv';p.write_text(p.read_text().replace('-1,1','-2,2'))
    if variant=='source_failure':
        p=source/'execution_receipt.json';r=load(p);r['status']='TIMEOUT';dump(p,r)
    if variant=='read_only_solve':(post/'input.inp').write_text('SOLVE\n')
    if variant=='negative_mapping':
        p=post/'stage001_displacements.csv';p.write_text(p.read_text().replace('2,0,','2,-2,'))
    if variant!='stale_export':bind()
    identity={'source_geometry_sha256':'wrong','mesh_semantic_sha256':'wrong'} if variant=='wrong_geometry' else None
    r=qualify(source,post,model,mesh,tmp_path/'result',load_json=load,identity=identity)
    assert r['accepted']==(variant=='valid')
    assert bool(r['accepted_measurements'])==(variant=='valid')
    assert r['effective_modulus_fit_MPa'] is None and not r['eligible_for_LLM_performance_ranking']


def test_streaming_rejects_nonfinite_and_malformed_arrays(tmp_path):
    p=tmp_path/'field.csv';p.write_text('node,ux,uy\n1,0,nan\n')
    with pytest.raises(ValueError):list(stream_csv(p,['node','ux','uy']))
