# v0.5A.1 scientific and geometric qualification

## Precise decision

**AMENDED_PASS_TESTED_DOMAIN_OPTIONAL_CANDIDATE_WORKFLOW** for the explicitly
selected `solid_separate_contacts` mode on the five registered native 1024
fixtures, with all 287 regression tests passing. This is a new scoped candidate
qualification, not a change to the historical exact v0.5A HOLD. The exact source
with a genuine contact remains `exact_nonmanifold`. Scientific review and
authorization to begin v0.5B remain pending. No v0.5B code is included.

Authoritative study: `experiments/pipeline_v0.5/manifold_qualification/run_001/`.
Settings, selection reasons, hashes, environment and executed source snapshots
were registered before final candidate evaluation. All 2958 pre-existing project
files remain byte-identical. Existing exact converter, generators, evaluator,
historical experiments/manifests and scientific decisions were not edited.

## Separate acceptance states

| Property | Result and scope |
|---|---|
| A: exact geometry fidelity | PASS, all five inputs and their exact baselines |
| B: contact classification | PASS, source/edge/ring/link agreement and synthetic artifacts distinguished |
| C: optional candidate manifold validity | PASS for all five selected-policy outputs, including one no-op |
| D: geometric modification budget | PASS for all five selected-policy outputs |
| E: raster morphology preservation | PASS; every compared descriptor and original-grid pixel unchanged |
| F: physical feature qualification | UNQUALIFIED |
| Mesh, mechanics, manufacturing | UNQUALIFIED; not performed |
| Full v0.5A.1 optional workflow | AMENDED PASS within the registered tested domain |
| Historical exact v0.5A | HOLD unchanged |

## Deterministic real-fixture sample

Selection reused existing controls: ordinary D0/S0; saved repaired D9/S1;
minimum-strut D1/S0; maximum-strut/minimum-pore D2/S0; prior envelope-center
D5/S0. D0 already has the largest saved pore-scale control. Actual OGC hole
counts range from 289 to 466, rather than treating requested pore scale as
measured complexity. No new generator outputs were produced.

| Design / seed | True contacts | Original area | Candidate area | Symmetric difference | Area error % | OGC holes before→after | Candidate status |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 / 0 | 1 pore–pore | 502791 | 502791.0625 | 0.0625 | 0.000012431 | 289→289 | ACCEPT_GEOMETRIC_CANDIDATE |
| 9 / 1 | 0 | 500104 | 500104 | 0 | 0 | 412→412 | ACCEPT_NOOP |
| 1 / 0 | 5 pore–pore, 1 hole–shell | 453505 | 453505.375 | 0.375 | 0.000082689 | 404→404 | ACCEPT_GEOMETRIC_CANDIDATE |
| 2 / 0 | 8 pore–pore | 542961 | 542961.5 | 0.5 | 0.000092088 | 466→466 | ACCEPT_GEOMETRIC_CANDIDATE |
| 5 / 0 | 9 pore–pore | 528285 | 528285.5625 | 0.5625 | 0.000106477 | 321→321 | ACCEPT_GEOMETRIC_CANDIDATE |

There are 24 contacts across this sample: 23 pore–pore and one hole–shell.
No additional real crossings, overlaps, duplicate/zero edges or numerical near
contacts were found. Those defect classes are exercised synthetically. This
finite five-design/fixed-seed sample does not establish universal coverage.

Every modified contact uses the same registered radius r=0.25. All selected
outputs have valid OGC polygons and an independent manifold boundary PASS.
For each of 24 modified neighborhoods:

- Actual added area = 0.0625 cell², comprising two triangular added regions.
- Removed solid area = 0; outside-support boundaries remain set-equal.
- Maximum local displacement and certified construction-family Hausdorff =
  0.1767766953 cell.
- Actual local clearance and minimum new boundary edge = 0.3535533906 cell.
- Minimum affected angle between boundary rays = 135°.
- Solid polygon count stays one; no new isolated solid sliver/component appears.

The OGC hole count is preserved, but **continuous contact topology changes**:
touching void closures separate and a positive-width local solid link replaces
a point-only link. At the hole–shell contact, zero-clearance access to the
exterior is closed continuously; source complementary-8 digital classification
does not change because no sampled pixel changes. Exact geometry is not claimed.

Design 9 receives no operation: area, holes, 47382 vertices, WKB coordinates,
and the original saved 15-pixel generator repair remain unchanged. That repair
is neither rerun nor overwritten. Both primary exact JSON/WKB outputs match
their historical run_003 bytes.

## Morphology and reconstruction

Every policy output with geometry was independently reloaded from WKB and
rasterized at half-integer cell centers. Every real output has XOR=FP=FN=0,
IoU=1, one 4-connected solid component, largest-component fraction 1 and both
percolation directions true. Selected outputs reproduce deterministic WKB bytes
and quantitative metrics on repeat.

Frozen evaluator v1.1 was invoked through `evaluate_native` independently on
original and candidate reconstructions. Solid fraction, component count,
largest-component fraction, Px/Py, mean strut thickness, P10, median pore
diameter, full S2 and full mean/directional lineal-path arrays match exactly.
No descriptor tolerance was relaxed. For the primary fixture:

| Frozen descriptor | Original = candidate |
|---|---:|
| Solid fraction | 0.47949886322021484 |
| Solid components / largest fraction | 1 / 1 |
| Px / Py | 1 / 1 |
| Mean strut thickness | 16.50708211522022 pixels |
| Whole-mask P10 | 10 pixels |
| Median pore diameter | 31.304951684997057 pixels |
| Maximum difference in S2 and all lineal arrays | 0 |

