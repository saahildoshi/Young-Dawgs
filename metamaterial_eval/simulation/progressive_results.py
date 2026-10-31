"""Qualify an explicitly identified converged native set, including partial jobs."""
from pathlib import Path
import re
import numpy as np
from .native_qualification import stream_csv
from .microstructure_results import numeric,force_metrics,contact_metrics,unsupported_result_queries
from .progressive_compression import load,result_sets
from .element_quality import quadratic_mapping,corner_metrics
from .deformed_boundaries import screen
from .progressive_contact import validate_inventory,certify_farfield_separation
from .general_contact_results import qualify_general_contact
from .reporting import write_json,mesh_hash
from .solver_execution import file_hash,has_negative_pivots


def matches_printed_time(actual,printed):
    """Honor the last displayed digit; full native history remains authoritative."""
    fields=printed.upper().replace('D','E').split('E');mantissa=fields[0];exponent=int(fields[1]) if len(fields)>1 else 0
    decimals=len(mantissa.split('.')[1]) if '.' in mantissa else 0
    bound=.5*10.**(exponent-decimals)
    return bool(np.isfinite(actual) and abs(actual-float(printed))<=bound+1e-14*max(1,abs(actual)))


def selected_state_log(text,key):
    headers=list(re.finditer(r'USE LOAD STEP\s+(\d+)\s+SUBSTEP\s+(\d+)\s+FOR LOAD CASE',text))
    found=[i for i,m in enumerate(headers) if tuple(map(int,m.groups()))==key]
    if len(found)!=1:raise ValueError('Missing/duplicate native selected-set readback marker')
    i=found[0];return text[headers[i].start():headers[i+1].start() if i+1<len(headers) else len(text)]


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
    if re.search(r'\*\*\*\s*(?:ERROR|FATAL)\s*\*\*',text,re.I):raise ValueError('Invalid native readback process')
    return manifest,receipt,post,provenance,result_sets((export/'result_sets.txt').read_text())


