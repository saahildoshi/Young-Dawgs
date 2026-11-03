"""Focused regression checks for the v0.6.8 native-face identity correction."""
from io import StringIO
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.v068_pair_common import face_owners,native_skin_ids_by_face,overlay


def specimen():
    # One TRI6 with oriented corner/midside boundary faces.
    return SimpleNamespace(
        triangles=np.array([[0,1,2,3,4,5]],dtype=np.int64),
        boundary=np.array([[0,1,3],[1,2,4],[2,0,5]],dtype=np.int64),
    )


def test_native_skin_mapping_uses_face_identity_not_element_order():
    mesh=specimen()
    # Deliberately shuffled native EID order reproduces the real setup hazard.
    native=np.array([[901,3,1,6,4,4],[502,1,2,4,4,4],[803,2,3,5,4,4]],dtype=float)
    assert native_skin_ids_by_face(mesh,native).tolist()==[502,803,901]
    assert face_owners(mesh).tolist()==[1,1,1]


@pytest.mark.parametrize('native',[
    np.array([[502,1,2,4],[803,2,3,5]],dtype=float),
    np.array([[502,1,2,4],[803,1,2,4],[901,3,1,6]],dtype=float),
    np.array([[502,1,2,4],[803,2,3,5],[901,6,1,3]],dtype=float),
])
def test_native_skin_mapping_rejects_missing_or_duplicate_faces(native):
    with pytest.raises(ValueError):native_skin_ids_by_face(specimen(),native)


def test_overlay_limits_esurf_to_original_owner_and_three_face_nodes():
    mesh=specimen();out=StringIO()
    overlay(out,mesh,face_owners(mesh),[1],etype=6,real=6)
    deck=out.getvalue()
    assert deck.count('ESURF\n')==1
    assert 'ESEL,S,ELEM,,1\n' in deck
    assert 'NSEL,A,NODE,,2\nNSEL,A,NODE,,3\nNSEL,A,NODE,,5\n' in deck
    assert 'TYPE,6\nREAL,6\nMAT,1\nESURF\n' in deck
    assert 'TSHAP' not in deck
