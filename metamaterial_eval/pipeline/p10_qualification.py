"""v0.4.3: prospective lower-tail qualification, without generator changes.

Register first, then qualify. Whole-mask frozen P10 remains a diagnostic;
historical failures are never overwritten. No native generation or CAD occurs.
"""
from __future__ import annotations

import argparse
from importlib.metadata import version
from pathlib import Path
import sys

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from .resolution_validation import inventory
from .scripts import sha256_file
from .stabilization import evaluator
from .state import read_json, write_json, utc_now
from .thickness_verification import code_inventory as prior_code_inventory

REPO = Path(__file__).resolve().parents[2]
UPPER = 4 / 256
AREA_LIMIT = 1 / 1024
NECK_LIMIT = 3 / 1024
LEVELS = (1024, 2048)


def source_hashes():
    return {**prior_code_inventory(), str(Path(__file__).relative_to(REPO)): sha256_file(Path(__file__))}


def cdf_distance(first, second, upper=UPPER):
    """Exact area between empirical CDFs on [0, upper], without tail rescaling.

    Inputs are normalized thickness samples. Every skeleton sample retains its
    frozen-evaluator weight, including those above the interval (CDFs are not
    conditioned on T <= upper). Integrate constant steps at their exact knots,
    so plotting-grid choices cannot change acceptance.
    """
    a, b = (np.sort(np.asarray(x, dtype=float)) for x in (first, second))
    if any(x.ndim != 1 or not x.size or not np.isfinite(x).all() or (x < 0).any() for x in (a, b)):
        raise ValueError("Require nonempty finite nonnegative 1D samples")
    if not np.isfinite(upper) or upper <= 0:
        raise ValueError("upper must be finite and positive")
    knots = np.unique(np.r_[0., a[(a > 0) & (a < upper)], b[(b > 0) & (b < upper)], upper])
    fa = np.searchsorted(a, knots[:-1], side="right") / a.size
    fb = np.searchsorted(b, knots[:-1], side="right") / b.size
    area = float(np.sum(np.abs(fa - fb) * np.diff(knots)))
    return {"area_normalized_length": area, "equivalent_1024_pixels": area * 1024,
            "mean_cdf_gap": area / upper, "max_cdf_gap_diagnostic": float(np.max(np.abs(fa - fb))),
            "tail_mass_first": float(np.searchsorted(a, upper, side="right") / a.size),
            "tail_mass_second": float(np.searchsorted(b, upper, side="right") / b.size),
            "pass": area <= AREA_LIMIT + 1e-12}


def independent_cases():
    """Previously untested analytic parameters; deterministic, not a random CI."""
    cases = []
    for angle in (17., 38., 67.):
        for width, phase in ((2.5, .19), (3.5, .61)):
            cases.append({"id": f"bar{angle:g}_w{width}", "family": "bar", "angle": angle,
                          "width": width, "phase": phase})
    for family in ("ring", "junction"):
        for width, phase in ((2.5, .19), (3.5, .61)):
            cases.append({"id": f"{family}_w{width}", "family": family, "angle": 17.,
                          "width": width, "phase": phase})
    return cases


def shape(n, case, width_factor=1.):
    """Independent native pixel-center samples of fixed normalized geometry."""
    axis = (np.arange(n) + .5) / n - .5
    y, x = np.meshgrid(axis - case["phase"] / 256, axis + case["phase"] / 256, indexing="ij")
    w = case["width"] / 256 * width_factor
    if case["family"] == "bar":
        angle = np.deg2rad(case["angle"])
        tangent = x * np.cos(angle) + y * np.sin(angle)
        normal = -x * np.sin(angle) + y * np.cos(angle)
        solid = (np.abs(normal) < w / 2) & (np.abs(tangent) < .215)
    elif case["family"] == "ring":
        solid = np.abs(np.hypot(x, y) - .173) < w / 2
    elif case["family"] == "junction":
        solid = np.zeros((n, n), dtype=bool)
        for degrees in (17., 137., 257.):
            angle = np.deg2rad(degrees)
            along = np.clip(x * np.cos(angle) + y * np.sin(angle), 0, .187)
            solid |= (x - along * np.cos(angle))**2 + (y - along * np.sin(angle))**2 <= (w / 2)**2
    else:
        raise ValueError("Unknown control family")
    return solid.astype(np.uint8)


