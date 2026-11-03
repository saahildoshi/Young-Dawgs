"""Prospective mechanical gate for the distinct central-crop demonstrator."""
import argparse
from pathlib import Path
import re
import numpy as np

from metamaterial_eval.simulation.native_qualification import stream_csv
from metamaterial_eval.simulation.microstructure_results import numeric,force_metrics,unsupported_result_queries
from metamaterial_eval.simulation.progressive_contact import validate_inventory,certify_farfield_separation
from metamaterial_eval.simulation.general_contact_results import read_table,explain_contact_pairs
from metamaterial_eval.simulation.general_contact_output import GC_COLUMNS
from metamaterial_eval.simulation.element_quality import quadratic_mapping
from metamaterial_eval.simulation.deformed_boundaries import screen
from scripts.v068_track_b import mesh_and_plan
from scripts.v068_common import BASE,RUN,read,write_json,file_hash


def qualify(source_name,selection='last'):
    mesh,plan,cfg,spec=mesh_and_plan()
    protocol=read(RUN/'protocol/TRACK_B.json')
    source=BASE/source_name;post=BASE/(source_name+'_post1_'+selection)
    sr=read(source/'execution_receipt.json');pr=read(post/'execution_receipt.json')
    sm=read(source/'simulation_manifest.json');pm=read(post/'simulation_manifest.json')
    setup=read(RUN/'track_B_contact_fixture/SETUP_QUALIFICATION.json')
    result={'schema':'young-dawgs-v068-track-b-prospective-qualification',
            'source_name':source_name,'selection':selection,'model_variant':'V068_TRACK_B_CENTRAL256_UNIFIED5',
            'source_receipt_sha256':file_hash(source/'execution_receipt.json'),
            'post_receipt_sha256':file_hash(post/'execution_receipt.json'),
            'mechanical_mesh_convergence':'UNQUALIFIED','accepted':False,'failures':[],
            'native_converged_states':sr['converged_steps']}
    try:
        if (sr['solver_version']!='2024 R1' or pr['solver_version']!='2024 R1' or
            pr['process']['returncode']!=0 or pr['status']!='PROCESS_EXITED' or
            sr['input_sha256']!=sm['input_sha256'] or file_hash(source/'input.inp')!=sm['input_sha256'] or
            pr['input_sha256']!=pm['input_sha256'] or file_hash(post/'input.inp')!=pm['input_sha256'] or
            pm['source_execution_receipt_sha256']!=result['source_receipt_sha256'] or
            pm['source_RST_sha256']!=file_hash(source/'compression.rst') or
            pm['setup_database_sha256']!=setup['native_database_sha256']):
            raise ValueError('Native source/POST1 identity or process mismatch')
        for d,r,names in [(source,sr,['compression.rst','solver.out']),
                          (post,pr,['result_sets.txt','solver.out'])]:
            for name in names:
                if file_hash(d/name)!=r['process']['artifacts'][name]['sha256']:
                    raise ValueError('Changed native evidence '+str(d/name))
        if re.search(r'^\s*(?:SOLVE|SAVE\s*,)',(post/'input.inp').read_text(encoding='utf-8'),re.M|re.I):
            raise ValueError('POST1 input is not read only')
        if unsupported_result_queries((post/'solver.out').read_text(errors='replace')):
            raise ValueError('Unsupported native POST1 field query')
        topology=read_table(BASE/'track_B_setup_001/gc_topology.csv',
                            ['element','i','j','mid','type','section']).astype(np.int64)
        if file_hash(BASE/'track_B_setup_001/gc_topology.csv')!=setup['native_topology_sha256']:
            raise ValueError('Native GC topology changed')
        eid_for_edge=np.arange(sm['model']['user_model_elements_before_GC']+1,
                               sm['model']['user_model_elements_before_GC']+len(mesh.boundary)+1)
        if not np.array_equal(topology[:,0],eid_for_edge):
            raise ValueError('Native GC element identity changed')
        # Native SET,LIST is an independent readable-set inventory.
        listing=(post/'result_sets.txt').read_text(encoding='utf-8',errors='replace')
        from metamaterial_eval.simulation.progressive_compression import result_sets
        sets={(r['load_step'],r['substep']) for r in result_sets(listing)}
        steps={(int(a),int(b)) for a,b in sr['converged_steps']}
        results=[]
        for index,state in enumerate(pm['states'],1):
            prefix=f'stage{index:03d}';key=(state['load_step'],state['substep'])
            row={'load_step':key[0],'substep':key[1],'requested_time':state['time'],'accepted':False,'failures':[]}
            if key not in steps or key not in sets:
                row['failures'].append('Missing native converged/independently readable set')
                results.append(row);continue
            names=[prefix+s for s in ['_history.csv','_gate.txt','_displacements.csv','_stress.csv',
                                      '_contact.csv','_contact_status.csv','_gc_status.csv','_gc_fields.csv']]
            for name in names:
                if file_hash(post/name)!=pr['process']['artifacts'][name]['sha256']:
                    raise ValueError('Incomplete or altered POST1 field '+name)
            h=numeric(post/(prefix+'_history.csv'),
                      ['pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'])
            if h.shape!=(1,6):raise ValueError('Incorrect history row count')
            t,ls,ss,uy,upper,lower=h[0]
            if (int(ls),int(ss))!=key or abs(t-state['time'])>1e-8 or abs(uy+2.56*t)>1e-8:
                row['failures'].append('Native checkpoint time/displacement mismatch')
            try:row['measurement']=force_metrics(t,uy,upper,lower,width=2.56,height=2.56,thickness=1)
            except ValueError as exc:row['failures'].append(str(exc))
            contact=numeric(post/(prefix+'_contact.csv'),
                            ['pair','element','status','pressure_i_MPa','pressure_j_MPa',
                             'gap_i_mm','gap_j_mm','contact_force_y_N'])
            status=numeric(post/(prefix+'_contact_status.csv'),['pair','element','status'])
            model={**sm['model'],'contact_elements':sm['model']['platen_contact_elements']}
            try:
                counts=validate_inventory(status,contact,model,len(mesh.triangles))
                pairs=[]
                for pair,group,rf in [(1,'bottom',lower),(2,'top',upper)]:
                    a=contact[contact[:,0]==pair]
                    closed=int(np.sum(a[:,2]>=2));pressure=float(a[:,3:5].max()) if len(a) else 0
                    penetration=max(0,float(a[:,5:7].max())) if len(a) else 0
                    force=float(a[:,7].sum());balance=abs(force+rf)/max(abs(rf),1e-12)
                    item={'pair':group,'native_stored_elements':counts[group],
                          'closed_elements':closed,'max_pressure_MPa':pressure,
                          'max_endpoint_penetration_mm':penetration,
                          'contact_force_y_N':force,'pilot_reaction_y_N':rf,
                          'signed_force_opposition_relative':balance}
                    pairs.append(item)
                    if not closed or pressure<=0 or penetration>5e-5 or balance>.01:
                        row['failures'].append('Platen '+group+' contact gate failed')
                row['platen_contact']=pairs
            except ValueError as exc:row['failures'].append(str(exc))
            count=len(mesh.nodes);corners=np.unique(mesh.triangles[:,:3])+1
            u=np.empty((count,2),float);offset=0
            for chunk in stream_csv(post/(prefix+'_displacements.csv'),['node','ux_mm','uy_mm']):
                n=len(chunk)
                if offset+n>count or not np.array_equal(chunk[:,0],np.arange(offset+1,offset+n+1)):
                    raise ValueError('Incomplete all-node displacement sequence')
                u[offset:offset+n]=chunk[:,1:];offset+=n
            if offset!=count:raise ValueError('Incomplete all-node displacement')
            s=np.empty((len(corners),4),float);offset=0
            for chunk in stream_csv(post/(prefix+'_stress.csv'),
                                    ['node','syy_MPa','seqv_MPa','elastic_eyy','elastic_exx']):
                n=len(chunk)
                if offset+n>len(corners) or not np.array_equal(chunk[:,0],corners[offset:offset+n]):
                    raise ValueError('Incomplete native corner-node field sequence')
                s[offset:offset+n]=chunk[:,1:];offset+=n
            if offset!=len(corners) or not np.any(s[:,:2]) or not np.any(s[:,2:]):
                raise ValueError('Absent native stress/strain fields')
            deformed=mesh.nodes+u;invalid=0;minimum=np.inf
            for offset in range(0,len(mesh.triangles),20000):
                q=quadratic_mapping(deformed[mesh.triangles[offset:offset+20000]])
                invalid+=int(np.sum(~q['positive_over_reference_triangle']))
                minimum=min(minimum,float(q['determinant_min'].min()))
            if invalid:row['failures'].append('Nonpositive deformed TRI6 mapping')
            row['fields']={'all_native_nodes':count,'corner_stress_nodes':len(corners),
                           'max_displacement_mm':float(np.linalg.norm(u,axis=1).max()),
                           'SYY_MPa_percentiles':np.percentile(s[:,0],[0,1,50,95,99,100]).tolist(),
                           'SEQV_MPa_percentiles':np.percentile(s[:,1],[0,1,50,95,99,100]).tolist(),
                           'elastic_EYY_percentiles':np.percentile(s[:,2],[0,1,50,95,99,100]).tolist(),
                           'invalid_quadratic_maps':invalid,'minimum_analytic_map_determinant':minimum,
                           'stress_location':'Native corner-node averages only'}
            try:row['platen_farfield']=certify_farfield_separation(mesh,deformed,model,status,uy)
            except ValueError as exc:row['failures'].append(str(exc))
            gc_status=read_table(post/(prefix+'_gc_status.csv'),['element','status'])
            gc_fields=read_table(post/(prefix+'_gc_fields.csv'),GC_COLUMNS)
            if len(gc_status)!=len(topology) or not np.array_equal(gc_status[:,0],topology[:,0]) or not np.isin(gc_status[:,1],[0,1,2,3]).all():
                raise ValueError('Incomplete general-contact status inventory')
            present=gc_status[gc_status[:,1]>0]
            if len(gc_fields)!=len(present) or not np.array_equal(gc_fields[:,:2],present):
                raise ValueError('Incomplete active general-contact fields')
            if len(gc_fields):
                take=np.searchsorted(topology[:,0],gc_fields[:,0])
                if not np.array_equal(gc_fields[:,10:13],topology[take,1:4]):
                    raise ValueError('General-contact native node identity mismatch')
            closed=int(np.sum(gc_status[:,1]>=2));pressure=max(0,float(gc_fields[:,2:5].max())) if len(gc_fields) else 0
            penetration=max(0,float(gc_fields[:,5:7].max())) if len(gc_fields) else 0
            telemetry=read(source/'contact_telemetry.json')['records']
            native=[r for r in telemetry if r['pair']<0 and (r['load_step'],r['substep'])==key]
            last={}
            for r in native:last[r['pair']]=r
            diagnostic_penetration=max([0]+[r['penetration_or_gap_mm'] for r in last.values()])
            row['internal_contact']={'closed_skins':closed,'stored_skins':len(gc_fields),
                                     'max_pressure_MPa':pressure,'max_endpoint_penetration_mm':penetration,
                                     'native_last_iteration_penetration_mm':diagnostic_penetration,
                                     'force_opposition':'NOT_APPLICABLE_OPEN' if not closed else 'PENDING_INDEPENDENT_STRUCTURAL_PATCH_PROOF'}
            if (closed and pressure<=0) or max(penetration,diagnostic_penetration)>5e-5:
                row['failures'].append('Internal contact pressure/penetration gate failed')
            overlap=screen(deformed,mesh.boundary,mesh.boundary_groups,
                           original=mesh.nodes,record_limit=100000)
            row['boundary_screen']={k:v for k,v in overlap.items() if k!='pore_area_records'}
            field_for_edge={int(eid-sm['model']['user_model_elements_before_GC']-1):r
                            for eid,r in zip(gc_fields[:,0].astype(int),gc_fields)}
            try:
                explanations=explain_contact_pairs(overlap,eid_for_edge,field_for_edge)
                row['native_explained_boundary_pairs']=len(explanations)
            except ValueError as exc:row['failures'].append(str(exc))
            if overlap['orientation_inverted_loops'] or overlap['edges_exceeding_requested_tolerance']:
                row['failures'].append('Boundary loop orientation or quadratic chord bound failed')
            if closed:
                row['failures'].append('Internal opposing structural patch force proof pending')
            row['raw_field_sha256']={name:file_hash(post/name) for name in names}
            row['accepted']=not row['failures'];results.append(row)
            del u,s,deformed
        result['states']=results
        result['max_native_converged_strain']=max((r['requested_time'] for r in results),default=None)
        result['max_qualified_strain']=max((r['requested_time'] for r in results if r['accepted']),default=None)
        result['accepted']=bool(results) and all(r['accepted'] for r in results)
        result['status']='PASS_TRACK_B_NATIVE_MECHANICAL' if result['accepted'] else 'HOLD_NATIVE_CONVERGED_UNQUALIFIED'
    except (ValueError,KeyError,FileNotFoundError,IndexError) as exc:
        result['failures'].append(str(exc));result['status']='HOLD_OUTPUT_OR_IDENTITY'
    output=RUN/'track_B_progressive_compression'/(source_name+'_qualification.json')
    write_json(output,result)
    print(result['status'],result.get('max_native_converged_strain'),
          result.get('max_qualified_strain'),result['failures'],flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source_name');p.add_argument('--selection',choices=['last','all'],default='last')
    a=p.parse_args();qualify(a.source_name,a.selection)
