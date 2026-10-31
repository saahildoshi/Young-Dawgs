"""Safety controls: positive pressure alone must not excuse a crossing."""
import numpy as np
import pytest
from metamaterial_eval.simulation.general_contact_results import explain_contact_pairs
from metamaterial_eval.simulation.general_contact_output import general_contact_vectors


@pytest.mark.parametrize('variant',['linked','unrelated_target','open','zero_pressure','missing_record','truncated'])
def test_crossing_requires_actual_engaged_native_target_identity(variant):
    row=np.array([11.,2.,1.,1.,1.,1e-8,1e-8,1.,12.,12.,1.,2.,3.,0.])
    if variant=='unrelated_target':row[8:10]=13
    if variant=='open':row[1]=1
    if variant=='zero_pressure':row[2:5]=0
    fields={} if variant=='missing_record' else {0:row}
    overlap={'suspicious_pair_count':2 if variant=='truncated' else 1,'examples':[{'edge_a':0,'edge_b':1}]}
    if variant=='linked':assert len(explain_contact_pairs(overlap,np.array([11,12]),fields))==1
    else:
        with pytest.raises(ValueError):explain_contact_pairs(overlap,np.array([11,12]),fields)


def test_empty_contact_fields_are_explicit_and_assembled_force_is_native():
    text='\n'.join(general_contact_vectors({'user_model_elements':14,'general_contact_component':'INTERNAL_GC'},'x',chunk_size=5))
    assert text.index('*CFOPEN,x_gc_fields,csv')<text.index('*IF,NGCF,GT,0,THEN')
    assert 'FSUM,,CONT' in text and '*GET,GFSX,FSUM,0,ITEM,FX' in text
    assert 'ETABLE,LFX,NMISC,21' in text and 'ETABLE,LFY,NMISC,22' in text
    assert 'SOLVE' not in text and 'SAVE,' not in text
