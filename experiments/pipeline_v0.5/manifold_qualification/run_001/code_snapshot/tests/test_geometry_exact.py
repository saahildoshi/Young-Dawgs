"""Analytic masks, pathology diagnostics and exact occupied-cell verification."""
import itertools
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from shapely import box
from shapely.ops import unary_union

from metamaterial_eval.geometry import convert_exact, load_binary_reference, validate_mask
from metamaterial_eval.geometry.boundaries import extract_cell_boundaries, signed_area2
from metamaterial_eval.geometry.conversion import geometry_bytes
from metamaterial_eval.geometry.planar import build_exact_planar_geometry, rasterize_exact_geometry
from metamaterial_eval.geometry.raster import rasterize_boundary_loops


def examples():
    full = np.ones((24, 24), dtype=np.uint8)
    rectangle = np.zeros_like(full); rectangle[3:20, 4:19] = 1
    central = rectangle.copy(); central[8:12, 9:14] = 0
    several = rectangle.copy()
    for r, c in ((6, 7), (13, 7), (13, 14)):
        several[r:r+3, c:c+2] = 0
    horizontal = np.zeros_like(full); horizontal[10:12, :] = 1
    vertical = np.zeros_like(full); vertical[:, 10:12] = 1
    cross = horizontal | vertical
    ring = np.zeros_like(full); ring[3:21, 3:21] = 1; ring[6:18, 6:18] = 0
    network = full.copy(); network[2:8, 2:8] = 0; network[12:19, 3:10] = 0; network[5:16, 14:21] = 0
    one = np.zeros_like(full); one[4:12, 2:9] = 1; one[4:12, 15:22] = 1; one[7, 9:15] = 1
    two = one.copy(); two[8, 9:15] = 1
    open_top = full.copy(); open_top[:15, 10:13] = 0
    multi = full.copy(); multi[:, 10:13] = 0; multi[10:13, :13] = 0
    corner = full.copy(); corner[:7, :7] = 0
    diagonal = np.zeros_like(full); diagonal[3:9, 3:9] = 1; diagonal[9:15, 9:15] = 1
    void_corner = full.copy(); void_corner[:8, :8] = 0; void_corner[8:14, 8:14] = 0
    nested = ring.copy(); nested[9:15, 9:15] = 1; nested[11:13, 11:13] = 0
    stair = np.zeros((80, 80), dtype=np.uint8)
    for row in range(4, 76):
        stair[row, 3:row+2] = 1
    rng = np.random.default_rng(7331)
    random = full.copy()
    # Random isolated rectangular pores in a guaranteed connected solid grid.
    for r, c in itertools.product(range(2, 20, 5), repeat=2):
        h, w = rng.integers(1, 4, size=2); random[r:r+h, c:c+w] = 0
    slit = full.copy(); slit[5:17, 6:18] = 0; slit[:6, 11] = 0
    near = full.copy(); near[4:14, 4:10] = 0; near[4:14, 11:18] = 0
    return dict(full=full, rectangle=rectangle, central_hole=central, several_holes=several,
                horizontal=horizontal, vertical=vertical, cross=cross, ring=ring, network=network,
                one_pixel=one, two_pixel=two, open_top=open_top, multi_boundary=multi,
                corner_void=corner, diagonal_solid=diagonal, diagonal_void=void_corner,
                nested=nested, staircase=stair, fixed_random=random,
                one_pixel_void_opening=slit, adjacent_pores=near)


@pytest.mark.parametrize("name,mask", examples().items())
def test_synthetic_exact_cells(name, mask):
    before = mask.copy()
    result = convert_exact(mask)
    assert result["comparison"]["exact_equal"]
    assert result["comparison"]["xor_pixels"] == 0
    assert result["comparison"]["iou"] == 1
    assert result["comparison"]["topology_unchanged"]
    assert result["validity"]["area_equals_occupied_cells"]
    assert result["validity"]["all_rings_closed"]
    assert result["validity"]["orientation_consistent"]
    assert result["boundaries"]["all_edges_traced_once"]
    assert result["boundaries"]["duplicate_edge_count"] == 0
    assert result["boundaries"]["zero_length_edge_count"] == 0
    # Independent, deliberately tiny per-cell union is a test oracle only.
    cells = [box(c, r, c+1, r+1) for r, c in zip(*np.nonzero(mask))]
    oracle = unary_union(cells)
    if result["validity"]["ogc_valid"]:
        assert result["geometry"].equals(oracle)
        assert result["comparison"]["polygon_roundtrip"]["exact_equal"]
    np.testing.assert_array_equal(mask, before)
    doc = json.loads(geometry_bytes(result["document"]))
    np.testing.assert_array_equal(rasterize_boundary_loops(doc["loops"], mask.shape[0]), mask)
    assert geometry_bytes(convert_exact(mask)["document"]) == geometry_bytes(result["document"])
    if name in ("diagonal_solid", "diagonal_void"):
        assert result["status"] == "HOLD_GEOMETRY"
        expected = [[9, 9]] if name == 'diagonal_solid' else [[8, 8]]
        assert result["validity"]["point_contact_vertices_xy"] == expected
    else:
        assert result["status"] == "PASS_EXACT_BASELINE"


