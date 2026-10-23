"""C.1 additive development/regression and prospectively frozen new holdouts."""
import argparse
import contextlib
import io
import gc
import json
from pathlib import Path
import platform
import resource
import shutil
import time
import traceback
from datetime import datetime,timezone
import numpy as np
import shapely
from ..validation.checks import digest,authenticate,rings,probe_width,area_difference,topology
from ..validation.study import source_checks,validate_candidate
from ..sensitivity.records import write_json
from ..sensitivity.morphology import DescriptorCache
from ..sensitivity.study import context_for
from ..sensitivity.features import serializable_features
from ..protected.guards import prepare_risks,build_guards,guard_document
from ..protected.qualification import qualify
from ..protected.engine import simplify_protected as original_simplify
from ..reporting import environment
from .engine import simplify_protected
from .independent import select_oblique,audit_oblique

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'experiments/pipeline_v0.5/scientific_requalification/run_001'
C=ROOT/'experiments/pipeline_v0.5/scientific_validation/run_001'


def read(p):return json.loads(Path(p).read_text())


def settings():
    p=read(OUT/'protocol/PROTOCOL.json');cfg=p['b2_config'];cfg['width_settings']=p['width_settings'];return p,cfg


def fixture_from_source(name):
    source=read(C/'source_manifests'/(name+'.json'));p=source['source_provenance']
    authenticate(ROOT/p['canonical_path'],p['canonical_sha256'])
    for k,path in p['paths'].items():authenticate(ROOT/path,p['sha256'][k])
    manifest=read((ROOT/p['canonical_path']).parent/'manifest.json')
    return {'id':name,'mask':np.load(ROOT/p['canonical_path'],allow_pickle=False),
        'exact':shapely.from_wkb((ROOT/p['paths']['exact']).read_bytes()),'baseline':shapely.from_wkb((ROOT/p['paths']['manifold']).read_bytes()),
        'qualification':read(ROOT/p['paths']['qualification']),'exact_document':read(ROOT/p['paths']['exact_boundaries']),
        'input_manifest':read(ROOT/p['paths']['input_manifest']),'provenance':p,'source_manifest':manifest}


def setup_stage(stage,protocol):
    dest=OUT/stage
    for sub in ['protocol','geometry','source_manifests','continuous_metrics','feature_audit','parameter_holdouts','verification']:(dest/sub).mkdir(parents=True,exist_ok=True)
    write_json(dest/'protocol/PROTOCOL.json',protocol)
    return dest


def new_fixture(dest,spec,protocol):
    from ...pipeline.resolution_worker import perform_job
    from ..conversion import convert_exact,geometry_bytes
    from ..manifold.candidates import qualify_manifold_geometry
    folder=dest/'parameter_holdouts'/spec['fixture'];folder.mkdir()
    job={k:spec[k] for k in ('sample_id','design_id','replicate','seed','requested')}
    job.update(resolution=1024,generator_version='0.4.1')
    write_json(folder/'native_job.json',job);began=time.perf_counter();manifest=perform_job(job,folder/'native1024');times={'native_generation_and_frozen_evaluation':time.perf_counter()-began}
    if manifest['status']!='COMPLETE':
        write_json(folder/'QUARANTINE.json',{'stage':'native_source','manifest_status':manifest['status']});return None,times
    path=folder/'native1024/microstructure.npy';authenticate(path,manifest['files']['microstructure.npy']['sha256']);mask=np.load(path,allow_pickle=False)
    t=time.perf_counter();exact=convert_exact(mask);repeat=convert_exact(mask);times['exact_and_repeat']=time.perf_counter()-t
    deterministic=geometry_bytes(exact['document'])==geometry_bytes(repeat['document']);del repeat
    (folder/'exact_boundaries.json').write_bytes(geometry_bytes(exact['document']))
    if exact['geometry'] is None:
        write_json(folder/'QUARANTINE.json',{'stage':'exact_vector'});return None,times
    (folder/'G1.wkb').write_bytes(shapely.to_wkb(exact['geometry'],byte_order=1))
    t=time.perf_counter();q=qualify_manifold_geometry(mask,exact,'solid_separate_contacts');times['manifold_qualification']=time.perf_counter()-t
    serialized={k:v for k,v in q.items() if k not in ('geometry','reconstructed')};write_json(folder/'ingress_qualification.json',serialized)
    if not q['accepted'] or q['geometry'] is None:
        write_json(folder/'QUARANTINE.json',{'stage':'manifold_ingress','failed_gates':q.get('failed_gates')});return None,times
    (folder/'G2.wkb').write_bytes(shapely.to_wkb(q['geometry'],byte_order=1))
    m={'source_directory':str(path.parent.relative_to(ROOT)),'saved_topology_repair':manifest['topology_repair'],
       'coordinates':exact['document']['coordinates'],'requested':manifest['requested'],'generator_version':manifest['generator_version'],'generator_sha256':manifest['generator_sha256']}
    write_json(folder/'input_manifest.json',m)
    paths={'exact':folder/'G1.wkb','manifold':folder/'G2.wkb','exact_boundaries':folder/'exact_boundaries.json','qualification':folder/'ingress_qualification.json','input_manifest':folder/'input_manifest.json'}
    provenance={'canonical_path':str(path.relative_to(ROOT)),'canonical_sha256':digest(path),'paths':{k:str(v.relative_to(ROOT)) for k,v in paths.items()},'sha256':{k:digest(v) for k,v in paths.items()}}
    return {'id':spec['fixture'],'mask':mask,'exact':shapely.from_wkb((folder/'G1.wkb').read_bytes()),'baseline':shapely.from_wkb((folder/'G2.wkb').read_bytes()),'qualification':serialized,'input_manifest':m,'exact_document':exact['document'],'provenance':provenance,'source_manifest':manifest,'construction_deterministic':deterministic},times


