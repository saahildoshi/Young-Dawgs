"""Independent licensed validation of target-normal nodal GC detection."""
from pathlib import Path
import re
import numpy as np
from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.element_quality import quadratic_mapping
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.general_contact_output import general_contact_vectors,GC_COLUMNS
from metamaterial_eval.simulation.general_contact_results import read_table
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.microstructure_results import unsupported_result_queries
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v064_small_study import direct_post
from scripts.v066_restart import BASE,RUN,load,compact


def main():
    source=BASE/'internal_fixture_enabled_003';m=load(source/'simulation_manifest.json')
    assert load(source/'execution_receipt.json')['process']['returncode']==0
    with np.load(BASE/'internal_fixture_geometry_003/mesh.npz') as z:mesh=Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])
    d=BASE/'internal_fixture_enabled_003_post001';d.mkdir(parents=True,exist_ok=False)
    model={'user_model_elements':len(mesh.triangles)+len(mesh.boundary),'general_contact_component':'INTERNAL_GC'}
    lines=['/BATCH','/CLEAR,START',database_resume(source/'checkpoint.db').strip(),'/FILNAME,readonly','/GOPR','/PREP7',
        '/OUTPUT,nodal_type_after,txt','ETLIST,2','/OUTPUT','FINISH']
    for line in direct_post(m['model'],m['target_strain']):
        lines.append(line)
        if line=='/POST1':lines.append("FILE,'"+(source/'compression').as_posix()+"',rst")
    lines+=['ESEL,S,ENAME,,172','ETABLE,ERAS','ETABLE,CNSTAT,NMISC,19']+general_contact_vectors(model,'check',chunk_size=1000)+['FINISH','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n')
    write_json(d/'provenance.json',{'source_RST_sha256':file_hash(source/'compression.rst'),'source_database_sha256':file_hash(source/'checkpoint.db'),'source_receipt_sha256':file_hash(source/'execution_receipt.json'),'input_sha256':file_hash(d/'input.inp'),'scope':'Independent actual nodal-contact RST readback, no solve'})
    r=run_progressive(d,timeout=180,solve=False,cores=1);compact(d,RUN/'internal_contact'/d.name)
    for name in ['check_gc_status.csv','check_gc_fields.csv','check_gc_balance.csv','direct_history.csv','direct_displacements.csv','direct_stress.csv','nodal_type_after.txt']:
        (RUN/'internal_contact'/d.name/name).write_bytes((d/name).read_bytes())
    if r['process']['returncode']!=0 or unsupported_result_queries((d/'solver.out').read_text(errors='replace')):raise ValueError('Nodal fixture readback failed')
    inventory=(d/'nodal_type_after.txt').read_text();assert re.search(r'KEYOPT\( 1- 6\)=\s+0\s+1\s+0\s+2',inventory)
    u=read_table(d/'direct_displacements.csv',['node','ux_mm','uy_mm']);h=read_table(d/'direct_history.csv',['pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'])[0]
    fields=read_table(d/'check_gc_fields.csv',GC_COLUMNS);status=read_table(d/'check_gc_status.csv',['element','status']);balance=read_table(d/'check_gc_balance.csv',['assembled_contact_fx_N','assembled_contact_fy_N'])
    assert np.array_equal(u[:,0],np.arange(1,len(mesh.nodes)+1))
    mapping=quadratic_mapping(mesh.nodes[mesh.triangles]+u[mesh.triangles,1:3]);positive=bool(np.all(mapping['positive_over_reference_triangle']))
    residual=float(abs(h[4]+h[5])/max(abs(h[4]),abs(h[5])));pen=max(0,float(fields[:,5:7].max()));force=float(np.linalg.norm(balance[0])/max(np.linalg.norm(fields[:,[13,7]],axis=1).sum(),1e-12))
    passed=bool(positive and residual<=.01 and pen<=1e-5 and force<=.01 and np.any(status[:,1]>=2) and fields[:,2:5].max()>0 and h[4]<0<h[5])
    q={'status':'PASS_ACTUAL_NODAL_GC_INTERFACE_FORCE_PEN_MAPPING' if passed else 'HOLD','native_contact_detection_keyopt4':2,
        'actual_type_after_solution_verified':True,'independent_RST_reopened':True,'nodes':len(mesh.nodes),'TRI6':len(mesh.triangles),
        'upper_RF_N':float(h[4]),'lower_RF_N':float(h[5]),'reaction_balance_relative':residual,'stored_endpoint_penetration_max_mm':pen,
        'assembled_GC_force_residual_relative':force,'closed_GC_skins':int(np.sum(status[:,1]>=2)),'all_quadratic_maps_positive':positive,
        'native_pressure_max_MPa':float(fields[:,2:5].max()),'scope':'Small interface force/penetration/mapping validation; full-microstructure corner behavior still requires actual independently checked loading.'}
    write_json(RUN/'internal_contact/NODAL_FIXTURE_QUALIFICATION.json',q);print(q,flush=True)


if __name__=='__main__':main()
