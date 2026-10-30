"""Synthetic parser controls, explicitly not licensed integration evidence."""
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from metamaterial_eval.simulation.nonlinear_diagnostics import (
    finite,residual_trend,parse_solver_log,parse_contact,contact_summary,
    localize_residual,diagnostic_stop,DiagnosticBudget,telemetry_commands)


@pytest.mark.parametrize('values,expected',[
    ([], 'MISSING'),([10,5], 'INSUFFICIENT_HISTORY'),([10,5,2,.5],'BELOW_FORCE_CRITERION_ONLY'),
    ([100,50,25,10],'DECREASING_NOT_CONVERGED'),([5,6,8,12],'INCREASING'),
    ([5,5.1,4.9,5.01],'PLATEAU'),([4,9,3,8],'OSCILLATING')])
def test_residual_sequences(values,expected):assert residual_trend(values)==expected


@pytest.mark.parametrize('value',['nan','inf','-inf'])
def test_nonfinite_diagnostics_rejected(value):
    with pytest.raises(ValueError):finite(value)


def test_fortran_D_exponent():assert finite('1.25D-3')==.00125


def test_force_evaluation_precedes_update_and_not_mechanical_convergence():
    s='FORCE CONVERGENCE VALUE = 5 CRITERION= 1\nEQUIL ITER 1 COMPLETED. NEW TRIANG MATRIX. MAX DOF INC= -.01\nFORCE CONVERGENCE VALUE = .5 CRITERION= 1'
    p=parse_solver_log(s)
    assert [r['last_completed_iteration'] for r in p['force_evaluations']]==[0,1]
    assert p['converged_substeps']==[] and p['factorizations_completed']==1


def test_repeated_iteration_and_bisection_preserve_source_order():
    s='EQUIL ITER 1 COMPLETED. NEW TRIANG MATRIX. MAX DOF INC= .1\nBISECTION NUMBER 1\nEQUIL ITER 1 COMPLETED. NEW TRIANG MATRIX. MAX DOF INC= .01'
    p=parse_solver_log(s)
    assert [r['iteration'] for r in p['completed_iterations']]==[1,1]
    assert [r['trial_sequence'] for r in p['completed_iterations']]==[0,1]


def test_multiple_loadsteps_are_explicit():
    p=parse_solver_log('*** LOAD STEP 1 SUBSTEP 2 COMPLETED\n*** LOAD STEP 2 SUBSTEP 1 COMPLETED')
    assert [(r['load_step'],r['substep']) for r in p['converged_substeps']]==[(1,2),(2,1)]


def test_partial_iteration_not_counted():
    p=parse_solver_log('EQUIL ITER 1 COMPLETED. NEW TRIANG MATRIX. MAX DOF INC= .01\nEQUIL ITER 2 COMP')
    assert len(p['completed_iterations'])==1


def test_duplicate_force_lines_remain_evaluations_not_duplicate_iterations():
    p=parse_solver_log(('FORCE CONVERGENCE VALUE = 1 CRITERION= .1\n')*2)
    assert len(p['force_evaluations'])==2 and p['completed_iterations']==[]


def test_cpu_and_wall_clock_not_pseudotime():
    p=parse_solver_log('*** NOTE *** CP = 22.5 TIME= 23:59:01\nEQUIL ITER 1 COMPLETED. NEW TRIANG MATRIX. MAX DOF INC= .001')
    r=p['completed_iterations'][0];assert r['preceding_CP_seconds']==22.5 and r['preceding_wall_clock']=='23:59:01'


def test_displacement_convergence_is_separate():
    p=parse_solver_log('DISP CONVERGENCE VALUE = .01 CRITERION= .1 <<< CONVERGED')
    assert p['displacement_evaluations'][0]['solver_marked_displacement_converged'] and not p['converged_substeps']


def test_zero_criterion_rejected():
    with pytest.raises(ValueError):parse_solver_log('FORCE CONVERGENCE VALUE = 1 CRITERION= 0')


def record(pair=2,active=5,chatter=0):
    return dict(pair=pair,active_elements=active,chattering_level=chatter,min_normal_stiffness=10,max_normal_stiffness=20,penetration_or_gap_mm=1e-7,max_pressure_MPa=1)


@pytest.mark.parametrize('states,transitions,chatter',[
    ([5,5,5],0,False),([5,0,0],1,False),([0,5,5],1,False),([5,0,5,0],3,True)])
def test_contact_open_close_and_chatter(states,transitions,chatter):
    r=contact_summary([record(active=a) for a in states])['2']
    assert r['whole_pair_open_closed_transitions']==transitions and r['chattering_evidenced']==chatter


def test_native_chatter_indicator_without_whole_pair_loss():
    assert contact_summary([record(chatter=2)])['2']['chattering_evidenced']


def test_missing_and_both_active_pairs():
    assert contact_summary([record()])['3']['status']=='MISSING_PAIR'
    assert all(a['status']=='ACTIVE_AT_ALL_RECORDED_ITERATIONS' for a in contact_summary([record(2),record(3)]).values())


def test_missing_contact_header_not_zero_contact():assert parse_contact('')['issues']==['MISSING_HEADER']


