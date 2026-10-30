"""Native contact fixture readback and enabled/disabled geometric comparison."""
from pathlib import Path
import argparse
import numpy as np
from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.element_quality import quadratic_mapping
from metamaterial_eval.simulation.deformed_boundaries import screen
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.reporting import write_json
from scripts.v066_restart import RUN,BASE,load,compact
from scripts.v066_contact import post_commands


def fixture_mesh():
    with np.load(BASE/'internal_fixture_geometry_002/mesh.npz') as z:return Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])


def post(source,mesh):
    out=BASE/(source.name+'_post001');out.mkdir(parents=True,exist_ok=False)
    result_base=(source/'compression').resolve().as_posix()
    lines=['/BATCH','/CLEAR,START',database_resume(source/'checkpoint.db').strip(),'/FILNAME,readonly','/GOPR']
    for line in post_commands(mesh):
        lines.append(line)
        if line=='/POST1':lines.extend(["FILE,'"+result_base+"',rst",'/OUTPUT,result_sets,txt','SET,LIST','/OUTPUT'])
    (out/'input.inp').write_text('\n'.join(lines+['FINISH','/EXIT,NOSAVE'])+'\n')
    write_json(out/'provenance.json',{'source_receipt_sha256':file_hash(source/'execution_receipt.json'),'source_RST_sha256':file_hash(source/'compression.rst'),
        'source_MODEL_database_sha256':file_hash(source/'checkpoint.db'),'input_sha256':file_hash(out/'input.inp'),'mode':'INDEPENDENT_NATIVE_POST1_NO_SOLVE_OR_SAVE'})
    r=run_progressive(out,timeout=300,solve=False,cores=1);compact(out,RUN/'internal_contact'/out.name)
    for name in ['direct_history.csv','direct_displacements.csv','direct_stress.csv','internal_contact.csv']:
        (RUN/'internal_contact'/out.name/name).write_bytes((out/name).read_bytes())
    assert r['process']['returncode']==0
    return out


