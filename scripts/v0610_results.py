"""Actual accepted crop fields, separate branch curves and finite campaign ledger."""
import csv
import subprocess
from datetime import datetime,timezone
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from scripts.v0610_common import BASE,RUN,REPO,read,write_json,file_hash
from scripts.v0610_final_fields import SOURCE,PROOF
from scripts.v068_track_b import mesh_and_plan

BRANCHES=[('', 'track_B_pair5_arc_trial_001'),('',SOURCE),('reverse','track_B_pair5_arc_trial_001')]


def dataset():
    rows=[];summaries=[]
    material_hash=file_hash(RUN/'material_selection/MATERIAL.json')
    for branch,source in BRANCHES:
        root=RUN/branch/'track_B_progressive_compression';p=root/(source+'_mechanical_qualification.json')
        if not p.exists():p=root/(source+'_qualification.json')
        q=read(p);d=BASE/branch/source;r=read(d/'execution_receipt.json');t=read(d/'nonlinear_telemetry.json');prefix=True;valid=[]
        for i,s in enumerate(q['states'],1):
            prefix=prefix and s['accepted'];m=s.get('measurement',{});pair=s['localized_pair_contact']
            rows.append({'branch':(branch+'/' if branch else '')+source,'material':'CROP_LINEAR_ELASTIC_E1000_V068','contact_identity':'extended_unified5_'+('reverse' if branch else 'forward'),
                'load_step':s['load_step'],'substep':s['substep'],'accepted_continuous_path':prefix,'native_time_requested_rounded':s['requested_time'],
                'engineering_compression':m.get('engineering_compression_strain'),'platen_travel_mm':m.get('compression_displacement_mm'),
                'upper_reaction_y_N':m.get('upper_rf_y_N'),'lower_reaction_y_N':m.get('lower_rf_y_N'),
                'nominal_compression_stress_MPa':m.get('nominal_compression_stress_MPa'),'reaction_imbalance_relative':m.get('reaction_balance_relative'),
                'pair_closed_faces':pair['closed_source_faces'],'pair_max_endpoint_pressure_MPa':pair['max_pressure_MPa'],'pair_max_endpoint_penetration_mm':pair['max_endpoint_penetration_mm'],
                'invalid_TRI6':s['fields']['invalid_quadratic_maps'],'general_contact_closed_skins':s['internal_contact']['closed_skins'],
                'qualification_sha256':file_hash(p),'source_receipt_sha256':file_hash(d/'execution_receipt.json'),'input_sha256':file_hash(d/'input.inp'),
                'mesh_semantic_sha256':read(RUN/'track_B_mesh/MESH_001.json')['semantic_sha256'],
                'failures':'; '.join(s['failures'])})
            if prefix:valid.append(m)
        first=next((s for s in q['states'] if not s['accepted']),None)
        summaries.append({'branch':rows[-1]['branch'],'material':'CROP_LINEAR_ELASTIC_E1000_V068','native_saved_states':len(q['states']),
            'accepted_prefix_states':len(valid),'maximum_accepted_strain':valid[-1]['engineering_compression_strain'] if valid else None,
            'maximum_native_strain':q['max_native_converged_strain'],'first_rejected_requested_strain':first['requested_time'] if first else None,
            'first_rejection_reasons':first['failures'] if first else [],'returncode':r['process']['returncode'],'native_status':r['status'],
            'cutback_events':len(t['cutback_events']),'native_wall_seconds':r['process']['runtime_seconds'],'source_RST_sha256':file_hash(d/'compression.rst'),
            'qualification_sha256':file_hash(p)})
    dest=RUN/'mechanical_response';dest.mkdir(exist_ok=True)
    with (dest/'ALL_NATIVE_CHECKPOINTS.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write_json(dest/'BRANCH_SUMMARY.json',summaries)
    accepted=[r for r in rows if r['branch']==SOURCE and r['accepted_continuous_path']]
    x=np.array([r['engineering_compression'] for r in accepted]);y=np.array([r['nominal_compression_stress_MPa'] for r in accepted]);small=x<=.005
    metrics={'material_identity':'CROP_LINEAR_ELASTIC_E1000_V068','final_strain':float(x[-1]),'accepted_states':len(accepted),
        'initial_nominal_loading_slope_MPa':float(np.polyfit(x[small],y[small],1)[0]),'slope_strain_window':[float(x[small].min()),float(x[small].max())],
        'accepted_prefix_loading_work_density_MJ_m3':float(np.trapezoid(y,x)),'work_lower_limit':float(x[0]),'work_upper_limit':float(x[-1]),
        'peak_accepted_force_N':max(abs(r['upper_reaction_y_N']) for r in accepted),'peak_accepted_nominal_stress_MPa':float(y.max()),
        'scope':'One monotonic E1000 loading branch; fitted small-window slope is not material Young modulus. Integral excludes unmeasured zero-to-first step. No hysteresis, densification, plateau, collapse, effective Poisson ratio or pore closure quantified.',
        'polymer_crop_status':'NOT_EXECUTED_CONTACT_GATE_FAILED','polymer_configuration_sha256':material_hash}
    write_json(dest/'METRICS.json',metrics)
    return rows,summaries


def resources():
    records=[]
    for p in sorted(BASE.rglob('execution_receipt.json')):
        r=read(p);proc=r['process'];deck=(p.parent/'input.inp').read_text(errors='replace');source='\nSOLVE\n' in deck
        records.append({'directory':str(p.parent),'kind':('COUPON_SOURCE' if 'coupon' in p.parent.name else 'CROP_SOURCE') if source else ('READ_ONLY_POST1' if '/POST1' in deck else 'NATIVE_SETUP'),
            'status':r['status'],'returncode':proc['returncode'],'wall_seconds':proc['runtime_seconds'],'peak_tree_RSS_bytes':proc.get('peak_tree_rss_bytes') or 0,
            'receipt_sha256':file_hash(p),'input_sha256':r['input_sha256'],'unique_launcher_job':r['unique_launcher_job'],
            'restart':bool('ANTYPE,STATIC,REST' in deck),'available_RAM_sample_min_bytes':min((s['available_RAM_bytes'] for s in proc['resource_samples']),default=None)})
    sources=[r for r in records if r['kind'].endswith('SOURCE')]
    perf={'generated_utc':datetime.now(timezone.utc).isoformat(),'processes':records,'native_processes':len(records),'source_solves':len(sources),
        'crop_source_solves':sum(r['kind']=='CROP_SOURCE' for r in records),'coupon_source_solves':sum(r['kind']=='COUPON_SOURCE' for r in records),
        'original_full_source_solves':0,'polymer_crop_source_solves':0,'genuine_restarts':sum(r['restart'] for r in records),
        'source_wall_seconds':sum(r['wall_seconds'] for r in sources),'all_native_wall_seconds':sum(r['wall_seconds'] for r in records),
        'peak_tree_RSS_bytes':max(r['peak_tree_RSS_bytes'] for r in records),'raw_disk_bytes':sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file()),
        'paging':'No sustained severe paging stop recorded. System hard-fault proxies are not pagefile-only or per-process page fault counts.',
        'stops':'First coarse trial interrupted by historical recoverable-error monitor. Strict trial completed; reverse trial exited nonconverged at minimum increment. Mechanical crossing rejection is independent of convergence.'}
    write_json(RUN/'performance/PERFORMANCE.json',perf)
    return perf


