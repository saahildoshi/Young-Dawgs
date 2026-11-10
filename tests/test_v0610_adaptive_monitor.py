"""Supervisor tests are synthetic and do not establish contact acceptance."""
from metamaterial_eval.simulation.progressive_compression import ProgressMonitor


def test_registered_adaptive_supervision_allows_native_trial_bisection(tmp_path):
    (tmp_path/'solver.out').write_text('*** ERROR ***\nElement 36599 has become highly distorted.\n*** BEGIN BISECTION NUMBER 1 NEW TIME INCREMENT=0.00001\n')
    assert ProgressMonitor(stop_on_trial_error=False)(tmp_path) is None
    assert ProgressMonitor()(tmp_path)=='NATIVE_SOLVER_ERROR_OR_DISTORTION'


def test_fatal_error_still_stops_adaptive_supervision(tmp_path):
    (tmp_path/'solver.out').write_text('*** FATAL ***\nNative unrecoverable failure\n')
    assert ProgressMonitor(stop_on_trial_error=False)(tmp_path)=='NATIVE_SOLVER_ERROR_OR_DISTORTION'


def test_adaptive_mode_keeps_prospective_no_progress_limit(tmp_path):
    (tmp_path/'solver.out').write_text('*** BEGIN BISECTION NUMBER 1\n')
    monitor=ProgressMonitor(stop_on_trial_error=False,no_progress_seconds=1200)
    monitor.last_progress-=1201
    assert monitor(tmp_path)=='NO_CONVERGED_PROGRESS_TIMEOUT'
