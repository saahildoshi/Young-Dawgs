# YOUNG DAWGS — PIPELINE v0.5C
# Independent Scientific Validation and Continuous Geometry Fidelity Qualification

## ROLE AND MISSION

You are acting as a senior computational geometry engineer, scientific software architect, and computational materials research developer.

You have full read and write access to the Young Dawgs research repository.

Your assignment is to implement and execute:

**Pipeline v0.5C — Independent Scientific Validation and Continuous Geometry Fidelity Qualification.**

The preceding stages have established a functional geometry conversion pipeline:

1. Native high-resolution procedural generation.
2. Exact raster-to-vector conversion.
3. Optional manifold contact qualification.
4. Feature-protected boundary simplification.

Your responsibility is to determine whether the resulting geometries preserve the original microstructures sufficiently well, within explicitly defined and independently tested limits, to justify advancing to 2D geometry export and subsequent CAD development.

This is not a request to improve the appearance of generated images.

This is not a request to maximize vertex reduction.

This is not a request to modify the generator, geometry construction, or simplification algorithm until they pass.

**Your responsibility is to independently validate the existing algorithms, identify their limitations, and issue an evidence-based scientific acceptance decision.**

IMPLEMENT v0.5C ONLY.

Do not implement v0.5D, STEP, STL, 3D extrusion, FEM, or manufacturing analysis.

---

# 1. RESEARCH BACKGROUND

The Young Dawgs project investigates whether large language models can infer procedural morphology generators from reference microstructures and create controllable families of disordered metamaterials.

The long-term research objective is to investigate relationships between microstructure geometry and mechanical performance.

The intended overall workflow is:

Reference image
→ LLM-derived procedural generator
→ Parametric exploration
→ Native high-resolution generation
→ Exact vector geometry
→ Manifold-qualified geometry
→ Protected simplification
→ Scientific validation
→ 2D geometry export
→ 3D CAD
→ FEM
→ Structure-property analysis.

The current milestone is scientific validation of the complete two-dimensional geometry conversion process.

A successful result should provide a defensible geometric foundation for later engineering analysis.

A successful result does NOT demonstrate mechanical strength or manufacturability.

---

# 2. PREVIOUS PIPELINE MILESTONES

## v0.3 — Parametric exploration

Procedural generation with controls including:

- `solid_fraction_target`
- `strut_scale`
- `pore_scale`
- random seed

The pipeline explores different parameter combinations rather than producing identical copies of the reference morphology.

The existing exploration used ten Latin-hypercube design points with stochastic replicates.

Inspect the repository to confirm the exact plan, seeds, and available artifacts.

## v0.4–v0.4.3 — High-resolution generation

Native generation at multiple resolutions.

Established:

- Reproducibility.
- Preservation of the 256 baseline.
- Connected-network topology.
- High-resolution descriptor convergence.
- Amended lower-tail thickness qualification.

The original v0.4.2 P10 calibration failure remains historical evidence.

The amended v0.4.3 acceptance is limited to its tested domain.

Do not alter either result.

## v0.5A — Exact vector geometry

Converted occupied raster cells into exact planar geometry.

Demonstrated:

- Exact occupied-cell area.
- Correct boundary extraction.
- Hole identification.
- Zero-error raster reconstruction.
- Preservation of raster topology.

Some exact geometries retain inherent non-manifold contacts.

The historical v0.5A HOLD remains unchanged.

## v0.5A.1 — Optional manifold candidates

Identified genuine boundary point contacts and introduced separately recorded local solid-side regularizations.

The exact source remains immutable.

The optional manifold-candidate workflow received AMENDED PASS within the tested domain.

Subpixel modifications were explicitly recorded.

## v0.5B1 — Simplification sensitivity

Evaluated ordinary Douglas–Peucker simplification over five representative geometries.

Found that substantial vertex reduction is possible but that ordinary simplification can alter continuous geometry and narrow features without changing the 1024 raster reconstruction.

## v0.5B2 — Feature-protected simplification

Implemented deterministic, guarded simplification with local proposal rejection and rollback.

Its final study produced:

**GEOMETRIC_SCREEN_PASS_TESTED_DOMAIN**

across 50 configurations.

Broader scientific sufficiency and production-policy qualification remain HOLD / UNQUALIFIED.

The purpose of v0.5C is to evaluate that remaining scientific qualification.

---

# 3. AUTHORITATIVE v0.5B2 RESULTS

The completed B2 study evaluated:

- Five development fixtures.
- Five holdout fixtures.
- Five tolerance settings per fixture.
- 50 final configurations.
- 25 development configurations.
- 25 reserved holdout configurations.

Results:

- 20 accepted changed candidates.
- 30 accepted no-ops.
- All 50 passed the registered geometric screens.
- All accepted outputs remained OGC-valid and manifold.
- No detected pore merges, splits, or deletions.
- No detected exterior-channel changes.
- No severed registered solid connections.
- Zero raster reconstruction disagreement.
- Exact frozen-evaluator descriptor equality.

## Feature protection

All 47 registered manifold repairs retained their original material and recorded clearance:

`0.3535533905932738 cell`

All 240 supported natural-width probes retained their measured widths and local connections.

Both saved connector depths remained 5 pixels.

All 137,475 recorded guard evaluations preserved the required local geometry and protected coordinates.

