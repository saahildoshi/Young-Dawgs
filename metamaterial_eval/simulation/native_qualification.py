"""Authenticate native exports and qualify fields without duplicate full arrays."""
import itertools
from pathlib import Path
import re
import numpy as np
import psutil
from .element_quality import quadratic_mapping
from .microstructure_results import numeric,force_metrics,contact_metrics,unsupported_result_queries
from .solver_execution import file_hash,has_negative_pivots
from .reporting import write_json,mesh_hash


def stream_csv(path,columns,chunk_size=100000):
    with Path(path).open() as stream:
        if stream.readline().strip().split(',')!=columns:raise ValueError('CSV schema mismatch: '+str(path))
        while lines:=list(itertools.islice(stream,chunk_size)):
            values=np.loadtxt(lines,delimiter=',',ndmin=2)
            if values.shape[1]!=len(columns) or not np.isfinite(values).all():raise ValueError('Partial/nonfinite field array')
            yield values


def qualify(source,export,model,mesh,output,*,load_json,identity=None):
    source,export,output=map(Path,[source,export,output]);output.mkdir(parents=True,exist_ok=False)
    receipt=load_json(source/'execution_receipt.json');post=load_json(export/'execution_receipt.json')
    manifest=load_json(source/'simulation_manifest.json');provenance=load_json(export/'provenance.json')
    result={'schema':'young-dawgs-v0.6.5-native-qualification','status':'OUTPUT_INCOMPLETE','accepted':False,
        'accepted_measurements':[],'effective_modulus_fit_MPa':None,'single_point_secant_modulus_MPa':None,
        'eligible_for_LLM_performance_ranking':False,'contact_scope':'PLATEN_CONTACT_ONLY',
        'mechanical_mesh_convergence':'UNQUALIFIED','internal_self_contact':'UNQUALIFIED_NOT_CONFIGURED',
        'source_geometry_sha256':identity.get('source_geometry_sha256') if identity else None,
        'mesh_semantic_sha256':identity.get('mesh_semantic_sha256') if identity else None,
        'native_RST_sha256':file_hash(source/'compression.rst'),
        'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
        'read_only_receipt_sha256':file_hash(export/'execution_receipt.json')}
    peak=psutil.Process().memory_info().rss
    try:
        if receipt['process']['returncode']!=0 or receipt['status']!='PROCESS_EXITED':raise ValueError('Source solver did not exit normally')
        if post['process']['returncode']!=0 or post['status']!='PROCESS_EXITED':raise ValueError('Independent native read failed')
        if receipt['input_sha256']!=manifest['input_sha256'] or receipt['input_sha256']!=file_hash(source/'input.inp'):raise ValueError('Stale/mismatched source input')
        if receipt['process']['artifacts'].get('simulation_manifest.json',{}).get('sha256')!=file_hash(source/'simulation_manifest.json'):raise ValueError('Changed source model manifest')
        if identity:
            if any(manifest.get(k)!=identity[k] for k in ['source_geometry_sha256','mesh_semantic_sha256']) or mesh_hash(mesh)!=identity['mesh_semantic_sha256']:raise ValueError('Mismatched source geometry/mesh identity')
        for filename in ['compression.rst','checkpoint.db']:
            if file_hash(source/filename)!=receipt['process']['artifacts'].get(filename,{}).get('sha256'):raise ValueError('Truncated/changed native '+filename)
        expected={'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
            'source_RST_sha256':result['native_RST_sha256'],'source_checkpoint_database_sha256':file_hash(source/'checkpoint.db'),
            'source_manifest_sha256':file_hash(source/'simulation_manifest.json'),'source_protocol_sha256':manifest['protocol_sha256'],
            'input_sha256':file_hash(export/'input.inp')}
        if any(provenance.get(k)!=v for k,v in expected.items()):raise ValueError('Independent export provenance mismatch')
        if post['input_sha256']!=expected['input_sha256'] or re.search(r'^\s*(?:SOLVE|SAVE\s*,)',(export/'input.inp').read_text(),re.M|re.I):raise ValueError('Unverified read-only input')
        source_log=(source/'solver.out').read_text(errors='replace');post_log=(export/'solver.out').read_text(errors='replace')
        for directory,r in [(source,receipt),(export,post)]:
            if file_hash(directory/'solver.out')!=r['process']['artifacts'].get('solver.out',{}).get('sha256'):raise ValueError('Changed native solver evidence')
        if unsupported_result_queries(post_log):raise ValueError('Missing native result records; ignored/default/sentinel fields quarantined')
        if re.search(r'\*\*\*\s*(?:ERROR|FATAL)\s*\*\*\*|highly distorted',source_log+'\n'+post_log,re.I) or has_negative_pivots(source_log):raise ValueError('Invalidating native solver diagnostic')
        if (1,1) not in set(map(tuple,receipt['converged_steps'])):raise ValueError('Unconverged native set')
        fields=['stage001_history.csv','stage001_gate.txt','stage001_displacements.csv','stage001_stress.csv','stage001_contact.csv','result_sets.txt']
        for name in fields:
            if file_hash(export/name)!=post['process']['artifacts'].get(name,{}).get('sha256'):raise ValueError('Incomplete/stale export '+name)
        sets=re.findall(r'^\s*(\d+)\s+([\d.Ee+\-]+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$',(export/'result_sets.txt').read_text(),re.M)
        target=manifest['target_strain']
        if len(sets)!=1 or [int(sets[0][i]) for i in [0,2,3]]!=[1,1,1] or not np.isclose(float(sets[0][1]),target,rtol=0,atol=1e-12):raise ValueError('Unexpected native result-set inventory/time')
        history=numeric(export/'stage001_history.csv',['pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'])
        if history.shape!=(1,6):raise ValueError('Duplicate or missing native history')
        time,ls,ss,uy,upper,lower=history[0]
        if ls!=1 or ss!=1 or not np.isclose(time,target,rtol=0,atol=1e-12) or not np.isclose(uy,-model['config']['height']*target,rtol=0,atol=1e-8):raise ValueError('Incorrect achieved state')
        gate=(export/'stage001_gate.txt').read_text().split(',')
        if float(gate[0])!=0:raise ValueError('Native mechanical gate failed')
        measurement=force_metrics(time,uy,upper,lower,**{k:model['config'][k] for k in ['width','height','thickness']})
        contacts=contact_metrics(numeric(export/'stage001_contact.csv',['pair','element','status','pressure_i_MPa','pressure_j_MPa','gap_i_mm','gap_j_mm','contact_force_y_N']),model['contact_elements'],upper,lower)
        count=len(mesh.nodes);corners=np.unique(mesh.triangles[:,:3])+1
        if count!=model['specimen_nodes'] or len(mesh.triangles)!=model['specimen_TRI6']:raise ValueError('Mesh/model inventory mismatch')
        u=np.lib.format.open_memmap(output/'native_displacement.npy',mode='w+',dtype=np.float64,shape=(count,5))
        offset=0;ranges=np.array([[np.inf,-np.inf]]*3)
        for values in stream_csv(export/'stage001_displacements.csv',['node','ux_mm','uy_mm']):
            n=len(values)
            if offset+n>count or not np.array_equal(values[:,0],np.arange(offset+1,offset+n+1)):raise ValueError('Partial/duplicate displacement node inventory')
            data=values[:,1:3];mag=np.linalg.norm(data,axis=1)
            u[offset:offset+n,:2]=data;u[offset:offset+n,2]=mag
            u[offset:offset+n,3:]=mesh.nodes[offset:offset+n]+data
            chunk=np.column_stack([data,mag]);ranges[:,0]=np.minimum(ranges[:,0],chunk.min(axis=0));ranges[:,1]=np.maximum(ranges[:,1],chunk.max(axis=0))
            offset+=n;peak=max(peak,psutil.Process().memory_info().rss)
        if offset!=count:raise ValueError('Missing nodal displacement rows')
        u.flush()
        stress=np.lib.format.open_memmap(output/'native_corner_stress_strain.npy',mode='w+',dtype=np.float64,shape=(len(corners),4))
        offset=0;sranges=np.array([[np.inf,-np.inf]]*4)
        for values in stream_csv(export/'stage001_stress.csv',['node','syy_MPa','seqv_MPa','elastic_eyy','elastic_exx']):
            n=len(values)
            if offset+n>len(corners) or not np.array_equal(values[:,0],corners[offset:offset+n]):raise ValueError('Partial/duplicate corner field inventory')
            stress[offset:offset+n]=values[:,1:];sranges[:,0]=np.minimum(sranges[:,0],values[:,1:].min(axis=0));sranges[:,1]=np.maximum(sranges[:,1],values[:,1:].max(axis=0))
            offset+=n;peak=max(peak,psutil.Process().memory_info().rss)
        if offset!=len(corners) or not np.any(sranges[:2]) or not np.any(sranges[2:]):raise ValueError('Missing continuum stress/strain')
        stress.flush();np.save(output/'corner_node_ids.npy',corners)
        minimum=np.inf
        for i in range(0,len(mesh.triangles),20000):
            triangles=mesh.triangles[i:i+20000]
            mapping=quadratic_mapping(mesh.nodes[triangles]+u[triangles,:2])
            if not np.all(mapping['positive_over_reference_triangle']):raise ValueError('Invalid deformed TRI6 mapping')
            minimum=min(minimum,float(mapping['determinant_min'].min()));peak=max(peak,psutil.Process().memory_info().rss)
        del u,stress
        result.update(status='FIRST_ACCEPTED_NATIVE_CHECKPOINT__PRELIMINARY_SINGLE_MESH_RESEARCH_HOLD',accepted=True,
            accepted_measurements=[measurement],contacts=contacts,readable_sets=sets,
            actual_nodes=count,actual_TRI6=len(mesh.triangles),actual_corner_field_nodes=len(corners),
            displacement_ranges_mm=ranges.tolist(),corner_stress_strain_ranges=sranges.tolist(),
            all_deformed_mappings_positive=True,minimum_deformed_determinant_mm2=minimum,
            field_locations='Displacement at all nodes; SYY/SEQV/EPEL Y/X are supported corner-node averages. No midside stress invented.',
            derived_displacement_columns=['native_UX_mm','native_UY_mm','derived_magnitude_mm','derived_deformed_X_mm','derived_deformed_Y_mm'],
            single_point_secant_modulus_MPa=measurement['nominal_compression_stress_MPa']/measurement['engineering_compression_strain'],
            raw_native_field_hashes={name:file_hash(export/name) for name in fields},
            large_field_artifacts={p.name:{'bytes':p.stat().st_size,'sha256':file_hash(p)} for p in output.glob('*.npy')})
    except (ValueError,FileNotFoundError) as exc:
        result.update(status='OUTPUT_INCOMPLETE__MECHANICAL_HOLD',failure=str(exc))
    result['sampled_python_peak_RSS_bytes']=peak
    write_json(output/'qualification.json',result)
    return result