def analyze(independent=False,refine=False):
    mesh=fixture_mesh();records=[]
    for enabled in [False,True]:
        source=BASE/(('internal_fixture_enabled_' if enabled else 'internal_fixture_disabled_')+'002')
        directory=post(source,mesh) if independent else source
        receipt=load(source/'execution_receipt.json');assert receipt['process']['returncode']==0
        u=np.loadtxt(directory/'direct_displacements.csv',delimiter=',',skiprows=1,ndmin=2)
        assert np.array_equal(u[:,0],np.arange(1,len(mesh.nodes)+1))
        xy=mesh.nodes+u[:,1:3];mapping=quadratic_mapping(xy[mesh.triangles])
        history=np.loadtxt(directory/'direct_history.csv',delimiter=',',skiprows=1,ndmin=2)[0]
        balance=abs(history[4]+history[5])/max(abs(history[4]),abs(history[5]))
        boundary=screen(xy,mesh.boundary,mesh.boundary_groups,original=mesh.nodes,tolerance=1e-7 if refine else 1e-6,record_limit=1000000)
        expected_contact_edges=[]
        for y in [.15,.16]:expected_contact_edges.append(np.all(np.isclose(mesh.nodes[mesh.boundary,1],y),axis=1)&np.all(mesh.nodes[mesh.boundary,0]>=.12-1e-9,axis=1))
        explained=all((expected_contact_edges[0][p['edge_a']] and expected_contact_edges[1][p['edge_b']]) or (expected_contact_edges[1][p['edge_a']] and expected_contact_edges[0][p['edge_b']]) for p in boundary['examples'])
        result={'enabled':enabled,'source':str(source),'independent_native_readback':independent,
            'engineering_strain':float(history[0]),'platen_travel_mm':float(-history[3]),'upper_RF_N':float(history[4]),'lower_RF_N':float(history[5]),
            'signed_support_balance_relative':float(balance),'invalid_deformed_mappings':int(np.sum(~mapping['positive_over_reference_triangle'])),
            'minimum_deformed_determinant_mm2':float(mapping['determinant_min'].min()),
            'boundary_screen':{k:v for k,v in boundary.items() if k not in ['examples','pore_area_records']},
            'all_flagged_pairs_are_the_intended_opposed_walls':bool(explained and len(boundary['examples'])==boundary['suspicious_pair_count']),
            'source_receipt_sha256':file_hash(source/'execution_receipt.json')}
        if enabled:
            c=np.loadtxt(directory/'internal_contact.csv',delimiter=',',skiprows=1,ndmin=2);nodes=c[:,-1].astype(int)-1
            lower=np.isclose(mesh.nodes[nodes,1],.15);upper=np.isclose(mesh.nodes[nodes,1],.16)
            fy_lower=float(c[lower,6].sum());fy_upper=float(c[upper,6].sum());fb=abs(fy_lower+fy_upper)/max(abs(fy_lower),abs(fy_upper),1e-12)
            pen=max(0,float(c[:,4:6].max()));pressure=float(c[:,2:4].max());active=int(np.sum(c[:,1]>=2))
            result.update(general_contact_elements=len(c),active_elements=active,max_endpoint_pressure_MPa=pressure,max_stored_endpoint_penetration_mm=pen,
                lower_wall_contact_FY_N=fy_lower,upper_wall_contact_FY_N=fy_upper,internal_signed_force_balance_relative=fb,
                only_opposed_exposed_walls_selected=bool(np.all(lower|upper)),gap_sign='Native positive gap record is penetration; negative is opening; pressure and force are independently read',
                tiny_contact_overlap_interpretation='Only intended native-contact wall pairs may approach/cross within the native1e-5mm penetration gate; this exception never applies to the platen-only microstructure')
            directions=[]
            for mask in expected_contact_edges:
                edges=mesh.boundary[mask];d=mesh.nodes[edges[:,1]]-mesh.nodes[edges[:,0]];directions.append(np.mean(d/np.linalg.norm(d,axis=1)[:,None],axis=0))
            result['initial_opposed_wall_normal_dot_product']=float(np.dot(*directions))
            result['fixture_mechanical_gates_passed']=bool(active>0 and pressure>0 and pen<=1e-5 and fb<=.01 and fy_lower*fy_upper<0 and balance<=.01 and not result['invalid_deformed_mappings'] and np.all(lower|upper) and result['all_flagged_pairs_are_the_intended_opposed_walls'])
        else:result['fixture_mechanical_gates_passed']=False
        if independent:
            comparisons={}
            for name in ['direct_history.csv','direct_displacements.csv','direct_stress.csv']+(['internal_contact.csv'] if enabled else []):
                a=np.loadtxt(source/name,delimiter=',',skiprows=1,ndmin=2);b=np.loadtxt(directory/name,delimiter=',',skiprows=1,ndmin=2)
                error=float(np.max(abs(a-b)/np.maximum(np.max(abs(a),axis=0),1e-12)))
                comparisons[name]=error;assert a.shape==b.shape and error<1e-10
            result['independent_repeat_max_column_scaled_error']=comparisons
        records.append(result)
    status='PASS_SMALL_NATIVE_INTERNAL_CONTACT_ONLY' if independent and records[1]['fixture_mechanical_gates_passed'] and not records[0]['boundary_screen']['passed'] else 'PRELIMINARY_OR_HOLD'
    out={'status':status,'fixtures':records,'full_microstructure_internal_contact':'NOT_CONFIGURED; fine continuation retains exact v065 platen-only native restart',
        'scalability':'Full213150pore-edge GC was not benchmarked; small success does not establish full model contact or postclosure response'}
    filename='QUALIFIED_SHORT_GAP.json' if independent else ('PRELIMINARY_SHORT_GAP_REFINED.json' if refine else 'PRELIMINARY_SHORT_GAP.json')
    write_json(RUN/'internal_contact'/filename,out)
    print(status,[(r['enabled'],r['fixture_mechanical_gates_passed']) for r in records],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--independent',action='store_true');p.add_argument('--refine',action='store_true');a=p.parse_args();analyze(a.independent,a.refine)
