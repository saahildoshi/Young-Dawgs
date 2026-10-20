# v0.4.1 investigation index

**Implementation complete; scientific acceptance HOLD. No CAD/vectorization.**

Start with [the technical reference and Windows commands](../../docs/PIPELINE_V0_4_1_STABILIZATION.md).

| Evidence | Location | Result |
|---|---|---|
| Original nine-pair successive changes, 24 analytic masks, three 2048 diagnostics | [DIAGNOSTICS.md](diagnostics/DIAGNOSTICS.md) | Dimensional increments generally decrease; estimator quantization demonstrated |
| Fixed-high-grid-geometry control | [FIXED_GEOMETRY.md](fixed_geometry_control/FIXED_GEOMETRY.md) | Sampling alone reproduces the dominant native mean-thickness trend in the three selected cases |
| Corner/component overlay | [topology_overlay.png](diagnostics/topology_overlay.png) | One-row coarse-grid bridge disappears at 512/1024 |
| Coarse neck graph sensitivity | [coarse_neck_diagnostic.json](coarse_neck_diagnostic.json) | Removing one neck pixel disconnects the diagnostic copy; original mask unchanged |
| Explicit normalized-capsule repair, full 30-case rerun | [VALIDATION.md](resolution_validation/VALIDATION.md) | 30/30 topology, 10/10 baseline regression, 28/28 previously accepted outputs unchanged |
| Prospective post-diagnostic gates | [protocol_amendment.json](resolution_validation/protocol_amendment.json) | 512→1024 limits: mean 3%, P10 10%, pore median 3%; original errors retained |
| Machine-readable acceptance and individual results | [summary.json](resolution_validation/summary.json) | HOLD: mean 5/10, P10 7/10, pore 10/10 |
| Software verification and unchanged-history checks | [verification.json](verification/verification.json) | 177 tests pass; frozen v1.1 and historical inventories unchanged |

Repair added 4 pixels at 512 and 15 at 1024 for Design 9/seed 1 only.
No solid pixels were removed, and no density retuning was needed.

The verification command explicitly selects evaluator v1.1. An initial local
test invocation used the harness default (v1.0) and an uninstalled temporary
environment, yielding 23 configuration-related failures. Installing the package
in that isolated environment and selecting the specified frozen v1.1 evaluator
produced 177 passing tests; no evaluator edits were made to resolve them.

These runs used macOS/Python 3.10. Windows commands are documented, but Windows
execution has not been performed here. Per-job manifests retain scientific
package versions and SHA-256 identifiers. See the guide for limitations of
traced memory, finite-raster controls, stochastic-cohort comparisons, and the
remaining acceptance decision.
