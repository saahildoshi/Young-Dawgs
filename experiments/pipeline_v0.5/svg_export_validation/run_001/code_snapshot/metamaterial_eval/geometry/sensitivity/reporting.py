"""Publication-scale diagnostic figures and quantitative sensitivity tables."""
import csv
import json
from pathlib import Path
import numpy as np
import shapely
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from shapely import box
from .metrics import polygons
from .records import write_json


def label(name):return name.replace('design_','D').replace('_seed_',' / S').replace('000','0').replace('001','1').replace('002','2').replace('005','5').replace('009','9')


def save_figure(fig,folder,name):
    fig.savefig(folder/(name+'.png'),dpi=220,bbox_inches='tight');plt.close(fig)


def _draw(ax,geometry,face='black',edge=None,offset=(0,0)):
    shift=np.asarray(offset)
    for p in sorted(polygons(geometry),key=lambda x:-x.area):
        xy=np.asarray(p.exterior.coords)-shift
        ax.fill(xy[:,0],xy[:,1],color=face,edgecolor=edge,linewidth=.5 if edge else 0)
        for h in p.interiors:
            xy=np.asarray(h.coords)-shift
            ax.fill(xy[:,0],xy[:,1],color='white',edgecolor=edge,linewidth=.5 if edge else 0)


def _boundary(ax,geometry,offset,color,lw=.8):
    for p in polygons(geometry):
        for ring in [p.exterior,*p.interiors]:
            xy=np.asarray(ring.coords)-np.asarray(offset);ax.plot(xy[:,0],xy[:,1],color=color,lw=lw)


def contact_panel(output,records,baseline,definition,figure_name):
    x,y=definition['xy'];window=box(x-1.25,y-1.25,x+1.25,y+1.25)
    fig,axes=plt.subplots(2,4,figsize=(14,7),layout='constrained')
    for ax,row in zip(axes.flat,records):
        g=shapely.from_wkb((output/row['relative_directory']/'diagnostic_candidate.wkb').read_bytes())
        m=row['_metrics'];local=g.intersection(window) if g.is_valid else g
        _draw(ax,local,offset=(x,y));_boundary(ax,baseline.intersection(window),(x,y),'#888888',.7)
        _boundary(ax,local,(x,y),'#0086bb' if m['manifold']['manifold'] else '#dd3b35',1.2)
        r=next((r for r in m['features'].get('repairs',[]) if r['contact_id']==definition['contact_id']),{})
        clearance=r.get('clearance');text=f'{clearance:.4f}' if clearance is not None else 'undefined'
        ax.set_title(f"ε={row['epsilon']:g}; clearance={text}",fontsize=10)
        ax.set_xlim(-1.25,1.25);ax.set_ylim(1.25,-1.25);ax.set_aspect('equal')
        ax.set_xticks([-1,-.5,0,.5,1]);ax.set_yticks([-1,-.5,0,.5,1]);ax.grid(alpha=.25)
        ax.set_xlabel('Δx (cell)');ax.set_ylabel('Δy down (cell)')
    fig.suptitle(f"{figure_name}: contact ({x:g},{y:g}); grey=accepted baseline, blue/red=diagnostic boundary\nROI is diagnostic only; no vertices or segments are protected",fontsize=11)
    save_figure(fig,output/'figures',figure_name)


