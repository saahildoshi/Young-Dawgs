"""Continuous region, correspondence and raster metrics, with invalid-data guards."""
import numpy as np
import shapely
from shapely import Polygon, STRtree, box
from shapely.errors import GEOSException
from shapely.validation import explain_validity
from ..manifold.contacts import polygon_rings
from ..topology import analyze_raster_topology
from ...pipeline.config import default_evaluator_path
from ...pipeline.evaluator import load_evaluator


def polygons(geometry):
    if geometry.is_empty:return []
    if geometry.geom_type=='Polygon':return [geometry]
    if hasattr(geometry,'geoms'):
        return [p for g in geometry.geoms for p in polygons(g)]
    return []


def complexity(geometry):
    ps=polygons(geometry)
    exterior=sum(len(p.exterior.coords)-1 for p in ps)
    holes=sum(len(h.coords)-1 for p in ps for h in p.interiors)
    return {'geometry_type':geometry.geom_type,'empty':bool(geometry.is_empty),'polygon_components':len(ps),
            'exterior_rings':len(ps),'hole_rings':sum(len(p.interiors) for p in ps),
            'total_rings':sum(1+len(p.interiors) for p in ps),'vertices':exterior+holes,
            'exterior_vertices':exterior,'hole_vertices':holes,'area':float(geometry.area),
            'boundary_length':float(geometry.length),'wkb_bytes':len(shapely.to_wkb(geometry,byte_order=1)),
            'geos_minimum_clearance_diagnostic':float(geometry.minimum_clearance) if ps else None,
            'minimum_clearance_interpretation':'GEOS geometry robustness distance; not a physical or load-bearing neck width.'}


def geometry_validity(candidate):
    ps=polygons(candidate);rings=[p.exterior for p in ps]+[r for p in ps for r in p.interiors]
    containment=[]
    for pi,p in enumerate(ps):
        shell=Polygon(p.exterior)
        for hi,hole in enumerate(p.interiors):
            if not shell.covers(Polygon(hole)):
                containment.append({'polygon':pi,'hole':hi,'kind':'hole_not_contained_in_shell'})
    return {'ogc_valid':bool(candidate.is_valid),'validity_reason':explain_validity(candidate),
            'empty':bool(candidate.is_empty),'polygonal':candidate.geom_type in ('Polygon','MultiPolygon'),
            'all_rings_closed':all(r.is_closed for r in rings),'all_rings_simple':all(r.is_simple for r in rings),
            'invalid_ring_indices':[i for i,r in enumerate(rings) if not r.is_simple or not r.is_closed],
            'hole_shell_relationship_violations':containment,'polygon_components':len(ps),
            'usable_polygon':bool(candidate.is_valid and not candidate.is_empty and candidate.geom_type in ('Polygon','MultiPolygon'))}


def area_comparison(reference,candidate):
    base={'reference_area':float(reference.area),'candidate_area':float(candidate.area),
          'signed_area_change':float(candidate.area-reference.area),
          'absolute_area_change':float(abs(candidate.area-reference.area)),
          'relative_signed_area_change':float((candidate.area-reference.area)/reference.area) if reference.area else None,
          'boundary_length_change':float(candidate.length-reference.length)}
    if not reference.is_valid or not candidate.is_valid:
        return {**base,'defined':False,'reason':'Boolean area comparison undefined for invalid region; no repair applied.',
                'added_solid_area':None,'removed_solid_area':None,'symmetric_difference_area':None,'relative_symmetric_difference_area':None}
    try:
        added=candidate.difference(reference);removed=reference.difference(candidate)
        sym=reference.symmetric_difference(candidate)
        return {**base,'defined':True,'added_solid_area':float(added.area),'removed_solid_area':float(removed.area),
                'symmetric_difference_area':float(sym.area),'relative_symmetric_difference_area':float(sym.area/reference.area) if reference.area else None}
    except GEOSException as exc:
        return {**base,'defined':False,'reason':str(exc),'added_solid_area':None,'removed_solid_area':None,
                'symmetric_difference_area':None,'relative_symmetric_difference_area':None}


