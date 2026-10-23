# v0.5D1 completion — 46 requested answers

1. **Reused modules.** Existing binary64 WKB loading, independent native-center rasterization/raster metrics, continuous area and region correspondence, boundary incidence, dedicated manifold ray/segment checker, serialization checks, frozen evaluator worker and frozen morphology comparison. No generator, exact converter, manifold or simplifier was rerun on real sources.

2. **New source modules.** The additive geometry/svg_io package contains exporter.py, importer.py, verification.py, controls.py, diagnostics.py and study.py, plus its package initializer. New report/closeout scripts, 72-test file, D1 documentation and a new experiment tree complete the work.

3. **SVG representation.** One black, unstroked compound path with explicit absolute M/L/Z commands. Source vertices are preserved, with deterministic ring/component ordering and cyclic starts.

4. **Representation rationale.** Saved geometry consists of straight polygon edges. Explicit line commands introduce no curve fitting, smoothing, transform, implicit approximation or second simplification. One semantic material path avoids decorative primitives being interpreted as solid.

5. **Polygon exteriors.** Each exterior is a closed SVG subpath. The exporter sidecar records shell ownership; the reader independently reconstructs shells from even nesting depth.

6. **Enclosed pores.** Each pore boundary is a closed subpath. Odd nesting depth makes void; deeper even rings become solid islands. All 1255 real-source pores retain identities and geometry.

7. **Fill rule.** Explicit fill-rule=evenodd. Winding variations, multiple components, concentric boundaries, deeply concave shapes and exterior channels are tested. Unsupported touching/overlapping subpaths fail instead of receiving automatic repair.

8. **Coordinate convention.** The unchanged [column,column+1]×[row,row+1] convention: x right, y down, viewBox 0 0 1024 1024. No padding, transpose, reflection or transform is applied.

9. **Coordinate precision.** Canonical 17 significant digits with exact binary64 vertex and undirected-edge multiplicities required. Tests cover 10,005 numeric values plus fractional/non-dyadic/short-edge shapes and every selected saved vertex.

10. **Physical scaling.** None. Coordinates remain dimensionless raster-cell coordinates; width/height are SVG display dimensions. Physical scale is null, not one millimeter per SVG coordinate.

11. **Independent reimport.** The reader opens persisted SVG bytes, parses XML, checks the restricted contract, tokenizes M/L/Z independently, recovers closed rings, indexes containment and assembles even-odd faces. Source coordinate arrays and sidecar ownership never enter reconstruction.

12. **Shared dependencies.** Python binary64 conversion and Shapely/GEOS geometry predicates/assembly are shared. Writer and reader do not share path construction/tokenization or ring classification. Sharp/libvips/librsvg interprets saved SVG separately for display previews; that is not CAD-kernel qualification.

13. **Selected source fixtures.** A: D9/S1 G1, already manifold without A1 regularization; its historical 15-pixel native-generator repair remains part of unchanged G0. B: D0/S0 G2 with one contact repair. C: D4/S1 corrected G3 at epsilon0.50, 5.157763706% nonzero reduction. D: C.1 new point0/seed12031 G2, including documented pore186 with6.25% historical loss. Exact paths, parameters, seeds and reasons were registered before export.

14. **Source hash verification.** Yes. All geometry, canonical raster, native-generation manifest, source manifest, qualification and applicable C.1 candidate/guard hashes were authenticated before execution and again at closeout.

15. **SVG parse success.** All four canonical real SVGs parsed successfully. Failed lower-precision and malformed/tampered diagnostic files remain saved and are not substituted for canonical files.

16. **Solid components.** All components were preserved. Each real fixture remains one continuous solid component. Synthetic multiple-component and nested-island cases also pass at canonical precision.

17. **Enclosed pores.** All real pores retain reciprocal identities, areas, boundaries and occupied/void semantics. The selected source pore with0.9375cell² remains exactly0.9375cell² after SVG reimport.

18. **Exterior-connected void channels.** Preserved through actual domain-void correspondence and domain-side incidence, supplemented by exact boundary/region equality. No exterior opening is silently closed.

19. **OGC validity.** Preserved for all four canonical imports. Invalid/crossing/degenerate negative controls are rejected without make_valid, buffer repair, snapping or replacement.

20. **Dedicated manifold status.** Preserved in4/4. The reused segment/ray/link checker and independent degree/edge/ring incidence detect no newly introduced contacts, crossings, overlaps or degenerate edges.

21. **Registered subpixel repairs.** All 14 sites pass. Local material and boundaries, original added-solid footprints, registered coordinates, pore relationships and minimum clearance0.3535533905932738cell are unchanged. The 96 available registered normal chords and G3 guard sets also retain geometry.

22. **Maximum area discrepancy.** 0cell², comparing imported G4 directly with its selected saved Gk. The separate arithmetic-only allowance never forgives changed coordinates or regions.

23. **Maximum symmetric difference.** 0cell². Added and removed material are each zero for every canonical real fixture.

24. **Maximum boundary displacement.** 0cell. Exact boundary line-set coincidence supplies the zero result; it is not an inference from sparse distance samples.

