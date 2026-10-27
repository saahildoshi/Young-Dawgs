"""Solver-independent controls only. No test substitutes for licensed integration."""
import csv
import json
from pathlib import Path
import pytest
from metamaterial_eval.simulation.ansys_qualification import (
    release_id,analytical_reference,prepare_rectangle,environment_report,
    checked_qualification,evidence_token,qualify,release_compatible)
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.solver_execution import discover_solver,classify_log,execute
from metamaterial_eval.simulation.postprocessing import read_numeric_csv


@pytest.mark.parametrize('text,expected',[('RELEASE2026 R1','2026 R1'),('v261','2026 R1'),
    ('252','2025 R2'),('2026 R2','2026 R2'),('unknown',None),(None,None)])
def test_actual_release_format_requires_recognized_version(text,expected):
    assert release_id(text)==expected


@pytest.mark.parametrize('actual,expected,compatible',[
    ('2026 R1','261',True),('2026 R2','261',False),('unrecognized','261',False)])
def test_incorrect_solver_release_rejected(actual,expected,compatible):
    assert release_compatible(actual,expected) is compatible


def test_explicit_executable_selector_is_detection_only(tmp_path,monkeypatch):
    executable=tmp_path/'UNIT_TEST_CONTROL.exe';executable.write_text('not a solver; never executed')
    monkeypatch.setenv('ANSYS_EXECUTABLE',str(executable))
    assert discover_solver()==executable.resolve()


def test_missing_installation_does_not_claim_missing_license(tmp_path,monkeypatch):
    monkeypatch.setattr('metamaterial_eval.simulation.ansys_qualification.discover_solver',lambda *_:None)
    r=environment_report(tmp_path/'environment',smoke=True)
    assert r['status']=='ANSYS_EXECUTION_BLOCKED'
    assert r['license']=='NOT_TESTED_NO_SOLVER'
    assert r['actual_release'] is None and r['solver_execution']=='NOT_EXECUTED'


@pytest.mark.parametrize('control_log',['ANSYS LICENSE MANAGER ERROR: license unavailable',
    'No licenses available','License checkout failed'])
def test_license_failure_log_classification_is_only_unit_control(control_log):
    assert classify_log(control_log,1,False,False)=='LICENSE_FAILURE'


def test_analytical_force_is_labelled_not_solver_measurement():
    r=analytical_reference(CompressionConfig(),[.005])
    assert r['reaction_force_N'][0]==pytest.approx(51.2)
    assert r['nominal_stress_MPa'][0]==5
    assert r['source']=='ANALYTICAL_INFINITESIMAL_UNIAXIAL_NOT_ANSYS'
    r=analytical_reference(CompressionConfig(mode='plane_strain'),[.005])
    assert r['effective_modulus_MPa']==pytest.approx(1000/(1-.3**2))


@pytest.fixture
def rectangle(tmp_path):
    pytest.importorskip('gmsh')
    root=tmp_path/'rectangle';prepare_rectangle(root)
    return root


def test_actual_gmsh_rectangle_and_static_deck_inventory(rectangle):
    report=json.loads((rectangle/'rectangle_manifest.json').read_text())
    assert report['mesh_quality']['accepted'] and report['config']['width']==10.24
    assert report['solver_execution']=='NOT_EXECUTED'
    a=json.loads((rectangle/'generated/direct/input_manifest.json').read_text())
    b=json.loads((rectangle/'generated/platen_contact/input_manifest.json').read_text())
    assert a['mesh_sha256']==b['mesh_sha256'] and a['config']==b['config']
    text=(rectangle/'generated/platen_contact/compression.inp').read_text()
    assert 'ET,1,PLANE183' in text and 'R,1,1' in text
    assert 'ET,2,TARGE169' in text and 'ET,3,CONTA172' in text
    template=json.loads((rectangle/'MODEL_REVIEW_TEMPLATE.json').read_text())
    assert not any(template['checks'].values())


