"""Reject missing active contact data and curved edges disguised as separated."""
from types import SimpleNamespace
import numpy as np
import pytest
from metamaterial_eval.simulation.progressive_contact import quadratic_range,validate_inventory,certify_farfield_separation
from metamaterial_eval.simulation.progressive_compression import multi_export_input


def test_quadratic_extrema_include_interior_overshoot():
    lo,hi=quadratic_range(np.array([[1.,1.,-2.],[0,1,.5]]))
    assert lo[0]==pytest.approx(-2) and hi[0]==pytest.approx(1)
    assert lo[1]==0 and hi[1]==1


@pytest.mark.parametrize('variant',['valid','missing_status','missing_active','fabricated_farfield','wrong_id','wrong_status'])
def test_native_status_and_available_record_inventory(variant):
    model={'contact_elements':{'bottom':1,'top':1}}
    status=np.array([[1.,5.,0.],[2.,8.,2.]])
    values=np.array([[2.,8.,2.,1.,1.,1e-7,1e-7,1.]])
    if variant=='missing_status':status=status[:1]
    if variant=='missing_active':values=values[:0]
    if variant=='fabricated_farfield':values=np.concatenate([[[1,5,0,0,0,0,0,0]],values])
    if variant=='wrong_id':status[1,1]=9
    if variant=='wrong_status':status[0,2]=-1
    if variant=='valid':assert validate_inventory(status,values,model,2)=={'bottom':0,'top':1}
    else:
        with pytest.raises(ValueError):validate_inventory(status,values,model,2)


@pytest.mark.parametrize('variant',['separated','touching','hidden_curve_penetration','wrong_top_sign','outside_finite_target'])
def test_farfield_requires_whole_quadratic_edge_separation(variant):
    nodes=np.array([[0.,0.],[1,0],[1,1],[0,1],[.5,0],[1,.5],[.5,1],[0,.5]])
    mesh=SimpleNamespace(nodes=nodes,boundary=np.array([[0,1,4],[2,3,6]]),boundary_groups=np.array(['bottom','top']))
    xy=nodes.copy();xy[[0,1,4],1]=.001;xy[[2,3,6],1]=.898
    if variant=='touching':xy[[0,1,4],1]=0
    if variant=='hidden_curve_penetration':xy[4,1]=-.002
    if variant=='wrong_top_sign':xy[[2,3,6],1]=.901
    if variant=='outside_finite_target':xy[[2,3,6],0]+=2;xy[[2,3,6],1]=.901
    status=np.array([[1.,5.,0.],[2.,8.,0.]])
    model={'config':{'width':1,'height':1}}
    if variant in ['separated','outside_finite_target']:
        r=certify_farfield_separation(mesh,xy,model,status,-.1);assert all(x['minimum_certified_axis_separation_mm']>1e-8 for x in r)
    else:
        with pytest.raises(ValueError):certify_farfield_separation(mesh,xy,model,status,-.1)


def test_native_export_skips_absent_farfield_fields_and_checks_actual_state(tmp_path):
    model={'specimen_nodes':8,'controls':{'top':14,'bottom':11},'config':{'height':1}}
    text=multi_export_input(tmp_path/'m.db',tmp_path/'r',model,[{'load_step':4,'substep':7,'time':.01}],farfield=True)
    assert 'ETABLE,CNSTAT,NMISC,19' in text and '*CFOPEN,stage001_contact_status,csv' in text
    assert '*GET,STV,ELEM,EID,ETAB,CNSTAT\n*IF,STV,GT,0,THEN' in text
    assert '*IF,LSV,NE,4,THEN' in text and '*IF,SSV,NE,7,THEN' in text
    assert '*IF,ABS(UYTOP+(1)*TNOW),GT,1e-8,THEN' in text
    assert '\nSOLVE\n' not in text and '\nSAVE,' not in text