def boundary_segments(xy,faces):
    v=xy[faces];t=np.linspace(0,1,9)
    points=(1-t)[None,:,None]*(1-2*t)[None,:,None]*v[:,0,None,:]+t[None,:,None]*(2*t-1)[None,:,None]*v[:,1,None,:]+4*t[None,:,None]*(1-t)[None,:,None]*v[:,2,None,:]
    return points


def figures():
    rows,_=dataset();resources();mesh,_,_,_=mesh_and_plan();d=RUN/'figures';d.mkdir(exist_ok=True)
    q=read(PROOF);accepted=[(i,s) for i,s in enumerate(q['states'],1) if s['accepted']];index,state=accepted[-1]
    u=np.loadtxt(BASE/'final_readback_001/final_u.csv',delimiter=',');s=np.loadtxt(BASE/'final_readback_001/final_fields.csv',delimiter=',');xy=mesh.nodes+u[:,1:3]
    fig,axes=plt.subplots(1,4,figsize=(15,4.4),layout='constrained')
    states=[None]+[min(accepted,key=lambda a:abs(a[1]['requested_time']-t)) for t in [.005,.01,.012575]]
    for ax,item in zip(axes,states):
        points=mesh.nodes if item is None else mesh.nodes+np.loadtxt(BASE/(SOURCE+'_post1_all_v2')/f'stage{item[0]:03d}_displacements.csv',delimiter=',',skiprows=1)[:,1:3]
        ax.add_collection(LineCollection(boundary_segments(points,mesh.boundary),linewidths=.25,colors='#156f80',rasterized=True));ax.set_xlim(-.05,2.64);ax.set_ylim(-.1,2.65);ax.set_aspect('equal');ax.set_xlabel('x mm');ax.set_ylabel('y mm');ax.set_title('Initial' if item is None else f'Accepted {100*item[1]["measurement"]["engineering_compression_strain"]:.4f}%')
    fig.suptitle('E1000 crop: native deformation scale 1:1; quadratic boundaries sampled only for display');fig.savefig(d/'ACTUAL_ACCEPTED_DEFORMATION.png',dpi=180);plt.close(fig)
    ids=s[:,0].astype(int)-1;lookup=np.full(len(xy),-1);lookup[ids]=np.arange(len(ids));tri=lookup[mesh.triangles[:,:3]]
    for filename,cols,labels in [('NATIVE_STRESS.png',[1,2,3,4],['SXX MPa','SYY MPa','SXY MPa','SEQV MPa']),('NATIVE_ELASTIC_STRAIN.png',[5,6,7],['Native EPEL XX','Native EPEL YY','Native EPEL XY'])]:
        fig,axes=plt.subplots(1,len(cols),figsize=(4*len(cols),4.8),layout='constrained')
        for ax,j,label in zip(axes,cols,labels):
            lo,hi=np.percentile(s[:,j],[1,99]);im=ax.tripcolor(xy[ids,0],xy[ids,1],tri,s[:,j],vmin=lo,vmax=hi,cmap='coolwarm',shading='gouraud',rasterized=True)
            fig.colorbar(im,ax=ax,shrink=.7);ax.set_aspect('equal');ax.set_title(label);ax.set_xlabel('x mm');ax.set_ylabel('y mm')
        fig.suptitle('E1000 crop, accepted 1.2575%: native corner averages; display interpolation; color limits 1–99 percentiles');fig.savefig(d/filename,dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(12,4.7),layout='constrained')
    for ax,values,label in zip(axes,[u[:,1],u[:,2],np.linalg.norm(u[:,1:3],axis=1)],['UX mm','UY mm','Displacement magnitude mm']):
        im=ax.tripcolor(xy[:,0],xy[:,1],mesh.triangles[:,:3],values,shading='gouraud',cmap='viridis',rasterized=True);fig.colorbar(im,ax=ax,shrink=.7);ax.set_aspect('equal');ax.set_title(label);ax.set_xlabel('x mm');ax.set_ylabel('y mm')
    fig.suptitle('E1000 native nodal displacement, accepted 1.2575%; no magnification');fig.savefig(d/'NATIVE_DISPLACEMENT.png',dpi=180);plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    for branch,source in BRANCHES:
        key=(branch+'/' if branch else '')+source;rr=[r for r in rows if r['branch']==key and r['accepted_continuous_path']]
        if not rr:continue
        label='Reversed extended arcs (E1000)' if branch else 'Forward extended arcs, strict (E1000)'
        axes[0].plot([r['engineering_compression']*100 for r in rr],[r['nominal_compression_stress_MPa'] for r in rr],'.-',ms=3,label=label)
        axes[1].plot([r['platen_travel_mm'] for r in rr],[abs(r['upper_reaction_y_N']) for r in rr],'.-',ms=3,label=label)
    axes[0].set_xlabel('Engineering compression %');axes[0].set_ylabel('Nominal compressive stress MPa');axes[1].set_xlabel('Top-platen travel magnitude mm');axes[1].set_ylabel('Upper reaction magnitude N')
    for ax in axes:ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.suptitle('Accepted continuous prefixes only; separate contact branches; no polymer crop curve');fig.savefig(d/'ACCEPTED_RESPONSE.png',dpi=180);plt.close(fig)
    fields=np.loadtxt(BASE/'final_readback_001/final_pair.csv',delimiter=',',skiprows=1)
    fig,axes=plt.subplots(1,3,figsize=(12,4),layout='constrained')
    for ax,value,label in [(axes[0],fields[:,1],'Native status'),(axes[1],np.where(fields[:,1]>0,fields[:,2:4].max(axis=1),np.nan),'Max stored endpoint pressure MPa'),(axes[2],np.where(fields[:,1]>0,fields[:,4:6].max(axis=1),np.nan),'Max stored endpoint penetration mm')]:
        ax.plot(fields[:,0],value,'o',ms=4);ax.set_title(label,fontsize=9);ax.set_xlabel('Native source contact element');ax.tick_params(axis='x',rotation=45)
    fig.suptitle('E1000 accepted 1.2575% contact; endpoint records are not a continuous penetration bound');fig.savefig(d/'NATIVE_CONTACT.png',dpi=180);plt.close(fig)
    protocol=read(RUN/'protocol/TRACK_B_LOCAL_PAIR_002.json');src=protocol['source_contact_faces_zero_based'];tgt=protocol['target_contact_faces_zero_based']
    chosen=[(index,state),next((i,s) for i,s in enumerate(q['states'],1) if not s['accepted'])]
    fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
    for ax,(i,row) in zip(axes,chosen):
        points=mesh.nodes+np.loadtxt(BASE/(SOURCE+'_post1_all_v2')/f'stage{i:03d}_displacements.csv',delimiter=',',skiprows=1)[:,1:3]
        for faces,color,label in [(mesh.boundary,'#bac4c8',None),(mesh.boundary[src],'#b44d26','Source arc'),(mesh.boundary[tgt],'#177c80','Target arc')]:ax.add_collection(LineCollection(boundary_segments(points,faces),colors=color,linewidths=.4 if label is None else 1.8,label=label))
        ax.set_xlim(2.515,2.585);ax.set_ylim(2.195,2.30);ax.set_aspect('equal');ax.set_xlabel('x mm');ax.set_ylabel('y mm');ax.set_title(f'{"Accepted" if row["accepted"] else "REJECTED diagnostic"} {100*row["measurement"]["engineering_compression_strain"]:.5f}%')
    axes[0].legend(fontsize=8);fig.suptitle('Forward E1000 actual contact neighborhood; 1:1 geometry scale');fig.savefig(d/'CONTACT_TRANSITION.png',dpi=200);plt.close(fig)
    fig,axes=plt.subplots(1,3,figsize=(13,4.2),layout='constrained')
    for branch,source in BRANCHES:
        p=BASE/branch/source;r=read(p/'execution_receipt.json')['process'];telemetry=read(p/'nonlinear_telemetry.json');samples=r['resource_samples'];label=('Reverse' if branch else ('Strict' if source==SOURCE else 'Coarse'))
        axes[0].plot([a['elapsed_seconds'] for a in samples],[a['tree_rss_bytes']/2**30 for a in samples],label=label)
        axes[1].plot([a['elapsed_seconds'] for a in samples],[a['available_RAM_bytes']/2**30 for a in samples],label=label)
        axes[2].semilogy([a['evaluation'] for a in telemetry['force_evaluations']],[max(a['ratio'],1e-16) for a in telemetry['force_evaluations']],'.',ms=1.5,label=label)
    axes[0].set_ylabel('Process-tree RSS GiB');axes[1].set_ylabel('System available RAM GiB');axes[2].set_ylabel('Native force / criterion ratio');axes[2].axhline(1,color='black',ls='--')
    for ax in axes:ax.legend(fontsize=8)
    for ax in axes[:2]:ax.set_xlabel('Actual process elapsed seconds')
    axes[2].set_xlabel('Native force evaluation index');fig.suptitle('Actual crop solves: convergence and sampled machine resources');fig.savefig(d/'CONVERGENCE_RESOURCES.png',dpi=180);plt.close(fig)
    write_json(d/'FIGURE_INVENTORY.json',{'material_identity':'CROP_LINEAR_ELASTIC_E1000_V068','state':[state['load_step'],state['substep']],'strain':state['measurement']['engineering_compression_strain'],
        'qualification_sha256':file_hash(PROOF),'native_fields_repeat_proof_sha256':file_hash(RUN/'fields/REPEAT_READBACK.json'),
        'visual_interpolation_only':True,'displacement_scale':1,'native_stress_location':'Corner-node averages, no midside stress filled',
        'figures':{p.name:{'sha256':file_hash(p),'bytes':p.stat().st_size} for p in sorted(d.glob('*.png'))}})
    write_json(RUN/'protocol/CAMPAIGN_STOP.json',{'recorded_utc':datetime.now(timezone.utc).isoformat(),'reason':'Two registered physical contact candidates exhausted; neither continuous accepted prefix reaches1.2675%. Polymer crop entry gate fails.',
        'status':'HOLD_CONTACT_ONSET__POLYMER_CROP_NOT_EXECUTED__THIRTY_PERCENT_NOT_ACHIEVED','mechanical_gates_unchanged':True,'native_results_scaled_to_high_strain':False,
        'maximum_accepted_strain':state['measurement']['engineering_compression_strain'],'maximum_native_diagnostic_strain':.015,
        'branch_summary_sha256':file_hash(RUN/'mechanical_response/BRANCH_SUMMARY.json'),'next_hypothesis':'Separately register supported corner-aware detection/segmentation or general-contact treatment with complete nonredundant coverage and actual crop proof. No further launch in this exhausted campaign.'})
    print('Rendered actual crop results and recorded contact-gated campaign stop',flush=True)


if __name__=='__main__':figures()
