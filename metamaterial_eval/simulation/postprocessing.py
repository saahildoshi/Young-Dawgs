"""Quarantine unverified outputs; preserve partial converged measurements."""
import csv
import json
from pathlib import Path
import re
import numpy as np
from .config import CompressionConfig
from .solver_execution import file_hash
from .mechanical_metrics import compression_metrics,effective_stiffness,selected_snapshots
from .reporting import write_json


def read_numeric_csv(path, columns):
    with Path(path).open(newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=columns:raise ValueError(f'CSV schema mismatch: {Path(path).name}')
        data=[{k:float(v) for k,v in row.items()} for row in reader]
    if not data or not np.isfinite([[r[k] for k in columns] for r in data]).all():
        raise ValueError(f'Empty or nonfinite solver data: {Path(path).name}')
    return data


def validate_output_hashes(folder,receipt):
    if receipt.get('status') in ('NOT_EXECUTED','MISSING_ANSYS_INSTALLATION') or not receipt.get('solver_version'):
        raise ValueError('No authenticated actual solver execution/version')
    for name in ['compression.rst','solver.out','history.csv','model_inventory.txt','nodal_fields.csv']:
        expected=receipt.get('outputs',{}).get(name)
        if not expected or not (folder/name).is_file() or file_hash(folder/name)!=expected:
            raise ValueError(f'Missing or modified actual solver output: {name}')


def postprocess(folder,output):
    folder,output=Path(folder),Path(output)
    if output.exists():raise FileExistsError(f'Refusing to overwrite results: {output}')
    output.mkdir(parents=True)
    try:
        receipt=json.loads((folder/'solver_status.json').read_text())
        manifest=json.loads((folder/'input_manifest.json').read_text())
        validate_output_hashes(folder,receipt)
        fields={k:manifest['config'][k] for k in CompressionConfig.__dataclass_fields__}
        fields['strains']=tuple(fields['strains']);config=CompressionConfig(**fields)
        history=read_numeric_csv(folder/'history.csv',['set','pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'])
        log=(folder/'solver.out').read_text(errors='replace')
        converged={(int(a),int(b)) for a,b in re.findall(r'LOAD STEP\s+(\d+)\s+SUBSTEP\s+(\d+)\s+COMPLETED',log,re.IGNORECASE)}
        rows=[r for r in history if (int(r['load_step']),int(r['substep'])) in converged]
        if not rows:raise ValueError('No history sets corroborated by solver convergence log')
        if any(r['set']!=int(r['set']) or r['set']<1 or r['load_step']!=int(r['load_step']) or r['substep']!=int(r['substep']) for r in rows):
            raise ValueError('Nonintegral result-set identifiers')
        if any(b['pseudo_time']<=a['pseudo_time'] for a,b in zip(rows,rows[1:])):
            raise ValueError('Solver stages are unordered or duplicated')
        m=compression_metrics([r['top_uy_mm'] for r in rows],[r['upper_rf_y_N'] for r in rows],[r['lower_rf_y_N'] for r in rows],config)
        nodal=read_numeric_csv(folder/'nodal_fields.csv',['set','pseudo_time','node','ux_mm','uy_mm','syy_MPa','seqv_MPa','elastic_eyy'])
        setids={int(r['set']) for r in rows}
        for sid in setids:
            ids=[r['node'] for r in nodal if int(r['set'])==sid]
            if sorted(ids)!=list(range(1,manifest['specimen_nodes']+1)):
                raise ValueError(f'Incomplete/duplicate nodal field set {sid}')
        contacts=[];contact_valid=not manifest['platen_contact'];penetration=None
        if manifest['platen_contact']:
            expected=receipt.get('outputs',{}).get('contact_fields.csv')
            if not expected or file_hash(folder/'contact_fields.csv')!=expected:raise ValueError('Missing/modified contact output')
            contacts=read_numeric_csv(folder/'contact_fields.csv',['set','pseudo_time','pair','element','status','pressure_MPa','penetration_mm','gap_mm'])
            contacts=[r for r in contacts if int(r['set']) in setids]
            penetration=max((max(0,r['penetration_mm']) for r in contacts),default=float('inf'))
            contact_valid=penetration<=.001
            for sid in setids:
                for pair in [1,2]:
                    subset=[r for r in contacts if int(r['set'])==sid and r['pair']==pair]
                    contact_valid=contact_valid and bool(subset) and any(r['status']>=2 and r['pressure_MPa']>0 for r in subset)
            contact_valid=contact_valid and all(r['status'] in [0,1,2,3] and r['pressure_MPa']>=-1e-8 for r in contacts)
        # Import/material acceptance still requires solver-side inventory review.
        inventory=(folder/'model_inventory.txt').read_text(errors='replace')
        counts=re.search(r'TRANSFER_COUNTS\s+(\d+)\.?\s+(\d+)\.?',inventory)
        transfer_ok=bool(counts and tuple(map(int,counts.groups()))==(manifest['total_nodes'],manifest['total_elements']))
        numeric_valid=m['force_balance_pass'] and contact_valid and transfer_ok
        achieved=m['engineering_compression_strain'];stress=m['nominal_compression_stress_MPa']
        data_output=output if numeric_valid else output/'quarantine'
        data_output.mkdir(parents=True,exist_ok=True)
        for name,columns in [('force_displacement.csv',['set','pseudo_time','compression_displacement_mm','upper_rf_y_N','lower_rf_y_N']),
                             ('stress_strain.csv',['set','pseudo_time','engineering_compression_strain','nominal_compression_stress_MPa'])]:
            with (data_output/name).open('w',newline='') as stream:
                writer=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n');writer.writeheader()
                for i,row in enumerate(rows):
                    data={**row,**{k:float(v[i]) for k,v in m.items() if isinstance(v,np.ndarray)}}
                    writer.writerow({k:data[k] for k in columns})
        modulus=effective_stiffness(achieved,stress,config.young_modulus) if numeric_valid else {'status':'QUARANTINED','value_MPa':None}
        completed=all(np.any(np.isclose(achieved,target,atol=1e-6,rtol=0)) for target in config.strains)
        report={'status':'NUMERIC_SCREEN_PASS_PENDING_MODEL_REVIEW' if numeric_valid else 'QUARANTINED_INVALID_MECHANICS',
                'solver_receipt_sha256':file_hash(folder/'solver_status.json'),'force_balance_pass':m['force_balance_pass'],
                'platen_contact_numeric_screen':bool(contact_valid),'maximum_contact_penetration_mm':penetration,
                'transfer_count_screen':transfer_ok,'full_import_material_review':'REQUIRED_NOT_INFERRED_FROM_COUNTS',
                'all_requested_stages_achieved':completed,'preserved_converged_sets':sorted(setids),
                'unverified_or_failed_sets_excluded':len(history)-len(rows),'effective_stiffness':modulus,
                'snapshots':selected_snapshots(achieved),'pseudo_time_units':'load_parameter_not_seconds',
                'internal_self_contact':'UNQUALIFIED','research_readiness':'HOLD','llm_performance_eligible':False}
        write_json(output/'mechanical_summary.json',report)
        # Keep full source numerical fields with their receipt references; no screenshot sampling.
        for name,values in [('nodal_fields.csv',nodal),('contact_fields.csv',contacts)]:
            valid_rows=[r for r in values if int(r['set']) in setids]
            if valid_rows:
                with (data_output/name).open('w',newline='') as stream:
                    writer=csv.DictWriter(stream,fieldnames=list(valid_rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(valid_rows)
        return report
    except (ValueError,KeyError,FileNotFoundError) as exc:
        report={'status':'QUARANTINED_INVALID_OR_MISSING_SOLVER_OUTPUT','reason':str(exc),
                'llm_performance_eligible':False,'effective_stiffness':None}
        write_json(output/'QUARANTINE.json',report)
        return report
