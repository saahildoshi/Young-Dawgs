"""APDL generator safety and chunk boundaries; actual support tested separately."""
import re
import pytest
from metamaterial_eval.simulation.native_output import SELECTIVE_OUTPUT,chunked_vectors,read_only_input


def test_selective_output_retains_explicit_required_categories():
    assert SELECTIVE_OUTPUT[:2]==['OUTRES,ERASE','OUTRES,ALL,NONE']
    assert {s.split(',')[1] for s in SELECTIVE_OUTPUT[2:]}=={'NSOL','RSOL','STRS','EPEL','CONT','MISC'}


@pytest.mark.parametrize('size,chunk',[(1,1),(617,128),(2766505,250000)])
def test_chunked_export_limits_arrays_and_last_block(size,chunk):
    text='\n'.join(chunked_vectors(size,'stage001',chunk))
    arrays=re.findall(r'\*DIM,\w+,ARRAY,(\d+)',text)
    assert arrays and max(map(int,arrays))==min(size,chunk)
    assert f'NLEN=MIN({min(size,chunk)},{size}-IBEG+1)' in text
    assert '*VMASK,MASKV(1)' in text


def test_read_only_export_cannot_solve_or_save(tmp_path):
    model={'specimen_nodes':617,'config':{'height':10.24},'controls':{'top':623,'bottom':620}}
    text=read_only_input(tmp_path/'checkpoint.db',tmp_path/'compression',model,.00005,chunk_size=128)
    assert not re.search(r'^\s*(SOLVE|SAVE\s*,)',text,re.M)
    assert 'SET,LIST' in text and 'SET,1,1' in text and 'RESUME,' in text
    assert 'stage001_contact' in text and 'RF,FY' in text