These findings are limited to the instrumented features.

They do NOT establish that every neck, strut, pore boundary, or microscopic geometric feature was independently verified.

## Continuous geometry changes

Maximum reported added material:

`603.25 cell²`

Maximum reported removed material:

`603.25 cell²`

Maximum symmetric difference:

`1,206.5 cell²`

Maximum cumulative exact-source-to-final symmetric difference:

`1,206.5625 cell²`

Maximum reported measured boundary displacement and evaluated bound:

approximately `0.685365 cell`

The existing B2 protocol included a documented numerical allowance of `1e-10 cell`.

Do not silently enlarge that numerical allowance.

Net occupied area and matched pore areas remained unchanged under the reported comparisons, but local boundary geometry changed.

## Complexity reduction

At epsilon 0.50, the observed vertex reductions were approximately 7.37%–9.69%, depending on the fixture.

At epsilon 0.75, reductions were approximately 5.13%–7.17%.

Higher tolerance did not necessarily produce more reduction because the feature guards and rejection mechanisms became more restrictive.

Do not assume monotonicity.

## Performance

The final 50-setting study took approximately 589 seconds.

Including retained earlier development work, execution took approximately 873 seconds, excluding reporting and development.

Peak traced allocation:

approximately 86.8 MiB.

Peak process RSS:

approximately 742.5 MiB.

Python tracing excludes some native GEOS memory.

## Software verification

363 tests passed:

- 316 existing tests.
- 47 new B2 tests.

All 3,719 previously existing project files remained byte-identical.

No v0.5C implementation exists yet.

---

# 4. PRIMARY SCIENTIFIC QUESTION

Determine:

**Does the complete geometry-conversion pipeline preserve the original microstructure's relevant continuous and discrete geometric properties sufficiently well, within predefined limits, across a broader portion of the existing parametric design space?**

Separate this into four questions.

### Question A — Discrete fidelity

Does the final geometry reconstruct the original binary microstructure without changing its occupancy and measured raster morphology?

### Question B — Continuous fidelity

Does the final planar region remain sufficiently close to the original exact geometry in material distribution, boundary position, topology, and feature shape?

### Question C — Feature preservation

Are the known protected regions preserved, and do broader independent checks reveal previously unmonitored narrow regions or geometric defects?

### Question D — Generalization

Do the established methods work on previously unused design-space parameter combinations rather than only on the five points used during B1/B2 development?

Do not substitute success on one question for success on another.

---

# 5. FIRST PHASE — COMPLETE REPOSITORY AUDIT

Before changing code, inspect the actual repository.

Read:

`docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_VALIDATION.md`

`docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_PROTOCOL.md`

`docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_ARCHITECTURE.md`

`docs/pipeline_v0.5/V0_5B2_HANDOFF.md`

`docs/pipeline_v0.5/SIMPLIFICATION_SENSITIVITY.md`

`docs/pipeline_v0.5/V0_5B2_DESIGN_RECOMMENDATION.md`

`docs/pipeline_v0.5/CONTACT_POLICY.md`

`docs/pipeline_v0.5/MANIFOLD_QUALIFICATION.md`

Read the complete B2 experiment results:

`experiments/pipeline_v0.5/protected_simplification/run_002/summary/ACCEPTANCE.md`

Inspect the saved candidate geometries, manifests, source hashes, verification records, and test suites.

Also inspect the original v0.3 Latin-hypercube design plan and the existing native 1024 outputs.

Verify actual paths.

Do not assume the files listed above are the complete source of implementation details.

## Audit deliverable

Before implementing anything, produce a short architecture and validation plan.

Identify:

1. Canonical binary source format.
2. Exact vector geometry format.
3. Saved manifold candidate format.
4. Protected simplified geometry format.
5. Existing serialization methods.
6. Independent rasterization options.
7. Frozen evaluator interface.
8. Existing topology and pore-matching functions.
9. Continuous geometry comparison functions.
10. Existing width and repair diagnostics.
11. Source and output hash conventions.
12. Available independent parameter combinations.
13. Existing software tests.
14. Areas where current validation reuses the same algorithm as the implementation being validated.

The final item is critical.

A validator that repeats the same algorithm may reproduce the same defect rather than independently detect it.

---

# 6. STRICT SOURCE PRESERVATION

Do not modify:

- The procedural generators.
- Existing parametric bounds.
- Native-resolution generation behavior.
- Frozen evaluator v1.1.
- Historical v0.4 records.
- v0.4.3 qualification records.
- v0.5A exact geometries.
- v0.5A.1 manifold candidates.
- v0.5B1 experiments.
- v0.5B2 source outputs and accepted candidates.
- Existing scientific acceptance decisions.

Prefer additive implementation.

If a verification tool discovers a defect in an earlier algorithm, do not silently fix that algorithm and continue.

Record the defect and determine whether it invalidates the current qualification.

Any required correction to a prior pipeline stage must be handled as a separately versioned change.

---

# 7. DEFINE FOUR GEOMETRY STATES

Every validation case must preserve four distinct representations.

## G0 — Canonical raster

The native 1024 binary microstructure.

- uint8.
- Values 0 and 1.
- Solid = 1.
- Void = 0.

## G1 — Exact vector representation

The exact pixel-cell solid region from v0.5A.

It preserves original cell geometry.

It may have non-manifold contacts.

