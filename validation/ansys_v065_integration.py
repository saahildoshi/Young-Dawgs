"""Explicit real licensed v241 evidence checks; no fresh solves or mock output."""
import json
from pathlib import Path
import numpy as np
import pytest
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.solver_execution import file_hash

REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'experiments/pipeline_v0.6.5/run_001'
BASE=artifact_root()/'solver/v065'
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


@pytest.mark.parametrize('fixture',['rectangle','compliant'])
def test_selective_actual_rst_reopened_with_all_fields(fixture):
    q=read(RUN/'small_licensed'/(fixture+'_selective_001')/'qualification.json')
    assert q['accepted'] and q['all_deformed_mappings_positive']
    assert q['raw_native_field_hashes']['stage001_stress.csv']==file_hash(BASE/(fixture+'_selective_001_post')/'stage001_stress.csv')
    assert q['accepted_measurements'][0]['reaction_balance_relative']<.01
    assert len(q['contacts'])==2


@pytest.mark.parametrize('fixture',['rectangle','compliant'])
def test_selective_reduces_rst_and_preserves_full_output_values(fixture):
    comparisons=read(RUN/'small_licensed/OUTPUT_PROTOCOL_VALIDATION.json')['comparisons']
    r=next(x for x in comparisons if x['fixture']==fixture)
    assert r['selective_RST_bytes']<r['full_RST_bytes']
    for field in r['full_vs_selective'].values():
        assert max(field['maximum_scaled_difference_by_column'])<1e-6 and field['repeat_identical']


@pytest.mark.parametrize('fixture',['rectangle','compliant'])
def test_read_only_repeat_uses_rst_with_model_only_database(fixture):
    source=BASE/(fixture+'_selective_001');p=BASE/(fixture+'_selective_001_repeat')
    text=(source/'input.inp').read_text();post=(p/'input.inp').read_text()
    assert 'SAVE,checkpoint,db,,MODEL' in text and '\nSOLVE\n' not in post
    prov=read(p/'provenance.json');assert prov['source_RST_sha256']==file_hash(source/'compression.rst')
    assert read(p/'execution_receipt.json')['process']['returncode']==0


@pytest.mark.parametrize('fixture',['rectangle','compliant'])
def test_actual_contact_forces_reactions_pressure_and_penetration(fixture):
    q=read(RUN/'small_licensed'/(fixture+'_selective_001')/'qualification.json')
    for c in q['contacts']:
        assert c['closed_elements']>0 and c['max_stored_endpoint_pressure_MPa']>0
        assert c['max_stored_endpoint_penetration_mm']<=1e-5
        assert c['signed_opposition_residual_relative']<.01


@pytest.mark.parametrize('fixture',['rectangle','compliant'])
def test_actual_uncapped_supervision_records_system_health(fixture):
    r=read(BASE/(fixture+'_selective_001')/'execution_receipt.json')['process']
    assert r['rss_limit_bytes'] is None and r['min_available_ram_bytes']==0
    assert r['system_before']['physical_RAM_bytes']>0 and r['resource_samples']
    assert any(s['commit_limit_bytes'] is not None for s in r['resource_samples'])


def test_real_missing_epel_output_is_quarantined():
    q=read(RUN/'small_licensed/NEGATIVE_CONTROL_QUARANTINE.json')
    assert not q['accepted'] and not q['accepted_measurements']
    assert 'Missing native result records' in q['failure']
    assert 'requested EPEL data is not available' in (BASE/'rectangle_missing_epel_001_post/solver.out').read_text()


def test_rectangle_actual_stress_strain_and_benchmark_units():
    p=BASE/'rectangle_selective_001_qualified'
    q=read(p/'qualification.json');force=q['accepted_measurements'][0]['upper_rf_y_N']
    assert abs(force-(-51.48250))/51.48250<.01
    s=np.load(p/'native_corner_stress_strain.npy')
    assert -.006<float(s[:,2].mean())<-.004
    assert -6<float(s[:,0].mean())<-4


