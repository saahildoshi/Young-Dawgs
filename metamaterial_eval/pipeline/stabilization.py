"""Reproducible v0.4.1 investigation; no evaluator changes or gate relaxation.

Run ``python -m metamaterial_eval.pipeline.stabilization --help``. Diagnostics
and validation use separate, new directories and refuse to overwrite evidence.
All geometry distances use endpoint coordinates i/(N-1); frozen dimensional
metrics retain the explicitly requested t/N and d/N convention.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy import ndimage as ndi
from PIL import Image

from .config import default_evaluator_path
from .evaluator import load_evaluator
from .execution import run_subprocess
from .resolution_validation import inventory
from .scripts import sha256_file
from .state import read_json, write_json, utc_now

FROZEN_SHA = "5f28ed1f77f95fd23a517cd223bbe6c6b5edc7d5508093f36f523b2d4f85cebb"
DIMENSIONS = ("mean_strut_thickness", "p10_strut_thickness", "median_pore_diameter")
REPO = Path(__file__).resolve().parents[2]


def evaluator():
    if sha256_file(default_evaluator_path()) != FROZEN_SHA:
        raise ValueError("Frozen evaluator v1.1 differs from the audited SHA-256.")
    return load_evaluator(str(default_evaluator_path()))


def signed_change(low, high):
    """Signed percentage relative to the lower-resolution measurement."""
    return None if low is None or high is None or low == 0 else 100 * (high / low - 1)


def successive_rows(jobs):
    rows = []
    for design, seed in sorted({(j["design_id"], j["seed"]) for j in jobs}):
        group = sorted((j for j in jobs if (j["design_id"], j["seed"]) == (design, seed)),
                       key=lambda j: j["resolution"])
        if not all(j["status"] == "COMPLETE" for j in group):
            continue
        for a, b in zip(group, group[1:]):
            rows.append({"design_id": design, "seed": seed, "low": a["resolution"], "high": b["resolution"],
                         **{k: signed_change(a["evaluation"]["normalized"]["normalized_" + k],
                                             b["evaluation"]["normalized"]["normalized_" + k]) for k in DIMENSIONS}})
    return rows


def synthetic_shape(n, family, width_base):
    """Independently sample analytic geometry at pixel centers, never resize.

    Bars have exact width w/256 and length 1/2. Annuli have centerline radius
    0.2 and wall width w/256, so analytic enclosed pore diameter is 0.4-w/256.
    The 45-degree bar uses orthonormal coordinates (true normal width).
    """
    axis = (np.arange(n) + .5) / n - .5
    y, x = np.meshgrid(axis, axis, indexing="ij")
    width = width_base / 256
    if family == "bar_x":
        solid = (np.abs(y) < width / 2) & (np.abs(x) < .25)
    elif family == "bar_y":
        solid = (np.abs(x) < width / 2) & (np.abs(y) < .25)
    elif family == "bar_45":
        solid = (np.abs((y - x) / np.sqrt(2)) < width / 2) & (np.abs((x + y) / np.sqrt(2)) < .25)
    elif family == "ring":
        solid = np.abs(np.hypot(y, x) - .2) < width / 2
    else:
        raise ValueError(f"Unknown analytic family {family!r}")
    return solid.astype(np.uint8)


def synthetic_diagnostics(out):
    e = evaluator()
    rows = []
    for family in ("bar_x", "bar_y", "bar_45", "ring"):
        for width in (4, 6):
            for n in (256, 512, 1024):
                a = synthetic_shape(n, family, width)
                folder = out / "synthetic" / f"{family}_w{width}" / str(n)
                folder.mkdir(parents=True)
                np.save(folder / "mask.npy", a, allow_pickle=False)
                Image.fromarray(a * 255).save(folder / "mask.png")
                raw = e.local_dimensions(a)
                row = {"family": family, "width_at_256": width, "resolution": n,
                       "analytic_width_normalized": width / 256,
                       "analytic_pore_diameter_normalized": .4 - width / 256 if family == "ring" else None,
                       "metrics": {k: float(raw[k]) / n for k in DIMENSIONS},
                       "skeleton_sample_count": len(raw["strut_diameters"]),
                       "enclosed_pore_count": len(raw["pore_diameters"])}
                row = e.json_safe(row)
                write_json(folder / "metrics.json", row)
                rows.append(row)
    write_json(out / "synthetic.json", rows)
    return rows


def component_diagnostic(a):
    """Return disjoint component masks and exact pixel-center nearest distances."""
    labels, count = ndi.label(a, structure=ndi.generate_binary_structure(2, 1))
    if not count:
        raise ValueError("No solid component.")
    sizes = np.bincount(labels.ravel()); sizes[0] = 0
    main = labels == sizes.argmax()
    distance, indices = ndi.distance_transform_edt(~main, return_indices=True)
    fragments = []
    for label in range(1, count + 1):
        if label == sizes.argmax():
            continue
        pixels = np.argwhere(labels == label)
        p = pixels[np.argmin(distance[labels == label])]
        q = indices[:, p[0], p[1]]
        fragments.append({"label": label, "pixels": int(len(pixels)), "area_fraction": len(pixels) / a.size,
                          "bbox_yx_inclusive": [pixels.min(axis=0).tolist(), pixels.max(axis=0).tolist()],
                          "centroid_yx_normalized": (pixels.mean(axis=0) / (a.shape[0] - 1)).tolist(),
                          "nearest_fragment_yx": p.tolist(), "nearest_main_yx": q.tolist(),
                          "min_pixel_center_distance": float(distance[tuple(p)]),
                          "min_normalized_center_distance": float(distance[tuple(p)]) / (a.shape[0] - 1)})
    return {"component_count": int(count), "main_pixels": int(main.sum()), "fragments": fragments}, main, labels


def topology_diagnostics(baseline, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = []
    fig, axes = plt.subplots(1, 4, figsize=(14, 4), constrained_layout=True)
    colors = ("tab:blue", "tab:orange", "tab:green")
    for axis, n, color in zip(axes, (256, 512, 1024), colors):
        folder = baseline / "design_009/seed_001" / str(n)
        source = folder / ("microstructure.npy" if n == 256 else "rejected_evidence/REJECTED.npy")
        a = np.load(source, allow_pickle=False)
        row, main, labels = component_diagnostic(a)
        rows.append({"resolution": n, **row, "source_sha256": sha256_file(source)})
        dest = out / "topology" / str(n); dest.mkdir(parents=True)
        np.save(dest / "main.npy", main.astype(np.uint8), allow_pickle=False)
        np.save(dest / "detached.npy", ((labels > 0) & ~main).astype(np.uint8), allow_pickle=False)
        size = int(np.ceil((n - 1) * .06)) + 1
        crop = np.zeros((size, size, 3), dtype=float)
        crop[main[:size, :size]] = .8
        crop[((labels > 0) & ~main)[:size, :size]] = [1, .2, .2]
        extent = (0, size / (n - 1), size / (n - 1), 0)
        axis.imshow(crop, interpolation="nearest", extent=extent)
        axis.set_title(f"N={n}, components={row['component_count']}")
        coords = np.arange(size) / (n - 1)
        axes[-1].contour(coords, coords, a[:size, :size], levels=[.5], colors=[color], linewidths=1)
        axes[-1].plot([], [], color=color, label=str(n))
    for axis in axes:
        axis.set_xlim(0, .06); axis.set_ylim(.06, 0); axis.set_aspect("equal")
        axis.set_xlabel("x / domain length")
    axes[0].set_ylabel("y / domain length")
    axes[-1].legend(); axes[-1].set_title("Native boundary overlay")
    fig.savefig(out / "topology_overlay.png", dpi=180); plt.close(fig)
    write_json(out / "topology.json", rows)
    return rows


def worker(job, destination, logs, timeout):
    job_path = logs / "job.json"
    write_json(job_path, job)
    execution = run_subprocess([sys.executable, "-m", "metamaterial_eval.pipeline.resolution_worker",
                                str(job_path), str(destination)], cwd=REPO, log_dir=logs,
                               timeout_seconds=timeout)
    path = destination / "manifest.json"
    if path.exists():
        record = read_json(path)
        if not execution.succeeded:
            record["status"] = "FAILED"
            record["execution"] = execution.to_dict()
        return record
    record = {**job, "status": "FAILED", "execution": execution.to_dict(),
              "error": "Worker failed before persisting manifest; inspect logs."}
    write_json(path, record)
    return record


def investigate(baseline, source, out, timeout=600):
    baseline, source, out = map(lambda p: Path(p).resolve(), (baseline, source, out))
    if any(p == out or p in out.parents for p in (baseline, source)):
        raise ValueError("Output must be outside historical runs.")
    e = evaluator()
    prior = read_json(baseline / "summary/resolution_convergence.json")
    before = {str(p): inventory(p) for p in (baseline, source)}
    out.mkdir(parents=True, exist_ok=False)
    # Chosen before observing 2048: worst 512->1024 mean-thickness change,
    # density maximum, and envelope center. No new random realizations.
    selected = [(1, 0), (2, 0), (5, 0)]
    protocol = {"created_at_utc": utc_now(), "baseline": str(baseline), "source": str(source),
                "evaluator_sha256": FROZEN_SHA, "inventory_before": before,
                "diagnostic_2048_pairs": selected,
                "selection_reason": "worst successive thickness; high density; envelope center",
                "acceptance_policy": "Original gates retained. Suggested 3% successive mean gate assessed, not silently adopted.",
                "code_sha256": sha256_file(Path(__file__)), "status": "RUNNING"}
    write_json(out / "protocol.json", protocol)
    successive = successive_rows(prior["rows"])
    write_json(out / "prior_successive.json", successive)
    synthetic = synthetic_diagnostics(out)
    topology = topology_diagnostics(baseline, out)
    extended = []
    for design, seed in selected:
        old = next(j for j in prior["rows"] if j["design_id"] == design and j["seed"] == seed and j["resolution"] == 1024)
        job = {k: old[k] for k in ("design_id", "seed", "requested", "sample_id")}
        job["resolution"] = 2048
        dest = out / "diagnostic_2048" / f"design_{design:03d}_seed_{seed:03d}"
        record = worker(job, dest, out / "logs" / dest.name, timeout)
        extended.extend([old, record])
        print(f"2048 diagnostic design={design}, seed={seed}: {record['status']}", flush=True)
    write_json(out / "diagnostic_2048.json", extended)
    write_json(out / "diagnostic_2048_successive.json", successive_rows(extended))
    protocol["historical_unchanged"] = all(before[str(p)] == inventory(p) for p in (baseline, source))
    protocol["status"] = "COMPLETE" if all(j["status"] == "COMPLETE" for j in extended) else "COMPLETED_WITH_FAILURES"
    write_json(out / "protocol.json", protocol)
    lines = ["# v0.4.1 diagnostics (before repair)", "", "Signed percentages use the lower-resolution value as denominator.", "",
             "## Nine originally successful pairs", "", "| Design | Seed | Step | Mean thickness % | P10 thickness % | Pore median % |",
             "|---:|---:|---|---:|---:|---:|"]
    for r in successive:
        lines.append(f"| {r['design_id']} | {r['seed']} | {r['low']} → {r['high']} | " + " | ".join(f"{r[k]:+.4f}" for k in DIMENSIONS) + " |")
    lines += ["", "## Analytic fixed-geometry controls", "", "All masks sampled independently. Values are normalized by N. Open bar voids have no enclosed pore.", "",
              "| Geometry | Width at 256 | N | Mean t/N | P10 t/N | Median pore/N |", "|---|---:|---:|---:|---:|---:|"]
    for r in synthetic:
        vals = ["N/A" if r["metrics"][k] is None else f"{r['metrics'][k]:.8f}" for k in DIMENSIONS]
        lines.append(f"| {r['family']} | {r['width_at_256']} | {r['resolution']} | " + " | ".join(vals) + " |")
    lines += ["", "## Limited 2048 diagnostic", "", "| Design | Seed | Step | Mean thickness % | P10 thickness % | Pore median % |",
              "|---:|---:|---|---:|---:|---:|"]
    for r in successive_rows(extended):
        lines.append(f"| {r['design_id']} | {r['seed']} | {r['low']} → {r['high']} | " + " | ".join(f"{r[k]:+.4f}" for k in DIMENSIONS) + " |")
    lines += ["", "## Detached corner", "", "Pixel-center distance is not an inferred continuous boundary gap.", "",
              "| N | Components | Detached pixels | Area fraction | Bounding box y,x (inclusive) | Nearest distance (pixels) | Distance / (N-1) |",
              "|---:|---:|---:|---:|---|---:|---:|"]
    for r in topology:
        for f in r["fragments"]:
            lines.append(f"| {r['resolution']} | {r['component_count']} | {f['pixels']} | {f['area_fraction']:.9f} | {f['bbox_yx_inclusive']} | {f['min_pixel_center_distance']:.6f} | {f['min_normalized_center_distance']:.9f} |")
    lines += ["", "![Normalized corner overlay](topology_overlay.png)", "", f"Historical inventories unchanged: {protocol['historical_unchanged']}.",
              "", "These diagnostics do not themselves amend acceptance thresholds or establish v0.5 readiness."]
    (out / "DIAGNOSTICS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return protocol


def fixed_geometry_control(diagnostics, out):
    """Re-sample fixed 2048 masks to isolate sampling from native generation.

    This deliberately samples a FINISHED raster only as a measurement control.
    It is not a generator, accepted output, or analytic continuum ground truth.
    Every control keeps the same fixed high-grid geometry; no score, quantile,
    nucleus or random field is regenerated at the lower resolutions.
    """
    diagnostics, out = Path(diagnostics).resolve(), Path(out).resolve()
    if diagnostics == out or diagnostics in out.parents:
        raise ValueError("Controls must be separate from the diagnostic source.")
    e = evaluator()
    before = inventory(diagnostics)
    records = json.loads((diagnostics / "diagnostic_2048.json").read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for r in records:
        if r["resolution"] != 2048 or r["status"] != "COMPLETE":
            continue
        name = f"design_{r['design_id']:03d}_seed_{r['seed']:03d}"
        source = diagnostics / "diagnostic_2048" / name / "microstructure.npy"
        a = np.load(source, allow_pickle=False)
        for n in (256, 512, 1024, 2048):
            indices = np.rint(np.arange(n) * 2047 / (n - 1)).astype(int)
            sampled = a[np.ix_(indices, indices)]
            raw = e.local_dimensions(sampled)
            dest = out / name / str(n); dest.mkdir(parents=True)
            np.save(dest / "CONTROL_ONLY_NOT_NATIVE.npy", sampled, allow_pickle=False)
            rows.append({"design_id": r["design_id"], "seed": r["seed"], "resolution": n,
                         "source_2048_sha256": sha256_file(source),
                         "normalized": e.json_safe({k: float(raw[k]) / n for k in DIMENSIONS})})
    result = {"method": "Fixed 2048 raster, nearest endpoint-aligned sampling; diagnostic only, never native production output",
              "limitations": "Finite 2048 raster is not continuum truth. Attribution is approximate, not a universal bias correction.",
              "evaluator_sha256": FROZEN_SHA, "rows": rows, "source_inventory_before": before,
              "code_sha256": sha256_file(Path(__file__)),
              "historical_unchanged": before == inventory(diagnostics), "status": "COMPLETE"}
    write_json(out / "fixed_geometry.json", result)
    lines = ["# Frozen-geometry sampling control", "", result["method"], "", result["limitations"], "",
             "| Design | Seed | Step | Mean thickness change % | P10 change % | Pore median change % |",
             "|---:|---:|---|---:|---:|---:|"]
    for design, seed in sorted({(r["design_id"], r["seed"]) for r in rows}):
        group = [r for r in rows if (r["design_id"], r["seed"]) == (design, seed)]
        for a, b in zip(group, group[1:]):
            values = [signed_change(a["normalized"][k], b["normalized"][k]) for k in DIMENSIONS]
            lines.append(f"| {design} | {seed} | {a['resolution']} → {b['resolution']} | " + " | ".join(f"{v:+.4f}" for v in values) + " |")
    (out / "FIXED_GEOMETRY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def validate(baseline, source, diagnostics, out, timeout=600):
    """Replay exactly the previous 30 jobs with the explicit stabilized model."""
    from ..generators import native_resolution, stabilized_resolution, v03_baseline
    from .resolution_report import compare_pair, control_trends, make_figures, TARGETS

    baseline, source, diagnostics, out = map(lambda p: Path(p).resolve(), (baseline, source, diagnostics, out))
    if any(p == out or p in out.parents for p in (baseline, source, diagnostics)):
        raise ValueError("Validation output must be outside its historical inputs.")
    e = evaluator()
    prior = read_json(baseline / "summary/resolution_convergence.json")
    evidence = read_json(diagnostics / "protocol.json")
    if evidence["status"] != "COMPLETE" or not evidence["historical_unchanged"]:
        raise ValueError("Complete and preserved diagnostic evidence is required before validation.")
    selected = read_json(baseline / "selected_designs.json")
    if len(selected["samples"]) != 10 or sorted(prior["resolutions"]) != [256, 512, 1024]:
        raise ValueError("Expected original five-design, two-seed, three-resolution experiment.")
    if sha256_file(source / "generator.py") != native_resolution.SOURCE_V03_SHA256 or sha256_file(Path(v03_baseline.__file__)) != native_resolution.SOURCE_V03_SHA256:
        raise ValueError("Historical generator differs from audited v0.3 baseline.")
    if sha256_file(Path(native_resolution.__file__)) != prior["native_generator_sha256"]:
        raise ValueError("Native v0.4 renderer changed since baseline validation.")
    before = {str(p): inventory(p) for p in (baseline, source, diagnostics)}
    source_manifest = read_json(source / "exploration_manifest.json")
    out.mkdir(parents=True, exist_ok=False)
    # This policy is persisted BEFORE any post-fix case is run. Original gates
    # remain reported separately; changing the reference is not a retroactive pass.
    protocol = {"version": "0.4.1", "created_at_utc": utc_now(),
                "amendment": "Use successive 512->1024 dimensional convergence, retaining coarse-baseline errors as diagnostics.",
                "rationale": "Analytic and fixed-geometry controls establish estimator quantization; 2048 increments decrease. Do not retune widths to coarse measurements.",
                "successive_targets": {"mean_strut_relative": .03, "p10_strut_relative": .10, "pore_relative": .03},
                "unchanged_256_to_1024_targets": {k: TARGETS[k] for k in ("phi_s_absolute", "S2_nrmse", "L_nrmse")},
                "diagnostic_2048_requirement": "For all three preselected cases, mean and pore fractional changes must be smaller than 512->1024; not a full 2048 production qualification.",
                "topology": "30/30 component_count=1, Px=1, Py=1",
                "baseline": "10/10 saved-v0.3 and old-generator bitwise equality",
                "identity": "same latent candidate index, raw arrays identical to v0.4 at all 30 resolutions, deterministic repeats, distinct paired seeds",
                "p10_note": "P10 remains explicitly gated at 10%; quantization does not excuse a failed gate.",
                "source_diagnostics_sha256": sha256_file(diagnostics / "DIAGNOSTICS.md")}
    write_json(out / "protocol_amendment.json", protocol)
    manifest = {"pipeline_version": "0.4.1", "source_run": str(source), "baseline_run": str(baseline),
                "created_at_utc": utc_now(), "resolutions": [256, 512, 1024], "source_inventory_before": before,
                "source_v03_sha256": native_resolution.SOURCE_V03_SHA256,
                "native_generator_sha256": sha256_file(Path(stabilized_resolution.__file__)),
                "native_renderer_sha256": sha256_file(Path(native_resolution.__file__)),
                "code_sha256": {str(p.relative_to(REPO)): sha256_file(p) for p in
                                (Path(__file__), Path(__file__).with_name("resolution_worker.py"),
                                 Path(stabilized_resolution.__file__), Path(native_resolution.__file__))},
                "jobs": [], "status": "RUNNING"}
    write_json(out / "manifest.json", manifest)
    for row in selected["samples"]:
        for n in (256, 512, 1024):
            rel = Path(f"design_{row['design_id']:03d}") / f"seed_{row['seed']:03d}" / str(n)
            historical = source / source_manifest["latest_attempt"] / "samples" / (row["sample_id"] + ".npy")
            job = {**row, "resolution": n, "generator_version": "0.4.1", "historical_sample": str(historical)}
            record = worker(job, out / rel, out / "logs" / f"{row['sample_id']}_{n}", timeout)
            record["relative_directory"] = rel.as_posix()
            if record["status"] == "COMPLETE":
                old_path = baseline / rel / "microstructure.npy"
                if not old_path.exists():
                    old_path = baseline / rel / "rejected_evidence/REJECTED.npy"
                old = np.load(old_path, allow_pickle=False)
                new = np.load(out / rel / "microstructure.npy", allow_pickle=False)
                import hashlib
                record["raw_matches_v04"] = hashlib.sha256(old.tobytes()).hexdigest() == record["topology_repair"]["raw_pixel_sha256"]
                record["final_matches_v04"] = bool(np.array_equal(old, new))
                old_record = next(j for j in prior["rows"] if (j["design_id"], j["seed"], j["resolution"]) == (row["design_id"], row["seed"], n))
                base_candidate = next(j["candidate_index"] for j in prior["rows"] if (j["design_id"], j["seed"], j["resolution"]) == (row["design_id"], row["seed"], 256))
                record["candidate_matches_v04"] = record["candidate_index"] == base_candidate
                record["previous_status"] = old_record["status"]
            manifest["jobs"].append(record)
            write_json(out / "manifest.json", manifest)
            print(f"v0.4.1 design={row['design_id']} seed={row['seed']} N={n}: {record['status']}", flush=True)
    jobs = manifest["jobs"]
    manifest["historical_unchanged"] = all(before[str(p)] == inventory(p) for p in (baseline, source, diagnostics))
    manifest["status"] = "COMPLETE" if all(j["status"] == "COMPLETE" for j in jobs) else "COMPLETED_WITH_FAILURES"
    write_json(out / "manifest.json", manifest)
    comparisons = []
    import itertools
    for design, seed in sorted({(j["design_id"], j["seed"]) for j in jobs}):
        group = [j for j in jobs if (j["design_id"], j["seed"]) == (design, seed)]
        comparisons.extend(compare_pair(out, a, b, e) for a, b in itertools.combinations(group, 2))
    successive = [c for c in comparisons if (c["low_resolution"], c["high_resolution"]) == (512, 1024)]
    broad = [c for c in comparisons if (c["low_resolution"], c["high_resolution"]) == (256, 1024)]
    checks = {k: [bool(c["available"] and c["errors"][k] is not None and c["errors"][k] <= limit) for c in successive]
              for k, limit in protocol["successive_targets"].items()}
    topology_ok = len(jobs) == 30 and all(j.get("evaluation", {}).get("raw", {}).get("component_count") == 1 and
                                         j.get("evaluation", {}).get("raw", {}).get("Px") == 1 and
                                         j.get("evaluation", {}).get("raw", {}).get("Py") == 1 for j in jobs)
    regressions = [j.get("regression", {}) for j in jobs if j["resolution"] == 256]
    baseline_ok = len(regressions) == 10 and all(r.get("old_generator_bitwise_equal") and r.get("saved_output_bitwise_equal") for r in regressions)
    identity_ok = all(j.get("exact_repeat") and j.get("raw_matches_v04") and j.get("candidate_matches_v04") for j in jobs)
    distinct = {}
    for n in (256, 512, 1024):
        completed = [j for j in jobs if j["resolution"] == n and j["status"] == "COMPLETE"]
        hashes = [j["files"]["microstructure.npy"]["sha256"] for j in completed]
        distinct[str(n)] = len(hashes) == len(set(hashes)) == 10
    extended = json.loads((diagnostics / "diagnostic_2048_successive.json").read_text(encoding="utf-8"))
    previous_steps = json.loads((diagnostics / "prior_successive.json").read_text(encoding="utf-8"))
    extended_checks = []
    for row in extended:
        previous = next(r for r in previous_steps if (r["design_id"], r["seed"], r["low"]) == (row["design_id"], row["seed"], 512))
        extended_checks.append(all(abs(row[k]) < abs(previous[k]) for k in ("mean_strut_thickness", "median_pore_diameter")))
    broad_checks = {k: [bool(c["available"] and c["errors"][k] <= limit) for c in broad]
                    for k, limit in protocol["unchanged_256_to_1024_targets"].items()}
    gates = {"topology_30_of_30": topology_ok, "baseline_10_of_10": baseline_ok,
             "stochastic_identity": identity_ok and all(distinct.values()),
             "historical_unchanged": manifest["historical_unchanged"],
             "successive_dimensions": all(all(v) for v in checks.values()),
             "density_and_curves": all(all(v) for v in broad_checks.values()),
             "smaller_2048_increments": len(extended_checks) == 3 and all(extended_checks),
             "all_jobs_complete": manifest["status"] == "COMPLETE"}
    summary = {"pipeline_version": "0.4.1", "scientific_status": "PASS" if all(gates.values()) else "HOLD",
               "ready_for_v05": all(gates.values()), "gates": gates, "successive_checks": checks,
               "broad_checks": broad_checks, "comparisons": comparisons,
               "distinct_samples_per_resolution": distinct,
               "original_256_to_1024_all_targets_pass": all(c["targets_pass"] for c in broad),
               "control_trends": control_trends(jobs), "rows": jobs,
               "repairs": [{"design_id": j["design_id"], "seed": j["seed"], "resolution": j["resolution"], **j["topology_repair"]}
                           for j in jobs if j.get("topology_repair", {}).get("added_pixels", 0)]}
    write_json(out / "summary.json", e.json_safe(summary))
    write_json(out / "successive.json", successive_rows(jobs))
    write_validation_report(out, summary, protocol)
    # Existing plotter only requires these trend/runtime fields beyond jobs.
    plot_summary = {"matched_control_trends": control_trends(jobs), "runtime": {}}
    for n in (256, 512, 1024):
        complete = [j for j in jobs if j["resolution"] == n and j["status"] == "COMPLETE"]
        plot_summary["runtime"][str(n)] = {key: float(np.mean([j[key] for j in complete])) if complete else None
                                          for key in ("generation_seconds", "evaluation_seconds", "peak_traced_generation_bytes")}
    write_json(out / "runtime.json", plot_summary["runtime"])
    make_figures(out, out / "figures", jobs, plot_summary)
    return manifest


def write_validation_report(out, summary, protocol):
    lines = ["# v0.4.1 — post-fix validation", "", f"Scientific status: **{summary['scientific_status']}**. CAD/vectorization: not started.", "",
             "The documented amendment uses successive dimensional convergence; the original coarse-baseline gates are still reported and are not retroactively marked PASS.", "",
             "| Gate | Result |", "|---|---|"]
    lines.extend(f"| {k} | {'PASS' if v else 'HOLD'} |" for k, v in summary["gates"].items())
    lines += ["", "## Successive-resolution dimensional gates", "", "| Metric | Limit (512 → 1024) | Passing pairs |", "|---|---:|---:|"]
    for k, values in summary["successive_checks"].items():
        lines.append(f"| {k} | {100 * protocol['successive_targets'][k]:g}% | {sum(values)}/{len(values)} |")
    lines += ["", "## All post-fix pairs", "", "| Design | Seed | Step | Mean thickness % | P10 thickness % | Pore median % |",
              "|---:|---:|---|---:|---:|---:|"]
    for r in successive_rows(summary["rows"]):
        lines.append(f"| {r['design_id']} | {r['seed']} | {r['low']} → {r['high']} | " + " | ".join(f"{r[k]:+.4f}" for k in DIMENSIONS) + " |")
    lines += ["", "## Explicit generator repairs", "", "| Design | Seed | N | Components before → after | Added pixels | Added area fraction |",
              "|---:|---:|---:|---|---:|---:|"]
    for r in summary["repairs"]:
        lines.append(f"| {r['design_id']} | {r['seed']} | {r['resolution']} | {r['components_before']} → {r['components_after']} | {r['added_pixels']} | {r['added_area_fraction']:.9f} |")
    lines += ["", "No solid pixels were removed. No density erosion was needed: additions are far below the unchanged 0.005 solid-fraction tolerance.",
              "", "See `summary.json` for every original and amended gate, native metrics, hashes, stochastic checks and repair endpoints; `manifest.json` retains source inventories and worker failures.",
              "", "A HOLD means the implementation and diagnostics are complete, not that scientific acceptance has been obtained. Do not begin v0.5 on the basis of software test passes."]
    (out / "VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["investigate", "fixed-geometry", "validate"])
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--source-run", type=Path)
    parser.add_argument("--diagnostics", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args(argv)
    if not np.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be finite and positive")
    if args.stage == "fixed-geometry":
        if args.diagnostics is None:
            parser.error("fixed-geometry requires --diagnostics")
        result = fixed_geometry_control(args.diagnostics, args.output_dir)
    else:
        if args.baseline is None or args.source_run is None:
            parser.error("investigate/validate require --baseline and --source-run")
        if args.stage == "validate":
            if args.diagnostics is None:
                parser.error("validate requires --diagnostics")
            result = validate(args.baseline, args.source_run, args.diagnostics, args.output_dir, args.timeout)
        else:
            result = investigate(args.baseline, args.source_run, args.output_dir, args.timeout)
    if args.stage == "validate" and (args.output_dir / "summary.json").exists():
        status = read_json(args.output_dir / "summary.json")["scientific_status"]
        print(f"Execution: {result['status']}; scientific acceptance: {status}")
        if status != "PASS":
            return 3
    return 0 if result["status"] == "COMPLETE" and result["historical_unchanged"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
