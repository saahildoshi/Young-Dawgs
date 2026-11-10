"""Private-to-experimental-model synthetic targets; algorithms are never prompt input."""
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
from scripts.v070_protocol import RUN,write,sha
from metamaterial_eval.composites import describe,validity


def target(family,seed):
    rng=np.random.default_rng(seed);yy,xx=np.mgrid[:256,:256];a=np.zeros((256,256),np.uint8);instances=[]
    wanted=42 if family=='particle' else 18
    for attempt in range(20000):
        cx,cy=rng.uniform(20,236,2)
        if family=='particle':
            radius=rng.uniform(6.5,11);ratio=rng.uniform(1.05,1.6);theta=rng.uniform(0,np.pi)
            x=(xx-cx)*np.cos(theta)+(yy-cy)*np.sin(theta);y=-(xx-cx)*np.sin(theta)+(yy-cy)*np.cos(theta)
            mask=(x/(radius*np.sqrt(ratio)))**2+(y/(radius/np.sqrt(ratio)))**2<=1
        else:
            length=rng.uniform(42,75);width=rng.uniform(4,7);theta=rng.normal(np.deg2rad(25),np.deg2rad(18));bend=rng.uniform(-4,4)
            t=np.linspace(-.5,.5,100);along=length*t;cross=bend*np.sin(2*np.pi*t)
            path=np.c_[cx+along*np.cos(theta)+cross*np.sin(theta),cy-along*np.sin(theta)+cross*np.cos(theta)]
            if path.min()<8 or path.max()>247:continue
            mask=np.zeros_like(a,bool)
            for x,y in path:mask|=(xx-x)**2+(yy-y)**2<=(width/2)**2
        if mask[0].any() or mask[-1].any() or mask[:,0].any() or mask[:,-1].any():continue
        if np.any(mask&ndi.binary_dilation(a,iterations=3)):continue
        a[mask]=1;instances.append({'area_pixels':int(mask.sum())})
        if len(instances)==wanted:break
    if len(instances)!=wanted:raise RuntimeError('Reference placement incomplete')
    return a,instances


def prepare():
    for family,seed in [('particle',73129),('fiber',95413)]:
        a,instances=target(family,seed);assert np.array_equal(a,target(family,seed)[0])
        d=RUN/'references'/family;d.mkdir(exist_ok=False)
        np.save(d/'original.npy',a);np.save(d/'processed.npy',a);Image.fromarray(a*255).save(d/'reference.png')
        descriptors=describe(a,family);assert validity(a,family,descriptors)['passed'];write(d/'descriptors.json',descriptors)
        write(d/'manifest.json',{'reference_id':family+'_synthetic_001','family':family,'kind':'SYNTHETIC_NOT_EXPERIMENTAL','provenance':'Locally authored procedural validation/pilot target',
            'source_code_sha256':sha(__file__),'seed':seed,'original_dimensions':[256,256],'processed_dimensions':[256,256],'phase0':'solid matrix','phase1':'solid reinforcement',
            'segmentation':'None: binary labels are ground truth by construction','preprocessing':'Identity; no resizing,cropping,thresholding or cleanup','original_sha256':sha(d/'original.npy'),
            'processed_sha256':sha(d/'processed.npy'),'image_sha256':sha(d/'reference.png'),'descriptors_sha256':sha(d/'descriptors.json'),'physical_scale':None,
            'license':'Locally authored project research artifact; not an external micrograph','instance_count_ground_truth':len(instances),
            'uncertainty':'Rasterization and component proxies; single synthetic target,not real-material validity','reference_algorithm_shown_to_experimental_model':False})
        print(family,{k:descriptors[k] for k in ['fraction','object_count','matrix_lcc']},flush=True)


if __name__=='__main__':prepare()
