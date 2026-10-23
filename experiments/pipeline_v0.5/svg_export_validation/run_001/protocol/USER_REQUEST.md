# YOUNG DAWGS — PIPELINE v0.5D1
# Research-Only 2D Geometry Export and Independent Reimport

## ROLE AND PRIMARY OBJECTIVE

You are acting as a senior computational geometry engineer, scientific software architect, and computational materials research developer.

You have complete read and write access to the Young Dawgs research repository.

Your assignment is to implement, execute, and validate:

**Pipeline v0.5D1 — Research-Only 2D Geometry Export and Independent Reimport.**

The preceding pipeline stages have established native-resolution procedural generation, exact raster-to-vector conversion, optional manifold qualification, feature-protected simplification, and independent scientific geometry validation.

The overall scientific status remains HOLD because cumulative small-pore fidelity is not yet qualified.

Your current responsibility is narrower.

Determine whether the existing saved two-dimensional vector geometries can be exported into a standard interchange format and independently reimported **without introducing any additional changes to the represented continuous geometry**.

This is an interoperability and serialization experiment.

It is not a request to resolve the outstanding scientific HOLD.

It is not authorization to begin 3D CAD.

It is not authorization to select a production simplification policy.

The primary interchange format for this milestone is **SVG**.

Implement a precise SVG exporter, an independently structured SVG import/verification pathway, comprehensive geometric comparisons, deterministic tests, and a scientific handoff.

**IMPLEMENT v0.5D1 ONLY.**

Do not implement DXF, STEP, STL, 3D extrusion, CAD-kernel integration, meshing, FEM, or manufacturing functionality.

---

# 1. SCIENTIFIC CONTEXT

The Young Dawgs project investigates the use of large language models to infer procedural generators for disordered metamaterial microstructures.

The broader objective is to explore how changes in generated morphology affect mechanical properties.

The intended pipeline is:

Reference image
→ LLM-derived procedural generator
→ Parametric exploration
→ Native high-resolution generation
→ Exact raster-to-vector representation
→ Manifold qualification
→ Feature-protected simplification
→ Independent geometry validation
→ 2D geometry export
→ Future 3D CAD construction
→ Future FEM
→ Structure-property analysis.

The eventual 3D models must be grounded in validated geometric representations.

A visually similar SVG is not sufficient.

The central question for v0.5D1 is:

**Can we serialize the existing continuous planar geometry into SVG and reconstruct the same geometry from the SVG without losing pores, changing topology, shifting boundaries, or altering subpixel features?**

---

# 2. PREVIOUS PIPELINE MILESTONES

## v0.3 — Parametric exploration

The procedural generator exposes design controls including:

- `solid_fraction_target`
- `strut_scale`
- `pore_scale`
- stochastic seed

Different combinations produce distinct structures within the inferred morphological family.

## v0.4–v0.4.3 — Native resolution

Native-resolution generation and convergence validation were implemented.

The frozen evaluator v1.1 remains unchanged.

The original v0.4.2 P10 calibration failure is retained historically.

The amended v0.4.3 qualification is limited to its tested domain.

## v0.5A — Exact vector geometry

Binary microstructures were converted into exact integer-coordinate planar geometry.

The pipeline demonstrated:

- Exact occupied-cell representation.
- Exact solid area.
- Correct boundary extraction.
- Enclosed-pore identification.
- Zero-error raster reconstruction.

Some exact vector geometries contain inherent non-manifold point contacts.

The historical v0.5A HOLD remains unchanged.

## v0.5A.1 — Manifold candidates

An optional separate manifold-candidate workflow was implemented.

Local solid-side regularization resolves certain non-manifold point contacts by introducing explicitly recorded subpixel geometry changes.

The canonical source and exact vector geometry remain unchanged.

The optional manifold-candidate workflow received AMENDED PASS within its tested domain.

## v0.5B1 — Simplification sensitivity

Ordinary Douglas–Peucker simplification was evaluated.

It demonstrated substantial possible vertex reductions, but also significant continuous boundary changes that could be invisible at the original raster resolution.

## v0.5B2 — Protected simplification

A guarded simplification method was implemented to protect:

- Manifold repairs.
- Narrow struts.
- Selected junctions.
- Close boundary pairs.
- Known connectors.
- Pore identities.
- Exterior void channels.

## v0.5C — Independent geometry validation

The pipeline was independently evaluated across 80 configurations.

One previously unguarded solid section narrowed.

The scientific status remained HOLD.

## v0.5C.1 — Feature-protection correction

A versioned proposal-level width gate was implemented.

The historical failure at Design 4/seed 1, epsilon 0.50, was reproduced:

Original B2 width:

`8.9166666667 cells`

Corrected geometry width:

`9.0000000000 cells`

The corrected implementation passed:

- 100 regression configurations.
- 60 independent configurations.
- Registered topology checks.
- Raster reconstruction checks.
- Continuous geometry budgets.
- Registered feature checks.

The independent cohort contained six newly sampled parameter combinations and two new stochastic seeds.

All 457 software tests passed.

Historical source files remained unchanged.

However, overall scientific advancement remained HOLD because of the separate cumulative small-pore fidelity issue.

---

# 3. CURRENT SCIENTIFIC LIMITATIONS

The scientific status of v0.5C.1 is:

**HOLD_SMALL_PORE_POLICY**

The current geometry-conversion process has demonstrated strong fidelity under its registered tests.

However, the following limitations remain.

## A. Cumulative small-pore distortion

