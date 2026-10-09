"""Convergence diagnostics and scientific reporting without redefining metrics."""
from pathlib import Path
import csv
import itertools

import numpy as np
from scipy.stats import spearmanr

from .config import default_evaluator_path
from .evaluator import load_evaluator
from .resolution import block_reduce
from .state import write_json

DIMENSIONS = ("mean_strut_thickness", "p10_strut_thickness", "median_pore_diameter")
TARGETS = {"phi_s_absolute": .005, "mean_strut_relative": .05, "p10_strut_relative": .10,
           "pore_relative": .05, "S2_nrmse": .05, "L_nrmse": .05}


def relative_difference(new, old):
    return None if new is None or old is None or old == 0 else abs(new - old) / abs(old)


def compare_pair(run, low, high, evaluator):
    result = {"design_id": low["design_id"], "seed": low["seed"],
              "low_resolution": low["resolution"], "high_resolution": high["resolution"],
              "available": low["status"] == high["status"] == "COMPLETE"}
    if not result["available"]:
        return {**result, "targets_pass": False, "reason": "At least one matched generation failed; retained, not skipped."}
    a, b = low["evaluation"], high["evaluation"]
    errors = {"phi_s_absolute": abs(a["raw"]["phi_s"] - b["raw"]["phi_s"]),
              "mean_strut_relative": relative_difference(b["normalized"]["normalized_mean_strut_thickness"], a["normalized"]["normalized_mean_strut_thickness"]),
              "p10_strut_relative": relative_difference(b["normalized"]["normalized_p10_strut_thickness"], a["normalized"]["normalized_p10_strut_thickness"]),
              "pore_relative": relative_difference(b["normalized"]["normalized_median_pore_diameter"], a["normalized"]["normalized_median_pore_diameter"]),
              "S2_nrmse": evaluator.normalized_rmse(np.array(b["common_curves"]["s2"]), np.array(a["common_curves"]["s2"])),
              "L_nrmse": evaluator.normalized_rmse(np.array(b["common_curves"]["lineal_path"]), np.array(a["common_curves"]["lineal_path"]))}
    result["errors"] = errors
    result["target_checks"] = {k: v is not None and np.isfinite(v) and v <= TARGETS[k] for k, v in errors.items()}
    result["targets_pass"] = all(result["target_checks"].values())
    try:
        aa = block_reduce(np.load(run / low["relative_directory"] / "microstructure.npy"))
        bb = block_reduce(np.load(run / high["relative_directory"] / "microstructure.npy"))
        intersection, union = np.logical_and(aa, bb).sum(), np.logical_or(aa, bb).sum()
        ssim, ncc = evaluator.similarity_metrics(bb, aa)
        result["secondary_correspondence"] = {"binary_iou": float(intersection / union) if union else 1.,
                                               "pixel_disagreement": float(np.mean(aa != bb)), "ssim": ssim, "ncc": ncc,
                                               "method": "both images block-area reduced to 256, majority >=0.5; no alignment"}
    except ValueError as error:
        result["secondary_correspondence"] = {"unavailable": str(error)}
    return result


def control_trends(jobs):
    pairs = (("solid_fraction_target", "phi_s"), ("strut_scale", "normalized_mean_strut_thickness"),
             ("pore_scale", "normalized_median_pore_diameter"))
    result = {}
    for n in sorted({j["resolution"] for j in jobs}):
        selected = [j for j in jobs if j["resolution"] == n]
        trends = {}
        for control, metric in pairs:
            x, y = [], []
            for design in sorted({j["design_id"] for j in selected}):
                group = [j for j in selected if j["design_id"] == design]
                if not all(j["status"] == "COMPLETE" for j in group):
                    continue
                measured = [j["evaluation"]["raw" if metric == "phi_s" else "normalized"][metric] for j in group]
                if any(v is None for v in measured):
                    continue
                x.append(group[0]["requested"][control]); y.append(float(np.mean(measured)))
            rho = float(spearmanr(x, y).statistic) if len(y) >= 3 and np.ptp(y) > 0 else None
            trends[control] = {"metric": metric, "spearman_design_means": rho, "complete_design_count": len(y),
                               "requested": x, "measured_design_mean": y}
        result[str(n)] = trends
    return result


