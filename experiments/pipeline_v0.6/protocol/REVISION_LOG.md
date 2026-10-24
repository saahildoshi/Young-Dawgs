# Prospective protocol and execution record

Revision1 PROTOCOL.json was written before any microstructure meshing or input
preparation. Each mesh run records its SHA256 and a byte-identical copy.

- run_001: source and coarse mesh retained; interrupted the expensive global
  boundary Hausdorff calculation. No threshold or physics changes.
- run_002: indexed boundary checking; coarse mesh gates pass but sampled feature
  screen fails. Medium mesh retained; interrupted full coverage-union scaling.
- run_003: coverage validity and complete-edge inventory retained; reconstruct
  domain from all boundary edges and independently compare area, holes and source
  segment coverage. Geometry, mesher configuration, material and gates unchanged.
  Coarse run_001/run_003 content hashes match exactly. All three levels finished.
- Final level2 fails minimum angle (8.27513422° <10°). Preserve the failure and
  stop. No final microstructure APDL input or solve, no threshold relaxation,
  source repair, substitute geometry or later deformation stages.

Performance improvements changed verification implementation, not the prospective
acceptance policy. There was no solver-driven tuning. Any subsequent mesher or
model change requires a new revision and unique run; do not overwrite these runs.
The executed study refines boundary sizes with fixed interior bulk size0.04mm;
it is a mesh-feasibility study, not a full global mechanical convergence study.
