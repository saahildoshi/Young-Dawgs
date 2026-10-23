# v0.5B2 validation and scientific handoff

Implementation and the prescribed development/independent study are complete.
**GEOMETRIC_SCREEN_PASS_TESTED_DOMAIN** applies to the explicitly qualified
outputs under the prospectively recorded B2 policy. Broader scientific/physical
sufficiency of the numerical limits and generality outside this tested family
remain **HOLD / UNQUALIFIED**. No production tolerance or automatic selection
policy is established. v0.5 is not complete. No v0.5C or later implementation
was performed.

Authoritative results:
`experiments/pipeline_v0.5/protected_simplification/run_002`.
Its `summary/ACCEPTANCE.md` has all 50 configuration rows, its JSON retains the
accepted-path lists and machine conclusions, and each case has source/output
hashes, raw/final WKB, qualification, NPY, complete guards, original/proposed/
restored chains, per-pore boundaries and per-feature diagnostics. The final
software/preservation authority is `verification/COMPLETION.json`.

## Prospective experiment and independence

The protocol and limits were recorded before real B2 outcomes. Five B1 fixtures
were the development set. All five other registered native-1024 v0.4.1 design/
seed combinations were reserved by path membership, before inspecting their
geometry outcomes: D0/S1, D1/S1, D2/S1, D5/S1 and D9/S0. These test additional
seeds at the same parameter locations, not unseen parameters or another family.
No holdout was selected for passing or visual simplicity.

The unchanged A/A1 routines prepared missing holdout vector artifacts additively
from authenticated saved masks after the final implementation freeze. No mask
or generator was rerun. All five ingress qualifications passed; no holdout was
excluded or substituted. Their baseline vertex counts are 39,254, 47,326,
47,940, 38,174 and 46,362 respectively. They contain 3,5,2,6,7 registered repairs,
in addition to the 24 development repairs: **47 repairs across ten sources**.
Historical A1 acceptance remains unchanged; these are new B2 ingress records.

There are **25 development and 25 holdout configurations**, at independent
ε=[0,0.20,0.35,0.50,0.75] native cells from each accepted baseline. All 50 final
records completed without internal errors, unsupported ingress or global
rollback: **20 ACCEPTED_CANDIDATE and 30 ACCEPTED_NOOP**. No final rejected raw
assembly needed a baseline fallback; local proposal failures were retained.

Run_001 separately retains the first 25 development evaluations. A finite-input
NumPy matrix-vector operation emitted warnings in the raster-support check;
all 3,710 checked D0 stress-proposal products were finite and exactly matched
explicit two-component products. The final implementation uses component
arithmetic and treats RuntimeWarning as an error. All 25 development geometries,
metrics and decisions reproduced exactly before the final holdout freeze.
There are **75 retained B2 evaluations over the two runs**, including the 25
repeated development cases, and 50 unique configurations. This correction did
not change guards or numerical limits and consumed no holdouts.

An earlier synthetic U-shaped exterior channel demonstrated a missing opposing-
side risk condition; that correction preceded every real B2 outcome. Initial
native-interface test masks were also padded to the existing supported 256 grid.
No evaluator definition or old test was changed. Synthetic correction evidence,
new code snapshots and both final freeze records remain available.

## What the algorithm protects

Ordinary global DP is replaced by stable original-coordinate chains separated
at full protected segments and endpoints. The risk registry covers saved repair
diamonds, complete relevant local boundaries, the known top connector, 24
supported natural chords per fixture, every skeleton support with EDT diameter
<=8 cells, skeleton junctions and close nonadjacent boundary pairs. Same-ring
opposing sides supplement the index-distance screen for short exterior openings.
No single repair-center vertex is treated as sufficient protection.

Repair half-width is r+0.75+ε; other guards use local radii/support geometry and
requested-tolerance influence. All intersecting source segments are retained
whole. Proposed chords and their possible change support must avoid guards and
unrelated boundaries, respect clearance and conservative signed material/pore
budgets, and avoid changing original cell-center occupancy. Rejected leaves
restore their original source chains once, without trying undocumented smaller
tolerances. New-chord assembly conflicts have a one-batch rollback; global
failure has a separately qualified original-baseline fallback. Neither assembly
rollback nor whole-candidate fallback was required by the real final sample. No automatic geometry repair
is present.

The final sources register 27,495 guard objects: 14,300 dense skeleton/junction
components, 12,907 boundary-proximity pairs, 240 supported normal probes, 47
repairs and one saved top connector. These overlap and must not be interpreted
as 27,495 distinct physical struts. Every one of **137,475 guard evaluations**
across five tolerances preserved exact local solid/boundary sets and original
protected segment coordinates. `guard_constraints.json` adds source segment
coordinates, guard dimensions, adjacent eligible chains, actual chord versus
change-support interactions, rejected proposals and final integrity outcomes.

## Quantitative limits and observed fidelity

