"""Frozen-cohort execution of independent C checks, never tuning producers."""
import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import platform
import resource
import time
import traceback
import tracemalloc
import numpy as np
import shapely
from shapely import box, Polygon, LineString
from .checks import (digest,authenticate,rings,polygons,serialization_check,independent_raster,
    raster_metrics,boundary_integrity,area_difference,topology,boundary_distance,area_gates,
    select_probes,feature_audit,provenance_check,acceptance,line_parts)
from ..sensitivity.records import write_json
from ..reporting import environment
from ..conversion import convert_exact,geometry_bytes
from ..manifold.candidates import qualify_manifold_geometry
from ..manifold.contacts import inspect_boundary
from ..sensitivity.study import context_for
from ..sensitivity.features import serializable_features
from ..sensitivity.morphology import DescriptorCache
from ..protected.guards import prepare_risks,build_guards,guard_document
from ..protected.engine import simplify_protected
from ..protected.qualification import qualify
from ...pipeline.resolution_worker import perform_job,evaluate_native

ROOT=Path(__file__).resolve().parents[3]
DEFAULT=ROOT/'experiments/pipeline_v0.5/scientific_validation/run_001'
B2=ROOT/'experiments/pipeline_v0.5/protected_simplification/run_002'


def read(p):return json.loads(Path(p).read_text())


def verify(output):
    frozen=read(output/'protocol/IMPLEMENTATION_FREEZE.json')
    for p,h in frozen['code_sha256'].items():authenticate(ROOT/p,h)
    authenticate(output/'protocol/PROTOCOL.json',frozen['protocol_sha256'])
    config=read(output/'protocol/PROTOCOL.json')
    for p,h in config['frozen_b2_code_sha256'].items():authenticate(ROOT/p,h)
    for row in config['cohort']:authenticate(ROOT/row['registered_256_source'],row['registered_256_sha256'])
    return config


def freeze(output):
    if (output/'protocol/IMPLEMENTATION_FREEZE.json').exists():raise FileExistsError('Frozen C implementation already registered')
    config=read(output/'protocol/PROTOCOL.json')
    for p,h in config['frozen_b2_code_sha256'].items():authenticate(ROOT/p,h)
    paths=list((ROOT/'metamaterial_eval/geometry/validation').glob('*.py'))
    paths += [ROOT/'tests/test_scientific_geometry_validation.py',ROOT/'docs/pipeline_v0.5/SCIENTIFIC_VALIDATION_ARCHITECTURE.md']
    paths += list((ROOT/'metamaterial_eval/generators').glob('*.py'))
    rec={'frozen_utc':datetime.now(timezone.utc).isoformat(),'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in paths},
         'protocol_sha256':digest(output/'protocol/PROTOCOL.json'),'new_parameter_outcomes_examined':False}
    write_json(output/'protocol/IMPLEMENTATION_FREEZE.json',rec);write_json(output/'protocol/environment.json',environment())
    print('Frozen C implementation and protocol before all real C outcomes.',flush=True)


def save_wkb(path,g):
    path.write_bytes(shapely.to_wkb(g,byte_order=1));return digest(path)


def old_fixture(folder):
    b=read(folder/'baseline.json');p=b['provenance']
    authenticate(ROOT/p['canonical_path'],p['canonical_sha256'])
    for k,v in p['paths'].items():authenticate(ROOT/v,p['sha256'][k])
    mask=np.load(ROOT/p['canonical_path'],allow_pickle=False)
    manifest=read((ROOT/p['canonical_path']).parent/'manifest.json')
    return {'id':b['fixture'],'mask':mask,'exact':shapely.from_wkb((ROOT/p['paths']['exact']).read_bytes()),
            'baseline':shapely.from_wkb((ROOT/p['paths']['manifold']).read_bytes()),
            'qualification':read(ROOT/p['paths']['qualification']),'provenance':p,
            'input_manifest':read(ROOT/p['paths']['input_manifest']),
            'exact_document':read(ROOT/p['paths']['exact_boundaries']),
            'features':b['registered_features'],'source_manifest':manifest}


