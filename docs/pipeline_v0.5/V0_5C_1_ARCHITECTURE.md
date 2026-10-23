# v0.5C.1 architecture and prospective qualification

The new `geometry.protected_v2` namespace preserves all original producers and
validators. `engine.py` is an additive version of guarded DP with one extra
proposal gate. It retains the original guards, traversal, source coordinates,
fan budgets, cell-center tests, collision checks, assembly checks and restoration
semantics. `width.py` queries source segments around the proposed change hull,
projects them into native horizontal/vertical frames, and partitions the change
by projected source/chord endpoints and intersections.

Within a slab where the edited chain has a single crossing, source and proposed
boundary positions and each nearest opposing crossing are affine. Evaluate
source and candidate widths on the slab closure, including the points at which
either width crosses the registered 16-cell horizon. Reject any qualifying solid
or bounded-void width loss above the unchanged 1e-10-cell numeric allowance.
An ambiguous affected graph rejects and restores its original subchain. Query
radius includes the displacement ceiling so a newly narrow section cannot be
ignored solely because its source was slightly wider. Missing opposition within
the bounded search denotes a wider/open section, not a fabricated zero width.

The registered horizon comes from C's independent narrow-run measurement domain;
it is not a physical width or a number fitted to the known 9-cell section. No
specific fixture or coordinate appears in the corrected algorithm. No guard is
enlarged and no epsilon or original budget is reduced or relaxed.

A preliminary four-direction prototype produced a complete no-op on the known
fixture because diagonal projections of pixel staircases fold. That development
record is retained. Before any new holdout, the integrated screen was limited
to the two native axes, where the affine opposing-boundary construction is most
useful. Complementary oblique directions remain an independent audit, rather
than being silently treated as an exhaustive theorem.

`independent.py` uses source-only locations distinct from proposal event cuts,
GEOS line-component widths at 22.5/67.5/112.5/157.5 degrees, and direct coordinate
interpolation to confirm any loss. The unchanged C axial/medial/serialization/
area/distance/topology checks also run. Both layers share WKB parsing/GEOS and
linear geometry definitions; no independent-kernel claim is made. Finite
orientations, a width horizon and source-specific geometric assumptions leave
arbitrary-direction/global minimum-neck preservation unqualified.

All 20 previously seen realizations are development/regression evidence. Their
five settings [0,0.20,0.35,0.50,0.75] give 100 regression configurations. Only
six new LHS parameter positions (sampling seed 20261021) and seeds 12031/12032,
generated after final freeze, constitute the 60 independent configurations.
Bounds are copied exactly from the original v0.3 plan; the selection is not
conditioned on morphology or expected passing behavior.

The small-pore question is separate. No A1 regularizer is changed. Both absolute
and relative errors, identities, shape and contact footprints are reported. An
absolute construction-scale diagnostic r²/2 is not adopted as a fidelity
allowance. Cumulative small-pore scientific policy remains UNQUALIFIED pending
physical/measurement justification; no historical relative criterion is erased.

Machine protocol, immutable final freeze, original/revised code snapshots and
results are in `experiments/pipeline_v0.5/scientific_requalification/run_001`.
Scientific status, feature qualification, pore-policy status and production
qualification must be reported separately. Stop before export or CAD.
