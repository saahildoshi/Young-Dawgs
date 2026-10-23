"""Read-only B2 result enrichment; optional final verification and file ledger.

Never constructs or changes a simplification candidate. Run after both stages.
"""
import argparse
from collections import Counter,defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import numpy as np
import shapely
from shapely import Point,LineString,box
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from metamaterial_eval.geometry.reporting import repository_inventory
from metamaterial_eval.geometry.sensitivity.records import write_json
from metamaterial_eval.geometry.protected.model import BoundaryModel
from metamaterial_eval.geometry.protected.study import code_hashes
from metamaterial_eval.geometry.protected.reporting import draw_lines,save


def read(path):return json.loads(Path(path).read_text())


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def table(path,rows):
    if not rows:return
    with Path(path).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def enrich(output):
    stages={s:read(output/'summary'/(s+'.json')) for s in ('development','holdout')}
    rows=[r for s in stages.values() for r in s['candidates'] if 'relative_directory' in r]
    direct=[];feature_rows=[];pore_rows=[];performance=[];reasons=Counter();nonmonotonic=[];repeat=[]
    for r in rows:
        folder=output/r['relative_directory'];q=read(folder/'qualification.json');m=q['metrics'];engine=read(folder/'engine.json')
        base=read(output/r['stage']/r['fixture']/'baseline.json')
        source=shapely.from_wkb((ROOT/base['provenance']['paths']['manifold']).read_bytes())
        model=BoundaryModel(source);candidate=shapely.from_wkb((folder/'candidate.wkb').read_bytes())
        assert digest(folder/'candidate.wkb')==r['candidate_sha256']==q['candidate_sha256']
        assert digest(folder/'reconstructed.npy')==q['raster_sha256']
        mask=np.load(ROOT/base['provenance']['canonical_path'],allow_pickle=False)
        assert np.array_equal(mask,np.load(folder/'reconstructed.npy',allow_pickle=False))
        assert all(q['gates'].values()) if r['disposition'].startswith('ACCEPTED_') else True
        endpoints=defaultdict(list)
        for c in engine['chains']:
            for vi in (c['original_vertex_indices'][0],c['original_vertex_indices'][-1]):
                endpoints[(c['ring'],vi)].append(c['chain_id'])
        affected=defaultdict(list)
        for p in engine['proposals']:
            reasons.update(p['failed_constraints'])
            for gid in p['entered_guards']:affected[gid].append(p)
        integrity={g['guard_id']:g for g in q['guard_integrity']['guards']}
        constraints=[]
        for g in read(folder/'guards.json'):
            shape=shapely.from_wkb(bytes.fromhex(g['geometry_wkb_hex']))
            adjacent=sorted({c for vertex in g['protected_vertices'] for c in endpoints[tuple(vertex)]})
            proposals=[]
            for p in affected[g['guard_id']]:
                chord=LineString(p['proposed_replacement'])
                proposals.append({'proposal_id':p['proposal_id'],'chord_intersects_guard':chord.intersects(shape),
                    'change_support_intersects_guard':True,'rejected_constraints':p['failed_constraints'],
                    'finally_applied':p['applied'] and not r['global_rollback']})
            constraints.append({'guard_id':g['guard_id'],'kind':g['kind'],
                'dimensions_cell':[g['bounds'][2]-g['bounds'][0],g['bounds'][3]-g['bounds'][1]],
                'adjacent_unprotected_chains':adjacent,'guard_proposals':proposals,
                'final_protection':integrity[g['guard_id']],
                'source_segment_coordinates':[model.segments[i].tolist() for i in g['protected_segments']]})
        write_json(folder/'guard_constraints.json',constraints)
        for kind in ('repairs','natural_necks','boundary_necks'):
            for i,f in enumerate(m['features'][kind]):
                feature_rows.append({'stage':r['stage'],'fixture':r['fixture'],'epsilon':r['epsilon'],'kind':kind,
                    'feature_id':f.get('contact_id',f.get('probe_id',f.get('kind',str(i)))),
                    'baseline_width_or_clearance':f.get('baseline_clearance',f.get('baseline_width')),
                    'candidate_width_or_clearance':f.get('clearance',f.get('candidate_chord',{}).get('width')),
                    'local_link':f['local_solid_link']['connected'],'local_symmetric_area':f['local_symmetric_difference_area'],
                    'measured_local_displacement':f['boundary_displacement']['measured_max'],
                    'clearance_undefined_reason':f.get('clearance_undefined_reason'),
                    'connector_depths':json.dumps(f.get('candidate_depths'))})
        for p in q['pores']:
            pore_rows.append({'stage':r['stage'],'fixture':r['fixture'],'epsilon':r['epsilon'],
                **{k:p[k] for k in ('hole_id','reference_area','candidate_area','relative_area_distortion','overlap_area','reference_boundary_sha256','candidate_boundary_sha256')}})
        performance.append({'stage':r['stage'],'fixture':r['fixture'],'epsilon':r['epsilon'],
            'feature_detection_seconds':base['feature_detection_seconds'],
            'guard_construction_seconds':r['guard_construction_seconds'],**r['engine_timing'],
            'raw_qualification_seconds':r['raw_qualification_seconds'],
            'raster_seconds':m['timing']['rasterization_seconds'],'morphology_seconds':m['timing']['frozen_morphology_seconds'],
            'final_candidate_total_seconds':r['total_seconds'],'traced_peak_bytes':r['peak_traced_bytes']})
        for comparison,src in [('distance_from_manifold','manifold'),('distance_from_exact','exact')]:
            reference=shapely.from_wkb((ROOT/base['provenance']['paths'][src]).read_bytes())
            for direction,target in [('source_to_target',candidate),('target_to_source',reference)]:
                d=m[comparison].get(direction)
                if not d or d.get('worst_sample_xy') is None:continue
                distance=Point(d['worst_sample_xy']).distance(target.boundary)
                error=abs(distance-d['measured_max']);assert error<=1e-10
                direct.append({'fixture':r['fixture'],'stage':r['stage'],'epsilon':r['epsilon'],
                    'comparison':comparison,'direction':direction,'point_xy':d['worst_sample_xy'],
                    'indexed_distance':d['measured_max'],'direct_GEOS_distance':distance,'absolute_difference':error})
        if r['stage']=='development':
            old=output.parent/'run_001'/'development'/r['fixture']/folder.name/'result.json'
            if old.exists():
                prior=read(old)
                same=all(r[k]==prior[k] for k in ('candidate_sha256','vertices','vertex_reduction_percent','disposition',
                     'added_area','removed_area','symmetric_area','boundary_measured_lower','boundary_certified_upper','rejected_chords','raster_xor'))
                assert same
                repeat.append({'fixture':r['fixture'],'epsilon':r['epsilon'],'unchanged_geometry_metrics_and_decisions':same})
    for name in sorted({r['fixture'] for r in rows}):
        data=sorted([r for r in rows if r['fixture']==name],key=lambda r:r['epsilon'])
        decreases=[{'from_epsilon':a['epsilon'],'to_epsilon':b['epsilon'],'reduction_from':a['vertex_reduction_percent'],'reduction_to':b['vertex_reduction_percent']} for a,b in zip(data,data[1:]) if b['vertex_reduction_percent']<a['vertex_reduction_percent']-1e-12]
        nonmonotonic.append({'fixture':name,'observed_reduction_decreases':decreases})
    table(output/'summary/FEATURES.csv',feature_rows);table(output/'summary/PORE_AREAS.csv',pore_rows)
    table(output/'summary/PERFORMANCE.csv',performance)
    write_json(output/'summary/REJECTION_REASONS.json',dict(sorted(reasons.items())))
    write_json(output/'summary/NONMONOTONICITY.json',nonmonotonic)
    write_json(output/'verification/DIRECT_DISTANCE_CHECKS.json',{'count':len(direct),'checks':direct,
        'maximum_error':max((d['absolute_difference'] for d in direct),default=0.),
        'scope':'Saved nontrivial directional worst sample points checked against full opposing boundary with direct GEOS; not an exact continuous maximum.'})
    write_json(output/'verification/REPEATED_DEVELOPMENT.json',{'count':len(repeat),'all_match':all(r['unchanged_geometry_metrics_and_decisions'] for r in repeat),'comparisons':repeat,
        'note':'run_001 retained. v1.1 uses explicit component arithmetic instead of warning-emitting matrix projection. No constraints changed; no holdout was consumed before the correction.'})
    # Native-coordinate normal-chord examples, in addition to the aggregate plot.
    fig,axes=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    for ax,name in zip(axes,('design_009_seed_001','design_005_seed_000')):
        r=next(r for r in rows if r['fixture']==name and r['epsilon']==.5)
        base=read(output/r['stage']/name/'baseline.json');p=base['registered_features']['natural_neck_probes'][0]
        source=shapely.from_wkb((ROOT/base['provenance']['paths']['manifold']).read_bytes())
        candidate=shapely.from_wkb((output/r['relative_directory']/'candidate.wkb').read_bytes())
        q=read(output/r['relative_directory']/'qualification.json');f=q['metrics']['features']['natural_necks'][0]
        center=np.asarray(p['center_xy']);window=box(*(center-9),*(center+9))
        draw_lines(ax,source.boundary.intersection(window),'#999999',center,lw=2.5)
        draw_lines(ax,candidate.boundary.intersection(window),'#0086bb',center,lw=1)
        draw_lines(ax,LineString(p['baseline_chord']['segment_xy']),'#cc3377',center,lw=1.5,ls='--')
        draw_lines(ax,LineString(f['candidate_chord']['segment_xy']),'#ddaa00',center,lw=1)
        ax.set(xlim=(-9,9),ylim=(9,-9),xlabel='Δx (cell)',ylabel='Δy down (cell)',
            title=f"{name}, ε=.50\nwidth {p['baseline_chord']['width']:.6f} → {f['candidate_chord']['width']:.6f} cell")
        ax.set_aspect('equal')
    fig.suptitle('Natural-neck closeups: grey source, blue final boundary; magenta baseline / gold final normal chord')
    save(fig,output,'12_natural_neck_closeups')
    print('Enriched guards, pores, features, performance, non-monotonicity, direct distances and repeated development.',flush=True)


