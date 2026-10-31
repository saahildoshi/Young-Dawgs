"""Native multiframe continuation, cumulative loading and multi-set exports."""
from dataclasses import dataclass
from pathlib import Path
import math
import json
import re
import shutil
import time
import psutil
from .microstructure_pilot import database_resume,stage_block,vector_fields
from .native_output import SELECTIVE_OUTPUT,chunked_vectors
from .nonlinear_diagnostics import parse_solver_log,parse_contact,contact_summary,telemetry_commands
from .system_health import HealthPolicy
from .windows_ansys import bounded_run
from .solver_execution import discover_solver,file_hash,solver_release,solver_warnings
from .reporting import write_json
from .general_contact_output import general_contact_vectors


def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def validate_targets(targets,start=0):
    if not targets or any(not math.isfinite(x) or not start<x<=.4 for x in targets):raise ValueError('Invalid progressive targets')
    if list(targets)!=sorted(set(targets)):raise ValueError('Targets must increase without duplicates')


def load_commands(target,previous,top,height,*,initial=.0005,minimum=1e-6,maximum=.005,all_fields=True):
    validate_targets([target],previous)
    delta=target-previous
    initial_steps=max(1,math.ceil(delta/initial));minimum_steps=max(1,math.ceil(delta/maximum))
    maximum_steps=max(initial_steps,math.ceil(delta/minimum))
    return ['AUTOTS,ON','NEQIT,24','NROPT,FULL','LNSRCH,ON','KBC,0',
            f'NSUBST,{initial_steps},{maximum_steps},{minimum_steps},OFF',
            'OUTRES,ERASE','OUTRES,ALL,NONE']+[
            'OUTRES,'+item+(','+'ALL' if all_fields else ',LAST') for item in ['NSOL','RSOL','STRS','EPEL','CONT','MISC']]+[
            'OUTPR,ALL,NONE','OSRESULT,ERASE','RESCONTROL,DEFINE,ALL,1,-1,,3',
            f'TIME,{target:.17g}',f'D,{top},UY,{-height*target:.17g}','SOLVE']


def authenticated_restart_copy(source,target,*,expected_mesh=None):
    source,target=Path(source),Path(target)
    receipt=load(source/'execution_receipt.json');manifest=load(source/'simulation_manifest.json')
    if expected_mesh is not None and manifest.get('mesh_semantic_sha256')!=expected_mesh:raise ValueError('Restart mesh mismatch')
    required=['compression.rdb','compression.ldhi']
    frames=sorted(p.name for p in source.glob('compression.r[0-9][0-9][0-9]'))
    if not frames:raise ValueError('No native multiframe restart frame')
    files=required+frames+(['compression.rst'] if (source/'compression.rst').exists() else [])
    inventory={}
    for name in files:
        path=source/name
        if not path.is_file():raise ValueError('Missing native restart file '+name)
        digest=file_hash(path)
        if receipt['process']['artifacts'].get(name,{}).get('sha256')!=digest:raise ValueError('Altered/stale restart file '+name)
        inventory[name]={'bytes':path.stat().st_size,'sha256':digest}
    target.mkdir(parents=True,exist_ok=False)
    for name in files:shutil.copy2(source/name,target/name)
    write_json(target/'restart_provenance.json',{'source':str(source.resolve()),'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
        'source_manifest_sha256':file_hash(source/'simulation_manifest.json'),'copied_native_files':inventory,
        'source_never_modified':True,'mesh_semantic_sha256':manifest.get('mesh_semantic_sha256')})
    return manifest


def continuation_input(load_step,substep,targets,previous,model,*,all_fields=True,initial=.0005):
    validate_targets(targets,previous)
    if min(load_step,substep)<1 or substep==999999:raise ValueError('Invalid native restart checkpoint')
    lines=['/BATCH','/CLEAR,START','RESUME,compression,rdb','/FILNAME,compression','/GOPR','/SOLU',
           f'ANTYPE,STATIC,REST,{load_step},{substep},CONTINUE']+telemetry_commands(model['controls']['top'])+[
           f'NLHIST,NSOL,RFLOW,F,Y,{model["controls"]["bottom"]}']
    for target in targets:
        lines+=load_commands(target,previous,model['controls']['top'],model['config']['height'],initial=initial,all_fields=all_fields)
        previous=target
    return '\n'.join(lines+['FINISH','SAVE,checkpoint,db,,MODEL','/EXIT,NOSAVE'])+'\n'