def test_contact_cannot_launch_from_unsupported_strings(rectangle,tmp_path,monkeypatch):
    executable=tmp_path/'UNIT_TEST_CONTROL.exe';executable.write_text('not executed')
    def forbid(*_,**__):raise AssertionError('Unqualified contact must never launch any process')
    monkeypatch.setattr('metamaterial_eval.simulation.solver_execution.subprocess.run',forbid)
    r=execute(rectangle/'generated/platen_contact',tmp_path/'execution',executable=executable,
              benchmark_evidence={'direct_rectangle_acceptance':'SOLVER_VERIFIED','solver_receipt_sha256':'invented'})
    assert r['status']=='BLOCKED_MISSING_DIRECT_BENCHMARK_EVIDENCE'


def test_arbitrary_pass_flag_is_not_actual_evidence():
    with pytest.raises(ValueError,match='receipt-linked'):checked_qualification({'status':'SOLVER_VERIFIED'},'direct')


def test_modified_qualification_report_rejected(tmp_path):
    report=tmp_path/'control.json';report.write_text('{}')
    token=evidence_token(report);report.write_text('{"status":"SOLVER_VERIFIED"}')
    with pytest.raises(ValueError,match='Modified'):checked_qualification(token,'direct')


def test_missing_actual_outputs_block_benchmark_qualification(tmp_path):
    execution=tmp_path/'absent_actual_execution';execution.mkdir()
    report=qualify(execution,tmp_path/'absent_numeric',tmp_path/'absent_review','2026 R1',tmp_path/'qualification')
    assert report['status']=='BLOCKED_OR_FAILED'
    assert report['mechanical_output_verified'] is False
    assert report['llm_performance_eligible'] is False


def test_nonfinite_numeric_control_cannot_be_measurement(tmp_path):
    control=tmp_path/'UNIT_TEST_CONTROL.csv';control.write_text('x,y\n1,nan\n')
    with pytest.raises(ValueError,match='nonfinite'):read_numeric_csv(control,['x','y'])


def analytical_history_control():
    # Independent analytical numeric control, never an ANSYS result/receipt.
    c=CompressionConfig(width=1,height=1)
    raw=[{'set':1.,'pseudo_time':.001,'load_step':1.,'substep':1.,'top_uy_mm':-.001,'upper_rf_y_N':1.,'lower_rf_y_N':-1.}]
    curve=[{'set':1.,'pseudo_time':.001,'engineering_compression_strain':.001,'nominal_compression_stress_MPa':1.}]
    return c,raw,curve


def test_derived_metric_control_must_match_raw_control():
    from metamaterial_eval.simulation.ansys_qualification import verify_derived_curve
    c,raw,curve=analytical_history_control()
    assert verify_derived_curve(raw,curve,c,{(1,1)})['force_balance_pass']
    curve[0]['nominal_compression_stress_MPa']=2
    with pytest.raises(ValueError,match='differs'):verify_derived_curve(raw,curve,c,{(1,1)})


def test_unconverged_numeric_control_excluded():
    from metamaterial_eval.simulation.ansys_qualification import verify_derived_curve
    c,raw,curve=analytical_history_control()
    with pytest.raises(ValueError,match='unconverged'):verify_derived_curve(raw,curve,c,set())


@pytest.mark.parametrize('failure',['missing','unengaged','penetration','inventory'])
def test_contact_numeric_control_cannot_hide_missing_or_bad_rows(failure):
    from metamaterial_eval.simulation.ansys_qualification import verify_derived_curve
    c,raw,curve=analytical_history_control()
    contacts=[{'set':1.,'pair':p,'element':p+10,'status':2,'pressure_MPa':1.,'penetration_mm':0.,'gap_mm':0.} for p in [1,2]]
    counts={1:1,2:1}
    if failure=='missing':contacts=[]
    elif failure=='unengaged':contacts[0]['status']=0
    elif failure=='penetration':contacts[0]['penetration_mm']=.002
    else:counts[1]=2
    with pytest.raises(ValueError):verify_derived_curve(raw,curve,c,{(1,1)},contacts,counts)
