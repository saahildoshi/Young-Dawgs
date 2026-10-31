"""Small scientific figures exposing the successful diagnostics and failed gates."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scripts.v067_fixture import BASE, RUN
from scripts.v067_forensics import curve


def main():
    fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    cases=[('local_baseline_003','Nodal2 FKN100','#49668b'),('local_fkn10_002','Nodal2 FKN10','#856347'),
           ('local_fkn1_001','Nodal2 FKN1','#3f8656'),('local_projection3_001','Projection3 FKN1 (geometry rejected)','#ba3f47')]
    for label,title,color in cases:
        d=BASE/label;tele=json.loads((d/'nonlinear_telemetry.json').read_text(encoding='utf-8'))
        c=json.loads((d/'contact_telemetry.json').read_text(encoding='utf-8'))['records'];points=[]
        for s in tele['converged_substeps']:
            rows=[r for r in c if r['pair']<0 and (r['load_step'],r['substep'])==(s['load_step'],s['substep'])]
            if rows:points.append(rows[-1])
        axes[0].plot([p['pseudo_time'] for p in points],[max(0,p['penetration_or_gap_mm'])*1e6 for p in points],label=title,color=color,ls='--' if 'projection' in label else '-')
        f=tele['force_evaluations'][-64:]
        axes[1].plot(range(-len(f)+1,1),[v['ratio'] for v in f],label=title,color=color,ls='--' if 'projection' in label else '-')
    axes[0].axhline(10,color='black',ls=':',label='Unchanged penetration limit')
    axes[0].set(xlabel='Cut-boundary loading parameter\n(secant extrapolation beyond0.009270609)',ylabel='Native converged contact penetration (nm)',xlim=(.0092,.01002))
    axes[1].set(xlabel='Force evaluations relative to terminal record',ylabel='Force residual / native criterion',yscale='log',ylim=(1e-4,1e5))
    axes[1].axhline(1,color='black',ls=':')
    axes[0].legend(fontsize=7);axes[1].set_title('Native convergence alone does not qualify geometry')
    fig.savefig(RUN/'figures/local_candidate_comparison.png',dpi=170);plt.close(fig)
    z=np.load(BASE/'source_fixture_001/mesh.npz');u=np.loadtxt(BASE/'local_projection3_001_post001/state019_displacements.csv',delimiter=',',skiprows=1)
    xy=z['nodes']+u[:,1:3];center=xy[65]
    fig,ax=plt.subplots(figsize=(6.5,5.5),layout='constrained')
    for edge,color in zip([257,258,259,130,131,423,424],['#ba3f47']*3+['#176aab']*4):
        c=curve(xy[z['boundary'][edge]],np.linspace(0,1,100));ax.plot(c[:,0],c[:,1],color=color,lw=1.5)
    ax.scatter(*center,color='black',s=15)
    ax.set(xlim=(center[0]-.003,center[0]+.003),ylim=(center[1]-.004,center[1]+.002),xlabel='x (mm)',ylabel='y (mm)',
           title='Local projection result: geometry HOLD\nTrue scale; extrapolated boundary parameter0.01')
    ax.ticklabel_format(axis='both',useOffset=False,style='plain')
    ax.set_aspect('equal');fig.savefig(RUN/'figures/local_projection_geometry_hold.png',dpi=180);plt.close(fig)


if __name__=='__main__':main()
