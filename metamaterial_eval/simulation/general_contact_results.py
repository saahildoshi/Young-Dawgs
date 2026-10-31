"""Authenticate full native GC records and explain only demonstrated contact."""
from pathlib import Path
import numpy as np
from .native_qualification import stream_csv
from .general_contact_output import GC_COLUMNS
from .progressive_compression import load
from .solver_execution import file_hash


def read_table(path,columns):
    chunks=list(stream_csv(path,columns))
    return np.concatenate(chunks) if chunks else np.empty((0,len(columns)))


def explain_contact_pairs(overlap,eid_for_edge,field_for_edge):
    if overlap['suspicious_pair_count']!=len(overlap['examples']):raise ValueError('Boundary contact explanations truncated; state unqualified')
    explained=[];unexplained=[]
    for pair in overlap['examples']:
        a,b=pair['edge_a'],pair['edge_b'];fa,fb=field_for_edge.get(a),field_for_edge.get(b)
        linked_a=fa is not None and fa[1]>=2 and eid_for_edge[b] in fa[8:10] and max(fa[2:5])>0
        linked_b=fb is not None and fb[1]>=2 and eid_for_edge[a] in fb[8:10] and max(fb[2:5])>0
        result={**pair,'native_element_a':int(eid_for_edge[a]),'native_element_b':int(eid_for_edge[b]),'native_target_link_a_to_b':bool(linked_a),'native_target_link_b_to_a':bool(linked_b)}
        (explained if linked_a or linked_b else unexplained).append(result)
    if unexplained:raise ValueError('Boundary crossing/near-touch lacks native engaged target-segment linkage: '+str(unexplained[:2]))
    return explained


