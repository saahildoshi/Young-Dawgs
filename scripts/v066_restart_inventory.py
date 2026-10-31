"""Inventory authenticated multiframe copies in their actual native file context."""
import argparse
import shutil
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import RUN,BASE,load,compact


def main(label):
    source=BASE/label;out=BASE/(label+'_restart_inventory001');out.mkdir(parents=True,exist_ok=False)
    receipt=load(source/'execution_receipt.json');files=['compression.rdb','compression.ldhi']+sorted(p.name for p in source.glob('compression.r[0-9][0-9][0-9]'))
    assert len(files)>2
    bindings={}
    for name in files:
        p=source/name;digest=file_hash(p);assert digest==receipt['process']['artifacts'][name]['sha256']
        bindings[name]={'sha256':digest,'bytes':p.stat().st_size};shutil.copy2(p,out/name)
    text='/BATCH\n/CLEAR,START\nRESUME,compression,rdb\n/FILNAME,compression\n/GOPR\n/SOLU\n/OUTPUT,restart_sets,txt\nRESCONTROL,FILE_SUMMARY\n/OUTPUT\nFINISH\n/EXIT,NOSAVE\n'
    (out/'input.inp').write_text(text)
    write_json(out/'provenance.json',{'source':str(source),'source_receipt_sha256':file_hash(source/'execution_receipt.json'),
        'copied_native_files':bindings,'no_RST_copy_needed_for_restart_inventory':True,'source_not_modified':True,'mode':'READ_ONLY_MULTIFRAME_FILE_INVENTORY_NO_SOLVE_OR_SAVE'})
    r=run_progressive(out,timeout=180,solve=False,cores=1)
    compact(out,RUN/'progressive_compression'/out.name)
    print(label,r['status'],r['process']['returncode'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');a=p.parse_args();main(a.label)
