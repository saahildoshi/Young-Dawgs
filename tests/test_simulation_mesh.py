"""Analytical geometry controls; no FEM results or solver PASS are fabricated."""
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from shapely import Polygon, box
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.geometry_adapter import authenticate_fixture, engineering_geometry
from metamaterial_eval.simulation.mesh_generation import Mesh, generate_mesh
from metamaterial_eval.simulation.mesh_validation import validate_mesh, feature_resolution


@pytest.fixture
def config():
    return CompressionConfig(width=1,height=1,boundary_size=.04,bulk_size=.12)


def test_explicit_y_reflection_and_scaling(config):
    g=engineering_geometry(box(4,1,7,3),8,config)
    assert g.bounds==(.5,.625,.875,.875)
    assert g.exterior.is_ccw
    assert g.area==pytest.approx(6/64)


@pytest.mark.parametrize('kw',[{'young_modulus':0},{'height':float('nan')},{'poisson_ratio':.5},
    {'mode':'3D'},{'mode':'plane_strain','thickness':2},{'strains':(.02,.01)},
    {'strains':(.05,)},{'units':'SI'},{'bulk_size':1e-5}])
def test_invalid_configuration(kw):
    with pytest.raises(ValueError):CompressionConfig(**kw)


@pytest.mark.parametrize('holes',[[],[box(.3,.3,.7,.7)], [box(.2,.2,.4,.4),box(.6,.6,.8,.8)]])
def test_actual_gmsh_holes_domain_topology(config,holes):
    pytest.importorskip('gmsh')
    g=Polygon(box(0,0,1,1).exterior.coords,[h.exterior.coords for h in holes])
    m=generate_mesh(g,config)
    q,_=validate_mesh(m,g,config)
    assert q['accepted'],q
    assert q['holes']==len(holes)
    assert q['relative_area_error']<1e-12
    assert q['min_jacobian_det_mm2']>0
    assert ('pore' in q['boundary_counts'])==bool(holes)


def test_unsupported_geometry_rejected(config):
    pytest.importorskip('gmsh')
    for g in [box(0,0,.4,1).union(box(.6,0,1,1)), Polygon([(0,0),(1,1),(0,1),(1,0)])]:
        with pytest.raises(ValueError):generate_mesh(g,config)


def test_adversarial_connectivity_and_boundary(config):
    pytest.importorskip('gmsh')
    g=box(0,0,1,1);m=generate_mesh(g,config)
    t=m.triangles.copy();t[0,[0,1]]=t[0,[1,0]]
    with pytest.raises(ValueError,match='Jacobian'):validate_mesh(replace(m,triangles=t),g,config)
    with pytest.raises(ValueError,match='Boundary inventory'):validate_mesh(replace(m,boundary=m.boundary[:-1]),g,config)
    t=m.triangles.copy();t[0,3]=t[0,4]
    with pytest.raises(ValueError,match='midsides'):validate_mesh(replace(m,triangles=t),g,config)
    with pytest.raises(ValueError,match='orphan'):validate_mesh(replace(m,nodes=np.vstack([m.nodes,[.1,.1]])),g,config)
    labels=m.boundary_groups.copy();labels[labels=='top']='bottom'
    assert not validate_mesh(replace(m,boundary_groups=labels),g,config)[0]['accepted']


def test_sampled_narrow_chords(config):
    pytest.importorskip('gmsh')
    g=box(0,0,1,1).difference(box(.1,.1,.45,.9)).difference(box(.55,.1,.9,.9))
    m=generate_mesh(g,config)
    probes=[{'xy':[.5,.5],'axis':0,'phase':'solid','source_pixel_run':.1}]
    screen=feature_resolution(m,probes,config,resolution=1)
    assert screen['records'][0]['covered_mm']==pytest.approx(.1)
    assert screen['exhaustive_neck_certification']=='UNQUALIFIED'


def test_real_source_authentication():
    root=Path(__file__).resolve().parents[1]
    g,mask,p=authenticate_fixture(root,CompressionConfig())
    assert len(g.interiors)==412 and mask.shape==(1024,1024)
    assert p['solid_area_cell2']==500104
    assert p['topology']['intended_network']
    assert p['topology_repair']['added_pixels']==15
    assert p['geometry_state']=='exact_manifold_no_new_regularization'
