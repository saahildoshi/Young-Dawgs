"""Constitutive reference checks independent of native coupon acceptance."""
import numpy as np
import pytest
from scripts.v0610_material import E,NU,MU,K,D,analytical


def test_neo_parameters_reproduce_registered_small_strain_moduli():
    assert 9*K*MU/(3*K+MU)==pytest.approx(E)
    assert (3*K-2*MU)/(2*(3*K+MU))==pytest.approx(NU)
    assert 2/D==pytest.approx(K)


def test_reference_has_zero_stress_at_identity():
    q=analytical(0)
    assert q['J']==pytest.approx(1) and q['nominal_y_MPa']==pytest.approx(0,abs=1e-10)


def test_reference_small_strain_nominal_tangent_is_E():
    eps=1e-6
    assert -analytical(eps)['nominal_y_MPa']/eps==pytest.approx(E,rel=1e-4)


@pytest.mark.parametrize('strain',[.01,.1,.2,.3,.4])
def test_reference_has_positive_volume_and_lateral_expansion(strain):
    q=analytical(strain)
    assert 0<q['J']<1 and q['lateral_stretch']>1
    assert q['nominal_y_MPa']<0 and q['cauchy_y_MPa']<0
    assert np.isfinite(list(q.values())).all()
