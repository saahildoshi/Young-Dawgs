"""Qualify an explicitly identified converged native set, including partial jobs."""
from pathlib import Path
import re
import numpy as np
from .native_qualification import stream_csv
from .microstructure_results import numeric,force_metrics,contact_metrics,unsupported_result_queries
from .progressive_compression import load,result_sets
from .element_quality import quadratic_mapping
from .deformed_boundaries import screen
from .reporting import write_json,mesh_hash
from .solver_execution import file_hash,has_negative_pivots


def authenticate(source,export,mesh):
    source,export=Path(source),Path(export)
    receipt=load(source/'execution_receipt.json');post=load(export/'execution_receipt.json')
    manifest=load(source/'simulation_manifest.json');provenance=load(export/'provenance.json')
    if manifest['mesh_semantic_sha256']!=mesh_hash(mesh):raise ValueError('Source mesh identity mismatch')
    if receipt['input_sha256']!=manifest['input_sha256'] or file_hash(source/'input.inp')!=receipt['input_sha256']:raise ValueError('Source input mismatch')
    if post['status']!='PROCESS_EXITED' or post['process']['returncode']!=0:raise ValueError('Independent read-only process failed')
    bindings={'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
        'source_RST_sha256':file_hash(source/'compression.rst'),'source_database_sha256':file_hash(source/provenance['source_database_filename']),
        'source_manifest_sha256':file_hash(source/'simulation_manifest.json'),'input_sha256':file_hash(export/'input.inp')}
    if any(provenance.get(k)!=v for k,v in bindings.items()):raise ValueError('Read-only provenance mismatch')
    if post['input_sha256']!=bindings['input_sha256'] or re.search(r'^\s*(?:SOLVE|SAVE\s*,)',(export/'input.inp').read_text(),re.M|re.I):raise ValueError('Export contains solve/save or stale input')
    for directory,r,names in [(source,receipt,['compression.rst',provenance['source_database_filename'],'simulation_manifest.json','solver.out']),
                              (export,post,['solver.out','result_sets.txt'])]:
        for name in names:
            if file_hash(directory/name)!=r['process']['artifacts'].get(name,{}).get('sha256'):raise ValueError('Changed native evidence: '+name)
    text=(export/'solver.out').read_text(errors='replace')
    if unsupported_result_queries(text) or re.search(r'\*\*\*\s*(?:ERROR|FATAL)\s*\*\*',text,re.I):raise ValueError('Unsupported or invalid native readback')
    return manifest,receipt,post,provenance,result_sets((export/'result_sets.txt').read_text())


