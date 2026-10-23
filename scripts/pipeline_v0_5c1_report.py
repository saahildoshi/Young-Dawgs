"""C.1 scientific reports and figures; never alters geometry or producer decisions."""
from collections import Counter,defaultdict
from pathlib import Path
import csv
import json
import math
import sys
import time
import numpy as np
import shapely
from shapely import Polygon,Point,box,LineString
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from metamaterial_eval.geometry.protected_v2.study import ROOT,OUT,C
from metamaterial_eval.geometry.validation.checks import rings,polygons,digest,region_correspondence
from metamaterial_eval.geometry.sensitivity.records import write_json


def read(p):return json.loads(Path(p).read_text())


def boundary(ax,g,color='black',label=None,lw=.7):
    ax.add_collection(LineCollection([r['xy'] for r in rings(g)],colors=color,linewidths=lw,label=label));ax.autoscale();ax.set_aspect('equal')


def lineparts(g):
    if g.is_empty:return []
    if g.geom_type in ('LineString','LinearRing'):return [list(g.coords)]
    if hasattr(g,'geoms'):return [p for q in g.geoms for p in lineparts(q)]
    return []


def fill(ax,g,color,alpha=.7):
    for p in polygons(g):
        ax.fill(*np.asarray(p.exterior.coords).T,color=color,alpha=alpha)
        for h in p.interiors:ax.fill(*np.asarray(h.coords).T,color='white')
    ax.set_aspect('equal');ax.autoscale()


def finish(fig,name,title):
    fig.suptitle(title,fontsize=11);fig.tight_layout(rect=(0,0,1,.95));fig.savefig(OUT/'figures'/name,dpi=165);plt.close(fig)


def source_geometry(stage,name,state):
    s=read(OUT/stage/'source_manifests'/(name+'.json'))['source_provenance'];key='exact' if state=='G1' else 'manifold'
    return shapely.from_wkb((ROOT/s['paths'][key]).read_bytes())


def section_metadata(record,kind,before,after,context):
    """Reporting-only provenance: exact finite section/chord incidence, no acceptance changes."""
    source,candidate,guard,chords,ids=context
    xy=record.get('xy',record.get('center_xy'));phase=record.get('phase','solid')
    if kind=='registered':
        seg=record['candidate_chord'].get('segment_xy')
        angle=math.degrees(math.atan2(seg[1][1]-seg[0][1],seg[1][0]-seg[0][0])) if seg else None
    else:angle=record.get('angle_degrees',90. if record.get('axis')==1 else 0.)
    delta=after-before if before is not None and after is not None else None
    out={'phase':phase,'angle_degrees':angle,'absolute_difference_cell':delta,'relative_difference':delta/before if delta is not None and before else None,
         'measurement_method':{'registered':'Frozen B2 contiguous normal chord','axial':'Independent C native-axis line component','oblique':'Independent C.1 oblique line component'}[kind],
         'selection_class':'registered' if kind=='registered' else 'independently_source_selected','center_in_guard':record.get('guarded_center',bool(guard.covers(Point(xy)))),
         'entire_monitored_section_in_guard':None,'accepted_chords_intersecting_section':None,'section_geometry_changed':None,
         'criterion_pass':delta is not None and delta>=-1e-10,'numeric_allowance_cell':1e-10}
    if angle is None or before is None or after is None:return out
    d=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle))]);p=np.asarray(xy);span=max(before,after)+1e-6;line=LineString([p-span*d,p+span*d]);point=Point(p);parts=[]
    for geom in [source,candidate]:
        cut=line.intersection(geom) if phase=='solid' else line.difference(geom)
        pp=[LineString(q) for q in lineparts(cut) if LineString(q).distance(point)<=1e-10]
        if len(pp)!=1:return out
        parts.append(pp[0])
    section=shapely.union_all(parts);out['entire_monitored_section_in_guard']=bool(guard.covers(section))
    out['accepted_chords_intersecting_section']=[ids[int(i)] for i in chords.query(section,predicate='intersects')]
    out['section_geometry_changed']=not parts[0].equals(parts[1])
    return out