Seven independent pores originally measuring:

`1.0000 cell²`

were reduced during manifold regularization to:

`0.9375 cell²`

This corresponds to:

- Absolute area loss: 0.0625 cell².
- Relative area loss: 6.25%.

The pore identities remain preserved.

The change arises from genuine continuous geometric modification during manifold regularization.

It is not an SVG serialization error.

No amended cumulative small-pore fidelity allowance has been adopted.

Cumulative pore fidelity remains UNQUALIFIED.

The v0.5D1 experiment must preserve this finding.

Do not change the manifold algorithm.

Do not remove or enlarge the pores.

Do not introduce new geometry repairs.

Do not retroactively declare the 6.25% change acceptable.

## B. Feature-coverage limitations

The corrected protected simplifier demonstrated zero measured narrowing across its registered and independent width probes.

However, the finite independent audit sections did not intersect accepted replacement chords.

Therefore, universal width preservation is not established.

The proposal-level width gate directly checks affected geometry in its supported directions, but the guarantees remain limited by its orientation set and measurement horizon.

v0.5D1 does not resolve this limitation.

## C. Physical adequacy remains unknown

The microstructures currently have no registered physical specimen dimensions.

The project has not established:

- Material properties.
- Loading conditions.
- Minimum printable feature sizes.
- CAD-kernel tolerance compatibility.
- Mesh convergence.
- Mechanical strength.
- Manufacturing feasibility.

Do not claim any of these have been validated.

---

# 4. REQUIRED REPOSITORY AUDIT

Before modifying code, inspect the repository thoroughly.

Prioritize:

`docs/pipeline_v0.5/V0_5C_1_HANDOFF.md`

`experiments/pipeline_v0.5/scientific_requalification/run_001/summary/INDEPENDENT_REQUALIFICATION.md`

`docs/pipeline_v0.5/V0_5D_HANDOFF.md`

`docs/pipeline_v0.5/PROTECTED_SIMPLIFICATION_VALIDATION.md`

`docs/pipeline_v0.5/MANIFOLD_QUALIFICATION.md`

`docs/pipeline_v0.5/CONTACT_POLICY.md`

`docs/pipeline_v0.5/ARCHITECTURE.md`

Also inspect:

- Exact geometry serialization.
- Polygon and hole representation.
- Canonical geometry hashes.
- Saved manifold candidates.
- Saved corrected simplified candidates.
- SVG-related dependencies, if any.
- Shapely 2.x integration.
- Independent polygon reconstruction utilities.
- Geometry validity and manifold-checking code.
- Rasterization utilities.
- Continuous area comparisons.
- Boundary displacement utilities.
- Existing test fixtures.
- Source provenance manifests.

Verify the actual repository structure.

Do not assume every named file exists exactly as written.

Do not trust a summary when source code or saved artifacts establish different behavior.

## Audit deliverable

Before coding, write an implementation plan answering:

1. What are the authoritative saved geometry formats?
2. How are exact, manifold, and simplified geometries identified?
3. Which geometries can be exported without requiring new topology modifications?
4. How are polygon exteriors and enclosed pores represented?
5. What coordinate system is currently used?
6. What numerical precision is needed?
7. Which SVG construction will preserve holes correctly?
8. How will the SVG be independently parsed?
9. How will export fidelity be verified in continuous geometry?
10. How will subpixel manifold features be preserved?
11. How will source provenance and qualification statuses be retained?
12. Which existing validation utilities can be reused?
13. What limitations prevent calling an SVG a CAD-ready model?

Freeze the export-validation protocol before running the final real-fixture study.

---

# 5. SCOPE AND AUTHORIZATION

This milestone authorizes:

- Research-only SVG export.
- SVG path serialization.
- Preservation of polygon shells and holes.
- An independently structured SVG reimport pathway.
- Continuous geometry comparisons.
- Raster reconstruction validation.
- Topology and manifold verification.
- Precision and numerical-error testing.
- Provenance manifests.
- Visual diagnostic previews.
- Scientific reporting.

It does NOT authorize:

- Modification of source masks.
- Changes to exact vector geometry.
- Changes to manifold regularization.
- Changes to protected simplification.
- Selection of a production simplification tolerance.
- DXF export.
- STEP or STL export.
- 3D extrusion.
- CAD-kernel integration.
- Meshing.
- FEM.
- Manufacturing qualification.

Do not expand scope without explicit authorization.

---

# 6. FOUR GEOMETRY STATES

The project defines four important geometric representations.

## G0 — Canonical binary raster

The original native 1024 microstructure.

- NumPy uint8.
- Values 0 and 1.
- Solid = 1.
- Void = 0.

## G1 — Exact vector geometry

The exact union of occupied pixel cells.

It preserves the canonical raster geometry exactly.

It may contain inherent non-manifold boundary contacts.

## G2 — Manifold candidate

The optional locally regularized geometry.

This may contain small explicit additions of solid material.

It is not mathematically identical to G1.

## G3 — Corrected protected simplified geometry

The versioned v0.5C.1 simplification result.

It preserves the registered geometric constraints within the tested domain.

It may differ continuously from both G1 and G2.

## v0.5D1 representation

Introduce:

**G4 — SVG-exported and independently reimported geometry.**

For a selected source geometry Gk, the objective is:

`G4 ≈ Gk`

to serialization-level numerical precision.

The primary comparison must be between the imported SVG geometry and the exact saved geometry that was exported.

Do not compare only with G0 and conclude success because the raster remains unchanged.