def qualify_state(source,export,mesh,index,state,output,*,general_contact_setup=None):
    source,export,output=map(Path,[source,export,output]);output.mkdir(parents=True,exist_ok=False)
    result={'schema':'young-dawgs-v0.6.6-actual-native-state','state':state,'accepted':False,'failures':[],
        'contact_scope':'PLATEN_ONLY_EXPLORATORY','mechanical_mesh_convergence':'UNQUALIFIED',
        'internal_self_contact':'UNQUALIFIED_NOT_CONFIGURED','eligible_for_LLM_performance_ranking':False,
        'source':str(source),'export':str(export),'field_artifact_directory':str(output)}
    try:
        manifest,receipt,post,provenance,sets=authenticate(source,export,mesh);model=manifest['model']
        if model.get('general_contact_elements'):
            result.update(contact_scope=model['contact_scope'],internal_self_contact='CONFIGURED_NATIVE_GENERAL_CONTACT',model_variant=model['model_variant'])
            if general_contact_setup is None:raise ValueError('General-contact state requires authenticated native GC qualification')
            if model.get('general_contact_detection_keyopt4')==2:
                inventory=export/'native_contact_type.txt'
                if file_hash(inventory)!=post['process']['artifacts'].get(inventory.name,{}).get('sha256') or not re.search(r'KEYOPT\( 1- 6\)=\s+0\s+1\s+0\s+2',inventory.read_text()):raise ValueError('Actual post-solution nodal contact detection was not verified')
                result['actual_postsolution_general_contact_detection_keyopt4']=2
        key=(state['load_step'],state['substep']);converged=load(source/'nonlinear_telemetry.json')['converged_substeps']
        matching=[r for r in converged if (r['load_step'],r['substep'])==key]
        if len(matching)!=1 or not any((s['load_step'],s['substep'])==key for s in sets):raise ValueError('Set not independently corroborated as converged')
        if index<1 or provenance['states'][index-1]!=state:raise ValueError('Selected export identity mismatch')
        if unsupported_result_queries(selected_state_log((export/'solver.out').read_text(errors='replace'),key)):raise ValueError('Unsupported native records in selected state')
        source_before='\n'.join((source/'solver.out').read_text(errors='replace').splitlines()[:matching[0]['source_line']])
        if has_negative_pivots(source_before) or re.search(r'\*\*\*\s*FATAL\s*\*\*',source_before,re.I):raise ValueError('Invalidating solver diagnostic before state')
        prefix=f'stage{index:03d}'
        names=[prefix+s for s in ['_history.csv','_gate.txt','_displacements.csv','_stress.csv','_contact.csv']]
        if provenance.get('native_farfield_status_inventory'):names.append(prefix+'_contact_status.csv')
        if model.get('general_contact_elements'):names.extend([prefix+'_gc_status.csv',prefix+'_gc_fields.csv'])
        if model.get('general_contact_elements') and (export/(prefix+'_gc_balance.csv')).exists():names.append(prefix+'_gc_balance.csv')
        hashes={}
        for name in names:
            hashes[name]=file_hash(export/name)
            if hashes[name]!=post['process']['artifacts'].get(name,{}).get('sha256'):raise ValueError('Changed/incomplete exported field '+name)
        history=numeric(export/(prefix+'_history.csv'),['pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'])
        if history.shape!=(1,6):raise ValueError('Missing/duplicate native history')
        time,ls,ss,uy,upper,lower=history[0]
        source_lines=(source/'solver.out').read_text(errors='replace').splitlines()
        printed=re.search(r'\*+\s*TIME\s*=\s*([\d.+\-Ee]+)\s+TIME INC','\n'.join(source_lines[matching[0]['source_line']:matching[0]['source_line']+3]))
        source_time_ok=matches_printed_time(time,printed[1]) if printed else abs(time-matching[0]['pseudo_time'])<=1e-12
        requested_time_ok=abs(state['time']-matching[0]['pseudo_time'])<=1e-12 or abs(state['time']-time)<=1e-12
        inventory=[t for t,l,s in re.findall(r'^\s*\d+\s+([\d.Ee+\-]+)\s+(\d+)\s+(\d+)\s+\d+\s*$',(export/'result_sets.txt').read_text(),re.M) if (int(l),int(s))==key]
        inventory_time_ok=len(inventory)==1 and matches_printed_time(time,inventory[0])
        if (ls,ss)!=key or not source_time_ok or not requested_time_ok or not inventory_time_ok or abs(uy+model['config']['height']*time)>1e-8:raise ValueError('Incorrect cumulative displacement/state')
        result['requested_state']=state;result['state']={'load_step':int(ls),'substep':int(ss),'time':float(time)}
        result.update(actual_history=history[0].tolist(),source_process_status=receipt['status'],native_RST_sha256=provenance['source_RST_sha256'],
            source_receipt_sha256=file_hash(source/'execution_receipt.json'),read_only_receipt_sha256=file_hash(export/'execution_receipt.json'),raw_native_field_hashes=hashes)
        try:
            result['measurement']=force_metrics(time,uy,upper,lower,**{k:model['config'][k] for k in ['width','height','thickness']})
        except ValueError as exc:result['failures'].append(str(exc))
        status=None
        try:
            contact_values=numeric(export/(prefix+'_contact.csv'),['pair','element','status','pressure_i_MPa','pressure_j_MPa','gap_i_mm','gap_j_mm','contact_force_y_N'])
            status=numeric(export/(prefix+'_contact_status.csv'),['pair','element','status']) if provenance.get('native_farfield_status_inventory') else None
            counts=validate_inventory(status,contact_values,model,len(mesh.triangles)) if status is not None else model['contact_elements']
            result['contacts']=contact_metrics(contact_values,counts,upper,lower)
            for c in result['contacts']:
                c['stored_record_elements']=c['total_elements'];c['total_elements']=model['contact_elements'][c['pair']]
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
        u.flush()
        if status is not None and 'contacts' in result:
            try:result['native_farfield_separation']=certify_farfield_separation(mesh,u[:,3:5],model,status,uy)
            except ValueError as exc:result['failures'].append(str(exc))
        stress=np.lib.format.open_memmap(output/'native_corner_stress_strain.npy',mode='w+',dtype=np.float64,shape=(len(corners),4));offset=0
        for v in stream_csv(export/(prefix+'_stress.csv'),['node','syy_MPa','seqv_MPa','elastic_eyy','elastic_exx']):
            n=len(v)
            if offset+n>len(corners) or not np.array_equal(v[:,0],corners[offset:offset+n]):raise ValueError('Missing/duplicate native corner field inventory')
            stress[offset:offset+n]=v[:,1:];offset+=n
        if offset!=len(corners):raise ValueError('Incomplete native continuum fields')
        if not np.any(stress[:,:2]) or not np.any(stress[:,2:]):raise ValueError('Absent continuum stress/strain under nonzero load')
        stress.flush();minimum=np.inf;invalid=0
        angle_values=np.empty(len(mesh.triangles));aspect_values=np.empty(len(mesh.triangles));nonpositive_corners=0
        for i in range(0,len(mesh.triangles),20000):
            tri=mesh.triangles[i:i+20000];points=mesh.nodes[tri]+u[tri,:2];q=quadratic_mapping(points);invalid+=int(np.sum(~q['positive_over_reference_triangle']));minimum=min(minimum,float(q['determinant_min'].min()))
            corners_shape=corner_metrics(points[:,:3]);angle_values[i:i+len(tri)]=corners_shape['minimum_angle_deg'];aspect_values[i:i+len(tri)]=corners_shape['aspect_ratio'];nonpositive_corners+=int(np.sum(~corners_shape['positive_orientation']))
        if invalid:result['failures'].append('Invalid deformed quadratic mappings')
        overlap=screen(u[:,3:5],mesh.boundary,mesh.boundary_groups,original=mesh.nodes,record_limit=100000 if model.get('general_contact_elements') else 32);write_json(output/'boundary_screen.json',overlap)
        if model.get('general_contact_elements'):
            try:result['general_contact']=qualify_general_contact(source,export,prefix,manifest,mesh,overlap,result['state'],general_contact_setup)
            except ValueError as exc:result['failures'].append(str(exc))
        elif not overlap['passed']:result['failures'].append('Unmodeled overlap/near contact uncertainty')
        result.update(actual_nodes=count,actual_TRI6=len(mesh.triangles),actual_native_corner_nodes=len(corners),
            invalid_deformed_mappings=invalid,minimum_deformed_determinant_mm2=minimum,
            deformed_corner_shape_diagnostics={'minimum_angle_deg':float(angle_values.min()),'angle_percentiles_deg':np.percentile(angle_values,[0,1,50,95,99,100]).tolist(),
                'finite_aspect_percentiles':np.percentile(aspect_values[np.isfinite(aspect_values)],[0,1,50,95,99,100]).tolist() if np.isfinite(aspect_values).any() else [],
                'nonfinite_aspect_count':int(np.sum(~np.isfinite(aspect_values))),'nonpositive_corner_triangle_count':nonpositive_corners,
                'scope':'Corner-based shape diagnostics, not a replacement for the whole-domain quadratic Jacobian check or mechanical mesh convergence. Frozen10deg gate applies to the original selected mesh.'},
            field_locations='U at every native node; SYY/SEQV/EPEL Y/X native corner-node averages, no invented midside stress',
            corner_field_columns=['SYY_MPa','SEQV_MPa','elastic_EYY','elastic_EXX'],
            corner_field_percentiles=np.percentile(stress,[0,1,50,95,99,100],axis=0).tolist(),percentile_levels=[0,1,50,95,99,100],
            absolute_elastic_components_percentiles=np.percentile(abs(stress[:,2:]),[50,95,99,100],axis=0).tolist(),
            displacement_ranges_mm=np.stack([np.min(u[:,:3],axis=0),np.max(u[:,:3],axis=0)]).tolist(),
            boundary_screen_summary={k:(v[:32] if k=='examples' else v) for k,v in overlap.items() if k!='pore_area_records'})
        np.save(output/'corner_node_ids.npy',corners);del u,stress
        if model.get('general_contact_elements') and abs(result['state']['time']-.001)<1e-12 and 'measurement' in result:
            reference=1.199313799677024;actual=float(-result['measurement']['upper_rf_y_N']);relative=float(abs(actual-reference)/reference)
            result['initial_response_comparison']={'platen_only_reference_force_N':reference,'general_contact_force_N':actual,'relative_difference':relative,'prospective_tolerance':.005,'passed':bool(relative<=.005)}
            if relative>.005:result['failures'].append('Full general-contact initial response differs from qualified reference by more than0.5%')
        result['large_field_artifacts']={p.name:{'bytes':p.stat().st_size,'sha256':file_hash(p)} for p in output.glob('*.npy')}
        result['accepted']=not result['failures'];result['status']='MECHANICALLY_ACCEPTED_SINGLE_MESH_EXPLORATORY' if result['accepted'] else 'NATIVE_CONVERGED_BUT_UNQUALIFIED'
    except (ValueError,FileNotFoundError,KeyError,IndexError) as exc:
        result['failures'].append(str(exc));result['status']='OUTPUT_OR_IDENTITY_HOLD'
    write_json(output/'qualification.json',result)
    return result