def new_fixture(output,spec,config):
    identifier=spec['fixture']; folder=output/'parameter_holdouts'/identifier;folder.mkdir()
    job={k:spec[k] for k in ('sample_id','design_id','replicate','seed','requested')}
    job.update(resolution=1024,generator_version='0.4.1',historical_sample=str(ROOT/spec['registered_256_source']))
    write_json(folder/'native_job.json',job)
    started=time.perf_counter();manifest=perform_job(job,folder/'native1024')
    times={'native_generation_and_evaluator':time.perf_counter()-started}
    if not tracemalloc.is_tracing():tracemalloc.start()
    if manifest['status']!='COMPLETE':
        write_json(folder/'QUARANTINE.json',{'stage':'native_source','manifest_status':manifest['status']});return None,times
    path=folder/'native1024/microstructure.npy';authenticate(path,manifest['files']['microstructure.npy']['sha256'])
    mask=np.load(path,allow_pickle=False)
    start=time.perf_counter();exact=convert_exact(mask);again=convert_exact(mask)
    times['exact_extraction_and_repeat']=time.perf_counter()-start
    if exact['geometry'] is None:
        write_json(folder/'QUARANTINE.json',{'stage':'exact_extraction'});return None,times
    exact_repeat=exact['geometry'].wkb==again['geometry'].wkb and geometry_bytes(exact['document'])==geometry_bytes(again['document'])
    del again
    (folder/'exact_boundaries.json').write_bytes(geometry_bytes(exact['document']));save_wkb(folder/'G1.wkb',exact['geometry'])
    start=time.perf_counter();q=qualify_manifold_geometry(mask,exact,'solid_separate_contacts');repeat=qualify_manifold_geometry(mask,exact,'solid_separate_contacts')
    times['manifold_qualification_and_repeat']=time.perf_counter()-start
    write_json(folder/'ingress_qualification.json',{k:v for k,v in q.items() if k not in ('geometry','reconstructed')})
    if not q['accepted'] or q['geometry'] is None:
        write_json(folder/'QUARANTINE.json',{'stage':'manifold_ingress','failed_gates':q.get('failed_gates'),
                   'exact_fidelity':raster_metrics(mask,independent_raster(exact['geometry'],len(mask))[0]),
                   'new_contacts':inspect_boundary(exact['geometry'])});return None,times
    deterministic=exact_repeat and repeat['geometry'].wkb==q['geometry'].wkb
    save_wkb(folder/'G2.wkb',q['geometry'])
    m={'source_directory':str(path.parent.relative_to(ROOT)),'saved_topology_repair':manifest['topology_repair'],
       'coordinates':exact['document']['coordinates'],'requested':manifest['requested'],
       'generator_version':manifest['generator_version'],'generator_sha256':manifest['generator_sha256']}
    write_json(folder/'input_manifest.json',m)
    paths={'exact':folder/'G1.wkb','manifold':folder/'G2.wkb','exact_boundaries':folder/'exact_boundaries.json',
           'qualification':folder/'ingress_qualification.json','input_manifest':folder/'input_manifest.json'}
    p={'canonical_path':str(path.relative_to(ROOT)),'canonical_sha256':digest(path),
       'paths':{k:str(p.relative_to(ROOT)) for k,p in paths.items()},'sha256':{k:digest(p) for k,p in paths.items()}}
    return {'id':identifier,'mask':mask,'exact':shapely.from_wkb((folder/'G1.wkb').read_bytes()),
            'baseline':shapely.from_wkb((folder/'G2.wkb').read_bytes()),'qualification':{k:v for k,v in q.items() if k not in ('geometry','reconstructed')},
            'input_manifest':m,'exact_document':exact['document'],'provenance':p,'source_manifest':manifest,
            'construction_deterministic':deterministic},times


