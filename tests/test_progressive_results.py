"""Malformed/partial native evidence controls; synthetic data are not solver evidence."""
import json
from types import SimpleNamespace
import numpy as np
import pytest
from metamaterial_eval.simulation.progressive_results import qualify_state
from metamaterial_eval.simulation.reporting import mesh_hash
from metamaterial_eval.simulation.solver_execution import file_hash


@pytest.mark.parametrize('variant',['valid_partial_job','unconverged','debug_set','wrong_displacement','partial_nodes','inverted_map','overlap','imbalance','missing_strain','zero_strain','stale_rst','mutating_post','wrong_mesh'])
def test_state_evidence_gates(tmp_path,variant):
    source=tmp_path/'source';post=tmp_path/'post';source.mkdir();post.mkdir()
    mesh=SimpleNamespace(nodes=np.array([[0.,0.],[1,0],[0,1],[.5,0],[.5,.5],[0,.5]]),triangles=np.array([[0,1,2,3,4,5]]),
        boundary=np.array([[0,1,3],[1,2,4],[2,0,5]]),boundary_groups=np.array(['external']*3))
    state={'time':.0001,'load_step':2,'substep':1}
    dump=lambda p,v:p.write_text(json.dumps(v))
    (source/'input.inp').write_text('SOLVE\n');(source/'compression.rst').write_text('Synthetic unit fixture, NOT native ANSYS');(source/'compression.rdb').write_text('synthetic database')
    (source/'solver.out').write_text('Converged step\nLater fatal stop\n')
    manifest={'mesh_semantic_sha256':mesh_hash(mesh),'input_sha256':file_hash(source/'input.inp'),
        'model':{'specimen_nodes':6,'specimen_TRI6':1,'contact_elements':{'top':1,'bottom':1},'config':{'width':1,'height':1,'thickness':1}}}
    if variant=='wrong_mesh':manifest['mesh_semantic_sha256']='wrong'
    dump(source/'simulation_manifest.json',manifest)
    dump(source/'nonlinear_telemetry.json',{'converged_substeps':[] if variant=='unconverged' else [{**state,'pseudo_time':state['time'],'source_line':1}]})
    receipt={'status':'TIMEOUT','input_sha256':file_hash(source/'input.inp'),'process':{'returncode':-1,'artifacts':{p.name:{'sha256':file_hash(p)} for p in source.iterdir()}}}
    dump(source/'execution_receipt.json',receipt)
    (post/'input.inp').write_text('SOLVE\n' if variant=='mutating_post' else 'SET,2,1\n')
    (post/'solver.out').write_text('The requested EPEL data is not available.' if variant=='missing_strain' else 'Synthetic readback')
    (post/'result_sets.txt').write_text('1 .0001 2 '+('999999' if variant=='debug_set' else '1')+' 7\n')
    (post/'stage001_gate.txt').write_text('0,0\n')
    uy=-.0002 if variant=='wrong_displacement' else -.0001
    lower=2 if variant=='imbalance' else 1
    (post/'stage001_history.csv').write_text(f'pseudo_time,load_step,substep,top_uy_mm,upper_rf_y_N,lower_rf_y_N\n.0001,2,1,{uy},-1,{lower}\n')
    (post/'stage001_contact.csv').write_text('pair,element,status,pressure_i_MPa,pressure_j_MPa,gap_i_mm,gap_j_mm,contact_force_y_N\n1,2,2,1,1,1e-7,1e-7,-1\n2,3,2,1,1,1e-7,1e-7,1\n')
    (post/'stage001_displacements.csv').write_text('node,ux_mm,uy_mm\n'+''.join(f'{i},{-2 if variant=="inverted_map" and i==2 else 0},-.0001\n' for i in range(1,6 if variant=='partial_nodes' else 7)))
    (post/'stage001_stress.csv').write_text('node,syy_MPa,seqv_MPa,elastic_eyy,elastic_exx\n'+''.join(f'{i},-1,1,-.001,.0003\n' for i in [1,2,3]))
    if variant=='zero_strain':
        p=post/'stage001_stress.csv';p.write_text(p.read_text().replace('-.001,.0003','0,0'))
    prov={'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),'source_RST_sha256':file_hash(source/'compression.rst'),
        'source_database_filename':'compression.rdb','source_database_sha256':file_hash(source/'compression.rdb'),
        'source_manifest_sha256':file_hash(source/'simulation_manifest.json'),'input_sha256':file_hash(post/'input.inp'),'states':[state]}
    dump(post/'provenance.json',prov)
    dump(post/'execution_receipt.json',{'status':'PROCESS_EXITED','input_sha256':file_hash(post/'input.inp'),'process':{'returncode':0,'artifacts':{p.name:{'sha256':file_hash(p)} for p in post.iterdir()}}})
    if variant=='stale_rst':(source/'compression.rst').write_text('changed')
    if variant=='overlap':
        # Duplicate physical loop must be caught even though every element maps positively.
        mesh.boundary=np.concatenate([mesh.boundary,mesh.boundary]);mesh.boundary_groups=np.array(['external']*6)
    r=qualify_state(source,post,mesh,1,state,tmp_path/'result')
    assert r['accepted']==(variant=='valid_partial_job')
    assert not r['eligible_for_LLM_performance_ranking']
