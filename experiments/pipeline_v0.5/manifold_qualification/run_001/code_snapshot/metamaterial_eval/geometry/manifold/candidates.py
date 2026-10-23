"""Explicit localized candidate policies and prospective quantitative gates."""
from dataclasses import dataclass, asdict
import math
import time

import numpy as np
import shapely
from shapely import Polygon, box, STRtree

from ..planar import rasterize_exact_geometry
from ..raster import compare_binary_masks
from .contacts import classify_contacts, inspect_boundary, polygon_rings


@dataclass(frozen=True)
class CandidateSettings:
    radius: float = 0.25
    max_displacement: float = 0.25
    max_symmetric_difference_fraction: float = 0.0001
    min_repaired_clearance: float = 0.25
    min_new_edge: float = 0.125
    min_affected_angle_degrees: float = 45.0
    near_contact_distance: float = 1e-6

    def validate(self):
        values=asdict(self)
        if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values.values()):
            raise ValueError('Candidate settings must be finite numbers.')
        if not 0 < self.radius <= .25:
            raise ValueError('Supported local diamond radius is 0 < r <= 0.25 cell.')
        if any(v < 0 for k,v in values.items() if k!='radius'):
            raise ValueError('Candidate limits must be nonnegative.')
        return self


def geometry_counts(geometry):
    ps=list(geometry.geoms) if geometry.geom_type=='MultiPolygon' else [geometry]
    return {'solid_polygon_components':len(ps),'holes':sum(len(p.interiors) for p in ps),
            'vertices':sum(len(r['xy'])-1 for r in polygon_rings(geometry))}


def region_count(geometry):
    if geometry.is_empty: return 0
    if geometry.geom_type=='Polygon': return 1
    if hasattr(geometry,'geoms'): return sum(region_count(g) for g in geometry.geoms)
    return 0