An SVG round-trip could preserve raster occupancy while significantly changing continuous geometry.

---

# 7. RESEARCH-ONLY STATUS PROPAGATION

Every export must retain the scientific status and provenance of its source geometry.

For example, an export may have:

- SVG serialization: PASS.
- SVG reimport: PASS.
- Continuous round-trip geometry fidelity: PASS.
- Raster reconstruction: PASS.
- Manifold representation: PASS.
- Cumulative small-pore fidelity: UNQUALIFIED.
- Production policy: HOLD.
- CAD-kernel interoperability: UNQUALIFIED.
- FEM readiness: UNQUALIFIED.
- Manufacturing readiness: UNQUALIFIED.

A successful SVG round-trip must not automatically change the scientific acceptance status.

Use explicit fields in the manifest.

Do not use a single Boolean such as `cad_ready=True`.

Do not label a file production-qualified merely because it can be opened in an SVG viewer.

---

# 8. PRIMARY OUTPUT FORMAT — SVG

Implement an SVG exporter for the existing planar polygon geometry.

The primary goal is reliable geometry serialization.

Use SVG as a two-dimensional vector interchange format, not as an illustration-only output.

## Coordinate convention

The existing canonical convention is:

Pixel `(r,c)` occupies:

`[c,c+1] × [r,r+1]`

with:

- x increasing to the right.
- y increasing downward.

Preserve this convention.

Do not silently flip the y-axis.

Do not silently transpose x and y.

Do not introduce any physical scaling.

For a 1024 source, the expected conceptual SVG coordinate domain is:

`viewBox="0 0 1024 1024"`

Verify the actual coordinate frame against the source geometry.

Do not assume an arbitrary margin or padding.

## Physical units

Do not assign millimeters or inches.

The source coordinates are dimensionless raster-cell coordinates.

SVG display dimensions may use ordinary SVG display units, but those are not material specimen dimensions.

Record this explicitly.

Do not allow a downstream script to treat one SVG coordinate as one millimeter by default.

---

# 9. SVG POLYGON AND HOLE REPRESENTATION

The structures contain many enclosed pores.

Preserving holes is essential.

Prefer a canonical compound-path representation where appropriate.

For example, use one SVG path containing multiple closed subpaths:

- Exterior boundary.
- Enclosed pore boundaries.
- Additional polygon components, if supported.

Use an explicit fill rule, such as:

`fill-rule="evenodd"`

where this correctly represents the planar solid.

The exact choice must be justified and tested.

Do not assume that ordinary SVG rendering automatically preserves the intended material/void semantics in every downstream importer.

## Requirements

- All rings must be closed.
- Ring coordinates must be serialized completely.
- Polygon shells must remain distinct from holes in the geometry manifest.
- Hole topology must survive reimport.
- No pore may be silently filled.
- No exterior void channel may be closed.
- No unexpected solid component may be created.
- No self-intersection may be introduced by serialization.
- No non-manifold contact may be created by coordinate rounding.

Use a clear semantic path identifier for the actual solid geometry.

Avoid auxiliary SVG primitives that could be mistaken for physical solid material.

For example, a decorative black background rectangle should not become an additional geometry element interpreted as material.

If a background is useful for visualization, generate it in a separate preview or clearly noncanonical display artifact.

Do not let preview styling change the exported material region.

---

# 10. SVG PATH RESTRICTIONS

For v0.5D1, prefer a deliberately limited SVG geometry subset.

The existing polygons consist of straight boundary segments.

Therefore, the SVG exporter should not need:

- Bezier curves.
- Arc fitting.
- Spline smoothing.
- Raster filters.
- Clipping masks.
- Transform-dependent geometry.
- Implicit approximations.

Prefer explicit path commands equivalent to:

- Move.
- Line.
- Close path.

Use a deterministic ordering of geometry components and rings.

Do not simplify coordinates during SVG export.

Do not remove vertices merely because SVG supports a more compact path.

Existing geometry simplification has already occurred in G3.

SVG serialization must preserve that saved geometry, not perform another simplification pass.

---

# 11. NUMERICAL PRECISION

This is one of the most important requirements.

Some manifold repairs have dimensions substantially smaller than one raster cell.

The previously registered minimum repaired clearance is approximately:

`0.3535533905932738 cell`

Other boundaries contain fractional coordinates from local regularization and protected simplification.

Insufficient decimal precision could:

- Collapse a small ligament.
- Create a new point contact.
- Shift a pore boundary.
- Remove a short segment.
- Change geometric area.
- Make an imported polygon invalid.
- Introduce a new non-manifold singularity.

## Required approach

Determine the actual coordinate precision used by the saved geometry representation.

If coordinates are stored as IEEE 754 binary64 values, a round-trip-safe decimal representation should be used.

For example, a 17-significant-digit serialization strategy may be appropriate for binary64 coordinates.

Verify this rather than assuming a fixed six-decimal formatting rule is sufficient.

Do not truncate coordinates for appearance or SVG file-size reduction.

Do not apply coordinate snapping during export.

Do not round subpixel repair vertices to integer pixel coordinates.

## Precision experiments

Evaluate controlled serialization precision levels as diagnostic negative controls.

Possible tests:

- Full round-trip-safe precision.
- 12 significant digits.
- 9 significant digits.
- 6 significant digits.
- 3 significant digits.

These are exploratory precision tests, not proposed production settings.

The production research export must use a precision level justified by successful round-trip reconstruction.

Low-precision tests must not modify the canonical output.