def source_checks(output,fixture):
    name=fixture['id'];folder=output/'geometry'/name;folder.mkdir()
    start=time.perf_counter();a=fixture['exact'];b=fixture['baseline'];mask=fixture['mask'];n=len(mask)
    serialization={};rasters={};times={}
    for key,g in [('G1',a),('G2',b)]:
        t=time.perf_counter();serialization[key]=serialization_check(g,folder,key);times[key+'_serialization']=time.perf_counter()-t
        t=time.perf_counter();rec,ties=independent_raster(g,n);times[key+'_raster']=time.perf_counter()-t
        np.save(folder/(key+'.reconstructed.npy'),rec,allow_pickle=False)
        rasters[key]={**raster_metrics(mask,rec),'boundary_center_ties':ties}
    t=time.perf_counter();metrics={'area':area_difference(a,b),'distance':boundary_distance(a,b),
                                'G1_integrity':boundary_integrity(a),'G2_integrity':boundary_integrity(b),
                                'G1_to_G2_topology':topology(a,b,n)}
    times['ingress_continuous_comparison']=time.perf_counter()-t
    # G1 singularities are explicitly authorized modifications, not silently
    # treated as topology-preserving continuous construction.
    metrics['contact_policy']='solid_separate_contacts; exact singularities may change closure adjacency. G2->G3 must preserve continuous topology.'
    t=time.perf_counter();descriptor=evaluate_native(mask);times['frozen_evaluator']=time.perf_counter()-t
    write_json(folder/'original_frozen_descriptors.json',descriptor)
    source={'fixture':name,'source_provenance':fixture['provenance'],'parameters':fixture['source_manifest']['requested'],
            'seed':fixture['source_manifest']['seed'],'resolution':n,'serialization':serialization,'rasters':rasters,
            'ingress_continuous':metrics,'times':times,'total_seconds':time.perf_counter()-start,
            'construction_deterministic':fixture.get('construction_deterministic','authenticated B2 repeated construction record'),
            'descriptor_pixel_sha256':__import__('hashlib').sha256(mask.tobytes()).hexdigest()}
    write_json(output/'source_manifests'/(name+'.json'),source)
    return source,descriptor


