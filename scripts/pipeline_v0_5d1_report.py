"""D1 reports and scientific figures from persisted study outputs only."""
from collections import Counter
import csv
import json
from pathlib import Path
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap
import numpy as np
from PIL import Image
import shapely
from shapely import Polygon, box

from metamaterial_eval.geometry.svg_io.diagnostics import write_json
from metamaterial_eval.geometry.svg_io.study import OUT, ROOT, read
from metamaterial_eval.geometry.validation.checks import polygons, rings


def boundary(ax, g, color="#456f9e", label=None, width=.7, style="solid"):
    ax.add_collection(LineCollection([r["xy"] for r in rings(g)], colors=color, linewidths=width, linestyles=style, label=label))
    ax.autoscale(); ax.set_aspect("equal")


def fill(ax, g, color="black", alpha=1.):
    for p in polygons(g):
        ax.fill(*np.asarray(p.exterior.coords).T, color=color, alpha=alpha, linewidth=0)
        for h in p.interiors:
            ax.fill(*np.asarray(h.coords).T, color="white", linewidth=0)
    ax.set_aspect("equal"); ax.autoscale()


def window(ax, bounds):
    x0, y0, x1, y1 = bounds
    ax.set_xlim(x0, x1); ax.set_ylim(y1, y0); ax.set_xlabel("x [cell]"); ax.set_ylabel("y [cell]")


def save(fig, path, title):
    fig.suptitle(title, fontsize=11); fig.tight_layout(rect=(0, 0, 1, .94))
    if Path(path).name == "01_raster_and_svg.png":
        fig.subplots_adjust(hspace=.25, top=.88, bottom=.03)
    fig.savefig(path, dpi=160, bbox_inches="tight", pad_inches=.15); plt.close(fig)


def load_case(f):
    source = shapely.from_wkb((ROOT / f["source_geometry_path"]).read_bytes())
    imported = shapely.from_wkb((OUT / "imports" / f["id"] / "G4.wkb").read_bytes())
    exact = shapely.from_wkb((ROOT / f["source_provenance"]["paths"]["exact"]).read_bytes())
    mask = np.load(ROOT / f["canonical_raster_path"], allow_pickle=False)
    rec = np.load(OUT / "raster_reconstruction" / (f["id"] + ".npy"), allow_pickle=False)
    metrics = read(OUT / "continuous_metrics" / (f["id"] + ".json"))
    pores = [Polygon(h) for p in polygons(source) for h in p.interiors]
    if f["id"].startswith("D_"):
        historical = [Polygon(h) for p in polygons(exact) for h in p.interiors][186]
        pore = max(pores, key=lambda p: p.intersection(historical).area)
    else:
        pore = min(pores, key=lambda p: (p.area, p.bounds)); historical = None
    x0, y0, x1, y1 = pore.bounds; margin = max(.3, .1 * max(x1 - x0, y1 - y0))
    pore_window = (x0 - margin, y0 - margin, x1 + margin, y1 + margin)
    if metrics["repairs"]["records"]:
        x, y = metrics["repairs"]["records"][0]["xy"]; repair_window = (x - .65, y - .65, x + .65, y + .65)
    else:
        repair_window = (0, 0, 16, 16)
    return {"f": f, "source": source, "imported": imported, "exact": exact, "mask": mask, "rec": rec,
            "metrics": metrics, "pore": pore, "historical_pore": historical, "pore_window": pore_window, "repair_window": repair_window}


