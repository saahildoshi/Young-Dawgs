"""Separate v0.4 matched-design convergence experiment; never edits source runs."""
from __future__ import annotations

from pathlib import Path
import sys

import numpy as np

from metamaterial_eval.generators import native_resolution as model, v03_baseline
from .execution import run_subprocess
from .resolution import validate_resolution
from .scripts import sha256_file
from .state import read_json, write_json, utc_now


def inventory(root):
    return {p.relative_to(root).as_posix(): sha256_file(p) for p in sorted(root.rglob("*"))
            if p.is_file() and "__pycache__" not in p.parts}


def select_designs(plan, count=5):
    """Select existing center, density extremes and opposed scale corners."""
    unique = {r["design_id"]: r for r in plan["samples"]}
    ids = sorted(unique)
    if count < 1 or count > len(ids):
        raise ValueError("Requested representative design count is not available.")
    controls = ("solid_fraction_target", "strut_scale", "pore_scale")
    normalized = np.array([[(unique[i]["requested"][c] - plan["bounds"][c][0]) /
                           (plan["bounds"][c][1] - plan["bounds"][c][0]) for c in controls] for i in ids])
    scores = [("nearest envelope center", np.sum((normalized - .5)**2, axis=1)),
              ("low solid fraction", normalized[:, 0]), ("high solid fraction", -normalized[:, 0]),
              ("low strut / high pore", normalized[:, 1] - normalized[:, 2]),
              ("high strut / low pore", normalized[:, 2] - normalized[:, 1])]
    chosen = []
    reasons = {}
    for reason, score in scores:
        for index in np.argsort(score, kind="stable"):
            if ids[index] not in chosen:
                chosen.append(ids[index]); reasons[str(ids[index])] = reason; break
        if len(chosen) >= count:
            break
    for i in ids:
        if len(chosen) >= count:
            break
        if i not in chosen:
            chosen.append(i); reasons[str(i)] = "additional existing LHS point"
    return {"design_ids": chosen, "selection_reasons": reasons,
            "bounds": plan["bounds"], "samples": [r for r in plan["samples"] if r["design_id"] in chosen]}


def validate_resolutions(source_run, output_dir, resolutions=(256, 512, 1024), designs=5, timeout=600):
    source_run, output_dir = Path(source_run).resolve(), Path(output_dir).resolve()
    resolutions = tuple(validate_resolution(n) for n in resolutions)
    if 256 not in resolutions or len(set(resolutions)) != len(resolutions):
        raise ValueError("Include 256 once as the regression baseline; resolutions must be unique.")
    if source_run == output_dir or source_run in output_dir.parents:
        raise ValueError("Validation must be outside historical source experiment.")
    if not np.isfinite(timeout) or timeout <= 0:
        raise ValueError("Timeout must be finite and positive.")
    if sha256_file(source_run / "generator.py") != model.SOURCE_V03_SHA256:
        raise ValueError("This native port applies only to the audited exploration_test_01 generator hash.")
    if sha256_file(Path(v03_baseline.__file__)) != model.SOURCE_V03_SHA256:
        raise ValueError("Preserved v0.3 baseline snapshot changed.")
    source_manifest = read_json(source_run / "exploration_manifest.json")
    if source_manifest["status"] != "COMPLETE":
        raise ValueError("Use a completed v0.3 experiment.")
    plan = read_json(source_run / "design_plan.json")
    selected = select_designs(plan, designs)
    before = inventory(source_run)
    output_dir.mkdir(parents=True, exist_ok=False)
    write_json(output_dir / "selected_designs.json", selected)
    manifest = {"pipeline_version": "0.4.0", "source_run": str(source_run),
                "created_at_utc": utc_now(), "resolutions": list(resolutions),
                "source_v03_sha256": model.SOURCE_V03_SHA256,
                "native_generator_sha256": sha256_file(Path(model.__file__)),
                "source_inventory_before": before, "status": "RUNNING", "jobs": []}
    write_json(output_dir / "manifest.json", manifest)
    for row in selected["samples"]:
        for n in resolutions:
            relative = Path(f"design_{row['design_id']:03d}") / f"seed_{row['seed']:03d}" / str(n)
            historical = source_run / source_manifest["latest_attempt"] / "samples" / (row["sample_id"] + ".npy")
            job = {**row, "resolution": n, "historical_sample": str(historical)}
            job_path = output_dir / "jobs" / f"{row['sample_id']}_{n}.json"
            write_json(job_path, job)
            destination = output_dir / relative
            result = run_subprocess([sys.executable, str(Path(__file__).with_name("resolution_worker.py")),
                                     str(job_path), str(destination)], cwd=output_dir,
                                     log_dir=output_dir / "logs" / f"{row['sample_id']}_{n}", timeout_seconds=timeout)
            record_path = destination / "manifest.json"
            if record_path.exists():
                record = read_json(record_path)
            else:
                record = {**job, "status": "FAILED", "error": "Worker failed or timed out before writing results.",
                          "execution": result.to_dict()}
                write_json(record_path, record)
            record["relative_directory"] = relative.as_posix()
            manifest["jobs"].append(record)
            write_json(output_dir / "manifest.json", manifest)
            print(f"design {row['design_id']} seed {row['seed']} N={n}: {record['status']}", flush=True)
    manifest["historical_unchanged"] = before == inventory(source_run)
    manifest["status"] = "COMPLETE" if all(j["status"] == "COMPLETE" for j in manifest["jobs"]) else "COMPLETED_WITH_FAILURES"
    write_json(output_dir / "manifest.json", manifest)
    from .resolution_report import build_report
    build_report(output_dir, manifest, selected)
    return manifest
