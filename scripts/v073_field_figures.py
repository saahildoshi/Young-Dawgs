"""Predetermined development native fields and explicit synthetic diagnostic fixtures."""
import importlib.util
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy import ndimage as ndi
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v073_experiment import RUN
from scripts.v073_development import FAMILIES
from scripts.v073_figures import COLORS
from metamaterial_eval.composites.morphology_v073 import describe

def fixtures():
    spec=importlib.util.spec_from_file_location('independent_v073_fixture_definitions',REPO/'tests/test_v073_morphology.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    kinds=['circles','horizontal','vertical','balanced','tail','irregular','lanes','horizontal_lanes','chain','boundary','clustered']
    arrays={kind:m.fixture(kind) for kind in kinds}
    a=np.zeros((256,256),bool);a[:,:64]=True;arrays['known_occupancy']=a
    arrays['reflection']=np.fliplr(arrays['irregular']).copy()
    records=[];fig,axes=plt.subplots(3,5,figsize=(13,8))
    for ax,(kind,a) in zip(axes.flat,arrays.items()):
        out=RUN/'morphology_descriptor_validation/fixtures'/f'{kind}.npy';out.parent.mkdir(exist_ok=True);np.save(out,a)
        row={'fixture':kind,'synthetic_analytical_digital_not_native_or_LLM':True,'array_sha256':sha(out),'descriptors':describe(a)}
        write(out.with_suffix('.json'),row);records.append(row)
        ax.imshow(a,cmap=COLORS,vmin=0,vmax=1,interpolation='nearest');ax.set_title(kind,fontsize=10);ax.set_xticks([]);ax.set_yticks([])
    for ax in axes.flat[len(arrays):]:ax.axis('off')
    fig.suptitle('Independent synthetic digital fixtures: descriptor verification only')
    fig.tight_layout();out=RUN/'figures/INDEPENDENT_DESCRIPTOR_FIXTURES.png';fig.savefig(out,dpi=160);plt.close(fig)
    write(RUN/'morphology_descriptor_validation/FIXTURE_INVENTORY.json',{'records':records,'fixture_source_sha256':sha(REPO/'tests/test_v073_morphology.py'),'figure_sha256':sha(out)})
    # Actual rejected geometry versus its evaluator-only diagnostic transformations.
    a=np.load(RUN/'controlled_variants/BASE/seed_3104.npy')==5
    yy,xx=np.mgrid[-2:3,-2:3];dil=ndi.binary_dilation(a,structure=xx*xx+yy*yy<=4)
    fig,axes=plt.subplots(1,2,figsize=(9,4.6))
    for ax,mask,title in zip(axes,[a,dil],['Actual BASE seed3104 (preserved)','Evaluator-only 2px disk dilation']):
        ax.imshow(mask,cmap=COLORS,vmin=0,vmax=1,interpolation='nearest');ax.set_title(title,fontsize=10);ax.set_xticks([]);ax.set_yticks([])
    fig.suptitle('Rejected development geometry: diagnostic near-spanning, not physical bonding',fontsize=11)
    fig.tight_layout();out=RUN/'figures/INFEASIBLE_BASELINE_DIAGNOSTIC.png';fig.savefig(out,dpi=160);plt.close(fig)
    write(out.with_suffix('.json'),{'source_sha256':sha(RUN/'controlled_variants/BASE/seed_3104.npy'),
        'specimen_modified':False,'mechanical_solve':False,'diagnostic_only_dilation_radius_px':2,'figure_sha256':sha(out)})

def fields():
    sources=[]
    for trial in FAMILIES:
        path=RUN/'mechanical_response'/f'{trial}_development_3100_H2_attempt001.json'
        r=read(path);d=Path(r['independent_readback_directory'])
        f=np.loadtxt(d/'fields.csv',delimiter=',');n=np.loadtxt(d/'nodes.csv',delimiter=',')
        sources.append((r,f,n))
    stress=max(float(np.percentile(np.abs(f[:,3]),99.5)) for r,f,n in sources)
    equivalent=max(float(np.percentile(f[:,5],99.5)) for r,f,n in sources)
    strain=max(float(np.percentile(np.abs(f[:,7]),99.5)) for r,f,n in sources)
    displacement=max(float(np.linalg.norm(n[:,3:5],axis=1).max()) for r,f,n in sources)
    limits=[(-stress,stress),(0,equivalent),(-strain,strain),(0,displacement)]
    fig,axes=plt.subplots(5,5,figsize=(15,13),gridspec_kw={'height_ratios':[1,1,1,1,.7]});images=[None]*4
    provenance=[]
    for i,(trial,(r,f,n)) in enumerate(zip(FAMILIES,sources)):
        values=[f[:,3].reshape(512,512),f[:,5].reshape(512,512),f[:,7].reshape(512,512),np.linalg.norm(n[:,3:5],axis=1).reshape(513,513)]
        for j,(value,cmap) in enumerate(zip(values,['coolwarm','magma','coolwarm','viridis'])):
            images[j]=axes[j,i].imshow(value,origin='lower',extent=(0,1,0,1),interpolation='nearest',cmap=cmap,vmin=limits[j][0],vmax=limits[j][1])
            axes[j,i].set_xticks([]);axes[j,i].set_yticks([])
        axes[0,i].set_title(trial,fontsize=10)
        axes[4,i].bar(['Matrix','Reinf.'],[r['phase_results'][str(k)]['elastic_energy_fraction'] for k in (1,2)],color=['#2d4664','#ebaa37']);axes[4,i].set_ylim(0,1);axes[4,i].tick_params(labelsize=8)
        provenance.append({'specimen_id':r['specimen_id'],'mesh_level':2,'native_RST_sha256':r['native_result_sha256'],'native_fields_sha256':r['native_fields_sha256'],
            'native_nodes_sha256':sha(Path(r['independent_readback_directory'])/'nodes.csv'),'native_phase_results':r['phase_results']})
    for ax,label in zip(axes[:,0],['Native SYY (MPa)','Native equivalent stress (MPa)','Native EYY','Derived native |U| (mm)','Elastic energy fraction']):ax.set_ylabel(label,fontsize=9)
    fig.suptitle('Actual H2 native fields · preselected development seed3100 · 0.5% compression',fontsize=13)
    fig.subplots_adjust(left=.08,right=.91,bottom=.04,top=.95,wspace=.16,hspace=.16)
    for j in range(4):
        position=axes[j,-1].get_position();cax=fig.add_axes([.935,position.y0,.012,position.height]);fig.colorbar(images[j],cax=cax).ax.tick_params(labelsize=8)
    out=RUN/'figures/NATIVE_DEVELOPMENT_FIELDS.png';fig.savefig(out,dpi=160);plt.close(fig)
    write(out.with_suffix('.json'),{'selection':'First registered development seed3100 in every family, chosen before results',
        'sources':provenance,'limits':limits,'stress_and_strain_clipping':'Common max per-specimen99.5-percentile magnitude; raw extremes retained. Element-associated values, no cross-material nodal averaging.',
        'displacement':'Euclidean norm of actual native nodal UX/UY; no magnification','computational_dimensions_not_microscopy_calibration':True,'figure_sha256':sha(out)})

if __name__=='__main__':fixtures();fields()
