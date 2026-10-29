"""Windows ANSYS discovery and bounded owned-process execution (no license secrets)."""
import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import time

from .reporting import write_json
from .solver_execution import file_hash


def installations(environ=None, program_files=None):
    environ = os.environ if environ is None else environ
    roots = {Path(value) for key, value in environ.items()
             if re.fullmatch(r'AWP_ROOT\d{3}', key)}
    base = Path(program_files or environ.get('ProgramFiles', 'C:/Program Files')) / 'ANSYS Inc'
    if base.is_dir():
        roots.update(p for p in base.glob('v[0-9][0-9][0-9]') if p.is_dir())
    result = []
    for root in sorted(roots):
        match = re.fullmatch(r'v(\d{3})', root.name, re.I)
        if not match:
            continue
        release = match[1]
        paths = {'workbench': root/'Framework/bin/Win64/RunWB2.exe',
                 'mechanical': root/'aisol/bin/winx64/AnsysWBU.exe',
                 'mapdl': root/f'ansys/bin/winx64/ANSYS{release}.exe'}
        result.append({'release_selector': release, 'root': str(root.resolve()),
                       **{k: str(p.resolve()) if p.is_file() else None for k, p in paths.items()}})
    return result


def bounded_run(command, directory, *, timeout=180, rss_limit=8*1024**3, prepared=False,
                min_disk_free=0, min_available_ram=0, stop_check=None):
    """Supervise only the new process and descendants; preserve logs on every exit."""
    import psutil
    directory = Path(directory).resolve()
    if prepared:
        if (directory/'process_receipt.json').exists():
            raise FileExistsError('Refusing to rerun an existing process directory')
    else:
        directory.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    receipt = {'command': list(map(str, command)), 'started_utc': datetime.now(timezone.utc).isoformat(),
               'timeout_seconds': timeout, 'rss_limit_bytes': rss_limit, 'peak_tree_rss_bytes': 0,
               'run_directory': str(directory), 'returncode': None}
    receipt.update(min_disk_free_bytes=min_disk_free,min_available_ram_bytes=min_available_ram)
    flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    with (directory/'launcher.log').open('w') as log:
        try:
            process = subprocess.Popen(command, cwd=directory, stdout=log, stderr=subprocess.STDOUT,
                                       creationflags=flags)
            owned = psutil.Process(process.pid)
            state = None
            while process.poll() is None:
                try:
                    tree = [owned, *owned.children(recursive=True)]
                    rss = sum(p.memory_info().rss for p in tree if p.is_running())
                    receipt['peak_tree_rss_bytes'] = max(receipt['peak_tree_rss_bytes'], rss)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                if time.perf_counter()-started > timeout:
                    state = 'TIMEOUT'
                if receipt['peak_tree_rss_bytes'] > rss_limit:
                    state = 'MEMORY_BUDGET_EXCEEDED'
                if min_disk_free and shutil.disk_usage(directory).free<min_disk_free:
                    state='DISK_RESERVE_EXHAUSTED'
                if min_available_ram and psutil.virtual_memory().available<min_available_ram:
                    state='OS_RAM_RESERVE_REACHED'
                if stop_check and not state:state=stop_check(directory)
                if state:
                    for child in reversed(owned.children(recursive=True)):
                        try:
                            child.kill()
                        except psutil.NoSuchProcess:
                            pass
                    try:
                        owned.kill()
                    except psutil.NoSuchProcess:
                        pass
                    break
                time.sleep(.1)
            receipt.update(returncode=process.wait(), status=state or 'PROCESS_EXITED')
        except OSError as exc:
            receipt.update(status='LAUNCH_FAILURE', error=str(exc))
    receipt['runtime_seconds'] = time.perf_counter()-started
    receipt['artifacts'] = {p.name: {'bytes': p.stat().st_size, 'sha256': file_hash(p)}
                            for p in directory.iterdir() if p.is_file()}
    write_json(directory/'process_receipt.json', receipt)
    return receipt


def audit(output):
    import psutil
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    packages = {}
    for name in ['numpy','scipy','scikit-image','matplotlib','pytest','shapely','gmsh','psutil',
                 'ansys-mechanical-core','ansys-mapdl-core']:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    memory = psutil.virtual_memory()
    report = {'schema': 'young-dawgs-v0.6.2-windows-environment',
              'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'platform': platform.platform(),
              'python': platform.python_version(), 'installations': installations(),
              'physical_cores': psutil.cpu_count(logical=False), 'logical_processors': os.cpu_count(),
              'physical_ram_bytes': memory.total, 'available_ram_bytes': memory.available,
              'disk_free_bytes': shutil.disk_usage(output.resolve()).free, 'packages': packages,
              'license': 'NOT_TESTED', 'mechanical_launch': 'NOT_TESTED',
              'external_model_import': 'NOT_TESTED', 'secrets': 'license environment and files not read'}
    write_json(output/'environment.json', report)
    return report


def workbench_probe(output, executable):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    journal = output/'probe.wbjn'
    script = "open(" + repr(str(output/'mechanical_query.txt')) + ", 'w').write(str(ExtAPI.DataModel.Project.Model.Analyses.Count))"
    journal.write_text('SetScriptVersion(Version="24.1.0")\n'
                       'system = GetTemplate(TemplateName="Static Structural", Solver="ANSYS").CreateSystem()\n'
                       'model = system.GetContainer(ComponentName="Model")\n'
                       'model.Edit(Interactive=False)\n'
                       'model.SendCommand(Language="Python", Command=' + repr(script) + ')\n'
                       'model.Exit()\n'
                       'open(' + repr(str(output/'workbench_query.txt')) + ', "w").write("JOURNAL_COMPLETED")\n')
    receipt = bounded_run([str(executable), '-B', '-R', str(journal)], output/'generated', timeout=120)
    receipt['workbench_journal_completed'] = (output/'workbench_query.txt').exists()
    receipt['mechanical_embedded_script_completed'] = (output/'mechanical_query.txt').exists()
    write_json(output/'probe_receipt.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['audit','workbench-probe'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--executable', type=Path)
    args = parser.parse_args()
    result = audit(args.output) if args.action == 'audit' else workbench_probe(args.output, args.executable)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
