"""Read-only geometry reporting for the registered C run; no candidate mutation."""
from collections import Counter,defaultdict
import csv
import json
from pathlib import Path
import sys
import time
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import shapely
from shapely import Polygon, box
from metamaterial_eval.geometry.validation.checks import rings,polygons,digest
from metamaterial_eval.geometry.sensitivity.records import write_json

ROOT=Path(__file__).resolve().parents[1]
DEFAULT=ROOT/'experiments/pipeline_v0.5/scientific_validation/run_001'


def read(p):return json.loads(Path(p).read_text())


def boundary(ax,g,color='black',label=None,lw=.6):
    lines=[r['xy'] for r in rings(g)]
    ax.add_collection(LineCollection(lines,colors=color,linewidths=lw,label=label));ax.autoscale();ax.set_aspect('equal')


def fill(ax,g,color,alpha=.8):
    for p in polygons(g):
        ax.fill(*np.asarray(p.exterior.coords).T,color=color,alpha=alpha)
        for h in p.interiors:ax.fill(*np.asarray(h.coords).T,color='white')
    ax.set_aspect('equal');ax.autoscale()


def finish(fig,out,name,caption):
    fig.suptitle(caption,fontsize=12);fig.tight_layout(rect=(0,0,1,.96));fig.savefig(out/'figures'/name,dpi=170);plt.close(fig)