def measure_candidate(original, candidate, mask, supports, contacts, settings, policy):
    """Measure actual regions and boundaries; do not infer errors from boxes."""
    settings.validate()
    added=candidate.difference(original);removed=original.difference(candidate)
    symmetric=original.symmetric_difference(candidate)
    containment=symmetric.difference(supports).is_empty
    before,after=geometry_counts(original),geometry_counts(candidate)
    classification=inspect_boundary(candidate)
    valid=bool(candidate.is_valid)
    rec=rasterize_exact_geometry(candidate,len(mask)) if valid else None
    comparison=compare_binary_masks(mask,rec) if rec is not None and rec.any() else None
    features=[];local_hausdorff=[]
    rings=polygon_rings(candidate)
    boundaries=[shapely.LineString(r['xy']) for r in rings]
    tree=STRtree(boundaries)
    changed_old=original.boundary.difference(candidate.boundary)
    changed_new=candidate.boundary.difference(original.boundary)
    boundary_outside_unchanged=changed_old.difference(supports).is_empty and changed_new.difference(supports).is_empty
    for contact in contacts:
        x,y=contact['xy'];window=box(x-.5,y-.5,x+.5,y+.5)
        ids=sorted(map(int,tree.query(window,predicate='intersects')))
        pieces=[boundaries[i].intersection(window) for i in ids]
        # A restricted supported checkerboard has exactly two boundary arcs.
        merged=shapely.line_merge(shapely.union_all(pieces))
        arcs=list(merged.geoms) if hasattr(merged,'geoms') else [merged]
        clearance=float(arcs[0].distance(arcs[1])) if len(arcs)==2 else 0.0
        local_old=original.boundary.intersection(window)
        local_new=candidate.boundary.intersection(window)
        hd=float(shapely.hausdorff_distance(local_old,local_new,densify=.5))
        local_hausdorff.append(hd)
        edge_lengths=[];angles=[]
        for i in ids:
            p=np.asarray(rings[i]['xy'][:-1],dtype=float)
            for j,v in enumerate(p):
                if abs(v[0]-x)+abs(v[1]-y)<=settings.radius:
                    a=p[(j-1)%len(p)]-v;b=p[(j+1)%len(p)]-v
                    if np.linalg.norm(a) and np.linalg.norm(b):
                        angle=math.degrees(math.acos(float(np.clip(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)),-1,1))))
                        angles.append(angle)
            for a,b in zip(rings[i]['xy'][:-1],rings[i]['xy'][1:]):
                segment=shapely.LineString([a,b])
                if segment.intersects(window) and not original.boundary.covers(segment):
                    edge_lengths.append(float(segment.length))
        features.append({'contact_id':contact['contact_id'],'xy':[x,y],
                         'local_minimum_clearance':clearance,
                         'minimum_new_edge_length':min(edge_lengths) if edge_lengths else None,
                         'minimum_affected_angle_degrees':min(angles) if angles else None,
                         'subpixel_feature_introduced':bool(policy.startswith('solid_') and clearance<1),
                         'local_discrete_hausdorff':hd,'local_boundary_arc_count':len(arcs)})
    max_hd=max(local_hausdorff,default=0.0)
    # Exact Hausdorff for the registered isolated orthogonal-checkerboard
    # chamfer family: outside supports sets coincide, and each V-to-chamfer
    # distance reaches r/sqrt(2) at the old corner, with no greater distance
    # along either incident edge. Unsupported candidates have no such proof.
    expected=settings.radius/math.sqrt(2) if contacts else 0.0
    family_certified=bool(boundary_outside_unchanged and all(c.get('inherent_in_source') and c.get('boundary_link_degree')==4 for c in contacts)
                          and abs(max_hd-expected)<=1e-10 and policy.startswith(('solid_','void_')))
    if not contacts and symmetric.is_empty:
        family_certified=True
    metrics={'original_area':float(original.area),'candidate_area':float(candidate.area),
             'signed_area_change':float(candidate.area-original.area),
             'absolute_area_difference':float(abs(candidate.area-original.area)),
             'relative_area_difference':float(abs(candidate.area-original.area)/original.area),
             'symmetric_difference_area':float(symmetric.area),
             'symmetric_difference_fraction':float(symmetric.area/original.area),
             'added_solid_area':float(added.area),'removed_solid_area':float(removed.area),
             'added_solid_regions':region_count(added),'removed_solid_regions':region_count(removed),
             'modified_contact_neighborhoods':len(contacts) if not symmetric.is_empty else 0,
             'maximum_local_boundary_displacement':max_hd,
             'boundary_hausdorff_distance':max_hd if family_certified else None,
             'hausdorff_certified_for_registered_family':family_certified,
             'hausdorff_method':'Actual local boundary comparisons with densify=0.5, plus isolated V/chamfer analytic maximum and unchanged-boundary check outside supports; no global discrete-distance claim.',
             'changes_confined_to_supports':containment,'boundary_outside_supports_unchanged':boundary_outside_unchanged,
             'geometry_before':before,'geometry_after':after,'features':features,
             'continuous_equivalent':bool(original.equals(candidate)),
             'continuous_boundary_contact_topology_changed':bool(contacts and not symmetric.is_empty),
             'continuous_topology_note':'Solid-side separates touching void closures and replaces a point-only local solid link by positive width; void-side may merge pore interiors. Digital topology is evaluated separately.'}
    clearance_ok=all(f['local_minimum_clearance']>=settings.min_repaired_clearance for f in features)
    edge_ok=all(f['minimum_new_edge_length'] is None or f['minimum_new_edge_length']>=settings.min_new_edge for f in features)
    angle_ok=all(f['minimum_affected_angle_degrees'] is None or f['minimum_affected_angle_degrees']>=settings.min_affected_angle_degrees for f in features)
    gates={'valid_polygon':valid,'manifold_boundary':classification['manifold'],
           'area_budget':metrics['symmetric_difference_fraction']<=settings.max_symmetric_difference_fraction,
           'displacement_budget':family_certified and max_hd<=settings.max_displacement,
           'positive_clearance':all(f['local_minimum_clearance']>0 for f in features),
           'clearance_floor':clearance_ok,'new_edge_floor':edge_ok,'angle_floor':angle_ok,
           'localized_changes':containment and boundary_outside_unchanged,
           'solid_polygon_components_preserved':before['solid_polygon_components']==after['solid_polygon_components'],
           'hole_count_preserved':before['holes']==after['holes'],
           'inside_original_domain':bool(candidate.covered_by(box(0,0,len(mask),len(mask)))),
           'raster_exact':bool(comparison and comparison['exact_equal']),
           'raster_topology_preserved':bool(comparison and comparison['topology_unchanged']),
           'solid_side_addition_only':bool(removed.is_empty) if policy.startswith('solid_') else True}
    return {'metrics':metrics,'gates':gates,'boundary':classification,'comparison':comparison,'reconstructed':rec,
            'accepted':all(gates.values()),'failed_gates':[k for k,v in gates.items() if not v]}


