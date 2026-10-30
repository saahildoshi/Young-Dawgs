"""v0.6.2 real MAPDL benchmark: native reactions and supported field locations.

Legacy v0.6.1 synthetic controls retain their positive-compression convention.
Here raw RF is the ANSYS support reaction: upper negative, lower positive.
Nodal displacement is exported everywhere; stress/elastic strain only at corner
nodes, since MAPDL 2024 R1 does not store those nodal quantities at midsides.
"""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import re
import shutil
import csv
import numpy as np
from shapely import box

from .ansys_adapter import write_input
from .ansys_qualification import evidence_token, checked_qualification
from .config import CompressionConfig
from .mesh_generation import generate_mesh, save_mesh, Mesh
from .mesh_remediation import POLICY_B
from .mesh_validation import validate_mesh
from .mechanical_metrics import compression_metrics, effective_stiffness
from .postprocessing import read_numeric_csv
from .reporting import write_json, mesh_hash
from .solver_execution import execute, file_hash

HISTORY=['set','pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N']
NODAL=['set','pseudo_time','node','ux_mm','uy_mm']
STRESS=['set','pseudo_time','node','syy_MPa','seqv_MPa','elastic_eyy','elastic_exx']
CONTACT=['set','pseudo_time','pair','element','status','pressure_MPa','penetration_mm','gap_mm']


def load_mesh(path):
    with np.load(path,allow_pickle=False) as z:
        return Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])


def export_macro(mesh, contact):
    corners=np.unique(mesh.triangles[:,:3])+1
    lines=['/POST1','ALLSEL,ALL','SET,LAST','*GET,NSETS,ACTIVE,0,SET,NSET','SET,FIRST',
           '*CFOPEN,nodal_fields,csv','*VWRITE',"('"+','.join(NODAL)+"')",'*DO,JJ,1,NSETS',
           '*GET,TNOW,ACTIVE,0,SET,TIME',f'*DO,NN,1,{len(mesh.nodes)}',
           '*GET,UXV,NODE,NN,U,X','*GET,UYV,NODE,NN,U,Y',
           '*VWRITE,JJ,TNOW,NN,UXV,UYV',"(F8.0,',',E16.8,',',F12.0,2(',',E16.8))",
           '*ENDDO','*IF,JJ,LT,NSETS,THEN','SET,NEXT','*ENDIF','*ENDDO','*CFCLOS',
           'SET,FIRST','*CFOPEN,stress_fields,csv','*VWRITE',"('"+','.join(STRESS)+"')",'*DO,JJ,1,NSETS',
           '*GET,TNOW,ACTIVE,0,SET,TIME','ESEL,S,TYPE,,1']
    # Explicit corner list avoids unsupported midside *GET and stale parameters.
    for node in corners:
        lines += [f'*GET,SYV,NODE,{node},S,Y',f'*GET,SEQV,NODE,{node},S,EQV',
                  f'*GET,EYV,NODE,{node},EPEL,Y',f'*GET,EXV,NODE,{node},EPEL,X',
                  f'*VWRITE,JJ,TNOW,{node},SYV,SEQV,EYV,EXV',
                  "(F8.0,',',E16.8,',',F12.0,4(',',E16.8))"]
    lines += ['ALLSEL,ALL','*IF,JJ,LT,NSETS,THEN','SET,NEXT','*ENDIF','*ENDDO','*CFCLOS']
    if contact:
        from .result_extraction import field_export_macro
        old=field_export_macro(len(mesh.nodes),True)
        lines += old[old.index('SET,FIRST\n*CFOPEN,contact_fields'):].splitlines()
    return '\n'.join(lines+['ALLSEL,ALL','FINISH'])+'\n'