def figures(rows,stats,observations,summaries,comparison):
    root=read(OUT/'root_cause/REPRODUCTION.json');base=source_geometry('regression','design_004_seed_001','G2')
    old=shapely.from_wkb((OUT/'root_cause/B2_original.wkb').read_bytes());new=shapely.from_wkb((OUT/'root_cause/C1_revised.wkb').read_bytes())
    origcase=C/'parameter_holdouts/design_004_seed_001/epsilon_0p50';guards=shapely.from_wkb((origcase/'guard_union.wkb').read_bytes())
    from metamaterial_eval.geometry.protected.model import BoundaryModel
    model=BoundaryModel(base);protected_ids=sorted({i for r in read(origcase/'guards.json') for i in r['protected_segments']})
    target=root['B2_original']['target_chord'][0];chain=np.asarray(target['original_chain']);chord=np.asarray(target['proposed_replacement']);roi=box(49,547,68,566)
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax in axes:
        fill(ax,guards.intersection(roi),'#e4dfad',.5);boundary(ax,base,'#444',label='G2');boundary(ax,old,'#d17b27',label='Original B2')
        protected_lines=[model.segments[i] for i in protected_ids if model.lines[i].intersects(roi)]
        ax.add_collection(LineCollection(protected_lines,colors='#3565a2',linewidths=1.4,label='Protected segments'))
        if protected_lines:
            pts=np.concatenate(protected_lines);ax.scatter(pts[:,0],pts[:,1],s=8,c='#3565a2')
        ax.plot(*chain.T,'o-',color='#444',ms=4,label='Eligible source subchain');ax.plot(*chord.T,'--',color='red',lw=1.4,label='Accepted chord')
        ax.plot([57.5,57.5],[552,561],color='#a02b8a',lw=1.6,label='Source section 9 cells');ax.scatter([57.5],[556.5],color='#a02b8a',s=15)
        ax.set_xlim(49,68);ax.set_ylim(566,547);ax.set_xlabel('x [cell]');ax.set_ylabel('y [cell]')
    fill(axes[1],base.difference(old).intersection(roi),'#1aa085');fill(axes[1],old.difference(base).intersection(roi),'#c74434');axes[0].legend(loc='lower right',fontsize=7)
    axes[1].set_xlim(49,68);axes[1].set_ylim(566,547)
    axes[0].set_title('Unguarded width: 9 → 8.916666667 cells');axes[1].set_title('Teal removed; red added; guard hull distance 3.5 cells')
    finish(fig,'01_original_failure.png','Historical D4/S1 epsilon 0.50: source and accepted B2 chord remain immutable')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for ax in axes:
        fill(ax,guards.intersection(roi),'#e4dfad',.5);boundary(ax,base,'#555',label='G2');boundary(ax,new,'#228b52',label='C.1 revised')
        ax.plot(*chord.T,':',color='red',label='Rejected original chord');ax.plot([57.5,57.5],[552,561],color='#a02b8a',lw=2)
        ax.set_xlim(49,68);ax.set_ylim(566,547);ax.legend(loc='lower right',fontsize=7)
    axes[0].set_title('Actual corrected width = 9.000000000 cells');axes[1].set_xlim(56.8,60.5);axes[1].set_ylim(561.4,559.8);axes[1].set_title('Original source subchain retained locally')
    finish(fig,'02_corrected_behavior.png','Proposal-level solid-width rejection; no guard enlargement or post hoc widening')
    primary=[r for r in rows if r.get('stage')=='regression' and r['epsilon']==.5 and 'result_path' in r]
    fig,axes=plt.subplots(1,3,figsize=(18,5));xx=np.arange(len(primary));labels=[r['fixture'].replace('design_','D').replace('_seed_','/S').replace('00','') for r in primary]
    axes[0].bar(xx,[r['guard_boundary_fraction']*100 for r in primary],color='#6673ac',label='Original = revised guard coverage');axes[0].set_ylabel('Source boundary guarded [%]');axes[0].legend(fontsize=7)
    axes[1].bar(xx,[r['width_counters']['width_rejections'] for r in primary],color='#dd8c39');axes[1].set_ylabel('Additional width/uncertainty rejection flags')
    for ax in axes[:2]:ax.set_xticks(xx,labels,rotation=65,ha='right',fontsize=7)
    ax=axes[2];fill(ax,guards.intersection(roi),'#e4dfad',.5);boundary(ax,base,'#555',label='G2');ax.plot(*chord.T,'r:',label='Proposed chord')
    for i,w in enumerate(root['C1_revised']['target_chord'][0]['width_qualification']['witnesses']):
        x=-w['mid_slab_cut'];segment=np.asarray(w['source_xy']);y=segment[0,1];ax.plot([x,x],[y-w['mid_slab_width_before'],y],color='#8b43a4',lw=1.2,label='New affine-slab sections' if i==0 else None)
    ax.plot([57.5,57.5],[552,561],'k--',lw=.9,label='Independent C failure probe')
    registered=read(OUT/'regression/parameter_holdouts/design_004_seed_001/epsilon_0p50/frozen_B2_qualification.json')['metrics']['features']['natural_necks']
    points=np.asarray([p['center_xy'] for p in registered]);ax.scatter(points[:,0],points[:,1],s=25,marker='x',color='#3565a2',label='Old registered normal centers')
    ax.set_xlim(49,68);ax.set_ylim(566,547);ax.set_xlabel('x [cell]');ax.set_ylabel('y [cell]');ax.legend(fontsize=6,loc='lower right');ax.set_title('Local coverage added at proposal impact')
    finish(fig,'03_feature_coverage.png','Same guards; new adaptive impact sections near each proposed change. Counts are not unique struts')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    colors={'registered':'#777','axial':'#3465a4','oblique':'#db8c28'}
    for kind in ['registered','axial','oblique']:
        pp=[p for p in observations if p['kind']==kind and p['after'] is not None and p['before'] is not None]
        axes[0].scatter([p['before'] for p in pp],[p['after'] for p in pp],s=5,c=colors[kind],label=kind,alpha=.4)
        axes[1].scatter([0 if p['stage']=='regression' else 1 for p in pp],[p['after']-p['before'] for p in pp],s=5,c=colors[kind],alpha=.4)
    axes[0].plot([0,25],[0,25],'k--',lw=.7);axes[0].set_xlabel('G2 width [cell]');axes[0].set_ylabel('Revised G3 width [cell]');axes[0].legend(fontsize=8)
    axes[1].axhline(-1e-10,color='red',ls='--',lw=.8);axes[1].set_xticks([0,1],['Regression','Independent']);axes[1].set_ylabel('Measured width change [cell]')
    finish(fig,'04_width_changes.png','Registered, source-selected axial and independent oblique measurements; undefined values remain explicit')
    fig,axes=plt.subplots(1,2,figsize=(12,5))
    for eps,col in [(.5,'#466baf'),(.75,'#d28a31')]:
        pp=[r for r in comparison['records'] if r['epsilon']==eps];xx=np.arange(len(pp))
        axes[0].plot(xx,[r['original_reduction_percent'] for r in pp],':',c=col,label=f'Original ε={eps}');axes[0].plot(xx,[r['revised_reduction_percent'] for r in pp],'-',c=col,label=f'Revised ε={eps}')
    axes[0].set_xlabel('Regression realization index');axes[0].set_ylabel('Vertex reduction [%]');axes[0].legend(fontsize=7)
    for stage,col in [('regression','#466baf'),('independent_cohort','#d28a31')]:
        pp=[r for r in rows if r.get('stage')==stage and 'vertices' in r];axes[1].scatter([r['epsilon'] for r in pp],[r['vertex_reduction_percent'] for r in pp],s=17,c=col,label=stage)
    axes[1].set_xlabel('Requested epsilon [cell]');axes[1].set_ylabel('Revised vertex reduction [%]');axes[1].legend(fontsize=7)
    finish(fig,'05_vertex_reduction.png','Useful reduction is retained after conservative local rejection; larger tolerance need not yield more reduction')
    eng=read(OUT/'root_cause/C1_revised_engine.json');active=[p for p in eng['proposals'] if p['applied'] and p['fan_added_upper']+p['fan_removed_upper']>0]
    chosen=max(active,key=lambda p:p['fan_added_upper']+p['fan_removed_upper']) if active else target;center=np.asarray(chosen['proposed_replacement']).mean(axis=0);x,y=center;window=box(x-8,y-8,x+8,y+8)
    fig,axes=plt.subplots(1,2,figsize=(11,5))
    for ax,span in zip(axes,[8,2]):
        boundary(ax,base,'#555',label='G2');boundary(ax,new,'#228b52',label='G3');fill(ax,new.difference(base).intersection(window),'#c74434');fill(ax,base.difference(new).intersection(window),'#1aa085');ax.set_xlim(x-span,x+span);ax.set_ylim(y+span,y-span)
    axes[0].set_title('Accepted safe region, separate from restored failure');axes[1].set_title('Subpixel difference close-up')
    finish(fig,'06_continuous_difference.png','Red added; teal removed. Net area and raster equality cannot replace these differences')
    pore=read(OUT/'pore_policy/HISTORICAL_RECONSTRUCTION.json');a=Polygon(pore['source_xy'][0]['xy']);b=Polygon(pore['candidate_xy'][0]['xy']);lo=a.bounds;fig,axes=plt.subplots(1,2,figsize=(11,5))
    for ax in axes:boundary(ax,a,'#444',label='G1 pore: 1 cell²');boundary(ax,b,'#3680b6',label='G2/G3 pore: 0.96875 cell²');fill(ax,a.difference(b),'#d6573c');ax.set_xlim(lo[0]-.15,lo[2]+.15);ax.set_ylim(lo[3]+.15,lo[1]-.15);ax.legend(loc='center',fontsize=8)
    axes[1].text(.5,.27,'Absolute loss = 1/32 cell²\nRelative loss = 3.125%\nA1 geometric policy ≠ pore-fidelity qualification',ha='center',va='center',transform=axes[1].transAxes,fontsize=8)
    axes[0].set_title('Historical D7/S0: one contact, 3.125% loss')
    axes[0].text(.5,.27,'Absolute loss = 1/32 cell²\nRelative loss = 3.125%\nA1 geometric policy ≠ pore-fidelity qualification',ha='center',va='center',transform=axes[0].transAxes,fontsize=8)
    audit=read(OUT/'pore_policy/REAL_COHORT_PORE_AUDIT.json');worst=max(audit['records'],key=lambda p:p['relative_error'] or 0)
    g1=source_geometry(worst['stage'],worst['fixture'],'G1');g2=source_geometry(worst['stage'],worst['fixture'],'G2');oldpores=[Polygon(h) for p in polygons(g1) for h in p.interiors];newpores=[Polygon(h) for p in polygons(g2) for h in p.interiors];a=oldpores[worst['source_pore']];b=max(newpores,key=lambda p:p.intersection(a).area)
    ax=axes[1];ax.clear();boundary(ax,a,'#444',label='G1 pore: 1 cell²');boundary(ax,b,'#3680b6',label='G2 pore: 0.9375 cell²');fill(ax,a.difference(b),'#d6573c');lo=a.bounds;ax.set_xlim(lo[0]-.15,lo[2]+.15);ax.set_ylim(lo[3]+.15,lo[1]-.15);ax.legend(loc='center',fontsize=8)
    ax.text(.5,.27,'Absolute loss = 2/32 cell²\nRelative loss = 6.25%\nIdentity preserved; fidelity UNQUALIFIED',ha='center',va='center',transform=ax.transAxes,fontsize=8);ax.set_title('Independent P0/S12031 pore 186: two contacts')
    finish(fig,'07_small_pore.png','One versus two local contact triangles r²/2; no amended fidelity allowance adopted')
    specs=read(OUT/'protocol/PROTOCOL.json')['cohort'][::2];fig,axes=plt.subplots(2,3,figsize=(12,8))
    for ax,spec in zip(axes.ravel(),specs):
        name=spec['fixture'];folder=OUT/'independent_cohort/parameter_holdouts'/name
        if not (folder/'native1024/microstructure.npy').exists():ax.text(.5,.5,'Unavailable / quarantined',ha='center');continue
        m=np.load(folder/'native1024/microstructure.npy',allow_pickle=False);ax.imshow(m,cmap='gray_r',extent=(0,1024,1024,0));case=folder/'epsilon_0p50/candidate.wkb'
        if case.exists():boundary(ax,shapely.from_wkb(case.read_bytes()),'#3f77a6',lw=.12)
        ax.set_title(f"New point {spec['design_id']-100}, seed {spec['seed']}\nnearest old normalized distance ≈ {spec['nearest_old_normalized_distance']:.3f}",fontsize=8)
    finish(fig,'08_independent_cohort.png','First native1024 sources from six newly registered parameter positions; revised ε=0.50 boundaries overlaid')
    independent=[r for r in rows if r.get('stage')=='independent_cohort'];names=[s['fixture'] for s in read(OUT/'protocol/PROTOCOL.json')['cohort']];eps=[0,.2,.35,.5,.75];matrix=np.full((12,5),-1.)
    for r in independent:matrix[names.index(r['fixture']),eps.index(r['epsilon'])]=1 if r['acceptance']['scientific_status']=='PASS_SAMPLED_DOMAIN' else 0
    fig,ax=plt.subplots(figsize=(9,7));im=ax.imshow(matrix,cmap='RdYlGn',vmin=0,vmax=1,aspect='auto');ax.set_xticks(range(5),[str(e) for e in eps]);ax.set_yticks(range(12),[n.replace('c1_design_','P').replace('_seed_',' / ') for n in names]);ax.set_xlabel('Requested epsilon [cell]')
    for i in range(12):
        for j in range(5):ax.text(j,i,'PASS' if matrix[i,j]==1 else ('HOLD' if matrix[i,j]==0 else 'N/A'),ha='center',va='center',fontsize=7,color='white' if matrix[i,j]==1 else 'black')
    finish(fig,'09_holdout_results.png','Independent feature/geometry screens; cumulative small-pore scientific policy remains separately UNQUALIFIED')
    costs=defaultdict(float)
    for r in rows:
        if 'timings' not in r:continue
        for k,v in r['timings'].items():costs[k]+=v
        costs['engine_total_including_width']+=r['engine_seconds'];costs['width_subset_of_engine']+=r['width_counters']['width_check_seconds'];costs['frozen_B2_qualification']+=r['qualification_seconds'];costs['guard_construction']+=r['guard_seconds']
        performance=read((ROOT/r['result_path']).with_name('producer_performance.json'))
        if r['epsilon']==0:costs['feature_preparation_once_per_source']+=performance['preparation_seconds']
        for k,v in performance['engine'].items():
            if k!='simplification_total_seconds':costs[k+'_subset_of_engine']+=v
        costs['deterministic_repeat']+=performance['repeat_seconds']
    profile=read(OUT/'performance/TARGETED_PROFILE.json');fig,axes=plt.subplots(1,2,figsize=(13,6));keys=sorted(costs,key=costs.get,reverse=True);axes[0].barh(keys[::-1],[costs[k] for k in keys[::-1]]);axes[0].set_xlabel('Stage sums [s]; width is an engine subset')
    labels=['B2 engine','C.1 engine'];xx=np.arange(2);axes[1].bar(xx-.18,[r['engine_traced_peak_bytes']/2**20 for r in profile['records']],.36,label='Engine tracked peak');axes[1].bar(xx+.18,[r['process_lifetime_peak_rss_bytes']/2**20 for r in profile['records']],.36,label='Lifetime RSS');axes[1].set_xticks(xx,labels);axes[1].set_ylabel('MiB');axes[1].legend(fontsize=8)
    finish(fig,'10_runtime_memory.png','Matched targeted engine profile; full-study RSS and native generation profiles are reported separately')
    write_json(OUT/'performance/STAGE_SUMS.json',{'seconds':dict(costs),'overlapping_subsets':True,
        'isolated_rollback_time':'Not separately instrumented; included in engine traversal/check/assembly times.',
        'isolated_oblique_audit_time':'Not separately instrumented; included in whole-study elapsed time.',
        'preparation':'Includes source feature detection and risk preparation, counted once per realization.',
        'memory':'Targeted Python engine peak plus whole-process lifetime RSS; no full-study traced peak.'})


