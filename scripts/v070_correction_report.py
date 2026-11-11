"""Concise reference-review delivery; leaves the main experiment unapproved."""
import subprocess,xml.etree.ElementTree as ET
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v070_correction_setup import CORRECTION,DOC


def count(path):
    root=ET.parse(path).getroot();s=root if root.tag=='testsuite' else root.find('testsuite')
    return {k:int(s.attrib[k]) for k in ['tests','failures','errors','skipped']}


def report():
    inv=read(CORRECTION/'audit/PRIOR_EXPERIMENT_INVENTORY.json');index=read(CORRECTION/'review/CANDIDATE_INDEX.json');candidates={}
    for name,item in index['candidates'].items():candidates[name]=read(CORRECTION/item['relative_path']/'CANDIDATE.json')
    summary=[]
    for name,c in candidates.items():
        phases=', '.join(f'{k}:{100*v:.3f}%' for k,v in c['proposed_phase_fractions'].items())
        summary.append(f"| {name.split('_')[0]} | {c['material']} | `{c['crop_xyxy_end_exclusive']}` | {phases} |")
    table='| Candidate | Source material | Native crop [x0,y0,x1,y1) | Raw-label fractions |\n|---|---|---|---|\n'+'\n'.join(summary)
    entries=[]
    for r in inv['records']:
        outputs=sum(e['stochastic_outputs'] for e in r['evaluations'])
        entries.append(f"| `{r['trial_id']}` | {r['classification']} | {outputs if r['evaluations'] else 'NOT_EVALUATED'} |")
    inventory='| Existing trial/control | Evidence classification | Actual outputs |\n|---|---|---:|\n'+'\n'.join(entries)
    document=f'''# v0.7.0 experimental correction: reference review

**Status: AWAITING_USER_REFERENCE_APPROVAL.** No new LLM call, reference freeze, ANSYS execution or mechanical optimization was performed in this correction. The existing synthetic pilot is preserved as framework/control evidence; it is not the main cross-family microscopy experiment.

## Proposed reference pair

Recommended review pair: **P1 + F1**. P2 and F2 are alternatives. These are proposals, not approved scientific targets. The proposed regions are native256×256 pixels with no resizing, thresholding, cleanup or phase merging. Larger source fields and raw categorical annotations are retained alongside the crops.

![Proposed microscopy reference pair](../../../experiments/pipeline_v0.7.0/reference_correction_001/review/PRIMARY_REFERENCE_REVIEW.png)

![Alternatives](../../../experiments/pipeline_v0.7.0/reference_correction_001/review/ALTERNATIVE_REFERENCE_REVIEW.png)

{table}

P1 is from `sem1000_x768_y256_HorizontalFlip.bmp`. Its256px ROI is [136,80,392,336). It shows the coarse-carbide boundary, reaction/dilution region, finer precipitates and a pore. The ROI was selected from an8px grid to retain all native classes while minimizing source-to-crop phase-fraction change. It contains a partial coarse carbide, so it cannot establish a reliable complete-particle diameter distribution or an RVE. Edge-touching objects, including pores, must be censored in object-size measurements.

F1 is original DatasetI `2_3_2_L_cut_128_15616.tif`, with its author-supplied PNG annotation. DatasetI is explicitly C/PEEK in the README. This field is close to the median phase-fraction vector among DatasetI tiles with0.5%-10% annotated void. It includes45.270% fiber and1.958% void. The entire native256px tile is used. The nominal3px-radius fiber sections offer many instances but limited contour resolution.

P2 is a native central crop of `sem600_x0_y0_HorizontalFlip.bmp`. It provides an alternative field at lower stated acquisition magnification and more fine-carbide geometry; its source has no label2 pore annotation. F2 is test tile `2-6-1_mid_768_1792.jpg`, with larger nominal7px-radius fiber sections and1.337% annotated void. It is easier to inspect visually, but the supplied README does not establish a filename-to-polymer subtype map for this test tile. No exact PEEK/LM-PEAK attribution is invented for F2.

## Provenance and phase interpretation

Ni-WC source: Mutahar Safdar(2025), [SEM dataset, Zenodo17315241](https://zenodo.org/records/17315241), DOI10.5281/zenodo.17315241, **CC BY4.0**. The supplied image and mask archives match both published MD5 checksums. The archive contains405 augmented tiles derived from a smaller set of source regions. Selection excludes elastic/grid distortion variants and uses only geometry-preserving horizontal flips. These are supplied augmented scientific SEM crops, not untouched full acquisition micrographs. Neighboring crops overlap; augmentation variants cannot be counted as independent specimens.

The associated [materials-characterization publication](https://doi.org/10.1016/j.matchar.2025.115645) identifies matrix, porosity, carbide, dilution and reprecipitation classes. Downloaded masks use IDs1–5, whereas the described training class order is zero-based. The displayed names map native1→matrix,2→void,3→carbide,4→dilution and5→reprecipitated carbide. **This offset mapping is inferred from the published order and paired visual inspection; an explicit export legend was not bundled. It remains provisional until independently confirmed.** No native ID has been changed. Raw0, if encountered elsewhere, remains unknown/unassigned and is never silently treated as matrix. The annotation classes include material regions rather than five independently calibrated mechanical materials.

Fiber source: Merit Fernhout(2023), [4TU dataset](https://doi.org/10.4121/bf11171a-1f57-4a8a-9768-757850d13665), independently described by the [University of Twente](https://research.utwente.nl/en/datasets/annotated-images-of-microscopy-images-from-carbon-fibre-composite-2/), **CC0_1.0**. The original archive and inner archive are SHA256-bound; no unobserved published checksum is claimed. The author README explicitly defines **0=matrix,1=fiber,2=void**. Original image tiles are used instead of augmentation variants.

These are **transverse sections of fibers**. Their2D component diameters/packing can be measured; their longitudinal fiber lengths, curvature and in-plane orientation distribution cannot be recovered from these images. The author located centers and drew circles using an average radius; voids came from minimum-based thresholding. Therefore the masks are approximate annotations, not exact measured physical fiber contours. This uncertainty must carry into any LLM accuracy claim.

Neither selected source establishes a calibrated micrometers-per-pixel value in the supplied tile metadata/README. Rulers are labeled **pixels**. Magnification, image DPI and nominal fiber radius are not substituted for physical calibration. No material properties, physical specimen dimensions or stress–strain values were assigned.

## Honest inventory of the preceding setup

{inventory}

- **NON_LLM_PROCEDURAL_BASELINE:** two researcher/Codex-authored implementation controls,40 executed outputs total across development/held-out seeds. These are not independent experimental ChatGPT generations.
- **One verified returned experimental LLM script:** `particle_A_01`, a genuine ordinary ChatGPT call, with10 development and10 held-out outputs. Its target was synthetic, so this is only the preceding synthetic pilot.
- **One additional genuine submitted chat:** `particle_A_02`, URL recorded and submission verified in the preceding UI session. Its response was not ingested, so it is not counted as a second captured/evaluated generator.
- **Ten unused initial prompt packets:** remaining particle B/C and all fiber A/B/C prompts. Zero feedback calls and zero real-micrograph LLM trials.
- Analytical fixtures, metric tests, baseline runs, prepared prompts and source-code infrastructure are not relabeled as LLM experiments.

All preceding scripts, responses, reference pixels, outputs and verification files are hash-inventoried in `audit/PRIOR_EVIDENCE_HASHES.json`. The only pending prior-turn change at correction start was the A02 submission metadata; it was committed as preserved evidence rather than reset. Synthetic reference arrays remain immutable controls and will not be promoted to corrected primary targets.

## Authorized model interface and next executable plan

The ordinary ChatGPT browser interface was genuinely used for A01 and A02; no API credential or paid external endpoint was required. The UI exposed “ChatGPT” and “High”, not a verified backend/model version. Tokens and cost were unavailable. Normal Chat mode was used, not Codex or Work. Exact model/version must remain unavailable unless the UI exposes it. Ordinary-chat personalization/memory and backend routing were not independently controlled.

See `NEXT_PILOT_PLAN.md`. The existing worker assumes binary0/1 labels and the old fiber evaluator assumes longitudinal components. **They are not ready for these corrected references.** Approval must precede any new frozen targets or actual main experiment. After approval, categorical validators and transverse-fiber measurements must be independently checked, Ni-WC export IDs confirmed or retained as explicitly provisional, then prompts can be frozen. No automatic experiment starts from this delivery.

## Verification and preservation

Exact-crop tests verify source-mask SHA256, native array equality, retained class sets, nonzero voids, no invented physical scale, figure hashes and the approval gate. Prior evidence hashes are unchanged. Full active and archived replay results, when completed, are recorded in `verification/TEST_SUMMARY.json`; passing integrity tests do not imply an LLM microscopy reconstruction result.

No original full specimen, contact repair, crop compression or solver execution was attempted. The previous mechanics status remains `HOLD_CONTACT_ONSET__POLYMER_CROP_NOT_EXECUTED__THIRTY_PERCENT_NOT_ACHIEVED`. Nothing was pushed. Exact commits through the evidence phase are in the review handoff; the final reporting commit is supplied with the final response.

**Decision required:** approve P1+F1, choose P2 and/or F2, or request a different native region. The displayed Ni-WC names are provisional. This correction stops at reference review.
'''
    (DOC/'V0_7_0_REFERENCE_CORRECTION.md').write_text(document,encoding='utf-8',newline='\n')
    (DOC/'NEXT_PILOT_PLAN.md').write_text('''# Proposed next pilot - not authorized to execute yet

1. Receive explicit approval of source image/annotation pair and native256px region for each material. Preserve the approval text and exact selected hashes. Confirm the provisional Ni-WC raw-ID export mapping against authoritative documentation or explicitly retain its uncertainty. Do not silently relabel or merge phases.
2. Replace the binary-only execution contract with a family-specific categorical schema. Ni-WC native1–5 distinguishes matrix,void,WC,dilution and reprecipitates; raw0 remains unknown. Carbon cross-sections use0matrix,1fiber,2void. Both matrix and reinforcement are solids;void is not. No unknown class or void-to-matrix conversion passes validation.
3. Validate per-class fraction,finite-field two-point correlation,phase-pair interface counts and component/censoring calculations on known categorical fixtures. For transverse fibers use cross-section diameter,packing,spacing and void descriptors. Do not use longitudinal fiber length/curvature/in-plane orientation metrics. For a partial coarse carbide,complete-particle size metrics stay unavailable. Compare against supplied annotations with segmentation uncertainty,not a claim of perfect physical ground truth.
4. Freeze visible descriptors,blind descriptors,stable error scales and family hard constraints before collecting corrected-trial outcomes. Do not import the old matrix-percolation/multiple-object policy blindly: a finite crop may legitimately have clipped particles or interrupted matrix paths. Phase-fraction/statistical mismatch is distinct from hard output validity.
5. Prepare matched A/B/C packets only after approval. Proposed A:the same approved micrograph and categorical phase panel as visual guidance,phase legend and interface requirements,without numerical targets. B:identical images/instructions plus preselected measured descriptors. C:identical initial B information plus one controlled development-feedback revision. The target-generation algorithm,reference arrays and holdout scores are never provided for runtime access. If using only the raw micrograph instead of a two-panel visual target,freeze that choice equally across conditions and document annotation ambiguity.
6. Use fresh ordinary ChatGPT chats for independent initial calls. Keep the same exposed model/effort configuration;record any routing/version uncertainty. Proposed finite pilot:two independent scripts per family per A/B/C condition (12 initial calls) and one revision for each C script (four additional calls maximum). Existing synthetic scripts are not reused as independent corrected trials. No API keys in prompts,code or Git. If browser access is unavailable,export the approved image packets and exact prompts for manual ordinary ChatGPT execution;mark unexecuted rows NOT_RUN.
7. Preserve complete response/source before execution. The preceding session demonstrated that the ordinary message-copy control can truncate a virtualized code preview. Use complete source selection/copy in the code editor and save the unedited module,then hash the capture. Do not repair failed code outside the registered revision budget. Retain URL,submission/capture times,available model identity,full prompt,feedback and code hash. Current response-ingestion tools can preserve captures but require the new categorical validator before corrected-trial execution.
8. Freeze disjoint development and held-out seeds prospectively;proposed100–109 development and0–9 final. Evaluate each standalone module under fixed runtime limits;review for embedded reference pixels,I-O,network,global RNG and import-time generation. Record failures and deterministic reruns. Use the development group for feedback;do not inspect or expose held-out scores before final code freezes.
9. Analyze script-level means as the independent units,with seeds nested. Show validity,visible/hidden descriptor errors,diversity and runtime separately. Condition C has extra iteration opportunity;without an equal-attempt no-feedback control,do not claim feedback alone caused a difference. Adjacent/augmented microscopy tiles are not independent material specimens. One approved field per material supports a small pilot,not broad cross-family generalization or statistical power claims.
10. Export phase roles,source/image/code/label hashes and unknown physical scale in a later mechanics-ready design record. Begin any subsequent mechanics milestone with calibrated small-strain homogeneous/two-phase benchmarks,not contact repair or30–40% compression. No mechanical experiment or autonomous optimizer is part of this correction.

Current gate: AWAITING_USER_REFERENCE_APPROVAL. No corrected-trial prompts have been submitted. The executable next action is to record the user's selected pair/regions,then implement and test the categorical evaluation contract before model collection.
''',encoding='utf-8',newline='\n')
    tests={}
    for key,name in [('correction','correction.xml'),('active','active.xml')]:
        path=CORRECTION/'verification'/name
        if path.exists():tests[key]=count(path)
    ar=[count(p) for p in sorted((CORRECTION/'verification/archived_replay').glob('*.xml'))]
    if ar:tests.update(archive_groups=len(ar),archive_total=sum(x['tests'] for x in ar),archives=ar)
    for item in [v for v in tests.values() if isinstance(v,dict) and 'tests' in v]+ar:assert not item['failures'] and not item['errors']
    write(CORRECTION/'verification/TEST_SUMMARY.json',tests)
    log=subprocess.check_output(['git','log','--reverse','--format=%H%x09%s','b6c94955886b49385c623c09005d32832dd82a9b..HEAD'],cwd=REPO,text=True).splitlines()
    commits=[{'hash':s.split('\t',1)[0],'message':s.split('\t',1)[1]} for s in log]
    write(CORRECTION/'audit/COMMITS_THROUGH_EVIDENCE.json',{'starting_head':'b6c94955886b49385c623c09005d32832dd82a9b','commits':commits,'no_push':True,'final_reporting_commit':'Supplied in terminal handoff;not self-referential'})
    checks=f"{tests.get('active',{}).get('tests','PENDING')} active checks;{tests.get('archive_total','PENDING')} archived checks across{tests.get('archive_groups','PENDING')} groups;10 focused correction checks included in the active total. Categories are separate and overlapping,not new scientific trials."
    (DOC/'HANDOFF.md').write_text('# Reference-review handoff\n\nStatus: **AWAITING_USER_REFERENCE_APPROVAL**. Recommended P1+F1;alternatives P2+F2. See [full review](V0_7_0_REFERENCE_CORRECTION.md) and [next executable pilot plan](NEXT_PILOT_PLAN.md).\n\nCurrent experiment inventory: two NON_LLM_PROCEDURAL_BASELINE scripts/40 outputs;one verified returned ordinary-ChatGPT script/20 outputs on a synthetic target;one additional submitted but uningested chat;ten unused prompt packets;zero feedback calls;zero real-microscopy LLM trials. All previous evidence retained.\n\nChecks: '+checks+'\n\nExact commits through evidence phase:\n\n'+'\n'.join(f"- `{c['hash']}` — {c['message']}" for c in commits)+'\n\nThe final report commit is supplied in the terminal handoff. No push. Full source archives remain in Downloads;selected original image/mask bytes,exact cropped categorical labels,phase/provenance manifests,screening indices and review images are versioned. Corrected references remain unapproved and no new experiment is launched.\n',encoding='utf-8',newline='\n')
    print('Prepared concise correction review,inventory and approval-gated executable plan',flush=True)


if __name__=='__main__':report()
