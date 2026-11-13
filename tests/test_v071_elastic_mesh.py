"""Categorical semantics and topology checks, independent of licensed qualification."""
import numpy as np
import pytest
from metamaterial_eval.simulation.composite_elastic import structured_mesh,validate_mesh,source_input,readonly_input


def test_asymmetric_image_orientation_and_solid_materials():
    a=np.array([[5,1,1],[1,1,5]],dtype=np.uint8)
    m=structured_mesh(a)
    assert len(m['nodes'])==12 and len(m['quads'])==6
    centers=m['nodes'][m['quads']].mean(axis=1)
    marked=centers[m['materials']==2]
    assert np.allclose(marked,[[5/6,1/4],[1/6,3/4]])
    assert np.array_equal(a,[[5,1,1],[1,1,5]])
    assert validate_mesh(m)['no_removed_pixels']


@pytest.mark.parametrize('labels',[np.array([[0,1]],dtype=np.uint8),np.array([[1,2]],dtype=np.uint8),np.array([[1,5]],dtype=float)])
def test_unknown_or_porous_labels_rejected(labels):
    with pytest.raises(ValueError):structured_mesh(labels)


def test_bonded_interface_has_two_shared_nodes_and_exact_area():
    m=structured_mesh(np.array([[1,5]],dtype=np.uint8))
    assert set(m['quads'][0])&set(m['quads'][1])=={1,4}
    proof=validate_mesh(m)
    assert proof['shared_material_interface_edges']==1
    assert proof['material_area_fractions']=={'1':.5,'2':.5}
    assert proof['area_mm2']==1.


@pytest.mark.parametrize('k',[1,2])
def test_native_256_grid_counts_and_refinement(k):
    a=np.ones((256,256),dtype=np.uint8);a[:77,9:63]=5
    m=structured_mesh(a,k);proof=validate_mesh(m)
    assert proof['nodes']==(256*k+1)**2 and proof['elements']==65536*k*k
    assert proof['material_elements']['2']==77*54*k*k
    # Independently query an upper-left and lower-right source pixel.
    centers=m['nodes'][m['quads']].mean(axis=1)
    source_rows=np.minimum((256*(1-centers[:,1])).astype(int),255)
    source_cols=np.minimum((256*centers[:,0]).astype(int),255)
    assert np.array_equal(m['materials'],np.where(a[source_rows,source_cols]==5,2,1))


def test_mesh_identity_depends_on_material_geometry_and_refinement():
    a=np.array([[1,5],[1,1]],dtype=np.uint8)
    assert structured_mesh(a)['mesh_id']==structured_mesh(a.copy())['mesh_id']
    assert structured_mesh(a)['mesh_id']!=structured_mesh(np.flipud(a))['mesh_id']
    assert structured_mesh(a)['mesh_id']!=structured_mesh(a,2)['mesh_id']


def test_actual_load_steps_and_independent_readonly_contract(tmp_path):
    m=structured_mesh(np.array([[1,5],[1,1]],dtype=np.uint8))
    props={1:{'E_MPa':1000.,'nu':.3},2:{'E_MPa':10000.,'nu':.3}}
    text=source_input(m,props,[.001,.002,.003,.004,.005])
    assert text.splitlines().count('SOLVE')==5
    assert 'NLGEOM,OFF' in text and 'KEYOPT,1,3,3' in text and 'KEYOPT,1,1,0' in text
    assert text.count(',UX,0\n')==1 and 'D,LEFT,UX' not in text and 'D,RIGHT,UX' not in text
    ro=readonly_input(m,[.001,.002,.003,.004,.005],tmp_path)
    assert not any(line.startswith(('SOLVE','SAVE,')) for line in ro.splitlines())
    assert 'RF,FY' in ro and 'SENE' in ro and 'ETAB,SYY' in ro


def test_connectivity_corruption_is_rejected():
    m=structured_mesh(np.array([[1,5],[1,1]],dtype=np.uint8))
    m['quads'][1]=m['quads'][1][::-1]
    with pytest.raises(AssertionError):validate_mesh(m)
