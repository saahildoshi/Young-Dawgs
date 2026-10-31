"""Localize retained native residual snapshots without changing the parent."""
from pathlib import Path
import json
import numpy as np
from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest, artifact_root
from metamaterial_eval.simulation.nonlinear_diagnostics import localize_residual, parse_contact, contact_summary
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.deformed_boundaries import trace_loops
from scripts.v067_audit import REPO, RUN


def main():
    mesh, _, _ = resolve_manifest(REPO / 'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json', root=Path.home() / 'YoungDawgs-Artifacts')
    base = artifact_root() / 'solver/v066'
    parent = base / 'fine_nodal_recovery01_001'
    u = np.load(base / 'fine_nodal_recovery01_001_qualified001/state006/native_displacement.npy', mmap_mode='r')
    edges = np.load(base / 'fine_gc_setup_001/gc_edge_indices.npy')
    topology = np.loadtxt(base / 'fine_gc_setup_001/gc_topology.csv', delimiter=',', skiprows=1).astype(np.int64)
    boundary_to_eid = np.zeros(len(mesh.boundary), dtype=np.int64)
    boundary_to_eid[edges] = topology[:, 0]
    loops=trace_loops(mesh.boundary)
    loop_for_edge=np.empty(len(mesh.boundary),dtype=int)
    for i,loop in enumerate(loops):loop_for_edge[loop]=i
    faces=[]
    for i in [27837,27838,28504,28505,28506]:
        faces.append({'original_boundary_index_zero_based':i,'original_mesh_loop_id':int(loop_for_edge[i]),
                      'group':str(mesh.boundary_groups[i]),'native_GC_skin':int(boundary_to_eid[i]),
                      'original_nodes_one_based':(mesh.boundary[i]+1).tolist(),
                      'original_quadratic_coordinates_mm':mesh.nodes[mesh.boundary[i]].tolist(),
                      'accepted_quadratic_coordinates_mm':u[mesh.boundary[i],3:5].tolist(),
                      'section':4,'section_evidence':'Actual parent_section_probe_001 native readback; not inferred from skin number'})
    write_json(RUN/'contact_onset/ORIGINAL_BOUNDARY_LOOPS_AND_FACES.json',{'mesh_boundary_loop_count':len(loops),'faces':faces})
    for name in ['compression.nr001', 'compression.nr002']:
        result = localize_residual(parent / name, mesh.nodes, mesh.boundary, mesh.boundary_groups, top_count=64)
        for node in result['top_residual_nodes']:
            i = node['node'] - 1
            bs = np.flatnonzero(np.any(mesh.boundary == i, axis=1))
            node.update(accepted_parent_xy_mm=u[i, 3:5].tolist(), accepted_parent_U_mm=u[i, :2].tolist(),
                        boundary_indices_zero_based=bs.tolist(), original_mesh_loop_ids=loop_for_edge[bs].tolist(), general_contact_skin_ids=boundary_to_eid[bs].tolist())
        write_json(RUN / 'contact_onset' / (name + '.json'), result)
        print(name, result['pseudo_time'], result['iteration'], json.dumps(result['top_residual_nodes'][:6]), flush=True)
    contact = parse_contact((parent / 'compression.cnd').read_text(encoding='utf-8'))
    write_json(RUN / 'contact_onset/NATIVE_CONTACT_DIAGNOSTICS.json', {'summary': contact_summary(contact['records'], (2, 3, -4)), 'records': contact['records'], 'issues': contact['issues']})


if __name__ == '__main__':
    main()
