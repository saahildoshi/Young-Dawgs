"""v0.5A.1 opt-in qualification; canonical exact conversion is unchanged."""
from .contacts import classify_contacts, inspect_boundary, inspect_patches
from .candidates import CandidateSettings, qualify_manifold_geometry

__all__ = ['classify_contacts', 'inspect_boundary', 'inspect_patches',
           'CandidateSettings', 'qualify_manifold_geometry']