def qualify_general_contact(source,export,prefix,manifest,mesh,overlap,state,setup,*,deformed_coordinates=None):
    source,export,setup=map(Path,[source,export,setup]);model=manifest['model'];receipt=load(setup/'execution_receipt.json')
    if manifest['source_setup_receipt_sha256']!=file_hash(setup/'execution_receipt.json'):raise ValueError('General-contact setup receipt mismatch')
    topology_path=setup/'gc_topology.csv'
    if file_hash(topology_path)!=receipt['process']['artifacts']['gc_topology.csv']['sha256'] or manifest['source_general_contact_database_sha256']!=receipt['process']['artifacts']['contact_model_gc.db']['sha256']:raise ValueError('Changed native general-contact topology/database')
    topology=read_table(topology_path,['element','i_node','j_node','midside_node']).astype(np.int64)
    if len(topology)!=model['general_contact_elements']:raise ValueError('General-contact topology count mismatch')
    by_nodes={tuple(e+1):i for i,e in enumerate(mesh.boundary)}
    indices=np.array([by_nodes.get(tuple(e),-1) for e in topology[:,1:]])
    if len(np.unique(indices))!=len(mesh.boundary) or np.any(indices<0):raise ValueError('Native general-contact skins do not cover every original oriented boundary')
    status=read_table(export/(prefix+'_gc_status.csv'),['element','status'])
    if len(status)!=len(topology) or not np.array_equal(status[:,0],topology[:,0]) or not np.isin(status[:,1],[0,1,2,3]).all():raise ValueError('Incomplete/invalid native general-contact status inventory')
    path=export/(prefix+'_gc_fields.csv');columns=path.read_text().splitlines()[0].strip().split(',')
    if columns not in [GC_COLUMNS,GC_COLUMNS[:-1]]:raise ValueError('Unknown general-contact field schema')
    fields=read_table(path,columns);present=status[status[:,1]>0]
    if fields.shape[0]!=len(present) or not np.array_equal(fields[:,:2],present):raise ValueError('Missing/stale active general-contact records')
    take=np.searchsorted(topology[:,0],fields[:,0])
    if not np.array_equal(fields[:,10:13],topology[take,1:4]):raise ValueError('General-contact native node identity mismatch')
    closed=int(np.sum(status[:,1]>=2));pressure=float(fields[:,2:5].max()) if len(fields) else 0
    penetration=max(0,float(fields[:,5:7].max())) if len(fields) else 0
    if penetration>1e-5 or (closed and pressure<=0):raise ValueError('General-contact pressure/penetration gate failed')
    if closed and columns!=GC_COLUMNS:raise ValueError('Engaged general contact lacks native horizontal force records')
    fy=float(fields[:,7].sum()) if len(fields) else 0;fy_norm=float(abs(fields[:,7]).sum()) if len(fields) else 0
    fx=float(fields[:,13].sum()) if len(fields) and columns==GC_COLUMNS else None
    fx_norm=float(abs(fields[:,13]).sum()) if len(fields) and columns==GC_COLUMNS else None
    ybalance=abs(fy)/max(fy_norm,1e-12);xbalance=abs(fx)/max(fx_norm,1e-12) if fx is not None else None
    balance_path=export/(prefix+'_gc_balance.csv');assembled=None;assembled_residual=None
    if balance_path.exists():
        table=read_table(balance_path,['assembled_contact_fx_N','assembled_contact_fy_N'])
        if table.shape not in [(0,2),(1,2)]:raise ValueError('Invalid native general-contact assembled force inventory')
        if len(table):
            assembled=table[0].tolist();norm=float(np.linalg.norm(fields[:,[13,7]],axis=1).sum()) if columns==GC_COLUMNS else fy_norm
            assembled_residual=float(np.linalg.norm(table[0])/max(norm,1e-12))
            if assembled_residual>.01:raise ValueError('Native assembled general-contact force imbalance exceeds1%')
    if closed and assembled is None:raise ValueError('Engaged general contact lacks independently assembled native force balance')
    field_for_edge={int(indices[i]):fields[j] for j,i in enumerate(take)}
    eid_for_edge=np.zeros(len(mesh.boundary),dtype=np.int64);eid_for_edge[indices]=topology[:,0]
    if model.get('general_contact_detection_keyopt4')==2:
        from .nodal_contact_geometry import explain_nodal_pairs
        if deformed_coordinates is None:raise ValueError('Nodal geometry requires actual deformed native coordinates')
        explained=explain_nodal_pairs(overlap,eid_for_edge,field_for_edge,mesh,deformed_coordinates)
    else:explained=explain_contact_pairs(overlap,eid_for_edge,field_for_edge)
    if overlap['orientation_inverted_loops'] or overlap['edges_exceeding_requested_tolerance']:raise ValueError('Unqualified general-contact contour orientation/approximation')
    # The CND record is corroborated by the explicitly converged/readable LS/SS.
    telemetry=load(source/'contact_telemetry.json')['records']
    native=[r for r in telemetry if r['pair']<0 and (r['load_step'],r['substep'])==(state['load_step'],state['substep'])]
    last={}
    for record in native:last[record['pair']]=record
    cnd_pen=max([0]+[r['penetration_or_gap_mm'] for r in last.values()])
    if cnd_pen>1e-5:raise ValueError('Converged-step native general-contact diagnostic penetration exceeds1e-5mm')
    return {'status':'PASS_FULL_NATIVE_GENERAL_CONTACT_CHECKS','general_contact_skin_count':len(status),'farfield_skins':int(np.sum(status[:,1]==0)),
        'stored_record_skins':len(fields),'closed_skins':closed,
        'closed_original_surface_groups':{str(g):int(np.sum(mesh.boundary_groups[indices[status[:,1]>=2]]==g)) for g in np.unique(mesh.boundary_groups[indices[status[:,1]>=2]])},
        'max_stored_pressure_MPa':pressure,'max_stored_endpoint_penetration_mm':penetration,
        'native_last_iteration_diagnostic_penetration_mm':cnd_pen,'native_pair_count_field_limitation':'General-contact CND active_elements may be -1; whole-element status inventory is authoritative',
        'native_skin_normal_FY_sum_N':fy,'native_skin_normal_FX_sum_N':fx,'native_skin_FY_balance_relative':ybalance,'native_skin_FX_balance_relative':xbalance,
        'native_assembled_contact_force_XY_N':assembled,'native_assembled_contact_force_balance_relative':assembled_residual,
        'explained_boundary_pair_count':len(explained),'explained_pair_examples':explained[:32],
        'boundary_interpretation':'Original direct native facet links retained; nodal shared-endpoint propagation additionally requires actual positive endpoint pressure/target identity and guarded contact localization inside5e-6mm-radius native-node balls. Strictly separated near pairs infer no contact. Native penetration remains<=1e-5mm.' if model.get('general_contact_detection_keyopt4')==2 else 'Only actual closed native target-segment links explain bounded-screen contact intersections; native penetration remains within1e-5mm. No unmodeled pair accepted.',
        'force_scope':'Symmetric native contact-skin normal forces; target-role force projection is also part of native assembly. Platen signed equilibrium independently required.',
        'columns':columns,'topology_sha256':file_hash(topology_path),'gc_status_sha256':file_hash(export/(prefix+'_gc_status.csv')),'gc_fields_sha256':file_hash(path)}
