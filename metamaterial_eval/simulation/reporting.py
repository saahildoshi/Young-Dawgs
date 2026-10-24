"""Deterministic documents, actual mesh diagnostics and immutable run folders."""
import hashlib
import json
from pathlib import Path
import numpy as np


def write_json(path, value):
    Path(path).write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n')


def mesh_hash(mesh):
    h=hashlib.sha256()
    for array in [mesh.nodes,mesh.triangles,mesh.boundary,mesh.boundary_groups.astype('S8')]:
        h.update(np.ascontiguousarray(array).tobytes())
    return h.hexdigest()


def diagnostic_figures(folder, mesh, geometry, mask, quality, config, probes):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection, PolyCollection
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    def finish(fig,name):
        fig.tight_layout();fig.savefig(folder/name,dpi=160);plt.close(fig)
    fig,ax=plt.subplots(figsize=(6,6))
    ax.imshow(mask,cmap='gray',origin='upper');ax.set_title('Authenticated source: solid white; native 1024')
    finish(fig,'01_original.png')
    fig,ax=plt.subplots(figsize=(6,6))
    ax.add_collection(LineCollection([np.asarray(r.coords) for r in [geometry.exterior,*geometry.interiors]],linewidths=.3))
    ax.set(xlim=(0,config.width),ylim=(0,config.height),aspect='equal',title='Exact 2D geometry in y-up mm coordinates')
    finish(fig,'02_vector.png')
    for closeup in [False,True]:
        fig,ax=plt.subplots(figsize=(7,6))
        coords=mesh.nodes[mesh.triangles[:,:3]]
        if closeup:
            p=min(probes,key=lambda p:p['source_pixel_run']);x=p['xy'][0]*config.width/1024;y=config.height-p['xy'][1]*config.height/1024
            visible=np.any((abs(coords[:,:,0]-x)<.12)&(abs(coords[:,:,1]-y)<.12),axis=1)
            coords=coords[visible]
            ax.set(xlim=(max(0,x-.1),min(config.width,x+.1)),ylim=(max(0,y-.1),min(config.height,y+.1)))
        else:ax.set(xlim=(0,config.width),ylim=(0,config.height))
        ax.add_collection(PolyCollection(coords,facecolors='none',edgecolors='#345778',linewidths=.2))
        ax.set(aspect='equal',xlabel='x [mm]',ylabel='y [mm]',title='Generated TRI6 mesh — no solver results'+(' / narrow-chord detail' if closeup else ''))
        finish(fig,'04_narrow_mesh.png' if closeup else '03_mesh.png')
    fig,ax=plt.subplots(figsize=(6,4));ax.hist(quality,bins=50)
    ax.set(xlabel='4√3 A / Σ(edge length²)',ylabel='Triangle count',title='Actual generated mesh quality; gate ≥ 0.1')
    finish(fig,'05_quality.png')
    fig,ax=plt.subplots(figsize=(7,6))
    colors={'top':'#e65c30','bottom':'#247cbc','pore':'#5d9b65','external':'#aaaaaa'}
    for label,color in colors.items():
        edges=mesh.boundary[mesh.boundary_groups==label,:2]
        ax.add_collection(LineCollection(mesh.nodes[edges],colors=color,linewidths=.5,label=label))
    ax.plot([-.1,config.width+.1],[config.height]*2,color=colors['top'],lw=3)
    ax.plot([-.1,config.width+.1],[0]*2,color=colors['bottom'],lw=3)
    ax.annotate('',xy=(config.width/2,config.height-.3),xytext=(config.width/2,config.height+.3),arrowprops={'arrowstyle':'->'})
    ax.set(xlim=(-.4,config.width+.4),ylim=(-.4,config.height+.5),aspect='equal',title='Platen/contact boundary plan — ANSYS NOT EXECUTED')
    ax.legend();finish(fig,'06_contact_setup.png')
