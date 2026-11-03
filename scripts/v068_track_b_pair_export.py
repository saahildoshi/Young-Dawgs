"""Independent all-field POST1 readback for the selected-specimen pair branch."""
import argparse
import re

from metamaterial_eval.simulation.progressive_compression import multi_export_input,run_progressive
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


def prepare(source_name,selection='last'):
    source=BASE/source_name;receipt=read(source/'execution_receipt.json')
    setup=read(RUN/'track_B_contact_fixture/PAIR_SETUP_QUALIFICATION.json')
    manifest=read(source/'simulation_manifest.json')
    if (receipt['solver_version']!='2024 R1' or
        receipt['input_sha256']!=manifest['input_sha256'] or
        file_hash(source/'input.inp')!=manifest['input_sha256'] or
        file_hash(BASE/'track_B_pair_setup_002/contact_model_pair.db')!=setup['pair_database_sha256']):
        raise ValueError('Changed pair source or native model')
    telemetry=read(source/'nonlinear_telemetry.json')
    states=[{'load_step':row['load_step'],'substep':row['substep'],'time':row['pseudo_time']}
            for row in telemetry['converged_substeps'] if 'pseudo_time' in row and row['substep']!=999999]
    if not states:raise ValueError('No native converged state for independent readback')
    if selection=='last':states=states[-1:]
    elif selection!='all':raise ValueError('Unsupported state selection')
    model=read(BASE/'track_B_setup_001/simulation_manifest.json')
    model.update(user_model_elements=read(RUN/'track_B_contact_fixture/SETUP_QUALIFICATION.json')['native_elements'],
                 general_contact_elements=setup['native_exact_face_counts']['gc'],
                 contact_elements=model['platen_contact_elements'])
    d=BASE/(source_name+'_post1_'+selection+'_v2');d.mkdir(parents=True,exist_ok=False)
    deck=multi_export_input(BASE/'track_B_pair_setup_002/contact_model_pair.db',
                            source/'compression',model,states,chunk_size=50000,farfield=True)
    lines=deck.splitlines();output=[];n=0
    for line in lines:
        if line=='*IF,FAILG,NE,0,THEN':
            n+=1;prefix=f'stage{n:03d}'
            output += ['ALLSEL,ALL','CMSEL,S,LOCAL_PAIR_CONTACT','*GET,NP,ELEM,0,COUNT',
                       f'*CFOPEN,{prefix}_pair_contact,csv','*VWRITE',
                       "('element,status,pressure_i_MPa,pressure_j_MPa,pen_i_mm,pen_j_mm,fy_N,target_i,target_j')",
                       'ETABLE,CNSTAT,NMISC,19',
                       'EID=0','*DO,KK,1,NP','EID=ELNEXT(EID)',
                       '*GET,STV,ELEM,EID,ETAB,CNSTAT',
                       'PI=0','PJ=0','GI=0','GJ=0','FYV=0','TI=0','TJ=0',
                       '*IF,STV,GT,0,THEN',
                       '*GET,PI,ELEM,EID,SMISC,1',
                       '*GET,PJ,ELEM,EID,SMISC,2','*GET,GI,ELEM,EID,NMISC,5',
                       '*GET,GJ,ELEM,EID,NMISC,6','*GET,FYV,ELEM,EID,NMISC,22',
                       '*GET,TI,ELEM,EID,NMISC,23','*GET,TJ,ELEM,EID,NMISC,24',
                       '*ENDIF',
                       '*VWRITE,EID,STV,PI,PJ,GI,GJ,FYV,TI,TJ',
                       "(F12.0,',',F4.0,5(',',E24.16),2(',',F12.0))",
                       '*ENDDO','*CFCLOS','ALLSEL,ALL']
            output.append('*IF,FAILG,EQ,-1,THEN')
        else:output.append(line)
    if n!=len(states):raise ValueError('POST1 stage injection count differs')
    deck='\n'.join(output)+'\n'
    if re.search(r'^\s*(?:SOLVE|SAVE\s*,)',deck,re.M|re.I):raise ValueError('POST1 contains mutation')
    (d/'input.inp').write_text(deck,encoding='utf-8',newline='\n')
    m={'schema':'young-dawgs-v068-selected-pair-independent-POST1','source':str(source),
       'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
       'source_RST_sha256':file_hash(source/'compression.rst'),
       'setup_database_sha256':setup['pair_database_sha256'],
       'states':states,'selection':selection,'input_sha256':file_hash(d/'input.inp'),
       'read_only':True,'native_gate_diagnostic_only':True}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_progressive_compression')
    print('Prepared pair POST1',source_name,states[-1],flush=True)


def execute(source_name,selection='last'):
    d=BASE/(source_name+'_post1_'+selection+'_v2')
    r=run_progressive(d,timeout=1800,solve=False,cores=2,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Pair POST1',source_name,r['status'],r['process']['returncode'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute'])
    p.add_argument('source_name');p.add_argument('--selection',choices=['last','all'],default='last')
    a=p.parse_args()
    {'prepare':prepare,'execute':execute}[a.action](a.source_name,a.selection)
