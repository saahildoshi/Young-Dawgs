"""Registered v0.5D1 study using only authenticated saved sources."""
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import time
import traceback
import tracemalloc

import numpy as np
import shapely

from . import exporter, importer
from .diagnostics import real_precision, run_controls, write_json
from .verification import compare_geometry, compare_protected, compare_repairs
from ..manifold.morphology import compare_frozen
from ..validation.checks import (authenticate, digest, independent_raster, raster_metrics,
                                 serialization_check)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "experiments/pipeline_v0.5/svg_export_validation/run_001"
C1 = ROOT / "experiments/pipeline_v0.5/scientific_requalification/run_001"


def read(path):
    return json.loads(Path(path).read_text())


def authenticate_source(f):
    for path, expected in [(f["source_geometry_path"], f["source_geometry_sha256"]),
                           (f["canonical_raster_path"], f["canonical_raster_sha256"]),
                           (f["source_manifest_path"], f["source_manifest_sha256"]),
                           (f["native_generation_manifest_path"], f["native_generation_manifest_sha256"]),
                           (f["qualification_path"], f["qualification_sha256"])]:
        authenticate(ROOT / path, expected)
    for key, path in f["source_provenance"]["paths"].items():
        authenticate(ROOT / path, f["source_provenance"]["sha256"][key])
    if f["prior_validation_path"]:
        authenticate(ROOT / f["prior_validation_path"], f["prior_validation_sha256"])


def freeze():
    target = OUT / "protocol/FINAL_FREEZE.json"
    if target.exists() or any((OUT / "exports").glob("*.svg")):
        raise FileExistsError("Protocol/study is already frozen or executed")
    protocol = read(OUT / "protocol/PROTOCOL.json")
    controls = sorted((OUT / "precision_controls").glob("synthetic_run_*/SUMMARY.json"))
    if not controls or not read(controls[-1])["passed"]:
        raise ValueError("Successful persistent synthetic controls required")
    for f in protocol["fixtures"]:
        authenticate_source(f)
    code = sorted((ROOT / "metamaterial_eval/geometry").rglob("*.py"))
    code += [ROOT / "tests/test_svg_roundtrip.py", ROOT / "validation/evaluators/evaluator_v1_1.py",
             ROOT / "metamaterial_eval/pipeline/resolution_worker.py"]
    record = {"frozen_utc": datetime.now(timezone.utc).isoformat(),
              "protocol_sha256": digest(OUT / "protocol/PROTOCOL.json"),
              "code_sha256": {str(p.relative_to(ROOT)): digest(p) for p in code},
              "synthetic_summary_path": str(controls[-1].relative_to(ROOT)), "synthetic_summary_sha256": digest(controls[-1]),
              "real_svg_exports_opened": False, "real_fixtures": [f["id"] for f in protocol["fixtures"]],
              "source_scientific_HOLD_unchanged": True}
    write_json(target, record)
    for p in code:
        dst = OUT / "code_snapshot" / p.relative_to(ROOT); dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(p, dst)
    print("Frozen protocol/code before four real SVG exports", flush=True)


def verify_freeze():
    record = read(OUT / "protocol/FINAL_FREEZE.json")
    authenticate(OUT / "protocol/PROTOCOL.json", record["protocol_sha256"])
    authenticate(ROOT / record["synthetic_summary_path"], record["synthetic_summary_sha256"])
    for p, h in record["code_sha256"].items():
        authenticate(ROOT / p, h)
    return read(OUT / "protocol/PROTOCOL.json")


def render_svg(svg, dest):
    """Actual saved SVG interpreted by bundled Sharp/libvips, display only."""
    bundle = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node"
    node = os.environ.get("YOUNG_DAWGS_NODE", str(bundle / "bin/node"))
    sharp = os.environ.get("YOUNG_DAWGS_SHARP", str(bundle / "node_modules/sharp"))
    script = "const s=require(process.argv[1]);s(process.argv[2],{density:72}).resize(1024,1024).flatten({background:'#ffffff'}).png().toFile(process.argv[3]).then(()=>process.stdout.write(JSON.stringify(s.versions))).catch(e=>{console.error(e);process.exit(1)});"
    result = subprocess.run([node, "-e", script, sharp, str(svg), str(dest)], capture_output=True, text=True, check=True)
    return {"renderer": "Sharp/libvips actual SVG input", "versions": json.loads(result.stdout),
            "node_executable": node, "module": sharp, "scientific_raster": False,
            "antialiasing": "Display antialiasing only; binary validation uses separate native-center predicates."}


