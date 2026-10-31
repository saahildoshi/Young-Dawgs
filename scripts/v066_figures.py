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
        title=f'Design9: {100*e:.6g}% compression, true 1× scale\n'+(('Accepted; full exposed-surface self-contact' if q.get('general_contact') else 'Accepted; platen-only reference') if accepted else 'UNQUALIFIED diagnostic state'))
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
        offsets=values[:,1].astype(int)-start
        assert np.all((offsets>=0)&(offsets<len(edges))) and len(np.unique(offsets))==len(offsets)
        ax.scatter(u[edges[offsets,:2],3].ravel(),values[:,3:5].ravel(),s=2,color='#006da5')
        if len(values)<len(edges):ax.text(.99,.9,f'{len(edges)-len(values)} native far-field records omitted',transform=ax.transAxes,ha='right',fontsize=8)
        ax.set(ylabel=f'{group.capitalize()} pressure (MPa)');ax.grid(alpha=.2)
    axes[1].set_xlabel('Actual deformed endpoint x (mm)');fig.suptitle(f'Native platen endpoint pressures at {100*e:.6g}% compression')
    save(fig,label+'_platen_pressure.png')
    if q.get('general_contact'):
        from metamaterial_eval.simulation.general_contact_results import read_table
        gc_file=export/next(name for name in q['raw_native_field_hashes'] if name.endswith('_gc_fields.csv'))
        columns=gc_file.read_text().splitlines()[0].strip().split(',');g=read_table(gc_file,columns)
        fig,ax=plt.subplots(figsize=(7,7));ax.add_collection(LineCollection(u[lines,3:5],colors='.8',linewidths=.2))
        if len(g) and np.any(g[:,4]>0):
            chosen=g[g[:,4]>0];nodes=chosen[:,[10,12,11]].astype(int)-1
            colored=LineCollection(u[nodes,3:5],array=chosen[:,4],cmap='magma',linewidths=1.5);ax.add_collection(colored)
            fig.colorbar(colored,ax=ax,label='Native element-mean contact pressure (MPa)')
        else:ax.text(.5,.02,'No native self-contact engagement',transform=ax.transAxes,ha='center')
        ax.set(xlim=(-.15,10.39),ylim=(-.15,10.39),aspect='equal',xlabel='Deformed x (mm)',ylabel='Deformed y (mm)',title=f'Native general self-contact pressure\nActual {100*e:.6g}% compression; true 1× scale')
        save(fig,label+'_self_contact_pressure.png')
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


def curves(rows,name='accepted_mechanical_response.png',model_label='Platen-only reference'):
    x=np.array([r['engineering_compression_strain'] for r in rows]);y=np.array([r['nominal_compression_stress_MPa'] for r in rows])
    fig,axes=plt.subplots(1,2,figsize=(10,4))
    axes[0].plot([r['compression_displacement_mm'] for r in rows],[-r['upper_rf_y_N'] for r in rows],'o-',ms=4)
    axes[0].set(xlabel='Actual platen travel (mm)',ylabel='Compressive force (N)')
    axes[1].plot(100*x,y,'o-',ms=4);axes[1].set(xlabel='Actual engineering compression (%)',ylabel='Nominal stress (MPa)')
    fig.suptitle(f'Accepted native states only — {model_label}, provisional material')
    for ax in axes:ax.grid(alpha=.2)
    save(fig,name)