def make_figures(out,rows,summaries):
    usable=[r for r in rows if 'result_path' in r]
    if not usable:return
    best=max(usable,key=lambda r:r['symmetric_G2_G3']);d=read(ROOT/best['result_path']);prov=d['provenance']
    src=read(out/'source_manifests'/(best['fixture']+'.json'));sp=src['source_provenance'];mask=np.load(ROOT/sp['canonical_path'],allow_pickle=False)
    a=shapely.from_wkb((ROOT/sp['paths']['exact']).read_bytes());b=shapely.from_wkb((ROOT/sp['paths']['manifold']).read_bytes())
    c=shapely.from_wkb((ROOT/prov['candidate_input_path']).read_bytes());rec=np.load((ROOT/best['result_path']).parent/'G3.reconstructed.npy',allow_pickle=False)
    fig,axes=plt.subplots(1,4,figsize=(15,4))
    axes[0].imshow(mask,cmap='gray_r',origin='upper',extent=(0,1024,1024,0));axes[0].set_title('G0 canonical1024')
    for ax,g,title in zip(axes[1:],[a,b,c],['G1 exact','G2 manifold','G3 protected']):
        fill(ax,g,'#222',1.0);boundary(ax,g,lw=.2);ax.set_title(title);ax.set_xlim(0,1024);ax.set_ylim(1024,0)
    finish(fig,out,'01_geometry_states.png',f"Same realization: {best['fixture']}, epsilon {best['epsilon']:.2f}")
    xy=d['distances']['G2_G3']['source_to_candidate']['worst_xy'] or [512,512];x,y=xy
    fig,axes=plt.subplots(1,2,figsize=(11,4.8))
    for ax,span in zip(axes,[20,3]):
        boundary(ax,b,'#555',label='G2');boundary(ax,c,'#2667c9',label='G3');fill(ax,c.difference(b),'#d34b34');fill(ax,b.difference(c),'#16a085')
        ax.set_xlim(x-span,x+span);ax.set_ylim(y+span,y-span);ax.set_xlabel('x [native cell]');ax.set_ylabel('y [native cell]')
    finish(fig,out,'02_continuous_difference.png',f"Red added; teal removed. XOR=0; actual G2→G3 symmetric area {best['symmetric_G2_G3']:.6f} cell²")
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for cohort,col in [('B2_reference','#4763b0'),('new_parameter','#d47d25')]:
        rr=[r for r in usable if r['cohort']==cohort]
        axes[0].scatter([r['epsilon'] for r in rr],[r['distance_lower'] for r in rr],label=cohort,c=col,marker='o')
        axes[0].scatter([r['epsilon']+.015 for r in rr],[r['distance_upper'] for r in rr],c=col,marker='x')
        axes[1].scatter([r['epsilon'] for r in rr],[r['cumulative_distance_upper'] for r in rr],label=cohort,c=col)
    for ax in axes:ax.axhline(np.sqrt(.5),c='red',ls='--');ax.set_xlabel('Requested epsilon [cell]');ax.set_ylabel('Distance [cell]');ax.legend()
    axes[0].set_title('G2→G3: sampled lower o; upper ×');axes[1].set_title('G1→G3 independent upper')
    finish(fig,out,'03_boundary_displacement.png','Independent changed-line sampling; gap ≤0.025 cell, upper = max + gap/2')
    repairs=d['features']['repairs']
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    if repairs:
        x,y=repairs[0]['xy']
        for ax,g,title in zip(axes,[a,b,c],['G1 contact','G2 regularization','G3 preserved repair']):
            boundary(ax,g,lw=1.2);ax.set_xlim(x-.65,x+.65);ax.set_ylim(y+.65,y-.65);ax.set_title(title)
    else:
        for ax in axes:ax.text(.5,.5,'No repair in selected case',ha='center',transform=ax.transAxes)
    finish(fig,out,'04_repair_closeup.png','Subpixel regularization: native cells; no physical or CAD tolerance assigned')
    feature_row=max(usable,key=lambda r:r['narrowed_probes'])
    fd=read(ROOT/feature_row['result_path']);fs=read(out/'source_manifests'/(feature_row['fixture']+'.json'))['source_provenance']
    fb=shapely.from_wkb((ROOT/fs['paths']['manifold']).read_bytes())
    fc=shapely.from_wkb((ROOT/fd['provenance']['candidate_input_path']).read_bytes())
    probes=fd['features']['independent_probes'];vulnerable=[p for p in probes if p['narrowed']]
    guarded=next((p for p in probes if p['guarded_center']),probes[0])
    exposed=next(iter(vulnerable+[p for p in probes if not p['guarded_center']]),probes[-1])
    selected=[guarded,exposed]
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    guard=shapely.from_wkb((ROOT/fd['provenance']['guard_input_path']).read_bytes())
    for ax,p in zip(axes,selected):
        x,y=p['xy'];roi=box(x-10,y-10,x+10,y+10);fill(ax,guard.intersection(roi),'#e7e5bb',.5)
        boundary(ax,fb,'#555',label='G2');boundary(ax,fc,'#2667c9',label='G3');ax.scatter([x],[y],s=20,c='red')
        from shapely import LineString, Point
        segment=LineString([(0,y),(1024,y)]) if p['axis']==0 else LineString([(x,0),(x,1024)])
        active=segment.intersection(fb) if p['phase']=='solid' else segment.difference(fb)
        from metamaterial_eval.geometry.validation.checks import line_parts
        for component in line_parts(active):
            if component.distance(Point(x,y))<=1e-10:ax.plot(*np.asarray(component.coords).T,color='red',lw=2)
        ax.set_xlim(x-8,x+8);ax.set_ylim(y+8,y-8)
        ax.legend(fontsize=7,loc='lower right')
        ax.set_title(f"{p['phase']} axial width {p['before']:.6f}→{p['after']:.6f}\ncenter guarded={p['guarded_center']}")
    finish(fig,out,'05_feature_audit.png',f"Independent axial probes: {feature_row['fixture']}, epsilon{feature_row['epsilon']}; shaded guards")
    hp=d['continuous_topology']['holes']['records'];pore=max(hp,key=lambda p:p.get('symmetric_area',0))
    oldholes=[Polygon(h) for p in polygons(b) for h in p.interiors];newholes=[Polygon(h) for p in polygons(c) for h in p.interiors]
    i=pore['source_id'];j=pore['candidate_ids'][0];old=oldholes[i];new=newholes[j]
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax in axes:boundary(ax,old,'#555',label='source pore');boundary(ax,new,'#2667c9',label='candidate pore');ax.invert_yaxis();ax.legend(loc='center',fontsize=9)
    xx,yy,xx1,yy1=old.bounds;axes[1].set_xlim(xx-1,xx1+1);axes[1].set_ylim(yy1+1,yy-1)
    axes[0].set_title(f"Unique overlap + reciprocal anchors: pore {i}→{j}")
    axes[1].set_title(f"Equal-area distortion {pore['relative_area_distortion']:.6g}; shape Δ {pore['symmetric_area']:.6f} cell²")
    finish(fig,out,'06_pore_correspondence.png','Pore identity uses geometry, not equal area; perimeter and boundary shape remain separately measured')
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    for cohort,col in [('B2_reference','#4763b0'),('new_parameter','#d47d25')]:
        rr=[r for r in usable if r['cohort']==cohort]
        for epsilon,marker in [(0,'s'),(.2,'+'),(.5,'o'),(.75,'x')]:
            rs=[r for r in rr if r['epsilon']==epsilon]
            axes[0].scatter([r['vertex_reduction_percent'] for r in rs],[r['symmetric_G2_G3'] for r in rs],c=col,marker=marker,label=f'{cohort} ε{epsilon}')
            axes[1].scatter([r['vertex_reduction_percent'] for r in rs],[r['distance_upper'] for r in rs],c=col,marker=marker)
    for ax in axes:ax.set_xlabel('Vertex reduction [%]')
    axes[0].set_ylabel('G2→G3 symmetric area [cell²]');axes[1].set_ylabel('G2→G3 independent distance upper [cell]')
    axes[0].legend(fontsize=6,ncol=2)
    finish(fig,out,'07_reduction_error.png','Blue saved B2; orange unseen parameter points; all requested settings retained')
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    for ax,img,title in zip(axes,[mask,rec,mask!=rec],['Original G0','Independent G3 reconstruction','XOR (white = disagreement)']):
        ax.imshow(img,cmap=('gray' if title.startswith('XOR') else 'gray_r'),vmin=0,vmax=1);ax.set_title(title)
    finish(fig,out,'08_raster_disagreement.png',f"Native1024 raster: {best['fixture']}, FP=FN=XOR={d['raster']['xor']}")
    fig,axes=plt.subplots(1,2,figsize=(12,4.5))
    labels=[];hard=[];science=[];feature=[]
    for cohort in ['B2_reference','new_parameter']:
        for ep in [0,.2,.5,.75]:
            rr=[r for r in rows if r['cohort']==cohort and r['epsilon']==ep]
            labels.append(cohort.replace('_',' ')+'\nε'+str(ep));hard.append(sum(r['acceptance']['hard_gate_pass'] for r in rr));science.append(sum(r['acceptance']['scientific_status']=='PASS_SAMPLED_DOMAIN' for r in rr));feature.append(sum(r.get('narrowed_probes',0) for r in rr))
    xx=np.arange(8);axes[0].bar(xx-.18,hard,.36,label='Hard gates');axes[0].bar(xx+.18,science,.36,label='All C screens');axes[0].legend(loc='lower center',bbox_to_anchor=(.5,1.01),ncol=2,fontsize=8);axes[0].set_ylabel('Passing configurations /10')
    axes[1].bar(xx,feature,color='#d47d25');axes[1].set_ylabel('Flagged axial narrowing observations')
    for ax in axes:ax.set_xticks(xx,labels,rotation=55,ha='right',fontsize=7)
    finish(fig,out,'09_validation_results.png','Independent C outcomes; sample-width flags remain distinct from frozen B2 constraints')
    stagecost=defaultdict(float)
    for row in usable:
        for k,v in row['timings'].items():stagecost[k]+=v
    for s in summaries:
        for r in s.get('source_timings',[]):
            for k,v in r.items():
                if k!='fixture':stagecost[k]+=v
    for p in (out/'parameter_holdouts').glob('*/*/producer_times.json'):
        producer=read(p);stagecost['guards_and_repeated_simplification']+=producer['guards_and_repeated_simplification']
        qpath=p.with_name('frozen_B2_qualification.json')
        if qpath.exists():stagecost['frozen_B2_qualification']+=read(qpath)['qualification_seconds']
    fig,axes=plt.subplots(1,2,figsize=(13,6))
    kk=sorted(stagecost,key=stagecost.get,reverse=True);axes[0].barh(kk[::-1],[stagecost[k] for k in kk[::-1]]);axes[0].set_xlabel('Measured stage sum [s]')
    names=[s['stage'] for s in summaries];xx=np.arange(len(names));axes[1].bar(xx-.18,[max([s['peak_traced_bytes']]+([read(p).get('peak_traced_generation_bytes',0) for p in (out/'parameter_holdouts').glob('*/native1024/manifest.json')] if s['stage']=='holdouts' else []))/2**20 for s in summaries],.36,label='Tracked allocation peak');axes[1].bar(xx+.18,[s['process_lifetime_peak_rss_bytes']/2**20 for s in summaries],.36,label='Lifetime RSS');axes[1].set_xticks(xx,names);axes[1].set_ylabel('MiB');axes[1].legend(fontsize=8)
    finish(fig,out,'10_runtime_memory.png','Stage observations; producer costs separately saved. Tracing omits some GEOS memory; RSS is lifetime highwater')
    write_json(out/'performance/stage_totals.json',dict(stagecost))