def neck_shape(n, healthy):
    """Fixed axis-aligned localized neck; endpoints and bulk width unchanged."""
    axis = (np.arange(n) + .5) / n - .5
    y, x = np.meshgrid(axis - .5 / 1024, axis, indexing="ij")
    width = np.where(np.abs(x) < .012, (4 if healthy else 1) / 1024, 3.5 / 256)
    return ((np.abs(x) < .21) & (np.abs(y) < width / 2)).astype(np.uint8)


def neck_measurement(a):
    """Direct occupied normal depth in the predefined |x|<.01 neck ROI.

    Qualified for these axis-aligned, single-interval sections only. This is not
    a generic global minimum-neck finder or a mechanical strength assessment.
    """
    n = a.shape[0]
    if a.shape != (n, n) or not np.isin(a, [0, 1]).all():
        raise ValueError("Expected a square binary mask")
    cols = np.flatnonzero(np.abs((np.arange(n) + .5) / n - .5) < .01)
    depths = []
    for x in cols:
        occupied = np.flatnonzero(a[:, x])
        if not len(occupied) or occupied[-1] - occupied[0] + 1 != len(occupied):
            raise ValueError("Missing or non-contiguous neck section")
        depths.append(len(occupied))
    minimum = min(depths)
    return {"minimum_depth_pixels": minimum, "minimum_depth_normalized": minimum / n,
            "single_component": ndi.label(a)[1] == 1,
            "pass": minimum / n >= NECK_LIMIT and ndi.label(a)[1] == 1}


def measure(a, e):
    m = e.local_dimensions(a)
    samples = np.asarray(m["strut_diameters"]) / a.shape[0]
    return samples, {"whole_mask_p10": float(m["p10_strut_thickness"]) / a.shape[0],
                     "mean": float(m["mean_strut_thickness"]) / a.shape[0],
                     "skeleton_sample_count": len(samples)}


def register(previous, out):
    previous, out = Path(previous).resolve(), Path(out).resolve()
    evaluator()  # fail before creating output if frozen evaluator changed
    summary = read_json(previous / "summary.json")
    old_protocol = read_json(previous / "protocol.json")
    if summary["milestone"] != "0.4.2" or summary["scientific_status"] != "HOLD":
        raise ValueError("This amendment requires the preserved v0.4.2 HOLD")
    for name, digest in old_protocol["code_inventory"].items():
        if sha256_file(REPO / name) != digest:
            raise ValueError(f"Previously frozen code changed: {name}")
    previous_041 = Path(old_protocol["previous_run"])
    if not previous_041.exists():
        # Resolve saved metadata relocated from macOS to the documented Windows checkout.
        previous_041 = REPO / "experiments/pipeline_v0.4.1/resolution_validation"
    protected = (previous.parent, previous_041.parent)
    if any(out == p or p in out.parents or out in p.parents for p in protected):
        raise ValueError("Output must be a new directory outside historical inputs")
    cases = independent_cases()
    protocol = {
        "milestone": "0.4.3", "registered_at_utc": utc_now(),
        "previous_042": str(previous), "previous_041": str(previous_041),
        "methodological_amendment": "Whole-mask P10 becomes diagnostic; lower-tail CDF area plus scoped local-neck checks replace its hard-gate role. Original failed P10 calibration remains failed.",
        "cdf_interval_normalized_width": [0., UPPER],
        "cdf_definition": "Exact integral of absolute difference of UNCONDITIONAL empirical CDFs; frozen skeleton samples with no pruning or reweighting",
        "cdf_area_limit_normalized_length": AREA_LIMIT,
        "budget_justification": "One nominal 1024-grid pixel of integrated thickness-distribution displacement; a declared numerical resolution budget, NOT a universal error bound or manufacturing tolerance",
        "limitation": "Aggregate lower-tail area may miss a rare localized weak neck, so independent local geometry checks are mandatory. Features above 4/256 are outside this metric's scope.",
        "independent_positive_controls": cases,
        "negative_controls": {"ids": ["bar38_w2.5", "ring_w2.5", "junction_w2.5"],
                              "width_factor": .75, "grid": 2048,
                              "rule": "Every deliberate 25% thinning must exceed the CDF area limit"},
        "neck_controls": {"resolutions": list(LEVELS), "healthy_width": 4 / 1024, "weak_width": 1 / 1024,
                          "minimum_required": NECK_LIMIT,
                          "rule": "Healthy neck passes, weak neck fails at both grids; local neck ROI |x|<.01"},
        "neck_justification": "Three nominal 1024 pixels is a numerical feature-resolution screen, not a physical manufacturing specification",
        "known_failed_bar": "Re-evaluate historical 30-degree w6 phase0.37 as regression ONLY, not independent qualification evidence",
        "holdout_rule": "All ten independent invariant controls must pass; all three thinning controls must fail CDF; all four healthy/weak neck outcomes must match expectations",
        "native_rule": "Only after holdout qualification: evaluate all ten saved 1024/2048 pairs, require CDF pass and retain prior mean/pore/density/spatial/topology/identity gates",
        "local_native_scope": "Previously inspected repaired connections only; NOT exhaustive neck certification across each network",
        "decision": "Amended tested-domain PASS only if all mandatory gates pass. No automatic CAD execution.",
        "code_sha256": source_hashes(),
        "histories": {str(p): inventory(p) for p in protected},
        "environment": {"python": sys.version, **{k: version(k) for k in ("numpy", "scipy", "scikit-image", "Pillow")}},
    }
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "protocol.json", protocol)
    print(f"Protocol registered, no qualification controls executed: {out}", flush=True)
    return protocol


