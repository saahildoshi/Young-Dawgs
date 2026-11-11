"""Independent analytic fixtures; these are not LLM trial generators."""
import numpy as np
import pytest
from metamaterial_eval.composites.microscopy import describe,validity,validate,errors,categorical_diversity,VISIBLE,HIDDEN,SCALES


def test_native_particle_mapping_has_known_geometry_and_keeps_source_labels():
    a=np.ones((256,256),np.uint8);a[40:44,40:44]=5;a[40:44,70:74]=5
    original=a.copy();d=describe(a,'P3')
    assert np.array_equal(a,original) and set(np.unique(a))=={1,5}
    assert d['reinforcement_fraction']==32/65536 and d['complete_regions']==2
    assert d['diameter_mean_px']==pytest.approx(2*np.sqrt(16/np.pi))
    assert d['nearest_neighbor_mean_px']==30 and d['working_map']=={'1':0,'5':1}


def test_fiber_three_phase_fixture_and_interface_edge_conservation():
    a=np.zeros((256,256),np.uint8);a[:,80:160]=1;a[:,160:]=2
    d=describe(a,'F1')
    assert d['fiber_fraction']==80/256 and d['void_fraction']==96/256
    assert d['matrix_fiber_interface']==256/65536
    assert d['fiber_S2_y_8']==80/256 and d['fiber_S2_x_8']==pytest.approx(72/248)
    assert d['complete_fiber_regions']==0 and d['fiber_diameter_mean_px'] is None
    assert validity(a,'F1')['passed']  # Clipped/nonspanning phases are legitimate.


@pytest.mark.parametrize('family,labels',[('P3',[0,1]),('P3',[1,2]),('F1',[1,5])])
def test_silent_binary_conversion_or_unknown_phases_rejected(family,labels):
    a=np.full((256,256),labels[0],np.uint8);a[:128]=labels[1]
    assert not validity(a,family)['passed']


def test_expected_void_is_not_optional_and_nonempty_is_separate_from_descriptors():
    a=np.zeros((256,256),np.uint8);a[32:40,32:40]=1
    validate(a,'F1')
    assert not validity(a,'F1')['passed']
    assert describe(a,'F1')['void_fraction']==0


def test_fixed_error_scale_and_missing_value_coverage_are_not_silently_averaged():
    names=VISIBLE['P3'];target={k:0 for k in names};obs={k:SCALES['P3'][k] for k in names}
    assert errors(obs,target,'P3',names)['mean']==1
    obs[names[0]]=None;d=errors(obs,target,'P3',names)
    assert d['mean'] is None and d['coverage']==.8 and d['available_mean_diagnostic']==1
    assert all(set(VISIBLE[f]).isdisjoint(HIDDEN[f]) for f in ['P3','F1'])


def test_categorical_diversity_does_not_or_multiphase_labels():
    a=np.zeros((256,256),np.uint8);a[:128]=1;a[128:192]=2
    b=a.copy();b[a==1]=2;b[a==2]=1
    d=categorical_diversity([a,b],'F1')
    assert d['mean_categorical_hamming']==.75
    assert d['by_phase']['0']['unique_hashes']==1 and d['by_phase']['1']['unique_hashes']==2


def test_approved_inputs_are_clean_and_native_labels_survive_freeze():
    from scripts.v070_real_pilot import RUN
    from scripts.v070_protocol import REPO,read,sha
    from PIL import Image
    p=read(RUN/'protocol/PROTOCOL.json');frozen=read(RUN/'protocol/FROZEN_HASHES.json')
    assert sha(RUN/'protocol/PROTOCOL.json')==frozen['protocol_sha256']
    assert not set(p['development_seeds'])&set(p['heldout_seeds'])
    for path,digest in frozen['descriptor_code'].items():assert sha(REPO/path)==digest
    for family,labels in [('P3',{1,5}),('F1',{0,1,2})]:
        d=RUN/'references'/family;m=read(d/'INPUT_MANIFEST.json')
        assert sha(d/'microscopy_input.png')==m['image_sha256']
        assert sha(d/'evaluation_only_labels.npy')==m['mask_sha256']
        assert set(np.unique(np.load(d/'evaluation_only_labels.npy',allow_pickle=False)))==labels
        assert np.array_equal(np.asarray(Image.open(d/'microscopy_input.png')),np.asarray(Image.open(REPO/m['image_origin'])))
        pa=(RUN/f'llm_trials/{family}_A_01/prompt.txt').read_text(encoding='utf-8')
        pb=(RUN/f'llm_trials/{family}_B_01/prompt.txt').read_text(encoding='utf-8')
        pc=(RUN/f'llm_trials/{family}_C_01/prompt.txt').read_text(encoding='utf-8')
        assert pa== (RUN/f'llm_trials/{family}_A_02/prompt.txt').read_text(encoding='utf-8')
        assert pb==pc and 'descriptor targets' not in pa and 'descriptor targets' in pb


def test_previous_evidence_remains_identical():
    from scripts.v070_real_pilot import RUN
    from scripts.v070_protocol import REPO,read,sha
    for path,digest in read(RUN/'audit/PRIOR_EVIDENCE_HASHES.json').items():assert sha(REPO/path)==digest