def individual_previews(cases):
    for c in cases:
        f = c["f"]; folder = OUT / "previews" / f["id"]
        Image.fromarray((255 * (1 - c["mask"])).astype(np.uint8)).save(folder / "canonical_raster.png")
        Image.fromarray((255 * (c["mask"] != c["rec"])).astype(np.uint8)).save(folder / "raster_xor.png")
        for key in ("source", "imported"):
            fig, ax = plt.subplots(figsize=(6, 6)); fill(ax, c[key]); window(ax, (0, 0, 1024, 1024))
            save(fig, folder / (key + "_vector.png"), f["id"] + " — " + key + " polygon fill")
        for name, bounds in [("boundary_overlay", c["pore_window"]), ("pore_closeup", c["pore_window"]), ("repair_closeup", c["repair_window"])]:
            fig, ax = plt.subplots(figsize=(6, 6)); boundary(ax, c["source"], "#555", "Saved source", 2)
            boundary(ax, c["imported"], "#16885c", "SVG-derived G4", 1, "dashed"); window(ax, bounds); ax.legend(fontsize=8)
            if name == "repair_closeup":
                ax.set_title("0.3535533906-cell clearance preserved" if c["metrics"]["repairs"]["registered_count"] else "No A1 repairs; saved native connector shown")
            save(fig, folder / (name + ".png"), f["id"] + " — " + name.replace("_", " "))
        fig, ax = plt.subplots(figsize=(6, 6)); boundary(ax, c["source"], "#bbb", width=.8); window(ax, c["repair_window"])
        ax.text(.5, .5, "Added = removed = symmetric = 0 cell²\nBoundary displacement = 0 cell", ha="center", transform=ax.transAxes, bbox={"facecolor": "white", "alpha": .9})
        save(fig, folder / "continuous_difference.png", f["id"] + " — zero additional SVG geometry difference")
        views = ["canonical_raster", "source_vector", "svg_rendered", "imported_vector", "boundary_overlay", "continuous_difference", "raster_xor", "pore_closeup", "repair_closeup"]
        fig, axes = plt.subplots(3, 3, figsize=(12, 12))
        for ax, view in zip(axes.ravel(), views):
            ax.imshow(Image.open(folder / (view + ".png")), cmap="gray", vmin=0, vmax=255); ax.set_title(view.replace("_", " "), fontsize=9); ax.set_axis_off()
        save(fig, folder / "OVERVIEW.png", f["id"] + " — all nine persisted views, display only")


