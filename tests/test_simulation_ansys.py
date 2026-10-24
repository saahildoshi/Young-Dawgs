"""Solver-independent construction tests; analytical controls are not ANSYS runs."""
from dataclasses import replace
import json
import numpy as np
import pytest
from shapely import box
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.mesh_generation import generate_mesh
from metamaterial_eval.simulation.contact_setup import platen_plan,require_internal_contact
from metamaterial_eval.simulation.ansys_adapter import build_deck,lint_transfer,write_input
from metamaterial_eval.simulation.solver_execution import classify_log,execute,discover_solver
from metamaterial_eval.simulation.mechanical_metrics import compression_metrics,effective_stiffness,selected_snapshots,convergence_report
from metamaterial_eval.simulation.postprocessing import postprocess,validate_output_hashes
from metamaterial_eval.simulation.reporting import write_json


@pytest.fixture
def model():
    pytest.importorskip('gmsh')
    c=CompressionConfig(width=1,height=1,boundary_size=.1,bulk_size=.2)
    return generate_mesh(box(0,0,1,1),c),c


@pytest.mark.parametrize('mode,keyopt',[('plane_stress',3),('plane_strain',2)])
@pytest.mark.parametrize('contact',[False,True])
def test_apdl_static_transfer_roundtrip(model,mode,keyopt,contact):
    m,c=model;c=replace(c,mode=mode)
    deck,manifest=build_deck(m,c,contact=contact)
    assert f'KEYOPT,1,3,{keyopt}' in deck and 'KEYOPT,1,1,1' in deck
    assert 'NLGEOM,ON' in deck and 'AUTOTS,ON' in deck
    assert f'D,{manifest["controls"]["top"]},UY,-0.02' in deck if contact else 'D,ALL,UY,-0.02' in deck
    assert lint_transfer(deck,m,c,contact=contact)['ansys_import']=='NOT_VERIFIED'
    assert manifest['status']=='DRAFT_UNVERIFIED'
    assert manifest['internal_self_contact']=='UNQUALIFIED_NOT_CONFIGURED'


def test_contact_surfaces_and_direction(model):
    m,c=model;plan=platen_plan(m,c)
    assert plan['top']['target_normal']==[0,-1] and plan['bottom']['target_normal']==[0,1]
    assert plan['top']['initial_gap_mm']==0 and not plan['bottom']['bonded']
    broken=replace(m,boundary_groups=np.where(m.boundary_groups=='top','external',m.boundary_groups))
    with pytest.raises(ValueError,match='Missing top'):platen_plan(broken,c)
    edge=m.boundary.copy();edge[:,[0,1]]=edge[:,[1,0]]
    with pytest.raises(ValueError,match='normal'):platen_plan(replace(m,boundary=edge),c)


def test_missing_or_changed_contact_transfer_detected(model):
    m,c=model;deck,_=build_deck(m,c)
    with pytest.raises(ValueError,match='Missing contact'):lint_transfer(deck.replace('ET,3,CONTA172','! omitted'),m,c)
    with pytest.raises(ValueError,match='Material'):lint_transfer(deck.replace('MP,EX,1,1000','MP,EX,1,500'),m,c)
    with pytest.raises(ValueError,match='connectivity'):lint_transfer(deck.replace('EN,1,','EN,1,999,',1),m,c)


@pytest.mark.parametrize('evidence',[{}, {'status':'DEFINED'},{'status':'SOLVER_VERIFIED','nonadjacent_only':True,'engaged_in_benchmark':False}])
def test_internal_contact_cannot_be_inferred(evidence):
    with pytest.raises(RuntimeError):require_internal_contact(evidence)


@pytest.mark.parametrize('log,code,rst,csv,status',[
    ('license checkout failed',0,True,True,'LICENSE_FAILURE'),
    ('*** ERROR ***',0,True,True,'SOLVER_ERROR_OR_NONCONVERGENCE'),
    ('solution not converged',0,True,True,'SOLVER_ERROR_OR_NONCONVERGENCE'),
    ('',1,False,False,'SOLVER_PROCESS_FAILURE'),
    ('',0,False,False,'MISSING_SOLVER_OUTPUT'),
    ('',0,True,True,'EXECUTED_PENDING_IMPORT_CONTACT_AND_NUMERIC_VALIDATION')])
