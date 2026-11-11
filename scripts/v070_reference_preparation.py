"""Prepare F1 and review a dispersed P3 against P2; submit no LLM prompts."""
from pathlib import Path
import hashlib
import io
import shutil
import subprocess
import zipfile

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Rectangle

from scripts.v070_protocol import REPO, RUN, read, write, sha
from scripts.v070_correction_setup import CORRECTION
from scripts.v070_microscopy_review import PARTICLE_IMAGES, PARTICLE_MASKS, array, colorize, PARTICLE_PHASES, FIBER_PHASES
from metamaterial_eval.composites.transverse import describe_transverse

PREP = RUN.parent / "reference_preparation_002"
DOC = REPO / "docs/pipeline_v0.7.0/reference_preparation_002"
F1 = CORRECTION / "candidates/F1_CPEEK_transverse_with_void"
P2 = CORRECTION / "candidates/P2_NiWC_lower_magnification"


def pixels_sha(a):
    return hashlib.sha256(a.tobytes()).hexdigest()


def search_particle():
    """Native crops only. No thresholding, cleanup, relabeling or resizing."""
    eligible = []
    with zipfile.ZipFile(PARTICLE_MASKS) as z:
        for name in sorted(z.namelist()):
            if not name.endswith("_HorizontalFlip.bmp"):
                continue
            labels = array(z, name)
            for y in range(0, 257, 16):
                for x in range(0, 257, 16):
                    roi = labels[y:y+256, x:x+256]
                    if set(np.unique(roi)) != {1, 5}:
                        continue
                    cc, n = ndi.label(roi == 5)
                    areas = np.bincount(cc.ravel())[1:]
                    edge = set(np.unique(np.r_[cc[0], cc[-1], cc[:, 0], cc[:, -1]])) - {0}
                    if n-len(edge) < 10:
                        continue
                    eligible.append({"mask": name, "crop_xyxy_end_exclusive": [x, y, x+256, y+256],
                                     "reinforcement_fraction": float(np.mean(roi == 5)),
                                     "annotation_regions_4_connected": int(n), "complete_regions": n-len(edge),
                                     "boundary_censored_regions": len(edge),
                                     "largest_region_fraction_of_reinforcement": float(areas.max()/areas.sum())})
    eligible.sort(key=lambda r: (r["largest_region_fraction_of_reinforcement"], -r["complete_regions"], r["mask"], r["crop_xyxy_end_exclusive"]))
    if not eligible:
        raise ValueError("No qualifying dispersed particle crop; do not invent annotations")
    write(PREP / "particle/SEARCH.json", {"rule": "Search every HorizontalFlip mask on a 16px crop-origin grid; exact native 256x256 crops containing only raw labels1,5 and >=10 uncensored 4-connected regions. Rank by smallest largest-region fraction, then most complete regions. Morphology selection only, no LLM outcomes.",
                                         "eligible_count": len(eligible), "ranked_candidates": eligible})
    return eligible[0]


