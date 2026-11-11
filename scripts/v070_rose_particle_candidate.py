"""Add a directly documented WC annotation candidate; no experimental calls."""
import hashlib
import io
import zipfile
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from scripts.v070_protocol import REPO, read, write, sha
from scripts.v070_reference_preparation import PREP, DOC, P2, pixels_sha
from scripts.v070_microscopy_review import colorize, PARTICLE_PHASES

ARCHIVE = REPO / '.artifacts/reference_sources/Ni_WC_Optical_Microscopy_Data.zip'
EXPECTED = 'ab14dffa6714647562790260bfb3d29ea091cc6e9853c51c8d26a929d3d437df'
P4 = PREP / 'particle/P4_NiWC_optical_WC_annotations'
DATASET = 'https://data.mendeley.com/datasets/2wmbc95xy9/1'
PAPER = 'https://doi.org/10.1016/j.commatsci.2022.111391'


def mask_array(z, name):
    return np.asarray(Image.open(io.BytesIO(z.read(name))).convert('L'))


def ranking(z):
    records = []
    for name in sorted(z.namelist()):
        if not name.endswith('_mask.jpg'):
            continue
        a = mask_array(z, name)
        if a.shape != (512, 512):
            continue
        for y in range(0, 257, 32):
            for x in range(0, 257, 32):
                r = a[y:y+256, x:x+256] > 127
                if not .15 <= r.mean() <= .55:
                    continue
                cc, n = ndi.label(r)
                areas = np.bincount(cc.ravel())
                edge = set(np.unique(np.r_[cc[0], cc[-1], cc[:,0], cc[:,-1]])) - {0}
                count = sum(int(areas[i] >= 100) for i in range(1,n+1) if i not in edge)
                if count < 5:
                    continue
                records.append({'mask_member': name, 'crop_xyxy_end_exclusive': [x,y,x+256,y+256],
                                'complete_regions_at_least_100px2': count, 'all_annotation_regions': int(n),
                                'boundary_censored_regions': len(edge), 'fraction': float(r.mean()),
                                'largest_region_fraction_of_WC': float(areas[1:].max()/areas[1:].sum())})
    # The region-size threshold affects only selection, never the stored mask.
    return sorted(records, key=lambda r:(r['largest_region_fraction_of_WC'], -r['complete_regions_at_least_100px2'], r['mask_member'], r['crop_xyxy_end_exclusive']))


