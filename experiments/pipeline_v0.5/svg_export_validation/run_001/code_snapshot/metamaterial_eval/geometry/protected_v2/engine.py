"""Constrained DP proposals with recorded, bounded local rollback."""
import math
import time
import numpy as np
import shapely
from shapely import LineString, MultiPoint, Point, STRtree
from ..manifold.contacts import inspect_boundary
from ..protected.settings import tolerance
from ..protected.model import signed_area
from ..protected.engine import chord_constraints as original_chord_constraints
from .width import chord_width_gate


def vertex_distances(xy):
    a,b = xy[0],xy[-1]; delta = b-a; denominator = float(delta[0]*delta[0]+delta[1]*delta[1])
    if denominator == 0:
        return np.linalg.norm(xy-a,axis=1)
    v=xy-a
    t = np.clip((v[:,0]*delta[0]+v[:,1]*delta[1])/denominator,0,1)
    return np.linalg.norm(xy-(a+t[:,None]*delta),axis=1)


def fan_bounds(xy, solid_orientation):
    delta = xy-xy[0]
    cross = delta[:-1,0]*delta[1:,1]-delta[:-1,1]*delta[1:,0]
    signed = cross*solid_orientation/2
    return float(np.maximum(-signed,0).sum()),float(np.maximum(signed,0).sum())


def fan_contains_cell_center(xy, maximum=4096):
    """Signed fan-change support via closed-chain parity, bounded local points.

    Internal fan diagonals can cancel and are not a changed boundary. Reject
    centers in a nonzero-winding lobe or on an actual replacement chord.
    """
    lo = np.ceil(xy.min(axis=0)-.5).astype(int); hi = np.floor(xy.max(axis=0)-.5).astype(int)
    size = int(np.prod(np.maximum(0,hi-lo+1)))
    if size > maximum:
        return True, 'local_raster_work_limit'
    if size == 0:
        return False, None
    xx,yy = np.meshgrid(np.arange(lo[0],hi[0]+1)+.5,np.arange(lo[1],hi[1]+1)+.5)
    points = np.column_stack((xx.ravel(),yy.ravel())); inside = np.zeros(len(points),dtype=bool)
    for a,b in zip(xy,np.roll(xy,-1,axis=0)):
        if a[1] != b[1]:
            crossing = ((a[1]>points[:,1]) != (b[1]>points[:,1]))
            x = a[0]+(points[:,1]-a[1])*(b[0]-a[0])/(b[1]-a[1])
            inside ^= crossing & (points[:,0]<x)
    if inside.any():
        return True, 'cell_center_in_fan_change_support'
    a,b = xy[0],xy[-1];delta=b-a;denominator=float(delta[0]*delta[0]+delta[1]*delta[1])
    if denominator:
        v=points-a
        t = np.clip((v[:,0]*delta[0]+v[:,1]*delta[1])/denominator,0,1)
        if np.any(np.linalg.norm(points-(a+t[:,None]*delta),axis=1)<=1e-12):
            return True, 'cell_center_on_replacement_boundary'
    return False, None


def chord_constraints(model,guards,ri,vertex_ids,xy,config):
    result=original_chord_constraints(model,guards,ri,vertex_ids,xy,config)
    if not result['failed_constraints']:
        width=chord_width_gate(model,ri,vertex_ids,xy,config['width_settings'])
        result['width_gate']=width
        result['failed_constraints'].extend(width['failed_constraints'])
    return result


