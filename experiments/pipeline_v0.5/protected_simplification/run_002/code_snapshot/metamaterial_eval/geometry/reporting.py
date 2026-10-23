"""Read-only historical fixture runner and reproducible baseline reports."""
from importlib.metadata import version
from pathlib import Path
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
import tracemalloc

import numpy as np
import shapely

from .inputs import load_binary_reference, sha256_file
from .conversion import convert_exact, geometry_bytes
from .planar import build_exact_planar_geometry, rasterize_exact_geometry
from .raster import rasterize_boundary_loops
from .figures import write_figures

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = (("fixture_A_design000_seed000", "design_000/seed_000"),
            ("fixture_B_design009_seed001", "design_009/seed_001"))


def write_json(path, data):
    path.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+"\n", encoding="utf-8")


def repository_inventory(root, output):
    excluded = {".git", ".venv", ".venv-macos", "__pycache__", ".pytest_cache", "metamaterial_eval.egg-info"}
    return {p.relative_to(root).as_posix():sha256_file(p) for p in sorted(root.rglob('*'))
            if p.is_file() and not excluded.intersection(p.relative_to(root).parts)
            and not p.is_relative_to(output)}


def environment():
    return {"os":platform.platform(), "python":sys.version,
            "packages":{p:version(p) for p in ("numpy","scipy","shapely","Pillow","matplotlib","scikit-image","pytest")},
            "geos":shapely.geos_version_string, "windows_tested":False}


def run_case(root, output, identifier, relative):
    folder = output/identifier; folder.mkdir()
    source = root/'experiments/pipeline_v0.4.1/resolution_validation'/relative/'1024'
    old = json.loads((source/'manifest.json').read_text())
    mask_path, png_path = source/'microstructure.npy', source/'microstructure.png'
    for p in (mask_path,png_path):
        if sha256_file(p) != old['files'][p.name]['sha256']:
            raise ValueError(f"Historical manifest/hash mismatch: {p.relative_to(root)}")
    mask = load_binary_reference(mask_path,png_path)
    provenance = {"source_npy":mask_path.relative_to(root).as_posix(),
                  "source_png":png_path.relative_to(root).as_posix(),
                  "source_manifest":(source/'manifest.json').relative_to(root).as_posix(),
                  "source_manifest_sha256":sha256_file(source/'manifest.json'),
                  "input_sha256":sha256_file(mask_path), "png_sha256":sha256_file(png_path),
                  "pixel_sha256":hashlib.sha256(mask.tobytes()).hexdigest(),
                  **{k:old[k] for k in ("design_id","seed","requested","generator_version","generator_sha256",
                                       "native_renderer_sha256","source_v03_generator_sha256","evaluator_sha256","topology_repair")}}
    if provenance['pixel_sha256'] != old['topology_repair']['repaired_pixel_sha256']:
        raise ValueError("Saved repaired pixel hash mismatch.")
    write_json(folder/'input_provenance.json',provenance)
    tracemalloc.start()
    start = time.perf_counter(); result = convert_exact(mask); elapsed = time.perf_counter()-start
    _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    # Warm, uninstrumented repeat reported separately; source hashes define code.
    start = time.perf_counter(); repeated = convert_exact(mask); repeat_seconds = time.perf_counter()-start
    payload = geometry_bytes(result['document'])
    deterministic = payload == geometry_bytes(repeated['document'])
    (folder/'exact_boundaries.json').write_bytes(payload)
    np.save(folder/'exposed_edges.npy',result['edges'],allow_pickle=False)
    np.save(folder/'reconstructed.npy',result['reconstructed'],allow_pickle=False)
    if result['geometry'] is not None:
        (folder/'polygon_candidate.wkb').write_bytes(shapely.to_wkb(result['geometry'],byte_order=1))
    # Re-read actual persisted geometry, rather than proving only an in-memory path.
    persisted = json.loads((folder/'exact_boundaries.json').read_bytes())
    disk_rec = rasterize_boundary_loops(persisted['loops'],persisted['resolution'])
    disk_equal = bool(np.array_equal(mask,disk_rec))
    polygon_disk_equal = None
    if result['validity']['ogc_valid']:
        wkb = shapely.from_wkb((folder/'polygon_candidate.wkb').read_bytes())
        polygon_disk_equal = bool(np.array_equal(mask,rasterize_exact_geometry(wkb,len(mask))))
    np.save(folder/'polygon_reconstructed.npy',rasterize_exact_geometry(result['geometry'],len(mask)),allow_pickle=False) if result['validity']['ogc_valid'] else None
    write_json(folder/'boundary_diagnostics.json',result['boundaries'])
    write_json(folder/'geometry_validity.json',result['validity'])
    write_json(folder/'comparison.json',result['comparison'])
    rss = None
    try:
        import resource
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if platform.system() != 'Darwin': rss *= 1024
    except ImportError:
        pass
    timing = {"profiled_conversion_seconds":elapsed,"uninstrumented_repeat_seconds":repeat_seconds,
              "peak_traced_conversion_bytes":peak,"process_lifetime_peak_rss_bytes":rss,
              "memory_definition":"tracemalloc peak includes tracked Python/NumPy allocations; excludes untracked GEOS allocations. RSS is process lifetime peak before figures, not conversion-only incremental memory.",
              "exact_boundary_json_bytes":len(payload),
              "polygon_wkb_bytes":(folder/'polygon_candidate.wkb').stat().st_size if result['geometry'] is not None else None}
    write_json(folder/'performance.json',timing)
    windows = write_figures(folder,mask,result,old['topology_repair'])
    write_json(folder/'visual_windows.json',windows)
    status = result['status'] if deterministic and disk_equal and polygon_disk_equal is not False else 'HOLD_REPRODUCIBILITY'
    report = {"fixture":identifier,"status":status,"provenance":provenance,"input_shape":list(mask.shape),
              "coordinates":result['document']['coordinates'],
              "boundaries":result['boundaries'],"validity":result['validity'],"comparison":result['comparison'],
              "performance":timing,"deterministic_geometry_bytes":deterministic,
              "serialized_boundary_roundtrip_exact":disk_equal,"serialized_polygon_roundtrip_exact":polygon_disk_equal}
    if status != 'PASS_EXACT_BASELINE':
        write_json(folder/'FAILURE.json', {"status":status,"validity":result['validity'],
                                         "source_preserved":True,"canonical_boundaries_preserved":True,
                                         "remedy":"Review a representation permitting non-manifold cell complexes or obtain explicit scientific authorization for a geometric alteration; no repair applied."})
    write_json(folder/'manifest.json',report)
    return report


