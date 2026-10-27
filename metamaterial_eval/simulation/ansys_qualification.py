"""v0.6.1 environment, small rectangle package and actual-evidence qualification.

Input lint and analytical references never establish a licensed solver PASS.
"""
import argparse
from dataclasses import replace
import csv
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import re
import time
import numpy as np
from shapely import box
from .config import CompressionConfig
from .mesh_generation import generate_mesh,save_mesh
from .mesh_remediation import POLICY_B
from .mesh_validation import validate_mesh
from .ansys_adapter import write_input
from .solver_execution import discover_solver,execute,file_hash
from .postprocessing import validate_output_hashes,read_numeric_csv
from .reporting import write_json
from .mechanical_metrics import compression_metrics

REVIEW_CHECKS=['node_coordinates','element_connectivity_and_midsides','PLANE183_type_and_keyopts',
    'material_ids_and_properties','thickness_and_force_units','boundary_components_and_DOFs',
    'dimensions_and_axes','converged_result_sets','contact_normals_and_gaps','contact_target_association']


def release_id(value):
    text=str(value).upper()
    m=re.search(r'(20\d{2})\s*R\s*([12])',text)
    if m:return f'{m[1]} R{m[2]}'
    m=re.fullmatch(r'V?(\d{2})([12])',text.strip())
    return f'20{m[1]} R{m[2]}' if m else None


def release_compatible(actual,expected=None):
    observed=release_id(actual)
    return bool(observed and (expected is None or observed==release_id(expected)))


def analytical_reference(config,strain):
    modulus=config.young_modulus if config.mode=='plane_stress' else config.young_modulus/(1-config.poisson_ratio**2)
    stress=modulus*np.asarray(strain,float)
    return {'effective_modulus_MPa':modulus,'nominal_stress_MPa':stress,
            'reaction_force_N':stress*config.width*config.thickness,
            'source':'ANALYTICAL_INFINITESIMAL_UNIAXIAL_NOT_ANSYS'}


def verify_derived_curve(raw_history,curve,config,converged_steps,contact_rows=None,contact_counts=None):
    """Pure numeric screen: derived CSV must agree with authenticated raw rows.

    This helper alone cannot establish an actual solver execution or import.
    """
    by_set={r['set']:r for r in raw_history}
    if len(by_set)!=len(raw_history):raise ValueError('Duplicate raw history sets')
    selected=[]
    for row in curve:
        raw=by_set.get(row['set'])
        if raw is None or (int(raw['load_step']),int(raw['substep'])) not in converged_steps:
            raise ValueError('Derived curve contains a missing or unconverged raw set')
        epsilon=-raw['top_uy_mm']/config.height
        sigma=raw['upper_rf_y_N']/(config.width*config.thickness)
        if not np.isclose(epsilon,row['engineering_compression_strain'],atol=1e-12,rtol=1e-10) or not np.isclose(sigma,row['nominal_compression_stress_MPa'],atol=1e-12,rtol=1e-10):
            raise ValueError('Derived curve differs from authenticated raw solver history')
        selected.append(raw)
    if not selected:raise ValueError('No corroborated actual curve rows')
    metrics=compression_metrics([r['top_uy_mm'] for r in selected],[r['upper_rf_y_N'] for r in selected],[r['lower_rf_y_N'] for r in selected],config)
    if not metrics['force_balance_pass']:raise ValueError('Authenticated raw reactions do not balance')
    if contact_rows is not None:
        for raw in selected:
            for pair in [1,2]:
                rows=[r for r in contact_rows if r['set']==raw['set'] and r['pair']==pair]
                if not rows or len({r['element'] for r in rows})!=len(rows):raise ValueError('Missing or duplicated actual contact rows')
                if contact_counts is not None and len(rows)!=contact_counts[pair]:raise ValueError('Actual contact element inventory incomplete')
                if any(r['status'] not in [0,1,2,3] or r['pressure_MPa']<0 or r['penetration_mm']>.001 for r in rows):
                    raise ValueError('Actual contact diagnostics violate registered criteria')
                if not any(r['status']>=2 and r['pressure_MPa']>0 for r in rows):raise ValueError('Actual platen contact did not transmit pressure')
    return metrics


