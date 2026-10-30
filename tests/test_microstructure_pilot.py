"""Input/gating unit controls; actual full-model evidence is tested separately."""
from pathlib import Path
import pytest
from metamaterial_eval.simulation.microstructure_pilot import database_resume,vector_fields,stage_block,prepare_pilot


def test_resume_keeps_actual_database_extension(tmp_path):
    assert ',rdb\n' in database_resume(tmp_path/'compression.rdb')
    assert ',db\n' in database_resume(tmp_path/'specimen.db')


def test_vector_export_masks_each_supported_stress_field():
    lines=vector_fields(6,'test')
    for line in ['*VGET,SYV(1),NODE,1,S,Y','*VGET,EYV(1),NODE,1,EPEL,Y']:
        assert lines[lines.index(line)-1]=='*VMASK,MASKV(1)'
    assert "('node,ux_mm,uy_mm')" in lines
    assert '*VWRITE,IDS(1),UXV(1),UYV(1)' in lines


def test_next_stage_block_requires_real_force_and_contact_gates():
    model={'controls':{'top':9,'bottom':8},'specimen_nodes':6,'config':{'height':10.24}}
    text='\n'.join(stage_block(1,.0001,model,{}))
    assert 'D,9,UY,-0.001024' in text and '*GET,RFTOP,NODE,9,RF,FY' in text
    assert 'CBAL=ABS(FYTOTAL+EXPECT)' in text
    assert 'PILOT_STAGE_GATE_FAILED_NO_ADVANCEMENT' in text
    assert 'MAXPEN,GT,1e-5' in text and 'RFTOP,GE,-1e-8' in text
    assert "5(',',E16.8)" in text  # below MAPDL 128-column line limit
    assert 'ANTYPE,STATIC,REST,,,CONTINUE' in '\n'.join(stage_block(2,.0005,model,{}))


def test_missing_actual_setup_blocks_pilot(tmp_path):
    with pytest.raises(FileNotFoundError):prepare_pilot(tmp_path/'pilot',tmp_path/'absent',tmp_path/'protocol.json')


def test_performance_zero_pivot_counts_do_not_trigger_false_failure():
    from metamaterial_eval.simulation.solver_execution import has_negative_pivots
    assert not has_negative_pivots('negative pivot monitoring activated\nnumber of negative pivots encountered = 0')
    assert has_negative_pivots('# of negative pivots = 1')