def prepare_particle():
    best = search_particle()
    d = PREP / "particle/P3_NiWC_dispersed_reprecipitates"
    d.mkdir(parents=True)
    mask_member = best["mask"]
    image_member = mask_member.replace("AugmentedMasks/", "AugmentedImages/")
    with zipfile.ZipFile(PARTICLE_IMAGES) as iz, zipfile.ZipFile(PARTICLE_MASKS) as mz:
        image_bytes, mask_bytes = iz.read(image_member), mz.read(mask_member)
    (d / "source_image.bmp").write_bytes(image_bytes)
    (d / "source_mask.bmp").write_bytes(mask_bytes)
    im = np.array(Image.open(io.BytesIO(image_bytes)))
    labels = np.array(Image.open(io.BytesIO(mask_bytes)))
    x0, y0, x1, y1 = best["crop_xyxy_end_exclusive"]
    crop, mask = im[y0:y1, x0:x1], labels[y0:y1, x0:x1]
    Image.fromarray(crop).save(d / "MICROGRAPH_256.png")
    Image.fromarray(mask).save(d / "NATIVE_LABELS_256.png")
    np.save(d / "NATIVE_LABELS_256.npy", mask)
    manifest = {**best, "candidate_id": d.name, "status": "REVIEW_ONLY_NOT_APPROVED",
                "material": "Ni-WC metal matrix composite; local Ni-alloy matrix with dispersed reprecipitated carbide regions",
                "not_primary_WC": "These are secondary reprecipitated carbides, not surviving coarse WC particles; no exact carbide chemistry assigned.",
                "source": "https://zenodo.org/records/17315241", "license": "CC BY4.0", "attribution": "Mutahar Safdar (2025)",
                "image_archive": str(PARTICLE_IMAGES), "mask_archive": str(PARTICLE_MASKS),
                "image_member": image_member, "mask_member": mask_member,
                "image_member_sha256": hashlib.sha256(image_bytes).hexdigest(), "mask_member_sha256": hashlib.sha256(mask_bytes).hexdigest(),
                "source_augmentation": "Supplied HorizontalFlip geometry-preserving variant; not an independently acquired original. Original unaugmented acquisition bytes unavailable in downloaded archive.",
                "processing": "Native crop only; no resampling, intensity changes, thresholding, mask cleanup or phase merging",
                "source_labels": [int(k) for k in np.unique(labels)], "crop_labels": [int(k) for k in np.unique(mask)],
                "phase_map": {"1": "Ni-alloy matrix", "5": "reprecipitated carbides"},
                "excluded_phases": "Coarse carbide, dilution band and any void excluded by spatial crop, not mapped into matrix; their original labels remain in the full source mask",
                "annotation_verification": "Paired supplied human annotation verified byte-for-byte. Semantic mapping cross-checked with publication class order, author reduce_zero_label=True and morphology; exact raw-ID export legend is not supplied. This is documented corroboration, not a claimed direct author-export verification.",
                "phase_legend_status": "CORROBORATED_NOT_DIRECTLY_VERIFIED", "experimental_input_eligible": False,
                "remaining_gates": ["User particle-target selection", "Resolve exact raw-ID semantic legend to the requested verification standard", "Establish acceptable original micrograph input provenance; supplied archive is augmented"],
                "pixel_count": {str(k): int(np.sum(mask == k)) for k in np.unique(mask)},
                "physical_um_per_pixel": None, "rve_status": "Single selected matrix-rich field; not bulk RVE or independent specimen",
                "micrograph_sha256": sha(d / "MICROGRAPH_256.png"), "micrograph_pixels_sha256": pixels_sha(crop),
                "mask_sha256": sha(d / "NATIVE_LABELS_256.npy")}
    write(d / "CANDIDATE.json", manifest)
    return d


