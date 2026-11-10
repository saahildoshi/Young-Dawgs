"""Fresh polymer crop branch, gated by native coupon and complete crop-contact proof."""
import argparse
import shutil
from scripts import v0610_common as common,v0610_crop as crop
from scripts.v0610_material import IDENTITY,MU,D,E,NU
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.progressive_compression import authenticated_restart_copy,load_commands
from metamaterial_eval.simulation.nonlinear_diagnostics import telemetry_commands

ROOT_BASE=common.BASE;ROOT_RUN=common.RUN
FIRST='track_B_pair5_polymer_first_001'

def qualified_onset_prefix(q):
    if q.get('failures'):return None
    prefix=[]
    for state in q.get('states',[]):
        if not state.get('accepted'):break
        prefix.append(state)
    if not prefix or max(s['requested_time'] for s in prefix)<.012675-1e-10:return None
    return prefix[-1]['requested_time']


def configure():
    common.BASE=ROOT_BASE/'polymer';common.RUN=ROOT_RUN/'polymer'
    common.BASE.mkdir(exist_ok=True);common.RUN.mkdir(exist_ok=True)
    if not (common.RUN/'protocol/PROTOCOL.json').exists():common.write_json(common.RUN/'protocol/PROTOCOL.json',common.read(ROOT_RUN/'protocol/PROTOCOL.json'))
    crop.BASE=common.BASE;crop.RUN=common.RUN


def prepare_setup():
    if common.read(ROOT_RUN/'material_coupon/QUALIFICATION.json')['status']!='PASS':raise ValueError('Native material coupon not qualified')
    material=common.read(ROOT_RUN/'material_selection/MATERIAL.json')
    if material['identity']!=IDENTITY or abs(material['mu_MPa']-MU)>1e-12 or abs(material['d_inverse_MPa']-D)>1e-12:raise ValueError('Material configuration drift from verified coupon')
    candidates=[(ROOT_BASE,ROOT_RUN,'track_B_pair5_arc_strict_001'),(ROOT_BASE/'reverse',ROOT_RUN/'reverse','track_B_pair5_arc_trial_001')]
    accepted=[]
    for base,run,name in candidates:
        p=run/'track_B_progressive_compression'/(name+'_mechanical_qualification.json')
        if p.exists():
            q=common.read(p)
            extent=qualified_onset_prefix(q)
            if extent is not None:accepted.append((base,run,p,extent))
    if not accepted:raise ValueError('No continuous direct crop path qualified through1.2675%; polymer branch is gated')
    source_base,source_run,proof,extent=accepted[0];source=source_base/'track_B_pair_unified_setup_001/contact_model_pair_unified.db'
    oldq=common.read(source_run/'track_B_contact_fixture/PAIR_UNIFIED5_SETUP_QUALIFICATION.json');assert common.file_hash(source)==oldq['native_database_sha256']
    for category,names in [('track_B_contact_fixture',['PAIR_SETUP_QUALIFICATION.json','PAIR_UNIFIED5_SETUP_QUALIFICATION.json','SETUP_QUALIFICATION.json']),('track_B_mesh',['MESH_001.json']),('protocol',['TRACK_B.json','TRACK_B_LOCAL_PAIR_002.json'])]:
        for name in names:
            target=common.RUN/category/name;target.parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(source_run/category/name,target)
    for name in ['gc_topology.csv','target_topology.csv','contact_topology.csv']:
        target=common.BASE/'track_B_pair_setup_002'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(source_base/'track_B_pair_setup_002'/name,target)
    p=common.read(common.RUN/'protocol/TRACK_B_LOCAL_PAIR_002.json');p['material_identity']=IDENTITY;p['contact_path_previously_qualified_through']=extent;p['new_material_requires_independent_complete_path']=True;common.write_json(common.RUN/'protocol/TRACK_B_LOCAL_PAIR_002.json',p)
    model=common.read(source_base/'track_B_setup_001/simulation_manifest.json');model['config'].update(young_modulus=E,poisson_ratio=NU,material=IDENTITY);model['material_identity']=IDENTITY
    common.write_json(common.BASE/'track_B_setup_001/simulation_manifest.json',model)
    d=common.BASE/'track_B_pair_unified_setup_001';d.mkdir(exist_ok=False)
    deck='/BATCH\n/CLEAR,START\n'+database_resume(source)+'/FILNAME,compression\n/PREP7\nMPDELE,EX,1\nMPDELE,PRXY,1\nKEYOPT,1,6,0\nTB,HYPER,1,,,NEO\n'+f'TBDATA,1,{MU:.17g},{D:.17g}\n'+ '/OUTPUT,contact_types,txt\nETLIST,ALL\nRLIST,ALL\nTBLIST,ALL\nGCDEF,LIST\n/OUTPUT\nFINISH\nSAVE,contact_model_pair_unified,db,,MODEL\n/EXIT,NOSAVE\n'
    (d/'input.inp').write_text(deck,encoding='utf-8',newline='\n')
    common.write_json(d/'simulation_manifest.json',{'material_identity':IDENTITY,'material_configuration_sha256':common.file_hash(ROOT_RUN/'material_selection/MATERIAL.json'),'mu_MPa':MU,'d_inverse_MPa':D,'source_unloaded_database_sha256':common.file_hash(source),'contact_path_qualification':str(proof),'contact_qualified_through':extent,'contact_path_qualification_sha256':common.file_hash(proof),'coupon_qualification_sha256':common.file_hash(ROOT_RUN/'material_coupon/QUALIFICATION.json'),'input_sha256':common.file_hash(d/'input.inp'),'fresh_zero_state_material_change':True})


