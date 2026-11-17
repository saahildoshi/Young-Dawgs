"""Analytical digital mesh contracts, distinct from licensed native evidence."""
import numpy as np
import pytest
from metamaterial_eval.simulation.three_phase_elastic import solid_mesh,validate_solid_mesh,extract_solid,source_solid

def test_void_pixels_have_no_elements_or_unused_nodes():
    a=np.zeros((8,8),np.uint8);a[2:6,2:6]=2;a[:,0]=1
    m=solid_mesh(a);r=validate_solid_mesh(m)
    assert len(m['quads'])==48 and r['free_void_edges']==16
    assert len(np.unique(m['quads']))==len(m['nodes'])
    assert r['material_elements']=={'1':40,'2':8}
    assert r['solid_area_mm2']==pytest.approx(.75)

def test_refinement_preserves_all_three_phase_geometry():
    a=np.zeros((8,8),np.uint8);a[2:6,2:6]=2;a[:,:2]=1
    x=validate_solid_mesh(solid_mesh(a,1));y=validate_solid_mesh(solid_mesh(a,2))
    assert y['elements']==4*x['elements']
    assert x['material_envelope_area_fractions']==y['material_envelope_area_fractions']
    assert x['source_phase_counts']==y['source_phase_counts']

def test_void_separated_load_bearing_strips_get_only_one_lateral_pin_each():
    a=np.zeros((8,8),np.uint8);a[:,2:6]=2;m=solid_mesh(a)
    assert m['solid_components']==2 and len(m['pins'])==2
    assert len(m['top'])==len(m['bottom'])==6
    assert set(m['pins'])<=set(m['bottom'])

def test_source_orientation_and_no_material_in_void():
    a=np.zeros((8,8),np.uint8);a[:2]=1;a[3:5,3:5]=2;m=solid_mesh(a)
    centers=m['nodes'][m['quads']].mean(axis=1)
    assert np.all(m['materials'][centers[:,1]>.75]==2)
    assert not np.any(np.all((centers>.375)&(centers<.625),axis=1))

def test_corner_only_connection_is_a_hold_not_a_repair():
    a=np.full((4,4),2,np.uint8);a[0,0]=0;a[1,1]=0
    with pytest.raises(ValueError,match='corners'):solid_mesh(a)

def test_floating_island_is_not_silently_removed_or_grounded():
    a=np.full((8,8),2,np.uint8);a[2:6,2:6]=1;before=a.copy()
    with pytest.raises(ValueError,match='both prescribed'):solid_mesh(a)
    assert np.array_equal(a,before)

def test_extraction_iterates_actual_boundary_components_not_dense_id_ranges():
    a=np.zeros((8,8),np.uint8);a[:,2:6]=2;m=solid_mesh(a)
    commands=extract_solid(m,[.001,.002,.003,.004,.005])
    assert 'CMSEL,S,TOP' in commands and 'INODE=NDNEXT(INODE)' in commands
    assert not any(line.startswith('*DO,INODE,') for line in commands)
    for pin in m['pins']:assert f'*GET,FXONE,NODE,{pin+1},RF,FX' in commands

def test_no_restraint_on_void_boundaries_and_native_linear_protocol():
    a=np.zeros((8,8),np.uint8);a[2:6,2:6]=2;m=solid_mesh(a)
    text=source_solid(m,{1:{'E_MPa':1000,'nu':.3},2:{'E_MPa':10000,'nu':.3}},[.001,.002,.003,.004,.005])
    assert text.count('\nSOLVE\n')==5 and 'NLGEOM,OFF' in text
    assert 'KEYOPT,1,3,3' in text
    assert text.count('D,BOTTOM,UY,0')==1
    assert 'D,ALL' not in text and 'EKILL' not in text
