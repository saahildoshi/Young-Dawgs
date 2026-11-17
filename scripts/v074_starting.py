"""Explicit researcher preparation; never counted as an ordinary ChatGPT trial."""
import importlib.util
import inspect
import json
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v074_experiment import RUN,DOC,PREV,now
from scripts.v073_prepare import generate
from scripts.v073_envelope import feasibility
from scripts.v072_experiment import diversity
from metamaterial_eval.composites import morphology_v073 as morph
from metamaterial_eval.composites.descriptors import directional_s2

CHECK='''

def _structural_ok(a):
    if a.shape!=(256,256) or a.dtype!=np.uint8 or set(np.unique(a))!={1,5} or int((a==5).sum())!=20731:return False
    rein=a==5;matrix=topology(~rein,1)
    if matrix['largest_fraction']<.95 or not(matrix['spans_x'] and matrix['spans_y']):return False
    for connectivity in (1,2):
        t=topology(rein,connectivity)
        if t['spans_x'] or t['spans_y'] or t['largest_fraction']>.15:return False
        if connectivity==1 and t['singleton_area_fraction']>.001:return False
    lab,n=ndi.label(rein);regions=regionprops(lab)
    edge=set(np.unique(np.r_[lab[0],lab[-1],lab[:,0],lab[:,-1]]))-{0}
    complete=[r for r in regions if r.label not in edge]
    if not(40<=len(complete)<=75 and 50<=n<=125 and 5<=len(edge)<=50):return False
    diameter=np.mean([r.equivalent_diameter_area for r in complete])
    aspects=[r.axis_major_length/r.axis_minor_length for r in complete if r.axis_minor_length>0]
    if not(12<=diameter<=20 and aspects and 1.2<=np.mean(aspects)<=3):return False
    values=flattened(describe(rein))
    for key,bounds in MORPHOLOGY_BOUNDS.items():
        value=values.get(key)
        if value is None or not bounds[0]<=value<=bounds[1]:return False
    if values['gap_dilation.2.spans_x'] or values['gap_dilation.2.spans_y']:return False
    return True


def generate_microstructure(seed, parameters):
    """At most8 actual geometry candidates from a deterministic local RNG stream."""
    rng=np.random.default_rng(seed)
    for attempt in range(8):
        candidate_seed=int(rng.integers(0,2**63))
        try:a=_generate_candidate(candidate_seed,{})
        except RuntimeError:continue
        if _structural_ok(a):return a
    raise RuntimeError('No feasible candidate within eight registered attempts')
'''

def prepare():
    path=RUN/'starting_generator/generator.py';assert not path.exists()
    inherited=PREV/'starting_generator/generator.py'
    code=inherited.read_text().replace('def generate_microstructure(seed, parameters):','def _generate_candidate(seed, parameters):')
    scientific=morph.__file__;text=open(scientific,encoding='utf-8').read()
    text=text[text.index('LAGS = '):]
    text='\nfrom scipy.spatial.distance import cdist\nfrom skimage.measure import regionprops\n\n'+inspect.getsource(directional_s2)+'\n'+text
    policy=read(RUN/'protocol/FEASIBILITY_FROZEN.json')
    code+='\n'+text+'\nMORPHOLOGY_BOUNDS = '+repr(policy['new_descriptor_bounds'])+'\n'+CHECK
    path.parent.mkdir();path.write_text(code,encoding='utf-8',newline='\n')
    rows=[]
    for seed in read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['common_calibration']:
        try:
            row=generate(path,seed,RUN/'starting_generator/calibration'/f'seed_{seed}.npy')
            row['feasibility']=feasibility(row,policy)
        except Exception as error:row={'seed':seed,'status':'EXECUTION_ERROR','error':repr(error),'feasibility':{'passed':False}}
        write(RUN/'starting_generator/calibration'/f'seed_{seed}.json',row);rows.append(row)
    arrays=[np.load(RUN/'starting_generator/calibration'/f"seed_{r['seed']}.npy") for r in rows if r['status']=='GENERATED']
    d=diversity(arrays,policy) if len(arrays)>1 else {'passed':False}
    write(RUN/'starting_generator/COMMON_STARTING_POINT_FROZEN.json',{'frozen_utc':now(),'identity':'P3_B02_EXACT_BOUNDED_MORPHOLOGY_RESEARCHER_ADAPTATION_V074',
        'original_v073_sha256':sha(inherited),'common_generator_sha256':sha(path),'descriptor_source_sha256':sha(scientific),
        'feasibility_sha256':sha(RUN/'protocol/FEASIBILITY_FROZEN.json'),'maximum_candidates':8,'mechanical_data_access':False,
        'researcher_prepared_not_LLM_trial':True,'rows':rows,'diversity':d,'fully_qualified_calibration':all(r['feasibility']['passed'] for r in rows) and d['passed']})
    print('COMMON CALIBRATION',sum(r['feasibility']['passed'] for r in rows),'/',len(rows),'diversity',d['passed'],'source',sha(path),flush=True)

if __name__=='__main__':prepare()
