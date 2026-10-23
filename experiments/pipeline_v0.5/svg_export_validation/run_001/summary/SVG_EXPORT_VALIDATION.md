# v0.5D1 — research-only SVG export validation

**Export-stage result: SVG_EXPORT_ROUNDTRIP_PASS_TESTED_FIXTURES.** Overall scientific status remains **HOLD_SMALL_PORE_POLICY**. This study measures added serialization error relative to the selected saved G1/G2/G3, not the physical adequacy of that source.

## Purpose and registered sources

Four saved native-1024 geometries were registered before final export execution. All source, canonical mask, native-generation manifest, earlier qualification and applicable C.1 validation hashes were authenticated. No source was regenerated, regularized, simplified, replaced or excluded. The initial inventory includes all preexisting local changes. Fixture A retains its saved 15-pixel native-generator repair in G0; it requires no A1 manifold regularization here.

| Fixture | State / reason | Vertices | Holes | Contacts |
|---|---|---:|---:|---:|
| A_G1_D9S1 | G1: No manifold regularization; exact source is already manifold. | 47382 | 412 | 0 |
| B_G2_D0S0 | G2: One recorded point-contact regularization. | 38832 | 289 | 1 |
| C_G3_D4S1_E050 | G3: Explicit saved corrected historical-failure realization, epsilon0.50, nonzero reduction; no production tolerance selected. | 35048 | 265 | 7 |
| D_G2_C1P0S12031 | G2: First saved independent realization containing documented one-cell pore186 with two-contact6.25% change. | 38928 | 289 | 6 |

## SVG representation and independent import

Each SVG has one black unstroked compound path, explicit absolute M/L/Z and `fill-rule=evenodd`. All vertices are retained; deterministic ordering changes neither edges nor occupied region. Native x-right/y-down coordinates and viewBox 0 0 1024 1024 are preserved. Width/height are unitless display values, coordinate units are raster cells, and physical scale is null.

Canonical decimal tokens use 17 significant digits. The independently structured reader opens the actual saved XML, checks its restricted contract and metadata, parses path text with a separate tokenizer/state machine, and reconstructs an indexed nesting forest using even-odd depth. It never uses original coordinates or sidecar shell/hole roles to assemble geometry. Unsupported syntax or invalid topology fails with saved evidence; no repair is performed.

Python binary64 and Shapely/GEOS are shared dependencies, so independence concerns file parsing and assembly, not a second mathematical kernel. Sharp0.35.5/libvips8.18.7/librsvg2.63.2 interprets saved SVG files for separate visual previews. Display antialiasing is not used for scientific raster comparisons.

The preregistered gates require exact binary64 vertex/edge multiplicities, geometric equals, zero added/removed/symmetric area, and zero boundary line-set difference. Winding/cyclic start/component order may differ. The area arithmetic allowance is 64×binary64 epsilon×1024² = 1.4901161193847656e-8 cell² for summation order only; it cannot forgive any changed coordinate or region. Here even the raw area discrepancies were zero.

Topology verification matches actual disjoint solid/void faces, reciprocal pore anchors and domain-side incidence. The original C filled-hole-disk helper remains unchanged and is retained as a diagnostic; it cannot disambiguate concentric nested holes in the synthetic control. Dedicated boundary ray/segment qualification supplements OGC validity.

## Continuous, topology and feature results

| Fixture | SVG bytes | Area discrepancy cell² | Symmetric cell² | Boundary upper cell | Raster XOR | Dedicated manifold | Export |
|---|---:|---:|---:|---:|---:|---|---|
| A_G1_D9S1 | 475,043 | 0 | 0 | 0 | 0 | PASS | PASS |
| B_G2_D0S0 | 389,584 | 0 | 0 | 0 | 0 | PASS | PASS |
| C_G3_D4S1_E050 | 350,963 | 0 | 0 | 0 | 0 | PASS | PASS |
| D_G2_C1P0S12031 | 388,543 | 0 | 0 | 0 | 0 | PASS | PASS |

All component counts, all 1255 enclosed pores, and exterior-connected void/domain-side relationships are preserved. All four inputs/imports retain OGC validity and dedicated manifold status. Exact coordinates and zero boundary line-set difference supply a zero boundary-displacement result, rather than a finite-sample Hausdorff assertion.

All 14 registered contact repairs preserve local solid/boundary geometry, added-solid footprints relative to G1, coordinates and positive clearance. Before/after minimum repaired clearance is 0.3535533905932738 cell. The available 96 registered normal chords also retain their widths. G3 guard material and boundary sets remain exact. No additional geometry was introduced.

## Raster and frozen morphology

Every imported file independently reconstructs G0 with FP=FN=XOR=0, IoU=1, one 4-connected solid component, largest fraction1, and both percolation directions true. The original source NPY and reconstructed arrays are separately loaded/constructed. Continuous geometry equality is checked independently of raster equality.

Fixture A received fresh frozen-v1.1 original and SVG-reconstructed evaluator calls, including all scalar descriptors and full S2/mean/directional lineal-path arrays. The other three reuse authenticated frozen results only after exact raster identity. No evaluator code, P10 definition or tolerance changed. Original v0.4.2 P10 failure and the scoped v0.4.3 qualification caveat remain.

## Precision controls and retained failures

Twenty analytic regions cover concavities, multiple components, concentric islands, exterior channels, fractional/non-dyadic coordinates, extremely short segments, 4096-vertex rings, 400 holes and manifold-regularized contacts. Full-precision outputs passed 20/20. All31 deliberate malformed, tampered, unsupported or geometry-altered cases were detected. The raster-invisible shift demonstrates that zero XOR cannot excuse continuous error.

