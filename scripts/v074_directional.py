"""Three fixed historical sources: reused y results and new equivalent x loading."""
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v074_experiment import RUN,PREV,now
from scripts.v074_mechanics import perform


def run():
    records=[]
    for family in ['BASE','V2_VERTICAL','V3_HORIZONTAL']:
        old=PREV/'controlled_variants'/family/'seed_3100.npy'
        original=np.load(old,allow_pickle=False);assert int((original==5).sum())==20731
        oldrow=read(old.with_suffix('.json'));assert oldrow['feasibility']['passed']
        # One exact array rotation reorients the computational loading. No
        # interpolation, smoothing, resizing, phase edits or new generation.
        rotated=np.rot90(original,1).copy();name=f'DIRECTIONAL_{family}_seed3100_EX'
        array=RUN/'directional'/f'{name}.npy'
        if not array.exists():
            array.parent.mkdir(parents=True,exist_ok=True);np.save(array,rotated,allow_pickle=False)
        assert np.array_equal(np.load(array),rotated)
        manifest=RUN/'specimen_manifests'/f'{name}.json'
        if not manifest.exists():write(manifest,{'specimen_id':name,'source_array_path':str(array.relative_to(REPO)).replace('\\','/'),
            'source_array_sha256':sha(array),'original_array_path':str(old.relative_to(REPO)).replace('\\','/'),
            'original_array_sha256':sha(old),'structural_feasibility':oldrow['feasibility'],
            'rotation':'np.rot90(a,1), physical+x_prime=1-y and+y_prime=x; exact permutation, no new generator or morphology modification',
            'feasibility_scope':'Original specimen passed frozen morphology; rotated loading is secondary diagnostic, not a newly selected inverse-design candidate',
            'loading':'New vertical compression maps to original horizontal compression; one transverse pin removes rigid translation. Equivalent finite square boundary conventions.'})
        ypath=PREV/'mechanical_response'/f'{family}_development_3100_H1_attempt001.json'
        y=read(ypath);assert y['accepted']
        # Authenticate critical old artifacts without executing the old solve.
        from pathlib import Path
        assert sha(Path(y['source_directory'])/'elastic.rst')==y['native_result_sha256']
        x=perform(name,1)
        records.append({'family':family,'seed':3100,'source_sha256':sha(old),'rotated_source_sha256':sha(array),
            'source_phase_counts':{str(v):int((original==v).sum()) for v in [1,5]},
            'E_y_MPa':y['effective_modulus_MPa'],'E_x_MPa':x['effective_modulus_MPa'],
            'directional_ratio_Ey_over_Ex':y['effective_modulus_MPa']/x['effective_modulus_MPa'],
            'vertical_result_reused':True,'vertical_result_manifest_sha256':sha(ypath),
            'native_y_RST_sha256':y['native_result_sha256'],'native_x_RST_sha256':x['native_result_sha256'],
            'not_complete_homogenized_tensor':True})
        write(RUN/'directional/RESULTS.json',{'updated_utc':now(),'cases':records,'new_source_solves':len(records),'reused_vertical_solves':len(records),
            'interpretation':'Apparent finite-domain x/y response under equivalent boundary conventions; not isotropic effective properties or an RVE tensor'})
        print(records[-1],flush=True)


def report():
    import csv
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    rows=read(RUN/'directional/RESULTS.json')['cases'];assert len(rows)==3
    with (RUN/'directional/PAIRED_DIRECTIONAL.csv').open('w',encoding='utf-8',newline='') as f:
        keys=['family','seed','E_y_MPa','E_x_MPa','directional_ratio_Ey_over_Ex','source_sha256','rotated_source_sha256','native_y_RST_sha256','native_x_RST_sha256']
        writer=csv.DictWriter(f,keys,extrasaction='ignore',lineterminator='\n');writer.writeheader();writer.writerows(rows)
    fig,axes=plt.subplots(2,3,figsize=(12,7))
    for i,row in enumerate(rows):
        a=np.load(PREV/'controlled_variants'/row['family']/'seed_3100.npy')
        axes[0,i].imshow(a==5,cmap=ListedColormap(['#29465c','#e1a944']),interpolation='nearest')
        axes[0,i].set_title(f'{row["family"]} · seed3100');axes[0,i].set_xticks([]);axes[0,i].set_yticks([])
        axes[1,i].bar(['E_x new','E_y reused'],[row['E_x_MPa'],row['E_y_MPa']],color=['#3a8792','#bd8c34'])
        axes[1,i].set(ylim=(0,1900),ylabel='Apparent modulus (MPa)',title=f'E_y/E_x = {row["directional_ratio_Ey_over_Ex"]:.4f}')
    fig.suptitle('Actual paired finite-domain directional response · H1 / illustrative materials / no homogenized tensor')
    fig.tight_layout(rect=(0,0,1,.95));fig.savefig(RUN/'directional/DIRECTIONAL_GEOMETRY_AND_MODULI.png',dpi=170);plt.close(fig)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--report-only',action='store_true');a=p.parse_args()
    if not a.report_only:run()
    report()
