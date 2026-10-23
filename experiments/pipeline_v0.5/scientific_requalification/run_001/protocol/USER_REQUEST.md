# YOUNG DAWGS — PIPELINE v0.5C.1
# Feature-Protection Correction and Independent Scientific Requalification

## ROLE AND PRIMARY OBJECTIVE

You are acting as a senior computational geometry engineer, scientific software architect, and computational materials research developer.

You have complete read and write access to the Young Dawgs research repository.

Your assignment is to implement and validate:

**Pipeline v0.5C.1 — Feature-Protection Correction and Independent Scientific Requalification.**

Pipeline v0.5C independently evaluated the full geometry-conversion workflow and identified a previously unprotected solid section that narrowed during simplification.

This is a meaningful failure because it demonstrates that the existing feature guards and local chord checks do not detect every geometrically relevant width change.

Your primary objective is to understand and correct this failure **at the algorithmic level**, without introducing design-specific exceptions or weakening the existing scientific standards.

A second finding concerns relative-area sensitivity in a very small pore during manifold regularization. This must be investigated as a distinct scientific-policy question.

Your responsibilities are:

1. Reproduce and diagnose the independent width-loss failure.
2. Identify the general mechanism allowing it to escape existing protection.
3. Develop a minimal, generalized correction to the nonfrozen protected-simplification implementation.
4. Preserve every historical source and experiment.
5. Requalify the modified algorithm using deterministic synthetic controls.
6. Evaluate the corrected implementation against all previously examined fixtures as regression cases.
7. Establish a genuinely independent validation cohort containing new parameter combinations and seeds.
8. Freeze the corrected implementation and scientific acceptance criteria before opening the independent cohort.
9. Investigate and document the separate small-pore discrepancy.
10. Issue a scientifically defensible acceptance decision for the revised geometry-conversion workflow.

**IMPLEMENT v0.5C.1 ONLY.**

Do not implement v0.5D, SVG/DXF export, 3D CAD, STEP, STL, FEM, or manufacturing functionality.

---

# 1. RESEARCH CONTEXT

The Young Dawgs project investigates using large language models to infer procedural generators for disordered metamaterial microstructures.

The broader objective is to explore relationships between generated structural morphology and mechanical performance.

The established workflow is:

Reference microstructure
→ LLM-derived procedural generator
→ Quantitative morphology evaluation
→ Parametric exploration
→ Native high-resolution generation
→ Exact raster-to-vector geometry
→ Manifold qualification
→ Feature-protected simplification
→ Independent scientific validation
→ 2D geometry export
→ Future 3D CAD
→ Future FEM
→ Mechanical structure-property analysis.

The long-term goal is scientifically credible engineering design, not merely attractive image generation.

The current milestone is intended to correct a specific deficiency in the two-dimensional geometry-conversion pipeline.

---

# 2. PRIOR PIPELINE HISTORY

## v0.3 — Parametric exploration

Parameterized procedural microstructure generation.

The generator exposes meaningful design controls, including:

- `solid_fraction_target`
- `strut_scale`
- `pore_scale`
- stochastic seed

The exploration uses parameter combinations selected by the pipeline, rather than hard-coded separate generators.

## v0.4–v0.4.3 — Native-resolution generation

Introduced resolution-independent procedural generation, topology stabilization, convergence studies, and qualification of lower-tail thickness measurements.

The original v0.4.2 P10-calibration failure remains historical evidence.

The amended v0.4.3 acceptance applies within its tested domain.

The generator and frozen evaluator remain unchanged.

## v0.5A — Exact raster-to-vector conversion

Converted binary microstructures into exact integer-coordinate planar geometry.

Established exact raster reconstruction, area preservation, and correct boundary extraction.

Some exact geometries contain non-manifold point contacts.

The historical v0.5A HOLD remains unchanged.

## v0.5A.1 — Manifold qualification

Investigated inherent raster-derived point contacts.

Introduced separate optional manifold candidates using explicitly documented local solid-side regularization.

Received AMENDED PASS within the tested domain.

The original exact geometry remains preserved.

## v0.5B1 — Simplification sensitivity

Evaluated ordinary Douglas–Peucker simplification and documented risks to narrow features and continuous geometry.

## v0.5B2 — Feature-protected simplification

Implemented:

- Deterministic simplification of eligible chains.
- Protected repair-region geometry.
- Narrow-feature guards.
- Junction and proximity guards.
- Chord collision checks.
- Material redistribution constraints.
- Pore correspondence.
- Raster cell-center checks.
- Deterministic rejection and rollback.

Received GEOMETRIC_SCREEN_PASS_TESTED_DOMAIN across its registered study.

## v0.5C — Independent scientific validation

Evaluated 80 configurations, including new parameter positions.

Results:

- 80/80 passed frozen hard constraints and morphology comparisons.
- 80/80 retained manifold geometry.
- 80/80 preserved raster reconstruction.
- 79/80 passed the complete independent scientific screen.
- One independent unguarded width-loss failure.
- One separate small-pore cumulative discrepancy disclosed.

Scientific advancement remained HOLD.

The purpose of v0.5C.1 is to resolve or properly qualify these findings.

---

# 3. AUTHORITATIVE DOCUMENTS

Before modifying anything, locate and read:

`docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_VALIDATION.md`

`docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_PROTOCOL.md`

`docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_ARCHITECTURE.md`

`docs/pipeline_v0.5/V0_5B2_HANDOFF.md`

`docs/pipeline_v0.5/V0_5D_HANDOFF.md`

