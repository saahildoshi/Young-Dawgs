# v0.5B1 audit and prospectively frozen study design

Scope: diagnostic simplification sensitivity only. No production tolerance,
protected simplifier, smoothing, export, physical scaling, CAD or FEM.

## Repository audit: twelve questions

1. Exact geometry is stored as integer oriented loops in exact_boundaries.json
   and derived little-endian polygon WKB. For this study use the saved
   manifold_qualification/run_001/design_*/exact_geometry/exact_polygon.wkb;
   do not reconstruct it or rerun the generator.
2. Accepted candidates are the separately named
   solid_separate_contacts/manifold_candidate.wkb in those same five cases.
   qualification.json has accepted=true; ACCEPTANCE.json scopes the five-case
   amended qualification. Verify WKB hashes using that run's verification/
   new_files.json, plus canonical/exact hashes in input_manifest.json.
3. Shapely Polygon.exterior and interiors represent shells and hole rings.
   Canonical loop coordinates retain the x-right/y-down raster-cell convention.
4. All five saved candidates are single Polygons, each with one shell. New
   diagnostics must also handle multipart, empty and invalid results.
5. Repaired locations, L1 radius and operations are stored in qualification.json
   changes; source phase sectors/rings are in contact_report.contacts. There
   are 1,0,6,8,9 repairs for D0/S0,D9/S1,D1/S0,D2/S0,D5/S0 respectively.
6. v0.5A.1 measured relevant boundary arcs in a local window, their separation,
   affected edge lengths/angles and the exact diamond construction. Its global
   GEOS minimum_clearance is not a physical neck-width definition.
7. Reuse geometry/manifold/contacts.py inspect_boundary and polygon_rings,
   Shapely validity/closure/simple-ring checks and explicit empty/type checks.
8. Reuse planar.rasterize_exact_geometry, raster.compare_binary_masks,
   geometry topology/frozen evaluator loading, evaluate_native, environment and
   repository inventories. Existing modules remain byte-identical.
9. Add full simplification/exact cumulative Boolean differences, indexed sampled
   boundary-distance bounds, hole/void overlap correspondence, repair retention,
   fixed-window clearance and local links, natural-neck probes and threshold scans.
10. Shapely 2.1.2 simplify returns a new geometry. At epsilon=0 explicitly return
    a WKB clone unchanged; every nonzero tolerance starts directly from the same
    saved baseline. Verify source bytes and repeated candidate WKB.
11. Isolate all code in a new geometry/sensitivity package and a new test file;
    register a fresh experiments/pipeline_v0.5/simplification_sensitivity run,
    snapshot code/configuration/source hashes and refuse overwrite/resume.
12. Principal costs are continuous overlay, indexed boundary distance sampling,
    manifold segment graphs, rasterization and frozen descriptor evaluation.
    Avoid global quadratic Hausdorff, all-pairs vertices and repeated descriptors.

Reviewed v0.5A architecture/validation/handoff, v0.5A.1 contact analysis/policy/
qualification/handoff, actual geometry and manifold modules, source manifests,
stored WKB/qualification records, tests, dependency specifications and relevant
v0.4 thickness/neck and frozen evaluator interfaces. Source candidates verified
against their existing artifact hashes. A pre-edit repository hash inventory is
recorded separately before implementation.

## Frozen primary experiment

Five fixtures: design_000_seed_000, design_009_seed_001, design_001_seed_000,
design_002_seed_000, design_005_seed_000 from the saved v0.5A.1 accepted policy.
Primary: Douglas–Peucker, preserve_topology=True, epsilon (native cells):
[0,0.05,0.10,0.20,0.35,0.50,0.75,1.00]. Forty independent primary candidates.
Negative control: D0/S0 only, preserve_topology=False at [0.35,0.75,1.00].
Three additional diagnostic controls, never combined with primary conclusions.
No post-hoc refinements are planned. No post-simplification repair is permitted.

For each candidate retain WKB, method/epsilon/source/output hashes, validity,
dedicated manifold contacts, topology, complexity/serialization, both Boolean
comparison baselines, boundary-distance observations, local features, original
and baseline-raster comparisons, frozen descriptors/cache provenance and timings.
All outputs remain diagnostic candidates, including those passing every screen.

## Baselines and quantitative definitions

