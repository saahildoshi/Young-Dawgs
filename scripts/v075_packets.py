"""Build matched revision prompts from frozen assignment and genuine measurements."""
import json
from statistics import mean, stdev

from scripts.v070_protocol import read, sha, write
from scripts.v074_packets import structural
from scripts.v075_design import target_error
from scripts.v075_protocol import RUN, TRIALS, V074, now
from scripts.v075_trials import ASSIGNMENT

STRUCTURAL_MARKER = '\n\nSTRUCTURAL DEVELOPMENT INFORMATION'
MEASURED_MARKER = '\n\nACTUAL LICENSED ANSYS DEVELOPMENT MEASUREMENTS:\n'


def compose(common, geometry, measured=None):
    message = common + STRUCTURAL_MARKER + ':\n' + json.dumps(geometry, sort_keys=True, separators=(',', ':'))
    if measured is None:
        return message + '\n\nUse the unchanged physical assumptions and the structural evidence to make the single revision.\n'
    return message + MEASURED_MARKER + json.dumps(measured, sort_keys=True, separators=(',', ':')) + (
        '\nUse the measured information to make the single revision. Historical variants are researcher-controlled probes. '
        'Their observed associations do not isolate a single causal descriptor.\n')


def prepare():
    assignment = read(ASSIGNMENT)
    assert sha(RUN / 'assignment/PRETREATMENT_FROZEN.json') == assignment['pretreatment_sha256']
    baseline = {r['trial_id']: r for r in read(RUN / 'assignment/PRETREATMENT_FROZEN.json')}
    prior_dir = V074 / 'llm_trials/IF_01'
    historical = read(prior_dir / 'FOLLOWUP_PACKET_FROZEN.json')
    prior_prompt = prior_dir / 'followup_prompt.txt'
    assert sha(prior_prompt) == historical['prompt_sha256']
    common = prior_prompt.read_text(encoding='utf-8').split(STRUCTURAL_MARKER, 1)[0]
    common = common.replace('We executed that exact captured module on the three registered development seeds before this continuation.',
        'We evaluated the exact captured response on the three registered development attempts before this continuation.')
    policy = read(RUN / 'protocol/FEASIBILITY_FROZEN.json')
    heldout = read(RUN / 'protocol/EVALUATOR_ONLY_SEEDS.json')['heldout']
    packets = []
    for trial in TRIALS:
        d = RUN / 'llm_trials' / trial
        receipt = read(d / 'RECEIPT_r0.json')
        structural_path = RUN / 'structures' / trial / 'r0/development/SUMMARY.json'
        campaign_path = RUN / 'mechanical_campaigns' / f'{trial}_r0_development_H1.json'
        assert sha(structural_path) == baseline[trial]['structural_summary_sha256']
        assert sha(campaign_path) == baseline[trial]['native_campaign_sha256']
        s = read(structural_path)
        development = [structural(r, policy) for r in s['rows']]
        for row in development:
            # Record the real exception privately. Send a consistent failure category.
            row['error'] = 'Development construction or execution failed' if row['error'] is not None else None
        geometry = {k: v for k, v in historical['geometry'].items() if k.startswith('previous_') or k == 'historical_caution'}
        geometry.update(development_structures=development, own_development_diversity=s['diversity'])
        arm = assignment['arms'][trial]
        measured = None
        if arm == 'IF':
            own = []
            for case in read(campaign_path)['cases']:
                response = {'seed': case['seed'], 'status': case['status'], 'apparent_modulus_MPa': None}
                if case['status'] == 'ACCEPTED_NATIVE_RESULT':
                    result = read(RUN / 'mechanical_response' / f'{trial}_r0_development_{case["seed"]}_H1_attempt001.json')
                    assert result['accepted'] and result['native_result_sha256'] == case['native_RST_sha256']
                    response.update(apparent_modulus_MPa=result['effective_modulus_MPa'],
                        absolute_relative_target_error=target_error(result['effective_modulus_MPa']),
                        actual_curve_strain_stress_MPa=list(zip(result['engineering_strains'], result['nominal_stresses_MPa'])),
                        native_RST_sha256=result['native_result_sha256'])
                own.append(response)
            values = [r['apparent_modulus_MPa'] for r in own if r['apparent_modulus_MPa'] is not None]
            measured = {k: historical['mechanical_feedback'][k] for k in (
                'historical_controlled_H1', 'historical_controlled_H2')}
            measured.update(own_initial=own, own_summary={'attempted': 3, 'accepted': len(values),
                'mean_modulus_MPa': mean(values) if values else None,
                'sample_SD_MPa': stdev(values) if len(values) > 1 else None,
                'mean_absolute_relative_target_error': mean(map(target_error, values)) if values else None})
            if not values:
                measured['own_measurements_status'] = 'No accepted development mechanical results for this script.'
        prompt = compose(common, geometry, measured)
        assert all(f'"seed":{s}' not in prompt for s in heldout)
        destination = d / 'followup_prompt.txt'
        assert not destination.exists() and not (d / 'SUBMISSION_r1.json').exists()
        packets.append((d, prompt, {'trial_id': trial, 'arm': arm,
            'original_chat_url': receipt['chat_url'], 'initial_code_sha256': receipt['code_sha256'],
            'assignment_sha256': sha(ASSIGNMENT), 'prompt_characters': len(prompt),
            'includes_measured_mechanics': measured is not None,
            'historical_packet_sha256': sha(prior_dir / 'FOLLOWUP_PACKET_FROZEN.json'),
            'structural_information': geometry, 'measured_mechanics': measured}))
    for d, prompt, metadata in packets:
        path = d / 'followup_prompt.txt'
        path.write_text(prompt, encoding='utf-8', newline='\n')
        write(d / 'FOLLOWUP_PACKET_FROZEN.json', {**metadata, 'frozen_utc': now(), 'prompt_sha256': sha(path)})


if __name__ == '__main__':
    prepare()
