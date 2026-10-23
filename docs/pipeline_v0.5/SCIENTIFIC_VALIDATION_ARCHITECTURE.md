# v0.5C preimplementation audit and architecture

The pre-C inventory contains 4,657 files. All recorded B2 freeze paths authenticate.
The 10-point, two-replicate v0.3 plan uses design seed42 and common stochastic
seeds0/1. Native1024 saved outputs exist for points0,1,2,5,9 only. The requested
points3,4,6,7,8 have authenticated original256 arrays, not saved1024 masks.
C will obtain their first native1024 realization with the frozen v0.4.1 worker,
without resampling or altering any renderer. Every newly created mask is retained
under C; previous arrays and historical acceptance remain untouched. This is
new source execution, explicitly distinguished from reusing historical1024.

| Audit interface | Finding and independent C layer |
|---|---|
| G0 | NPY uint8 binary1024, solid1, y down; manifest NPY/PNG/pixel hashes |
| G1 | A exact cell-union polygon WKB plus exact boundary JSON; may be singular |
| G2 | Separate A1 `solid_separate_contacts` WKB and contact/repair qualification |
| G3 | Saved B2 `candidate.wkb`, guards, chains, raw and final qualifications |
| Serialization | Little-endian double WKB; C adds full coordinate JSON reconstruction, precise order/orientation checks |
| Rasterization | Frozen scanline is supplemented by prepared GEOS point predicates; positive boundary ties recorded |
| Evaluator | Unmodified v1.1 via `resolution_worker.evaluate_native`; pixel-equal arrays permit descriptor reuse |
| Topology / matching | Existing manifold classifier and B1 overlap graph retained as reference; C builds separate incidence and reciprocal-anchor/overlap matches |
| Continuous metrics | Frozen B1 Booleans/distances retained; C uses translated fsum shoelace, actual three pairwise Boolean comparisons, independent changed-boundary sampling |
| Width/repair | Existing 24 probes, saved connector and local repair diagnostics; C adds independently selected axial probes for both phases and medial-axis coverage |
| Hashes | SHA256 file bytes, pixel bytes, recorded source paths; verify frozen path subset rather than dynamic glob that now includes new C files |
| Available new parameters | All five unused positions, both registered seeds, first native1024 artifacts required |
| Existing tests | 363 tests including exact, manifold, sensitivity, guarded simplifier; retain every expectation |
| Shared dependencies | WKB parser, polygon construction, set operations, nearest-segment predicates all share GEOS; raster descriptors share frozen definitions. No independent kernel or interval arithmetic claim |

The implementation lives in a new `geometry.validation` package. Validation
loads persisted geometry, reconstructs coordinates, calculates independent
checks and records disagreement without editing older components. Source/algorithm
freeze and prospective acceptance logic are in scientific_validation/run_001/
protocol/PROTOCOL.json. All40 saved B2 configurations at eps0,.2,.5,.75 are
revalidated before the40 new-point trials. Unsupported ingress stays quarantined.
Sampling supplies lower and Lipschitz upper boundary bounds, not an exact
Hausdorff maximum. Width screens do not certify all continuous bottlenecks.