def prepare(output, protocol, *, contact=False, thickness=1.0, correction=None):
    output,protocol=Path(output),Path(protocol)
    frozen=json.loads(protocol.read_text())
    config=replace(CompressionConfig(),boundary_size=.512,bulk_size=1.28,
                   strains=tuple(frozen['requested_strains']),thickness=thickness)
    mesh=generate_mesh(box(0,0,config.width,config.height),config,policy=POLICY_B)
    quality,_=validate_mesh(mesh,box(0,0,config.width,config.height),config)
    if not quality['accepted']:raise ValueError('Rectangle mesh quality failed')
    manifest=write_input(output,mesh,config,contact=contact)
    deck=(output/'compression.inp').read_text()
    # /BATCH must be the first line. Explicit MINREF removes an implicit default.
    deck='/BATCH\n'+deck.replace('/BATCH\n','')
    deck=deck.replace('CNVTOL,F,,0.005,2','CNVTOL,F,,0.005,2,0.001')
    if correction:
        if not contact:raise ValueError('Contact correction requires a contact model')
        change=json.loads(Path(correction).read_text())['correction']
        for real in [2,3]:
            deck=deck.replace(f'R,{real}\n',f'R,{real},0,0,{change["FKN"]},{change["FTOLN_absolute_mm"]:.16g}\n')
    deck=deck.replace('/OUTPUT,model_inventory,txt','CDWRITE,DB,rectangle,cdb\n/OUTPUT,model_inventory,txt')
    # Export exact solver-side mesh records for independent import comparison.
    inventory=['*CFOPEN,import_nodes,csv','*VWRITE',"('node,x_mm,y_mm,z_mm')",f'*DO,NN,1,{len(mesh.nodes)}',
               '*GET,XV,NODE,NN,LOC,X','*GET,YV,NODE,NN,LOC,Y','*GET,ZV,NODE,NN,LOC,Z',
               '*VWRITE,NN,XV,YV,ZV',"(F12.0,3(',',E24.16))",'*ENDDO','*CFCLOS',
               '*CFOPEN,import_elements,csv','*VWRITE',"('element,type,material,real,n1,n2,n3,n4,n5,n6')",
               f'*DO,EE,1,{len(mesh.triangles)}','*GET,TV,ELEM,EE,ATTR,TYPE','*GET,MV,ELEM,EE,ATTR,MAT',
               '*GET,RV,ELEM,EE,ATTR,REAL']
    inventory += [f'*GET,EV{i},ELEM,EE,NODE,{i}' for i in range(1,7)]
    inventory += ['*VWRITE,EE,TV,MV,RV,EV1,EV2,EV3,EV4,EV5,EV6',"(F12.0,9(',',F12.0))",'*ENDDO','*CFCLOS']
    deck=deck.replace('/SOLU','\n'.join(['/PREP7',*inventory,'FINISH','/SOLU']),1)
    (output/'compression.inp').write_text(deck)
    (output/'extract_fields.mac').write_text(export_macro(mesh,contact))
    save_mesh(mesh,output/'mesh.npz')
    manifest.update(schema='young-dawgs-v0.6.2-input',field_schema='displacement_all_stress_corners',
                    protocol_sha256=file_hash(protocol),reaction_sign_convention='native_ANSYS_support_RF',
                    mesh_quality=quality,documentation='v241 help unavailable; v242 comparison plus actual v241 empirical verification')
    if correction:
        manifest['contact_correction_sha256']=file_hash(correction)
        manifest['contact_numerics']=change
    write_json(output/'input_manifest.json',manifest)
    return manifest


def write_csv(path,rows):
    if not rows:return
    with Path(path).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def export_evidence(execution, output):
    """Track compact text/numeric evidence; retain complete raw runs locally."""
    execution,output=Path(execution),Path(output)
    output.mkdir(parents=True,exist_ok=False)
    for name in ['solver_status.json','input_manifest.json','compression.inp','extract_fields.mac',
                 'history.csv','import_nodes.csv','import_elements.csv']:
        if (execution/name).exists():shutil.copy2(execution/name,output/name)
    manifest=json.loads((execution/'input_manifest.json').read_text())
    stages=read_numeric_csv(execution/'history.csv',HISTORY)
    selected={r['set'] for r in stages if any(np.isclose(r['pseudo_time'],s,rtol=0,atol=1e-12) for s in [.005,.01,.02])}
    for name,columns in [('nodal_fields.csv',NODAL),('stress_fields.csv',STRESS),('contact_fields.csv',CONTACT)]:
        if (execution/name).exists():
            rows=read_numeric_csv(execution/name,columns)
            write_csv(output/name,[r for r in rows if r['set'] in selected])
    # Raw logs and RST hashes remain in the immutable solver receipt. Sanitized
    # logs are explicitly labelled and have their own hashes, never substituted.
    for name in ['solver.out','model_inventory.txt','compression.err','compression.mntr']:
        if (execution/name).exists():
            log=(execution/name).read_text(errors='replace')
            log=re.sub(r'\b\d{8}\s+VERSION=', '[site-redacted] VERSION=',log)
            log=log.replace(str(Path.cwd()),'[repository]')
            log=re.sub(r'(?im)^.*(?:license server|license file|USER=|HOST=).*$','[environment line redacted]',log)
            log='\n'.join(line.rstrip() for line in log.splitlines()).rstrip()+'\n'
            (output/(name+'.sanitized.txt')).write_text(log)
    write_json(output/'evidence_manifest.json',{
        'raw_execution':str(execution.resolve()),'raw_receipt_sha256':file_hash(execution/'solver_status.json'),
        'raw_RST_sha256':file_hash(execution/'compression.rst'),'mesh_sha256':manifest['mesh_sha256'],
        'selected_pseudo_times':[.005,.01,.02],'stress_location':'corner nodal averages only',
        'raw_outputs':'complete immutable run retained locally under ignored generated directory',
        'exported_files':{p.name:file_hash(p) for p in output.iterdir() if p.is_file()}})


