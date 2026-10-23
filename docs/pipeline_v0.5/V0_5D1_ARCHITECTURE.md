# Research-only SVG export and independent reimport

The additive package `metamaterial_eval.geometry.svg_io` implements v0.5D1.
No earlier geometry, generator, evaluator, qualification, or experiment file is
edited. The executed protocol is under `svg_export_validation/run_001`.

`exporter.py` walks authenticated saved binary64 polygon rings, preserves every
vertex, chooses deterministic cyclic starts/orientations/order, and writes one
unstroked even-odd compound path using explicit absolute M/L/Z. It uses 17
significant digits, unchanged x-right/y-down cell coordinates, and no physical
scale. Shell/hole roles remain in the JSON sidecar. SVG metadata identifies the
source and its scientific HOLD; no auxiliary shape can be mistaken for material.

`importer.py` reads the saved bytes, validates XML/metadata, tokenizes the path
with a separate state machine, checks closed simple disjoint boundaries, and
infers an STRtree-assisted nesting forest. Even-depth rings become shells and
their odd-depth children become holes. It never reads original coordinates or
sidecar ring ownership to reconstruct geometry. Unsupported syntax or ambiguous
boundaries fail; no snapping, buffering, simplification, or repair is performed.

`verification.py` requires exact binary64 vertex/edge multisets, represented-set
equality, zero added/removed/symmetric area and zero boundary line-set difference.
The arithmetic-only area allowance is 64×binary64 epsilon×domain area; it cannot
excuse a changed coordinate or region. Existing manifold and raster checkers are
reused. Actual void-face correspondence supplements the historical hole-disk
helper so nested solid islands are represented correctly. Repairs, guard sets,
registered normal chords, clearances and pore relationships remain checked.

`controls.py`, `diagnostics.py`, and `study.py` supply analytic positive/negative
controls, separately retained precision experiments, fixed real-fixture
selection, provenance, code/protocol freeze, execution and memory observations.
The independent parser shares Python floats and Shapely/GEOS with the exporter
and verifier; this is not independent-kernel certification. A separate
Sharp/libvips SVG rendering supplies human previews only. Scientific rasters
use native cell centers, without display antialiasing.

Research-only SVG round-trip qualification is separate from cumulative small-pore
fidelity, production simplification, CAD-kernel interoperability, physical scale,
3D, FEM and manufacturing. All earlier HOLD/UNQUALIFIED statuses propagate.
No DXF or subsequent stage is implemented.

Format references: [SVG path data](https://www.w3.org/TR/SVG2/paths.html),
[even-odd filling](https://www.w3.org/TR/SVG2/painting.html#FillRuleProperty),
and [Python binary floating point](https://docs.python.org/3/tutorial/floatingpoint.html).
