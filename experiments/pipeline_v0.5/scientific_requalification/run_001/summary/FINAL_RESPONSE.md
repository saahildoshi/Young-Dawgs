# v0.5C.1 completion —42 requested answers

1. **Cause of width loss.** A four-point staircase was replaced by an endpoint chord that removed material from a9-cell solid section. The opposite boundary stayed fixed; the replacement line intersects x=57.5 at y=560.9166666667 instead of561, giving a1/12-cell width loss.

2. **Detection versus validation.** Both. EDT-based screening used diameter≤8 while the probe had diameter8.94427191; proximity screening used2cells while the section was9cells; no registered probe guarded the change hull. Chord collision, clearance, area and raster tests did not measure that corridor width.

3. **Algorithmic correction.** The new protected_v2 namespace adds local source-opposition queries and native-axis projection-event affine width qualification before leaf acceptance. Qualifying loss above1e-10cell or ambiguous affected geometry rejects and restores the original subchain. All original guards/budgets and DP traversal semantics remain.

4. **Generalization of correction.** It operates on every otherwise eligible proposal using geometry, source indices, a registered16-cell width horizon and horizontal/vertical section events. It contains no design identifier or failed coordinate. Complementary oblique measurements remain independent validation.

5. **Original B2 preservation.** Yes. Original B2 source hashes are unchanged and its full failure-fixture output reproduced the historical WKB byte-for-byte: True.

6. **Independent reproduction.** Yes. Saved geometry, full original rerun, GEOS section measurement and independent coordinate interpolation reproduce9→8.916666666667cells.

7. **Corrected original section.** Yes. Revised actual section width=9.000000000000cells. The exact old chord is rejected for qualifying_solid_width_loss; its source subchain is retained.

8. **Synthetic failure controls.** 50 new analytic/adversarial cases cover translated/angled/tapered/curved corridors, high curvature, junctions, raster-invisible narrowing, area/topology-insensitive losses, safe edits, uncertainty, guards, rollback, no-op/determinism and small-pore identity/metric controls. Fifteen synthetic pore-policy artifact cases are separately saved.

9. **Unsafe chord rejection.** Yes. Width-damaging and uncertain leaves retain their original source coordinates, with original/proposed/restored chains and reasons. No morphology or post hoc widening repairs a failed output.

10. **New rejection counts.** Total width/uncertainty rejection flags=102668. Regression leaves formerly accepted by original B2 and now rejected specifically by width qualification=41016. Flags are repeated-setting instances and may overlap prior area rejection; they are not unique damaged struts.

11. **Rollback and no-op.** Total local restorations=173847, unchanged eligible-chain instances=250201, assembly rollbacks=0. Whole-candidate no-op configurations=96. Raw failures remain failures; no hidden rescue is applied.

12. **Newly identified vulnerable sections.** Yes. Proposal impact screening evaluates390787 qualifying affine section instances beyond fixed guards, including the originally unguarded failure. It does not enlarge or relabel the original guard coverage.

13. **Repair preservation.** Registered repair sites=161; maximum measured clearance loss=0cell. Exact patch and protected-coordinate gates remain active.

14. **Registered width preservation.** Registered natural probes=768; maximum measured registered width loss=0cell. Fixed connector/link requirements remain unchanged.

15. **Retained reduction.** Regression reduction ranges: ε.50 1.628392–5.157764%; ε.75 1.164927–3.431293%. Independent ranges: ε.50 1.315537–6.228008%; ε.75 0.870632–4.474548%. All lower settings and no-ops are retained.

16. **Runtime and memory.** Matched targeted instrumented engine times were 2.212345s original and 4.094561s revised. Engine traced peaks were 23.143/23.138MiB. Full-study execution=2703.774s and lifetime RSS=913.875MiB. No full-validation tracemalloc peak or cross-instrumentation speedup is claimed.

17. **New topology defects.** Independent manifold checks passed160/160 evaluable candidates; raw failures/internal errors=[]. Unsupported inputs=[]. All exceptions remain counted.

18. **Pore identities.** Unique positive-overlap plus reciprocal-anchor matching, region counts, domain-void incidence and per-pore records check identities; equal area alone does not establish correspondence. See every independent_validation.json for merges/splits/births/deletions and any failure.

19. **Area budgets.** Frozen hard-constraint passes=160/160. Worst added/removed=336.25/336.25cell². Budgets remain0.25% per sign and0.5% symmetric of occupied G2 area; G2-based per-pore cap remains0.5%.

20. **Displacement bound.** Worst independently bounded G2→G3 displacement=0.702155172414cell; cumulative G1→G3=0.702155172414cell. Ceiling remains sqrt(2)/2cell with1e-10 numeric allowance; sampled lower bounds are not exact Hausdorff maxima.

21. **Raster equality.** Exact native reconstruction passed160/160 evaluable cases. G1/G2 source reconstructions are separately checked; masks are not replaced.

22. **Frozen descriptors.** Frozen v1.1 comparisons passed160/160. Independently identical arrays reuse authenticated deterministic scalar/full S2/L results; selected changed candidates receive explicit integration evaluation. P10 definition/caveat is unchanged.

23. **Origin of small-pore discrepancy.** A local solid-side A1 regularization adds a diamond of radius0.25cell at a genuine point contact; one incident pore loses a triangle r²/2=1/32cell². A1 changes1cell² to0.96875cell², a3.125% relative loss. Simplification does not cause that original discrepancy.

