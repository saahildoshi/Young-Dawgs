"""Prospective parent-match and local-contact gates for the expanded original fixture."""
import argparse
import numpy as np

from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.element_quality import quadratic_mapping
from metamaterial_eval.simulation.deformed_boundaries import screen
from metamaterial_eval.simulation.quadratic_separation import certify_separated
from metamaterial_eval.simulation.general_contact_results import explain_contact_pairs
from metamaterial_eval.simulation.microstructure_results import unsupported_result_queries
from scripts.v067_qualify_fixture import table
from scripts.v068_common import BASE,RUN,read,write_json,file_hash


def qualify(label):
    source=BASE/label;post=BASE/(label+'_post1_002');fixture=BASE/'track_A_expanded_fixture_001'
    provenance=read(post/'simulation_manifest.json');r=read(post/'execution_receipt.json')
    if (file_hash(source/'compression.rst')!=provenance['source_RST_sha256'] or
        file_hash(source/'initial.db')!=provenance['source_database_sha256'] or
        file_hash(source/'execution_receipt.json')!=provenance['source_receipt_sha256'] or
        file_hash(post/'input.inp')!=provenance['input_sha256'] or
        r['solver_version']!='2024 R1' or r['process']['returncode']!=0 or
        unsupported_result_queries((post/'solver.out').read_text(errors='replace'))):
        raise ValueError('Altered source or unsupported native field query')
    spec=read(fixture/'fixture_manifest.json');manifest=read(source/'simulation_manifest.json')
    with np.load(fixture/'mesh.npz',allow_pickle=False) as z:
        mesh=Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])
        original=z['original_nodes_one_based'];cut=z['cut_nodes_zero_based']
    if (file_hash(fixture/'mesh.npz')!=spec['mesh_archive_sha256'] or
        file_hash(fixture/'measured_displacements.npy')!=spec['history_array_sha256']):
        raise ValueError('Local original-mesh extraction changed')
    topo=table(source/'gc_topology.csv',6).astype(int)
    by_nodes={tuple(sorted(edge+1)):i for i,edge in enumerate(mesh.boundary)}
    eids=np.zeros(len(mesh.boundary),dtype=int)
    for row in topo:
        index=by_nodes[tuple(sorted(row[1:4]))]
        if eids[index]:raise ValueError('Duplicate original physical face skin')
        eids[index]=row[0]
    physical=mesh.boundary_groups!='artificial_cut'
    if not np.array_equal(eids>0,physical):raise ValueError('Artificial cut or missing GC skin')
    source_states=read(source/'execution_receipt.json')['converged_steps']
    measured=np.load(fixture/'measured_displacements.npy',mmap_mode='r')
    core=np.linalg.norm(mesh.nodes-np.array([1.97,10.22]),axis=1)<.12
    core[cut]=False
    states=[]
    for state in provenance['states']:
        prefix=post/state['prefix'];key=(state['load_step'],state['substep'])
        if list(key) not in source_states:raise ValueError('POST1 state not natively converged')
        native_time=table(prefix.with_name(prefix.name+'_time.csv'),1)[0,0]
        u=table(prefix.with_name(prefix.name+'_displacements.csv'),3)
        s=table(prefix.with_name(prefix.name+'_stress.csv'),5)
        contact=table(prefix.with_name(prefix.name+'_gc_fields.csv'),14)
        forces=table(prefix.with_name(prefix.name+'_reactions.csv'),3)
        if (len(u)!=len(mesh.nodes) or not np.array_equal(u[:,0],np.arange(1,len(u)+1)) or
            len(forces)!=len(cut)+1 or abs(native_time-state['time'])>1e-8):
            raise ValueError('Incomplete or inconsistent native state')
        xy=mesh.nodes+u[:,1:3]
        mapping=quadratic_mapping(xy[mesh.triangles])
        positive=bool(mapping['positive_over_reference_triangle'].all())
        overlap=screen(xy,mesh.boundary,mesh.boundary_groups,original=mesh.nodes,record_limit=100000)
        pressure=float(contact[:,2:5].max()) if len(contact) else 0
        closed=int(np.sum(contact[:,1]>=2)) if len(contact) else 0
        penetration=max(0,float(contact[:,5:7].max())) if len(contact) else 0
        force_error=float(np.linalg.norm(forces[:,1:3].sum(axis=0))/max(np.linalg.norm(forces[:,1:3],axis=1).sum(),1e-12))
        geometry_error=None
        try:
            if overlap['orientation_inverted_loops'] or overlap['edges_exceeding_requested_tolerance']:
                raise ValueError('Boundary loop or quadratic chord tolerance failed')
            lookup={int(row[0]):row for row in contact}
            for pair in overlap['examples']:
                a,b=pair['edge_a'],pair['edge_b']
                if certify_separated(xy[mesh.boundary[a]],xy[mesh.boundary[b]])['passed']:continue
                explain_contact_pairs({**overlap,'suspicious_pair_count':1,'examples':[pair]},eids,
                                      {a:lookup.get(eids[a]),b:lookup.get(eids[b])})
        except (ValueError,KeyError,TypeError) as exc:geometry_error=str(exc)
        record={**state,'native_time':float(native_time),'scope':'LOCAL_DIAGNOSTIC_ONLY',
                'positive_all_TRI6':positive,'max_endpoint_penetration_mm':penetration,
                'max_native_pressure_MPa':pressure,'signed_reaction_residual_relative':force_error,
                'closed_GC_skins':closed,
                'two_sided_interface_force':'PENDING_NATIVE_PROOF' if closed else 'NOT_APPLICABLE_OPEN',
                'boundary_candidates':overlap['suspicious_pair_count'],'geometry_failure':geometry_error,
                'local_mechanical_gates_passed':bool(positive and penetration<=1e-5 and force_error<=.01 and geometry_error is None and not closed),
                'extrapolated_cut_motion':state['load_step']>len(measured)}
        if state['load_step']<=len(measured):
            snapshot=spec['source_snapshots'][state['load_step']-1]
            parent=measured[state['load_step']-1]
            error=u[:,1:3]-parent
            record['cut_U_max_error_mm']=float(abs(error[cut]).max())
            record['core_U_RMS_relative']=float(np.sqrt(np.mean(error[core]**2))/max(np.linalg.norm(parent[core],axis=1).max(),1e-12))
            ids=np.load(snapshot['directory']+'/corner_node_ids.npy',mmap_mode='r')
            values=np.load(snapshot['directory']+'/native_corner_stress_strain.npy',mmap_mode='r')
            expected=values[np.searchsorted(ids,original[s[:,0].astype(int)-1])]
            mask=core[s[:,0].astype(int)-1]
            errors=np.sqrt(np.mean((s[mask,1:]-expected[mask])**2,axis=0))/np.maximum(np.sqrt(np.mean(expected[mask]**2,axis=0)),1e-12)
            record['core_SYY_SEQV_EYY_EXX_RMS_relative']=errors.tolist()
            record['parent_match_passed']=bool(record['cut_U_max_error_mm']<=1e-10 and
                                               record['core_U_RMS_relative']<=.02 and errors.max()<=.1)
        states.append(record)
    result={'schema':'young-dawgs-v068-expanded-parent-comparison','label':label,
            'native_POST1_receipt_sha256':file_hash(post/'execution_receipt.json'),
            'native_physical_face_count':int(physical.sum()),'native_gc_skin_count':len(topo),
            'parent_match_all_measured_states':all(s['parent_match_passed'] for s in states if 'parent_match_passed' in s),
            'local_mechanical_gates_all_states':all(s['local_mechanical_gates_passed'] for s in states),
            'full_model_strain_qualification':False,'states':states}
    result['status']='PASS_LOCAL_DIAGNOSTIC_ONLY' if result['parent_match_all_measured_states'] and result['local_mechanical_gates_all_states'] else 'HOLD_LOCAL_CONTEXT_OR_CONTACT'
    write_json(RUN/'track_A_local_fixture'/(label+'_qualification.json'),result)
    print(label,result['status'],'parent',result['parent_match_all_measured_states'],
          'local',result['local_mechanical_gates_all_states'],flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');qualify(p.parse_args().label)