def cnd(rows,tail=''):
    names={1:'Contact Pair ID',2:'Number of Contact Elements in Contact',4:'Max. Chattering Level',5:'Max. Penetration/Min. Gap',7:'Max. Normal Stiffness',14:'Max. Contact Pressure',32:'Total contact force due to pressure -y component'}
    head='<HEADER FRQ="ITERATION">'+''.join(f'<COLUMN ID="{i}">{names.get(i,"other")}</COLUMN>' for i in range(1,43))+'</HEADER>'
    return head+'<COLDATA LOAD_STEP="1" SUBSTEP="1" ITERATION="0" TIME=".001">'+rows+'</COLDATA>'+tail


def test_actual_column_schema_and_trial_scope():
    values=[0]*42;values[0]=2;values[1]=4;values[31]=-5
    p=parse_contact(cnd(' '.join(map(str,values))))
    assert p['records'][0]['contact_force_y_N']==-5 and p['frequency']=='ITERATION'
    assert 'UNCONVERGED' in p['records'][0]['scope']


def test_incomplete_final_contact_block_preserves_prior_records():
    values=[0]*42;values[0]=2
    p=parse_contact(cnd(' '.join(map(str,values)),'<COLDATA LOAD_STEP="1">'))
    assert len(p['records'])==1 and p['issues']==['INCOMPLETE_FINAL_BLOCK']


def test_duplicate_contact_pair_rejected():
    row=' '.join(['2']+['0']*41)
    with pytest.raises(ValueError,match='Duplicate'):parse_contact(cnd(row+'\n'+row))


def test_partial_contact_row_rejected():
    with pytest.raises(ValueError,match='Incomplete'):parse_contact(cnd('2 3'))


def nr(tmp_path,rows='1 .3 .4 0\n2 0 0 0\n',count=2):
    p=tmp_path/'compression.nr001';p.write_text('/COM,ANSYS RELEASE 2024 R1\nCNVV=.5 CNVC=.1\n'+str(count)+' .001 1 1 3\n1 2 6\n'+rows);return p


def test_spatial_residual_association_and_norm(tmp_path):
    nodes=np.array([[0.,0.],[1.,1.]])
    r=localize_residual(nr(tmp_path),nodes,np.array([[0,1,0]]),np.array(['bottom']))
    assert r['specimen_translation_L2_N']==.5
    assert r['top_residual_nodes'][0]['node']==1 and r['top_residual_nodes'][0]['xy_mm']==[0,0]
    assert r['top_residual_nodes'][0]['dominant_direction']=='FY'
    assert r['top_residual_nodes'][0]['boundary_membership']==['bottom']


@pytest.mark.parametrize('rows,count',[
    ('1 1 1 0\n',2),('1 1 1 0\n1 2 2 0\n',2),('1 nan 0 0\n2 0 0 0\n',2),('1 1\n2 0 0 0\n',2)])
def test_residual_missing_duplicate_invalid_partial(tmp_path,rows,count):
    with pytest.raises(ValueError):localize_residual(nr(tmp_path,rows,count),np.array([[0.,0.],[1.,1.]]))


def test_internal_nodes_excluded_from_specimen_localization(tmp_path):
    r=localize_residual(nr(tmp_path,'1 1 0 0\n2 0 1 0\n3 999 999 0\n',3),np.array([[0.,0.],[1.,1.]]))
    assert r['top_residual_nodes'][0]['node']<=2


def test_budget_rejects_snapshot_excess(tmp_path):
    for i in range(5):(tmp_path/f'compression.nr{i:03d}').touch()
    assert diagnostic_stop(tmp_path,DiagnosticBudget())=='DIAGNOSTIC_FILE_COUNT_LIMIT'


def test_diagnostic_bytes_cap(tmp_path):
    (tmp_path/'compression.cnd').write_text('1234')
    assert diagnostic_stop(tmp_path,DiagnosticBudget(bytes_cap=3))=='DIAGNOSTIC_DISK_BUDGET'


def test_no_early_stop_for_first_large_residual(tmp_path):
    (tmp_path/'solver.out').write_text('FORCE CONVERGENCE VALUE = 1e8 CRITERION= 1')
    assert diagnostic_stop(tmp_path,DiagnosticBudget(stop_stagnation=True)) is None


def test_completed_iteration_cap_is_prospective(tmp_path):
    (tmp_path/'solver.out').write_text('EQUIL ITER 1 COMPLETED. NEW TRIANG MATRIX. MAX DOF INC= 1')
    assert diagnostic_stop(tmp_path,DiagnosticBudget(completed_iterations_cap=1))=='REGISTERED_ITERATION_LIMIT'


def test_snapshot_command_limits_explicit():
    commands=telemetry_commands(42)
    assert 'NLDIAG,CONT,ITER' in commands and 'NLDIAG,NRRE,ON,2' in commands
    assert 'NLHIST,NSOL,RFUP,F,Y,42' in commands


def test_no_false_negative_pivot_from_zero_statistics(tmp_path):
    (tmp_path/'solver.out').write_text('# of negative pivots = 0')
    assert diagnostic_stop(tmp_path,DiagnosticBudget()) is None


@pytest.mark.parametrize('error,status',[(RuntimeError('monitor control'),'MONITOR_FAILURE'),(KeyboardInterrupt(),'CANCELLED')])
def test_monitor_failure_and_cancel_terminate_owned_process(tmp_path,error,status):
    import sys
    from metamaterial_eval.simulation.windows_ansys import bounded_run
    def stop(folder):raise error
    r=bounded_run([sys.executable,'-c','import time; time.sleep(30)'],tmp_path/'owned',timeout=10,stop_check=stop)
    assert r['status']==status and r['returncode'] is not None and r['runtime_seconds']<10