Read the completed independent scientific report:

`experiments/pipeline_v0.5/scientific_validation/run_001/summary/SCIENTIFIC_GEOMETRY_VALIDATION.md`

Read the complete response and findings:

`experiments/pipeline_v0.5/scientific_validation/run_001/summary/FINAL_RESPONSE.md`

Also inspect:

- v0.5C validation source code.
- v0.5B2 simplification implementation.
- Narrow-feature and normal-chord diagnostics.
- Protected-region construction.
- Existing independent width-interpolation utilities.
- Existing pore correspondence and area comparison.
- Frozen evaluator integration.
- v0.5A and v0.5A.1 implementations.
- Experiment manifests and hashes.
- Existing software tests.
- The complete parametric design plan.
- Native-resolution generation interfaces.

Verify filenames and file contents against the actual repository.

Do not assume that the summary in this prompt supersedes the detailed scientific report.

---

# 4. CURRENT SCIENTIFIC RESULTS

The previous v0.5C study evaluated 80 configurations.

Forty configurations came from previously saved B2 outputs.

Forty additional configurations covered:

- Design 3.
- Design 4.
- Design 6.
- Design 7.
- Design 8.

Each used seeds 0 and 1, across the registered simplification settings.

The native 1024 sources for these additional designs were created using the unchanged renderer because only 256-resolution sources existed previously.

All 80 configurations passed:

- Frozen hard constraints.
- OGC polygon validity.
- Dedicated manifold checks.
- Pore correspondence.
- Raster reconstruction.
- Frozen descriptor comparison.

However, only 79 passed the complete independent scientific screen.

## Failure A — Independent width loss

The identified failure occurred for:

**Design 4, seed 1, epsilon = 0.50.**

An independently sampled, previously unguarded solid section changed from:

`9.000000 cell`

to:

`8.916667 cell`

Absolute narrowing:

`0.083333 cell`

Relative narrowing:

approximately `0.9259%`

Independent coordinate interpolation confirmed that the change was real.

This was not merely a rounding discrepancy in a reported scalar.

The simplified geometry genuinely narrowed the sampled solid section.

The source raster and frozen descriptors remained unchanged, demonstrating that the width change occurred below the resolution of the existing raster-level validation.

This case must remain a registered regression failure for the original B2 algorithm.

Do not erase or retroactively reinterpret it as a pass.

## Finding B — Small-pore relative area discrepancy

The cumulative audit identified a:

**3.125% relative area change in a pore originally measuring 1 cell².**

The absolute change is:

`0.03125 cell²`

This discrepancy originated during manifold regularization.

It must be evaluated separately from the B2 simplification stage.

In particular, do not confuse:

- G1→G2 error introduced during manifold regularization.
- G2→G3 error introduced during protected simplification.
- Cumulative G1→G3 error.

The 0.5% per-pore distortion budget used during B2 simplification must not be silently reinterpreted as a historical requirement for every previous transformation unless the repository's registered protocols actually establish that scope.

Determine precisely which existing acceptance criteria apply to each transformation.

---

# 5. REQUIRED INITIAL AUDIT

Before coding, inspect the actual v0.5C failure.

Identify:

1. The exact source geometry.
2. The original manifold candidate.
3. The simplified candidate.
4. The location of the narrowed section.
5. The saved independent probe coordinates.
6. The original width-measurement method.
7. The independent coordinate-interpolation method.
8. The neighboring boundary segments.
9. The accepted replacement chord responsible for the change.
10. Which existing guards covered the surrounding region.
11. Whether the changed region was entirely unguarded.
12. Which local chord checks allowed the modification.
13. Whether any existing feature detector should have identified the section.
14. Whether the failure is caused by incomplete feature discovery, incomplete chord validation, or both.
15. Whether similar vulnerable regions are present in other saved structures.

Produce a concise root-cause plan before modifying source code.

Do not immediately increase all guard sizes.

Do not immediately reduce the global simplification tolerance.

Do not hard-code the failed coordinates.

Do not add a special-case rule for Design 4, seed 1.

---

# 6. DEFINE THE FOUR GEOMETRY STATES

Continue to distinguish:

## G0 — Canonical binary structure

The unchanged native-resolution raster.

## G1 — Exact vector geometry

The exact pixel-cell planar representation.

## G2 — Manifold candidate

The locally regularized geometry from v0.5A.1.

## G3 — Protected simplified geometry

The result of the B2 or revised B2 algorithm.

For each relevant comparison, retain:

- G1→G2.
- G2→G3.
- G1→G3.
- G0→rasterized G3.

The width-loss investigation must compare G2 and G3, because the defect concerns simplification of an already manifold-qualified structure.

The small-pore investigation must separately examine G1→G2 and cumulative G1→G3.

Do not combine these errors into an unqualified aggregate.

---

# 7. PRIMARY TASK — ROOT-CAUSE ANALYSIS OF WIDTH LOSS

Construct a focused diagnostic for the Design 4/seed 1 failure.

Required outputs:

### A. Original local geometry

Show the G2 boundary near the failing section.

### B. Simplified local geometry

Overlay G3.

### C. Independent width measurement

Show the original and simplified sampled cross-sections.

### D. Simplification chord

Identify the exact replacement chord or sequence of proposals responsible.

### E. Guard coverage

Display:

- Protected vertices.
- Protected segments.
- Guard regions.
- Eligible boundary chains.
- Accepted chords.
- Nearby opposing boundaries.

### F. Candidate-change region

Display the polygonal region added or removed by the chord replacement.