def region_correspondence(reference,candidate,area_allowance=1e-12):
    """Track all positive-area overlaps; do not assume ring order or counts suffice."""
    tree=STRtree(candidate);forward=[];reverse=[[] for _ in candidate]
    for i,region in enumerate(reference):
        matches=[]
        for j in sorted(map(int,tree.query(region,predicate='intersects'))):
            if region.intersection(candidate[j]).area>area_allowance:
                matches.append(j);reverse[j].append(i)
        forward.append(matches)
    return {'lost_reference_regions':[i for i,v in enumerate(forward) if not v],
            'new_candidate_regions':[i for i,v in enumerate(reverse) if not v],
            'split_reference_regions':[i for i,v in enumerate(forward) if len(v)>1],
            'merged_candidate_regions':[i for i,v in enumerate(reverse) if len(v)>1],
            'reference_to_candidate':forward,'candidate_to_reference':reverse,
            'bijection':len(reference)==len(candidate) and all(len(x)==1 for x in forward) and all(len(x)==1 for x in reverse)}


def void_partition(geometry,resolution):
    domain=box(0,0,resolution,resolution)
    parts=polygons(domain.difference(geometry))
    exterior=[bool(p.boundary.intersection(domain.boundary).length>0) for p in parts]
    return parts,exterior


def continuous_topology(reference,candidate,resolution,reference_void=None,candidate_void=None):
    if not reference.is_valid or not candidate.is_valid or candidate.geom_type not in ('Polygon','MultiPolygon'):
        return {'defined':False,'reason':'Invalid/nonpolygonal region; no topology repair applied.'}
    a,b=polygons(reference),polygons(candidate)
    ha=[Polygon(h) for p in a for h in p.interiors];hb=[Polygon(h) for p in b for h in p.interiors]
    solids=region_correspondence(a,b);holes=region_correspondence(ha,hb)
    va,ea=reference_void if reference_void is not None else void_partition(reference,resolution)
    vb,eb=candidate_void if candidate_void is not None else void_partition(candidate,resolution);voids=region_correspondence(va,vb)
    closures=[];openings=[]
    for i,matches in enumerate(voids['reference_to_candidate']):
        for j in matches:
            if ea[i] and not eb[j]:closures.append({'reference_void':i,'candidate_void':j})
            if not ea[i] and eb[j]:openings.append({'reference_void':i,'candidate_void':j})
    return {'defined':True,'solid_interior_components_before':len(a),'solid_interior_components_after':len(b),
            'hole_count_before':len(ha),'hole_count_after':len(hb),
            'solid_correspondence':solids,'hole_correspondence':holes,'void_correspondence':voids,
            'exterior_void_regions_before':sum(ea),'exterior_void_regions_after':sum(eb),
            'exterior_channel_closures':closures,'new_exterior_openings':openings,
            'preserved':solids['bijection'] and holes['bijection'] and voids['bijection'] and not closures and not openings,
            'component_definition':'Positive-area polygon-interior components; point contacts are separately assessed by the manifold checker.'}


def raster_comparison(reference,reconstructed):
    if reference.shape!=reconstructed.shape:raise ValueError('Raster comparisons require the same original grid.')
    fp=int(np.count_nonzero((reference==0)&(reconstructed==1)));fn=int(np.count_nonzero((reference==1)&(reconstructed==0)))
    intersection=int(np.count_nonzero(reference&reconstructed));union=int(np.count_nonzero(reference|reconstructed))
    basic=load_evaluator(str(default_evaluator_path().resolve())).basic_metrics(reconstructed)
    original=load_evaluator(str(default_evaluator_path().resolve())).basic_metrics(reference)
    return {'reference_solid_pixels':int(reference.sum()),'solid_pixels':int(reconstructed.sum()),
            'false_positive_pixels':fp,'false_negative_pixels':fn,'xor_pixels':fp+fn,'iou':intersection/union if union else 1.,
            'exact_equal':bool(np.array_equal(reference,reconstructed)),
            'component_count':int(basic['component_count']),'largest_component_fraction':float(basic['f_largest']),
            'percolates_x':bool(basic['Px']),'percolates_y':bool(basic['Py']),
            'topology_unchanged':all(basic[k]==original[k] for k in ('component_count','Px','Py'))}
