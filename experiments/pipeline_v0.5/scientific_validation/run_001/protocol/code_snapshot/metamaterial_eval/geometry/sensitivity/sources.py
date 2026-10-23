"""Verified loading of saved qualified artifacts; no generator or repair calls."""
import hashlib
import json
from pathlib import Path
import shapely
from ..inputs import load_binary_reference


def digest(path):
    path=Path(path)
    if not path.is_file():raise FileNotFoundError('Required saved geometry/provenance artifact missing: '+str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fixture(root,protocol,identifier):
    root=Path(root);study=root/protocol['source_study'];folder=study/identifier
    expected={r['path']:r.get('sha256') for r in json.loads((study/'verification/new_files.json').read_text())['new_files']}
    paths={'qualification':folder/protocol['source_policy']/'qualification.json',
           'manifold':folder/protocol['source_policy']/'manifold_candidate.wkb',
           'exact':folder/'exact_geometry/exact_polygon.wkb',
           'exact_boundaries':folder/'exact_geometry/exact_boundaries.json',
           'input_manifest':folder/'input_manifest.json'}
    hashes={}
    for key,path in paths.items():
        actual=digest(path);relative=path.relative_to(root).as_posix()
        if expected.get(relative)!=actual:
            raise ValueError('Saved v0.5A.1 artifact hash mismatch: '+relative)
        hashes[key]=actual
    q=json.loads(paths['qualification'].read_text());m=json.loads(paths['input_manifest'].read_text())
    if not q['accepted'] or q['state']!='manifold_candidate' or q['contact_policy']!=protocol['source_policy']:
        raise ValueError('Source is not a saved accepted manifold candidate: '+identifier)
    if hashes['exact']!=m['exact_polygon_sha256']:
        raise ValueError('Exact geometry reference hash mismatch.')
    canonical=root/m['source_directory']/'microstructure.npy';preview=canonical.with_suffix('.png')
    if digest(canonical)!=m['input_sha256'] or digest(preview)!=m['input_png_sha256']:
        raise ValueError('Canonical NPY/PNG hash mismatch.')
    mask=load_binary_reference(canonical,preview)
    if mask.shape!=(protocol['resolution'],protocol['resolution']):
        raise ValueError('Source mask resolution differs from the registered protocol.')
    baseline=shapely.from_wkb(paths['manifold'].read_bytes());exact=shapely.from_wkb(paths['exact'].read_bytes())
    if baseline.is_empty or baseline.geom_type not in ('Polygon','MultiPolygon') or not baseline.is_valid:
        raise ValueError('Qualified saved baseline is empty, invalid or nonpolygonal.')
    return {'id':identifier,'baseline':baseline,'exact':exact,'mask':mask,'qualification':q,'input_manifest':m,
            'exact_document':json.loads(paths['exact_boundaries'].read_text()),
            'provenance':{'fixture':identifier,'paths':{k:p.relative_to(root).as_posix() for k,p in paths.items()},
                          'sha256':hashes,'canonical_path':canonical.relative_to(root).as_posix(),
                          'canonical_sha256':digest(canonical),'coordinates':m['coordinates'],
                          'registered_source_controls':m['requested'],'generator_version':m['generator_version'],
                          'generator_sha256':m['generator_sha256'],'saved_topology_repair':m['saved_topology_repair']}}
