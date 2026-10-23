# v0.5A.1 contact policies and prospective geometric screening

Default: **contact_policy="preserve_exact"**. Canonical masks and exact vectors
are never replaced. Geometry-changing modes require explicit policy selection.
All units are raster cells; physical scale is null.

## Three states and explicit modes

1. `canonical_binary`: the original generator NPY, with source manifest/hash.
2. `exact_geometry`: byte-preserved v0.5A cell boundaries and polygon reference.
3. `manifold_candidate`: a separately serialized derived geometry with a policy,
   change log, source reference, gates and independent raster/continuous checks.

`preserve_exact` performs diagnosis only and returns `exact_manifold` or
`exact_nonmanifold`. `solid_separate_pores` supports verified same-polygon
hole–hole contacts. `solid_separate_contacts` also supports same-polygon
hole–shell point contacts. `void_side_probe` records a competing local removal;
it is rejected if hole or solid-component counts change. Already manifold inputs
pass through every mode with zero modification and `ACCEPT_NOOP`.

Unsupported defects are quarantined, not passed to a fallback operation. Separate
solid polygons, non-grid contacts, degree >4/more than two rings, crossings,
overlaps, duplicate/zero edges and mere numerical near contacts are not repaired
by the candidate path. Preserve mode is always available. No global offset,
erosion/dilation, smoothing, make_valid or buffer(0) is applied.

## Local solid-side construction

At a verified alternating source vertex v, form the L1 diamond
|x-vx|+|y-vy|<=r, r=0.25. A single set union adds its two triangles lying in void;
the portions already solid do nothing. Each triangle has legs r, area r²/2.
Thus actual added area is r²=0.0625 cell²/contact. All supports are disjoint for
distinct lattice vertices with r<=0.25. Original rings are otherwise retained.
Recorded support containment and unchanged-boundary comparisons verify locality.

The two opposing chamfers have positive separation sqrt(2)r=0.3535533906 cell.
Maximum displacement is r/sqrt(2)=0.1767766953 cell, attained at the old contact.
Direct boundary distances confirm these values. Old and new boundaries coincide
outside supports. Within each support, the perpendicular distance along a V edge
or chamfer never exceeds this value. This supplies a Hausdorff certificate for
this restricted construction. Shapely's densified discrete Hausdorff is also
reported; it is not treated as a generally exact Hausdorff oracle.

No cell center lies in a modified triangle: its L1 distance from the corner is
at least 1, while r<=0.25. Nevertheless, the pipeline independently rasterizes
the actual candidate and verifies XOR/FP/FN rather than relying only on that proof.

The local bridge has **subpixel width**. It is a real continuous-geometry change,
not a demonstrated load-bearing ligament. Its width and short-edge/angle checks
are geometric diagnostics, not physical qualification.

## Prospective gates

Registered in V0_5A_1_PLAN.md and run_001/protocol.json before final candidates:

| Property | Required screening result |
|---|---|
| Original-grid reconstruction | XOR=FP=FN=0; IoU=1 |
| Solid components and percolation | Original raster states unchanged |
| Frozen raster descriptors | Exact equality; no weighted score or relaxed limits |
| Maximum boundary displacement | <=0.25 cell |
| Symmetric-difference area | <=0.0001 × original occupied area (0.01%) |
| Geometry | Valid OGC object and independent manifold boundary PASS |
| Repaired local clearance | Positive and >=0.25 cell |
| Affected new edge | >=0.125 cell |
| Affected boundary-ray angle | >=45° |
| Planar topology | Same solid-polygon component count and OGC hole count |
| Locality | Actual changes and changed boundaries confined to recorded diamonds |
| Solid-side policy | No removed solid; geometry stays in original domain |
| Reproducibility | Identical candidate WKB and measurements on repeat; saved WKB rasterizes exactly |

These are newly registered geometric screening limits, not established mechanical
or manufacturing tolerances. Settings are immutable dataclasses; changing a study
setting requires a new protocol/run. The original exact baseline retains zero
continuous error. No limit was adjusted to obtain a candidate PASS.

## Strategies compared

The quantitative column below uses Design 0/seed 0 and r=0.25 where applicable.

| Strategy | Exact set preserved? | Manifold boundary | Pore/solid topology | Area delta | Max displacement | New clearance | Recommended use / CAD implication |
|---|---|---|---|---:|---:|---:|---|
| A: exact ring correction | Yes | No for genuine source contact | Same set and singularity | 0 | 0 | 0 | Correct bookkeeping artifacts; cannot regularize this contact |
| B: preserve and quarantine | Yes | No | All original topology retained | 0 | 0 | 0 | Default authoritative evidence; block manifold-dependent operations |
| C: local solid addition | No | Yes under registered gates | OGC holes and solid components retained; touching void closures separated, positive-width local solid link added | +0.0625 | 0.1767767 | 0.3535534 | Preferred opt-in geometric candidate; subpixel feature physically unqualified |
| D: local void addition | No | Yes in tested representative | Merges two pore interiors, holes 289→288 | -0.0625 | 0.1767767 | 0.3535534 | Retained diagnostic candidate; rejected for pore topology change |
| E: patch decomposition | Assembled set can be exact | Individual patches may pass; assembled source still fails | Singularity remains after assembly | 0 | 0 | 0 | Explicit shared seams can be valid; does not bypass the source singularity |

Hole–shell solid-side regularization removes a zero-clearance exterior contact
and separates the hole from its shell. Original complementary-8 raster void
classification stays unchanged because occupancy stays unchanged. The continuous
contact topology changes and is reported explicitly; OGC hole count is preserved.

## Status boundaries

Report separate exact-fidelity, classifier, manifold-candidate, modification-budget
and raster-morphology results. `physical_feature_qualification`, mesh quality,
mechanical validation and manufacturability remain **UNQUALIFIED**. A tested-domain
amended candidate PASS is not a revision of the historical exact v0.5A HOLD.
Downstream code must explicitly select the candidate and read its qualification;
it must never substitute a candidate for canonical or exact geometry implicitly.
