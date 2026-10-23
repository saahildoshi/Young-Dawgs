"""Register and execute isolated v0.5A.1 manifold-qualification experiments."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
import tracemalloc

import numpy as np
import shapely

from .. import convert_exact, load_binary_reference
from ..conversion import geometry_bytes
from ..inputs import sha256_file
from ..planar import rasterize_exact_geometry
from ..reporting import repository_inventory, environment
from .contacts import classify_contacts
from .candidates import CandidateSettings, qualify_manifold_geometry
from .figures import contact_figures, candidate_figures
from .morphology import compare_frozen

ROOT=Path(__file__).resolve().parents[3]
SELECTED=[(0,0,'primary representative; largest saved pore scale'),
          (9,1,'saved repaired-boundary stress fixture; no repair recomputation'),
          (1,0,'minimum saved requested strut scale'),
          (2,0,'maximum saved requested strut scale and minimum pore scale'),
          (5,0,'registered envelope-center design from prior convergence studies')]
POLICIES=['preserve_exact','solid_separate_pores','solid_separate_contacts','void_side_probe']


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def profile(function):
    tracemalloc.start();start=time.perf_counter()
    try:
        result=function();elapsed=time.perf_counter()-start
        _,peak=tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return result,{'seconds':elapsed,'peak_traced_bytes':peak,
                   'memory_definition':'Peak tracked Python/NumPy allocations for this stage; untracked GEOS-native memory and prior allocations are excluded.'}


def prepare(output,root=ROOT):
    root=Path(root).resolve();output=Path(output).resolve()
    if not output.is_relative_to(root/'experiments/pipeline_v0.5/manifold_qualification'):
        raise ValueError('Use a new output under experiments/pipeline_v0.5/manifold_qualification.')
    if output.exists():raise FileExistsError('Existing study directory will not be overwritten.')
    before=repository_inventory(root,output)
    selected=[]
    for design,seed,reason in SELECTED:
        source=root/f'experiments/pipeline_v0.4.1/resolution_validation/design_{design:03d}/seed_{seed:03d}/1024'
        m=json.loads((source/'manifest.json').read_text())
        for name in ('microstructure.npy','microstructure.png'):
            if sha256_file(source/name)!=m['files'][name]['sha256']:
                raise ValueError('Original source manifest hash mismatch: '+str(source/name))
        selected.append({'design':design,'seed':seed,'selection_reason':reason,
                         'source_directory':source.relative_to(root).as_posix(),
                         'input_sha256':sha256_file(source/'microstructure.npy'),
                         'manifest_sha256':sha256_file(source/'manifest.json'),
                         'requested':m['requested']})
    output.mkdir(parents=True)
    write_json(output/'preservation_before.json',before)
    write_json(output/'environment.json',environment())
    sources={p.relative_to(root).as_posix():sha256_file(p) for p in sorted((root/'metamaterial_eval/geometry').rglob('*.py'))}
    for name in ('tests/test_geometry_exact.py','tests/test_manifold_qualification.py',
                 'validation/evaluators/evaluator_v1_1.py','requirements-v0.5.txt',
                 'metamaterial_eval/pipeline/evaluator.py','metamaterial_eval/pipeline/resolution_worker.py',
                 'metamaterial_eval/pipeline/config.py','docs/pipeline_v0.5/V0_5A_1_PLAN.md'):
        sources[name]=sha256_file(root/name)
    for name in sources:
        p=output/'code_snapshot'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((root/name).read_bytes())
    protocol={'schema':'young-dawgs-manifold-study-v0.5A.1','registered_utc':datetime.now(timezone.utc).isoformat(),
              'fixtures':selected,'policies':POLICIES,'settings':asdict(CandidateSettings()),'source_sha256':sources,
              'default_policy':'preserve_exact','selected_candidate_policy':'solid_separate_contacts',
              'scientific_scope':'Optional local candidates within the tested contact classes; exact v0.5A HOLD unchanged.',
              'acceptance':{'required_fixtures':len(selected),'selected_policy_all_accepted':True,
                            'exact_fidelity_all_pass':True,'classification_all_pass':True,
                            'raster_descriptors_exact':True,'full_regression_required':True,
                            'physical_feature_qualification':'UNQUALIFIED'}}
    write_json(output/'protocol.json',protocol)
    print('Registered',len(selected),'fixtures',flush=True)
    return protocol


def _serialized_result(result):
    return {k:v for k,v in result.items() if k not in ('geometry','reconstructed')}


def run_fixture(root,output,fixture,settings):
    identifier=f"design_{fixture['design']:03d}_seed_{fixture['seed']:03d}"
    folder=output/identifier;folder.mkdir()
    source=root/fixture['source_directory']
    old=json.loads((source/'manifest.json').read_text())
    mask=load_binary_reference(source/'microstructure.npy',source/'microstructure.png')
    if sha256_file(source/'microstructure.npy')!=fixture['input_sha256'] or sha256_file(source/'manifest.json')!=fixture['manifest_sha256']:
        raise ValueError('Registered fixture source changed.')
    exact,exact_profile=profile(lambda:convert_exact(mask))
    start=time.perf_counter();repeat_exact=convert_exact(mask);exact_repeat_seconds=time.perf_counter()-start
    exact_doc=geometry_bytes(exact['document']);original_wkb=shapely.to_wkb(exact['geometry'],byte_order=1)
    if exact_doc!=geometry_bytes(repeat_exact['document']):raise ValueError('Exact baseline nondeterminism.')
    baseline_name={0:'fixture_A_design000_seed000',9:'fixture_B_design009_seed001'}.get(fixture['design'])
    baseline_reference=None
    if baseline_name:
        baseline=root/'experiments/pipeline_v0.5/baseline_vectorization/run_003'/baseline_name
        if exact_doc!=(baseline/'exact_boundaries.json').read_bytes() or original_wkb!=(baseline/'polygon_candidate.wkb').read_bytes():
            raise ValueError('Historical v0.5A exact geometry differs from unchanged converter.')
        baseline_reference={'document':(baseline/'exact_boundaries.json').relative_to(root).as_posix(),
                            'document_sha256':sha256_file(baseline/'exact_boundaries.json'),
                            'wkb_sha256':sha256_file(baseline/'polygon_candidate.wkb')}
    exact_folder=folder/'exact_geometry';exact_folder.mkdir()
    (exact_folder/'exact_boundaries.json').write_bytes(exact_doc)
    (exact_folder/'exact_polygon.wkb').write_bytes(original_wkb)
    write_json(exact_folder/'comparison.json',exact['comparison'])
    diagnosis,contact_profile=profile(lambda:classify_contacts(mask,exact,near_distance=settings.near_contact_distance))
    write_json(folder/'contacts.json',diagnosis)
    contact_rows=['id\tx\ty\ttype\tdegree\tinherent\tblocks_manifold']
    contact_rows.extend(f"{c['contact_id']}\t{c['xy'][0]}\t{c['xy'][1]}\t{c['kind']}\t{c['boundary_link_degree']}\t{c['inherent_in_source']}\t{c['blocks_manifold']}" for c in diagnosis['contacts'])
    (folder/'contact_locations.tsv').write_text('\n'.join(contact_rows)+'\n')
    pictures=folder/'contact_diagnostics';pictures.mkdir();contact_figures(pictures,mask,exact,diagnosis)
    provenance={**fixture,'state':'canonical_binary','canonical_input_modified':False,
                'input_png_sha256':sha256_file(source/'microstructure.png'),
                'pixel_sha256':hashlib.sha256(mask.tobytes()).hexdigest(),
                'exact_document_sha256':hashlib.sha256(exact_doc).hexdigest(),
                'exact_polygon_sha256':hashlib.sha256(original_wkb).hexdigest(),
                'historical_exact_reference':baseline_reference,
                'generator_version':old['generator_version'],'generator_sha256':old['generator_sha256'],
                'evaluator_sha256':old['evaluator_sha256'],'saved_topology_repair':old['topology_repair'],
                'coordinates':exact['document']['coordinates']}
    write_json(folder/'input_manifest.json',provenance)
    results=[]
    for policy in POLICIES:
        policy_folder=folder/policy;policy_folder.mkdir()
        result,qualification_profile=profile(lambda:qualify_manifold_geometry(mask,exact,policy,settings,diagnosis))
        result['profiling']=qualification_profile
        if result['geometry'] is not None:
            candidate_bytes=shapely.to_wkb(result['geometry'],byte_order=1)
            name='preserved_exact.wkb' if policy=='preserve_exact' else 'manifold_candidate.wkb'
            (policy_folder/name).write_bytes(candidate_bytes)
            np.save(policy_folder/'reconstructed.npy',result['reconstructed'],allow_pickle=False)
            # Re-read the actual persisted geometry and independently rasterize it.
            decoded=shapely.from_wkb((policy_folder/name).read_bytes())
            disk_rec=rasterize_exact_geometry(decoded,len(mask))
            result['serialized_raster_exact']=bool(np.array_equal(disk_rec,mask))
            repeated=qualify_manifold_geometry(mask,exact,policy,settings,diagnosis)
            result['deterministic_wkb']=candidate_bytes==shapely.to_wkb(repeated['geometry'],byte_order=1)
            result['deterministic_metrics']=result['metrics']==repeated['metrics']
            frozen,frozen_profile=profile(lambda:compare_frozen(mask,result['reconstructed']))
            write_json(policy_folder/'frozen_evaluator_comparison.json',frozen)
            result['frozen_morphology_status']=frozen['status']
            result['frozen_evaluation_profile']=frozen_profile
            if result.get('accepted') and not (result['serialized_raster_exact'] and result['deterministic_wkb'] and result['deterministic_metrics'] and frozen['status']=='PASS'):
                result['accepted']=False;result['status']='REJECT_REPRODUCIBILITY_OR_MORPHOLOGY'
            candidate_figures(policy_folder,mask,exact,result)
        else:
            write_json(policy_folder/'FAILURE.json',{'status':result['status'],'reasons':result['failed_gates'],
                                                   'exact_geometry_preserved':True})
        if geometry_bytes(exact['document'])!=exact_doc or shapely.to_wkb(exact['geometry'],byte_order=1)!=original_wkb:
            raise ValueError('Exact geometry was mutated by qualification.')
        write_json(policy_folder/'qualification.json',_serialized_result(result))
        results.append({'policy':policy,'status':result['status'],'accepted':result.get('accepted',False),
                        'failed_gates':result.get('failed_gates',[]),'exact_fidelity':result['exact_fidelity'],
                        'contact_classification':result['contact_classification'],
                        'manifold_candidate_validity':result['manifold_candidate_validity'],
                        'geometric_modification_budget':result['geometric_modification_budget'],
                        'raster_morphology_preservation':result['raster_morphology_preservation'],
                        'frozen_morphology_status':result.get('frozen_morphology_status'),
                        'metrics':result.get('metrics'),'profiling':qualification_profile})
        print(identifier,policy,result['status'],flush=True)
    report={'fixture':identifier,'input_manifest':provenance,'contact_count':len(diagnosis['contacts']),
            'contact_types':{k:sum(c['kind']==k for c in diagnosis['contacts']) for k in sorted(set(c['kind'] for c in diagnosis['contacts']))},
            'exact_profile':exact_profile,'exact_uninstrumented_repeat_seconds':exact_repeat_seconds,
            'contact_detection_classification_profile':contact_profile,'policies':results,
            'physical_feature_qualification':'UNQUALIFIED'}
    write_json(folder/'summary.json',report)
    return report


def run(output,root=ROOT):
    root=Path(root).resolve();output=Path(output).resolve()
    protocol=json.loads((output/'protocol.json').read_text())
    if (output/'execution.json').exists():raise FileExistsError('Study already started; retain it and register a new run.')
    mismatches=[p for p,h in protocol['source_sha256'].items() if sha256_file(root/p)!=h]
    if mismatches:raise ValueError('Registered sources changed: '+str(mismatches))
    write_json(output/'execution.json',{'started_utc':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha256_file(output/'protocol.json')})
    cases=[];settings=CandidateSettings(**protocol['settings'])
    for fixture in protocol['fixtures']:
        try:
            cases.append(run_fixture(root,output,fixture,settings))
        except Exception:
            name=f"design_{fixture['design']:03d}_seed_{fixture['seed']:03d}"
            failure={'fixture':name,'status':'FAILED_EXECUTION','traceback':traceback.format_exc()}
            write_json(output/(name+'_FAILURE.json'),failure);cases.append(failure)
            print(name,'FAILED_EXECUTION',flush=True)
    before=json.loads((output/'preservation_before.json').read_text())
    changed=[p for p,h in before.items() if not (root/p).is_file() or sha256_file(root/p)!=h]
    selected=[]
    for case in cases:
        selected.extend(p for p in case.get('policies',[]) if p['policy']==protocol['selected_candidate_policy'])
    passed=len(selected)==len(protocol['fixtures']) and all(p['accepted'] and p['exact_fidelity']=='PASS' and p['contact_classification']=='PASS' and p['frozen_morphology_status']=='PASS' for p in selected) and not changed
    summary={'schema':'v0.5A.1-study-results','geometric_study_status':'PASS_TESTED_DOMAIN' if passed else 'HOLD',
             'full_acceptance':'PENDING_REGRESSION_AND_REVIEW','cases':cases,
             'existing_files_unchanged':not changed,'changed_existing_files':changed,
             'historical_v0_5A_status':'HOLD_UNCHANGED','physical_feature_qualification':'UNQUALIFIED',
             'mesh_mechanical_manufacturing':'UNQUALIFIED','general_simplification_implemented':False}
    write_json(output/'summary.json',summary)
    lines=['# v0.5A.1 manifold qualification results','',f"Geometry study: **{summary['geometric_study_status']}**. Full acceptance awaits regression verification.",'',
           '| Fixture | Contacts | Policy | Result | Added/removed area | Max displacement | Local clearance | Raster XOR |',
           '|---|---:|---|---|---:|---:|---:|---:|']
    for case in cases:
        for p in case.get('policies',[]):
            m=p.get('metrics')
            if m:
                clear=min((f['local_minimum_clearance'] for f in m['features']),default=0)
                lines.append(f"| {case['fixture']} | {case['contact_count']} | {p['policy']} | {p['status']} | +{m['added_solid_area']:.6f}/-{m['removed_solid_area']:.6f} | {m['maximum_local_boundary_displacement']:.8f} | {clear:.8f} | see qualification.json |")
            else:
                lines.append(f"| {case['fixture']} | {case['contact_count']} | {p['policy']} | {p['status']} | not produced | | | |")
    lines+=['','Exact source geometry is preserved in exact_geometry/. Only separately named opt-in policies produce manifold_candidate.wkb.',
            'Subpixel ligaments remain physically unqualified. Matching frozen raster descriptors do not establish continuous equivalence.',
            'The original v0.5A HOLD and prior v0.4.2 failure/v0.4.3 scoped amendment remain unchanged. No v0.5B work is included.']
    (output/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='action',required=True)
    p=sub.add_parser('prepare');p.add_argument('--output-dir',required=True)
    p=sub.add_parser('run');p.add_argument('output_dir')
    args=parser.parse_args()
    if args.action=='prepare':prepare(args.output_dir);return 0
    result=run(args.output_dir);return 0 if result['geometric_study_status']=='PASS_TESTED_DOMAIN' else 3


if __name__=='__main__':sys.exit(main())