## G2 — Manifold-qualified candidate

The separately recorded v0.5A.1 output.

It may contain explicitly documented subpixel additions.

## G3 — Protected simplified candidate

The v0.5B2 output.

It may have bounded continuous geometric differences relative to G2.

## Required comparisons

Calculate:

- G0 versus rasterization of G1.
- G0 versus rasterization of G2.
- G0 versus rasterization of G3.
- G1 versus G2 in continuous geometry.
- G2 versus G3 in continuous geometry.
- G1 versus G3 in continuous geometry.

Report G1→G2 and G2→G3 errors separately.

Also report cumulative G1→G3 error.

Do not assume componentwise errors simply add; calculate the actual final geometric differences.

Do not conflate pixel equality with continuous geometry equality.

---

# 8. INDEPENDENT VALIDATION ARCHITECTURE

Build a validation layer that is logically separated from the generation and simplification implementations.

The validator may reuse stable, frozen scientific definitions and trusted geometry interfaces, but it should not derive every conclusion from the same internal functions that produced the candidate.

Use independent checks wherever practical.

Examples:

- Load saved geometry from serialized files rather than only evaluating in-memory objects.
- Reconstruct the planar region from saved coordinates.
- Independently rasterize the saved geometry.
- Recalculate area using a separate supported method.
- Verify ring orientation and closure.
- Independently inspect boundary topology.
- Recalculate hole correspondence.
- Cross-check geometric differences.
- Independently sample boundary displacement.
- Compare file hashes before and after validation.

Document which tests are truly independent and which share implementation components.

Do not claim mathematical independence when both checks depend on the same library function or geometry representation.

The objective is layered verification, not unnecessary duplicate code.

---

# 9. VALIDATION SET DESIGN

The existing B2 holdouts used different seeds at the same five parameter positions as development.

That is useful evidence of stochastic generalization.

It is not strong evidence of generalization to new parameter combinations.

v0.5C must explicitly address this limitation.

## Existing design points

The prior parametric exploration reportedly included ten Latin-hypercube designs.

B2 used design indices:

- 0
- 1
- 2
- 5
- 9

Inspect the original design plan.

If all ten design indices exist as expected, prioritize the remaining parameter combinations:

- Design 3.
- Design 4.
- Design 6.
- Design 7.
- Design 8.

Prefer both registered stochastic replicates for each.

This would provide up to ten additional structures covering five previously unused parameter positions.

Verify their actual availability.

Do not invent design files, parameters, or hashes.

## Independent cohort protocol

Before examining final performance on these designs:

1. Register the exact designs and seeds.
2. Register the candidate selection procedure.
3. Freeze the B2 algorithm version.
4. Freeze the manifold policy.
5. Freeze the relevant geometry budgets.
6. Freeze the validation metrics.
7. Freeze the acceptance decision logic.
8. Record all source hashes.

Do not use these previously unused parameter positions to tune the simplifier.

## Missing artifacts

If exact or manifold geometry files do not yet exist for the selected structures, the v0.5C workflow may construct new derived artifacts using the existing frozen v0.5A and v0.5A.1 algorithms.

Store these only in new v0.5C experiment directories.

Authenticate original raster sources.

Do not regenerate source microstructures when the saved canonical arrays already exist.

Do not alter the v0.5A or v0.5A.1 algorithms.

Any new contact or unsupported geometry must be reported and handled using the existing policy.

Do not force every structure to pass.

## Scope of generalization

Even if all these new parameter combinations pass, that establishes evidence only within the current sampled design domain.

It is not universal proof for arbitrary metamaterials, resolutions, or geometric topologies.

---

# 10. VALIDATION CONFIGURATIONS

The complete end-to-end cohort should exercise more than one simplification configuration.

At minimum include:

- Exact/no-simplification baseline.
- A conservative nonzero simplification setting.
- Epsilon 0.50.
- Epsilon 0.75 as a stress setting.

Use the existing frozen B2 interpretation of these settings.

Do not assume epsilon 0.75 should produce more vertex reduction than epsilon 0.50.

Do not choose the best setting after inspecting independent holdout performance and then claim it was prospectively validated.

Report every tested configuration.

A separate exploratory comparison may identify promising future production settings, but its conclusions must remain explicitly exploratory.

---

# 11. PREDECLARED SCIENTIFIC ACCEPTANCE PROTOCOL

Before final validation, write and freeze a scientific acceptance protocol.

Reuse the existing B2 hard constraints and numerical budgets without loosening them.

The reported B2 prospective limits included:

- Exact protected geometry.
- Zero registered width loss.
- Zero registered repair-clearance loss.
- Added solid area ≤0.25% of occupied solid area.
- Removed solid area ≤0.25% of occupied solid area.
- Symmetric-difference area ≤0.5%.
- Per-pore area distortion ≤0.5%.
- Boundary displacement bound ≤sqrt(2)/2 cell.
- Zero raster disagreement.
- Exact frozen-evaluator descriptor equality.

Verify the exact definitions and denominators from the repository's frozen protocol.

Do not silently reinterpret relative area percentages.

Retain the documented numerical tolerance for floating-point comparisons.

Do not raise tolerances to accommodate newly observed results.

## Additional v0.5C checks

Define the following before final testing:

- Independent serialization/reconstruction correctness.
- Continuous area consistency.
- Continuous topology preservation.
- Hole correspondence robustness.
- Exterior-channel integrity.
- Boundary displacement cross-check.
- Feature-screen coverage reporting.
- New manifold-contact detection.
- Unsupported-geometry handling.
- Full provenance completeness.
- Deterministic reproduction.

Where possible, use hard criteria for objectively defined failures.

Where no scientifically justified numerical threshold exists, report the property as diagnostic or unqualified rather than inventing a convenient acceptance number.

---

# 12. INDEPENDENT SERIALIZATION VALIDATION

The geometry will eventually be exported to CAD-compatible formats.

Therefore, v0.5C must validate the existing canonical geometry serialization.

For every selected candidate:

1. Load the original saved geometry.
2. Record its canonical hash.
3. Serialize using the registered format.
4. Reload using the supported parser.
5. Independently compare with the original.
6. Recalculate geometric area.
7. Recalculate topology.
8. Recalculate hole count.
9. Recalculate manifold status.
10. Rasterize the reloaded geometry.
11. Compare against the canonical mask.

Check:

- Geometry component count.
- Ring count.
- Hole count.
- Ring closure.
- Coordinate orientation.
- Coordinate precision.
- Material area.
- Boundary topology.
- Reconstructed occupancy.

Do not claim successful future STEP/DXF interoperability from successful internal serialization alone.

No SVG, DXF, STEP, or STL export is required in v0.5C.

---

# 13. DISCRETE MORPHOLOGY VALIDATION

For each candidate, independently rasterize onto the native 1024 grid.

Use the established coordinate convention:

Pixel (row, column) occupies:

`[column,column+1] × [row,row+1]`

The x-axis points right.

The y-axis points down.

Record:

- Input solid-pixel count.
- Reconstructed solid-pixel count.
- False positives.
- False negatives.
- XOR disagreement.
- IoU.
- Solid connected components.
- Largest-component fraction.
- Horizontal percolation.
- Vertical percolation.

For the existing B2 accepted outputs, the registered requirement is zero raster disagreement.

Do not relax it.

If any final candidate differs from the source raster, record the failure.

Do not replace the original mask.

---

# 14. FROZEN MORPHOLOGICAL DESCRIPTORS

Reuse evaluator v1.1 without modification.

For every valid reconstructed mask, compare:

- Solid fraction.
- Component count.
- Largest-component fraction.
- Left-right percolation.
- Top-bottom percolation.
- Mean local strut thickness.
- P10 thickness.
- Median enclosed-pore diameter.
- Two-point correlation S2.
- Lineal-path function L.

Retain the historical P10 measurement-qualification caveat from v0.4.3.

Do not redefine P10.

Do not invent a corrected P10 under the frozen metric name.

## Important interpretation

When two binary masks are exactly identical, all deterministic frozen-evaluator descriptors should also match.

That equality is a consistency check.

It is not independent evidence that continuous vector geometry is unchanged.

The central additional scientific contribution of v0.5C must therefore come from continuous-geometry validation, feature inspection, and broader design-space testing.

---

# 15. CONTINUOUS AREA FIDELITY

For G1, G2, and G3, independently calculate:

- Total solid area.
- Signed net area change.
- Added solid area.
- Removed solid area.
- Symmetric-difference area.
- Relative symmetric-difference area.
- Exterior boundary length.
- Total internal boundary length.
- Per-pore area.
- Per-pore perimeter.
- Per-pore shape change where robustly measurable.

For material changes:

`A_added = area(G_final \ G_reference)`

`A_removed = area(G_reference \ G_final)`

`A_symmetric = A_added + A_removed`

Do not use net area difference as a substitute for material redistribution.

The B2 experiments demonstrated that material additions and removals can nearly cancel while boundary shapes change.

Report:

- Exact-to-manifold changes.
- Manifold-to-simplified changes.
- Exact-to-final changes.

The exact-to-final comparison is particularly important for scientific reporting because it includes the manifold regularizations.

---

# 16. BOUNDARY DISPLACEMENT VERIFICATION

Independently verify the registered B2 boundary displacement claims.

Use the actual source and final continuous boundaries.

Calculate or rigorously bound:

- Maximum directed boundary distance, source to candidate.
- Maximum directed boundary distance, candidate to source.
- Symmetric boundary Hausdorff distance or a justified bound.
- Local repair-region displacement.
- Exterior-boundary displacement.
- Enclosed-pore boundary displacement.

Document the numerical method.

If the method uses sampled points, clearly state that a sampled maximum is not necessarily the exact continuous maximum.

If the existing implementation provides a certified bound, inspect its assumptions and independently test representative cases.

Retain the registered B2 displacement ceiling:

`sqrt(2)/2 cell`

Do not silently expand it.

## Required controls

Construct deterministic analytic geometries for which boundary displacement is known or can be bounded independently.

Examples:

- Parallel shifted line segments.
- Simplified right-angle staircase.
- Triangle boundary replacement.
- Polygon with a known displaced edge.
- Narrow channel boundaries.

Test that the validator detects both compliant and noncompliant displacements.

---

# 17. CONTINUOUS TOPOLOGY VERIFICATION

Evaluate the planar solid independently of the source raster topology.

Check:

