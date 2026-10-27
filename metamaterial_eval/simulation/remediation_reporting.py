"""Regenerate v0.6.1 actual mesh comparisons and derived quality summaries."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from .config import CompressionConfig
from .element_quality import corner_metrics,quadratic_mapping,quality_summary
from .geometry_adapter import authenticate_fixture
from .mesh_diagnosis import load_mesh
from .reporting import write_json
from .mesh_remediation import HISTORICAL


def generate(study,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import PolyCollection,LineCollection
    study,output=Path(study),Path(output)
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);started=time.perf_counter()
    geometry,_,provenance=authenticate_fixture(Path('.'),CompressionConfig())
    old=load_mesh(HISTORICAL);new=load_mesh(study/'fine_new/generated/mesh.npz')
    diagnosis=json.loads(Path('experiments/pipeline_v0.6.1/mesh_diagnosis/run_001/diagnosis.json').read_text())
    worst=min(diagnosis['failed_elements'],key=lambda r:r['minimum_angle_deg'])
    boundary=next(r for r in diagnosis['failed_elements'] if r['boundary_edge_count']==2)
    summaries=[];distributions={}
    for folder in ['fine_new','coarse_new']:
        m=new if folder=='fine_new' else load_mesh(study/folder/'generated/mesh.npz')
        c=corner_metrics(m.nodes[m.triangles[:,:3]]);q=quadratic_mapping(m.nodes[m.triangles])
        summary=quality_summary(c,q);summary['level']=folder;summary['nodes']=len(m.nodes)
        write_json(output/(folder+'_element_summary.json'),summary);summaries.append(summary)
        distributions[folder]={'angle':c['minimum_angle_deg'].copy(),'quality':c['quality'].copy(),'jacobian':q['determinant_min'].copy()}
    source_lines=[np.asarray(r.coords) for r in [geometry.exterior,*geometry.interiors]]
    def finish(fig,name):fig.tight_layout();fig.savefig(output/name,dpi=160);plt.close(fig)
    for label,record in [('worst',worst),('boundary',boundary)]:
        center=np.asarray(record['coordinates_mm'])[:3].mean(axis=0);radius=.05
        fig,axes=plt.subplots(1,2,figsize=(11,5))
        for ax,m,title in [(axes[0],old,'Original fine: rejected'),(axes[1],new,'New fine: geometric gates pass')]:
            xy=m.nodes[m.triangles[:,:3]];ids=np.flatnonzero(np.any(np.linalg.norm(xy-center,axis=2)<radius,axis=1))
            ax.add_collection(PolyCollection(xy[ids],facecolors='none',edgecolors='#42667f',linewidths=.5))
            ax.add_collection(LineCollection(source_lines,colors='#171717',linewidths=1))
            mids=m.nodes[m.triangles[ids,3:]].reshape(-1,2);ax.scatter(mids[:,0],mids[:,1],s=3,c='#c26b4a')
            ax.set(xlim=(center[0]-radius,center[0]+radius),ylim=(max(0,center[1]-radius),center[1]+radius),aspect='equal',title=title,xlabel='x [mm]',ylabel='y [mm]')
        fig.suptitle('Actual saved meshes; same immutable vector boundary; midsides shown')
        finish(fig,f'original_vs_revised_{label}.png')
    old_angles=corner_metrics(old.nodes[old.triangles[:,:3]])['minimum_angle_deg']
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for name,angles in [('Original fine',old_angles),('New fine',distributions['fine_new']['angle']),('New coarse',distributions['coarse_new']['angle'])]:
        axes[0].hist(angles,bins=np.linspace(0,60,61),histtype='step',label=name)
        axes[1].hist(angles,bins=np.linspace(0,20,81),histtype='step',label=name)
    for ax in axes:ax.axvline(10,color='#bf432c',ls='--');ax.set(xlabel='Minimum angle [deg]',ylabel='Triangle count');ax.legend()
    axes[1].set_yscale('symlog',linthresh=1);fig.suptitle('Actual angle distributions; frozen gate10°');finish(fig,'minimum_angle_comparison.png')
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].hist(distributions['fine_new']['quality'],bins=60);axes[0].set(xlabel='New fine corner quality',ylabel='Count')
    axes[1].hist(distributions['fine_new']['jacobian'],bins=60);axes[1].set(xlabel='New fine whole-reference minimum detJ [mm²]',ylabel='Count')
    fig.suptitle('Independent corner shape and quadratic mapping; no solver results');finish(fig,'quadratic_quality_distribution.png')
    fig,ax=plt.subplots(figsize=(7,7));edges=new.boundary[new.boundary_groups=='pore',:2]
    ax.add_collection(LineCollection(new.nodes[edges],colors='#277f67',linewidths=.6))
    ax.add_collection(LineCollection([np.asarray(r.coords) for r in geometry.interiors],colors='#222222',linewidths=.25))
    ax.set(xlim=(0,10.24),ylim=(0,10.24),aspect='equal',title='All412 source pore boundaries overlaid on new fine mesh',xlabel='x [mm]',ylabel='y [mm]');finish(fig,'pore_boundary_preservation.png')
    probe=min(provenance['source_only_solid_probes'],key=lambda p:p['source_pixel_run'])
    center=np.array([probe['xy'][0]*.01,10.24-probe['xy'][1]*.01]);radius=.04
    fig,ax=plt.subplots(figsize=(6,5));xy=new.nodes[new.triangles[:,:3]]
    ids=np.flatnonzero(np.any(np.linalg.norm(xy-center,axis=2)<radius,axis=1))
    ax.add_collection(PolyCollection(xy[ids],facecolors='none',edgecolors='#52788e',linewidths=.5));ax.add_collection(LineCollection(source_lines,colors='#222222',linewidths=1))
    a=center.copy();b=center.copy();delta=probe['source_pixel_run']*.01/2;a[probe['axis']]-=delta;b[probe['axis']]+=delta
    ax.plot([a[0],b[0]],[a[1],b[1]],color='#d35534',lw=3)
    ax.set(xlim=(center[0]-radius,center[0]+radius),ylim=(center[1]-radius,center[1]+radius),aspect='equal',title='Actual new fine mesh / registered shortest axial chord',xlabel='x [mm]',ylabel='y [mm]');finish(fig,'narrow_feature_resolution.png')
    fig,ax=plt.subplots(figsize=(8,4));labels=['Old coarse','Old medium','Old fine','New coarse','New fine']
    historical=Path('experiments/pipeline_v0.6/mesh_validation/run_003')
    values=[json.loads((historical/f'level_{i:02d}/mesh_quality.json').read_text())['min_angle_deg'] for i in range(3)]
    values.extend([summaries[1]['min_angle_deg'],summaries[0]['min_angle_deg']])
    ax.bar(labels,values,color=['#a2acb6','#a2acb6','#b74d36','#b74d36','#3c8e6a']);ax.axhline(10,c='#c5442c',ls='--')
    ax.set(ylabel='Minimum corner angle [deg]',title='Geometric mesh levels; no mechanical convergence claim')
    finish(fig,'mesh_level_comparison.png')
    write_json(output/'reporting_performance.json',{'seconds':time.perf_counter()-started,'scope':'derived element summaries and actual mesh figures','source_mesh_files_preserved':True})


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--study',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();generate(args.study,args.output)