def test_solver_failure_classification(log,code,rst,csv,status):
    assert classify_log(log,code,rst,csv)==status


def test_missing_solver_and_immutable_outputs(tmp_path,model):
    m,c=model;source=tmp_path/'input';write_input(source,m,c)
    assert (source/'extract_fields.mac').exists()
    state=execute(source,tmp_path/'execution',executable=tmp_path/'absent.exe')
    assert state['status']=='MISSING_ANSYS_INSTALLATION'
    assert state['license']=='NOT_TESTED_NO_SOLVER'
    with pytest.raises(FileExistsError):execute(source,tmp_path/'execution')
    with pytest.raises(FileExistsError):write_input(source,m,c)


def test_analytical_sign_units_force_balance_and_modulus():
    # Explicit independent analytical control: E=1000 MPa, W=H=b=1 mm.
    c=CompressionConfig(width=1,height=1)
    strain=np.array([.001,.002,.005]);force=1000*strain
    r=compression_metrics(-strain,force,-force,c)
    np.testing.assert_allclose(r['engineering_compression_strain'],strain)
    np.testing.assert_allclose(r['nominal_compression_stress_MPa'],force)
    assert r['force_balance_pass']
    assert effective_stiffness(strain,force,1000)['value_MPa']==pytest.approx(1000)
    assert not compression_metrics(-strain,force,-force*.8,c)['force_balance_pass']
    with pytest.raises(ValueError,match='sign'):compression_metrics(strain,force,-force,c)
    with pytest.raises(ValueError,match='Nonfinite'):compression_metrics(-strain,[np.nan]*3,-force,c)
    assert effective_stiffness([.02],[20],1000)['value_MPa'] is None


def test_envelope_stress_and_plane_strain_unit_depth():
    c=CompressionConfig(width=2,height=4,thickness=.5)
    r=compression_metrics([-.04],[10],[-10],c)
    assert r['engineering_compression_strain'][0]==pytest.approx(.01)
    assert r['nominal_compression_stress_MPa'][0]==10
    c=replace(c,mode='plane_strain',thickness=1)
    assert c.manifest()['force_basis']=='N_per_mm_depth'


def test_only_achieved_snapshots():
    result=selected_snapshots([.0005,.005,.01])
    assert result['first_nonzero']==0 and result['one_percent']==2
    assert result['two_percent'] is None and result['last_converged']==2


def test_convergence_rejects_unexecuted_or_changed_models():
    assert convergence_report([])['status']=='NOT_QUALIFIED'
    a={'validity':'VALID_SOLVER_MEASUREMENTS','model_fingerprint':'same','strain':[.005,.01],'stress':[1,2]}
    assert convergence_report([a,a,a])['status']=='PASS_GLOBAL_RESPONSE'
    assert convergence_report([a,a,{**a,'model_fingerprint':'different'}])['status']=='NOT_QUALIFIED'
    assert convergence_report([a,a,{**a,'validity':'SYNTHETIC'}])['status']=='NOT_QUALIFIED'
    assert convergence_report([a,a,{**a,'stress':[2,4]}])['status']=='HOLD_GLOBAL_RESPONSE'


def test_missing_results_quarantined(tmp_path):
    source=tmp_path/'source';source.mkdir()
    write_json(source/'solver_status.json',{'status':'NOT_EXECUTED'})
    report=postprocess(source,tmp_path/'results')
    assert report['llm_performance_eligible'] is False
    assert report['effective_stiffness'] is None
    assert (tmp_path/'results/QUARANTINE.json').exists()


def test_modified_receipt_cannot_authenticate_outputs(tmp_path):
    with pytest.raises(ValueError,match='actual solver'):validate_output_hashes(tmp_path,{'status':'NOT_EXECUTED'})
    with pytest.raises(ValueError,match='output'):validate_output_hashes(tmp_path,{'status':'EXECUTED','solver_version':'test_control'})


def test_failed_refinement_blocks_pilot_input_before_loading(tmp_path):
    from metamaterial_eval.simulation.ansys_adapter import prepare_pilot_input
    run=tmp_path/'run';level=run/'level_01';level.mkdir(parents=True)
    write_json(run/'FAILURE.json',{'stage':'mesh_quality','level':2})
    with pytest.raises(RuntimeError,match='recorded mesh-study failure'):
        prepare_pilot_input(level,tmp_path/'pilot',tmp_path)
