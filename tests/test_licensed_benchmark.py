"""Unit controls for native ANSYS data, not licensed solver integration tests."""
import numpy as np
import pytest
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.licensed_benchmark import export_macro, native_metrics, analyze
from metamaterial_eval.simulation.mesh_generation import Mesh


def test_native_reactions_are_converted_explicitly():
    rows=[{'top_uy_mm':-.0512,'upper_rf_y_N':-51.2,'lower_rf_y_N':51.2}]
    result=native_metrics(rows,CompressionConfig())
    assert result['engineering_compression_strain'][0]==pytest.approx(.005)
    assert result['nominal_compression_stress_MPa'][0]==pytest.approx(5)
    assert result['force_balance_pass']
    rows[0]['upper_rf_y_N']=51.2
    with pytest.raises(ValueError,match='sign'):native_metrics(rows,CompressionConfig())


def test_stress_export_queries_corners_only_displacements_include_midsides():
    mesh=Mesh(np.array([[0,0],[1,0],[0,1],[.5,0],[.5,.5],[0,.5]]),
              np.array([[0,1,2,3,4,5]]),np.array([[0,1,3],[1,2,4],[2,0,5]]),
              np.array(['bottom','external','external']))
    macro=export_macro(mesh,False)
    assert '*DO,NN,1,6' in macro
    assert '*GET,SYV,NODE,3,S,Y' in macro
    assert '*GET,SYV,NODE,4,S,Y' not in macro
    assert '*GET,SYV,NODE,NN,S,Y' not in macro
    assert 'stress_fields' in macro and 'elastic_exx' in macro


def test_missing_actual_output_cannot_qualify(tmp_path):
    execution=tmp_path/'execution';execution.mkdir()
    result=analyze(execution,tmp_path/'out',tmp_path/'absent.json')
    assert result['status']=='QUARANTINED'
    assert not result['llm_performance_eligible']