The frozen geometric screens require <=0.25% of occupied area added, <=0.25%
removed, <=0.5% symmetric redistribution, <=0.5% area distortion in each matched
pore, and a continuous displacement upper bound <=sqrt(2)/2 native cell. This
ceiling is the native cell's center-to-corner distance, independent of requested
ε. Required repairs, supported widths/depths and local links permit no loss.
Guard geometry, raster occupancy and frozen descriptors must be identical.
Ambiguous/undefined required measurements reject. The protocol explains the
screening rationale and explicitly does not establish mechanical sufficiency.

| Property | Observed final result |
|---|---|
| OGC validity, dedicated manifoldness, ring ownership/orientation | PASS, all 50 |
| Continuous solid/hole/void correspondence and exterior channels | PASS, all 50 |
| Hole merge/split/loss/birth | None detected |
| Registered repair material and clearances | All original patches retained; all 47 clearances exactly 0.3535533905932738 cell at every setting |
| Supported natural normal chords | 240 probes, 1,200 evaluations; zero measured width change and no lost local link |
| Saved D9/S1 connector | Both registered depths remain 5 cells; local link retained |
| Guard local geometry/displacement | Exact set/coordinate preservation; measured local displacement and symmetric area zero |
| Per-pore area distortion | Zero for every matched pore in this sample; boundary shape can still change |
| Raster reconstruction | FP=FN=XOR=0, IoU=1 in every case against source and accepted-baseline rasters |
| Raster topology | One solid 4-component, largest fraction 1, both percolations throughout |
| Frozen v1.1 scalar and full S2/mean/directional L arrays | Exactly identical, authenticated cache provenance retained |
| Same-environment construction and serialization | Repeated WKB identical; persisted WKB reconstructed the recorded NPY |

All original source geometry remains immutable. Geometric error A (accepted
manifold→B2) and cumulative error B (exact→B2) are stored separately. At ε=0.50,
added and removed A areas each range **532.5–603.25 cell²**, giving symmetric
areas **1065–1206.5 cell²**, despite zero net occupied-area change and zero raster
error. At ε=0.75 they each range **343.5–411.702381 cell²**, with symmetric areas
**687–823.404762 cell²**. Across all settings the largest A symmetric fraction
is **0.244209%**, below the prospective 0.5% cap. Net area cancellation and raster
identity do not establish continuous equivalence.

The largest cumulative B symmetric area is **1206.5625 cell²** for D0/S0 at
ε=0.50, including its historical 0.0625-cell² repair. No-op outputs have zero
new simplification error but may retain that earlier exact→manifold difference.
Those historical changes are not charged or credited as B2 complexity reduction.

The maximum independently sampled A boundary distance and evaluated matched-
chain bound are **0.685364699005 cell**, for D0/S0 at ε=0.75. The analytic bound
uses endpoint-matched source subchains and replacement chords; coverage and
original coordinates are independently checked. It is evaluated in floating
arithmetic, with the prospectively fixed **1e-10-cell comparison allowance**;
it is not an exact rational or interval certificate. Tiny rounding differences
between the sampled lower and computed bound remain within that allowance.
`BOUNDS_WITH_NUMERIC_ALLOWANCE.json` explicitly adds the allowance to nonzero
bounds. Independent direct GEOS checks matched all **80** saved nontrivial
directional worst-point distances exactly. Original exact→candidate distances
are separately retained, including unchanged-source construction certificates.

## Useful reduction and guarded no-ops

| Set | Fixture | Baseline vertices | ε=0.50 vertices / reduction % | ε=0.75 vertices / reduction % |
|---|---|---:|---:|---:|
| Development | D0/S0 | 38,832 | 35,068 / 9.6930 | 36,106 / 7.0200 |
| Development | D9/S1 | 47,382 | 43,704 / 7.7624 | 44,664 / 5.7364 |
| Development | D1/S0 | 47,900 | 44,370 / 7.3695 | 45,442 / 5.1315 |
| Development | D2/S0 | 46,544 | 43,100 / 7.3994 | 44,036 / 5.3884 |
| Development | D5/S0 | 39,542 | 35,942 / 9.1042 | 36,808 / 6.9142 |
| Holdout | D0/S1 | 39,254 | 35,480 / 9.6143 | 36,536 / 6.9241 |
| Holdout | D1/S1 | 47,326 | 43,762 / 7.5307 | 44,758 / 5.4262 |
| Holdout | D2/S1 | 47,940 | 44,384 / 7.4176 | 45,360 / 5.3817 |
| Holdout | D5/S1 | 38,174 | 34,526 / 9.5562 | 35,438 / 7.1672 |
| Holdout | D9/S0 | 46,362 | 42,918 / 7.4285 | 43,926 / 5.2543 |

All structures remain unchanged at ε=0,0.20,0.35. B1's small low-tolerance
reductions were associated with repaired neighborhoods, now protected exactly.
The ε=0.50 setting gives **7.3695–9.6930%** development and **7.4176–9.6143%**
holdout reduction under the fixed screens. The corresponding ε=0.75 ranges
are **5.1315–7.0200%** and **5.2543–7.1672%**. These are observed settings, not a
selected production tolerance or proof of optimal reduction.