def report(output):
    output=Path(output);summary=json.loads((output/'summary/SIMPLIFICATION_SENSITIVITY.json').read_text())
    registered=json.loads((output/'protocol.json').read_text());config=registered['config']
    baselines=json.loads((output/'baselines.json').read_text())['fixtures'];byid={b['fixture']:b for b in baselines}
    records=[]
    for row in summary['candidates']:
        records.append({**row,'_metrics':json.loads((output/row['metrics_file']).read_text())})
    groups={name:sorted([r for r in records if r['fixture']==name and r['study_role']=='primary'],key=lambda r:r['epsilon']) for name in config['fixture_ids']}
    plt.rcParams.update({'font.size':10,'axes.grid':True,'grid.alpha':.2,'axes.spines.top':False,'axes.spines.right':False})
    colors={name:f'C{i}' for i,name in enumerate(groups)};figures=output/'figures'
    def line_plot(name,ylabel,function,filename,zero=True):
        fig,ax=plt.subplots(figsize=(8.5,5),layout='constrained')
        for fixture,rows in groups.items():
            values=[function(r['_metrics']) for r in rows]
            ax.plot([r['epsilon'] for r in rows],[np.nan if v is None else v for v in values],'.-',color=colors[fixture],label=label(fixture))
        ax.set(xlabel='Douglas–Peucker tolerance ε (native cell)',ylabel=ylabel,title=name);ax.legend(fontsize=9)
        if zero:ax.axhline(0,color='grey',lw=.5)
        save_figure(fig,figures,filename)
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    for fixture,rows in groups.items():
        ax.plot([r['epsilon'] for r in rows],[r['vertex_reduction_percent'] for r in rows],'.-',label=label(fixture),color=colors[fixture])
        threshold=summary['thresholds'][fixture]['nonmanifold']['first_tested_failure']
        if threshold is not None:
            value=next(r['vertex_reduction_percent'] for r in rows if r['epsilon']==threshold)
            ax.scatter([threshold],[value],marker='x',s=70,color=colors[fixture])
    ax.set(xlabel='Tolerance ε (cell)',ylabel='Reduction from accepted manifold vertices (%)',title='Vertex reduction; × marks first tested manifold failure');ax.legend(fontsize=9)
    save_figure(fig,figures,'01_vertex_reduction')
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
    for fixture,rows in groups.items():
        eps=[r['epsilon'] for r in rows]
        for ax,key,title in zip(axes,('added_solid_area','removed_solid_area','symmetric_difference_area'),('Added solid','Removed solid','Symmetric difference')):
            ax.plot(eps,[r['_metrics']['area_from_manifold'].get(key) for r in rows],'.-',color=colors[fixture],label=label(fixture))
            if key=='symmetric_difference_area':ax.plot(eps,[r['_metrics']['area_from_exact'].get(key) for r in rows],'--',color=colors[fixture],alpha=.7)
            ax.set(xlabel='ε (cell)',ylabel='Area (cell²)',title=title)
    axes[0].legend(fontsize=8);fig.suptitle('Solid=manifold→candidate; dashed=exact→candidate (right panel)')
    save_figure(fig,figures,'02_area_changes')
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    for fixture,rows in groups.items():
        eps=[r['epsilon'] for r in rows]
        for ax,key in zip(axes,('distance_from_manifold','distance_from_exact')):
            lower=[r['_metrics'][key].get('measured_hausdorff_lower') for r in rows]
            upper=[r['_metrics'][key].get('continuous_hausdorff_upper') for r in rows]
            ax.plot(eps,lower,'.-',color=colors[fixture],label=label(fixture));ax.fill_between(eps,lower,upper,color=colors[fixture],alpha=.12)
            ax.set(xlabel='ε (cell)',ylabel='Boundary distance (cell)',title=key.replace('_',' '))
    axes[0].legend(fontsize=8);fig.suptitle('Lines: sampled Hausdorff lower bound; bands: Lipschitz upper bound')
    save_figure(fig,figures,'03_boundary_distance_bounds')
    line_plot('Hole count (primary preserve_topology=True sweep)','OGC hole rings',lambda m:m['complexity']['hole_rings'],'04_hole_count',zero=False)
    fig,ax=plt.subplots(figsize=(9,5),layout='constrained')
    for fixture,rows in groups.items():
        if not byid[fixture]['registered_manifold_repairs']:continue
        ids=[p['contact_id'] for p in byid[fixture]['feature_definitions']['repairs']]
        for cid in ids:
            values=[next((p.get('clearance') for p in r['_metrics']['features'].get('repairs',[]) if p['contact_id']==cid),None) for r in rows]
            ax.plot([r['epsilon'] for r in rows],[np.nan if v is None else v for v in values],color=colors[fixture],alpha=.2,lw=.8)
        values=[r['_metrics']['features'].get('minimum_repair_clearance') for r in rows]
        ax.plot([r['epsilon'] for r in rows],[np.nan if v is None else v for v in values],'.-',label=label(fixture),color=colors[fixture])
    ax.axhline(np.sqrt(2)/4,color='black',ls='--',lw=.8,label='Qualified baseline clearance')
    ax.set(xlabel='ε (cell)',ylabel='Relevant interface separation (cell)',title='Repair clearance: thin curves per contact, bold fixture minimum');ax.legend(fontsize=8)
    save_figure(fig,figures,'05_repair_clearance')
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
    for fixture,rows in groups.items():
        for ax,key in zip(axes,('false_positive_pixels','false_negative_pixels','xor_pixels')):
            ax.plot([r['epsilon'] for r in rows],[r['_metrics']['raster_from_canonical'][key] if r['_metrics']['raster_from_canonical'] else np.nan for r in rows],'.-',label=label(fixture),color=colors[fixture])
            ax.set(xlabel='ε (cell)',ylabel='Pixels',title=key.replace('_',' '));ax.set_yscale('symlog',linthresh=1)
    axes[0].legend(fontsize=8);save_figure(fig,figures,'06_raster_disagreement')
    primary=groups['design_000_seed_000'];chosen=[0,.2,.5,1.]
    fig,axes=plt.subplots(2,2,figsize=(11,11),layout='constrained')
    for ax,epsilon in zip(axes.flat,chosen):
        row=next(r for r in primary if r['epsilon']==epsilon)
        g=shapely.from_wkb((output/row['relative_directory']/'diagnostic_candidate.wkb').read_bytes());_draw(ax,g)
        ax.set(xlim=(0,1024),ylim=(1024,0),title=f"ε={epsilon:g}; {row['vertex_reduction_percent']:.2f}% vertex reduction",xlabel='x (cell)',ylabel='y down (cell)');ax.set_aspect('equal')
    fig.suptitle('D0/S0: accepted baseline, mild, moderate and aggressive diagnostic candidates')
    save_figure(fig,figures,'07_overall_geometry')
    source_study=Path(config['source_study'])
    baseline=shapely.from_wkb((source_study/'design_000_seed_000/solid_separate_contacts/manifold_candidate.wkb').read_bytes())
    contact_panel(output,primary,baseline,byid['design_000_seed_000']['feature_definitions']['repairs'][0],'08_primary_contact')
    extra='design_001_seed_000';baseline=shapely.from_wkb((source_study/extra/'solid_separate_contacts/manifold_candidate.wkb').read_bytes())
    definition=next(p for p in byid[extra]['feature_definitions']['repairs'] if p['original_contact_type']=='hole_shell_point')
    contact_panel(output,groups[extra],baseline,definition,'09_exterior_contact')
    fig,axes=plt.subplots(1,3,figsize=(15,4.5),layout='constrained')
    for fixture,rows in groups.items():
        eps=[r['epsilon'] for r in rows]
        for ax,values,title,unit in (
            (axes[0],[r['_metrics']['timing']['simplification_seconds'] for r in rows],'Simplification','seconds'),
            (axes[1],[r['_metrics']['timing']['validation_total_seconds'] for r in rows],'Full validation','seconds'),
            (axes[2],[r['_metrics']['validation_peak_traced_bytes']/2**20 for r in rows],'Validation traced peak','MiB')):
            ax.plot(eps,values,'.-',color=colors[fixture],label=label(fixture));ax.set(xlabel='ε (cell)',ylabel=unit,title=title)
    axes[0].legend(fontsize=8);fig.suptitle('Instrumentation includes Python tracing; GEOS-native memory is not fully tracked')
    save_figure(fig,figures,'10_runtime_and_memory')
    negative=[r for r in records if r['study_role']=='negative_control']
    if negative:
        fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
        for preserve,rows in ((True,primary),(False,negative)):
            rows=sorted(rows,key=lambda x:x['epsilon']);text='primary preserve_topology=True' if preserve else 'negative control False'
            axes[0].plot([r['epsilon'] for r in rows],[r['_metrics']['complexity']['hole_rings'] for r in rows],'.-',label=text)
            axes[1].plot([r['epsilon'] for r in rows],[r['vertex_reduction_percent'] for r in rows],'.-',label=text)
        axes[0].set(xlabel='ε',ylabel='Hole count',title='D0 negative control');axes[1].set(xlabel='ε',ylabel='Vertex reduction (%)',title='Diagnostic control only');axes[0].legend(fontsize=8)
        save_figure(fig,figures,'11_negative_control')
    flat=[];repairs=[]
    for row in records:
        m=row['_metrics'];a=m['area_from_manifold'];b=m['area_from_exact'];f=m['features'];r=m['raster_from_canonical']
        flat.append({'fixture':row['fixture'],'role':row['study_role'],'epsilon':row['epsilon'],'vertices':row['vertices'],'reduction_percent':row['vertex_reduction_percent'],
                     'ogc_valid':m['validity']['ogc_valid'],'manifold':m['manifold']['manifold'],'holes':m['complexity']['hole_rings'],
                     'added_area':a.get('added_solid_area'),'removed_area':a.get('removed_solid_area'),'symmetric_area':a.get('symmetric_difference_area'),
                     'cumulative_exact_symmetric_area':b.get('symmetric_difference_area'),
                     'boundary_lower':m['distance_from_manifold'].get('measured_hausdorff_lower'),'boundary_upper':m['distance_from_manifold'].get('continuous_hausdorff_upper'),
                     'minimum_repair_clearance':f.get('minimum_repair_clearance'),'raster_xor':r['xor_pixels'] if r else None,
                     'fp':r['false_positive_pixels'] if r else None,'fn':r['false_negative_pixels'] if r else None,'diagnostic_flags':';'.join(m['diagnostic_flags'])})
        for p in f.get('repairs',[]):repairs.append({'fixture':row['fixture'],'role':row['study_role'],'epsilon':row['epsilon'],**{k:p.get(k) for k in ('contact_id','clearance','baseline_clearance','retained_added_fraction','local_symmetric_difference_area','contact_remains_resolved','material_repair_risk_flag')}})
    for filename,data in [('PER_TOLERANCE.csv',flat),('PER_CONTACT.csv',repairs)]:
        with (output/'summary'/filename).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(data[0]) if data else []);writer.writeheader();writer.writerows(data)
    promises={name:[r['epsilon'] for r in rows if r['promising_under_strict_available_diagnostics']] for name,rows in groups.items()}
    intersection=sorted(set.intersection(*(set(v) for v in promises.values())))
    write_json(output/'summary/INTERPRETATION.json',{'promising_tolerances_by_fixture':promises,'common_promising_tolerances':intersection,
                'production_tolerance_selected':False,'thresholds':summary['thresholds']})
    lines=['# v0.5B1 — Simplification sensitivity and feature-risk analysis','',
           'Scientific status: **EXPLORATORY STUDY EXECUTED; NOT FULL v0.5B ACCEPTANCE**. Regression and preservation verification are recorded separately. No production tolerance is selected.','',
           '## Objective and immutable sources','',
           'Measure complexity reduction and failure mechanisms using five saved accepted manifold candidates. Source geometries and exact baselines are separately hashed; no masks, generators or regularizations are regenerated.','',
           '## Methods','',
           'Douglas–Peucker, preserve_topology=True, independently from each saved baseline at ε=[0,0.05,0.10,0.20,0.35,0.50,0.75,1.00] native cells. Three D0 negative controls use False at [0.35,0.75,1.00]. Epsilon zero is an unchanged WKB clone. No automatic repair or feature protection.','',
           'A=manifold→simplified continuous error; B=exact→final cumulative error; C=canonical/baseline raster→reconstruction. All three are retained separately. Vertices exclude closure duplicates. Existing exact collinear reduction is not credited to this study.','',
           'Rasterization uses original half-integer centers and x-right/y-down coordinates. Frozen evaluator v1.1 uses the established native interface; cache reuse requires verified raster/evaluator/configuration identity. P10 qualification remains scoped and the historic v0.4.2 calibration remains failed.','',
           'Boundary distance uses indexed samples at ≤0.25-cell spacing, exact sample-to-segment distance, and a Lipschitz upper bound. Local spacing is ≤0.0625 cell. Bounds are not an exact continuous maximum. Validity and manifoldness are checked independently. Positive-area overlap tracks hole/solid/void correspondence, not just counts.','',
           'Fixed repair ROI half-width=r+0.75=1 cell. Per-contact retention, local separation, local links, displacement and geometry differences are recorded. Three deterministic low-EDT/PCA neck probes and the saved D9 boundary connector are monitored; this is not exhaustive neck screening or mechanics.','',
           '## Baseline complexity','',
           '| Fixture | Exposed vertices | Exact coalesced | Existing reduction % | Accepted vertices | Holes | Area | Repairs | GEOS clearance diagnostic |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for b in baselines:
        c=b['complexity'];lines.append(f"| {b['fixture']} | {b['original_exposed_vertices']} | {b['exact_collinear_vertices']} | {b['existing_exact_coalescing_reduction_percent']:.3f} | {c['vertices']} | {c['hole_rings']} | {c['area']} | {b['registered_manifold_repairs']} | {c['geos_minimum_clearance_diagnostic']:.6f} |")
    lines+=['','GEOS minimum_clearance is a robustness diagnostic, not a physical neck width. All baseline topology, shell/hole vertices, boundary lengths, source hashes, local probes and archived neck context are in fixtures/*/baseline.json.','', '## Per-tolerance primary results']
    for name,rows in groups.items():
        lines+=['',f'### {name}','','| ε | Vertices | Reduction % | OGC | Manifold | Holes | Added / removed cell² | Symmetric cell² | Boundary measured / upper | Repair min clearance | Raster XOR |',
                '|---:|---:|---:|---|---|---:|---:|---:|---:|---:|---:|']
        for row in rows:
            m=row['_metrics'];a=m['area_from_manifold'];d=m['distance_from_manifold'];clear=m['features'].get('minimum_repair_clearance');r=m['raster_from_canonical']
            ds=f"{d['measured_hausdorff_lower']:.6f} / {d['continuous_hausdorff_upper']:.6f}" if d.get('measured_hausdorff_lower') is not None else 'undefined'
            area=f"{a['added_solid_area']:.6f} / {a['removed_solid_area']:.6f}" if a.get('defined') else 'undefined'
            sym=f"{a['symmetric_difference_area']:.6f}" if a.get('defined') else 'undefined'
            lines.append(f"| {row['epsilon']:g} | {row['vertices']} | {row['vertex_reduction_percent']:.3f} | {m['validity']['ogc_valid']} | {m['manifold']['manifold']} | {m['complexity']['hole_rings']} | {area} | {sym} | {ds} | {clear if clear is not None else 'N/A or undefined'} | {r['xor_pixels'] if r else 'undefined'} |")
    lines+=['','## Contact, neck and morphology sensitivity','',
            'PER_CONTACT.csv contains every registered repair at every tolerance, including undefined reasons in the individual metrics.json files. Removed original patch material is distinguished from a still-resolved but shifted/widened connection. Local anchor failures and chord changes are geometric warnings, not predictions of strength.','',
            'Each candidate has full raster FP/FN/IoU/connectivity/percolation results against both canonical and baseline rasters, plus frozen scalar/curve differences with cache provenance. Continuous differences can be nonzero despite exact raster descriptors.','',
            'Notable descriptor and material-repair flags use the prospective exploratory definitions in protocol.json; they are not a scientific production acceptance gate.','',
            '## First observed events and non-monotonicity','',
            '| Fixture | Event | First tested event | Preceding tested ε | Non-monotonic recovery ε |','|---|---|---:|---:|---|']
    for name,thresholds in summary['thresholds'].items():
        for event,t in thresholds.items():
            lines.append(f"| {name} | {event} | {t['first_tested_failure'] if t['first_tested_failure'] is not None else 'none observed'} | {t['preceding_tested_tolerance']} | {t['recovery_tolerances']} |")
    lines+=['','These are discrete observed brackets, not exact thresholds. Null diagnostics do not count as recovered passes. Complete sequences are retained.','',
            '## Conservative promising diagnostic points','',*['- '+name+': '+str(values) for name,values in promises.items()],
            '',f'Intersection across all five fixtures: {intersection}. This is a strict available-diagnostics screen requiring positive vertex reduction; it is not production selection.',
            '', '## Performance','',f"Sweep elapsed: {summary['total_sweep_seconds']:.3f} s; maximum traced candidate-stage allocation: {summary['peak_traced_candidate_bytes']/2**20:.3f} MiB; process lifetime peak RSS: {summary['process_lifetime_peak_rss_bytes']} bytes.",
            '', 'Per-candidate files split simplification, geometry, manifold, distance, feature, raster and frozen morphology time. Python tracing does not include all GEOS-native allocations; lazy baseline caches can contribute to the first candidate peak. RSS is process lifetime high-water, not incremental candidate memory.',
            '', '## Limitations and stage boundary','',
            'Only five registered fixtures and the stated controls were tested. No physical units, FEM, manufacturing criteria, universal morphology preservation or production tolerance are established. Raster equality does not imply continuous equality. v0.5B1 is not full v0.5B acceptance. Historical v0.5A HOLD and scoped v0.5A.1 amended PASS remain unchanged.',
            '', 'Review the study-specific scientific interpretation and proposed v0.5B2 architecture in the accompanying new documentation. No protected simplifier or later stage has been implemented.']
    (output/'summary/SIMPLIFICATION_SENSITIVITY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Wrote quantitative report, CSV tables and diagnostic figures.',flush=True)
