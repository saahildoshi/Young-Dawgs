# Pipeline v0.5B1 — scientific interpretation and sensitivity results

Scientific status: **EXPLORATORY SENSITIVITY STUDY COMPLETE**. Ordinary
topology-preserving Douglas–Peucker simplification reduces complexity substantially,
but does not preserve all monitored subpixel and narrow-feature geometry. No
tested positive-reduction candidate passes every prospectively defined available
diagnostic, even individually. No production tolerance is selected. v0.5B is not
complete; v0.5B2 and later stages have not been implemented.

## Evidence and reproducibility

The authoritative corrected study is
`experiments/pipeline_v0.5/simplification_sensitivity/run_002`. Its
`summary/SIMPLIFICATION_SENSITIVITY.md` contains the full 40-row primary result
tables and first-event sequences. Its JSON summary, individual candidate
`metrics.json` files, WKB, raster arrays and authenticated descriptor artifacts
retain the underlying measurements. CSV tables include PER_TOLERANCE, PER_CONTACT,
NECK_PROBES, MORPHOLOGY_COMPARISONS and PERFORMANCE. Final completion, regression,
historical-preservation and artifact-hash records are under `verification/`.

The first full study, run_001, is retained. It exposed a reporting defect:
undefined repair tracking was aggregated as a false clearance-decrease flag.
The corrected tri-valued aggregation preserves unknown values and never counts
them as recovered passes. The full unchanged sweep was repeated in run_002;
all 43 candidate WKB hashes, continuous area/distance/topology measurements,
rasters and frozen descriptor comparisons reproduced exactly. The correction
changed no epsilon, source, warning threshold or geometric algorithm. There
are **43 unique configurations, 86 saved candidate evaluations over two runs**;
each run also repeats candidate construction to verify deterministic WKB.

## Source provenance and baseline complexity

All sources were loaded from saved accepted artifacts in
`experiments/pipeline_v0.5/manifold_qualification/run_001/<fixture>/`:

- Exact independent reference: `exact_geometry/exact_polygon.wkb`, with its
  original loop document `exact_boundaries.json`.
- Accepted source: `solid_separate_contacts/manifold_candidate.wkb`.
- Repairs and scoped acceptance: `solid_separate_contacts/qualification.json`.
- Input mapping: `input_manifest.json`; canonical masks remain at
  `experiments/pipeline_v0.4.1/resolution_validation/design_NNN/seed_NNN/1024/microstructure.npy`.

The existing v0.5A.1 artifact-hash ledger authenticated the saved source files.
The B1 protocol and baseline documents record full per-file SHA-256 provenance,
generator identity, source controls, coordinate mapping and qualification hash.
No masks or regularizations were regenerated. The original D9 generator's
15-pixel connector was retained as historical source geometry, independently
of the later manifold-repair policy.

| Fixture | Exposed vertices | Exact coalesced | Existing reduction % | Accepted vertices | Shell / hole vertices | Holes | Accepted area (cell²) | Repairs / diagnostic ROIs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| D0/S0 | 67,550 | 38,830 | 42.517 | 38,832 | 4,668 / 34,164 | 289 | 502,791.0625 | 1 / 1 |
| D9/S1 | 81,192 | 47,382 | 41.642 | 47,382 | 5,218 / 42,164 | 412 | 500,104 | 0 / 0 |
| D1/S0 | 82,352 | 47,888 | 41.850 | 47,900 | 4,959 / 42,941 | 404 | 453,505.375 | 6 / 6 |
| D2/S0 | 80,634 | 46,528 | 42.297 | 46,544 | 4,586 / 41,958 | 466 | 542,961.5 | 8 / 8 |
| D5/S0 | 68,820 | 39,524 | 42.569 | 39,542 | 4,786 / 34,756 | 321 | 528,285.5625 | 9 / 9 |

