"""Checks against actual licensed v241 evidence, including rejected solutions."""
import json
import numpy as np
import pytest
from scripts.v067_fixture import BASE, RUN
from scripts.v067_audit import REPO
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest
from pathlib import Path


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


@pytest.mark.parametrize('name',['compression.rdb','compression.ldhi','compression.r001','compression.rst'])
def test_immutable_full_parent_native_bytes_match_registered_hash(name):
    a=read(RUN/'audit/INITIAL_AUTHENTICATION.json')
    p=Path(a['parent_source'])/name
    assert file_hash(p)==a['parent_native_files'][name]['sha256']


def test_fresh_full_parent_POST1_matches_qualified_reactions_and_fields():
    q=read(RUN/'restart_validation/PARENT_NATIVE_READBACK.json')
    assert q['status']=='PASS'
    assert q['sampled_U_S_EPEL_match_existing_qualified_fields']
    assert all(q['all_four_immutable_native_files_reauthenticated_after_readback'].values())


def test_local_mesh_is_an_exact_subset_of_original_TRI6():
    z=np.load(BASE/'source_fixture_001/mesh.npz')
    m,_,_=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    nodes=z['original_nodes_one_based']-1; elements=z['original_elements_one_based']-1
    assert np.array_equal(z['nodes'],m.nodes[nodes])
    assert np.array_equal(nodes[z['triangles']],m.triangles[elements])


@pytest.mark.parametrize('label',['local_baseline_001','local_baseline_002','local_fkn10_001','local_baseline_003','local_fkn10_002','local_fkn1_001','local_projection3_001','local_fkn1_neqit64_001'])
def test_native_solve_has_actual_v241_log_and_bound_input(label):
    d=BASE/label;r=read(d/'execution_receipt.json')
    assert r['input_sha256']==file_hash(d/'input.inp')
    assert 'Ansys MAPDL 2024 R1' in (d/'solver.out').read_text(encoding='utf-8',errors='replace')
    assert r['process']['runtime_seconds']>0
    assert (d/'compression.rst').is_file()


@pytest.mark.parametrize('label',['local_baseline_003','local_fkn10_002','local_fkn1_001','local_projection3_001'])
def test_corrected_fixture_retains_every_physical_face_and_parent_section(label):
    t=np.loadtxt(BASE/label/'gc_topology.csv',delimiter=',',skiprows=1).astype(int)
    z=np.load(BASE/'source_fixture_001/mesh.npz')
    expected={tuple(sorted(e+1)) for e in z['boundary'][z['boundary_groups']!='artificial_cut']}
    assert {tuple(sorted(e)) for e in t[:,1:4]}==expected
    assert len(t)==len(expected)==498
    assert np.all(t[:,4:6]==4)


@pytest.mark.parametrize('label',['local_baseline_003','local_fkn10_002','local_fkn1_001'])
def test_nodal_variants_preserve_real_nonconvergence(label):
    r=read(BASE/label/'execution_receipt.json')
    assert r['process']['returncode']!=0
    assert 'Solution not converged' in (BASE/label/'compression.err').read_text(encoding='utf-8')
    assert read(BASE/label/'nonlinear_telemetry.json')['cutback_events']


def test_projection_convergence_does_not_override_geometry_rejection():
    assert read(BASE/'local_projection3_001/execution_receipt.json')['process']['returncode']==0
    q=read(RUN/'local_fixture/local_projection3_001_qualification.json')
    assert not q['all_local_states_mechanical_gates_passed']
    assert q['states'][-1]['geometry_failure']
    assert q['states'][-1]['maximum_penetration_mm']>0
    assert not q['full_model_strain_qualification']


@pytest.mark.parametrize('label',['local_baseline_003','local_projection3_001','local_fkn1_neqit64_001'])
def test_both_interface_sides_transmit_equal_opposite_native_solid_forces(label):
    q=read(RUN/'local_fixture'/(label+'_interface_force.json'))['states'][-1]
    f=np.array(q['solid_restoring_forces_A_B_N'])
    assert np.linalg.norm(f,axis=1).min()>1e-6
    assert q['opposition_passed'] and q['opposition_relative']<.01
    assert q['platen_fraction']<.01
    assert f[0,0]<0<f[1,0]


def test_actual_native_restart_preserves_one_success_and_next_failure():
    d=BASE/'local_fkn1_neqit64_001'
    p=read(d/'restart_provenance.json')
    assert p['source_never_modified']
    assert 'ANTYPE,STATIC,REST,18,8,CONTINUE' in (d/'input.inp').read_text(encoding='utf-8')
    r=read(d/'execution_receipt.json')
    assert r['converged_steps']==[[18,9]] and r['process']['returncode']!=0
    q=read(RUN/'local_fixture/local_fkn1_neqit64_001_qualification.json')['states']
    assert len(q)==1 and q[0]['mechanical_gates_passed'] and q[0]['extrapolated']
    assert q[0]['maximum_penetration_mm']<=1e-5


def test_last_full_parent_match_is_reported_without_hiding_early_mismatch():
    q=read(RUN/'local_fixture/local_baseline_003_qualification.json')
    assert not q['parent_match_all_measured_states']
    assert q['states'][14]['parent_match_passed']
    assert not q['states'][0]['parent_match_passed']