Record when rounding causes measurable errors or topological failures.

---

# 12. INDEPENDENT SVG REIMPORT

Do not validate the SVG solely by loading data from the same Python objects used to write it.

Implement an independently structured import pathway.

The test must actually read the saved SVG file.

## Required steps

1. Open the serialized SVG.
2. Parse the XML.
3. Locate the declared solid-geometry path.
4. Parse the supported path commands.
5. Recover closed subpaths.
6. Reconstruct polygon shells and holes.
7. Reconstruct the planar solid region.
8. Validate geometric integrity.
9. Compare against the authoritative saved source geometry.

Prefer a separately implemented or vetted path parser rather than using the exporter's in-memory coordinate arrays.

Inspect available dependencies before choosing the import library.

Do not introduce a large CAD toolchain merely to parse SVG.

## Independence requirement

The exporter and importer should not share the same path-string construction/parsing algorithm.

They may use common well-tested geometry libraries for final geometric operations, but shared dependencies must be disclosed.

A genuinely independent parsing step is required.

Do not call the verification independent if it merely copies the original polygon coordinates.

## Unsupported SVG features

If the importer supports only the deliberately restricted v0.5D1 SVG subset, reject unsupported commands and features explicitly.

Do not silently approximate or ignore unsupported path segments, transforms, clip paths, or fill operations.

The limitations of the importer must be documented.

---

# 13. SVG FILL-SEMANTICS VALIDATION

A file may contain all the correct boundary coordinates but still represent the wrong filled region.

Therefore, validate fill semantics.

Test at least:

1. A simple filled rectangle.
2. A rectangle with one enclosed hole.
3. A rectangle with several enclosed holes.
4. A region containing deeply concave boundaries.
5. Multiple solid components where supported.
6. A connected network containing many pores.
7. A narrow exterior void channel.
8. A small interior pore.
9. A pore adjacent to another pore.
10. A manifold-regularized former point contact.

Verify that the reimported geometry represents the intended occupied planar region.

Do not validate solely by comparing SVG text or counting path commands.

The number and placement of enclosed pores must be correct.

---

# 14. SOURCE FIXTURE SELECTION

Start with a small, deterministic set of existing geometries.

Do not generate new procedural structures for v0.5D1 unless a missing fixture is unavoidable and explicitly documented.

The purpose is export validation, not another design-space exploration study.

## Required fixture categories

### Fixture A — Manifold geometry requiring no regularization

Prefer an existing authenticated structure such as Design 9/seed 1, if the current repository confirms it remains suitable.

This case establishes a simple baseline.

### Fixture B — Manifold geometry containing recorded contact regularization

Prefer an existing accepted candidate such as Design 0/seed 0.

This tests whether the SVG representation preserves subpixel contact repairs.

### Fixture C — Corrected protected simplified geometry

Select one saved v0.5C.1 G3 candidate that:

- Was accepted under its registered feature and geometry screens.
- Has nonzero simplification.
- Has complete provenance.
- Contains internal pores.
- Is OGC-valid and manifold.

Do not assume epsilon 0.50 always yields changed geometry.

Inspect saved results and select a qualifying candidate deterministically.

### Fixture D — Small-pore stress geometry

Where available, select a saved manifold candidate containing one of the 1-cell² pores whose cumulative area loss was documented in v0.5C.1.

The purpose is to prove the export preserves the saved geometry exactly, including its already documented pore modification.

Do not attempt to correct that modification.

If one fixture satisfies multiple categories, retain a small independent selection where feasible so different geometry conditions are represented.

## Selection protocol

Record:

- Design.
- Seed.
- Geometry state.
- Source hash.
- Original parameter combination.
- Contact count.
- Simplification setting, if applicable.
- Scientific status.
- Reason for selecting the fixture.

Freeze fixture selection before the final export-validation run.

Do not silently replace a fixture that fails.

---

# 15. CONTINUOUS GEOMETRY ROUND-TRIP VALIDATION

This is the central scientific check for v0.5D1.

For each source geometry Gk and independently reconstructed SVG geometry G4, calculate:

- Source area.
- Imported area.
- Signed area difference.
- Added material area.
- Removed material area.
- Symmetric-difference area.
- Relative symmetric difference.
- Boundary Hausdorff distance or justified bound.
- Exterior boundary lengths.
- Hole boundary lengths.
- Polygon component count.
- Hole count.
- Ring closure.
- Geometric validity.
- Manifold status.
- Minimum registered repair clearance.
- Protected feature coordinates, when available.

The desired result is no meaningful change beyond the numerical precision of the stored geometry and verification calculations.

Because export is intended as serialization rather than geometry approximation, the fidelity requirement should be much stricter than the B2 simplification budgets.

Do NOT reuse the B2 allowance of 0.5% symmetric difference for SVG export.

That allowance was established for a geometry-changing simplification operation.

SVG export is not authorized to change geometry.

## Numerical acceptance

Before final validation, preregister an appropriate numerical comparison policy.

Prefer exact recovery of stored binary64 coordinates where achievable.

If exact coordinate equality is not possible because of justified parser or geometry normalization behavior, define a very small numerical tolerance based on floating-point precision and the coordinate range.

Use geometric equality as well as coordinate-level checks.

Do not require byte-identical WKB when different, equivalent ring ordering is permitted, but do require a clear demonstration that the represented solid regions are geometrically equivalent.

Any positive geometric difference above the registered numerical allowance must be a failure.

Do not silently raise the allowance after inspecting the results.