def prepare_rectangle(output,mode='plane_stress'):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);started=time.perf_counter()
    # Same provisional full envelope/material as the pilot, deliberately small
    # solver mesh; minimum additional lateral constraint removes rigid drift.
    config=replace(CompressionConfig(),mode=mode,boundary_size=.512,bulk_size=1.28,
                   strains=(.0001,.0005,.001,.005))
    mesh=generate_mesh(box(0,0,config.width,config.height),config,policy=POLICY_B)
    quality,_=validate_mesh(mesh,box(0,0,config.width,config.height),config)
    if not quality['accepted']:raise RuntimeError('Small rectangle mesh failed independent checks')
    generated=output/'generated';generated.mkdir()
    for contact in [False,True]:
        stage='platen_contact' if contact else 'direct'
        manifest=write_input(generated/stage,mesh,config,contact=contact)
        manifest.update(schema='young-dawgs-v0.6.1-rectangle',benchmark_stage=stage,
                        dimensions_source='PROVISIONAL_NOT_MEASURED',
                        acceptance={'analytical_relative_error':.02,'force_balance_relative':.01,'penetration_mm':.001},
                        execution_order='direct_qualification_before_contact',solver_verification='NOT_EXECUTED')
        write_json(generated/stage/'input_manifest.json',manifest)
        save_mesh(mesh,generated/stage/'mesh.npz')
        write_json(output/(stage+'_transfer_lint.json'),json.loads((generated/stage/'transfer_lint.json').read_text()))
    reference=analytical_reference(config,config.strains)
    with (output/'ANALYTICAL_reference.csv').open('w',newline='') as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['source','strain','displacement_mm','nominal_stress_MPa','reaction_force_N'])
        for i,strain in enumerate(config.strains):
            w.writerow([reference['source'],strain,strain*config.height,reference['nominal_stress_MPa'][i],reference['reaction_force_N'][i]])
    write_json(output/'rectangle_manifest.json',{'schema':'young-dawgs-v0.6.1-rectangle-package',
        'config':config.manifest(),'mesh_quality':quality,'input_generation_seconds':time.perf_counter()-started,
        'solver_execution':'NOT_EXECUTED','analytical_modulus_MPa':reference['effective_modulus_MPa'],
        'requirements':['actual release review','licensed direct run and qualification','licensed platen contact run and qualification']})
    write_json(output/'MODEL_REVIEW_TEMPLATE.json',{'schema':'young-dawgs-model-review',
        'execution_receipt_sha256':'REPLACE_WITH_ACTUAL_RECEIPT_HASH','expected_release':'REPLACE_WITH_ACTUAL_RELEASE',
        'official_release_documentation_reviewed':False,'checks':{k:False for k in REVIEW_CHECKS},
        'notes':'Fill from actual NLIST/ELIST/material/real-constant/component/DOF/contact inventory and solver output; never from input lint alone.'})
    return quality


def environment_report(output,executable=None,expected_release=None,smoke=False):
    output=Path(output)
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True)
    detected=discover_solver(executable)
    packages={}
    for name in ['gmsh','ansys-mapdl-core','ansys-mechanical-core']:
        try:packages[name]=metadata.version(name)
        except metadata.PackageNotFoundError:packages[name]=None
    report={'schema':'young-dawgs-v0.6.1-ansys-environment','platform':platform.platform(),
        'executable':str(detected) if detected else None,'configured_release':expected_release,
        'actual_release':None,'interface':'MAPDL_batch' if detected else None,'packages':packages,
        'installation':'DETECTED_FILE_ONLY_NOT_EXECUTED' if detected else 'NOT_FOUND',
        'license':'NOT_TESTED','solver_execution':'NOT_EXECUTED','windows_execution':'NOT_EXECUTED' if os.name!='nt' else 'PENDING',
        'conventional_locations':{p:Path(p).exists() for p in ['/ansys_inc','/opt/ansys_inc','/usr/ansys_inc','/mnt/c/Program Files/ANSYS Inc']}}
    if detected is None:
        report.update(status='ANSYS_EXECUTION_BLOCKED',reason='No MAPDL executable on PATH, explicit path/ANSYS_EXECUTABLE/AWP_ROOT selectors or conventional locations',license='NOT_TESTED_NO_SOLVER')
    elif not smoke:
        report.update(status='DETECTED_NOT_LICENSE_OR_EXECUTION_VERIFIED',reason='Run --smoke for a bounded licensed direct rectangle attempt')
    else:
        prepare_rectangle(output/'generated/smoke_package')
        receipt=execute(output/'generated/smoke_package/generated/direct',output/'generated/smoke_execution',detected,timeout=120)
        actual=release_id(receipt.get('solver_version'))
        version_match=release_compatible(receipt.get('solver_version'),expected_release)
        observed=receipt.get('status')=='EXECUTED_PENDING_IMPORT_CONTACT_AND_NUMERIC_VALIDATION' and version_match
        report['status']='LICENSED_EXECUTION_OBSERVED_PENDING_MODEL_QUALIFICATION' if observed else 'ANSYS_EXECUTION_BLOCKED'
        report['reason']=receipt.get('status');report['actual_release']=actual
        report['license']='LICENSED_ANALYSIS_OBSERVED' if observed else receipt.get('license','NOT_VERIFIED')
        report['solver_execution']=receipt.get('status');report['receipt_ref']='generated/smoke_execution/solver_status.json'
        if expected_release and not version_match:report['reason']='UNEXPECTED_OR_UNRECOGNIZED_SOLVER_RELEASE'
    write_json(output/'environment.json',report)
    return report


