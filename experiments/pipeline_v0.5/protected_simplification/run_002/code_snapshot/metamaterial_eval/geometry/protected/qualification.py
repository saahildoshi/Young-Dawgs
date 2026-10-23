"""Independent full-candidate gates; no unqualified output is accepted."""
import hashlib
import time
import numpy as np
import shapely
from shapely import Polygon
from ..manifold.contacts import inspect_boundary, polygon_rings
from ..sensitivity.analysis import evaluate_candidate
from ..sensitivity.metrics import polygons
from .engine import vertex_distances


def protected_integrity(reference, candidate, risks, guards):
    model = risks['model']; before = model.rings; after = polygon_rings(candidate)
    same_roles = [(r['polygon'],r['role']) for r in before] == [(r['polygon'],r['role']) for r in after]
    coordinate_failures = []
    if same_roles:
        for ri, (ring, xy) in enumerate(zip(before, model.xy)):
            new = after[ri]['xy'][:-1]
            edges = set(zip(map(tuple,new),map(tuple,new[1:]+new[:1])))
            vertices = set(map(tuple,new))
            for si in np.flatnonzero(guards['protected'][model.offsets[ri]:model.offsets[ri+1]]):
                a,b = tuple(xy[si]),tuple(xy[(si+1)%len(xy)])
                if (a,b) not in edges or a not in vertices or b not in vertices:
                    coordinate_failures.append([ri,int(si)])
    else:
        coordinate_failures.append('ring_ownership_or_count_changed')
    difference = reference.symmetric_difference(candidate)
    boundary_change = reference.boundary.symmetric_difference(candidate.boundary)
    records = []
    equal = reference.equals(candidate)
    for guard in guards['records']:
        g = guard['geometry']
        solid_equal = equal or not difference.intersects(g) or reference.intersection(g).equals(candidate.intersection(g))
        boundary_equal = equal or not boundary_change.intersects(g) or reference.boundary.intersection(g).equals(candidate.boundary.intersection(g))
        records.append({'guard_id':guard['guard_id'],'kind':guard['kind'],
                        'solid_set_equal':bool(solid_equal),'boundary_set_equal':bool(boundary_equal),
                        'protected_segment_count':len(guard['protected_segments']),
                        'baseline_diagnostic':guard.get('baseline_width',guard.get('baseline_clearance',guard.get('baseline_separation',guard.get('minimum_edt_diameter')))),
                        'candidate_diagnostic':guard.get('baseline_width',guard.get('baseline_clearance',guard.get('baseline_separation',guard.get('minimum_edt_diameter')))) if solid_equal and boundary_equal else None,
                        'diagnostic_comparison_method':'Exact local solid/boundary invariance; EDT is a raster support diagnostic, proximity is not load-bearing width.',
                        'protection_pass':bool(solid_equal and boundary_equal)})
    return {'passed':same_roles and not coordinate_failures and all(r['protection_pass'] for r in records),
            'coordinate_failures':coordinate_failures,'ring_roles_ownership_preserved':same_roles,'guards':records}


def pore_records(reference,candidate,topology):
    old = [Polygon(h) for p in polygons(reference) for h in p.interiors]
    new = [Polygon(h) for p in polygons(candidate) for h in p.interiors]
    correspondence = topology.get('hole_correspondence',{})
    rows = []
    for i,p in enumerate(old):
        ids = correspondence.get('reference_to_candidate',[[] for _ in old])[i]
        q = new[ids[0]] if len(ids)==1 else None
        rows.append({'hole_id':f'hole_{i:05d}','reference_area':p.area,
                     'reference_boundary_sha256':hashlib.sha256(p.boundary.wkb).hexdigest(),
                     'reference_boundary_xy':list(map(list,p.exterior.coords)),
                     'candidate_indices':ids,'candidate_area':q.area if q is not None else None,
                     'candidate_boundary_sha256':hashlib.sha256(q.boundary.wkb).hexdigest() if q is not None else None,
                     'candidate_boundary_xy':list(map(list,q.exterior.coords)) if q is not None else None,
                     'overlap_area':p.intersection(q).area if q is not None else None,
                     'relative_area_distortion':abs(q.area-p.area)/p.area if q is not None and p.area else None,
                     'reference_contains_candidate':p.covers(q) if q is not None else None,
                     'candidate_contains_reference':q.covers(p) if q is not None else None})
    return rows


