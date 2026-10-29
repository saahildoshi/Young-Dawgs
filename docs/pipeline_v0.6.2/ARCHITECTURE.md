# v0.6.2 Windows ANSYS qualification decision

Starting branch: master. Starting HEAD: 4e261f3. Initial worktree: clean.
This is an additive study; historical runs and scientific HOLD decisions remain.

## Observed environment and ordered route evaluation

AWP_ROOT241 resolves to C:/Program Files/ANSYS Inc/v241. Workbench RunWB2.exe
and Mechanical AnsysWBU.exe report product version 24.1. MAPDL ANSYS241.exe
exists. These observations establish installed files, not license checkout.
The machine reports 68,403,589,120 bytes RAM and 20 logical processors, with
approximately 1.46 TB free on C: at the initial audit. Python .venv is 3.14.6.
Missing pytest, Shapely, Gmsh and psutil are installed into that existing venv.
PyMechanical and PyMAPDL are optional and will not be required for batch MAPDL.

Evaluate Workbench first with a bounded journal: create a Static Structural
system, launch Mechanical without an interactive window, and execute a small
embedded scripting query. Record failures. The existing mesh transfer emits
APDL N/EN commands, not a blocked CDB archive and not a Workbench import.
Use direct MAPDL for the production benchmark if available: it preserves genuine
PLANE183 TRI6 and explicit CONTA172/TARGE169 pairs with inspectable solver
listings. Do not create a competing production integration or convert to 3D.
Workbench External Model compatibility remains unverified unless actually tested.

## Existing implementation audit

Reuse CompressionConfig, Mesh, Gmsh rectangle meshing, independent mesh
validation, platen_plan, APDL generation, raw field export, reaction metrics,
hash receipts, quarantine and qualification gates. Discovery currently omits
AWP_ROOT241. The draft solver input and extraction require actual execution
and release-specific verification; local transfer lint is not solver acceptance.
Add bounded Windows process supervision, sanitized environment records and
actual solver evidence rather than extending geometry development.

Official v241 help links were attempted but inaccessible through web browsing;
the local help installation contains a help-not-installed placeholder. Accessible
v242 official PLANE183/CONTA172 pages are provisional comparison references,
not proof of v241 compatibility. Record the installed solver's actual element
listings, warnings and calculated response. Do not claim an unavailable v241
documentation review was completed.

## Large mesh prerequisite

The recorded selected fine mesh has 2,766,505 nodes, 1,261,670 TRI6 and 412
pores. Its expected generated/mesh.npz is absent in this checkout at audit.
Authenticate its manifest and search for the exact saved mesh before import.
Do not regenerate or substitute a rejected coarse mesh. Missing authenticated
mesh bytes block large-model import and pilot independently of rectangle success.

## Stop conditions

Direct failure blocks contact qualification. Contact failure blocks pilot.
Every failed attempt retains its original input and logs. No unrestricted large
solve, geometry changes, historical edits, 3D, batch studies or LLM optimization.
Commit validated coherent changes without pushing.
