"""Isolated v0.6.10 crop-only native experiments and unique launcher jobs."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import re
import shutil
import psutil
from scripts.v068_common import REPO,BASE as OLD,RUN as V068,read,file_hash
from scripts.v069_study import write_json
from scripts.v066_restart import compact
from metamaterial_eval.simulation.windows_ansys import bounded_run
from metamaterial_eval.simulation.system_health import HealthPolicy
from metamaterial_eval.simulation.solver_execution import discover_solver,solver_release
from metamaterial_eval.simulation.progressive_compression import ProgressMonitor
from metamaterial_eval.simulation.nonlinear_diagnostics import parse_solver_log

BASE=OLD.parent/'v0610'
RUN=REPO/'experiments/pipeline_v0.6.10/run_001'
DOC=REPO/'docs/pipeline_v0.6.10'
REQUEST=Path(r'C:\Users\sd22446\.codex\attachments\994899da-1c36-4eb7-8513-c776b11f51bd\Pasted text.txt')


def copy_evidence(d,category='native_results'):
    target=RUN/category/d.name
    if target.exists():target=target/('receipt_'+file_hash(d/'execution_receipt.json')[:8])
    compact(d,target)
    for name in ['gc_topology.csv','target_topology.csv','contact_topology.csv','contact_types.txt','material_inventory.txt']:
        p=d/name
        if p.exists() and p.stat().st_size<2**20:
            if p.suffix=='.txt':
                text=re.sub(r'(?m)^\s*\d{6,}\s+(VERSION=)',r'[customer identifier omitted] \1',p.read_text(errors='replace'))
                (target/name).write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n',encoding='utf-8',newline='\n')
                write_json(target/(name+'.source.json'),{'raw_native_sha256':file_hash(p),'formatting':'Trailing spaces removed; customer identifier omitted. Native option and material records unchanged.'})
            else:shutil.copyfile(p,target/name)
    return target


def execute(name,solve=True,timeout=5400,cores=2):
    d=BASE/name
    protocol=read(RUN/'protocol/PROTOCOL.json')
    remaining=protocol['campaign_wall_seconds']-(datetime.now(timezone.utc)-datetime.fromisoformat(protocol['registered_utc'])).total_seconds()
    if remaining<=0:
        raise RuntimeError('Registered campaign clock exhausted; native launch refused')
    timeout=min(timeout,remaining)
    if any((p.info['name'] or '').lower() in ['ansys.exe','ansys241.exe'] for p in psutil.process_iter(['name'])):raise RuntimeError('Native process already active')
    write_json(d/'preflight.json',{'available_RAM_bytes':psutil.virtual_memory().available,'disk_free_bytes':shutil.disk_usage(BASE).free,'estimated_RSS_bytes':6*2**30,'estimated_disk_bytes':8*2**30,'timeout_s':timeout,'rss_cap':None})
    monitor=ProgressMonitor(no_progress_seconds=1200,stop_on_trial_error=False)
    job='v610_'+hashlib.sha256(str(d.resolve()).encode()).hexdigest()[:12]
    p=bounded_run([str(discover_solver()),'-b','-smp','-np',str(cores),'-m','4096','-j',job,'-i','input.inp','-o','solver.out'],d,prepared=True,timeout=timeout,rss_limit=None,min_disk_free=80*2**30,min_available_ram=0,resource_sample_seconds=5,health_policy=HealthPolicy(),stop_check=monitor if solve else None)
    out=(d/'solver.out').read_text(errors='replace');telemetry=parse_solver_log(out)
    receipt={'status':p['status'],'process':p,'solver_version':solver_release(out),'input_sha256':file_hash(d/'input.inp'),'unique_launcher_job':job,'converged_steps':[(s['load_step'],s['substep']) for s in telemetry['converged_substeps']],'observed_progress':monitor.observed,'execution_kind':'LICENSED_SOURCE_SOLVE' if solve else 'INDEPENDENT_POST1'}
    write_json(d/'execution_receipt.json',receipt);write_json(d/'nonlinear_telemetry.json',telemetry)
    from metamaterial_eval.simulation.nonlinear_diagnostics import parse_contact
    if (d/'compression.cnd').exists():write_json(d/'contact_telemetry.json',parse_contact((d/'compression.cnd').read_text(errors='replace')))
    copy_evidence(d);print(name,p['status'],p['returncode'],flush=True)
    return receipt


def register():
    import subprocess
    from scripts.v068_track_b import mesh_and_plan
    mesh,_,_,spec=mesh_and_plan()
    RUN.mkdir(parents=True,exist_ok=False);BASE.mkdir(parents=True,exist_ok=False);DOC.mkdir(parents=True,exist_ok=False)
    protocol={'registered_utc':datetime.now(timezone.utc).isoformat(),'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'request_sha256':file_hash(REQUEST),'crop_only':True,'local_parent_matching_required':False,'campaign_wall_seconds':43200,'source_stage_seconds':5400,'stall_seconds':1200,'disk_reserve_bytes':80*2**30,'arbitrary_RSS_cap':None,'native_concurrency':1,'material_coupon_before_polymer_crop':True,'contact_recovery_before_polymer_crop':True,'candidate_cap':2,'candidate1':'Extend both contiguous selected arcs by six original faces on each end; unchanged unified detection and FKN10. Fresh E1000 branch.','candidate2':'Only if coverage fails and evidence supports it: symmetric two-pass adjoining-arc detection, registered separately.','limits':{'reaction_relative':.01,'contact_force_relative':.01,'native_penetration_mm':5e-5,'positive_TRI6':True,'unexplained_crossing_allowed':False},'schedule':[.005,.01,.0115,.012,.012575,.012675,.015,.02,.05,.10,.15,.20,.25,.30,.35,.40],'no_mesh_geometry_material_silent_changes':True,'polymer_identity':'ILLUSTRATIVE_UNCALIBRATED_POLYMER_MODEL__COMPRESSIBLE_NEO_HOOKEAN_E10_NU045'}
    write_json(RUN/'protocol/PROTOCOL.json',protocol)
    files={}
    for p in [OLD/'track_B_setup_001/contact_model.db',OLD/'track_B_pair5_to_01200_001/compression.rst',OLD/'track_B_pair5_to_01200_001/compression.rdb',OLD/'track_B_pair5_to_01500_001/compression.rst']:
        r=read(p.parent/'execution_receipt.json');digest=file_hash(p);assert digest==r['process']['artifacts'][p.name]['sha256'];files[str(p)]={'sha256':digest,'bytes':p.stat().st_size}
    write_json(RUN/'audit/BASELINE.json',{'status':'PASS_CROP_AUTHENTICATION','mesh':spec,'native_files':files,'pores':19,'nodes':len(mesh.nodes),'TRI6':len(mesh.triangles),'physical_RAM_bytes':psutil.virtual_memory().total,'available_RAM_bytes':psutil.virtual_memory().available,'disk_free_bytes':shutil.disk_usage(BASE).free,'historical_accepted_strain':.012575,'historical_native_unqualified_strain':.015,'new_material_fresh_branch_required':True})
    (DOC/'V0_6_10_PROTOCOL.md').write_text('# v0.6.10 crop-only protocol\n\nThe existing 256-pixel crop is the sole structural specimen. No original full-model work or local parent-matching prerequisite applies. A12-hour finite campaign uses one native job,5400s stage and1200s stall limits,80GiB disk reserve and system-health supervision without a fixed RSS cap. Exact mechanical gates remain1% force/reaction balance,5e-5mm native penetration,positive TRI6 mappings and no unexplained quadratic crossing.\n\nFirst validate one illustrative compressible Neo-Hookean elastomer coupon through40%; then test extended contiguous contact coverage on a fresh historical E1000 crop branch. Only promote contact to a fresh polymer branch after crop qualification. At most two evidence-driven contact candidates; no parameter sweep. Targets progress adaptively from0.5% through2%,5%,10%,20%,30%,40%. Preserve every failed attempt, all input/output hashes and separate material curves.\n',encoding='utf-8')
    print('Registered crop-only protocol',flush=True)


if __name__=='__main__':register()