- OGC validity.
- Dedicated manifold boundary.
- Number of solid components.
- Enclosed-hole count.
- Hole identity correspondence.
- Unexpected hole splits.
- Unexpected hole merges.
- Hole deletion.
- Hole creation.
- External void-channel connectivity.
- Pinched boundaries.
- New point contacts.
- Overlapping boundary segments.
- Zero-width connections.
- Unexpected geometrical slivers.

Do not assume that zero raster XOR guarantees continuous topology preservation.

Do not assume OGC validity establishes manifoldness.

Use the existing manifold classifier and supplement it with independent local-topology checks where feasible.

Report whether a failure is:

- Original exact-geometry singularity.
- Manifold-construction failure.
- Simplification failure.
- Serialization failure.
- Validation-tool failure.

Do not treat these as equivalent.

---

# 18. PORE CORRESPONDENCE VALIDATION

The project currently reports matched pore preservation.

v0.5C should independently assess the robustness of that claim.

For each enclosed pore:

1. Identify the source pore.
2. Identify the corresponding candidate pore.
3. Confirm unique correspondence.
4. Compare areas.
5. Compare perimeters.
6. Compare boundary position.
7. Check containment.
8. Check adjacency relationships where available.
9. Detect merges, splits, additions, or deletions.

Do not assume two pores correspond merely because they have similar area.

Use a justified combination of geometric overlap, containment, topology, and source identity.

Where correspondence is ambiguous, report ambiguity.

Do not fabricate a one-to-one match.

## Independent stress tests

Include:

- Two nearby pores with similar area.
- Two pores whose boundaries move without changing area.
- One pore split into two.
- Two pores merged.
- One deleted pore.
- One added pore.
- A narrow pore near an exterior channel.
- A contact-regularized pore pair.

Verify that the validation system detects these changes.

---

# 19. FEATURE AND NECK PRESERVATION

The B2 algorithm protected registered repair regions and narrow-feature probes.

All 47 repairs and 240 natural probes passed the reported study.

However, these are finite selected samples.

They do not guarantee that every feature is protected.

v0.5C should add an independent feature-coverage audit.

## Required audit

Determine:

- What fraction of candidate boundary was covered by guards.
- What fraction of potentially narrow regions was instrumented.
- Which narrow regions were not explicitly probed.
- Whether feature detection is biased toward previously known repair sites.
- Whether unguarded boundaries contain small separations.
- Whether new narrow features appeared after simplification.
- Whether any existing critical link became narrower outside the registered probes.

Where reliable, use complementary methods:

- Distance-transform-based thickness.
- Skeleton or medial-axis screening.
- Vector-space near-boundary queries.
- Local bottleneck inspection.
- Independent probe locations.

Do not assert mechanical significance from purely geometric measurements.

## Feature-screen limitations

If exhaustive minimum-neck verification is computationally infeasible or mathematically unresolved, report the limitation.

Do not substitute finite probe success for exhaustive certification.

Differentiate:

- Registered-feature preservation.
- Broader sampled-feature preservation.
- Exhaustive continuous-width certification.

The first two may be established.

The third must not be claimed without suitable evidence.

---

# 20. SUBPIXEL MANIFOLD REPAIR AUDIT

The manifold candidates contain local regularizations introduced to resolve genuine point contacts.

These modifications are part of G2 and G3 but not G1.

For each registered repair, validate:

- Original contact location.
- Original contact classification.
- Added-material geometry.
- Exact repair footprint.
- Positive boundary clearance.
- Preservation after simplification.
- Local material difference.
- Local boundary displacement.
- Nearby hole topology.
- Neighboring narrow-feature geometry.

The registered clearance for the existing repairs is approximately:

`0.3535533905932738 cell`

Do not assume every new parameter combination has exactly that same clearance without checking.

New cases may expose different contact configurations.

## Critical limitation

A subpixel positive clearance is not necessarily suitable for:

- CAD kernel tolerances.
- Meshing.
- Physical manufacturing.
- Mechanical loading.

Do not claim those qualifications.

v0.5C should identify this as a future engineering risk and preserve the geometric evidence needed for subsequent CAD decisions.

---

# 21. FINE-SCALE SUBPIXEL VALIDATION

Raster equality at 1024 can conceal significant continuous boundary changes.

Develop at least one complementary fine-scale geometric comparison.

Possible approaches include:

- Direct polygon symmetric difference.
- Local high-resolution sampling of selected regions.
- Subpixel occupancy comparisons.
- Boundary-distance sampling.
- Exact vector intersections.
- Local clearance measurements.

Direct continuous geometry calculations should remain authoritative when available.

Optional fine-grid rasterization may be useful for visualizing subpixel modifications.

If using a fine grid, document its resolution and error characteristics.

Do not represent fine-grid agreement as proof of exact continuous equivalence.

Do not use image super-resolution.

Do not regenerate a different procedural sample.

The purpose is to inspect the same existing geometry at finer sampling resolution.

---

# 22. END-TO-END PIPELINE AUDIT

v0.5C must test the complete transformation:

G0 → G1 → G2 → G3

Use the existing frozen implementations.

For each selected validation fixture:

1. Authenticate the canonical binary mask.
2. Obtain or reconstruct the exact vector geometry.
3. Verify exact occupancy.
4. Obtain or construct the manifold candidate using the registered policy.
5. Verify manifold status.
6. Apply the frozen B2 simplification policy.
7. Validate its registered constraints.
8. Serialize the candidate.
9. Reload the candidate.
10. Independently rasterize it.
11. Recalculate continuous geometry metrics.
12. Recalculate frozen raster descriptors.
13. Inspect feature preservation.
14. Record complete provenance.
15. Issue an acceptance decision.

