"""Independent checks of delivered meshes and actual generic slicer outputs."""
import tempfile
from pathlib import Path
import numpy as np
import pytest
import shapely
from shapely import affinity
from shapely.geometry import box
import trimesh
import manifold3d
from scripts.v070_protocol import read,sha
from scripts.v074_experiment import ASSETS,RUN
from scripts.v074_porous import CACHE,extrude
from scripts.v074_toolpaths import parse
from scripts.v074_stl import heightfield

FILES=['P3_REFERENCE_PRINT_READY.stl','POROUS_METAMATERIAL_FULL1024_ORIGINAL.stl',
    'POROUS_METAMATERIAL_ORIGINAL.stl','POROUS_METAMATERIAL_PRINT_READY.stl']


@pytest.mark.parametrize('name',FILES)
def test_actual_STL_reimport_topology_and_hash(name):
    document='STL_VALIDATION.json' if name.startswith('P3') else 'POROUS_METAMATERIAL_STL_VALIDATION.json'
    r=read(ASSETS/document)['variants'][name]
    assert r['passed'] and all(r['checks'].values())
    assert sha(ASSETS/name)==r.get('file_sha256',r.get('STL_sha256'))
    m=trimesh.load_mesh(ASSETS/name,process=False);m.merge_vertices();m.remove_unreferenced_vertices()
    assert m.is_watertight and m.is_winding_consistent and m.volume>0
    assert np.all(np.bincount(m.edges_unique_inverse)==2)
    assert np.all(m.area_faces>1e-10) and len(m.split(only_watertight=False))==1
    assert len(np.unique(np.sort(m.faces,axis=1),axis=0))==len(m.faces)


def test_exact_P3_remains_explicitly_unqualified_for_diagonal_contacts():
    r=read(ASSETS/'STL_VALIDATION.json')['variants']['P3_REFERENCE_EXACT_RELIEF.stl']
    assert sha(ASSETS/'P3_REFERENCE_EXACT_RELIEF.stl')==r['file_sha256']
    assert not r['passed'] and r['nonmanifold_edges']==14


def test_P3_print_export_is_byte_deterministic_from_saved_print_mask():
    a=np.load(ASSETS/'P3_PRINT_SAFE_DISPLAY_MASK.npy',allow_pickle=False)==5
    raw=heightfield(a)
    solid=manifold3d.Manifold(manifold3d.Mesh(np.asarray(raw.vertices,dtype=np.float32),np.asarray(raw.faces,dtype=np.uint32)))
    compact=solid.simplify(1e-7).to_mesh()
    mesh=trimesh.Trimesh(compact.vert_properties[:,:3],compact.tri_verts,process=False)
    with tempfile.TemporaryDirectory() as directory:
        p=Path(directory)/'repeat.stl';mesh.export(p,file_type='stl')
        assert sha(p)==sha(ASSETS/'P3_REFERENCE_PRINT_READY.stl')


@pytest.mark.parametrize('name', ['P3_REFERENCE_PRINT_READY.stl','POROUS_METAMATERIAL_PRINT_READY.stl'])
def test_actual_generic_slicer_extrusions_on_bed_and_all_layers(name):
    r=read(RUN/'fabrication'/f'{Path(name).stem}_TOOLPATH_VALIDATION.json')
    assert r['passed'] and all(r['checks'].values()) and not r['actual_printer_known']
    assert sha(Path(r['raw_Gcode_path']))==r['Gcode_sha256']
    rows,filament,estimate=parse(Path(r['raw_Gcode_path']))
    assert len(rows)==r['extruding_segment_count'] and filament==pytest.approx(r['filament_mm_from_actual_E_moves_retraction_compensated'])
    assert len({x['layer'] for x in rows})==(18 if name.startswith('P3') else 25)
    if name.startswith('POROUS'):
        assert len(r['through_pore_checks'])==35
        assert all(x['representative_center_clear'] and x['extrusion_overlap_core_mm2']<.001 for x in r['through_pore_checks'])


@pytest.mark.parametrize('variant',['full','crop','framed'])
def test_porous_export_is_byte_deterministic_from_authenticated_polygon(variant):
    p=shapely.from_wkb((CACHE/'polygon_candidate.wkb').read_bytes())
    if variant!='full':
        clipped=p.intersection(box(384,384,640,640))
        p=[g for g in clipped.geoms if g.area>0][0]
        p=affinity.translate(p,xoff=-384,yoff=-384)
    size=1024 if variant=='full' else 256
    p=affinity.scale(affinity.translate(affinity.scale(p,xfact=1,yfact=-1,origin=(0,0)),yoff=size),xfact=160/size,yfact=160/size,origin=(0,0))
    if variant=='framed':p=affinity.translate(p.union(box(-2.5,-2.5,162.5,162.5).difference(box(0,0,160,160))),xoff=2.5,yoff=2.5)
    name={'full':'POROUS_METAMATERIAL_FULL1024_ORIGINAL.stl','crop':'POROUS_METAMATERIAL_ORIGINAL.stl','framed':'POROUS_METAMATERIAL_PRINT_READY.stl'}[variant]
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/name;extrude(p,path)
        assert sha(path)==sha(ASSETS/name)