def _descriptors(f, mask, rec, *, fresh):
    original_path = C1 / f["source_stage"] / "geometry" / f["source_fixture"] / "original_frozen_descriptors.json"
    initial = read(OUT / "verification/INITIAL_INVENTORY.json")
    authenticate(original_path, initial[str(original_path.relative_to(ROOT))])
    original = read(original_path)
    if fresh or not np.array_equal(mask, rec):
        result = compare_frozen(mask, rec)
        result["execution"] = "Fresh original and independently SVG-rasterized evaluator-v1.1 calls"
    else:
        result = {"status": "PASS", "execution": "Authenticated deterministic frozen result reused after independently identical arrays",
                  "raw_descriptor_reference": str(original_path.relative_to(ROOT)), "raw_descriptor_sha256": digest(original_path),
                  "raw_descriptor_pixel_sha256": sha256(mask.tobytes()).hexdigest(),
                  "all_scalar_and_full_S2_L_arrays_identical_by_input_identity": True,
                  "evaluator_sha256": original["raw"]["evaluator_sha256"],
                  "p10_caveat": "Frozen whole-mask P10 unchanged; v0.4.3 tail/neck qualification is scoped and original v0.4.2 calibration remains FAILED."}
    result["canonical_raster_sha256"] = f["canonical_raster_sha256"]
    result["raster_exact"] = bool(np.array_equal(mask, rec))
    result["continuous_equivalence_established_by_descriptors"] = False
    return result


def _metadata(f, protocol):
    return {"source_id": f["id"], "source_fixture": f["source_fixture"], "source_state": f["source_state"],
            "source_geometry_path": f["source_geometry_path"], "source_geometry_sha256": f["source_geometry_sha256"],
            "canonical_raster_path": f["canonical_raster_path"], "canonical_raster_sha256": f["canonical_raster_sha256"],
            "parameters": f["parameters"], "seed": f["seed"], "design": f["design"], "resolution": f["resolution"],
            "source_scientific_qualification": protocol["inherited_statuses"], "contact_regularization_count": f["contact_count"],
            "simplification_epsilon": f["simplification_epsilon"], "physical_scale": None,
            "source_qualification_path": f["qualification_path"], "source_qualification_sha256": f["qualification_sha256"],
            "source_manifest_path": f["source_manifest_path"], "source_manifest_sha256": f["source_manifest_sha256"],
            "importer_version": importer.VERSION, "importer_code_sha256": digest(Path(importer.__file__)),
            "protocol_sha256": digest(OUT / "protocol/PROTOCOL.json"), "run_identifier": "v0.5D1/run_001",
            "generator_source_sha256": f["generator_sha256"], "native_renderer_sha256": f["native_renderer_sha256"],
            "native_generation_manifest_path": f["native_generation_manifest_path"], "native_generation_manifest_sha256": f["native_generation_manifest_sha256"],
            "native_source_provenance": f["source_provenance"], "no_new_geometry_operation": True}


