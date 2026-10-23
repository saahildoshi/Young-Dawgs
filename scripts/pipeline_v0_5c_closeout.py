"""Additive closeout records; refuses to hide any changed historical file."""
from collections import Counter
from pathlib import Path
import json
import sys
from datetime import datetime,timezone
from metamaterial_eval.geometry.validation.checks import digest,authenticate
from metamaterial_eval.geometry.reporting import repository_inventory
from metamaterial_eval.geometry.sensitivity.records import write_json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'experiments/pipeline_v0.5/scientific_validation/run_001'


def main(finalize=False):
    summary=json.loads((OUT/'summary/SCIENTIFIC_GEOMETRY_VALIDATION.json').read_text());rows=summary['rows'];usable=[r for r in rows if 'result_path' in r]
    stats={'registered_repairs':0,'registered_natural_probes':0,'independent_unique_probes':0,'independent_probe_evaluations':0,
           'repair_clearances':[],'new_contact_classes':Counter(),'source_contact_classes':Counter(),'new_repairs':0,
           'guard_evaluations':0,'protected_segment_evaluations':0,'minimum_medial_guard_fraction':1.,'maximum_medial_guard_fraction':0.,
           'maximum_pore_shape_symmetric':0.,'maximum_pore_perimeter_change':0.,'maximum_pore_area_fraction':0.,
           'cumulative_maximum_pore_area_fraction':0.,'G1_G2_maximum_area':0.,'G1_G2_maximum_displacement_upper':0.}
    topology_passes=manifold_passes=descriptor_passes=0;changed=noop=0;recorded_comparisons=[];feature_holds=[]
    for r in usable:
        d=json.loads((ROOT/r['result_path']).read_text());f=d['features'];cohort=r['cohort']
        stats['independent_probe_evaluations']+=len(f['independent_probes']);stats['protected_segment_evaluations']+=f['protected_segment_count']
        if r['epsilon']==0:
            stats['registered_repairs']+=len(f['repairs']);stats['independent_unique_probes']+=len(f['independent_probes'])
            source=json.loads((OUT/'source_manifests'/(r['fixture']+'.json')).read_text());p=source['source_provenance']
            q=json.loads((ROOT/p['paths']['qualification']).read_text())
            contacts=q.get('contact_report',{}).get('contacts',[])
            for c in contacts:
                stats['source_contact_classes'][c['kind']]+=1
                if cohort=='new_parameter':stats['new_contact_classes'][c['kind']]+=1
            if cohort=='new_parameter':
                stats['new_repairs']+=len(f['repairs']);registered=json.loads((OUT/'parameter_holdouts'/r['fixture']/'registered_features.json').read_text())
            else:
                registered=json.loads((ROOT/d['provenance']['candidate_input_path']).parent.parent.joinpath('baseline.json').read_text())['registered_features']
            stats['registered_natural_probes']+=len(registered['natural_neck_probes'])
            stats['repair_clearances'].extend(p['before_clearance'] for p in f['repairs'])
            stats['G1_G2_maximum_area']=max(stats['G1_G2_maximum_area'],d['areas']['G1_G2']['symmetric'])
            stats['G1_G2_maximum_displacement_upper']=max(stats['G1_G2_maximum_displacement_upper'],d['distances']['G1_G2']['upper'])
        guard_records=json.loads((ROOT/d['provenance']['guard_input_path']).with_name('guards.json').read_text());stats['guard_evaluations']+=len(guard_records)
        if f['guarded_narrow_fraction'] is not None:
            stats['minimum_medial_guard_fraction']=min(stats['minimum_medial_guard_fraction'],f['guarded_narrow_fraction']);stats['maximum_medial_guard_fraction']=max(stats['maximum_medial_guard_fraction'],f['guarded_narrow_fraction'])
        for h in d['continuous_topology']['holes']['records']:
            stats['maximum_pore_shape_symmetric']=max(stats['maximum_pore_shape_symmetric'],h.get('symmetric_area',0))
            stats['maximum_pore_perimeter_change']=max(stats['maximum_pore_perimeter_change'],abs(h.get('candidate_perimeter',0)-h.get('source_perimeter',0)))
            stats['maximum_pore_area_fraction']=max(stats['maximum_pore_area_fraction'],h.get('relative_area_distortion') or 0)
        for h in d['cumulative_topology']['holes']['records']:
            stats['cumulative_maximum_pore_area_fraction']=max(stats['cumulative_maximum_pore_area_fraction'],h.get('relative_area_distortion') or 0)
        topology_passes+=d['continuous_topology']['passed'];manifold_passes+=d['G3_integrity']['passed'];descriptor_passes+=d['descriptor_comparison']['exact']
        qpath=(ROOT/d['provenance']['candidate_input_path']).with_name('qualification.json' if cohort=='B2_reference' else 'frozen_B2_qualification.json')
        prior=json.loads(qpath.read_text());measure=prior['metrics']['area_from_manifold']
        differences={k:d['areas']['G2_G3'][k]-measure[field] for k,field in [('added','added_solid_area'),('removed','removed_solid_area'),('symmetric','symmetric_difference_area')]}
        recorded_comparisons.append({'fixture':r['fixture'],'cohort':cohort,'epsilon':r['epsilon'],
            'continuous_area_differences_from_registered':differences,'areas_agree_within_fixed_allowance':all(abs(v)<=1e-10 for v in differences.values()),
            'sampled_lower_within_B2_certificate':d['distances']['G2_G3']['lower']<=prior['certified_boundary_displacement_upper']+1e-10,
            'independent_upper':d['distances']['G2_G3']['upper'],'B2_certificate':prior['certified_boundary_displacement_upper']})
        if f['narrowed_probes'] or f['undefined_probes']:
            feature_holds.append({'fixture':r['fixture'],'epsilon':r['epsilon'],'result_path':r['result_path'],
                'flags':[p for p in f['independent_probes'] if p['narrowed'] or p['delta'] is None],
                'disposition':'C_SCIENTIFIC_HOLD; B2 screening acceptance remains historical; no producer correction authorized in this milestone'})
        if d['B2_disposition']=='ACCEPTED_NOOP':noop+=1
        if d['B2_disposition']=='ACCEPTED_CANDIDATE':changed+=1
    for k in ['source_contact_classes','new_contact_classes']:stats[k]=dict(stats[k])
    stats.update(topology_passes=topology_passes,manifold_passes=manifold_passes,descriptor_passes=descriptor_passes,changed=changed,noops=noop)
    write_json(OUT/'summary/SCIENTIFIC_EXTREMA.json',stats)
    write_json(OUT/'verification/RECORDED_METRIC_COMPARISON.json',{'records':recorded_comparisons,'all_area_comparisons_agree':all(r['areas_agree_within_fixed_allowance'] for r in recorded_comparisons)})
    write_json(OUT/'summary/SCIENTIFIC_HOLDS.json',{'cases':feature_holds,'producer_code_changed':False,'thresholds_changed':False})
    previous=json.loads((OUT/'verification/SESSION_INITIAL_INVENTORY.json').read_text());current=repository_inventory(ROOT,ROOT/'NONEXISTENT-v05C')
    changed_old=[p for p,h in previous.items() if current.get(p)!=h]
    preservation={'prior_files':len(previous),'unchanged':len(previous)-len(changed_old),'modified_or_missing':changed_old,
        'scope':'Every pre-C file outside the historical inventory exclusions, including all generators/evaluator/experiments/acceptance documents.'}
    write_json(OUT/'verification/PRESERVATION.json',preservation)
    w=summary['worst'];reg=json.loads((OUT/'verification/REGRESSION.json').read_text());status=summary['statuses'];new=[r for r in usable if r['cohort']=='new_parameter']
    reductions={str(ep):[min([r['vertex_reduction_percent'] for r in new if r['epsilon']==ep],default=0),max([r['vertex_reduction_percent'] for r in new if r['epsilon']==ep],default=0)] for ep in [0,.2,.5,.75]}
    write_json(OUT/'summary/REDUCTION_RANGES.json',reductions)
    answers=[
        'A separate persisted-artifact validation package was implemented: geometry.validation.checks and study, with immutable protocol/freeze and reporting/closeout scripts.',
        'Reused unchanged exact converter, A1 solid_separate_contacts, B2 guards/engine/qualifier, native v0.4.1 perform_job, frozen v1.1 evaluator and authenticated descriptor cache.',
        'Separate coordinate reconstruction, translated fsum shoelace, point-predicate rasterization, degree/edge/ring topology, reciprocal-anchor/overlap pore identities, changed-line distance bounds and independently selected feature probes.',
        'Parsing, Booleans, polygon construction, spatial predicates and segment distances share GEOS. Scientific descriptor definitions and producer contact policies remain frozen shared definitions. No independent-kernel claim.',
        'G0 versus rasterized G1/G2/G3, and actual continuous G1→G2, G2→G3, G1→G3; cumulative differences are computed directly.',
        'Previously unused original Latin-hypercube designs3,4,6,7,8, with exact registered parameter values in the cohort table. No saved1024 arrays existed there; first native outputs use frozen v0.4.1.',
        f"{summary['new_parameter_structures']} new realizations, both registered seeds0/1, plus ten authenticated prior B2 realizations.",
        f"{summary['total_configurations']} total: {summary['saved_B2_revalidations']} saved-output revalidations and {summary['new_parameter_configurations']} new-point configurations, at ε0,.20,.50,.75.",
        status['B_exact_fidelity']+'; independent pixel reconstruction and integer occupied-area checks retained.',
        status['C_manifold_qualification']+f"; quarantined cases={summary['unsupported']}.",
        f"New exact-source contact classes/counts: {stats['new_contact_classes']}. New G3 non-manifold failures: {len(usable)-manifold_passes}. Original exact singularities remain distinct from introduced defects.",
        f"OGC/dedicated independent manifold checks passed {manifold_passes}/{len(usable)} persisted candidates.",
        f"Manifold candidates passed {manifold_passes}/{len(usable)} independent degree/ring and frozen-classifier checks.",
        f"Unique hole/solid/void topology correspondence passed {topology_passes}/{len(usable)} G2→G3 cases; per-pore area, perimeter, shape and containment records retained. Maximum cumulative G1-pore distortion is {stats['cumulative_maximum_pore_area_fraction']:.3%}: a1cell² pore becomes0.96875cell² through A1 regularization, while G2→G3 pore-area distortion remains zero. This cumulative small-pore effect is diagnostic, not charged against the differently defined B2 cap.",
        'Exterior void-component/domain-side incidence is checked, plus independent void-axis widths. Passing incidence does not exhaustively certify unchanged width.',
        f"Continuous G2→G3 component/region correspondence passed {topology_passes}/{len(usable)}. G1→G2 contact topology changes are separately authorized, measured and disclosed.",
        f"Worst actual symmetric area: G2→G3 {w['G2_G3_symmetric']:.12g}cell²; G1→G3 {w['G1_G3_symmetric']:.12g}cell². G1→G2 maximum {stats['G1_G2_maximum_area']:.12g}cell².",
        f"Worst G2→G3 added/removed material: {w['added']:.12g}/{w['removed']:.12g}cell². Signed net cancellation is not used as a fidelity proxy.",
        f"Worst sampled G2→G3 lower/independent Lipschitz upper: {w['distance_sampled_lower']:.12g}/{w['distance_independent_upper']:.12g}cell. Cumulative lower/upper: {w['cumulative_sampled_lower']:.12g}/{w['cumulative_independent_upper']:.12g}cell.",
        f"Independent continuous status {status['E_independent_continuous_fidelity']}; all hard-gate failures preserved: {summary['hard_gate_failures']}. Original→final limits were prospective, not enlarged.",
        status['F_raster_morphology']+f"; maximum XOR {max((r['raster_xor'] for r in usable),default=0)}.",
        f"Frozen descriptor comparisons passed {descriptor_passes}/{len(usable)}. Fresh originals and two reconstructed integration controls were executed; other proven pixel-identical arrays reuse those deterministic results.",
        f"{stats['registered_repairs']} repair sites ({stats['new_repairs']} new) independently retain footprints/clearances, with {stats['guard_evaluations']} guard evaluations and {stats['protected_segment_evaluations']} protected-segment checks.",
        f"{stats['independent_unique_probes']} unique source-selected axial probes; {stats['independent_probe_evaluations']} evaluations. Narrow raster-medial support guard coverage spans {stats['minimum_medial_guard_fraction']:.3%}–{stats['maximum_medial_guard_fraction']:.3%}; uncovered locations saved. Finite coverage leaves uninstrumented vulnerable regions.",
        f"Detected axial narrowing observations={summary['axial_narrowing_observations']}. No exhaustive continuous-width conclusion follows from zero observed narrowing; supplementary unguarded cross-ring distances are separately retained.",
        f"Independent hard-gate failure classes={summary['hard_gate_failures']}; internal errors={len(summary['errors'])}. Review exact source singularities separately from candidate defects.",
        f"New-point reduction ranges: ε.50 {reductions['0.5'][0]:.5f}–{reductions['0.5'][1]:.5f}%; ε.75 {reductions['0.75'][0]:.5f}–{reductions['0.75'][1]:.5f}%. ε0/.20 remain separately recorded no-op controls.",
        'Epsilon.50 is assessed as a candidate tested-domain setting only if every C case passes; larger epsilon is not assumed better and no production default is selected.',
        status['H_new_parameter_generalization']+' across the stated five positions and two seeds only; no claim for unsampled parameters, resolutions or topologies.',
        'Persisted WKB and full-coordinate JSON are reconstructed and independently checked; new producer constructions repeat byte-identically, with separate metric-repeat evidence in verification/SUPPLEMENTAL_CHECKS.json.',
        f"Execution {summary['execution_seconds']:.3f}s excluding reporting/development; tracked maximum {summary['peak_traced_bytes']/2**20:.3f}MiB, lifetime RSS {summary['peak_process_lifetime_rss_bytes']/2**20:.3f}MiB. Stage costs and shared-tracker caveat retained.",
        f"All {reg['previous_tests']} previous tests retained and passing; full suite {reg['passed']} passed, failures/errors {reg['failures']}/{reg['errors']}.",
        f"{reg['new_C_tests']} new C test cases cover analytic, malformed, topology, subpixel, displacement, provenance and feature failures; one small synthetic was padded before freeze to respect unchanged A1 area budget.",
        f"{preservation['unchanged']}/{preservation['prior_files']} pre-C files unchanged; modified/missing={changed_old}.",
        status['I_scientific_advancement']+' under finite geometric screening, with numeric limits not demonstrated as mechanical sufficiency.',
        status['J_production_policy']+'. A candidate tolerance recommendation is distinct from a production default.',
        'Physical scale, CAD kernel tolerances/interoperability, meshing, materials, load cases, mechanics and manufacturing all remain unqualified; FEM readiness is not claimed.',
        ('A separately scoped v0.5D 2D-export validation can begin using explicitly accepted artifact bundles; no export is implemented here.' if status['I_scientific_advancement'].startswith('SCOPED_PASS') else 'General advancement remains HOLD. Resolve the reported independent limitations under a separately versioned study before downstream qualification.'),
        'All files are additive: geometry.validation package, C tests, report/supplement/closeout scripts, new C docs and scientific_validation/run_001 tree. The final ledger lists exact paths/hashes; no old file is intentionally modified.',
        'Before3D: assign physical dimensions/tolerances, validate 2D export/import in the chosen CAD kernel, assess subpixel repair viability and all relevant bottlenecks, define material/load/mesh requirements and separately verify solid construction. No mechanical or manufacturing evidence is supplied by C.'
    ]
    questions=['Architecture','Reused modules','Independent checks','Shared dependencies','Geometry comparisons','Unused parameters','Stochastic realizations','Configurations','Lossless exact vectorization','New-point manifold qualification','New non-manifold contacts','OGC validity','Manifold status','Pore identity','Exterior channels','Continuous connectivity','Symmetric differences','Added/removed material','Boundary displacement','Original-to-final budgets','Raster fidelity','Frozen descriptors','Repairs','Independent feature coverage','Unguarded narrowing','New geometry defects','Vertex reduction','Candidate settings','New-point consistency','Reproducibility','Runtime/memory','Previous tests','New tests','Historical preservation','Scientific status','Production policy','CAD/FEM limits','v0.5D readiness','Files changed/created','Missing evidence before3D']
    md=['# v0.5C completion — answers to the40 requested questions','']
    for i,(q,a) in enumerate(zip(questions,answers),1):md += [f'{i}. **{q}.** {a}','']
    (OUT/'summary/FINAL_RESPONSE.md').write_text('\n'.join(md))
    handoff=['# v0.5C handoff — stop before export','',f"Scientific status: **{status['I_scientific_advancement']}**.",f"Production: **{status['J_production_policy']}**. CAD/manufacturing: **{status['K_CAD_manufacturing']}**.",'',
        'Authoritative evidence: scientific_validation/run_001/summary/SCIENTIFIC_GEOMETRY_VALIDATION.md and JSON, CONFIGURATIONS.csv, SCIENTIFIC_EXTREMA.json, FINAL_RESPONSE.md (all40 requested questions), protocol freezes and verification/COMPLETION.json.','',
        f"Tested cohort: ten new realizations at original designs3,4,6,7,8 × seeds0/1, four settings each, plus40 authenticated saved B2 revalidations. Limits unchanged. G2→G3 worst symmetric area {w['G2_G3_symmetric']:.12g}cell², displacement upper {w['distance_independent_upper']:.12g}cell. Cumulative G1→G3 actual errors are separately retained.",'',
        answers[37],'',
        'Use only individually accepted cases and all four state/provenance bundles. For each G3, independent_validation.json identifies canonical source, parameter values, seed, G1/G2/G3 hashes, frozen algorithm/configuration and guard files. Preserve G1 and G2 separately; accepted simplification does not supersede the source. Do not pass quarantined or failed raw candidates downstream.','',
        'Epsilon.50 is only a candidate setting for this tested domain when all C gates pass; no automatic production tolerance policy exists. No-op0/.20 is valid evidence, not useful simplification. Stress.75 can retain more vertices because guards/proposal rejection increase.','',
        'Required future2D export protocol: exact physical mapping; selected format and coordinate convention; double precision/tolerance budgets; hole orientation/ownership; reload in an independent consumer; re-run area/topology/pore/raster/distance/feature checks; keep original/exact/manifold/simplified/exported states and hashes. Internal WKB/JSON success does not establish SVG/DXF/STEP interoperability.','',
        'Subpixel regularization remains a specific engineering risk: nominal clearance is not assigned a physical size or CAD kernel tolerance. Finite feature samples do not certify every bottleneck; coverage and uncovered locations remain evidence. No meshing, material model, loads, strength,3D or manufacturing qualification. Preserve v0.4.2 P10 failure, scoped v0.4.3 amendment, A HOLD, A1 and B2 scientific records.','',
        'Reproduction commands and actual platform: V0_5C_REPRODUCTION.md. macOS execution only; Windows syntax is documentation. Any producer correction must be separately versioned and evaluated on newly reserved independent evidence. **No v0.5D/export or later implementation was performed.**','']
    (ROOT/'docs/pipeline_v0.5/V0_5D_HANDOFF.md').write_text('\n'.join(handoff))
    if finalize:
        for source in summary['source_summaries']:
            provenance=source['source_provenance'];authenticate(ROOT/provenance['canonical_path'],provenance['canonical_sha256'])
            for key,path in provenance['paths'].items():authenticate(ROOT/path,provenance['sha256'][key])
        for row in usable:
            result=json.loads((ROOT/row['result_path']).read_text());p=result['provenance']
            authenticate(ROOT/p['candidate_input_path'],p['candidate_input_sha256']);authenticate(ROOT/p['guard_input_path'],p['guard_input_sha256'])
        supplemental=json.loads((OUT/'verification/SUPPLEMENTAL_CHECKS.json').read_text());fig=json.loads((OUT/'verification/FIGURE_QA.json').read_text())
        for p,h in json.loads((OUT/'protocol/IMPLEMENTATION_FREEZE.json').read_text())['code_sha256'].items():authenticate(ROOT/p,h)
        assert not changed_old,'Historical preservation failed'
        assert reg['passed']==407 and reg['failures']==0 and reg['errors']==0
        assert supplemental['all_orientation_ownership_preserved'] and supplemental['all_repeats_identical']
        assert fig['inspected_figures']==10
        write_json(OUT/'verification/COMPLETION.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'statuses':status,
            'implementation_complete':True,'scientific_acceptance':status['I_scientific_advancement'],'regression':reg,
            'preservation':preservation,'supplemental_checks':'SUPPLEMENTAL_CHECKS.json','figure_QA':'FIGURE_QA.json','export_implemented':False})
        # Record all additions after the report, handoff and completion are final.
        current=repository_inventory(ROOT,ROOT/'NONEXISTENT-v05C')
        added=[{'path':p,'sha256':h,'bytes':(ROOT/p).stat().st_size} for p,h in current.items() if p not in previous and p!=str((OUT/'verification/new_files.json').relative_to(ROOT))]
        write_json(OUT/'verification/new_files.json',{'count':len(added),'ledger_self_excluded':True,'modified_preexisting':changed_old,'new_files':added})
    print('Closeout stats',stats,'preservation',preservation['unchanged'],'/',preservation['prior_files'])


if __name__=='__main__':main('--finalize' in sys.argv)