def verify_setup():
    d=common.BASE/'track_B_pair_unified_setup_001';r=common.read(d/'execution_receipt.json');assert r['process']['returncode']==0 and r['solver_version']=='2024 R1'
    text=(d/'contact_types.txt').read_text(errors='replace');assert 'NEO' in text and 'PLANE183' in text
    q=common.read(common.RUN/'track_B_contact_fixture/PAIR_UNIFIED5_SETUP_QUALIFICATION.json');q.update(native_database_sha256=common.file_hash(d/'contact_model_pair_unified.db'),material_identity=IDENTITY,setup_receipt_sha256=common.file_hash(d/'execution_receipt.json'),native_contact_inventory_sha256=common.file_hash(d/'contact_types.txt'),scope='Native polymer setup only; fresh mechanics require full independent qualification')
    common.write_json(common.RUN/'track_B_contact_fixture/PAIR_UNIFIED5_SETUP_QUALIFICATION.json',q)


def prepare_loading(parent=None,target=None):
    model=common.read(common.BASE/'track_B_setup_001/simulation_manifest.json');top=model['controls']['top'];bottom=model['controls']['bottom']
    if parent:
        path=common.RUN/'track_B_progressive_compression'/(parent+'_mechanical_qualification.json');q=common.read(path)
        if not q['accepted'] or not all(s['accepted'] for s in q['states']):raise ValueError('Cannot continue invalid polymer path')
        parent_manifest=common.read(common.BASE/parent/'simulation_manifest.json');schedule=[.015,.02,.05,.10,.15,.20,.25,.30,.35,.40]
        if target not in schedule or schedule.index(target)!=schedule.index(parent_manifest['target_engineering_strain'])+1:raise ValueError('Unregistered or skipped polymer target')
        state=q['states'][-1];previous=state['measurement']['engineering_compression_strain'];name=f'track_B_pair5_polymer_to_{round(target*100000):05d}_001';d=common.BASE/name
        mesh_sha=common.read(common.RUN/'track_B_mesh/MESH_001.json')['semantic_sha256'];m=authenticated_restart_copy(common.BASE/parent,d,expected_mesh=mesh_sha)
        if m['material_identity']!=IDENTITY:raise ValueError('Material restart mismatch')
        lines=['/BATCH','/CLEAR,START','RESUME,compression,rdb','/FILNAME,compression','/GOPR','/SOLU',f'ANTYPE,STATIC,REST,{state["load_step"]},{state["substep"]},CONTINUE'];targets=[target]
    else:
        previous=0;name=FIRST;d=common.BASE/name;d.mkdir(exist_ok=False)
        lines=['/BATCH','/CLEAR,START',database_resume(common.BASE/'track_B_pair_unified_setup_001/contact_model_pair_unified.db').strip(),'/FILNAME,compression','/GOPR','/SOLU','ANTYPE,STATIC'];targets=[.005,.01,.015]
    start=previous
    lines+=['NLGEOM,ON','EQSLV,SPARSE','NROPT,FULL','LNSRCH,ON','CNVTOL,F,,.00001,2,1e-8',f'NLHIST,NSOL,RFLOW,F,Y,{bottom}']+telemetry_commands(top)
    for t in targets:
        controls=load_commands(t,previous,top,2.56,initial=.0001 if previous==0 else (.00005 if t<=.02 else .0005),maximum=.0001 if .01<t<=.02 else (.0005 if t<=.01 else .0025),minimum=1e-6)
        i=controls.index('OUTRES,ERASE');j=controls.index('OUTPR,ALL,NONE');controls[i:j]=['OUTRES,ALL,ALL','OUTRES,NLOAD,ALL'];controls.insert(controls.index('SOLVE'),'NEQIT,40');lines+=controls;previous=t
    lines+=['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE'];(d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    common.write_json(d/'simulation_manifest.json',{'schema':'v0610-fresh-polymer-progressive-crop','model_variant':IDENTITY,'material_identity':IDENTITY,'model':model,'parent':parent,'parent_qualification_sha256':common.file_hash(path) if parent else None,'previous_engineering_strain':start,'target_engineering_strain':targets[-1],'targets':targets,'mesh_semantic_sha256':common.read(common.RUN/'track_B_mesh/MESH_001.json')['semantic_sha256'],'all_native_fields_all_substeps':True,'input_sha256':common.file_hash(d/'input.inp')})
    common.copy_evidence(d,'progressive_compression');print('Prepared polymer loading',name,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare-setup','setup-run','verify-setup','prepare-first','prepare-next','run','export-prepare','export-run','force-prepare','force-run','qualify']);p.add_argument('--source',default=FIRST);p.add_argument('--parent');p.add_argument('--target',type=float);a=p.parse_args();configure();crop.TRIAL=a.source
    actions={'prepare-setup':prepare_setup,'setup-run':lambda:common.execute('track_B_pair_unified_setup_001',timeout=900),'verify-setup':verify_setup,'prepare-first':prepare_loading,'prepare-next':lambda:prepare_loading(a.parent,a.target),'run':lambda:common.execute(a.source,cores=8),'export-prepare':crop.export_prepare,'export-run':lambda:common.execute(a.source+'_post1_all_v2',solve=False,timeout=1800),'force-prepare':crop.force_prepare,'force-run':lambda:common.execute(a.source+'_pair_force_scan_001',solve=False,timeout=900),'qualify':crop.qualify};actions[a.action]()
