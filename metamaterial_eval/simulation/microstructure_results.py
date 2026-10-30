"""Corroborate actual checkpoint results, signed contact forces and full fields."""
import argparse
import csv
import json
from pathlib import Path
import re
import numpy as np
from .mesh_artifacts import resolve_manifest,artifact_root
from .element_quality import quadratic_mapping
from .reporting import write_json
from .solver_execution import file_hash


def numeric(path,columns):
    with Path(path).open() as f:
        if f.readline().strip().split(',')!=columns:raise ValueError('CSV schema mismatch: '+Path(path).name)
    values=np.loadtxt(path,delimiter=',',skiprows=1,ndmin=2)
    if values.shape[1]!=len(columns) or not len(values) or not np.isfinite(values).all():raise ValueError('Incomplete/nonfinite actual CSV')
    return values


def dump_csv(path,rows):
    if not rows:return
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def force_metrics(time,uy,upper,lower,width=10.24,height=10.24,thickness=1):
    if not np.isfinite([time,uy,upper,lower]).all() or uy>=0 or upper>=-1e-8 or lower<=1e-8:
        raise ValueError('Absent force transmission or invalid native reaction signs')
    residual=abs(upper+lower)/max(abs(upper),abs(lower),1e-12)
    if residual>.01:raise ValueError('Reaction equilibrium failed')
    return {'pseudo_time':time,'compression_displacement_mm':-uy,'engineering_compression_strain':-uy/height,
            'upper_rf_y_N':upper,'lower_rf_y_N':lower,'nominal_compression_stress_MPa':-upper/(width*thickness),
            'reaction_balance_relative':residual}


def contact_metrics(values,expected_counts,upper,lower):
    result=[]
    for pair,group,rf in [(1,'bottom',lower),(2,'top',upper)]:
        subset=values[values[:,0]==pair]
        if len(subset)!=expected_counts[group] or len(np.unique(subset[:,1]))!=len(subset):raise ValueError('Incomplete contact inventory')
        if not np.isin(subset[:,2],[0,1,2,3]).all():raise ValueError('Invalid or unavailable contact status')
        closed=int(np.sum(subset[:,2]>=2));pressure=float(subset[:,3:5].max());penetration=float(max(0,subset[:,5:7].max()))
        force=float(subset[:,7].sum());balance=abs(force+rf)/max(abs(rf),1e-12)
        if not closed or pressure<=0 or penetration>1e-5 or balance>.01:raise ValueError('Contact engagement/penetration/force gate failed')
        result.append({'pair':group,'closed_elements':closed,'total_elements':len(subset),
                       'max_stored_endpoint_pressure_MPa':pressure,'max_stored_endpoint_penetration_mm':penetration,
                       'minimum_signed_gap_mm':float(subset[:,5:7].min()),'contact_element_force_y_N':force,
                       'pilot_reaction_y_N':rf,'signed_opposition_residual_relative':balance})
    return result


def fit_stiffness(rows):
    chosen=[r for r in rows if 0<r['engineering_compression_strain']<=.001+1e-12]
    if len(chosen)<2:return {'status':'INSUFFICIENT_POINTS','effective_modulus_MPa':None,'secant_modulus_MPa':chosen[0]['nominal_compression_stress_MPa']/chosen[0]['engineering_compression_strain'] if chosen else None}
    x=np.array([r['engineering_compression_strain'] for r in chosen]);y=np.array([r['nominal_compression_stress_MPa'] for r in chosen])
    slope=float(x@y/(x@x));sse=float(np.sum((y-slope*x)**2));sst=float(np.sum((y-y.mean())**2))
    return {'status':'PRELIMINARY_SINGLE_MESH_FIT','effective_modulus_MPa':slope,'base_material_modulus_MPa':1000,
            'normalized_modulus':slope/1000,'points':len(chosen),'method':'least squares through origin',
            'strain_interval':[0,.001],'R_squared':1-sse/sst if sst>0 else None}