def prepare_fiber():
    d = PREP / "fiber/F1_transverse_CPEEK"
    inp, evaluator = d / "llm_image_only", d / "evaluation_only"
    inp.mkdir(parents=True)
    evaluator.mkdir()
    source = read(F1 / "CANDIDATE.json")
    with zipfile.ZipFile(source["source_image_archive"]) as z:
        raw = z.read(source["source_image_member"])
    image = np.asarray(Image.open(io.BytesIO(raw)))
    target = np.load(F1 / "PROPOSED_NATIVE_LABELS_256.npy", allow_pickle=False)
    Image.fromarray(image).save(inp / "ORIGINAL_MICROGRAPH_256.png")
    shutil.copyfile(F1 / "PROPOSED_NATIVE_LABELS_256.npy", evaluator / "NATIVE_LABELS_256.npy")
    shutil.copyfile(F1 / "PROPOSED_NATIVE_LABELS_256.png", evaluator / "NATIVE_LABELS_256.png")
    write(evaluator / "CROSS_SECTION_DESCRIPTORS.json", describe_transverse(target))
    manifest = {"target_id": "F1_transverse_CPEEK", "user_decision": "CONDITIONALLY_APPROVED_PREPARED",
                "family": "fiber_transverse", "phase_schema": {"0": {"meaning": "PEEK matrix", "physical_role": "solid"},
                                                                    "1": {"meaning": "carbon fiber cross-sections", "physical_role": "solid"},
                                                                    "2": {"meaning": "void", "physical_role": "void"}},
                "source_manifest": str((F1 / "CANDIDATE.json").relative_to(REPO)), "source_manifest_sha256": sha(F1 / "CANDIDATE.json"),
                "source_member": source["source_image_member"], "source_member_sha256": source["image_member_sha256"],
                "llm_image": "llm_image_only/ORIGINAL_MICROGRAPH_256.png", "llm_image_sha256": sha(inp / "ORIGINAL_MICROGRAPH_256.png"),
                "source_image_pixels_sha256": pixels_sha(image), "llm_image_pixels_sha256": pixels_sha(image),
                "image_processing": "Decoded original unaugmented RGB TIFF to lossless PNG; entire native 256x256 field, identical pixels, no overlays, rulers, labels or text added",
                "evaluation_mask": "evaluation_only/NATIVE_LABELS_256.npy", "evaluation_mask_sha256": sha(evaluator / "NATIVE_LABELS_256.npy"),
                "evaluation_mask_never_attached_to_LLM": True, "physical_um_per_pixel": None,
                "annotation_method": "Author README: local-maxima fiber centers, perfect circles with mean fiber radius; minimum-threshold voids. DatasetI nominal mean radius3pixels. Contours and region statistics are approximate; touching circles may merge.",
                "descriptor_replacement": "Cross-sectional phase fractions, annotation-region area-equivalent diameters/aspect ratios, centroid spacing/packing, per-phase S2, phase-pair interfaces, void-region and boundary-censoring summaries. No longitudinal length/curvature/fiber-axis orientation.",
                "descriptor_status": "PREPARATION_DIAGNOSTICS_NOT_YET_FROZEN_EXPERIMENT_SCORING",
                "execution_gate": "Particle approval and provenance/annotation gates must pass before any corrected trial"}
    write(d / "INPUT_MANIFEST.json", manifest)
    return d


