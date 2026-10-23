# v0.5B2 prospective architecture and implementation plan

Scope: additive feature-protected simplification of explicit accepted manifold
inputs. No C/D, export, physical scaling, CAD, FEM or automatic geometry repair.
Historical B1 data and all earlier decisions remain immutable.

1. **Algorithm.** Deterministic Douglas–Peucker proposals on eligible open ring
   chains; preserve original coordinate subsets and orientation. Requested
   tolerances are [0,0.20,0.35,0.50,0.75], independently from one source. Epsilon
   zero is a byte-preserving clone. A proposed chord passing the DP deviation
   criterion must also pass the constraints below. No global simplifier call
   is treated as proof of safety.
2. **Protected representation.** Keep full original segments intersecting guards,
   including their endpoint coordinates, with stable ring/segment IDs. Partition
   cyclic rings into free edge runs between protected endpoints; never simplify
   across those endpoints. Rings without protected edges use two deterministic
   anchors. Reassemble with unchanged hole ownership and ring winding.
3. **Guard construction.** Repair boxes enclose the actual saved diamond,
   B1's one-cell analysis neighborhood, plus requested-tolerance influence.
   Protect the saved generator connector and 24 supported B1-style natural chord
   probes per fixture (including the original three, where available), covering
   their complete chords and local anchors. Additionally guard *every* detected
   skeleton location with EDT diameter <=8 cells and every skeleton junction
   (8-neighbor degree >=3), using local radius plus tolerance and half-cell
   margin; connected features use unions of local boxes rather than a global
   large radius. Guard nonadjacent boundary pairs <=2 cells apart (different
   rings, cyclic segment-index separation >=8, or nonadjacent opposing sides
   with direction cosine <=-0.5). A synthetic one-cell U-shaped exterior channel
   demonstrated that index distance alone misses its two opposing sides; this
   detection correction was made before any real development or holdout outcomes.
   These are geometric risk
   conditions, not mechanical-width or strength definitions. Report all features,
   detected support pixels, guard geometry, original segment/vertex IDs and
   measurements. Sparse normal probes supplement, not replace, dense screening.
4. **Chord checks.** Spatially index original segments and guards. A replacement
   may not enter any guard, collide with an unrelated original boundary, create
   a nonadjacent gap below 0.25 cell, exceed the independent displacement budget,
   exceed conservative fan-triangle material/pore budgets, or contain an original
   half-integer cell center in its fan-change support. The local raster rule is
   conservative; final independent full-grid reconstruction remains mandatory.
5. **Continuous displacement certificate.** A polyline and its endpoint chord
   have two-sided Hausdorff distance no greater than the maximum original vertex
   distance to the chord. Distance to a convex segment is convex on each original
   edge, so the source maximum is attained at vertices. For each interior chord
   projection, continuity of the polyline's projection between its endpoints
   supplies a source point with that projection and perpendicular distance within
   the same bound. Combining matched source subchains/chords proves a global
   boundary upper bound. Retain B1 independent sampled lower/upper measurements;
   reject a certificate contradicted by measured distances. This certificate
   does not establish topology or widths.
6. **Material budgeting.** Fan triangles bound the entire region potentially
   changed by a chord even if signed contributions cancel. Allocate additions
   and removals conservatively by winding and shell/hole role; reject proposals
   exhausting independent global or per-pore budgets. Final actual Boolean
   additions/removals/symmetric difference and matched pore areas must pass too.
7. **Validity and topology.** Check newly proposed chords against each other at
   assembly; restore implicated source chains in one deterministic batch. Apply
   existing OGC, dedicated manifold, positive-area solid/hole/void correspondence
   and exterior-channel checks globally. Hole identities have stable source IDs,
   full boundary hashes and coordinates, overlap match, areas and containment.
   Ambiguity is a rejection. No make_valid, buffer or morphology repairs.
8. **Feature validation.** Compare every guard's solid and boundary geometry as
   sets, and protected segment coordinates directly. Require zero change, all
   registered clearances/chords/depths defined, zero width loss and all supported
   local solid links preserved. Near-boundary risk measurements are not physical
   ligament widths. Unknown feature measurements cannot pass.
9. **Bounded rollback.** A failed leaf chord restores that source subchain without
   retrying a smaller tolerance. Record its full original chain, replacement,
   reason and restored coordinates. After one assembly conflict rollback, a
   failed global candidate is retained as REJECTED_CANDIDATE and the original
   baseline is independently qualified as ACCEPTED_NOOP (or rejected if ingress
   does not qualify). Record both. No repeated arbitrary retries. Local changes
   elsewhere may remain only if the combined candidate passes every gate.
10. **Reproducibility.** Hash masks/exact/manifold inputs, configuration, code and
    outputs; stable source ordering, ring indices, pixel scan order and DP tie
    breaking. Save WKB/NPY, full proposal/guard/rollback logs and both geometric
    comparison baselines. Same-environment repeated candidate WKB is required.
    Cross-GEOS byte identity is not claimed without execution.
11. **Reuse.** B1 authenticated source loading, context/feature preparation,
    indexed distances, region correspondence, area/raster comparisons, frozen
    native evaluator and authenticated descriptor cache; A/A1 exact conversion
    and ingress qualification for missing holdout vectors only. Existing five
    development candidates are never recomputed. Source masks are never generated.
12. **New modules.** A separate `geometry/protected` package for settings, guards,
    chain/chord engine, independent qualification, source preparation, registered
    study execution and reporting; one additive test file and new documentation.
13. **Prospective limits.** The JSON/Markdown protocol records exact protection,
    zero registered width/clearance loss, zero raster/descriptor change, stable
    topology and bounded continuous errors before final results. These are
    conservative *geometric screening* limits, not validated physical fidelity
    limits. Scientific/general production qualification remains scoped accordingly.

## Development and independent holdouts

Development is exactly the five B1 fixtures. Reserve **all** remaining combinations
in the existing v0.4.1 native-1024 registered manifest set: D0/S1, D1/S1, D2/S1,
D5/S1 and D9/S0, sorted by design then seed. Membership uses source paths only,
not image appearance, geometry quality or outcomes. They supply new seeds at the
same five parameter positions; no claim of unseen-parameter validation is made.
This selection and input hashes are recorded before any holdout geometry check.

Missing holdout vectors are a known audit finding: prepare new, separately named
exact/A1-policy ingress artifacts from the existing authenticated masks, using
unchanged converters/settings. Never silently substitute or rerun a generator.
An unsupported/rejected ingress is retained and counted as a holdout limitation;
it is not replaced. Freeze final implementation/configuration after development
and before holdout preparation/evaluation. No tuning to holdout outcomes is allowed.
