"""Actual-data morphology review with predetermined first-seed examples."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import numpy as np
from scripts.v070_protocol import read,write,sha
from scripts.v073_experiment import RUN,DOC,PREV,REFERENCE

COLORS=ListedColormap(['#2d4664','#ebaa37'])

def review():
    paths=[REFERENCE,RUN/'envelope_calibration/seed_3000.npy',RUN/'envelope_calibration/seed_3001.npy',
        PREV/'heldout_structures/P3_OPT_MF_01/seed_2000.npy',PREV/'heldout_structures/P3_OPT_MF_02/seed_2000.npy',
        PREV/'heldout_structures/P3_OPT_NF_01/seed_2000.npy',PREV/'heldout_structures/P3_OPT_NF_02/seed_2000.npy',
        RUN/'controlled_variants/BASE/seed_3100.npy',RUN/'controlled_variants/V1_ELONGATION/seed_3100.npy',
        RUN/'controlled_variants/V2_VERTICAL/seed_3100.npy',RUN/'controlled_variants/V3_HORIZONTAL/seed_3100.npy',
        RUN/'controlled_variants/V4_DISPERSION/seed_3100.npy']
    titles=['P3 annotation','Exact baseline /3000','Exact baseline /3001','Historical MF01','Historical MF02','Historical NF01','Historical NF02',
        'Development BASE','Elongation','Vertical bias','Horizontal bias','Reduced field clustering']
    fig,axes=plt.subplots(3,4,figsize=(13,10))
    from metamaterial_eval.composites.morphology_v073 import describe
    for ax,path,title in zip(axes.flat,paths,titles):
        a=np.load(path)==5;d=describe(a)
        ax.imshow(a,cmap=COLORS,vmin=0,vmax=1,interpolation='nearest');ax.set_xticks([]);ax.set_yticks([])
        ax.set_title(f"{title}\narea-weighted aspect {d['all_observed']['area_weighted_aspect']:.2f}; axial order {d['all_observed']['axial_order']:.2f}",fontsize=9)
    fig.suptitle('Prospective morphology review: actual arrays, identical pixel scale and phase colors',fontsize=13)
    fig.text(.5,.012,'Historical lanes remain accepted in v0.7.2; their new-rule rejection is prospective design-set evidence. No physical scale inferred.',ha='center',fontsize=9)
    fig.tight_layout(rect=(0,.03,1,.96));out=RUN/'figures/MORPHOLOGY_ENVELOPE_REVIEW.png';out.parent.mkdir(exist_ok=True)
    fig.savefig(out,dpi=160);plt.close(fig)
    write(out.with_suffix('.json'),{'selection':'Reference, first two calibration seeds, first historical heldout seed and first development seed, fixed independently of mechanics',
        'source_arrays':{str(p):sha(p) for p in paths},'figure_sha256':sha(out)})

if __name__=='__main__':review()
