"""Independent XML/path reader and even-odd nesting assembly.

This module does not import the writer, its coordinate records, or its cycle
ordering. The sidecar authenticates identities, never supplies geometry.
"""
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import time
from xml.etree import ElementTree as ET

from shapely import LineString, MultiPolygon, Polygon, STRtree

VERSION = "svg_evenodd_reader_1.0"
NS = "{http://www.w3.org/2000/svg}"
TOKEN = re.compile(r"[A-Za-z]|[+-]?(?:(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)")


class SVGImportError(ValueError):
    def __init__(self, message, *, raw_rings=None):
        super().__init__(message)
        self.raw_rings = raw_rings


def parse_path(data, domain):
    """Explicit absolute M/L/Z subset, checked by an independent state machine."""
    tokens, end = [], 0
    for match in TOKEN.finditer(data):
        gap = data[end:match.start()]
        if not re.fullmatch(r"\s*,?\s*", gap):
            raise SVGImportError("Invalid path token or separator")
        if "," in gap and (not tokens or tokens[-1] in ("M", "L", "Z") or match.group() in ("M", "L", "Z")):
            raise SVGImportError("Comma cannot separate path commands")
        tokens.append(match.group()); end = match.end()
    if data[end:].strip() or not tokens:
        raise SVGImportError("Invalid/empty path data")
    rings, active, index = [], None, 0
    while index < len(tokens):
        command = tokens[index]; index += 1
        if command not in ("M", "L", "Z"):
            raise SVGImportError("Unsupported path command or implicit coordinates: " + command, raw_rings=rings)
        if command == "Z":
            if active is None or len(active) < 3:
                raise SVGImportError("Close without at least three vertices", raw_rings=rings)
            # A redundant explicit final endpoint is allowed; repeated interior
            # or zero-length edges are rejected by assembly, never removed.
            closed = active if active[-1] == active[0] else active + [active[0]]
            rings.append(closed); active = None
            if len(rings) > 10000:
                raise SVGImportError("Ring resource limit exceeded")
            continue
        if index + 1 >= len(tokens):
            raise SVGImportError("Incomplete coordinate pair", raw_rings=rings)
        try:
            xy = [float(tokens[index]), float(tokens[index + 1])]
        except ValueError as e:
            raise SVGImportError("Invalid numeric coordinate", raw_rings=rings) from e
        index += 2
        if not all(math.isfinite(v) and 0 <= v <= domain for v in xy):
            raise SVGImportError("Nonfinite or out-of-domain coordinate", raw_rings=rings)
        if command == "M":
            if active is not None:
                raise SVGImportError("Missing Z closure before next M", raw_rings=rings + [active])
            active = [xy]
        else:
            if active is None:
                raise SVGImportError("Line without active subpath", raw_rings=rings)
            active.append(xy)
        if index > 6000000:
            raise SVGImportError("Path resource limit exceeded")
    if active is not None or not rings:
        raise SVGImportError("Missing path closure", raw_rings=rings + ([active] if active else []))
    return rings


def assemble_evenodd(rings):
    """Infer nesting from geometry, independent of sidecar roles or winding."""
    surfaces, boundaries = [], []
    for xy in rings:
        if len(xy) < 4 or any(a == b for a, b in zip(xy[:-1], xy[1:])):
            raise SVGImportError("Degenerate or repeated consecutive vertex", raw_rings=rings)
        surface, boundary = Polygon(xy), LineString(xy)
        if surface.area <= 0 or not surface.is_valid or not boundary.is_simple:
            raise SVGImportError("Invalid/self-intersecting ring", raw_rings=rings)
        surfaces.append(surface); boundaries.append(boundary)
    tree = STRtree(boundaries)
    for i, line in enumerate(boundaries):
        if any(int(j) > i for j in tree.query(line, predicate="intersects")):
            raise SVGImportError("Crossing, touching or overlapping subpaths", raw_rings=rings)
    areas = [p.area for p in surfaces]; tree = STRtree(surfaces); parents = []
    for i, p in enumerate(surfaces):
        # A boundary vertex avoids an outer ring's representative point lying
        # inside a descendant. Boundaries were proven disjoint above.
        from shapely import Point
        candidates = [int(j) for j in tree.query(Point(rings[i][0]), predicate="within") if areas[int(j)] > areas[i]]
        parents.append(min(candidates, key=areas.__getitem__) if candidates else None)
    depths = [None] * len(rings)
    for i in sorted(range(len(rings)), key=areas.__getitem__, reverse=True):
        depths[i] = 0 if parents[i] is None else depths[parents[i]] + 1
    children = [[] for _ in rings]
    for i, parent in enumerate(parents):
        if parent is not None:
            children[parent].append(i)
    parts, assignments = [], []
    for i, depth in enumerate(depths):
        if depth % 2:
            continue
        holes = [j for j in children[i] if depths[j] == depth + 1]
        parts.append(Polygon(rings[i], [rings[j] for j in holes]))
        assignments.append({"shell_subpath": i, "hole_subpaths": holes})
    geometry = parts[0] if len(parts) == 1 else MultiPolygon(parts)
    if geometry.is_empty or not geometry.is_valid:
        raise SVGImportError("Invalid even-odd polygon assembly", raw_rings=rings)
    return geometry, {"parents": parents, "depths": depths, "components": assignments}


