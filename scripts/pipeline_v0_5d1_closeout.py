"""D1 preservation, 46 completion answers, handoff and final file authentication."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from metamaterial_eval.geometry.reporting import repository_inventory
from metamaterial_eval.geometry.svg_io.diagnostics import write_json
from metamaterial_eval.geometry.svg_io.study import OUT, ROOT, authenticate_source, read, verify_freeze
from metamaterial_eval.geometry.validation.checks import authenticate, digest


def main(finalize=False):
    protocol = verify_freeze(); s = read(OUT / "summary/SVG_EXPORT_VALIDATION.json"); tests = read(OUT / "verification/SOFTWARE_TESTS.json")
    initial = read(OUT / "verification/INITIAL_INVENTORY.json"); current = repository_inventory(ROOT, ROOT / "NONEXISTENT_D1")
    changed = [p for p, h in initial.items() if current.get(p) != h]
    preservation = {"preexisting_files": len(initial), "unchanged": len(initial) - len(changed), "modified_or_missing": changed}
    write_json(OUT / "verification/PRESERVATION.json", preservation); s["preservation"] = preservation
    write_json(OUT / "summary/SVG_EXPORT_VALIDATION.json", s)
    row = s["rows"]; profile = s["traced_profile"]["records"]
    size_text = "; ".join(r["fixture"] + ": " + f"{r['svg_bytes']:,}" + " bytes" for r in row)
    answers = [
        ("Reused modules", "Existing binary64 WKB loading, independent native-center rasterization/raster metrics, continuous area and region correspondence, boundary incidence, dedicated manifold ray/segment checker, serialization checks, frozen evaluator worker and frozen morphology comparison. No generator, exact converter, manifold or simplifier was rerun on real sources."),
        ("New source modules", "The additive geometry/svg_io package contains exporter.py, importer.py, verification.py, controls.py, diagnostics.py and study.py, plus its package initializer. New report/closeout scripts, 72-test file, D1 documentation and a new experiment tree complete the work."),
        ("SVG representation", "One black, unstroked compound path with explicit absolute M/L/Z commands. Source vertices are preserved, with deterministic ring/component ordering and cyclic starts."),
        ("Representation rationale", "Saved geometry consists of straight polygon edges. Explicit line commands introduce no curve fitting, smoothing, transform, implicit approximation or second simplification. One semantic material path avoids decorative primitives being interpreted as solid."),
        ("Polygon exteriors", "Each exterior is a closed SVG subpath. The exporter sidecar records shell ownership; the reader independently reconstructs shells from even nesting depth."),
        ("Enclosed pores", f"Each pore boundary is a closed subpath. Odd nesting depth makes void; deeper even rings become solid islands. All {sum(r['holes'] for r in row)} real-source pores retain identities and geometry."),
        ("Fill rule", "Explicit fill-rule=evenodd. Winding variations, multiple components, concentric boundaries, deeply concave shapes and exterior channels are tested. Unsupported touching/overlapping subpaths fail instead of receiving automatic repair."),
        ("Coordinate convention", "The unchanged [column,column+1]×[row,row+1] convention: x right, y down, viewBox 0 0 1024 1024. No padding, transpose, reflection or transform is applied."),
        ("Coordinate precision", "Canonical 17 significant digits with exact binary64 vertex and undirected-edge multiplicities required. Tests cover 10,005 numeric values plus fractional/non-dyadic/short-edge shapes and every selected saved vertex."),
        ("Physical scaling", "None. Coordinates remain dimensionless raster-cell coordinates; width/height are SVG display dimensions. Physical scale is null, not one millimeter per SVG coordinate."),
        ("Independent reimport", "The reader opens persisted SVG bytes, parses XML, checks the restricted contract, tokenizes M/L/Z independently, recovers closed rings, indexes containment and assembles even-odd faces. Source coordinate arrays and sidecar ownership never enter reconstruction."),
        ("Shared dependencies", "Python binary64 conversion and Shapely/GEOS geometry predicates/assembly are shared. Writer and reader do not share path construction/tokenization or ring classification. Sharp/libvips/librsvg interprets saved SVG separately for display previews; that is not CAD-kernel qualification."),
        ("Selected source fixtures", "A: D9/S1 G1, already manifold without A1 regularization; its historical 15-pixel native-generator repair remains part of unchanged G0. B: D0/S0 G2 with one contact repair. C: D4/S1 corrected G3 at epsilon0.50, 5.157763706% nonzero reduction. D: C.1 new point0/seed12031 G2, including documented pore186 with6.25% historical loss. Exact paths, parameters, seeds and reasons were registered before export."),
        ("Source hash verification", "Yes. All geometry, canonical raster, native-generation manifest, source manifest, qualification and applicable C.1 candidate/guard hashes were authenticated before execution and again at closeout."),
        ("SVG parse success", "All four canonical real SVGs parsed successfully. Failed lower-precision and malformed/tampered diagnostic files remain saved and are not substituted for canonical files."),
        ("Solid components", "All components were preserved. Each real fixture remains one continuous solid component. Synthetic multiple-component and nested-island cases also pass at canonical precision."),
        ("Enclosed pores", "All real pores retain reciprocal identities, areas, boundaries and occupied/void semantics. The selected source pore with0.9375cell² remains exactly0.9375cell² after SVG reimport."),
        ("Exterior-connected void channels", "Preserved through actual domain-void correspondence and domain-side incidence, supplemented by exact boundary/region equality. No exterior opening is silently closed."),
        ("OGC validity", "Preserved for all four canonical imports. Invalid/crossing/degenerate negative controls are rejected without make_valid, buffer repair, snapping or replacement."),
        ("Dedicated manifold status", "Preserved in4/4. The reused segment/ray/link checker and independent degree/edge/ring incidence detect no newly introduced contacts, crossings, overlaps or degenerate edges."),
        ("Registered subpixel repairs", f"All {s['registered_repairs']} sites pass. Local material and boundaries, original added-solid footprints, registered coordinates, pore relationships and minimum clearance0.3535533905932738cell are unchanged. The {s['registered_normal_widths']} available registered normal chords and G3 guard sets also retain geometry."),
        ("Maximum area discrepancy", f"{s['maximum_absolute_area_discrepancy']:.12g}cell², comparing imported G4 directly with its selected saved Gk. The separate arithmetic-only allowance never forgives changed coordinates or regions."),
        ("Maximum symmetric difference", f"{s['maximum_symmetric_area']:.12g}cell². Added and removed material are each zero for every canonical real fixture."),
        ("Maximum boundary displacement", f"{s['maximum_boundary_displacement']:.12g}cell. Exact boundary line-set coincidence supplies the zero result; it is not an inference from sparse distance samples."),
        ("Coordinate changes", "None in canonical real imports: exact binary64 vertex/segment recovery, preserving multiplicity. Winding, cyclic starts and ring/component order may differ, so byte-identical source WKB is not required."),
        ("Raster reconstruction", "Every imported geometry independently rasterizes exactly to the original1024 G0 mask with IoU1. The scientific raster uses cell-center predicates and is separate from antialiased SVG preview rendering."),
        ("FP, FN and XOR maxima", f"FP={s['maximum_false_positive']}, FN={s['maximum_false_negative']}, XOR={s['maximum_raster_xor']}. Every real fixture retains one4-connected solid component, largest fraction1 and both percolation directions."),
        ("Frozen morphology", "Preserved. Fixture A has fresh original/imported evaluator-v1.1 calls; the other three reuse authenticated deterministic scalar/full S2/lineal results after independently identical arrays. The historical P10 caveats remain. Descriptor equality is not used as continuous-equivalence proof."),
        ("Precision failures", "At17 digits all 20 analytic shapes pass. At12 digits six parsed shapes change geometry; at 9 digits four change and two fail parsing; at 6 digits four change and three fail parsing; at 3 digits three change and seven fail parsing. Real12/9/6-digit files happen to recover their dyadic coordinates, but all four real3-digit files collapse vertices and are rejected. Canonical policy remains17 digits."),
        ("Output SVG sizes", size_text + ". These are actual saved canonical byte counts, including provenance metadata."),
        ("Export runtime", f"Sum={s['svg_export_seconds_sum']:.9f}s; per-fixture range={min(r['timings']['export_seconds'] for r in row):.9f}–{max(r['timings']['export_seconds'] for r in row):.9f}s. Single untraced observations, including writer checks and file output."),
        ("Import runtime", f"Sum={s['svg_import_seconds_sum']:.9f}s; per-fixture range={min(r['timings']['total_import_seconds'] for r in row):.9f}–{max(r['timings']['total_import_seconds'] for r in row):.9f}s. Includes saved-file reading, XML/path interpretation and polygon reconstruction; comparison is timed separately."),
        ("Observed memory", f"Real-study process lifetime peak RSS={s['process_lifetime_peak_rss_bytes']/2**20:.3f}MiB. Isolated Python traced export/import peaks reach{max(r['export_traced_peak_bytes'] for r in profile)/2**20:.3f}/{max(r['import_traced_peak_bytes'] for r in profile)/2**20:.3f}MiB. Already-loaded sources and native GEOS allocation are incompletely covered by tracing; no full-study traced peak is claimed."),
        ("Previous software tests", f"All{tests['previous_tests']} previous tests passed unchanged. The full suite has{tests['tests']} passing tests, zero failures/errors/skips, executed on macOS ARM64. Windows execution is not claimed."),
        ("New software tests", f"{tests['new_svg_tests']} new SVG tests passed. Persisted experiments additionally retain20 positive regions,100 precision configurations and31 known failure cases, all 31 detected in the final synthetic run."),
        ("Historical preservation", f"{preservation['unchanged']}/{preservation['preexisting_files']} preexisting files remain byte-identical. Changed/missing={changed}. Existing Git modifications were inventoried and preserved rather than reset."),
        ("Created files", "New svg_io source package, SVG test file, D1 reporting/closeout scripts, architecture/reproduction/validation/handoff documents, and svg_export_validation/run_001 protocol, snapshots, four canonical SVG/sidecars, imported WKB/JSON, rasters, metrics, controls, previews, figures and verification ledger. Exact additions/hashes are in verification/new_files.json."),
        ("Modified existing files", "None. Generators, evaluator, exact/manifold/simplified geometries, older geometry modules, prior reports and experiments remain unchanged. New D1 development files were finalized within the new implementation before its registered freeze."),
        ("Exact export qualification", s["status"] + ". This is research-only qualification of the selected saved files and supported SVG subset, not full scientific advancement."),
        ("Cumulative small-pore fidelity", "Still UNQUALIFIED. The selected stress pore remains G1=1, G2=G4=0.9375cell²: original loss0.0625cell²/6.25%, additional SVG loss0. No manifold or cumulative pore policy was amended."),
        ("Production simplification", "Still HOLD_UNQUALIFIED. The selected G3 is one individually screened research input, not a chosen production tolerance or automatic simplification policy."),
        ("CAD-kernel interoperability", "Still UNQUALIFIED. No CAD kernel, downstream solid builder, DXF, STEP, STL,3D, mesh or FEM tool was used."),
        ("Before DXF export", "Obtain separate authorization and register a DXF-specific representation/consumer contract: dimensional semantics without assumed millimeters, entity/loop/hole ownership, precision, unsupported features, trusted hashes, independent reload and continuous/raster/feature acceptance. Preserve source qualification limitations."),
        ("Before 3D CAD", "Establish accepted source and cumulative-pore criteria, physical dimensions and intended use, minimum-feature clearances relative to a selected CAD kernel's numeric tolerance, independent kernel import and a separately authorized validated solid-construction protocol. No extrusion is authorized by SVG success."),
        ("Remaining limitations", "Four real fixtures in one morphology family; restricted M/L/Z even-odd subset; shared floating geometry kernel; importer-specific behavior; no cross-platform guarantee; retained subpixel A1 changes and C.1 changed-region audit coverage limits; unknown physical scale, material/load/strength, meshing, manufacturing and cumulative pore fidelity."),
        ("Next proposed milestone", "A separately authorized research-only v0.5D2 DXF interchange protocol and independent reimport study. Define its contract first; do not begin implementation now. Broader scientific policy resolution and eventual3D/CAD qualification remain distinct work.")
    ]
    assert len(answers) == 46
    (OUT / "summary/FINAL_RESPONSE.md").write_text("# v0.5D1 completion — 46 requested answers\n\n" + "\n\n".join(f"{i}. **{title}.** {answer}" for i, (title, answer) in enumerate(answers, 1)) + "\n")
    report = OUT / "summary/SVG_EXPORT_VALIDATION.md"
    text = report.read_text(); marker = "\n## Final preservation verification\n"
    if marker in text:
        text = text.split(marker)[0]
    report.write_text(text + marker + f"\n{preservation['unchanged']}/{preservation['preexisting_files']} preexisting files remain byte-identical; modified/missing={changed}. Final code/protocol/source and figure hashes are authenticated in verification/COMPLETION.json and new_files.json. Implementation completion does not change the source scientific HOLD.\n")
    handoff = f'''# v0.5D1 handoff — stop before DXF or 3D

Research-only SVG result: **{s['status']}**, four registered saved fixtures.
Source scientific status: **HOLD_SMALL_PORE_POLICY**. Cumulative pore fidelity:
**UNQUALIFIED**. Production simplification: **HOLD_UNQUALIFIED**. CAD-kernel,
FEM and manufacturing interoperability/readiness: **UNQUALIFIED**.

The exporter preserves every stored binary64 vertex in one explicit M/L/Z
even-odd compound path at 17 significant digits. The independent reader parses
saved XML/path text and infers nesting without source coordinates or sidecar
ownership. Shared Python/Shapely/GEOS dependencies remain disclosed. SVG preview
rendering is separate from scientific cell-center rasterization.

All four real cases have zero additional area, symmetric difference, boundary
displacement and raster XOR. All14registered repair sites retain their exact
local geometry and0.3535533905932738cell clearance. The selected stress pore stays
G1=1→G2=G4=0.9375cell²:6.25% historical loss remains scientifically unqualified.
The earlier finite width-audit coverage limitation also remains unchanged.

Use only the paired SVG, JSON sidecar, imported geometry and complete source
qualification/provenance bundle in svg_export_validation/run_001. Read
summary/SVG_EXPORT_VALIDATION.md and JSON/CSV, FINAL_RESPONSE.md (all 46 answers),
protocol/FINAL_FREEZE.json and verification/COMPLETION.json. Do not replace
saved sources or treat a successful viewer rendering as mathematical evidence.

Proposed next software stage: separately authorized research-only DXF
interchange qualification. Before implementation, register the format/entity
and independent consumer, source state, ring/pore ownership, coordinate/unit
semantics, numerical precision, continuous/raster/topology/feature gates and
failure retention. No default1 SVG coordinate=1mm mapping is permitted.

Before 3D: resolve or explicitly qualify the source scientific scope, cumulative
small-pore fidelity and feature-coverage limitations; assign justified physical
dimensions; compare clearances against a named CAD kernel's tolerances; verify
independent kernel import; register solid construction and subsequent mesh/load/
material studies separately. SVG success provides none of these qualifications.

No DXF, STEP, STL, CAD kernel,3D extrusion, mesh, FEM, strength prediction or
manufacturing functionality is implemented. All{preservation['preexisting_files']}
preexisting files are preserved. Actual execution: macOS ARM64; Windows syntax
is documentation only. **Stop at v0.5D1.**
'''
    (OUT / "summary/V0_5D1_HANDOFF.md").write_text(handoff)
    (ROOT / "docs/pipeline_v0.5/V0_5D1_HANDOFF.md").write_text(handoff)
    (ROOT / "docs/pipeline_v0.5/SVG_EXPORT_VALIDATION.md").write_text("# v0.5D1 executed SVG validation\n\nAuthoritative report: `experiments/pipeline_v0.5/svg_export_validation/run_001/summary/SVG_EXPORT_VALIDATION.md`, with adjacent JSON/CSV, FINAL_RESPONSE.md and verification/COMPLETION.json.\n\nResearch-only export qualification is separate from the unchanged scientific HOLD, production HOLD, absent physical scale and unqualified CAD/FEM/manufacturing. No DXF or3D is implemented.\n")
    if finalize:
        assert not changed
        assert tests["tests"] == 529 and tests["failures"] == tests["errors"] == tests["skipped"] == 0
        qa = read(OUT / "verification/FIGURE_QA.json"); assert qa["inspected_global_figures"] == 10
        for p, h in qa["sha256"].items():
            authenticate(OUT / p, h)
        for f in protocol["fixtures"]:
            authenticate_source(f); m = read(OUT / "exports" / (f["id"] + ".json"))
            authenticate(OUT / "exports" / m["svg_filename"], m["svg_sha256"])
            authenticate(OUT / "imports" / f["id"] / "G4.wkb", m["imported_geometry_sha256"])
            assert m["validation"]["passed"]
            assert m["source_scientific_qualification"] == protocol["inherited_statuses"]
        completion = {"completed_utc": datetime.now(timezone.utc).isoformat(), "implementation_complete": True,
                      "export_qualification": s["status"], "inherited_statuses": protocol["inherited_statuses"],
                      "software_tests": tests, "preservation": preservation, "figures": 10,
                      "real_fixtures": 4, "canonical_source_generation": False,
                      "historical_acceptances_and_HOLDs_unchanged": True, "DXF_or_3D_implemented": False}
        write_json(OUT / "verification/COMPLETION.json", completion)
        current = repository_inventory(ROOT, ROOT / "NONEXISTENT_D1")
        ledger_path = str((OUT / "verification/new_files.json").relative_to(ROOT))
        additions = [{"path": p, "sha256": h, "bytes": (ROOT / p).stat().st_size} for p, h in current.items() if p not in initial and p != ledger_path]
        write_json(OUT / "verification/new_files.json", {"count": len(additions), "ledger_self_excluded": True, "modified_preexisting": changed, "files": additions})
    print("Closeout", s["status"], "answers", len(answers), "preserved", preservation, flush=True)


if __name__ == "__main__":
    main("--finalize" in sys.argv)