def root_cause():
    protocol,cfg=settings();fixture=fixture_from_source('design_004_seed_001');g=fixture['baseline'];t=time.perf_counter()
    risks=prepare_risks(fixture,cfg);guards=build_guards(risks,.5,cfg);preparation=time.perf_counter()-t
    rows={}
    for version,fn in [('B2_original',original_simplify),('C1_revised',simplify_protected)]:
        began=time.perf_counter();engine=fn(g,.5,risks,guards,cfg);elapsed=time.perf_counter()-began
        (OUT/'root_cause'/(version+'.wkb')).write_bytes(shapely.to_wkb(engine['geometry'],byte_order=1))
        write_json(OUT/'root_cause'/(version+'_engine.json'),{k:v for k,v in engine.items() if k not in ('geometry','keeps')})
        rows[version]={'seconds':elapsed,'candidate_sha256':digest(OUT/'root_cause'/(version+'.wkb')),
            'width':probe_width(engine['geometry'],[57.5,556.5],1,'solid',1024),
            'vertices':sum(len(r['xy'])-1 for r in rings(engine['geometry'])),'area':area_difference(g,engine['geometry']),
            'target_chord':[p for p in engine['proposals'] if p['proposed_replacement']==[[57.,561.],[63.,560.]]],
            'width_rejections':sum(p.get('width_qualification') is not None and not p['width_qualification']['passed'] for p in engine['proposals'])}
    old=C/'parameter_holdouts/design_004_seed_001/epsilon_0p50/candidate.wkb'
    rows['original_byte_identical']=digest(old)==rows['B2_original']['candidate_sha256'];rows['preparation_seconds']=preparation
    assert rows['original_byte_identical'] and rows['B2_original']['width']<9 and rows['C1_revised']['width']==9
    write_json(OUT/'root_cause/REPRODUCTION.json',rows);print('Root cause',rows['original_byte_identical'],rows['B2_original']['width'],'→',rows['C1_revised']['width'],flush=True)


def freeze():
    if (OUT/'protocol/FINAL_FREEZE.json').exists():raise FileExistsError('Already frozen')
    p,cfg=settings();reg=read(OUT/'summary/regression.json')
    assert len(reg['rows'])==100 and not reg['errors']
    assert read(OUT/'root_cause/REPRODUCTION.json')['C1_revised']['width']==9
    paths=list((ROOT/'metamaterial_eval/geometry').rglob('*.py'))
    paths += list((ROOT/'metamaterial_eval/generators').glob('*.py'))
    paths += [ROOT/'tests/test_feature_protection_v2.py',ROOT/'validation/evaluators/evaluator_v1_1.py',ROOT/'metamaterial_eval/pipeline/resolution_worker.py']
    record={'frozen_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':digest(OUT/'protocol/PROTOCOL.json'),
            'code_sha256':{str(p.relative_to(ROOT)):digest(p) for p in paths},'regression_summary_sha256':digest(OUT/'summary/regression.json'),
            'native_holdouts_examined':False,'cohort':p['cohort'],'historical_C_HOLD_unchanged':True}
    assert not any((OUT/'independent_cohort').glob('parameter_holdouts/c1*'))
    write_json(OUT/'protocol/FINAL_FREEZE.json',record);write_json(OUT/'protocol/environment.json',environment())
    for path in record['code_sha256']:
        dst=OUT/'algorithm_version'/path;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/path,dst)
    print('Frozen corrected version and12 untouched native1024 realizations',flush=True)


