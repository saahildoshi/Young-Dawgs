"""C.1 final inventory, scientific handoff and answers to42 requested questions."""
from pathlib import Path
import json
import sys
from datetime import datetime,timezone
from metamaterial_eval.geometry.protected_v2.study import ROOT,OUT
from metamaterial_eval.geometry.validation.checks import digest,authenticate
from metamaterial_eval.geometry.reporting import repository_inventory
from metamaterial_eval.geometry.sensitivity.records import write_json


def read(p):return json.loads(Path(p).read_text())


def main(finalize=False):
    s=read(OUT/'summary/INDEPENDENT_REQUALIFICATION.json');stats=s['stats'];reg=read(OUT/'verification/REGRESSION.json');root=read(OUT/'root_cause/REPRODUCTION.json');ranges=read(OUT/'summary/REDUCTION_RANGES.json');cmp=read(OUT/'summary/REGRESSION_COMPARISON.json');profile=read(OUT/'performance/TARGETED_PROFILE.json')
    initial=read(OUT/'verification/INITIAL_INVENTORY.json');current=repository_inventory(ROOT,ROOT/'NONEXISTENT-C1');changed=[p for p,h in initial.items() if current.get(p)!=h];preservation={'prior_files':len(initial),'unchanged':len(initial)-len(changed),'modified_or_missing':changed}
    write_json(OUT/'verification/PRESERVATION.json',preservation)
    s['statuses']['A_source_preservation']='PASS_BYTE_IDENTICAL' if not changed else 'FAIL';s['software_regression']=reg;s['preservation']=preservation
    write_json(OUT/'summary/INDEPENDENT_REQUALIFICATION.json',s)
    p=OUT/'summary/INDEPENDENT_REQUALIFICATION.md';p.write_text(p.read_text().replace('VERIFY_FINAL_INVENTORY',s['statuses']['A_source_preservation']))
    plan=read(OUT/'protocol/PROTOCOL.json');ind=[r for r in s['rows'] if r.get('stage')=='independent_cohort'];allrows=[r for r in s['rows'] if 'result_path' in r]
    native=list((OUT/'independent_cohort/parameter_holdouts').glob('*/native1024/microstructure.npy'))
    targeted=root['C1_revised'];original=root['B2_original'];answers=[
        'A four-point staircase was replaced by an endpoint chord that removed material from a9-cell solid section. The opposite boundary stayed fixed; the replacement line intersects x=57.5 at y=560.9166666667 instead of561, giving a1/12-cell width loss.',
        'Both. EDT-based screening used diameter≤8 while the probe had diameter8.94427191; proximity screening used2cells while the section was9cells; no registered probe guarded the change hull. Chord collision, clearance, area and raster tests did not measure that corridor width.',
        'The new protected_v2 namespace adds local source-opposition queries and native-axis projection-event affine width qualification before leaf acceptance. Qualifying loss above1e-10cell or ambiguous affected geometry rejects and restores the original subchain. All original guards/budgets and DP traversal semantics remain.',
        'It operates on every otherwise eligible proposal using geometry, source indices, a registered16-cell width horizon and horizontal/vertical section events. It contains no design identifier or failed coordinate. Complementary oblique measurements remain independent validation.',
        f"Yes. Original B2 source hashes are unchanged and its full failure-fixture output reproduced the historical WKB byte-for-byte: {root['original_byte_identical']}.",
        f"Yes. Saved geometry, full original rerun, GEOS section measurement and independent coordinate interpolation reproduce9→{original['width']:.12f}cells.",
        f"Yes. Revised actual section width={targeted['width']:.12f}cells. The exact old chord is rejected for qualifying_solid_width_loss; its source subchain is retained.",
        f"{reg['new_tests']} new analytic/adversarial cases cover translated/angled/tapered/curved corridors, high curvature, junctions, raster-invisible narrowing, area/topology-insensitive losses, safe edits, uncertainty, guards, rollback, no-op/determinism and small-pore identity/metric controls. Fifteen synthetic pore-policy artifact cases are separately saved.",
        'Yes. Width-damaging and uncertain leaves retain their original source coordinates, with original/proposed/restored chains and reasons. No morphology or post hoc widening repairs a failed output.',
        f"Total width/uncertainty rejection flags={stats['width_rejections']}. Regression leaves formerly accepted by original B2 and now rejected specifically by width qualification={cmp['newly_prevented_previously_accepted']}. Flags are repeated-setting instances and may overlap prior area rejection; they are not unique damaged struts.",
        f"Total local restorations={stats['local_rollbacks']}, unchanged eligible-chain instances={stats['unchanged_chains']}, assembly rollbacks={stats['assembly_rollbacks']}. Whole-candidate no-op configurations={sum(r.get('B2_disposition')=='ACCEPTED_NOOP' for r in allrows)}. Raw failures remain failures; no hidden rescue is applied.",
        f"Yes. Proposal impact screening evaluates{stats['integrated_sections']} qualifying affine section instances beyond fixed guards, including the originally unguarded failure. It does not enlarge or relabel the original guard coverage.",
        f"Registered repair sites={stats['registered_repairs']}; maximum measured clearance loss={stats['max_repair_clearance_loss']:.12g}cell. Exact patch and protected-coordinate gates remain active.",
        f"Registered natural probes={stats['registered_natural_probes']}; maximum measured registered width loss={stats['max_registered_width_loss']:.12g}cell. Fixed connector/link requirements remain unchanged.",
        f"Regression reduction ranges: ε.50 {ranges['regression']['0.5'][0]:.6f}–{ranges['regression']['0.5'][1]:.6f}%; ε.75 {ranges['regression']['0.75'][0]:.6f}–{ranges['regression']['0.75'][1]:.6f}%. Independent ranges: ε.50 {ranges['independent_cohort']['0.5'][0]:.6f}–{ranges['independent_cohort']['0.5'][1]:.6f}%; ε.75 {ranges['independent_cohort']['0.75'][0]:.6f}–{ranges['independent_cohort']['0.75'][1]:.6f}%. All lower settings and no-ops are retained.",
        f"Matched targeted instrumented engine times were {profile['records'][0]['instrumented_engine_seconds']:.6f}s original and {profile['records'][1]['instrumented_engine_seconds']:.6f}s revised. Engine traced peaks were {profile['records'][0]['engine_traced_peak_bytes']/2**20:.3f}/{profile['records'][1]['engine_traced_peak_bytes']/2**20:.3f}MiB. Full-study execution={s['execution_seconds']:.3f}s and lifetime RSS={s['peak_process_lifetime_rss_bytes']/2**20:.3f}MiB. No full-validation tracemalloc peak or cross-instrumentation speedup is claimed.",
        f"Independent manifold checks passed{stats['geometry_manifold_passes']}/{len(allrows)} evaluable candidates; raw failures/internal errors={s['errors']}. Unsupported inputs={s['unsupported']}. All exceptions remain counted.",
        'Unique positive-overlap plus reciprocal-anchor matching, region counts, domain-void incidence and per-pore records check identities; equal area alone does not establish correspondence. See every independent_validation.json for merges/splits/births/deletions and any failure.',
        f"Frozen hard-constraint passes={stats['frozen_B2_passes']}/{len(allrows)}. Worst added/removed={stats['max_added']:.12g}/{stats['max_removed']:.12g}cell². Budgets remain0.25% per sign and0.5% symmetric of occupied G2 area; G2-based per-pore cap remains0.5%.",
        f"Worst independently bounded G2→G3 displacement={stats['max_distance_upper']:.12g}cell; cumulative G1→G3={stats['max_cumulative_distance_upper']:.12g}cell. Ceiling remains sqrt(2)/2cell with1e-10 numeric allowance; sampled lower bounds are not exact Hausdorff maxima.",
        f"Exact native reconstruction passed{stats['raster_exact_passes']}/{len(allrows)} evaluable cases. G1/G2 source reconstructions are separately checked; masks are not replaced.",
        f"Frozen v1.1 comparisons passed{stats['descriptor_passes']}/{len(allrows)}. Independently identical arrays reuse authenticated deterministic scalar/full S2/L results; selected changed candidates receive explicit integration evaluation. P10 definition/caveat is unchanged.",
        'A local solid-side A1 regularization adds a diamond of radius0.25cell at a genuine point contact; one incident pore loses a triangle r²/2=1/32cell². A1 changes1cell² to0.96875cell², a3.125% relative loss. Simplification does not cause that original discrepancy.',
        'Existing A1 criteria were applied correctly within their geometric scope; that does not establish cumulative pore-fidelity adequacy. The B2 relative cap starts at G2 and is not retroactively applied to A1. Cumulative small-pore scientific policy remains UNQUALIFIED.',
        'No fidelity amendment is adopted. An absolute1/32cell² construction-scale diagnostic and0.5% relative diagnostic were evaluated with AND/OR combinations on synthetic and independent real pores. Both errors and mandatory topology/identity remain visible; a mathematical construction envelope is not a physical allowance.',
        f"Across all source pores, maximum G1→G2 absolute error={s['pore_maximum_absolute_error']:.12g}cell² and relative error={s['pore_maximum_relative_error']:.6%}. Actual G1→G3 maxima: absolute={stats['max_pore_G1_G3_absolute']:.12g}cell²; relative={stats['max_pore_G1_G3_fraction']:.6%}. Maximum G2→G3 relative pore-area distortion={stats['max_pore_G2_G3_fraction']:.6%}; shape and perimeter changes remain separate. Seven independent 1-cell² pores lose two contact triangles, leaving0.9375cell² (6.25% loss), with identity preserved.",
        'Six entirely new parameter positions inside original v0.3 bounds, listed exactly in the main report, PROTOCOL.json and the machine cohort table; both new seeds12031/12032 at each.',
        'Deterministic scipy.stats.qmc.LatinHypercube, sampling seed20261021, with normalized distances from every original point recorded. No outcome filtering or native geometry inspection occurred before final code/protocol freeze.',
        f"{len(native)} new native1024 arrays were generated out of12 planned realizations. Existing20 source masks were authenticated and reused, never regenerated. Unsupported/native failures remain in the denominator.",
        f"{len(ind)} independent configuration records versus60 expected; total study={s['total_configurations']} including100 expected consumed regression configurations. Settings=[0,.20,.35,.50,.75].",
        s['statuses']['F_independent_features']+' for the registered feature/geometry domain. Overall scientific acceptance is separately '+s['statuses']['J_overall_scientific']+'.',
        'No. Final hashes, cohort, seeds, width settings, budgets and small-pore disposition were frozen before independent native generation; final verification authenticates them again. Any subsequent algorithm correction would require a new version and fresh cohort.',
        f"Integrated finite native-axis event checks and a16-cell horizon; independent unique axial probes={stats['independent_axial_unique']}, oblique probes={stats['independent_oblique_unique']}. Finite orientation/location coverage, raster resolution, ambiguous cases and shared floating GEOS definitions prevent universal minimum-neck or mechanical claims. No monitored section intersects an accepted replacement chord in this cohort, limiting independent evidence about the changed regions.",
        f"Maximum measured new independent width loss={stats['maximum_measured_narrowing']:.12g}cell. Narrowing observations axial/oblique={stats['axial_narrowed']}/{stats['oblique_narrowed']}; undefined sections={stats['undefined']}. Values within1e-10 are numerical comparisons, not an engineering loss allowance.",
        f"Worst actual G2→G3 symmetric difference={stats['max_symmetric_G2_G3']:.12g}cell²; cumulative G1→G3={stats['max_symmetric_G1_G3']:.12g}cell². G1→G2 repair differences are separately measured, never added as assumed error totals.",
        f"{reg['passed']} tests passed: all{reg['previous_tests']} prior tests plus{reg['new_tests']} new tests; failures/errors={reg['failures']}/{reg['errors']}. Actual platform macOS ARM64. Windows execution is not claimed.",
        f"{preservation['unchanged']}/{preservation['prior_files']} initial files remain byte-identical; modified/missing={changed}. This includes generators, evaluator, exact/manifold artifacts, original B2/C code and all historical acceptances/failures.",
        'New files only: geometry/protected_v2,50-case test file, C.1 comparison/profile/pore/report/closeout scripts, new documentation and scientific_requalification/run_001 evidence tree. verification/new_files.json lists exact additions and hashes; no prior file is intentionally modified.',
        '; '.join(k+'='+v for k,v in s['statuses'].items()),
        'General scientific advancement remains HOLD while cumulative small-pore fidelity is unqualified, and also for any recorded feature/geometry failure. A separately scoped future export software investigation is distinct from qualifying the complete workflow. No v0.5D implementation is performed.',
        'Yes: HOLD_UNQUALIFIED. No tolerance is selected by best-of-holdout performance and no universal or automatic production simplification policy is established.',
        'Finite geometry/probe coverage, unresolved cumulative small-pore criteria, subpixel regularizations, absent physical scale and CAD-kernel tolerances/interoperability, no mesh/material/load/strength/manufacturing qualification. Resolve these through separately registered engineering stages before claiming3D or FEM readiness.'
    ]
    titles=['Cause of width loss','Detection versus validation','Algorithmic correction','Generalization of correction','Original B2 preservation','Independent reproduction','Corrected original section','Synthetic failure controls','Unsafe chord rejection','New rejection counts','Rollback and no-op','Newly identified vulnerable sections','Repair preservation','Registered width preservation','Retained reduction','Runtime and memory','New topology defects','Pore identities','Area budgets','Displacement bound','Raster equality','Frozen descriptors','Origin of small-pore discrepancy','Scientific adequacy of pore policy','Policy amendment','Remaining pore errors','New parameter combinations','Independent selection','New realizations','Independent configurations','Independent qualification','Holdout tuning','Coverage limits','Maximum width loss','Continuous error','Software tests','Historical preservation','Created/modified files','Exact status','v0.5D eligibility','Production qualification','Limits before3D']
    assert len(answers)==42 and len(titles)==42
    md=['# v0.5C.1 completion —42 requested answers','']
    for i,(title,answer) in enumerate(zip(titles,answers),1):md += [f'{i}. **{title}.** {answer}','']
    (OUT/'summary/FINAL_RESPONSE.md').write_text('\n'.join(md))
    handoff=f'''# v0.5C.1 handoff — stop before v0.5D

Scientific status: **{s['statuses']['J_overall_scientific']}**. Feature qualification: **{s['statuses']['F_independent_features']}**. Cumulative small-pore policy: **UNQUALIFIED**. Production: **HOLD_UNQUALIFIED**. CAD/manufacturing/FEM: **UNQUALIFIED**.

The new explicit algorithm is `{s['algorithm_version']}` under geometry.protected_v2. Original protected/validation modules, B2 accepted candidates and the historical C HOLD remain immutable. The original9→8.916666667-cell failure is preserved and reproduced; the versioned correction keeps that section at9cells without a coordinate-specific rule.

Read scientific_requalification/run_001/summary/FEATURE_PROTECTION_CORRECTION.md, SMALL_PORE_QUALIFICATION.md, INDEPENDENT_REQUALIFICATION.md and JSON, CONFIGURATIONS.csv and FINAL_RESPONSE.md for all42 completion answers. Read protocol/FINAL_FREEZE.json and verification/COMPLETION.json for actual freeze, platform, repeat, software, figure and preservation evidence. Every case records G0/G1/G2/G3 provenance and actual independent measurements.

All20 original realizations are consumed regression evidence. The only new holdouts are six LHS positions under original bounds, sampling seed20261021, stochastic seeds12031/12032, generated after final freeze. Do not tune a later algorithm against these consumed holdouts while calling the result independent. A further correction needs a separate version and fresh reserved cohort.

The integrated criterion covers registered native-axis affine corridors/horizon, not every possible cross-section. Independent axial and oblique audits remain finite. A local positive clearance or width is not assigned physical dimensions. Small-pore area must retain absolute and relative errors: one contact triangle changes1cell² to0.96875cell²; no engineering allowance is adopted merely because the footprint is small. The new cohort contains seven1-cell² pores with two contact repairs and6.25% loss. None of the finite independent monitored sections intersects an accepted replacement chord, which limits changed-region audit coverage. Existing A1 geometric scope is not cumulative scientific qualification.

**General advancement remains HOLD.** A future2D export protocol must separately define physical mapping, consumer/kernel, numeric tolerances, formats, ring/ownership conventions and reload checks, retaining original/exact/manifold/simplified/exported states. Internal WKB/JSON checks do not establish future interoperability. Any limited software-only export investigation must explicitly state its individually accepted input scope and cannot imply complete pipeline acceptance.

No exporter, SVG/DXF, CAD kernel,3D, meshing, FEM or manufacturing functionality is implemented. Actual execution was macOS ARM64; reproduction syntax for Windows is documentation only. Do not rerender saved native sources or overwrite completed experiment trees during reproduction. **Stop at v0.5C.1.**
'''
    (OUT/'summary/V0_5C_1_HANDOFF.md').write_text(handoff)
    (ROOT/'docs/pipeline_v0.5/V0_5C_1_HANDOFF.md').write_text(handoff)
    for name in ['FEATURE_PROTECTION_CORRECTION','SMALL_PORE_QUALIFICATION','INDEPENDENT_REQUALIFICATION']:
        (ROOT/'docs/pipeline_v0.5'/(name+'.md')).write_text(f'# v0.5C.1 — {name.replace("_"," ").lower()}\n\nAuthoritative executed report:\n\n`experiments/pipeline_v0.5/scientific_requalification/run_001/summary/{name}.md`\n\nRead adjacent JSON/CSV and verification/COMPLETION.json. Historical C HOLD remains unchanged. Feature acceptance, cumulative small-pore policy, overall scientific status and production qualification are separate. No export or CAD implementation is included.\n')
    if finalize:
        assert not changed
        assert reg['passed']==457 and reg['failures']==0 and reg['errors']==0
        frozen=read(OUT/'protocol/FINAL_FREEZE.json');authenticate(OUT/'protocol/PROTOCOL.json',frozen['protocol_sha256'])
        authenticate(OUT/'summary/regression.json',frozen['regression_summary_sha256'])
        for p,h in frozen['code_sha256'].items():authenticate(ROOT/p,h)
        qa=read(OUT/'verification/FIGURE_QA.json');assert qa['inspected_figures']==10
        for p,h in qa['files'].items():authenticate(OUT/'figures'/p,h)
        for stage in ['regression','independent_cohort']:
            for p in (OUT/stage/'source_manifests').glob('*.json'):
                provenance=read(p)['source_provenance'];authenticate(ROOT/provenance['canonical_path'],provenance['canonical_sha256'])
                for k,path in provenance['paths'].items():authenticate(ROOT/path,provenance['sha256'][k])
        for r in allrows:
            d=read(ROOT/r['result_path']);p=d['provenance'];authenticate(ROOT/p['candidate_input_path'],p['candidate_input_sha256']);authenticate(ROOT/p['guard_input_path'],p['guard_input_sha256'])
        repeated=[r for r in allrows if r['epsilon']==.5];assert len(repeated)==32
        assert all(read(ROOT/r['result_path'])['repeat_identical'] for r in repeated)
        assert s['regression_configurations']==100 and s['independent_configurations']==60
        write_json(OUT/'verification/COMPLETION.json',{'completed_utc':datetime.now(timezone.utc).isoformat(),'implementation_complete':True,'statuses':s['statuses'],'regression':reg,'preservation':preservation,'figures':10,'same_platform_epsilon_050_repeats':len(repeated),'all_repeats_byte_identical':True,'historical_C_HOLD_unchanged':True,'export_implemented':False,'independent_holdout_tuning':False})
        current=repository_inventory(ROOT,ROOT/'NONEXISTENT-C1');added=[{'path':p,'sha256':h,'bytes':(ROOT/p).stat().st_size} for p,h in current.items() if p not in initial and p!=str((OUT/'verification/new_files.json').relative_to(ROOT))]
        write_json(OUT/'verification/new_files.json',{'count':len(added),'ledger_self_excluded':True,'modified_preexisting':changed,'new_files':added})
    print('Closeout',s['statuses'],'preserved',preservation,'answers',len(answers),flush=True)


if __name__=='__main__':main('--finalize' in sys.argv)