def validate_candidate(output,fixture,source,descriptor,candidate_path,guards_path,frozen_qualification,epsilon,cohort,probes,registered,integration=False):
    started=time.perf_counter();name=fixture['id'];cid=f'epsilon_{epsilon:.2f}'.replace('.','p')
    folder=output/('development_reference' if cohort=='B2_reference' else 'parameter_holdouts')/name/cid
    folder.mkdir(parents=True,exist_ok=True)
    timings={};t=time.perf_counter();candidate=shapely.from_wkb(candidate_path.read_bytes());timings['independent_loading']=time.perf_counter()-t
    a=fixture['exact'];b=fixture['baseline'];mask=fixture['mask'];n=len(mask)
    t=time.perf_counter();serial=serialization_check(candidate,folder,'G3');timings['serialization_reconstruction']=time.perf_counter()-t
    t=time.perf_counter();rec,ties=independent_raster(candidate,n);rm=raster_metrics(mask,rec);rm['boundary_center_ties']=ties
    timings['raster']=time.perf_counter()-t;np.save(folder/'G3.reconstructed.npy',rec,allow_pickle=False)
    t=time.perf_counter();same=b.equals(candidate)
    areas={'G1_G2':source['ingress_continuous']['area'],'G2_G3':area_difference(b,candidate),'G1_G3':area_difference(a,candidate)}
    d23=boundary_distance(b,candidate);d13=source['ingress_continuous']['distance'] if same else boundary_distance(a,candidate)
    dist={'G1_G2':source['ingress_continuous']['distance'],'G2_G3':d23,'G1_G3':d13}
    integrity=boundary_integrity(candidate);continuous=topology(b,candidate,n);cumulative=topology(a,candidate,n)
    dedicated=inspect_boundary(candidate);timings['continuous_comparison']=time.perf_counter()-t
    # Separate role distances to entire target boundary; source role statistics
    # do not invent hole identities or use DP source indices.
    role_distance={}
    from .checks import directed_bound
    for role in ['shell','hole']:
        pieces=[LineString(r['xy']) for r in rings(b) if r['role']==role]
        if pieces:role_distance[role]=directed_bound(shapely.union_all(pieces),candidate.boundary)
    t=time.perf_counter();guard=shapely.from_wkb(guards_path.read_bytes());fa=feature_audit(b,candidate,mask,guard,probes,registered)
    # Repair patches are the actual G2\G1 intersections, not assumed diamonds.
    for row in fa['repairs']:
        x,y=row['xy'];window=box(x-.5,y-.5,x+.5,y+.5)
        patch=b.difference(a).intersection(window)
        row.update(added_material_area=patch.area,retained_patch_area=patch.intersection(candidate).area,
                   footprint_xy=rings(patch),G1_G2_distance=boundary_distance(a.intersection(window),b.intersection(window)),
                   G2_G3_local_boundary_difference=b.boundary.intersection(window).symmetric_difference(candidate.boundary.intersection(window)).length)
    timings['feature_audit']=time.perf_counter()-t
    limits=read(output/'protocol/PROTOCOL.json')['b2_config']['limits']
    pixel_equal=rm['xor']==0
    t=time.perf_counter();desc_equal=pixel_equal
    desc_method='Reused fresh frozen original evaluation by independently proven identical pixel bytes; no repeated metric execution.'
    if integration:
        repeated=evaluate_native(rec);write_json(folder/'reconstructed_frozen_descriptors.json',repeated)
        desc_equal=repeated==descriptor;desc_method='Fresh original and reconstructed evaluator v1.1 executions; complete nested scalar/curve equality.'
    timings['frozen_evaluator']=time.perf_counter()-t
    p=fixture['provenance'];provenance={'source_path':p['canonical_path'],'source_sha256':p['canonical_sha256'],
        'parameters':fixture['source_manifest']['requested'],'seed':fixture['source_manifest']['seed'],'resolution':n,
        'geometry_hashes':{'G1':p['sha256']['exact'],'G2':p['sha256']['manifold'],'G3_input':digest(candidate_path),'G3_roundtrip':digest(folder/'G3.wkb')},
        'algorithm_versions':{'exact':'frozen A','manifold':'frozen A1 solid_separate_contacts','simplifier':'guarded_dp_v1.1','validator':'v0.5C-v1'},
        'candidate_input_path':str(candidate_path.relative_to(ROOT)),'guard_input_path':str(guards_path.relative_to(ROOT)),
        'candidate_input_sha256':digest(candidate_path),'guard_input_sha256':digest(guards_path),
        'protocol_sha256':digest(output/'protocol/PROTOCOL.json'),'environment_path':'protocol/environment.json'}
    metadata_expected=source['ingress_continuous']['area']['symmetric']>0
    metadata_complete=not metadata_expected or (bool(registered.get('repairs')) and abs(sum(r['added_material_area'] for r in fa['repairs'])-source['ingress_continuous']['area']['added'])<=1e-10)
    source_edges=[(tuple(u),tuple(v)) for r in rings(b) for u,v in zip(r['xy'][:-1],r['xy'][1:])]
    new_edges={(tuple(u),tuple(v)) for r in rings(candidate) for u,v in zip(r['xy'][:-1],r['xy'][1:])}
    guard_records=read(guards_path.with_name('guards.json'))
    protected_ids=sorted(set(i for r in guard_records for i in r['protected_segments']))
    missing_protected=[i for i in protected_ids if source_edges[i] not in new_edges]
    fa['protected_segment_count']=len(protected_ids);fa['missing_protected_segments']=missing_protected
    gates={'provenance':provenance_check(provenance),'serialization':serial['passed'],
        'exact_occupancy':source['rasters']['G1']['xor']==0,'manifold_occupancy':source['rasters']['G2']['xor']==0,
        'exact_area':abs(a.area-int(mask.sum()))<=1e-10,'G2_manifold':source['ingress_continuous']['G2_integrity']['passed'],
        'G3_ogc_and_independent_manifold':integrity['passed'],'frozen_manifold_classifier':dedicated['manifold'],
        'frozen_B2_constraints':frozen_qualification['accepted_geometric_screen'],
        'G2_G3_continuous_topology':continuous['passed'],'raster_exact':pixel_equal,'frozen_descriptors':desc_equal,
        'all_source_serializations':all(q['passed'] for q in source['serialization'].values()),
        'area_consistency':all(abs(d['boolean_identity_error'])<=1e-10 and abs(d['net_identity_error'])<=1e-10 for d in areas.values()),
        'independent_displacement_G2_G3':d23['upper']<=limits['max_displacement']+limits['length_allowance'],
        'independent_displacement_G1_G3':d13['upper']<=limits['max_displacement']+limits['length_allowance'],
        'sampled_lower_vs_B2_certificate':d23['lower']<=frozen_qualification['certified_boundary_displacement_upper']+limits['length_allowance'],
        'pore_area':all(r['relative_area_distortion'] is not None and r['relative_area_distortion']<=limits['max_pore_area_fraction']+1e-10 for r in continuous['holes']['records']),
        'guard_sets_exact':fa['guard_exact'],'protected_coordinates_exact':not missing_protected,'repair_metadata_complete':metadata_complete,
        'repairs_preserved':all(r['preserved'] for r in fa['repairs']),
        'construction_deterministic':fixture.get('construction_deterministic',True)}
    for pair,first,last in [('G2_G3',b,candidate),('G1_G3',a,candidate)]:
        gates.update({pair+'_'+k:v for k,v in area_gates(first,last,limits).items()})
    flags=fa['narrowed_probes']+fa['undefined_probes']
    result={'fixture':name,'cohort':cohort,'epsilon':epsilon,'provenance':provenance,
        'G3_serialization':serial,'areas':areas,'distances':dist,'source_role_to_candidate_distance':role_distance,
        'G3_integrity':integrity,'continuous_topology':continuous,'cumulative_topology':cumulative,
        'raster':rm,'features':fa,'descriptor_comparison':{'exact':desc_equal,'method':desc_method},
        'gates':gates,'acceptance':acceptance(gates,flags),'timings':timings,
        'vertices':serial['vertices'],'baseline_vertices':source['serialization']['G2']['vertices'],
        'vertex_reduction_percent':100*(1-serial['vertices']/source['serialization']['G2']['vertices']),
        'B2_disposition':frozen_qualification['disposition'],'B2_certificate':frozen_qualification['certified_boundary_displacement_upper'],
        'total_seconds':time.perf_counter()-started}
    write_json(folder/'independent_validation.json',result)
    # Save complete candidate-specific scientific evidence, not only aggregate.
    write_json(output/'continuous_metrics'/(name+'_'+cid+'.json'),{'areas':areas,'distances':dist,'topology':continuous})
    write_json(output/'feature_audit'/(name+'_'+cid+'.json'),fa)
    row={k:result[k] for k in ['fixture','cohort','epsilon','vertices','baseline_vertices','vertex_reduction_percent','total_seconds','timings','acceptance','B2_disposition']}
    row.update(symmetric_G2_G3=areas['G2_G3']['symmetric'],symmetric_G1_G3=areas['G1_G3']['symmetric'],
               added=areas['G2_G3']['added'],removed=areas['G2_G3']['removed'],distance_lower=d23['lower'],distance_upper=d23['upper'],
               cumulative_distance_lower=d13['lower'],cumulative_distance_upper=d13['upper'],raster_xor=rm['xor'],
               narrowed_probes=fa['narrowed_probes'],undefined_probes=fa['undefined_probes'],
               guard_boundary_fraction=fa['guard_boundary_fraction'],narrow_medial_guard_fraction=fa['guarded_narrow_fraction'],
               repairs=len(fa['repairs']),holes=integrity['holes'],result_path=str((folder/'independent_validation.json').relative_to(ROOT)))
    print(cohort,name,epsilon,result['acceptance']['scientific_status'],'failed',result['acceptance']['failed_gates'],
          'narrowed',fa['narrowed_probes'],'undefined',fa['undefined_probes'],flush=True)
    return row