def native_metrics(history,config):
    upper=np.array([r['upper_rf_y_N'] for r in history])
    lower=np.array([r['lower_rf_y_N'] for r in history])
    # Explicit conversion only for the legacy positive-compression metric API.
    return compression_metrics([r['top_uy_mm'] for r in history],-upper,-lower,config)


def verify_import(execution,mesh,manifest):
    nodes=read_numeric_csv(execution/'import_nodes.csv',['node','x_mm','y_mm','z_mm'])
    elements=read_numeric_csv(execution/'import_elements.csv',
                              ['element','type','material','real',*[f'n{i}' for i in range(1,7)]])
    if [r['node'] for r in nodes]!=list(range(1,len(mesh.nodes)+1)):
        raise ValueError('Solver-side node inventory mismatch')
    if not np.allclose([[r['x_mm'],r['y_mm']] for r in nodes],mesh.nodes,atol=1e-13,rtol=1e-14):
        raise ValueError('Solver-side coordinates differ')
    if any(r['z_mm']!=0 for r in nodes):raise ValueError('Nonplanar solver model')
    if [r['element'] for r in elements]!=list(range(1,len(mesh.triangles)+1)):
        raise ValueError('Solver-side element inventory mismatch')
    if not np.array_equal([[r[f'n{i}'] for i in range(1,7)] for r in elements],mesh.triangles+1):
        raise ValueError('Solver-side TRI6 order differs')
    if any((r['type'],r['material'],r['real'])!=(1,1,1) for r in elements):
        raise ValueError('Solver-side structural attributes differ')
    inventory=(execution/'model_inventory.txt').read_text()
    required=['PLANE183','2-D 6-NODE PLANE STRS SOLID','BOTTOM_FACE','TOP_FACE','1000.000','0.3000000']
    if manifest['platen_contact']:required+=['CONTA172','TARGE169','TOP_CONTACT','BOTTOM_CONTACT']
    if any(token not in inventory for token in required):raise ValueError('Solver model definitions incomplete')
    if not re.search(r'KEYOPT\( 1- 6\)=\s+1\s+0\s+3\s+0\s+0\s+0',inventory):
        raise ValueError('Solver PLANE183 options differ')
    constants=re.search(r'REAL CONSTANT SET\s+1\s+ITEMS\s+1 TO\s+6\s+([\d.Ee+\-]+)',inventory)
    if not constants or not np.isclose(float(constants[1]),manifest['config']['thickness']):
        raise ValueError('Actual specimen thickness differs')
    if manifest['platen_contact']:
        # DLIST is actual solver state, before applying the upper pilot travel.
        constraints=re.findall(r'^\s*(\d+)\s+(UX|UY|ROTZ)\s+([\d.Ee+\-]+)',inventory,re.M)
        if any(int(n)<=len(mesh.nodes) and dof=='UY' for n,dof,_ in constraints):
            raise ValueError('Contact bypassed by specimen UY constraints')
        solver_log=(execution/'solver.out').read_text()
        if any(token not in solver_log for token in [
            'Frictionless contact pair is defined',
            'CONTACT PAIR HAVING REAL ID =           2 IS INITIALLY CLOSED',
            'CONTACT PAIR HAVING REAL ID =           3 IS INITIALLY CLOSED']):
            raise ValueError('Actual initial contact/formulation check missing')
        if manifest.get('contact_algorithm_keyopt2',0)==1:
            if not re.search(r'Contact algorithm:.*penalty',solver_log,re.I):raise ValueError('Actual pure-penalty algorithm missing')
        elif 'Contact algorithm: Augmented Lagrange method' not in solver_log:raise ValueError('Actual augmented-Lagrange algorithm missing')
    return {'status':'PASS','nodes':len(nodes),'TRI6':len(elements),'exact_connectivity':True,
            'axes':'global XY','max_coordinate_error_mm':float(np.max(np.abs(np.array([[r['x_mm'],r['y_mm']] for r in nodes])-mesh.nodes))),
            'stress_field_location':'corner_nodes_only; midside displacements retained'}


