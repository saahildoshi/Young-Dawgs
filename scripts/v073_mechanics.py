"""Use the unchanged licensed evaluator on frozen v073 feasible geometries."""
import argparse
import importlib.util
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v073_experiment import RUN,BASE,DOC,now
from metamaterial_eval.simulation.composite_elastic import structured_mesh

def engine():
    for name,digest in read(RUN/'audit/QUALIFIED_EVALUATOR.json').items():assert sha(REPO/name)==digest
    spec=importlib.util.spec_from_file_location('v073_unchanged_native_engine',REPO/'scripts/v071_mechanics.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.RUN,m.BASE,m.DOC=RUN,BASE,DOC
    def model(specimen,k=1):
        r=read(RUN/'specimen_manifests'/f'{specimen}.json');path=REPO/r['source_array_path']
        assert sha(path)==r['source_array_sha256'] and r['structural_feasibility']['passed']
        a=np.load(path,allow_pickle=False);assert int((a==5).sum())==20731
        properties={int(key):v for key,v in read(RUN/'protocol/PROTOCOL.json')['material']['materials'].items()}
        return structured_mesh(a,k),properties,None
    m.model=model;return m

def perform(trial,partition,seed,k):
    directory=RUN/('controlled_variants' if partition=='development' else 'heldout_structural_evaluation')/trial
    row=read(directory/f'seed_{seed}.json');assert row['feasibility']['passed']
    assert row['phase_counts']['5']==20731
    if partition!='development':assert (RUN/'frozen_scripts/ALL_V073_INVERSE_DESIGN_SCRIPTS_FROZEN.json').exists()
    name=f'{trial}_{partition}_{seed}';source_path=directory/f'seed_{seed}.npy'
    manifest=RUN/'specimen_manifests'/f'{name}.json'
    if not manifest.exists():write(manifest,{'specimen_id':name,'trial_id':trial,'partition':partition,'seed':seed,
        'source_array_path':str(source_path.relative_to(REPO)).replace('\\','/'),'source_array_sha256':sha(source_path),
        'generator_sha256':row['generator_sha256'],'phase_counts':row['phase_counts'],'structural_feasibility':row['feasibility']})
    result_path=RUN/'mechanical_response'/f'{name}_H{k}_attempt001.json'
    if result_path.exists():
        r=read(result_path);assert r['accepted'];return r
    assert sum(p.stat().st_size for p in BASE.rglob('*') if p.is_file())<read(RUN/'protocol/PROTOCOL.json')['resource_limits']['raw_storage_budget_bytes']
    m=engine();source=m.prepare(name,k)
    assert m.execute(source),'Native source failed; preserved without retry'
    post=m.readback(source);assert post is not None,'Native readback failed'
    r=m.qualify(source,post);assert r['accepted'],[key for key,value in r['checks'].items() if not value]
    delta=abs(r['secant_modulus_MPa']-r['effective_modulus_MPa'])/r['effective_modulus_MPa']
    assert delta<=read(RUN/'protocol/PROTOCOL.json')['secant_confirmation_relative_tolerance']
    write(RUN/'native_result_manifests'/source.name/'SECANT_CONFIRMATION.json',
        {'actual_five_native_checkpoints':True,'relative_secant_fit_difference':delta,'passed':True})
    return r

def campaign(partition,level):
    if partition=='development':
        frozen=read(RUN/'controlled_variants/GEOMETRY_DATASET_FROZEN.json')
        assert sha(RUN/'protocol/FEASIBILITY_FROZEN.json')==frozen['feasibility_sha256']
        planned=frozen['rows']
        if level==2:planned=[r for r in planned if r['seed']==read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['development'][0]]
    else:
        from scripts.v073_experiment import TRIALS
        assert (RUN/'frozen_scripts/ALL_V073_INVERSE_DESIGN_SCRIPTS_FROZEN.json').exists()
        seeds=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['heldout' if level==1 else 'H2']
        planned=[{**read(RUN/'heldout_structural_evaluation'/t/f'seed_{s}.json'),'trial_id':t} for t in ['BASE']+TRIALS for s in seeds]
    results=[];destination=RUN/f'{partition}_mechanics_h{level}'
    for row in planned:
        trial,seed=row['trial_id'],row['seed']
        record={'trial_id':trial,'seed':seed,'mesh_level':level,'structural_feasible':row['feasibility']['passed'],
            'structural_failures':row['feasibility']['failures'],'apparent_modulus_MPa':None}
        if not row['feasibility']['passed']:record['status']='NOT_SOLVED_STRUCTURALLY_INFEASIBLE'
        else:
            try:
                r=perform(trial,partition,seed,level)
                record.update(status='ACCEPTED_NATIVE_RESULT',apparent_modulus_MPa=r['effective_modulus_MPa'],native_RST_sha256=r['native_result_sha256'])
            except Exception as error:
                record.update(status='MECHANICAL_EXECUTION_OR_ACCEPTANCE_FAILED',error=repr(error));print('FAILURE',record,flush=True)
        results.append(record);write(destination/'PROGRESS.json',{'updated_utc':now(),'cases':results})
    write(destination/'CAMPAIGN.json',{'completed_utc':now(),'cases':results,'planned':len(planned),
        'accepted':sum(r['status']=='ACCEPTED_NATIVE_RESULT' for r in results),'no_retries_or_substitutions':True})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('partition',choices=['development','heldout']);p.add_argument('level',type=int,choices=[1,2]);a=p.parse_args();campaign(a.partition,a.level)
