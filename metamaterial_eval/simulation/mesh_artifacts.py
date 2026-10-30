"""Portable, authenticated mesh artifacts; raw files are never Git payloads."""
import argparse
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path,PureWindowsPath
import time
import zipfile
import numpy as np
from .config import CompressionConfig
from .geometry_adapter import authenticate_fixture
from .mesh_generation import Mesh,generate_mesh,save_mesh
from .mesh_remediation import POLICY_B
from .mesh_validation import validate_mesh,feature_resolution
from .reporting import write_json,mesh_hash
from .solver_execution import file_hash

HISTORICAL='e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc'
SOURCE='4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1'
REPO=Path(__file__).resolve().parents[2]


def artifact_root():
    override=os.environ.get('YD_ARTIFACT_ROOT')
    if override:return Path(override).expanduser().resolve()
    if os.name=='nt':return Path(os.environ['LOCALAPPDATA'])/'YoungDawgs/artifacts'
    return Path(os.environ.get('XDG_CACHE_HOME',str(Path.home()/'.cache')))/'YoungDawgs/artifacts'


def contained_path(root,relative):
    relative=str(relative).replace('\\','/')
    if PureWindowsPath(relative).drive or Path(relative).is_absolute():raise ValueError('Artifact path must be relative to configured root')
    root=Path(root).resolve();path=(root/relative).resolve()
    if not path.is_relative_to(root):raise ValueError('Artifact path escapes configured root')
    return path


def normalized_protocol(path,expected):
    raw=Path(path).read_bytes();lf=raw.replace(b'\r\n',b'\n')
    digest=hashlib.sha256(lf).hexdigest()
    if digest!=expected:raise ValueError('Frozen protocol content differs beyond CRLF normalization')
    return json.loads(lf),{'byte_sha256':hashlib.sha256(raw).hexdigest(),'LF_sha256':digest,
                         'CRLF_normalization_only':raw!=lf,'historical_file_modified':False}


def load_archive(path,*,source_hash=None,expected_semantic=None,expected_bytes=None):
    path=Path(path)
    if not path.is_file():raise FileNotFoundError('Missing mesh archive')
    attrs=getattr(path.stat(),'st_file_attributes',0)
    # Read/test actual data: placeholders must hydrate successfully, never pass
    # merely because a directory entry exists. OS/provider failure propagates.
    if expected_bytes and file_hash(path)!=expected_bytes:raise ValueError('Mesh byte hash mismatch')
    try:
        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:raise ValueError('Corrupt NPZ member')
        with np.load(path,allow_pickle=False) as z:
            required={'nodes','triangles','boundary','boundary_groups'}
            if not required.issubset(z.files):raise ValueError('Missing mesh arrays')
            mesh=Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])
    except (zipfile.BadZipFile,EOFError,OSError) as exc:raise ValueError('Unreadable/corrupt mesh archive') from exc
    if mesh.nodes.dtype!=np.dtype('float64') or mesh.triangles.dtype!=np.dtype('int64') or mesh.boundary.dtype!=np.dtype('int64'):
        raise ValueError('Require registered float64 nodes and int64 connectivity')
    if mesh.nodes.ndim!=2 or mesh.nodes.shape[1]!=2 or not np.isfinite(mesh.nodes).all():raise ValueError('Invalid node array')
    if mesh.triangles.ndim!=2 or mesh.triangles.shape[1]!=6 or not len(mesh.triangles):raise ValueError('Invalid TRI6 shape')
    if mesh.triangles.min()<0 or mesh.triangles.max()>=len(mesh.nodes):raise ValueError('Connectivity out of bounds')
    if np.any(np.diff(np.sort(mesh.triangles,axis=1),axis=1)==0):raise ValueError('Repeated node in TRI6')
    if mesh.boundary.ndim!=2 or mesh.boundary.shape[1]!=3 or mesh.boundary.min()<0 or mesh.boundary.max()>=len(mesh.nodes):raise ValueError('Invalid boundary connectivity')
    if mesh.boundary_groups.dtype.kind not in 'SU' or mesh.boundary_groups.shape!=(len(mesh.boundary),):raise ValueError('Invalid boundary labels')
    if source_hash is not None and source_hash!=SOURCE:raise ValueError('Source identity mismatch')
    semantic=mesh_hash(mesh)
    if expected_semantic and semantic!=expected_semantic:raise ValueError('Mesh semantic hash mismatch')
    return mesh,{'semantic_sha256':semantic,'byte_sha256':file_hash(path),'bytes':path.stat().st_size,
                'nodes':len(mesh.nodes),'TRI6':len(mesh.triangles),'file_attributes_before_read':attrs,
                'archive_bytes_read_and_CRC_verified':True}


def identity(semantic,accepted):
    if not accepted:return 'MESH_REGENERATION_HOLD'
    return 'HISTORICAL_MESH_IDENTITY_VERIFIED' if semantic==HISTORICAL else 'NEW_REGENERATED_MESH_QUALIFIED'