def analyze(execution, output, protocol):
    execution,output,protocol=Path(execution).resolve(),Path(output).resolve(),Path(protocol).resolve()
    output.mkdir(parents=True,exist_ok=False)
    try:
        receipt=json.loads((execution/'solver_status.json').read_text())
        if receipt['status']!='EXECUTED_PENDING_IMPORT_CONTACT_AND_NUMERIC_VALIDATION':
            raise ValueError('Solver process did not complete cleanly')
        if receipt['solver_version']!='2024 R1':raise ValueError('Unexpected solver release')
        manifest=json.loads((execution/'input_manifest.json').read_text())
        if file_hash(protocol)!=manifest['protocol_sha256']:raise ValueError('Protocol hash differs')
        required=['compression.rst','solver.out','history.csv','nodal_fields.csv','stress_fields.csv',
                  'model_inventory.txt','import_nodes.csv','import_elements.csv','compression.inp','extract_fields.mac','mesh.npz','input_manifest.json']
        if manifest['platen_contact']:required.append('contact_fields.csv')
        for name in required:
            if receipt['outputs'].get(name)!=file_hash(execution/name):raise ValueError('Missing or altered output: '+name)
        log=(execution/'solver.out').read_text(errors='replace')
        if re.search(r'Requested data is not stored|undefined parameter|\*\*\*\s*(?:ERROR|FATAL)\s*\*\*\*',log,re.I):
            raise ValueError('Solver error or unsupported result query')
        mesh=load_mesh(execution/'mesh.npz')
        if mesh_hash(mesh)!=manifest['mesh_sha256']:raise ValueError('Mesh hash differs')
        import_result=verify_import(execution,mesh,manifest)
        c={k:manifest['config'][k] for k in CompressionConfig.__dataclass_fields__}
        c['strains']=tuple(c['strains']);config=CompressionConfig(**c)
        frozen=json.loads(protocol.read_text())
        history=read_numeric_csv(execution/'history.csv',HISTORY)
        completed={(int(a),int(b)) for a,b in re.findall(r'LOAD STEP\s+(\d+)\s+SUBSTEP\s+(\d+)\s+COMPLETED',log,re.I)}
        if any((int(r['load_step']),int(r['substep'])) not in completed for r in history):
            raise ValueError('Unconverged result set in history')
        if [r['set'] for r in history]!=list(range(1,len(history)+1)) or any(b['pseudo_time']<=a['pseudo_time'] for a,b in zip(history,history[1:])):
            raise ValueError('Invalid or duplicate result sets')
        m=native_metrics(history,config)
        strain=m['engineering_compression_strain'];stress=m['nominal_compression_stress_MPa']
        if not m['force_balance_pass']:raise ValueError('Native reactions do not balance')
        requested=[]
        for target in config.strains:
            ids=np.flatnonzero(np.isclose([r['pseudo_time'] for r in history],target,atol=1e-12,rtol=1e-8))
            if len(ids)!=1:raise ValueError('Requested stage not uniquely achieved')
            i=int(ids[0]);row=history[i]
            if not np.isclose(row['top_uy_mm'],-config.height*target,atol=frozen['achieved_displacement_atol_mm'],rtol=frozen['achieved_displacement_rtol']):
                raise ValueError('Requested displacement not achieved')
            reference=config.young_modulus*strain[i]*config.width*config.thickness
            requested.append({**row,'engineering_compression_strain':float(strain[i]),
                              'nominal_compression_stress_MPa':float(stress[i]),'analytical_reference_N':float(reference),
                              'relative_error':float(abs(-row['upper_rf_y_N']-reference)/reference),
                              'analytical_acceptance_domain':target<=.005})
        small=strain<=.005+1e-9
        error=np.abs(stress[small]/(config.young_modulus*strain[small])-1)
        if np.any(error>frozen['analytical_relative_error_max']):raise ValueError('Analytical force tolerance exceeded')
        fields=read_numeric_csv(execution/'nodal_fields.csv',NODAL)
        stress_fields=read_numeric_csv(execution/'stress_fields.csv',STRESS)
        corners=(np.unique(mesh.triangles[:,:3])+1).tolist()
        for r in history:
            nodal=[x for x in fields if x['set']==r['set']]
            sf=[x for x in stress_fields if x['set']==r['set']]
            if sorted(x['node'] for x in nodal)!=list(range(1,len(mesh.nodes)+1)) or sorted(x['node'] for x in sf)!=corners:
                raise ValueError('Incomplete or duplicate actual fields')
            if any(not np.isclose(x['pseudo_time'],r['pseudo_time'],rtol=1e-8,atol=1e-12) for x in [*nodal,*sf]):
                raise ValueError('Field pseudo-time differs from actual set')
            if r['pseudo_time']<=.005:
                nominal=-r['upper_rf_y_N']/(config.width*config.thickness)
                if max(abs(x['syy_MPa']/(-nominal)-1) for x in sf)>.02:
                    raise ValueError('Actual stress field inconsistent with nominal force')
                eps=-r['top_uy_mm']/config.height
                if max(abs(x['elastic_eyy']/(-eps)-1) for x in sf)>.02:
                    raise ValueError('Actual elastic strain field inconsistent with displacement')
        contacts=[];diagnostics=[]
        if manifest['platen_contact']:
            contacts=read_numeric_csv(execution/'contact_fields.csv',CONTACT)
            for r in history:
                for pair,group in [(1,'bottom'),(2,'top')]:
                    subset=[x for x in contacts if x['set']==r['set'] and x['pair']==pair]
                    expected=len(manifest['contact_plan'][group]['edges'])
                    if len(subset)!=expected or len({x['element'] for x in subset})!=expected:
                        raise ValueError('Contact inventory incomplete or duplicated')
                    if not any(x['status']>=2 and x['pressure_MPa']>0 for x in subset):raise ValueError('Contact did not transmit pressure')
                    if any(x['status'] not in [0,1,2,3] or x['pressure_MPa']<0 for x in subset):raise ValueError('Invalid contact status/pressure')
                    penetration=max(max(0,x['penetration_mm']) for x in subset)
                    if penetration>frozen['contact_penetration_max_mm']:raise ValueError('Excessive penetration')
                    diagnostics.append({'set':r['set'],'pseudo_time':r['pseudo_time'],'pair':group,
                                        'closed_elements':sum(x['status']>=2 for x in subset),
                                        'pressure_max_MPa':max(x['pressure_MPa'] for x in subset),
                                        'penetration_max_mm':penetration,'gap_max_mm':max(x['gap_mm'] for x in subset),
                                        'pilot_reaction_y_N':r['lower_rf_y_N'] if pair==1 else r['upper_rf_y_N']})
        force=[];curve=[];balance=[]
        for i,r in enumerate(history):
            force.append({**r,'compression_displacement_mm':-r['top_uy_mm']})
            curve.append({'set':r['set'],'pseudo_time':r['pseudo_time'],
                          'engineering_compression_strain':float(strain[i]),'nominal_compression_stress_MPa':float(stress[i])})
            balance.append({'set':r['set'],'upper_rf_y_N':r['upper_rf_y_N'],'lower_rf_y_N':r['lower_rf_y_N'],
                            'relative_residual':float(m['force_balance_relative'][i])})
        write_csv(output/'force_displacement.csv',force);write_csv(output/'stress_strain.csv',curve)
        write_csv(output/'reaction_balance.csv',balance);write_csv(output/'contact_diagnostics.csv',diagnostics)
        write_csv(output/'requested_stages.csv',requested)
        summary={'status':'VALID_SOLVER_MEASUREMENTS','solver_receipt_sha256':file_hash(execution/'solver_status.json'),
                 'all_requested_stages_achieved':True,'completed_sets':len(history),'requested_stages':requested,
                 'force_balance_max_relative':float(m['force_balance_relative'].max()),
                 'max_relative_analytical_error_small_strain':float(error.max()),'mesh_import':import_result,
                 'effective_stiffness':effective_stiffness(strain,stress,config.young_modulus),
                 'maximum_contact_penetration_mm':max((d['penetration_max_mm'] for d in diagnostics),default=None),
                 'maximum_contact_pressure_MPa':max((d['pressure_max_MPa'] for d in diagnostics),default=None),
                 'stress_fields':'actual corner nodal averages; no midside stress fabricated',
                 'reaction_sign':'native ANSYS upper negative/lower positive; compressive stress = -upper_RF/(W*t)',
                 'solver_warnings':re.findall(r'\*\*\* WARNING \*\*\*[^\n]*\n([^\n]+)',log),
                 'pseudo_time':'load parameter, not seconds','llm_performance_eligible':False}
        write_json(output/'mechanical_summary.json',summary)
        report={'schema':'young-dawgs-v0.6.2-empirical-qualified-benchmark','status':'SOLVER_VERIFIED',
                'benchmark_stage':'platen_contact' if manifest['platen_contact'] else 'direct','config':config.manifest(),
                'actual_release':receipt['solver_version'],'execution_relative_path':str(Path(__import__('os').path.relpath(execution,output))),
                'solver_receipt_sha256':file_hash(execution/'solver_status.json'),
                'model_review_relative_path':'mechanical_summary.json','model_review_sha256':file_hash(output/'mechanical_summary.json'),
                'numeric_summary_relative_path':'mechanical_summary.json','numeric_summary_sha256':file_hash(output/'mechanical_summary.json'),
                'protocol_sha256':file_hash(protocol),'documentation_limitation':'v241 help inaccessible; v242 references checked empirically in actual v241 solver; no claim of completed v241 help review',
                'internal_self_contact':'UNQUALIFIED','mechanical_mesh_convergence':'UNQUALIFIED','paper_readiness':'HOLD'}
        write_json(output/'qualification.json',report)
        return summary
    except (ValueError,KeyError,FileNotFoundError) as exc:
        result={'status':'QUARANTINED','reason':str(exc),'llm_performance_eligible':False}
        write_json(output/'QUARANTINE.json',result)
        return result