def main():
    if sha(ARCHIVE) != EXPECTED:
        raise ValueError('Archive disagrees with published checksum')
    P4.mkdir(parents=True, exist_ok=False)
    with zipfile.ZipFile(ARCHIVE) as z:
        ranked = ranking(z)
        if not ranked:
            raise ValueError('No suitable crop; no substitute segmentation allowed')
        selected = ranked[0]
        member = selected['mask_member']
        image_member = member.replace('/mask/', '/').replace('_mask.jpg', '.jpg')
        im_bytes, mask_bytes = z.read(image_member), z.read(member)
        im = np.asarray(Image.open(io.BytesIO(im_bytes)))
        fullmask = mask_array(z, member)
    (P4/'source_image.jpg').write_bytes(im_bytes)
    (P4/'source_mask.jpg').write_bytes(mask_bytes)
    x0,y0,x1,y1 = selected['crop_xyxy_end_exclusive']
    image, encoded = im[y0:y1,x0:x1], fullmask[y0:y1,x0:x1]
    labels = (encoded > 127).astype(np.uint8)
    Image.fromarray(image).save(P4/'ORIGINAL_MICROGRAPH_CROP_256.png')
    Image.fromarray(labels).save(P4/'EVALUATION_LABELS_256.png')
    np.save(P4/'EVALUATION_LABELS_256.npy', labels)
    write(P4/'SEARCH.json', {'method': 'Every paired512px annotation; native256px crops on32px origins, WC area15%-55%, >=5 uncensored4-connected annotation regions with area>=100px2. Rank smallest largest-region fraction. No mask cleanup, no deletion of small regions, no LLM outcomes used.',
                             'eligible_count': len(ranked), 'ranking': ranked})
    write(P4/'CANDIDATE.json', {**selected, 'candidate_id': P4.name, 'status': 'PROPOSED_VERIFIED_WC_ANNOTATION_NOT_APPROVED',
                               'dataset': DATASET, 'doi': '10.17632/2wmbc95xy9.1', 'attribution': 'Dylan Rose (2022), University of Alberta', 'license': 'CC BY4.0',
                               'published_archive_sha256': EXPECTED, 'local_archive_sha256_verified': sha(ARCHIVE),
                               'archive_path': str(ARCHIVE), 'image_member': image_member,
                               'image_member_sha256': hashlib.sha256(im_bytes).hexdigest(), 'mask_member_sha256': hashlib.sha256(mask_bytes).hexdigest(),
                               'source_kind': 'Dataset optical micrograph and corresponding ground truth; no augmentation indicated by archive/file naming or dataset description. Native image crop, not annotation visualization.',
                               'phase_map': {'0':'non-WC background (NiCrBSi matrix region in author binary task)', '1':'WC reinforcement'},
                               'annotation_semantics_verified_by': {'dataset':DATASET, 'publication':PAPER, 'basis':'Dataset explicitly pairs Ni-WC optical images with ground truths; publication Figure 1 identifies white ground-truth pixels as WC.'},
                               'mask_encoding': 'JPEG ground truth with dark/light compression values. Decode grayscale>127 to WC1; otherwise non-WC0. This thresholds the supplied annotation encoding, never the scientific micrograph.',
                               'mask_encoding_minmax': [int(encoded.min()), int(encoded.max())],
                               'threshold64_vs192_changed_pixels': int(np.sum((encoded>64)!=(encoded>192))),
                               'no_mask_cleanup_or_phase_merging': True, 'pixel_count': {'0':int(np.sum(labels==0)), '1':int(np.sum(labels==1))},
                               'physical_um_per_pixel': None, 'image_pixels_sha256': pixels_sha(image),
                               'limitation': 'Only WC/non-WC annotated. No separate void, internal inclusion or matrix-subphase ground truth. Non-WC is not verified as entirely solid matrix; no pore-free or mechanics-ready claim. Optical blur and contour uncertainty remain. Dataset training/test designation concerns its original segmentation study, not independent LLM trials.',
                               'llm_mask_attachment': False, 'new_LLM_calls':0})
    render()
    decisions = read(PREP/'DECISIONS.json')
    decisions.update(P3='USER_PREFERRED_MORPHOLOGY_PENDING_VERIFICATION', P4='VERIFIED_WC_NON_WC_ANNOTATION_ALTERNATIVE_AWAITING_USER_REVIEW',
                     gate='P3_VERIFICATION_PENDING_OR_EXPLICIT_SELECTION_OF_P4_WITH_BINARY_SCHEMA_LIMITS;NO_LLM_TRIALS')
    write(PREP/'DECISIONS.json', decisions)
    write(PREP/'sources/ROSE_DATASET.json', {'url':DATASET, 'published_archive_filename':'Ni_WC_Optical_Microscopy_Data.zip',
                                            'published_archive_size':13571221, 'published_archive_sha256':EXPECTED,
                                            'metadata_endpoint':'https://data.mendeley.com/public-api/datasets/2wmbc95xy9/files?folder_id=root&version=1',
                                            'download_url':'https://data.mendeley.com/public-files/datasets/2wmbc95xy9/files/ace6acfc-71d1-4a64-9af1-32888020b7a4/file_downloaded',
                                            'paper':PAPER, 'paper_annotation_definition':'White ground-truth pixels identify WC; the complementary class is non-WC background.',
                                            'license':'https://creativecommons.org/licenses/by/4.0/', 'attribution':'Dylan Rose (2022) U_Net_Ni_WC_Optical_images, version1',
                                            'archive_observation':'231 images,230 paired mask files; one missing annotation pair. Candidate selected only among existing aligned512x512 pairs; no annotation invented.'})
    (DOC/'P4_VERIFIED_ANNOTATION_ALTERNATIVE.md').write_text(NOTE,encoding='utf-8',newline='\n')
    print('P4 documented and compared with P2; user-preferred P3 remains pending verification. No LLM submissions.')


