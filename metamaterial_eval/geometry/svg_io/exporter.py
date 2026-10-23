"""Deterministic polygon writer. No parser or importer construction is reused."""
from hashlib import sha256
from html import escape
import json
import math
from pathlib import Path

import shapely

from ..validation.checks import boundary_integrity

VERSION = "svg_polygon_writer_1.0"


def _parts(g):
    if g.geom_type == "Polygon":
        return [g]
    if g.geom_type == "MultiPolygon":
        return list(g.geoms)
    raise ValueError("Only nonempty Polygon/MultiPolygon sources are supported")


def _cycle(ring):
    """Rotate and orient a cycle canonically; never drop a source vertex."""
    points = [tuple(map(float, p)) for p in ring.coords]
    if len(points) < 4 or points[0] != points[-1]:
        raise ValueError("Open or undersized source ring")
    points = points[:-1]
    if any(not all(math.isfinite(v) for v in p) for p in points):
        raise ValueError("Nonfinite source coordinates")
    k = min(range(len(points)), key=points.__getitem__)
    forward = points[k:] + points[:k]
    reverse = [forward[0], *reversed(forward[1:])]
    return tuple(min(forward, reverse))


def serialize(geometry, metadata, *, diagnostic_digits=None):
    """Return actual SVG bytes and role records; lower precision is diagnostic only."""
    if geometry.is_empty or not boundary_integrity(geometry)["passed"]:
        raise ValueError("Require valid manifold source; export never repairs it")
    n = metadata["resolution"]
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError("Positive integer coordinate domain required")
    if metadata.get("physical_scale") is not None:
        raise ValueError("Physical scaling is not authorized")
    digits = 17 if diagnostic_digits is None else diagnostic_digits
    if digits not in (17, 12, 9, 6, 3):
        raise ValueError("Unregistered precision diagnostic")
    parts = []
    for p in _parts(geometry):
        parts.append((_cycle(p.exterior), sorted(_cycle(h) for h in p.interiors)))
    parts.sort(key=lambda p: p[0])
    commands, records = [], []
    number = lambda v: format(v, f".{digits}g")
    for pi, (shell, holes) in enumerate(parts):
        for role, points in [("shell", shell), *[("hole", h) for h in holes]]:
            for x, y in points:
                if not 0 <= x <= n or not 0 <= y <= n:
                    raise ValueError("Coordinates outside the declared viewBox")
            commands.append("M " + " ".join(number(v) for v in points[0]))
            commands.extend("L " + " ".join(number(v) for v in p) for p in points[1:])
            commands.append("Z")
            closed = [*points, points[0]]
            records.append({"polygon": pi, "role": role, "vertices": len(points),
                            "coordinates_sha256": sha256(json.dumps(closed, separators=(",", ":")).encode()).hexdigest()})
    embedded = {**metadata, "contract_version": "young-dawgs-svg-polygon-1",
                "pipeline_version": "v0.5D1", "exporter_version": VERSION,
                "exporter_code_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
                "canonical_significant_digits": digits,
                "diagnostic_precision": diagnostic_digits is not None and digits != 17,
                "coordinate_orientation": {"x": "right", "y": "down"},
                "coordinate_unit": "raster_cell", "physical_scale": None,
                "research_only": True}
    text = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 {n} {n}" width="{n}" height="{n}">\n'
            '<metadata id="young-dawgs-provenance">' + escape(json.dumps(embedded, sort_keys=True, separators=(",", ":"))) + '</metadata>\n'
            '<path id="solid-geometry" fill="#000000" stroke="none" fill-rule="evenodd" d="' + " ".join(commands) + '"/>\n</svg>\n')
    return text.encode("utf-8"), embedded, records


def write_svg(geometry, svg_path, manifest_path, metadata, *, diagnostic_digits=None):
    svg_path, manifest_path = Path(svg_path), Path(manifest_path)
    if svg_path.exists() or manifest_path.exists():
        raise FileExistsError("Export/manifest already exists; use a new artifact")
    payload, embedded, records = serialize(geometry, metadata, diagnostic_digits=diagnostic_digits)
    manifest = {**embedded, "svg_filename": svg_path.name,
                "svg_sha256": sha256(payload).hexdigest(), "svg_bytes": len(payload),
                "rings": records, "roundtrip_validation": "NOT_YET_EVALUATED"}
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with svg_path.open("xb") as f:
        f.write(payload)
    with manifest_path.open("x") as f:
        json.dump(manifest, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
    return manifest


def export_saved(source_path, source_sha256, svg_path, manifest_path, metadata):
    payload = Path(source_path).read_bytes()
    if sha256(payload).hexdigest() != source_sha256 or metadata.get("source_geometry_sha256") != source_sha256:
        raise ValueError("Saved source geometry hash mismatch")
    return write_svg(shapely.from_wkb(payload), svg_path, manifest_path, metadata)

