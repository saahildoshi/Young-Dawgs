"""Scientific figures from authenticated native fields; true deformation scale."""
from pathlib import Path
import gc
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.contact_setup import platen_plan
from metamaterial_eval.simulation.reporting import write_json
from scripts.v066_restart import REPO,RUN,BASE,load


def save(fig,name):
    fig.savefig(RUN/'figures'/name,dpi=170,bbox_inches='tight');plt.close(fig);gc.collect()


def snapshot(mesh,directory,label):
    u=np.load(directory/'native_displacement.npy',mmap_mode='r')
    s=np.load(directory/'native_corner_stress_strain.npy',mmap_mode='r')
    corners=np.load(directory/'corner_node_ids.npy',mmap_mode='r')-1
    q=load(directory/'qualification.json');e=q['state']['time'] if 'state' in q else q['accepted_measurements'][0]['engineering_compression_strain'];accepted=q['accepted']
    lines=mesh.boundary[:,:2]
    fig,ax=plt.subplots(figsize=(7,7))
    ax.add_collection(LineCollection(mesh.nodes[lines],colors='.75',linewidths=.2,label='Initial'))
    ax.add_collection(LineCollection(u[lines,3:5],colors='#006da5',linewidths=.22,label='Actual deformed'))
    ax.set(xlim=(-.15,10.39),ylim=(-.15,10.39),aspect='equal',xlabel='x (mm)',ylabel='y (mm)',
        title=f'Design9: {100*e:.6g}% compression, true 1× scale\n'+('Mechanically accepted; platen-only exploratory model' if accepted else 'UNQUALIFIED diagnostic state'))
    ax.legend(loc='upper right');save(fig,label+'_deformation.png')
    # Native corner fields plotted only at their actual supported locations.
    corner_tri=np.searchsorted(corners,mesh.triangles[:,:3])
    assert np.array_equal(corners[corner_tri],mesh.triangles[:,:3])
    values=[(u[corners,2],'Mean native corner displacement magnitude (mm)','viridis'),(s[:,0],'Mean native corner SYY (MPa)','coolwarm'),
            (s[:,1],'Mean native corner SEQV (MPa)','magma'),(s[:,2],'Mean native corner elastic EYY','coolwarm')]
    for (v,title,cmap),suffix in zip(values,['U','SYY','SEQV','EYY']):
        fig,ax=plt.subplots(figsize=(7,7));xy=u[corners,3:5]
        im=ax.tripcolor(xy[:,0],xy[:,1],corner_tri,np.mean(v[corner_tri],axis=1),shading='flat',cmap=cmap,rasterized=True)
        ax.set(aspect='equal',xlabel='Deformed x (mm)',ylabel='Deformed y (mm)',title=f'{title}\nCorner-linear display; actual {100*e:.6g}%; true 1× scale')
        fig.colorbar(im,ax=ax,label=title);save(fig,label+'_'+suffix+'.png')
    pore=load(directory/'boundary_screen.json' if (directory/'boundary_screen.json').exists() else RUN/'deformation/baseline_boundary_screen.json')['pore_area_records']
    fig,ax=plt.subplots(figsize=(7,4));ratios=np.array([p['area_ratio'] for p in pore])
    ax.hist(ratios,bins=35,color='#006da5');ax.set(xlabel='Deformed / original pore signed area',ylabel='Pore count',title=f'412 pore loops at actual {100*e:.6g}% compression')
    save(fig,label+'_pore_area.png')
    export=Path(q['export']) if 'export' in q else directory.parent/'full_recovery_001_post'
    native=np.loadtxt(export/next(name for name in q['raw_native_field_hashes'] if name.endswith('_contact.csv')),delimiter=',',skiprows=1,ndmin=2)
    plan=platen_plan(mesh,CompressionConfig());fig,axes=plt.subplots(2,1,figsize=(8,5),sharex=True)
    for pair,group,ax in [(1,'bottom',axes[0]),(2,'top',axes[1])]:
        edges=np.asarray(plan[group]['edges']);values=native[native[:,0]==pair]
        start=len(mesh.triangles)+3 if pair==1 else len(mesh.triangles)+5+len(plan['bottom']['edges'])
        assert np.array_equal(values[:,1],np.arange(start,start+len(edges)))
        ax.scatter(u[edges[:,:2],3].ravel(),values[:,3:5].ravel(),s=2,color='#006da5')
        ax.set(ylabel=f'{group.capitalize()} pressure (MPa)');ax.grid(alpha=.2)
    axes[1].set_xlabel('Actual deformed endpoint x (mm)');fig.suptitle(f'Native platen endpoint pressures at {100*e:.6g}% compression')
    save(fig,label+'_platen_pressure.png')
    peak=int(np.argmax(s[:,1]));center=u[corners[peak],3:5]
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    for ax,v,title,cmap in [(axes[0],s[:,1],'Native SEQV (MPa)','magma'),(axes[1],s[:,2],'Native elastic EYY','coolwarm')]:
        xy=u[corners,3:5];near=np.all(abs(xy-center)<.2,axis=1)
        im=ax.scatter(xy[near,0],xy[near,1],c=v[near],s=4,cmap=cmap,linewidths=0)
        ax.set(xlim=(center[0]-.15,center[0]+.15),ylim=(center[1]-.15,center[1]+.15),aspect='equal',xlabel='Deformed x (mm)',ylabel='Deformed y (mm)',title=title)
        fig.colorbar(im,ax=ax)
    fig.suptitle(f'Actual corner-node hotspot at {100*e:.6g}% compression; no stress mesh-convergence claim')
    save(fig,label+'_hotspot.png')
    write_json(RUN/'mechanical_results'/(label+'_hotspot.json'),{'native_corner_node':int(corners[peak]+1),'deformed_xy_mm':center.tolist(),
        'native_SEQV_MPa':float(s[peak,1]),'native_elastic_EYY':float(s[peak,2]),'scope':'Native corner-node averages, single mesh, provisional material; not a converged peak stress or failure prediction'})


def curves(rows):
    x=np.array([r['engineering_compression_strain'] for r in rows]);y=np.array([r['nominal_compression_stress_MPa'] for r in rows])
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].plot([r['compression_displacement_mm'] for r in rows],[-r['upper_rf_y_N'] for r in rows],'o-',ms=4)
    axes[0].set(xlabel='Actual platen travel (mm)',ylabel='Compressive force (N)')
    axes[1].plot(100*x,y,'o-',ms=4);axes[1].set(xlabel='Actual engineering compression (%)',ylabel='Nominal stress (MPa)')
    fig.suptitle('Accepted native states only — fine mesh, platen contact, provisional material')
    for ax in axes:ax.grid(alpha=.2)
    save(fig,'accepted_mechanical_response.png')


def main():
    summary=load(RUN/'summary/V0_6_6_VALIDATION.json');curves(summary['accepted_measurements'])
    mesh,_,_=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    selected=[];major=[.00005,.001,.01,.05,.1,.2,.3,.4,summary['maximum_qualified_engineering_strain']]
    for record in summary['snapshot_artifacts']:
        if any(abs(record['engineering_strain']-x)<1e-10 for x in major):
            snapshot(mesh,Path(record['directory']),record['label']);selected.append(record)
    write_json(RUN/'figures/manifest.json',{'rendered_states':selected,'deformation_scale':1,'curve':'Accepted actual states only; no uncomputed extension',
        'field_location':'U all nodes; SYY/SEQV/EPEL native corner-node averages; pressures at native platen endpoints',
        'png_files':[p.name for p in (RUN/'figures').glob('*.png')]})


if __name__=='__main__':main()
