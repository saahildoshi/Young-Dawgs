# v0.5B2 prospective protocol

Recorded before final B2 candidate outcomes. Machine authority:
`PROTECTED_SIMPLIFICATION_PROTOCOL.json`; each new run snapshots its exact bytes,
source manifests and implementation. Implementation is frozen a second time
after development and before independent holdout ingress/evaluation.

Five development plus five deterministically reserved holdouts, each at
[0,0.20,0.35,0.50,0.75], give 25+25 planned configurations. No post hoc tolerance
refinement, excluded failures, adaptive acceptance thresholds or production
tolerance selection is permitted. Any necessary algorithm revision after holdouts
consumes those holdouts and requires a fresh independent set; do not relabel them.

## Hard invariants and budgets

| Property | Required result |
|---|---|
| Inputs, historical artifacts and frozen evaluator | Byte-identical |
| Geometry | Nonempty valid Polygon/MultiPolygon; same components/ownership/orientation; closed simple rings; no dedicated manifold violation |
| Solid/hole/void identities and exterior channels | Bijective positive-area correspondence; no merges, splits, losses, births or exterior opening/closure |
| Guard geometry | Exact solid/boundary set equality within every guard; original protected coordinates/segments retained |
| Repairs | Full original patch retained; defined relevant separation; zero separation loss (length comparison allowance 1e-10 cell) |
| Registered supported natural links/chords and connector depths | Defined; local links pass; zero width/depth loss (same allowance) |
| New nonadjacent chord clearance | >=0.25 cell; near baseline features are guarded unchanged |
| Independent continuous boundary displacement | Certified upper <=sqrt(2)/2 cell, the center-to-corner distance of a native cell; not the requested 0.50 trial tolerance |
| Actual added solid / baseline occupied area | <=0.0025 |
| Actual removed solid / baseline occupied area | <=0.0025 |
| Actual symmetric difference / baseline occupied area | <=0.005; additions/removals reported separately |
| Each matched pore's absolute area distortion | <=0.005 of its original pore area |
| Original-grid reconstruction | FP=FN=XOR=0; IoU=1; same components, largest fraction and both percolations |
| Frozen morphology | Exact scalar and full curve equality through native v1.1 interface; authenticated cache permitted |
| Determinism/serialization | Repeated WKB identical in executed environment; persisted WKB reconstructs the recorded raster |
| Unsupported, ambiguous or undefined required measurements | Reject; never substitute zero or a recovered pass |

The independent displacement ceiling derives from native-cell geometry, not a
production tolerance choice. The redistribution limits deliberately allow only
one part in 400 of occupied area for each sign, with a separate per-pore cap to
prevent global cancellation hiding localized distortion. These are transparent,
prospective engineering screens; no experiment establishes them as mechanically
or statistically sufficient. Report geometric-screen acceptance separately from
**broader scientific/physical fidelity UNQUALIFIED**. If the screens yield only
no-ops, retain that result rather than relaxing them. Historical A1 modifications
are reported cumulatively against exact geometry, not charged or hidden as B2
changes. Whole-mask P10 and its v0.4.3 caveat remain unchanged.

## Algorithm controls and failure semantics

The architecture document fixes dense risk conditions, influence-derived guards,
stable ordering, conservative chord checks and bounded rollback. Every leaf
proposal rejection retains its original/replacement/restored coordinates. A
global failure retains raw candidate metrics/WKB and separately evaluates a
baseline fallback; accepted no-op does not erase or reclassify the rejected raw
proposal. Dispositions distinguish ACCEPTED_CANDIDATE, ACCEPTED_NOOP,
REJECTED_CANDIDATE, PARTIAL_REQUIRES_QUALIFICATION, UNSUPPORTED_INPUT and
INTERNAL_ALGORITHM_ERROR. No partial/unqualified candidate is downstream eligible.

Report local rejections and global rejections separately, not as independent
scientific trials. Save all expected configurations, including unsupported ingress
and execution failure records. Peak Python-traced memory omits some GEOS-native
allocations; RSS is process high-water, not candidate incremental memory.

Stop after development/holdouts, full regression, preservation verification,
figures and formal acceptance/handoff. No v0.5C implementation is authorized.