def evaluate(out):
    out = Path(out).resolve()
    p = read_json(out / "protocol.json")
    if (out / "execution.json").exists():
        raise FileExistsError("Run already started; preserve it and register a new directory")
    if source_hashes() != p["code_sha256"]:
        raise ValueError("Code changed after registration")
    for path, expected in p["histories"].items():
        if inventory(Path(path)) != expected:
            raise ValueError("Historical inputs changed after registration")
    e = evaluator()
    execution = {"started_at_utc": utc_now(), "protocol_sha256": sha256_file(out / "protocol.json"), "status": "RUNNING"}
    write_json(out / "execution.json", execution)
    positives, negatives, necks = [], [], []
    cached = {}
    for case in p["independent_positive_controls"]:
        folder = out / "controls" / case["id"]; folder.mkdir(parents=True)
        measurements, samples = {}, {}
        for n in LEVELS:
            a = shape(n, case)
            samples[n], measurements[str(n)] = measure(a, e)
            Image.fromarray(a * 255).save(folder / f"{n}.png")
        comparison = cdf_distance(samples[1024], samples[2048])
        positives.append({"id": case["id"], "metrics": measurements, **comparison})
        cached[case["id"]] = (samples[2048], case)
        print(f"Invariant control {case['id']}: {comparison['equivalent_1024_pixels']:.4f} equivalent pixels", flush=True)
    for ident in p["negative_controls"]["ids"]:
        original, case = cached[ident]
        thinner = shape(2048, case, p["negative_controls"]["width_factor"])
        samples, metrics = measure(thinner, e)
        comparison = cdf_distance(original, samples)
        negatives.append({"id": ident, "thinned_metrics": metrics, **comparison, "defect_detected": not comparison["pass"]})
        Image.fromarray(thinner * 255).save(out / "controls" / ident / "NEGATIVE_25percent_thinner.png")
    neck_samples = {}
    for n in LEVELS:
        for healthy in (True, False):
            a = neck_shape(n, healthy)
            row = neck_measurement(a)
            row.update(resolution=n, healthy=healthy, expected_outcome_met=row["pass"] == healthy)
            necks.append(row)
            samples, _ = measure(a, e); neck_samples[n, healthy] = samples
            Image.fromarray(a * 255).save(out / "controls" / f"neck_{'healthy' if healthy else 'weak'}_{n}.png")
    neck_cdf = {str(n): cdf_distance(neck_samples[n, True], neck_samples[n, False]) for n in LEVELS}
    qualification = {
        "invariant_controls": len(positives) == 10 and all(r["pass"] for r in positives),
        "detects_25percent_thinning": len(negatives) == 3 and all(r["defect_detected"] for r in negatives),
        "local_neck_controls": len(necks) == 4 and all(r["expected_outcome_met"] for r in necks),
    }
    q = {"gates": qualification, "qualified": all(qualification.values()), "positives": positives,
         "negative_thinning": negatives, "necks": necks,
         "localized_neck_cdf_diagnostic": neck_cdf,
         "completed_before_native_evaluation_utc": utc_now()}
    write_json(out / "independent_qualification.json", q)
    previous = Path(p["previous_042"])
    old = read_json(previous / "summary.json")
    native = []
    if q["qualified"]:
        base = Path(p["previous_041"])
        lows = read_json(base / "manifest.json")["jobs"]
        highs = read_json(previous / "manifest.json")["jobs"]
        for high in highs:
            low = next(j for j in lows if (j["design_id"], j["seed"], j["resolution"]) == (high["design_id"], high["seed"], 1024))
            samples, measurements = [], []
            for root, job in ((base, low), (previous, high)):
                source = root / job["relative_directory"] / "microstructure.npy"
                if sha256_file(source) != job["files"]["microstructure.npy"]["sha256"]:
                    raise ValueError("Native sample differs from its historical manifest")
                a = np.load(source, allow_pickle=False)
                t, m = measure(a, e)
                old_p10 = job["evaluation"]["normalized"]["normalized_p10_strut_thickness"]
                m["p10_identical_to_history"] = m["whole_mask_p10"] == old_p10
                samples.append(t); measurements.append(m)
            native.append({"design_id": high["design_id"], "seed": high["seed"],
                           "metrics_1024_2048": measurements, **cdf_distance(*samples)})
            print(f"Native D{high['design_id']}/S{high['seed']}: evaluated saved masks", flush=True)
    # Historical outlier is a regression check only; never counted as holdout.
    known = []
    for n in LEVELS:
        source = previous / "analytic" / "bar_30_w6_phase0.37" / f"{n}.png"
        with Image.open(source) as im:
            a = (np.asarray(im.convert("L")) > 0).astype(np.uint8)
        known.append(measure(a, e))
    regression = {"role": "Known failure regression, NOT independent validation",
                  "metrics": [x[1] for x in known], **cdf_distance(known[0][0], known[1][0])}
    retained = {k: old["gates"][k] for k in (
        "topology_30_of_30", "baseline_10_of_10", "stochastic_identity", "density_and_curves",
        "all_ten_2048_complete", "2048_topology_repeat_identity", "mean_1024_2048", "pore_1024_2048",
        "density_curves_1024_2048", "repaired_neck_local_screen", "historical_and_code_unchanged")}
    neck_rows = []
    for r in old["repairs"]:
        depths = [min(c["gap_column_depths_pixels"]) / r["resolution"] for c in r["cross_sections"] if c["supported"]]
        neck_rows.append({"resolution": r["resolution"], "min_depth_normalized": min(depths) if depths else None,
                          "pass": bool(depths) and min(depths) >= NECK_LIMIT and r["local_neck_screen_pass"]})
    preservation = all(inventory(Path(path)) == h for path, h in p["histories"].items())
    gates = {**qualification, **retained,
             "all_native_lower_tail": len(native) == 10 and all(r["pass"] for r in native),
             "whole_p10_preserved": len(native) == 10 and all(m["p10_identical_to_history"] for r in native for m in r["metrics_1024_2048"]),
             "repair_neck_resolution_screen": bool(neck_rows) and all(r["pass"] for r in neck_rows),
             "inputs_and_code_unchanged": preservation and source_hashes() == p["code_sha256"]}
    result = {"milestone": "0.4.3", "scientific_status": "AMENDED_PASS_TESTED_DOMAIN" if all(gates.values()) else "HOLD",
              "eligible_for_single_sample_v05_study": all(gates.values()), "cad_started": False,
              "original_P10_calibration_passed": False, "historical_v042_status": old["scientific_status"],
              "p10_role": "diagnostic, unchanged definition and values", "gates": gates,
              "independent_qualification": q, "native": native, "known_outlier_regression": regression,
              "repair_necks": neck_rows,
              "limitations": ["Deterministic unseen-parameter controls, not statistical independence or a confidence guarantee.",
                              "Qualification covers the specified lower-tail interval and tested morphologies only.",
                              "Sensitivity demonstrated for 25% uniform thinning, not all smaller/local defects.",
                              "Local neck qualification is scoped to axis-aligned controls and inspected repairs; not an exhaustive network neck audit.",
                              "No physical scale, material/load or manufacturing minimum is certified.",
                              "Prior failed P10 calibration remains failed; no retrospective gate substitution in historical reports."]}
    write_json(out / "summary.json", result)
    execution.update(status="COMPLETE", completed_at_utc=utc_now(), histories_unchanged=preservation)
    write_json(out / "execution.json", execution)
    write_report(out, result)
    plot_cdfs(out, p, cached)
    print(result["scientific_status"], flush=True)
    return result