def evidence_token(path):
    path=Path(path).resolve()
    return {'report_path':str(path),'sha256':file_hash(path)}


def checked_qualification(token,required_stage,expected_config=None):
    if not isinstance(token,dict) or not token.get('report_path') or not token.get('sha256'):
        raise ValueError('Missing receipt-linked qualification report')
    path=Path(token['report_path'])
    if not path.is_file() or file_hash(path)!=token['sha256']:raise ValueError('Modified or missing qualification report')
    report=json.loads(path.read_text())
    if report.get('status')!='SOLVER_VERIFIED' or report.get('benchmark_stage')!=required_stage:
        raise ValueError('Required actual benchmark stage is unqualified')
    execution=(path.parent/report['execution_relative_path']).resolve()
    receipt_path=execution/'solver_status.json'
    if file_hash(receipt_path)!=report['solver_receipt_sha256']:raise ValueError('Modified actual execution receipt')
    receipt=json.loads(receipt_path.read_text());validate_output_hashes(execution,receipt)
    if receipt.get('status')!='EXECUTED_PENDING_IMPORT_CONTACT_AND_NUMERIC_VALIDATION':
        raise ValueError('Required actual solver run did not complete cleanly')
    for path_key,hash_key in [('model_review_relative_path','model_review_sha256'),('numeric_summary_relative_path','numeric_summary_sha256')]:
        artifact=path.parent/report[path_key]
        if not artifact.is_file() or file_hash(artifact)!=report[hash_key]:
            raise ValueError('Modified or missing actual benchmark review/numerical summary')
    if expected_config:
        for key in ['width','height','thickness','young_modulus','poisson_ratio','mode','units']:
            if report['config'][key]!=expected_config[key]:raise ValueError(f'Benchmark modeling mismatch: {key}')
    return report