def read_svg(svg_path, manifest, *, expected_source_sha256=None):
    """Read a persisted file. No original polygon coordinates are accepted."""
    start = time.perf_counter(); svg_path = Path(svg_path)
    manifest = json.loads(Path(manifest).read_text()) if isinstance(manifest, (str, Path)) else manifest
    if not isinstance(manifest, dict):
        raise SVGImportError("Missing sidecar manifest")
    payload = svg_path.read_bytes()
    if len(payload) > 32 * 1024**2:
        raise SVGImportError("SVG resource limit exceeded")
    if sha256(payload).hexdigest() != manifest.get("svg_sha256"):
        raise SVGImportError("SVG hash mismatch/tampering")
    if manifest.get("svg_filename") != svg_path.name:
        raise SVGImportError("SVG filename/sidecar mismatch")
    if b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise SVGImportError("Unsupported XML declarations")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as e:
        raise SVGImportError("Malformed XML: " + str(e)) from e
    if root.tag != NS + "svg" or set(root.attrib) != {"version", "viewBox", "width", "height"} or root.attrib["version"] != "1.1":
        raise SVGImportError("Unsupported root namespace, attributes or version")
    children = list(root)
    if len(children) != 2 or [x.tag for x in children] != [NS + "metadata", NS + "path"]:
        raise SVGImportError("Require metadata and exactly one solid path; no extra primitives")
    metadata, path = children
    if metadata.attrib != {"id": "young-dawgs-provenance"} or list(metadata):
        raise SVGImportError("Missing/unsupported provenance metadata")
    try:
        embedded = json.loads(metadata.text or "")
    except (ValueError, TypeError) as e:
        raise SVGImportError("Invalid provenance JSON") from e
    required = {"contract_version", "pipeline_version", "exporter_version", "exporter_code_sha256", "source_id", "source_state", "source_geometry_sha256", "canonical_raster_sha256", "resolution", "coordinate_orientation", "coordinate_unit", "physical_scale", "source_scientific_qualification", "research_only", "canonical_significant_digits", "diagnostic_precision"}
    if not isinstance(embedded, dict) or not required <= embedded.keys():
        raise SVGImportError("Missing required provenance fields")
    if any(manifest.get(k) != v for k, v in embedded.items()):
        raise SVGImportError("Embedded/sidecar provenance disagreement")
    if embedded["contract_version"] != "young-dawgs-svg-polygon-1" or embedded["pipeline_version"] != "v0.5D1" or embedded["source_state"] not in ("G1", "G2", "G3") or not embedded["source_id"]:
        raise SVGImportError("Unknown source identity/state or contract")
    digits = embedded["canonical_significant_digits"]
    if isinstance(digits, bool) or digits not in (17, 12, 9, 6, 3) or embedded["diagnostic_precision"] is not (digits != 17):
        raise SVGImportError("Unknown or inconsistent precision declaration")
    for key in ("source_geometry_sha256", "canonical_raster_sha256", "exporter_code_sha256"):
        if not isinstance(embedded[key], str) or not re.fullmatch(r"[a-f0-9]{64}", embedded[key]):
            raise SVGImportError("Invalid provenance hash")
    if expected_source_sha256 is not None and embedded["source_geometry_sha256"] != expected_source_sha256:
        raise SVGImportError("Source hash differs from trusted registration")
    if embedded["coordinate_orientation"] != {"x": "right", "y": "down"} or embedded["coordinate_unit"] != "raster_cell" or embedded["physical_scale"] is not None or embedded["research_only"] is not True:
        raise SVGImportError("Unauthorized coordinate/scaling/status semantics")
    statuses = embedded["source_scientific_qualification"]
    expected = {"overall_scientific": "HOLD_SMALL_PORE_POLICY", "cumulative_small_pore_fidelity": "UNQUALIFIED", "production_simplification": "HOLD_UNQUALIFIED", "cad_kernel_interoperability": "UNQUALIFIED", "FEM": "UNQUALIFIED", "manufacturing": "UNQUALIFIED"}
    if not isinstance(statuses, dict) or any(statuses.get(k) != v for k, v in expected.items()):
        raise SVGImportError("Required source HOLD/UNQUALIFIED statuses not propagated")
    n = embedded["resolution"]
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0 or root.attrib["viewBox"] != f"0 0 {n} {n}" or root.attrib["width"] != str(n) or root.attrib["height"] != str(n):
        raise SVGImportError("Incorrect viewBox/display dimensions")
    if set(path.attrib) != {"id", "fill", "stroke", "fill-rule", "d"} or path.attrib["id"] != "solid-geometry" or path.attrib["fill-rule"] != "evenodd" or path.attrib["fill"] != "#000000" or path.attrib["stroke"] != "none" or list(path):
        raise SVGImportError("Unsupported solid path, fill, stroke or transform")
    rings = parse_path(path.attrib["d"], n); parsed = time.perf_counter()
    geometry, nesting = assemble_evenodd(rings); finished = time.perf_counter()
    return {"geometry": geometry, "rings": rings, "nesting": nesting, "metadata": embedded,
            "svg_sha256": sha256(payload).hexdigest(), "importer_version": VERSION,
            "importer_code_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "timings": {"read_xml_path_seconds": parsed - start, "polygon_reconstruction_seconds": finished - parsed, "total_import_seconds": finished - start}}