def run(output, root=ROOT):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not output.is_relative_to(root/'experiments/pipeline_v0.5'):
        raise ValueError("Output must be a new directory under experiments/pipeline_v0.5.")
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing v0.5 run.")
    before = repository_inventory(root,output)
    output.mkdir(parents=True,exist_ok=False)
    write_json(output/'preservation_before.json',before)
    write_json(output/'environment.json',environment())
    sources = {p.relative_to(root).as_posix():sha256_file(p) for p in sorted((root/'metamaterial_eval/geometry').glob('*.py'))}
    sources.update({name:sha256_file(root/name) for name in ('requirements-v0.5.txt','tests/test_geometry_exact.py','validation/evaluators/evaluator_v1_1.py')})
    # Archive executed source as well as hashes, including the dirty-tree code.
    for name in sources:
        target = output/'code_snapshot'/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((root/name).read_bytes())
    write_json(output/'protocol.json', {"stage":"v0.5A", "sources_sha256":sources,
               "git_head":subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
               "dirty_tree":True,"fixtures":FIXTURES,"input_resolution":1024,
               "acceptance":{"xor_pixels":0,"false_positives":0,"false_negatives":0,"iou":1,
                             "area_error":0,"topology_unchanged":True,"ogc_valid":True,"manifold_boundary":True},
               "settings":{"repair":False,"smoothing":False,"coalescing":"exact collinear only", "corner_pairing":"right turn", "rasterization":"cell-center parity; independent GEOS contains_xy on valid candidates"}})
    cases = []
    for identifier, relative in FIXTURES:
        try:
            cases.append(run_case(root,output,identifier,relative))
        except Exception as exc:
            import traceback
            failure = {"fixture":identifier,"status":"FAILED_EXECUTION","error":str(exc),"traceback":traceback.format_exc()}
            write_json(output/identifier/'FAILURE.json',failure)
            cases.append(failure)
        print(identifier,cases[-1]['status'],flush=True)
    after = repository_inventory(root,output)
    changed = [p for p,h in before.items() if after.get(p) != h]
    summary = {"stage":"v0.5A","status":"PASS_EXACT_BASELINE" if all(c['status']=='PASS_EXACT_BASELINE' for c in cases) and not changed else "HOLD",
               "cases":cases,"historical_and_existing_files_unchanged":not changed,"changed_existing_files":changed,
               "acceptance_scope":"Exact cell baseline only; no mechanical/manufacturing or simplified-geometry acceptance.",
               "v04_2_historical_p10":"FAILED_UNCHANGED","v04_3":"AMENDED_PASS_TESTED_DOMAIN_UNCHANGED"}
    write_json(output/'summary.json',summary)
    lines = ['# v0.5A exact baseline validation','',f"Overall decision: **{summary['status']}**.",'',
             '| Fixture | Status | OGC valid | Manifold | Loops | Vertices before / after | XOR | Area | Repeat seconds | Traced MiB |',
             '|---|---|---|---|---:|---:|---:|---:|---:|---:|']
    for c in cases:
        if 'boundaries' not in c:
            lines.append(f"| {c['fixture']} | {c['status']} | unavailable | unavailable | | | | | | |")
            continue
        b,v,p = c['boundaries'],c['validity'],c['performance']
        lines.append(f"| {c['fixture']} | {c['status']} | {v['ogc_valid']} | {v['manifold_boundary']} | {b['loop_count']} | {b['vertices_before_coalescing']} / {b['vertices_after_coalescing']} | {c['comparison']['xor_pixels']} | {v['geometry_area']} | {p['uninstrumented_repeat_seconds']:.3f} | {p['peak_traced_conversion_bytes']/2**20:.2f} |")
    lines += ['',f"Existing files preserved: {not changed}.",'',
              'Boundary reconstruction and valid polygon reconstruction are reported separately. An invalid polygon is never passed to the independent containment rasterizer.',
              'Point contacts block ordinary manifold boundaries even when a geometry library accepts an OGC object. No repair was applied.',
              'Performance covers conversion, topology, comparison and independent rasterization; excludes file IO and figures. Tracemalloc instrumentation adds overhead. RSS is a process lifetime measure.',
              'Execution: macOS only. Historical v0.4.2 P10 calibration remains FAILED; v0.4.3 qualification remains restricted to its tested domain.',
              'See each input_provenance.json for exact source paths/hashes/parameters and each geometry_validity.json for limitations. No v0.5B–D implementation is included.']
    (output/'VALIDATION.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True)
    args = parser.parse_args()
    summary = run(args.output_dir)
    return 0 if summary['status']=='PASS_EXACT_BASELINE' else 3


if __name__ == '__main__':
    sys.exit(main())
