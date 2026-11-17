# Presentation fabrication results

Two different material systems are represented. P3 is a raised composite annotation on a continuous solid backing; its matrix is not void. The historical Design9/seed1 model is a straight extrusion of the porous network, with genuine open holes and no backing. Both are enlarged educational props, not authentic3D reconstructions, calibrated specimens or physically printed results.

| File | Display dimensions (mm) | Independent mesh qualification | Open enclosed through-pores |
|---|---|---|---|
| P3_REFERENCE_EXACT_RELIEF.stl |168×168×3.6|FAIL:14 diagonal-only nonmanifold contacts|0|
| P3_REFERENCE_PRINT_READY.stl |168×168×3.6|PASS|0|
| POROUS_METAMATERIAL_FULL1024_ORIGINAL.stl |160×160×5|PASS; fine details remain|412|
| POROUS_METAMATERIAL_ORIGINAL.stl |160×160×5|PASS; authenticated central crop|19|
| POROUS_METAMATERIAL_PRINT_READY.stl |165×165×5|PASS; external2.5mm frame|35|

P3 source labels1/5 contain20731 raised pixels. The print copy contains20354:1383 pixels change (880 removed,503 added), and four-connected raised regions change78→52. Scientific source arrays remain unchanged. Prescribed3×3 opening/closing is followed by six additions at three remaining diagonal-contact sites. The unchanged exact export is retained with its failure explicitly visible.

The porous full1024 array has500104 solid pixels and one four-connected body. Its15-pixel add-only repair was already part of the preserved historical canonical source. The central[384:640,384:640] crop has32195 solid pixels, one body,19 interior pores and16 boundary-clipped void pockets. The crop is recommended at presentation size because it enlarges each original pixel to0.625mm instead of0.15625mm in the full specimen. No internal crop pixel is changed. A1625mm² frame outside the160mm field encloses the16 boundary pockets; the original19 interior holes remain open. Uniform XY scaling preserves proportions.

All qualified meshes have positive volume, consistent winding, two faces per edge, no duplicate/degenerate faces and one connected body after independent STL parsing and identical-position welding. Porous midsections at Z0.25,2.5,4.75mm match the expected polygons with zero area difference; Euler characteristic agrees with the through-hole count. Source polygon fidelity is authenticated against all1048576 pixel centers, integer axis-aligned boundaries and exact area. Eight zero-area crop-boundary line remnants are discarded, as in the historical positive-area crop convention. A nominal1e-7mm triangulation simplification removes degeneracy; analytic volume and all independent sections retain exact source support. Self-intersection exclusion is based on the valid simple-polygon straight extrusion or disjoint height-field construction, plus independent topology/section tests; no arbitrary-triangle collision solver is claimed.

Actual installed Dremel CuraEngine slicing succeeded for both recommended files using a hypothetical220×220×250mm bed,0.4mm nozzle,0.45mm extrusion width and0.2mm layers. P3 produced18 layers, porous25. Independent G-code inspection found all layers present, on-bed extrusion, no support paths and one significant connected first-layer body. Approximate nominal first-layer coverage is99.985% for P3 and99.463% for porous. All35 porous centers and eroded pore cores remain clear. These are computed bead-footprint approximations, not measurements of a physical print. Older slicer header placeholders for time/zero filament are not trusted; actual E moves and elapsed-time output are retained separately.

Two initial slicer setup attempts and two rejected porous triangulation attempts are preserved outside Git with hashes and compact receipts. The first slicer attempt used a wrong extruder path, the second placed the object off bed; neither qualifies. No scientific geometry or historical solver result was changed to resolve these fabrication setup issues.

Minimum-width diagnostics are approximate EDT/skeleton proxies. Narrow stair-step/taper details remain, including0.625mm steps in the crop. The frame improves boundary support without guaranteeing0.8mm minimum width everywhere. Both recommended meshes have actual generic-engine and toolpath checks, but physical reliability and compatibility with the user's printer are NOT_VERIFIED. Reslice for the real printer and inspect narrow members, holes and optional color changes. No generic G-code is supplied as printer-ready.

Actual mesh previews, generic toolpath previews, the side-by-side comparison, source/validation JSON and separate printing instructions are in presentation_assets/v0.7.4. P3 instructions describe an optional color change after the2.4mm base; porous instructions describe the source-faithful and framed variants. There were zero new porous mechanical solves and zero3D mechanical analyses.
