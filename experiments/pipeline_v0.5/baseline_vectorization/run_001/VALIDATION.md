# v0.5A exact baseline validation

Overall decision: **HOLD**.

| Fixture | Status | OGC valid | Manifold | Loops | Vertices before / after | XOR | Area | Repeat seconds | Traced MiB |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| fixture_A_design000_seed000 | HOLD_GEOMETRY | False | False | 289 | 67550 / 38830 | 0 | 502791.0 | 0.469 | 56.53 |
| fixture_B_design009_seed001 | PASS_EXACT_BASELINE | True | True | 413 | 81192 / 47382 | 0 | 500104.0 | 0.913 | 70.55 |

Existing files preserved: True.

Boundary reconstruction and valid polygon reconstruction are reported separately. An invalid polygon is never passed to the independent containment rasterizer.
Point contacts block ordinary manifold boundaries even when a geometry library accepts an OGC object. No repair was applied.
Performance covers conversion, topology, comparison and independent rasterization; excludes file IO and figures. Tracemalloc instrumentation adds overhead. RSS is a process lifetime measure.
Execution: macOS only. Historical v0.4.2 P10 calibration remains FAILED; v0.4.3 qualification remains restricted to its tested domain.
See each input_provenance.json for exact source paths/hashes/parameters and each geometry_validity.json for limitations. No v0.5B–D implementation is included.
