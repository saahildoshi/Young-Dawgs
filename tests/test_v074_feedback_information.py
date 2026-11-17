"""Scientific intervention checks on frozen packets, without any model call."""
import pytest
from scripts.v070_protocol import read,sha
from scripts.v074_experiment import RUN,PREV


@pytest.mark.parametrize('trial',['NF_01','NF_02','NF_03','NF_04'])
def test_NF_packet_withholds_actual_mechanical_measurements(trial):
    d=RUN/'llm_trials'/trial;packet=read(d/'FOLLOWUP_PACKET_FROZEN.json')
    text=(d/'followup_prompt.txt').read_text()
    assert sha(d/'followup_prompt.txt')==packet['prompt_sha256']
    assert not packet['measured_mechanics_in_prompt'] and packet['mechanical_feedback'] is None
    assert 'actual_curve_strain_stress_MPa' not in text
    assert 'apparent_modulus_MPa' not in text and 'native_RST_sha256' not in text
    assert 'mean_absolute_relative_target_error' not in text
    for row in read(RUN/'mechanical_campaigns'/f'{trial}_r0_development_H1.json')['cases']:
        assert str(row['apparent_modulus_MPa']) not in text


@pytest.mark.parametrize('trial',['IF_01','IF_02','IF_03','IF_04'])
def test_IF_packet_curves_are_actual_private_and_historical_native_results(trial):
    d=RUN/'llm_trials'/trial;packet=read(d/'FOLLOWUP_PACKET_FROZEN.json')
    text=(d/'followup_prompt.txt').read_text();assert sha(d/'followup_prompt.txt')==packet['prompt_sha256']
    measured=packet['mechanical_feedback']
    assert [len(measured[k]) for k in ['own_initial','historical_controlled_H1','historical_controlled_H2']]==[3,17,5]
    for key,root in [('own_initial',RUN),('historical_controlled_H1',PREV),('historical_controlled_H2',PREV)]:
        for row in measured[key]:
            name=f'{trial}_r0_development_{row["seed"]}' if key=='own_initial' else f'{row["family"]}_development_{row["seed"]}'
            result=read(root/'mechanical_response'/f'{name}_H{row["mesh_level"]}_attempt001.json')
            assert row['native_RST_sha256']==result['native_result_sha256']
            assert row['apparent_modulus_MPa']==result['effective_modulus_MPa']
            assert row['actual_curve_strain_stress_MPa']==[list(pair) for pair in zip(result['engineering_strains'],result['nominal_stresses_MPa'])]
            assert str(row['apparent_modulus_MPa']) in text


def test_conditions_share_historical_geometry_policy_and_do_not_disclose_heldout():
    packets=[read(RUN/'llm_trials'/t/'FOLLOWUP_PACKET_FROZEN.json') for t in ['NF_01','IF_01']]
    assert packets[0]['geometry']['previous_controlled_geometry']==packets[1]['geometry']['previous_controlled_geometry']
    for t,packet in zip(['NF_01','IF_01'],packets):
        assert packet['complete_morphology_policy_sha256']==sha(RUN/'protocol/FEASIBILITY_FROZEN.json')
        assert packet['same_chat_url']==read(RUN/'llm_trials'/t/'SUBMISSION_r0.json')['chat_url']
        assert packet['heldout_excluded'] and packet['mask_excluded'] and packet['initial_code_not_reattached']
        assert packet['geometry']['own_initial_source_sha256']==sha(RUN/'llm_trials'/t/'generator_r0.py')
        text=(RUN/'llm_trials'/t/'followup_prompt.txt').read_text()
        assert not any(f'"seed":{s}' in text for s in range(5000,5006))
