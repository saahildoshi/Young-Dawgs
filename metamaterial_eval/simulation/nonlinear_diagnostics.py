"""Versioned native MAPDL diagnostics; trial data never become mechanical scores."""
from dataclasses import dataclass
import csv
import heapq
import json
import math
from pathlib import Path
import re
import numpy as np
from .reporting import write_json
from .solver_execution import discover_solver,file_hash,has_negative_pivots,solver_warnings,solver_release
from .windows_ansys import bounded_run

NUMBER=r'[+\-]?(?:\d+\.?\d*|\.\d+)(?:[EDed][+\-]?\d+)?'


def finite(value):
    number=float(str(value).replace('D','E').replace('d','e'))
    if not math.isfinite(number):raise ValueError('Nonfinite diagnostic value')
    return number


def residual_trend(values):
    a=np.asarray(values,dtype=float)
    if not len(a):return 'MISSING'
    if not np.isfinite(a).all() or np.any(a<0):raise ValueError('Invalid residual sequence')
    if a[-1]<=1:return 'BELOW_FORCE_CRITERION_ONLY'
    if len(a)<4:return 'INSUFFICIENT_HISTORY'
    a=a[-6:];d=np.diff(a)
    if np.all(d<=0) and a[-1]<a[0]*.8:return 'DECREASING_NOT_CONVERGED'
    if np.all(d>=0) and a[-1]>a[0]*1.2:return 'INCREASING'
    if np.ptp(a)<=max(np.mean(a)*.25,1e-12):return 'PLATEAU'
    if np.any(d>0) and np.any(d<0):return 'OSCILLATING'
    return 'UNRESOLVED'


def parse_solver_log(text):
    """Keep source order, repeated iteration numbers and incomplete terminal work.

    Force evaluations precede Newton updates. They are recorded with the last
    completed iteration, not falsely called residuals after the next update.
    CP is process CPU time; TIME=HH:MM:SS is a wall-clock stamp, not load time.
    """
    force=[];disp=[];iterations=[];cuts=[];converged=[];pivots=[];search=[]
    last_iter=0;trial=0;cp=None;wall=None;step=None;sub=None
    for lineno,line in enumerate(text.splitlines(),1):
        m=re.search(r'CP\s*=\s*('+NUMBER+r')',line)
        if m:cp=finite(m[1])
        m=re.search(r'TIME=\s*(\d\d:\d\d:\d\d)',line)
        if m:wall=m[1]
        m=re.search(r'FORCE CONVERGENCE VALUE\s*=\s*('+NUMBER+r')\s+CRITERION=\s*('+NUMBER+r')',line)
        if m:
            value,criterion=map(finite,m.groups())
            if criterion<=0 or value<0:raise ValueError('Invalid force criterion')
            force.append({'source_line':lineno,'evaluation':len(force),'last_completed_iteration':last_iter,'trial_sequence':trial,'value_N':value,'criterion_N':criterion,'ratio':value/criterion,'diagnostic_only':True})
        m=re.search(r'DISP CONVERGENCE VALUE\s*=\s*('+NUMBER+r')\s+CRITERION=\s*('+NUMBER+r')',line)
        if m:disp.append({'source_line':lineno,'value_mm':finite(m[1]),'criterion_mm':finite(m[2]),'solver_marked_displacement_converged':'<<< CONVERGED' in line,'trial_sequence':trial})
        m=re.search(r'EQUIL ITER\s+(\d+) COMPLETED.*MAX DOF INC=\s*('+NUMBER+r')',line)
        if m:
            last_iter=int(m[1]);iterations.append({'source_line':lineno,'iteration':last_iter,'trial_sequence':trial,'max_DOF_increment':finite(m[2]),'new_tangent':'NEW TRIANG MATRIX' in line,'preceding_CP_seconds':cp,'preceding_wall_clock':wall})
        m=re.search(r'LINE SEARCH PARAMETER\s*=\s*('+NUMBER+r')',line)
        if m:search.append({'source_line':lineno,'factor':finite(m[1]),'trial_sequence':trial,'iteration':last_iter})
        # Explicit native bisection events only: ignore descriptive option lines.
        if re.search(r'BISECTION NUMBER|BISECTING|BISected|CUTBACK.*(?:DUE|REASON)',line,re.I):
            trial+=1;last_iter=0;cuts.append({'source_line':lineno,'text':line.strip(),'trial_sequence':trial})
        m=re.search(r'LOAD STEP\s+(\d+)\s+SUBSTEP\s+(\d+)\s+COMPLETED',line)
        if m:
            step,sub=map(int,m.groups());converged.append({'source_line':lineno,'load_step':step,'substep':sub});last_iter=0
        m=re.search(r'# of negative pivots\s*=\s*(\d+)',line,re.I)
        if m:pivots.append(int(m[1]))
    ratios=[r['ratio'] for r in force]
    return {'schema':'young-dawgs-native-nonlinear-log-v1','force_evaluations':force,'displacement_evaluations':disp,'completed_iterations':iterations,'line_search':search,'cutback_events':cuts,'converged_substeps':converged,'negative_pivot_counts':pivots,'warnings':solver_warnings(text),'force_trend':residual_trend(ratios[1:]),'best_force_ratio':min(ratios) if ratios else None,'last_force_ratio':ratios[-1] if ratios else None,'factorizations_completed':sum(r['new_tangent'] for r in iterations),'factorizations_started':len(re.findall(r'# of negative pivots\s*=',text,re.I)),'limits':'CPU/wall stamps are explicitly observed; no invented iteration duration or trial displacement when absent.'}