def render():
    fig, axes = plt.subplots(2,3,figsize=(10,7.4))
    fig.subplots_adjust(left=.04,right=.99,top=.88,bottom=.18,hspace=.24,wspace=.09)
    for row,d in enumerate([P4,P2]):
        new = row == 0
        image = np.asarray(Image.open(d/('ORIGINAL_MICROGRAPH_CROP_256.png' if new else 'PROPOSED_MICROGRAPH_256.png')))
        labels = np.asarray(Image.open(d/('EVALUATION_LABELS_256.png' if new else 'PROPOSED_NATIVE_LABELS_256.png')))
        palette = {0:('Non-WC background','#d6d9df'),1:('WC reinforcement','#168f83')} if new else PARTICLE_PHASES
        rgb = colorize(labels,palette)
        photo = image if image.ndim==3 else np.repeat(image[:,:,None],3,axis=2)
        for ax,pic,title in zip(axes[row],[photo,rgb,np.round(.65*photo+.35*rgb).astype(np.uint8)],['Original image crop','Evaluation annotation','Review overlay only']):
            ax.imshow(pic);ax.set_title(title,fontsize=10);ax.set_xticks([]);ax.set_yticks([])
        axes[row,0].set_ylabel('P4: documented WC / non-WC' if new else 'P2: previous SEM alternative',fontsize=10)
        axes[row,1].legend(handles=[Patch(facecolor=palette[int(k)][1],label=f'{k}: {palette[int(k)][0]}') for k in np.unique(labels)],
                           loc='upper center',bbox_to_anchor=(.5,-.02),ncol=2,fontsize=7,frameon=False)
    fig.suptitle('P4 verified WC annotations beside P2 — additional review option',fontsize=13)
    fig.text(.5,.035,'P4 is an original optical micrograph crop with author ground truth. P3 remains the user-preferred morphology pending verification.\nNo added overlay, text or ruler in clean inputs. Pixel calibration unknown. P4 has no independent void annotation.',ha='center',fontsize=8)
    out = PREP/'review/P4_VS_P2.png'
    fig.savefig(out,dpi=160);plt.close(fig)
    hashes=read(PREP/'review/FIGURE_HASHES.json');hashes[out.name]=sha(out);write(PREP/'review/FIGURE_HASHES.json',hashes)


NOTE = """# P4: newly located directly documented WC annotation alternative

The user prefers P3's dispersed secondary-carbide morphology, pending verification. That preference is recorded and has not been changed into final approval. The P3 phase legend and original-image gates remain unresolved.

Further research located [Dylan Rose's original Ni-WC optical image/ground-truth dataset](https://data.mendeley.com/datasets/2wmbc95xy9/1), DOI10.17632/2wmbc95xy9.1, CC BY4.0. Its 13,571,221-byte ZIP matches published SHA-256 ab14dffa6714647562790260bfb3d29ea091cc6e9853c51c8d26a929d3d437df. The [publication](https://doi.org/10.1016/j.commatsci.2022.111391), Figure 1, explicitly defines white ground-truth pixels as WC. This gives a directly documented WC/non-WC semantic pair, resolving the raw-ID chemical interpretation problem for this alternative. It does not verify P3's different SEM annotation IDs.

P4 preserves source image and JPEG ground-truth bytes, and uses a native 256x256 crop of `img_19_crop9.jpg` at [128,96,384,352). No micrograph resampling, enhancement, synthetic content, display overlay or ruler is added. The source mask's JPEG compression produces dark/light values; grayscale>127 decodes WC 1, otherwise non-WC 0. Thresholds 64 and 192 yield identical labels across this crop, so no intermediate-tone ambiguity affects those labels. This is decoding the supplied mask, not segmenting the raw micrograph. No speckle deletion or contour cleanup is performed. Nine 4-connected annotation regions are retained; five complete regions have area >= 100 pixels squared. The latter area threshold is only a screening rule; small annotation regions stay in the evaluation mask. WC fraction 18.806%.

**Limit:** the author task annotates WC versus non-WC background, not an exhaustive chemical/void map. Non-WC includes the NiCrBSi matrix region but cannot be certified as entirely pore-free solid matrix. There is no independent void mask, and dark internal features are not assigned new physical identities. This is suitable for a two-class annotation-pattern reference if explicitly selected with that limitation; it is not a certified three-phase physical/void reference or mechanics-ready material map. Optical blur and contour uncertainty also remain.

P4 is shown beside P2 in `review/P4_VS_P2.png`. P3 remains preserved and preferred, P2 remains available, P1 remains optional advanced multiphase, and F1 preparation is complete. No new LLM trial has started. Final particle selection is still required, followed by prospective categorical execution/scoring registration. Original micrographs alone will be attached in every condition; masks stay evaluator-only. There is no micrometer calibration claim and no automatic Git push.
"""


if __name__ == '__main__':
    main()
