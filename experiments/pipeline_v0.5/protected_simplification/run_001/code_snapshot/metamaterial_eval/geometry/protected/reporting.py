"""Recorded outcomes, diagnostic figures and scoped geometric-screen acceptance."""
from collections import Counter
import csv
import json
from pathlib import Path
import numpy as np
import shapely
from shapely import box, Polygon, LineString
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ..sensitivity.reporting import _draw
from ..sensitivity.distance import line_components
from ..sensitivity.records import write_json
from .settings import ROOT
from .model import BoundaryModel


def read(path):return json.loads(Path(path).read_text())


def draw_lines(ax,geometry,color,origin=(0,0),**kwargs):
    if geometry.geom_type in ('Polygon','MultiPolygon'):geometry=geometry.boundary
    for line in line_components(geometry):
        xy=np.asarray(line.coords)-np.asarray(origin)
        ax.plot(xy[:,0],xy[:,1],color=color,**kwargs)


def save(fig,output,name):
    fig.savefig(output/'figures'/(name+'.png'),dpi=210,bbox_inches='tight');plt.close(fig)


def report(output):
    output=Path(output);config=read(output/'protocol.json')['config']
    summaries={stage:read(output/'summary'/(stage+'.json')) for stage in ('development','holdout')}
    rows=[{**r} for s in summaries.values() for r in s['candidates']]
    usable=[r for r in rows if 'relative_directory' in r]
    grouped={name:sorted([r for r in usable if r['fixture']==name],key=lambda r:r['epsilon']) for name in config['development']+config['holdouts']}
    baseline={name:read(output/data[0]['stage']/name/'baseline.json') for name,data in grouped.items() if data}
    details={r['relative_directory']:read(output/r['relative_directory']/'qualification.json') for r in usable}
    counts=Counter(r['disposition'] for r in rows)
    accepted=[r for r in usable if r['disposition']=='ACCEPTED_CANDIDATE']
    noops=[r for r in usable if r['disposition']=='ACCEPTED_NOOP']
    errors=sum(len(s['internal_errors']) for s in summaries.values());unsupported=sum(len(s['unsupported_ingress']) for s in summaries.values())
    status='GEOMETRIC_SCREEN_PASS_TESTED_DOMAIN' if not errors and not unsupported and len(usable)==50 and len(accepted)+len(noops)==50 else 'GEOMETRIC_SCREEN_PARTIAL_OR_HOLD'
    conclusions={'stage':'v0.5B2','implementation_status':'IMPLEMENTED_AND_STUDIED','geometric_screen_status':status,
        'broader_scientific_physical_acceptance':'HOLD_UNQUALIFIED_NUMERIC_BUDGET_SUFFICIENCY_AND_GENERALITY',
        'counts':dict(counts),'development_configurations':len(summaries['development']['candidates']),
        'holdout_configurations':len(summaries['holdout']['candidates']),'unsupported_holdout_ingress':summaries['holdout']['unsupported_ingress'],
        'raw_global_rejections':sum(r.get('global_rollback',False) for r in usable),
        'local_chord_rejections':sum(r['rejected_chords'] for r in usable),
        'local_rollbacks':sum(r['local_rollbacks'] for r in usable),
        'unchanged_eligible_chains':sum(r['no_op_chains'] for r in usable),
        'protected_chain_instances':sum(r['protected_chains'] for r in usable),
        'accepted_candidate_paths':[r['relative_directory']+'/candidate.wkb' for r in accepted],
        'accepted_noop_paths':[r['relative_directory']+'/candidate.wkb' for r in noops],
        'maximum_vertex_reduction_percent':max((r['vertex_reduction_percent'] for r in usable),default=None),
        'maximum_certified_displacement_cell':max((r['boundary_certified_upper'] for r in usable),default=None),
        'maximum_measured_displacement_cell':max((r['boundary_measured_lower'] for r in usable),default=None),
        'all_accepted_raster_xor_zero':all(r['raster_xor']==0 for r in accepted+noops),
        'all_accepted_gates_pass':all(all(details[r['relative_directory']]['gates'].values()) for r in accepted+noops),
        'production_policy_selected':False,'v0_5C_implemented':False,'v0_5_complete':False,
        'eligible_for_separately_authorized_v0_5C_investigation':status=='GEOMETRIC_SCREEN_PASS_TESTED_DOMAIN',
        'eligibility_scope':'Only explicitly accepted WKB with its qualification/provenance under this prospective geometric screen; not a production policy or export certificate.',
        'performance':{stage:{k:s[k] for k in ('elapsed_seconds','peak_traced_bytes','process_lifetime_peak_rss_bytes')} for stage,s in summaries.items()},
        'candidate_rows':rows}
    write_json(output/'summary/ACCEPTANCE.json',conclusions)
    flat=[{k:v for k,v in r.items() if k not in ('engine_timing','failed_constraints')} for r in usable]
    if flat:
        with (output/'summary/RESULTS.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False})
    def line_figure(fields,titles,units,name):
        fig,axes=plt.subplots(1,len(fields),figsize=(6*len(fields),4.7),layout='constrained',squeeze=False)
        for index,(fixture,data) in enumerate(grouped.items()):
            if not data:continue
            color=f'C{index%5}';style='-' if data[0]['stage']=='development' else '--'
            for ax,field,title,unit in zip(axes.flat,fields,titles,units):
                ax.plot([r['epsilon'] for r in data],[r[field] for r in data],'.'+style,color=color,label=fixture)
                ax.set(xlabel='Requested ε (cell)',ylabel=unit,title=title)
        axes.flat[0].legend(fontsize=7,ncol=2)
        fig.suptitle('Solid=development; dashed=reserved holdouts. All settings start from the accepted source.')
        save(fig,output,name)
    line_figure(['vertex_reduction_percent'],['Accepted reduction (including no-ops)'],['Vertices removed (%)'],'05_vertex_reduction')
    line_figure(['added_area','removed_area','symmetric_area'],['Added solid','Removed solid','Symmetric difference'],['cell²']*3,'06_continuous_material_changes')
    line_figure(['boundary_measured_lower','boundary_certified_upper'],['Independent sampled lower distance','Matched-chain continuous certificate'],['cell']*2,'07_boundary_displacement')
    # Required accepted/rejected/no-op distinctions are explicit in a disposition grid.
    fig,ax=plt.subplots(figsize=(10,6),layout='constrained')
    for i,name in enumerate(grouped):
        for r in grouped[name]:
            marker='o' if r['disposition']=='ACCEPTED_CANDIDATE' else 's' if r['disposition']=='ACCEPTED_NOOP' else 'x'
            ax.scatter(r['epsilon'],i,marker=marker,color=f'C{i%5}',s=55)
            if r['global_rollback']:ax.scatter(r['epsilon'],i+.16,marker='x',color='red',s=35)
    ax.set(yticks=range(len(grouped)),yticklabels=list(grouped),xlabel='ε (cell)',title='○ accepted change; □ accepted no-op; red × raw global rejection')
    save(fig,output,'11_dispositions')
    for representative in ('design_000_seed_000','design_009_seed_001'):
        if not grouped[representative]:continue
        r=next(r for r in grouped[representative] if r['epsilon']==.5);b=baseline[representative]
        exact=shapely.from_wkb((ROOT/b['provenance']['paths']['exact']).read_bytes())
        source=shapely.from_wkb((ROOT/b['provenance']['paths']['manifold']).read_bytes())
        candidate=shapely.from_wkb((output/r['relative_directory']/'candidate.wkb').read_bytes())
        fig,axes=plt.subplots(1,3,figsize=(15,5.4),layout='constrained')
        for ax,g,title in zip(axes,[exact,source,candidate],['Exact reference','Accepted manifold source',f"B2 ε=.50; {r['vertex_reduction_percent']:.3f}% reduction"]):
            _draw(ax,g);ax.set(xlim=(0,1024),ylim=(1024,0),xlabel='x (cell)',ylabel='y down (cell)',title=title);ax.set_aspect('equal')
        fig.suptitle(representative+' — separate geometry states; full-field appearance cannot establish local fidelity')
        save(fig,output,'01_full_structure_'+representative)
    # Repair overlays show all fixed native-coordinate details and guard extents.
    repair_examples=[]
    for fixture in config['development']:
        if fixture not in baseline:continue
        p=baseline[fixture]['registered_features']['repairs']
        if p:repair_examples.append((fixture,p[0]))
    fig,axes=plt.subplots(1,len(repair_examples),figsize=(5*len(repair_examples),5),layout='constrained',squeeze=False)
    for ax,(fixture,p) in zip(axes.flat,repair_examples):
        row=next(r for r in grouped[fixture] if r['epsilon']==.75);b=baseline[fixture];origin=np.array(p['xy']);x,y=origin
        source=shapely.from_wkb((ROOT/b['provenance']['paths']['manifold']).read_bytes());candidate=shapely.from_wkb((output/row['relative_directory']/'candidate.wkb').read_bytes())
        guard=next(g for g in read(output/row['relative_directory']/'guards.json') if g.get('repair_id')==p['contact_id'])
        shape=shapely.from_wkb(bytes.fromhex(guard['geometry_wkb_hex']));window=box(x-2.5,y-2.5,x+2.5,y+2.5)
        draw_lines(ax,source.boundary.intersection(window),'#777777',origin,lw=2.5)
        draw_lines(ax,candidate.boundary.intersection(window),'#0086bb',origin,lw=1)
        draw_lines(ax,shape.boundary,'#cc3377',origin,ls='--',lw=1)
        radius=p['L1_radius'];draw_lines(ax,Polygon([(x-radius,y),(x,y-radius),(x+radius,y),(x,y+radius)]),'#ddaa00',origin,lw=1)
        ax.set(xlim=(-2.5,2.5),ylim=(2.5,-2.5),xlabel='Δx (cell)',ylabel='Δy down (cell)',title=f'{fixture}\nrepair {p["xy"]}; ε=.75');ax.set_aspect('equal')
    fig.suptitle('Grey=source; blue=final; magenta=guard; gold=registered repair diamond')
    save(fig,output,'02_repair_guard_closeups')
    # Supported natural chord measurements and connector comparisons.
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for i,(name,data) in enumerate(grouped.items()):
        if not data:continue
        values=[];local=[]
        for r in data:
            d=details[r['relative_directory']];f=d['metrics']['features']
            values.append(max((abs(p['width_change']) for p in f['natural_necks'] if p['width_change'] is not None),default=0))
            local.append(max((p['boundary_displacement']['measured_max'] or 0 for p in f['repairs']+f['natural_necks']+f['boundary_necks']),default=0))
        axes[0].plot([r['epsilon'] for r in data],values,'.-',label=name,color=f'C{i%5}',alpha=1 if i<5 else .5)
        axes[1].plot([r['epsilon'] for r in data],local,'.-',color=f'C{i%5}',alpha=1 if i<5 else .5)
    axes[0].set(xlabel='ε',ylabel='Maximum absolute normal-chord change (cell)',title='Registered supported local widths')
    axes[1].set(xlabel='ε',ylabel='Maximum sampled local displacement (cell)',title='Repair / natural / connector neighborhoods')
    axes[0].legend(fontsize=7,ncol=2)
    save(fig,output,'03_neck_and_local_displacement')
    # Representative boundary portions: full original segments, not center pins.
    name='design_000_seed_000';r=next(r for r in grouped[name] if r['epsilon']==.5);b=baseline[name]
    source=shapely.from_wkb((ROOT/b['provenance']['paths']['manifold']).read_bytes());model=BoundaryModel(source)
    gs=read(output/r['relative_directory']/'guards.json');locked=sorted({s for g in gs for s in g['protected_segments']})
    protected=np.zeros(len(model.lines),dtype=bool);protected[locked]=True
    candidate=shapely.from_wkb((output/r['relative_directory']/'candidate.wkb').read_bytes());window=box(0,264,64,328)
    fig,ax=plt.subplots(figsize=(8,7),layout='constrained')
    draw_lines(ax,shapely.union_all(model.lines[~protected]).intersection(window),'#999999',lw=.7)
    draw_lines(ax,shapely.union_all(model.lines[protected]).intersection(window),'#cc3377',lw=1.5)
    draw_lines(ax,candidate.boundary.difference(source.boundary).intersection(window),'#0086bb',lw=1.4)
    ax.set(xlim=(0,64),ylim=(328,264),xlabel='x (cell)',ylabel='y down (cell)',title='D0 ε=.50: grey eligible, magenta protected, blue new chords');ax.set_aspect('equal')
    save(fig,output,'04_protected_and_eligible_segments')
    fig,axes=plt.subplots(1,2,figsize=(12,4.7),layout='constrained')
    for i,(name,data) in enumerate(grouped.items()):
        if not data:continue
        scalar=[];curves=[]
        for r in data:
            d=details[r['relative_directory']]['metrics']['morphology']['comparison']
            scalar.append(max(abs(x['difference'] or 0) for x in d['scalars'].values()))
            curves.append(max(x['nrmse_reference_rms'] for x in d['curves'].values()))
        axes[0].plot([r['epsilon'] for r in data],scalar,'.-',color=f'C{i%5}',label=name)
        axes[1].plot([r['epsilon'] for r in data],curves,'.-',color=f'C{i%5}')
    axes[0].set(xlabel='ε',ylabel='Largest absolute scalar difference',title='Frozen v1.1 scalar identity')
    axes[1].set(xlabel='ε',ylabel='Largest curve NRMSE',title='Frozen S2 / all L curve identity')
    axes[0].legend(fontsize=7,ncol=2)
    save(fig,output,'08_frozen_morphology')
    examples={}
    for r in usable:
        if len(examples)>=3:break
        engine=read(output/r['relative_directory']/'engine.json')
        for p in engine['proposals']:
            if p['failed_constraints']:
                reason=p['failed_constraints'][0]
                if reason not in examples:examples[reason]=(r,p)
                if len(examples)>=3:break
    fig,axes=plt.subplots(1,max(1,len(examples)),figsize=(6*max(1,len(examples)),5),layout='constrained',squeeze=False)
    if not examples:
        axes.flat[0].text(.5,.5,'No local rejection observed',ha='center');axes.flat[0].set_axis_off()
    for ax,(reason,(r,p)) in zip(axes.flat,examples.items()):
        xy=np.asarray(p['original_chain']);origin=xy.mean(axis=0);lo=xy.min(axis=0)-1;hi=xy.max(axis=0)+1;window=box(*lo,*hi)
        b=baseline[r['fixture']];source=shapely.from_wkb((ROOT/b['provenance']['paths']['manifold']).read_bytes())
        draw_lines(ax,source.boundary.intersection(window),'#bbbbbb',origin,lw=1)
        draw_lines(ax,LineString(p['original_chain']),'#0086bb',origin,lw=2)
        draw_lines(ax,LineString(p['proposed_replacement']),'#cc3377',origin,lw=1.5,ls='--')
        for g in read(output/r['relative_directory']/'guards.json'):
            if g['guard_id'] in p['entered_guards']:
                draw_lines(ax,shapely.from_wkb(bytes.fromhex(g['geometry_wkb_hex'])).boundary.intersection(window),'#ddaa00',origin,lw=.8)
        ax.set(xlim=(lo[0]-origin[0],hi[0]-origin[0]),ylim=(hi[1]-origin[1],lo[1]-origin[1]),xlabel='Δx (cell)',ylabel='Δy down (cell)',title=f'{reason}\n{r["fixture"]}, ε={r["epsilon"]:g}');ax.set_aspect('equal')
    fig.suptitle('Rejected local proposals: blue original/restored chain, dashed magenta replacement, gold guards')
    save(fig,output,'09_rejected_chord_examples')
    fig,axes=plt.subplots(1,3,figsize=(15,4.8),layout='constrained')
    for stage,style in [('development','-'),('holdout','--')]:
        for ax,key,title in zip(axes,['guard_construction_seconds','engine','qualification'],['Guard construction','Constrained simplification','Raw full qualification']):
            means=[]
            for eps in config['tolerances']:
                values=[r for r in usable if r['stage']==stage and r['epsilon']==eps]
                means.append(np.mean([r['engine_timing']['simplification_total_seconds'] if key=='engine' else r['raw_qualification_seconds'] if key=='qualification' else r[key] for r in values]) if values else np.nan)
            ax.plot(config['tolerances'],means,'.'+style,label=stage);ax.set(xlabel='ε',ylabel='Mean seconds per fixture',title=title)
    axes[0].legend();fig.suptitle('Recorded stage times with Python allocation tracing; GEOS-native memory is not fully traced')
    save(fig,output,'10_runtime')
    lines=['# v0.5B2 protected simplification — geometric screening acceptance','',
        f'Geometric status: **{status}**. Broader scientific/physical fidelity remains **HOLD / UNQUALIFIED**. No production policy or tolerance selected. v0.5 is not complete.','',
        'Protocol and holdout selection were recorded before real outcomes; final code/configuration was frozen before reserved holdout ingress and evaluation. Holdouts use new seeds at the existing five parameter positions, not unseen parameter locations.','',
        '## Dispositions','',f'Counts: {dict(counts)}. Raw global rejections: {conclusions["raw_global_rejections"]}. Local chord rejections: {conclusions["local_chord_rejections"]}; local rollbacks: {conclusions["local_rollbacks"]}; unchanged eligible chain instances: {conclusions["unchanged_eligible_chains"]}. Counts include independent trial settings, not unique physical features.','',
        'Accepted no-op outcomes remain distinct from useful simplification. A raw rejected candidate retains its own WKB/qualification and is never relabeled by a passing fallback.','',
        '## Per-configuration results','',
        '| Stage | Fixture | ε | Vertices | Reduction % | Protected vertices / segments | Rejected chords | Local rollbacks | Global rollback | Added / removed cell² | Symmetric cell² | Measured / certified boundary cell | XOR | Final disposition |',
        '|---|---|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---|']
    for r in rows:
        if 'vertices' not in r:
            lines.append(f'| {r["stage"]} | {r["fixture"]} | {r["epsilon"]} | — | — | — | — | — | — | — | — | — | — | {r["disposition"]} |');continue
        lines.append(f'| {r["stage"]} | {r["fixture"]} | {r["epsilon"]:g} | {r["vertices"]} | {r["vertex_reduction_percent"]:.4f} | {r["protected_vertices"]} / {r["protected_segments"]} | {r["rejected_chords"]} | {r["local_rollbacks"]} | {r["global_rollback"]} | {r["added_area"]:.6f} / {r["removed_area"]:.6f} | {r["symmetric_area"]:.6f} | {r["boundary_measured_lower"]:.6f} / {r["boundary_certified_upper"]:.6f} | {r["raster_xor"]} | {r["disposition"]} |')
    lines+=['','## Scientific boundaries','',
        'Global validity, independent manifoldness, solid/hole/void correspondence, exterior channels, exact protected coordinates/sets, defined registered widths/clearances, signed material limits, per-pore distortion, certified displacement, raster identity, frozen descriptors and persisted reconstruction are separate hard gates. Individual qualification JSON retains every gate and its failures.','',
        'Actual error against the accepted manifold candidate and cumulative error against the original exact reference remain separate in every qualification metrics record. Pore entries retain stable source IDs, coordinates, boundary hashes, positive-area correspondence, containment and individual area changes. Guard records retain complete source segment/vertex IDs and geometry, not merely booleans.','',
        'The geometric thresholds are prospective screening policies, not measured mechanical or manufacturing limits. Dense skeleton/junction/proximity guards and supported normal probes improve coverage but do not prove every possible geometric bottleneck is registered. Raster equality cannot establish continuous equivalence. Frozen whole-mask P10 and its historical limitations remain unchanged.','',
        'Only explicitly accepted outputs and their qualification/provenance are eligible as inputs to a separately authorized v0.5C study under this scoped screening policy. This is not an export/round-trip certificate or a general production simplification policy. Unsupported ingress and failed candidates are excluded.','',
        '## Performance','']
    for stage,s in summaries.items():lines.append(f'- {stage}: {s["elapsed_seconds"]:.3f} s; traced peak {s["peak_traced_bytes"]/2**20:.3f} MiB; process lifetime RSS {s["process_lifetime_peak_rss_bytes"]} bytes.')
    lines+=['','Python tracing excludes some GEOS-native allocations. RSS is process lifetime high-water and not per-candidate incremental memory. Feature construction, partitioning, DP traversal, chord checks, assembly, qualification/raster/morphology and serialization timings remain separately recorded.','',
        '## Software / preservation verification','',
        'Execution-stage geometric conclusions above are supplemented by verification/COMPLETION.json after full regression, source/code/inventory checks and figure inspection. Historical v0.5A HOLD, scoped A1 amended PASS, B1 results, frozen evaluator and generators are not revised. No C/D, physical scaling, CAD, meshing, strength or FEM work is implemented.']
    (output/'summary/ACCEPTANCE.md').write_text('\n'.join(lines)+'\n')
    print('Wrote scoped acceptance, all configuration tables and diagnostic figures.',flush=True)
