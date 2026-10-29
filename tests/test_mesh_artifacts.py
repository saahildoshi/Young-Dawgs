"""Small archive/unit controls; never synthetic ANSYS integration evidence."""
import hashlib
from pathlib import Path
import numpy as np
import pytest
from metamaterial_eval.simulation.mesh_artifacts import (
    SOURCE,HISTORICAL,load_archive,identity,contained_path,normalized_protocol,artifact_root)
from metamaterial_eval.simulation.mesh_generation import Mesh,save_mesh
from metamaterial_eval.simulation.reporting import mesh_hash
from metamaterial_eval.simulation.solver_execution import file_hash


@pytest.fixture
def archive(tmp_path):
    m=Mesh(np.array([[0.,0.],[1,0],[0,1],[.5,0],[.5,.5],[0,.5]]),
        np.array([[0,1,2,3,4,5]],dtype=np.int64),np.array([[0,1,3],[1,2,4],[2,0,5]],dtype=np.int64),
        np.array(['bottom','external','external']))
    path=tmp_path/'mesh.npz';save_mesh(m,path)
    return path,m


def test_complete_archive_semantic_and_byte_hash(archive):
    p,m=archive;actual,r=load_archive(p,source_hash=SOURCE,expected_semantic=mesh_hash(m),expected_bytes=file_hash(p))
    assert r['archive_bytes_read_and_CRC_verified'] and r['nodes']==6
    assert np.array_equal(actual.triangles,m.triangles)


@pytest.mark.parametrize('field',['source','semantic','bytes'])
def test_mismatched_identity_rejected(archive,field):
    p,_=archive
    kwargs={'source_hash':'wrong'} if field=='source' else {'expected_'+field:'wrong'}
    with pytest.raises(ValueError,match='mismatch'):load_archive(p,**kwargs)


@pytest.mark.parametrize('field',['nodes','triangles','boundary','boundary_groups'])
def test_missing_array_rejected(archive,field):
    p,m=archive;data={k:getattr(m,k) for k in ['nodes','triangles','boundary','boundary_groups'] if k!=field}
    np.savez(p,**data)
    with pytest.raises(ValueError,match='Missing'):load_archive(p)


@pytest.mark.parametrize('damage',['float32','uint32','out_of_bounds','repeated','nonfinite'])
def test_invalid_mesh_arrays_rejected(archive,damage):
    p,m=archive
    if damage=='float32':m.nodes=m.nodes.astype('float32')
    elif damage=='uint32':m.triangles=m.triangles.astype('uint32')
    elif damage=='out_of_bounds':m.triangles[0,0]=6
    elif damage=='repeated':m.triangles[0,0]=1
    else:m.nodes[0,0]=np.nan
    save_mesh(m,p)
    with pytest.raises(ValueError):load_archive(p)


def test_missing_corrupt_and_unhydrated_archives_fail(tmp_path,archive,monkeypatch):
    with pytest.raises(FileNotFoundError):load_archive(tmp_path/'absent.npz')
    bad=tmp_path/'corrupt.npz';bad.write_bytes(b'not an archive')
    with pytest.raises(ValueError,match='corrupt'):load_archive(bad)
    p,_=archive
    def unavailable(*args,**kwargs):raise OSError('Cloud bytes unavailable; unit control')
    monkeypatch.setattr('zipfile.ZipFile',unavailable)
    with pytest.raises(ValueError,match='Unreadable'):load_archive(p)


def test_identity_classification_never_equates_new_hash():
    assert identity(HISTORICAL,True)=='HISTORICAL_MESH_IDENTITY_VERIFIED'
    assert identity('different',True)=='NEW_REGENERATED_MESH_QUALIFIED'
    assert identity(HISTORICAL,False)=='MESH_REGENERATION_HOLD'


def test_protocol_CRLF_authentication_does_not_modify_file(tmp_path):
    p=tmp_path/'protocol.json';data=b'{\r\n "gate":10\r\n}\r\n';p.write_bytes(data)
    normalized=hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()
    value,record=normalized_protocol(p,normalized)
    assert value['gate']==10 and record['CRLF_normalization_only']
    assert p.read_bytes()==data
    with pytest.raises(ValueError):normalized_protocol(p,'wrong')


def test_portable_root_and_no_escape(tmp_path,monkeypatch):
    monkeypatch.setenv('YD_ARTIFACT_ROOT',str(tmp_path))
    assert artifact_root()==tmp_path.resolve()
    with pytest.raises(ValueError):contained_path(tmp_path,'../outside')
