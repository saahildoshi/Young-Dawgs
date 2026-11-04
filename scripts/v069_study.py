"""Prospective v0.6.9 authentication and original-face onset reconstruction."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import subprocess
import shutil
import numpy as np
from scripts.v068_common import REPO,BASE as OLD,RUN as PREVIOUS,read,write_json as _write_json,file_hash
from scripts.v068_track_b import mesh_and_plan

RUN=REPO/'experiments/pipeline_v0.6.9/run_001'
BASE=OLD.parent/'v069'
DOC=REPO/'docs/pipeline_v0.6.9'
PARENT='track_B_pair5_to_01500_001'

def write_json(path,value):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    _write_json(path,value)


def register():
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).splitlines()
    if any(line!='?? scripts/v069_study.py' for line in dirty):
        raise ValueError('Registration requires clean checkpoint; preserve existing changes')
    for d in [RUN,BASE,DOC]:
        if d.exists() and any(d.iterdir()):raise ValueError('Registration destination is not empty')
        d.mkdir(parents=True,exist_ok=True)
    start=datetime.now(timezone.utc)
    protocol={'schema':'young-dawgs-v069-prospective-contact-study','registered_utc':start.isoformat(),
      'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
      'wall_budget_seconds':21600,'native_stage_seconds':5400,'stall_seconds':1200,
      'concurrent_native_processes':1,'disk_reserve_bytes':80*2**30,'arbitrary_RSS_cap':None,
      'system_health_policy':'Existing progressive_compression defaults; no unrelated process termination',
      'track_A_full_solve_authorized':False,'track_B_continuation_gate':'Complete local parent matching and all-state native contact qualification first',
      'parent_matching':{'U_relative_RMS':.02,'S_and_EPEL_relative_RMS':.10,'reaction_relative':.01,
       'normal_angle_degrees':2,'gap_absolute_mm':1e-6,'all_measured_states_required':True},
      'mechanics':{'reaction_relative':.01,'opposing_force_relative':.01,'native_penetration_mm':5e-5,
       'positive_analytic_TRI6_maps':True,'unexplained_continuous_crossing_allowed':False},
      'geometry_material_mesh':'Exact v068 Track B unchanged; E1000MPa nu0.3 plane stress thickness1mm, exploratory',
      'local_fixture':'Exact original TRI6 centroid ROI [2.35,2.56] x [2.05,2.45] mm; one element adjacency halo; measured cut U histories; artificial cuts excluded from contact',
      'candidate_policy':'Baseline first. Diagnose discrete surface transition before one targeted candidate; no parameter sweep. Candidate config committed before native execution.',
      'future_loading':[.012675,.015,.02,.05,.10,.20,.30,.40],
      'stop':'No qualified local match => no specimen source solve; preserve failures and report'}
    write_json(RUN/'protocol/PROTOCOL.json',protocol)
    (DOC/'V0_6_9_PROTOCOL.md').write_text('# v0.6.9 prospective protocol\n\nSix-hour bounded sequential contact study. Original full specimen remains at 0.9270608836%; no full Track A solve is authorized. Track B remains accepted through 1.2575%, with complete restart at 1.2%.\n\nReconstruct per-element contact transitions and exact quadratic geometry, then qualify an original-element local baseline against every available measured history before testing one diagnosed correction. Freeze 2% displacement RMS, 10% stress/strain RMS, 1% reaction and opposing-force gates, 2 degree normal and 1e-6 mm gap comparison. Native endpoint penetration limit remains 5e-5 mm and does not bound continuous overlap. No unexplained crossing or nonpositive mapping is accepted. Full crop continuation requires complete local and parent matching.\n\nReuse existing system-health supervision, one native process, 80 GiB disk reserve, 5400 s stage and 1200 s no-progress limits. All candidates require a committed config before execution. See experiments/pipeline_v0.6.9/run_001/protocol/PROTOCOL.json.\n',encoding='utf-8')
    print('Registered',RUN,BASE)


def authenticate():
    mesh,_,_,spec=mesh_and_plan()
    paths=[OLD/'track_B_pair_unified_setup_001/contact_model_pair_unified.db',OLD/'track_B_pair5_to_01200_001/compression.rst',OLD/PARENT/'compression.rst']
    records={}
    for p in paths:
        receipt=read(p.parent/'execution_receipt.json')
        digest=file_hash(p)
        assert digest==receipt['process']['artifacts'][p.name]['sha256']
        records[str(p)]={'sha256':digest,'bytes':p.stat().st_size}
    from scripts.v067_fixture import RUN as R67
    a=read(R67/'audit/INITIAL_AUTHENTICATION.json')
    for name,record in a['parent_native_files'].items():
        p=Path(a['parent_source'])/name;assert file_hash(p)==record['sha256']
        records[str(p)]={'sha256':record['sha256'],'bytes':p.stat().st_size}
    write_json(RUN/'audit/AUTHENTICATION.json',{'status':'PASS','native_files':records,'mesh':spec,
      'physical_RAM_bytes':__import__('psutil').virtual_memory().total,'available_RAM_bytes':__import__('psutil').virtual_memory().available,
      'free_disk_bytes':shutil.disk_usage(BASE).free,'native_processes':[p.info for p in __import__('psutil').process_iter(['pid','name']) if (p.info['name'] or '').lower().startswith('ansys')],
      'historical_qualification_sha256':file_hash(PREVIOUS/'track_B_progressive_compression'/ (PARENT+'_qualification.json'))})
    print('Authenticated mesh and',len(records),'native files')


def diagnose():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    mesh,_,_,_=mesh_and_plan()
    post=OLD/(PARENT+'_post1_all_v2')
    topo=np.loadtxt(OLD/'track_B_pair_setup_002/contact_topology.csv',delimiter=',',skiprows=1).astype(int)
    targets=np.loadtxt(OLD/'track_B_pair_setup_002/target_topology.csv',delimiter=',',skiprows=1).astype(int)
    q=read(PREVIOUS/'track_B_progressive_compression'/(PARENT+'_qualification.json'))
    rows=[];fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
    normals={}
    for i in range(1,33):
        fields=np.loadtxt(post/f'stage{i:03d}_pair_contact.csv',delimiter=',',skiprows=1)
        for f in fields:rows.append([i,q['states'][i-1]['requested_time'],*f])
        if i not in [7,8,9]:continue
        u=np.loadtxt(post/f'stage{i:03d}_displacements.csv',delimiter=',',skiprows=1)[:,1:3]
        xy=mesh.nodes+u;ax=axes[[7,8,9].index(i)]
        for group,color in [(topo,'#c75b24'),(targets,'#147d86')]:
            for r in group:
                edge=xy[r[1:4]-1];t=np.linspace(-1,1,101)
                curve=(t*(t-1)/2)[:,None]*edge[0]+(t*(t+1)/2)[:,None]*edge[1]+(1-t*t)[:,None]*edge[2]
                ax.plot(*curve.T,color=color,lw=1)
                if r[0] in [95927,95928,95916]:ax.text(*edge[2],str(r[0]),fontsize=7)
                tangent=edge[1]-edge[0];normal=np.array([tangent[1],-tangent[0]])/np.linalg.norm(tangent)
                normals[f'{i}:{r[0]}']={'midpoint_normal':normal.tolist(),'coordinates_mm':edge.tolist(),
                  'midside_chord_deviation_mm':float(np.linalg.norm(edge[2]-(edge[0]+edge[1])/2))}
        ax.set_xlim(2.553,2.564);ax.set_ylim(2.226,2.234);ax.set_aspect('equal');ax.set_title(f'{100*q["states"][i-1]["requested_time"]:.4f}%');ax.set_xlabel('x mm');ax.set_ylabel('y mm')
    d=RUN/'diagnostics';d.mkdir(exist_ok=True)
    np.savetxt(d/'ELEMENT_CONTACT_HISTORY.csv',rows,delimiter=',',header='substep,strain,element,status,pressure_i_MPa,pressure_j_MPa,pen_i_mm,pen_j_mm,fy_N,target_i,target_j',comments='')
    fig.savefig(d/'ONSET_GEOMETRY.png',dpi=220);plt.close(fig)
    write_json(d/'DEFORMED_NORMALS.json',normals)
    write_json(d/'SOURCE_BINDINGS.json',{'source_RST_sha256':file_hash(OLD/PARENT/'compression.rst'),
      'post_receipt_sha256':file_hash(post/'execution_receipt.json'),'contact_topology_sha256':file_hash(OLD/'track_B_pair_setup_002/contact_topology.csv'),
      'limitation':'Saved converged states only; historical failed trial per-element fields unavailable. Geometric normals from deformed exact TRI6 boundary, not native solver normals.'})
    print('Reconstructed',len(rows),'individual element observations')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','authenticate','diagnose']);a=p.parse_args()
    globals()[a.action]()
