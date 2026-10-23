# v0.5A engineering validation and decision

**Decision: HOLD.** Exact conversion is demonstrated; general manifold/CAD
readiness is not accepted because ordinary Fixture A retains a point contact.
No scientific threshold or source pixel was changed. Authoritative current run:
`experiments/pipeline_v0.5/baseline_vectorization/run_003/`.

## Audited and reused components

Reused saved v0.4.1 native NPY/PNG arrays, adjacent manifests, generator provenance,
v0.3 design controls, v0.4.2/v0.4.3 acceptance records, frozen evaluator v1.1
`basic_metrics`, its existing loader/configuration interface, SciPy topology,
NumPy arrays, Pillow previews, Matplotlib and the repository's pytest framework.
No generator is executed during the geometry demonstration. Existing image
threshold/uint8-coercion loaders are deliberately bypassed by strict NPY input.

## Representation and coordinate contract

Canonical geometry is deterministic integer exposed-cell edges and oriented
closed face walks. Pixel (r,c) occupies [c,c+1]×[r,r+1]; x points right, y down,
centers are half integers and the domain is [0,1024]². Units are raster cells;
the display transform is identity and physical scale is null. Shapely 2.1.2/GEOS
provides derived Polygon/MultiPolygon objects and an independent rasterizer.
This retains exact occupied-cell geometry without cell-by-cell heavyweight unions.

Exposed interfaces include the image perimeter wherever source solid actually
exists. Shells have positive signed area and holes negative area in the chosen
coordinate algebra. Boundary-connected voids remain open shell indentations;
no solid frame is inserted. Complementary 8-connected void counts are geometry
diagnostics; frozen 4-connected void counts remain separately reported.

Degree-four corners receive deterministic right-turn face walks. Exact cycle
decomposition at existing repeated vertices produces simple OGC rings while
retaining original walks and all contact coordinates. No make_valid, buffer,
coordinate perturbation, material addition/removal or topology repair is used.
Point-touching hole rings may be OGC-valid yet non-manifold. For an exterior
corner contact a derived hole can touch its shell; it is explicitly identified
as originating in an exterior walk, not miscounted as an enclosed digital pore.

## Exact high-resolution results

| Quantity | A: Design 0 / seed 0 | B: Design 9 / seed 1 |
|---|---:|---:|
| Original saved repair additions | 0 | 15, retained unchanged |
| Solid area / occupied cells | 502791 | 500104 |
| Void area / cells | 545785 | 548472 |
| Exposed unit edges | 67550 | 81192 |
| Traced boundary loops | 289 | 413 |
| Traced shell / pore loops | 1 / 288 | 1 / 412 |
| Derived simple polygon rings | 290 | 413 |
| Derived polygon holes | 289 | 412 |
| 8-connected exterior void regions | 67 | 86 |
| 8-connected enclosed void regions | 288 | 412 |
| Frozen-convention 4-connected enclosed void regions | 289 | 412 |
| Vertices before / after exact coalescing, closures excluded | 67550 / 38830 | 81192 / 47382 |
| Exact vertex reduction | 42.516654% | 41.642034% |
| Boundary reconstruction XOR / FP / FN | 0 / 0 / 0 | 0 / 0 / 0 |
| Independent polygon reconstruction XOR / FP / FN | 0 / 0 / 0 | 0 / 0 / 0 |
| Both round-trip IoUs | 1 | 1 |
| Geometry area error | 0 | 0 |
| Original / reconstructed 4-solid components | 1 / 1 | 1 / 1 |
| Original / reconstructed horizontal and vertical percolation | true / true | true / true |
| OGC validity | valid | valid |
| Manifold boundary | **FAIL: holes touch at (31,296)** | PASS |
| Case acceptance | HOLD_GEOMETRY | PASS_EXACT_BASELINE |

All rings close, all derived rings are simple, winding is consistent, and every
extracted edge is walked once. There are no duplicate or zero-length exposed
edges. Both produce one polygon with connected geometrical interior. Fixture A's
original pore walk repeats its shared vertex; its two derived holes still meet
there. This limits boundary regularity, not mask reconstruction or area.

Both fixtures pass reconstruction from re-read JSON boundaries and re-read WKB
polygon candidates. Geometry JSON bytes match exactly between repeated runs.
The real input NPY SHA-256 values are:

```text
A 5d5bf7b578c659e8c2c66e6154cb1fbcbddbf015d9b4f276b8d008c739a6097d
B e4b28517f4147a9f5eefd045a023f8f7bf2f99c63e950d995ad9ce5bbe68faf8
```