| Significant digits | Analytic passes /20 | Parse failures | Parsed but changed | Real passes /4 |
|---:|---:|---:|---:|---:|
| 17 | 20 | 0 | 0 | 4 |
| 12 | 14 | 0 | 6 | 4 |
| 9 | 14 | 2 | 4 | 4 |
| 6 | 13 | 3 | 4 | 4 |
| 3 | 10 | 7 | 3 | 0 |

Real6/9/12-digit diagnostics happen to recover the selected integer/quarter-cell source coordinates; that does not qualify those precisions generally. Analytic non-dyadic coordinates already change at 12 digits; short edges and nearly touching boundaries can collapse at lower precision. All four real3-digit files fail on degenerate/repeated vertices. Canonical files remain17 digits and were not replaced by diagnostic outputs.

Development evidence is retained: synthetic_run_001 stopped on NumPy-scalar JSON recording; run_002 exposed the nested-hole-disk ambiguity; run_003 passes the full persisted controls. Fixes and two added tests preceded the real-study freeze. No numerical allowance or source geometry was changed.

## Inherited small-pore limitation

The selected D source retains G1 pore186 area 1.0 cell² → saved G2 0.9375 cell² → imported G4 0.9375 cell². Historical A1 loss is 0.0625 cell² (6.25%); additional SVG loss is 0.0 cell². This is preserved evidence, not a retroactive scientific PASS. The seven independent C.1 pores with6.25% loss remain part of the unresolved cumulative policy.

## Runtime and memory

Real-study elapsed time was 25.053494s across four fixtures, including authentication, export/import, comparison, feature checks, rasterization, fresh/reused evaluation, repeats and display previews. Export sum=0.717549s; import sum=0.724903s. Detailed per-stage timings are in every sidecar and the machine summary. SVG sizes range 350,963–475,043bytes.

Observed real-study process lifetime peak RSS=504.047MiB. Isolated stage tracing is separately instrumented and not added to untraced timings: export Python peaks span 12.546–19.285MiB; import peaks span 10.704–14.789MiB. Native GEOS memory and already-loaded sources are incompletely covered. These are single-run observations, not throughput guarantees.

## Software, preservation and acceptance

529 software tests passed: all 457 previous tests plus 72 new SVG tests, with zero failures/errors/skips. Execution was macOS ARM64; Windows execution and cross-platform byte identity are not claimed. Final preservation, code/protocol verification, figure inspection and the new-file hash ledger are recorded under verification/. Historical results and existing local modifications are preserved.

| Scope | Status |
|---|---|
| SVG round-trip on four registered fixtures | SVG_EXPORT_ROUNDTRIP_PASS_TESTED_FIXTURES |
| Source scientific adequacy | HOLD_SMALL_PORE_POLICY |
| Cumulative small-pore fidelity | UNQUALIFIED |
| Production simplification | HOLD_UNQUALIFIED |
| CAD-kernel interoperability / FEM / manufacturing | UNQUALIFIED |
| Physical dimensions | UNASSIGNED |

The finite four-fixture result is not a universal SVG implementation, a certificate for arbitrary SVG importers, a different CAD-kernel result, or a source geometry qualification. Arbitrary curves, transforms, styles, masks, overlapping/touching subpaths and additional primitives are unsupported and rejected. Source subpixel modifications and the finite C.1 width-audit/changed-region limitation remain. There are no physical specimen dimensions, material/load laws, mesh convergence, strength or manufacturing criteria.

## Next-stage handoff

The next proposed software milestone is a separately authorized research-only DXF interchange protocol and independent reimport study. Register representation, units/scale semantics, consumer, hole ownership, precision, acceptance and preserved source scope before implementation. It cannot promote the scientific HOLD. Before 3D, establish an accepted source/pore policy, physical dimensions, minimum clearances relative to kernel tolerances, an independently tested CAD consumer and a separate solid-construction validation protocol. No DXF, CAD kernel,3D, meshing or FEM is implemented here.

The dedicated V0_5D1_HANDOFF.md and FINAL_RESPONSE.md supply the next-stage restrictions and all46 requested completion answers. Stop at v0.5D1.

## Figures and format references

[01_raster_and_svg](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/01_raster_and_svg.png>)

[02_vector_overlay](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/02_vector_overlay.png>)

[03_continuous_difference](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/03_continuous_difference.png>)

[04_raster_difference](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/04_raster_difference.png>)

[05_pore_preservation](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/05_pore_preservation.png>)

[06_subpixel_repairs](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/06_subpixel_repairs.png>)

[07_precision_sensitivity](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/07_precision_sensitivity.png>)

[08_area_displacement](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/08_area_displacement.png>)

[09_runtime_memory](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/09_runtime_memory.png>)

[10_acceptance](</Users/saahildoshi/Library/CloudStorage/OneDrive-UniversityofGeorgia/Young-Dawgs-VSCode/experiments/pipeline_v0.5/svg_export_validation/run_001/figures/10_acceptance.png>)

Format references: [W3C SVG path data](https://www.w3.org/TR/SVG2/paths.html), [W3C even-odd fill rule](https://www.w3.org/TR/SVG2/painting.html#FillRuleProperty), [Python binary64 explanation](https://docs.python.org/3/tutorial/floatingpoint.html). The measured results above derive from saved project artifacts, not these references.

## Final preservation verification

8507/8507 preexisting files remain byte-identical; modified/missing=[]. Final code/protocol/source and figure hashes are authenticated in verification/COMPLETION.json and new_files.json. Implementation completion does not change the source scientific HOLD.
