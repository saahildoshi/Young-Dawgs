"""Actual licensed F1 curves, phase fields, true-scale displacement and summaries."""
import csv
from pathlib import Path
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v074_experiment import RUN,DOC,MICRO,now
from scripts.v074_f1 import model


def table(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def build():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.collections import PolyCollection,LineCollection
    destination=RUN/'f1/figures';destination.mkdir(exist_ok=True)
    results=[read(path) for path in sorted((RUN/'f1/mechanical_response').glob('*.json'))]
    assert len(results)==7 and all(r['accepted'] for r in results)
    curve=[];summary=[];phases=[]
    for r in results:
        for c in r['signed_native_curve']:
            curve.append({'specimen':r['specimen_id'],'mesh_level':r['mesh_level'],'step':int(c[0]),
                'strain_compression_positive':-c[2],'nominal_stress_MPa_compression_positive':-c[5],
                'top_displacement_mm_signed':c[2],'top_reaction_N_signed':c[5],
                'bottom_reaction_N_signed':c[6],'strain_energy_Nmm':c[8],'solid_volume_mm3':c[9],
                'native_RST_sha256':r['native_result_sha256']})
        summary.append({'specimen':r['specimen_id'],'mesh_level':r['mesh_level'],'apparent_modulus_MPa':r['effective_modulus_MPa'],
            'analytical_expected_MPa':r['analytical_expected_MPa'],'elements':r['mesh_proof']['elements'],'nodes':r['mesh_proof']['nodes'],
            'solid_components':r['mesh_proof']['solid_components'],'void_area_fraction':r['mesh_proof']['void_area_mm2'],
            'native_accepted':r['accepted']})
        for mid,values in r['phase_results'].items():
            phases.append({'specimen':r['specimen_id'],'mesh_level':r['mesh_level'],'native_material':int(mid),
                'source_phase':'matrix0' if mid=='1' else 'fiber1','elements':values['elements'],
                'envelope_volume_fraction':values['envelope_volume_fraction'],'mean_syy_MPa':values['mean_syy_MPa'],
                'mean_axial_strain':values['mean_axial_strain'],'equivalent_p95_MPa':values['equivalent_percentiles_MPa']['95'],
                'elastic_energy_fraction':values['elastic_energy_fraction']})
    table(RUN/'f1/F1_NATIVE_CURVES.csv',curve);table(RUN/'f1/F1_MECHANICAL_SUMMARY.csv',summary);table(RUN/'f1/F1_PHASE_SUMMARY.csv',phases)
    selected=['F1_M2_REFERENCE','F1_M3_B02_SEED0'];labels=['Reference','Genuine F1_B_02/r0/seed0'];colors=['#355f8a','#c27d27']
    actual={name:{r['mesh_level']:r for r in results if r['specimen_id']==name} for name in selected}
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for name,label,color in zip(selected,labels,colors):
        for level in [1,2]:
            r=actual[name][level];c=np.asarray(r['signed_native_curve'])
            axes[0].plot(-c[:,2]*100,-c[:,5],marker='o',color=color,linestyle='-' if level==1 else '--',label=f'{label} H{level}')
            axes[1].plot(-c[:,2],-c[:,5],marker='o',color=color,linestyle='-' if level==1 else '--')
    axes[0].set(xlabel='Engineering compression (%)',ylabel='Nominal compression stress (MPa)',title='Actual five-checkpoint ANSYS curves')
    axes[0].legend(fontsize=8)
    axes[1].set(xlabel='Top displacement magnitude (mm)',ylabel='Top reaction magnitude (N)',title='Actual force–displacement · full1mm² envelope')
    for ax in axes:ax.grid(alpha=.2)
    fig.suptitle('F1 · transverse two-solid composite with explicit void · illustrative properties')
    fig.tight_layout(rect=(0,0,1,.94));fig.savefig(destination/'F1_ACTUAL_STRESS_STRAIN_AND_FORCE.png',dpi=170);plt.close(fig)
    cmap=ListedColormap(['#29465c','#e1a944','#ffffff'])
    fig,axes=plt.subplots(1,3,figsize=(12,4))
    from PIL import Image
    axes[0].imshow(Image.open(MICRO/'references/F1/microscopy_input.png'));axes[0].set_title('Prepared original C/PEEK micrograph')
    for ax,name,label in zip(axes[1:],selected,labels):
        m,_,_=model(name,1);ax.imshow(m['source'],cmap=cmap,vmin=0,vmax=2,interpolation='nearest');ax.set_title(label)
    for ax in axes:ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('Matrix0 blue · transverse fiber cross-sections1 gold · void2 white; approximate circular annotations')
    fig.tight_layout(rect=(0,0,1,.92));fig.savefig(destination/'F1_REFERENCE_AND_GENERATED_PHASES.png',dpi=170);plt.close(fig)
    fields=[]
    for name in selected:
        r=actual[name][1];post=Path(r['independent_readback_directory']);m,_,_=model(name,1)
        f=np.loadtxt(post/'fields.csv',delimiter=',');nodes=np.loadtxt(post/'nodes.csv',delimiter=',');q=np.loadtxt(post/'connectivity.csv',delimiter=',').astype(int)[:,1:]-1
        assert np.array_equal(q,m['quads']) and np.allclose(nodes[:,1:3],m['nodes'])
        fields.append((r,m,f,nodes,q))
    fig,axes=plt.subplots(2,2,figsize=(11,10))
    nominal=[r['nominal_stresses_MPa'][-1] for r,_,_,_,_ in fields]
    vmax=max(np.percentile(f[:,5]/stress,99) for (_,_,f,_,_),stress in zip(fields,nominal))
    for column,((r,m,f,nodes,q),label,stress) in enumerate(zip(fields,labels,nominal)):
        label='Reference' if column==0 else 'Generated B02/r0/seed0'
        for row,values,title in [(0,-f[:,3]/stress,'Axial compression / nominal stress'),(1,f[:,5]/stress,'Equivalent stress / nominal stress')]:
            grid=np.full((256,256),np.nan);keep=np.flipud(m['source'])!=2;grid[keep]=values
            image=axes[row,column].imshow(grid,origin='lower',extent=[0,1,0,1],cmap='magma',vmin=0,vmax=vmax,interpolation='nearest')
            axes[row,column].set(title=f'{label}\n{title}',xlabel='Computational X (mm)',ylabel='Computational Y (mm)')
    fig.suptitle('Actual H1 fields at0.5% · void has no element / white · no cross-phase nodal averaging')
    fig.subplots_adjust(top=.87,right=.82,wspace=.3,hspace=.4)
    fig.colorbar(image,cax=fig.add_axes([.86,.23,.02,.52]),label='Native stress / nominal; common99th-percentile limit')
    fig.savefig(destination/'F1_NATIVE_STRESS_FIELDS.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,10))
    for column,((r,m,f,nodes,q),label) in enumerate(zip(fields,labels)):
        label='Reference' if column==0 else 'Generated B02/r0/seed0'
        xy=nodes[:,1:3];u=nodes[:,3:5]
        pc=axes[0,column].scatter(xy[:,0],xy[:,1],c=u[:,1],s=.8,cmap='viridis',vmin=-.005,vmax=0,rasterized=True)
        axes[0,column].set(title=f'{label}\nNative nodal UY (mm)',xlim=(0,1),ylim=(0,1),aspect='equal')
        deformed=(xy+u)[q]
        colors=ListedColormap(['#29465c','#e1a944'])(m['materials']-1)
        axes[1,column].add_collection(PolyCollection(deformed,facecolors=colors,edgecolors='none',antialiased=False))
        axes[1,column].plot([0,1,1,0,0],[0,0,1,1,0],'--',color='gray',linewidth=.7)
        axes[1,column].set(title=f'{label}\nDeformation scale1×',xlim=(-.01,1.01),ylim=(-.01,1.01),aspect='equal',xlabel='Computational X (mm)',ylabel='Computational Y (mm)')
    fig.suptitle('Actual native displacement and true-scale deformation · dashed original envelope')
    fig.subplots_adjust(top=.87,right=.82,wspace=.3,hspace=.4)
    fig.colorbar(pc,cax=fig.add_axes([.86,.59,.02,.22]),label='Actual native UY (mm)')
    fig.savefig(destination/'F1_NATIVE_DISPLACEMENT_TRUE_SCALE.png',dpi=170);plt.close(fig)
    sensitivity=[]
    for name in selected:
        a,b=actual[name][1],actual[name][2]
        sensitivity.append({'specimen':name,'H1_MPa':a['effective_modulus_MPa'],'H2_MPa':b['effective_modulus_MPa'],
            'relative_change_H2_minus_H1_over_H1':b['effective_modulus_MPa']/a['effective_modulus_MPa']-1})
    write(RUN/'f1/MESH_SENSITIVITY.json',{'cases':sensitivity,'interpretation':'Two levels only; non-negligible residual resolution sensitivity, no rigorous error bound or convergence claim'})
    lines=['# F1 mechanical benchmark','',
        'Actual licensed ANSYS solves were completed for three controls, the authenticated C/PEEK reference annotation and the prospectively selected genuine archived F1_B_02/r0/seed0 output. Reference and generated source both received H1/H2. There were seven new source solves and seven independent readbacks, each with five actual strain checkpoints through0.5%. No native failures or geometry repairs occurred.','',
        '| Model | H1 apparent modulus (MPa) | H2 apparent modulus (MPa) | H2 change relative to H1 |','|---|---:|---:|---:|']
    lines += [f'|{label}|{actual[name][1]["effective_modulus_MPa"]:.6f}|{actual[name][2]["effective_modulus_MPa"]:.6f}|{s["relative_change_H2_minus_H1_over_H1"]*100:.3f}%|' for name,label,s in zip(selected,labels,sensitivity)]
    lines += ['',
        'Homogeneous matrix control gave1000MPa (analytical1000); the parallel two-solid,nu0 control gave5500MPa (analytical5500); the explicit-void control gave500MPa (analytical500). The void control has two separate full-height load-carrying matrix strips with one minimal transverse pin per strip. It verifies pruned-node boundary enumeration and full-envelope nominal stress normalization. No arbitrary porous analytical solution is claimed.','',
        'Native phase semantics remain matrix0→MAT1, fiber cross-sections1→MAT2, void2→no element. The reference has34585/29668/1283 matrix/fiber/void pixels; the generated field has34084/30096/1356. Both have one edge-connected solid component, with no floating island or corner-only component attachment. Void elements and unused nodes are removed; internal void boundaries receive no restraints. Shared matrix/fiber interfaces are ideally bonded. No weak springs, pore filling, fiber removal, contact or large-strain simulation was used.','',
        'Illustrative plane-stress properties are E1000/10000MPa,nu0.30. The1mm square/thickness is a computational convention, not microscopy calibration. Nominal stress is total boundary reaction over the full envelope, including void; volume-integrated solid stress independently agrees. All cases pass reaction balance, external work/strain energy, phase constitutive fields, mesh/material/constraint inventories and independent RST reopening. The archived generator receipt/source/output hashes authenticate the genuine specimen; no new F1 generator call or researcher replacement baseline was counted.','',
        'F1_NATIVE_CURVES.csv records35 actual checkpoint rows including signed reactions/displacements and strain energy. F1_PHASE_SUMMARY.csv contains native element-associated phase stress/strain/energy summaries; F1_MECHANICAL_SUMMARY.csv records all seven models. Source/readback paths and native hashes are preserved in the mechanical-response manifests. The figures show actual stress–strain/force response, phase maps, native axial/equivalent stress, native nodal displacement and deformation at1× scale. Void regions remain blank; no cross-material nodal stress averaging is used.','',
        'The reference is a transverse cross-section. Approximately circular fiber annotations carry documented boundary and void-label uncertainty; no longitudinal fiber length or in-plane fiber-axis orientation is inferred. One reference and one archived generated realization do not establish cross-family generalization. H2 reduces apparent modulus by about3.24% and2.54%; these non-negligible changes must accompany comparisons. Two levels do not establish mesh convergence or a rigorous error bound. Mechanical material calibration, physical composite behavior, RVE homogenization and isotropy remain unverified. Additional archived C02 comparisons were optional and were not run, preserving focus on the registered P3 trial.','']
    (DOC/'V0_7_4_F1_MECHANICAL_RESULTS.md').write_text('\n'.join(lines),encoding='utf-8',newline='\n')
    write(RUN/'f1/REPORT_MANIFEST.json',{'created_utc':now(),'actual_source_solves':7,'independent_readbacks':7,'actual_checkpoints':35,
        'files':{str(path.relative_to(RUN)):sha(path) for path in sorted((RUN/'f1').rglob('*')) if path.is_file() and path.name!='REPORT_MANIFEST.json'},
        'report_sha256':sha(DOC/'V0_7_4_F1_MECHANICAL_RESULTS.md'),'not_physically_calibrated':True})
    print('F1 ACTUAL REPORT',sensitivity,flush=True)


if __name__=='__main__':build()