Matching raster descriptors cannot see the new subpixel ligament and do not
prove continuous equivalence. Frozen whole-mask P10 is not replaced. v0.4.3's
amended lower-tail/local-neck qualification remains confined to its tested
domain; the v0.4.2 analytic P10 calibration remains FAILED. Its scoped neck
screen does not qualify this newly constructed 0.353553-cell diagonal feature.

## Strategies and retained failures

Representation-only correction and patch decomposition retain the actual source
singularity. Preserve/quarantine remains the default. Local solid-side addition
is accepted under the registered geometric gates. Local void-side removal also
produces manifold boundaries and identical raster descriptors, but is rejected:

| Fixture | Void-side area change | OGC holes before→after | Rejection |
|---|---:|---:|---|
| D0/S0 | -0.0625 | 289→288 | hole_count_preserved |
| D1/S0 | -0.375 | 404→398 | hole_count_preserved |
| D2/S0 | -0.5 | 466→458 | hole_count_preserved |
| D5/S0 | -0.5625 | 321→312 | hole_count_preserved |

On D9, every explicit policy is a zero-change no-op. Enclosed-pore-only policy
rejects D1 before candidate construction because it also has a hole–shell
contact; the separately registered broader mode handles that class. Rejected
candidate geometry, measurements and logs are retained, not silently substituted.
The full strategy comparison and limits are in CONTACT_POLICY.md.

## Synthetic and software verification

**287 passed, 0 failed**, terminal wall time 32.07 s (JUnit aggregate 31.995 s).
This retains all 249 previous tests and adds 38 tests. Both the original
511-nonempty-3×3 exact enumeration and a new independent source/classifier
enumeration pass. Canonical exact behavior and historical source hashes remain
unchanged. No test expectation was weakened.

The requested 23 categories map to tests in tests/test_manifold_qualification.py:
square/irregular corner-touching pores; generic three-ring/six-ray incidence;
alternating sectors; hole–exterior contact; one/two-pixel pore separations;
diagonal strut; pinched exterior; concave hole; long thin ligament; independent
defects; adjacent clusters; border defect; source-domain ordinary corner plus
general-polygon corner contact; ordinary boundaries; shared internal patch seam;
area-budget rejection; raster-change rejection; too-narrow-ligament rejection;
OGC-valid/non-manifold distinction; representation-only seam correction; and
the impossibility of removing an inherent contact while retaining the exact set.
Additional tests cover crossings/overlaps/duplicates/zero edges, near-contact
separation, deterministic WKB, no-op inputs, unsupported diagonal solid components,
invalid settings, overwrite refusal and frozen original file hashes.

The default synthetic candidate introduces a measured subpixel ligament; it is
accepted only geometrically. Radius 0.125 yields clearance 0.176777 cell and is
correctly rejected by the registered clearance floor. Zero area budget rejects
the nonzero-area candidate. An independently altered occupied cell is rejected
for raster disagreement. No fallback policy is applied to rescue these failures.

## Runtime and allocation observations

Stage times below include tracemalloc instrumentation except exact repeat.
Full qualification includes continuous Boolean comparisons, local distances,
feature checks, a fresh boundary qualifier and independent raster comparison.
Construction is also broken out as a component of that total, not added twice.

| Fixture | Exact repeat s | Contact classification s / MiB | Local construction s | Candidate comparison+qualification s / MiB |
|---|---:|---:|---:|---:|
| D0/S0 | 0.812 | 0.616 / 25.85 | 0.018 | 1.401 / 25.29 |
| D9/S1 | 1.032 | 0.745 / 32.28 | no-op | 1.649 / 30.61 |
| D1/S0 | 1.022 | 0.774 / 31.91 | 0.024 | 1.815 / 30.89 |
| D2/S0 | 0.984 | 0.751 / 31.06 | 0.024 | 1.708 / 30.06 |
| D5/S0 | 0.873 | 0.630 / 26.37 | 0.018 | 1.427 / 25.79 |

Frozen original/candidate evaluation additionally took 1.47–1.61 s per selected
pair, with about 76.3 MiB peak traced allocation. These are per-stage tracked
allocations, not total RSS or total native GEOS memory. Source/classification and
candidate stages are separate from exact extraction. Exact extraction code was
not rewritten and its two primary uninstrumented times remain comparable to
the original observations. Timings are single-run observations, not statistical
benchmark guarantees. Source hashes are unchanged even where timings vary.

Execution: macOS 27.0.1 ARM64, Python 3.10.0, NumPy 2.2.6, SciPy 1.14.1,
scikit-image 0.25.2, Shapely 2.1.2 / GEOS 3.13.1, Matplotlib 3.10.9 and
Pillow 12.3.0. Windows was not executed. Reproduction commands are in the handoff.

## Remaining limits

Exact non-manifold sources remain blocked for operations requiring their
unchanged boundary to be manifold. Unsupported contact classes remain
quarantined. Accepted candidates are eligible only as explicitly identified
inputs to a separately authorized topology/feature-preserving simplification
study. Protect every recorded subpixel contact neighborhood; no universal
tolerance, CAD interoperability, mesh quality, load capacity or manufacturability
has been established. See V0_5A_1_HANDOFF.md. Stop before v0.5B.
