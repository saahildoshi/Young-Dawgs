"""Execute only the preregistered v0.6.4 small diagnostic matrix."""
from pathlib import Path
from dataclasses import replace
import json
import shutil
import numpy as np
from shapely import box,LineString,unary_union,to_wkb
import hashlib
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.mesh_generation import generate_mesh,save_mesh
from metamaterial_eval.simulation.mesh_remediation import POLICY_B
from metamaterial_eval.simulation.mesh_validation import validate_mesh
from metamaterial_eval.simulation.microstructure_import import prepare_import,launch,read_cdb
from metamaterial_eval.simulation.microstructure_pilot import setup_contact,database_resume,stage_block,vector_fields
from metamaterial_eval.simulation.nonlinear_diagnostics import run_diagnostic,telemetry_commands,parse_solver_log,parse_contact,contact_summary,localize_residual,export_csv
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.reporting import write_json,mesh_hash

REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'experiments/pipeline_v0.6.4/run_001'
BASE=artifact_root()/'solver/v064'


def load(path):return json.loads(Path(path).read_text())


def export_evidence(directory,label):
    directory=Path(directory);out=RUN/'diagnostic_validation'/label;out.mkdir(exist_ok=False)
    for name in ['input.inp','provenance.json','execution_receipt.json','model_manifest.json','nonlinear_telemetry.json','contact_telemetry.json','contact_summary.json','stage001_history.csv','stage001_gate.txt','stage001_contact.csv','direct_history.csv']:
        if (directory/name).exists():shutil.copy2(directory/name,out/name)
    for name in ['solver.out','compression.cnd','compression.nlh','compression.mntr']:
        if (directory/name).exists():
            # Explicitly normalized text copies; original bytes/hashes stay local.
            text=(directory/name).read_text(errors='replace')
            (out/(name+'.normalized.txt')).write_text('\n'.join(s.rstrip() for s in text.splitlines())+'\n',encoding='utf-8')
    t=load(directory/'nonlinear_telemetry.json');c=load(directory/'contact_telemetry.json')
    export_csv(out/'force_iterations.csv',t['force_evaluations']);export_csv(out/'completed_iterations.csv',t['completed_iterations']);export_csv(out/'contact_iterations.csv',c['records'])
    return out


def prepare_synthetic():
    cfg=replace(CompressionConfig(),width=4,height=4,boundary_size=.025,bulk_size=.06)
    struts=[LineString([(x,.15),(x+.55,1.4),(x,2.6),(x+.55,3.85)]).buffer(.06,cap_style='flat',join_style='mitre') for x in [.6,2.6]]
    geometry=unary_union([box(0,0,4,.2),box(0,3.8,4,4),*struts])
    assert geometry.geom_type=='Polygon' and geometry.is_valid
    mesh=generate_mesh(geometry,cfg,policy=POLICY_B);quality,distribution=validate_mesh(mesh,geometry,cfg)
    assert quality['accepted'],quality
    out=RUN/'synthetic_models/compliant_zigzag_001';out.mkdir(exist_ok=False)
    local=BASE/'compliant_geometry_001';local.mkdir(exist_ok=False)
    save_mesh(mesh,local/'mesh.npz');(out/'source.wkt').write_text(geometry.wkt)
    write_json(out/'manifest.json',{'scope':'DIAGNOSTIC_ONLY, distinct synthetic geometry; no Design9 response inference','geometry_sha256':hashlib.sha256(to_wkb(geometry)).hexdigest(),'mesh_semantic_sha256':mesh_hash(mesh),'nodes':len(mesh.nodes),'TRI6':len(mesh.triangles),'pores':len(geometry.interiors),'config':cfg.manifest(),'width_of_bending_struts_mm':.12,'quality':quality,'local_mesh':str(local/'mesh.npz')})
    imp=BASE/'compliant_import_001';prepare_import(mesh,imp,cfg);receipt=launch(imp,timeout=180,rss_limit=8*1024**3,min_available_ram=12*1024**3)
    assert receipt['process']['returncode']==0
    nodes,tri,attrs,groups=read_cdb(imp/'imported.cdb',len(mesh.nodes),len(mesh.triangles))
    assert np.allclose(nodes,mesh.nodes,rtol=0,atol=1e-11) and np.array_equal(tri,mesh.triangles)
    write_json(out/'import_verification.json',{'all_nodes_and_TRI6_match':True,'source_CDB_sha256':file_hash(imp/'imported.cdb'),'import_receipt':receipt})
    setup=BASE/'compliant_setup_001';result=setup_contact(imp/'specimen.db',mesh,setup,cfg,-1e-5,algorithm=1,stiffness_update=1,fkn=100)
    assert result['status']=='CONTACT_SETUP_PASS'
    shutil.copy2(setup/'model_manifest.json',out/'contact_model_manifest.json')
    return mesh,setup