def full():return read(RUN/'mechanical_results/qualification.json')


def test_full_source_exits_normally_without_rss_guard():
    r=read(BASE/'full_recovery_001/execution_receipt.json')
    assert r['status']=='PROCESS_EXITED' and r['process']['returncode']==0
    assert r['process']['rss_limit_bytes'] is None and r['process']['min_available_ram_bytes']==0
    assert r['converged_steps']==[[1,1]]
    assert (BASE/'full_recovery_001/compression.r001').stat().st_size>0


def test_full_native_provenance_matches_frozen_input_and_rst():
    q=full();p=read(RUN/'protocol/FULL_RECOVERY_001.json')
    assert file_hash(BASE/'full_recovery_001/input.inp')==p['frozen_input_sha256']
    assert file_hash(BASE/'full_recovery_001/compression.rst')==q['native_RST_sha256']
    assert q['mesh_semantic_sha256']=='e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc'


def test_full_independent_signed_support_and_contact_force_balance():
    q=full();m=q['accepted_measurements'][0]
    assert m['upper_rf_y_N']<0<m['lower_rf_y_N'] and m['reaction_balance_relative']<.01
    assert len(q['contacts'])==2
    for c in q['contacts']:
        assert c['closed_elements']>0 and c['max_stored_endpoint_pressure_MPa']>0
        assert c['max_stored_endpoint_penetration_mm']<1e-5 and c['signed_opposition_residual_relative']<.01


def test_full_actual_native_field_inventory_and_hashes():
    q=full();assert q['accepted'] and q['actual_nodes']==2766505 and q['actual_corner_field_nodes']==752212
    for name in ['stage001_stress.csv','stage001_displacements.csv']:
        assert file_hash(BASE/'full_recovery_001_post'/name)==q['raw_native_field_hashes'][name]
    s=np.load(BASE/'full_recovery_001_qualified/native_corner_stress_strain.npy',mmap_mode='r')
    assert s.shape==(752212,4) and np.isfinite(s).all() and np.max(abs(s[:,2]))>0


def test_full_every_deformed_quadratic_mapping_is_positive():
    q=full();assert q['actual_TRI6']==1261670 and q['all_deformed_mappings_positive']
    assert q['minimum_deformed_determinant_mm2']>0


def test_full_repeated_independent_native_extraction_is_identical():
    r=read(RUN/'mechanical_results/repeated_native_extraction.json')
    assert r['status']=='PASS_INDEPENDENT_REPEAT_IDENTICAL' and r['actual_returncode']==0
    assert all(v['first_sha256']==v['repeat_sha256'] for v in r['files'].values())
    assert '\nSOLVE\n' not in (BASE/'full_recovery_001_repeat/input.inp').read_text()


def test_full_one_point_normalization_never_becomes_a_fitted_modulus():
    q=full();assert len(q['accepted_measurements'])==1 and q['effective_modulus_fit_MPa'] is None
    m=q['accepted_measurements'][0]
    assert np.isclose(m['engineering_compression_strain'],.00005,rtol=0,atol=1e-12)
    assert np.isclose(m['nominal_compression_stress_MPa'],-m['upper_rf_y_N']/10.24,rtol=1e-12)
    assert not q['eligible_for_LLM_performance_ranking']


def test_full_actual_windows_pressure_and_output_growth_are_recorded():
    r=read(BASE/'full_recovery_001/execution_receipt.json')['process'];samples=r['resource_samples']
    assert any(s['output_file_bytes'].get('compression.rst',0)>0 for s in samples)
    assert all(s['available_RAM_bytes']>0 and s['commit_limit_bytes']>0 for s in samples)
    assert not any(s['windows_low_memory'] for s in samples)
    event=read(RUN/'performance/windows_resource_exhaustion_events.json')
    assert event['event_count']==0
