"""Synthetic numerical controls only, separate from licensed integration checks."""
import numpy as np
import pytest
from metamaterial_eval.simulation.microstructure_results import force_metrics,contact_metrics,fit_stiffness,numeric


def test_nominal_envelope_units_and_native_signs():
    m=force_metrics(.001,-.01024,-.1024,.1024)
    assert m['engineering_compression_strain']==pytest.approx(.001)
    assert m['nominal_compression_stress_MPa']==pytest.approx(.01)


@pytest.mark.parametrize('upper,lower',[(-1,0),(0,0),(1,-1),(-1,.5)])
def test_absent_or_unbalanced_load_is_not_physical_performance(upper,lower):
    with pytest.raises(ValueError):force_metrics(.001,-.01,upper,lower)


def test_contact_endpoint_scope_and_signed_force_opposition():
    rows=np.array([[1,10,2,1,1,1e-7,1e-7,-1],[2,20,2,1,1,1e-7,1e-7,1.]])
    out=contact_metrics(rows,{'bottom':1,'top':1},-1,1)
    assert out[0]['signed_opposition_residual_relative']==0
    rows[0,7]=1
    with pytest.raises(ValueError):contact_metrics(rows,{'bottom':1,'top':1},-1,1)


@pytest.mark.parametrize('column,value',[(2,0),(3,0),(5,.001)])
def test_inactive_missing_or_penetrating_contact_rejected(column,value):
    rows=np.array([[1,10,2,1,0,1e-7,1e-7,-1],[2,20,2,1,0,1e-7,1e-7,1.]])
    rows[0,column]=value
    with pytest.raises(ValueError):contact_metrics(rows,{'bottom':1,'top':1},-1,1)


def test_single_point_does_not_establish_fitted_modulus():
    row={'engineering_compression_strain':.0001,'nominal_compression_stress_MPa':.001}
    assert fit_stiffness([row])['effective_modulus_MPa'] is None
    fit=fit_stiffness([row,{'engineering_compression_strain':.001,'nominal_compression_stress_MPa':.01}])
    assert fit['effective_modulus_MPa']==pytest.approx(10)
    assert fit['normalized_modulus']==pytest.approx(.01)


def test_missing_stress_component_is_not_filled(tmp_path):
    p=tmp_path/'field.csv';p.write_text('node,uy_mm\n1,0\n')
    with pytest.raises(ValueError,match='schema'):numeric(p,['node','syy_MPa'])


def test_windows_blank_lines_do_not_hide_solver_warning():
    from metamaterial_eval.simulation.solver_execution import solver_warnings
    assert solver_warnings('*** WARNING *** CP = 1\n\n It is highly recommended to update stiffness\n')==['It is highly recommended to update stiffness']


def test_unique_native_result_jobname_is_validated(tmp_path):
    from metamaterial_eval.simulation.microstructure_results import native_result_path
    assert native_result_path(tmp_path,{'result_jobname':'v064r001'})==tmp_path/'v064r001.rst'
    assert native_result_path(tmp_path,{})==tmp_path/'compression.rst'
    with pytest.raises(ValueError):native_result_path(tmp_path,{'result_jobname':'../outside'})


@pytest.mark.parametrize('correct_hash,expected_name',[(True,'compression.rst'),(False,'requested.rst')])
def test_observed_jobname_requires_native_log_and_receipt_hash(tmp_path,correct_hash,expected_name):
    from metamaterial_eval.simulation.microstructure_results import observed_native_result
    from metamaterial_eval.simulation.solver_execution import file_hash
    actual=tmp_path/'compression.rst';actual.write_bytes(b'unit control only')
    receipt={'process':{'artifacts':{'compression.rst':{'sha256':file_hash(actual) if correct_hash else 'wrong'}}}}
    path,record=observed_native_result(tmp_path,{'result_jobname':'requested'},receipt,'CURRENT JOBNAME REDEFINED AS compression')
    assert path.name==expected_name and record['deviation']==correct_hash