def parse_contact(text):
    """Read complete native COLDATA blocks; retain a truncated-tail warning."""
    columns={int(i):label.strip() for i,label in re.findall(r'<COLUMN ID="\s*(\d+)">(.*?)</COLUMN>',text)}
    records=[];issues=[]
    if not columns:return {'records':[],'issues':['MISSING_HEADER'],'frequency':None}
    required={1:'Contact Pair ID',2:'Number of Contact Elements in Contact',4:'Max. Chattering Level',5:'Max. Penetration/Min. Gap',7:'Max. Normal Stiffness',14:'Max. Contact Pressure',32:'Total contact force due to pressure -y component'}
    if any(columns.get(i)!=name for i,name in required.items()):raise ValueError('Unsupported contact column schema')
    blocks=re.findall(r'<COLDATA\s+([^>]+)>(.*?)</COLDATA>',text,re.S)
    if text.count('<COLDATA ')!=len(blocks):issues.append('INCOMPLETE_FINAL_BLOCK')
    for block,(header,body) in enumerate(blocks):
        meta=dict(re.findall(r'(\w+)="\s*([^" ]+)\s*"',header));seen=set()
        for line in body.splitlines():
            if not line.strip():continue
            values=[finite(v) for v in line.split()]
            if len(values)!=len(columns):raise ValueError('Incomplete contact row')
            pair=int(values[0])
            if pair in seen:raise ValueError('Duplicate contact pair within iteration block')
            seen.add(pair)
            records.append({'block_sequence':block,'load_step':int(meta['LOAD_STEP']),'substep':int(meta['SUBSTEP']),'iteration':int(meta['ITERATION']),'pseudo_time':finite(meta['TIME']),'pair':pair,'active_elements':int(values[1]),'sticking_elements':int(values[2]),'chattering_level':values[3],'penetration_or_gap_mm':values[4],'geometric_gap_mm':values[5],'max_normal_stiffness':values[6],'min_normal_stiffness':values[7],'max_pressure_MPa':values[13],'contact_force_y_N':values[31],'force_norm':values[37],'force_criterion':values[38],'scope':'UNCONVERGED_DIAGNOSTIC_ONLY; convergence must be corroborated separately'})
    frequency=re.search(r'<HEADER FRQ="([^"]+)"',text)
    return {'columns':columns,'records':records,'issues':issues,'frequency':frequency[1] if frequency else None}