### G. Failure classification

Determine whether the problem is:

1. A feature-detector coverage gap.
2. A candidate-chord constraint gap.
3. An incorrect width definition.
4. Incorrect local geometry interpolation.
5. An accepted numerical tolerance issue.
6. A combination of the above.

The finding must be supported by the actual saved geometry and diagnostic measurements.

Do not assume the problem is caused exclusively by sparse normal probes before checking the implementation.

---

# 8. CORRECTION OBJECTIVE

The corrected simplifier must detect and prevent the documented narrowing mechanism for eligible structures under the registered feature-protection policy.

The goal is not to freeze every boundary.

The goal is to identify when a proposed simplification would violate a meaningful local width constraint and reject or modify that proposal appropriately.

Use a generalized constraint method.

Do not depend on the known failed coordinates.

Do not assume every mechanically relevant neck can be represented by one perpendicular width measurement.

Distinguish:

- Registered protected widths.
- Additional sampled widths.
- Geometrically inferred local bottlenecks.
- Global minimum-width behavior.
- Exhaustive continuous-width guarantees.

Do not claim the last category unless an algorithm with a justified mathematical guarantee is actually implemented.

---

# 9. INVESTIGATE FEATURE-DETECTION COVERAGE

The current B2 implementation used:

- Dense skeleton/EDT screening.
- Registered repair and connector guards.
- Supported normal-chord probes.

The independent audit discovered a width change outside the registered guards.

Investigate how to improve coverage.

Possible strategies:

### Strategy A — Adaptive local width sampling

Increase sampling density where:

- Boundaries are close.
- The local geometry has high curvature.
- A candidate chord enters a narrow corridor.
- Nearby opposing boundaries create a potential bottleneck.

Do not merely multiply the number of global probes.

### Strategy B — Chord-impact-region analysis

For every proposed replacement chord, identify the continuous region whose solid/void occupancy will change.

Determine whether the change region can reduce local solid-channel width.

This may be more efficient than exhaustively measuring every location in the full structure.

### Strategy C — Spatially indexed opposing-boundary detection

Use nearby boundary segments to identify potential width-sensitive configurations.

Differentiate solid corridors from void gaps.

### Strategy D — Candidate-level local geometry comparison

Before accepting a chord, compare original and proposed local geometry along relevant cross-sections.

Reject the chord if the measured width falls below the prospective allowed value.

### Strategy E — More conservative uncertain-region behavior

If an affected region is too complicated to measure reliably, preserve the original chain rather than accepting an unverified modification.

Evaluate these approaches against the actual failure mechanism.

You may combine methods where justified.

---

# 10. CHORD-LEVEL PROTECTION

The preferred correction should operate near the source of the geometric change.

For a proposed replacement chord:

1. Identify the original boundary chain.
2. Identify the proposed replacement segment.
3. Determine the candidate material-addition/removal region.
4. Query potentially affected opposing boundaries.
5. Identify relevant local solid corridors.
6. Determine whether the chord reduces a protected or qualifying measured width.
7. Apply the frozen constraint.
8. Accept or reject deterministically.
9. Record the decision.

Do not infer that a chord is safe solely because:

- It does not intersect another boundary.
- The final polygon is OGC-valid.
- The manifold checker passes.
- Hole count remains unchanged.
- Raster occupancy remains unchanged.
- Global symmetric difference is small.
- Previously registered probes retain their widths.

These are useful checks, but they do not guarantee local width preservation.

A geometric section can narrow without violating any of them.

---

# 11. CONSERVATIVE LOCAL ROLLBACK

Preserve the B2 principle of deterministic rollback.

If a chord fails width qualification:

- Reject the proposed simplification.
- Restore the original source subchain.
- Record the rejection reason.
- Continue with other eligible regions when safe.

Do not globally revert the structure unless required to preserve correctness.

Do not repeatedly retry random variations until a proposal happens to pass.

Do not use hidden erosion, dilation, smoothing, or buffering to repair the result.

A no-op is acceptable.

A smaller vertex reduction is preferable to accepting an unqualified width loss.

---

# 12. VERSION THE CORRECTION

Do not silently overwrite the historical B2 implementation or outputs.

Create a separately identifiable corrected algorithm version.

For example:

`protected_simplification_v2`

or a repository-consistent equivalent.

Preserve:

- Original B2 code and hashes.
- Original B2 accepted geometries.
- Original v0.5C independent validation results.
- Original failed Design 4/seed 1 candidate.
- Original validation reports.
- Original acceptance statuses.

If shared code must be modified, preserve reproducible access to the earlier algorithm and document the compatibility implications.

Prefer additive implementation and explicit version selection.

The revised algorithm must be distinguishable in every manifest.

---

# 13. STRICT ACCEPTANCE CRITERIA

Do not weaken the existing B2 hard constraints.

Preserve, subject to verification of their registered definitions:

- OGC-valid planar geometry.
- Manifold boundary.
- Continuous component preservation.
- Pore identities preserved.
- Exterior channels preserved.
- No severed protected links.
- Exact protected repair geometry.
- Zero registered repair-clearance loss.
- Zero registered protected-width loss.
- Added solid area ≤0.25% of occupied area.
- Removed solid area ≤0.25% of occupied area.
- Symmetric-difference area ≤0.5%.
- Per-pore area distortion ≤0.5%, applied to the transformation scope specified in the registered B2 protocol.
- Continuous displacement bound ≤sqrt(2)/2 cell.
- Zero raster XOR.
- Exact frozen-evaluator descriptor equality.

