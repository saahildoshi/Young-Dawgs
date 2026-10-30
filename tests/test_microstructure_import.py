"""Synthetic archive/parser controls; actual MAPDL checks run separately."""
import io
import numpy as np
import pytest
from metamaterial_eval.simulation.microstructure_import import component,read_cdb,prepare_import
from metamaterial_eval.simulation.mesh_generation import Mesh


def test_component_writer_keeps_every_identifier():
    stream=io.StringIO();component(stream,'PORE_FACE',[9,1,5,5])
    lines=stream.getvalue().splitlines()
    assert lines[0]=='CMBLOCK,PORE_FACE,NODE,3'
    assert [int(lines[2][i:i+10]) for i in range(0,len(lines[2]),10)]==[1,5,9]
    with pytest.raises(ValueError):component(stream,'EMPTY',[])


def make_cdb(path,*,first_node=1,nodal_count=6):
    xyz=[[0,0],[1,0],[0,1],[.5,0],[.5,.5],[0,.5]]
    lines=['NBLOCK,6,SOLID,6,6','(3i9,6e21.13e3)']
    for i,(x,y) in enumerate(xyz[:nodal_count],first_node):
        lines.append(f'{i:9d}{0:9d}{0:9d}{x:21.13E}{y:21.13E}{0:21.13E}')
    lines+=['N,UNBL,LOC,-1,','EBLOCK,19,SOLID,1,1','(19i10)',
            ''.join(f'{v:10d}' for v in [1,1,1,1,0,0,0,0,6,0,1,1,2,3,4,5,6]),
            '        -1','CMBLOCK,SPECIMEN,ELEM,1','(8i10)',f'{1:10d}',
            'CMBLOCK,BOUNDARY,NODE,2','(8i10)',f'{1:10d}{-6:10d}']
    path.write_text('\n'.join(lines)+'\n')


def test_complete_fixed_width_inventory_and_compressed_components(tmp_path):
    p=tmp_path/'unit.cdb';make_cdb(p)
    nodes,tri,attrs,groups=read_cdb(p,6,1)
    assert nodes.shape==(6,2) and np.all(attrs==1)
    assert tri.tolist()==[[0,1,2,3,4,5]]
    assert groups['BOUNDARY']['ids'].tolist()==[1,2,3,4,5,6]


@pytest.mark.parametrize('damage',['partial','shifted','wrong_format'])
def test_partial_or_changed_actual_inventory_rejected(tmp_path,damage):
    p=tmp_path/'unit.cdb';make_cdb(p,first_node=2 if damage=='shifted' else 1,nodal_count=5 if damage=='partial' else 6)
    if damage=='wrong_format':p.write_text(p.read_text().replace('(19i10)','(19i8)'))
    with pytest.raises(ValueError):read_cdb(p,6,1)


def test_streamed_input_preserves_quadratic_nodes_and_no_solve(tmp_path):
    m=Mesh(np.array([[0.,0.],[1,0],[0,1],[.5,0],[.5,.5],[0,.5]]),
        np.array([[0,1,2,3,4,5]]),np.array([[0,1,3],[1,2,4],[2,0,5]]),np.array(['bottom','external','external']))
    p=tmp_path/'input';prepare_import(m,p)
    text=(p/'import.inp').read_text()
    assert 'EN,1,1,2,3,4,5,6' in text and 'KEYOPT,1,3,3' in text
    assert '\nSOLVE\n' not in text and 'CDWRITE,DB,imported,cdb' in text
    with pytest.raises(FileExistsError):prepare_import(m,p)