def result_sets(text):
    rows=[]
    for n,t,ls,ss,cumulative in re.findall(r'^\s*(\d+)\s+([\d.Ee+\-]+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$',text,re.M):
        row={'set':int(n),'time':float(t),'load_step':int(ls),'substep':int(ss),'cumulative_iterations':int(cumulative)}
        if row['substep']==999999:continue
        if rows and (row['set']<=rows[-1]['set'] or row['time']<=rows[-1]['time']):raise ValueError('Duplicate/unordered native result sets')
        rows.append(row)
    if not rows:raise ValueError('No readable converged native result sets')
    return rows


def multi_export_input(database,result_base,model,states,*,chunk_size=250000,farfield=False):
    result_base=Path(result_base).resolve().as_posix()
    if "'" in result_base:raise ValueError('Unsupported result path')
    lines=['/BATCH','/CLEAR,START',database_resume(database).strip(),'/FILNAME,readonly','/GOPR',
           '/POST1',"FILE,'"+result_base+"',rst",'/OUTPUT,result_sets,txt','SET,LIST','/OUTPUT']
    old=vector_fields(model['specimen_nodes'],'stage001')
    seen=set()
    for i,state in enumerate(states,1):
        key=(state['load_step'],state['substep'])
        if key in seen or min(key)<1 or key[1]==999999:raise ValueError('Duplicate/invalid export state')
        seen.add(key);block=stage_block(1,state['time'],model,{})
        block=block[block.index('/POST1'):]
        offset=next(j for j in range(len(block)) if block[j:j+len(old)]==old)
        block=block[:offset]+chunked_vectors(model['specimen_nodes'],'stage001',chunk_size)+block[offset+len(old):]
        if farfield:
            where=block.index('*CFOPEN,stage001_contact,csv')
            inventory=['ESEL,S,ENAME,,172','ETABLE,ERAS','ETABLE,CNSTAT,NMISC,19','ALLSEL,ALL',
                '*CFOPEN,stage001_contact_status,csv','*VWRITE',"('pair,element,status')",'*DO,PAIR,1,2',
                '*IF,PAIR,EQ,1,THEN','CMSEL,S,BOTTOM_CONTACT','*ELSE','CMSEL,S,TOP_CONTACT','*ENDIF',
                '*GET,NC,ELEM,0,COUNT','EID=0','*DO,KK,1,NC','EID=ELNEXT(EID)',
                '*GET,CSTATV,ELEM,EID,ETAB,CNSTAT','*VWRITE,PAIR,EID,CSTATV',"(F4.0,',',F12.0,',',F4.0)",
                '*ENDDO','ALLSEL,ALL','*ENDDO','*CFCLOS']
            block=block[:where]+inventory+block[where:]
            revised=[];inside=False
            for line in block:
                if line=='*GET,STV,ELEM,EID,NMISC,19':
                    revised.extend(['*GET,STV,ELEM,EID,ETAB,CNSTAT','*IF,STV,GT,0,THEN']);inside=True
                elif line=='*ENDDO' and inside:
                    revised.extend(['*ENDIF',line]);inside=False
                else:revised.append(line)
            block=revised
        if model.get('general_contact_elements'):
            if not farfield:raise ValueError('General contact requires explicit native availability inventory')
            where=block.index('*IF,FAILG,NE,0,THEN')
            block=block[:where]+general_contact_vectors(model,'stage001',chunk_size=min(250000,chunk_size))+block[where:]
        for line in block:
            if line=='/POST1':lines+=['/POST1',"FILE,'"+result_base+"',rst"]
            elif line=='SET,LAST':lines.append(f'SET,{key[0]},{key[1]}')
            elif line.startswith('*IF,ABS(TNOW-'):
                lines.extend([f'*IF,LSV,NE,{key[0]},THEN','FAILG=1','*ENDIF',f'*IF,SSV,NE,{key[1]},THEN'])
            elif line.startswith('*IF,ABS(UYTOP-'):
                lines.append(f'*IF,ABS(UYTOP+({model["config"]["height"]:.17g})*TNOW),GT,1e-8,THEN')
            elif line=='SAVE,pilot_partial,db' or line=='/EXIT,NOSAVE':lines.append('/COM,UNQUALIFIED_STATE_EXPORTED_FOR_DIAGNOSTICS')
            else:lines.append(line.replace('stage001',f'stage{i:03d}'))
    text='\n'.join(lines+['FINISH','/EXIT,NOSAVE'])+'\n'
    if re.search(r'^\s*(?:SOLVE|SAVE\s*,)',text,re.M|re.I):raise ValueError('Read-only export contains mutation')
    return text