def review(p3, f1):
    out = PREP / "review"
    out.mkdir(exist_ok=True)
    fig, axes = plt.subplots(2, 4, figsize=(13, 8.0))
    fig.subplots_adjust(top=.89, bottom=.19, left=.035, right=.99, wspace=.10, hspace=.34)
    for row, (d, name) in enumerate([(p3, "P3: dispersed secondary carbides"), (P2, "P2: retained alternative")]):
        is_new = row == 0
        im = np.asarray(Image.open(d / ("source_image.bmp" if is_new else "SOURCE_MICROGRAPH.png")))
        crop = np.asarray(Image.open(d / ("MICROGRAPH_256.png" if is_new else "PROPOSED_MICROGRAPH_256.png")))
        labels = np.asarray(Image.open(d / ("NATIVE_LABELS_256.png" if is_new else "PROPOSED_NATIVE_LABELS_256.png")))
        c = read(d / "CANDIDATE.json")
        rgb = colorize(labels, PARTICLE_PHASES)
        photo = np.repeat(crop[:, :, None], 3, axis=2) if crop.ndim == 2 else crop
        overlay = np.round(.65*photo.astype(float)+.35*rgb).astype(np.uint8)
        for ax, picture, title in zip(axes[row], [im, crop, rgb, overlay], ["Supplied micrograph", "Native256px crop", "Supplied annotations", "Review overlay only"]):
            ax.imshow(picture, interpolation="nearest"); ax.set_title(title, fontsize=10); ax.set_xticks([]); ax.set_yticks([])
        x0,y0,x1,y1 = c["crop_xyxy_end_exclusive"]
        axes[row, 0].add_patch(Rectangle((x0-.5, y0-.5), x1-x0, y1-y0, fill=False, edgecolor="red", lw=1.5))
        axes[row, 0].set_ylabel(name, fontsize=10)
        handles = [Patch(facecolor=PARTICLE_PHASES[int(k)][1], label=f"{k}: {PARTICLE_PHASES[int(k)][0]}") for k in np.unique(labels)]
        axes[row, 2].legend(handles=handles, loc="upper center", bbox_to_anchor=(.5, -.03), ncol=2, fontsize=7, frameon=False)
    fig.suptitle("P3 replacement beside P2 — selection remains open", fontsize=15)
    fig.text(.5, .035, "Native pixels; no physical calibration. Color panels, red boxes and overlays are review-only. No added scale bars in input images.\nP3 = reprecipitated carbides, not coarse WC. Raw-ID legend corroborated from paper/code; direct export legend remains unavailable.", ha="center", fontsize=9)
    fig.savefig(out / "P3_VS_P2.png", dpi=160); plt.close(fig)
    a = np.asarray(Image.open(f1 / "llm_image_only/ORIGINAL_MICROGRAPH_256.png"))
    labels = np.load(f1 / "evaluation_only/NATIVE_LABELS_256.npy", allow_pickle=False)
    fig, axes = plt.subplots(1, 2, figsize=(8, 4.5))
    for ax, picture, title in zip(axes, [a, colorize(labels, FIBER_PHASES)], ["F1 original micrograph: model input", "F1 supplied mask: evaluation only"]):
        ax.imshow(picture); ax.set_title(title, fontsize=11); ax.axis("off")
    fig.suptitle("C/PEEK transverse cross-section — three phases retained")
    fig.text(.5, .035, "0 matrix 52.77% | 1 fiber 45.27% | 2 void 1.96%\nApproximate circle annotations; pixel units only; physical scale unknown.", ha="center", fontsize=10)
    fig.subplots_adjust(bottom=.16, top=.83); fig.savefig(out / "F1_PREPARED.png", dpi=160); plt.close(fig)
    write(out / "FIGURE_HASHES.json", {p.name: sha(p) for p in out.glob("*.png")})