def rejected_crossing():
    path=RUN/'deformation/EXACT_CROSSING_DIAGNOSIS_013.json'
    if not path.exists():return
    data=load(path);fig,axes=plt.subplots(1,2,figsize=(9,5))
    colors=['#0072b2','#d55e00'];t=np.linspace(0,1,150)
    shape=np.column_stack([(1-t)*(1-2*t),t*(2*t-1),4*t*(1-t)])
    for i,record in enumerate(data['results']):
        for ax,key in zip(axes,['original_coordinates_mm','deformed_quadratic_coordinates_mm']):
            xy=np.asarray(record[key])
            for p in xy:
                curve=shape@p;ax.plot(curve[:,0],curve[:,1],color=colors[i],lw=2)
        x,y=record['crossing_xy_mm'];axes[1].scatter([x],[y],color='red',marker='x',s=60,zorder=5)
    axes[0].set_title('Original quadratic edges')
    axes[1].set_title('Rejected 1% platen-only native state')
    for ax in axes:
        ax.set(aspect='equal',xlabel='x (mm)',ylabel='y (mm)');ax.grid(alpha=.2)
    fig.suptitle('Confirmed free-boundary crossings — excluded from accepted curves')
    save(fig,'rejected_platen_1percent_exact_crossing.png')



def rejected_general_crossing():
    path=RUN/'deformation/FULL_GC_ONE_PERCENT_EXACT_DIAGNOSIS.json'
    if not path.exists():return
    data=load(path);fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
    t=np.linspace(0,1,200)
    shape=np.column_stack([(1-t)*(1-2*t),t*(2*t-1),4*t*(1-t)])
    for ax,record in zip(axes,data['pairs']):
        for points,color in zip(record['quadratic_points'],['#0072b2','#d55e00']):
            xy=np.asarray(points);curve=shape@xy;ax.plot(curve[:,0],curve[:,1],color=color,lw=2)
            ax.scatter(xy[:2,0],xy[:2,1],color=color,s=25)
        v=record['solutions'][0]['parameters'][0]
        cross=np.array([(1-v)*(1-2*v),v*(2*v-1),4*v*(1-v)])@np.asarray(record['quadratic_points'][0])
        ax.scatter(cross[0],cross[1],color='red',marker='x',s=65,zorder=5)
        ax.set(aspect='equal',xlabel='Native deformed x (mm)',ylabel='Native deformed y (mm)',title=f"Edges {record['edge_a']} / {record['edge_b']}")
        ax.grid(alpha=.2);ax.ticklabel_format(axis='both',style='plain',useOffset=False)
    from matplotlib.ticker import MaxNLocator
    axes[1].set_aspect('auto');axes[1].xaxis.set_major_locator(MaxNLocator(3));axes[1].tick_params(axis='x',labelsize=8)
    axes[1].set_title(axes[1].get_title()+'\nIndependent x/y scales',fontsize=11)
    fig.suptitle('Rejected 1% Gauss-point general contact: exact endpoint-region crossings',fontsize=13)
    save(fig,'rejected_gc_gauss_1percent_exact_crossing.png')


def main():
    summary=load(RUN/'summary/V0_6_6_VALIDATION.json')
    label='Full exposed-surface self-contact' if summary.get('primary_model_variant','').startswith('FINE_FULL') else 'Platen-only reference'
    curves(summary['accepted_measurements'],model_label=label)
    for variant,branch in summary.get('model_branches',{}).items():curves(branch['accepted_measurements'],name=variant+'_response.png',model_label='Full exposed-surface self-contact' if variant.startswith('FINE_FULL') else 'Platen-only reference')
    mesh,_,_=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    selected=[];major=[.00005,.001,.01,.05,.1,.2,.3,.4,summary['maximum_qualified_engineering_strain']]
    major += [b['maximum_qualified_engineering_strain'] for b in summary.get('model_branches',{}).values()]
    for record in summary['snapshot_artifacts']:
        if any(abs(record['engineering_strain']-x)<1e-10 for x in major):
            snapshot(mesh,Path(record['directory']),record['label']);selected.append(record)
    rejected_crossing();rejected_general_crossing()
    write_json(RUN/'figures/manifest.json',{'rendered_states':selected,'deformation_scale':1,'curve':'Accepted actual states only; no uncomputed extension',
        'field_location':'U all nodes; SYY/SEQV/EPEL native corner-node averages; pressures at native platen endpoints; GC pressure is native element mean',
        'png_files':[p.name for p in (RUN/'figures').glob('*.png')]})


if __name__=='__main__':main()
