# v0.5A.1 audit, investigation plan and prospective protocol

Audit completed before implementation: reviewed v0.5 ARCHITECTURE.md,
VALIDATION.md, HANDOFF.md, baseline_vectorization/run_003 manifests, geometry
documents/WKB, geometry_validity/comparison/performance reports, verification
CHANGES.md, all geometry modules and tests/test_geometry_exact.py, dependency
specifications, evaluator/native evaluation interfaces, and v0.4.3 amended
acceptance. Recorded a pre-edit inventory of 2958 existing project files.

## Diagnosis to verify independently

At vertex (31,296), canonical cells NW/NE/SW/SE are 0/1/1/0. Four exposed
boundary rays meet at one point. Inspect source 4-solid and 4/8-void labels,
local-link sectors, traced walks, decomposed rings and polygon containment.
Distinguish inherent geometry from tracing errors. Produce native-grid enlarged
figures with ring colors, incidence rays, labels and orientation arrows.

Current exact converter is retained unchanged: boundaries.py extracts/walks
oriented edges; decompose_pinched_loops partitions repeated walks; planar.py
assembles holes and checks OGC validity; conversion.py orchestrates; raster.py
does scanline reconstruction; reporting.py serializes exact JSON and WKB.
The current manifold check catches checkerboards but is tied to extracted
vertices and ring simplicity; add an independent boundary-intersection/local-link
qualifier for arbitrary polygon candidates and representation-artifact tests.

## New architecture, no edits to existing exact modules

Add a separate geometry/manifold package for boundary graph classification,
source-contact provenance, explicit policies, candidate construction, feature
and error budgets, frozen descriptor comparison, reports and figures. Retain
three explicit states: canonical_binary, exact_geometry, manifold_candidate.
Default policy is preserve_exact. Quarantine remains available for every defect.

General diagnostics use vectorized segment STRtree indexing, exact intersection
predicates (zero snapping tolerance), graph rays/local links, repeated-walk/ring
incidence and separately configured positive-distance near contacts. Shared
internal patch seams are evaluated against the assembled set boundary, not
misreported as external defects. Overlaps, duplicate/zero edges, crossings,
multi-ring clusters and unsupported contacts fail closed. Use no per-pixel GEOS
objects and no all-pairs vertex search.

## Strategies and candidate construction to evaluate

A: exact representation correction can remove spurious seams but cannot resolve
a genuine point contact. B: preserve/quarantine always. C: explicit local solid
addition for two enclosed pore rings of the same solid polygon, at a verified
isolated checkerboard vertex. D: local void addition as a diagnostic alternative;
reject if it merges pores or changes required solid topology. E: valid patch
decomposition does not by itself regularize the assembled boundary.

For C, propose the L1 diamond |x-vx|+|y-vy|<=r with r=0.25 raster-cell units.
Only its two void-quadrant triangles add solid. Union once with the exact set,
retaining all untouched boundaries. For disjoint unit-grid contact supports:
added area r²/contact, maximum boundary displacement r/sqrt(2), newly separated
pore clearance sqrt(2)r. Verify these predictions with actual Boolean region
differences and boundary distances, not bounding boxes. This changes continuous
geometry and creates a subpixel ligament; it is not an exact or physical repair.
No candidate is constructed for unsupported contact classes; no silent fallback.

## Prospective screening limits, registered before candidate experiments

- Original-grid XOR/FP/FN all zero; IoU=1; topology and frozen raster descriptors
  unchanged exactly (no relaxed descriptor thresholds).
- Maximum local displacement and certified family-specific Hausdorff <=0.25 cell.
- Symmetric difference <=0.0001 × original solid area (0.01%).
- Valid OGC polygon and independently qualified manifold boundary.
- Preserve solid polygon-component count and OGC hole count. Explicitly report
  changes in boundary-contact topology and digital-8 versus continuous holes.
- Positive local repaired clearance >=0.25 cell. This is a geometric screening
  floor for this study, not a printability or strength threshold.
- No affected new edge shorter than 0.125 cell or affected acute ring angle <45°;
  no unexpected removed material in solid-side mode; changes confined to recorded
  diamonds; no new boundary contact or geometry outside [0,N]².
- Default r=0.25; supported candidate radii are finite 0<r<=0.25, never tuned
  after results. Unsupported radii/settings fail or produce recorded rejection.
- Physical-feature, mesh, mechanical and manufacturing qualification remain
  UNQUALIFIED. A geometric candidate PASS does not qualify its subpixel ligament.

Shapely's Hausdorff implementation is discrete. For this restricted chamfer
family prove the analytic maximum, and also measure discrete Hausdorff with
densification. Do not present the library's value as a universal exact metric.

## Validation sequence and fixture selection

Retain all 249 tests and original 511-mask enumeration. Add the requested 23
contact/repair categories, generic crossed/overlapping/near boundary tests,
patch-assembly artifacts, budget/raster/feature rejection, determinism and no-op
checks. Enumerate small masks for classifier agreement with alternating sectors.

Real sample: retain Design 0/seed 0 and Design 9/seed 1; additionally select
Design 1/seed 0 (minimum registered strut scale), Design 2/seed 0 (maximum strut
scale and minimum pore scale), and Design 5/seed 0 (the registered envelope-center
design used by prior convergence studies). Design 0 already supplies the maximum
saved pore scale. Together these span thin/thick and high/low pore-scale controls.
Record actual pore counts, not assumed complexity.
Selection uses existing controls, never candidate pass/fail. Do not regenerate.

Register settings, selected paths/hashes, code snapshots and environment in a new
experiments/pipeline_v0.5/manifold_qualification run before evaluating candidates.
Record separate exact-fidelity, classification, manifold, budget, raster-morphology
and physical-feature statuses. Preserve failures, old v0.5A HOLD and v0.4.2/v0.4.3
decisions. Measure each stage's time and traced memory, which excludes untracked
GEOS-native allocations. Stop before v0.5B.

Primary API references checked: https://shapely.readthedocs.io/en/2.1.2/strtree.html
and https://shapely.readthedocs.io/en/2.1.2/reference/shapely.hausdorff_distance.html.

### Pre-candidate scope clarification from source audit

Design 1/seed 0 also contains a hole–shell point contact at (850,994). No candidate
has yet been constructed or selected. Evaluate both an enclosed-pore-only mode
and a separately named `solid_separate_contacts` mode that additionally allows
a hole–shell contact of the same polygon. The same verified alternating sectors,
diamond support, area/displacement proof and all budgets apply. Hole–shell mode
must measure separation from the outer boundary and explicitly report removal
of the zero-clearance exterior contact; do not relabel the source void as an
enclosed digital pore. Separate solid polygons, multi-ring links of degree >4,
overlaps, crossings, non-grid vertices and numerical near contacts remain
unsupported for automatic candidate construction. This scope clarification is
based on local geometry, before seeing any candidate acceptance outcome.
