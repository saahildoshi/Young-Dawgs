"""Small installed-release unified-GC feasibility run, not parsing-only evidence."""
import argparse
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.progressive_compression import run_progressive
from scripts.v068_common import RUN,BASE,read,write_json,file_hash,copy_evidence


def prepare():
    source=artifact_root()/'solver/v066/internal_fixture_enabled_003'
    receipt=read(source/'execution_receipt.json');assert file_hash(source/'input.inp')==receipt['input_sha256']
    directory=BASE/'unified_internal_fixture_001';directory.mkdir(parents=True,exist_ok=False)
    text=(source/'input.inp').read_text(encoding='utf-8')
    assert text.count('KEYOPT,2,4,2')==1
    text=text.replace('KEYOPT,2,4,2','KEYOPT,2,4,5').replace('RESCONTROL,DEFINE,ALL,ALL,-1,,3','RESCONTROL,DEFINE,ALL,1,-1,,3')
    text=text.replace('SAVE,checkpoint,db,,MODEL','/PREP7\n/OUTPUT,native_type_after,txt\nETLIST,ALL\nGCDEF,LIST\n/OUTPUT\nFINISH\nSAVE,checkpoint,db,,MODEL')
    (directory/'input.inp').write_text(text,encoding='utf-8',newline='\n')
    m=read(source/'simulation_manifest.json');m.update(input_sha256=file_hash(directory/'input.inp'),contact_detection_keyopt4=5,
            source_native_input_sha256=file_hash(source/'input.inp'),execution_scope='SMALL_UNIFIED_GENERAL_CONTACT_INSTALLED_V241_QUALIFICATION')
    write_json(directory/'simulation_manifest.json',m)
    copy_evidence(directory,'track_B_contact_fixture')


def execute():
    directory=BASE/'unified_internal_fixture_001'
    r=run_progressive(directory,timeout=300,no_progress_seconds=120,cores=2)
    copy_evidence(directory,'track_A_unified_detection')
    print('Unified fixture',r['status'],r['process']['returncode'],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute']);a=p.parse_args();prepare() if a.action=='prepare' else execute()
