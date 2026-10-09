"""One profiled native render per process; frozen evaluator definitions reused."""
from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import json
import sys
import time
import tracemalloc
import traceback

import numpy as np
from PIL import Image

from metamaterial_eval.generators import native_resolution as model
from metamaterial_eval.generators import v03_baseline
from metamaterial_eval.pipeline.config import PipelineConfig, default_evaluator_path
from metamaterial_eval.pipeline.evaluator import extract_target_descriptors, load_evaluator
from metamaterial_eval.pipeline.resolution import normalized_dimensions, normalized_radii, validate_resolution
from metamaterial_eval.pipeline.scripts import sha256_file
from metamaterial_eval.pipeline.state import read_json, write_json


def evaluate_native(array):
    n = validate_resolution(array.shape[0])
    if array.shape != (n, n) or array.dtype != np.uint8 or not np.isin(array, [0, 1]).all():
        raise ValueError("Expected a square native uint8 binary array.")
    radii = normalized_radii(n)
    maximum = int(np.ceil(n / 4))
    config = PipelineConfig(image_shape=(n, n), max_r=maximum,
                            sample_radii=tuple(radii["pixel_radii"]),
                            topology_mode="single_connected_network")
    raw = extract_target_descriptors(array, config, default_evaluator_path())
    rho = np.arange(65) / 256
    full_rho = np.asarray(raw["curves"]["r"]) / n
    curves = {key: np.interp(rho, full_rho, raw["curves"][key]).tolist()
              for key in ("s2", "lineal_path", "l_x", "l_y", "l_45", "l_135")}
    return {"raw": raw, "normalized": normalized_dimensions(raw, n),
            "common_rho": rho.tolist(), "common_curves": curves, "sampled_radii": radii}


def perform_job(job, directory):
    """Persist failures as evidence; successful outputs are never repaired."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    n = job["resolution"]
    record = {**job, "pipeline_version": "0.4.0", "resolution_scale": n / 256,
              "generator_sha256": sha256_file(Path(model.__file__)),
              "source_v03_generator_sha256": sha256_file(Path(v03_baseline.__file__)),
              "evaluator_sha256": sha256_file(default_evaluator_path()),
              "environment": {"python": sys.version, **{k: version(k) for k in
                              ("numpy", "scipy", "scikit-image", "Pillow", "matplotlib")}},
              "status": "FAILED"}
    try:
        model._select.cache_clear()  # each timing includes baseline candidate selection
        tracemalloc.start()
        start = time.perf_counter()
        array = model.generate_microstructure(job["seed"], **job["requested"], resolution=n)
        record["generation_seconds"] = time.perf_counter() - start
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        record["peak_traced_generation_bytes"] = peak
        record["memory_definition"] = "tracemalloc peak during generation; includes traced NumPy allocations, not total process RSS"
        record["candidate_index"] = model._select(job["seed"], job["requested"]["solid_fraction_target"],
                                                job["requested"]["strut_scale"], job["requested"]["pore_scale"])[2]
        np.save(directory / "microstructure.npy", array, allow_pickle=False)
        Image.fromarray(array * 255).save(directory / "microstructure.png")
        # Repeat the native rendering with the same accepted latent realization.
        repeated = model.generate_microstructure(job["seed"], **job["requested"], resolution=n)
        record["exact_repeat"] = bool(np.array_equal(array, repeated))
        start = time.perf_counter()
        record["evaluation"] = evaluate_native(array)
        record["evaluation_seconds"] = time.perf_counter() - start
        if n == 256:
            original = v03_baseline.generate_microstructure(job["seed"], **job["requested"])
            saved = np.load(job["historical_sample"], allow_pickle=False) if job.get("historical_sample") else None
            record["regression"] = {"old_generator_bitwise_equal": bool(np.array_equal(array, original)),
                                    "saved_output_bitwise_equal": bool(np.array_equal(array, saved)) if saved is not None else None,
                                    "old_generator_pixel_disagreement": float(np.mean(array != original)),
                                    "saved_output_pixel_disagreement": float(np.mean(array != saved)) if saved is not None else None}
        record["files"] = {name: {"sha256": sha256_file(directory / name), "bytes": (directory / name).stat().st_size}
                           for name in ("microstructure.npy", "microstructure.png")}
        record["topology_valid"] = record["evaluation"]["raw"]["valid"]
        record["status"] = "COMPLETE" if record["exact_repeat"] and record["topology_valid"] else "FAILED"
    except Exception:
        record["error"] = traceback.format_exc()
        if tracemalloc.is_tracing():
            tracemalloc.stop()
    write_json(directory / "timing.json", {k: record.get(k) for k in
               ("generation_seconds", "evaluation_seconds", "peak_traced_generation_bytes", "memory_definition", "files")})
    write_json(directory / "manifest.json", record)
    if "evaluation" in record:
        write_json(directory / "evaluation/metrics.json", record["evaluation"])
    return record


if __name__ == "__main__":
    job = read_json(Path(sys.argv[1]))
    result = perform_job(job, Path(sys.argv[2]))
    print(json.dumps({"status": result["status"], "resolution": job["resolution"]}))
    sys.exit(0 if result["status"] == "COMPLETE" else 2)