Each baseline is one valid Polygon, with one exterior, the listed holes and
therefore holes+1 rings. All dedicated manifold checks pass; all reconstruct
their original mask exactly, with one solid 4-component, largest-component
fraction 1 and both percolations. There are **zero algorithmically protected
regions** in B1: the 24 repair ROIs are diagnostic only. Every repaired baseline
has relevant local separation 0.3535533905932738 cell. GEOS minimum_clearance is
recorded separately as a robustness diagnostic, never as physical strut width.
Boundary lengths and the complete natural-neck baseline data are in
`fixtures/*/baseline.json`. Existing collinear reduction is not credited to B1.

## Methods and interpretation of measurements

The frozen primary sweep uses Shapely 2.1.2 / GEOS 3.13.1 Douglas–Peucker with
`preserve_topology=True` at ε=[0,0.05,0.10,0.20,0.35,0.50,0.75,1.00]. Every
candidate starts directly from the same immutable accepted baseline; ε=0 is an
unchanged WKB clone. Three D0 negative controls use False at ε=[0.35,0.75,1.00].
No automatic repair, smoothing or post hoc refinement is applied. Method API:
[Shapely simplify](https://shapely.readthedocs.io/en/2.1.2/reference/shapely.simplify.html).

Comparison A measures accepted manifold→candidate continuous changes. Comparison
B measures original exact→candidate cumulative changes, including the historical
subpixel additions. Comparison C separately compares reconstruction with the
canonical mask and accepted-baseline raster. Raster centers are (c+0.5,r+0.5),
x points right, y points down, and all units are native 1024-grid cells.

OGC validity is separate from the v0.5A.1 segment-incidence manifold checker.
Continuous region correspondence uses indexed positive-area intersections to
detect losses, splits and merges for solid components, holes and exterior voids;
it does not rely only on ring counts. Both signed area change and actual
added/removed/symmetric areas are recorded.

Boundary samples spaced at most 0.25 cell use exact nearest-segment distances
in both directions. The largest sampled distance is a lower bound on continuous
Hausdorff distance; adding half the maximum sampling gap to each directed
maximum gives a conservative upper bound by the distance function's Lipschitz
property. This is not an exact continuous maximum or a discrete-vertex-only
Hausdorff call. Exterior and pore-source maxima are retained separately. Local
ROI sampling uses at most 0.0625-cell spacing, measured against full opposing
boundaries to avoid artificial clipping endpoints. Unchanged accepted candidates
may reuse their separately recorded v0.5A.1 construction certificate relative
to the exact source. Direct GEOS Point.distance checks reproduce all **104**
saved nontrivial directional worst-point distances with zero discrepancy.

Repair ROIs have half-width r+0.75=1 cell, fixed before the sweep. They track
original added material, local symmetric area/displacement, incident void
separation, new manifold events and positive-area solid links between fixed
anchors. A warning occurs for a link/qualification failure, at least 10% patch
loss, at least 10% clearance loss, or ROI symmetric change at least 10% of the
original patch area. This is an exploratory warning definition, not acceptance.
Three deterministic separated low-EDT/PCA normal-chord probes per fixture and
two D9 connector-depth columns supplement the repair diagnostics. They are not
an exhaustive neck search or minimum load-bearing width determination.

The frozen evaluator v1.1 is unchanged. Exact raster identity permits descriptor
reuse only under verified raster, evaluator and interface-configuration hashes;
memory reuse also checks array equality. Cache provenance is retained. The
whole-mask P10 definition and v0.4.3 scope are unchanged; the historical v0.4.2
calibration remains FAILED. Exploratory notable drift screens are density
absolute change >0.001, relative mean/P10/pore change >1%, or S2/L NRMSE >0.01.

## Complexity reduction at every primary tolerance

Entries show **candidate vertices (reduction from accepted baseline, %)**.

| ε (cell) | D0/S0 | D9/S1 | D1/S0 | D2/S0 | D5/S0 |
|---:|---:|---:|---:|---:|---:|
| 0 | 38,832 (0) | 47,382 (0) | 47,900 (0) | 46,544 (0) | 39,542 (0) |
| 0.05 | 38,832 (0) | 47,382 (0) | 47,900 (0) | 46,544 (0) | 39,542 (0) |
| 0.10 | 38,832 (0) | 47,382 (0) | 47,900 (0) | 46,544 (0) | 39,542 (0) |
| 0.20 | 38,831 (0.0026) | 47,382 (0) | 47,893 (0.0146) | 46,532 (0.0258) | 39,528 (0.0354) |
| 0.35 | 38,830 (0.0052) | 47,382 (0) | 47,888 (0.0251) | 46,528 (0.0344) | 39,524 (0.0455) |
| 0.50 | 31,190 (19.6796) | 37,774 (20.2777) | 38,472 (19.6827) | 37,280 (19.9037) | 31,566 (20.1710) |
| 0.75 | 15,191 (60.8802) | 18,292 (61.3946) | 18,547 (61.2797) | 18,314 (60.6523) | 15,408 (61.0338) |
| 1.00 | 5,859 (84.9119) | 7,415 (84.3506) | 7,352 (84.6514) | 7,422 (84.0538) | 6,071 (84.6467) |

## Observed first events

These are first tested events with discrete brackets, not exact thresholds.

| Diagnostic | D0/S0 | D9/S1 | D1/S0 | D2/S0 | D5/S0 |
|---|---|---|---|---|---|
| OGC invalidity, collapse or non-manifold boundary | None | None | None | None | None |
| Solid/hole correspondence or exterior-channel change | None | None | None | None | None |
| Material repair-change warning | 0.20, (0.10,0.20] | N/A | 0.20, (0.10,0.20] | 0.20, (0.10,0.20] | 0.20, (0.10,0.20] |
| Relevant repair clearance below baseline | Not observed where defined | N/A | Not observed where defined | 0.75, (0.50,0.75] | Not observed where defined |
| Repair separation untrackable | 1.00, (0.75,1.00] | N/A | 1.00, (0.75,1.00] | 1.00, (0.75,1.00] | 1.00, (0.75,1.00] |
| Any monitored neck narrowing | 0.75 | 0.50 | 1.00 | 0.50 | 0.50 |
| Raster disagreement / any and notable descriptor drift | 0.75 | 0.75 | 0.75 | 0.75 | 0.75 |
| Raster connectivity/percolation change; monitored local link lost | None | None | None | None | None |

No new near-zero GEOS robustness-distance warning was observed. None observed
means only that the tested diagnostic did not detect the event within this
finite study. No fixture-level true→false failure recovery was observed among
available event flags. Unknown values at ε=1 are not passes. Severity and
individual features are non-monotonic: D2 natural_00 narrows at ε=0.50, widens at
0.75 and narrows at 1.00; D9 natural_02 narrows at 0.50 then widens at 0.75.
D0 mean-thickness and S2/L errors become smaller at 1.00 than at 0.75 despite
larger continuous differences and raster XOR. Increasing ε is not a monotonic
fidelity or safety scale.

## Repairs and narrow features

No primary candidate exhibited a new contact singularity, pore merge or severed
monitored solid link. No original repair patch was completely removed. These
facts do not establish unchanged repair geometry. At ε=0.20 all 24 ROIs already
have local symmetric area changes of 0.09375–0.1875 cell², 1.5–3 times an original
0.0625-cell² patch, while the patch itself remains present. D0 at (31,296) keeps
0.353553 separation at 0.20, widens to 0.485071 at 0.35–0.75, and has undefined
separation at 1.00 because a fixed void anchor is no longer in a candidate void
interior. Local shape change is the early warning, not proven severance.

D2 contact_0002 at ε=0.75 retains approximately 90% of its original added solid
and has separation **0.312347523777 cell**, an 11.65% decrease from its accepted
baseline. At ε=1 all 24 contacts have undefined separation under the registered
tracking rule. All global boundaries still pass the manifold checker, all repair
solid links pass and original patch retention returns to 100%; this cannot be
called restored clearance or proof that the original contact has reappeared.
Per-contact undefined reasons and measured displacement remain in metrics files.

Natural chord narrowing begins at 0.50 for D9, D2 and D5. For example, D5
natural_00 decreases from 7.924466 to 7.506289 cells at 0.50 and to 7.312996 at
1.00. D9 natural_00 decreases from 9.418464 to 8.625113 at 0.75. Its historical
connector remains locally connected, but both registered inward depths fall
from 5 to 4 cells at 1.00. D2 natural_01 has an undefined chord at 1.00 because
the contiguous chord reaches the fixed analysis endpoint; its local solid link
still passes. No supported chord is replaced with a generic robustness distance.

## Material changes invisible to raster descriptors

At ε=0.50 every fixture has FP=FN=XOR=0 and IoU=1 against both raster references.
All scalar and curve descriptor comparisons are exactly equal. The continuous
geometries nonetheless change substantially:

| Fixture at ε=0.50 | Added / removed (cell²), A | Signed Δarea | Symmetric area A | A / occupied area % | Cumulative symmetric area B |
|---|---:|---:|---:|---:|---:|
| D0/S0 | 1283.1875 / 1282.75 | +0.4375 | 2565.9375 | 0.510339 | 2566.0 |
| D9/S1 | 1611 / 1611 | 0 | 3222 | 0.644266 | 3222 |
| D1/S0 | 1600.25 / 1598.25 | +2 | 3198.5 | 0.705284 | 3198.875 |
| D2/S0 | 1572.5 / 1570 | +2.5 | 3142.5 | 0.578770 | 3143.0 |
| D5/S0 | 1371.9375 / 1368.75 | +3.1875 | 2740.6875 | 0.518789 | 2741.25 |

Net area cancellation is particularly strong: D9 has zero net change but
3222 cell² of symmetric difference. At ε=1.00 the primary symmetric areas range
from 16,279.506156 to 19,972.285062 cell², or 3.10973–4.40398% of occupied area.
Added and removed regions are retained separately in every candidate; small net
area change cannot establish feature preservation.

The largest primary measured boundary distance is **1.987767469347 cells** for
D1/S0 at ε=1.00; the continuous bound is **[1.987767469347,2.112767469347] cells**.
D0 at ε=0.75 already has measured distance 1.245682197806 cells at source point
(419,790), verified independently by direct GEOS distance. Nominal ε is not a
verified output displacement limit. Pore-source and shell-source directional
maxima, and cumulative distances relative to exact geometry, remain separate.

## Morphological changes after raster disagreement

All primary rasters retain one solid 4-component, largest fraction 1 and both
percolations through ε=1.00. Raster equality ends at 0.75 in every fixture:

| Fixture | XOR at 0.75 / 1.00 | Δsolid fraction at 0.75 | Δmean thickness at 0.75 (cell) | ΔP10 at 0.75 (cell) | S2 / L NRMSE at 0.75 |
|---|---:|---:|---:|---:|---:|
| D0/S0 | 6116 / 12912 | -0.00408745 | -0.206795 | 0 | 0.016325 / 0.016578 |
| D9/S1 | 7679 / 14594 | -0.00509930 | -0.186683 | 0 | 0.020547 / 0.020053 |
| D1/S0 | 7788 / 15717 | -0.00519180 | -0.193744 | 0 | 0.022902 / 0.022257 |
| D2/S0 | 7675 / 15315 | -0.00519276 | -0.206850 | -1.055728 | 0.019401 / 0.019985 |
| D5/S0 | 6489 / 13041 | -0.00428677 | -0.197707 | -0.198039 | 0.016362 / 0.017438 |

Median pore-diameter changes at 0.75 are zero except D9 (+0.071889 cell) and D1
(+0.204603 cell); at 1.00 D0, D9, D1 and D5 change by +0.317825, +0.215112,
+0.409207 and +0.463092 cell, respectively. D2 stays unchanged for this descriptor.
Full values, relative differences and all directional lineal-path comparisons
are in MORPHOLOGY_COMPARISONS.csv and individual records. These descriptor
observations do not retroactively qualify P10 or any historical stage.

The False negative controls lose one D0 hole at 0.75 and 1.00 (289→288), while
remaining OGC valid and manifold. Their vertex counts are 15,187 and 5,856;
the topology-preserving primary counts are 15,191 and 5,859. The extra reduction
is negligible compared with the lost pore. They are diagnostic controls only.

## Interpretation and v0.5B2 recommendation

Ordinary topology-preserving simplification works for the tested coarse topology
invariants, but is inadequate as the complete geometry-fidelity policy. The
earliest constraint is local repair geometry, followed by monitored narrowing;
primary pore topology does not constrain this sweep more strongly than those
features. Global net area and hole count are particularly weak fidelity screens.
The negative controls independently show why pore constraints remain necessary.

ε=0–0.10 are unchanged and provide no reduction. ε=0.20–0.35 yield at most
0.046% reduction while changing repair neighborhoods. ε=0.50 offers an
informative **conditional free-arc starting point** for future protected trials:
19.68–20.28% reduction and exact raster descriptors, but no current all-diagnostic
pass. ε=0.75–1.00 offer 60.65–84.91% reduction with clear continuous, local and
raster changes. There is no demonstrated single global tolerance giving useful
reduction while preserving every available diagnostic on all five fixtures.

The proposed B2 design must freeze complete accepted boundary segments and
solid/void geometry inside feature guards, constrain neighboring chords, carry
local pore identities, and validate widths, manifoldness and independent error
bounds. Protect the repairs, saved connector and an expanded corridor/junction
registry. Simplify eligible free arcs with spatially varying proposals; revert
or return a deterministic no-op on failed or undefined constraints. Do not repair
failed outputs afterward. The concrete architecture and proposed prospective
tests are in `V0_5B2_DESIGN_RECOMMENDATION.md`; none has been implemented.

## Performance, verification and limitations

On the recorded macOS ARM64 environment, final characterization took 9.655 s
and the final 43-candidate sweep took **185.997 s**. Candidate simplification
totaled 1.208 s, full validation 175.790 s, dedicated manifold checks 16.508 s,
rasterization 12.111 s and frozen morphology/cache access 7.961 s. The two global
boundary-comparison stages totaled 75.128 s. Individual simplifications took
0.00114–0.05000 s and validations 1.971–7.476 s. Two retained sweeps totaled
366.533 s and their characterizations 19.071 s; these totals exclude reporting,
test and development time.

Peak candidate-stage Python-traced allocation was **95,673,612 bytes
(91.241 MiB)**; process lifetime peak RSS was **616,185,856 bytes (587.641 MiB)**.
Tracing excludes untracked GEOS-native memory; baseline lazy caches contribute
to stage peaks, and RSS is a process high-water mark, not incremental memory.
Candidates are evaluated sequentially with bounded descriptor caches and indexed
nearest queries; they are not accumulated in memory. The main cost is validation,
not simplification. No historical geometry algorithm was redesigned for speed.

The full regression suite passed **316 tests**, including all 287 existing tests
and 29 new tests, in 32.34 s. The initial 3,226-file inventory is the authority for
historical preservation, including pre-existing local changes relative to Git.
Final hashes are recorded separately; existing files are not reset to Git HEAD.
The unchanged evaluator SHA-256 is
`5f28ed1f77f95fd23a517cd223bbe6c6b5edc7d5508093f36f523b2d4f85cebb`.
Windows reproduction commands are documented but no Windows run is claimed.

Fourteen figures cover all ten requested categories, the negative controls,
monitored necks and independently checked displacement. Figures 08/09 show
fixed-scale contact grids. Figure 14 makes undefined ε=1 repair coverage explicit;
Figure 05 displays only defined clearances and consequently ends at 0.75.
Figure 01 has no failure crosses because no primary manifold failure occurred.
All figures were visually inspected; supplementary Figure 13 was re-rendered
to correct an initial clipped title and display all clipped boundary components.
No frozen metric or candidate changed during figure QA.

Only five registered fixtures and three negative controls were tested. Natural
neck screening is sparse, clipped/ambiguous measurements are explicitly unknown,
and there is no universal morphology-preservation claim. No physical dimensions,
manufacturing criterion, FEM, strength prediction, meshing or export qualification
exists. Raster equality does not imply continuous equality. Historical exact
v0.5A HOLD, scoped v0.5A.1 amended PASS, v0.4.3 qualification and v0.4.2 failure
remain unchanged. Complete and qualify an authorized B2 protected simplifier
before defining and executing v0.5C export work. **Stop at v0.5B1.**