def main():
    PREP.mkdir(parents=True, exist_ok=False)
    DOC.mkdir(parents=True, exist_ok=False)
    old = {str(p.relative_to(REPO)).replace("\\", "/"): sha(p) for root in [RUN, CORRECTION] for p in sorted(root.rglob("*")) if p.is_file()}
    write(PREP / "audit/PRESERVED_EVIDENCE_HASHES.json", old)
    p3, f1 = prepare_particle(), prepare_fiber()
    review(p3, f1)
    write(PREP / "DECISIONS.json", {"starting_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
                                    "P1": "REJECTED_PRIMARY_PRESERVED_OPTIONAL_ADVANCED_MULTIPHASE", "P2": "ALTERNATIVE_AWAITING_SELECTION",
                                    "P3": "PROPOSED_DISPERSED_SECONDARY_CARBIDES_WITH_UNRESOLVED_LEGEND_AND_ORIGINAL_INPUT_GATES",
                                    "F1": "CONDITIONALLY_APPROVED_PREPARED_THREE_PHASE_TRANSVERSE", "new_LLM_calls": 0,
                                    "both_targets_approved": False, "main_experiment_authorized_to_start": False,
                                    "gate": "AWAIT_PARTICLE_SELECTION_AND_VERIFIED_PHASE_ANNOTATION_ORIGINAL_IMAGE_PROVENANCE",
                                    "mask_role": "Evaluation only; never model image input in any condition", "push": False})
    write(PREP / "FUTURE_TRIAL_CONTRACT.json", {
        "status": "NOT_STARTED_NOT_FROZEN", "ordinary_ChatGPT_only": True, "fresh_chat_per_initial_script": True,
        "A_B_C_same_image_and_phase_definitions": True, "model_image_inputs": "Approved original micrograph only; no masks, annotation panels, overlays, scale rulers or legends embedded in the image",
        "phase_definitions": "Textual phase IDs and solid/void roles identical across conditions; F1 uses0matrix,1fiber,2void. Particle schema remains pending selection and verification.",
        "A": "Image and common textual contract only", "B": "Same as A plus prospectively frozen cross-sectional/particle descriptors",
        "C": "Same initial B information plus one development-feedback revision", "independent_scripts_per_family_condition": 2,
        "initial_calls": 12, "maximum_calls_including_C_revisions": 16, "development_seeds": list(range(100,110)), "heldout_seeds": list(range(10)),
        "generator_contract": "generate(seed:int, params:dict)->np.ndarray; native 256x256 uint8 categorical labels; standalone algorithm with no embedded target raster, file or network access",
        "execution": "Before submissions, implement categorical worker/ingestion/scoring, freeze descriptor lists/scales and hard output requirements, validate fixture metrics, then capture complete independently returned LLM scripts and provenance. Historical binary worker cannot validate F1.",
        "no_baseline_substitution": True, "preserve_raw_responses": True, "score_unit": "Independent script; seeds nested, descriptive pilot only",
        "physical_um_per_pixel": None, "solver_jobs": 0, "feedback_repair_calls_outside_budget": 0})
    (DOC / "REFERENCE_PREPARATION.md").write_text(REPORT, encoding="utf-8", newline="\n")
    print("Prepared F1, P3/P2 comparison and evidence audit. No new LLM calls. Particle annotation/original-input gates remain open.")


