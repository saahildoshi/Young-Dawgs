# v0.5D1 implementation plan, recorded before export implementation

1. **Authoritative saved formats.** Native masks are NPY uint8 arrays. Saved
   continuous geometries are binary64 WKB, accompanied by exact boundary JSON,
   C/C.1 coordinate JSON, source manifests, and qualification records. WKB input
   bytes and their recorded hashes identify the geometry being exported.
2. **State selection.** G1 is the exact cell union; G2 is the separately saved
   `solid_separate_contacts` candidate; G3 is a separately saved corrected
   `guarded_dp_v2.0_impact_width` candidate. The protocol registers four distinct
   saved fixtures, not freshly generated sources or newly simplified candidates.
3. **Exportable scope.** The selected G1 baseline is already manifold. Selected
   G2/G3 candidates are valid and manifold under their saved screens. Unsupported
   invalid/non-manifold input is rejected, never repaired. Historical exact
   sources with contacts remain unchanged and retain their earlier qualification.
4. **Shells and pores.** Existing Shapely Polygon/MultiPolygon objects have
   explicit exterior/interior rings. The exporter records their roles in its
   sidecar, but the importer reconstructs nesting from SVG subpaths alone.
5. **Coordinates.** Pixel (r,c) occupies [c,c+1]×[r,r+1]. Domain/viewBox is
   0 0 1024 1024; x right, y down. Width/height are unitless display dimensions;
   physical scale is null. No padding, affine transform, axis reversal, or units
   conversion is applied.
6. **Precision.** Saved coordinates use IEEE754 binary64. Canonical output uses
   17 significant digits and requires exact recovery of vertices and segments.
   Tests include non-dyadic, near-boundary, very short, and subpixel coordinates.
   Low-precision variants are distinct diagnostic files, never substitutes.
7. **SVG representation.** One filled, unstroked compound path with explicit
   absolute M/L/Z commands and fill-rule=evenodd represents all material. Ring
   nesting parity preserves pores and nested solid islands independently of
   ring winding. There are no auxiliary physical shapes or transforms. All
   source vertices, including collinear vertices, remain represented.
8. **Independent parsing.** No SVG parser library is installed in the research
   environment. A separate reader module will use Python XML parsing and its
   own path tokenizer/state machine, then STRtree-assisted containment/parity
   assembly. It must read saved SVG bytes, reject unsupported constructs, and
   never obtain coordinate arrays or ring ownership from the exporter/sidecar.
   Both modules share Python binary64 and final Shapely/GEOS operations. This is
   parsing/assembly independence, not independent geometry-kernel verification.
9. **Continuous verification.** Require exact coordinate/edge multiplicities,
   geometric equals, zero added/removed/symmetric area and zero boundary line-set
   difference. A small preregistered arithmetic-only area allowance handles
   reordered GEOS summation; it cannot forgive any changed coordinate or region.
   Zero boundary line-set difference supplies a zero displacement certificate;
   changed negative controls also get independently sampled distance bounds.
10. **Subpixel features.** Reuse saved contacts and repair footprints. Compare
    local material, boundary sets, exact segment coordinates, positive chamfer
    clearance, and pore relationships before/after import. Preserve existing
    small-pore modifications rather than reinterpreting their adequacy.
11. **Provenance/status.** Hash sources, masks, source manifests, qualification,
    code, protocol, SVG, sidecars and imported WKB. Propagate scientific
    HOLD_SMALL_PORE_POLICY, cumulative-pore UNQUALIFIED, production HOLD, and
    CAD/FEM/manufacturing UNQUALIFIED separately from export-stage results.
12. **Reused checks.** Use existing independent raster predicates, raster metrics,
    topology/pore correspondence, area difference, boundary incidence and
    dedicated manifold checks, frozen evaluator worker and descriptor comparison.
    At least one fresh original/imported evaluator pair will be executed; other
    equality claims require authenticated descriptors and identical arrays.
13. **Limits.** SVG success establishes this restricted file round-trip only.
    There is no registered physical scale, CAD-kernel consumer/tolerance, 3D,
    mesh, material/load/strength, manufacturing or cumulative pore qualification.

Protocol and fixture selection are saved in protocol/PROTOCOL.json before code.
After synthetic tests, a final code/protocol hash freeze must precede real SVG
exports. Retain failed controls and real cases without replacement or fallback.
Historical file inventory and the C.1 ledger were authenticated before this plan.

Actual SVG previews will use the bundled Sharp/libvips SVG renderer on the saved
files, separately from binary point-center scientific rasterization. Preview
antialiasing is display evidence only. No new dependency, CAD toolchain, source
geometry modification, DXF, 3D or later-stage implementation is required.
