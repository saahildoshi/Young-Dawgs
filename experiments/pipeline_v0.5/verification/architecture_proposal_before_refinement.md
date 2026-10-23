# Pipeline v0.5A architecture and repository audit

Scope registered before implementation: exact cell geometry only. No v0.5B–D,
generator execution, repair, simplification, CAD interchange, physical scale or FEM.

## Audited evidence

Read `README.md`, `docs/PROJECT_REFERENCE.md`, `docs/PIPELINE_V0_3_EXPLORATION.md`,
`docs/PIPELINE_V0_4_RESOLUTION.md`, `docs/PIPELINE_V0_4_1_STABILIZATION.md`,
`docs/PIPELINE_V0_4_2_THICKNESS.md`, `docs/PIPELINE_V0_4_3_P10_QUALIFICATION.md`,
`experiments/pipeline_v0.4.2/thickness_verification/SCIENTIFIC_ACCEPTANCE.md` and
`experiments/pipeline_v0.4.3/p10_qualification/AMENDED_ACCEPTANCE.md`.
Inspected design_plan.json, native manifests, generator/native worker code, frozen
evaluator interfaces, tests, pyproject.toml and requirements.txt.

1. **Canonical source:** saved `microstructure.npy` under
   `experiments/pipeline_v0.4.1/resolution_validation/design_NNN/seed_NNN/1024/`.
   These exact arrays also underpin the later qualification; do not regenerate.
   Verify file SHA-256 against the adjacent manifest, plus raw pixel hash and PNG.
2. **Invocation:** v0.3 exposes `generate_microstructure(seed,
   solid_fraction_target, strut_scale, pore_scale)`; the native and stabilized
   wrappers add `resolution=1024`. Existing CLI selects `--generator-version 0.4.1`.
   v0.5A does not invoke them. Existing Latin-hypercube controls retain their
   original baseline-pixel semantics and recorded common-seed pairing.
3. **Topology:** frozen `basic_metrics` uses 4-connected solid labels and
   finite-domain percolation. Frozen `local_dimensions` also uses 4-connected void
   pores. Geometry diagnostics separately use complementary 8-connected voids;
   report both counts and never substitute the latter for frozen morphology.
4. **Exact region:** integer-coordinate oriented exposed pixel-cell edges,
   followed by deterministic face walks and exact collinear coalescing. Solid lies
   on the right when displayed with y down. Top/right/bottom/left edges point
   east/south/west/north. Signed shoelace area is positive for shells, negative
   for holes. This is not marching squares.
5. **Exterior void:** boundary-connected voids carve shell boundaries. No frame
   or artificial closure is inserted. Report their 8-connected labels separately.
6. **Pores:** negative loops become holes in the smallest containing positive
   shell, using an STRtree and full-region containment. Nested solid islands
   remain separate polygon members. Signed loops remain authoritative even if
   polygon construction is blocked.
7. **Corner ambiguity:** degree-four checkerboard vertices receive deterministic
   right-turn pairing (4-connected solid face walks). Preserve the shared vertex,
   all edges and all loops; never perturb coordinates. Record non-manifold
   point contacts, repeated ring vertices, GEOS validity and boundary simplicity
   separately. An OGC-valid point-touching MultiPolygon can still be blocked for
   ordinary CAD boundaries. No make_valid/buffer repair.
8. **Library:** isolated `requirements-v0.5.txt` pins Shapely 2.1.2 (Python 3.10
   compatible); existing environment lacked Shapely. Use GEOS for polygon
   construction/validity and independent cell-center inclusion. Existing SciPy,
   NumPy, Pillow and Matplotlib suffice otherwise. No CAD toolchain.
9. **Rasterization:** scanline parity from serialized integer loops at
   y=row+0.5, classify x=column+0.5. No center lies on an integer cell edge.
   Independently compare valid Shapely geometry using contains_xy, in row chunks.
   Invalid polygons use only the exact boundary reconstruction, explicitly
   labeled as such; do not claim a valid-polygon round-trip for them.
10. **Cost:** O(N²+E) extraction/tracing plus edge ordering, ring construction,
    spatial-index containment and scanline crossing sorts. Python edge maps and
    coordinate serialization are likely memory/time hotspots; avoid per-cell
    polygons, global unions, all-pairs containment and recursive tracing.
11. **Preservation:** only new package, tests, dependency file and docs; new run
    directories refuse overwrite. Snapshot existing repository file hashes before
    work and compare afterward. Preserve the dirty working tree and historical
    failures. Run full regression with explicit evaluator v1.1.
12. **Acceptance:** distinguish exact boundary reconstruction, GEOS validity,
    strict manifold boundary suitability, intended connected-network topology and
    scientific acceptance. Require zero XOR/FP/FN, IoU=1, exact occupied area,
    unchanged topology, deterministic serialization and measured 1024 cost.
    v0.4.3 qualification remains scoped; historical v0.4.2 P10 failure stays failed.

## Coordinates and interfaces

Cell (r,c) occupies [c,c+1] × [r,r+1], center (c+0.5,r+0.5), domain
[0,N]², x right and y down. Units are raster cells; physical scale is unknown.
Display transform is identity and invertible. A future y-up transform would be
(x,N-y), but is not applied. This cell convention differs deliberately from the
generator's endpoint sampling coordinates; no generator coordinates are changed.

Separate modules: strict binary/provenance input; frozen-solid and complementary
void topology; edge extraction/loop walks; polygon construction/diagnostics;
rasterization/comparison; conversion orchestration; reporting/figures/CLI.
Canonical baseline serialization stores schema, coordinate metadata and exact
integer closed loops. WKB is a validity-annotated derived polygon diagnostic,
not a v0.5D interchange claim.

## Initial fixtures and prospective failure policy

Fixture A: Design 0, seed 0, native 1024, representative controls and zero repair.
Fixture B: Design 9, seed 1, native 1024, saved top-boundary 15-pixel repair.
Audit of all ten saved masks found checkerboard counts 1,3,6,5,8,2,9,6,7,0
in design/seed order. Thus A already has one point-contact risk; preserve it and
report it rather than searching for a convenient unrepresentative replacement.
B has zero checkerboards; inspect its saved repair region at rows 0–12,
columns 0–12. No new dataset is generated.

Synthetic suite covers the 24 requested cases plus edge-set oracle, exhaustive
small-mask checks, nested islands, orientation, deterministic serialization,
independent GEOS reconstruction and overwrite protection. Pathological cases
must reconstruct from boundaries but be explicitly blocked where necessary.
Any unresolved representative polygon/manifold requirement keeps v0.5A on HOLD.

## Library references

Primary API documentation checked during audit:
https://shapely.readthedocs.io/en/stable/reference/shapely.Polygon.html and
https://shapely.readthedocs.io/en/stable/reference/shapely.contains_xy.html.
Pinned runtime APIs will also be exercised by tests.
