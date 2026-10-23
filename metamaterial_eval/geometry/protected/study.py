"""Registered development, frozen independent holdouts and additive reporting."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import time
import traceback
import tracemalloc
import numpy as np
import shapely
from ..reporting import repository_inventory, environment
from ..planar import rasterize_exact_geometry
from ..sensitivity.study import context_for
from ..sensitivity.records import write_json
from ..sensitivity.sources import digest
from ..sensitivity.morphology import DescriptorCache
from ..sensitivity.metrics import complexity
from ..sensitivity.features import serializable_features
from .settings import ROOT, PROTOCOL, settings
from .sources import development,holdout
from .guards import prepare_risks,build_guards,guard_document
from .engine import simplify_protected
from .qualification import qualify


def code_hashes():
    paths = sorted((ROOT/'metamaterial_eval/geometry').rglob('*.py'))
    paths += [ROOT/PROTOCOL,ROOT/'docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_ARCHITECTURE.md',
              ROOT/'docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_PROTOCOL.md',ROOT/'tests/test_protected_simplification.py',
              ROOT/'validation/evaluators/evaluator_v1_1.py',ROOT/'requirements-v0.5.txt',
              ROOT/'metamaterial_eval/pipeline/evaluator.py',ROOT/'metamaterial_eval/pipeline/resolution_worker.py']
    return {p.relative_to(ROOT).as_posix():digest(p) for p in paths}


def register(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'experiments/pipeline_v0.5/protected_simplification'):
        raise ValueError('Use a new run under experiments/pipeline_v0.5/protected_simplification.')
    if output.exists(): raise FileExistsError('Existing B2 study will not be overwritten.')
    config = settings(); inventory = repository_inventory(ROOT,output)
    for source in config['sources']:
        if digest(ROOT/source['manifest'])!=source['manifest_sha256'] or digest((ROOT/source['manifest']).parent/'microstructure.npy')!=source['npy_sha256']:
            raise ValueError('Prospectively registered source changed.')
    for name in config['development']: development(ROOT,config,name)
    output.mkdir(parents=True)
    for name in ('sources','development','holdout','figures','summary','verification','code_snapshot'):
        (output/name).mkdir()
    registered = {'config':config,'registered_utc':datetime.now(timezone.utc).isoformat(),'code_sha256':code_hashes()}
    write_json(output/'protocol.json',registered);write_json(output/'source_inventory.json',inventory)
    write_json(output/'environment.json',environment())
    for p in registered['code_sha256']:
        target = output/'code_snapshot'/p;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,target)
    for src,name in [('/tmp/yd-b2-initial.json','SESSION_INITIAL_INVENTORY.json'),('/tmp/yd-b2-initial-git.txt','SESSION_INITIAL_GIT_STATUS.txt')]:
        if Path(src).exists():shutil.copyfile(src,output/'verification'/name)
    print('Registered 25 development + 25 reserved holdout configurations.',flush=True)


def verify_code(output):
    registered = json.loads((output/'protocol.json').read_text())
    if registered['code_sha256']!=code_hashes():
        raise ValueError('Registered code/config changed. Preserve this run and register another; never tune consumed holdouts.')
    return registered['config']


def freeze(output):
    output = Path(output).resolve();config = verify_code(output)
    if (output/'HOLDOUT_FREEZE.json').exists():raise FileExistsError('Independent holdout freeze already exists.')
    dev = json.loads((output/'summary/development.json').read_text())
    if len(dev['candidates'])!=25 or dev['internal_errors']:
        raise ValueError('Complete development and fix internal errors before reserving final implementation.')
    record = {'frozen_utc':datetime.now(timezone.utc).isoformat(),'code_sha256':code_hashes(),
              'protocol_sha256':digest(output/'protocol.json'),'development_summary_sha256':digest(output/'summary/development.json'),
              'reserved_holdouts':config['holdouts'],'no_holdout_geometry_examined_in_this_run':not any((output/'holdout').iterdir()) and not any((output/'sources').iterdir())}
    if not record['no_holdout_geometry_examined_in_this_run']:raise ValueError('Holdout independence was already consumed.')
    write_json(output/'HOLDOUT_FREEZE.json',record)
    print('Final implementation/configuration frozen before holdout ingress and evaluation.',flush=True)


def fallback_engine(engine,risks):
    result = dict(engine);result['keeps']=[np.ones(len(x),dtype=bool) for x in risks['model'].xy]
    result['proposals']=[{**p,'applied':False} for p in engine['proposals']]
    result['certified_boundary_displacement_upper']=0.
    result['simplified_chain_count']=0;result['no_op_chain_count']=len(engine['chains'])
    result['chains']=[{**c,'no_op':True,'kept_vertex_indices':c['original_vertex_indices']} for c in engine['chains']]
    return result


def _save_geometry(folder,name,geometry):
    payload = shapely.to_wkb(geometry,byte_order=1);(folder/name).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def run(output,stage):
    output = Path(output).resolve();config = verify_code(output)
    if stage=='holdout':
        frozen = json.loads((output/'HOLDOUT_FREEZE.json').read_text())
        if frozen['code_sha256']!=code_hashes() or frozen['protocol_sha256']!=digest(output/'protocol.json'):
            raise ValueError('Independent holdout code/configuration freeze mismatch.')
    marker = output/(stage+'_execution.json')
    if marker.exists():raise FileExistsError('Stage already started; preserve it and use a new run.')
    write_json(marker,{'started_utc':datetime.now(timezone.utc).isoformat(),'code_sha256':code_hashes()})
    start = time.perf_counter(); rows = []; errors = []; ingress_failures = []; peak = 0
    fixture_ids = config['development'] if stage=='development' else config['holdouts']
    for name in fixture_ids:
        began = time.perf_counter();fixture = development(ROOT,config,name) if stage=='development' else holdout(ROOT,output,config,name)
        if fixture is None:
            ingress_failures.append(name)
            for epsilon in config['tolerances']:
                rows.append({'fixture':name,'epsilon':epsilon,'stage':stage,'disposition':'UNSUPPORTED_INPUT','reason':'Frozen source ingress rejected; retained without replacement.'})
            continue
        folder = output/stage/name;folder.mkdir(exist_ok=False)
        cache = DescriptorCache(folder/'descriptor_cache',config['b1_config']['descriptor_cache_entries_per_fixture'])
        context = context_for(fixture,config['b1_config'],cache)
        risks = prepare_risks(fixture,config,context['features'])
        source_wkb = shapely.to_wkb(fixture['baseline'],byte_order=1);source_exact = shapely.to_wkb(fixture['exact'],byte_order=1)
        baseline = {'fixture':name,'stage':stage,'provenance':fixture['provenance'],'complexity':complexity(fixture['baseline']),
                    'registered_features':serializable_features(context['features']),
                    'dense_risk_features':risks['dense'],'proximity_risks':risks['proximity'],
                    'feature_detection_seconds':risks['feature_detection_seconds'],'preparation_seconds':time.perf_counter()-began}
        write_json(folder/'baseline.json',baseline)
        for epsilon in config['tolerances']:
            cid = f'epsilon_{epsilon:.2f}'.replace('.','p');case = folder/cid;case.mkdir()
            try:
                tracemalloc.start();began = time.perf_counter()
                guards = build_guards(risks,epsilon,config,len(fixture['mask']))
                engine = simplify_protected(fixture['baseline'],epsilon,risks,guards,config)
                if engine['geometry'] is None:raise ValueError(engine.get('reason','Unsupported input'))
                raw = engine['geometry'];repeated = simplify_protected(fixture['baseline'],epsilon,risks,guards,config)
                deterministic = shapely.to_wkb(raw,byte_order=1)==shapely.to_wkb(repeated['geometry'],byte_order=1)
                del repeated
                if not deterministic:raise ValueError('Repeated candidate WKB mismatch.')
                raw_report,raw_raster = qualify(fixture,raw,context,risks,guards,engine,config,cache)
                write_json(case/'raw_qualification.json',raw_report)
                raw_hash = _save_geometry(case,'raw_candidate.wkb',raw)
                global_rollback = not raw_report['accepted_geometric_screen']
                final_engine = engine;candidate = raw;final_report = raw_report;raster = raw_raster
                if global_rollback:
                    write_json(case/'GLOBAL_ROLLBACK.json',{'failed_constraints':raw_report['failed_constraints'],
                        'original_input_sha256':fixture['provenance']['sha256']['manifold'],
                        'rejected_candidate_sha256':raw_hash,'policy':'Restore all remaining modified source chains once; no further trial.',
                        'restored_chains':[c['chain_id'] for c in engine['chains'] if not c['no_op']], 'further_attempt':False})
                    candidate = shapely.from_wkb(source_wkb);final_engine = fallback_engine(engine,risks)
                    final_report,raster = qualify(fixture,candidate,context,risks,guards,final_engine,config,cache)
                    final_report['fallback_after_rejected_raw']=True
                _,traced = tracemalloc.get_traced_memory();tracemalloc.stop();peak=max(peak,traced)
                # Persisted output is independently reloaded and reconstructed.
                candidate_hash = _save_geometry(case,'candidate.wkb',candidate)
                loaded = shapely.from_wkb((case/'candidate.wkb').read_bytes())
                disk_raster = rasterize_exact_geometry(loaded,len(fixture['mask']))
                serialization_pass = raster is not None and np.array_equal(disk_raster,raster)
                if not serialization_pass:raise ValueError('Persisted candidate raster does not reproduce recorded raster.')
                np.save(case/'reconstructed.npy',disk_raster,allow_pickle=False)
                raster_hash = digest(case/'reconstructed.npy')
                final_report.update(candidate_sha256=candidate_hash,raster_sha256=raster_hash,serialized_reconstruction_pass=True,
                    repeated_raw_WKB_deterministic=deterministic,source_provenance=fixture['provenance'],epsilon=epsilon,
                    algorithm_version=config['algorithm_version'],guard_settings=config['guards'],limits=config['limits'])
                write_json(case/'qualification.json',final_report)
                write_json(case/'guards.json',guard_document(guards))
                write_json(case/'engine.json',{k:v for k,v in engine.items() if k not in ('geometry','keeps')})
                (case/'guard_union.wkb').write_bytes(guards['union'].wkb)
                metrics = final_report['metrics'];stats=metrics['complexity']
                row = {'fixture':name,'stage':stage,'epsilon':epsilon,'relative_directory':case.relative_to(output).as_posix(),
                    'disposition':final_report['disposition'],'raw_disposition':raw_report['disposition'],'global_rollback':global_rollback,
                    'vertices':stats['vertices'],'baseline_vertices':baseline['complexity']['vertices'],
                    'vertex_reduction_percent':metrics['vertex_reduction_percent'],'candidate_sha256':candidate_hash,
                    'guard_count':len(guards['records']),'protected_vertices':engine['protected_vertex_count'],
                    'protected_segments':engine['protected_segment_count'],'protected_chains':engine['protected_chain_count'],
                    'proposed_chords':len(engine['proposals']),
                    'rejected_chords':engine['rejected_chord_count'],'local_rollbacks':engine['local_rollback_count'],
                    'simplified_chains':final_engine['simplified_chain_count'],'no_op_chains':final_engine['no_op_chain_count'],
                    'guard_construction_seconds':guards['construction_seconds'], 'engine_timing':engine['timing'],
                    'raw_qualification_seconds':raw_report['qualification_seconds'],'final_qualification_seconds':final_report['qualification_seconds'],
                    'total_seconds':time.perf_counter()-began,'peak_traced_bytes':traced,
                    'added_area':metrics['area_from_manifold']['added_solid_area'],'removed_area':metrics['area_from_manifold']['removed_solid_area'],
                    'symmetric_area':metrics['area_from_manifold']['symmetric_difference_area'],
                    'boundary_measured_lower':metrics['distance_from_manifold']['measured_hausdorff_lower'],
                    'boundary_sampled_upper':metrics['distance_from_manifold']['continuous_hausdorff_upper'],
                    'boundary_certified_upper':final_report['certified_boundary_displacement_upper'],
                    'raster_xor':metrics['raster_from_canonical']['xor_pixels'],'failed_constraints':final_report['failed_constraints']}
                if source_wkb!=shapely.to_wkb(fixture['baseline'],byte_order=1) or source_exact!=shapely.to_wkb(fixture['exact'],byte_order=1):
                    raise ValueError('Source geometry mutated.')
                write_json(case/'result.json',row);rows.append(row)
                print(stage,name,epsilon,final_report['disposition'],f"{metrics['vertex_reduction_percent']:.3f}% reduction; {engine['rejected_chord_count']} rejected chords; global rollback={global_rollback}",flush=True)
                del engine,final_engine,guards,raw_report,final_report,raw_raster,raw,candidate,raster,loaded,disk_raster,metrics
            except Exception:
                if tracemalloc.is_tracing():tracemalloc.stop()
                failure = {'fixture':name,'stage':stage,'epsilon':epsilon,'disposition':'INTERNAL_ALGORITHM_ERROR','traceback':traceback.format_exc()}
                write_json(case/'INTERNAL_ALGORITHM_ERROR.json',failure);rows.append(failure);errors.append(failure)
                print(stage,name,epsilon,'INTERNAL_ALGORITHM_ERROR',flush=True)
        del context,risks,fixture,cache
    rss = None
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system()!='Darwin':rss*=1024
    except ImportError:pass
    summary = {'stage':stage,'candidates':rows,'expected':25,'internal_errors':errors,'unsupported_ingress':ingress_failures,
               'elapsed_seconds':time.perf_counter()-start,'peak_traced_bytes':peak,'process_lifetime_peak_rss_bytes':rss,
               'physical_or_general_scientific_fidelity':'UNQUALIFIED','production_policy_selected':False}
    write_json(output/'summary'/(stage+'.json'),summary)
    print(stage,'complete:',len(rows),'records;',len(errors),'internal errors;',len(ingress_failures),'unsupported ingress',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['register','development','freeze','holdout','report'])
    parser.add_argument('--output-dir',required=True);args=parser.parse_args();output=Path(args.output_dir).resolve()
    if args.action=='register':register(output)
    elif args.action=='freeze':freeze(output)
    elif args.action=='report':
        from .reporting import report
        report(output)
    else:run(output,args.action)


if __name__=='__main__':main()