Preserve the documented numerical tolerances.

Do not silently increase the numerical allowance.

## Additional C.1 feature criterion

The corrected pipeline must be evaluated against additional, independently selected width measurements.

Define the new validation coverage and decision rules before the final confirmatory study.

Do not define a threshold based solely on the width change already observed in Design 4.

Do not claim that finite sample-based width preservation guarantees every possible cross-section.

If the project continues to require zero width loss at the evaluated sections, apply that requirement consistently.

If numerical precision prevents literal zero comparisons, document a justified floating-point tolerance separately from any engineering allowance.

A numerical tolerance must not hide an actual 0.083333-cell geometric narrowing.

---

# 14. SMALL-PORE SCIENTIFIC INVESTIGATION

Investigate the separate 3.125% discrepancy in the 1-cell² pore.

This is not the same failure as the unprotected strut narrowing.

Do not combine the two.

## Required reconstruction

Identify:

1. The original pore boundary in G1.
2. Its manifold-qualified representation in G2.
3. Its simplified representation in G3.
4. The associated manifold contact.
5. The regularization footprint.
6. The absolute pore-area change.
7. The relative pore-area change.
8. Whether the pore identity remains unchanged.
9. Whether neighboring pores are affected.
10. Whether the original contact policy explicitly permits this modification.

Verify the reported absolute discrepancy of approximately 0.03125 cell² against saved geometry.

## Evaluate relative versus absolute error

Relative area error is:

`abs(A_final - A_reference) / A_reference`

For very small pores, a small absolute change can produce a relatively large percentage.

For a 1-cell² pore:

`0.03125 / 1 = 3.125%`

Investigate whether a scientifically defensible evaluation should report BOTH:

- Absolute pore-area change.
- Relative pore-area change.

Also evaluate:

- Pore identity.
- Pore count.
- Minimum aperture or characteristic size where meaningful.
- Boundary displacement.
- Whether the pore is altered by necessary manifold regularization.
- Whether a local topology modification occurred.

Do not exclude small pores automatically.

Do not dismiss a discrepancy because its absolute area is small.

Do not declare the original relative-error criterion invalid simply because this case fails it.

---

# 15. SMALL-PORE POLICY REVIEW

Produce a separate scientific-policy recommendation.

Possible outcomes:

### Outcome A — Existing policy remains adequate

The result is correctly recorded under its intended transformation scope, and no change is needed.

### Outcome B — A prospective amended metric is justified

A combined absolute/relative measurement or area-tiered diagnostic may be appropriate.

Any amended rule must:

- Have a mathematical rationale.
- State its intended transformation scope.
- Preserve pore identity.
- Preserve topology requirements.
- Retain absolute and relative errors in reporting.
- Be evaluated on independent synthetic and real controls.
- Avoid retroactively claiming the historical result passed.

### Outcome C — Scientific decision remains unresolved

If no defensible policy can be established, retain HOLD / UNQUALIFIED for that criterion.

Do not force a policy amendment.

The old v0.5C result remains historical evidence regardless of the recommendation.

---

# 16. SYNTHETIC SMALL-PORE CONTROLS

Create deterministic controls containing:

1. A 1-cell² enclosed pore.
2. A 2-cell² enclosed pore.
3. A larger pore with identical absolute area change.
4. A pore affected by local solid-side manifold regularization.
5. A pore unaffected by regularization.
6. A pore with changed area but preserved identity.
7. A pore with changed boundary shape but unchanged area.
8. Two pores merged into one.
9. One pore split into two.
10. A pore connected to an exterior channel.
11. A pore whose area changes below raster detectability.
12. A case violating an absolute-area limit.
13. A case violating a relative-area limit.
14. A case violating both limits.
15. A case where area metrics pass but topology changes.

These tests should determine what the alternative policies detect and miss.

Do not merely create examples that justify the desired amendment.

---

# 17. SYNTHETIC FEATURE-PROTECTION CONTROLS

Before testing independent parameter combinations, build a targeted suite.

Include:

1. A straight uniform-width strut.
2. A curved uniform-width strut.
3. A tapered strut.
4. A narrow neck.
5. A wide neck.
6. An angled solid corridor.
7. A high-curvature boundary.
8. Two nearby nonparallel boundaries.
9. A junction with multiple struts.
10. A chord that reduces corridor width.
11. A chord that increases corridor width.
12. A chord that leaves width unchanged.
13. A chord whose raster reconstruction remains unchanged but whose continuous width decreases.
14. A chord that passes global area limits but violates local width preservation.
15. A chord that passes ordinary topology checks but reduces a critical section.
16. A chord that enters an existing guard.
17. A chord that affects a nearby region without directly entering its guard.
18. A narrow region not identified by the original B2 detector.
19. A feature requiring adaptive sampling.
20. A candidate whose width cannot be reliably measured.
21. A safe simplification outside any vulnerable feature.
22. A case requiring no-op fallback.
23. Multiple nearby proposed chords with interacting effects.
24. A non-monotonic width response across tolerances.
25. A case where the corrected algorithm must reject the original B2 proposal.
26. A case where the corrected algorithm should accept a safe proposal.

Use analytically understandable geometries where possible.

Test both the detection method and the corrective decision logic.

Verify that the revised method catches the exact class of failure found in Design 4 without referencing that design's coordinates.

---

# 18. DEVELOPMENT AND REGRESSION COHORTS

All previously examined designs and seeds must now be treated as development or regression evidence.

This includes the original B2 development set:

