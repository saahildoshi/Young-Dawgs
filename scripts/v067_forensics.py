"""Reviewable residual localization and true-scale accepted-state close-up."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.optimize import minimize
from scripts.v067_audit import REPO, RUN
from scripts.v067_fixture import BASE


def curve(p, t):
    t = np.asarray(t)[..., None]
    return p[0]*(1-t)*(1-2*t) + p[1]*t*(2*t-1) + p[2]*4*t*(1-t)


def main():
    from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest, artifact_root
    from metamaterial_eval.simulation.reporting import write_json
    m, _, _ = resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json', root=Path.home()/'YoungDawgs-Artifacts')
    old = artifact_root()/'solver/v066'
    u = np.load(old/'fine_nodal_recovery01_001_qualified001/state006/native_displacement.npy', mmap_mode='r')
    xy = u[:, 3:5]
    residuals = [json.loads((RUN/'contact_onset'/f'compression.nr00{i}.json').read_text(encoding='utf-8')) for i in [1, 2]]
    pair = [27837, 28505]
    points = [xy[m.boundary[i]] for i in pair]
    solution = minimize(lambda ts: float(np.sum((curve(points[0], ts[0])-curve(points[1], ts[1]))**2)), [.9,.5], bounds=[(0,1),(0,1)], method='Nelder-Mead', options={'xatol':1e-14,'fatol':1e-30,'maxiter':3000})
    normals=[]
    for p,t in zip(points, solution.x):
        tangent=p[0]*(-3+4*t)+p[1]*(-1+4*t)+p[2]*(4-8*t)
        normal=np.array([tangent[1],-tangent[0]])/np.linalg.norm(tangent)
        normals.append(normal.tolist())
    normal_evidence={'boundary_indices_zero_based':pair,'parameter_t':solution.x.tolist(),'outward_right_normals_assuming_original_oriented_boundary':normals,
                     'normal_dot_product':float(np.dot(*normals)),'estimated_separation_mm':float(np.sqrt(solution.fun)),
                     'scope':'Floating-point closest-point estimate, not certified minimum gap; prior exact subdivision lower bound remains governing.'}
    write_json(RUN/'contact_onset/LOCAL_NORMAL_ESTIMATE.json',normal_evidence)
    fig, ax=plt.subplots(1,2,figsize=(11,5),layout='constrained')
    for panel,extent in zip(ax,[(1.90,1.97,10.10,10.16),(1.932,1.936,10.1295,10.1335)]):
        mask=np.any((xy[m.boundary,:,][...,0]>extent[0]) & (xy[m.boundary][...,0]<extent[1]) & (xy[m.boundary][...,1]>extent[2]) & (xy[m.boundary][...,1]<extent[3]),axis=1)
        for i in np.flatnonzero(mask):
            c=curve(xy[m.boundary[i]],np.linspace(0,1,20)); panel.plot(c[:,0],c[:,1],color='#999999',lw=.5)
        for i,color in zip([27837,28505,28506],['#bc342f','#156aab','#27854c']):
            c=curve(xy[m.boundary[i]],np.linspace(0,1,100));panel.plot(c[:,0],c[:,1],color=color,lw=1.8,label=f'boundary {i}')
        for r in residuals[-1]['top_residual_nodes'][:4]:
            panel.scatter(*r['accepted_parent_xy_mm'],s=20,color='#111111',zorder=5)
        panel.set(xlim=extent[:2],ylim=extent[2:],xlabel='x (mm)',ylabel='y (mm)');panel.set_aspect('equal')
    ax[0].legend(fontsize=8);ax[0].set_title('Accepted parent: true-scale boundary geometry')
    ax[1].set_title('Residual hotspot positions on accepted geometry\nFailed-trial displacement is unavailable')
    fig.savefig(RUN/'figures/contact_onset_closeup.png',dpi=180);plt.close(fig)
    lines=['# v0.6.7 contact-onset forensics','',
           'The retained v241 Newton residual snapshots localize the difficulty to approaching external surfaces near the upper edge. This is self-contact in general-contact group −4, adjacent to a free/top corner; it is not evidence of an internal pore wall engaging. The residuals, pair-level switching, and prior exact crossing share the same location. Causality still requires a mechanically matching local experiment.','',
           '| File | Native time | LS/SS/iteration | Specimen residual L2 (N) | Largest node | Original x,y (mm) | Accepted x,y (mm) | Magnitude (N) |','|---|---:|---|---:|---:|---|---|---:|']
    for q in residuals:
        r=q['top_residual_nodes'][0]
        lines.append(f"| {'nr001' if q is residuals[0] else 'nr002'} | {q['pseudo_time']:.12g} | {q['load_step']}/{q['substep']}/{q['iteration']} | {q['specimen_translation_L2_N']:.9g} | {r['node']} | {r['xy_mm']} | {r['accepted_parent_xy_mm']} | {r['translation_residual_norm_N']:.9g} |")
    lines += ['', 'The largest components are FX. Native residual values are component magnitudes; their signs and failed-trial coordinates are unavailable. The close-up uses the last accepted displacement field and does not portray the failed trial as converged.', '',
              'Relevant zero-based boundary indices 27837, 28505 and 28506 map to native GC skin IDs 1295993, 1494296 and 1494295. Adjacent surfaces include 27838/1285266 and 28504/1383913. Original nodes 98184, 99405, 99399 and 4990 dominate the terminal region. Full top-64 mappings and source hashes are in the residual JSON files.', '',
              f"At the accepted parent, an approximate closest-point normal dot product is {normal_evidence['normal_dot_product']:.9g}; the normals oppose. This numerical estimate is not a rigorous global gap measurement. Prior exact subdivision proved positive lower bounds 5.490409559e−11 and 1.112294602e−10 mm for the two suspicious pairs; those tiny values are geometric bounds, not physical resolution.", '',
              'Accepted parent general contact is open with zero pressure. The terminal UNCONVERGED group −4 record reports three active skins, chattering level4, penetration3.178046e−6 mm, pressure4906.241 MPa, stiffness1.543792e9 and FY−2.060718 N. Pair-level diagnostics do not identify individual switching skins or their pressures. Their locations are inferred from residual concentration, not invented per-element trial fields.', '',
              'Strongest hypothesis: near endpoint contact activates a stiff penalty constraint and cycles between surfaces. FKN100 may amplify the switching; reducing it is a candidate only if the licensed local fixture preserves force transmission and the unchanged penetration/overlap gates. Other unresolved contributions include missing global compliance and nonlinear boundary-path sensitivity.', '',
              'The previous platen-only and Gauss-GC 1% states remain rejected for exact quadratic solid crossing. The 15 accepted nodal-branch states through0.9270608836206897% remain preserved. No new full-model solve has been run.', '']
    (RUN/'summary/V0_6_7_CONTACT_ONSET_FORENSICS.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')


if __name__=='__main__':main()

