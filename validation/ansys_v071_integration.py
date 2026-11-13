"""Read-only verification of actual licensed v0.7.1 artifacts; launches no solver."""
from pathlib import Path
import numpy as np
import pytest
from scripts.v071_register import RUN,BASE
from scripts.v070_protocol import read,REPO,sha
from scripts.v071_mechanics import model
from metamaterial_eval.simulation.solver_execution import file_hash

CASES=[('M0_matrix',1,1),('M1_parallel',1,1),('M1_series',1,1),('M1_equal',1,2),
       ('M2_reference',1,1),('M2_reference',2,1)]+[(sid,k,1) for sid in ['M3_A01','M4_B02','M5_C02_r1','M6_C02_r0'] for k in [1,2]]


@pytest.mark.parametrize('sid,k,attempt',CASES)
def test_real_rst_database_and_independent_fields(sid,k,attempt):
    name=f'{sid}_H{k}_attempt{attempt:03d}';r=read(RUN/'mechanical_response'/f'{name}.json')
    assert r['accepted'] and all(r['checks'].values())
    source=Path(r['source_directory']);post=Path(r['independent_readback_directory'])
    process=read(source/'EXECUTION.json');assert process['native_process_ok'] and process['solver_release']=='2024 R1'
    assert file_hash(source/'elastic.rst')==r['native_result_sha256']==process['process']['artifacts']['elastic.rst']['sha256']
    assert file_hash(source/'model.db')==r['native_database_sha256']
    assert file_hash(post/'fields.csv')==r['native_fields_sha256']
    assert not any(line.startswith(('SOLVE','SAVE,')) for line in (post/'input.inp').read_text().splitlines())
    assert all(read(post/'READBACK.json')['identical_exports_to_solve'].values())
    assert len(r['native_curve'])==5 and r['engineering_strains']==pytest.approx([.001,.002,.003,.004,.005])
    m,_,_=model(sid,k);q=np.loadtxt(post/'connectivity.csv',delimiter=',')
    assert np.array_equal(q[:,1:],m['quads']+1)


@pytest.mark.parametrize('sid,expected,attempt',[('M0_matrix',1000,1),('M1_parallel',5500,1),('M1_series',20000/11,1),('M1_equal',1000,2)])
def test_native_curves_against_analytical_controls(sid,expected,attempt):
    d=BASE/f'{sid}_H1_attempt{attempt:03d}'
    curve=np.loadtxt(d/'curve.csv',delimiter=',');strain=-curve[:,2];stress=-curve[:,5]
    fitted=np.polyfit(strain,stress,1)
    assert fitted[0]==pytest.approx(expected,rel=.001)
    assert np.max(np.abs(curve[:,5]+curve[:,6]))<.001*np.max(stress)
    assert curve[:,8]==pytest.approx(.5*stress*strain,rel=.001)


def test_failed_coordinate_tolerance_attempt_is_preserved_and_rejected():
    r=read(RUN/'mechanical_response/M1_equal_H1_attempt001.json')
    assert not r['accepted'] and not r['checks']['exact_native_constraint_inventory']
    assert r['constraint_inventory']['native_constraint_count']==772
    assert r['constraint_inventory']['expected_constraint_count']==515
    assert file_hash(Path(r['source_directory'])/'elastic.rst')==r['native_result_sha256']


@pytest.mark.parametrize('sid',['M2_reference','M3_A01','M4_B02','M5_C02_r1','M6_C02_r0'])
def test_same_geometry_mesh_sensitivity_and_phase_fraction(sid):
    a,b=[read(RUN/'mechanical_response'/f'{sid}_H{k}_attempt001.json') for k in [1,2]]
    assert a['mesh']['material_area_fractions']==b['mesh']['material_area_fractions']
    assert b['mesh']['elements']==4*a['mesh']['elements']
    assert abs(a['effective_modulus_MPa']-b['effective_modulus_MPa'])/b['effective_modulus_MPa']<=.02


def test_original_selected_sources_and_scripts_unchanged():
    pilot=REPO/'experiments/pipeline_v0.7.0/run_002_real_microscopy'
    frozen=read(pilot/'protocol/ALL_SCRIPTS_FROZEN.json')
    assert all(sha(pilot/path)==digest for path,digest in frozen['files'].items())
    for path in (RUN/'specimen_manifests').glob('*.json'):
        m=read(path);assert sha(REPO/m['source_array_path'])==m['source_array_sha256']


def test_native_budget_and_repeated_reference_readback():
    receipts=[read(p) for p in BASE.glob('*/process_receipt.json')]
    p=read(RUN/'protocol/PROTOCOL.json')['resource_limits']
    assert len(receipts)<=p['maximum_native_jobs'] and sum(r['runtime_seconds'] for r in receipts)<=p['native_campaign_seconds']
    a,b=[BASE/f'M2_reference_H1_attempt001_read{i:02d}' for i in [1,2]]
    for name in ['curve.csv','nodes.csv','fields.csv','connectivity.csv']:
        assert file_hash(a/name)==file_hash(b/name)
