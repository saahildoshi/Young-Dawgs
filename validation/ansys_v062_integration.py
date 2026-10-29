"""Explicitly invoked checks against REAL local ANSYS run receipts and RST files.

Run separately from the unit suite. Missing real artifacts fail, never mock/skip.
"""
from pathlib import Path
import json
import pytest
from metamaterial_eval.simulation.ansys_qualification import checked_qualification,evidence_token
from metamaterial_eval.simulation.licensed_benchmark import analyze
from metamaterial_eval.simulation.solver_execution import file_hash

ROOT=Path(__file__).resolve().parents[1]/'experiments/pipeline_v0.6.2/run_001'


@pytest.mark.parametrize('stage',['rectangle_direct','rectangle_contact'])
def test_actual_solver_receipt_and_reextract(stage,tmp_path):
    base=ROOT/stage
    attempt='001' if stage=='rectangle_direct' else '002'
    report=base/f'analysis_{attempt}/qualification.json'
    kind='direct' if stage=='rectangle_direct' else 'platen_contact'
    checked_qualification(evidence_token(report),kind)
    result=analyze(base/f'generated/execution_{attempt}',tmp_path/'extraction',ROOT/'protocol/BENCHMARK_PROTOCOL.json')
    assert result['status']=='VALID_SOLVER_MEASUREMENTS'
    assert result['all_requested_stages_achieved']
    assert result['force_balance_max_relative']<.01
    assert result['max_relative_analytical_error_small_strain']<.02


def test_actual_workbench_mechanical_scripting():
    r=json.loads((ROOT/'environment/workbench_probe/probe_receipt.json').read_text())
    assert r['returncode']==0
    assert r['workbench_journal_completed'] and r['mechanical_embedded_script_completed']


def test_actual_contact_element_force_and_endpoint_results():
    folder=ROOT/'contact_validation/point_extraction_001'
    report=json.loads((folder/'contact_point_validation.json').read_text())
    assert report['status']=='PASS'
    assert report['source_RST_sha256']==file_hash(ROOT/'rectangle_contact/generated/execution_002/compression.rst')
    assert report['point_csv_sha256']==file_hash(folder/'contact_points.csv')
    assert report['maximum_stored_endpoint_penetration_mm']<1e-7
    assert report['maximum_contact_force_pilot_magnitude_difference_relative']<.01


def test_independent_licensed_repeat_has_same_history():
    original=ROOT/'rectangle_contact/generated/execution_002'
    repeat=ROOT/'rectangle_contact/generated/repeat_002'
    a=json.loads((original/'solver_status.json').read_text())
    b=json.loads((repeat/'solver_status.json').read_text())
    assert a['input_sha256']==b['input_sha256']
    assert b['status']=='EXECUTED_PENDING_IMPORT_CONTACT_AND_NUMERIC_VALIDATION'
    assert b['outputs']['compression.rst']==file_hash(repeat/'compression.rst')
    assert file_hash(original/'history.csv')==file_hash(repeat/'history.csv')
