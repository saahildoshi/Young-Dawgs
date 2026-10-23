"""Persisted positive/negative SVG experiments, separate from canonical exports."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import traceback
from xml.etree import ElementTree as ET

import numpy as np
import shapely
from shapely import box

from .controls import analytic_cases, metadata
from .exporter import write_svg
from .importer import NS, SVGImportError, read_svg
from .verification import compare_geometry


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    def scalar(v):
        if isinstance(v, np.generic):
            return v.item()
        raise TypeError("Unsupported JSON value: " + type(v).__name__)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False, default=scalar) + "\n")


def evaluate(svg, manifest, source, source_hash, *, full=False):
    try:
        result = read_svg(svg, manifest, expected_source_sha256=source_hash)
        geometry = result.pop("geometry")
        path = Path(svg).with_suffix(".imported.wkb"); path.write_bytes(geometry.wkb)
        result["geometry_comparison"] = compare_geometry(source, geometry, full=full)
        result.update(parsed=True, roundtrip_pass=result["geometry_comparison"]["passed"])
    except SVGImportError as e:
        result = {"parsed": False, "roundtrip_pass": False, "error": str(e), "raw_rings": e.raw_rings}
    write_json(Path(svg).with_suffix(".diagnostic.json"), result)
    return result


def run_controls(out):
    index = 1
    while (Path(out) / f"precision_controls/synthetic_run_{index:03d}").exists():
        index += 1
    folder = Path(out) / f"precision_controls/synthetic_run_{index:03d}"
    folder.mkdir(parents=True)
    cases = analytic_cases(); rows = []
    for name, g in cases.items():
        dest = folder / name; dest.mkdir(); (dest / "source.wkb").write_bytes(g.wkb)
        for digits in (17, 12, 9, 6, 3):
            svg = dest / f"digits_{digits}.svg"; side = svg.with_suffix(".json")
            m = write_svg(g, svg, side, metadata(g, name), diagnostic_digits=None if digits == 17 else digits)
            result = evaluate(svg, m, g, m["source_geometry_sha256"], full=digits == 17)
            rows.append({"case": name, "digits": digits, "parsed": result["parsed"], "roundtrip_pass": result["roundtrip_pass"], "error": result.get("error"),
                         "symmetric_area": result.get("geometry_comparison", {}).get("area", {}).get("symmetric"), "coordinates_exact": result.get("geometry_comparison", {}).get("gates", {}).get("exact_binary64_vertices")})
    source = cases["single_hole"]; negative = []
    mutations = {
        "unsupported_curve": lambda r: r[1].set("d", "M 10 10 C 20 20 30 30 40 40 Z"),
        "unsupported_arc": lambda r: r[1].set("d", "M 10 10 A 10 10 0 0 1 20 20 Z"),
        "unsupported_relative": lambda r: r[1].set("d", "m 10 10 l 20 20 z"),
        "missing_closure": lambda r: r[1].set("d", "M 10 10 L 20 10 L 20 20"),
        "incorrect_closure": lambda r: r[1].set("d", "M 10 10 Z"),
        "invalid_numeric": lambda r: r[1].set("d", "M 10 10 L NaN 20 L 20 20 Z"),
        "nonfinite": lambda r: r[1].set("d", "M 10 10 L 1e999 20 L 20 20 Z"),
        "out_of_bounds": lambda r: r[1].set("d", "M 10 10 L 1025 20 L 20 20 Z"),
        "repeated_coordinates": lambda r: r[1].set("d", "M 10 10 L 20 10 L 20 10 L 20 20 Z"),
        "crossing_ring": lambda r: r[1].set("d", "M 10 10 L 20 20 L 10 20 L 20 10 Z"),
        "point_contact": lambda r: r[1].set("d", "M 10 10 L 20 10 L 20 20 L 10 20 Z M 20 20 L 30 20 L 30 30 L 20 30 Z"),
        "overlapping_rings": lambda r: r[1].set("d", "M 10 10 L 30 10 L 30 30 L 10 30 Z M 20 20 L 40 20 L 40 40 L 20 40 Z"),
        "root_transform": lambda r: r.set("transform", "scale(2)"),
        "path_transform": lambda r: r[1].set("transform", "translate(1,1)"),
        "wrong_namespace": lambda r: setattr(r, "tag", "{urn:wrong}svg"),
        "wrong_fill_rule": lambda r: r[1].set("fill-rule", "nonzero"),
        "missing_geometry_id": lambda r: r[1].attrib.pop("id"),
        "extra_geometry": lambda r: r.append(ET.Element(NS + "rect", {"width": "1024", "height": "1024"})),
        "duplicate_geometry_id": lambda r: r.append(deepcopy(r[1])),
        "missing_metadata": lambda r: r.remove(r[0]),
        "physical_units": lambda r: r.set("width", "1024mm"),
        "wrong_viewbox": lambda r: r.set("viewBox", "0 0 512 512"),
        "orientation_reversed": lambda r: r[1].set("d", "M 10 924 L 100 924 L 100 1014 L 10 1014 Z M 20 964 L 60 964 L 60 1004 L 20 1004 Z"),
        "filled_pore": lambda r: r[1].set("d", "M 10 10 L 100 10 L 100 100 L 10 100 Z"),
        "pore_opened_to_exterior": lambda r: r[1].set("d", "M 10 10 L 100 10 L 100 100 L 10 100 L 10 50 L 20 50 L 20 60 L 60 60 L 60 20 L 20 20 L 20 40 L 10 40 Z"),
        "raster_invisible_continuous_shift": lambda r: r[1].set("d", "M 10.01 10 L 100 10 L 100 100 L 10.01 100 Z M 20 20 L 60 20 L 60 60 L 20 60 Z"),
    }
    for name, mutate in mutations.items():
        dest = folder / ("negative_" + name); dest.mkdir(); svg = dest / "solid.svg"; side = dest / "solid.json"
        m = write_svg(source, svg, side, metadata(source, name)); root = ET.fromstring(svg.read_bytes()); mutate(root)
        svg.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True)); m["svg_sha256"] = sha256(svg.read_bytes()).hexdigest()
        write_json(side, m); result = evaluate(svg, m, source, m["source_geometry_sha256"], full=True)
        negative.append({"case": name, "detected": not result["roundtrip_pass"], "parsed": result["parsed"], "error": result.get("error"), "comparison": result.get("geometry_comparison")})
    for name in ("tampered_source_hash", "tampered_svg_bytes", "missing_source_identifier", "promoted_scientific_status", "malformed_xml"):
        dest = folder / ("negative_" + name); dest.mkdir(); svg = dest / "solid.svg"; side = dest / "solid.json"
        m = write_svg(source, svg, side, metadata(source, name)); trusted = m["source_geometry_sha256"]
        if name == "tampered_svg_bytes":
            svg.write_bytes(svg.read_bytes() + b"\n")
        elif name == "malformed_xml":
            svg.write_bytes(b"<svg><path"); m["svg_sha256"] = sha256(svg.read_bytes()).hexdigest()
        else:
            root = ET.fromstring(svg.read_bytes()); embedded = json.loads(root[0].text)
            if name == "tampered_source_hash":
                embedded["source_geometry_sha256"] = "1" * 64; m["source_geometry_sha256"] = "1" * 64
            elif name == "missing_source_identifier":
                embedded.pop("source_id"); m.pop("source_id")
            else:
                embedded["source_scientific_qualification"]["overall_scientific"] = "PASS"
                m["source_scientific_qualification"]["overall_scientific"] = "PASS"
            root[0].text = json.dumps(embedded); svg.write_bytes(ET.tostring(root)); m["svg_sha256"] = sha256(svg.read_bytes()).hexdigest()
        write_json(side, m); result = evaluate(svg, m, source, trusted, full=True)
        negative.append({"case": name, "detected": not result["roundtrip_pass"], "parsed": result["parsed"], "error": result.get("error")})
    baseline = [r for r in rows if r["digits"] == 17]
    summary = {"positive_cases": len(cases), "precision_configurations": len(rows), "canonical_passes": sum(r["roundtrip_pass"] for r in baseline),
               "negative_cases": len(negative), "negative_failures_detected": sum(r["detected"] for r in negative), "rows": rows, "negative_records": negative,
               "passed": all(r["roundtrip_pass"] for r in baseline) and all(r["detected"] for r in negative)}
    write_json(folder / "SUMMARY.json", summary)
    print("Synthetic controls", summary["canonical_passes"], "/", len(cases), "negative detected", summary["negative_failures_detected"], "/", len(negative), flush=True)
    return summary


def real_precision(out, protocol, root):
    out, root = Path(out), Path(root); folder = out / "precision_controls/real"
    if folder.exists():
        raise FileExistsError("Precision study already exists")
    folder.mkdir(parents=True); rows = []
    for f in protocol["fixtures"]:
        g = shapely.from_wkb((root / f["source_geometry_path"]).read_bytes())
        canonical = json.loads((out / "exports" / (f["id"] + ".json")).read_text())
        rows.append({"fixture": f["id"], "digits": 17, "parsed": canonical["validation"]["statuses"]["parse"] == "SVG_PARSE_PASS", "roundtrip_pass": canonical["validation"]["passed"], "symmetric_area": canonical["validation"]["continuous"]["area"]["symmetric"], "displacement_upper": canonical["validation"]["continuous"]["distance"]["upper"]})
        dest = folder / f["id"]; dest.mkdir()
        for digits in (12, 9, 6, 3):
            svg = dest / f"digits_{digits}.svg"; side = svg.with_suffix(".json")
            m = write_svg(g, svg, side, {k: v for k, v in canonical.items() if k not in ("validation", "roundtrip_validation", "rings", "svg_sha256", "svg_bytes", "svg_filename", "imported_geometry_sha256", "execution_utc")}, diagnostic_digits=digits)
            result = evaluate(svg, m, g, f["source_geometry_sha256"], full=True)
            comparison = result.get("geometry_comparison", {})
            rows.append({"fixture": f["id"], "digits": digits, "parsed": result["parsed"], "roundtrip_pass": result["roundtrip_pass"], "error": result.get("error"),
                         "symmetric_area": comparison.get("area", {}).get("symmetric"), "displacement_upper": comparison.get("distance", {}).get("upper"),
                         "coordinate_instances_changed": comparison.get("coordinate_comparison", {}).get("missing_vertex_instances")})
            print("Precision", f["id"], digits, result["roundtrip_pass"], result.get("error", ""), flush=True)
    summary = {"rows": rows, "canonical_unchanged": True, "amended_precision_selected": False}
    write_json(folder / "SUMMARY.json", summary)
    return summary

