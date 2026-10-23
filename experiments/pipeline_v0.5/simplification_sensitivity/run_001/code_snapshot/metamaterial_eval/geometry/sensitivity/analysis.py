"""One independently simplified candidate, evaluated against three distinct references."""
import time
import numpy as np
import shapely
from shapely.errors import GEOSException

from ..manifold.contacts import inspect_boundary
from ..planar import rasterize_exact_geometry
from .distance import BoundaryIndex, compare_boundaries
from .features import evaluate_features
from .metrics import complexity,geometry_validity,area_comparison,continuous_topology,void_partition,raster_comparison
from .morphology import descriptor_comparison


def timed(timings,name,function):
    start=time.perf_counter();value=function();timings[name]=time.perf_counter()-start;return value


def evaluate_candidate(fixture,candidate,context,config,*,descriptor_cache=None):
    start=time.perf_counter();timing={};reference=fixture['baseline'];exact=fixture['exact'];mask=fixture['mask']
    validity=timed(timing,'geometry_validation_seconds',lambda:geometry_validity(candidate))
    stats=timed(timing,'complexity_seconds',lambda:complexity(candidate))
    result={'state':'diagnostic_simplification_candidate','validity':validity,'complexity':stats,
            'vertex_reduction_percent':100*(1-stats['vertices']/context['baseline_complexity']['vertices']),
            'serialization_size_change_bytes':stats['wkb_bytes']-context['baseline_complexity']['wkb_bytes']}
    if stats['vertices']:
        manifold=timed(timing,'manifold_check_seconds',lambda:inspect_boundary(candidate))
    else:
        manifold={'manifold':False,'contacts':[],'overlaps':[],'zero_length_segments':[],'reason':'Collapsed/empty polygon boundary'}
        timing['manifold_check_seconds']=0.
    result['manifold']=manifold
    result['manifold_violation_count']=len(manifold.get('contacts',[]))+len(manifold.get('overlaps',[]))+len(manifold.get('zero_length_segments',[]))
    result['area_from_manifold']=timed(timing,'manifold_area_comparison_seconds',lambda:area_comparison(reference,candidate))
    result['area_from_exact']=timed(timing,'exact_area_comparison_seconds',lambda:area_comparison(exact,candidate))
    candidate_index=None;candidate_void=None
    if validity['usable_polygon']:
        candidate_index=timed(timing,'candidate_boundary_index_seconds',lambda:BoundaryIndex(candidate,config['boundary_sample_spacing'],config['boundary_query_chunk']))
        same=reference.equals(candidate)
        result['distance_from_manifold']=timed(timing,'manifold_boundary_distance_seconds',lambda:compare_boundaries(context['baseline_index'],candidate_index,equal=same))
        if same and fixture['qualification']['metrics']['hausdorff_certified_for_registered_family']:
            d=fixture['qualification']['metrics']['boundary_hausdorff_distance']
            result['distance_from_exact']={'measured_hausdorff_lower':d,'continuous_hausdorff_upper':d,
                'definition':'Unchanged saved accepted baseline: reuse its v0.5A.1 isolated-construction Hausdorff certificate.',
                'reused_qualification_sha256':fixture['provenance']['sha256']['qualification']}
            timing['exact_boundary_distance_seconds']=0.
        else:
            result['distance_from_exact']=timed(timing,'exact_boundary_distance_seconds',lambda:compare_boundaries(context['exact_index'],candidate_index,equal=exact.equals(candidate)))
        candidate_void=timed(timing,'void_partition_seconds',lambda:void_partition(candidate,len(mask)))
        result['continuous_topology']=timed(timing,'continuous_topology_seconds',lambda:continuous_topology(reference,candidate,len(mask),context['baseline_void'],candidate_void))
        result['features']=timed(timing,'feature_diagnostics_seconds',lambda:evaluate_features(reference,candidate,context['features'],config,manifold,context['baseline_index'],candidate_index,
            baseline_clearances=context.get('baseline_repair_clearances'),candidate_void=candidate_void))
    else:
        result['distance_from_manifold']={'measured_hausdorff_lower':None,'continuous_hausdorff_upper':None,'reason':'Invalid/empty/nonpolygonal candidate'}
        result['distance_from_exact']=dict(result['distance_from_manifold'])
        result['continuous_topology']={'defined':False,'reason':'Invalid/empty/nonpolygonal candidate'}
        result['features']={'defined':False,'reason':'Invalid/empty/nonpolygonal candidate','repairs':[]}
        if validity['ogc_valid'] and validity['polygonal']:
            # Empty polygons have meaningful region/topology losses even though
            # they have no boundary or feature distances to evaluate.
            result['continuous_topology']=timed(timing,'continuous_topology_seconds',lambda:continuous_topology(reference,candidate,len(mask),context['baseline_void']))
    reconstructed=None
    if validity['ogc_valid'] and validity['polygonal']:
        reconstructed=timed(timing,'rasterization_seconds',lambda:rasterize_exact_geometry(candidate,len(mask)))
        result['raster_from_canonical']=raster_comparison(mask,reconstructed)
        result['raster_from_manifold']=raster_comparison(context['baseline_raster'],reconstructed)
        result['raster_comparisons_identical']=result['raster_from_canonical']==result['raster_from_manifold']
        if descriptor_cache:
            def morphology():
                data,provenance=descriptor_cache.get(reconstructed)
                return {'comparison':descriptor_comparison(context['baseline_descriptors'],data,config['notable_descriptor_drift_screen']),
                        'candidate_cache_provenance':provenance,'baseline_cache_provenance':context['baseline_descriptor_provenance']}
            result['morphology']=timed(timing,'frozen_morphology_seconds',morphology)
    else:
        result['raster_from_canonical']=None;result['raster_from_manifold']=None
        result['morphology']={'defined':False,'reason':'No certified rasterization for an invalid/nonpolygonal geometry.'}
    features=result['features'];topology=result['continuous_topology'];raster=result['raster_from_canonical']
    morphology=result.get('morphology',{}).get('comparison',{})
    result['events']={
        'ogc_invalid':not validity['ogc_valid'],'geometry_collapse':not validity['usable_polygon'],
        'nonmanifold':not manifold['manifold'],
        'hole_topology_change':bool(topology.get('defined') and not topology['hole_correspondence']['bijection']),
        'continuous_connectivity_change':bool(topology.get('defined') and not topology['solid_correspondence']['bijection']),
        'exterior_channel_change':bool(topology.get('exterior_channel_closures') or topology.get('new_exterior_openings')),
        'repair_material_risk':bool(features.get('any_material_repair_risk',False)),
        'repair_clearance_below_baseline':bool(features.get('any_clearance_below_baseline',False)),
        'repair_unresolved':bool(features.get('any_repair_unresolved',False)),
        'monitored_neck_link_lost':bool(features.get('any_monitored_neck_link_lost',False)),
        'monitored_neck_narrowed':bool(features.get('any_monitored_neck_narrowed',False)),
        'raster_disagreement':bool(raster and raster['xor_pixels']>0),
        'raster_topology_change':bool(raster and not raster['topology_unchanged']),
        'any_descriptor_drift':bool(morphology.get('any_descriptor_change',False)),
        'notable_descriptor_drift':bool(morphology.get('notable_drift_screen',False))}
    clearance=stats.get('geos_minimum_clearance_diagnostic')
    old_clearance=context['baseline_complexity'].get('geos_minimum_clearance_diagnostic')
    limit=config['geos_near_zero_robustness_screen']
    result['events']['new_near_zero_geos_robustness_distance']=bool(clearance is not None and old_clearance is not None and clearance<limit<=old_clearance)
    if not topology.get('defined'):
        for key in ('hole_topology_change','continuous_connectivity_change','exterior_channel_change'):result['events'][key]=None
    if not features.get('defined'):
        for key in ('repair_material_risk','repair_clearance_below_baseline','repair_unresolved','monitored_neck_link_lost','monitored_neck_narrowed'):result['events'][key]=None
    if raster is None:
        result['events']['raster_disagreement']=None;result['events']['raster_topology_change']=None
    if not morphology:
        result['events']['any_descriptor_drift']=None;result['events']['notable_descriptor_drift']=None
    reasons=[k for k,v in result['events'].items() if v]
    result['diagnostic_flags']=reasons
    result['status']='DIAGNOSTIC_FLAGS_PRESENT' if reasons else 'DIAGNOSTIC_NO_OBSERVED_FLAGS'
    result['production_accepted']=False
    result['promising_under_strict_available_diagnostics']=bool(not reasons and result['vertex_reduction_percent']>0)
    result['timing']=timing;timing['validation_total_seconds']=time.perf_counter()-start
    return result,reconstructed