- D0/S0.
- D9/S1.
- D1/S0.
- D2/S0.
- D5/S0.

The original B2 seed-only holdouts:

- D0/S1.
- D1/S1.
- D2/S1.
- D5/S1.
- D9/S0.

And the v0.5C independent parameter-point cohort:

- D3/S0 and S1.
- D4/S0 and S1.
- D6/S0 and S1.
- D7/S0 and S1.
- D8/S0 and S1.

These are no longer untouched validation samples for a revised algorithm.

They may and should be used for:

- Root-cause analysis.
- Regression tests.
- Algorithm development.
- Performance assessment.
- Previously established morphology comparisons.

However, do not describe their post-correction results as new independent holdout validation.

## Required regression checks

The corrected algorithm must be tested on:

- The original Design 4/seed 1 failure.
- The other 79 v0.5C configurations.
- Relevant B2 development cases.
- Relevant synthetic geometry controls.

For the original failure, independently confirm whether the 9.000000-cell section remains preserved after correction.

Do not assume success from a change in a guard flag.

Recompute the actual continuous width.

---

# 19. NEW INDEPENDENT VALIDATION COHORT

Because the previous ten Latin-hypercube parameter points have now been examined, establish new parameter combinations inside the original registered parametric bounds.

Do not reuse the same ten points as an independent cohort.

Do not invent new design-space bounds.

Inspect the actual v0.3 plan.

Use the existing parameter ranges for:

- `solid_fraction_target`
- `strut_scale`
- `pore_scale`

## Proposed cohort

If computationally feasible:

**Six new parameter combinations × two stochastic seeds.**

That produces:

12 new native-1024 microstructures.

Use a deterministic space-filling sampling method such as Latin hypercube or Sobol sampling.

Record:

- Sampling algorithm.
- Sampling seed.
- New parameter combinations.
- Distance from existing parameter points, under normalized design-space coordinates.
- Replicate seeds.
- Source generator hash.
- Native resolution.
- Generation manifest.

Do not deliberately select parameter combinations because the revised algorithm is expected to pass them.

Do not hard-code individual generated morphologies.

The procedural generator must remain unchanged.

## Avoiding data leakage

Before generating or inspecting the new validation outputs:

1. Freeze the revised simplification algorithm.
2. Freeze feature-detection settings.
3. Freeze geometry budgets.
4. Freeze acceptance criteria.
5. Freeze the small-pore policy being evaluated.
6. Freeze the cohort-generation algorithm and random seeds.
7. Record relevant source hashes.

If these new parameter combinations have already been inspected during development, they do not qualify as untouched holdouts. Select fresh combinations and record the reason.

Do not tune the algorithm based on holdout results.

If a holdout fails, preserve it as a failure.

If a further algorithm revision is needed, document that new revision and reserve another fresh cohort for confirmatory validation.

Do not repeatedly reuse failed holdouts while continuing to call them independent.

---

# 20. NEW COHORT GENERATION

The user has authorized validation using the existing procedural generator.

You may generate new native-1024 source structures for the registered independent cohort.

However:

- Do not modify the generator.
- Do not alter parameter bounds.
- Do not modify the original Latin-hypercube plan.
- Do not substitute upscaled 256 images.
- Do not manually repair generated masks.
- Do not add disconnected islands.
- Do not silently replace topology-invalid outputs.

Record any generator failures.

The new source arrays must be stored in new experiment directories.

If the new cohort contains unsupported geometries or previously unseen manifold contacts, preserve them as evidence and apply only the established contact policy.

Do not invent a new geometry repair merely to ensure completion.

---

# 21. END-TO-END VALIDATION

For each new independent structure, evaluate:

G0 → G1 → G2 → revised G3

Required sequence:

1. Generate or authenticate the canonical raster.
2. Verify binary dtype and shape.
3. Check connected components and percolation.
4. Build exact vector geometry.
5. Verify exact raster reconstruction.
6. Classify manifold contacts.
7. Apply the existing optional manifold policy where supported.
8. Record all continuous manifold modifications.
9. Verify the manifold candidate.
10. Run the revised protected simplifier.
11. Apply the registered geometry constraints.
12. Run independent width and feature checks.
13. Verify continuous topology.
14. Verify pore identities.
15. Verify material addition/removal budgets.
16. Verify boundary displacement.
17. Rasterize the revised candidate.
18. Verify original raster equality.
19. Verify frozen descriptor equality.
20. Serialize and reload geometry.
21. Repeat critical geometric comparisons.
22. Record acceptance or failure.

Do not skip intermediate failures.

If a source fails qualification, preserve the source and classify the failure.

Do not silently remove it from the denominator.

---

# 22. SIMPLIFICATION CONFIGURATIONS

Evaluate the existing registered settings where appropriate.

At minimum:

- Epsilon 0: baseline.
- Epsilon 0.35: conservative diagnostic.
- Epsilon 0.50: primary nonzero candidate.
- Epsilon 0.75: stress case.

If the frozen v0.5C or v0.5B2 protocol requires additional settings, include them.

Report the exact set in the prospective C.1 protocol.

Do not select only the setting that produces the highest vertex reduction.

The epsilon 0.50 setting is particularly important because the original width-loss failure occurred there.

The corrected implementation should reject width-damaging proposals even if that reduces vertex savings.

---

# 23. REVISED WIDTH-VALIDATION REQUIREMENTS

For each structure, run two distinct width-screening methods where feasible.

## A. Algorithm-integrated protection

These are the checks used to decide whether a simplification proposal is allowed.

## B. Independent width audit

