"""Independent native POST1 readback for the registered Track B stage."""
import argparse
from pathlib import Path
import re

from metamaterial_eval.simulation.progressive_compression import multi_export_input,run_progressive
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


def prepare(source_name,selection='last'):
    source=BASE/source_name
    receipt=read(source/'execution_receipt.json')
    setup=read(RUN/'track_B_contact_fixture/SETUP_QUALIFICATION.json')
    if (receipt['solver_version']!='2024 R1' or
        file_hash(source/'input.inp')!=receipt['input_sha256'] or
        file_hash(BASE/'track_B_setup_001/contact_model.db')!=setup['native_database_sha256']):
        raise ValueError('Unverified Track B source or altered native setup')
    telemetry=read(source/'nonlinear_telemetry.json')
    states=[]
    for row in telemetry['converged_substeps']:
        if 'pseudo_time' in row and row['substep']!=999999:
            states.append({'load_step':row['load_step'],'substep':row['substep'],
                           'time':row['pseudo_time']})
    if not states:raise ValueError('No actual converged state available for POST1')
    if selection=='last':states=states[-1:]
    elif selection!='all':raise ValueError('Unsupported state selection')
    model=read(BASE/'track_B_setup_001/simulation_manifest.json')
    model.update(user_model_elements=setup['native_elements'],
                 general_contact_elements=setup['oriented_GC_faces'],
                 contact_elements=model['platen_contact_elements'])
    output=BASE/(source_name+'_post1_'+selection)
    output.mkdir(parents=True,exist_ok=False)
    deck=multi_export_input(BASE/'track_B_setup_001/contact_model.db',
                            source/'compression',model,states,chunk_size=50000,farfield=True)
    # Readback gates are recorded for independent qualification; a native gate
    # failure must not prevent evidence from being exported for diagnosis.
    deck=deck.replace('*IF,FAILG,NE,0,THEN','*IF,FAILG,EQ,-1,THEN')
    if re.search(r'^\s*(?:SOLVE|SAVE\s*,)',deck,re.M|re.I):
        raise ValueError('POST1 input contains a mutation')
    (output/'input.inp').write_text(deck,encoding='utf-8',newline='\n')
    manifest={'schema':'young-dawgs-v068-independent-POST1','source':str(source),
              'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
              'source_RST_sha256':file_hash(source/'compression.rst'),
              'setup_database_sha256':setup['native_database_sha256'],
              'states':states,'selection':selection,'input_sha256':file_hash(output/'input.inp'),
              'read_only':True,'native_gate_diagnostic_only':True,
              'qualifier':'Separate prospective Track B mechanical acceptance'}
    write_json(output/'simulation_manifest.json',manifest)
    copy_evidence(output,'track_B_progressive_compression')
    print('Prepared independent POST1',source_name,selection,states[-1],flush=True)


def execute(source_name,selection='last'):
    d=BASE/(source_name+'_post1_'+selection)
    r=run_progressive(d,timeout=1800,solve=False,cores=2,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('POST1',source_name,r['status'],r['process']['returncode'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute'])
    p.add_argument('source_name');p.add_argument('--selection',choices=['last','all'],default='last')
    a=p.parse_args();prepare(a.source_name,a.selection) if a.action=='prepare' else execute(a.source_name,a.selection)
