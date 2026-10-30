"""Reconstruct actual historical evidence, with explicit missing-data boundaries."""
import json
from pathlib import Path
import re
import numpy as np
from metamaterial_eval.simulation.mesh_artifacts import artifact_root,resolve_manifest
from metamaterial_eval.simulation.nonlinear_diagnostics import parse_solver_log,export_csv
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.reporting import write_json

REPO=Path(__file__).resolve().parents[1];RUN=REPO/'experiments/pipeline_v0.6.4/run_001'


def main():
    for index in [1,2]:
        directory=artifact_root()/f'solver/v063/pilot_{index:03d}'
        log=(directory/'solver.out').read_text(errors='replace');parsed=parse_solver_log(log)
        receipt=json.loads((directory/'execution_receipt.json').read_text());manifest=json.loads((directory/'simulation_manifest.json').read_text())
        assert receipt['input_sha256']==file_hash(directory/'input.inp')==manifest['input_sha256']
        clocks=[r['preceding_wall_clock'] for r in parsed['completed_iterations'] if r['preceding_wall_clock']]
        seconds=[sum(int(v)*f for v,f in zip(t.split(':'),[3600,60,1])) for t in clocks]
        observed_differences=[(b-a)%86400 for a,b in zip(seconds,seconds[1:])]
        parsed.update(input_sha256=file_hash(directory/'input.inp'),solver_out_sha256=file_hash(directory/'solver.out'),geometry_sha256=manifest['source_geometry_sha256'],mesh_semantic_sha256=manifest['mesh_semantic_sha256'],model=manifest['model'],actual_process_status=receipt['status'],runtime_seconds=receipt['process']['runtime_seconds'],peak_tree_rss_bytes=receipt['process']['peak_tree_rss_bytes'],requested_first_strain=.0001,requested_first_displacement_mm=-.001024,
            inferred_initial_trial={'strain':.00005,'platen_travel_mm':.000512,'evidence':'TIME target / inherited NSUBST initial2; reconstructed prescription, NOT independently recorded trial telemetry'},
            observed_wall_stamp_differences_seconds=observed_differences,
            timing_scope='Differences between printed factorization-note wall stamps, second precision; not exact complete-iteration wall durations. CP means CPU time.',
            missing=['actual native trial-time/contact iteration file','contact point transitions and gaps','spatial residual snapshots','completed-substep monitor rows'],
            termination='Documented manual numerical-diagnosis stop' if index==1 else 'Registered 1200s timeout',
            conclusions={'force_nonconvergence':'OBSERVED','memory_exhaustion':'NOT_OBSERVED','negative_pivots':'NOT_OBSERVED_IN_LOGGED_FACTORIZATIONS','element_distortion':'NOT_REPORTED_BEFORE_STOP','cutback':'ZERO_REPORTED_BEFORE_STOP; iteration count below NEQIT30','chattering':'UNRESOLVED_HISTORICALLY','stiffness_condition_number':'NOT_MEASURED','soft_mode':'UNRESOLVED','large_iteration_cost':'SUPPORTED_BY_WALL_STAMPS'})
        write_json(RUN/f'historical_failure_forensics/attempt_{index:03d}_reconstruction.json',parsed)
        export_csv(RUN/f'historical_failure_forensics/attempt_{index:03d}_force.csv',parsed['force_evaluations'])
        export_csv(RUN/f'historical_failure_forensics/attempt_{index:03d}_iterations.csv',parsed['completed_iterations'])
        export_csv(RUN/f'historical_failure_forensics/attempt_{index:03d}_displacement.csv',parsed['displacement_evaluations'])
    mesh,manifest,where=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    # Analytic rigid motions [Tx,Ty,theta], not a full FE eigenanalysis.
    bottom=np.unique(mesh.boundary[mesh.boundary_groups=='bottom']);xy=mesh.nodes[bottom]
    rows=np.vstack([[1,0,-xy[:,1].min()],np.column_stack([np.zeros(len(xy)),np.ones(len(xy)),xy[:,0]])])
    records={'scope':'Analytical constraint rank on planar rigid-motion subspace only; not flexible-mode/eigenvalue qualification',
        'one_UX_anchor_and_distributed_closed_bottom_normal_rank':int(np.linalg.matrix_rank(rows)),
        'singular_values':np.linalg.svd(rows,compute_uv=False).tolist(),
        'one_UX_anchor_if_both_platens_open_rank':1,'uncontrolled_rigid_modes_when_both_open':['Ty','rotation combined with Tx at anchor'],
        'closed_constraints':'Geometrically distributed normal constraints suppress rigid modes when active; actual per-iteration activation must still be measured',
        'full_FE_eigenanalysis':'NOT_EXECUTED; outside bounded need',
        'specimen_UY_constraints':'NONE; no additional restraints introduced',
        'soft_deformation_modes':'UNRESOLVED for full specimen; no inference from connectivity alone'}
    write_json(RUN/'constraint_analysis/rigid_motion_subspace.json',records)
    print('Historical native log reconstructions and analytical rigid-motion rank complete')


if __name__=='__main__':main()