These are validation measurements that were not used directly to accept every proposal.

Where practical, the independent audit should use different sample locations or complementary geometric constructions.

Report any shared mathematical or library dependencies honestly.

## Required results

For each monitored cross-section:

- Original width.
- Simplified width.
- Absolute difference.
- Relative difference.
- Location.
- Measurement method.
- Whether the feature was registered or independently sampled.
- Whether its geometry was protected.
- Whether it was changed by an accepted chord.
- Whether it passed the configured criterion.

Aggregate:

- Number of registered features.
- Number of independent features.
- Number of detected narrowing events.
- Maximum measured narrowing.
- Number of unmeasurable or ambiguous sections.
- Feature coverage diagnostics.
- Number of width-related chord rejections.

A failed or undefined measurement must not be silently treated as zero narrowing.

---

# 24. TOPOLOGY VALIDATION

All accepted candidates must retain:

- OGC-valid planar geometry.
- Manifold boundary.
- Solid component count.
- Pore count.
- Pore identities.
- Exterior-channel connectivity.
- Registered manifold repairs.
- Registered narrow links.
- Positive clearances where required.

Detect:

- New point contacts.
- Hole merges.
- Hole splits.
- Pore deletions.
- Pore additions.
- Boundary overlaps.
- New zero-width necks.
- Continuous corridor severance.
- Invalid polygon assembly.

Do not assume raster connectivity establishes continuous topology preservation.

Do not assume OGC validity establishes manifoldness.

---

# 25. CONTINUOUS GEOMETRY COMPARISON

For every accepted and rejected candidate where geometry remains evaluable, calculate:

- Baseline area.
- Candidate area.
- Added solid area.
- Removed solid area.
- Net area difference.
- Symmetric-difference area.
- Relative symmetric-difference area.
- Maximum boundary displacement or justified upper bound.
- Hole-area differences.
- Hole-boundary displacement.
- Narrow-feature changes.
- Repair-region integrity.

Perform both:

G2→G3

and:

G1→G3.

For the manifold stage, also report:

G1→G2.

Do not collapse these into one total error number.

Keep the previously registered acceptance budgets unchanged unless a separate policy amendment is explicitly approved.

---

# 26. PORE POLICY QUALIFICATION

The small-pore finding requires an explicitly separated decision.

The corrected simplification algorithm does not need to alter manifold regularization to address it.

Do not rewrite the v0.5A.1 regularization algorithm.

Produce:

1. A reconstruction of the original 1-cell² pore finding.
2. A comparison of existing metric definitions.
3. An analysis of absolute and relative pore-area errors.
4. Results from synthetic controls.
5. A prospective candidate policy, if justified.
6. An independent evaluation of any candidate policy.
7. A clear scientific disposition.

Possible final statuses:

- Existing policy correctly applied; no amendment necessary.
- Amended policy qualified within a stated domain.
- Policy remains unqualified.
- Additional scientific decision required.

Never turn the original observed failure into a historical PASS.

If a prospective amendment is proposed, retain the original discrepancy and both error measurements.

The policy must not permit pore mergers, splits, or deletions merely because the absolute area involved is small.

---

# 27. PERFORMANCE AND USAGE EFFICIENCY

The existing pipeline has already accumulated substantial validation code and experimental evidence.

Avoid unnecessary repetition.

Prioritize:

1. Root-cause reproduction.
2. Targeted synthetic tests.
3. Local algorithm correction.
4. Regression tests.
5. Independent holdouts.
6. Final reporting.

Do not launch the entire independent cohort before the correction is tested on the known failure and deterministic controls.

Do not regenerate historical structures unnecessarily.

Reuse authenticated inputs where possible.

Avoid repeatedly running expensive frozen descriptor evaluations on byte-identical raster masks unless needed for an integration test.

Use spatial indexing for boundary checks.

Avoid quadratic all-pairs geometry calculations.

Profile:

- Feature detection.
- Guard construction.
- Candidate chord checks.
- Width qualification.
- Rollback.
- Geometry assembly.
- Continuous validation.
- Raster reconstruction.
- Frozen evaluation.
- Serialization.
- Total runtime.
- Peak memory.

Report that Python traced allocation may omit native GEOS memory.

Do not sacrifice correctness merely to improve runtime.

---

# 28. DETERMINISM AND PROVENANCE

Every output must be reproducible.

Record:

- Pipeline version.
- Source generator hash.
- Exact raster source hash.
- Exact vector geometry hash.
- Manifold candidate hash.
- Original B2 algorithm hash.
- Revised algorithm hash.
- Simplification settings.
- Guard settings.
- Width-detection settings.
- Acceptance budgets.
- Parameter values.
- Random seed.
- Resolution.
- Candidate geometry hash.
- Raster reconstruction hash.
- Software versions.
- Operating system.
- Validation results.
- Failure reasons.

Preserve deterministic traversal order where possible.

Do not claim byte-identical cross-platform results without evidence.

---

# 29. REQUIRED FIGURES

Generate detailed figures.

At minimum:

## Figure 1 — Original width-loss failure

Show:

- Original manifold geometry.
- Original B2 simplified geometry.
- Width cross-section.
- Accepted chord responsible.
- Previously unguarded region.

## Figure 2 — Corrected behavior

Overlay the revised simplified geometry on the original failure region.

Show whether the problematic chord was rejected and which geometry was retained.

## Figure 3 — Feature-detection coverage

Compare original and revised guard/probe coverage.

## Figure 4 — Width changes

Plot original versus revised measurements for registered and independent sections.