def run(source,output,direct=None,timeout=180):
    evidence=evidence_token(direct) if direct else None
    return execute(source,output,timeout=timeout,benchmark_evidence=evidence)


def extract_contact_points(execution, output):
    """Read actual RST endpoint data and total element forces, not ETABLE averages."""
    from .solver_execution import discover_solver, classify_log
    from .windows_ansys import bounded_run
    execution,output=Path(execution).resolve(),Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((execution/'solver_status.json').read_text())
    for name in ['compression.rst','compression.rdb']:
        if file_hash(execution/name)!=receipt['outputs'][name]:raise ValueError('Altered actual RST/database')
    generated=output/'generated';generated.mkdir()
    for name in ['compression.rst','compression.rdb']:shutil.copy2(execution/name,generated/name)
    columns=['set','pseudo_time','pair','element','pressure_i_MPa','pressure_j_MPa',
             'signed_gap_i_mm','signed_gap_j_mm','contact_force_y_N']
    lines=['/BATCH','/CLEAR,START','RESUME,compression,rdb','/POST1','FILE,compression,rst','ALLSEL,ALL',
           'SET,LAST','*GET,NSETS,ACTIVE,0,SET,NSET','SET,FIRST','*CFOPEN,contact_points,csv',
           '*VWRITE',"('"+','.join(columns)+"')",'*DO,JJ,1,NSETS','*GET,TNOW,ACTIVE,0,SET,TIME',
           '*DO,PAIR,1,2','*IF,PAIR,EQ,1,THEN','CMSEL,S,BOTTOM_CONTACT','*ELSE','CMSEL,S,TOP_CONTACT','*ENDIF',
           '*GET,NC,ELEM,0,COUNT','EID=0','*DO,KK,1,NC','EID=ELNEXT(EID)',
           '*GET,PI,ELEM,EID,SMISC,1','*GET,PJ,ELEM,EID,SMISC,2',
           '*GET,GI,ELEM,EID,NMISC,5','*GET,GJ,ELEM,EID,NMISC,6',
           '*GET,FYV,ELEM,EID,NMISC,22','*VWRITE,JJ,TNOW,PAIR,EID,PI,PJ,GI,GJ,FYV',
           "(F8.0,',',E16.8,',',F4.0,',',F12.0,5(',',E16.8))",'*ENDDO','ALLSEL,ALL','*ENDDO',
           '*IF,JJ,LT,NSETS,THEN','SET,NEXT','*ENDIF','*ENDDO','*CFCLOS','FINISH','/EXIT,NOSAVE']
    (generated/'extract.inp').write_text('\n'.join(lines)+'\n')
    process=bounded_run([str(discover_solver()),'-b','-smp','-np','1','-j','post',
                         '-i','extract.inp','-o','post.out'],generated,prepared=True,timeout=120)
    log=(generated/'post.out').read_text(errors='replace')
    if process['returncode'] or re.search(r'\*\*\*\s*(?:ERROR|FATAL)\s*\*\*\*|Unknown label|not stored',log,re.I):
        write_json(output/'QUARANTINE.json',{'status':'POSTPROCESS_FAILED','process':process})
        return
    data=read_numeric_csv(generated/'contact_points.csv',columns)
    history=read_numeric_csv(execution/'history.csv',HISTORY)
    balance=[]
    for r in history:
        for pair,group,key in [(1,'bottom','lower_rf_y_N'),(2,'top','upper_rf_y_N')]:
            subset=[x for x in data if x['set']==r['set'] and x['pair']==pair]
            force=sum(x['contact_force_y_N'] for x in subset)
            balance.append({'set':r['set'],'pseudo_time':r['pseudo_time'],'pair':group,
                            'sum_contact_force_y_N':force,'native_pilot_RF_y_N':r[key],
                            'magnitude_relative_difference':abs(abs(force)-abs(r[key]))/max(abs(r[key]),1e-12)})
    maxpen=max(max(0,r['signed_gap_i_mm'],r['signed_gap_j_mm']) for r in data)
    maxdiff=max(r['magnitude_relative_difference'] for r in balance)
    shutil.copy2(generated/'contact_points.csv',output/'contact_points.csv')
    write_csv(output/'contact_force_balance.csv',balance)
    write_json(output/'contact_point_validation.json',{
        'status':'PASS' if maxpen<=.001 and maxdiff<=.01 else 'FAIL',
        'source_RST_sha256':file_hash(execution/'compression.rst'),
        'source_solver_receipt_sha256':file_hash(execution/'solver_status.json'),
        'postprocess_receipt_sha256':file_hash(generated/'process_receipt.json'),
        'point_csv_sha256':file_hash(output/'contact_points.csv'),
        'maximum_stored_endpoint_penetration_mm':maxpen,
        'maximum_contact_force_pilot_magnitude_difference_relative':maxdiff,
        'scope':'SMISC1/2 pressure; NMISC5/6 stored endpoint penetration/gap; NMISC22 total contact element force',
        'limitation':'stored contact endpoints are not an exhaustive continuous-surface penetration bound',
        'old_CONT_ETABLE_values':'element averages, not pointwise extrema; retained as such',
        'process':process})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare');p.add_argument('--contact',action='store_true');p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--correction',type=Path)
    p=sub.add_parser('run');p.add_argument('--source',type=Path,required=True);p.add_argument('--direct',type=Path)
    p=sub.add_parser('analyze');p.add_argument('--execution',type=Path,required=True);p.add_argument('--protocol',type=Path,required=True)
    p=sub.add_parser('contact-points');p.add_argument('--execution',type=Path,required=True)
    for p in sub.choices.values():p.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='prepare':result=prepare(args.output,args.protocol,contact=args.contact,correction=args.correction)
    elif args.action=='run':result=run(args.source,args.output,args.direct)
    elif args.action=='analyze':result=analyze(args.execution,args.output,args.protocol)
    else:result=extract_contact_points(args.execution,args.output)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