def reproduce(output,root):
    output,root=Path(output),Path(root).resolve();output.mkdir(parents=True,exist_ok=False)
    registered=REPO/'experiments/pipeline_v0.6.3/run_001/protocol/RECOVERY_AND_GATES.json'
    protocol=json.loads(registered.read_text())
    frozen,normalization=normalized_protocol(REPO/protocol['frozen_mesh_protocol'],protocol['frozen_mesh_protocol_sha256'])
    write_json(output/'protocol_authentication.json',normalization)
    if importlib.metadata.version('gmsh')!='4.15.0':raise ValueError('Frozen Gmsh 4.15.0 required')
    level=next(x for x in frozen['new_full_mesh_levels_after_strategy_identified'] if x['id']=='fine_new')
    config=replace(CompressionConfig(),boundary_size=level['boundary_size_mm'],bulk_size=level['bulk_size_mm'])
    geometry,_,provenance=authenticate_fixture(REPO,config)
    if provenance['geometry_sha256']!=SOURCE:raise ValueError('Canonical geometry differs')
    settings={'config':config.manifest(),'meshing_policy':asdict(POLICY_B),'gmsh':'4.15.0',
              'frozen_protocol_LF_sha256':normalization['LF_sha256']}
    settings_hash=hashlib.sha256(json.dumps(settings,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    directory=root/'meshes/design009_seed001_native1024/v063_regen_001'
    directory.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    print('Generating frozen fine_new from authenticated geometry',flush=True)
    mesh=generate_mesh(geometry,config,policy=POLICY_B)
    generation=time.perf_counter()-started;save_mesh(mesh,directory/'mesh.npz')
    if len(mesh.nodes)>4000000 or len(mesh.triangles)>1800000:raise ValueError('Frozen mesh size budget exceeded')
    print(f'Generated {len(mesh.nodes)} nodes / {len(mesh.triangles)} TRI6; validating unchanged gates',flush=True)
    at=time.perf_counter();quality,distribution=validate_mesh(mesh,geometry,config)
    validation=time.perf_counter()-at
    at=time.perf_counter();features=feature_resolution(mesh,provenance['source_only_solid_probes'],config)
    feature_seconds=time.perf_counter()-at
    _,inventory=load_archive(directory/'mesh.npz',source_hash=SOURCE)
    status=identity(inventory['semantic_sha256'],quality['accepted'] and features['accepted'])
    manifest={'schema':'young-dawgs-mesh-artifact-v1','logical_artifact_id':'design009-seed001-native1024-v063-regen001',
              'source_geometry_sha256':SOURCE,'generation_configuration_sha256':settings_hash,'settings':settings,
              **inventory,'identity_status':status,'geometry_qualification':'PASS' if quality['accepted'] and features['accepted'] else 'HOLD',
              'artifact_relative_path':str((directory/'mesh.npz').relative_to(root)),'artifact_root_selector':'YD_ARTIFACT_ROOT or per-user local cache',
              'known_storage_root':str(root),'generation_seconds':generation,'validation_seconds':validation,
              'feature_seconds':feature_seconds,'total_seconds':time.perf_counter()-started,
              'reproduction_command':'python -m metamaterial_eval.simulation.mesh_artifacts reproduce --output NEW_EVIDENCE_PATH',
              'historical_semantic_sha256':HISTORICAL,'historical_counts':{'nodes':2766505,'TRI6':1261670},
              'mechanical_mesh_convergence':'UNQUALIFIED','scientific_status':provenance['scientific_status']}
    write_json(directory/'artifact_manifest.json',manifest)
    write_json(output/'artifact_manifest.json',manifest);write_json(output/'mesh_quality.json',quality)
    write_json(output/'feature_resolution.json',features)
    write_json(output/'generation_configuration.json',settings)
    # Full distributions remain local, not a large tracked binary.
    np.savez_compressed(directory/'quality.npz',quality=distribution)
    print(json.dumps({'status':status,'mesh':inventory,'minimum_angle':quality['min_angle_deg'],'features':features['minimum_elements_across']}),flush=True)
    return manifest


def resolve_manifest(path,root=None):
    manifest=json.loads(Path(path).read_text())
    if manifest['geometry_qualification']!='PASS':raise ValueError('Artifact is not geometrically qualified')
    location=contained_path(root or artifact_root(),manifest['artifact_relative_path'])
    # Packaged Windows apps may virtualize LOCALAPPDATA. A normal terminal can
    # use the recorded existing root when no explicit selector was supplied.
    if not location.is_file() and root is None and not os.environ.get('YD_ARTIFACT_ROOT') and manifest.get('known_storage_root'):
        recorded=contained_path(manifest['known_storage_root'],manifest['artifact_relative_path'])
        if recorded.is_file():location=recorded
    mesh,record=load_archive(location,source_hash=manifest['source_geometry_sha256'],
                             expected_semantic=manifest['semantic_sha256'],expected_bytes=manifest['byte_sha256'])
    return mesh,manifest,location


def discover_artifacts(root=None,logical_id=None):
    """Search only the configured mesh registry, not arbitrary user directories."""
    root=Path(root or artifact_root()).resolve();found=[]
    for path in sorted((root/'meshes').glob('**/artifact_manifest.json')):
        manifest=json.loads(path.read_text())
        if manifest.get('schema')!='young-dawgs-mesh-artifact-v1':continue
        if logical_id and manifest.get('logical_artifact_id')!=logical_id:continue
        location=contained_path(root,manifest['artifact_relative_path'])
        found.append({'manifest':str(path),'logical_artifact_id':manifest['logical_artifact_id'],
                      'path':str(location),'bytes_available':location.is_file(),
                      'identity_check':'MANIFEST_ONLY_CALL_VERIFY_BEFORE_USE'})
    return found


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['reproduce','verify','discover'])
    p.add_argument('--output',type=Path);p.add_argument('--manifest',type=Path);p.add_argument('--root',type=Path)
    a=p.parse_args()
    if a.action=='reproduce':reproduce(a.output,a.root or artifact_root())
    elif a.action=='verify':
        _,m,location=resolve_manifest(a.manifest,a.root);print(m['identity_status'],location)
    else:print(json.dumps(discover_artifacts(a.root),indent=2))


if __name__=='__main__':main()