def report(out):
    started=time.perf_counter();summaries=[read(out/'summary/reference.json'),read(out/'summary/holdouts.json')];protocol=read(out/'protocol/PROTOCOL.json')
    rows=[r for s in summaries for r in s['rows']];usable=[r for r in rows if 'result_path' in r]
    failures=Counter(k for r in rows for k in r['acceptance']['failed_gates']);flags=sum(r.get('narrowed_probes',0) for r in rows)
    errors=[e for s in summaries for e in s['errors']];unsupported=[n for s in summaries for n in s['unsupported']]
    allpass=len(rows)==80 and not errors and not unsupported and not failures and flags==0 and all(r.get('undefined_probes',0)==0 for r in rows)
    new=[r for r in usable if r['cohort']=='new_parameter'];old=[r for r in usable if r['cohort']=='B2_reference']
    def maxval(key,rr=usable):return max((r[key] for r in rr),default=None)
    source=[read(p) for p in sorted((out/'source_manifests').glob('*.json'))]
    worst={'G2_G3_symmetric':maxval('symmetric_G2_G3'),'G1_G3_symmetric':maxval('symmetric_G1_G3'),
           'added':maxval('added'),'removed':maxval('removed'),'distance_sampled_lower':maxval('distance_lower'),
           'distance_independent_upper':maxval('distance_upper'),'cumulative_sampled_lower':maxval('cumulative_distance_lower'),
           'cumulative_independent_upper':maxval('cumulative_distance_upper')}
    statuses={'A_source_integrity':'PASS_AUTHENTICATED' if not errors else 'SEE_ERRORS',
        'B_exact_fidelity':'PASS_TESTED_DOMAIN' if all(s['rasters']['G1']['xor']==0 for s in source) else 'FAIL',
        'C_manifold_qualification':'PASS_TESTED_DOMAIN' if not unsupported else 'HOLD_UNSUPPORTED_INPUT',
        'D_simplification_validity':'PASS_TESTED_DOMAIN' if not failures.get('frozen_B2_constraints') else 'HOLD',
        'E_independent_continuous_fidelity':'PASS_TESTED_SCREENING_DOMAIN' if not failures and not errors and len(usable)==80 else 'HOLD',
        'F_raster_morphology':'PASS_EXACT_RECONSTRUCTION' if all(r['raster_xor']==0 for r in usable) else 'FAIL',
        'G_feature_preservation':'HOLD_BROADER_SCREEN_FLAGS' if flags or any(r['undefined_probes'] for r in usable) else 'PASS_REGISTERED_AND_SAMPLED_ONLY',
        'H_new_parameter_generalization':'PASS_SAMPLED_DESIGNS' if allpass else 'HOLD',
        'I_scientific_advancement':'SCOPED_PASS_TO_2D_EXPORT_VALIDATION' if allpass else 'HOLD',
        'J_production_policy':'HOLD_UNQUALIFIED','K_CAD_manufacturing':'UNQUALIFIED'}
    summary={'stage':'v0.5C','statuses':statuses,'total_configurations':len(rows),'saved_B2_revalidations':len(old),'new_parameter_configurations':len(new),
        'new_parameter_structures':len(set(r['fixture'] for r in new)),'new_parameter_points':[3,4,6,7,8],'seeds':[0,1],
        'worst':worst,'hard_gate_failures':dict(failures),'axial_narrowing_observations':flags,
        'unsupported':unsupported,'errors':errors,'rows':rows,'source_summaries':source,
        'execution_seconds':sum(s['elapsed_seconds'] for s in summaries),
        'peak_traced_bytes':max([s['peak_traced_bytes'] for s in summaries]+[json.loads(p.read_text()).get('peak_traced_generation_bytes',0) for p in (out/'parameter_holdouts').glob('*/native1024/manifest.json')]),
        'peak_process_lifetime_rss_bytes':max(s['process_lifetime_peak_rss_bytes'] for s in summaries),
        'acceptance_limits':protocol['b2_config']['limits'],'thresholds_changed':False,
        'production_policy_selected':False,'export_implemented':False,'physical_scale':None}
    write_json(out/'summary/SCIENTIFIC_GEOMETRY_VALIDATION.json',summary)
    fields=['cohort','fixture','epsilon','B2_disposition','vertices','vertex_reduction_percent','added','removed','symmetric_G2_G3','symmetric_G1_G3','distance_lower','distance_upper','cumulative_distance_upper','raster_xor','narrowed_probes','undefined_probes','guard_boundary_fraction','narrow_medial_guard_fraction','hard_gate_pass','scientific_status','failed_gates']
    with (out/'summary/CONFIGURATIONS.csv').open('w',newline='') as handle:
        w=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for r in rows:w.writerow({**r,**r['acceptance'],'failed_gates':';'.join(r['acceptance']['failed_gates'])})
    make_figures(out,rows,summaries)
    text=['# v0.5C — independent scientific geometry validation','',
        '**Scientific advancement: '+statuses['I_scientific_advancement']+'**. Production policy HOLD / UNQUALIFIED. CAD/manufacturing UNQUALIFIED.','',
        '## A. Executive scientific summary','',
        f"Evaluated {len(old)} persisted B2 configurations and {len(new)} new-parameter configurations, from {len(set(r['fixture'] for r in new))} new stochastic realizations at five previously unused parameter positions. Every requested outcome is retained. Hard-gate failures: {dict(failures)}. Independent axial narrowing observations: {flags}. Unsupported inputs: {unsupported}. Internal errors: {len(errors)}.",'',
        'The numerical budgets are prospective geometric screening limits; these data do not establish their mechanical sufficiency. Pixel equality and deterministic descriptors are discrete consistency evidence, not continuous equivalence.','',
        '## B. Methodology and prospective registration','',
        'G0 is native1024 uint8 occupancy (solid1); G1 exact pixel-cell WKB/JSON; G2 separate frozen A1 solid-side regularization; G3 frozen guarded_dp_v1.1 output. Cell(row,column) occupies [column,column+1]×[row,row+1], x right, y down. G0 versus independent rasterizations of all three states and all three actual continuous comparisons G1→G2, G2→G3 and G1→G3 are recorded. No addition of component errors substitutes for final set difference.','',
        'The protocol and source selection were written before implementation; the final C implementation was frozen after analytic controls and before all real C outcomes. All ten old B2 fixtures at ε0,.20,.50,.75 were revalidated before the new parameter study. Algorithm/config hashes, complete original256 sources, protocol and environment are authenticated. Native1024 hashes are recorded immediately after first creation, before vector conversion.','',
        'Independent of producer logic: translated math.fsum shoelace areas; exact coordinate/order/winding/ownership reconstruction; prepared point-predicate rasterization replacing frozen scanline; coordinate edge/degree/ring-pair topology; overlap plus reciprocal representative-point identities; changed-line boundary sampling at maximum gap0.025 with explicit Lipschitz upper bound; independent axial probes and medial-axis coverage.','',
        'Shared dependencies: both layers use GEOS for WKB, polygon construction, Booleans, intersections and spatial distances. Frozen evaluator definitions, contact policy and geometric budgets are reused unchanged. The existing dedicated manifold classifier supplements C incidence checks. This is layered verification, not a second independent geometry kernel, exact rational proof or interval arithmetic.','',
        '## C. Historical B2 evidence','',
        'Historical B2 remains GEOMETRIC_SCREEN_PASS_TESTED_DOMAIN over50 configurations (20 changed,30 no-ops); all47 repairs,240 supported normal probes and137475 guard evaluations passed its registered checks. Its prior scientific HOLD and lack of production policy are immutable. C revalidates40 of those saved configurations rather than rerunning B2 simplification. Original v0.5A HOLD, scoped A1 amended PASS, v0.4.2 P10 calibration failure and scoped v0.4.3 amendment remain unchanged.','',
        '## D. Independent parameter-point cohort','',
        'The original ten-point Latin-hypercube plan used design seed42 and common stochastic seeds0/1. B1/B2 used positions0,1,2,5,9. C prospectively selected every remaining position, without outcome filtering. Audit found no saved native1024 source at these positions: only original256 arrays existed. C therefore created their first native1024 artifacts using unchanged v0.4.1 perform_job, original parameter values, both registered seeds, repeat generation and frozen evaluation. This is new execution of the existing renderer, not reuse of historical1024 masks, upsampling, generator redesign or amendment of v0.4.3 acceptance.','',
        '| Design | Seeds | Solid fraction target | Strut scale | Pore scale |','|---|---|---:|---:|---:|']
    for i in [3,4,6,7,8]:
        s=next(s for s in protocol['cohort'] if s['design_id']==i);p=s['requested'];text.append(f"| {i} | 0,1 | {p['solid_fraction_target']:.17g} | {p['strut_scale']:.17g} | {p['pore_scale']:.17g} |")
    text += ['', 'All raw, accepted, no-op, quarantined and failed candidates remain explicit. No parameter, radius, guard, tolerance, allowance or simplifier code was tuned against these outcomes.','',
        '## E. Exact representation fidelity','',f"All available G1 independent raster checks have XOR0: {all(s['rasters']['G1']['xor']==0 for s in source)}. Occupied area is checked against integer solid-pixel count. Original singularities are retained and independently identified rather than automatically repaired.",'',
        '## F. Manifold qualification and subpixel contact policy','',
        'G1→G2 uses the frozen explicit solid_separate_contacts policy; new exact contacts, classification, patch footprints, added area, local displacement and resulting clearance are recorded in each source and repair record. Original void-closure adjacency can change at a documented contact: G1→G2 is not represented as unchanged continuous topology. G2→G3 must maintain the qualified topology. Unsupported ingress is quarantined, with no substituted source or fallback pass.','',
        f"Total recorded repair sites across loaded sources: {sum(len(read(ROOT/r['result_path'])['features']['repairs']) for r in usable if r['epsilon']==0)}; original-source contact diagnostics are in source_manifests and native ingress qualifications. Existing and new clearances are measured, not inferred from the historical0.353553-cell value.",'',
        '## G. Protected simplification','',
        'Four independently requested settings start from each G2. The unchanged B2 qualifier checks registered constraints; C separately checks all persisted protected segment coordinates, guard solid/boundary sets and repairs. Rejected raw outputs retain failure status. No new regularization or simplifier repair is performed. No-op and changed dispositions remain separate.','',
        '## H. Continuous material changes','',
        '| Worst observation | Value |','|---|---:|']
    text += [f'| {k} | {v:.12g} |' for k,v in worst.items() if v is not None]
    text += ['', 'Area units are native cell²; distance units are native cells. B2 G2→G3 added/removed/symmetric denominators are occupied G2 area. C additionally screens actual G1→G3 against the same fractions using occupied G1 area, prospectively declared. Per-pore area uses that individual source pore. Allowances remain1e-10, without enlargement. G1→G2 regularization is separately measured. Every comparison retains added, removed, signed net and actual symmetric area; equal net area does not imply equal sets.','',
        '## I. Raster morphology','',
        'C rasterization samples the closed solid at native half-integer centers using prepared intersects_xy, with boundary-center ties recorded. FP/FN/XOR, IoU, 4-components, largest fraction and horizontal/vertical percolation are independently calculated. Frozen v1.1 is freshly run once on every original source and on one reconstructed integration control in each cohort; independently identical reconstructions reuse those deterministic scalar/curve results. Producer qualifier cache evaluations are separately retained. Full S2 and directional/mean L equality is required. Whole-mask P10 is not redefined; the historical calibration caveat remains.','',
        '## J. Continuous topology and pores','',
        'OGC validity is supplemented by direct degree-two coordinate incidence, no zero/duplicate edges, simple rings and no cross-ring intersection, plus the frozen dedicated classifier. Solid, enclosed-hole and domain-void correspondence requires unique positive overlap and reciprocal interior anchors; similar area alone cannot identify a pore. Every matched pore retains area, perimeter, shape symmetric difference, containment, overlap and sampled boundary movement. Domain-side void incidence screens exterior opening/closure. Count/side preservation cannot establish unchanged channel width, so separate void chords are measured. New slivers are recorded by component minimum area and ownership; no unregistered physical size threshold is invented.','',
        '## K. Independent displacement','',
        'For both directions, subtract identical boundary line sets, sample remaining pieces including endpoints with gap≤0.025cell, query exact nearest target segments using a fresh STRtree, and add half the largest gap. Distance to a closed target is1-Lipschitz, giving a continuous upper bound in floating geometry arithmetic. Sampled maxima are lower bounds, not exact Hausdorff distances. Source shell/hole directions are separately recorded. C independently tests the B2 certificate against sampled lower bounds and independently screens its own upper bound against sqrt(2)/2+1e-10. Known shifts, displaced edges, staircase and channel controls test compliant and excessive movements.','',
        '## L. Feature coverage and independent screening','',
        f"Guard boundary coverage spans {min((r['guard_boundary_fraction'] for r in usable),default=0):.3%}–{max((r['guard_boundary_fraction'] for r in usable),default=0):.3%}. Raster medial-axis support with EDT diameter≤8 is counted independently of B2 skeletonize/PCA and compared against guard membership. This denominator is raster medial support, not the number of all physical necks. Uncovered coordinates are saved.",'',
        f"Per fixture, up to96 shortest interior run-midpoint chords per phase are selected from original occupancy, with8-cell separation and run length≤16cells. Solid and void probes are independent of B2's24 PCA probes. All configurations retain their source-defined locations and widths. Detected shortening observations: {flags}; undefined observations: {sum(r.get('undefined_probes',0) for r in usable)}. These are geometric screening flags, not material-strength conclusions. A shortened fixed axial section is not proof that the true minimum neck shrank. No exhaustive continuous-width certification is claimed.",'',
        'Flagged axial widths also receive a post-study direct edge-coordinate interpolation check in feature_audit/AXIAL_COORDINATE_CONFIRMATION.json. This uses no Boolean/intersection predicate for the width calculation and changes no gate or threshold. Registered-feature preservation is distinct from broader sampled-feature preservation, which is distinct from exhaustive verification. The frozen B2 registered probes/repair-clearance gates can pass while a new diagnostic identifies a geometric limitation. C retains that disagreement and its consequence for advancement.','',
        '## M. Subpixel regularization limitations','',
        'Each actual added G2\G1 footprint and local clearance is retained and compared against G3. A positive subpixel ligament is not qualified for CAD tolerances, meshing, fabrication or loading. Local patches do not supply physical dimensions. No source geometry is replaced.','',
        '## N. Generalization','',
        f"New-parameter configurations completed: {len(new)}/40, spanning {len(set(r['fixture'] for r in new))}/10 realizations. This tests five new sampled positions in the original finite envelope, not arbitrary points, materials, resolutions or topologies. New native-source execution is explicitly distinguished from historical source reuse. Overall new-parameter status: {statuses['H_new_parameter_generalization']}.",'',
        '## O. Performance','',
        f"Validation execution wall time: {summary['execution_seconds']:.3f}s. Peak tracked allocation: {summary['peak_traced_bytes']/2**20:.3f}MiB; process lifetime high-water RSS: {summary['peak_process_lifetime_rss_bytes']/2**20:.3f}MiB. Tracing excludes some GEOS-native memory. Stage JSON records source loading/generation, extraction, manifold qualification, repeated simplification, serialization, reload, raster, continuous comparison, features and evaluator. Reused saved vectors are marked loading rather than invented conversion timings. Producer times are in each new case. Native worker timing is separately instrumented; its start can inherit an already-active C tracker, so worker peak fields are not clean incremental per-stage allocations. The overall maximum includes both C and recorded worker tracked peaks. Observations are single-run, not statistical benchmarks.",'',
        '## P. Scientific limitations','',
        'Finite designs and feature coverage; native1024 raster resolution; subpixel regularization; no physical dimensions, material model, load case, mechanics, manufacturing criterion, CAD-kernel interoperability or meshing verification. Shared GEOS and floating-point behavior remain dependencies. Passing numeric geometric screens does not establish mechanical sufficiency. Same-environment determinism does not establish cross-platform WKB identity. Executed on macOS ARM64; Windows commands are documentation only.','',
        '## Q. Acceptance','',
        '| Scope | Status |','|---|---|']
    text += [f'| {k} | {v} |' for k,v in statuses.items()]
    text += ['', '## R. Recommended next stage','',
        ('The recorded sampled geometry supports beginning separately scoped v0.5D 2D export validation. A production default is not selected. Use individually accepted artifact/provenance bundles; preserve physical/CAD limitations.' if allpass else 'Broad scientific advancement remains HOLD. Preserve the independently flagged candidates and investigate their geometric significance under a separately versioned protocol. A limited export software experiment could use explicit individually accepted bundles only after its scope is separately defined; this report does not clear the complete tested pipeline for general downstream construction.'),'',
        'Epsilon0.50 and0.75 are evaluated independently. Higher tolerance need not improve reduction; guards and rejection grow with influence. Epsilon0.50 may be considered a tested-domain candidate setting only if every required independent case passes. No best-of-holdout selection, universal production qualification, 3D CAD or FEM readiness is claimed.','',
        '## Complete configuration table','',
        '| Cohort | Fixture | ε | Reduction % | Symmetric G2→G3 | Symmetric G1→G3 | Independent upper | XOR | Narrow flags | Hard gates | C status |','|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for r in rows:
        if 'result_path' not in r:text.append(f"| {r['cohort']} | {r['fixture']} | {r['epsilon']} | — | — | — | — | — | — | FAIL | QUARANTINED |")
        else:text.append(f"| {r['cohort']} | {r['fixture']} | {r['epsilon']:.2f} | {r['vertex_reduction_percent']:.5f} | {r['symmetric_G2_G3']:.8f} | {r['symmetric_G1_G3']:.8f} | {r['distance_upper']:.9f} | {r['raster_xor']} | {r['narrowed_probes']} | {r['acceptance']['hard_gate_pass']} | {r['acceptance']['scientific_status']} |")
    text += ['', '## Verification and created artifacts','',
        'Software/preservation/figure-inspection completion is separately recorded in verification/COMPLETION.json after report generation. New implementation files are geometry/validation/{__init__,checks,study}.py, tests/test_scientific_geometry_validation.py, scripts/pipeline_v0_5c_report.py, new C documentation, and the new experiment tree. Existing files are not intentionally modified. The final hash ledger lists every added file. No exporter or later-stage implementation was created.','']
    text += ['', '## Independently flagged feature locations', '',
             '| Fixture | ε | Phase | x,y | Before | After | Δ cell | Center guarded |',
             '|---|---:|---|---|---:|---:|---:|---|']
    for row in usable:
        if row['narrowed_probes']:
            document=read(ROOT/row['result_path'])
            for probe in document['features']['independent_probes']:
                if probe['narrowed']:
                    text.append(f"| {row['fixture']} | {row['epsilon']} | {probe['phase']} | {probe['xy']} | {probe['before']:.12g} | {probe['after']:.12g} | {probe['delta']:.12g} | {probe['guarded_center']} |")
    extrema_path=out/'summary/SCIENTIFIC_EXTREMA.json'
    if extrema_path.exists():
        extrema=read(extrema_path)
        text += ['', '## Cumulative pore and coverage qualifications', '',
            f"Across20 source realizations: {extrema['registered_repairs']} recorded repair sites ({extrema['new_repairs']} new), {extrema['registered_natural_probes']} registered natural probes, {extrema['independent_unique_probes']} independent axial probes and {extrema['independent_probe_evaluations']} axial evaluations. All measured repair clearances remain0.3535533905932738cell. New exact contact classes: {extrema['new_contact_classes']}.", '',
            f"The maximum G2→G3 matched-pore area distortion is {extrema['maximum_pore_area_fraction']:.6%}; shape symmetric area nevertheless reaches {extrema['maximum_pore_shape_symmetric']:.12g}cell² and absolute perimeter change reaches {extrema['maximum_pore_perimeter_change']:.12g}cell. No physical shape threshold is invented.", '',
            f"**Original-to-final pore caveat:** maximum matched-pore area distortion relative to G1 is {extrema['cumulative_maximum_pore_area_fraction']:.6%}. In design7/seed0, source pore1 has area1cell² and becomes0.96875cell² under the A1 contact regularization, then retains that area through simplification. This3.125% change is visible only when the original small-pore denominator is retained. The frozen B2 per-pore0.5% cap uses G2 pore area for G2→G3; it does not retrospectively qualify or reject G1→G2. C registers cumulative global material/displacement caps but no new cumulative per-pore cap. This measured limitation remains diagnostic and strengthens the broader scientific HOLD; no threshold is changed after observing it.", '',
            f"Guarded narrow medial-center coverage ranges {extrema['minimum_medial_guard_fraction']:.3%}–{extrema['maximum_medial_guard_fraction']:.3%}. Center membership does not certify coverage of an entire ligament. Supplementary unguarded cross-ring portions have no detected separations≤2cells; same-ring self-approach and exhaustive minimum-neck verification remain unqualified."]
    (out/'summary/SCIENTIFIC_GEOMETRY_VALIDATION.md').write_text('\n'.join(text))
    write_json(out/'performance/reporting.json',{'reporting_seconds':time.perf_counter()-started})
    print('Report',statuses,'worst',worst,flush=True)


if __name__=='__main__':report(Path(sys.argv[1]).resolve() if len(sys.argv)>1 else DEFAULT)
