"""Supplementary relative-coordinate contact figures; no geometry is changed.

Run from the repository root with --study and a NEW --output-dir. Original study
figures remain untouched. Relative ticks keep three-digit native coordinates
legible at quarter-cell inspection scales.
"""
import argparse
import json
from pathlib import Path
import numpy as np
import shapely
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from metamaterial_eval.geometry.manifold.contacts import polygon_rings


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--study',required=True);parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();study=Path(args.study);out=Path(args.output_dir)
    out.mkdir(parents=True,exist_ok=False)
    for case in sorted(study.glob('design_*')):
        if not case.is_dir():continue
        qpath=case/'solid_separate_contacts/qualification.json'
        if not qpath.exists():continue
        q=json.loads(qpath.read_text());source=json.loads((case/'input_manifest.json').read_text())
        mask=np.load(Path(source['source_directory'])/'microstructure.npy',allow_pickle=False)
        exact=shapely.from_wkb((case/'exact_geometry/exact_polygon.wkb').read_bytes())
        candidate=shapely.from_wkb((qpath.parent/'manifold_candidate.wkb').read_bytes())
        added=candidate.difference(exact)
        for c in q['contact_report']['contacts']:
            x,y=c['xy'];fig,axes=plt.subplots(1,2,figsize=(10,5),layout='constrained')
            for ax,g,title in zip(axes,(exact,candidate),('State 2: exact','State 3: optional solid-side candidate')):
                ax.imshow(mask,extent=(-x,len(mask)-x,len(mask)-y,-y),origin='upper',cmap='gray',vmin=0,vmax=1,interpolation='nearest')
                for ring in polygon_rings(g):
                    p=np.asarray(ring['xy'])-[x,y];ax.plot(p[:,0],p[:,1],color='#ec168c' if g is candidate else '#00a5ee',lw=2)
                ax.set_xlim(-1.25,1.25);ax.set_ylim(1.25,-1.25);ax.set_aspect('equal')
                ax.set_xticks([-1,-.5,0,.5,1]);ax.set_yticks([-1,-.5,0,.5,1]);ax.grid(alpha=.3)
                ax.set_xlabel('x − contact x / raster cell');ax.set_ylabel('y − contact y / raster cell (down)');ax.set_title(title,fontsize=10)
            local=added.intersection(shapely.box(x-1.25,y-1.25,x+1.25,y+1.25))
            parts=list(local.geoms) if hasattr(local,'geoms') else [local]
            for p in parts:
                if p.geom_type=='Polygon':
                    xy=np.asarray(p.exterior.coords)-[x,y];axes[1].fill(xy[:,0],xy[:,1],color='#e5a000',alpha=.85)
            fig.suptitle(f"{case.name}: {c['kind']} at ({x:g},{y:g})\nAmber = added solid; continuous geometry differs; raster occupancy unchanged",fontsize=10)
            fig.savefig(out/(case.name+'_'+c['contact_id']+'.png'),dpi=180);plt.close(fig)
    (out/'README.txt').write_text('Source: saved exact/candidate WKB and canonical NPY. Relative-coordinate figures supplement, and do not overwrite, original study diagrams.\n')


if __name__=='__main__':main()
