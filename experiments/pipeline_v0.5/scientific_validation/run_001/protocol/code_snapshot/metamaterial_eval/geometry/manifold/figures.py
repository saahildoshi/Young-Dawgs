"""Native-grid contact diagrams and separately labeled candidate diagnostics."""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from PIL import Image
from .contacts import polygon_rings


def contact_figures(folder,mask,exact,diagnosis):
    rings=polygon_rings(exact['geometry'])
    for c in diagnosis['contacts']:
        x,y=c['xy'];radius=4
        fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
        for ax in axes:
            ax.imshow(mask,extent=(0,len(mask),len(mask),0),origin='upper',cmap='gray',vmin=0,vmax=1,interpolation='nearest')
            ax.set_xlim(max(0,x-radius),min(len(mask),x+radius));ax.set_ylim(min(len(mask),y+radius),max(0,y-radius))
            ax.set_xticks(np.arange(max(0,x-radius),min(len(mask),x+radius)+1))
            ax.set_yticks(np.arange(max(0,y-radius),min(len(mask),y+radius)+1))
            ax.grid(color='#888888',linewidth=.5);ax.set_aspect('equal')
            ax.scatter([x],[y],s=70,c='#ff00b4',zorder=5)
            ax.set_xlabel('x / raster cell');ax.set_ylabel('y down / raster cell')
        for ri in c['incident_rings']:
            p=np.asarray(rings[ri]['xy']);color=f'C{ri%10}'
            axes[1].plot(p[:,0],p[:,1],color=color,lw=2,label=f"ring {ri}: {rings[ri]['role']}")
            for a,b in zip(p[:-1],p[1:]):
                if max(abs(a[0]-x),abs(a[1]-y))<=1 and max(abs(b[0]-x),abs(b[1]-y))<=3:
                    midpoint=(a+b)/2;delta=(b-a)/np.linalg.norm(b-a)*.3
                    axes[1].annotate('',xy=midpoint+delta,xytext=midpoint-delta,arrowprops={'arrowstyle':'->','color':color,'lw':1.5})
        for label,(dx,dy),solid in zip(('NW','NE','SW','SE'),((-.5,-.5),(.5,-.5),(-.5,.5),(.5,.5)),c.get('local_cells_NW_NE_SW_SE',[0]*4)):
            axes[0].text(x+dx,y+dy,f"{label}\n{'solid 1' if solid else 'void 0'}",ha='center',va='center',fontsize=9,color='black' if solid else 'white')
        axes[0].set_title('Canonical cells; integer grid; no interpolation')
        axes[1].set_title(f"{c['kind']}; boundary link degree {c['boundary_link_degree']}")
        axes[1].legend(loc='upper right',fontsize=8)
        fig.suptitle(f"{c['contact_id']} at ({x:g},{y:g}): 2 solid / 2 void sectors; point-only local link",fontsize=11)
        fig.savefig(folder/(c['contact_id']+'.png'),dpi=180);plt.close(fig)


def candidate_figures(folder,mask,exact,result):
    geometry=result['geometry']
    if geometry is None:return
    rec=result['reconstructed'];Image.fromarray(rec*255).save(folder/'candidate_reconstruction.png')
    diff=np.zeros((*mask.shape,3),dtype=np.uint8)
    diff[(mask==0)&(rec==1)]=(255,50,20);diff[(mask==1)&(rec==0)]=(20,120,255)
    Image.fromarray(diff).save(folder/'raster_difference.png')
    contacts=result['contact_report']['contacts']
    if not contacts:return
    fig,axes=plt.subplots(1,2,figsize=(12,5.5),layout='constrained')
    x,y=contacts[0]['xy']
    for ax in axes:
        ax.imshow(mask,extent=(0,len(mask),len(mask),0),origin='upper',cmap='gray',vmin=0,vmax=1,interpolation='nearest')
        ax.set_xlim(x-1.25,x+1.25);ax.set_ylim(y+1.25,y-1.25);ax.set_aspect('equal')
        ax.set_xticks(np.arange(x-1,x+1.01,.25));ax.set_yticks(np.arange(y-1,y+1.01,.25));ax.grid(alpha=.25)
    for ring in polygon_rings(exact['geometry']):
        p=np.asarray(ring['xy']);axes[0].plot(p[:,0],p[:,1],color='#00b0ff',lw=1.5)
    for ring in polygon_rings(geometry):
        p=np.asarray(ring['xy']);axes[1].plot(p[:,0],p[:,1],color='#ff1685',lw=2)
    added=geometry.difference(exact['geometry']);removed=exact['geometry'].difference(geometry)
    for area,color in ((added,'#f5a000'),(removed,'#00ccdd')):
        parts=list(area.geoms) if hasattr(area,'geoms') else [area]
        for part in parts:
            if part.geom_type=='Polygon':
                p=np.asarray(part.exterior.coords);axes[1].fill(p[:,0],p[:,1],color=color,alpha=.8)
    axes[0].set_title('State 2: exact vector boundary')
    axes[1].set_title('State 3: candidate; amber added / cyan removed')
    fig.suptitle(f"{result['contact_policy']}: {result['status']}\nContinuous geometry change is shown; source pixels remain unchanged",fontsize=11)
    fig.savefig(folder/'candidate_contact.png',dpi=180);plt.close(fig)
