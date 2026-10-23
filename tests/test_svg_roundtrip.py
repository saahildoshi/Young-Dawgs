"""D1 SVG parsing, fill, precision, provenance and failure controls."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import pytest
import shapely
from shapely import MultiPolygon, Polygon, box

from metamaterial_eval.geometry.svg_io import exporter, importer
from metamaterial_eval.geometry.svg_io.controls import analytic_cases, metadata
from metamaterial_eval.geometry.svg_io.verification import compare_geometry
from metamaterial_eval.geometry.validation.checks import independent_raster


@pytest.fixture(scope="module")
def cases():
    return analytic_cases()


def files(tmp_path, g=None):
    g = box(10, 20, 60, 80) if g is None else g
    svg, side = tmp_path / "solid.svg", tmp_path / "solid.json"
    manifest = exporter.write_svg(g, svg, side, metadata(g))
    return g, svg, side, manifest


def alter(svg, manifest, operation, *, refresh=True):
    root = ET.fromstring(svg.read_bytes()); operation(root)
    svg.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))
    if refresh:
        manifest["svg_sha256"] = sha256(svg.read_bytes()).hexdigest()


@pytest.mark.parametrize("name", list(analytic_cases()))
def test_analytic_regions_roundtrip(tmp_path, cases, name):
    g, svg, side, manifest = files(tmp_path, cases[name])
    read = importer.read_svg(svg, side, expected_source_sha256=manifest["source_geometry_sha256"])
    comparison = compare_geometry(g, read["geometry"], full=False)
    assert comparison["passed"], comparison["gates"]


def test_orientation_viewbox_and_no_units(tmp_path):
    g, svg, side, manifest = files(tmp_path)
    root = ET.fromstring(svg.read_bytes())
    assert root.attrib == {"version": "1.1", "viewBox": "0 0 1024 1024", "width": "1024", "height": "1024"}
    q = importer.read_svg(svg, side)["geometry"]
    assert q.bounds == (10., 20., 60., 80.)
    assert manifest["physical_scale"] is None and manifest["coordinate_unit"] == "raster_cell"


def test_evenodd_ignores_orientation_and_subpath_order(tmp_path):
    g = MultiPolygon([box(10, 10, 100, 100).difference(box(20, 20, 90, 90)), box(30, 30, 80, 80)])
    _, svg, _, m = files(tmp_path, g)
    import re
    alter(svg, m, lambda root: root[1].set("d", " ".join(reversed(re.findall(r"M.*?Z", root[1].attrib["d"])))))
    assert importer.read_svg(svg, m)["geometry"].equals(g)


def test_nested_topology_uses_actual_disjoint_void_faces(tmp_path, cases):
    g, svg, side, m = files(tmp_path, cases["concentric_nested_islands"])
    q = compare_geometry(g, importer.read_svg(svg, side)["geometry"])
    assert q["passed"] and q["topology"]["holes"]["source_count"] == 2
    assert not q["topology"]["legacy_C_ring_disk_comparison"]["passed"]


def test_diagnostic_json_preserves_numpy_boolean_values(tmp_path):
    from metamaterial_eval.geometry.svg_io.diagnostics import write_json
    p = tmp_path / "values.json"; write_json(p, {"gate": np.bool_(True), "value": np.float64(.25)})
    assert json.loads(p.read_text()) == {"gate": True, "value": .25}


def test_canonical_path_order_preserves_vertices(tmp_path):
    a = Polygon([(10, 10), (15, 10), (20, 10), (20, 20), (10, 20)], [box(12, 12, 14, 14).exterior.coords])
    b = Polygon(list(a.exterior.coords)[::-1], [list(a.interiors[0].coords)[::-1]])
    meta = metadata(a)
    first = ET.fromstring(exporter.serialize(a, meta)[0])[1].attrib["d"]
    second = ET.fromstring(exporter.serialize(b, meta)[0])[1].attrib["d"]
    assert first == second and first.count("L") == 7


def test_binary64_roundtrip_random_extremes():
    rng = np.random.default_rng(20261023)
    values = np.r_[rng.uniform(0, 1024, 10000), [np.nextafter(0., 1.), np.nextafter(1024., 0.), .1, 1/3, np.pi]]
    assert all(float(format(float(v), ".17g")).hex() == float(v).hex() for v in values)


def test_raster_identity_cannot_forgive_continuous_change(tmp_path):
    g = box(10.01, 20.01, 60.01, 80.01); b = box(10.02, 20.01, 60.01, 80.01)
    assert np.array_equal(independent_raster(g, 128)[0], independent_raster(b, 128)[0])
    q = compare_geometry(g, b, domain=128)
    assert not q["passed"] and q["area"]["symmetric"] > 0 and q["distance"]["upper"] > 0


@pytest.mark.parametrize("digits", [12, 9, 6, 3])
def test_truncation_detected_even_below_arithmetic_allowance(tmp_path, digits):
    g = Polygon([(10.123456789012345, 20.123456789012345), (70.12345678901235, 20.33333333333333), (50.11111111111111, 80.12345678901235)])
    svg, side = tmp_path / "p.svg", tmp_path / "p.json"
    exporter.write_svg(g, svg, side, metadata(g), diagnostic_digits=digits)
    q = compare_geometry(g, importer.read_svg(svg, side)["geometry"], full=False)
    assert not q["passed"] and not q["gates"]["exact_binary64_vertices"]


def test_low_precision_collapses_registered_repair(tmp_path, cases):
    g = cases["manifold_regularized_contact"]; svg, side = tmp_path / "p.svg", tmp_path / "p.json"
    exporter.write_svg(g, svg, side, metadata(g), diagnostic_digits=3)
    with pytest.raises(importer.SVGImportError):
        importer.read_svg(svg, side)


@pytest.mark.parametrize("mutation", [
    lambda r: r.set("transform", "scale(2)"),
    lambda r: r[1].set("transform", "translate(1,1)"),
    lambda r: r[1].set("d", "M 10 10 C 20 20 30 30 40 40 Z"),
    lambda r: r[1].set("d", "M 10 10 Q 20 20 40 40 Z"),
    lambda r: r[1].set("d", "m 10 10 l 20 20 z"),
    lambda r: r[1].set("d", "M 10 10 L 20 10 L 20 20"),
    lambda r: r[1].set("d", "M 10 10 Z"),
    lambda r: r[1].set("d", "M 10 10 L NaN 20 L 20 20 Z"),
    lambda r: r[1].set("d", "M 10 10 L 1e999 20 L 20 20 Z"),
    lambda r: r[1].set("d", "M 10 10 L -1 20 L 20 20 Z"),
    lambda r: r[1].set("d", "M 10 10 L 20 10 L 20 10 L 20 20 Z"),
    lambda r: r[1].set("d", "M 10 10 L 20 20 L 10 20 L 20 10 Z"),
    lambda r: r[1].set("d", "M 10 10 L 20 10 L 30 10 Z"),
    lambda r: r[1].set("fill-rule", "nonzero"),
    lambda r: r[1].set("fill", "none"),
    lambda r: r[1].set("stroke", "black"),
    lambda r: r[1].set("id", "decoration"),
    lambda r: r.set("viewBox", "0 0 512 512"),
    lambda r: r.set("width", "1024mm"),
    lambda r: r.append(ET.Element(importer.NS + "rect", {"width": "1024", "height": "1024"})),
    lambda r: r.append(deepcopy(r[1])),
    lambda r: r.remove(r[0]),
    lambda r: setattr(r, "tag", "{urn:wrong}svg"),
    lambda r: r[1].set("style", "fill:black"),
    lambda r: r.append(ET.Element(importer.NS + "g")),
])
def test_unsupported_or_malformed_svg_is_rejected(tmp_path, mutation):
    _, svg, _, m = files(tmp_path); alter(svg, m, mutation)
    with pytest.raises(importer.SVGImportError):
        importer.read_svg(svg, m)


@pytest.mark.parametrize("key,value", [("source_id", ""), ("physical_scale", 1.), ("coordinate_unit", "mm"), ("coordinate_orientation", {"x": "right", "y": "up"}), ("research_only", False), ("source_state", "CAD"), ("source_geometry_sha256", "invalid")])
def test_invalid_provenance_rejected(tmp_path, key, value):
    _, svg, _, m = files(tmp_path)
    def change(root):
        d = json.loads(root[0].text); d[key] = value; root[0].text = json.dumps(d)
    alter(svg, m, change); m[key] = value
    with pytest.raises(importer.SVGImportError):
        importer.read_svg(svg, m)


def test_source_hash_trust_anchor_rejects_joint_metadata_tampering(tmp_path):
    _, svg, _, m = files(tmp_path); trusted = m["source_geometry_sha256"]
    def change(root):
        d = json.loads(root[0].text); d["source_geometry_sha256"] = "1" * 64; root[0].text = json.dumps(d)
    alter(svg, m, change); m["source_geometry_sha256"] = "1" * 64
    with pytest.raises(importer.SVGImportError, match="trusted"):
        importer.read_svg(svg, m, expected_source_sha256=trusted)


def test_modified_svg_hash_rejected(tmp_path):
    _, svg, _, m = files(tmp_path); svg.write_bytes(svg.read_bytes() + b"\n")
    with pytest.raises(importer.SVGImportError, match="hash"):
        importer.read_svg(svg, m)


def test_missing_metadata_field_rejected(tmp_path):
    _, svg, _, m = files(tmp_path)
    def change(root):
        d = json.loads(root[0].text); d.pop("canonical_raster_sha256"); root[0].text = json.dumps(d)
    alter(svg, m, change)
    with pytest.raises(importer.SVGImportError, match="Missing"):
        importer.read_svg(svg, m)


def test_scientific_status_cannot_be_promoted(tmp_path):
    _, svg, _, m = files(tmp_path)
    def change(root):
        d = json.loads(root[0].text); d["source_scientific_qualification"]["overall_scientific"] = "PASS"; root[0].text = json.dumps(d)
    alter(svg, m, change); m["source_scientific_qualification"]["overall_scientific"] = "PASS"
    with pytest.raises(importer.SVGImportError, match="statuses"):
        importer.read_svg(svg, m)


def test_coordinate_orientation_flip_detected_by_comparison(tmp_path):
    g, svg, _, m = files(tmp_path)
    alter(svg, m, lambda root: root[1].set("d", "M 10 1004 L 60 1004 L 60 944 L 10 944 Z"))
    assert not compare_geometry(g, importer.read_svg(svg, m)["geometry"], full=False)["passed"]


def test_saved_source_hash_and_overwrite_protection(tmp_path):
    g = box(10, 10, 20, 20); source = tmp_path / "source.wkb"; source.write_bytes(g.wkb); meta = metadata(g)
    with pytest.raises(ValueError, match="hash"):
        exporter.export_saved(source, "1" * 64, tmp_path / "s.svg", tmp_path / "s.json", meta)
    exporter.export_saved(source, sha256(g.wkb).hexdigest(), tmp_path / "s.svg", tmp_path / "s.json", meta)
    with pytest.raises(FileExistsError):
        exporter.export_saved(source, sha256(g.wkb).hexdigest(), tmp_path / "s.svg", tmp_path / "s.json", meta)
    assert source.read_bytes() == g.wkb


def test_repeated_export_and_import_deterministic(tmp_path):
    g, svg, _, m = files(tmp_path)
    q = importer.read_svg(svg, m)["geometry"]
    assert q.wkb == importer.read_svg(svg, m)["geometry"].wkb
    assert exporter.serialize(g, metadata(g))[0] == svg.read_bytes()


def test_exporter_rejects_nonmanifold_and_invalid_without_mutation(tmp_path):
    g = Polygon(box(10, 10, 100, 100).exterior.coords, [box(20, 20, 40, 40).exterior.coords, box(40, 40, 60, 60).exterior.coords])
    before = g.wkb
    with pytest.raises(ValueError, match="manifold"):
        exporter.write_svg(g, tmp_path / "s.svg", tmp_path / "s.json", metadata(g))
    assert g.wkb == before