def qualify(fixture, candidate, context, risks, guards, engine, config, cache):
    started = time.perf_counter()
    metrics, raster = evaluate_candidate(fixture,candidate,context,config['b1_config'],descriptor_cache=cache)
    limits = config['limits']; allowance = limits['length_allowance']; a = metrics['area_from_manifold']
    gates = {'valid_polygon':metrics['validity']['usable_polygon'],
             'manifold':metrics['manifold']['manifold'],
             'continuous_topology':metrics['continuous_topology'].get('preserved',False),
             'raster_exact':bool(metrics['raster_from_canonical'] and metrics['raster_from_canonical']['exact_equal']),
             'raster_baseline_exact':bool(metrics['raster_from_manifold'] and metrics['raster_from_manifold']['exact_equal']),
             'frozen_descriptors_exact':not metrics.get('morphology',{}).get('comparison',{}).get('any_descriptor_change',True),
             'continuous_area_defined':a.get('defined',False)}
    guards_result = {'passed':False,'guards':[],'reason':'Unusable candidate'}; pores = []
    near = []; certificate = None
    if gates['valid_polygon']:
        guards_result = protected_integrity(fixture['baseline'],candidate,risks,guards)
        pores = pore_records(fixture['baseline'],candidate,metrics['continuous_topology'])
        near = inspect_boundary(candidate,near_distance=limits['minimum_new_chord_clearance'])['near_contacts']
        model = risks['model']
        coverage = candidate.equals(model.assemble(engine['keeps']))
        active = [p for p in engine['proposals'] if p['applied']]
        proposal_certificates = all(np.array_equal(model.xy[p['ring']][p['original_vertex_indices']], np.asarray(p['original_chain'])) and
                 abs(float(vertex_distances(np.asarray(p['original_chain'])).max())-p['certified_displacement_upper']) <= allowance for p in active)
        certificate = max((p['certified_displacement_upper'] for p in active),default=0.)
        # Verify the kept-index coverage itself: every removed original vertex
        # belongs to an applied endpoint-matched proposal, with no skipped arcs.
        proposed_removed = [set() for _ in model.xy]
        for p in active:
            proposed_removed[p['ring']].update(p['original_vertex_indices'][1:-1])
        coverage = coverage and all(set(np.flatnonzero(~keep)) == removed for keep,removed in zip(engine['keeps'],proposed_removed))
        lower = metrics['distance_from_manifold'].get('measured_hausdorff_lower')
        gates.update(guard_exact=guards_result['passed'], ring_chain_certificate=coverage and proposal_certificates,
                     displacement=certificate <= limits['max_displacement']+allowance,
                     independent_distance_consistent=lower is not None and lower <= certificate+allowance,
                     near_contact_floor=not any(p['distance'] < limits['minimum_new_chord_clearance']-allowance for p in near),
                     pore_area_budget=all(p['relative_area_distortion'] is not None and p['relative_area_distortion'] <= limits['max_pore_area_fraction']+allowance for p in pores))
    else:
        gates.update({key:False for key in ('guard_exact','ring_chain_certificate','displacement','independent_distance_consistent','near_contact_floor','pore_area_budget')})
    for key,field,limit in [('added_material','added_solid_area','max_added_fraction'),('removed_material','removed_solid_area','max_removed_fraction'),('symmetric_area','symmetric_difference_area','max_symmetric_fraction')]:
        gates[key] = bool(a.get('defined') and a[field] <= fixture['baseline'].area*limits[limit]+limits['area_allowance'])
    f = metrics['features']
    gates['repairs_defined_resolved'] = bool(f.get('defined') and all(p['contact_remains_resolved'] is True and p['clearance'] is not None for p in f.get('repairs',[])))
    gates['repair_patch_and_clearance'] = bool(f.get('defined') and all(p['retained_added_fraction'] is not None and p['retained_added_fraction'] >= 1-allowance and p['clearance'] is not None and p['clearance'] >= p['baseline_clearance']-allowance for p in f.get('repairs',[])))
    gates['natural_links_widths_defined_preserved'] = bool(f.get('defined') and all(p['candidate_chord']['width'] is not None and p['width_change'] >= -allowance and p['local_solid_link']['connected'] for p in f.get('natural_necks',[])))
    gates['saved_connector_preserved'] = bool(f.get('defined') and all(not p['narrowed'] and p['local_solid_link']['connected'] for p in f.get('boundary_necks',[])))
    failed = sorted(k for k,v in gates.items() if not v)
    equal = fixture['baseline'].equals(candidate)
    return {'disposition':('ACCEPTED_NOOP' if equal else 'ACCEPTED_CANDIDATE') if not failed else 'REJECTED_CANDIDATE',
            'accepted_geometric_screen':not failed,'full_scientific_physical_acceptance':False,
            'gates':gates,'failed_constraints':failed,'metrics':metrics,'guard_integrity':guards_result,
            'pores':pores,'near_contacts':near,'certified_boundary_displacement_upper':certificate,
            'qualification_seconds':time.perf_counter()-started},raster