---

# 16. TOPOLOGY AND MANIFOLD VERIFICATION

For every reimported candidate, verify:

- OGC validity.
- Dedicated manifold-boundary qualification.
- Solid component count.
- Enclosed-pore count.
- Pore identities where available.
- Exterior void-channel connectivity.
- Absence of newly introduced boundary crossings.
- Absence of new point contacts.
- Absence of overlapping rings.
- Absence of degenerate edges.
- Preservation of narrow positive-clearance regions.

Reuse the established manifold checker, but supplement it with independent geometric checks where practical.

Do not treat OGC validity as sufficient proof of manifoldness.

Do not assume the SVG fill rule was interpreted correctly merely because the output has the expected hole count.

---

# 17. SUBPIXEL FEATURE PRESERVATION

The SVG export must preserve the manifold repair features introduced during v0.5A.1.

For every selected registered repair, compare before and after export:

- Repair location.
- Local polygon geometry.
- Added-solid footprint.
- Positive geometric clearance.
- Relevant boundary segments.
- Registered coordinates.
- Hole relationships.
- Local solid-region topology.

A subpixel repair feature that disappears during SVG export is a failure.

A repaired region that becomes non-manifold after reimport is a failure.

A change hidden below the 1024 raster resolution is still a failure if it exceeds serialization-level numerical tolerance.

Do not substitute raster equality for this check.

---

# 18. RASTER RECONSTRUCTION

After independent SVG reimport, rasterize the resulting geometry onto the original 1024 grid.

Use the registered coordinate convention.

Compare with G0.

Record:

- False-positive pixels.
- False-negative pixels.
- XOR disagreement.
- IoU.
- Solid-pixel count.
- 4-connected solid component count.
- Left-right percolation.
- Top-bottom percolation.

The expected result for an accepted saved geometry is:

- FP = 0.
- FN = 0.
- XOR = 0.
- IoU = 1.
- Same component count.
- Same percolation state.

However, the raster test is secondary to continuous geometry equivalence.

A candidate may pass the raster check while still having failed SVG precision or local geometric fidelity.

---

# 19. FROZEN MORPHOLOGICAL DESCRIPTORS

Use the frozen evaluator v1.1 without modification.

Compare the original canonical raster against the independently rasterized SVG geometry.

Relevant descriptors include:

- Solid fraction.
- Component count.
- Largest-component fraction.
- Horizontal percolation.
- Vertical percolation.
- Mean strut thickness.
- P10 strut thickness.
- Median pore diameter.
- Two-point correlation.
- Lineal-path function.

Where arrays are independently confirmed byte-identical, deterministic descriptor equality is expected.

Reuse authenticated results if appropriate, but retain at least one explicit fresh end-to-end evaluator integration test.

Do not describe descriptor equality as independent proof of continuous geometric equivalence.

Retain the historical v0.4.3 P10 qualification caveat.

---

# 20. SVG VISUAL PREVIEW

Generate visualization files for human inspection.

For each selected fixture, provide:

1. Original canonical raster.
2. Saved source vector geometry.
3. SVG rendering preview.
4. Independently reimported geometry.
5. Boundary overlay.
6. Continuous difference visualization.
7. Raster XOR image.
8. Selected pore close-ups.
9. Selected repair close-ups.

The SVG preview must not be the canonical scientific comparison.

Rasterized screen rendering may use antialiasing.

Antialiasing can introduce grayscale pixels or apparent boundary shifts.

Do not interpret these preview pixels as changes to the underlying vector region.

Generate binary validation rasters separately, without display-oriented antialiasing.

---

# 21. EXPLICIT NUMERICAL STRESS TESTS

Include controlled tests designed to expose serialization problems.

At minimum:

1. Integer-coordinate rectangle.
2. Polygon containing half-integer coordinates.
3. Polygon containing quarter-cell coordinates.
4. Polygon containing non-dyadic binary64 coordinates.
5. Small subpixel diamond.
6. Two separated pores with very small positive clearance.
7. Hole touching or nearly touching a shell.
8. Multiple concentric ring boundaries.
9. Large coordinate values near the image boundary.
10. Very short boundary segment.
11. Acute polygon corner.
12. Long irregular ring.
13. Thousands of polygon vertices.
14. Hundreds of enclosed holes.
15. Valid compound path with multiple subpaths.
16. Ring orientation variations.
17. Even-odd fill interpretation.
18. Repeated coordinates.
19. Incorrectly closed path.
20. Missing path closure.
21. Invalid numeric coordinate.
22. Nonfinite coordinate.
23. Unsupported SVG transform.
24. Unsupported curve command.
25. Incorrect SVG namespace.
26. Incorrect fill rule.
27. Coordinate precision truncation.
28. Coordinate orientation reversal.
29. Missing source geometry identifier.
30. Tampered source hash.
31. Modified SVG after export.
32. Unsupported additional geometry primitive.
33. Duplicate geometry path identifier.
34. Valid geometry that rasterizes identically despite a continuous difference.
35. Manifold repair that collapses under deliberate low-precision serialization.

The validator must detect known failures.

Do not merely verify that valid examples pass.

---

# 22. INDEPENDENCE REQUIREMENTS

The research value of v0.5D1 depends on avoiding circular validation.

Use separate stages:

**Exporter**

Authoritative saved planar geometry → SVG.

**Independent parser**

Saved SVG bytes → reconstructed geometry.

**Geometry comparison**

Authoritative geometry versus reconstructed geometry.