def qualify_manifold_geometry(mask, exact, contact_policy='preserve_exact', settings=None, contacts=None):
    """Return separate candidate state; never mutate exact geometry or mask."""
    settings=(settings or CandidateSettings()).validate()
    allowed={'preserve_exact','solid_separate_pores','solid_separate_contacts','void_side_probe'}
    if contact_policy not in allowed:
        raise ValueError(f'Unknown explicit contact policy: {contact_policy}')
    start=time.perf_counter()
    diagnosis=contacts if contacts is not None else classify_contacts(mask,exact)
    detection_seconds=time.perf_counter()-start
    original=exact['geometry'];changes=diagnosis['contacts']
    exact_fidelity=exact['comparison']['exact_equal'] and exact['comparison']['topology_unchanged'] and exact['validity']['area_equals_occupied_cells']
    base={'schema':'young-dawgs-manifold-qualification-v0.5A.1', 'contact_policy':contact_policy,
          'settings':asdict(settings),'state':'exact_geometry' if contact_policy=='preserve_exact' else 'manifold_candidate',
          'exact_fidelity':'PASS' if exact_fidelity else 'FAIL',
          'contact_classification':'PASS' if diagnosis['classification_pass'] else 'FAIL',
          'physical_feature_qualification':'UNQUALIFIED','mesh_quality':'UNQUALIFIED',
          'mechanical_validation':'UNQUALIFIED','manufacturability_validation':'UNQUALIFIED',
          'contact_report':diagnosis,'geometry':original,'reconstructed':mask.copy(),
          'timing':{'contact_detection_seconds':detection_seconds},'changes':[]}
    if contact_policy=='preserve_exact' or not changes:
        measurement=measure_candidate(original,original,mask,Polygon(),[],settings,'preserve_exact')
        base.update(measurement)
        base['status']='exact_manifold' if diagnosis['manifold'] else 'exact_nonmanifold'
        if contact_policy!='preserve_exact':
            base['status']='ACCEPT_NOOP' if measurement['accepted'] else 'REJECT_NOOP'
        base['manifold_candidate_validity']='PASS' if diagnosis['manifold'] else 'FAIL'
        base['geometric_modification_budget']='PASS'
        base['raster_morphology_preservation']='PASS' if measurement['gates']['raster_exact'] else 'FAIL'
        return base
    reasons=[]
    if not diagnosis['classification_pass'] or diagnosis['overlaps'] or diagnosis['zero_length_segments']:
        reasons.append('unqualified_boundary_graph')
    for c in changes:
        supported_types={'pore_pore_point'} if contact_policy=='solid_separate_pores' else {'pore_pore_point','hole_shell_point'}
        if not (c['kind'] in supported_types and c['inherent_in_source'] and c['boundary_link_degree']==4
                and len(c['incident_rings'])==2 and len(c['incident_polygons'])==1):
            reasons.append(c['contact_id']+':unsupported_contact_type')
    if reasons:
        base.update(status='REJECT_UNSUPPORTED_CONTACT',geometry=None,accepted=False,
                    failed_gates=reasons,manifold_candidate_validity='NOT_PRODUCED',
                    geometric_modification_budget='NOT_EVALUATED',raster_morphology_preservation='NOT_EVALUATED')
        return base
    start=time.perf_counter()
    diamonds=[]
    for c in changes:
        x,y=c['xy'];r=settings.radius
        diamonds.append(Polygon([(x-r,y),(x,y-r),(x+r,y),(x,y+r)]))
        base['changes'].append({'contact_id':c['contact_id'],'xy':[x,y],
                                'operation':'add_solid_diamond' if contact_policy.startswith('solid_') else 'remove_solid_diamond',
                                'L1_radius':r,'predicted_symmetric_difference_area':r*r,
                                'predicted_max_displacement':r/math.sqrt(2),
                                'predicted_local_clearance':math.sqrt(2)*r})
    supports=shapely.union_all(diamonds)
    candidate=original.union(supports) if contact_policy.startswith('solid_') else original.difference(supports)
    base['timing']['construction_seconds']=time.perf_counter()-start
    start=time.perf_counter()
    measurement=measure_candidate(original,candidate,mask,supports,changes,settings,contact_policy)
    base['timing']['comparison_and_validation_seconds']=time.perf_counter()-start
    base.update(measurement,geometry=candidate)
    base['status']='ACCEPT_GEOMETRIC_CANDIDATE' if measurement['accepted'] and exact_fidelity and diagnosis['classification_pass'] else 'REJECT_CANDIDATE'
    base['accepted']=base['status']=='ACCEPT_GEOMETRIC_CANDIDATE'
    base['manifold_candidate_validity']='PASS' if measurement['gates']['valid_polygon'] and measurement['gates']['manifold_boundary'] else 'FAIL'
    budget_keys=['area_budget','displacement_budget','positive_clearance','clearance_floor','new_edge_floor','angle_floor','localized_changes','hole_count_preserved','solid_polygon_components_preserved','inside_original_domain','solid_side_addition_only']
    base['geometric_modification_budget']='PASS' if all(measurement['gates'][k] for k in budget_keys) else 'FAIL'
    base['raster_morphology_preservation']='PASS' if measurement['gates']['raster_exact'] and measurement['gates']['raster_topology_preserved'] else 'FAIL'
    return base