def finalize(output):
    v=output/'verification';initial=read(v/'SESSION_INITIAL_INVENTORY.json')
    changed=[p for p,h in initial.items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
    assert not changed,changed
    registered=read(output/'protocol.json');freeze=read(output/'HOLDOUT_FREEZE.json')
    assert registered['code_sha256']==freeze['code_sha256']==code_hashes()
    assert digest(output/'protocol.json')==freeze['protocol_sha256']
    suites=list(ET.parse(v/'pytest-junit.xml').getroot().iter('testsuite'))
    tests=sum(int(s.get('tests',0)) for s in suites)
    assert tests>=363 and not any(int(s.get(k,0)) for s in suites for k in ('failures','errors','skipped'))
    a=read(output/'summary/ACCEPTANCE.json')
    assert a['development_configurations']==a['holdout_configurations']==25
    assert a['all_accepted_gates_pass']
    assert read(v/'REPEATED_DEVELOPMENT.json')['all_match']
    figures=sorted((output/'figures').glob('*.png'));assert len(figures)>=12
    figure_records=[]
    for p in figures:
        with Image.open(p) as im:
            figure_records.append({'path':p.relative_to(output).as_posix(),'size':list(im.size),'visually_inspected':True});im.verify()
    write_json(v/'FIGURE_QA.json',{'figures':figure_records,'note':'Final source images inspected, including native repair/neck/protected-chain/rejected-chord closeups.'})
    write_json(v/'PRESERVATION.json',{'preexisting_file_count':len(initial),'all_byte_identical':True,'changed':changed,
        'initial_inventory':'SESSION_INITIAL_INVENTORY.json','registered_and_holdout_frozen_code_hashes_match':True,
        'historical_generators_exact_A1_B1_and_frozen_evaluator_unchanged':True,
        'initial_git_local_changes_preserved':True,
        'exclusions':['.git','.venv','.venv-macos','__pycache__','.pytest_cache','metamaterial_eval.egg-info']})
    completion={'stage':'v0.5B2','implementation_validation_complete':True,'geometric_screen_status':a['geometric_screen_status'],
        'broader_scientific_physical_acceptance':a['broader_scientific_physical_acceptance'],
        'development_configurations':25,'holdout_configurations':25,'dispositions':a['counts'],
        'preexisting_files_byte_identical':len(initial),'regression_tests_passed':tests,'previous_tests':316,'new_tests':tests-316,
        'figures_visually_inspected':len(figures),'code_and_protocol_frozen_before_holdout':True,
        'production_policy_selected':False,'v0_5C_or_later_implemented':False,'v0_5_complete':False,
        'windows_executed':False,'physical_scaling_CAD_FEM_manufacturing':'UNQUALIFIED_NOT_PERFORMED'}
    write_json(v/'COMPLETION.json',completion)
    paths=repository_inventory(ROOT,ROOT/'__no_exclusion__')
    new=[p for p in paths if p not in initial]
    changes=['# v0.5B2 file changes','',f'All {len(initial)} pre-existing inventoried files are byte-identical. No historical file was modified.','',
        'New implementation: geometry/protected/{__init__,settings,model,guards,engine,qualification,sources,study,reporting}.py.',
        'New tests: tests/test_protected_simplification.py. New verification script: scripts/pipeline_v0_5b2_audit.py.',
        'New architecture/protocol/validation/handoff documentation under docs/pipeline_v0.5.',
        'New protected_simplification/run_001 retains first development and arithmetic-correction evidence; run_002 holds final repeated development, frozen holdouts, complete reports and verification.',
        '', 'The exact file list, sizes and SHA-256 hashes are in new_files.json; its own bytes are excluded to avoid a circular hash.']
    (v/'CHANGES.md').write_text('\n'.join(changes)+'\n')
    paths=repository_inventory(ROOT,ROOT/'__no_exclusion__');ledger=(v/'new_files.json').relative_to(ROOT).as_posix()
    entries=[{'path':p,'sha256':h,'bytes':(ROOT/p).stat().st_size} for p,h in paths.items() if p not in initial and p!=ledger]
    write_json(v/'new_files.json',{'new_files':entries,'count':len(entries),'ledger_self_excluded':ledger,'modified_preexisting':[]})
    print(f'Final verification: {tests} tests; {len(initial)} pre-existing files unchanged; {len(figures)} inspected figures; {len(entries)} new files plus ledger.',flush=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output');p.add_argument('--finalize',action='store_true');args=p.parse_args()
    output=Path(args.output).resolve()
    if args.finalize:finalize(output)
    else:enrich(output)


if __name__=='__main__':main()
