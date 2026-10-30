"""One exact-source lower-cost mesh candidate; never overwrite the fine mesh."""
from dataclasses import replace,asdict
from pathlib import Path
import time
import numpy as np
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.geometry_adapter import authenticate_fixture
from metamaterial_eval.simulation.mesh_generation import generate_mesh,save_mesh
from metamaterial_eval.simulation.mesh_remediation import POLICY_B
from metamaterial_eval.simulation.mesh_validation import validate_mesh,feature_resolution
from metamaterial_eval.simulation.reporting import write_json,mesh_hash
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import REPO,RUN,BASE,PLAN,load


def main():
    registered=load(PLAN)['mesh_candidate'];start=time.perf_counter()
    cfg=replace(CompressionConfig(),boundary_size=registered['boundary_size_mm'],bulk_size=registered['bulk_size_mm'])
    geometry,_,provenance=authenticate_fixture(REPO,cfg)
    local=BASE/'mesh_candidate_001';local.mkdir(parents=True,exist_ok=False)
    mesh=generate_mesh(geometry,cfg,policy=POLICY_B);save_mesh(mesh,local/'mesh.npz')
    quality,distribution=validate_mesh(mesh,geometry,cfg)
    features=feature_resolution(mesh,provenance['source_only_solid_probes'],cfg)
    np.savez_compressed(local/'quality.npz',quality=distribution)
    result={'schema':'young-dawgs-v0.6.6-smaller-mesh','status':'GEOMETRY_GATES_PASS__MECHANICS_NOT_YET_TESTED' if quality['accepted'] and features['accepted'] else 'REJECTED_ORIGINAL_GEOMETRY_GATES',
        'mesh_semantic_sha256':mesh_hash(mesh),'source_geometry_sha256':provenance['geometry_sha256'],
        'mesh_archive_sha256':file_hash(local/'mesh.npz'),'mesh_archive':str(local/'mesh.npz'),
        'nodes':len(mesh.nodes),'TRI6':len(mesh.triangles),'config':cfg.manifest(),'meshing_policy':asdict(POLICY_B),
        'quality':quality,'features':features,'fine_reference_TRI6':1261670,'element_reduction_factor':1261670/len(mesh.triangles),
        'comparison_tolerance_frozen':registered['benchmark_relative_force_tolerance'],
        'fine_observed_minimum_chord_elements':7,'feature_rule':'Original registered criterion>=3; fine observed>=7 is not silently asserted for this candidate',
        'mechanical_mesh_convergence':'UNQUALIFIED','elapsed_seconds':time.perf_counter()-start}
    write_json(RUN/'mesh_strategy/candidate_001.json',result)
    print(result['status'],'nodes',result['nodes'],'TRI6',result['TRI6'],'angle',quality['min_angle_deg'],'chord',features['minimum_elements_across'],flush=True)


if __name__=='__main__':main()