def execute():
    protocol = verify_freeze(); marker = OUT / "verification/REAL_EXECUTION.json"
    if marker.exists():
        raise FileExistsError("Real study already executed; preserve prior outcomes")
    write_json(marker, {"started_utc": datetime.now(timezone.utc).isoformat(), "expected_fixtures": 4})
    began = time.perf_counter(); rows, failures = [], []
    for index, f in enumerate(protocol["fixtures"]):
        name = f["id"]; case_start = time.perf_counter(); timings = {}
        try:
            t = time.perf_counter(); authenticate_source(f)
            source = shapely.from_wkb((ROOT / f["source_geometry_path"]).read_bytes())
            exact = shapely.from_wkb((ROOT / f["source_provenance"]["paths"]["exact"]).read_bytes())
            mask = np.load(ROOT / f["canonical_raster_path"], allow_pickle=False)
            assert mask.dtype == np.uint8 and mask.shape == (1024, 1024) and np.isin(mask, [0, 1]).all()
            qualification = read(ROOT / f["qualification_path"]); assert qualification["accepted"]
            timings["source_loading_authentication_seconds"] = time.perf_counter() - t
            write_json(OUT / "source_manifests" / (name + ".json"), f)
            svg = OUT / "exports" / (name + ".svg"); side = svg.with_suffix(".json")
            t = time.perf_counter(); m = exporter.export_saved(ROOT / f["source_geometry_path"], f["source_geometry_sha256"], svg, side, _metadata(f, protocol)); timings["export_seconds"] = time.perf_counter() - t
            t = time.perf_counter(); result = importer.read_svg(svg, side, expected_source_sha256=f["source_geometry_sha256"])
            timings.update(result["timings"]); imported = result["geometry"]
            folder = OUT / "imports" / name; folder.mkdir()
            write_json(folder / "parsed_subpaths.json", result["rings"]); write_json(folder / "inferred_nesting.json", result["nesting"])
            serialization = serialization_check(imported, folder, "G4")
            t = time.perf_counter(); comparison = compare_geometry(source, imported, domain=1024)
            timings["continuous_geometry_comparison_seconds"] = time.perf_counter() - t
            t = time.perf_counter(); repairs = compare_repairs(source, imported, exact, qualification)
            guard, probes = None, []
            setting = "epsilon_0p50" if f["source_state"] == "G3" else "epsilon_0p00"
            old_case = C1 / f["source_stage"] / "parameter_holdouts" / f["source_fixture"] / setting
            prior = read(old_case / "frozen_B2_qualification.json")
            probes = prior["metrics"]["features"]["natural_necks"]
            if f["source_state"] == "G3":
                validation = read(ROOT / f["prior_validation_path"]); p = validation["provenance"]
                authenticate(ROOT / p["guard_input_path"], p["guard_input_sha256"])
                guard = shapely.from_wkb((ROOT / p["guard_input_path"]).read_bytes())
            protected = compare_protected(source, imported, guard, probes)
            timings["registered_repair_feature_seconds"] = time.perf_counter() - t
            t = time.perf_counter(); rec, ties = independent_raster(imported, 1024); raster = raster_metrics(mask, rec)
            raster["boundary_center_ties"] = ties; raster["canonical_topology"] = raster_metrics(mask, mask)
            timings["rasterization_comparison_seconds"] = time.perf_counter() - t
            np.save(OUT / "raster_reconstruction" / (name + ".npy"), rec, allow_pickle=False)
            t = time.perf_counter(); descriptors = _descriptors(f, mask, rec, fresh=index == 0)
            timings["scientific_evaluation_seconds"] = time.perf_counter() - t
            t = time.perf_counter(); repeated_svg = exporter.serialize(source, _metadata(f, protocol))[0]
            repeated_import = importer.read_svg(svg, side, expected_source_sha256=f["source_geometry_sha256"])["geometry"]
            determinism = {"svg_bytes_identical": repeated_svg == svg.read_bytes(), "imported_wkb_identical": repeated_import.wkb == imported.wkb}
            timings["repeat_validation_seconds"] = time.perf_counter() - t
            preview = OUT / "previews" / name; preview.mkdir()
            t = time.perf_counter(); renderer = render_svg(svg, preview / "svg_rendered.png"); timings["display_svg_rendering_seconds"] = time.perf_counter() - t
            gates = {**comparison["gates"], "serialization_reload": serialization["passed"], "repairs_exact": repairs["passed"],
                     "protected_features": protected["passed"], "zero_raster_xor": raster["xor"] == 0, "frozen_descriptors": descriptors["status"] == "PASS",
                     "determinism": all(determinism.values()), "status_propagation": result["metadata"]["source_scientific_qualification"] == protocol["inherited_statuses"],
                     "canonical_precision": result["metadata"]["canonical_significant_digits"] == 17 and result["metadata"]["diagnostic_precision"] is False}
            passed = all(gates.values())
            statuses = {"serialization": "EXPORT_SERIALIZATION_PASS", "parse": "SVG_PARSE_PASS",
                        "continuous": "CONTINUOUS_ROUNDTRIP_PASS" if comparison["passed"] else "HOLD",
                        "raster": "RASTER_ROUNDTRIP_PASS" if raster["xor"] == 0 else "HOLD",
                        "manifold": "MANIFOLD_PRESERVED" if comparison["dedicated_manifold"]["manifold"] else "HOLD",
                        **protocol["inherited_statuses"], "export_roundtrip": "SVG_EXPORT_ROUNDTRIP_PASS_TESTED_FIXTURE" if passed else "HOLD"}
            timings["total_validation_seconds"] = time.perf_counter() - case_start
            validation = {"fixture": name, "source_state": f["source_state"], "passed": passed, "gates": gates, "failed_gates": [k for k, v in gates.items() if not v],
                          "statuses": statuses, "continuous": comparison, "repairs": repairs, "protected": protected, "raster": raster,
                          "descriptors": descriptors, "determinism": determinism, "import_serialization": serialization,
                          "imported_geometry_sha256": digest(folder / "G4.wkb"), "timings": timings, "preview_renderer": renderer,
                          "process_lifetime_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if platform.system() == "Darwin" else 1024)}
            m.update(imported_geometry_sha256=validation["imported_geometry_sha256"], dependency_environment=read(OUT / "protocol/environment.json"),
                     execution_utc=datetime.now(timezone.utc).isoformat(), roundtrip_validation=statuses["export_roundtrip"], validation=validation)
            write_json(side, m); write_json(OUT / "continuous_metrics" / (name + ".json"), validation)
            write_json(OUT / "topology" / (name + ".json"), {"topology": comparison["topology"], "dedicated_manifold": comparison["dedicated_manifold"], "repairs": repairs})
            rows.append({"fixture": name, "source_state": f["source_state"], "vertices": f["vertices"], "holes": f["source_integrity"]["holes"],
                         "svg_bytes": m["svg_bytes"], "svg_sha256": m["svg_sha256"], "imported_geometry_sha256": validation["imported_geometry_sha256"],
                         "symmetric_area": comparison["area"]["symmetric"], "net_area": comparison["area"]["net_area"], "displacement_upper": comparison["distance"]["upper"],
                         "raster_xor": raster["xor"], "repair_count": repairs["registered_count"], "timings": timings, "passed": passed, "statuses": statuses})
            print(name, statuses["export_roundtrip"], "vertices", f["vertices"], "holes", f["source_integrity"]["holes"], "SVG bytes", m["svg_bytes"], flush=True)
        except Exception:
            failure = {"fixture": name, "passed": False, "traceback": traceback.format_exc(), "source_retained": True, "replacement": False}
            write_json(OUT / "verification" / (name + "_ERROR.json"), failure); failures.append(failure); rows.append(failure)
            print("HOLD", name, failure["traceback"], flush=True)
    summary = {"pipeline_version": "v0.5D1", "expected_fixtures": 4, "rows": rows, "errors": failures,
               "status": "SVG_EXPORT_ROUNDTRIP_PASS_TESTED_FIXTURES" if len(rows) == 4 and all(r["passed"] for r in rows) else "HOLD",
               "inherited_statuses": protocol["inherited_statuses"], "elapsed_seconds": time.perf_counter() - began,
               "process_lifetime_peak_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if platform.system() == "Darwin" else 1024),
               "full_study_tracemalloc": False, "no_new_source_generation": True, "no_geometry_repairs_or_simplification": True}
    write_json(OUT / "summary/REAL_STUDY.json", summary)
    print("Real study complete", summary["status"], flush=True)


def profile():
    protocol = verify_freeze(); records = []
    for f in protocol["fixtures"]:
        source = shapely.from_wkb((ROOT / f["source_geometry_path"]).read_bytes())
        tracemalloc.start(); t = time.perf_counter(); payload = exporter.serialize(source, _metadata(f, protocol))[0]
        export_seconds = time.perf_counter() - t; _, export_peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        tracemalloc.start(); t = time.perf_counter(); result = importer.read_svg(OUT / "exports" / (f["id"] + ".svg"), OUT / "exports" / (f["id"] + ".json"), expected_source_sha256=f["source_geometry_sha256"])
        import_seconds = time.perf_counter() - t; _, import_peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
        records.append({"fixture": f["id"], "instrumented_export_seconds": export_seconds, "instrumented_import_seconds": import_seconds,
                        "export_traced_peak_bytes": export_peak, "import_traced_peak_bytes": import_peak,
                        "svg_repeat_identical": sha256(payload).hexdigest() == result["svg_sha256"]})
    write_json(OUT / "performance/TRACED_STAGE_PROFILE.json", {"records": records, "source_loading_excluded": True,
               "traced_memory_caveat": "Selected exporter/importer Python allocations only; native GEOS and prior source allocations are incompletely covered. Not a full-study traced peak."})
    print("Targeted tracing completed", flush=True)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("action", choices=["controls", "freeze", "run", "precision", "profile"]); action = parser.parse_args().action
    if action == "controls":
        run_controls(OUT)
    elif action == "freeze":
        freeze()
    elif action == "run":
        execute()
    elif action == "precision":
        real_precision(OUT, verify_freeze(), ROOT)
    else:
        profile()


if __name__ == "__main__":
    main()
