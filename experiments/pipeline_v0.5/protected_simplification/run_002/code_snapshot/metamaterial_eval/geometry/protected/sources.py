"""Authenticated unchanged development inputs and additive holdout ingress."""
import json
from pathlib import Path
import shapely
from ..inputs import load_binary_reference
from ..conversion import convert_exact, geometry_bytes
from ..manifold.candidates import qualify_manifold_geometry
from ..sensitivity.sources import load_fixture, digest
from ..sensitivity.records import write_json


def development(root, config, identifier):
    return load_fixture(root,config['b1_config'],identifier)


def holdout(root, output, config, identifier):
    """Only call after code/config freeze. No source masks or generators run."""
    root,output = Path(root),Path(output)
    source = next(s for s in config['sources'] if s['fixture']==identifier and s['role']=='holdout')
    path = root/source['manifest']; manifest = json.loads(path.read_text())
    if digest(path)!=source['manifest_sha256'] or digest(path.parent/'microstructure.npy')!=source['npy_sha256']:
        raise ValueError('Reserved holdout source hash changed.')
    for name in ('microstructure.npy','microstructure.png'):
        if digest(path.parent/name)!=manifest['files'][name]['sha256']:
            raise ValueError('Holdout historical manifest mismatch: '+name)
    mask = load_binary_reference(path.parent/'microstructure.npy',path.parent/'microstructure.png')
    if mask.shape!=(1024,1024): raise ValueError('Reserved holdout is not native 1024.')
    folder = output/'sources'/identifier; folder.mkdir(parents=True,exist_ok=False)
    exact = convert_exact(mask)
    if exact['geometry'] is None:
        write_json(folder/'INGRESS_REJECTED.json',{'reason':'Frozen exact converter could not construct source polygon.'})
        return None
    (folder/'exact_polygon.wkb').write_bytes(shapely.to_wkb(exact['geometry'],byte_order=1))
    (folder/'exact_boundaries.json').write_bytes(geometry_bytes(exact['document']))
    result = qualify_manifold_geometry(mask,exact,'solid_separate_contacts')
    serialized = {k:v for k,v in result.items() if k not in ('geometry','reconstructed')}
    write_json(folder/'ingress_qualification.json',serialized)
    if not result['accepted'] or result['geometry'] is None:
        write_json(folder/'INGRESS_REJECTED.json',{'reason':'Frozen A1-policy ingress did not qualify.', 'failed_gates':result.get('failed_gates')})
        return None
    (folder/'ingress_manifold.wkb').write_bytes(shapely.to_wkb(result['geometry'],byte_order=1))
    m = {'source_directory':path.parent.relative_to(root).as_posix(),
         'saved_topology_repair':manifest['topology_repair'],'coordinates':exact['document']['coordinates'],
         'requested':manifest['requested'],'generator_version':manifest['generator_version'],
         'generator_sha256':manifest['generator_sha256']}
    write_json(folder/'input_manifest.json',m)
    paths = {'exact':folder/'exact_polygon.wkb','exact_boundaries':folder/'exact_boundaries.json',
             'manifold':folder/'ingress_manifold.wkb','qualification':folder/'ingress_qualification.json',
             'input_manifest':folder/'input_manifest.json'}
    return {'id':identifier,'baseline':result['geometry'],'exact':exact['geometry'],'mask':mask,
            'qualification':serialized,'input_manifest':m,'exact_document':exact['document'],
            'provenance':{'fixture':identifier,'source_manifest':source,
                'paths':{k:p.relative_to(root).as_posix() for k,p in paths.items()},
                'sha256':{k:digest(p) for k,p in paths.items()},
                'canonical_path':(path.parent/'microstructure.npy').relative_to(root).as_posix(),
                'canonical_sha256':source['npy_sha256'],
                'ingress_scope':'New B2 holdout ingress under unchanged A/A1 algorithms and gates. Does not amend historical A1 acceptance.'}}
