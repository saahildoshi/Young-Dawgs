# v0.6.3 actual MAPDL import

**ANSYS_IMPORT_PASS**, ANSYS 2024 R1 / Mechanical Enterprise Academic Research.
The streamed input is actual N/EN APDL with bounded 10k-record temporary
chunks, not a renamed pseudo-CDB. The real solver generated a native blocked
archive with CDWRITE and a reusable specimen database.

Actual specimen nodes: 2766505; actual PLANE183 TRI6:
1261670. Every node ID/coordinate and all six element
connectivity IDs were compared. Maximum coordinate difference:
5.04485342e-13 mm (CDB printed precision; tolerance 1e-11 mm).
Every material/type/real attribute is 1 and all boundary/component memberships
match. Actual ETLIST/RLIST/MPLIST verify six-node triangles, plane stress
KEYOPT(1)=1 / KEYOPT(3)=3, initial thickness 1 mm, E=1000 MPa and nu=.3.

The imported coordinates lie in global XY, z=0, with the 10.24 mm envelope.
Connectivity-derived topology and full geometric validation confirm one solid
component, 412 pores, preserved material area, no filled voids or lost boundary,
positive whole-element mapping and registered feature resolution. Count matching
alone was not used as topology evidence. No compression occurred in this phase.

Source archive SHA256: 6072a7fbcfa71eb2975ec907c6256836fc27f04f0803af20e2a0243c25a1acfc.
Database SHA256: b2f3bc964daddff43e6ac2dabd1e3eb430bacee604a1ed1ebeb53b9200558c36.
The full raw CDB/database remain under the configured artifact root; compact
inventories, receipts and explicitly labelled log excerpts are tracked.
