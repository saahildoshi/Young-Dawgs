# v0.5C.1 handoff — stop before v0.5D

Scientific status: **HOLD_SMALL_PORE_POLICY**. Feature qualification: **PASS_TESTED_DOMAIN**. Cumulative small-pore policy: **UNQUALIFIED**. Production: **HOLD_UNQUALIFIED**. CAD/manufacturing/FEM: **UNQUALIFIED**.

The new explicit algorithm is `guarded_dp_v2.0_impact_width` under geometry.protected_v2. Original protected/validation modules, B2 accepted candidates and the historical C HOLD remain immutable. The original9→8.916666667-cell failure is preserved and reproduced; the versioned correction keeps that section at9cells without a coordinate-specific rule.

Read scientific_requalification/run_001/summary/FEATURE_PROTECTION_CORRECTION.md, SMALL_PORE_QUALIFICATION.md, INDEPENDENT_REQUALIFICATION.md and JSON, CONFIGURATIONS.csv and FINAL_RESPONSE.md for all42 completion answers. Read protocol/FINAL_FREEZE.json and verification/COMPLETION.json for actual freeze, platform, repeat, software, figure and preservation evidence. Every case records G0/G1/G2/G3 provenance and actual independent measurements.

All20 original realizations are consumed regression evidence. The only new holdouts are six LHS positions under original bounds, sampling seed20261021, stochastic seeds12031/12032, generated after final freeze. Do not tune a later algorithm against these consumed holdouts while calling the result independent. A further correction needs a separate version and fresh reserved cohort.

The integrated criterion covers registered native-axis affine corridors/horizon, not every possible cross-section. Independent axial and oblique audits remain finite. A local positive clearance or width is not assigned physical dimensions. Small-pore area must retain absolute and relative errors: one contact triangle changes1cell² to0.96875cell²; no engineering allowance is adopted merely because the footprint is small. The new cohort contains seven1-cell² pores with two contact repairs and6.25% loss. None of the finite independent monitored sections intersects an accepted replacement chord, which limits changed-region audit coverage. Existing A1 geometric scope is not cumulative scientific qualification.

**General advancement remains HOLD.** A future2D export protocol must separately define physical mapping, consumer/kernel, numeric tolerances, formats, ring/ownership conventions and reload checks, retaining original/exact/manifold/simplified/exported states. Internal WKB/JSON checks do not establish future interoperability. Any limited software-only export investigation must explicitly state its individually accepted input scope and cannot imply complete pipeline acceptance.

No exporter, SVG/DXF, CAD kernel,3D, meshing, FEM or manufacturing functionality is implemented. Actual execution was macOS ARM64; reproduction syntax for Windows is documentation only. Do not rerender saved native sources or overwrite completed experiment trees during reproduction. **Stop at v0.5C.1.**
