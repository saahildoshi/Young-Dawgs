"""Source integrity, phase preservation and model/evaluator separation."""
import hashlib
import io
import zipfile
import numpy as np
import pytest
from PIL import Image
from scripts.v070_protocol import REPO, read, sha
from scripts.v070_reference_preparation import PREP, F1, pixels_sha


@pytest.mark.parametrize('name', ['P1_NiWC_multiphase', 'P2_NiWC_lower_magnification',
                                  'F1_CPEEK_transverse_with_void', 'F2_carbon_transverse_larger_sections'])
def test_previous_clean_micrographs_exclude_display_rulers_and_overlays(name):
    d = F1.parent / name
    m = read(d / 'CANDIDATE.json')
    with zipfile.ZipFile(m['source_image_archive']) as z:
        raw = z.read(m['source_image_member'])
    source = np.asarray(Image.open(io.BytesIO(raw)))
    x0,y0,x1,y1 = m['crop_xyxy_end_exclusive']
    assert np.array_equal(np.asarray(Image.open(d / 'PROPOSED_MICROGRAPH_256.png')), source[y0:y1,x0:x1])


def test_f1_model_image_is_exact_original_pixels_and_only_attachment():
    d = PREP / 'fiber/F1_transverse_CPEEK'
    m = read(d / 'INPUT_MANIFEST.json')
    c = read(F1 / 'CANDIDATE.json')
    with zipfile.ZipFile(c['source_image_archive']) as z:
        raw = z.read(c['source_image_member'])
    source = np.asarray(Image.open(io.BytesIO(raw)))
    actual = np.asarray(Image.open(d / m['llm_image']))
    assert hashlib.sha256(raw).hexdigest() == m['source_member_sha256']
    assert np.array_equal(actual, source)
    assert pixels_sha(actual) == m['source_image_pixels_sha256'] == m['llm_image_pixels_sha256']
    assert sha(d / m['llm_image']) == m['llm_image_sha256']
    assert [p.name for p in (d / 'llm_image_only').iterdir()] == ['ORIGINAL_MICROGRAPH_256.png']
    assert m['evaluation_mask_never_attached_to_LLM'] and m['physical_um_per_pixel'] is None


def test_f1_mask_preserves_author_phases_and_cross_sectional_observations():
    d = PREP / 'fiber/F1_transverse_CPEEK'
    a = np.load(d / 'evaluation_only/NATIVE_LABELS_256.npy', allow_pickle=False)
    assert np.array_equal(a, np.load(F1 / 'PROPOSED_NATIVE_LABELS_256.npy', allow_pickle=False))
    assert {int(k): int(np.sum(a == k)) for k in np.unique(a)} == {0: 34585, 1: 29668, 2: 1283}
    desc = read(d / 'evaluation_only/CROSS_SECTION_DESCRIPTORS.json')
    assert desc['family'] == 'fiber_transverse'
    assert desc['phase_roles'] == {'matrix': 'solid', 'fiber': 'solid', 'void': 'void'}
    assert desc['physical_fiber_instance_count'] is None


def test_p3_is_native_crop_and_not_falsely_approved_or_export_legend_verified():
    d = PREP / 'particle/P3_NiWC_dispersed_reprecipitates'
    m = read(d / 'CANDIDATE.json')
    im = np.asarray(Image.open(d / 'source_image.bmp'))
    mask = np.asarray(Image.open(d / 'source_mask.bmp'))
    x0,y0,x1,y1 = m['crop_xyxy_end_exclusive']
    assert np.array_equal(np.asarray(Image.open(d / 'MICROGRAPH_256.png')), im[y0:y1,x0:x1])
    a = np.load(d / 'NATIVE_LABELS_256.npy', allow_pickle=False)
    assert np.array_equal(a, mask[y0:y1,x0:x1]) and set(np.unique(a)) == {1,5}
    assert m['phase_legend_status'] == 'CORROBORATED_NOT_DIRECTLY_VERIFIED'
    assert not m['experimental_input_eligible'] and m['status'] == 'REVIEW_ONLY_NOT_APPROVED'
    assert sha(d / 'source_image.bmp') == m['image_member_sha256']
    assert sha(d / 'source_mask.bmp') == m['mask_member_sha256']
    assert m['complete_regions'] >= 10 and m['largest_region_fraction_of_reinforcement'] < .06


