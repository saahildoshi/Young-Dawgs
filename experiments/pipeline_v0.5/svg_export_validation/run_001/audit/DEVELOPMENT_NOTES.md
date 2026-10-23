# Development findings before the final real-fixture freeze

The first 70 new unit tests passed. Persisted controls then found two issues
that did not require a source-geometry or numerical-policy change:

1. `synthetic_run_001` stopped while recording a NumPy boolean through strict
   JSON. The partial SVG/WKB evidence and full exception are retained there.
   The new diagnostic serializer now converts NumPy scalars to Python scalars
   without replacing nonfinite measurements with zeros or a successful result.
2. `synthetic_run_002` passed 19/20 canonical controls and detected all 31
   deliberate failures. The concentric-island control recovered identical
   vertices, segments, area, boundaries and manifold status, but the historical
   C topology helper produced ambiguous hole matches. Its filled-hole disks
   overlap in a nested arrangement. D1 now matches actual disjoint domain-void
   faces with nested solid islands excluded, while retaining the original C
   result explicitly as a diagnostic. Original C code remains byte-identical.

`synthetic_run_003` passed all 20 canonical controls and detected all 31 known
failures. Each run also retains 100 precision configurations across
17/12/9/6/3 significant digits. Added regression tests check the nested-void
case and strict JSON scalar handling. No fixture was replaced; no real SVG
had been exported. There was no change to exact coordinate recovery, zero
Boolean geometry differences, the arithmetic-only allowance, topology/identity,
repair preservation, raster equality, scientific status propagation, or scope.

The protocol audit draft is preserved separately. The final protocol adds the
exact native-generation manifest/code hashes and states the disjoint-void-face
verification construction. These additions precede final code/protocol freeze
and real SVG export. They do not change existing sources or historical results.
