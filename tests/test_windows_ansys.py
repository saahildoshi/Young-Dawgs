"""Unit controls only; licensed integration evidence is recorded separately."""
import os
from pathlib import Path
import sys
import pytest
from metamaterial_eval.simulation.windows_ansys import installations, bounded_run
from metamaterial_eval.simulation.solver_execution import discover_solver, solver_release
from metamaterial_eval.simulation.solver_execution import execute, classify_log


def test_release_241_environment_discovery(tmp_path, monkeypatch):
    root=tmp_path/'v241'
    solver=root/'ansys/bin/winx64/ANSYS241.exe'
    solver.parent.mkdir(parents=True);solver.write_text('unit control, never executed')
    monkeypatch.delenv('ANSYS_EXECUTABLE',raising=False)
    for name in list(os.environ):
        if name.startswith('AWP_ROOT'):monkeypatch.delenv(name)
    monkeypatch.setenv('AWP_ROOT241',str(root))
    monkeypatch.setattr('shutil.which',lambda _:None)
    assert discover_solver()==solver
    found=installations({'AWP_ROOT241':str(root)},tmp_path/'programs')
    assert found[0]['mapdl']==str(solver.resolve())
    assert found[0]['mechanical'] is None


def test_discovery_rejects_invalid_paths_and_unknown_release(tmp_path):
    assert installations({'AWP_ROOT241':str(tmp_path/'absent')},tmp_path)==[]
    assert installations({'AWP_ROOT241':str(tmp_path/'v241')},tmp_path)[0]['mapdl'] is None


@pytest.mark.parametrize('banner,expected',[
    ('! verify installed release\nANSYS MAPDL 2024 R1', '2024 R1'),
    ('/COM,ANSYS RELEASE 2024 R1 BUILD 24.1','2024 R1'),
    ('! verify installed release\n2 ! Actual 2D',None)])
def test_release_banner_excludes_input_comments(banner,expected):
    assert solver_release(banner)==expected


def test_owned_process_exit_and_timeout(tmp_path):
    result=bounded_run([sys.executable,'-c','print(42)'],tmp_path/'ok',timeout=10)
    assert result['returncode']==0 and result['status']=='PROCESS_EXITED'
    result=bounded_run([sys.executable,'-c','import time; time.sleep(20)'],tmp_path/'timeout',timeout=.3)
    assert result['status']=='TIMEOUT' and result['runtime_seconds']<10
    with pytest.raises(FileExistsError):
        bounded_run([sys.executable,'-c','pass'],tmp_path/'ok')


def test_missing_monitor_dependency_blocks_before_solver_launch(tmp_path,monkeypatch):
    import json
    source=tmp_path/'input';source.mkdir()
    (source/'compression.inp').write_text('unit control, never executed')
    (source/'input_manifest.json').write_text(json.dumps({'purpose':'rectangle_benchmark',
        'mesh_sha256':'unit-control','platen_contact':False}))
    fake=tmp_path/'not-a-solver.exe';fake.write_text('unit control')
    def missing(*args,**kwargs):raise ImportError('psutil unit control')
    monkeypatch.setattr('metamaterial_eval.simulation.windows_ansys.bounded_run',missing)
    result=execute(source,tmp_path/'output',executable=fake)
    assert result['status']=='MISSING_PROCESS_MONITOR_DEPENDENCY'
    assert result['license']=='NOT_CHECKED'


@pytest.mark.parametrize('message,state',[
    ('Insufficient memory','MEMORY_EXHAUSTION'),
    ('Element 10 is highly distorted','ELEMENT_DISTORTION_OR_INSTABILITY')])
def test_resource_and_distortion_failures(message,state):
    assert classify_log(message,1,False,False)==state


@pytest.mark.parametrize('setting,state',[
    ({'min_disk_free':10**18},'DISK_RESERVE_EXHAUSTED'),
    ({'min_available_ram':10**18},'OS_RAM_RESERVE_REACHED')])
def test_owned_job_stops_at_operating_system_reserve(tmp_path,setting,state):
    result=bounded_run([sys.executable,'-c','import time;time.sleep(10)'],tmp_path/'run',timeout=20,**setting)
    assert result['status']==state and result['runtime_seconds']<5
