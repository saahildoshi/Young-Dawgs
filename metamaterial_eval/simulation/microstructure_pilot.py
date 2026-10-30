"""Bounded model checks, assembly diagnostics and staged platen-only pilot."""
import argparse
import json
from pathlib import Path
import re
import numpy as np
from .contact_setup import platen_plan
from .config import CompressionConfig
from .mesh_artifacts import artifact_root,resolve_manifest
from .microstructure_import import component
from .reporting import write_json
from .solver_execution import discover_solver,file_hash,solver_release,has_negative_pivots
from .windows_ansys import bounded_run


def database_resume(path):
    path=Path(path).resolve();extension=path.suffix.lstrip('.') or 'db'
    base=str(path.with_suffix('')).replace('\\','/')
    if "'" in base:raise ValueError('Unsupported apostrophe in ANSYS database path')
    return f"RESUME,'{base}',{extension}\n/FILNAME,compression\n"


def run_input(directory,*,timeout=600,rss_GiB=20,reserve_GiB=12):
    directory=Path(directory).resolve()
    def stop_check(folder):
        p=folder/'solver.out'
        if not p.exists():return None
        with p.open('rb') as f:
            f.seek(max(0,p.stat().st_size-65536));text=f.read().decode(errors='replace')
        if re.search(r'\*\*\*\s*(?:ERROR|FATAL)\s*\*\*\*|element.*highly distorted',text,re.I) or has_negative_pivots(text):
            return 'SOLVER_ERROR_OR_DISTORTION_STOP'
        return None
    receipt=bounded_run([str(discover_solver()),'-b','-smp','-np','1','-m','4096','-j','compression',
                         '-i','input.inp','-o','solver.out'],directory,prepared=True,timeout=timeout,
                        rss_limit=rss_GiB*1024**3,min_disk_free=20*1024**3,
                        min_available_ram=reserve_GiB*1024**3,stop_check=stop_check)
    log=(directory/'solver.out').read_text(errors='replace') if (directory/'solver.out').exists() else ''
    result={'status':receipt['status'],'solver_version':solver_release(log),'process':receipt,
            'input_sha256':file_hash(directory/'input.inp'),
            'warnings':re.findall(r'\*\*\* WARNING \*\*\*[^\n]*\n([^\n]+)',log),
            'converged_steps':[(int(a),int(b)) for a,b in re.findall(r'LOAD STEP\s+(\d+)\s+SUBSTEP\s+(\d+)\s+COMPLETED',log,re.I)]}
    write_json(directory/'execution_receipt.json',result)
    return result


