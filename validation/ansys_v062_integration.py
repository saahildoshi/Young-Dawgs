"""Explicitly invoked checks against REAL local ANSYS run receipts and RST files.

Run separately from the unit suite. Missing real artifacts fail, never mock/skip.
"""
from pathlib import Path
import json
import pytest
from metamaterial_eval.simulation.ansys_qualification import checked_qualification,evidence_token
from metamaterial_eval.simulation.licensed_benchmark import analyze

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