def analyze_pores(summaries):
    allrows=[];max_abs=max_rel=0.;violations=[]
    for summary in summaries:
        stage=summary['stage']
        for path in sorted((OUT/stage/'source_manifests').glob('*.json')):
            s=read(path);p=s['source_provenance'];a=shapely.from_wkb((ROOT/p['paths']['exact']).read_bytes());b=shapely.from_wkb((ROOT/p['paths']['manifold']).read_bytes());q=read(ROOT/p['paths']['qualification']);old=[Polygon(h) for pp in polygons(a) for h in pp.interiors];new=[Polygon(h) for pp in polygons(b) for h in pp.interiors];matches=region_correspondence(old,new)
            for row in matches['records']:
                i=row['source_id'];area=row['candidate_area'];absolute=abs(area-row['source_area']) if area is not None else None;relative=row['relative_area_distortion'];inc=[c['contact_id'] for c in q.get('contact_report',{}).get('contacts',[]) if old[i].boundary.distance(Point(c['xy']))<=1e-10];envelope=len(inc)*.03125
                passed=absolute is not None and absolute<=envelope+1e-10
                item={'stage':stage,'fixture':s['fixture'],'source_pore':i,'source_area':row['source_area'],'manifold_area':area,'absolute_error':absolute,'relative_error':relative,'incident_contacts':inc,'triangle_envelope':envelope,'envelope_pass':passed,'identity':len(row['candidate_ids'])==1 and row['reciprocal_anchors']}
                ap=absolute is not None and absolute<=.03125+1e-10;rp=relative is not None and relative<=.005+1e-10
                item.update(absolute_diagnostic=ap,relative_diagnostic=rp,AND_diagnostic_with_identity=bool(item['identity'] and ap and rp),OR_diagnostic_with_identity=bool(item['identity'] and (ap or rp)),
                    diagnostic_only=True,source_perimeter=old[i].length,candidate_perimeter=new[row['candidate_ids'][0]].length if len(row['candidate_ids'])==1 else None,
                    symmetric_area=row.get('symmetric_area'))
                allrows.append(item)
                if absolute is not None:max_abs=max(max_abs,absolute)
                if relative is not None:max_rel=max(max_rel,relative)
                if not passed or not item['identity']:violations.append(item)
    data={'records':allrows,'maximum_absolute_error':max_abs,'maximum_relative_error':max_rel,'construction_envelope_violations':violations,
        'diagnostic_counts':dict(Counter(f"{r['stage']}:absolute={r['absolute_diagnostic']},relative={r['relative_diagnostic']}" for r in allrows)),
        'policy_status':'UNQUALIFIED_CUMULATIVE_PORE_FIDELITY','amendment_adopted':False,'scope':'G1→G2 pore changes, also present cumulatively in G1→G3; G2→G3 per-pore0.5% budget unchanged.'}
    write_json(OUT/'pore_policy/REAL_COHORT_PORE_AUDIT.json',data);return data