@dataclass
class ProgressMonitor:
    no_progress_seconds:float=1800
    diagnostic_bytes:int=2*1024**3
    max_cutbacks_without_progress:int=10

    def __post_init__(self):
        self.start=time.monotonic();self.last_progress=self.start;self.last_key=None;self.last_check=-1e30
        self.observed=[]

    def __call__(self,directory):
        now=time.monotonic()
        if now-self.last_check<1:return None
        self.last_check=now;directory=Path(directory)
        total=0
        for path in directory.iterdir():
            if re.search(r'\.(?:nr\d+|nd\d+|cnd|nlh)$',path.name):
                try:total+=path.stat().st_size
                except FileNotFoundError:pass
        if total>self.diagnostic_bytes:return 'DIAGNOSTIC_DISK_BUDGET'
        log=directory/'solver.out'
        if not log.exists():return None
        with log.open('rb') as stream:
            stream.seek(max(0,log.stat().st_size-512000));text=stream.read().decode(errors='replace')
        if re.search(r'^\s*\*\*\*\s*(?:ERROR|FATAL)\s*\*\*\*|element.*highly distorted',text,re.M|re.I):return 'NATIVE_SOLVER_ERROR_OR_DISTORTION'
        parsed=parse_solver_log(text)
        if parsed['converged_substeps']:
            latest=parsed['converged_substeps'][-1]
            key=(latest['load_step'],latest['substep'],latest.get('pseudo_time'))
            if key!=self.last_key:
                self.last_key=key;self.last_progress=now
                self.observed.append({'elapsed_seconds':now-self.start,**latest})
                write_json(directory/'progress_live.json',{'latest_converged':latest,'last_progress_seconds':now-self.start})
        if now-self.last_progress>self.no_progress_seconds:return 'NO_CONVERGED_PROGRESS_TIMEOUT'
        last_line=parsed['converged_substeps'][-1]['source_line'] if parsed['converged_substeps'] else 0
        recent_cuts=sum(r['source_line']>last_line for r in parsed['cutback_events'])
        if recent_cuts>=self.max_cutbacks_without_progress and now-self.last_progress>300:return 'REPEATED_CUTBACKS_WITHOUT_PROGRESS'
        return None


def run_progressive(directory,*,timeout=5400,solve=True,no_progress_seconds=1800,cores=2,disk_reserve=40*1024**3):
    directory=Path(directory)
    if [p.pid for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() in ['ansys.exe','ansys241.exe']]:raise RuntimeError('Another MAPDL process is active')
    monitor=ProgressMonitor(no_progress_seconds=no_progress_seconds)
    process=bounded_run([str(discover_solver()),'-b','-smp','-np',str(cores),'-m','4096','-j','compression' if solve else 'readonly',
        '-i','input.inp','-o','solver.out'],directory,prepared=True,timeout=timeout,rss_limit=None,
        min_disk_free=disk_reserve,min_available_ram=0,resource_sample_seconds=5,health_policy=HealthPolicy(),stop_check=monitor if solve else None)
    text=(directory/'solver.out').read_text(errors='replace') if (directory/'solver.out').exists() else ''
    parsed=parse_solver_log(text);warnings=solver_warnings(text)
    receipt={'status':process['status'],'process':process,'solver_version':solver_release(text),
        'input_sha256':file_hash(directory/'input.inp'),'warnings':list(dict.fromkeys(warnings)),
        'warning_occurrences':len(warnings),'converged_steps':[(r['load_step'],r['substep']) for r in parsed['converged_substeps']],
        'observed_progress':monitor.observed,'execution_kind':'LICENSED_PROGRESSIVE_SOLVE' if solve else 'INDEPENDENT_READ_ONLY_POST1'}
    write_json(directory/'execution_receipt.json',receipt);write_json(directory/'nonlinear_telemetry.json',parsed)
    if solve:
        path=directory/'compression.cnd';c=parse_contact(path.read_text(errors='replace')) if path.exists() else {'records':[],'issues':['MISSING_FILE']}
        write_json(directory/'contact_telemetry.json',c);write_json(directory/'contact_summary.json',contact_summary(c['records']))
    return receipt
