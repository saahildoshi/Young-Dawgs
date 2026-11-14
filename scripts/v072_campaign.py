"""Execute only the prospectively selected, structurally feasible native cases."""
import argparse
from scripts.v070_protocol import read,write
from scripts.v072_experiment import RUN,TRIALS,now
from scripts.v072_mechanics import perform


def campaign(level):
    freeze=RUN/'frozen_scripts/ALL_OPTIMIZATION_SCRIPTS_FROZEN.json';assert freeze.exists()
    seeds=read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['heldout' if level==1 else 'H2']
    inventory=[]
    for trial in ['BASE']+TRIALS:
        summary=read(RUN/'heldout_structures'/trial/'SUMMARY.json');assert summary['attempted']==10
        for seed in seeds:
            row=read(RUN/'heldout_structures'/trial/f'seed_{seed}.json')
            if not row['feasibility']['passed']:
                inventory.append({'trial_id':trial,'seed':seed,'mesh_level':level,'status':'NOT_SOLVED_STRUCTURALLY_INFEASIBLE',
                    'apparent_modulus_MPa':None,'failures':row['feasibility']['failures']})
                continue
            try:
                result=perform(trial,'heldout',seed,level)
                inventory.append({'trial_id':trial,'seed':seed,'mesh_level':level,'status':'ACCEPTED_NATIVE_RESULT',
                    'apparent_modulus_MPa':result['effective_modulus_MPa'],'native_RST_sha256':result['native_result_sha256']})
            except Exception as e:
                inventory.append({'trial_id':trial,'seed':seed,'mesh_level':level,'status':'MECHANICAL_EXECUTION_OR_ACCEPTANCE_FAILED',
                    'apparent_modulus_MPa':None,'error':repr(e)})
                # Preserve failure, continue other registered designs; no replacement seed or automatic retry.
                print('MECHANICAL FAILURE',trial,seed,level,repr(e),flush=True)
            write(RUN/f'heldout_mechanics_h{level}/PROGRESS.json',{'updated_utc':now(),'cases':inventory})
    write(RUN/f'heldout_mechanics_h{level}/CAMPAIGN.json',{'completed_utc':now(),'cases':inventory,
        'planned_cases':len(seeds)*5,'accepted':sum(r['status']=='ACCEPTED_NATIVE_RESULT' for r in inventory),
        'invalid_designs_not_scored':True,'no_retry_or_seed_substitution':True})


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('level',type=int,choices=[1,2]);a=p.parse_args();campaign(a.level)