def contact_summary(records,expected_pairs=(2,3)):
    result={}
    for pair in expected_pairs:
        a=[r for r in records if r['pair']==pair]
        if not a:result[str(pair)]={'status':'MISSING_PAIR'};continue
        state=[r['active_elements']>0 for r in a]
        transitions=sum(x!=y for x,y in zip(state,state[1:]))
        result[str(pair)]={'status':'ACTIVE_AT_ALL_RECORDED_ITERATIONS' if all(state) else 'CONTACT_OPENS_OR_INACTIVE',
            'records':len(a),'min_active_elements':min(r['active_elements'] for r in a),'max_active_elements':max(r['active_elements'] for r in a),'whole_pair_open_closed_transitions':transitions,
            'max_chattering_level':max(r['chattering_level'] for r in a),'chattering_evidenced':max(r['chattering_level'] for r in a)>0 or transitions>=2,
            'min_normal_stiffness':min(r['min_normal_stiffness'] for r in a),'max_normal_stiffness':max(r['max_normal_stiffness'] for r in a),'max_recorded_penetration_mm':max(0,max(r['penetration_or_gap_mm'] for r in a)),'max_recorded_pressure_MPa':max(r['max_pressure_MPa'] for r in a),
            'limitation':'Pair counts cannot identify which individual contact elements switched; far-field penetration/gap may be pinball, not a measured gap.'}
    return result


def localize_residual(path,nodes,boundary=None,groups=None,top_count=32):
    """Stream observed v241 text NR format. Component signs are not inferred.

    DOF codes 1,2,6 are FX,FY,MZ. Platen/internal nodes are inventoried but
    excluded from specimen localization. Missing/truncated nodes are failures.
    """
    nodes=np.asarray(nodes);heap=[];seen=set();sum_squares=0.;specimen=0
    with Path(path).open() as stream:
        lines=(s.strip() for s in stream if s.strip());first=next(lines)
        if not first.startswith('/COM,ANSYS RELEASE 2024 R1'):raise ValueError('Unverified residual file version')
        convergence=next(lines);header=next(lines).split();dofs=list(map(int,next(lines).split()))
        if dofs!=[1,2,6] or len(header)!=5:raise ValueError('Unsupported residual DOF schema')
        count=int(header[0]);meta={'native_nodes':count,'pseudo_time':finite(header[1]),'load_step':int(header[2]),'substep':int(header[3]),'iteration':int(header[4]),'DOF_codes':dofs}
        for line in lines:
            row=line.split()
            if len(row)!=4:raise ValueError('Partial residual row')
            node=int(row[0]);values=[finite(x) for x in row[1:]]
            if node in seen:raise ValueError('Duplicate residual node')
            seen.add(node)
            if 1<=node<=len(nodes):
                specimen+=1;norm=math.hypot(*values[:2]);sum_squares+=norm*norm
                item=(norm,node,values[0],values[1])
                if len(heap)<top_count:heapq.heappush(heap,item)
                elif item>heap[0]:heapq.heapreplace(heap,item)
        if len(seen)!=count or specimen!=len(nodes):raise ValueError('Incomplete residual snapshot or missing specimen node')
    ranked=[]
    for norm,node,fx,fy in sorted(heap,reverse=True):
        xy=nodes[node-1];r={'node':node,'xy_mm':xy.tolist(),'FX_component_magnitude_N':fx,'FY_component_magnitude_N':fy,'translation_residual_norm_N':norm,'dominant_direction':'FY' if abs(fy)>=abs(fx) else 'FX','distance_to_bottom_mm':float(xy[1]),'distance_to_top_mm':float(nodes[:,1].max()-xy[1])}
        if boundary is not None:
            ids=np.flatnonzero(np.any(np.asarray(boundary)==node-1,axis=1));r['boundary_membership']=sorted(set(np.asarray(groups)[ids].tolist()))
        ranked.append(r)
    meta.update(source_sha256=file_hash(path),top_residual_nodes=ranked,specimen_translation_L2_N=math.sqrt(sum_squares),scope='UNCONVERGED_DIAGNOSTIC_ONLY; native component magnitudes, no signed trial forces or physical performance score',native_convergence_header=convergence)
    return meta