def build_report(run, manifest, selected):
    run = Path(run)
    directory = run / "summary"
    directory.mkdir(exist_ok=True)
    evaluator = load_evaluator(str(default_evaluator_path()))
    jobs = manifest["jobs"]
    comparisons = []
    for key in sorted({(j["design_id"], j["seed"]) for j in jobs}):
        group = sorted([j for j in jobs if (j["design_id"], j["seed"]) == key], key=lambda j: j["resolution"])
        comparisons.extend(compare_pair(run, a, b, evaluator) for a, b in itertools.combinations(group, 2))
    completed = [j for j in jobs if j["status"] == "COMPLETE"]
    main = [c for c in comparisons if c["low_resolution"] == 256 and c["high_resolution"] == 1024]
    summary = {"pipeline_version": "0.4.0", "source_run": manifest["source_run"],
               "source_v03_sha256": manifest["source_v03_sha256"],
               "native_generator_sha256": manifest["native_generator_sha256"],
               "resolutions": manifest["resolutions"], "selected_designs": selected,
               "expected_outputs": len(jobs), "successful_outputs": len(completed),
               "topology_valid_count": sum(j.get("topology_valid", False) for j in jobs),
               "historical_unchanged": manifest["historical_unchanged"],
               "regressions": [{"design_id": j["design_id"], "seed": j["seed"], **j.get("regression", {})}
                               for j in jobs if j["resolution"] == 256],
               "provisional_targets": TARGETS, "comparisons": comparisons,
               "control_trends": control_trends(jobs), "runtime": {},
               "all_256_to_1024_targets_pass": bool(main) and all(c["targets_pass"] for c in main),
               "rows": jobs,
               "curve_method": "Full native evaluator curves interpolated onto rho=0:1/256:0.25; NRMSE denominator is lower-resolution curve RMS.",
               "limitations": ["v0.3 thickness uses discrete EDT and skeletonization; normalized estimates are quantized, especially P10.",
                               "Native two-sided interface footprint and lattice EDT are approximate continuations of v0.3 raster rules.",
                               "Continuous latent fields retain v0.3's 256-grid bandwidth; higher N adds boundary samples, not new random features.",
                               "Four-direction digital lineal paths retain evaluator v1.1 conventions, including equal step indices for diagonal paths.",
                               "LHS controls are coupled; small-sample rank trends are associations, not isolated causal effects.",
                               "Timing includes baseline candidate selection and tracemalloc instrumentation, excludes process startup and repeatability check.",
                               "No CAD, vectorization, STEP, STL, extrusion, FEM, ANSYS or mesh has been produced."]}
    baseline_ok = len(summary["regressions"]) == len(selected["samples"]) and all(
        r.get("old_generator_bitwise_equal") and r.get("saved_output_bitwise_equal") for r in summary["regressions"])
    summary["baseline_bitwise_preserved"] = baseline_ok
    summary["ready_for_v05"] = bool(summary["all_256_to_1024_targets_pass"] and baseline_ok and
                                     len(completed) == len(jobs) and manifest["historical_unchanged"])
    summary["conclusion"] = ("Provisional numeric gates passed; manual geometry review remains necessary before v0.5."
                              if summary["ready_for_v05"] else
                              "Native generation is implemented, but v0.5 readiness is NOT established. Review failed convergence gates and remaining discretization effects; no morphology was retuned to force acceptance.")
    for n in sorted(manifest["resolutions"]):
        records = [j for j in completed if j["resolution"] == n]
        summary["runtime"][str(n)] = {"count": len(records), **{name: float(np.mean([j[name] for j in records])) if records else None
            for name in ("generation_seconds", "evaluation_seconds", "peak_traced_generation_bytes")},
            "mean_output_bytes": float(np.mean([sum(f["bytes"] for f in j["files"].values()) for j in records])) if records else None}
    # Diversity/copy diagnostics reuse frozen evaluator on a common 256 grid,
    # not novel resolution-specific definitions. These are secondary checks.
    summary["secondary_diversity"] = {}
    for n in sorted(manifest["resolutions"]):
        arrays = []
        if n % 256:
            continue
        for j in completed:
            if j["resolution"] == n:
                arrays.append(block_reduce(np.load(run / j["relative_directory"] / "microstructure.npy")))
        if arrays:
            _, mean = evaluator.pairwise_disagreement(np.array(arrays))
            summary["secondary_diversity"][str(n)] = {"common_grid_mean_pairwise_disagreement": mean}
    write_json(directory / "resolution_convergence.json", evaluator.json_safe(summary))
    fields = ["design_id", "seed", "resolution", "status", "phi_s", "component_count", "Px", "Py", *DIMENSIONS,
              *("normalized_"+k for k in DIMENSIONS), "generation_seconds", "evaluation_seconds", "peak_traced_generation_bytes", "error"]
    with (directory / "resolution_convergence.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for j in jobs:
            row = {k: j.get(k) for k in fields}
            row.update({k: j.get("evaluation", {}).get("raw", {}).get(k) for k in ("phi_s", "component_count", "Px", "Py", *DIMENSIONS)})
            row.update(j.get("evaluation", {}).get("normalized", {})); writer.writerow(row)
    write_markdown(directory, summary)
    make_figures(run, directory / "figures", jobs, summary)
    return summary


def fmt(value):
    return "N/A" if value is None else f"{value:.6g}" if isinstance(value, (float, np.floating)) else str(value)


def write_markdown(directory, report):
    rows = report["rows"]
    lines = ["# Pipeline v0.4 Resolution Validation", "", "## Generator", "",
             f"Source: `{report['source_run']}/generator.py`", "",
             f"v0.3 SHA-256: `{report['source_v03_sha256']}`", "",
             f"v0.4 SHA-256: `{report['native_generator_sha256']}`", "",
             "## Resolutions", "", str(report["resolutions"]), "", "## Representative Designs", "",
             "| Design | Solid fraction target | Strut scale | Pore scale | Selection |", "|---|---:|---:|---:|---|"]
    selected = report["selected_designs"]
    for design in selected["design_ids"]:
        row = next(r for r in selected["samples"] if r["design_id"] == design)
        p = row["requested"]
        lines.append(f"| {design} | {p['solid_fraction_target']:.6f} | {p['strut_scale']:.6f} | {p['pore_scale']:.6f} | {selected['selection_reasons'][str(design)]} |")
    lines += ["", "## Topology", "", "| Design | Seed | N | Components | Px | Py | Status |", "|---|---:|---:|---:|---:|---:|---|"]
    for j in rows:
        m = j.get("evaluation", {}).get("raw", {})
        lines.append(f"| {j['design_id']} | {j['seed']} | {j['resolution']} | {fmt(m.get('component_count'))} | {fmt(m.get('Px'))} | {fmt(m.get('Py'))} | {j['status']} |")
    lines += ["", "## Morphological Convergence", "", "| Design | Seed | N | phi_s | mean t/N | p10 t/N | median pore/N |", "|---|---:|---:|---:|---:|---:|---:|"]
    for j in rows:
        m = j.get("evaluation", {})
        values = [m.get("raw", {}).get("phi_s"), *[m.get("normalized", {}).get("normalized_"+k) for k in DIMENSIONS]]
        lines.append(f"| {j['design_id']} | {j['seed']} | {j['resolution']} | " + " | ".join(map(fmt, values)) + " |")
    lines += ["", "## Cross-Resolution Error", "", report["curve_method"], "",
              "| Design | Seed | 256→512 S2 | 256→1024 S2 | 256→512 L | 256→1024 L |", "|---|---:|---:|---:|---:|---:|"]
    for design, seed in sorted({(j["design_id"], j["seed"]) for j in rows}):
        cc = {c["high_resolution"]: c for c in report["comparisons"] if c["design_id"] == design and c["seed"] == seed and c["low_resolution"] == 256}
        values = [cc.get(n, {}).get("errors", {}).get(k) for k, n in (("S2_nrmse",512),("S2_nrmse",1024),("L_nrmse",512),("L_nrmse",1024))]
        lines.append(f"| {design} | {seed} | " + " | ".join(map(fmt, values)) + " |")
    lines += ["", "### Provisional target checks: 256→1024", "", "| Metric | Limit | Passing pairs | Worst error |", "|---|---:|---:|---:|"]
    main = [c for c in report["comparisons"] if c["low_resolution"] == 256 and c["high_resolution"] == 1024]
    for key, limit in TARGETS.items():
        values = [c["errors"][key] for c in main if c.get("errors", {}).get(key) is not None]
        passed = sum(c.get("target_checks", {}).get(key, False) for c in main)
        lines.append(f"| {key} | {limit} | {passed}/{len(main)} | {fmt(max(values) if values else None)} |")
    lines += ["", "512→1024 errors and block-reduced IoU, disagreement, SSIM and NCC are retained in the JSON.", "",
              "## Parametric-Control Preservation", "", "Spearman associations of design means; not independent causal tests.", "",
              "| N | Density control | Strut control | Pore control |", "|---|---:|---:|---:|"]
    for n, trends in report["control_trends"].items():
        lines.append(f"| {n} | " + " | ".join(fmt(v["spearman_design_means"]) for v in trends.values()) + " |")
    lines += ["", "## Runtime", "", "| N | Mean generation s | Mean evaluation s | Mean PNG+NPY bytes | Mean peak traced bytes |", "|---|---:|---:|---:|---:|"]
    for n, values in report["runtime"].items():
        lines.append(f"| {n} | " + " | ".join(fmt(values[k]) for k in ("generation_seconds", "evaluation_seconds", "mean_output_bytes", "peak_traced_generation_bytes")) + " |")
    lines += ["", "## Regression Against v0.3", "",
              f"All selected 256 outputs equal old generator AND saved historical arrays: **{report['baseline_bitwise_preserved']}**.", "",
              f"Historical source inventory unchanged: **{report['historical_unchanged']}**.", "",
              "## Limitations and diagnosis", "", *["- " + s for s in report["limitations"]], "",
              "Mean-width drift can combine digital skeleton/EDT bias with changes in the native interface footprint. "
              "The current experiment does not isolate those contributions. P10 often quantizes to only a few pixels at 256. "
              "Do not reinterpret missed thresholds as passes or add morphology corrections to hide them.", "",
              "## Conclusions", "", report["conclusion"], "",
              "## Failures", ""]
    failures = [j for j in rows if j["status"] != "COMPLETE"]
    lines += [f"- Design {j['design_id']}, seed {j['seed']}, N={j['resolution']}: {j.get('error', 'See job manifest')}" for j in failures] or ["None."]
    (directory / "resolution_convergence.md").write_bytes(("\n".join(lines)+"\n").encode())


def make_figures(run, directory, jobs, report):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    directory.mkdir(exist_ok=True)
    valid = [j for j in jobs if j["status"] == "COMPLETE"]
    matched = sorted({(j["design_id"], j["seed"]) for j in jobs})
    resolutions = sorted({j["resolution"] for j in jobs})
    for design, seed in matched:
        group = {j["resolution"]: j for j in jobs if j["design_id"] == design and j["seed"] == seed}
        fig, axes = plt.subplots(2, len(resolutions), figsize=(4*len(resolutions), 8), squeeze=False)
        for col, n in enumerate(resolutions):
            for ax in axes[:, col]: ax.axis("off")
            j = group[n]
            if j["status"] != "COMPLETE":
                axes[0,col].set_title(f"{n}: FAILED"); continue
            array = np.load(run / j["relative_directory"] / "microstructure.npy")
            crop = array[int(n*.375):int(n*.625), int(n*.375):int(n*.625)]
            Image.fromarray(crop*255).save(directory / f"design_{design:03d}_seed_{seed:03d}_{n}_crop.png")
            axes[0,col].imshow(array, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
            axes[1,col].imshow(crop, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
            axes[0,col].set_title(f"N = {n}"); axes[1,col].set_title("Central 25% × 25% of domain")
        fig.suptitle(f"Matched design {design}, seed {seed}; full image and native crop")
        fig.tight_layout(); fig.savefig(directory / f"design_{design:03d}_seed_{seed:03d}_montage.png", dpi=150); plt.close(fig)
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for n, j in sorted(group.items()):
            if j["status"] != "COMPLETE": continue
            for ax, curve in zip(axes, ("s2", "lineal_path")):
                ax.plot(j["evaluation"]["common_rho"], j["evaluation"]["common_curves"][curve], label=str(n))
                ax.set(xlabel="Normalized separation rho = r/N", ylabel=curve)
                ax.legend()
        fig.tight_layout(); fig.savefig(directory / f"design_{design:03d}_seed_{seed:03d}_curves.png", dpi=150); plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    for ax, metric in zip(axes.flat, ("phi_s", *("normalized_"+k for k in DIMENSIONS))):
        for design, seed in matched:
            group = sorted([j for j in valid if j["design_id"] == design and j["seed"] == seed], key=lambda j:j["resolution"])
            ax.plot([j["resolution"] for j in group], [j["evaluation"]["raw" if metric == "phi_s" else "normalized"][metric] for j in group], marker="o", label=f"D{design}/S{seed}")
        ax.set(xlabel="Resolution N", ylabel=metric)
    axes[0,0].legend(fontsize=7, ncol=2)
    fig.tight_layout(); fig.savefig(directory / "normalized_metrics.png", dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(14, 4))
    for n, controls in report["control_trends"].items():
        for ax, (control, info) in zip(axes, controls.items()):
            ax.scatter(info["requested"], info["measured_design_mean"], label=n)
            ax.set(xlabel=control, ylabel=info["metric"])
            ax.legend()
    fig.tight_layout(); fig.savefig(directory / "parameter_controls.png", dpi=150); plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    nn = [int(n) for n in report["runtime"]]
    for key in ("generation_seconds", "evaluation_seconds"):
        axes[0].plot(nn, [v[key] for v in report["runtime"].values()], marker="o", label=key)
    axes[0].set(xlabel="Resolution N", ylabel="Mean seconds"); axes[0].legend()
    axes[1].plot(nn, [None if v["peak_traced_generation_bytes"] is None else v["peak_traced_generation_bytes"]/2**20 for v in report["runtime"].values()], marker="o")
    axes[1].set(xlabel="Resolution N", ylabel="Mean generation peak traced MiB")
    fig.tight_layout(); fig.savefig(directory / "runtime_memory.png", dpi=150); plt.close(fig)
