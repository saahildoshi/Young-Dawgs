"""Reuse the unchanged v0.7.1 solver, extraction and qualification on new specimens."""
import argparse
import hashlib
import importlib.util
import shutil
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v072_experiment import RUN,BASE,DOC
from metamaterial_eval.simulation.composite_elastic import structured_mesh


def inherited():
    identity=read(RUN/'audit/QUALIFIED_EVALUATOR.json')
    for name,digest in identity.items():
        assert sha(REPO/name)==digest, name
    old=REPO/'experiments/pipeline_v0.7.1/run_001'
    for name in ['M0_matrix_H1_attempt001','M1_parallel_H1_attempt001','M1_series_H1_attempt001','M1_equal_H1_attempt002']:
        assert read(old/'mechanical_response'/f'{name}.json')['accepted']
    spec=importlib.util.spec_from_file_location('v072_unchanged_qualified_mechanics',REPO/'scripts/v071_mechanics.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.RUN,module.BASE,module.DOC=RUN,BASE,DOC
    def model(specimen,k=1):
        record=read(RUN/'specimen_manifests'/f'{specimen}.json')
        path=REPO/record['source_array_path'];assert sha(path)==record['source_array_sha256']
        labels=np.load(path,allow_pickle=False)
        assert record['structural_feasibility']['passed']
        properties={int(key):value for key,value in read(RUN/'protocol/PROTOCOL.json')['material']['materials'].items()}
        return structured_mesh(labels,k),properties,None
    module.model=model
    return module


def specimen(trial,partition,seed):
    if partition=='development':source=RUN/'baseline_development'
    else:source=RUN/'heldout_structures'/trial
    row=read(source/f'seed_{seed}.json')
    assert row['feasibility']['passed'],row['feasibility']
    name=f'{trial}_{partition}_{seed}'
    path=source/f'seed_{seed}.npy'
    out=RUN/'specimen_manifests'/f'{name}.json'
    if not out.exists():
        write(out,{'specimen_id':name,'trial_id':trial,'seed_partition':partition,'seed':seed,
            'source_array_path':str(path.relative_to(REPO)).replace('\\','/'),'source_array_sha256':sha(path),
            'generator_sha256':row['generator_sha256'],'phase_counts':row['phase_counts'],
            'structural_feasibility':row['feasibility'],'morphology_descriptors':row['descriptors']})
    return name


def perform(trial,partition,seed,k=1):
    assert (RUN/'protocol/FEASIBILITY_FROZEN.json').exists()
    if partition!='development':assert (RUN/'frozen_scripts/ALL_OPTIMIZATION_SCRIPTS_FROZEN.json').exists()
    name=specimen(trial,partition,seed)
    previous=RUN/'mechanical_response'/f'{name}_H{k}_attempt001.json'
    if previous.exists():
        r=read(previous);assert r['accepted'];print('EXISTING ACCEPTED',name,k,flush=True);return r
    assert sum(f.stat().st_size for f in BASE.rglob('*') if f.is_file())<read(RUN/'protocol/PROTOCOL.json')['resource_limits']['raw_storage_budget_bytes']
    engine=inherited();source=engine.prepare(name,k)
    assert engine.execute(source),'Native source process failed; preserved, no automatic replacement'
    post=engine.readback(source);assert post is not None,'Native readback failed'
    r=engine.qualify(source,post)
    assert r['accepted'],[key for key,v in r['checks'].items() if not v]
    difference=abs(r['secant_modulus_MPa']-r['effective_modulus_MPa'])/r['effective_modulus_MPa']
    assert difference<=read(RUN/'protocol/PROTOCOL.json')['secant_confirmation_relative_tolerance']
    write(source/'SECANT_CONFIRMATION.json',{'actual_full_curve':True,'actual_final_point_secant':r['secant_modulus_MPa'],
        'actual_fitted_modulus':r['effective_modulus_MPa'],'relative_difference':difference,'passed':True,
        'one_point_only_native_route_used':False})
    write(RUN/'native_result_manifests'/source.name/'SECANT_CONFIRMATION.json',read(source/'SECANT_CONFIRMATION.json'))
    return r


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trial');p.add_argument('partition');p.add_argument('seeds');p.add_argument('--level',type=int,default=1)
    a=p.parse_args()
    for seed in map(int,a.seeds.split(',')):perform(a.trial,a.partition,seed,a.level)
