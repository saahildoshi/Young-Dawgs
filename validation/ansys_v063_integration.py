"""Actual local solver/mesh evidence only. Missing evidence fails, never mocks/skips."""
import json
from pathlib import Path
import numpy as np
from metamaterial_eval.simulation.mesh_artifacts import artifact_root,resolve_manifest,HISTORICAL
from metamaterial_eval.simulation.microstructure_import import read_cdb
from metamaterial_eval.simulation.solver_execution import file_hash

RUN=Path(__file__).resolve().parents[1]/'experiments/pipeline_v0.6.3/run_001'
BASE=artifact_root()/'solver/v063'


def test_actual_historical_mesh_identity_reproduction():
    mesh,record,_=resolve_manifest(RUN/'mesh_reproduction/attempt_002/artifact_manifest.json')
    assert record['semantic_sha256']==HISTORICAL and len(mesh.nodes)==2766505
    assert len(mesh.triangles)==1261670 and record['archive_bytes_read_and_CRC_verified']


def test_actual_complete_MAPDL_CDB_roundtrip():
    mesh,record,_=resolve_manifest(RUN/'mesh_reproduction/attempt_002/artifact_manifest.json')
    path=BASE/'import_001/imported.cdb'
    evidence=json.loads((RUN/'import_only/attempt_001/validation/import_validation.json').read_text())
    assert file_hash(path)==evidence['solver_archive_sha256']
    nodes,tri,attrs,groups=read_cdb(path,len(mesh.nodes),len(mesh.triangles))
    assert np.array_equal(tri,mesh.triangles) and np.all(attrs==1)
    assert np.allclose(nodes,mesh.nodes,rtol=0,atol=1e-11)
    assert evidence['pores_from_imported_connectivity']==412 and evidence['actual_mesh_validation']['accepted']
    for label in set(mesh.boundary_groups):
        assert np.array_equal(groups[label.upper()+'_FACE']['ids'],np.unique(mesh.boundary[mesh.boundary_groups==label])+1)


def test_actual_assembly_resource_diagnostic_is_not_solver_acceptance():
    record=json.loads((BASE/'assembly_001/resource_assessment.json').read_text())
    assert record['status']=='ASSEMBLY_ONLY_COMPLETE_NOT_SOLVED'
    assert record['process']['returncode']==0 and record['matrix_file_bytes']>100000000
    assert record['process']['artifacts']['compression.full']['sha256']==file_hash(BASE/'assembly_001/compression.full')
    assert record['factorization_memory']=='NOT_ESTABLISHED_BY_WRFULL'


def test_actual_contact_sensitivity_and_rejected_penalty_candidate():
    for index in range(1,5):
        directory=RUN/f'contact_sensitivity/candidate_{index:03d}'
        report=json.loads((directory/'contact_points/contact_point_validation.json').read_text())
        assert file_hash(directory/'generated/execution/compression.rst')==report['source_RST_sha256']
        assert report['maximum_contact_force_pilot_magnitude_difference_relative']<.01
        assert (report['maximum_stored_endpoint_penetration_mm']<=1e-5)==(index!=3)
    selected=RUN/'contact_sensitivity/candidate_004/generated'
    assert file_hash(selected/'execution/history.csv')==file_hash(selected/'repeat/history.csv')


def test_actual_corrected_platen_setup():
    record=json.loads((BASE/'contact_setup_002/contact_setup_validation.json').read_text())
    assert record['status']=='CONTACT_SETUP_PASS' and record['both_pairs_initially_closed']
    assert record['no_specimen_UY_constraints']
    assert file_hash(BASE/'contact_setup_002/contact_model.db')==record['process']['artifacts']['contact_model.db']['sha256']


def test_actual_checkpoint_driver_control_has_increasing_load_steps():
    record=json.loads((BASE/'staged_control_solve_003/execution_receipt.json').read_text())
    assert record['process']['returncode']==0
    assert sorted({a for a,b in record['converged_steps']})==[1,2,3]
    for index in [1,2,3]:
        assert float((BASE/f'staged_control_solve_003/stage{index:03d}_gate.txt').read_text().split(',')[0])==0


def test_actual_microstructure_converged_response_and_fields():
    report=json.loads((RUN/'mechanical_results/attempt_002/mechanical_summary.json').read_text())
    assert report['actual_valid_stages'],'No microstructure checkpoint converged; genuine physics acceptance check fails'
    assert not report['unsupported_output_queries']
    assert report['result_RST_sha256']==file_hash(BASE/'pilot_002/compression.rst')
    assert report['stage_fields'][0]['fields']['actual_nodes']==2766505
    assert all(r['reaction_balance_relative']<=.01 for r in report['actual_valid_stages'])