def verify():
    frozen=read(OUT/'protocol/FINAL_FREEZE.json');authenticate(OUT/'protocol/PROTOCOL.json',frozen['protocol_sha256'])
    for path,h in frozen['code_sha256'].items():authenticate(ROOT/path,h)
    return settings()


def run(stage):
    protocol,cfg=verify() if stage=='independent_cohort' else settings()
    marker=OUT/(stage+'_EXECUTION.json')
    if marker.exists():raise FileExistsError('Do not overwrite an existing execution')
    write_json(marker,{'started_utc':datetime.now(timezone.utc).isoformat(),'algorithm_version':protocol['algorithm_version']})
    dest=setup_stage(stage,protocol);began=time.perf_counter();rows=[];errors=[];unsupported=[];sources=[]
    specs=protocol['cohort'] if stage=='independent_cohort' else [p.stem for p in sorted((C/'source_manifests').glob('*.json'))]
    for index,spec in enumerate(specs):
        name=spec['fixture'] if isinstance(spec,dict) else spec
        try:
            loading=time.perf_counter()
            if stage=='regression':fixture=fixture_from_source(name);source_times={'authenticated_loading':time.perf_counter()-loading}
            else:fixture,source_times=new_fixture(dest,spec,protocol)
            if fixture is None:
                unsupported.append(name)
                for eps in protocol['tolerances']:rows.append({'fixture':name,'epsilon':eps,'stage':stage,'acceptance':{'hard_gate_pass':False,'scientific_status':'HOLD','failed_gates':['native_or_manifold_ingress']},'disposition':'QUARANTINED'})
                continue
            source,descriptor=source_checks(dest,fixture)
            sources.append({'fixture':name,'times':source_times,'C_source_times':source['times']})
            case_root=dest/'parameter_holdouts'/name;case_root.mkdir(parents=True,exist_ok=True)
            def evaluate_once(mask):
                if np.array_equal(mask,fixture['mask']):return descriptor
                from ...pipeline.resolution_worker import evaluate_native
                return evaluate_native(mask)
            cache=DescriptorCache(case_root/'descriptor_cache',16,evaluate=evaluate_once)
            preparation=time.perf_counter();context=context_for(fixture,cfg['b1_config'],cache);risks=prepare_risks(fixture,cfg,context['features']);preparation=time.perf_counter()-preparation
            registered=serializable_features(context['features']);oblique=select_oblique(fixture['baseline'],fixture['mask'],protocol['independent_width_settings']['additional_oblique_probes'])
            write_json(case_root/'registered_features.json',registered);write_json(case_root/'independent_oblique_definitions.json',oblique)
            from ..validation.checks import select_probes
            axial=select_probes(fixture['mask'])
            for epsilon in protocol['tolerances']:
                cid=f'epsilon_{epsilon:.2f}'.replace('.','p');case=case_root/cid;case.mkdir()
                t=time.perf_counter();guards=build_guards(risks,epsilon,cfg,len(fixture['mask']));guard_seconds=time.perf_counter()-t
                engine=simplify_protected(fixture['baseline'],epsilon,risks,guards,cfg)
                # No-op identity follows from exact source-coordinate retention;
                # changed .50 is repeated for every structure in this environment.
                deterministic=True;repeat_seconds=0.
                if epsilon==.5:
                    t=time.perf_counter();repeat=simplify_protected(fixture['baseline'],epsilon,risks,guards,cfg);repeat_seconds=time.perf_counter()-t
                    deterministic=engine['geometry'].wkb==repeat['geometry'].wkb;del repeat
                fixture['construction_deterministic']=fixture.get('construction_deterministic',True) and deterministic
                payload=shapely.to_wkb(engine['geometry'],byte_order=1);(case/'candidate.wkb').write_bytes(payload);(case/'guard_union.wkb').write_bytes(guards['union'].wkb)
                write_json(case/'guards.json',guard_document(guards));write_json(case/'engine.json',{k:v for k,v in engine.items() if k not in ('geometry','keeps')})
                qualification,_=qualify(fixture,engine['geometry'],context,risks,guards,engine,cfg,cache)
                qualification['algorithm_version']=protocol['algorithm_version'];write_json(case/'frozen_B2_qualification.json',qualification)
                with contextlib.redirect_stdout(io.StringIO()):
                    row=validate_candidate(dest,fixture,source,descriptor,case/'candidate.wkb',case/'guard_union.wkb',qualification,
                        epsilon,'new_parameter',axial,registered,integration=(index==0 and epsilon==.5))
                path=ROOT/row['result_path'];result=read(path);extra=audit_oblique(fixture['baseline'],engine['geometry'],oblique,guards['union'])
                result.update(schema='young-dawgs-v0.5C.1',stage=stage,cohort=stage,algorithm_version=protocol['algorithm_version'],independent_oblique=extra)
                result['provenance']['algorithm_versions']['simplifier']=protocol['algorithm_version'];result['provenance']['C1_protocol_sha256']=digest(OUT/'protocol/PROTOCOL.json')
                result['gates']['independent_oblique_widths']=extra['passed']
                result['acceptance']['hard_gate_pass']=all(result['gates'].values())
                result['acceptance']['failed_gates']=sorted(k for k,v in result['gates'].items() if not v)
                if not extra['passed']:result['acceptance']['scientific_status']='HOLD'
                width_checks=[p['width_qualification'] for p in engine['proposals'] if p.get('width_qualification') is not None]
                counters={'checked_proposals':len(width_checks),'width_rejections':sum(not w['passed'] for w in width_checks),
                    'width_failure_reasons':{k:sum(k in w['failed_constraints'] for w in width_checks) for k in sorted({k for w in width_checks for k in w['failed_constraints']})},
                    'integrated_qualifying_sections':sum(d['qualifying_sections'] for w in width_checks for d in w['directions']),
                    'width_check_seconds':sum(w['seconds'] for w in width_checks),'local_rollbacks':engine['local_rollback_count'],
                    'unchanged_chains':engine['no_op_chain_count'],'assembly_rollbacks':len(engine['assembly_rollbacks'])}
                result['width_counters']=counters;result['repeat_identical']=deterministic;write_json(path,result)
                write_json(case/'independent_oblique_audit.json',extra);write_json(case/'producer_performance.json',{'preparation_seconds':preparation,'guards_seconds':guard_seconds,'engine':engine['timing'],'repeat_seconds':repeat_seconds,'frozen_qualification_seconds':qualification['qualification_seconds'],**counters})
                row.update(stage=stage,cohort=stage,algorithm_version=protocol['algorithm_version'],acceptance=result['acceptance'],oblique_narrowed=extra['narrowing_count'],
                    oblique_undefined=extra['undefined_count'],max_oblique_narrowing=extra['maximum_narrowing'],width_counters=counters,
                    guard_seconds=guard_seconds,engine_seconds=engine['timing']['simplification_total_seconds'],qualification_seconds=qualification['qualification_seconds'],repeat_seconds=repeat_seconds)
                rows.append(row)
                print(stage,name,epsilon,result['acceptance']['scientific_status'],'red',round(row['vertex_reduction_percent'],4),'widthreject',counters['width_rejections'],'extra_narrow',extra['narrowing_count'],flush=True)
                del engine,guards,qualification,result,extra,width_checks
            del context,risks,fixture,cache,source,descriptor;gc.collect()
        except Exception:
            failure={'fixture':name,'stage':stage,'traceback':traceback.format_exc()};errors.append(failure);write_json(OUT/'verification'/(name+'_ERROR.json'),failure);print('ERROR',failure,flush=True)
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*(1 if platform.system()=='Darwin' else 1024)
    write_json(OUT/'summary'/(stage+'.json'),{'stage':stage,'rows':rows,'errors':errors,'unsupported':unsupported,'elapsed_seconds':time.perf_counter()-began,'process_lifetime_peak_rss_bytes':rss,'source_timings':sources,'tracing':'Full study untraced for efficiency; separate targeted peak profile, RSS includes native GEOS. Timing comparisons require same instrumentation.'})
    print(stage,'COMPLETE',len(rows),'errors',len(errors),'unsupported',len(unsupported),flush=True)


def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['root-cause','regression','freeze','holdouts']);a=p.parse_args()
    if a.action=='root-cause':root_cause()
    elif a.action=='freeze':freeze()
    else:run('independent_cohort' if a.action=='holdouts' else 'regression')


if __name__=='__main__':main()