Do not silently skip a failed intermediate stage.

A structure cannot be considered successfully validated end-to-end if it failed manifold qualification and the pipeline quietly substituted a different input.

Unsupported input geometries must remain classified as unsupported or quarantined.

---

# 23. PRODUCTION POLICY QUESTION

The B2 work did not select a production simplification policy.

v0.5C should provide evidence for a subsequent policy decision, but must not prematurely force one.

Evaluate whether the existing accepted settings provide a reasonable tradeoff between:

- Vertex reduction.
- Geometric fidelity.
- Feature protection.
- Reproducibility.
- Runtime.
- Generalization.

Compare epsilon 0.50 and epsilon 0.75 carefully.

Do not assume a larger tolerance is better.

Do not optimize solely for vertex reduction.

## Important

If epsilon 0.50 passes every independent validation case, it may be recommended as a candidate policy within the tested domain.

However, distinguish:

- Scientifically validated candidate setting.
- Production default proposed for later approval.
- Universally qualified production policy.

These are not equivalent.

Do not label a production policy qualified unless the prospective protocol explicitly authorizes that decision and all corresponding requirements are satisfied.

If the evidence is incomplete, leave production-policy qualification as HOLD / UNQUALIFIED.

---

# 24. ACCEPTANCE STATUS SYSTEM

Produce separate statuses for:

## A. Source integrity

All canonical sources authenticated and unchanged.

## B. Exact vector fidelity

Correct G0→G1 representation.

## C. Manifold qualification

Correct G1→G2 behavior under the registered policy.

## D. Simplification validity

B2 candidate satisfies the frozen algorithmic constraints.

## E. Independent continuous fidelity

Independent checks satisfy the prospective v0.5C protocol.

## F. Raster morphology preservation

Original and reconstructed binary masks satisfy their registered criteria.

## G. Feature preservation

Known repairs, registered probes, and added independent tests satisfy their respective criteria.

## H. Broader design-space validation

Previously unused parameter combinations pass within the tested domain.

## I. Scientific acceptance

Evidence supports proceeding to v0.5D within an explicitly stated domain and with documented limitations.

## J. Production policy

Qualified only if separately justified.

## K. CAD/manufacturing readiness

UNQUALIFIED.

Do not reduce all of these distinctions to a single vague PASS.

The original historical acceptance decisions must remain unchanged.

---

# 25. SYNTHETIC AND NEGATIVE-CONTROL TESTS

Build independent validation tests covering:

1. Exact raster-cell polygon.
2. Ordinary manifold polygon.
3. Polygon with one enclosed hole.
4. Polygon with multiple enclosed holes.
5. Inherent point-contact singularity.
6. Correctly regularized point contact.
7. Regularization removed by simplification.
8. Narrow solid bridge.
9. Bridge severed by subpixel modification.
10. Two pores merged through boundary movement.
11. One pore split into two.
12. Hole removed without a large area change.
13. Exterior void channel closed.
14. Exterior void channel narrowed.
15. Large symmetric difference with zero net area change.
16. Zero raster XOR with nonzero continuous difference.
17. Boundary displacement exceeding the registered limit.
18. Area redistribution exceeding the registered limit.
19. Protected-segment coordinates changed.
20. Missing repair metadata.
21. Invalid geometry serialization.
22. Round-trip geometry orientation reversal.
23. Duplicate boundary segments.
24. Unexpected polygon components.
25. Matched pores with substantially changed shapes.
26. Misidentified pore correspondence.
27. Narrow feature outside existing guard coverage.
28. Unsupported manifold contact.
29. Already manifold geometry requiring no repair.
30. Accepted no-op simplification.
31. Valid changed simplification.
32. Failed simplification candidate.
33. Non-monotonic outcomes across requested tolerances.
34. Deterministic repeated evaluation.
35. Tampered source hash.
36. Missing or inconsistent provenance.

These tests should verify the validator's ability to detect failures rather than simply confirm that the current candidate set passes.

Retain and run all previous tests.

---

# 26. SCIENTIFIC FIGURES

Generate useful figures for interpretation and review.

At minimum:

## Figure 1 — End-to-end geometry states

Show:

- Canonical binary mask.
- Exact vector geometry.
- Manifold candidate.
- Simplified candidate.

Use the same coordinate frame.

## Figure 2 — Continuous geometry differences

Show added and removed regions separately.

Include a representative case with nonzero symmetric difference but zero raster XOR.

## Figure 3 — Boundary displacement

Map or summarize displacement between the exact source and final candidate.

## Figure 4 — Repair close-ups

Show local repair geometry before and after simplification.

## Figure 5 — Narrow-feature diagnostics

Show both protected and independently sampled vulnerable regions.

## Figure 6 — Pore correspondence

Visualize representative pore matches and shape differences.

## Figure 7 — Vertex reduction versus continuous error

Separate development and independent parameter-point results.

## Figure 8 — Raster disagreement

Show original and reconstructed masks with a difference image.

## Figure 9 — Independent validation results

Summarize pass/fail rates and reasons by configuration.

## Figure 10 — Runtime and memory