def qualify(execution,numeric_results,review,expected_release,output):
    execution,numeric_results,review,output=map(Path,[execution,numeric_results,review,output])
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True)
    try:
        receipt=json.loads((execution/'solver_status.json').read_text());validate_output_hashes(execution,receipt)
        if receipt['status']!='EXECUTED_PENDING_IMPORT_CONTACT_AND_NUMERIC_VALIDATION':raise ValueError('Solver did not complete cleanly; preserve partial converged data separately')
        manifest=json.loads((execution/'input_manifest.json').read_text())
        if receipt.get('outputs',{}).get('input_manifest.json')!=file_hash(execution/'input_manifest.json'):
            raise ValueError('Input manifest not authenticated by execution receipt')
        if receipt['input_sha256']!=file_hash(execution/'compression.inp'):raise ValueError('Executed APDL input changed')
        actual=release_id(receipt.get('solver_version'));wanted=release_id(expected_release)
        if not wanted or not release_compatible(receipt.get('solver_version'),expected_release):raise ValueError('Incorrect/unrecognized actual solver release')
        verified=json.loads(review.read_text())
        if verified.get('execution_receipt_sha256')!=file_hash(execution/'solver_status.json'):
            raise ValueError('Model inventory review is not linked to this actual run')
        if release_id(verified.get('expected_release'))!=actual or verified.get('official_release_documentation_reviewed') is not True:
            raise ValueError('Actual-release documentation and model review required')
        if any(verified.get('checks',{}).get(k) is not True for k in REVIEW_CHECKS):
            raise ValueError('Full model import/material/contact inventory review incomplete')
        numeric=json.loads((numeric_results/'mechanical_summary.json').read_text())
        if numeric.get('solver_receipt_sha256')!=file_hash(execution/'solver_status.json'):
            raise ValueError('Numerical extraction belongs to a different solver run')
        if numeric.get('status')!='NUMERIC_SCREEN_PASS_PENDING_MODEL_REVIEW' or not numeric.get('all_requested_stages_achieved'):
            raise ValueError('Incomplete or invalid actual benchmark response')
        fields={k:manifest['config'][k] for k in CompressionConfig.__dataclass_fields__};fields['strains']=tuple(fields['strains'])
        config=CompressionConfig(**fields)
        curve=read_numeric_csv(numeric_results/'stress_strain.csv',['set','pseudo_time','engineering_compression_strain','nominal_compression_stress_MPa'])
        history=read_numeric_csv(execution/'history.csv',['set','pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'])
        log=(execution/'solver.out').read_text(errors='replace')
        converged={(int(a),int(b)) for a,b in re.findall(r'LOAD STEP\s+(\d+)\s+SUBSTEP\s+(\d+)\s+COMPLETED',log,re.IGNORECASE)}
        contact_rows=None;contact_counts=None
        if manifest['platen_contact']:
            if receipt.get('outputs',{}).get('contact_fields.csv')!=file_hash(execution/'contact_fields.csv'):
                raise ValueError('Missing or modified actual contact output')
            contact_rows=read_numeric_csv(execution/'contact_fields.csv',['set','pseudo_time','pair','element','status','pressure_MPa','penetration_mm','gap_mm'])
            contact_counts={1:len(manifest['contact_plan']['bottom']['edges']),2:len(manifest['contact_plan']['top']['edges'])}
        verify_derived_curve(history,curve,config,converged,contact_rows,contact_counts)
        strain=np.array([r['engineering_compression_strain'] for r in curve]);stress=np.array([r['nominal_compression_stress_MPa'] for r in curve])
        reference=analytical_reference(config,strain)
        errors=np.abs(stress-reference['nominal_stress_MPa'])/np.maximum(np.abs(reference['nominal_stress_MPa']),1e-12)
        if np.any(errors>.02):raise ValueError('Actual response exceeds frozen analytical tolerance')
        if not numeric.get('force_balance_pass'):raise ValueError('Actual reactions do not balance')
        if manifest['platen_contact'] and not numeric.get('platen_contact_numeric_screen'):raise ValueError('Platen engagement/penetration unverified')
        report={'schema':'young-dawgs-v0.6.1-qualified-benchmark','status':'SOLVER_VERIFIED',
            'benchmark_stage':'platen_contact' if manifest['platen_contact'] else 'direct','config':config.manifest(),
            'actual_release':actual,'execution_relative_path':os.path.relpath(execution.resolve(),output.resolve()),
            'solver_receipt_sha256':file_hash(execution/'solver_status.json'),'model_review_sha256':file_hash(review),
            'model_review_relative_path':os.path.relpath(review.resolve(),output.resolve()),
            'max_relative_analytical_error':float(errors.max()),'actual_curve_points':len(curve),
            'numeric_summary_sha256':file_hash(numeric_results/'mechanical_summary.json'),
            'numeric_summary_relative_path':os.path.relpath((numeric_results/'mechanical_summary.json').resolve(),output.resolve()),
            'internal_self_contact':'UNQUALIFIED','mechanical_mesh_convergence':'UNQUALIFIED',
            'paper_readiness':'UNQUALIFIED','llm_optimization':'NOT_IMPLEMENTED'}
        write_json(output/'qualification.json',report);return report
    except (ValueError,KeyError,FileNotFoundError) as exc:
        report={'schema':'young-dawgs-v0.6.1-qualified-benchmark','status':'BLOCKED_OR_FAILED','reason':str(exc),
                'mechanical_output_verified':False,'llm_performance_eligible':False}
        write_json(output/'qualification.json',report);return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    env=commands.add_parser('environment');env.add_argument('--executable',type=Path);env.add_argument('--smoke',action='store_true');env.add_argument('--expected-release')
    prepare=commands.add_parser('prepare');prepare.add_argument('--mode',choices=['plane_stress','plane_strain'],default='plane_stress')
    q=commands.add_parser('qualify');q.add_argument('--execution',type=Path,required=True);q.add_argument('--numeric-results',type=Path,required=True);q.add_argument('--review',type=Path,required=True);q.add_argument('--expected-release',required=True)
    for command in [env,prepare,q]:command.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='prepare':prepare_rectangle(args.output,args.mode)
    elif args.command=='environment':print(environment_report(args.output,args.executable,args.expected_release,args.smoke)['status'])
    else:print(qualify(args.execution,args.numeric_results,args.review,args.expected_release,args.output)['status'])


if __name__=='__main__':main()
