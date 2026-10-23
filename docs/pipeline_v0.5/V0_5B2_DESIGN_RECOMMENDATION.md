# Proposed v0.5B2 architecture — recommendation only

Status: **NOT IMPLEMENTED**. This document is an output of v0.5B1, not an
authorization or acceptance of v0.5B2. Native raster-cell coordinates remain the
only spatial units. No production simplification tolerance is selected.

## Evidence driving the design

The five-fixture sweep is retained in
`experiments/pipeline_v0.5/simplification_sensitivity/run_002`. All 40 primary
Douglas–Peucker candidates remained OGC valid and manifold, with the same solid
and hole-region correspondence. Those invariants alone did not protect local
geometry. Every repaired fixture first triggered the prospectively defined
repair-change warning at ε=0.20, with almost no useful vertex reduction. At
ε=0.50 the five structures lost approximately 20% of their vertices and retained
identical 1024 rasters and frozen descriptors, while repaired neighborhoods
changed and some monitored natural chords narrowed. At ε=0.75, D2 contact_0002
clearance fell from 0.353553 to 0.312348 cell. At ε=1.00 the D9 top connector's
measured inward depths fell from 5 to 4 cells. Three natural probes per fixture
do not constitute exhaustive bottleneck screening.

At ε=1.00 all 24 repair separations became undefined under the fixed void-anchor
tracking rule. Global manifoldness and the local solid links still passed. This
is loss of feature qualification, not evidence that all repairs were severed.
The proposed architecture must treat undefined tracking as rejection until it
can establish the relevant correspondence independently.

Actual sampled boundary distances exceeded the nominal simplification tolerance
at some aggressive settings. D0 at ε=0.75 had a verified source-to-candidate
distance of 1.245682 cells. Therefore algorithm tolerance and permitted output
displacement must be separate controls.

## Comparison of protection strategies

| Strategy | Recommendation and reason |
|---|---|
| Freeze only repair vertices | Necessary anchors can help partition arcs, but vertex identity alone cannot prevent a newly proposed neighboring chord from crossing a protected region. Insufficient as the final constraint. |
| Freeze full repair boundary segments | Use exact accepted boundary subsets inside explicit guard regions, with fixed entry/exit points. Reject any other chord that enters a guard or changes its solid/void geometry. This directly addresses the ε=0.20 repair reshaping. |
| Spatially varying tolerances | Zero geometric change in guards; independently trial positive tolerances on free arcs. A free-arc ε=0.50 is a useful experimental starting point because of the observed reduction and raster equality, not a production setting. |
| Protect narrow struts and junctions | Expand the feature registry beyond the 15 diagnostic natural probes. Include the saved D9 connector, all registered repairs, narrow corridors and junction incidence. Preserve both positive-area links and relevant widths. |
| Local pore constraints | Carry incident void-region identities and adjacency through each arc edit. Validate full solid, hole and exterior-void correspondence after combining edits. Ring counts alone are insufficient. |
| Manifold rejection | Retain the dedicated checker in addition to OGC validity. Reject contacts, overlaps, pinches, collapsed rings and zero-length edges. |
| Iterative validation | Trial edits on immutable baseline references, validate locally, then validate the combined geometry globally. Reverting a trial is allowed; silently repairing its output is not. |
| Exterior versus pore boundaries | Maintain separate budgets and feature roles. D1 includes a hole-shell repair and D9 has a boundary connector, so exterior arcs require feature constraints as well. Separate treatment must still pass joint validation. |
| Constrained edits versus post hoc repair | Constrain proposals before acceptance. No buffer, make_valid, morphology operation or renewed contact regularization may conceal a failed edit. |
| No-op fallback | Retain the exact accepted arc whenever its constraints cannot be established. A deterministic unchanged result is an acceptable outcome. |

## Recommended data flow

1. **Immutable source bundle.** Load the accepted WKB, exact reference, original
   mask, repair records, provenance and frozen evaluator identity. Verify hashes.
   Retain distinct exact, accepted and diagnostic representations.
2. **Constraint registry.** Assign stable feature IDs to all 24 repairs, the D9
   connector and an expanded, reproducible corridor/junction screening. Store
   incident solid/void identities, boundary intervals, guard polygons, anchors,
   baseline widths/separations and the interpretation of every measurement.
   The B1 one-cell repair ROI is evidence for an initial guard, not proof that
   one cell is universally sufficient. Enlarge guards prospectively to cover
   interacting features, incidence and any chord influence.