def postprocess(directory,artifact_manifest,protocol_path,output):
    directory,output,protocol_path=Path(directory),Path(output),Path(protocol_path);output.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((directory/'execution_receipt.json').read_text());manifest=json.loads((directory/'simulation_manifest.json').read_text())
    protocol=json.loads(protocol_path.read_text());mesh,artifact,_=resolve_manifest(artifact_manifest)
    if file_hash(protocol_path)!=manifest['protocol_sha256'] or artifact['semantic_sha256']!=manifest['mesh_semantic_sha256']:
        raise ValueError('Changed protocol/mesh identity')
    log=(directory/'solver.out').read_text(errors='replace')
    completed=set(map(tuple,receipt['converged_steps']));rows=[];contacts=[];stages=[];failed=None
    corners=np.unique(mesh.triangles[:,:3])+1
    for i,target in enumerate(protocol['strains'],1):
        prefix=f'stage{i:03d}'
        try:
            names=[prefix+s for s in ['_history.csv','_gate.txt','_displacements.csv','_stress.csv','_contact.csv']]
            for name in names:
                if receipt['process']['artifacts'].get(name,{}).get('sha256')!=file_hash(directory/name):raise ValueError('Missing/altered actual checkpoint: '+name)
            gate=(directory/(prefix+'_gate.txt')).read_text().split(',')
            if float(gate[0])!=0:raise ValueError('Actual solver checkpoint gate failed')
            h=numeric(directory/(prefix+'_history.csv'),['pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'])
            if len(h)!=1:raise ValueError('Duplicate checkpoint history')
            t,ls,ss,uy,upper,lower=h[0]
            if ls!=i or ss!=int(ss) or (int(ls),int(ss)) not in completed:raise ValueError('Uncorroborated load-step convergence')
            if not np.isclose(t,target,atol=1e-12,rtol=0) or not np.isclose(uy,-10.24*target,atol=1e-8,rtol=0):raise ValueError('Requested checkpoint not achieved')
            row={'stage':i,'load_step':int(ls),'substep':int(ss),**force_metrics(t,uy,upper,lower)}
            c=numeric(directory/(prefix+'_contact.csv'),['pair','element','status','pressure_i_MPa','pressure_j_MPa','gap_i_mm','gap_j_mm','contact_force_y_N'])
            cm=contact_metrics(c,manifest['model']['contact_elements'],upper,lower)
            u=numeric(directory/(prefix+'_displacements.csv'),['node','ux_mm','uy_mm'])
            s=numeric(directory/(prefix+'_stress.csv'),['node','syy_MPa','seqv_MPa','elastic_eyy','elastic_exx'])
            if not np.array_equal(u[:,0],np.arange(1,len(mesh.nodes)+1)) or not np.array_equal(s[:,0],corners):raise ValueError('Incomplete all-node/corner field inventory')
            deformed=mesh.nodes+u[:,1:3]
            mapping=quadratic_mapping(deformed[mesh.triangles])
            if not np.all(mapping['positive_over_reference_triangle']):raise ValueError('Deformed quadratic mapping invalid/uncertified')
            field={'actual_nodes':len(u),'actual_stress_corner_nodes':len(s),'max_displacement_magnitude_mm':float(np.linalg.norm(u[:,1:3],axis=1).max()),
                   'SYY_range_MPa':[float(s[:,1].min()),float(s[:,1].max())],
                   'elastic_EYY_range':[float(s[:,3].min()),float(s[:,3].max())],
                   'deformed_map_minimum_determinant_mm2':float(mapping['determinant_min'].min()),
                   'deformed_mapping':'all elements positive under registered analytic polynomial floating-point check',
                   'stress_location':'supported corner-node averages only; no midside stresses fabricated'}
            rows.append(row);contacts.extend({'stage':i,**item} for item in cm)
            stages.append({'stage':i,'status':'VALID_CONVERGED','fields':field,
                           'raw_files':{name:receipt['process']['artifacts'][name]['sha256'] for name in names}})
            del u,s,deformed,mapping
        except (ValueError,FileNotFoundError) as exc:
            failed={'stage':i,'reason':str(exc)};break
    warnings=receipt.get('warnings',[])
    unsupported=bool(re.search(r'Requested data is not stored|Unknown label|Undefined parameter',log,re.I))
    if unsupported:
        status='OUTPUT_INCOMPLETE';eligible=[]
    else:
        eligible=rows
        status=('VALID_WITH_DOCUMENTED_WARNING' if warnings else 'VALID_CONVERGED') if len(rows)==len(protocol['strains']) else ('PARTIALLY_CONVERGED' if rows else 'SOLVER_FAILED')
    if not rows and receipt['status'] in ['MEMORY_BUDGET_EXCEEDED','OS_RAM_RESERVE_REACHED','DISK_RESERVE_EXHAUSTED','TIMEOUT']:status='RESOURCE_LIMIT'
    dump_csv(output/'force_displacement.csv',rows)
    dump_csv(output/'stress_strain.csv',[{k:r[k] for k in ['stage','pseudo_time','engineering_compression_strain','nominal_compression_stress_MPa']} for r in rows])
    dump_csv(output/'contact_diagnostics.csv',contacts)
    summary={'schema':'young-dawgs-v0.6.3-mechanical-results','status':status,'actual_valid_stages':rows,'stage_fields':stages,
             'solver_reported_converged_substeps':receipt['converged_steps'],
             'logged_converged_substep_times':[(int(a),int(b),float(t)) for a,b,t in re.findall(
                 r'LOAD STEP\s+(\d+)\s+SUBSTEP\s+(\d+)\s+COMPLETED[^\n]*\s*\*+\s*TIME=\s*([\d.Ee+\-]+)',log,re.I)],
             'first_failed_or_missing_stage':failed,'unsupported_output_queries':unsupported,
             'effective_stiffness':fit_stiffness(eligible),'warnings':warnings,'execution_receipt_sha256':file_hash(directory/'execution_receipt.json'),
             'result_RST_sha256':file_hash(directory/'compression.rst') if (directory/'compression.rst').exists() else None,
             'protocol_sha256':file_hash(protocol_path),'mesh_semantic_sha256':artifact['semantic_sha256'],
             'source_geometry_sha256':artifact['source_geometry_sha256'],'contact_scope':'PLATEN_CONTACT_ONLY',
             'pseudo_time':'load parameter, not physical seconds','sign_convention':'native upper RF negative, lower positive; CNFY is opposite support RF',
             'mechanical_mesh_convergence':'UNQUALIFIED','internal_self_contact':'UNQUALIFIED_NOT_CONFIGURED',
             'scientific_status':'PRELIMINARY_SINGLE_MESH_RESEARCH_HOLD','eligible_for_design_ranking':False}
    write_json(output/'mechanical_summary.json',summary)
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--execution',type=Path);p.add_argument('--protocol',type=Path)
    a=p.parse_args();protocol=a.protocol or Path(__file__).resolve().parents[2]/'experiments/pipeline_v0.6.3/run_001/protocol/PILOT_PROTOCOL_001.json'
    result=postprocess(a.execution or artifact_root()/'solver/v063/pilot_001',a.manifest,protocol,a.output)
    print(result['status'],result['actual_valid_stages'],flush=True)


if __name__=='__main__':main()
