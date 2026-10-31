"""Read-only geometry qualification of the independently solved nodal fixture."""
import numpy as np
from scripts.v066_restart import BASE,RUN,load
from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.deformed_boundaries import screen
from metamaterial_eval.simulation.general_contact_results import read_table
from metamaterial_eval.simulation.general_contact_output import GC_COLUMNS
from metamaterial_eval.simulation.nodal_contact_geometry import explain_nodal_pairs
from metamaterial_eval.simulation.reporting import write_json,mesh_hash
from metamaterial_eval.simulation.solver_execution import file_hash


def main():
    q=load(RUN/'internal_contact/NODAL_FIXTURE_QUALIFICATION.json')
    assert q['status']=='PASS_ACTUAL_NODAL_GC_INTERFACE_FORCE_PEN_MAPPING'
    with np.load(BASE/'internal_fixture_geometry_003/mesh.npz') as z:m=Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])
    assert mesh_hash(m)==load(RUN/'internal_contact/fixture_manifest_003.json')['mesh_semantic_sha256']
    d=BASE/'internal_fixture_enabled_003_post001';receipt=load(d/'execution_receipt.json')
    hashes={name:file_hash(d/name) for name in ['direct_displacements.csv','check_gc_fields.csv']}
    assert all(digest==receipt['process']['artifacts'][name]['sha256'] for name,digest in hashes.items())
    u=read_table(d/'direct_displacements.csv',['node','ux_mm','uy_mm']);xy=m.nodes+u[:,1:3]
    overlap=screen(xy,m.boundary,m.boundary_groups,original=m.nodes,record_limit=100000)
    fields=read_table(d/'check_gc_fields.csv',GC_COLUMNS);by_nodes={tuple(e+1):i for i,e in enumerate(m.boundary)}
    lookup={by_nodes[tuple(f[10:13].astype(int))]:f for f in fields};eids=np.zeros(len(m.boundary),dtype=int)
    for edge,f in lookup.items():eids[edge]=int(f[0])
    try:
        if overlap['orientation_inverted_loops'] or overlap['edges_exceeding_requested_tolerance']:raise ValueError('Fixture contour orientation/approximation failed')
        explanations=explain_nodal_pairs(overlap,eids,lookup,m,xy);status='PASS_ACTUAL_NODAL_FIXTURE_BOUNDED_CONTACT_GEOMETRY';failure=None
    except ValueError as exc:explanations=[];status='HOLD';failure=str(exc)
    result={'status':status,'radius_mm':5e-6,'maximum_propagated_contact_neighborhood_diameter_mm':1e-5,
        'candidate_records':overlap['suspicious_pair_count'],'explanations':explanations,'failure':failure,
        'native_fixture_force_qualification_sha256':file_hash(RUN/'internal_contact/NODAL_FIXTURE_QUALIFICATION.json'),
        'native_readback_receipt_sha256':file_hash(d/'execution_receipt.json'),'actual_native_field_hashes':hashes,
        'scope':'Original direct engaged target-facet rule retained. Every other pair strictly separated or localized at actual positive-pressure endpoint constraint. No extrapolated contact force or relaxed pen allowance.'}
    write_json(RUN/'internal_contact/NODAL_FIXTURE_GEOMETRY_QUALIFICATION_002.json',result);print(status,failure,flush=True)


if __name__=='__main__':main()