def execute(output,stage):
    output=Path(output).resolve();config=verify(output);cfg=config['b2_config']
    marker=output/(stage+'_EXECUTION.json')
    if marker.exists():raise FileExistsError('Preserve existing execution; do not overwrite '+str(marker))
    if stage=='holdouts' and not (output/'summary/reference.json').exists():raise ValueError('Revalidate saved B2 first')
    write_json(marker,{'started':datetime.now(timezone.utc).isoformat(),'protocol_sha256':digest(output/'protocol/PROTOCOL.json')})
    started=time.perf_counter();rows=[];errors=[];unsupported=[];source_times=[]
    folders=sorted([* (B2/'development').glob('design_*'),* (B2/'holdout').glob('design_*')]) if stage=='reference' else config['cohort']
    tracemalloc.start();peak=0
    for idx,spec in enumerate(folders):
        name=spec.name if stage=='reference' else spec['fixture']
        try:
            began=time.perf_counter()
            if stage=='reference':fixture=old_fixture(spec);times={'authenticated_loading':time.perf_counter()-began}
            else:fixture,times=new_fixture(output,spec,config)
            if fixture is None:
                unsupported.append(name)
                for epsilon in config['tolerances']:rows.append({'fixture':name,'cohort':'new_parameter','epsilon':epsilon,'disposition':'QUARANTINED_INGRESS','acceptance':{'hard_gate_pass':False,'scientific_status':'HOLD','failed_gates':['native_or_manifold_ingress']}})
                continue
            source,descriptor=source_checks(output,fixture);source_times.append({'fixture':name,**times,**source['times']})
            probes=select_probes(fixture['mask'])
            if stage=='holdouts':
                cache=DescriptorCache(output/'parameter_holdouts'/name/'descriptor_cache',cfg['b1_config']['descriptor_cache_entries_per_fixture'])
                context=context_for(fixture,cfg['b1_config'],cache);risks=prepare_risks(fixture,cfg,context['features'])
                registered=serializable_features(context['features']);write_json(output/'parameter_holdouts'/name/'registered_features.json',registered)
            else:registered=fixture['features']
            for epsilon in config['tolerances']:
                cid=f'epsilon_{epsilon:.2f}'.replace('.','p')
                if stage=='reference':
                    case=spec/cid;qualification=read(case/'qualification.json')
                    authenticate(case/'candidate.wkb',qualification['candidate_sha256'])
                else:
                    case=output/'parameter_holdouts'/name/cid;case.mkdir()
                    t=time.perf_counter();guards=build_guards(risks,epsilon,cfg,len(fixture['mask']))
                    engine=simplify_protected(fixture['baseline'],epsilon,risks,guards,cfg)
                    repeated=simplify_protected(fixture['baseline'],epsilon,risks,guards,cfg)
                    deterministic=engine['geometry'].wkb==repeated['geometry'].wkb
                    del repeated
                    write_json(case/'producer_times.json',{'guards_and_repeated_simplification':time.perf_counter()-t,'engine':engine['timing']})
                    save_wkb(case/'candidate.wkb',engine['geometry']);save_wkb(case/'guard_union.wkb',guards['union'])
                    write_json(case/'guards.json',guard_document(guards));write_json(case/'engine.json',{k:v for k,v in engine.items() if k not in ('geometry','keeps')})
                    qualification,_=qualify(fixture,engine['geometry'],context,risks,guards,engine,cfg,cache)
                    qualification['repeated_construction_identical']=deterministic
                    fixture['construction_deterministic']=fixture['construction_deterministic'] and deterministic
                    write_json(case/'frozen_B2_qualification.json',qualification)
                    del engine,guards
                row=validate_candidate(output,fixture,source,descriptor,case/'candidate.wkb',case/'guard_union.wkb',qualification,
                    epsilon,'B2_reference' if stage=='reference' else 'new_parameter',probes,registered,integration=(idx==0 and epsilon==0))
                rows.append(row)
            del fixture,descriptor,source,probes
            if stage=='holdouts':del cache,context,risks
            gc.collect()
            if not tracemalloc.is_tracing():tracemalloc.start()
            peak=max(peak,tracemalloc.get_traced_memory()[1])
        except Exception:
            failure={'fixture':name,'stage':stage,'traceback':traceback.format_exc()};errors.append(failure)
            write_json(output/'verification'/(name+'_ERROR.json'),failure);print('ERROR',name,failure['traceback'],flush=True)
            if not tracemalloc.is_tracing():tracemalloc.start()
    peak=max(peak,tracemalloc.get_traced_memory()[1]);tracemalloc.stop()
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
    write_json(output/'summary'/(stage+'.json'),{'stage':stage,'rows':rows,'unsupported':unsupported,'errors':errors,
        'elapsed_seconds':time.perf_counter()-started,'peak_traced_bytes':peak,'process_lifetime_peak_rss_bytes':rss,'source_timings':source_times,
        'tracing_caveat':'Frozen native worker starts/stops its own tracing. C restarts at fixture boundaries. Peaks are tracked Python/NumPy allocation observations, not full native memory; RSS lifetime highwater includes GEOS.'})
    print(stage,'complete',len(rows),'records',len(errors),'errors',len(unsupported),'quarantines',flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','reference','holdouts']);p.add_argument('--output-dir',type=Path,default=DEFAULT);args=p.parse_args()
    if args.action=='freeze':freeze(args.output_dir)
    else:execute(args.output_dir,args.action)


if __name__=='__main__':main()
