"""Synthetic telemetry tests, not licensed ANSYS evidence or large allocations."""
import sys
import pytest
from metamaterial_eval.simulation.system_health import HealthPolicy,HealthGuard,SystemSampler
from metamaterial_eval.simulation.windows_ansys import bounded_run


def sample(t, available=20, rss=35, commit=.7, paging=0, stalled=0, notification=False):
    return {'elapsed_seconds':t,'available_RAM_bytes':available*1024**3,'tree_rss_bytes':rss*1024**3,
            'commit_fraction':commit,'page_reads_per_second':paging,'seconds_without_output_growth':stalled,
            'windows_low_memory':notification}


@pytest.mark.parametrize('rss',[21,31,50])
def test_healthy_system_allows_large_process_rss(rss):
    guard=HealthGuard(HealthPolicy())
    assert all(guard.evaluate(sample(t,rss=rss)) is None for t in [0,30,120,600])


def test_gradual_low_memory_recovery_and_transient_reset():
    guard=HealthGuard(HealthPolicy())
    for t,available in [(0,12),(10,8),(20,5),(35,4),(40,9),(50,5),(70,4)]:
        assert guard.evaluate(sample(t,available)) is None
    assert guard.evaluate(sample(80,5))=='SYSTEM_MEMORY_PRESSURE_SUSTAINED'


@pytest.mark.parametrize('settings,duration,expected',[
    ({'available':5},30,'SYSTEM_MEMORY_PRESSURE_SUSTAINED'),
    ({'available':.5},3,'SYSTEM_MEMORY_CRITICAL'),
    ({'available':5,'commit':.99},15,'SYSTEM_COMMIT_PRESSURE_SUSTAINED'),
    ({'available':5,'notification':True},10,'WINDOWS_LOW_MEMORY_SUSTAINED'),
    ({'paging':11000,'stalled':100},60,'SEVERE_PAGING_WITHOUT_OUTPUT_PROGRESS')])
def test_sustained_pressure_requires_registered_duration(settings,duration,expected):
    guard=HealthGuard(HealthPolicy())
    assert guard.evaluate(sample(0,**settings)) is None
    assert guard.evaluate(sample(duration-.1,**settings)) is None
    assert guard.evaluate(sample(duration,**settings))==expected


def test_commit_and_paging_signals_do_not_stop_healthy_progress_alone():
    guard=HealthGuard(HealthPolicy())
    for t in [0,60,180]:
        assert guard.evaluate(sample(t,commit=.99,paging=11000,stalled=1)) is None


def test_missing_optional_counters_and_output_stall_do_not_fabricate_pressure():
    guard=HealthGuard(HealthPolicy())
    for t in [0,600]:assert guard.evaluate(sample(t,commit=None,paging=None,stalled=600)) is None


def test_sampler_records_native_health_file_growth_and_recovers(tmp_path):
    sampler=SystemSampler(tmp_path)
    try:
        first=sampler.sample(0)
        (tmp_path/'native.rst').write_bytes(b'actual unit-control bytes')
        growing=sampler.sample(1);stalled=sampler.sample(5)
        assert first['physical_RAM_bytes']>first['available_RAM_bytes']>0
        assert growing['output_file_bytes']['native.rst']==25
        assert growing['seconds_without_output_growth']==0 and stalled['seconds_without_output_growth']==4
        assert 'commit_limit_bytes' in growing and 'windows_low_memory' in growing
    finally:sampler.close()


def test_owned_normal_exit_and_disk_stop_without_rss_cap(tmp_path):
    result=bounded_run([sys.executable,'-c','print(42)'],tmp_path/'ok',timeout=10,rss_limit=None,
                       health_policy=HealthPolicy(),resource_sample_seconds=.05)
    assert result['status']=='PROCESS_EXITED' and result['returncode']==0
    assert result['rss_limit_bytes'] is None and result['resource_samples']
    assert result['system_before']['physical_RAM_bytes']>0
    stopped=bounded_run([sys.executable,'-c','import time;time.sleep(10)'],tmp_path/'disk',timeout=20,
                        rss_limit=None,health_policy=HealthPolicy(),min_disk_free=10**18)
    assert stopped['status']=='DISK_RESERVE_EXHAUSTED' and stopped['runtime_seconds']<5


def test_safe_emergency_guard_with_synthetic_low_ram(tmp_path):
    result=bounded_run([sys.executable,'-c','import time;time.sleep(10)'],tmp_path/'pressure',timeout=20,
        rss_limit=None,health_policy=HealthPolicy(available_reserve_bytes=10**18,reserve_seconds=0))
    assert result['status']=='SYSTEM_MEMORY_PRESSURE_SUSTAINED' and result['runtime_seconds']<5


@pytest.mark.parametrize('interrupt,status',[(False,'MONITOR_FAILURE'),(True,'CANCELLED')])
def test_monitor_error_or_user_cancel_terminates_only_owned_child(tmp_path,interrupt,status):
    def stop(_):
        if interrupt:raise KeyboardInterrupt()
        raise RuntimeError('intentional unit-control failure')
    result=bounded_run([sys.executable,'-c','import time;time.sleep(10)'],tmp_path/'stop',timeout=20,
                       rss_limit=None,health_policy=HealthPolicy(),stop_check=stop)
    assert result['status']==status and result['runtime_seconds']<5
