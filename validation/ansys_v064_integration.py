"""Real installed v241 evidence checks; run explicitly, never synthetic fixtures."""
import json
from pathlib import Path
import re
from decimal import Decimal
import numpy as np
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.nonlinear_diagnostics import parse_contact,parse_solver_log,localize_residual
from metamaterial_eval.simulation.microstructure_results import force_metrics,contact_metrics
from metamaterial_eval.simulation.solver_execution import file_hash

RUN=Path(__file__).resolve().parents[1]/'experiments/pipeline_v0.6.4/run_001'
BASE=artifact_root()/'solver/v064'


def read(path):return json.loads(Path(path).read_text())


def history(label):return np.loadtxt(BASE/label/'stage001_history.csv',delimiter=',',skiprows=1,ndmin=2)[0]


def validated_contact(label):
    p=BASE/label;h=history(label);m=read(p/'model_manifest.json');receipt=read(p/'execution_receipt.json')
    assert receipt['process']['returncode']==0 and receipt['converged_steps']
    assert float((p/'stage001_gate.txt').read_text().split(',')[0])==0
    actual=force_metrics(h[0],h[3],h[4],h[5],m['config']['width'],m['config']['height'],m['config']['thickness'])
    contacts=contact_metrics(np.loadtxt(p/'stage001_contact.csv',delimiter=',',skiprows=1,ndmin=2),m['contact_elements'],h[4],h[5])
    return actual,contacts


def test_installed_v241_diagnostics_are_actual_iteration_files():
    p=BASE/'rectangle_telemetry_001';r=read(p/'execution_receipt.json')
    assert r['solver_version']=='2024 R1' and r['process']['returncode']==0
    assert sorted(f.suffix for f in p.glob('compression.nr[0-9]*'))==['.nr001','.nr002']
    c=parse_contact((p/'compression.cnd').read_text())
    assert c['frequency']=='ITERATION' and len(c['records'])==10
    assert (p/'compression.nlh').stat().st_size>0 and (p/'compression.nd001').exists()


def test_native_residual_schema_reproduces_native_norm():
    p=BASE/'rectangle_telemetry_001';z=np.load(RUN.parents[1]/'pipeline_v0.6.2/run_001/rectangle_contact/generated/input_002/mesh.npz')
    r=localize_residual(p/'compression.nr001',z['nodes'],z['boundary'],z['boundary_groups'])
    printed=re.search(r'CNVV\s*=\s*([\d.Ee+\-]+)',r['native_convergence_header'])[1]
    norm=float(printed)
    half_last_printed_digit=.5*10**Decimal(printed).as_tuple().exponent
    assert abs(r['specimen_translation_L2_N']-norm)<=half_last_printed_digit
    assert r['DOF_codes']==[1,2,6] and r['top_residual_nodes'][0]['node']==67


def test_rectangle_diagnostics_preserve_accepted_response():
    actual,_=validated_contact('rectangle_telemetry_001')
    assert abs(-actual['upper_rf_y_N']/51.48250-1)<1e-6


def test_nodal_detection_preserves_rectangle_force_and_gates():
    a,_=validated_contact('rectangle_pp_base');b,_=validated_contact('rectangle_pp_nodal')
    assert abs(a['upper_rf_y_N']/b['upper_rf_y_N']-1)<.01


def test_actual_two_core_capability_not_all_core_entitlement():
    a,_=validated_contact('rectangle_pp_nodal');b,_=validated_contact('rectangle_pp_nodal_2cores')
    assert abs(a['upper_rf_y_N']/b['upper_rf_y_N']-1)<1e-8
    text=(BASE/'rectangle_pp_nodal_2cores/solver.out').read_text(errors='replace')
    assert re.search(r'NUMBER OF SMP THREADS USED\s*=\s*2',text)


def test_compliant_contact_reproduces_chatter_without_total_pair_loss():
    assert not read(BASE/'pp_base/execution_receipt.json')['converged_steps']
    c=read(BASE/'pp_base/contact_summary.json')
    assert all(p['chattering_evidenced'] and p['min_active_elements']>0 for p in c.values())
    r=read(BASE/'pp_base/residual_localization.json')
    assert all(a['top_residual_nodes'][0]['boundary_membership'] in [['top'],['bottom']] for a in r)


def test_direct_diagnostic_converges_but_changes_boundary_conditions():
    h=np.loadtxt(BASE/'direct/direct_history.csv',delimiter=',',skiprows=1)
    r=force_metrics(h[0],h[3],h[4],h[5],4,4,1)
    assert r['compression_displacement_mm']==.02 and read(BASE/'direct/execution_receipt.json')['converged_steps']


def test_linearized_and_smaller_increment_alone_do_not_cure_contact():
    for label in ['pp_linearized_monitorfix','pp_initial8','pp_update100','pp_fkn1']:
        r=read(BASE/label/'execution_receipt.json')
        assert r['process']['returncode']==1 and not r['converged_steps']


def test_native_cutback_and_unconverged_rst_are_not_accepted():
    p=BASE/'forced_cutback_control';t=parse_solver_log((p/'solver.out').read_text(errors='replace'))
    assert len(t['cutback_events'])==5 and not t['converged_substeps']
    c=parse_contact((p/'compression.cnd').read_text())
    assert min(r['pseudo_time'] for r in c['records'])==.00046875
    assert (p/'compression.rst').exists()  # Debug substep999999 is real, invalid for mechanics.


def test_nodal_correction_has_actual_nonzero_force_and_supported_fields():
    result,contacts=validated_contact('pp_nodal_target')
    assert result['upper_rf_y_N']<-.01 and all(c['max_stored_endpoint_penetration_mm']<1e-5 for c in contacts)
    z=np.load(BASE/'compliant_geometry_001/mesh.npz');p=BASE/'pp_nodal_target'
    u=np.loadtxt(p/'stage001_displacements.csv',delimiter=',',skiprows=1)
    s=np.loadtxt(p/'stage001_stress.csv',delimiter=',',skiprows=1)
    assert len(u)==len(z['nodes']) and len(s)==len(np.unique(z['triangles'][:,:3]))