Full repository-relative source paths, PNG/pixel/manifest hashes, exact controls,
generator versions/source hashes and saved repair provenance are recorded in
each `input_provenance.json`. The final run archives executed source and tests
under `code_snapshot/`; its protocol fingerprints the code and settings.

## Performance and memory, macOS only

| Measurement | A | B |
|---|---:|---:|
| Uninstrumented conversion repeat | 0.810158 s | 0.998360 s |
| Tracemalloc-instrumented conversion | 1.826001 s | 2.288303 s |
| Peak traced allocations | 56.53 MiB | 70.55 MiB |
| Process lifetime peak RSS before case figures | 312.80 MiB | 584.81 MiB |
| Exact boundary JSON size | 404389 bytes | 498751 bytes |
| Derived WKB size | 627089 bytes | 766381 bytes |

Conversion includes strict validation, edge extraction, walks, decomposition,
polygon construction/validity, repeated topology analyses, exact scanline round-trip,
independent GEOS round-trip and comparisons. Loading, writing and figures are
excluded. One uninstrumented repeat per fixture is descriptive, not a benchmark
distribution; concurrent regression execution may affect wall time.
Traced memory excludes untracked GEOS allocations. RSS is process lifetime peak,
including imports and prior-case visualization allocations, not incremental
conversion memory; it is not a per-case memory requirement. The two memory
measures provide bounded practical observations, not a universal memory ceiling.
Boundary maps and coordinate materialization are the principal expected costs.

## Tests, defects and limitations

Final verification: **249 passed, 0 failed**, in 25.57 seconds, with explicit
`EVALUATOR_PATH=validation/evaluators/evaluator_v1_1.py`. This is the original
212-test regression suite plus 37 geometry tests. The exhaustive test covers
all 511 nonempty 3×3 masks, independently comparing each candidate with a union
of analytically defined occupied-cell rectangles. All tested nonempty binary
fixtures admit valid OGC polygonal regions after exact cycle decomposition.
Some still fail the stricter manifold requirement; OGC validity is not CAD readiness.

Tests cover the 24 requested categories, including empty rejection, all-solid,
rectangle, holes, bars, cross, annulus, porous network, 1/2-pixel connections,
single/multiple exterior channels, corner voids, diagonal solid/void contacts,
nested solid islands, staircase, fixed random connected network, invalid values,
dtype/dimension rejection and exact PNG/NPY correspondence. Edge cancellation,
orientation, deterministic serialization, original-source hashes and overwrite
refusal are also checked. A deliberately invalid bow-tie polygon is rejected
by the independent rasterizer. Expected HOLD cases are asserted, not waived.

Initial test collection could not load a SciPy 1.15.3 macOS binary. Reinstalling
the same version did not resolve it; SciPy 1.14.1 imported correctly and was used
for every recorded geometry run. This local environment change is documented;
no evaluator or scientific definition was edited. No Windows run is claimed.

Runs 001 and 002 preserve the initial invalid pore-walk polygon diagnostics.
Run 001 additionally exposed uninformative close-up selection; run 002 corrected
the windows. Run 003 resolves the ring bookkeeping exactly and preserves the
remaining contact blocker. Earlier failed candidates and figures were not deleted
or overwritten. Final figures show originals, overlays, reconstructions,
differences, narrow struts, pores, junctions, exterior edges, the saved repaired
connection and the point contact. Binary data uses no interpolation/antialiasing.
Close-up selections are illustrative inspections, not exhaustive neck screens.

The new implementation does not perform descriptor drift, simplification, CAD
interchange, 3D construction, FEM or manufacturing certification. Those remain
outside v0.5A. The original v0.4.2 P10 calibration remains FAILED and historical
HOLD remains unchanged. v0.4.3 remains AMENDED_PASS_TESTED_DOMAIN with its original
lower-tail and local-neck limitations.

## Preservation and next decision

The run's before/after inventories confirm existing files were preserved.
Session-wide verification additionally compares 2800 pre-existing project files
with the final checkout; all remain byte-identical. The inventory finished after
the newly written architecture proposal existed, before implementation; its
original bytes are separately archived and its later refinement is recorded as
an intentional change to a new session document. See
`verification/session_preservation.json` and the
exact new-file inventory alongside it. No pre-existing source files were edited.
New code lives only in `metamaterial_eval/geometry/`, `tests/test_geometry_exact.py`
and `requirements-v0.5.txt`; new docs and experiments are isolated under v0.5.

v0.5A does not need another pixel-exactness correction on these fixtures. It does
need review of the non-manifold contact representation before an overall PASS
or general simplification can be authorized. Keep the manifold gate unchanged.
See `HANDOFF.md` for the required review and prospective v0.5B work, which has
not been implemented.