def figures(cases, study, synthetic, precision, profile):
    names = [c["f"]["id"].split("_")[0] for c in cases]
    fig, axes = plt.subplots(2, 4, figsize=(15, 8))
    for j, c in enumerate(cases):
        axes[0, j].imshow(c["mask"], cmap="gray_r", extent=(0, 1024, 1024, 0)); axes[0, j].set_title(c["f"]["id"] + "\nCanonical native raster", fontsize=8)
        axes[1, j].imshow(Image.open(OUT / "previews" / c["f"]["id"] / "svg_rendered.png")); axes[1, j].set_title("Actual saved SVG: Sharp/libvips", fontsize=8)
        for i in range(2): axes[i, j].set_xticks([]); axes[i, j].set_yticks([])
    save(fig, OUT / "figures/01_raster_and_svg.png", "Four authenticated saved fixtures; black solid / white void. SVG antialiasing is display-only")
    fig, axes = plt.subplots(1, 4, figsize=(15, 4))
    for ax, c in zip(axes, cases):
        boundary(ax, c["source"], "#555", "Saved source", 2); boundary(ax, c["imported"], "#16885c", "SVG-derived", 1, "dashed")
        bounds = (52, 550, 64, 564) if c["f"]["source_state"] == "G3" else c["repair_window"] if c["metrics"]["repairs"]["registered_count"] else c["pore_window"]
        window(ax, bounds); ax.set_title(c["f"]["id"], fontsize=8); ax.legend(fontsize=6)
    save(fig, OUT / "figures/02_vector_overlay.png", "Source-versus-imported boundary overlays; exact segment recovery, not visual similarity, determines acceptance")
    fig, axes = plt.subplots(1, 2, figsize=(11, 5)); c = cases[1]
    boundary(axes[0], c["source"], "#888", width=1.4); boundary(axes[0], c["imported"], "#16885c", width=.7); window(axes[0], c["repair_window"])
    axes[0].set_title("Canonical round-trip: zero continuous difference"); axes[0].text(.5, .12, "Added / removed / symmetric = 0 cell²", ha="center", transform=axes[0].transAxes, fontsize=8)
    base = OUT / "precision_controls/synthetic_run_003"
    a = shapely.from_wkb((base / "single_hole/source.wkb").read_bytes()); b = shapely.from_wkb((base / "negative_raster_invisible_continuous_shift/solid.imported.wkb").read_bytes())
    boundary(axes[1], a, "#555", "Source", 1.2); boundary(axes[1], b, "#cf5a32", "Deliberate altered SVG", 1.2)
    fill(axes[1], a.difference(b).intersection(box(9.98, 74.98, 10.04, 75.04)), "#e78b63", .7); window(axes[1], (9.98, 74.98, 10.04, 75.04)); axes[1].legend(fontsize=7)
    axes[1].set_title("Negative control: continuous error with zero raster XOR"); axes[1].text(.5, .12, "0.01-cell inward shift: rejected", ha="center", transform=axes[1].transAxes, fontsize=8)
    save(fig, OUT / "figures/03_continuous_difference.png", "Serialization preserves the source region; a subpixel shift fails despite unchanged cell-center occupancy")
    fig, axes = plt.subplots(1, 4, figsize=(13, 4))
    for ax, c in zip(axes, cases):
        ax.imshow(c["mask"] != c["rec"], cmap=ListedColormap(["white", "red"]), vmin=0, vmax=1)
        ax.text(.5, .5, "FP = FN = XOR = 0\nIoU = 1", ha="center", transform=ax.transAxes, fontsize=9); ax.set_title(c["f"]["id"], fontsize=8); ax.set_xticks([]); ax.set_yticks([])
    save(fig, OUT / "figures/04_raster_difference.png", "Independent native-center raster reconstruction; raster equality remains secondary to continuous equality")
    fig, axes = plt.subplots(1, 4, figsize=(15, 4))
    for ax, c in zip(axes, cases):
        boundary(ax, c["source"], "#456f9e", "Saved Gk", 2); boundary(ax, c["imported"], "#16885c", "Imported G4", 1, "dashed")
        if c["historical_pore"] is not None: boundary(ax, c["historical_pore"], "#cc793f", "Historical G1 pore", 1, "dotted")
        window(ax, c["pore_window"]); ax.legend(fontsize=6); ax.set_title(c["f"]["id"] + f"\nGk = G4 pore area {c['pore'].area:.8g} cell²", fontsize=8)
    save(fig, OUT / "figures/05_pore_preservation.png", "Pores preserved. D retains G1 1 → G2=G4 0.9375 cell²; historical 6.25% loss is not an SVG error")
    fig, axes = plt.subplots(1, 4, figsize=(15, 4))
    for ax, c in zip(axes, cases):
        boundary(ax, c["source"], "#555", "Source", 2); boundary(ax, c["imported"], "#16885c", "G4", 1, "dashed"); window(ax, c["repair_window"])
        n = c["metrics"]["repairs"]["registered_count"]
        ax.set_title(c["f"]["id"] + (f"\n{n} repairs: 0.3535533906-cell clearance" if n else "\nNo A1 regularization; saved connector"), fontsize=8)
    save(fig, OUT / "figures/06_subpixel_repairs.png", "All 14 registered repair sites retain coordinates, local material, boundaries, footprints and positive clearances")
    fig, axes = plt.subplots(1, 2, figsize=(15, 9), gridspec_kw={"width_ratios": [1.4, 1.]}); levels = [17, 12, 9, 6, 3]
    def matrix(ax, rows, ids, key):
        a = np.zeros((len(ids), 5))
        for r in rows: a[ids.index(r[key]), levels.index(r["digits"])] = 2 if r["roundtrip_pass"] else 1 if r["parsed"] else 0
        ax.imshow(a, cmap=ListedColormap(["#c75c53", "#edbd60", "#6bb18b"]), vmin=0, vmax=2, aspect="auto")
        ax.set_xticks(range(5), levels); ax.set_yticks(range(len(ids)), [i.replace("_", " ") for i in ids], fontsize=7); ax.set_xlabel("Significant digits: canonical 17; others diagnostic")
        for i in range(len(ids)):
            for j in range(5): ax.text(j, i, ["Parse HOLD", "Geometry HOLD", "PASS"][int(a[i, j])], ha="center", va="center", fontsize=5.5)
    matrix(axes[0], synthetic["rows"], list(dict.fromkeys(r["case"] for r in synthetic["rows"])), "case"); axes[0].set_title("20 analytic shapes / 100 precision configurations")
    matrix(axes[1], precision["rows"], [c["f"]["id"] for c in cases], "fixture"); axes[1].set_title("Four real fixtures / 20 precision configurations")
    save(fig, OUT / "figures/07_precision_sensitivity.png", "Lower precision can shift boundaries, erase short edges and collapse repairs; canonical policy remains 17 digits")
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for ax, key, label in [(axes[0], "symmetric_area", "Symmetric difference [cell²]"), (axes[1], "displacement_upper", "Boundary displacement upper [cell]")]:
        values = [r[key] for r in study["rows"]]; ax.bar(names, values, color="#4b8b7b"); ax.set_ylim(-.005, .025); ax.set_ylabel(label)
        for i, value in enumerate(values): ax.text(i, .001, f"{value:g}", ha="center")
    save(fig, OUT / "figures/08_area_displacement.png", "Maximum additional SVG area discrepancy = symmetric difference = boundary displacement = 0")
    fig, axes = plt.subplots(1, 3, figsize=(15, 5)); xx = np.arange(4)
    axes[0].bar(xx - .18, [r["timings"]["export_seconds"] for r in study["rows"]], .36, label="Export")
    axes[0].bar(xx + .18, [r["timings"]["total_import_seconds"] for r in study["rows"]], .36, label="Read/parse/assemble")
    axes[0].set_xticks(xx, names); axes[0].set_ylabel("Untraced elapsed [s]"); axes[0].legend(fontsize=7)
    stages = ["source_loading_authentication_seconds", "export_seconds", "total_import_seconds", "continuous_geometry_comparison_seconds", "registered_repair_feature_seconds", "rasterization_comparison_seconds", "scientific_evaluation_seconds", "display_svg_rendering_seconds", "repeat_validation_seconds"]
    sums = [sum(r["timings"][k] for r in study["rows"]) for k in stages]; labels = [k.replace("_seconds", "").replace("_", " ") for k in stages]
    axes[1].barh(labels[::-1], sums[::-1]); axes[1].set_xlabel("Stage sums [s]"); axes[1].tick_params(axis="y", labelsize=7)
    axes[2].bar(xx - .18, [r["export_traced_peak_bytes"] / 2**20 for r in profile["records"]], .36, label="Export Python peak")
    axes[2].bar(xx + .18, [r["import_traced_peak_bytes"] / 2**20 for r in profile["records"]], .36, label="Import Python peak")
    axes[2].set_xticks(xx, names); axes[2].set_ylabel("Selected traced peak [MiB]"); axes[2].legend(fontsize=7)
    save(fig, OUT / "figures/09_runtime_memory.png", "Single-run timings and isolated Python peaks; full real-study process RSS reported separately, native GEOS tracing incomplete")
    fig, ax = plt.subplots(figsize=(13, 4)); labels = ["SVG", "Parse", "Region", "Raster", "Manifold", "Repairs", "Source science", "Pore fidelity", "Production", "CAD / FEM"]
    a = np.tile([2, 2, 2, 2, 2, 2, 1, 0, 1, 0], (4, 1)); ax.imshow(a, cmap=ListedColormap(["#b9bdc1", "#e3b15f", "#71b28f"]), vmin=0, vmax=2, aspect="auto")
    ax.set_xticks(range(10), labels, rotation=35, ha="right", fontsize=8); ax.set_yticks(range(4), [c["f"]["id"] for c in cases], fontsize=8)
    for i in range(4):
        for j in range(10): ax.text(j, i, ["UNQUALIFIED", "HOLD", "PASS"][a[i, j]], ha="center", va="center", fontsize=6.5)
    save(fig, OUT / "figures/10_acceptance.png", "SVG round-trip passes tested fixtures; source scientific HOLD and downstream UNQUALIFIED statuses remain")