def test_void_8_is_separate_from_ogc_hole_touching_exterior():
    result = convert_exact(examples()["diagonal_void"])
    topology = result["comparison"]["input_topology"]
    assert topology["void_8"]["enclosed_count"] == 0
    assert topology["void_4_frozen_convention"]["enclosed_count"] == 1
    assert result["validity"]["ogc_valid"]
    assert result["comparison"]["polygon_roundtrip"]['exact_equal']
    assert result['validity']['polygon_holes_from_exterior_walk'] == 1
    assert result['validity']['boundary_contact_diagnostics'][0]['kind'] == 'hole_touches_shell'
    assert not result['validity']['manifold_boundary']
    assert result["validity"]["repeated_vertex_loop_indices"]
    # Reject an actually invalid OGC candidate, independently of this exact split.
    from shapely import Polygon
    with pytest.raises(ValueError, match="invalid geometry"):
        rasterize_exact_geometry(Polygon([(0,0),(3,3),(0,3),(3,0),(0,0)]), 24)


def test_exterior_and_hole_counts():
    for name, holes in (("full", 0), ("central_hole", 1), ("several_holes", 3),
                        ("open_top", 0), ("one_pixel_void_opening", 0), ("nested", 2)):
        result = convert_exact(examples()[name])
        assert result["validity"]["hole_count"] == holes
        assert result["validity"]["hole_loop_count"] == holes


def test_exhaustive_three_by_three_nonempty_masks():
    for bits in range(1, 512):
        mask = np.array([(bits >> i) & 1 for i in range(9)], dtype=np.uint8).reshape(3, 3)
        result = convert_exact(mask)
        assert result["comparison"]["exact_equal"], bits
        assert result["validity"]["area_equals_occupied_cells"], bits
        assert result['validity']['ogc_valid'], bits
        oracle = unary_union([box(c,r,c+1,r+1) for r,c in zip(*np.nonzero(mask))])
        assert result['geometry'].equals(oracle), bits
        assert sum(r["signed_area2"] for r in result["document"]["loops"]) == 2 * int(mask.sum())
        if result["validity"]["ogc_valid"]:
            assert result["comparison"]["polygon_roundtrip"]["exact_equal"], bits


def test_edge_set_and_coordinate_orientation():
    mask = examples()["central_hole"]
    oracle = set()
    for r, c in zip(*np.nonzero(mask)):
        for a, b in (((c,r),(c+1,r)), ((c+1,r),(c+1,r+1)), ((c+1,r+1),(c,r+1)), ((c,r+1),(c,r))):
            if (b, a) in oracle:
                oracle.remove((b, a))
            else:
                oracle.add((a, b))
    assert set((tuple(a),tuple(b)) for a,b in extract_cell_boundaries(mask)) == oracle
    asymmetric = np.zeros((8,8), dtype=np.uint8); asymmetric[1:3,4:7] = 1
    result = convert_exact(asymmetric)
    assert result["geometry"].bounds == (4,1,7,3)
    assert result["document"]["loops"][0]["signed_area2"] == 12
    assert result["boundaries"]["vertices_after_coalescing"] == 4


@pytest.mark.parametrize("mask,message", [
    (np.zeros((8,8),dtype=np.uint8), "Empty solid"),
    (np.ones((0,0),dtype=np.uint8), "nonempty square"),
    (np.ones((8,7),dtype=np.uint8), "square"),
    (np.ones((8,8,1),dtype=np.uint8), "two-dimensional"),
    (np.ones(8,dtype=np.uint8), "two-dimensional"),
    (np.ones((8,8),dtype=float), "uint8"),
    (np.ones((8,8),dtype=bool), "uint8"),
    (np.full((8,8),2,dtype=np.uint8), "binary values"),
    ([[1]], "NumPy array"),
])
def test_invalid_contract(mask, message):
    with pytest.raises(ValueError, match=message):
        validate_mask(mask)


def test_png_npy_exact_correspondence(tmp_path):
    mask = examples()["rectangle"]
    path, preview = tmp_path/'mask.npy', tmp_path/'mask.png'
    np.save(path, mask); Image.fromarray(mask*255).save(preview)
    np.testing.assert_array_equal(load_binary_reference(path, preview), mask)
    Image.fromarray((1-mask)*255).save(preview)
    with pytest.raises(ValueError, match="phase mismatch"):
        load_binary_reference(path, preview)
    Image.fromarray(mask*254).save(preview)
    with pytest.raises(ValueError, match="phase mismatch"):
        load_binary_reference(path, preview)
    with pytest.raises(ValueError, match="must be NPY"):
        load_binary_reference(preview)


def test_real_1024_sources_and_expected_blocker():
    root = Path(__file__).resolve().parents[1]
    for name, status in (("design_000/seed_000", "HOLD_GEOMETRY"), ("design_009/seed_001", "PASS_EXACT_BASELINE")):
        folder = root/'experiments/pipeline_v0.4.1/resolution_validation'/name/'1024'
        manifest = json.loads((folder/'manifest.json').read_text())
        from metamaterial_eval.geometry.inputs import sha256_file
        assert sha256_file(folder/'microstructure.npy') == manifest['files']['microstructure.npy']['sha256']
        result = convert_exact(load_binary_reference(folder/'microstructure.npy', folder/'microstructure.png'))
        assert result["status"] == status
        assert result["comparison"]["xor_pixels"] == 0
        assert result["validity"]["area_equals_occupied_cells"]


def test_reporting_refuses_existing_runs_and_wrong_location(tmp_path):
    from metamaterial_eval.geometry.reporting import run
    root = tmp_path/'repository'
    old = root/'experiments/pipeline_v0.5/completed'
    old.mkdir(parents=True)
    marker = old/'preserved.txt'; marker.write_text('do not overwrite')
    with pytest.raises(FileExistsError, match='Refusing to overwrite'):
        run(old, root=root)
    assert marker.read_text() == 'do not overwrite'
    with pytest.raises(ValueError, match='pipeline_v0.5'):
        run(root/'experiments/pipeline_v0.4', root=root)