25. **Coordinate changes.** None in canonical real imports: exact binary64 vertex/segment recovery, preserving multiplicity. Winding, cyclic starts and ring/component order may differ, so byte-identical source WKB is not required.

26. **Raster reconstruction.** Every imported geometry independently rasterizes exactly to the original1024 G0 mask with IoU1. The scientific raster uses cell-center predicates and is separate from antialiased SVG preview rendering.

27. **FP, FN and XOR maxima.** FP=0, FN=0, XOR=0. Every real fixture retains one4-connected solid component, largest fraction1 and both percolation directions.

28. **Frozen morphology.** Preserved. Fixture A has fresh original/imported evaluator-v1.1 calls; the other three reuse authenticated deterministic scalar/full S2/lineal results after independently identical arrays. The historical P10 caveats remain. Descriptor equality is not used as continuous-equivalence proof.

29. **Precision failures.** At17 digits all 20 analytic shapes pass. At12 digits six parsed shapes change geometry; at 9 digits four change and two fail parsing; at 6 digits four change and three fail parsing; at 3 digits three change and seven fail parsing. Real12/9/6-digit files happen to recover their dyadic coordinates, but all four real3-digit files collapse vertices and are rejected. Canonical policy remains17 digits.

30. **Output SVG sizes.** A_G1_D9S1: 475,043 bytes; B_G2_D0S0: 389,584 bytes; C_G3_D4S1_E050: 350,963 bytes; D_G2_C1P0S12031: 388,543 bytes. These are actual saved canonical byte counts, including provenance metadata.

31. **Export runtime.** Sum=0.717549125s; per-fixture range=0.164326917–0.206544666s. Single untraced observations, including writer checks and file output.

32. **Import runtime.** Sum=0.724902666s; per-fixture range=0.161210416–0.217276083s. Includes saved-file reading, XML/path interpretation and polygon reconstruction; comparison is timed separately.

33. **Observed memory.** Real-study process lifetime peak RSS=504.047MiB. Isolated Python traced export/import peaks reach19.285/14.789MiB. Already-loaded sources and native GEOS allocation are incompletely covered by tracing; no full-study traced peak is claimed.

34. **Previous software tests.** All457 previous tests passed unchanged. The full suite has529 passing tests, zero failures/errors/skips, executed on macOS ARM64. Windows execution is not claimed.

35. **New software tests.** 72 new SVG tests passed. Persisted experiments additionally retain20 positive regions,100 precision configurations and31 known failure cases, all 31 detected in the final synthetic run.

36. **Historical preservation.** 8507/8507 preexisting files remain byte-identical. Changed/missing=[]. Existing Git modifications were inventoried and preserved rather than reset.

37. **Created files.** New svg_io source package, SVG test file, D1 reporting/closeout scripts, architecture/reproduction/validation/handoff documents, and svg_export_validation/run_001 protocol, snapshots, four canonical SVG/sidecars, imported WKB/JSON, rasters, metrics, controls, previews, figures and verification ledger. Exact additions/hashes are in verification/new_files.json.

38. **Modified existing files.** None. Generators, evaluator, exact/manifold/simplified geometries, older geometry modules, prior reports and experiments remain unchanged. New D1 development files were finalized within the new implementation before its registered freeze.

39. **Exact export qualification.** SVG_EXPORT_ROUNDTRIP_PASS_TESTED_FIXTURES. This is research-only qualification of the selected saved files and supported SVG subset, not full scientific advancement.

40. **Cumulative small-pore fidelity.** Still UNQUALIFIED. The selected stress pore remains G1=1, G2=G4=0.9375cell²: original loss0.0625cell²/6.25%, additional SVG loss0. No manifold or cumulative pore policy was amended.

41. **Production simplification.** Still HOLD_UNQUALIFIED. The selected G3 is one individually screened research input, not a chosen production tolerance or automatic simplification policy.

42. **CAD-kernel interoperability.** Still UNQUALIFIED. No CAD kernel, downstream solid builder, DXF, STEP, STL,3D, mesh or FEM tool was used.

43. **Before DXF export.** Obtain separate authorization and register a DXF-specific representation/consumer contract: dimensional semantics without assumed millimeters, entity/loop/hole ownership, precision, unsupported features, trusted hashes, independent reload and continuous/raster/feature acceptance. Preserve source qualification limitations.

44. **Before 3D CAD.** Establish accepted source and cumulative-pore criteria, physical dimensions and intended use, minimum-feature clearances relative to a selected CAD kernel's numeric tolerance, independent kernel import and a separately authorized validated solid-construction protocol. No extrusion is authorized by SVG success.

45. **Remaining limitations.** Four real fixtures in one morphology family; restricted M/L/Z even-odd subset; shared floating geometry kernel; importer-specific behavior; no cross-platform guarantee; retained subpixel A1 changes and C.1 changed-region audit coverage limits; unknown physical scale, material/load/strength, meshing, manufacturing and cumulative pore fidelity.

46. **Next proposed milestone.** A separately authorized research-only v0.5D2 DXF interchange protocol and independent reimport study. Define its contract first; do not begin implementation now. Broader scientific policy resolution and eventual3D/CAD qualification remain distinct work.