REPORT = """# Reference preparation following user review

P1 is rejected as the primary particle target and retained unchanged, including its original source bytes and native multiphase mask, as an optional advanced reference. P2 remains available. F1 is conditionally approved and prepared as a three-phase transverse C/PEEK reference. No prior experiment, generator, descriptor output or candidate record was overwritten.

## F1 prepared

`fiber/F1_transverse_CPEEK/llm_image_only/ORIGINAL_MICROGRAPH_256.png` is an exact pixel copy of the original unaugmented TIFF field, losslessly encoded as PNG. It contains no added overlays, text, annotation colors or 64-pixel ruler. Matrix 0, carbon fiber 1 and void 2 are distinct evaluator labels. Both matrix and fiber are solid. Void is never converted into matrix or reinforcement. The mask is in `evaluation_only`, outside the single-image model attachment directory.

The source author describes local-maxima fiber centers with perfect circles at the mean radius, and minimum-threshold void annotations. Dataset I is C/PEEK with nominal 3 px radius. These contours are approximate. Touching circles can form one connected annotation region, so region counts, equivalent diameters and centroid spacings are proxies, not physical fiber-instance truth. The new transverse observer reports per-phase fractions/S2/connectivity, phase-pair pixel-edge interfaces, complete-region diameter/aspect/spacing and void/censoring summaries. It does not use longitudinal fiber length, curvature or fiber-axis orientation. Historical binary descriptors remain available only to historical experiments. These are preparation diagnostics, not yet registered experiment scores.

Author definition: [4TU dataset](https://doi.org/10.4121/bf11171a-1f57-4a8a-9768-757850d13665); the original README and archive/member hashes are retained in the preceding correction record.

## P3 beside P2

![P3 beside P2](../../../experiments/pipeline_v0.7.0/reference_preparation_002/review/P3_VS_P2.png)

P3 is a matrix-rich field from the real Ni-WC composite, containing dispersed **secondary reprecipitated carbides**, rather than surviving coarse WC. Native crop [16,208,272,464) of `sem600_x768_y448_HorizontalFlip.bmp`: matrix 68.367%, carbide 31.633%; 78 four-connected annotated regions,57 complete and 21 boundary-censored. The largest region is 5.56% of reinforcement area. Raw labels 1 and 5 are retained without merging. Other source phases lie outside this spatial crop; full source annotations are preserved. Selection searched all geometry-preserving tiles on a 16 px grid; 499 crops qualified, ranked by the smallest largest-region fraction, then number of complete regions. It is a morphology-selected local field, not an unbiased bulk RVE or independent specimen.

P2 retains matrix, coarse carbide, dilution and reprecipitate regions; its central crop has no void label. It remains an alternative, not a binary particle field. P1 stays archived as the advanced five-phase option.

### Annotation and input provenance limits

The human mask/image pairs and archive checksums are verified. Semantic IDs 1=matrix, 2=void, 3=coarse carbide, 4=dilution, 5=reprecipitate are corroborated by the paper's class order and the author's `reduce_zero_label=True` training configuration (raw 1 maps to training 0). The paper explicitly calls training-index 1 porosity. The exact raw-ID export legend/custom dataset metadata is absent from the downloaded files and author repository. This corroboration must not be called direct author-export verification. Therefore P3 is **review-only**, with a remaining phase-legend verification gate.

The supplied particle archive has augmented variants; selected HorizontalFlip pixels preserve geometry but are not original acquisition bytes. P3 and P2 are not yet authorized model attachments under the user's original-micrograph requirement. An original tile/confirmed inverse-flip reconstruction provenance is still needed. No segmentation-derived or manually authored replacement image will be used to bypass either gate.

Primary evidence: [Safdar dataset, CC BY4.0](https://zenodo.org/records/17315241), [paper](https://doi.org/10.1016/j.matchar.2025.115645), [author configuration](https://github.com/Mutahar-Safdar/SEM_Segmentation_ViTs/blob/main/Segformer%20%2B%20ViT.ipynb), [MMSegmentation label-offset definition](https://mmsegmentation.readthedocs.io/en/latest/notes/faq.html#functionality-of-reduce-zero-label). Author configuration Git blob 167fd9f3680ee9faf958151a4679496bcdc36c07. Paper support is a class-order cross-check, not a bundled raw-ID legend.

Follow-up research located Dylan Rose's original optical Ni-WC image/ground-truth dataset DOI10.17632/2wmbc95xy9.1 and produced P4. Its directly documented WC/non-WC annotations resolve the semantic-ID problem for that alternative, but do not verify P3. See [P4 verified annotation alternative](P4_VERIFIED_ANNOTATION_ALTERNATIVE.md) for the source, checksum, native crop, JPEG-mask decoding and absence of independent void annotation. P3 remains the user's preferred morphology pending verification. Annotated TiO2 powder datasets lack an embedded composite matrix; Al/B4C images lack verified masks, so neither was substituted.

## Input separation and next trial gate

**Confirmed:** the old displayed 64-pixel rulers, review overlays, red crop rectangles, legends and phase-color panels are generated in separate review figures. They are absent from the prepared F1 model image and the clean particle review crops. Exact array equality to the source crop is tested; the clean crops are not screenshots. No micrometer scale is inferred from pixel counts, magnification, nominal fiber radius or image metadata. Physical pixel calibration remains unknown.

No new LLM trials were submitted. The future A/B/C contract requires identical original micrograph inputs and phase definitions; masks remain evaluator-only, including in image-only A. After both targets and provenance are approved, categorical execution/scoring must be frozen and actual independent regular ChatGPT scripts collected. Prepared prompts, historical synthetic trials, and hand-authored controls do not count as those trials. Scripts and full responses must be retained without out-of-budget manual repairs. Nothing is pushed automatically.

The user prefers P3's morphology pending verification. P4 is an additional directly documented WC/non-WC annotation option, shown beside P2 for review; it has not silently replaced that preference. F1 preparation is complete. P3 verification remains incomplete, and no particle target is finally approved for trials.
"""


if __name__ == "__main__":
    main()
