"""Post-study explanatory examples and allowance-explicit bound table.

Read-only geometry analysis; does not change candidate acceptance or frozen code.
"""
import json
from pathlib import Path
import sys
import numpy as np
import shapely
from shapely import box,LineString,MultiPoint
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUTPUT=Path(__file__).resolve().parents[1];ROOT=OUTPUT.parents[3]
sys.path.insert(0,str(ROOT))
from metamaterial_eval.geometry.sensitivity.records import write_json
from metamaterial_eval.geometry.protected.reporting import draw_lines,save


def read(path):return json.loads(path.read_text())


def main():
    acceptance=read(OUTPUT/'summary/ACCEPTANCE.json');rows=acceptance['candidate_rows']
    examples={};bounds=[]
    for r in rows:
        folder=OUTPUT/r['relative_directory'];engine=read(folder/'engine.json');q=read(folder/'qualification.json')
        allowance=q['limits']['length_allowance'];bound=r['boundary_certified_upper']
        bounds.append({'fixture':r['fixture'],'epsilon':r['epsilon'],'analytic_bound_evaluated_in_float':bound,
            'numeric_comparison_allowance':allowance,'upper_with_numeric_allowance':bound+allowance if bound else 0.,
            'measured_lower':r['boundary_measured_lower'],
            'note':'Analytic endpoint-matched chain bound, evaluated in floating arithmetic; not an exact rational/interval calculation.'})
        for p in engine['proposals']:
            if p['entered_guards'] and 'guard' not in examples:examples['guard']=(r,p)
            if 'cell_center_on_replacement_boundary' in p['failed_constraints'] and 'center' not in examples:examples['center']=(r,p)
    write_json(OUTPUT/'verification/BOUNDS_WITH_NUMERIC_ALLOWANCE.json',bounds)
    assert set(examples)=={'guard','center'}
    fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
    for ax,kind in zip(axes,('guard','center')):
        r,p=examples[kind];folder=OUTPUT/r['relative_directory'];xy=np.asarray(p['original_chain']);origin=xy.mean(axis=0)
        lo=xy.min(axis=0)-1;hi=xy.max(axis=0)+1;guard=None
        if kind=='guard':
            g=next(g for g in read(folder/'guards.json') if g['guard_id'] in p['entered_guards'])
            guard=shapely.from_wkb(bytes.fromhex(g['geometry_wkb_hex']))
            # Keep a native-coordinate closeup of the proposed change. The full
            # guard can be a long corridor and would hide this small rejection.
        window=box(*lo,*hi);base=read(OUTPUT/r['stage']/r['fixture']/'baseline.json')
        source=shapely.from_wkb((ROOT/base['provenance']['paths']['manifold']).read_bytes())
        draw_lines(ax,source.boundary.intersection(window),'#bbbbbb',origin,lw=1)
        draw_lines(ax,LineString(p['original_chain']),'#0086bb',origin,lw=2)
        chord=LineString(p['proposed_replacement']);draw_lines(ax,chord,'#cc3377',origin,lw=1.7,ls='--')
        if kind=='guard':
            draw_lines(ax,guard.boundary.intersection(window),'#ddaa00',origin,lw=2)
            draw_lines(ax,MultiPoint(xy).convex_hull,'#cc3377',origin,lw=.7,ls=':')
            title=f"Guard/change-support rejection (local guard boundary)\n{r['fixture']}, ε={r['epsilon']:g}; {g['guard_id']}"
        else:
            xx,yy=np.meshgrid(np.arange(np.ceil(lo[0]-.5),np.floor(hi[0]-.5)+1)+.5,
                              np.arange(np.ceil(lo[1]-.5),np.floor(hi[1]-.5)+1)+.5)
            centers=np.column_stack((xx.ravel(),yy.ravel()));local=centers-origin
            ax.scatter(local[:,0],local[:,1],s=16,color='#bbbbbb',zorder=2)
            on=shapely.distance(shapely.points(centers),chord)<1e-10
            ax.scatter(local[on,0],local[on,1],s=65,facecolors='none',edgecolors='#cc3377',zorder=4)
            title=f"Conservative cell-center boundary rejection\n{r['fixture']}, ε={r['epsilon']:g}; circled sampled centers"
        ax.set(xlim=(lo[0]-origin[0],hi[0]-origin[0]),ylim=(hi[1]-origin[1],lo[1]-origin[1]),
            xlabel='Δx (cell)',ylabel='Δy down (cell)',title=title);ax.set_aspect('equal');ax.grid(alpha=.2)
    fig.suptitle('Actual rejected proposals: blue source/restored chain; dashed magenta replacement; gold guard\nExamples selected after the study for explanation only; no limits, algorithms or candidates changed',fontsize=10)
    save(fig,OUTPUT,'13_guard_and_cell_center_rejections')
    print('Wrote numerical-allowance bounds and actual guard/cell-center rejection closeups.')


if __name__=='__main__':main()