@dataclass(frozen=True)
class DiagnosticBudget:
    bytes_cap:int=2*1024**3
    native_snapshot_cap:int=4
    completed_iterations_cap:int=16
    cutbacks_cap:int=4
    trend_window:int=6
    stop_stagnation:bool=False


def telemetry_commands(top):
    return ['NLDIAG,CONT,ITER','NLDIAG,NRRE,ON,2','NLDIAG,EFLG,ON,2',f'NLHIST,NSOL,UYTOP,U,Y,{top}',f'NLHIST,NSOL,RFUP,F,Y,{top}']


def diagnostic_stop(directory,budget):
    directory=Path(directory)
    files=[p for p in directory.iterdir() if re.search(r'\.(?:nr\d+|nd\d+|cnd|nlh)$',p.name)]
    sizes=[]
    for p in files:
        try:sizes.append(p.stat().st_size)
        except FileNotFoundError:pass  # Native ring rotation can remove/recreate.
    if sum(sizes)>budget.bytes_cap:return 'DIAGNOSTIC_DISK_BUDGET'
    if len([p for p in files if re.search(r'\.(?:nr|nd)\d+$',p.name)])>budget.native_snapshot_cap:return 'DIAGNOSTIC_FILE_COUNT_LIMIT'
    log=directory/'solver.out'
    if not log.exists():return None
    text=log.read_text(errors='replace');parsed=parse_solver_log(text)
    if has_negative_pivots(text) or re.search(r'element.*highly distorted',text,re.I):return 'SOLVER_PIVOT_OR_DISTORTION_STOP'
    if len(parsed['completed_iterations'])>=budget.completed_iterations_cap:return 'REGISTERED_ITERATION_LIMIT'
    if len(parsed['cutback_events'])>=budget.cutbacks_cap:return 'REGISTERED_CUTBACK_LIMIT'
    if budget.stop_stagnation and len(parsed['cutback_events'])>=2:
        values=[v['ratio'] for v in parsed['force_evaluations'] if v['trial_sequence']==len(parsed['cutback_events'])]
        if len(values)>=budget.trend_window and residual_trend(values) in ['PLATEAU','OSCILLATING','INCREASING']:return 'REGISTERED_RESIDUAL_STAGNATION'
    return None


def run_diagnostic(directory,*,cores=1,timeout=180,rss_GiB=8,budget=None):
    directory=Path(directory);budget=budget or DiagnosticBudget(bytes_cap=256*1024**2,completed_iterations_cap=300,cutbacks_cap=100)
    if cores not in [1,2]:raise ValueError('Only prospectively registered 1/2-core diagnostic probes')
    process=bounded_run([str(discover_solver()),'-b','-smp','-np',str(cores),'-m','4096','-j','compression','-i','input.inp','-o','solver.out'],directory,prepared=True,timeout=timeout,rss_limit=rss_GiB*1024**3,min_disk_free=20*1024**3,min_available_ram=12*1024**3,stop_check=lambda p:diagnostic_stop(p,budget))
    text=(directory/'solver.out').read_text(errors='replace') if (directory/'solver.out').exists() else ''
    parsed=parse_solver_log(text)
    receipt={'status':process['status'],'process':process,'solver_version':solver_release(text),'input_sha256':file_hash(directory/'input.inp'),'converged_steps':[(r['load_step'],r['substep']) for r in parsed['converged_substeps']],'warnings':solver_warnings(text),'diagnostic_only':True}
    write_json(directory/'execution_receipt.json',receipt)
    write_json(directory/'nonlinear_telemetry.json',parsed)
    contact=parse_contact((directory/'compression.cnd').read_text(errors='replace')) if (directory/'compression.cnd').exists() else {'records':[],'issues':['MISSING_FILE']}
    write_json(directory/'contact_telemetry.json',contact);write_json(directory/'contact_summary.json',contact_summary(contact['records']))
    return receipt


def export_csv(path,records):
    if not records:return
    with Path(path).open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