def write_report(out, result):
    q = result["independent_qualification"]
    lines = ["# v0.4.3 — amended lower-tail qualification decision", "",
             f"Decision: **{result['scientific_status']}**.", "",
             "Original 10% P10 calibration: **FAILED, unchanged**. Historical v0.4.2: **HOLD, unchanged**.",
             "P10 is retained as a diagnostic, not relabeled as a passing calibration. No generator/evaluator change or CAD execution.", "",
             "## Prospective method", "",
             r"$A=\int_0^{4/256}|F_{1024}(w)-F_{2048}(w)|\,dw \le 1/1024$.",
             "CDFs are unconditional empirical distributions of unchanged frozen skeleton-thickness samples. Integration uses exact step-function knots.",
             "One 1024 pixel is a declared aggregate numerical-displacement budget, not a physical safety tolerance.",
             "Local necks require occupied normal depth ≥3/1024 in the specified ROI. Aggregate CDF checks alone may miss rare defects.", "",
             "## Independent invariant controls", "",
             "| Control | CDF area ×1024 (limit 1) | Maximum CDF gap (diagnostic) | Pass |", "|---|---:|---:|---|"]
    for r in q["positives"]:
        lines.append(f"| {r['id']} | {r['equivalent_1024_pixels']:.6f} | {r['max_cdf_gap_diagnostic']:.6f} | {r['pass']} |")
    lines += ["", "## Independent defect controls", "",
              "| Control (25% thinner) | CDF area ×1024 | Defect detected |", "|---|---:|---|"]
    for r in q["negative_thinning"]:
        lines.append(f"| {r['id']} | {r['equivalent_1024_pixels']:.6f} | {r['defect_detected']} |")
    lines += ["", "| N | Neck | Minimum depth (px) | Minimum normalized depth | Expected outcome met |", "|---:|---|---:|---:|---|"]
    for r in q["necks"]:
        lines.append(f"| {r['resolution']} | {'healthy' if r['healthy'] else 'weak'} | {r['minimum_depth_pixels']} | {r['minimum_depth_normalized']:.8f} | {r['expected_outcome_met']} |")
    lines += ["", "## Saved native pairs — only evaluated after independent qualification", "",
              "| Design | Seed | CDF area ×1024 | Whole-mask P10 at 1024 | Whole-mask P10 at 2048 | Pass |", "|---:|---:|---:|---:|---:|---|"]
    for r in result["native"]:
        a, b = r["metrics_1024_2048"]
        lines.append(f"| {r['design_id']} | {r['seed']} | {r['equivalent_1024_pixels']:.6f} | {a['whole_mask_p10']:.9f} | {b['whole_mask_p10']:.9f} | {r['pass']} |")
    if not result["native"]:
        lines += ["", "Native evaluation withheld because independent qualification did not pass."]
    lines += ["", "## Decision gates", "", "| Gate | Pass |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in result["gates"].items()]
    lines += ["", "## Limitations", ""] + [f"- {s}" for s in result["limitations"]]
    lines += ["", "An amended tested-domain PASS permits considering a separate single-sample v0.5 raster-to-vector validation; it does not establish CAD validity or manufacturing suitability.",
              "This study does not itself begin v0.5. Windows reproduction commands are documented; execution here was on macOS."]
    (out / "AMENDED_ACCEPTANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_cdfs(out, protocol, cached):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    e = evaluator()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    case = next(c for c in protocol["independent_positive_controls"] if c["id"] == "bar38_w2.5")
    widths = np.linspace(0, UPPER, 600)
    for n in LEVELS:
        t, _ = measure(shape(n, case), e)
        axes[0].plot(widths, np.searchsorted(np.sort(t), widths, side="right") / len(t), label=str(n))
    t, _ = measure(shape(2048, case, .75), e)
    axes[0].plot(widths, np.searchsorted(np.sort(t), widths, side="right") / len(t), "--", label="25% thinner")
    q = read_json(out / "independent_qualification.json")
    axes[1].bar(range(10), [r["equivalent_1024_pixels"] for r in q["positives"]])
    axes[1].axhline(1, color="red", linestyle="--", label="Registered limit")
    axes[0].set(xlabel="Normalized thickness w", ylabel="Unconditional CDF F(w)", title="Independent 38° bar")
    axes[1].set(xlabel="Independent control index", ylabel="CDF area ×1024", title="Ten invariant controls")
    for ax in axes:
        ax.legend(fontsize=8)
    fig.savefig(out / "qualification.png", dpi=170); plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("register")
    p.add_argument("--previous-run", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    r = sub.add_parser("qualify")
    r.add_argument("output_dir", type=Path)
    args = parser.parse_args(argv)
    if args.stage == "register":
        register(args.previous_run, args.output_dir)
        return 0
    result = evaluate(args.output_dir)
    return 0 if result["eligible_for_single_sample_v05_study"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