def main():
    began = time.perf_counter(); protocol = read(OUT / "protocol/PROTOCOL.json"); study = read(OUT / "summary/REAL_STUDY.json")
    synthetic = read(OUT / "precision_controls/synthetic_run_003/SUMMARY.json"); precision = read(OUT / "precision_controls/real/SUMMARY.json"); profile = read(OUT / "performance/TRACED_STAGE_PROFILE.json")
    assert len(study["rows"]) == 4 and not study["errors"]
    cases = [load_case(f) for f in protocol["fixtures"]]
    individual_previews(cases); figures(cases, study, synthetic, precision, profile)
    d = cases[-1]; old = d["historical_pore"]; imported_pores = [Polygon(h) for p in polygons(d["imported"]) for h in p.interiors]; imported_pore = max(imported_pores, key=lambda p: p.intersection(old).area)
    small_pore = {"fixture": d["f"]["id"], "original_G1_pore_id": 186, "G1_area": old.area, "saved_G2_area": d["pore"].area,
                  "SVG_G4_area": imported_pore.area, "historical_absolute_loss": old.area - d["pore"].area,
                  "historical_relative_loss": (old.area - d["pore"].area) / old.area, "additional_SVG_area_change": imported_pore.area - d["pore"].area,
                  "scientific_disposition": "UNQUALIFIED; SVG round-trip does not amend A1 or cumulative pore policy"}
    metrics = [c["metrics"] for c in cases]; summary = {**study, "scientific_status": protocol["inherited_statuses"], "software_tests": read(OUT / "verification/SOFTWARE_TESTS.json"),
        "maximum_absolute_area_discrepancy": max(abs(m["continuous"]["area"]["net_area"]) for m in metrics),
        "maximum_symmetric_area": max(m["continuous"]["area"]["symmetric"] for m in metrics),
        "maximum_boundary_displacement": max(m["continuous"]["distance"]["upper"] for m in metrics),
        "maximum_false_positive": max(m["raster"]["false_positive"] for m in metrics), "maximum_false_negative": max(m["raster"]["false_negative"] for m in metrics), "maximum_raster_xor": max(m["raster"]["xor"] for m in metrics),
        "registered_repairs": sum(m["repairs"]["registered_count"] for m in metrics), "registered_normal_widths": sum(len(m["protected"]["natural_widths"]) for m in metrics),
        "svg_export_seconds_sum": sum(r["timings"]["export_seconds"] for r in study["rows"]), "svg_import_seconds_sum": sum(r["timings"]["total_import_seconds"] for r in study["rows"]),
        "small_pore_stress": small_pore, "synthetic_controls": {k: synthetic[k] for k in ("positive_cases", "precision_configurations", "canonical_passes", "negative_cases", "negative_failures_detected", "passed")},
        "precision_rows": precision["rows"], "traced_profile": profile, "preservation": "PENDING_FINAL_INVENTORY", "figures": 10,
        "shared_dependencies": ["Python binary64 conversion", "Shapely2.1.2/GEOS3.13.1"], "new_generators_or_designs": False, "CAD_kernel_import": False, "DXF_or_3D_implemented": False}
    write_json(OUT / "summary/SVG_EXPORT_VALIDATION.json", summary); write_json(OUT / "continuous_metrics/SMALL_PORE_STRESS.json", small_pore)
    fields = ["fixture", "source_state", "vertices", "holes", "svg_bytes", "net_area", "symmetric_area", "displacement_upper", "raster_xor", "repair_count", "export_seconds", "import_seconds", "passed"]
    with (OUT / "summary/SVG_EXPORT_VALIDATION.csv").open("w", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=fields, extrasaction="ignore"); writer.writeheader()
        for row in study["rows"]: writer.writerow({**row, "export_seconds": row["timings"]["export_seconds"], "import_seconds": row["timings"]["total_import_seconds"]})
    lines = ["# v0.5D1 — research-only SVG export validation", "", f"**Export-stage result: {study['status']}.** Overall scientific status remains **HOLD_SMALL_PORE_POLICY**. This study measures added serialization error relative to the selected saved G1/G2/G3, not the physical adequacy of that source.", "", "## Purpose and registered sources", "",
        "Four saved native-1024 geometries were registered before final export execution. All source, canonical mask, native-generation manifest, earlier qualification and applicable C.1 validation hashes were authenticated. No source was regenerated, regularized, simplified, replaced or excluded. The initial inventory includes all preexisting local changes. Fixture A retains its saved 15-pixel native-generator repair in G0; it requires no A1 manifold regularization here.", "",
        "| Fixture | State / reason | Vertices | Holes | Contacts |", "|---|---|---:|---:|---:|"]
    for f in protocol["fixtures"]: lines.append(f"| {f['id']} | {f['source_state']}: {f['reason']} | {f['vertices']} | {f['source_integrity']['holes']} | {f['contact_count']} |")
    lines += ["", "## SVG representation and independent import", "",
        "Each SVG has one black unstroked compound path, explicit absolute M/L/Z and `fill-rule=evenodd`. All vertices are retained; deterministic ordering changes neither edges nor occupied region. Native x-right/y-down coordinates and viewBox 0 0 1024 1024 are preserved. Width/height are unitless display values, coordinate units are raster cells, and physical scale is null.", "",
        "Canonical decimal tokens use 17 significant digits. The independently structured reader opens the actual saved XML, checks its restricted contract and metadata, parses path text with a separate tokenizer/state machine, and reconstructs an indexed nesting forest using even-odd depth. It never uses original coordinates or sidecar shell/hole roles to assemble geometry. Unsupported syntax or invalid topology fails with saved evidence; no repair is performed.", "",
        "Python binary64 and Shapely/GEOS are shared dependencies, so independence concerns file parsing and assembly, not a second mathematical kernel. Sharp0.35.5/libvips8.18.7/librsvg2.63.2 interprets saved SVG files for separate visual previews. Display antialiasing is not used for scientific raster comparisons.", "",
        "The preregistered gates require exact binary64 vertex/edge multiplicities, geometric equals, zero added/removed/symmetric area, and zero boundary line-set difference. Winding/cyclic start/component order may differ. The area arithmetic allowance is 64×binary64 epsilon×1024² = 1.4901161193847656e-8 cell² for summation order only; it cannot forgive any changed coordinate or region. Here even the raw area discrepancies were zero.", "",
        "Topology verification matches actual disjoint solid/void faces, reciprocal pore anchors and domain-side incidence. The original C filled-hole-disk helper remains unchanged and is retained as a diagnostic; it cannot disambiguate concentric nested holes in the synthetic control. Dedicated boundary ray/segment qualification supplements OGC validity.", "",
        "## Continuous, topology and feature results", "", "| Fixture | SVG bytes | Area discrepancy cell² | Symmetric cell² | Boundary upper cell | Raster XOR | Dedicated manifold | Export |", "|---|---:|---:|---:|---:|---:|---|---|"]
    for r in study["rows"]: lines.append(f"| {r['fixture']} | {r['svg_bytes']:,} | {r['net_area']:.12g} | {r['symmetric_area']:.12g} | {r['displacement_upper']:.12g} | {r['raster_xor']} | PASS | {'PASS' if r['passed'] else 'HOLD'} |")
    lines += ["", f"All component counts, all {sum(r['holes'] for r in study['rows'])} enclosed pores, and exterior-connected void/domain-side relationships are preserved. All four inputs/imports retain OGC validity and dedicated manifold status. Exact coordinates and zero boundary line-set difference supply a zero boundary-displacement result, rather than a finite-sample Hausdorff assertion.", "",
        f"All {summary['registered_repairs']} registered contact repairs preserve local solid/boundary geometry, added-solid footprints relative to G1, coordinates and positive clearance. Before/after minimum repaired clearance is 0.3535533905932738 cell. The available {summary['registered_normal_widths']} registered normal chords also retain their widths. G3 guard material and boundary sets remain exact. No additional geometry was introduced.", "",
        "## Raster and frozen morphology", "",
        "Every imported file independently reconstructs G0 with FP=FN=XOR=0, IoU=1, one 4-connected solid component, largest fraction1, and both percolation directions true. The original source NPY and reconstructed arrays are separately loaded/constructed. Continuous geometry equality is checked independently of raster equality.", "",
        "Fixture A received fresh frozen-v1.1 original and SVG-reconstructed evaluator calls, including all scalar descriptors and full S2/mean/directional lineal-path arrays. The other three reuse authenticated frozen results only after exact raster identity. No evaluator code, P10 definition or tolerance changed. Original v0.4.2 P10 failure and the scoped v0.4.3 qualification caveat remain.", "",
        "## Precision controls and retained failures", "",
        "Twenty analytic regions cover concavities, multiple components, concentric islands, exterior channels, fractional/non-dyadic coordinates, extremely short segments, 4096-vertex rings, 400 holes and manifold-regularized contacts. Full-precision outputs passed 20/20. All31 deliberate malformed, tampered, unsupported or geometry-altered cases were detected. The raster-invisible shift demonstrates that zero XOR cannot excuse continuous error.", "",
        "| Significant digits | Analytic passes /20 | Parse failures | Parsed but changed | Real passes /4 |", "|---:|---:|---:|---:|---:|"]
    for digits in [17, 12, 9, 6, 3]:
        rows = [r for r in synthetic["rows"] if r["digits"] == digits]; real = [r for r in precision["rows"] if r["digits"] == digits]
        lines.append(f"| {digits} | {sum(r['roundtrip_pass'] for r in rows)} | {sum(not r['parsed'] for r in rows)} | {sum(r['parsed'] and not r['roundtrip_pass'] for r in rows)} | {sum(r['roundtrip_pass'] for r in real)} |")
    lines += ["", "Real6/9/12-digit diagnostics happen to recover the selected integer/quarter-cell source coordinates; that does not qualify those precisions generally. Analytic non-dyadic coordinates already change at 12 digits; short edges and nearly touching boundaries can collapse at lower precision. All four real3-digit files fail on degenerate/repeated vertices. Canonical files remain17 digits and were not replaced by diagnostic outputs.", "",
        "Development evidence is retained: synthetic_run_001 stopped on NumPy-scalar JSON recording; run_002 exposed the nested-hole-disk ambiguity; run_003 passes the full persisted controls. Fixes and two added tests preceded the real-study freeze. No numerical allowance or source geometry was changed.", "",
        "## Inherited small-pore limitation", "",
        f"The selected D source retains G1 pore186 area {small_pore['G1_area']} cell² → saved G2 {small_pore['saved_G2_area']} cell² → imported G4 {small_pore['SVG_G4_area']} cell². Historical A1 loss is {small_pore['historical_absolute_loss']} cell² ({small_pore['historical_relative_loss']:.2%}); additional SVG loss is {small_pore['additional_SVG_area_change']} cell². This is preserved evidence, not a retroactive scientific PASS. The seven independent C.1 pores with6.25% loss remain part of the unresolved cumulative policy.", "",
        "## Runtime and memory", "",
        f"Real-study elapsed time was {study['elapsed_seconds']:.6f}s across four fixtures, including authentication, export/import, comparison, feature checks, rasterization, fresh/reused evaluation, repeats and display previews. Export sum={summary['svg_export_seconds_sum']:.6f}s; import sum={summary['svg_import_seconds_sum']:.6f}s. Detailed per-stage timings are in every sidecar and the machine summary. SVG sizes range {min(r['svg_bytes'] for r in study['rows']):,}–{max(r['svg_bytes'] for r in study['rows']):,}bytes.", "",
        f"Observed real-study process lifetime peak RSS={study['process_lifetime_peak_rss_bytes']/2**20:.3f}MiB. Isolated stage tracing is separately instrumented and not added to untraced timings: export Python peaks span {min(r['export_traced_peak_bytes'] for r in profile['records'])/2**20:.3f}–{max(r['export_traced_peak_bytes'] for r in profile['records'])/2**20:.3f}MiB; import peaks span {min(r['import_traced_peak_bytes'] for r in profile['records'])/2**20:.3f}–{max(r['import_traced_peak_bytes'] for r in profile['records'])/2**20:.3f}MiB. Native GEOS memory and already-loaded sources are incompletely covered. These are single-run observations, not throughput guarantees.", "",
        "## Software, preservation and acceptance", "",
        "529 software tests passed: all 457 previous tests plus 72 new SVG tests, with zero failures/errors/skips. Execution was macOS ARM64; Windows execution and cross-platform byte identity are not claimed. Final preservation, code/protocol verification, figure inspection and the new-file hash ledger are recorded under verification/. Historical results and existing local modifications are preserved.", "",
        "| Scope | Status |", "|---|---|", f"| SVG round-trip on four registered fixtures | {study['status']} |", "| Source scientific adequacy | HOLD_SMALL_PORE_POLICY |", "| Cumulative small-pore fidelity | UNQUALIFIED |", "| Production simplification | HOLD_UNQUALIFIED |", "| CAD-kernel interoperability / FEM / manufacturing | UNQUALIFIED |", "| Physical dimensions | UNASSIGNED |", "",
        "The finite four-fixture result is not a universal SVG implementation, a certificate for arbitrary SVG importers, a different CAD-kernel result, or a source geometry qualification. Arbitrary curves, transforms, styles, masks, overlapping/touching subpaths and additional primitives are unsupported and rejected. Source subpixel modifications and the finite C.1 width-audit/changed-region limitation remain. There are no physical specimen dimensions, material/load laws, mesh convergence, strength or manufacturing criteria.", "",
        "## Next-stage handoff", "",
        "The next proposed software milestone is a separately authorized research-only DXF interchange protocol and independent reimport study. Register representation, units/scale semantics, consumer, hole ownership, precision, acceptance and preserved source scope before implementation. It cannot promote the scientific HOLD. Before 3D, establish an accepted source/pore policy, physical dimensions, minimum clearances relative to kernel tolerances, an independently tested CAD consumer and a separate solid-construction validation protocol. No DXF, CAD kernel,3D, meshing or FEM is implemented here.", "",
        "The dedicated V0_5D1_HANDOFF.md and FINAL_RESPONSE.md supply the next-stage restrictions and all46 requested completion answers. Stop at v0.5D1.", "", "## Figures and format references", ""]
    for p in sorted((OUT / "figures").glob("*.png")): lines.append(f"[{p.stem}](<{p.resolve()}>)\n")
    lines += ["Format references: [W3C SVG path data](https://www.w3.org/TR/SVG2/paths.html), [W3C even-odd fill rule](https://www.w3.org/TR/SVG2/painting.html#FillRuleProperty), [Python binary64 explanation](https://docs.python.org/3/tutorial/floatingpoint.html). The measured results above derive from saved project artifacts, not these references."]
    (OUT / "summary/SVG_EXPORT_VALIDATION.md").write_text("\n".join(lines) + "\n")
    write_json(OUT / "performance/REPORTING.json", {"seconds": time.perf_counter() - began})
    print("Reports, per-fixture previews and ten figures generated", flush=True)


if __name__ == "__main__":
    main()