**Raster comparison**

Canonical binary raster versus rasterized reconstructed geometry.

**Scientific evaluator**

Frozen descriptors on independently reconstructed occupancy.

These stages should not all obtain their expected output from the same in-memory polygon object.

The independent parser must actually interpret the saved SVG.

Document shared libraries, especially where GEOS/Shapely is used by both the original and reimported geometry pathways.

Do not overstate independence.

---

# 23. SVG METADATA AND PROVENANCE

Every exported geometry must have a machine-readable sidecar manifest.

Prefer JSON, consistent with project conventions.

Include:

- Pipeline version.
- Exporter version.
- Exporter code hash.
- Source geometry state.
- Source geometry hash.
- Canonical raster hash.
- Design identifier.
- Random seed.
- Parameter values.
- Resolution.
- Coordinate orientation.
- Coordinate unit.
- Physical scale status.
- Source scientific qualification.
- Contact-regularization status.
- Simplification status.
- Existing scientific HOLD reason.
- SVG filename.
- SVG hash.
- Importer version/hash.
- Reimported geometry hash.
- Round-trip validation result.
- Geometry comparison metrics.
- Raster comparison metrics.
- Topology result.
- Manifold result.
- Dependency versions.
- Operating system.
- Execution timestamp or run identifier.

Do not invent physical dimensions.

Do not omit historical limitations.

The sidecar must unambiguously identify what was exported.

---

# 24. EXPORT STATUS CLASSIFICATION

Define separate statuses.

Examples:

## EXPORT_SERIALIZATION_PASS

The SVG was written with the registered format and precision.

## SVG_PARSE_PASS

The independent parser recovered supported path geometry.

## CONTINUOUS_ROUNDTRIP_PASS

The recovered planar solid is equivalent to the saved exported geometry within serialization-level numerical criteria.

## RASTER_ROUNDTRIP_PASS

The recovered geometry reconstructs the canonical native-resolution mask exactly.

## MANIFOLD_PRESERVED

The recovered geometry retains the relevant registered manifold condition.

## SOURCE_SCIENTIFIC_HOLD

The source remains subject to unresolved scientific qualification.

## CAD_INTEROPERABILITY_UNQUALIFIED

No independent CAD kernel has imported and validated the geometry.

## FEM_UNQUALIFIED

No meshing or mechanical simulation has been performed.

## MANUFACTURING_UNQUALIFIED

No physical-scale or manufacturing qualification exists.

Do not combine these into one generic success flag.

A research-only export can pass its own validation while retaining the overall scientific HOLD.

---

# 25. FAILURE HANDLING

Do not silently repair invalid imported geometry.

If an SVG cannot be parsed:

- Preserve the SVG.
- Record the parser error.
- Classify the failure.
- Do not substitute source geometry.

If imported geometry is invalid:

- Preserve the reconstructed coordinates.
- Record the geometric defect.
- Do not run automatic topology-changing correction.
- Mark the candidate as failed.

If an SVG loses a subpixel ligament:

- Record the precise feature.
- Measure the change.
- Reject the round-trip.

If a pore is filled or merged:

- Preserve the evidence.
- Reject the round-trip.

If a fixture fails:

- Keep it in the study denominator.
- Do not silently select a replacement fixture.
- Do not reduce decimal precision or change geometry tolerances simply to make the case pass.

---

# 26. PERFORMANCE AND MEMORY

The source geometries may contain approximately 40,000–50,000 vertices and hundreds of holes.

The exporter must handle this scale reliably.

Measure:

- Source loading time.
- SVG serialization time.
- SVG output size.
- SVG parsing time.
- Polygon reconstruction time.
- Geometry comparison time.
- Rasterization time.
- Scientific evaluation time.
- Total validation time.
- Peak RSS.
- Python traced allocation, if practical.

Avoid:

- One heavyweight geometry object per pixel.
- Quadratic all-pairs vertex comparisons.
- Excessive XML element nesting.
- Repeated serialization of unchanged structures.
- Large in-memory preview images when unnecessary.
- Repeated evaluator calls on authenticated identical arrays.

A single compound path may be efficient, but choose the representation based on correctness and parser compatibility.

Do not optimize file size by sacrificing coordinate precision.

Report that traced Python memory may exclude native GEOS allocations.

---

# 27. OUTPUT DIRECTORY

Create an additive experiment area.

Suggested location:

`experiments/pipeline_v0.5/svg_export_validation/`

Use a unique run identifier.

Suggested structure:

- `run_001/`
  - `protocol/`
  - `source_manifests/`
  - `exports/`
  - `imports/`
  - `continuous_metrics/`
  - `raster_reconstruction/`
  - `topology/`
  - `precision_controls/`
  - `figures/`
  - `performance/`
  - `summary/`
  - `verification/`

For each fixture, retain:

- Authoritative geometry reference.
- SVG export.
- SVG sidecar manifest.
- Reimported canonical geometry.
- Geometry comparison.
- Raster comparison.
- Topology report.
- Precision report.
- Performance metadata.
- Acceptance status.

Do not overwrite existing files or experiments.

Keep failed exports and failed reimports.

---

# 28. SOFTWARE TESTING

The previously reported software baseline was:

457 tests passed.

Run all existing tests and new SVG export/reimport tests.

New automated tests should cover:

1. Correct coordinate orientation.
2. Correct viewBox.
3. No physical scaling.
4. Hole preservation.
5. Exterior channel preservation.
6. Ring closure.
7. Fill-rule interpretation.
8. Deterministic path ordering.
9. Round-trip-safe numeric formatting.
10. Fractional coordinate preservation.
11. Subpixel repair preservation.
12. OGC validity after reimport.
13. Dedicated manifold status after reimport.
14. Continuous area equivalence.
15. Symmetric-difference equivalence.
16. Boundary displacement.
17. Exact raster reconstruction.
18. Source provenance.
19. Scientific status propagation.
20. Invalid SVG rejection.
21. Unsupported SVG command rejection.
22. Missing metadata handling.
23. Hash mismatch detection.
24. Tampered SVG detection.
25. Repeated-run determinism.
26. Existing exact geometry preservation.
27. Existing manifold candidate preservation.
28. Existing simplified geometry preservation.
29. No mutation of historical files.
30. No implicit CAD-readiness claim.

Do not weaken earlier tests.

If an existing test fails, diagnose the underlying problem.

Record the final test count.

---

# 29. SCIENTIFIC REPORT

Create:

`SVG_EXPORT_VALIDATION.md`

`SVG_EXPORT_VALIDATION.json`

and an appropriate tabular summary.

The Markdown report must contain:

## A. Purpose

Explain that v0.5D1 is a research-only export interoperability experiment.

## B. Source qualification

Identify the saved geometry sources and their existing scientific limitations.

## C. SVG representation

Explain path construction, holes, fill rules, coordinates, and precision.

## D. Independent import method

Explain how the SVG was actually parsed and reconstructed.

## E. Continuous round-trip fidelity

Report source-versus-imported:

- Area.
- Symmetric difference.
- Boundary displacement.
- Topology.
- Manifold status.
- Holes.
- Repair clearances.

## F. Raster round-trip fidelity

Report FP, FN, XOR, IoU, components, and percolation.

## G. Frozen morphology

Report descriptor consistency.

## H. Precision stress tests

Explain how coordinate rounding affects small features.

## I. Real fixture results

Table:

| Fixture | Source state | Vertices | Holes | SVG size | Geometry difference | Raster XOR | Manifold | Export result |

## J. Performance

Runtime and memory.

## K. Scientific limitations

Explicitly acknowledge:

- Existing cumulative small-pore HOLD.
- Limited independent width-audit coverage.
- Subpixel manifold modifications.
- Absence of physical dimensions.
- No downstream CAD-kernel import.
- No 3D geometry.
- No FEM.
- No manufacturing qualification.
- Potential limitations of SVG importing software.
- Shared dependencies in supposedly independent geometric checks.

## L. Acceptance decision

Separate SVG round-trip qualification from broader scientific advancement.

## M. Next-stage handoff

Explain the requirements for later DXF export, CAD-kernel import, and eventual 3D geometry creation.

Do not implement those stages.

---

# 30. REQUIRED FIGURES

Generate:

1. Source raster and SVG preview.
2. Source vector and imported vector overlay.
3. Continuous geometric difference.
4. Raster difference.
5. Hole preservation close-ups.
6. Subpixel repair close-ups.
7. Numeric precision sensitivity.
8. Area and displacement comparisons.
9. Export/import timing.
10. Summary of fixture acceptance.

Figures should be inspected for correct rendering.

Do not treat visually pleasing output as evidence of mathematical equivalence.

Subpixel features require enlarged coordinate-space close-ups.

---

# 31. SCIENTIFIC ACCEPTANCE PROTOCOL

Before final real-fixture execution, freeze the export-validation protocol.

At minimum, require:

### Source integrity

Authenticated saved source geometry.

### SVG serialization

Valid output conforming to the supported SVG subset.

### Independent parsing

SVG successfully reconstructed without consulting the original polygon coordinates.

### Continuous fidelity

No geometric change exceeding the preregistered serialization-level numerical tolerance.

### Topology

No newly introduced components, holes, contacts, or channel changes.

### Manifoldness

Required manifold status preserved.

### Repair geometry

Registered subpixel repair features preserved.

### Raster

Original binary occupancy reconstructed exactly.

### Provenance

Complete and correct.

### Scientific status

Existing HOLD/UNQUALIFIED states retained.

Do not silently loosen criteria after observing outcomes.

If these conditions pass, the appropriate conclusion is:

**SVG_EXPORT_ROUNDTRIP_PASS_TESTED_FIXTURES**

or an equivalent clearly scoped status.

It is not:

**FULL_SCIENTIFIC_PASS**

and not:

**CAD_READY**

If requirements fail, preserve the failures and issue HOLD for the export stage.

---

# 32. HISTORICAL PRESERVATION

Do not modify:

- Existing procedural generators.
- Native-resolution algorithms.
- Frozen evaluator v1.1.
- Historical v0.4 results.
- Historical v0.4.3 qualification.
- Exact v0.5A geometry.
- v0.5A.1 manifold candidates.
- v0.5B1 experiments.
- Original B2 results.
- Corrected v0.5C.1 results.
- Historical scientific acceptance reports.
- Historical scientific HOLD decisions.

Prefer additive source modules and experiments.

Verify original file hashes using the repository's established inventory mechanism.

If an additive test requires a shared package import change, document it and preserve backward compatibility.

Do not rewrite historical files.

---

# 33. WHAT NOT TO IMPLEMENT

Do not implement:

- New procedural generators.
- New parametric designs.
- New topology repairs.
- New manifold-regularization rules.
- New protected simplification algorithms.
- Scientific small-pore policy amendments.
- General curve smoothing.
- SVG-based resimplification.
- Physical units.
- DXF export.
- STEP export.
- STL export.
- CadQuery.
- OpenCascade.
- 3D extrusion.
- Mesh generation.
- ANSYS.
- FEM.
- Mechanical strength predictions.
- Manufacturing certification.

No 3D work is authorized.

---

# 34. EXECUTION PROCESS

Follow this order.

## Phase A — Audit

1. Inspect repository.
2. Read v0.5C.1 handoff and scientific report.
3. Locate authenticated saved geometries.
4. Inspect serialization and topology tools.
5. Inspect dependency environment.
6. Write architecture and implementation plan.

## Phase B — Protocol

7. Choose and document the SVG geometry subset.
8. Define coordinate convention.
9. Define numeric serialization method.
10. Define independent parsing approach.
11. Define numerical acceptance tolerance.
12. Choose and register fixtures.
13. Freeze the protocol before final testing.

## Phase C — Implementation

14. Implement deterministic SVG export.
15. Implement complete hole/subpath serialization.
16. Implement round-trip-safe numeric formatting.
17. Implement independent SVG parsing.
18. Implement reconstructed polygon assembly.
19. Implement continuous geometry comparison.
20. Implement manifold and topology checks.
21. Implement raster reconstruction and comparison.
22. Implement metadata and status propagation.

## Phase D — Synthetic tests

23. Test analytic polygons.
24. Test holes.
25. Test fractional coordinates.
26. Test short segments.
27. Test subpixel repairs.
28. Test deliberately rounded coordinates.
29. Test unsupported SVG features.
30. Test malformed geometry and metadata.

## Phase E — Real fixtures

31. Load the registered saved geometries.
32. Authenticate source hashes.
33. Export to SVG.
34. Save the files.
35. Independently parse those saved SVG files.
36. Reconstruct planar geometry.
37. Compare continuous geometry.
38. Compare topology and manifoldness.
39. Inspect registered repair clearances.
40. Rasterize the imported geometry.
41. Compare with canonical source masks.
42. Check frozen descriptors.
43. Record all results.

## Phase F — Precision analysis

44. Run controlled lower-precision negative tests.
45. Identify which numerical failures can occur.
46. Verify that the chosen canonical export precision avoids them on the tested cases.
47. Preserve negative-control results separately.

## Phase G — Reporting

48. Generate machine-readable summaries.
49. Generate human-readable scientific reports.
50. Generate and inspect figures.
51. Profile runtime and memory.
52. Run the full software test suite.
53. Verify historical file preservation.
54. Write the next-stage handoff.

## Phase H — STOP

Do not implement DXF or 3D CAD.

Do not begin another pipeline stage without authorization.

---

# 35. REQUIRED FINAL RESPONSE

When complete, answer:

1. What existing project modules were reused?
2. What new source modules were created?
3. What SVG representation was selected?
4. Why was it selected?
5. How are polygon exteriors represented?
6. How are enclosed pores represented?
7. Which fill rule is used?
8. What coordinate convention is preserved?
9. What coordinate precision is used?
10. Was any physical scaling introduced?
11. How is independent SVG reimport implemented?
12. Which dependencies are shared between export and import?
13. What source fixtures were selected?
14. Were all source hashes verified?
15. Did every SVG parse successfully?
16. Were all geometry components preserved?
17. Were all enclosed pores preserved?
18. Were exterior-connected void channels preserved?
19. Was OGC validity preserved?
20. Was dedicated manifold status preserved?
21. Were all registered subpixel repairs preserved?
22. What was the maximum continuous area discrepancy?
23. What was the maximum symmetric-difference area?
24. What was the maximum boundary displacement?
25. Did any coordinate change beyond floating-point tolerance?
26. Did the imported geometry rasterize exactly?
27. What were the maximum FP, FN, and XOR counts?
28. Were frozen morphology descriptors preserved?
29. What precision-related failures were observed in negative controls?
30. What were the output SVG file sizes?
31. What was the export runtime?
32. What was the import runtime?
33. What was the peak observed memory use?
34. Did all previous software tests pass?
35. How many new tests passed?
36. Were all historical files preserved?
37. What files were created?
38. What existing files were modified, if any?
39. What is the exact SVG export qualification status?
40. Does cumulative small-pore scientific fidelity remain unqualified?
41. Does production simplification remain unqualified?
42. Is CAD-kernel interoperability still unqualified?
43. What is required before DXF export?
44. What is required before 3D CAD?
45. What limitations remain?
46. What should the next pipeline milestone be?

Do not claim that successful SVG export qualifies the geometry for CAD kernels, FEM, or manufacturing.

Do not declare the full Pipeline v0.5 complete.

---

# FINAL INSTRUCTION

The Young Dawgs project has already established carefully validated raster, vector, manifold, and simplified geometry representations.

Do not compromise this work merely to produce SVG files.

The objective is to determine whether a standards-based two-dimensional export preserves the complete saved geometry—including holes, narrow connections, subpixel manifold repairs, and numerical precision—when interpreted through an independent import pathway.

A successful SVG round-trip is an interoperability result, not a scientific resolution of the outstanding cumulative pore-fidelity limitation.

Preserve the canonical sources.

Preserve all historical validation records.

Make no additional geometry modifications.

Measure continuous geometry directly.

Retain all failed cases.

Report all limitations accurately.

**Complete v0.5D1, issue a scoped SVG export-validation decision, prepare the next-stage handoff, and STOP before DXF or 3D CAD.**