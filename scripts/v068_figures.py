"""Publication-style exploratory plots from independently accepted native states."""
import argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from scripts.v068_common import BASE,RUN,read,write_json,file_hash
from scripts.v068_track_b import mesh_and_plan


def lines(xy,faces):
    vertices=xy[faces]
    return np.concatenate([vertices[:,[0,2]],vertices[:,[2,1]]],axis=0)


def make(source_name):
    q=read(RUN/'track_B_progressive_compression'/(source_name+'_qualification.json'))
    if not q['accepted'] or len(q['states'])!=1:raise ValueError('Only independently accepted state can be drawn as a result')
    state=q['states'][0]
    mesh,_,_,_=mesh_and_plan()
    post=BASE/(source_name+'_post1_last_v2')
    u=np.loadtxt(post/'stage001_displacements.csv',delimiter=',',skiprows=1)
    s=np.loadtxt(post/'stage001_stress.csv',delimiter=',',skiprows=1)
    if len(u)!=len(mesh.nodes) or not np.array_equal(u[:,0],np.arange(1,len(u)+1)):
        raise ValueError('Incomplete native displacement plot source')
    xy=mesh.nodes+u[:,1:3]
    figdir=RUN/'figures';figdir.mkdir(parents=True,exist_ok=True)
    # Full actual crop geometry at native 1:1 deformed scale.
    fig,ax=plt.subplots(1,2,figsize=(11,5.4),layout='constrained')
    for axis,points,title,color in [(ax[0],mesh.nodes,'Initial selected specimen','#34495e'),
                                    (ax[1],xy,f'Native accepted {100*state["requested_time"]:.3f}%','#156f80')]:
        axis.add_collection(LineCollection(lines(points,mesh.boundary),colors=color,linewidths=.23,rasterized=True))
        axis.set_xlim(-.05,2.64);axis.set_ylim(-.12,2.66);axis.set_aspect('equal')
        axis.set_title(title);axis.set_xlabel('x (mm)');axis.set_ylabel('y (mm)')
    fig.suptitle('Track B: actual deformed boundary; no displacement magnification')
    path=figdir/'TRACK_B_ACCEPTED_BOUNDARY.png';fig.savefig(path,dpi=220);plt.close(fig)
    # Prespecified selected original faces at contact onset.
    p=read(RUN/'protocol/TRACK_B_LOCAL_PAIR_002.json')
    source=np.array(p['source_contact_faces_zero_based']);target=np.array(p['target_contact_faces_zero_based'])
    fig,ax=plt.subplots(1,2,figsize=(10,5),layout='constrained')
    for axis,points,title in [(ax[0],mesh.nodes,'Original gap'),(ax[1],xy,'Deformed contact neighborhood')]:
        axis.add_collection(LineCollection(lines(points,mesh.boundary),colors='#aeb7bd',linewidths=.65))
        axis.add_collection(LineCollection(lines(points,mesh.boundary[source]),colors='#cc5926',linewidths=2.5,label='selected source'))
        axis.add_collection(LineCollection(lines(points,mesh.boundary[target]),colors='#177c80',linewidths=2.5,label='selected target'))
        axis.set_xlim(2.515,2.585);axis.set_ylim(2.195,2.30);axis.set_aspect('equal')
        axis.set_title(title);axis.set_xlabel('x (mm)');axis.set_ylabel('y (mm)')
    ax[0].legend(loc='lower left',fontsize=8)
    fig.suptitle(f'Track B selected exterior-arc pair, accepted {100*state["requested_time"]:.3f}%')
    path2=figdir/'TRACK_B_CONTACT_ONSET.png';fig.savefig(path2,dpi=230);plt.close(fig)
    # Native corner-node stress values, linearly interpolated across corner
    # triangles solely for plotting; reported extrema still come from nodes.
    ids=s[:,0].astype(int)-1
    corner_index=np.full(len(mesh.nodes),-1,dtype=int);corner_index[ids]=np.arange(len(ids))
    tri=corner_index[mesh.triangles[:,:3]]
    if np.any(tri<0):raise ValueError('Native corner field omits structural corner node')
    fig,ax=plt.subplots(1,2,figsize=(11,5.4),layout='constrained')
    for axis,column,title,cmap in [(ax[0],1,'Native corner-node SYY (MPa)','coolwarm'),
                                   (ax[1],2,'Native corner-node SEQV (MPa)','viridis')]:
        lo,hi=np.percentile(s[:,column],[1,99])
        im=axis.tripcolor(xy[ids,0],xy[ids,1],tri,s[:,column],cmap=cmap,
                          vmin=lo,vmax=hi,shading='gouraud',rasterized=True)
        fig.colorbar(im,ax=axis,shrink=.8,label='MPa')
        axis.set_xlim(-.05,2.64);axis.set_ylim(-.12,2.66);axis.set_aspect('equal')
        axis.set_title(title);axis.set_xlabel('x (mm)');axis.set_ylabel('y (mm)')
    fig.suptitle(f'Track B native corner stresses at accepted {100*state["requested_time"]:.3f}% (visual interpolation)')
    path3=figdir/'TRACK_B_ACCEPTED_STRESS.png';fig.savefig(path3,dpi=220);plt.close(fig)
    # Every pair-branch accepted checkpoint is shown as a discrete native result.
    records=[]
    for file in (RUN/'track_B_progressive_compression').glob('track_B_pair*_qualification.json'):
        item=read(file)
        if item.get('accepted') and len(item.get('states',[]))==1:
            m=item['states'][0]['measurement'];records.append((m['engineering_compression_strain'],m['nominal_compression_stress_MPa'],
                                                                m['compression_displacement_mm'],abs(m['upper_rf_y_N'])))
    records=sorted(set(records))
    if not records:raise ValueError('No accepted native force curve')
    arr=np.array(records)
    fig,ax=plt.subplots(1,2,figsize=(10,4.1),layout='constrained')
    ax[0].plot(100*arr[:,0],arr[:,1],'-o',color='#156f80',markersize=4)
    ax[0].set_xlabel('Engineering compression (%)');ax[0].set_ylabel('Nominal stress (MPa)')
    ax[1].plot(arr[:,2],arr[:,3],'-o',color='#9c4c22',markersize=4)
    ax[1].set_xlabel('Upper-platen displacement magnitude (mm)');ax[1].set_ylabel('Upper reaction magnitude (N)')
    for a in ax:a.grid(alpha=.25)
    fig.suptitle('Track B: independently accepted native checkpoints only')
    path4=figdir/'TRACK_B_ACCEPTED_CURVES.png';fig.savefig(path4,dpi=230);plt.close(fig)
    m={'schema':'young-dawgs-v068-actual-native-figure-inventory','state_source':source_name,
       'state_qualification_sha256':file_hash(RUN/'track_B_progressive_compression'/(source_name+'_qualification.json')),
       'source_displacement_sha256':file_hash(post/'stage001_displacements.csv'),
       'source_stress_sha256':file_hash(post/'stage001_stress.csv'),
       'accepted_curve_points':len(records),
       'figures':{p.name:{'sha256':file_hash(p),'bytes':p.stat().st_size} for p in [path,path2,path3,path4]},
       'limitations':'2D assumed material, no mesh-convergence, corner-node stress averages, no deformation magnification, separate crop specimen.'}
    write_json(figdir/'FIGURE_INVENTORY.json',m)
    print('Rendered actual native figures',source_name,len(records),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source_name');make(p.parse_args().source_name)
