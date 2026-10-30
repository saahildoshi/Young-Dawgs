"""Auditable batch execution with explicit installation/license/output failure states."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from .reporting import write_json


def file_hash(path):
    """Hash large solver artifacts without a second file-sized RAM allocation."""
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''):digest.update(block)
    return digest.hexdigest()


def discover_solver(executable=None):
    executable=executable or os.environ.get('ANSYS_EXECUTABLE')
    if executable:
        path=Path(executable)
        return path.resolve() if path.is_file() else None
    releases=sorted({key[8:] for key in os.environ if re.fullmatch(r'AWP_ROOT\d{3}',key)} |
                    {'261','252','251','242','241'},reverse=True)
    for name in [*(f'ansys{release}' for release in releases),'mapdl']:
        found=shutil.which(name)
        if found:return Path(found)
    # Read only path selectors, never license server values or credential files.
    for release in releases:
        value=os.environ.get('AWP_ROOT'+release)
        if value:
            for suffix in [f'ansys/bin/winx64/ANSYS{release}.exe',f'ansys/bin/ansys{release}']:
                path=Path(value)/suffix
                if path.is_file():return path
    return None


def has_negative_pivots(text):
    """Performance logs also print monitoring enabled and zero counts."""
    counts=re.findall(r'(?:#\s*of\s+negative pivots|number of negative pivots encountered)\s*=\s*(\d+)',text,re.I)
    return any(int(n)>0 for n in counts) or bool(re.search(r'\b(?:a|an) negative pivot (?:value|was|has|at)',text,re.I))


def solver_warnings(text):
    """Windows solver logs can contain blank lines between header and message."""
    return [s.strip() for s in re.findall(r'\*\*\*\s*WARNING\s*\*\*\*[^\n]*\n\s*([^\n]+)',text,re.I)]


def classify_log(text,returncode,has_result,has_history):
    lower=text.lower()
    if re.search(r'license.*(?:fail|denied|unavailable|not available)|(?:fail|unable).*license|licensed number.*exceeded|ansys license manager error|no licenses? available',lower):
        return 'LICENSE_FAILURE'
    if re.search(r'not enough memory|insufficient memory|out of memory|unable to allocate',lower):
        return 'MEMORY_EXHAUSTION'
    if re.search(r'element.*(?:highly distorted|excessive distortion)',lower) or has_negative_pivots(text):
        return 'ELEMENT_DISTORTION_OR_INSTABILITY'
    if returncode!=0:return 'SOLVER_PROCESS_FAILURE'
    if re.search(r'\*\*\*\s*(?:error|fatal)\s*\*\*\*|solution.*not converged|unconverged solution|convergence failure',lower):
        return 'SOLVER_ERROR_OR_NONCONVERGENCE'
    if not has_result or not has_history:return 'MISSING_SOLVER_OUTPUT'
    return 'EXECUTED_PENDING_IMPORT_CONTACT_AND_NUMERIC_VALIDATION'


def solver_release(text):
    """Recognize actual banners, never the word release in a deck comment."""
    match=re.search(r'(?:ANSYS\s+(?:MAPDL\s+)?|RELEASE\s+)(20\d{2}\s+R[12])',text,re.I)
    return match.group(1).upper() if match else None


def execute(input_folder, output_folder, executable=None, timeout=3600, benchmark_evidence=None):
    source=Path(input_folder);output=Path(output_folder)
    if output.exists():raise FileExistsError(f'Refusing to overwrite solver run: {output}')
    output.mkdir(parents=True)
    manifest=json.loads((source/'input_manifest.json').read_text())
    solver=discover_solver(executable)
    status={'status':'NOT_EXECUTED','solver_version':None,'license':'NOT_CHECKED',
            'input_sha256':file_hash(source/'compression.inp'),'purpose':manifest['purpose'],
            'mesh_sha256':manifest['mesh_sha256']}
    if solver is None:
        status.update(status='MISSING_ANSYS_INSTALLATION',license='NOT_TESTED_NO_SOLVER')
        write_json(output/'solver_status.json',status)
        return status
    # Contact qualification must follow a real direct benchmark. Strings in an
    # arbitrary JSON file cannot substitute for receipt-linked solver evidence.
    from .ansys_qualification import checked_qualification
    if manifest['purpose']=='rectangle_benchmark' and manifest.get('platen_contact'):
        try:
            direct=checked_qualification(benchmark_evidence,'direct',manifest['config'])
            if direct['config']['strains']!=manifest['config']['strains']:
                raise ValueError('Direct/contact target strain schedules differ')
        except (ValueError,KeyError,FileNotFoundError) as exc:
            status.update(status='BLOCKED_MISSING_DIRECT_BENCHMARK_EVIDENCE',reason=str(exc))
            write_json(output/'solver_status.json',status)
            return status
    if manifest['purpose']=='microstructure_pilot':
        evidence=benchmark_evidence or {}
        try:
            checked_qualification(evidence.get('direct'),'direct',manifest['config'])
            checked_qualification(evidence.get('contact'),'platen_contact',manifest['config'])
            protocol=evidence.get('pilot_protocol',{})
            path=Path(protocol.get('path',''))
            if not path.is_file() or file_hash(path)!=protocol.get('sha256'):
                raise ValueError('Missing frozen microstructure pilot protocol')
            frozen=json.loads(path.read_text())
            if frozen.get('mesh_sha256')!=manifest['mesh_sha256'] or frozen.get('strains')!=manifest['config']['strains']:
                raise ValueError('Pilot protocol mesh/loading mismatch')
        except (ValueError,KeyError,FileNotFoundError) as exc:
            status.update(status='BLOCKED_MISSING_RECTANGLE_EVIDENCE',reason=str(exc))
            write_json(output/'solver_status.json',status)
            return status
    for name in ['compression.inp','input_manifest.json','extract_fields.mac','mesh.npz']:
        if (source/name).exists():shutil.copy2(source/name,output/name)
    command=[str(solver),'-b','-j','compression','-i','compression.inp','-o','solver.out','-np','1','-smp','-m','2048']
    started=time.perf_counter()
    try:
        from .windows_ansys import bounded_run
        process=bounded_run(command,output,timeout=timeout,prepared=True)
        text=(output/'launcher.log').read_text(errors='replace')
        if (output/'solver.out').exists():text+='\n'+(output/'solver.out').read_text(errors='replace')
        state=classify_log(text,process['returncode'],(output/'compression.rst').is_file(),(output/'history.csv').is_file())
        if process['status']!='PROCESS_EXITED':state=process['status']
        status.update(status=state,returncode=process['returncode'],solver_version=solver_release(text),
                      license='CHECKOUT_FAILED' if state=='LICENSE_FAILURE' else 'NOT_INDEPENDENTLY_VERIFIED',
                      runtime_seconds=time.perf_counter()-started,
                      started_utc=process['started_utc'],peak_tree_rss_bytes=process['peak_tree_rss_bytes'])
    except subprocess.TimeoutExpired:
        status.update(status='SOLVER_TIMEOUT',runtime_seconds=time.perf_counter()-started)
    except OSError as exc:
        status.update(status='SOLVER_LAUNCH_FAILURE',error=str(exc))
    except ImportError as exc:
        status.update(status='MISSING_PROCESS_MONITOR_DEPENDENCY',error=str(exc))
    status['outputs']={p.name:file_hash(p) for p in output.iterdir() if p.is_file() and p.name not in ['solver_status.json']}
    status['command']=command
    write_json(output/'solver_status.json',status)
    return status
