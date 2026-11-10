"""Controls for experimental separation and generator restrictions."""
import ast
import numpy as np
import pytest
from scripts.v070_protocol import RUN,REPO,read,sha
from scripts.v070_experiment import audit
from metamaterial_eval.composites import baselines
from metamaterial_eval.composites.diversity import diversity,configuration_signature


@pytest.mark.parametrize('family',['particle','fiber'])
def test_baseline_seed_contract_and_genuine_geometric_variation(family):
    f=getattr(baselines,family);a=f(100,{});b=f(101,{})
    assert a.dtype==np.uint8 and a.shape==(256,256) and set(np.unique(a))=={0,1}
    assert np.array_equal(a,f(100,{})) and not np.array_equal(a,b)
    assert configuration_signature(a)!=configuration_signature(b)


def test_configuration_signature_detects_rigid_translation_without_calling_it_new_geometry():
    a=np.zeros((256,256),np.uint8);a[30:33,30:33]=1;a[60:64,60:64]=1
    b=np.roll(a,10,axis=1);assert configuration_signature(a)==configuration_signature(b)
    assert configuration_signature(a)==configuration_signature(np.rot90(a))
    assert diversity([a,a])['mean_jaccard_distance']==0


def test_missing_diversity_results_are_not_zero_scores():assert diversity([])['unique_hashes'] is None


@pytest.mark.parametrize('bad',['import os\ndef generate_microstructure(seed,parameters): return os.listdir()','import numpy as np\nx=np.random.default_rng(1)\ndef generate_microstructure(seed,parameters): return x.random(2)','def generate_microstructure(seed,parameters):\n return open("target.png")'])
def test_code_audit_rejects_import_time_rng_and_input_output(bad):assert not audit(bad)['passed']


def test_seed_partitions_and_condition_fairness_are_frozen():
    p=read(RUN/'protocol/PROTOCOL.json');assert not set(p['development_seeds'])&set(p['heldout_seeds'])
    for family in p['families']:
        for trial in [1,2]:
            d=RUN/'llm_trials';a=(d/f'{family}_A_{trial:02d}'/'prompt.txt').read_text();b=(d/f'{family}_B_{trial:02d}'/'prompt.txt').read_bytes();c=(d/f'{family}_C_{trial:02d}'/'prompt.txt').read_bytes()
            assert 'target descriptors' not in a and b==c
    assert read(RUN/'protocol/FROZEN_INPUTS.json')['descriptor_code_sha256']==sha(REPO/'metamaterial_eval/composites/descriptors.py')


@pytest.mark.parametrize('family',['particle','fiber'])
def test_reference_identity_semantics_and_no_processing_change(family):
    d=RUN/'references'/family;m=read(d/'manifest.json')
    assert m['kind']=='SYNTHETIC_NOT_EXPERIMENTAL' and m['physical_scale'] is None
    assert 'matrix' in m['phase0'] and 'void' not in m['phase0']
    assert np.array_equal(np.load(d/'original.npy'),np.load(d/'processed.npy'))
    assert m['image_sha256']==sha(d/'reference.png') and not m['reference_algorithm_shown_to_experimental_model']