Show overall cost by validation stage.

Do not rely only on full-size overview images.

Subpixel contact changes require native-coordinate close-ups.

---

# 27. REPORTING AND OUTPUT DIRECTORY

Create a new experiment directory consistent with repository conventions.

Suggested location:

`experiments/pipeline_v0.5/scientific_validation/`

Use a unique run identifier.

Suggested organization:

- `protocol/`
- `source_manifests/`
- `development_reference/`
- `parameter_holdouts/`
- `geometry/`
- `raster_reconstruction/`
- `continuous_metrics/`
- `feature_audit/`
- `figures/`
- `performance/`
- `summary/`
- `verification/`

Do not overwrite earlier runs.

Every structure and configuration must retain:

- Source mask identifier.
- Source hash.
- Parameter values.
- Seed.
- Resolution.
- Exact geometry hash.
- Manifold candidate hash.
- Simplified candidate hash.
- Algorithm versions.
- Software versions.
- Validation settings.
- Results.
- Acceptance status.
- Failure reason if applicable.

Preserve failed candidates and supporting diagnostics.

---

# 28. REQUIRED SCIENTIFIC REPORTS

Create:

`SCIENTIFIC_GEOMETRY_VALIDATION.md`

`SCIENTIFIC_GEOMETRY_VALIDATION.json`

and a machine-readable tabular summary.

The main report should include:

## A. Executive scientific summary

State what was tested and what conclusions are supported.

## B. Methodology

Explain all four geometry states, validation methods, controls, and decision rules.

## C. Existing B2 evidence

Summarize without overwriting its historical results.

## D. Independent parameter-point cohort

List every parameter combination and stochastic replicate.

Explain the selection procedure.

## E. Exact representation fidelity

Document G0→G1.

## F. Manifold qualification

Document G1→G2.

## G. Protected simplification

Document G2→G3.

## H. Cumulative geometric changes

Document G1→G3.

## I. Raster reconstruction and morphology

Document all original-versus-final comparisons.

## J. Continuous topology and pore preservation

Report counts, correspondences, and failures.

## K. Boundary displacement

Present measured results and numerical qualifications.

## L. Feature preservation

Separate registered probes from additional independent feature screening.

## M. Subpixel regularization limitations

Explain what has and has not been established.

## N. Generalization

Distinguish parameter-point holdouts from seed-only holdouts.

## O. Performance

Runtime, peak memory, and computational bottlenecks.

## P. Scientific limitations

Explicitly identify:

- Finite number of sampled designs.
- Finite feature-screen coverage.
- Original raster resolution.
- Subpixel manifold modifications.
- Lack of assigned physical dimensions.
- Lack of mechanical verification.
- Lack of manufacturing criteria.
- Lack of CAD-kernel interoperability testing.
- Any dependence on specific geometry libraries or floating-point behavior.

## Q. Acceptance

Issue separate scientific, production-policy, and CAD-readiness statuses.

## R. Recommended next stage

State whether v0.5D can begin and under what restrictions.

---

# 29. PERFORMANCE REQUIREMENTS

Avoid turning this into an unnecessarily expensive reimplementation of all historical experiments.

Reuse authenticated source artifacts.

Reuse verified invariant measurements where scientifically justified.

Perform independent checks specifically where they add new evidence.

Do not repeatedly invoke the frozen evaluator when two source arrays have already been independently proven identical, unless needed for a defined integration test.

Record when a metric is independently recomputed versus reused from an authenticated result.

Use spatial indexing for geometry operations where helpful.

Avoid quadratic all-pairs boundary comparisons.

Stream or release large geometry objects to control peak memory.

Measure:

- Source loading.
- Vector extraction.
- Manifold qualification.
- Simplification.
- Serialization.
- Independent reloading.
- Raster reconstruction.
- Continuous geometry comparison.
- Feature auditing.
- Frozen evaluator execution.
- Reporting.

Report peak RSS and traced allocations where supported.

Do not assume Python tracing includes all GEOS-native allocations.

Correctness takes priority over runtime.

---

# 30. SOFTWARE VERIFICATION

The previously reported baseline was:

363 tests passed.

Run all existing tests and new v0.5C tests.

Verify:

- Generator hashes unchanged.
- Frozen evaluator unchanged.
- Historical results unchanged.
- v0.5A source artifacts unchanged.
- v0.5A.1 candidates unchanged.
- v0.5B1 experiments unchanged.
- v0.5B2 experiments unchanged.
- Deterministic reproduction.
- Serialization consistency.
- Raster reconstruction.
- Continuous comparison correctness.
- Acceptance logic.
- Complete provenance.

Do not weaken existing tests.

Do not change the frozen evaluator.

Do not rewrite prior reports.

Record the actual operating system.

If validation runs on macOS, do not claim Windows execution.

Provide Windows reproduction instructions where useful.

---

# 31. DO NOT IMPLEMENT

Do not implement:

- General generator redesign.
- New morphology parameters.
- New LLM prompting.
- New high-resolution generation architecture.
- Revised manifold regularization.
- Revised feature-protected simplification.
- New production tolerance optimization.
- SVG export.
- DXF export.
- STEP export.
- STL export.
- CadQuery or OpenCascade integration.
- 3D extrusion.
- Volume meshing.
- ANSYS.
- FEM.
- Mechanical optimization.
- Strength prediction.
- Manufacturing certification.

