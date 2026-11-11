"""Review integrity checks,not LLM generation or material validation experiments."""
import hashlib,io,zipfile
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from scripts.v070_protocol import REPO,read,sha
from scripts.v070_correction_setup import CORRECTION
from scripts.v070_microscopy_review import colorize,FIBER_PHASES


@pytest.mark.parametrize('name',['P1_NiWC_multiphase','P2_NiWC_lower_magnification','F1_CPEEK_transverse_with_void','F2_carbon_transverse_larger_sections'])
def test_proposed_crops_are_exact_native_pixels_and_source_bytes(name):
    d=CORRECTION/'candidates'/name;c=read(d/'CANDIDATE.json');a=np.load(d/'PROPOSED_NATIVE_LABELS_256.npy',allow_pickle=False)
    with zipfile.ZipFile(c['source_mask_archive']) as z:raw=z.read(c['source_mask_member'])
    original=np.asarray(Image.open(io.BytesIO(raw)));x0,y0,x1,y1=c['crop_xyxy_end_exclusive']
    assert hashlib.sha256(raw).hexdigest()==c['mask_member_sha256']
    assert a.shape==(256,256) and a.dtype==np.uint8 and np.array_equal(a,original[y0:y1,x0:x1])
    assert set(np.unique(a))==set(np.unique(original)) and c['all_source_labels_retained_in_crop']
    assert sum(c['proposed_phase_pixels'].values())==65536
    assert c['physical_um_per_pixel'] is None and c['status']=='PROPOSED_NOT_APPROVED_NOT_FROZEN' and not c['primary_target']
    assert np.array_equal(a,np.asarray(Image.open(d/'PROPOSED_NATIVE_LABELS_256.png')))


def test_porosity_is_not_merged_into_matrix():
    p=read(CORRECTION/'candidates/P1_NiWC_multiphase/CANDIDATE.json');f=read(CORRECTION/'candidates/F1_CPEEK_transverse_with_void/CANDIDATE.json')
    assert p['proposed_phase_pixels']['2']>0 and f['proposed_phase_pixels']['2']>0
    assert set(p['proposed_phase_pixels'])==set('12345') and set(f['proposed_phase_pixels'])==set('012')
    assert 'inferred' in p['phase_mapping_evidence'] and 'Explicit author' in f['phase_mapping_evidence']


def test_unknown_display_labels_raise_instead_of_becoming_background():
    with pytest.raises(ValueError):colorize(np.array([[0,1,2,3]],np.uint8),FIBER_PHASES)


def test_published_particle_archive_checksums_are_verified():
    m=read(CORRECTION/'sources/SOURCE_ARCHIVES.json')
    assert m['NiWC_license']['id']=='cc-by-4.0'
    assert all(r['published_checksum_verified'] for r in m['local_archives'] if r['path'].endswith(('AugmentedImages.zip','AugmentedMasks.zip')))


def test_reference_approval_gate_and_trial_counts_are_explicit():
    p=read(CORRECTION/'protocol/CORRECTION.json');assert not p['references_approved'] and not p['main_experiment_authorized_to_start'] and p['new_LLM_calls']==0
    s=read(CORRECTION/'audit/PRIOR_EXPERIMENT_INVENTORY.json')['summary']
    assert s['non_LLM_baseline_scripts']==2 and s['verified_returned_LLM_scripts']==1 and s['verified_returned_LLM_script_outputs']==20
    assert s['additional_submitted_chats_without_ingested_response']==1 and s['initial_prompt_packets_never_submitted']==10 and s['real_micrograph_LLM_trials']==0


def test_prior_evidence_bytes_are_preserved():
    for relative,digest in read(CORRECTION/'audit/PRIOR_EVIDENCE_HASHES.json').items():assert sha(REPO/relative)==digest


def test_review_figures_match_their_recorded_hashes():
    for name,digest in read(CORRECTION/'review/FIGURE_HASHES.json').items():assert sha(CORRECTION/'review'/name)==digest