24. **Scientific adequacy of pore policy.** Existing A1 criteria were applied correctly within their geometric scope; that does not establish cumulative pore-fidelity adequacy. The B2 relative cap starts at G2 and is not retroactively applied to A1. Cumulative small-pore scientific policy remains UNQUALIFIED.

25. **Policy amendment.** No fidelity amendment is adopted. An absolute1/32cell² construction-scale diagnostic and0.5% relative diagnostic were evaluated with AND/OR combinations on synthetic and independent real pores. Both errors and mandatory topology/identity remain visible; a mathematical construction envelope is not a physical allowance.

26. **Remaining pore errors.** Across all source pores, maximum G1→G2 absolute error=0.0625cell² and relative error=6.250000%. Actual G1→G3 maxima: absolute=0.0625cell²; relative=6.250000%. Maximum G2→G3 relative pore-area distortion=0.000000%; shape and perimeter changes remain separate. Seven independent 1-cell² pores lose two contact triangles, leaving0.9375cell² (6.25% loss), with identity preserved.

27. **New parameter combinations.** Six entirely new parameter positions inside original v0.3 bounds, listed exactly in the main report, PROTOCOL.json and the machine cohort table; both new seeds12031/12032 at each.

28. **Independent selection.** Deterministic scipy.stats.qmc.LatinHypercube, sampling seed20261021, with normalized distances from every original point recorded. No outcome filtering or native geometry inspection occurred before final code/protocol freeze.

29. **New realizations.** 12 new native1024 arrays were generated out of12 planned realizations. Existing20 source masks were authenticated and reused, never regenerated. Unsupported/native failures remain in the denominator.

30. **Independent configurations.** 60 independent configuration records versus60 expected; total study=160 including100 expected consumed regression configurations. Settings=[0,.20,.35,.50,.75].

31. **Independent qualification.** PASS_TESTED_DOMAIN for the registered feature/geometry domain. Overall scientific acceptance is separately HOLD_SMALL_PORE_POLICY.

32. **Holdout tuning.** No. Final hashes, cohort, seeds, width settings, budgets and small-pore disposition were frozen before independent native generation; final verification authenticates them again. Any subsequent algorithm correction would require a new version and fresh cohort.

33. **Coverage limits.** Integrated finite native-axis event checks and a16-cell horizon; independent unique axial probes=6144, oblique probes=1536. Finite orientation/location coverage, raster resolution, ambiguous cases and shared floating GEOS definitions prevent universal minimum-neck or mechanical claims. No monitored section intersects an accepted replacement chord in this cohort, limiting independent evidence about the changed regions.

34. **Maximum width loss.** Maximum measured new independent width loss=0cell. Narrowing observations axial/oblique=0/0; undefined sections=0. Values within1e-10 are numerical comparisons, not an engineering loss allowance.

35. **Continuous error.** Worst actual G2→G3 symmetric difference=672.5cell²; cumulative G1→G3=672.75cell². G1→G2 repair differences are separately measured, never added as assumed error totals.

36. **Software tests.** 457 tests passed: all407 prior tests plus50 new tests; failures/errors=0/0. Actual platform macOS ARM64. Windows execution is not claimed.

37. **Historical preservation.** 5777/5777 initial files remain byte-identical; modified/missing=[]. This includes generators, evaluator, exact/manifold artifacts, original B2/C code and all historical acceptances/failures.

38. **Created/modified files.** New files only: geometry/protected_v2,50-case test file, C.1 comparison/profile/pore/report/closeout scripts, new documentation and scientific_requalification/run_001 evidence tree. verification/new_files.json lists exact additions and hashes; no prior file is intentionally modified.

39. **Exact status.** A_source_preservation=PASS_BYTE_IDENTICAL; B_root_cause=PASS_REPRODUCED; C_generalized_correction=PASS_DOCUMENTED_FAILURE_CLASS; D_synthetic_controls=PASS_50_TARGETED_TESTS; E_regression=PASS_TESTED_DOMAIN; F_independent_features=PASS_TESTED_DOMAIN; G_continuous_geometry=PASS_TESTED_BUDGETS; H_raster_morphology=PASS_EXACT; I_small_pore_policy=UNQUALIFIED_CUMULATIVE_FIDELITY; J_overall_scientific=HOLD_SMALL_PORE_POLICY; K_production=HOLD_UNQUALIFIED; L_CAD_manufacturing_FEM=UNQUALIFIED

40. **v0.5D eligibility.** General scientific advancement remains HOLD while cumulative small-pore fidelity is unqualified, and also for any recorded feature/geometry failure. A separately scoped future export software investigation is distinct from qualifying the complete workflow. No v0.5D implementation is performed.

41. **Production qualification.** Yes: HOLD_UNQUALIFIED. No tolerance is selected by best-of-holdout performance and no universal or automatic production simplification policy is established.

42. **Limits before3D.** Finite geometry/probe coverage, unresolved cumulative small-pore criteria, subpixel regularizations, absent physical scale and CAD-kernel tolerances/interoperability, no mesh/material/load/strength/manufacturing qualification. Resolve these through separately registered engineering stages before claiming3D or FEM readiness.
