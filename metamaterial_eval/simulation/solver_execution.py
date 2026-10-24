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


def file_hash(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def discover_solver(executable=None):
    if executable:
        path=Path(executable)
        return path.resolve() if path.is_file() else None
    for name in ['ansys261','ansys252','ansys251','ansys242','mapdl']:
        found=shutil.which(name)
        if found:return Path(found)
    # Read only path selectors, never license server values or credential files.
    for release in ['261','252','251','242']:
        value=os.environ.get('AWP_ROOT'+release)
        if value:
            for suffix in [f'ansys/bin/winx64/ANSYS{release}.exe',f'ansys/bin/ansys{release}']:
                path=Path(value)/suffix
                if path.is_file():return path
    return None


def classify_log(text,returncode,has_result,has_history):
    lower=text.lower()
    if re.search(r'license.*(?:fail|denied|unavailable|not available)|(?:fail|unable).*license|licensed number.*exceeded',lower):
        return 'LICENSE_FAILURE'
    if returncode!=0:return 'SOLVER_PROCESS_FAILURE'
    if re.search(r'\*\*\*\s*(?:error|fatal)\s*\*\*\*|solution.*not converged|unconverged solution|convergence failure',lower):
        return 'SOLVER_ERROR_OR_NONCONVERGENCE'
    if not has_result or not has_history:return 'MISSING_SOLVER_OUTPUT'
    return 'EXECUTED_PENDING_IMPORT_CONTACT_AND_NUMERIC_VALIDATION'


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
    if manifest['purpose']=='microstructure_pilot':
        evidence=benchmark_evidence or {}
        required=['import_acceptance','material_acceptance','direct_rectangle_acceptance','platen_contact_acceptance']
        if any(evidence.get(k)!='SOLVER_VERIFIED' for k in required) or not evidence.get('solver_receipt_sha256'):
            status['status']='BLOCKED_MISSING_RECTANGLE_EVIDENCE'
            write_json(output/'solver_status.json',status)
            return status
    for name in ['compression.inp','input_manifest.json','extract_fields.mac']:
        if (source/name).exists():shutil.copy2(source/name,output/name)
    command=[str(solver),'-b','-j','compression','-i','compression.inp','-o','solver.out','-np','1']
    started=time.perf_counter()
    try:
        with (output/'launcher.log').open('w') as log:
            result=subprocess.run(command,cwd=output,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,check=False)
        text=(output/'launcher.log').read_text(errors='replace')
        if (output/'solver.out').exists():text+='\n'+(output/'solver.out').read_text(errors='replace')
        state=classify_log(text,result.returncode,(output/'compression.rst').is_file(),(output/'history.csv').is_file())
        version=re.search(r'RELEASE\s+[^\r\n]+',text,re.IGNORECASE)
        status.update(status=state,returncode=result.returncode,solver_version=version.group(0) if version else None,
                      license='CHECKOUT_FAILED' if state=='LICENSE_FAILURE' else 'NOT_INDEPENDENTLY_VERIFIED',
                      runtime_seconds=time.perf_counter()-started)
    except subprocess.TimeoutExpired:
        status.update(status='SOLVER_TIMEOUT',runtime_seconds=time.perf_counter()-started)
    except OSError as exc:
        status.update(status='SOLVER_LAUNCH_FAILURE',error=str(exc))
    status['outputs']={p.name:file_hash(p) for p in output.iterdir() if p.is_file() and p.name not in ['solver_status.json']}
    status['command']=command
    write_json(output/'solver_status.json',status)
    return status
