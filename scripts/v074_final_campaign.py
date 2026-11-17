"""Run the registered final cohort serially, without retries or substitutions."""
import argparse
from scripts.v070_protocol import read, write, sha
from scripts.v074_experiment import RUN, REPO, now
from scripts.v074_trials import evaluate
from scripts.v074_mechanics import campaign


def run(stage):
    frozen = RUN / 'frozen_scripts/ALL_SIXTEEN_SCRIPTS_FROZEN.json'
    record = read(frozen)
    assert record['registered_initial_and_revision_sources'] == 16
    assert record['adapter_sha256'] == sha(REPO / 'scripts/v074_mechanics.py')
    protocol = read(RUN / 'protocol/PROTOCOL.json')
    seeds = read(RUN / 'protocol/EVALUATOR_ONLY_SEEDS.json')
    for trial in protocol['trial_order']:
        for revision in (0, 1):
            directory = RUN / 'structures' / trial / f'r{revision}' / 'heldout'
            if stage == 'generation':
                if directory.exists():
                    summary = read(directory / 'SUMMARY.json')
                    assert [r['seed'] for r in summary['rows']] == seeds['heldout']
                    print('PRESERVED completed generation', trial, revision, flush=True)
                else:
                    evaluate(trial, revision, 'heldout')
            else:
                # A completed campaign is never rerun. An interrupted partial
                # campaign requires an explicit evidence review, not a retry.
                for k in (1, 2):
                    path = RUN / 'mechanical_campaigns' / f'{trial}_r{revision}_heldout_H{k}.json'
                    expected = seeds['heldout' if k == 1 else 'H2']
                    if path.exists():
                        cases = read(path)['cases']
                        assert [r['seed'] for r in cases] == expected, 'Partial campaign: inspect before resuming'
                        print('PRESERVED completed mechanics', trial, revision, k, flush=True)
                    else:
                        campaign(trial, revision, 'heldout', k)
            write(RUN / 'performance' / f'FINAL_{stage.upper()}_PROGRESS.json', {
                'updated_utc': now(), 'last_completed_trial': trial,
                'last_completed_revision': revision, 'stage': stage,
                'collective_freeze_sha256': sha(frozen),
                'serial_native_execution': True,
                'no_retries_repairs_substitutions_or_new_model_calls': True,
            })
    write(RUN / 'performance' / f'FINAL_{stage.upper()}_COMPLETE.json', {
        'completed_utc': now(), 'collective_freeze_sha256': sha(frozen),
        'registered_scripts': 16, 'independent_conversations': 8,
        'stage': stage, 'all_registered_cases_accounted_for': True,
    })


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['generation', 'mechanics'])
    run(parser.parse_args().stage)
