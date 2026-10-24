"""Read authenticated persisted sources; never invoke a generator or repair."""
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely
from shapely.affinity import affine_transform
from shapely.geometry.polygon import orient
from ..geometry.inputs import load_binary_reference, sha256_file
from ..geometry.manifold.contacts import inspect_boundary
from ..geometry.planar import rasterize_exact_geometry
from ..geometry.topology import analyze_raster_topology
from ..geometry.validation.checks import select_probes

FIXTURE = Path('experiments/pipeline_v0.5/baseline_vectorization/run_003/fixture_B_design009_seed001')


def engineering_geometry(geometry, resolution, config):
    """Explicit reflection: x'=x*W/N, y'=H-y*H/N; then restore CCW shell."""
    return orient(affine_transform(geometry, [config.width/resolution, 0, 0,
                 -config.height/resolution, 0, config.height]), sign=1)


def authenticate_fixture(root, config):
    root = Path(root)
    folder = root / FIXTURE
    provenance = json.loads((folder/'input_provenance.json').read_text())
    source = root/provenance['source_npy']
    checks = [('source_npy', 'input_sha256'), ('source_png', 'png_sha256'),
              ('source_manifest', 'source_manifest_sha256')]
    for path_key, hash_key in checks:
        if sha256_file(root/provenance[path_key]) != provenance[hash_key]:
            raise ValueError(f'Authentication failed: {path_key}')
    manifest = json.loads((root/provenance['source_manifest']).read_text())
    for key in ('generator_sha256', 'native_renderer_sha256', 'source_v03_generator_sha256', 'evaluator_sha256'):
        if manifest[key] != provenance[key]:
            raise ValueError(f'Generator provenance mismatch: {key}')
    for filename, key in [('stabilized_resolution.py','generator_sha256'),
                          ('native_resolution.py','native_renderer_sha256'),
                          ('v03_baseline.py','source_v03_generator_sha256')]:
        if sha256_file(root/'metamaterial_eval/generators'/filename) != provenance[key]:
            raise ValueError(f'Frozen source changed: {filename}')
    mask = load_binary_reference(source, root/provenance['source_png'])
    if mask.shape != (1024, 1024) or hashlib.sha256(mask.tobytes()).hexdigest() != provenance['pixel_sha256']:
        raise ValueError('Canonical resolution/pixel hash mismatch')
    wkb = folder/'polygon_candidate.wkb'
    # Authenticate WKB against independently serialized exact loops, not its own hash.
    from ..geometry.planar import build_exact_planar_geometry
    document = json.loads((folder/'exact_boundaries.json').read_text())
    geometry = shapely.from_wkb(wkb.read_bytes())
    if not geometry.equals_exact(build_exact_planar_geometry(document['loops']), 0):
        raise ValueError('Persisted WKB differs from exact boundary serialization')
    if geometry.geom_type != 'Polygon' or not geometry.is_valid or not inspect_boundary(geometry)['manifold']:
        raise ValueError('Unsupported invalid, multipart or nonmanifold geometry')
    if not np.array_equal(rasterize_exact_geometry(geometry, 1024), mask) or geometry.area != int(mask.sum()):
        raise ValueError('Geometry occupancy or area mismatch')
    topology = analyze_raster_topology(mask)
    if not topology['intended_network']:
        raise ValueError('Require one solid component and both percolation directions')
    probes = [p for p in select_probes(mask) if p['phase'] == 'solid']
    record = {**provenance, 'geometry_state': 'exact_manifold_no_new_regularization',
              'geometry_sha256': sha256_file(wkb), 'geometry_path': str(FIXTURE/'polygon_candidate.wkb'),
              'resolution': 1024, 'solid_area_cell2': geometry.area, 'holes': len(geometry.interiors),
              'minimum_clearance_cell': geometry.minimum_clearance,
              'minimum_sampled_solid_chord_cell': min(p['source_pixel_run'] for p in probes),
              'source_only_solid_probes': probes, 'topology': topology,
              'scientific_status': 'HOLD_CUMULATIVE_SMALL_PORE_FIDELITY',
              'width_certification': 'FINITE_AXIAL_SCREEN_ONLY',
              'transform': {'x': 'x*W/1024', 'y': 'H-y*H/1024', 'origin': 'lower_left', 'axes': 'x_right_y_up'},
              'physical_solid_area_mm2': geometry.area*config.width*config.height/1024**2}
    return engineering_geometry(geometry, 1024, config), mask, record