A: accepted manifold candidate → simplified candidate (new simplification error).
B: original exact v0.5A polygon → candidate (cumulative continuous difference).
C: canonical mask and independently rasterized accepted baseline → reconstructed
candidate. Never conflate these. Vertex reduction denominator is the accepted
manifold vertex count, excluding duplicate closure coordinates. Report existing
exposed-edge→exact-collinear reductions separately.

Use actual region differences/intersections for added/removed/symmetric area.
Match positive-area solid/void/hole regions by indexed overlap to detect losses,
splits, merges and newly enclosed/open exterior voids, rather than just ring count.
Geometry interior-component counts and raster 4-components remain separate.

Boundary distance: sample each segment at spacing <=0.25 cell, including all
vertices; find exact sample-to-nearest-target-segment distances using STRtree.
Compute both directions, exterior and hole subsets. The measured maximum is a
lower bound on continuous Hausdorff; adding half the maximum sample gap gives
an upper bound by the distance function's 1-Lipschitz property. Report both,
never a false exact maximum. Equality returns exact zero. At unchanged accepted
baselines the prior saved v0.5A.1 construction certificate may be cited separately.
Use local versions near repairs; no O(V²) full-boundary library Hausdorff.

## Prospective feature regions and risk flags

For each recorded radius-r repair, define analysis ROI half-width r+0.75=1.0
cell, clipped to the original domain. The 0.75-cell safety margin is fixed for
all tolerances; it does not constrain the simplifier. Preserve original source
phase-sector identities. Match the two incident void regions using canonical
void-cell centers. Measure actual local interface separation, retained original
added-solid fraction, local symmetric area, boundary displacement, manifold
events, and positive-area solid connection between fixed solid-sector anchors
at offset 0.75 cell. Merged/lost anchors or ambiguous arcs produce explicit
undefined reasons, not generic minimum_clearance substitutes.

Report any continuous ROI change and any clearance below baseline (numeric
comparison allowance 1e-10 cell). A **material repair risk flag** means any
local link/contact failure, loss of >=10% of original added material, clearance
drop >=10%, or ROI symmetric difference >=10% of original added area. These
are prospective exploratory warning definitions, not scientific acceptance gates.
Report the continuous measurements as well as the flags. A moved/widened repair
can trigger a change warning while remaining resolved; do not call it severed.

Additional monitored necks: the saved D9 top-boundary connector, using actual
inward solid depths along registered gap-column centers; and up to three fixed
spatially separated low-EDT skeleton samples per fixture. Natural probes use
local skeleton PCA to define a normal cross-section and local tangent anchors;
only supported contiguous, unclipped baseline chords are retained. Record normal
chord widths and local anchor connectivity as geometric diagnostics, not true
minimum load-bearing width or a comprehensive bottleneck search.
GEOS robustness distance newly below 1e-6 cell receives a separate numerical
near-zero warning; this must not be interpreted as a measured strut width.

Morphology warning definitions: separately report any nonzero descriptor drift;
an exploratory notable-drift marker is density absolute change >0.001, relative
mean/P10/pore change >1%, or S2/L NRMSE >0.01. These flags are deliberately
sensitive study annotations (sub-cell-scale dimension changes), not transferred
v0.4 scientific thresholds or a production acceptance protocol. Retain the
v0.4.3 P10 caveat and original failed calibration. No weighted fidelity score.

## Execution, caching and interpretation

Characterize and persist baselines/ROIs before the sensitivity stage. Evaluate
deterministic synthetic tests before running all 43 configurations. Cache frozen
descriptors only by verified raster hash/evaluator/configuration identity with
bounded per-fixture storage; exact array equality permits reuse of baseline
descriptors with explicit provenance. Do not retain all geometry candidates in RAM.
Measure simplification, validation, manifold, raster, morphology and total cost;
Python-traced peak excludes untracked GEOS/native memory.

First failures are first tested failing tolerances and preceding tested brackets,
with full non-monotonic sequences retained. No observed failure means none in
the tested interval, not proof of absence. A conservative promising diagnostic
requires valid/manifold geometry, unchanged relevant topology and monitored
features, exact raster descriptors and positive vertex reduction. This is not
a production tolerance decision. Draw v0.5B2 design recommendations from actual
results, then stop without implementing them.

Primary API references checked:
https://shapely.readthedocs.io/en/2.1.2/reference/shapely.simplify.html
https://shapely.readthedocs.io/en/2.1.2/reference/shapely.hausdorff_distance.html
https://shapely.readthedocs.io/en/2.1.2/reference/shapely.segmentize.html