Reduction is non-monotonic in all ten fixtures: increasing ε from 0.50 to 0.75
grows guards and creates larger leaf proposals that more often fail conservative
checks. The bounded local rollback policy preserves the whole rejected leaf
rather than silently retrying it at ε=0.50. Smaller final errors and fewer
removed vertices at the stress setting therefore have a recorded explanation.
Exact earlier collinear-coalescing reductions are not counted again.

## Rejections and fallback accounting

Across the final 50 configurations, **64,703 checked local proposals** include
**36,852 rejected/restored leaves**. Constraint flags overlap:

| Rejection reason | Flag instances |
|---|---:|
| Conservative per-pore fan area budget | 25,799 |
| Cell center in signed fan-change support | 17,864 |
| Cell center on proposed replacement boundary | 3,784 |
| Independent displacement budget | 2,350 |
| Conservative global fan material budget | 596 |
| Chord or possible change support enters a guard | 6 |

These are prevented/unsupported proposals, not evidence that the accepted
geometry suffered those failures. Fan-triangle allocations deliberately bound
redistribution conservatively even when actual areas cancel. They can reject
edits that a more expensive exact local comparison might permit; do not call
each budget rejection proven physical damage. This conservatism is a documented
efficiency/reduction limitation, not a reason to relax limits post hoc.

There are **73,596 unchanged eligible-chain instances** and **87,599 protected-
chain instances** across repeated settings, plus 13,694 simplified eligible-chain
instances. They are not unique physical regions. Whole-geometry no-ops total 30;
global fallback/assembly rollback in the final real set totals zero. Synthetic
tests separately exercise global rejection, restored no-op qualification,
crossing guards, hole collisions/merges, severed links, non-manifold contacts,
width/area failures, ambiguous tracking and determinism.

## Performance and software verification

Final development took **290.752 s**, holdouts **298.432 s**, total **589.184 s**
including preparation, deterministic repeated construction, qualification and
recording. The two first-construction engine sums are 41.447 and 41.140 s;
guard construction totals 10.480 and 10.323 s; full raw qualification totals
151.506 and 148.768 s. Detailed tables retain detection, partition, traversal,
chord-checking, assembly, raster and morphology times. The earlier retained
development run is additional work, not included in this final-study total.

Peak candidate-stage traced allocation was **91,009,202 bytes (86.793 MiB)**
in development and **88,399,387 bytes (84.304 MiB)** in holdouts. Process peak RSS
was **778,616,832 bytes (742.547 MiB)** and **770,867,200 bytes (735.156 MiB)**.
Tracing does not include already-allocated source/context data or all GEOS-native
memory. RSS is process lifetime high-water. These are instrumented single-run
observations, not statistical timing guarantees. Spatial indexing, bounded
descriptor caches, NumPy local center tests and sequential candidate evaluation
avoid all-pairs comparisons and whole-study geometry accumulation.

**363 tests passed, 0 failed**, in 33.42 s: all 316 previous tests plus 47 new B2
tests. No existing tests or interfaces were weakened. Execution used macOS ARM64,
Python 3.10.0, NumPy 2.2.6, SciPy 1.14.1, scikit-image 0.25.2, Shapely 2.1.2 /
GEOS 3.13.1 and Matplotlib 3.10.9. Windows commands are documented, not executed.
The final original-file inventory check covers **3,719 pre-existing files**,
including historical B1 evidence and pre-existing local Git changes; its verified
outcome is recorded in verification/PRESERVATION.json. No dependency was changed.

Fourteen inspected figures cover full exact/manifold/B2 views, complete repair
guards/diamonds, natural chord closeups, protected/eligible segments, reductions,
continuous material and boundary errors, frozen morphology, dispositions,
actual rejection examples and runtime. The extra guard/cell-center example was
selected after the study for explanation only; its native closeup was adjusted
to display the small rejected change rather than an entire long corridor guard.
Frozen metric code, limits, candidates and acceptance results were not edited.

## Eligibility, unresolved issues and stop boundary

The 20 accepted changed WKBs and 30 explicitly accepted no-op WKBs, paired with
their qualification/provenance, are eligible as **inputs to a separately
authorized formal v0.5C investigation under this scoped geometric screen**.
They are not export-certified or automatically selected as production geometry.
The manifest lists those paths explicitly; `raw_candidate.wkb` alone is never
an acceptance contract. Any future formal round-trip procedure must register
its own scientific criteria and distinguish exact, accepted manifold and B2
geometry states.

Independent new-seed results support operation in this limited native morphology
family. No unseen-parameter, universal bottleneck, cross-platform, physical
dimension, material, meshing, strength, manufacturing or FEM qualification exists.
The subpixel repaired ligament remains physically unqualified even when it is
preserved exactly. Budget sufficiency and feature-risk thresholds are prospective
policy choices needing broader scientific review; a general production policy
has not been established. Finer exact local budgeting or a different fallback
policy would be a new algorithm version needing a fresh independent set, because
these holdouts are now consumed.

Historical v0.5A HOLD, scoped v0.5A.1 amended PASS, v0.4.3 qualifications,
v0.4.2 failed calibration and all B1 results remain unchanged. The B2
implementation/validation milestone is complete within the stated scope;
broader scientific sufficiency remains HOLD/UNQUALIFIED. **Stop before v0.5C.**