## Figure 5 — Vertex reduction

Compare original B2 and corrected algorithm across regression fixtures.

## Figure 6 — Continuous geometry difference

Show material added and removed by simplification.

## Figure 7 — Small-pore analysis

Display the original 1-cell² pore before and after manifold regularization.

Annotate absolute and relative area differences.

## Figure 8 — Independent parameter cohort

Show representative new native 1024 structures and validated geometry.

## Figure 9 — Holdout scientific results

Summarize acceptance by design, seed, and tolerance.

## Figure 10 — Runtime and memory

Show stage-by-stage computational costs.

Use detailed native-coordinate close-ups.

Small continuous differences may be invisible in full-field raster images.

---

# 30. OUTPUT DIRECTORY

Create a new experiment directory.

Suggested path:

`experiments/pipeline_v0.5/scientific_requalification/`

Use a unique run identifier.

Suggested contents:

- `audit/`
- `protocol/`
- `root_cause/`
- `algorithm_version/`
- `synthetic_controls/`
- `regression/`
- `pore_policy/`
- `independent_cohort/`
- `geometry/`
- `feature_audit/`
- `figures/`
- `performance/`
- `summary/`
- `verification/`

Retain all failures and rejected candidates.

Do not overwrite previous runs.

Do not modify existing experiment directories.

---

# 31. SCIENTIFIC REPORTS

Create:

`FEATURE_PROTECTION_CORRECTION.md`

`SMALL_PORE_QUALIFICATION.md`

`INDEPENDENT_REQUALIFICATION.md`

`V0_5C_1_HANDOFF.md`

and machine-readable summaries.

The main report should include:

## A. Executive summary

Precise acceptance status and scope.

## B. Original failure

Coordinates, cause, and geometry measurements.

## C. Corrective algorithm

What changed and why.

## D. Synthetic validation

Known-success and known-failure controls.

## E. Regression comparison

Original versus corrected B2 behavior.

## F. Independent validation cohort

New parameter combinations, seeds, and qualification results.

## G. Feature coverage

Registered versus independent width measurements.

## H. Continuous geometry fidelity

Added/removed material, displacement, topology, and pore comparisons.

## I. Small-pore policy

Separate reconstruction, analysis, and disposition.

## J. Performance

Runtime, memory, and complexity.

## K. Scientific interpretation

What has genuinely been established.

## L. Limitations

At minimum:

- Finite validation cohort.
- Finite width-probe coverage.
- No universal guarantee for arbitrary geometries.
- Subpixel manifold modifications.
- Raster equality does not imply continuous equality.
- No assigned physical dimensions.
- No CAD-kernel interoperability qualification.
- No mesh-quality qualification.
- No mechanical strength verification.
- No manufacturing certification.

## M. Acceptance decision

Separate feature-protection acceptance, small-pore policy qualification, overall v0.5C.1 acceptance, and v0.5D eligibility.

---

# 32. SCIENTIFIC ACCEPTANCE SYSTEM

Report separate statuses.

### A. Source preservation

Historical generators, evaluator, and experiment files unchanged.

### B. Root-cause diagnosis

Original width-loss mechanism correctly reproduced and explained.

### C. Generalized algorithm correction

Corrected implementation addresses the failure class without hard-coded sample-specific exceptions.

### D. Synthetic controls

Required tests pass.

### E. Regression qualification

Previously observed width failure corrected, with no unacceptable regressions.

### F. Independent feature qualification

New parameter-point holdouts pass prospective criteria.

### G. Continuous geometry fidelity

Area, displacement, topology, pore, and feature requirements pass.

### H. Raster morphology

Canonical 1024 raster and frozen descriptors retained where required.

### I. Small-pore scientific policy

Qualified, unresolved, or amended within a defined domain.

### J. Overall scientific acceptance

Evidence supports or does not support advancement under the registered policy.

### K. Production simplification policy

Qualified only if independently justified.

### L. CAD/manufacturing/FEM readiness

UNQUALIFIED.

The historical v0.5C HOLD remains unchanged.

Do not retroactively replace it with the new result.

---

# 33. SOFTWARE VERIFICATION

Previous reported software baseline:

407 tests passed.

Run all previous tests and new C.1 tests.

Verify:

- Historical file inventories.
- Generator hashes.
- Frozen evaluator hash.
- Exact geometry preservation.
- Manifold candidate preservation.
- Original B2 reproducibility.
- Corrected implementation reproducibility.
- Accepted width constraints.
- Geometry validity.
- Hole preservation.
- Serialization.
- Error reporting.
- Protocol integrity.
- Independent cohort provenance.

Do not weaken previous tests.

If an existing test must change because a new versioned interface was introduced, preserve verification of the original behavior.

Report the actual test count and all failures.

Record the actual operating system.

Provide Windows reproduction commands if useful, but do not claim Windows execution unless it was performed.

---

# 34. EXPLICITLY OUT OF SCOPE

Do not implement:

- A new procedural generator.
- New morphology parameters.
- New native-resolution algorithms.
- Changes to evaluator v1.1.
- Changes to the exact vectorization algorithm.
- Changes to historical manifold candidates.
- General global smoothing.
- Arbitrary widening of network struts.
- Raster dilation or erosion.
- Unrecorded polygon repair.
- SVG export.
- DXF export.
- STEP export.
- STL export.
- CadQuery.
- OpenCascade.
- 3D extrusion.
- Volume meshing.
- ANSYS.
- FEM.
- Mechanical optimization.
- Mechanical strength predictions.
- Manufacturing certification.

