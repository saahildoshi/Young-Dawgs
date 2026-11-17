"""Versioned P3 adapter to the unchanged native five-checkpoint evaluator."""
import argparse
import importlib.util
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v074_experiment import RUN,BASE,DOC,PREV,now
from metamaterial_eval.simulation.composite_elastic import structured_mesh


def engine():
    for name,digest in read(RUN/'audit/QUALIFIED_EVALUATOR.json').items():
        assert sha(REPO/name)==digest
    spec=importlib.util.spec_from_file_location('v074_unchanged_native_engine',REPO/'scripts/v071_mechanics.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.RUN,m.BASE,m.DOC=RUN,BASE,DOC
    def model(name,k=1):
        r=read(RUN/'specimen_manifests'/f'{name}.json');path=REPO/r['source_array_path']
        assert sha(path)==r['source_array_sha256'] and r['structural_feasibility']['passed']
        a=np.load(path,allow_pickle=False);assert int((a==5).sum())==20731
        properties={int(key):v for key,v in read(RUN/'protocol/PROTOCOL.json')['material']['materials'].items()}
        return structured_mesh(a,k),properties,None
    m.model=model
    return m


def perform(name,k):
    previous=RUN/'mechanical_response'/f'{name}_H{k}_attempt001.json'
    if previous.exists():return read(previous)
    assert sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())<read(RUN/'protocol/PROTOCOL.json')['resource_limits']['raw_storage_budget_bytes']
    m=engine();source=m.prepare(name,k)
    assert not (source/'EXECUTION.json').exists(),'Native attempt cannot be repeated'
    assert m.execute(source),'Native solve failed; no retry'
    post=m.readback(source);assert post is not None,'Independent readback failed'
    result=m.qualify(source,post)
    assert result['accepted'],[key for key,value in result['checks'].items() if not value]
    delta=abs(result['secant_modulus_MPa']-result['effective_modulus_MPa'])/result['effective_modulus_MPa']
    assert delta<=1e-5
    write(RUN/'native_result_manifests'/source.name/'SECANT_CONFIRMATION.json',{'actual_five_native_checkpoints':True,'relative_secant_fit_difference':delta,'passed':True})
    return result


def campaign(trial,revision,partition,k):
    directory=RUN/'structures'/trial/f'r{revision}'/partition
    rows=read(directory/'SUMMARY.json')['rows']
    if k==2:
        selected=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['H2']
        rows=[r for r in rows if r['seed'] in selected]
    results=[]
    for row in rows:
        seed=row['seed'];name=f'{trial}_r{revision}_{partition}_{seed}'
        record={'trial_id':trial,'revision':revision,'partition':partition,'seed':seed,'mesh_level':k,
            'structural_feasible':row['feasibility']['passed'],'structural_failures':row['feasibility']['failures'],
            'apparent_modulus_MPa':None}
        if not row['feasibility']['passed']:
            record['status']='NOT_SOLVED_STRUCTURALLY_INFEASIBLE'
        else:
            source=directory/f'seed_{seed}.npy';manifest=RUN/'specimen_manifests'/f'{name}.json'
            if not manifest.exists():write(manifest,{'specimen_id':name,'trial_id':trial,'revision':revision,'partition':partition,'seed':seed,
                'source_array_path':str(source.relative_to(REPO)).replace('\\','/'),'source_array_sha256':sha(source),
                'generator_sha256':row['generator_sha256'],'structural_feasibility':row['feasibility']})
            try:
                result=perform(name,k)
                record.update(status='ACCEPTED_NATIVE_RESULT' if result['accepted'] else 'NATIVE_ACCEPTANCE_FAILED',
                    apparent_modulus_MPa=result['effective_modulus_MPa'] if result['accepted'] else None,
                    native_RST_sha256=result['native_result_sha256'])
            except Exception as error:
                record.update(status='MECHANICAL_EXECUTION_OR_ACCEPTANCE_FAILED',error=repr(error))
        results.append(record)
        write(RUN/'mechanical_campaigns'/f'{trial}_r{revision}_{partition}_H{k}.json',{'updated_utc':now(),'cases':results,'planned':len(rows),'no_retries_or_substitutions':True})
        print(record,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trial');p.add_argument('revision',type=int);p.add_argument('partition');p.add_argument('k',type=int);a=p.parse_args()
    campaign(a.trial,a.revision,a.partition,a.k)
