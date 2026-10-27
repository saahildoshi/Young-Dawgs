"""Registered remediation, immutable boundary and independent metric controls."""
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
import pytest
from shapely import box
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.element_quality import corner_metrics,quadratic_mapping
from metamaterial_eval.simulation.mesh_generation import MeshingPolicy,generate_mesh
from metamaterial_eval.simulation.mesh_remediation import POLICY_B,relocate_saved,saved_patch,study
from metamaterial_eval.simulation.mesh_diagnosis import source_corner_angles
from metamaterial_eval.simulation.mesh_validation import validate_mesh
from metamaterial_eval.simulation.reporting import mesh_hash


@pytest.fixture
def model():
    pytest.importorskip('gmsh')
    config=CompressionConfig(width=1,height=1,boundary_size=.04,bulk_size=.12)
    geometry=box(0,0,1,1).difference(box(.3,.3,.7,.7))
    return geometry,config


def test_boundary_field_and_quadratic_policy_preserve_pore(model):
    g,c=model;m=generate_mesh(g,c,policy=POLICY_B)
    quality,_=validate_mesh(m,g,c)
    assert quality['accepted'] and quality['holes']==1
    assert quality['quadratic_mapping']['invalid_or_uncertified']==0
    assert quality['boundary_error_mm']<1e-12
    assert quality['relative_area_error']<1e-12
    edges=m.nodes[m.boundary[:,:2]]
    assert np.linalg.norm(edges[:,1]-edges[:,0],axis=1).max()<=c.boundary_size*1.01


def test_actual_small_policy_repeatability(model):
    g,c=model
    assert mesh_hash(generate_mesh(g,c,policy=POLICY_B))==mesh_hash(generate_mesh(g,c,policy=POLICY_B))


def test_incorrect_optimizer_boundary_motion_rejected_and_preserved(tmp_path,model,monkeypatch):
    import gmsh
    g,c=model;m=generate_mesh(g,c)
    fixed=int(np.unique(m.boundary[:,:2])[0])+1
    def move_boundary(*args,**kwargs):
        xyz,param,*_=gmsh.model.mesh.getNode(fixed)
        xyz[0]+=.001;gmsh.model.mesh.setNode(fixed,xyz,param)
    monkeypatch.setattr(gmsh.model.mesh,'optimize',move_boundary)
    failed=tmp_path/'rejected.npz'
    with pytest.raises(ValueError,match='fixed boundary'):
        relocate_saved(m,failure_output=failed)
    assert failed.exists()
    with np.load(failed) as z:
        assert z['nodes'][fixed-1,0]!=m.nodes[fixed-1,0]


def test_mesh_moving_accepted_source_boundary_rejected(model):
    g,c=model;m=generate_mesh(g,c,policy=POLICY_B)
    moved=m.nodes.copy();moved[:,0]*=1.001
    quality,_=validate_mesh(replace(m,nodes=moved),g,c)
    assert not quality['accepted'] and not quality['gates']['boundary']


def test_patch_is_explicit_and_closed(model):
    g,c=model;m=generate_mesh(g,c)
    patch,scope=saved_patch(m,0,radius=.1)
    assert scope['scope']=='CROPPED_MESH_DIAGNOSTIC_NOT_FULL_SPECIMEN'
    assert len(patch.nodes)==len(np.unique(patch.triangles))
    assert quadratic_mapping(patch.nodes[patch.triangles])['positive_over_reference_triangle'].all()
    assert set(patch.boundary.ravel()).issubset(set(patch.triangles.ravel()))


def test_immutable_rectilinear_geometry_has_no_forced_acute_wedge(model):
    g,_=model
    angles=source_corner_angles(g)
    assert set(angles)=={90,270}
    assert np.min(angles)>=10


@pytest.mark.parametrize('iterations',[-1,11,2.5])
def test_unregistered_optimizer_budget_rejected(iterations):
    with pytest.raises(ValueError):MeshingPolicy(relocate_iterations=iterations)


def test_invalid_local_evidence_blocks_full_study(tmp_path):
    p=tmp_path/'evidence.json';p.write_text(json.dumps({'B_supported_for_full_candidate':False}))
    with pytest.raises(RuntimeError,match='local strategy'):study(tmp_path/'full',p)
    assert not (tmp_path/'full').exists()