@pytest.mark.parametrize('change,expected_error',[(None,None),('source_RST_sha256','provenance'),('solve','read-only')])
def test_separate_field_export_requires_original_native_provenance(tmp_path,change,expected_error):
    import json
    from metamaterial_eval.simulation.microstructure_results import verified_field_export
    from metamaterial_eval.simulation.solver_execution import file_hash
    source=tmp_path/'source';source.mkdir();fields=tmp_path/'fields';fields.mkdir()
    for name in ['execution_receipt.json','native.rst','checkpoint.db','protocol.json']:(source/name).write_bytes(b'unit authentication control')
    (fields/'input.inp').write_text('/POST1\n'+('SOLVE\n' if change=='solve' else 'SET,1,1\n'))
    r={'process':{'returncode':0},'input_sha256':file_hash(fields/'input.inp')}
    p={'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),'source_RST_sha256':file_hash(source/'native.rst'),'source_protocol_sha256':file_hash(source/'protocol.json'),'source_checkpoint_database_sha256':file_hash(source/'checkpoint.db'),'input_sha256':r['input_sha256']}
    if change=='source_RST_sha256':p[change]='wrong'
    (fields/'execution_receipt.json').write_text(json.dumps(r));(fields/'provenance.json').write_text(json.dumps(p))
    if expected_error:
        with pytest.raises(ValueError,match=expected_error):verified_field_export(source,fields,source/'native.rst',source/'protocol.json')
    else:assert verified_field_export(source,fields,source/'native.rst',source/'protocol.json')==r


@pytest.mark.parametrize('variant,accepted',[
    ('valid',True),('no_read_only_export',False),('no_announcement',False),('duplicate_announcement',False),
    ('debug_substep',False),('wrong_time',False),('multiple_solves',False),('multiple_increments',False),
    ('no_force_criterion_pass',False),('other_process_failure',False)])
def test_output_memory_stop_requires_native_equilibrium_and_readable_unique_set(variant,accepted):
    from metamaterial_eval.simulation.microstructure_results import checkpoint_convergence_evidence
    r={'converged_steps':[],'status':'MEMORY_BUDGET_EXCEEDED'};source='NSUBST,1,1,1\nSOLVE\n';time=.00005;ss=1
    force='FORCE CONVERGENCE VALUE = .0004 CRITERION= .00043 <<< CONVERGED\n'
    announcement='>>> SOLUTION CONVERGED AFTER EQUILIBRIUM ITERATION 7\n';log=force+announcement
    if variant=='no_announcement':log=force
    if variant=='duplicate_announcement':log+=announcement
    if variant=='debug_substep':ss=999999
    if variant=='wrong_time':time=.0001
    if variant=='multiple_solves':source+='SOLVE\n'
    if variant=='multiple_increments':source='NSUBST,2,20,1\nSOLVE\n'
    if variant=='no_force_criterion_pass':log=announcement
    if variant=='other_process_failure':r['status']='SOLVER_FAILURE'
    args=(r,log,source,{'strains':[.00005]},1,ss,time,variant!='no_read_only_export')
    if accepted:assert checkpoint_convergence_evidence(*args)=='NATIVE_EQUILIBRIUM_AND_READABLE_SET_BEFORE_OUTPUT_MEMORY_STOP'
    else:
        with pytest.raises(ValueError):checkpoint_convergence_evidence(*args)


@pytest.mark.parametrize('text',[
    'The requested S data is not available. The *VGET command is ignored.',
    'The requested EPEL data is not available.',
    'Item NMIS has not been stored in the database.',
    'Item SMIS has not been stored in the database.',
    'Unknown parameter name= FYV. A value of 7.888609052E-31 will be used.'])
def test_native_missing_results_are_never_accepted_as_zero_fields(text):
    from metamaterial_eval.simulation.microstructure_results import unsupported_result_queries
    assert unsupported_result_queries(text)
