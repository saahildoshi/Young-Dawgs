"""Registered, isolated v0.5B1 baseline characterization and sensitivity execution."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import traceback
import tracemalloc
import numpy as np
import shapely

from ..reporting import repository_inventory,environment
from ..manifold.contacts import inspect_boundary
from ..planar import rasterize_exact_geometry
from .sources import load_fixture,digest
from .simplification import simplify_diagnostic
from .metrics import complexity,void_partition,raster_comparison
from .distance import BoundaryIndex
from .features import prepare_features,serializable_features,evaluate_features
from .morphology import DescriptorCache
from .analysis import evaluate_candidate
from .records import write_json,save_candidate,threshold_scan

ROOT=Path(__file__).resolve().parents[3]
PROTOCOL='docs/pipeline_v0.5/V0_5B1_PROTOCOL.json'


def verify_code(root,registered):
    changed=[p for p,h in registered['code_sha256'].items() if digest(root/p)!=h]
    if changed:raise ValueError('Registered code/configuration changed; register a new study: '+str(changed))


def register(output,root=ROOT):
    root=Path(root).resolve();output=Path(output).resolve()
    if not output.is_relative_to(root/'experiments/pipeline_v0.5/simplification_sensitivity'):
        raise ValueError('Use a new directory under experiments/pipeline_v0.5/simplification_sensitivity.')
    if output.exists():raise FileExistsError('Existing sensitivity run will not be overwritten.')
    config=json.loads((root/PROTOCOL).read_text());inventory=repository_inventory(root,output)
    fixtures=[load_fixture(root,config,name) for name in config['fixture_ids']]
    output.mkdir(parents=True)
    for name in ('fixtures','candidates','metrics','figures','failures','summary','verification'): (output/name).mkdir()
    sources={p.relative_to(root).as_posix():digest(p) for p in sorted((root/'metamaterial_eval/geometry').rglob('*.py'))}
    for name in (PROTOCOL,'docs/pipeline_v0.5/V0_5B1_PLAN.md','tests/test_simplification_sensitivity.py',
                 'requirements-v0.5.txt','validation/evaluators/evaluator_v1_1.py',
                 'metamaterial_eval/pipeline/resolution_worker.py','metamaterial_eval/pipeline/evaluator.py'):
        sources[name]=digest(root/name)
    for name in sources:
        p=output/'code_snapshot'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/name).read_bytes())
    registered={'config':config,'registered_utc':datetime.now(timezone.utc).isoformat(),
                'code_sha256':sources,'protocol_source_sha256':digest(root/PROTOCOL),
                'fixture_provenance':[f['provenance'] for f in fixtures],
                'primary_configurations':40,'negative_control_configurations':3,
                'production_tolerance_selected':False}
    write_json(output/'protocol.json',registered);write_json(output/'source_inventory.json',inventory)
    write_json(output/'environment.json',environment())
    print('Registered 40 primary candidates and 3 negative controls.',flush=True)
    return registered


def context_for(fixture,config,cache):
    baseline=fixture['baseline'];mask=fixture['mask']
    raster=rasterize_exact_geometry(baseline,len(mask))
    if not np.array_equal(raster,mask):raise ValueError('Saved accepted baseline does not reconstruct canonical mask exactly.')
    features=prepare_features(fixture,config)
    data,provenance=cache.get(raster)
    return {'baseline_complexity':complexity(baseline),
            'baseline_index':BoundaryIndex(baseline,config['boundary_sample_spacing'],config['boundary_query_chunk']),
            'exact_index':BoundaryIndex(fixture['exact'],config['boundary_sample_spacing'],config['boundary_query_chunk']),
            'baseline_void':void_partition(baseline,len(mask)),
            'baseline_raster':raster,'features':features,'baseline_descriptors':data,
            'baseline_descriptor_provenance':provenance}


def characterize(output,root=ROOT):
    root=Path(root).resolve();output=Path(output).resolve();registered=json.loads((output/'protocol.json').read_text())
    verify_code(root,registered);config=registered['config']
    if (output/'baselines.json').exists():raise FileExistsError('Baselines already characterized; do not overwrite.')
    baselines=[];start=time.perf_counter()
    for name in config['fixture_ids']:
        fixture=load_fixture(root,config,name);folder=output/'fixtures'/name;folder.mkdir()
        cache=DescriptorCache(folder/'descriptor_cache',config['descriptor_cache_entries_per_fixture'])
        context=context_for(fixture,config,cache);baseline=fixture['baseline']
        manifold=inspect_boundary(baseline)
        if not manifold['manifold']:raise ValueError('Saved baseline no longer qualifies as manifold: '+name)
        features=evaluate_features(baseline,baseline,context['features'],config,manifold,context['baseline_index'],context['baseline_index'],candidate_void=context['baseline_void'])
        if features.get('any_repair_unresolved'):raise ValueError('Baseline contact analysis does not recover resolved contacts.')
        loops=fixture['exact_document']['loops'];exposed=sum(r['unit_edge_count'] for r in loops);coalesced=sum(len(r['xy'])-1 for r in loops)
        record={'fixture':name,'provenance':fixture['provenance'],'complexity':context['baseline_complexity'],
                'exact_polygon_complexity':complexity(fixture['exact']),
                'original_exposed_vertices':exposed,'exact_collinear_vertices':coalesced,
                'existing_exact_coalescing_reduction_percent':100*(1-coalesced/exposed),
                'registered_manifold_repairs':len(context['features']['repairs']),
                'protected_analysis_neighborhoods':len(context['features']['repairs']),
                'algorithm_protection_applied':False,'ogc_valid':bool(baseline.is_valid),'manifold':manifold,
                'raster':raster_comparison(fixture['mask'],context['baseline_raster']),
                'feature_definitions':serializable_features(context['features']),'baseline_feature_measurements':features,
                'descriptor_provenance':context['baseline_descriptor_provenance']}
        write_json(folder/'baseline.json',record);baselines.append(record)
        print(name,'baseline verified:',record['complexity']['vertices'],'vertices;',record['registered_manifold_repairs'],'repair ROIs',flush=True)
    write_json(output/'baselines.json',{'fixtures':baselines,'characterization_seconds':time.perf_counter()-start})
    return baselines


def candidate_id(epsilon,primary):
    return ('primary_' if primary else 'negative_')+f'epsilon_{epsilon:.2f}'.replace('.','p')


def run(output,root=ROOT):
    root=Path(root).resolve();output=Path(output).resolve();registered=json.loads((output/'protocol.json').read_text())
    verify_code(root,registered);config=registered['config']
    if not (output/'baselines.json').exists():raise ValueError('Characterize and verify all saved baselines before the sweep.')
    if (output/'execution.json').exists():raise FileExistsError('Sensitivity run already started; preserve it and register a fresh run.')
    write_json(output/'execution.json',{'started_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':digest(output/'protocol.json')})
    study_start=time.perf_counter();rows=[];peak=0;fixture_thresholds={};execution_failures=[]
    for name in config['fixture_ids']:
        fixture=load_fixture(root,config,name);folder=output/'fixtures'/name
        cache=DescriptorCache(folder/'descriptor_cache',config['descriptor_cache_entries_per_fixture'])
        context=context_for(fixture,config,cache)
        previous=json.loads((folder/'baseline.json').read_text())
        if previous['feature_definitions']!=serializable_features(context['features']):raise ValueError('Feature definitions changed since baseline characterization.')
        context['baseline_repair_clearances']={r['contact_id']:r['clearance'] for r in previous['baseline_feature_measurements']['repairs']}
        source_bytes=shapely.to_wkb(fixture['baseline'],byte_order=1);exact_bytes=shapely.to_wkb(fixture['exact'],byte_order=1)
        settings=[(e,True,True) for e in config['primary']['tolerances']]
        if name==config['negative_control']['fixture']:
            settings.extend((e,False,False) for e in config['negative_control']['tolerances'])
        fixture_rows=[]
        for epsilon,preserve,primary in settings:
            cid=candidate_id(epsilon,primary);candidate_folder=output/'candidates'/name/cid
            began=time.perf_counter()
            try:
                tracemalloc.start();start=time.perf_counter()
                candidate=simplify_diagnostic(fixture['baseline'],epsilon,preserve_topology=preserve)
                simplification_seconds=time.perf_counter()-start;_,simplification_peak=tracemalloc.get_traced_memory();tracemalloc.stop()
                payload=shapely.to_wkb(candidate,byte_order=1)
                repeated=simplify_diagnostic(fixture['baseline'],epsilon,preserve_topology=preserve)
                deterministic=payload==shapely.to_wkb(repeated,byte_order=1)
                del repeated
                tracemalloc.start()
                report,reconstructed=evaluate_candidate(fixture,candidate,context,config,descriptor_cache=cache)
                _,validation_peak=tracemalloc.get_traced_memory();tracemalloc.stop();peak=max(peak,validation_peak,simplification_peak)
                report.update(fixture=name,epsilon=float(epsilon),method='douglas_peucker',preserve_topology=preserve,
                              study_role='primary' if primary else 'negative_control',
                              input_geometry_sha256=fixture['provenance']['sha256']['manifold'],
                              exact_reference_sha256=fixture['provenance']['sha256']['exact'],
                              deterministic_geometry_bytes=deterministic,
                              simplification_peak_traced_bytes=simplification_peak,validation_peak_traced_bytes=validation_peak,
                              memory_interpretation='Per-stage traced Python/NumPy peak, including lazily populated bounded baseline caches; excludes untracked GEOS-native allocations and prior allocations.')
                report['timing']['simplification_seconds']=simplification_seconds
                report['timing']['candidate_total_seconds_before_saving']=time.perf_counter()-began
                if not deterministic:raise ValueError('Candidate serialization is nondeterministic.')
                if source_bytes!=shapely.to_wkb(fixture['baseline'],byte_order=1) or exact_bytes!=shapely.to_wkb(fixture['exact'],byte_order=1):
                    raise ValueError('Source geometry mutated during simplification.')
                saved=save_candidate(candidate_folder,candidate,report,reconstructed)
                relative=candidate_folder.relative_to(output).as_posix()
                row={'fixture':name,'epsilon':float(epsilon),'study_role':saved['study_role'],
                     'relative_directory':relative,'candidate_sha256':saved['candidate_sha256'],
                     'events':saved['events'],'status':saved['status'],
                     'metrics_file':relative+'/metrics.json','vertices':saved['complexity']['vertices'],
                     'vertex_reduction_percent':saved['vertex_reduction_percent'],
                     'promising_under_strict_available_diagnostics':saved['promising_under_strict_available_diagnostics']}
                rows.append(row);fixture_rows.append(row)
                print(name,cid,':',saved['complexity']['vertices'],'vertices;',','.join(saved['diagnostic_flags']) or 'no observed flags',flush=True)
                del candidate,reconstructed,report,saved
            except Exception:
                if tracemalloc.is_tracing():tracemalloc.stop()
                failure={'fixture':name,'epsilon':epsilon,'study_role':'primary' if primary else 'negative_control',
                         'candidate_id':cid,'status':'FAILED_EXECUTION','traceback':traceback.format_exc()}
                if 'candidate' in locals():
                    retain=output/'failures'/(name+'_'+cid+'.wkb');retain.write_bytes(shapely.to_wkb(candidate,byte_order=1))
                write_json(output/'failures'/(name+'_'+cid+'.json'),failure);execution_failures.append(failure)
                print(name,cid,'FAILED_EXECUTION',flush=True)
        fixture_thresholds[name]=threshold_scan([r for r in fixture_rows if r['study_role']=='primary'])
        write_json(folder/'observed_thresholds.json',fixture_thresholds[name])
        del context,fixture,cache
    initial=json.loads((output/'source_inventory.json').read_text())
    changed=[p for p,h in initial.items() if not (root/p).is_file() or digest(root/p)!=h]
    rss=None
    try:
        import resource
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system()!='Darwin':rss*=1024
    except ImportError:
        pass
    summary={'stage':'v0.5B1','status':'STUDY_EXECUTED_PENDING_REPORT_AND_REGRESSION' if not execution_failures and not changed else 'STUDY_INCOMPLETE',
             'primary_expected':40,'negative_control_expected':3,'primary_completed':sum(r['study_role']=='primary' for r in rows),
             'negative_control_completed':sum(r['study_role']=='negative_control' for r in rows),
             'candidates':rows,'thresholds':fixture_thresholds,'execution_failures':execution_failures,
             'total_sweep_seconds':time.perf_counter()-study_start,'peak_traced_candidate_bytes':peak,
             'process_lifetime_peak_rss_bytes':rss,'rss_interpretation':'Process lifetime high-water RSS, including imports/baseline caches; not per-candidate incremental memory.',
             'existing_files_unchanged':not changed,'changed_existing_files':changed,'production_tolerance_selected':False,
             'full_v0_5B_acceptance':False,'v0_5B2_implemented':False,'physical_mesh_mechanical_manufacturing':'UNQUALIFIED'}
    write_json(output/'summary/SIMPLIFICATION_SENSITIVITY.json',summary)
    print('Sweep complete:',len(rows),'candidates;',len(execution_failures),'execution failures',flush=True)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    for name in ('register','characterize','run','report'):
        p=sub.add_parser(name);p.add_argument('--output-dir',required=True)
    args=parser.parse_args()
    if args.action=='register':register(args.output_dir)
    elif args.action=='characterize':characterize(args.output_dir)
    elif args.action=='run':run(args.output_dir)
    else:
        from .reporting import report
        report(Path(args.output_dir))


if __name__=='__main__':main()