If validation reveals a defect requiring changes to an earlier stage, document the blocker and stop that affected pathway.

Do not silently implement a fix in a frozen component.

---

# 32. EXECUTION PLAN

Follow the sequence below.

## Phase A — Audit

1. Inspect the repository.
2. Read all v0.5B2 validation and handoff documents.
3. Authenticate saved source geometries.
4. Identify reusable validation interfaces.
5. Identify insufficiently independent existing checks.
6. Confirm the complete parametric design plan.

## Phase B — Protocol

7. Define the independent parameter-point cohort.
8. Define the complete validation configurations.
9. Reuse the existing prospective B2 budgets.
10. Specify additional v0.5C checks.
11. Define independent validation methods.
12. Freeze cohort selection and acceptance rules.

## Phase C — Validation implementation

13. Build saved-geometry loading and independent reconstruction.
14. Build end-to-end provenance verification.
15. Build continuous geometry comparison checks.
16. Build independent displacement diagnostics.
17. Build pore/topology correspondence verification.
18. Build broader feature-screen diagnostics.
19. Build acceptance aggregation and reporting.

## Phase D — Synthetic controls

20. Test known-valid geometries.
21. Test known-invalid geometries.
22. Test raster-invisible continuous differences.
23. Test pore merges and splits.
24. Test boundary displacement failures.
25. Test geometry and source tampering.
26. Test ambiguous feature and pore correspondence.

## Phase E — Existing B2 candidate revalidation

27. Independently validate representative saved B2 outputs.
28. Compare with registered results.
29. Identify any disagreement.
30. Do not silently reconcile inconsistent evidence.

## Phase F — Independent parameter-point study

31. Load the previously unused parameter combinations.
32. Verify source hashes.
33. Apply existing frozen geometry conversion stages.
34. Preserve all intermediate geometry states.
35. Evaluate the registered simplification configurations.
36. Run independent geometric checks.
37. Run feature audits.
38. Record every outcome.
39. Do not tune the algorithm to these results.

## Phase G — Scientific analysis

40. Aggregate continuous and raster results.
41. Compare parameter-point behavior.
42. Analyze failure types.
43. Assess generalization limits.
44. Evaluate whether any candidate simplification setting merits later production-policy consideration.
45. Issue an evidence-based scientific acceptance decision.

## Phase H — Final verification

46. Run the full software test suite.
47. Verify historical file integrity.
48. Generate scientific figures.
49. Generate machine-readable reports.
50. Write the v0.5D handoff.

## Phase I — STOP

Do not begin v0.5D or 3D CAD.

---

# 33. FINAL RESPONSE REQUIREMENTS

At completion, report:

1. What validation architecture was implemented?
2. What existing modules were reused?
3. What checks are genuinely independent?
4. Which checks still share implementation dependencies?
5. What geometry states were compared?
6. Which previously unused parameter combinations were tested?
7. How many stochastic realizations were included?
8. How many final configurations were evaluated?
9. Did the exact vectorization remain lossless?
10. Did manifold qualification succeed on new parameter combinations?
11. Did any new non-manifold contacts occur?
12. Were all accepted simplified candidates OGC-valid?
13. Were all accepted candidates manifold?
14. Were pore identities preserved?
15. Were exterior channels preserved?
16. Was continuous connectivity preserved?
17. What were the worst continuous symmetric-difference errors?
18. What were the worst added and removed material areas?
19. What were the worst boundary displacements?
20. Did original-to-final errors remain within the prospective protocol?
21. Did raster reconstruction remain exact?
22. Did frozen descriptors remain unchanged?
23. Were registered repairs preserved?
24. Did independent feature screening identify new vulnerable regions?
25. Were any narrow features weakened outside existing guards?
26. Were any previously undetected geometry defects identified?
27. How much vertex reduction was retained?
28. Which settings performed best within the tested domain?
29. Was behavior consistent across new parameter combinations?
30. Were results reproducible after serialization?
31. What were the total runtime and memory costs?
32. Did all existing tests pass?
33. How many new tests were added?
34. Were all historical files preserved?
35. What is the scientific acceptance status?
36. What is the production-policy qualification status?
37. What remains unqualified for physical CAD and FEM?
38. Is the project ready to begin v0.5D export validation?
39. What files were created or modified?
40. What scientific evidence remains missing before 3D construction?

Do not claim universal geometric fidelity.

Do not claim FEM readiness.

Do not claim manufacturability.

Do not treat raster equality as proof of continuous equivalence.

---

# FINAL SCIENTIFIC INSTRUCTION

Pipeline v0.5B2 has already demonstrated that feature-protected simplification can reduce geometric complexity while preserving the existing registered constraints for the tested structures.

The purpose of v0.5C is to determine whether those findings withstand independent verification and generalize beyond the development parameter positions.

Prioritize scientifically meaningful tests over simply expanding the software test count.

Use previously unused parameter combinations.

Inspect continuous geometry directly.

Audit feature coverage.

Preserve exact source geometries.

Preserve the historical scientific record.

If the evidence supports advancement, issue a carefully scoped acceptance statement identifying the tested domain and unresolved limitations.

If important checks fail, preserve the failures and report a HOLD.

**Complete v0.5C, write its full scientific report and v0.5D handoff, and STOP before export or 3D CAD.**