def main():
    began=time.perf_counter();protocol=read(OUT/'protocol/PROTOCOL.json');summaries=[read(OUT/'summary/regression.json'),read(OUT/'summary/independent_cohort.json')];comparison=read(OUT/'summary/REGRESSION_COMPARISON.json');rows=[r for s in summaries for r in s['rows']];usable=[r for r in rows if 'result_path' in r];observations=[]
    stats={'width_rejections':0,'integrated_sections':0,'local_rollbacks':0,'unchanged_chains':0,'assembly_rollbacks':0,'registered_repairs':0,'registered_natural_probes':0,'independent_axial_unique':0,'independent_oblique_unique':0,'axial_evaluations':0,'oblique_evaluations':0,'axial_narrowed':0,'oblique_narrowed':0,'undefined':0,'maximum_measured_narrowing':0.,'max_symmetric_G2_G3':0.,'max_symmetric_G1_G3':0.,'max_added':0.,'max_removed':0.,'max_distance_upper':0.,'max_cumulative_distance_upper':0.,'max_pore_G2_G3_fraction':0.,'max_registered_width_loss':0.,'max_repair_clearance_loss':0.,'frozen_B2_passes':0,'geometry_manifold_passes':0,'raster_exact_passes':0,'descriptor_passes':0,'source_case_count':0,'new_pore_contacts':Counter()}
    stats.update(max_pore_G1_G3_absolute=0.,max_pore_G1_G3_fraction=0.,transform_maxima={k:{m:0. for m in ['added','removed','symmetric','relative_symmetric','displacement_upper']} for k in ['G1_G2','G2_G3','G1_G3']})
    hard_failures=Counter();C1holds=[]
    for r in usable:
        d=read(ROOT/r['result_path']);f=d['features'];extra=d['independent_oblique'];stage=r['stage'];stats['width_rejections']+=r['width_counters']['width_rejections'];stats['integrated_sections']+=r['width_counters']['integrated_qualifying_sections'];stats['local_rollbacks']+=r['width_counters']['local_rollbacks'];stats['unchanged_chains']+=r['width_counters']['unchanged_chains'];stats['assembly_rollbacks']+=r['width_counters']['assembly_rollbacks']
        case=(ROOT/r['result_path']).parent;engine=read(case/'engine.json');applied=[p for p in engine['proposals'] if p['applied']]
        context=(source_geometry(stage,r['fixture'],'G2'),shapely.from_wkb((case/'candidate.wkb').read_bytes()),shapely.from_wkb((case/'guard_union.wkb').read_bytes()),shapely.STRtree([LineString(p['proposed_replacement']) for p in applied]),[p['proposal_id'] for p in applied])
        stats['axial_evaluations']+=len(f['independent_probes']);stats['oblique_evaluations']+=len(extra['records']);stats['axial_narrowed']+=f['narrowed_probes'];stats['oblique_narrowed']+=extra['narrowing_count'];stats['undefined']+=f['undefined_probes']+extra['undefined_count']
        for kind,pp in [('axial',f['independent_probes']),('oblique',extra['records'])]:
            for p in pp:
                observations.append({'stage':stage,'fixture':r['fixture'],'epsilon':r['epsilon'],'kind':kind,'before':p['before'],'after':p['after'],'xy':p['xy'],**section_metadata(p,kind,p['before'],p['after'],context)})
                if p['delta'] is not None:stats['maximum_measured_narrowing']=max(stats['maximum_measured_narrowing'],-p['delta'])
        qualification=read((ROOT/r['result_path']).with_name('frozen_B2_qualification.json'));registered=qualification['metrics']['features']
        for p in registered['natural_necks']:
            observations.append({'stage':stage,'fixture':r['fixture'],'epsilon':r['epsilon'],'kind':'registered','before':p['baseline_width'],'after':p['candidate_chord']['width'],'xy':p['center_xy'],**section_metadata(p,'registered',p['baseline_width'],p['candidate_chord']['width'],context)});stats['max_registered_width_loss']=max(stats['max_registered_width_loss'],-p['width_change'] if p['width_change'] is not None else float('inf'))
        for p in registered['repairs']:
            if p['clearance'] is not None:stats['max_repair_clearance_loss']=max(stats['max_repair_clearance_loss'],p['baseline_clearance']-p['clearance'])
        if r['epsilon']==0:
            stats['source_case_count']+=1;stats['registered_repairs']+=len(f['repairs']);stats['registered_natural_probes']+=len(registered['natural_necks']);stats['independent_axial_unique']+=len(f['independent_probes']);stats['independent_oblique_unique']+=len(extra['records'])
            if stage=='independent_cohort':
                source=read(OUT/stage/'source_manifests'/(r['fixture']+'.json'))['source_provenance'];ingress=read(ROOT/source['paths']['qualification']);stats['new_pore_contacts'].update(c['kind'] for c in ingress.get('contact_report',{}).get('contacts',[]))
        stats['frozen_B2_passes']+=d['gates']['frozen_B2_constraints'];stats['geometry_manifold_passes']+=d['G3_integrity']['passed'];stats['raster_exact_passes']+=d['raster']['xor']==0;stats['descriptor_passes']+=d['descriptor_comparison']['exact']
        for key,field in [('max_symmetric_G2_G3','symmetric_G2_G3'),('max_symmetric_G1_G3','symmetric_G1_G3'),('max_added','added'),('max_removed','removed'),('max_distance_upper','distance_upper'),('max_cumulative_distance_upper','cumulative_distance_upper')]:stats[key]=max(stats[key],r[field])
        for p in d['continuous_topology']['holes']['records']:stats['max_pore_G2_G3_fraction']=max(stats['max_pore_G2_G3_fraction'],p['relative_area_distortion'] or 0)
        for p in d['cumulative_topology']['holes']['records']:
            stats['max_pore_G1_G3_fraction']=max(stats['max_pore_G1_G3_fraction'],p['relative_area_distortion'] or 0)
            if p['candidate_area'] is not None:stats['max_pore_G1_G3_absolute']=max(stats['max_pore_G1_G3_absolute'],abs(p['candidate_area']-p['source_area']))
        for transform,values in stats['transform_maxima'].items():
            for m in ['added','removed','symmetric','relative_symmetric']:values[m]=max(values[m],d['areas'][transform][m])
            values['displacement_upper']=max(values['displacement_upper'],d['distances'][transform]['upper'])
        hard_failures.update(d['acceptance']['failed_gates'])
        if d['acceptance']['scientific_status']=='HOLD':C1holds.append({'fixture':r['fixture'],'epsilon':r['epsilon'],'stage':stage,'failed':d['acceptance']['failed_gates'],'axial_flags':[p for p in f['independent_probes'] if p['narrowed'] or p['delta'] is None],'oblique_flags':[p for p in extra['records'] if p['narrowed'] or not p['defined']]})
    coverage=[]
    for stage in ['regression','independent_cohort']:
        for kind in ['registered','axial','oblique']:
            pp=[p for p in observations if p['stage']==stage and p['kind']==kind]
            coverage.append({'stage':stage,'kind':kind,'evaluations':len(pp),'unguarded_centers':sum(not p['center_in_guard'] for p in pp),'sections_not_entirely_guarded':sum(p['entire_monitored_section_in_guard'] is False for p in pp),'geometry_changed_sections':sum(p['section_geometry_changed'] is True for p in pp),'accepted_chord_incidence_sections':sum(bool(p['accepted_chords_intersecting_section']) for p in pp),'unresolved_section_metadata':sum(p['section_geometry_changed'] is None for p in pp)})
    stats['coverage']=coverage;write_json(OUT/'feature_audit/COVERAGE_SUMMARY.json',coverage)
    stats['new_pore_contacts']=dict(stats['new_pore_contacts']);pores=analyze_pores(summaries);ind=[r for r in rows if r.get('stage')=='independent_cohort'];reg=[r for r in rows if r.get('stage')=='regression'];errors=[e for s in summaries for e in s['errors']];unsupported=[x for s in summaries for x in s['unsupported']];indpass=len(ind)==60 and all(r['acceptance']['scientific_status']=='PASS_SAMPLED_DOMAIN' for r in ind) and not errors and not unsupported;regpass=len(reg)==100 and all(r['acceptance']['scientific_status']=='PASS_SAMPLED_DOMAIN' for r in reg)
    statuses={'A_source_preservation':'VERIFY_FINAL_INVENTORY','B_root_cause':'PASS_REPRODUCED','C_generalized_correction':'PASS_DOCUMENTED_FAILURE_CLASS','D_synthetic_controls':'PASS_50_TARGETED_TESTS','E_regression':'PASS_TESTED_DOMAIN' if regpass else 'HOLD','F_independent_features':'PASS_TESTED_DOMAIN' if indpass else 'HOLD','G_continuous_geometry':'PASS_TESTED_BUDGETS' if stats['frozen_B2_passes']==len(usable) and not errors else 'HOLD','H_raster_morphology':'PASS_EXACT' if stats['raster_exact_passes']==len(usable) and stats['descriptor_passes']==len(usable) else 'HOLD','I_small_pore_policy':'UNQUALIFIED_CUMULATIVE_FIDELITY','J_overall_scientific':'HOLD_SMALL_PORE_POLICY' if regpass and indpass else 'HOLD_FEATURE_OR_GEOMETRY_AND_PORE_POLICY','K_production':'HOLD_UNQUALIFIED','L_CAD_manufacturing_FEM':'UNQUALIFIED'}
    summary={'stage':'v0.5C.1','algorithm_version':protocol['algorithm_version'],'statuses':statuses,'regression_configurations':len(reg),'independent_configurations':len(ind),'independent_structures':len({r['fixture'] for r in ind}),'total_configurations':len(rows),'stats':stats,'pore_maximum_absolute_error':pores['maximum_absolute_error'],'pore_maximum_relative_error':pores['maximum_relative_error'],'hard_failures':dict(hard_failures),'independent_holds':C1holds,'errors':errors,'unsupported':unsupported,'execution_seconds':sum(s['elapsed_seconds'] for s in summaries),'peak_process_lifetime_rss_bytes':max(s['process_lifetime_peak_rss_bytes'] for s in summaries),'rows':rows,'new_parameters':protocol['cohort'],'historical_C_HOLD_unchanged':True,'production_policy_selected':False,'export_implemented':False,'thresholds_relaxed':False,'newly_prevented_original_accepted':comparison['newly_prevented_previously_accepted']}
    write_json(OUT/'summary/INDEPENDENT_REQUALIFICATION.json',summary);write_json(OUT/'feature_audit/WIDTH_OBSERVATIONS.json',observations);write_json(OUT/'summary/FEATURE_HOLDS.json',C1holds)
    fields=['stage','fixture','epsilon','algorithm_version','B2_disposition','vertices','vertex_reduction_percent','added','removed','symmetric_G2_G3','symmetric_G1_G3','distance_upper','cumulative_distance_upper','raster_xor','narrowed_probes','oblique_narrowed','oblique_undefined','max_oblique_narrowing','width_rejections','scientific_status','failed_gates']
    with (OUT/'summary/CONFIGURATIONS.csv').open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=fields,extrasaction='ignore');w.writeheader()
        for r in rows:w.writerow({**r,**r['acceptance'],'width_rejections':r.get('width_counters',{}).get('width_rejections'),'failed_gates':';'.join(r['acceptance']['failed_gates'])})
    figures(rows,stats,observations,summaries,comparison)
    root=read(OUT/'root_cause/REPRODUCTION.json');profile=read(OUT/'performance/TARGETED_PROFILE.json');old=root['B2_original'];new=root['C1_revised']
    def range_reduction(stage,eps):
        a=[r['vertex_reduction_percent'] for r in usable if r['stage']==stage and r['epsilon']==eps];return [min(a),max(a)] if a else [None,None]
    ranges={stage:{str(e):range_reduction(stage,e) for e in [0,.2,.35,.5,.75]} for stage in ['regression','independent_cohort']};write_json(OUT/'summary/REDUCTION_RANGES.json',ranges)
    correction=f'''# Feature-protection correction — v0.5C.1

The historical width-loss failure is reproduced byte-for-byte by original B2. At D4/S1 epsilon 0.50, the fixed vertical section at (57.5,556.5) changes from 9 to 8.916666666666629 cells. Original proposal p0000391 replaces [(57,561),(60,561),(60,560),(63,560)] with [(57,561),(63,560)]. The opposite boundary remains y=552. Direct coordinate interpolation gives y=560.9166666667 at x=57.5. This is a real 1/12-cell loss, not numeric tolerance.

The source probe EDT diameter is 8.94427191 cells, above the dense guard threshold 8; the nearest registered normal probe is 9.21954 cells away. The change hull lies 3.5 cells from the guard union; its opposing section is wider than the 2-cell proximity screen. The old chord passes collision, 0.25-cell clearance, raster-center, area, pore and displacement tests. **Both feature discovery and proposal-level width validation were incomplete.** None of those old gates measures this width.

The additive `{protocol['algorithm_version']}` keeps all original guards and budgets. It adds local spatial queries around a proposed change, native-axis projection events, affine source/opposing boundary sections, the existing C diagnostic horizon of 16 cells and zero qualifying width loss with 1e-10-cell numeric allowance. Ambiguous affected projections restore the original subchain. No coordinate-specific exception, global tolerance decrease, guard enlargement or geometry widening is used. Original B2 source and outputs remain intact.

The corrected targeted section is {new['width']:.12f} cells; the offending chord is rejected for qualifying_solid_width_loss. Original untraced engine time was {old['seconds']:.6f} s; revised was {new['seconds']:.6f} s. The revised candidate has {new['vertices']} vertices. These are single same-fixture observations, not universal speed estimates.

Fifty targeted controls passed. An initial four-direction prototype produced only a no-op; that record is retained. Before all independent generation, integrated checks were restricted to the two native axes because diagonal staircase projections fold. Independent oblique sections were retained as validators. Two rotated-control lookup failures were corrected by using the same rotation operation for polygon and exact source subchain; no scientific tolerance or prior test changed.

Across the complete study, {stats['width_rejections']} width/uncertainty rejection flags were recorded over {stats['integrated_sections']} qualifying affine-section checks. Within regression, {comparison['newly_prevented_previously_accepted']} formerly accepted original B2 leaves are now rejected specifically by width qualification. Rejection counts are repeated-setting leaf instances, not distinct physical struts or proven mechanical failures. Total local restorations {stats['local_rollbacks']}; unchanged chain instances {stats['unchanged_chains']}; assembly rollback instances {stats['assembly_rollbacks']}.

Regression: {len(reg)} configurations over all 20 consumed realizations, including all prior 80 C configurations and the conservative 0.35 settings. This is development/regression evidence, not untouched validation. At epsilon 0.50, revised reduction spans {ranges['regression']['0.5'][0]:.6f}–{ranges['regression']['0.5'][1]:.6f}%; at 0.75 it spans {ranges['regression']['0.75'][0]:.6f}–{ranges['regression']['0.75'][1]:.6f}%. Conservative no-ops at lower settings remain explicit.

Independent width audits use unchanged C axial sections plus source-only oblique probes at 22.5/67.5/112.5/157.5 degrees. They do not select proposal event cuts. Flagged oblique widths receive separate coordinate interpolation. GEOS parsing and geometry interfaces remain shared; mathematical/kernel independence is not claimed. Global arbitrary-direction minimum-width preservation remains UNQUALIFIED.

See 01_original_failure.png, 02_corrected_behavior.png and 03_feature_coverage.png. Source, chord, guards, affine witnesses and restored chains are retained in the root_cause and per-case engine records. No B2 or C acceptance is revised.
'''
    (OUT/'summary/FEATURE_PROTECTION_CORRECTION.md').write_text(correction)
    pore_report=f'''# Small-pore scientific qualification — separate from simplification

The saved D7/S0 source pore 1 has G1 area 1 cell², G2 area 0.96875 cell² and unchanged G2→G3 area. Its identity remains unique. The A1 regularizer adds solid in a local L1 diamond of radius 0.25 cell. One incident pore loses a right-isosceles triangle of area r²/2 = 1/32 = 0.03125 cell², giving 3.125% relative loss for a 1-cell² pore. The associated source contact, exact ring coordinates, actual footprint, perimeter and neighboring pore identities are retained in pore_policy/HISTORICAL_RECONSTRUCTION.json.

The existing A1 policy constrains global G1 occupied-area modification (0.0001), local support, validity/manifoldness, hole count, reconstruction, displacement and positive clearance. It did not register a G1-based 0.5% per-pore fidelity requirement. B2's 0.5% cap applies to each G2 pore under G2→G3. That distinction is preserved; it does not establish that a 3.125% cumulative pore change is scientifically adequate.

Both absolute and relative errors are required. The same 1/32-cell² loss gives 3.125% at area 1, 1.5625% at area 2 and 0.03125% at area 100. A single incident triangle crosses the 0.5% relative diagnostic at area 6.25 cell²; m incident contacts multiply both the construction bound and crossover by m. This is algebra, not permission to discard small pores or adopt an area tier.

Fifteen deterministic saved controls exercise these sizes, unaffected pores, shape change at equal area, merge/split/deletion/addition, exterior opening, raster-invisible change and absolute/relative diagnostic disagreement. An OR rule can accept a violation of one component; an AND rule detects both. Neither replaces topology/identity. The 0.03125-cell² absolute diagnostic is the construction scale, not an independently justified engineering allowance.

All real source pores are independently matched. Maximum G1→G2 absolute pore change is {pores['maximum_absolute_error']:.12g} cell²; maximum relative change is {pores['maximum_relative_error']:.6%}. Construction-envelope violations: {len(pores['construction_envelope_violations'])}. Maximum G2→G3 per-pore area distortion remains {stats['max_pore_G2_G3_fraction']:.6%}. Continuous shape/perimeter changes remain separately recorded even at zero area distortion.

**Disposition: the existing policy was applied correctly within its geometric scope; cumulative small-pore scientific fidelity remains UNQUALIFIED. No amended fidelity allowance is adopted.** A physical/measurement-based criterion and fresh policy qualification remain necessary. No pore is excluded and no merge, split or deletion is forgiven because its area is small. The original C finding and HOLD remain historical evidence.
'''
    worst=[p for p in pores['records'] if p['relative_error']==pores['maximum_relative_error']]
    pore_report+=f"\nActual cumulative G1→G3 matched-pore maxima over every setting: absolute {stats['max_pore_G1_G3_absolute']:.12g} cell²; relative {stats['max_pore_G1_G3_fraction']:.8%}. These direct measurements are separate from the G1→G2 maxima above.\n"
    pore_report+=f"\n**New independent finding:** {len(worst)} source pores attain the maximum relative error. Each has area 1→0.9375 cell² and two incident contact repairs, so two 1/32-cell² triangles give 6.25% loss. All are independent-cohort pores, and identities remain unique. Their fixture/pore/contact identifiers are retained in REAL_COHORT_PORE_AUDIT.json. The construction envelope predicts this loss; it does not justify accepting it as scientific fidelity. Both fixed absolute and relative diagnostic screens reject these cases. No rule was changed after this finding.\n"
    (OUT/'summary/SMALL_PORE_QUALIFICATION.md').write_text(pore_report)
    main_report=[f'# Independent scientific requalification — v0.5C.1\n',f"**Overall scientific status: {statuses['J_overall_scientific']}**. Feature qualification and cumulative pore policy are separate. Production remains HOLD / UNQUALIFIED. No export or CAD work is implemented.\n",'## Method and root cause\n',correction.split('\n\n')[1]+'\n','The four states remain G0 canonical native1024 binary occupancy, G1 exact cell geometry, G2 explicit A1 manifold candidate and G3 revised protected simplification. Every source is authenticated; G1→G2, G2→G3, actual G1→G3 and native-grid reconstruction remain distinct. All prior files and scientific statuses are immutable.\n', 'The versioned proposal gate and independent audit are detailed in FEATURE_PROTECTION_CORRECTION.md and the frozen protocol. Event-slab source/opposition width functions are affine where single-valued; the largest qualifying loss is checked at the applicable interval endpoints. One-sided limits are explicitly distinguished from a possibly ambiguous section exactly at an event coordinate. Only the registered directions/horizon are covered. Unsupported or ambiguous input remains a failure, not a zero measurement.\n','## Synthetic and regression evidence\n',f"50 new targeted tests cover safe/unsafe/uncertain sections, conservative restoration and small-pore diagnostics. Original B2 reproduced the historical failure byte-for-byte; revised actual width is {new['width']:.12f} cells. All {len(reg)} regression settings are retained with original/revised proposal, geometry, vertex and timing comparisons.\n",'## Untouched independent cohort\n','Six new parameter combinations were selected by scipy.stats.qmc.LatinHypercube with seed 20261021 inside exactly the original v0.3 bounds. Replicate seeds are 12031 and 12032. All prior ten points/seeds are consumed evidence. Final corrected code, settings, controls, regression results, policy and cohort were hashed before generating or inspecting the new native outputs. No parameter was selected for expected passing behavior and no holdout was used to tune the algorithm.\n','| New point | Solid fraction target | Strut scale | Pore scale | Nearest old normalized distance |\n|---|---:|---:|---:|---:|']
    for s in protocol['cohort'][::2]:
        p=s['requested'];main_report.append(f"| {s['design_id']-100} | {p['solid_fraction_target']:.17g} | {p['strut_scale']:.17g} | {p['pore_scale']:.17g} | {s['nearest_old_normalized_distance']:.8f} |")
    main_report += ['',f"Independent structures: {len({r['fixture'] for r in ind})}/12; independent configurations: {len(ind)}/60 at [0,0.20,0.35,0.50,0.75]. Unsupported sources: {unsupported}. Internal errors: {errors}. Independent feature status: **{statuses['F_independent_features']}**. No unsupported or failed case is excluded from the expected denominator.\n",'## Continuous, discrete and feature results\n',f"Frozen hard constraints passed {stats['frozen_B2_passes']}/{len(usable)}; independently manifold {stats['geometry_manifold_passes']}/{len(usable)}; XOR zero {stats['raster_exact_passes']}/{len(usable)}; frozen descriptor equality {stats['descriptor_passes']}/{len(usable)}. Maximum G2→G3 symmetric area {stats['max_symmetric_G2_G3']:.12g} cell²; actual G1→G3 {stats['max_symmetric_G1_G3']:.12g} cell². Added/removed maxima {stats['max_added']:.12g}/{stats['max_removed']:.12g} cell². Independent displacement upper maxima G2→G3 {stats['max_distance_upper']:.12g}, G1→G3 {stats['max_cumulative_distance_upper']:.12g} cell, against sqrt(2)/2 + 1e-10.\n",'Budgets are unchanged: added/removed each 0.0025 of G2 occupied area; symmetric 0.005 of G2 occupied area; each matched G2 pore distortion 0.005 of that pore; guard coordinates/sets exact; registered widths and repair clearances permit zero loss with 1e-10-cell numeric allowance. C cumulative global screens use G1 occupied area and actual G1→G3 displacement. No cumulative per-pore0.5% cap is invented retrospectively.\n',f"Registered repair sites {stats['registered_repairs']}; registered natural probes {stats['registered_natural_probes']}; unique independent axial probes {stats['independent_axial_unique']}; oblique probes {stats['independent_oblique_unique']}. Axial/oblique evaluations {stats['axial_evaluations']}/{stats['oblique_evaluations']}. Narrowing events {stats['axial_narrowed']}/{stats['oblique_narrowed']}; undefined {stats['undefined']}; maximum measured new independent narrowing {stats['maximum_measured_narrowing']:.12g} cell. Registered width-loss maximum {stats['max_registered_width_loss']:.12g}; repair-clearance-loss maximum {stats['max_repair_clearance_loss']:.12g} cell.\n",'Pore identity, split/merge/birth/deletion and domain-void incidence are independently checked alongside direct edge/ring incidence, orientation, WKB/coordinate reconstruction and native-center rasterization. Boundary displacement uses the unchanged C changed-line sampling with maximum gap0.025 cell and an explicit Lipschitz upper bound; sampled maxima alone are not exact continuous Hausdorff distances. Descriptor reuse requires independently proven identical arrays; fresh original and selected changed-candidate integration evaluations are retained. Frozen whole-mask P10 and its historical calibration caveat are unchanged.\n','## Small-pore policy\n','\n\n'.join(pore_report.split('\n\n')[-3:])+'\n','## Performance\n',f"Regression plus independent execution: {summary['execution_seconds']:.3f} s, excluding development, reporting, tests and targeted profiling. Whole-study process lifetime RSS high-water: {summary['peak_process_lifetime_rss_bytes']/2**20:.3f} MiB. The studies were untraced; targeted same-fixture engine tracing and native-worker generation peaks are separately saved. Do not present selected stage peaks as a measured full-validation tracemalloc peak. GEOS-native allocation is incompletely covered by Python tracing.\n",f"Matched targeted instrumented engine times: original {profile['records'][0]['instrumented_engine_seconds']:.6f} s, revised {profile['records'][1]['instrumented_engine_seconds']:.6f} s. Traced engine peaks: {profile['records'][0]['engine_traced_peak_bytes']/2**20:.3f} and {profile['records'][1]['engine_traced_peak_bytes']/2**20:.3f} MiB. Single-run observations; historical C/B2 studies used different instrumentation and are not fair speed comparators.\n",'## Scientific interpretation and limitations\n','The correction addresses a generalized native-axis corridor mechanism and preserves useful local simplification, with conservative no-op behavior for uncertain edits. Independent oblique measurements supplement its finite orientation set. Neither finite probe success nor the affine local rule establishes arbitrary-direction/global minimum-neck preservation. Fixed directions/horizon, feature-selection bias, source resolution, floating arithmetic and shared GEOS remain limitations. Raster equality is discrete consistency evidence, not continuous equivalence.\n','The small-pore result remains scientifically unresolved under a cumulative fidelity policy. No physical dimensions, CAD-kernel tolerance/interoperability, material law, loads, meshing, strength or manufacturing criteria are established. The v0.4.2 failure, scoped v0.4.3 amendment, A HOLD, A1/B2 geometric acceptances and historical C HOLD are unchanged.\n','## Separate acceptance statuses\n','| Scope | Status |\n|---|---|']
    at=main_report.index('## Small-pore policy\n')
    table=['### Separate transformation maxima\n','Each column is its own maximum across evaluable configurations; a row does not describe one selected fixture. Areas are cell²; displacement is cells.\n','| Transformation | Added | Removed | Symmetric | Relative symmetric | Displacement upper |\n|---|---:|---:|---:|---:|---:|']
    for k,v in stats['transform_maxima'].items():table.append(f"| {k.replace('_','→')} | {v['added']:.12g} | {v['removed']:.12g} | {v['symmetric']:.12g} | {v['relative_symmetric']:.8%} | {v['displacement_upper']:.12g} |")
    table+=['',f"Actual cumulative G1→G3 matched-pore maxima: absolute {stats['max_pore_G1_G3_absolute']:.12g} cell²; relative {stats['max_pore_G1_G3_fraction']:.8%}. These are measured directly, rather than inferred by summing stage errors.\n"]
    table+=['### Monitored-section coverage\n','Counts include repeated tolerances. A chord intersection may retain a collinear section; it does not alone establish a width change.\n','| Cohort | Method | Evaluations | Unguarded centers | Sections not entirely guarded | Section geometry changed | Accepted chord incidence | Metadata unresolved |\n|---|---|---:|---:|---:|---:|---:|---:|']
    for v in coverage:table.append(f"| {v['stage']} | {v['kind']} | {v['evaluations']} | {v['unguarded_centers']} | {v['sections_not_entirely_guarded']} | {v['geometry_changed_sections']} | {v['accepted_chord_incidence_sections']} | {v['unresolved_section_metadata']} |")
    table+=['','Undefined width measurements and unresolved reporting metadata are separate. A reporting incidence calculation never changes the prospectively registered width decision.\n']
    table+=['**Coverage limitation:** none of the monitored registered, axial, or oblique sections intersects an accepted replacement chord in this study. Consequently these finite audits verify unchanged sampled sections; they do not independently interrogate every accepted edit. The proposal-integrated affine gate supplies the direct changed-region protection in the registered native directions. Oblique probe selection is biased toward short source corridors, many already guarded. This limits the strength of feature generalization despite all prospective sampled gates passing.\n']
    main_report[at:at]=table
    main_report += [f'| {k} | {v} |' for k,v in statuses.items()]
    main_report += ['','## Handoff and verification\n','General advancement remains HOLD while the cumulative pore-fidelity policy is unqualified. Even a feature-screen pass is not production, CAD or FEM qualification. A later policy decision or algorithm revision requires separately versioned rules and newly reserved independent evidence. The C.1 handoff defines these restrictions; v0.5D is not implemented.\n','Final software regression, historical preservation, hash ledger, repeat checks and figure inspection are recorded under verification/COMPLETION.json. CONFIGURATIONS.csv lists every case, including failures; FEATURE_HOLDS.json retains any independent disagreements. FINAL_RESPONSE.md answers all42 requested completion questions.\n','## Scientific figures\n']
    for p in sorted((OUT/'figures').glob('*.png')):main_report.append(f'[{p.stem}]({p.resolve()})\n')
    (OUT/'summary/INDEPENDENT_REQUALIFICATION.md').write_text('\n'.join(main_report))
    write_json(OUT/'performance/REPORTING.json',{'seconds':time.perf_counter()-began})
    print('Report statuses',statuses,'stats',stats,'pore relative',pores['maximum_relative_error'],flush=True)


if __name__=='__main__':main()