def test_prior_evidence_unchanged_and_p1_decision_preserved():
    for path, digest in read(PREP / 'audit/PRESERVED_EVIDENCE_HASHES.json').items():
        assert sha(REPO / path) == digest
    d = read(PREP / 'DECISIONS.json')
    assert d['P1'] == 'REJECTED_PRIMARY_PRESERVED_OPTIONAL_ADVANCED_MULTIPHASE'
    assert not d['both_targets_approved'] and not d['main_experiment_authorized_to_start']
    assert d['new_LLM_calls'] == 0 and not d['push']


def test_future_conditions_keep_raw_images_only_and_genuine_script_trials():
    d = read(PREP / 'FUTURE_TRIAL_CONTRACT.json')
    assert d['status'] == 'NOT_STARTED_NOT_FROZEN'
    assert d['A_B_C_same_image_and_phase_definitions'] and d['no_baseline_substitution']
    assert d['fresh_chat_per_initial_script'] and d['ordinary_ChatGPT_only']
    assert set(d['development_seeds']).isdisjoint(d['heldout_seeds'])
    assert d['maximum_calls_including_C_revisions'] == 16


def test_review_figures_are_separate_and_hashed():
    for name, digest in read(PREP / 'review/FIGURE_HASHES.json').items():
        assert sha(PREP / 'review' / name) == digest


def test_p4_verified_archive_native_image_and_annotation_encoding():
    from scripts.v070_rose_particle_candidate import P4, ARCHIVE, EXPECTED
    m = read(P4 / 'CANDIDATE.json')
    assert sha(ARCHIVE) == EXPECTED == m['published_archive_sha256']
    with zipfile.ZipFile(ARCHIVE) as z:
        im_raw, mask_raw = z.read(m['image_member']), z.read(m['mask_member'])
    assert hashlib.sha256(im_raw).hexdigest() == m['image_member_sha256']
    assert hashlib.sha256(mask_raw).hexdigest() == m['mask_member_sha256']
    im = np.asarray(Image.open(io.BytesIO(im_raw)))
    encoded = np.asarray(Image.open(io.BytesIO(mask_raw)).convert('L'))
    x0,y0,x1,y1 = m['crop_xyxy_end_exclusive']
    assert np.array_equal(np.asarray(Image.open(P4 / 'ORIGINAL_MICROGRAPH_CROP_256.png')), im[y0:y1,x0:x1])
    labels = np.load(P4 / 'EVALUATION_LABELS_256.npy', allow_pickle=False)
    crop = encoded[y0:y1,x0:x1]
    assert np.array_equal(labels, (crop > 127).astype(np.uint8))
    assert np.array_equal(crop > 64, crop > 192)
    assert int(labels.sum()) == 12325 and labels.shape == (256,256)
    assert m['status'] == 'PROPOSED_VERIFIED_WC_ANNOTATION_NOT_APPROVED'
    assert m['physical_um_per_pixel'] is None and not m['llm_mask_attachment']


def test_latest_user_prefers_p3_but_p4_is_not_silently_selected():
    m = read(PREP / 'DECISIONS.json')
    assert m['P3'] == 'USER_PREFERRED_MORPHOLOGY_PENDING_VERIFICATION'
    assert m['P4'] == 'VERIFIED_WC_NON_WC_ANNOTATION_ALTERNATIVE_AWAITING_USER_REVIEW'
    assert not m['both_targets_approved'] and not m['main_experiment_authorized_to_start']
    assert m['new_LLM_calls'] == 0
