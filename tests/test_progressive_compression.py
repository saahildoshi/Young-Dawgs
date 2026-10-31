"""Synthetic safety controls; actual native restart is tested separately."""
import re
import pytest
from metamaterial_eval.simulation.progressive_compression import validate_targets,load_commands,result_sets,continuation_input,multi_export_input


@pytest.mark.parametrize('targets,start', [([.01,.3,.4],0),([.0001,.001],.00005)])
def test_valid_cumulative_targets(targets,start):validate_targets(targets,start)


@pytest.mark.parametrize('targets,start',[([],0),([.1,.1],0),([.3,.2],0),([.41],0),([float('nan')],0),([.01],.01)])
def test_invalid_or_duplicate_targets(targets,start):
    with pytest.raises(ValueError):validate_targets(targets,start)


def test_total_displacement_and_adaptive_bounds():
    lines=load_commands(.1,.05,99,10.24)
    assert 'D,99,UY,-1.024' in lines and 'TIME,0.10000000000000001' in lines
    assert 'NEQIT,24' in lines and 'OUTRES,EPEL,ALL' in lines
    assert 'RESCONTROL,DEFINE,ALL,1,-1,,3' in lines
    n=next(x for x in lines if x.startswith('NSUBST')).split(',')
    assert int(n[2])>=int(n[1])>=int(n[3])>=1 and n[4]=='OFF'
    assert (.1-.05)/int(n[2])>=1e-6


def test_result_inventory_discards_debug_and_rejects_stale_order():
    text=' 1 .00005 1 1 7\n 2 .0001 2 2 11\n 3 .00011 2 999999 30\n'
    assert len(result_sets(text))==2
    with pytest.raises(ValueError):result_sets('1 .1 1 1 2\n2 .1 2 1 3\n')
    with pytest.raises(ValueError):result_sets('No Data Sets')


def test_native_restart_and_multi_export_commands(tmp_path):
    model={'specimen_nodes':617,'controls':{'top':623,'bottom':620},'config':{'height':10.24}}
    text=continuation_input(1,1,[.0001],.00005,model)
    assert 'ANTYPE,STATIC,REST,1,1,CONTINUE' in text and 'RESUME,compression,rdb' in text
    assert text.count('/SOLU')==1 and text.index('FINISH')>text.index('\nSOLVE\n')
    states=[{'load_step':1,'substep':1,'time':.00005},{'load_step':2,'substep':4,'time':.0001}]
    export=multi_export_input(tmp_path/'checkpoint.db',tmp_path/'compression',model,states,chunk_size=128)
    assert 'SET,2,4' in export and 'stage002_stress' in export
    assert export.count("FILE,'")==3
    assert not re.search(r'^\s*(SOLVE|SAVE\s*,)',export,re.M)
    with pytest.raises(ValueError):multi_export_input(tmp_path/'model.db',tmp_path/'x',model,[states[0],states[0]])