def direct_post(model,strain):
    lines=['FINISH','/POST1','ALLSEL,ALL','SET,LAST','*GET,TNOW,ACTIVE,0,SET,TIME','*GET,LSV,ACTIVE,0,SET,LSTP','*GET,SSV,ACTIVE,0,SET,SBST']
    for group,var in [('TOP_FACE','RFTOP'),('BOTTOM_FACE','RFBOT')]:
        lines+=['CMSEL,S,'+group,'*GET,NC,NODE,0,COUNT','NID=0',var+'=0','*DO,KK,1,NC','NID=NDNEXT(NID)','*GET,FVAL,NODE,NID,RF,FY',var+'='+var+'+FVAL','*ENDDO']
    lines+=['CMSEL,S,TOP_FACE','*GET,NID,NODE,0,NUM,MIN','*GET,UYTOP,NODE,NID,U,Y','ALLSEL,ALL','*CFOPEN,direct_history,csv','*VWRITE',"('pseudo_time,load_step,substep,top_uy_mm,upper_rf_y_N,lower_rf_y_N')",'*VWRITE,TNOW,LSV,SSV,UYTOP,RFTOP,RFBOT',"(E24.16,2(',',F10.0),3(',',E24.16))",'*CFCLOS']
    return lines+vector_fields(model['specimen_nodes'],'direct')


def run_variant(mesh,setup,variant):
    label=variant['id'];out=BASE/label;out.mkdir(exist_ok=False)
    m=load(setup/'model_manifest.json');top=m['controls']['top'];height=m['config']['height'];strain=variant['strain']
    lines=['/BATCH','/CLEAR,START',database_resume(setup/'contact_model.db').strip(),'/GOPR']
    if not variant['contact']:
        bottom=np.unique(mesh.boundary[mesh.boundary_groups=='bottom']);anchor=int(bottom[np.argmin(mesh.nodes[bottom,0])])+1
        top=int(np.unique(mesh.boundary[mesh.boundary_groups=='top']).min())+1
        lines+=['/PREP7','ESEL,S,TYPE,,2,3','EDELE,ALL','ALLSEL,ALL','DDELE,ALL,ALL',f'D,{anchor},UX,0','CMSEL,S,BOTTOM_FACE','D,ALL,UY,0','CMSEL,S,TOP_FACE',f'D,ALL,UY,{-height*strain:.17g}','ALLSEL,ALL','FINISH']
    n=variant['NSUBST'];lines+=['/SOLU','NLGEOM,'+('ON' if variant['NLGEOM'] else 'OFF'),'AUTOTS,ON',f'NSUBST,{n[0]},{n[1]},{n[2]}',f'NEQIT,{variant["NEQIT"]}','KBC,0','OUTRES,ALL,ALL']+telemetry_commands(top)
    if variant['contact']:lines+=stage_block(1,strain,m,{})
    else:lines += [f'TIME,{strain:.17g}','SOLVE']+direct_post(m,strain)
    lines+=['FINISH','SAVE,diagnostic_final,db','/EXIT,NOSAVE']
    (out/'input.inp').write_text('\n'.join(lines)+'\n');write_json(out/'model_manifest.json',m)
    write_json(out/'provenance.json',{'variant':variant,'source_mesh_semantic_sha256':mesh_hash(mesh),'source_database_sha256':file_hash(setup/'contact_model.db'),'input_sha256':file_hash(out/'input.inp'),'registered_plan_sha256':file_hash(RUN/'protocol/DIAGNOSTIC_PLAN_001.json'),'scope':'DIAGNOSTIC_ONLY, explicitly different direct/linearized physical variants'})
    receipt=run_diagnostic(out)
    snapshots=[]
    for path in sorted(out.glob('compression.nr[0-9]*')):
        snapshots.append(localize_residual(path,mesh.nodes,mesh.boundary,mesh.boundary_groups))
    write_json(out/'residual_localization.json',snapshots)
    target=export_evidence(out,label);shutil.copy2(out/'residual_localization.json',target/'residual_localization.json')
    print(label,receipt['status'],receipt['process']['returncode'],len(receipt['converged_steps']),flush=True)
    return receipt


def main():
    mesh,setup=prepare_synthetic()
    for variant in load(RUN/'protocol/DIAGNOSTIC_PLAN_001.json')['small_controlled_variants']:run_variant(mesh,setup,variant)


if __name__=='__main__':main()