def simplify_protected(geometry, epsilon, risks, guards, config):
    epsilon = tolerance(epsilon); start = time.perf_counter()
    if geometry.is_empty or geometry.geom_type not in ('Polygon','MultiPolygon') or not geometry.is_valid:
        return {'disposition':'UNSUPPORTED_INPUT','geometry':None,'reason':'Require nonempty valid polygonal input.'}
    if not inspect_boundary(geometry)['manifold']:
        return {'disposition':'UNSUPPORTED_INPUT','geometry':None,'reason':'Require an independently manifold input.'}
    model = risks['model']
    if shapely.to_wkb(geometry,byte_order=1) != shapely.to_wkb(model.geometry,byte_order=1):
        return {'disposition':'UNSUPPORTED_INPUT','geometry':None,'reason':'Risk registry does not belong to this exact source geometry.'}
    keeps = [np.ones(len(x),dtype=bool) for x in model.xy]
    t = time.perf_counter(); chains = model.chains(guards['protected']); partition_seconds = time.perf_counter()-t
    proposals = []; chain_records = []; spent = np.zeros(2); max_budget = geometry.area*np.array([config['limits']['max_added_fraction'], config['limits']['max_removed_fraction']])
    checking_seconds = 0.; traversal_seconds = 0.; pore_spent = {}
    for chain in chains:
        ri = chain['ring']; ids = chain['vertices']; xy = model.xy[ri][ids]; n = len(ids)
        accepted = []; rejected = []; keep = set([0,n-1]); stack = [(0,n-1)]
        ring_budget = math.inf if model.rings[ri]['role']=='shell' else abs(signed_area(model.xy[ri]))*config['limits']['max_pore_area_fraction']
        # All chains of one pore share a ledger; do not reset a per-pore budget.
        pore_spent.setdefault(ri,0.)
        orientation = np.sign(signed_area(model.xy[ri]))*(1 if model.rings[ri]['role']=='shell' else -1)
        while stack:
            first,last = stack.pop()
            if last-first < 2 or epsilon == 0:
                keep.update(range(first,last+1)); continue
            began = time.perf_counter(); local = xy[first:last+1]; distances = vertex_distances(local)
            split = first+int(np.argmax(distances)); maximum = float(distances.max())
            traversal_seconds += time.perf_counter()-began
            if maximum > epsilon:
                keep.add(split); stack.extend([(split,last),(first,split)]); continue
            began = time.perf_counter()
            result = chord_constraints(model,guards,ri,ids[first:last+1],local,config)
            added,removed = fan_bounds(local,orientation)
            if np.any(spent+[added,removed] > max_budget+config['limits']['area_allowance']):
                result['failed_constraints'].append('global_fan_material_budget')
            if pore_spent[ri]+added+removed > ring_budget+config['limits']['area_allowance']:
                result['failed_constraints'].append('pore_fan_area_budget')
            checking_seconds += time.perf_counter()-began
            index = len(proposals)
            record = {'proposal_id':f'p{index:07d}', 'chain_id':chain['chain_id'], 'ring':ri,
                      'original_vertex_indices':ids[first:last+1].tolist(), 'original_chain':local.tolist(),
                      'proposed_replacement':[local[0].tolist(),local[-1].tolist()],
                      'failed_constraints':sorted(set(result['failed_constraints'])), 'entered_guards':result['guard_ids'],
                      'certified_displacement_upper':maximum, 'fan_added_upper':added,'fan_removed_upper':removed,
                      'further_tolerance_retry':False, 'applied':not result['failed_constraints'],
                      'width_qualification':result.get('width_gate')}
            if result['failed_constraints']:
                keep.update(range(first,last+1)); rejected.append(index)
                record.update(disposition='REJECTED_CHORD_RESTORED', restored_geometry=local.tolist())
            else:
                keep.update([first,last]); accepted.append(index); spent += [added,removed]; pore_spent[ri] += added+removed
                record['disposition']='ACCEPTED_LOCAL_PROPOSAL'
            proposals.append(record)
        final = sorted(keep); keeps[ri][ids[1:-1]] = False; keeps[ri][ids[final]] = True
        chain_records.append({'chain_id':chain['chain_id'],'ring':ri,'original_vertex_indices':ids.tolist(),
                              'kept_vertex_indices':ids[final].tolist(),'accepted_proposals':accepted,'rejected_proposals':rejected,
                              'no_op':len(final)==n})
    assembly_start = time.perf_counter(); assembly_rollbacks = []
    active = [p for p in proposals if p['applied']]
    if active:
        lines = shapely.linestrings(np.asarray([p['proposed_replacement'] for p in active])); pairs = STRtree(lines).query(lines,predicate='intersects')
        conflicts = set()
        for i,j in zip(*pairs):
            if i >= j: continue
            intersection = lines[i].intersection(lines[j])
            common = set(map(tuple,active[i]['proposed_replacement'])) & set(map(tuple,active[j]['proposed_replacement']))
            if intersection.geom_type == 'Point' and tuple(intersection.coords[0]) in common:
                continue
            conflicts.update([active[i]['chain_id'],active[j]['chain_id']])
        for chain in chain_records:
            if chain['chain_id'] in conflicts:
                keeps[chain['ring']][chain['original_vertex_indices']] = True
                chain['no_op'] = True; chain['kept_vertex_indices'] = chain['original_vertex_indices']
                assembly_rollbacks.append({'chain_id':chain['chain_id'],'reason':'assembled_new_chord_collision',
                    'restored_geometry':model.xy[chain['ring']][chain['original_vertex_indices']].tolist(),'further_attempt':False})
                for p in proposals:
                    if p['chain_id']==chain['chain_id']: p['applied']=False
    candidate = shapely.from_wkb(shapely.to_wkb(geometry,byte_order=1)) if epsilon==0 else model.assemble(keeps)
    assembly_seconds = time.perf_counter()-assembly_start
    max_deviation = max((p['certified_displacement_upper'] for p in proposals if p['applied']),default=0.)
    protected_vertices = set()
    for si in np.flatnonzero(guards['protected']):
        ri = int(model.owner[si]); vi = int(model.local_index[si]); protected_vertices.update([(ri,vi),(ri,(vi+1)%len(model.xy[ri]))])
    protected_chains = []
    for ri,xy in enumerate(model.xy):
        locked = guards['protected'][model.offsets[ri]:model.offsets[ri+1]];n=len(xy)
        if locked.all():
            protected_chains.append({'ring':ri,'original_vertex_indices':list(range(n))+[0],'closed':True})
        elif locked.any():
            for first in np.flatnonzero(locked & ~np.roll(locked,1)):
                count=0
                while locked[(first+count)%n]:count+=1
                protected_chains.append({'ring':ri,'original_vertex_indices':((np.arange(count+1)+first)%n).tolist(),'closed':False})
    return {'algorithm_version':'guarded_dp_v2.0_impact_width','disposition':'PARTIAL_REQUIRES_QUALIFICATION','geometry':candidate,'proposals':proposals,
            'chains':chain_records,'protected_chains':protected_chains,'protected_chain_count':len(protected_chains),
            'assembly_rollbacks':assembly_rollbacks,'keeps':keeps,
            'certified_boundary_displacement_upper':max_deviation,
            'certificate_definition':'Maximum source-vertex-to-matched-chord distance bounds both directions for each continuous endpoint-matched source polyline/chord; maximum over retained replacements bounds the combined boundary.',
            'protected_segment_count':int(guards['protected'].sum()),'protected_vertex_count':len(protected_vertices),
            'simplified_chain_count':sum(not c['no_op'] for c in chain_records),'no_op_chain_count':sum(c['no_op'] for c in chain_records),
            'rejected_chord_count':sum(bool(p['failed_constraints']) for p in proposals),
            'local_rollback_count':sum(bool(p['failed_constraints']) for p in proposals)+len(assembly_rollbacks),
            'timing':{'chain_partition_seconds':partition_seconds,'dp_traversal_seconds':traversal_seconds,
                      'chord_check_seconds':checking_seconds,'candidate_assembly_seconds':assembly_seconds,
                      'simplification_total_seconds':time.perf_counter()-start}}
