"""Prospective extended-arc direct crop trial using authenticated legacy infrastructure."""
import argparse
import shutil
import numpy as np
from scripts.v0610_common import BASE,RUN,DOC,OLD,V068,read,write_json,file_hash,execute,copy_evidence
from scripts.v068_track_b import mesh_and_plan

TRIAL='track_B_pair5_arc_trial_001'


def bind():
    from scripts import v068_track_b_pair as pair,v068_pair_unified as unified,v068_track_b_pair_export as export,v068_track_b_pair_qualify as qualify,v068_pair_force_scan as force
    for mod in [pair,unified,export,qualify,force]:
        mod.BASE=BASE;mod.RUN=RUN
        if hasattr(mod,'copy_evidence'):mod.copy_evidence=copy_evidence
    return pair,unified,export,qualify,force


def prepare():
    mesh,_,_,_=mesh_and_plan();source=np.arange(2128,2152);target=np.arange(2628,2650)
    assert not np.intersect1d(mesh.boundary[source],mesh.boundary[target]).size
    for subdir in ['track_B_mesh','track_B_contact_fixture','protocol']: (RUN/subdir).mkdir(exist_ok=True)
    for name in ['MESH_001.json']:shutil.copyfile(V068/'track_B_mesh'/name,RUN/'track_B_mesh'/name)
    for name in ['SETUP_QUALIFICATION.json','PAIR_FIXTURE_QUALIFICATION.json','PAIR_UNIFIED5_FIXTURE_QUALIFICATION.json']:
        q=read(V068/'track_B_contact_fixture'/name);q['inherited_fixture_or_unchanged_mesh_evidence']=True
        write_json(RUN/'track_B_contact_fixture'/name,q)
    oldp=read(V068/'protocol/TRACK_B_LOCAL_PAIR_002.json')
    p={**oldp,'model_variant':'V0610_E1000_EXTENDED_CONTIGUOUS_ARC','source_contact_faces_zero_based':source.tolist(),'target_contact_faces_zero_based':target.tolist(),'hypothesis':'Contiguous coverage beyond both original patch endpoints may retain intended interaction as contact migrates across adjoining faces. No FKN,friction,normal algorithm or solid geometry change.','new_faces':{'source':24,'target':22},'material_identity':'CROP_LINEAR_ELASTIC_E1000_V068'}
    write_json(RUN/'protocol/TRACK_B_LOCAL_PAIR_002.json',p)
    shutil.copyfile(V068/'protocol/TRACK_B.json',RUN/'protocol/TRACK_B.json')
    write_json(RUN/'protocol/TRACK_B_PAIR_UNIFIED5_TECHNICAL_CORRECTION_003.json',{'scope':'v0610 extended pair; inherited supported unified detection, fresh setup','protocol_sha256':file_hash(RUN/'protocol/PROTOCOL.json')})
    d=BASE/'track_B_setup_001';d.mkdir(exist_ok=False)
    for name in ['contact_model.db','gc_topology.csv','simulation_manifest.json']:
        shutil.copyfile(OLD/'track_B_setup_001'/name,d/name)
    assert file_hash(d/'contact_model.db')==read(V068/'track_B_contact_fixture/SETUP_QUALIFICATION.json')['native_database_sha256']
    pair,*_=bind();pair.prepare_setup()
    write_json(RUN/'contact_forensics/ARC_EXTENSION.json',{'source_original':list(range(2134,2146)),'target_original':list(range(2634,2644)),'source_extended':source.tolist(),'target_extended':target.tolist(),'no_shared_source_target_nodes':True,'geometry_unchanged':True,'removed_GC_faces':46,'remaining_GC_faces':15362,'old_opening_skin':95927,'old_adjacent_loaded_skin':95928,'old_target_skin':95916,'normal_rotation_degrees':[.0864,.1115,.0379],'interpretation':'Corner pressure redistribution; no proven abrupt normal flip. Coverage hypothesis requires direct crop test.'})
    print('Prepared extended-arc candidate',flush=True)


def verify_setup():
    pair,*_=bind();pair.verify_setup()


def prepare_unified():
    _,unified,*_=bind();unified.prepare_setup()


def verify_unified():
    _,unified,*_=bind();unified.verify_setup()


def prepare_trial():
    from metamaterial_eval.simulation.microstructure_pilot import database_resume
    from metamaterial_eval.simulation.progressive_compression import load_commands
    from metamaterial_eval.simulation.nonlinear_diagnostics import telemetry_commands
    q=read(RUN/'track_B_contact_fixture/PAIR_UNIFIED5_SETUP_QUALIFICATION.json')
    model=read(BASE/'track_B_setup_001/simulation_manifest.json');top=model['controls']['top'];bottom=model['controls']['bottom']
    d=BASE/TRIAL;d.mkdir(exist_ok=False)
    lines=['/BATCH','/CLEAR,START',database_resume(BASE/'track_B_pair_unified_setup_001/contact_model_pair_unified.db').strip(),'/FILNAME,compression','/GOPR','/SOLU','ANTYPE,STATIC','NLGEOM,ON','EQSLV,SPARSE','NROPT,FULL','LNSRCH,ON','CNVTOL,F,,.005,2,1e-8',f'NLHIST,NSOL,RFLOW,F,Y,{bottom}']
    lines+=telemetry_commands(top)
    previous=0;targets=[.005,.01,.0115,.012,.012575,.012675,.015]
    for t in targets:
        controls=load_commands(t,previous,top,2.56,initial=.00005 if t>.01 else .0005,maximum=.0001 if t>.01 else .0025,minimum=1e-6)
        i=controls.index('OUTRES,ERASE');j=controls.index('OUTPR,ALL,NONE');controls[i:j]=['OUTRES,ALL,ALL','OUTRES,NLOAD,ALL'];controls.insert(controls.index('SOLVE'),'NEQIT,40')
        lines+=controls;previous=t
    lines+=['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    write_json(d/'simulation_manifest.json',{'schema':'young-dawgs-v0610-direct-crop-contact-trial','model_variant':'V0610_E1000_EXTENDED_ARC_UNIFIED','model':model,'material_identity':'CROP_LINEAR_ELASTIC_E1000_V068','target_engineering_strain':.015,'targets':targets,'source_setup_sha256':q['native_database_sha256'],'all_native_fields_all_substeps':True,'input_sha256':file_hash(d/'input.inp')})
    copy_evidence(d,'crop_contact_trials')


def export_prepare():
    *_,export,qualify,force=bind();export.prepare(TRIAL,'all')


def force_prepare():
    *_,force=bind();force.prepare(TRIAL)


def qualify():
    pair,unified,export,q,force=bind();force.qualify(TRIAL);q.qualify(TRIAL,'all')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','setup-run','verify-setup','prepare-unified','unified-run','verify-unified','prepare-trial','trial-run','export-prepare','export-run','force-prepare','force-run','qualify']);a=p.parse_args()
    actions={'setup-run':lambda:execute('track_B_pair_setup_002',timeout=900),'verify-setup':verify_setup,'prepare-unified':prepare_unified,'unified-run':lambda:execute('track_B_pair_unified_setup_001',timeout=900),'verify-unified':verify_unified,'prepare-trial':prepare_trial,'trial-run':lambda:execute(TRIAL,cores=8),'export-prepare':export_prepare,'export-run':lambda:execute(TRIAL+'_post1_all_v2',solve=False,timeout=1800),'force-prepare':force_prepare,'force-run':lambda:execute(TRIAL+'_pair_force_scan_001',solve=False,timeout=900)}
    if a.action in actions:actions[a.action]()
    else:globals()[a.action.replace('-','_')]()