Do not begin v0.5D.

---

# 35. REQUIRED EXECUTION SEQUENCE

Follow this sequence.

## Phase A — Audit

1. Read existing source code and reports.
2. Authenticate the saved failure geometry.
3. Locate the original failing width section.
4. Trace accepted chord proposals.
5. Inspect guard coverage.
6. Establish the cause.
7. Write the implementation plan.

## Phase B — Targeted correction

8. Implement complementary feature screening where justified.
9. Improve local chord-impact validation.
10. Introduce conservative rejection for uncertifiable affected widths.
11. Preserve deterministic rollback.
12. Version the correction separately.

## Phase C — Synthetic testing

13. Test analytic strut and corridor geometries.
14. Test subpixel narrowing.
15. Test safe simplifications.
16. Test unsafe chord rejection.
17. Test no-op fallback.
18. Test repeatability.
19. Test geometry budgets.

## Phase D — Regression

20. Reproduce the historical Design 4/seed 1 failure using original B2.
21. Test the corrected algorithm on the same structure.
22. Independently verify width preservation.
23. Evaluate all previously examined structures.
24. Document changes in vertex reduction, geometry error, and runtime.
25. Fix development defects as needed before freezing the new algorithm.

## Phase E — Small-pore qualification

26. Reconstruct the 1-cell² pore discrepancy.
27. Analyze its mathematical origin.
28. Examine transformation-specific policies.
29. Run synthetic area and topology controls.
30. Document a prospective policy or unresolved scientific decision.

## Phase F — Freeze

31. Freeze the corrected algorithm version.
32. Freeze feature-detection settings.
33. Freeze acceptance thresholds.
34. Freeze independent cohort parameters and seeds.
35. Freeze the small-pore evaluation policy.
36. Record code and protocol hashes.

## Phase G — Independent validation

37. Generate the new registered parameter combinations using the unchanged generator.
38. Generate two stochastic replicates per combination.
39. Construct exact geometry.
40. Apply established manifold qualification.
41. Apply corrected simplification.
42. Run independent continuous and raster checks.
43. Audit feature preservation.
44. Retain failures.
45. Do not tune against holdout results.

## Phase H — Final analysis

46. Aggregate scientific results.
47. Compare regression and independent cohorts.
48. Evaluate remaining feature-detection limitations.
49. Determine whether the small-pore policy is scientifically qualified.
50. Issue the final C.1 acceptance decision.

## Phase I — Verification

51. Run all software tests.
52. Verify historical files.
53. Generate figures.
54. Generate machine-readable results.
55. Write scientific reports.
56. Write the v0.5D handoff.

## Phase J — STOP

Do not implement v0.5D.

Do not begin CAD export or 3D development.

---

# 36. FINAL RESPONSE REQUIREMENTS

When finished, answer:

1. What caused the original unguarded width reduction?
2. Was the failure due to feature detection, chord validation, or both?
3. What specific algorithmic correction was implemented?
4. How does the correction generalize beyond the original coordinate?
5. Was the original B2 behavior preserved and reproducible?
6. Was the 9.000000→8.916667-cell failure independently reproduced?
7. Did the revised algorithm preserve that section?
8. What additional synthetic failures were tested?
9. Were unsafe chords rejected?
10. How many proposals were newly rejected?
11. How many regions required rollback or no-op?
12. Did the revised detector identify previously unguarded vulnerable sections?
13. Were the original manifold repairs preserved?
14. Were registered narrow features preserved?
15. How much vertex reduction was retained?
16. Did correction significantly increase runtime or memory?
17. Were any new topology defects introduced?
18. Were pore identities preserved?
19. Were area budgets preserved?
20. Was the continuous displacement bound preserved?
21. Did raster reconstruction remain exact?
22. Did frozen descriptors remain unchanged?
23. What caused the small-pore relative-area discrepancy?
24. Is the existing small-pore policy scientifically adequate?
25. Was an amendment proposed or qualified?
26. What absolute and relative pore errors remain?
27. Which new parameter combinations were selected?
28. How were they selected independently?
29. How many new stochastic realizations were generated?
30. How many independent configurations were evaluated?
31. Did the revised method pass independent validation?
32. Were holdout results used for tuning?
33. What limits remain on feature-screen coverage?
34. What is the maximum measured new width loss?
35. What continuous geometry error remains?
36. What software tests passed?
37. Were all historical artifacts preserved?
38. What files were created or modified?
39. What is the precise acceptance status?
40. Is the project scientifically eligible to advance to v0.5D?
41. Does production simplification remain unqualified?
42. What geometric and physical limitations remain before 3D CAD?

Do not report universal width preservation unless an exhaustive continuous guarantee has actually been established.

Do not report that a previously failed historical validation passed retroactively.

Do not declare v0.5 complete.

---

# FINAL INSTRUCTION

The independent v0.5C study revealed a real limitation in the feature-protected simplifier.

The correct response is not to lower scientific standards or add a hard-coded guard around one failed structure.

The correct response is to improve the general mechanism for detecting and rejecting width-damaging simplification proposals.

Preserve the historical results.

Preserve the canonical microstructures.

Correct only the necessary nonfrozen geometry logic.

Investigate the small-pore qualification separately.

Revalidate using truly new parameter combinations and stochastic replicates.

Prefer conservative no-op behavior over uncertain geometry modifications.

**Complete Pipeline v0.5C.1, issue an evidence-based scientific acceptance decision, prepare the handoff for v0.5D, and STOP.**