def assembly_check(database,mesh,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    bottom=np.unique(mesh.boundary[mesh.boundary_groups=='bottom'])
    anchor=int(bottom[np.argmin(mesh.nodes[bottom,0])])+1
    text='/BATCH\n/CLEAR,START\n'+database_resume(database)
    text+=f'/SOLU\nANTYPE,STATIC\nNLGEOM,OFF\nEQSLV,SPARSE\nBCSOPTION,,DEFAULT,,,,PERFORMANCE\n'
    text+='CMSEL,S,BOTTOM_FACE\nD,ALL,UY,0\nALLSEL,ALL\n'+f'D,{anchor},UX,0\n'
    text+='CMSEL,S,TOP_FACE\nD,ALL,UY,-0.001024\nALLSEL,ALL\nOUTRES,ALL,NONE\nWRFULL,1\nSOLVE\nFINISH\n/EXIT,NOSAVE\n'
    (directory/'input.inp').write_text(text)
    result=run_input(directory,timeout=600,rss_GiB=20)
    log=(directory/'solver.out').read_text(errors='replace')
    result.update(status='ASSEMBLY_ONLY_COMPLETE_NOT_SOLVED' if result['process']['returncode']==0 and (directory/'compression.full').is_file() else 'RESOURCE_DIAGNOSTIC_FAILED',
                  matrix_file_bytes=(directory/'compression.full').stat().st_size if (directory/'compression.full').exists() else None,
                  reported_equations=re.findall(r'(?:Number of equations|NUMBER OF EQUATIONS)\s*[=:]\s*(\d+)',log),
                  memory_lines=[s.strip() for s in log.splitlines() if re.search(r'memory|equation|matrix|nonzero',s,re.I)][-70:],
                  scope='linear no-contact assembly only; no equation solution, factorization or mechanical result',
                  factorization_memory='NOT_ESTABLISHED_BY_WRFULL')
    write_json(directory/'resource_assessment.json',result)
    return result


def setup_contact(database,mesh,directory,config,ftoln):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    plan=platen_plan(mesh,config);count=len(mesh.nodes);eid=len(mesh.triangles);controls={}
    bottom=np.asarray(plan['bottom']['nodes']);anchor=int(bottom[np.argmin(mesh.nodes[bottom,0])])+1
    with (directory/'input.inp').open('w') as f:
        f.write('/BATCH\n/CLEAR,START\n'+database_resume(database)+'/PREP7\n/NOPR\n')
        component(f,'CORNERS',np.unique(mesh.triangles[:,:3])+1)
        f.write('ET,2,TARGE169\nKEYOPT,2,2,1\nET,3,CONTA172\nKEYOPT,3,2,0\nKEYOPT,3,4,0\nKEYOPT,3,5,0\nKEYOPT,3,12,0\n')
        for offset,group in enumerate(['bottom','top']):
            real=offset+2;y=0 if group=='bottom' else config.height
            left,right,pilot=count+3*offset+1,count+3*offset+2,count+3*offset+3;controls[group]=pilot
            f.write(f'R,{real},0,0,1,{ftoln:.17g}\nN,{left},{-config.width*.05:.17g},{y:.17g},0\n'
                    f'N,{right},{config.width*1.05:.17g},{y:.17g},0\nN,{pilot},{config.width/2:.17g},{y:.17g},0\n'
                    f'TYPE,2\nREAL,{real}\nTSHAP,LINE\n')
            a,b=(right,left) if group=='bottom' else (left,right);eid+=1;f.write(f'EN,{eid},{a},{b}\n')
            eid+=1;f.write(f'TSHAP,PILO\nEN,{eid},{pilot}\nTYPE,3\nREAL,{real}\nMAT,1\n')
            first=eid+1
            for a,b,mid in plan[group]['edges']:
                eid+=1;f.write(f'EN,{eid},{a+1},{b+1},{mid+1}\n')
            f.write(f'ESEL,S,ELEM,,{first},{eid}\nCM,{group.upper()}_CONTACT,ELEM\nALLSEL,ALL\n')
        f.write(f'D,{controls["bottom"]},UX,0\nD,{controls["bottom"]},UY,0\nD,{controls["bottom"]},ROTZ,0\n'
                f'D,{controls["top"]},UX,0\nD,{controls["top"]},UY,0\nD,{controls["top"]},ROTZ,0\nD,{anchor},UX,0\n'
                'ALLSEL,ALL\n/GOPR\n/OUTPUT,model_inventory,txt\nETLIST,ALL\nRLIST,ALL\nMPLIST,ALL\nCMLIST,ALL\nDLIST,ALL\n/OUTPUT\n'
                'FINISH\n/SOLU\nANTYPE,STATIC\nNLGEOM,ON\nEQSLV,SPARSE\nBCSOPTION,,DEFAULT,,,,PERFORMANCE\n'
                'NROPT,FULL\nAUTOTS,ON\nNSUBST,2,20,1\nNEQIT,30\nLNSRCH,ON\nCNVTOL,F,,0.005,2,1e-8\n'
                'OUTRES,ALL,LAST\n/OUTPUT,initial_contact,txt\nCNCHECK,DETAIL\n/OUTPUT\nFINISH\nSAVE,contact_model,db\n/EXIT,NOSAVE\n')
    manifest={'schema':'young-dawgs-v0.6.3-contact-model','specimen_nodes':len(mesh.nodes),'specimen_TRI6':len(mesh.triangles),
              'user_model_nodes':len(mesh.nodes)+6,'user_model_elements':eid,'controls':controls,
              'contact_elements':{g:len(plan[g]['edges']) for g in ['top','bottom']},'config':config.manifest(),
              'FKN':1,'FTOLN_absolute_mm':ftoln,'internal_self_contact':'UNQUALIFIED_NOT_CONFIGURED',
              'contact_scope':'PLATEN_CONTACT_ONLY','specimen_UY_constraints':False,'anchor_UX_node':anchor,
              'initial_geometric_gaps_mm':{'top':0,'bottom':0}}
    write_json(directory/'model_manifest.json',manifest)
    result=run_input(directory,timeout=300,rss_GiB=12)
    initial=(directory/'initial_contact.txt').read_text(errors='replace') if (directory/'initial_contact.txt').exists() else ''
    model=(directory/'model_inventory.txt').read_text(errors='replace') if (directory/'model_inventory.txt').exists() else ''
    closed=all(re.search(r'REAL ID\s*=\s*'+str(real)+r' IS INITIALLY CLOSED',initial) for real in [2,3])
    uy=[int(n) for n in re.findall(r'^\s*(\d+)\s+UY\s+',model,re.M)]
    no_bypass=all(n>len(mesh.nodes) for n in uy)
    status='CONTACT_SETUP_PASS' if result['process']['returncode']==0 and closed and no_bypass and (directory/'contact_model.db').exists() else 'CONTACT_SETUP_HOLD'
    result.update(status=status,both_pairs_initially_closed=closed,no_specimen_UY_constraints=no_bypass,
                  initial_penetration_lines=[s.strip() for s in initial.splitlines() if 'penetration' in s.lower()],
                  scope='configured and initially checked; no compression executed')
    write_json(directory/'contact_setup_validation.json',result)
    return result


def vector_fields(node_count,prefix):
    """Vector export, masking corner nodes before every stress operation."""
    variables=['IDS','UXV','UYV','MASKV','SYV','SEQV','EYV','EXV']
    lines=['ALLSEL,ALL']+[f'*DIM,{name},ARRAY,{node_count}' for name in variables]
    lines+=['*VFILL,IDS(1),RAMP,1,1','*VGET,UXV(1),NODE,1,U,X','*VGET,UYV(1),NODE,1,U,Y',
            f'*CFOPEN,{prefix}_displacements,csv','*VWRITE',"('node,ux_mm,uy_mm')",
            '*VWRITE,IDS(1),UXV(1),UYV(1)',"(F12.0,2(',',E24.16))",'*CFCLOS',
            'CMSEL,S,CORNERS','*VGET,MASKV(1),NODE,1,NSEL','ALLSEL,ALL','ESEL,S,TYPE,,1']
    for name,item,comp in [('SYV','S','Y'),('SEQV','S','EQV'),('EYV','EPEL','Y'),('EXV','EPEL','X')]:
        lines+=['*VMASK,MASKV(1)',f'*VGET,{name}(1),NODE,1,{item},{comp}']
    lines += [f'*CFOPEN,{prefix}_stress,csv','*VWRITE',"('node,syy_MPa,seqv_MPa,elastic_eyy,elastic_exx')",'*VMASK,MASKV(1)',
              '*VWRITE,IDS(1),SYV(1),SEQV(1),EYV(1),EXV(1)',"(F12.0,4(',',E24.16))",'*CFCLOS','ALLSEL,ALL']
    lines += [f'*DEL,{name}' for name in variables]
    return lines


def stage_block(index,strain,model,protocol):
    prefix=f'stage{index:03d}';top=model['controls']['top'];bottom=model['controls']['bottom']
    height=model['config']['height'];target=-height*strain
    lines=['/SOLU']
    if index>1:lines+=['ANTYPE,STATIC,REST,,,CONTINUE']
    lines += [f'TIME,{strain:.17g}',f'D,{top},UY,{target:.17g}','SOLVE','FINISH','/POST1','ALLSEL,ALL','SET,LAST',
           '*GET,TNOW,ACTIVE,0,SET,TIME','*GET,LSV,ACTIVE,0,SET,LSTP','*GET,SSV,ACTIVE,0,SET,SBST',
           f'*GET,UYTOP,NODE,{top},U,Y',f'*GET,RFTOP,NODE,{top},RF,FY',f'*GET,RFBOT,NODE,{bottom},RF,FY',
           f'*CFOPEN,{prefix}_history,csv','*VWRITE',"('pseudo_time,load_step,substep,top_uy_mm,upper_rf_y_N,lower_rf_y_N')",
           '*VWRITE,TNOW,LSV,SSV,UYTOP,RFTOP,RFBOT',"(E24.16,2(',',F10.0),3(',',E24.16))",'*CFCLOS',
           'FAILG=0',f'*IF,ABS(TNOW-{strain:.17g}),GT,1e-12,THEN','FAILG=1','*ENDIF',
           f'*IF,ABS(UYTOP-({target:.17g})),GT,1e-8,THEN','FAILG=1','*ENDIF',
           '*IF,RFTOP,GE,-1e-8,THEN','FAILG=1','*ENDIF','*IF,RFBOT,LE,1e-8,THEN','FAILG=1','*ENDIF',
           'BAL=ABS(RFTOP+RFBOT)/MAX(ABS(RFTOP),ABS(RFBOT),1e-12)',
           '*IF,BAL,GT,0.01,THEN','FAILG=1','*ENDIF',
           f'*CFOPEN,{prefix}_contact,csv','*VWRITE',
           "('pair,element,status,pressure_i_MPa,pressure_j_MPa,gap_i_mm,gap_j_mm,contact_force_y_N')",
           '*DO,PAIR,1,2','*IF,PAIR,EQ,1,THEN','CMSEL,S,BOTTOM_CONTACT','EXPECT=RFBOT','*ELSE','CMSEL,S,TOP_CONTACT','EXPECT=RFTOP','*ENDIF',
           '*GET,NC,ELEM,0,COUNT','EID=0','FYTOTAL=0','CLOSED=0','MAXPEN=0','MAXPRES=0',
           '*DO,KK,1,NC','EID=ELNEXT(EID)','*GET,STV,ELEM,EID,NMISC,19',
           '*GET,PI,ELEM,EID,SMISC,1','*GET,PJ,ELEM,EID,SMISC,2','*GET,GI,ELEM,EID,NMISC,5','*GET,GJ,ELEM,EID,NMISC,6',
           '*GET,FYV,ELEM,EID,NMISC,22','FYTOTAL=FYTOTAL+FYV','MAXPEN=MAX(MAXPEN,GI,GJ)','MAXPRES=MAX(MAXPRES,PI,PJ)',
           '*IF,STV,GE,2,THEN','CLOSED=CLOSED+1','*ENDIF',
           '*VWRITE,PAIR,EID,STV,PI,PJ,GI,GJ,FYV',"(F4.0,',',F12.0,',',F4.0,5(',',E16.8))",'*ENDDO',
           '*IF,CLOSED,LT,1,THEN','FAILG=1','*ENDIF','*IF,MAXPRES,LE,0,THEN','FAILG=1','*ENDIF',
           '*IF,MAXPEN,GT,1e-5,THEN','FAILG=1','*ENDIF',
           'CBAL=ABS(FYTOTAL+EXPECT)/MAX(ABS(EXPECT),1e-12)',
           '*IF,CBAL,GT,0.01,THEN','FAILG=1','*ENDIF','ALLSEL,ALL','*ENDDO','*CFCLOS',
           f'*CFOPEN,{prefix}_gate,txt','*VWRITE,FAILG,BAL',"(F4.0,',',E24.16)",'*CFCLOS']
    lines+=vector_fields(model['specimen_nodes'],prefix)
    lines+=['*IF,FAILG,NE,0,THEN','/COM,PILOT_STAGE_GATE_FAILED_NO_ADVANCEMENT','FINISH','SAVE,pilot_partial,db','/EXIT,NOSAVE','*ENDIF','FINISH']
    return lines


def prepare_pilot(directory,setup,protocol_path):
    directory,setup,protocol_path=Path(directory),Path(setup),Path(protocol_path)
    protocol=json.loads(protocol_path.read_text());model=json.loads((setup/'model_manifest.json').read_text())
    setup_result=json.loads((setup/'contact_setup_validation.json').read_text())
    if setup_result['status']!='CONTACT_SETUP_PASS':raise ValueError('Contact setup gate incomplete')
    if file_hash(setup/'contact_model.db')!=setup_result['process']['artifacts']['contact_model.db']['sha256']:
        raise ValueError('Contact database changed')
    if protocol['FTOLN_absolute_mm']!=model['FTOLN_absolute_mm']:raise ValueError('Frozen contact protocol differs')
    directory.mkdir(parents=True,exist_ok=False)
    lines=['/BATCH','/CLEAR,START',database_resume(setup/'contact_model.db').strip(),'/NOPR']
    for i,strain in enumerate(protocol['strains'],1):lines+=stage_block(i,strain,model,protocol)
    lines+=['SAVE,pilot_final,db','/EXIT,NOSAVE']
    (directory/'input.inp').write_text('\n'.join(lines)+'\n')
    write_json(directory/'simulation_manifest.json',{'protocol_sha256':file_hash(protocol_path),
        'source_contact_setup_receipt_sha256':file_hash(setup/'contact_setup_validation.json'),
        'source_contact_database_sha256':file_hash(setup/'contact_model.db'),'model':model,
        'source_geometry_sha256':protocol['source_geometry_sha256'],'mesh_semantic_sha256':protocol['mesh_semantic_sha256'],
        'input_sha256':file_hash(directory/'input.inp'),'contact_scope':'PLATEN_CONTACT_ONLY',
        'actual_execution':'NOT_EXECUTED','mechanical_mesh_convergence':'UNQUALIFIED'})
    return model


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['assembly','setup'])
    p.add_argument('--manifest',type=Path,required=True);p.add_argument('--ftoln',type=float,default=-1e-5)
    a=p.parse_args();mesh,manifest,_=resolve_manifest(a.manifest)
    cfg={k:manifest['settings']['config'][k] for k in CompressionConfig.__dataclass_fields__};cfg['strains']=tuple(cfg['strains']);config=CompressionConfig(**cfg)
    base=artifact_root()/'solver/v063';database=base/'import_001/specimen.db'
    report_path=Path(__file__).resolve().parents[2]/'experiments/pipeline_v0.6.3/run_001/import_only/attempt_001/validation/import_validation.json'
    report=json.loads(report_path.read_text())
    if report['status']!='ANSYS_IMPORT_PASS' or file_hash(database)!=report['solver_database_sha256']:
        raise ValueError('Authenticated import gate required before model/resource checks')
    if (report['actual_nodes'],report['actual_PLANE183_TRI6'])!=(manifest['nodes'],manifest['TRI6']):
        raise ValueError('Import/artifact inventory mismatch')
    if a.action=='assembly':result=assembly_check(database,mesh,base/'assembly_001')
    else:result=setup_contact(database,mesh,base/'contact_setup_001',config,a.ftoln)
    print(result['status'],flush=True)


if __name__=='__main__':main()
