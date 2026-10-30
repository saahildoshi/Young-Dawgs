"""Read an already converged native state; never issue another SOLVE."""
import re
import shutil
from scripts.v064_recovery import RUN,BASE,DIRECTORY,load
from metamaterial_eval.simulation.microstructure_pilot import database_resume,stage_block,run_input
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash


def main():
    protocol=load(RUN/'protocol/PARTIAL_STATE_EXTRACTION_008.json')
    assert file_hash(DIRECTORY/'compression.rst')==protocol['source_RST_sha256']
    model=load(DIRECTORY/'simulation_manifest.json')['model']
    out=BASE/'postprocess_converged_001';out.mkdir(exist_ok=False)
    block=stage_block(1,protocol['achieved_strain'],model,{})
    block=block[block.index('SOLVE')+1:]
    lines=['/BATCH','/CLEAR,START',database_resume(DIRECTORY/'compression.rdb').strip(),'/FILNAME,v064post001']
    for line in block:
        if line=='SET,LAST':
            lines.extend(["FILE,'"+str((DIRECTORY/'compression').resolve()).replace('\\','/')+"',rst",'SET,1,1'])
        elif line=='SAVE,pilot_partial,db':lines.append('/COM,READ_ONLY_CHECKPOINT_GATE_FAILED')
        else:lines.append(line)
    lines+=['/EXIT,NOSAVE'];text='\n'.join(lines)+'\n'
    if re.search(r'^\s*SOLVE\s*$',text,re.M|re.I):raise ValueError('Read-only extraction must not solve')
    (out/'input.inp').write_text(text)
    write_json(out/'provenance.json',{'mode':'READ_ONLY_POST1_ZERO_SOLVE_COMMANDS','source_full_execution_receipt_sha256':protocol['source_execution_receipt_sha256'],'source_RST_sha256':protocol['source_RST_sha256'],'source_state':protocol['native_converged_set'],'input_sha256':file_hash(out/'input.inp'),'extraction_protocol_sha256':file_hash(RUN/'protocol/PARTIAL_STATE_EXTRACTION_008.json')})
    r=run_input(out,timeout=300,rss_GiB=8,reserve_GiB=12)
    target=RUN/'mechanical_results/read_only_extraction_001';target.mkdir(exist_ok=False)
    for name in ['input.inp','execution_receipt.json','provenance.json','stage001_history.csv','stage001_gate.txt','stage001_contact.csv']:
        if (out/name).exists():shutil.copy2(out/name,target/name)
    print(r['status'],r['process']['returncode'],(out/'stage001_gate.txt').read_text() if (out/'stage001_gate.txt').exists() else 'No gate')


if __name__=='__main__':main()
