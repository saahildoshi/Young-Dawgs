"""Prepare explicit researcher count adaptation and morphology calibration evidence."""
import argparse
import importlib.util
import time
import numpy as np
from PIL import Image
from scripts.v070_protocol import REPO, read, write, sha
from scripts.v072_experiment import observe, diversity
from scripts.v073_experiment import RUN, DOC, PREV, REFERENCE, now
from metamaterial_eval.composites.morphology_v073 import describe, flattened

EXACT_HELPER='''

def _exact_count(canvas, rng):
    """Bounded topology-preserving small boundary adjustment inside the generator.

    Researcher adaptation, not an unedited LLM response. Every changed site adjoins
    an existing region. Connected foreground/background in the local3x3 exclude
    bridges, splits and isolated additions. Interior sites only; finite edges stay.
    Random ranking is isotropic. No evaluator or mechanical outcome is consulted.
    """
    target=20731
    delta=target-int(canvas.sum())
    if abs(delta)>2048: raise RuntimeError('Count correction exceeds registered bound')
    if delta==0:return canvas
    adding=delta>0
    boundary=(ndi.binary_dilation(canvas)&~canvas) if adding else (canvas&~ndi.binary_erosion(canvas))
    boundary[[0,-1],:]=False;boundary[:,[0,-1]]=False
    sites=np.argwhere(boundary);rng.shuffle(sites)
    remaining=abs(delta)
    # A single bounded pass, at most256^2 sites; no full-domain candidate search.
    for y,x in sites:
        patch=canvas[y-1:y+2,x-1:x+2].copy()
        patch[1,1]=adding
        neighbours=int(patch[0,1])+int(patch[2,1])+int(patch[1,0])+int(patch[1,2])
        if not 2<=neighbours<=3:continue
        if ndi.label(patch)[1]!=1 or ndi.label(~patch)[1]!=1:continue
        canvas[y,x]=adding;remaining-=1
        if remaining==0:break
    if remaining:raise RuntimeError('Bounded topology-safe count calibration exhausted')
    return canvas
'''

def module(path):
    spec=importlib.util.spec_from_file_location('v073_'+sha(path)[:12],path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def save_array(path,a):
    path.parent.mkdir(parents=True,exist_ok=True);np.save(path,a,allow_pickle=False)
    Image.fromarray(np.where((a==5)[...,None],np.array([235,170,55]),np.array([45,70,100])).astype(np.uint8)).save(path.with_suffix('.png'))

def generate(source,seed,path,parameters=None):
    m=module(source);t=time.perf_counter();a=m.generate_microstructure(seed,parameters or {});elapsed=time.perf_counter()-t
    b=m.generate_microstructure(seed,parameters or {})
    valid=isinstance(a,np.ndarray) and a.shape==(256,256) and a.dtype==np.uint8 and set(np.unique(a))=={1,5}
    if not valid:raise ValueError('Output contract violation')
    save_array(path,a)
    row={'seed':seed,'generator_sha256':sha(source),'parameters':parameters or {},'status':'GENERATED','generation_seconds':elapsed,
        'deterministic':bool(np.array_equal(a,b)),'source_array_sha256':sha(path),**observe(a),'morphology_v073':describe(a==5)}
    write(path.with_suffix('.json'),row);return row

def prepare():
    source=PREV/'starting_generator/generator.py';original=module(source)
    seeds=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['calibration']
    counts={str(seed):int((original.generate_microstructure(seed,{})==5).sum()) for seed in seeds}
    destination=RUN/'starting_generator/generator.py';assert not destination.exists()
    destination.parent.mkdir(exist_ok=True)
    code=source.read_text(encoding='utf-8')
    adapted=not all(v==20731 for v in counts.values())
    if adapted:
        code=code.replace('    return np.where(canvas, 5, 1).astype(np.uint8)',
                          '    canvas = _exact_count(canvas, rng)\n    return np.where(canvas, 5, 1).astype(np.uint8)')+EXACT_HELPER
    destination.write_text(code,encoding='utf-8',newline='\n')
    write(destination.parent/'AUTHENTICATION.json',{'identity':'P3_B02_EXACT_COMPOSITION_RESEARCHER_ADAPTATION_V073' if adapted else 'P3_B_02/r0',
        'original_source':str(source.relative_to(REPO)),'original_sha256':sha(source),'adapted_sha256':sha(destination),
        'researcher_adapted':adapted,'original_calibration_counts':counts,'adaptation':'Only internal bounded small topology-safe boundary count adjustment; original polygon/placement strategy unchanged',
        'not_independent_LLM_trial':True,'no_historical_source_edits':True})
    rows=[generate(destination,seed,RUN/'envelope_calibration'/f'seed_{seed}.npy') for seed in seeds]
    assert all(r['phase_counts']['5']==20731 and r['deterministic'] for r in rows)
    policy=read(RUN/'protocol/PROTOCOL.json')
    arrays=[np.load(RUN/'envelope_calibration'/f'seed_{seed}.npy') for seed in seeds]
    div=diversity(arrays,policy);assert div['passed']
    write(RUN/'envelope_calibration/SUMMARY.json',{'rows':rows,'diversity':div})
    reference=np.load(REFERENCE);write(RUN/'envelope_calibration/REFERENCE.json',{'source_sha256':sha(REFERENCE),**observe(reference),'morphology_v073':describe(reference==5)})
    challenge=[]
    for trial in ['BASE','P3_OPT_MF_01','P3_OPT_MF_02','P3_OPT_NF_01','P3_OPT_NF_02']:
        for path in sorted((PREV/'heldout_structures'/trial).glob('seed_*.npy')):
            a=np.load(path);challenge.append({'trial_id':trial,'source_path':str(path.relative_to(REPO)),'source_sha256':sha(path),'morphology_v073':describe(a==5)})
    assert len(challenge)==50
    write(RUN/'historical_lane_controls/OBSERVATIONS.json',challenge)
    table={key:[flattened(r['morphology_v073'])[key] for r in rows] for key in flattened(rows[0]['morphology_v073'])}
    write(RUN/'envelope_calibration/NUMERIC_RANGES.json',{key:{'reference':flattened(read(RUN/'envelope_calibration/REFERENCE.json')['morphology_v073'])[key],
        'baseline_min':min(v for v in values if v is not None) if any(v is not None for v in values) else None,
        'baseline_max':max(v for v in values if v is not None) if any(v is not None for v in values) else None} for key,values in table.items()})
    print('EXACT BASELINE',len(rows),'all exact; source',sha(destination),'diversity',div['passed'],flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare']);a=p.parse_args();prepare()