def qualify_state(source,export,mesh,index,state,output):
    source,export,output=map(Path,[source,export,output]);output.mkdir(parents=True,exist_ok=False)
    result={'schema':'young-dawgs-v0.6.6-actual-native-state','state':state,'accepted':False,'failures':[],
        'contact_scope':'PLATEN_ONLY_EXPLORATORY','mechanical_mesh_convergence':'UNQUALIFIED',
        'internal_self_contact':'UNQUALIFIED_NOT_CONFIGURED','eligible_for_LLM_performance_ranking':False,
        'source':str(source),'export':str(export)}
    try:
        manifest,receipt,post,provenance,sets=authenticate(source,export,mesh);model=manifest['model']
        key=(state['load_step'],state['substep']);converged=load(source/'nonlinear_telemetry.json')['converged_substeps']
        matching=[r for r in converged if (r['load_step'],r['substep'])==key and abs(r['pseudo_time']-state['time'])<1e-10]
        if len(matching)!=1 or not any((s['load_step'],s['substep'])==key and abs(s['time']-state['time'])<1e-10 for s in sets):raise ValueError('Set not independently corroborated as converged')
        if index<1 or provenance['states'][index-1]!=state:raise ValueError('Selected export identity mismatch')
        source_before='\n'.join((source/'solver.out').read_text(errors='replace').splitlines()[:matching[0]['source_line']])
        if has_negative_pivots(source_before) or re.search(r'\*\*\*\s*FATAL\s*\*\*',source_before,re.I):raise ValueError('Invalidating solver diagnostic before state')
        prefix=f'stage{index:03d}'
        names=[prefix+s for s in ['_history.csv','_gate.txt','_displacements.csv','_stress.csv','_contact.csv']]
        hashes={}
        for name in names:
            hashes[name]=file_hash(export/name)
            if hashes[name]!=post['process']['artifacts'].get(name,{}).get('sha256'):raise ValueError('Changed/incomplete exported field '+name)
        history=numeric(export/(prefix+'_history.csv'),['pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'])
        if history.shape!=(1,6):raise ValueError('Missing/duplicate native history')
        time,ls,ss,uy,upper,lower=history[0]
        if (ls,ss)!=key or abs(time-state['time'])>1e-10 or abs(uy+model['config']['height']*time)>1e-8:raise ValueError('Incorrect cumulative displacement/state')
        result.update(actual_history=history[0].tolist(),source_process_status=receipt['status'],native_RST_sha256=provenance['source_RST_sha256'],
            source_receipt_sha256=file_hash(source/'execution_receipt.json'),read_only_receipt_sha256=file_hash(export/'execution_receipt.json'),raw_native_field_hashes=hashes)
        try:
            result['measurement']=force_metrics(time,uy,upper,lower,**{k:model['config'][k] for k in ['width','height','thickness']})
        except ValueError as exc:result['failures'].append(str(exc))
        try:
            result['contacts']=contact_metrics(numeric(export/(prefix+'_contact.csv'),['pair','element','status','pressure_i_MPa','pressure_j_MPa','gap_i_mm','gap_j_mm','contact_force_y_N']),model['contact_elements'],upper,lower)
        except ValueError as exc:result['failures'].append(str(exc))
        if float((export/(prefix+'_gate.txt')).read_text().split(',')[0])!=0:result['failures'].append('Native mechanical gate failed')
        count=len(mesh.nodes);corners=np.unique(mesh.triangles[:,:3])+1
        if count!=model['specimen_nodes'] or len(mesh.triangles)!=model['specimen_TRI6']:raise ValueError('Mesh/model inventory mismatch')
        u=np.lib.format.open_memmap(output/'native_displacement.npy',mode='w+',dtype=np.float64,shape=(count,5));offset=0
        for v in stream_csv(export/(prefix+'_displacements.csv'),['node','ux_mm','uy_mm']):
            n=len(v)
            if offset+n>count or not np.array_equal(v[:,0],np.arange(offset+1,offset+n+1)):raise ValueError('Missing/duplicate displacement inventory')
            u[offset:offset+n,:2]=v[:,1:];u[offset:offset+n,2]=np.linalg.norm(v[:,1:],axis=1);u[offset:offset+n,3:]=mesh.nodes[offset:offset+n]+v[:,1:];offset+=n
        if offset!=count:raise ValueError('Incomplete all-node displacement')
        u.flush();stress=np.lib.format.open_memmap(output/'native_corner_stress_strain.npy',mode='w+',dtype=np.float64,shape=(len(corners),4));offset=0
        for v in stream_csv(export/(prefix+'_stress.csv'),['node','syy_MPa','seqv_MPa','elastic_eyy','elastic_exx']):
            n=len(v)
            if offset+n>len(corners) or not np.array_equal(v[:,0],corners[offset:offset+n]):raise ValueError('Missing/duplicate native corner field inventory')
            stress[offset:offset+n]=v[:,1:];offset+=n
        if offset!=len(corners):raise ValueError('Incomplete native continuum fields')
        stress.flush();minimum=np.inf;invalid=0
        for i in range(0,len(mesh.triangles),20000):
            tri=mesh.triangles[i:i+20000];q=quadratic_mapping(mesh.nodes[tri]+u[tri,:2]);invalid+=int(np.sum(~q['positive_over_reference_triangle']));minimum=min(minimum,float(q['determinant_min'].min()))
        if invalid:result['failures'].append('Invalid deformed quadratic mappings')
        overlap=screen(u[:,3:5],mesh.boundary,mesh.boundary_groups,original=mesh.nodes);write_json(output/'boundary_screen.json',overlap)
        if not overlap['passed']:result['failures'].append('Unmodeled overlap/near contact uncertainty')
        result.update(actual_nodes=count,actual_TRI6=len(mesh.triangles),actual_native_corner_nodes=len(corners),
            invalid_deformed_mappings=invalid,minimum_deformed_determinant_mm2=minimum,
            field_locations='U at every native node; SYY/SEQV/EPEL Y/X native corner-node averages, no invented midside stress',
            corner_field_columns=['SYY_MPa','SEQV_MPa','elastic_EYY','elastic_EXX'],
            corner_field_percentiles=np.percentile(stress,[0,1,50,95,99,100],axis=0).tolist(),percentile_levels=[0,1,50,95,99,100],
            absolute_elastic_components_percentiles=np.percentile(abs(stress[:,2:]),[50,95,99,100],axis=0).tolist(),
            displacement_ranges_mm=np.stack([np.min(u[:,:3],axis=0),np.max(u[:,:3],axis=0)]).tolist(),
            boundary_screen_summary={k:v for k,v in overlap.items() if k!='pore_area_records'})
        np.save(output/'corner_node_ids.npy',corners);del u,stress
        result['large_field_artifacts']={p.name:{'bytes':p.stat().st_size,'sha256':file_hash(p)} for p in output.glob('*.npy')}
        result['accepted']=not result['failures'];result['status']='MECHANICALLY_ACCEPTED_SINGLE_MESH_EXPLORATORY' if result['accepted'] else 'NATIVE_CONVERGED_BUT_UNQUALIFIED'
    except (ValueError,FileNotFoundError,KeyError,IndexError) as exc:
        result['failures'].append(str(exc));result['status']='OUTPUT_OR_IDENTITY_HOLD'
    write_json(output/'qualification.json',result)
    return result