3. **Arc partition.** Split rings at guard crossings and stable anchors. Preserve
   the entire accepted boundary inside guards and all guard endpoints. Index
   guards and neighboring arcs spatially; disallow proposed free chords that
   cross, enter or alter a guard. Adjacent protected solid/void regions must
   remain identical as sets, not merely retain selected vertices.
4. **Free-arc proposals.** Apply a constrained simplification to each eligible
   arc with a recorded local tolerance and displacement budget. Preserve ring
   order, endpoint identity and exterior/hole role. A tolerance ladder may
   decrease after rejection; it must be frozen before the confirmatory study.
5. **Local verification.** Check guards, relevant interface separation, local
   positive-area connectivity, void labels and junction incidence. Enforce a
   continuous displacement bound independent of nominal ε. Retain additions and
   removals separately so area cancellation cannot hide shape change.
6. **Combined verification.** Check OGC and dedicated manifold validity, complete
   positive-area solid/hole/void correspondence, boundary distances, original
   and baseline raster round trips, frozen descriptors and all registered
   feature constraints. Local passes do not imply a combined pass.
7. **Deterministic acceptance or rollback.** Accept only a fully qualified
   diagnostic candidate under a prospectively frozen B2 policy. Otherwise
   reduce free-arc proposals or return original arcs. Record rejected geometry,
   failed constraints, selected fallbacks and hashes. No weighted score may
   compensate for a failed critical constraint.

## Proposed prospective acceptance tests

These are proposed tests for a future B2 protocol. Freeze the final numerical
budgets and expanded feature-selection procedure before implementing or judging
the protected simplifier; B1 does not establish production or mechanical limits.

- Zero tolerance and all-protected input return the original geometry, without
  mutating input bytes. Repeated runs yield identical output geometry and IDs.
- Protected boundary sets and solid/void occupancy within guards remain exactly
  unchanged, allowing only explicitly declared numerical comparison allowances.
  B1 used 1e-10 cell for lengths and 1e-12 cell² for areas. Test adversarial
  neighboring chords that retain protected vertices but cross a guard.
- All repairs retain their incident void identities, resolved local manifold
  links and at least their accepted 0.3535533905932738-cell separation. Undefined
  feature tracking is a failed qualification, never a recovered pass.
- Retain the D9 connector's two registered 5-cell depths and its positive-area
  link; require no narrowing at the expanded supported corridor probes. Add
  analytic pinches, slit openings, thin ligaments, high-curvature junctions and
  interactions between adjacent guards. Width claims must retain their geometric
  definition; they are not load-bearing strength predictions.
- Require OGC validity, nonempty polygonal structure, closed simple rings and
  zero dedicated manifold violations. Require bijective positive-area region
  correspondence for solids, holes and exterior voids, with no new exterior
  opening/closure. Test examples where equal ring counts hide a merge and loss.
- Preserve the canonical 1024 raster exactly as an initial conservative B2
  hypothesis: FP=FN=XOR=0, IoU=1, the original component count/largest fraction
  and both percolations unchanged. Verify all frozen scalar and curve descriptors
  remain identical using the established interface and authenticated cache.
  This is necessary alongside continuous constraints, not sufficient alone.
- Set independent upper bounds for boundary displacement and continuous
  added/removed/symmetric area before the confirmatory sweep. Report a certified
  bound or conservatively reject; do not substitute nominal ε for measured
  error. Adaptive diagnostic sampling can tighten a loose bound but cannot
  change the chosen acceptance budget. Do not infer an acceptable area budget
  from B1's smallest net area change.
- Evaluate all five saved fixtures plus synthetic adversarial cases; hold out
  additional seeds/designs for any broader claim. Report no-op cases and useful
  reduction separately. Do not impose an arbitrary reduction target that can
  override the constraints.
- Verify the frozen evaluator, generators, historical inventories, exact WKB
  and accepted manifold WKB remain byte-identical. Keep all failed diagnostic
  candidates and the historical acceptance decisions.

Before v0.5C, complete an explicitly authorized v0.5B2 implementation, its
prospectively registered scientific qualification and reproducible selection
policy, then define a separate 2D-export specification and round-trip validation.
No B1 candidate is qualified for CAD, FEM or manufacturing.
