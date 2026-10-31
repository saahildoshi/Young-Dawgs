"""Independent local mechanics gates; extrapolated states stay diagnostic."""
import argparse
import json
import numpy as np
from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.element_quality import quadratic_mapping
from metamaterial_eval.simulation.deformed_boundaries import screen
from metamaterial_eval.simulation.nodal_contact_geometry import explain_nodal_pairs
from metamaterial_eval.simulation.general_contact_results import explain_contact_pairs
from metamaterial_eval.simulation.quadratic_separation import certify_separated
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.microstructure_results import unsupported_result_queries
from scripts.v067_fixture import BASE, RUN


def table(path, columns):
    with path.open(encoding='utf-8') as f:
        first=next(f).strip().split(',')
        assert len(first)==columns
        rows=[s for s in f if s.strip()]
    return np.loadtxt(rows, delimiter=',', ndmin=2) if rows else np.empty((0,columns))


def qualify(label):
    source=BASE/label; post=BASE/(label+'_post001'); fixture=BASE/'source_fixture_001'
    p=json.loads((post/'provenance.json').read_text(encoding='utf-8'))
    assert file_hash(source/'compression.rst')==p['source_RST_sha256']
    assert not unsupported_result_queries((post/'solver.out').read_text(encoding='utf-8',errors='replace'))
    receipt=json.loads((post/'execution_receipt.json').read_text(encoding='utf-8'))
    assert receipt['process']['returncode']==0
    z=np.load(fixture/'mesh.npz'); m=Mesh(*[z[k] for k in ['nodes','triangles','boundary','boundary_groups']])
    spec=json.loads((fixture/'fixture_manifest.json').read_text(encoding='utf-8'))
    manifest=json.loads((source/'simulation_manifest.json').read_text(encoding='utf-8'))
    native_contact=json.loads((source/'contact_telemetry.json').read_text(encoding='utf-8'))['records']
    original=z['original_nodes_one_based']
    topology_path=source/'gc_topology.csv'
    if not topology_path.exists() and manifest.get('source_local_restart'):
        parent_source=__import__('pathlib').Path(manifest['source_local_restart'])
        topology_path=parent_source/'gc_topology.csv'
        parent_receipt=json.loads((parent_source/'execution_receipt.json').read_text(encoding='utf-8'))
        assert file_hash(topology_path)==parent_receipt['process']['artifacts']['gc_topology.csv']['sha256']
    topo=table(topology_path,6).astype(int)
    by_nodes={tuple(sorted(e+1)):i for i,e in enumerate(m.boundary)}
    eid_to_boundary={int(row[0]):by_nodes[tuple(sorted(row[1:4]))] for row in topo}
    mapped=np.array(list(eid_to_boundary.values()))
    physical=np.flatnonzero(m.boundary_groups!='artificial_cut')
    assert np.array_equal(np.sort(mapped),physical), 'Missing/duplicate physical GC faces or included artificial cuts'
    eids=np.zeros(len(m.boundary),dtype=int)
    for eid,edge in eid_to_boundary.items(): eids[edge]=eid
    core=np.linalg.norm(m.nodes-np.array([1.97,10.22]),axis=1)<.12
    core[z['cut_nodes_zero_based']]=False
    states=[]
    for state in p['states']:
        prefix=post/state['prefix']
        time_file=prefix.with_name(prefix.name+'_time.csv')
        native_time=float(table(time_file,1)[0,0]) if time_file.exists() else state['time']
        u=table(prefix.with_name(prefix.name+'_displacements.csv'),3)
        assert np.array_equal(u[:,0],np.arange(1,len(m.nodes)+1))
        xy=m.nodes+u[:,1:3]
        mapping=quadratic_mapping(xy[m.triangles])
        positive=bool(mapping['positive_over_reference_triangle'].all())
        contact=table(prefix.with_name(prefix.name+'_gc_fields.csv'),14)
        forces=table(prefix.with_name(prefix.name+'_reactions.csv'),3)
        balance=table(prefix.with_name(prefix.name+'_gc_balance.csv'),2)
        endpoint_pen=max(0,float(contact[:,5:7].max())) if len(contact) else 0.
        last_contact={}
        for row in native_contact:
            if row['pair']<0 and (row['load_step'],row['substep'])==(state['load_step'],state['substep']):
                last_contact[row['pair']]=row
        cnd_pen=max([0.]+[r['penetration_or_gap_mm'] for r in last_contact.values()])
        pen=max(endpoint_pen,cnd_pen)
        reaction_error=float(np.linalg.norm(forces[:,1:3].sum(axis=0))/max(np.linalg.norm(forces[:,1:3],axis=1).sum(),1e-12))
        contact_error=float(np.linalg.norm(balance[0])/max(np.linalg.norm(contact[:,[13,7]],axis=1).sum(),1e-12)) if len(balance) else 0.
        overlap=screen(xy,m.boundary,m.boundary_groups,original=m.nodes,record_limit=100000)
        geometry_error=None
        try:
            if overlap['orientation_inverted_loops'] or overlap['edges_exceeding_requested_tolerance']: raise ValueError('Boundary orientation/subdivision failure')
            lookup={eid_to_boundary[int(r[0])]:r for r in contact}
            if manifest.get('GC_detection_keyopt4',2)==2:
                explanations=explain_nodal_pairs(overlap,eids,lookup,m,xy)
            else:
                explanations=[]
                for pair in overlap['examples']:
                    proof=certify_separated(xy[m.boundary[pair['edge_a']]],xy[m.boundary[pair['edge_b']]])
                    if proof['passed']:
                        explanations.append({**pair,'explanation':'GUARDED_POSITIVE_QUADRATIC_SEPARATION','geometry_proof':proof})
                    else:
                        one={**overlap,'suspicious_pair_count':1,'examples':[pair]}
                        explanations+=explain_contact_pairs(one,eids,lookup)
        except ValueError as exc:
            geometry_error=str(exc); explanations=[]
        native_closed=int(np.sum(contact[:,1]>=2)) if len(contact) else 0
        force_path=RUN/'local_fixture'/(label+'_interface_force.json')
        force_q=json.loads(force_path.read_text(encoding='utf-8')) if force_path.exists() else None
        interface=next((r for r in force_q['states'] if (r['load_step'],r['substep'])==(state['load_step'],state['substep'])),None) if force_q else None
        native_closed=int(np.sum(contact[:,1]>=2)) if len(contact) else 0
        force_pass=bool(interface and interface['opposition_passed']) if native_closed else True
        valid=positive and pen<=1e-5 and reaction_error<=.01 and force_pass and geometry_error is None
        record={**state,'time':native_time,'parsed_solver_log_time':state['time'],'mechanical_gates_passed':bool(valid),'extrapolated':state['load_step']>15,
                'scope':'LOCAL_DIAGNOSTIC_ONLY', 'all_TRI6_positive':positive,'maximum_penetration_mm':pen,
                'stored_endpoint_penetration_mm':endpoint_pen,'native_converged_contact_diagnostic_penetration_mm':cnd_pen,
                'signed_reaction_sum_N':forces[:,1:3].sum(axis=0).tolist(),'reaction_sum_relative':reaction_error,
                'platen_signed_RF_N':forces[-1,1:3].tolist(),'cut_signed_RF_N':forces[:-1,1:3].sum(axis=0).tolist(),
                'assembled_GC_force_residual_relative':contact_error,'closed_gc_skins':native_closed,
                'selected_skin_FSUM_scope':'Selected contact element contributions, not a complete two-sided interface balance',
                'independent_two_sided_interface':interface,'contact_force_opposition_passed':force_pass,
                'maximum_pressure_MPa':float(contact[:,2:5].max()) if len(contact) else 0.,
                'boundary_candidates':overlap['suspicious_pair_count'],'geometry_failure':geometry_error,'geometry_explanations':explanations}
        if state['load_step']<=15:
            snapshot=spec['source_snapshots'][state['load_step']-1]
            parent=np.load(fixture/'measured_displacements.npy',mmap_mode='r')[state['load_step']-1]
            err=u[:,1:3]-parent
            record['cut_displacement_max_error_mm']=float(abs(err[z['cut_nodes_zero_based']]).max())
            record['core_U_RMS_relative']=float(np.sqrt(np.mean(err[core]**2))/np.linalg.norm(parent[core],axis=1).max())
            s=table(prefix.with_name(prefix.name+'_stress.csv'),5)
            ids=np.load(snapshot['directory']+'/corner_node_ids.npy',mmap_mode='r')
            values=np.load(snapshot['directory']+'/native_corner_stress_strain.npy',mmap_mode='r')
            expected=values[np.searchsorted(ids,original[s[:,0].astype(int)-1])]
            mask=core[s[:,0].astype(int)-1]
            errors=np.sqrt(np.mean((s[mask,1:]-expected[mask])**2,axis=0))/np.maximum(np.sqrt(np.mean(expected[mask]**2,axis=0)),1e-12)
            record['core_SYY_SEQV_EYY_EXX_RMS_relative']=errors.tolist()
            record['parent_match_passed']=bool(record['cut_displacement_max_error_mm']<=1e-10 and record['core_U_RMS_relative']<=.02 and errors.max()<=.1)
        states.append(record)
    q={'label':label,'physical_face_inventory_verified':True,'GC_faces':len(mapped),'native_GC_types':np.unique(topo[:,4]).tolist(),
       'parent_match_all_measured_states':all(r['parent_match_passed'] for r in states if 'parent_match_passed' in r) if any('parent_match_passed' in r for r in states) else None,
       'licensed_POST1_receipt_sha256':file_hash(post/'execution_receipt.json'),'states':states,
       'all_local_states_mechanical_gates_passed':all(r['mechanical_gates_passed'] for r in states),
       'full_model_strain_qualification':False,
       'local_failure_reproduced':'Qualitative contact-onset nonconvergence reproduced; exact global threshold/context differs.' if json.loads((source/'execution_receipt.json').read_text(encoding='utf-8'))['process']['returncode'] else 'No Newton stall in this variant; all independent geometry gates still apply.'}
    write_json(RUN/'local_fixture'/(label+'_qualification.json'),q)
    print(label,'parent match',q['parent_match_all_measured_states'],'all mechanics',q['all_local_states_mechanical_gates_passed'],flush=True)
    for r in states[-5:]:print(r['time'],r['maximum_penetration_mm'],r['mechanical_gates_passed'],r.get('parent_match_passed'),str(r['geometry_failure'])[:140],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');qualify(p.parse_args().label)
