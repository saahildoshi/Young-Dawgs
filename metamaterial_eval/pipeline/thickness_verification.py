"""v0.4.2 validation-only protocol, analytic calibration, and ten-case 2048 study.

The generator remains v0.4.1 and evaluator remains frozen v1.1. Run ``prepare``
first to commit the protocol and control-derived P10 limit, then ``run``.
Neither stage overwrites old evidence. No CAD or manufacturing claim is made.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from ..generators import native_resolution, stabilized_resolution, v03_baseline
from .config import default_evaluator_path
from .resolution_report import TARGETS
from .resolution_validation import inventory
from .scripts import sha256_file
from .stabilization import evaluator, signed_change, successive_rows, worker
from .state import read_json, write_json, utc_now

REPO = Path(__file__).resolve().parents[2]
LEVELS = (256, 512, 1024, 2048)
DIMENSIONS = ("mean_strut_thickness", "p10_strut_thickness", "median_pore_diameter")
FAMILIES = ("bar_0", "bar_30", "bar_45", "ring", "junction_T", "junction_Y")
WIDTHS = (2, 3, 4, 6)
PHASES = (0., .37)  # fixed shifts in baseline units, not shifts in output pixels
FOUR = ndi.generate_binary_structure(2, 1)


def read_list(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected list in {path}")
    return data


def code_inventory():
    paths = [Path(__file__), Path(native_resolution.__file__), Path(stabilized_resolution.__file__),
             Path(v03_baseline.__file__), default_evaluator_path(),
             Path(__file__).with_name("resolution_worker.py"),
             Path(__file__).with_name("resolution.py"), Path(__file__).with_name("stabilization.py"),
             Path(__file__).with_name("evaluator.py")]
    return {str(p.relative_to(REPO)): sha256_file(p) for p in paths}


def analytic_mask(n, family, width, phase):
    """Independent pixel-center samples of explicit rectangles/annuli/capsules.

    All widths and centers are fixed in normalized space. T and Y junctions are
    unions of three round-ended rays of length .22; their node widths vary by
    construction, so nominal arm width is not a claimed whole-mask mean truth.
    """
    if family not in FAMILIES or width not in WIDTHS or n not in LEVELS:
        raise ValueError("Unknown analytic geometry or resolution")
    axis = (np.arange(n) + .5) / n - .5
    y, x = np.meshgrid(axis - phase / 256, axis + phase / 256, indexing="ij")
    w = width / 256
    if family.startswith("bar_"):
        angle = np.deg2rad(float(family.split("_")[1]))
        tangent = x * np.cos(angle) + y * np.sin(angle)
        normal = -x * np.sin(angle) + y * np.cos(angle)
        solid = (np.abs(normal) < w / 2) & (np.abs(tangent) < .25)
    elif family == "ring":
        solid = np.abs(np.hypot(x, y) - .2) < w / 2
    else:
        angles = (0, 90, 180) if family == "junction_T" else (30, 150, 270)
        solid = np.zeros((n, n), dtype=bool)
        for degrees in angles:
            angle = np.deg2rad(degrees)
            along = np.clip(x * np.cos(angle) + y * np.sin(angle), 0, .22)
            solid |= (x - along * np.cos(angle))**2 + (y - along * np.sin(angle))**2 <= (w / 2)**2
    return solid.astype(np.uint8)


def relative(low, high):
    value = signed_change(low, high)
    return None if value is None else abs(value) / 100


def calibrate_p10(rows):
    """Empirical worst-control envelope, capped at the existing 10% ceiling.

    Never increase the envelope after seeing native outputs. Missing controls
    or a >10% calibration demand are qualification failures, not permission to
    loosen the ceiling. This is an empirical tested-domain bound, not a CI.
    """
    changes = []
    for family in FAMILIES:
        for width in WIDTHS:
            for phase in PHASES:
                group = [r for r in rows if (r["family"], r["width"], r["phase"]) == (family, width, phase)]
                values = {r["resolution"]: r["normalized"]["p10_strut_thickness"] for r in group}
                if len(group) != 4 or set(values) != set(LEVELS) or any(v is None or not np.isfinite(v) or v <= 0 for v in values.values()):
                    raise ValueError("Incomplete or undefined analytic P10 control")
                changes.append({"family": family, "width": width, "phase": phase,
                                "relative_1024_2048": relative(values[1024], values[2048])})
    maximum = max(x["relative_1024_2048"] for x in changes)
    return {"method": "Maximum absolute 1024->2048 relative P10 change over all 48 preregistered controls",
            "empirical_envelope": maximum, "existing_ceiling": .10,
            "effective_limit": min(maximum, .10),
            "calibration_qualified": maximum <= .10 + 1e-12,
            "controls": changes, "control_count": len(changes)}


def prepare(previous_run, v04_run, out):
    """Freeze design subset, criterion rules and code BEFORE new native results."""
    previous_run, v04_run, out = [Path(p).resolve() for p in (previous_run, v04_run, out)]
    e = evaluator()
    old = read_json(previous_run / "manifest.json")
    if old["pipeline_version"] != "0.4.1" or old["status"] != "COMPLETE" or len(old["jobs"]) != 30:
        raise ValueError("Require the completed 30-case v0.4.1 manifest")
    expected = {(j["design_id"], j["seed"], n) for j in old["jobs"] for n in (256, 512, 1024)}
    actual = {(j["design_id"], j["seed"], j["resolution"]) for j in old["jobs"]}
    if len(expected) != 30 or actual != expected or any(j["status"] != "COMPLETE" for j in old["jobs"]):
        raise ValueError("Incomplete matched design subset")
    for module, key in ((stabilized_resolution, "native_generator_sha256"), (native_resolution, "native_renderer_sha256")):
        if sha256_file(Path(module.__file__)) != old[key]:
            raise ValueError("Generator changed since v0.4.1; no automatic port permitted")
    for job in old["jobs"]:
        for name, file_info in job["files"].items():
            if sha256_file(previous_run / job["relative_directory"] / name) != file_info["sha256"]:
                raise ValueError("A saved v0.4.1 sample differs from its recorded hash")
    protected = (previous_run.parent, v04_run)
    if any(out == p or p in out.parents or out in p.parents for p in protected):
        raise ValueError("Choose a new output outside all historical runs")
    out.mkdir(parents=True, exist_ok=False)
    protocol = {
        "milestone": "0.4.2", "generator_version": "0.4.1", "created_at_utc": utc_now(),
        "previous_run": str(previous_run), "v04_run": str(v04_run),
        "code_inventory": code_inventory(),
        "historical_inventories": {str(p): inventory(p) for p in protected},
        "cases": [{k: j[k] for k in ("design_id", "seed", "requested", "sample_id", "candidate_index")}
                  for j in old["jobs"] if j["resolution"] == 1024],
        "mean_thickness_limit_1024_2048": .03,
        "pore_limit_1024_2048": .03,
        "p10_rule": "Maximum relative 1024->2048 change across preregistered analytic controls, capped at old 10% ceiling; controls exceeding ceiling force HOLD",
        "analytic_controls": {"families": list(FAMILIES), "widths_at_256": list(WIDTHS),
                              "fixed_shift_at_256": list(PHASES), "resolutions": list(LEVELS)},
        "analytic_truth_note": "Arms have fixed width w/256; curved/junction masks are analytically fixed geometry, not a claim of uniform whole-mask skeleton width",
        "native_gate": "All 10 pairs must satisfy mean, calibrated P10 and pore limits at 1024->2048",
        "calibration_coverage": "1024 native P10 range must lie within the 1024 analytic control P10 range; this is range coverage, not proof that every morphology is represented",
        "inherited_gates": "Preserve v0.4.1 30/30 topology, 10/10 baseline, stochastic identity, density and S2/L gates; 512->1024 thickness failures remain historical",
        "new_curve_limits": {"phi_s_absolute": .005, "S2_nrmse": .05, "L_nrmse": .05},
        "attribution_rule": "Compare native and fixed-2048 geometry sampling increments; residual <= half native mean increment indicates dominant sampling pattern in that case; not a universal bias correction",
        "repair_rule": "No single solid-pixel deletion in connector neighborhood may disconnect the network; boundary-normal occupied gap-column depth >= 1/255 domain length, half nominal 2/255 capsule width after boundary clipping",
        "physical_limits": "No dimensional scale, material, load, manufacturing feature size or mesh size specified: structural/manufacturing adequacy NOT certified",
        "execution": "Sequential isolated 2048 workers, 600 s default timeout, no in-task generator revision, no production promotion to 2048",
        "cad": "Not started; a resolution-stage PASS is not CAD/mesh/manufacturing validation",
        "status": "CALIBRATING_CONTROLS",
    }
    write_json(out / "protocol.json", protocol)
    controls = []
    for family in FAMILIES:
        for width in WIDTHS:
            for phase in PHASES:
                for n in LEVELS:
                    a = analytic_mask(n, family, width, phase)
                    m = e.local_dimensions(a)
                    row = {"family": family, "width": width, "phase": phase, "resolution": n,
                           "analytic_arm_width": width / 256,
                           "normalized": e.json_safe({k: float(m[k]) / n for k in DIMENSIONS}),
                           "pixel_sha256": hashlib.sha256(a.tobytes()).hexdigest()}
                    controls.append(row)
                    folder = out / "analytic" / f"{family}_w{width}_phase{phase}"
                    folder.mkdir(parents=True, exist_ok=True)
                    Image.fromarray(a * 255).save(folder / f"{n}.png")
            print(f"Analytic controls: {family}, width={width}", flush=True)
        write_json(out / "analytic_controls.json", controls)
    calibration = calibrate_p10(controls)
    calibration["created_before_native_runs_utc"] = utc_now()
    write_json(out / "p10_calibration.json", calibration)
    protocol["calibration_sha256"] = sha256_file(out / "p10_calibration.json")
    protocol["analytic_results_sha256"] = sha256_file(out / "analytic_controls.json")
    protocol["status"] = "READY_FOR_NATIVE_DIAGNOSTICS"
    write_json(out / "protocol.json", protocol)
    write_control_report(out, controls, calibration)
    print(f"P10 envelope={calibration['empirical_envelope']:.6%}; effective limit={calibration['effective_limit']:.6%}; qualified={calibration['calibration_qualified']}", flush=True)
    return protocol


def fixed_sampling(a, e):
    """Measurement-only nearest endpoint sampling; never a native generator."""
    values = {}
    for n in LEVELS:
        indices = np.rint(np.arange(n) * (a.shape[0] - 1) / (n - 1)).astype(int)
        sample = a[np.ix_(indices, indices)]
        m = e.local_dimensions(sample)
        values[str(n)] = e.json_safe({k: float(m[k]) / n for k in DIMENSIONS})
    return values


def repair_fragility(raw, repaired, audit):
    """Test connector neighborhood, using finite-domain 4-connectivity.

    Test deletion of EVERY solid pixel in the capsule bbox plus one pixel.
    No deletion changes the stored mask. Also report inward occupied depth
    across horizontal top/bottom boundary connectors, without doubling EDT
    values at an open image edge. Other orientations are explicitly unqualified.
    This tests a local discrete neck, not mechanical strength.
    """
    if raw.shape != repaired.shape or np.any(raw > repaired):
        raise ValueError("Expected addition-only, equal-size repair")
    n = raw.shape[0]
    radius = audit["bridge_width_normalized"] * (n - 1) / 2
    regions = np.zeros(raw.shape, dtype=bool)
    profiles = []
    for bridge in audit["bridges"]:
        p, q = np.array(bridge["start_yx"]), np.array(bridge["end_yx"])
        lo = np.maximum(0, np.floor(np.minimum(p, q) - radius - 1).astype(int))
        hi = np.minimum(n, np.ceil(np.maximum(p, q) + radius + 1).astype(int) + 1)
        regions[lo[0]:hi[0], lo[1]:hi[1]] = True
        if p[0] == q[0] and p[0] in (0, n - 1):
            depths = []
            for x in range(min(p[1], q[1]) + 1, max(p[1], q[1])):
                col = repaired[:, x] if p[0] == 0 else repaired[::-1, x]
                void = np.flatnonzero(col == 0)
                depths.append(int(void[0]) if len(void) else n)
            if depths:
                profiles.append({"supported": True, "gap_column_depths_pixels": depths,
                                 "min_depth_normalized": min(depths) / (n - 1)})
            else:
                profiles.append({"supported": False, "reason": "No interior column"})
        else:
            profiles.append({"supported": False, "reason": "Non-horizontal boundary repair needs separate cross-section analysis"})
    fragile = []
    test = repaired.copy()
    tested = np.argwhere(regions & repaired.astype(bool))
    for y, x in tested:
        test[y, x] = 0
        if ndi.label(test, structure=FOUR)[1] != 1:
            fragile.append([int(y), int(x)])
        test[y, x] = 1
    depth_ok = bool(profiles) and all(p["supported"] and p["min_depth_normalized"] >= 1 / 255 for p in profiles)
    return {"resolution": n, "added_pixels": int(np.count_nonzero(repaired != raw)),
            "tested_solid_pixels": len(tested), "single_pixel_articulations_yx": fragile,
            "cross_sections": profiles, "local_neck_screen_pass": len(tested) > 0 and not fragile and depth_ok,
            "not_certified": "Mechanical strength, CAD meshing and manufacturing minimum feature size"}


def reconstruct_raw(case, n):
    state, baseline, _ = native_resolution._select(case["seed"], case["requested"]["solid_fraction_target"],
                                                  case["requested"]["strut_scale"], case["requested"]["pore_scale"])
    if n == 256:
        return baseline.copy()
    rng = np.random.default_rng()
    rng.bit_generator.state = deepcopy(state)
    return native_resolution._render_native(rng, case["requested"]["solid_fraction_target"],
                                            case["requested"]["strut_scale"], case["requested"]["pore_scale"], n)


def high_pair(low, high, e, p10_limit):
    result = {"design_id": low["design_id"], "seed": low["seed"],
              "available": high["status"] == "COMPLETE"}
    if not result["available"]:
        return {**result, "pass": False, "reason": high.get("error", "Worker failed")}
    a, b = low["evaluation"], high["evaluation"]
    errors = {key: relative(a["normalized"]["normalized_" + key], b["normalized"]["normalized_" + key]) for key in DIMENSIONS}
    errors.update(phi_s_absolute=abs(a["raw"]["phi_s"] - b["raw"]["phi_s"]),
                  S2_nrmse=e.normalized_rmse(np.array(b["common_curves"]["s2"]), np.array(a["common_curves"]["s2"])),
                  L_nrmse=e.normalized_rmse(np.array(b["common_curves"]["lineal_path"]), np.array(a["common_curves"]["lineal_path"])))
    limits = {"mean_strut_thickness": .03, "p10_strut_thickness": p10_limit, "median_pore_diameter": .03,
              **{k: TARGETS[k] for k in ("phi_s_absolute", "S2_nrmse", "L_nrmse")}}
    checks = {key: value is not None and np.isfinite(value) and value <= limits[key] + 1e-12 for key, value in errors.items()}
    return {**result, "errors": errors, "checks": checks, "pass": all(checks.values())}


def run(out, timeout=600):
    out = Path(out).resolve()
    protocol = read_json(out / "protocol.json")
    if protocol["status"] != "READY_FOR_NATIVE_DIAGNOSTICS":
        raise ValueError("Complete prepare first")
    if (out / "manifest.json").exists():
        raise FileExistsError("A run already started here; preserve it and prepare a new directory")
    if protocol["code_inventory"] != code_inventory():
        raise ValueError("Code changed after protocol preparation; prepare a fresh evidence directory")
    for path, key in (("p10_calibration.json", "calibration_sha256"), ("analytic_controls.json", "analytic_results_sha256")):
        if sha256_file(out / path) != protocol[key]:
            raise ValueError("Calibration evidence changed after preparation")
    for path, hashes in protocol["historical_inventories"].items():
        if inventory(Path(path)) != hashes:
            raise ValueError("Historical input changed after preparation")
    e = evaluator()
    previous = Path(protocol["previous_run"])
    old = read_json(previous / "manifest.json")
    prior_summary = read_json(previous / "summary.json")
    calibration = read_json(out / "p10_calibration.json")
    manifest = {"milestone": "0.4.2", "generator_version": "0.4.1", "status": "RUNNING",
                "protocol_sha256": sha256_file(out / "protocol.json"),
                "started_at_utc": utc_now(), "jobs": []}
    write_json(out / "manifest.json", manifest)
    for case in protocol["cases"]:
        relative_dir = f"native_2048/design_{case['design_id']:03d}_seed_{case['seed']:03d}"
        job = {**case, "resolution": 2048, "generator_version": "0.4.1"}
        record = worker(job, out / relative_dir, out / "logs" / Path(relative_dir).name, timeout)
        record["relative_directory"] = relative_dir
        record["latent_identity_preserved"] = record.get("candidate_index") == case["candidate_index"]
        manifest["jobs"].append(record)
        write_json(out / "manifest.json", manifest)
        print(f"2048 design {case['design_id']} seed {case['seed']}: {record['status']}", flush=True)
    all_rows = old["jobs"] + manifest["jobs"]
    changes = successive_rows(all_rows)
    write_json(out / "successive_changes.json", changes)
    pairs, controls, attribution, repairs = [], [], [], []
    for high in manifest["jobs"]:
        low = next(j for j in old["jobs"] if (j["design_id"], j["seed"], j["resolution"]) == (high["design_id"], high["seed"], 1024))
        pairs.append(high_pair(low, high, e, calibration["effective_limit"]))
        if high["status"] != "COMPLETE":
            continue
        a = np.load(out / high["relative_directory"] / "microstructure.npy", allow_pickle=False)
        sampled = fixed_sampling(a, e)
        controls.append({"design_id": high["design_id"], "seed": high["seed"], "values": sampled,
                         "warning": "Diagnostic resampling ONLY; not native outputs or continuum truth"})
        native_delta = signed_change(low["evaluation"]["normalized"]["normalized_mean_strut_thickness"],
                                     high["evaluation"]["normalized"]["normalized_mean_strut_thickness"])
        fixed_delta = signed_change(sampled["1024"]["mean_strut_thickness"], sampled["2048"]["mean_strut_thickness"])
        attribution.append({"design_id": high["design_id"], "seed": high["seed"],
                            "native_mean_step_percent": native_delta, "fixed_geometry_mean_step_percent": fixed_delta,
                            "residual_percentage_points": native_delta - fixed_delta,
                            "dominant_sampling_pattern": abs(native_delta - fixed_delta) <= .5 * abs(native_delta) + 1e-12})
    for record in all_rows:
        audit = record.get("topology_repair", {})
        if record["status"] != "COMPLETE" or not audit.get("added_pixels"):
            continue
        root = out if record["resolution"] == 2048 else previous
        repaired = np.load(root / record["relative_directory"] / "microstructure.npy", allow_pickle=False)
        raw = reconstruct_raw(record, record["resolution"])
        if hashlib.sha256(raw.tobytes()).hexdigest() != audit["raw_pixel_sha256"]:
            raise ValueError("Raw replay differs from recorded repair input")
        detail = repair_fragility(raw, repaired, audit)
        detail.update(design_id=record["design_id"], seed=record["seed"], audit=audit)
        repairs.append(detail)
        folder = out / "repair_inspection" / f"D{record['design_id']}_S{record['seed']}_N{record['resolution']}"
        folder.mkdir(parents=True)
        np.save(folder / "raw.npy", raw, allow_pickle=False)
        np.save(folder / "added_pixels.npy", (repaired - raw).astype(np.uint8), allow_pickle=False)
        plot_repair(raw, repaired, folder / "repair.png")
    unchanged = all(inventory(Path(p)) == hashes for p, hashes in protocol["historical_inventories"].items())
    manifest.update(status="COMPLETE" if all(j["status"] == "COMPLETE" for j in manifest["jobs"]) else "COMPLETED_WITH_FAILURES",
                    historical_unchanged=unchanged, code_unchanged=code_inventory() == protocol["code_inventory"],
                    finished_at_utc=utc_now())
    write_json(out / "manifest.json", manifest)
    inherited = {k: prior_summary["gates"][k] for k in ("topology_30_of_30", "baseline_10_of_10", "stochastic_identity", "density_and_curves")}
    native_p10 = [j["evaluation"]["normalized"]["normalized_p10_strut_thickness"] for j in old["jobs"] if j["resolution"] == 1024]
    analytic = read_list(out / "analytic_controls.json")
    analytic_p10 = [r["normalized"]["p10_strut_thickness"] for r in analytic if r["resolution"] == 1024]
    gates = {**inherited,
             "all_ten_2048_complete": len(manifest["jobs"]) == 10 and manifest["status"] == "COMPLETE",
             "2048_topology_repeat_identity": all(j.get("topology_valid") and j.get("exact_repeat") and j["latent_identity_preserved"] for j in manifest["jobs"]),
             "p10_controls_qualified": calibration["calibration_qualified"],
             "p10_control_width_coverage": min(analytic_p10) <= min(native_p10) <= max(native_p10) <= max(analytic_p10),
             "mean_1024_2048": len(pairs) == 10 and all(p.get("checks", {}).get("mean_strut_thickness", False) for p in pairs),
             "p10_1024_2048": len(pairs) == 10 and all(p.get("checks", {}).get("p10_strut_thickness", False) for p in pairs),
             "pore_1024_2048": len(pairs) == 10 and all(p.get("checks", {}).get("median_pore_diameter", False) for p in pairs),
             "density_curves_1024_2048": all(all(p.get("checks", {}).get(k, False) for k in ("phi_s_absolute", "S2_nrmse", "L_nrmse")) for p in pairs),
             "repaired_neck_local_screen": bool(repairs) and all(r["local_neck_screen_pass"] for r in repairs),
             "historical_and_code_unchanged": unchanged and manifest["code_unchanged"]}
    summary = {"milestone": "0.4.2", "scientific_status": "PASS" if all(gates.values()) else "HOLD",
               "resolution_stage_complete": all(gates.values()), "cad_started": False,
               "physical_necks_certified": False, "gates": gates, "pairs": pairs, "p10_calibration": calibration,
               "sampling_attribution": attribution, "repairs": repairs,
               "limitation": "No continuum truth for generated networks. Empirical calibration does not certify all geometries or manufacturing. Historical v0.4.1 HOLD retained."}
    write_json(out / "fixed_geometry_controls.json", controls)
    write_json(out / "repair_inspection.json", repairs)
    write_json(out / "summary.json", summary)
    write_report(out, summary, changes, manifest)
    plot_convergence(out, all_rows, controls)
    print(f"v0.4.2 execution: {manifest['status']}; scientific status: {summary['scientific_status']}", flush=True)
    return summary


def write_control_report(out, rows, calibration):
    lines = ["# v0.4.2 analytic thickness controls", "",
             "192 masks: six geometry families × four fixed widths × two fixed spatial shifts × four resolutions.",
             "The rule was fixed before native 2048 results. P10 tolerance is an empirical tested-control envelope, not a statistical confidence interval.", "",
             f"Observed envelope: {100 * calibration['empirical_envelope']:.6f}%.",
             f"Effective limit: {100 * calibration['effective_limit']:.6f}%; existing 10% ceiling retained.",
             f"Calibration qualified: {calibration['calibration_qualified']}.", "",
             "| Geometry | Width at 256 | Fixed phase | P10 1024→2048 absolute change % |", "|---|---:|---:|---:|"]
    for r in calibration["controls"]:
        lines.append(f"| {r['family']} | {r['width']} | {r['phase']} | {100 * r['relative_1024_2048']:.6f} |")
    lines += ["", "## Full normalized mean and P10 measurements", "",
              "| Geometry | Width | Phase | N | Mean t/N | P10 t/N |", "|---|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['family']} | {r['width']} | {r['phase']} | {r['resolution']} | {r['normalized']['mean_strut_thickness']:.9f} | {r['normalized']['p10_strut_thickness']:.9f} |")
    (out / "ANALYTIC_CONTROLS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_report(out, summary, changes, manifest):
    lines = ["# Pipeline v0.4.2 — thickness convergence verification", "",
             f"Scientific status: **{summary['scientific_status']}**. Generator v0.4.1 and evaluator v1.1 unchanged. No CAD started.", "",
             "## Acceptance", "", "| Gate | Result |", "|---|---|"]
    lines += [f"| {k} | {'PASS' if v else 'HOLD'} |" for k, v in summary["gates"].items()]
    lines += ["", "## All ten high-resolution pairs", "",
              f"P10 limit from controls: {summary['p10_calibration']['effective_limit'] * 100:.6f}%; mean and pore limits: 3%.", "",
              "| Design | Seed | Mean % | P10 % | Pore % | All pair gates |", "|---:|---:|---:|---:|---:|---|"]
    for r in summary["pairs"]:
        if not r["available"]:
            lines.append(f"| {r['design_id']} | {r['seed']} | N/A | N/A | N/A | FAILED |")
        else:
            vals = " | ".join(f"{100*r['errors'][k]:.6f}" for k in DIMENSIONS)
            lines.append(f"| {r['design_id']} | {r['seed']} | {vals} | {'PASS' if r['pass'] else 'HOLD'} |")
    lines += ["", "## Successive changes (signed, lower-resolution denominator)", "",
              "| Design | Seed | Step | Mean % | P10 % | Pore % |", "|---:|---:|---|---:|---:|---:|"]
    for r in changes:
        vals = " | ".join(f"{r[k]:+.6f}" if r[k] is not None else "N/A" for k in DIMENSIONS)
        lines.append(f"| {r['design_id']} | {r['seed']} | {r['low']} → {r['high']} | {vals} |")
    lines += ["", "## Sampling versus generator contribution", "",
              "Fixed-2048 controls vary sampling only. Agreement supports a dominant sampling pattern; it does not prove zero generator discretization error.", "",
              "| Design | Seed | Native mean step % | Fixed-geometry mean step % | Residual percentage points | Dominant pattern |",
              "|---:|---:|---:|---:|---:|---|"]
    for r in summary["sampling_attribution"]:
        lines.append(f"| {r['design_id']} | {r['seed']} | {r['native_mean_step_percent']:+.6f} | {r['fixed_geometry_mean_step_percent']:+.6f} | {r['residual_percentage_points']:+.6f} | {r['dominant_sampling_pattern']} |")
    lines += ["", "## Repaired neck screen", "",
              "| Design | Seed | N | Added pixels | Solid pixels tested individually | Articulation pixels | Local screen |",
              "|---:|---:|---:|---:|---:|---:|---|"]
    for r in summary["repairs"]:
        lines.append(f"| {r['design_id']} | {r['seed']} | {r['resolution']} | {r['added_pixels']} | {r['tested_solid_pixels']} | {len(r['single_pixel_articulations_yx'])} | {'PASS' if r['local_neck_screen_pass'] else 'HOLD'} |")
    lines += ["", "Boundary clipping means the occupied neck depth can be roughly HALF the nominal capsule diameter. Inspect `repair_inspection.json` and the native-pixel repair figures.",
              "A no-one-pixel-neck result is NOT mechanical, mesh-quality or manufacturing certification: physical scale, loads, material and minimum feature size are unspecified.", "",
              "## Preservation and scope", "", f"Historical inventories unchanged: {manifest['historical_unchanged']}. Code unchanged: {manifest['code_unchanged']}.",
              "Previous v0.4.1 HOLD remains historical evidence. The new criterion was recorded before all ten new native diagnostics.",
              "2048 is a diagnostic grid, not a newly adopted production resolution. This milestone produces no CAD, vector geometry, mesh, STEP or STL.",
              "Execution was on macOS. PowerShell reproduction commands are documented separately; Windows execution is not claimed."]
    (out / "SCIENTIFIC_ACCEPTANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_repair(raw, repaired, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    added = repaired != raw
    points = np.argwhere(added)
    margin = max(4, int(raw.shape[0] * .012))
    low = np.maximum(0, points.min(axis=0) - margin)
    high = np.minimum(raw.shape, points.max(axis=0) + margin + 1)
    crop = tuple(slice(a, b) for a, b in zip(low, high))
    rgb = np.repeat(repaired[crop][..., None], 3, axis=-1).astype(float)
    rgb[added[crop]] = [1, .2, .2]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.5), constrained_layout=True)
    for ax, a, title in zip(axes, (raw[crop], repaired[crop], rgb), ("Raw rejected corner", "Repaired", "Added pixels in red")):
        ax.imshow(a, cmap="gray", vmin=0, vmax=1, interpolation="nearest")
        ax.set_title(title); ax.set_xlabel("Local pixel column"); ax.set_ylabel("Local pixel row")
    fig.suptitle(f"N={raw.shape[0]}; crop origin (y,x)={low.tolist()}")
    fig.savefig(path, dpi=180); plt.close(fig)


def plot_convergence(out, rows, controls):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    for design, seed in sorted({(j["design_id"], j["seed"]) for j in rows}):
        group = sorted((j for j in rows if (j["design_id"], j["seed"]) == (design, seed) and j["status"] == "COMPLETE"), key=lambda j: j["resolution"])
        for axis, key in zip(axes, DIMENSIONS[:2]):
            axis.plot([j["resolution"] for j in group], [j["evaluation"]["normalized"]["normalized_" + key] for j in group],
                      marker="o", label=f"D{design}/S{seed}")
            axis.set(xlabel="Resolution N", ylabel=key + " / N", xticks=LEVELS)
    axes[0].legend(fontsize=7, ncol=2)
    fig.savefig(out / "thickness_convergence.png", dpi=180); plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("prepare", help="Record protocol and calibrate analytic controls before new native results")
    p.add_argument("--previous-run", type=Path, required=True)
    p.add_argument("--v04-run", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    r = sub.add_parser("run", help="Run ten isolated 2048 cases against the prepared protocol")
    r.add_argument("output_dir", type=Path)
    r.add_argument("--timeout", type=float, default=600)
    args = parser.parse_args(argv)
    if args.stage == "prepare":
        prepare(args.previous_run, args.v04_run, args.output_dir)
        return 0
    if not np.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("timeout must be finite and positive")
    result = run(args.output_dir, args.timeout)
    return 0 if result["scientific_status"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
