"""Read-only licensed-artifact checks; no new native processes."""
from pathlib import Path
import numpy as np
import pytest
from scripts.v070_protocol import read,sha
from scripts.v074_experiment import RUN
from scripts.v074_f1 import model

F1=sorted((RUN/'f1/mechanical_response').glob('*.json'))

@pytest.mark.parametrize('path',F1,ids=lambda p:p.stem)
def test_native_F1_three_phase_mesh_curves_and_independent_fields(path):
    r=read(path);assert r['accepted'] and all(r['checks'].values())
    source=Path(r['source_directory']);post=Path(r['independent_readback_directory'])
    assert read(source/'EXECUTION.json')['solver_release']=='2024 R1'
    assert sha(source/'elastic.rst')==r['native_result_sha256']
    assert sha(source/'model.db')==r['native_database_sha256']
    assert sha(post/'fields.csv')==r['native_fields_sha256']
    assert all(read(post/'READBACK.json')['identical_exports_to_solve'].values())
    m,props,expected=model(r['specimen_id'],r['mesh_level'])
    f=np.loadtxt(post/'fields.csv',delimiter=',');q=np.loadtxt(post/'connectivity.csv',delimiter=',')
    assert np.array_equal(q[:,1:],m['quads']+1) and np.array_equal(f[:,1],m['materials'])
    assert len(f)==int((m['source']!=2).sum())*r['mesh_level']**2
    assert r['actual_engineering_strains']==pytest.approx([.001,.002,.003,.004,.005],abs=1e-9)
    c=np.asarray(r['signed_native_curve'])
    assert np.polyfit(-c[:,2],-c[:,5],1)[0]==pytest.approx(r['effective_modulus_MPa'],rel=1e-10)
    assert c[:,8]==pytest.approx(.5*np.abs(c[:,5]*c[:,2]),rel=.001)
    assert np.max(np.abs(c[:,5]+c[:,6])/np.abs(c[:,5]))<.001
    if expected:assert r['effective_modulus_MPa']==pytest.approx(expected,rel=.005)

def test_F1_selected_refinements_preserve_void_and_material_area():
    for name in ['F1_M2_REFERENCE','F1_M3_B02_SEED0']:
        a=read(RUN/'f1/mechanical_response'/f'{name}_H1_attempt001.json')
        b=read(RUN/'f1/mechanical_response'/f'{name}_H2_attempt001.json')
        assert b['mesh_proof']['elements']==4*a['mesh_proof']['elements']
        assert a['mesh_proof']['source_phase_counts']==b['mesh_proof']['source_phase_counts']
        assert a['mesh_proof']['material_envelope_area_fractions']==b['mesh_proof']['material_envelope_area_fractions']
