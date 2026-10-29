# v0.6.3 audit and prospective execution plan

Started clean on master at 9af3d404c94293c9fa705552bb41497358ddd63e.
AGENTS.md commit/preservation policy applies. v0.6.1 qualification and Windows
handoff, v0.6.2 validation/execution/self-contact handoff, v0.5 C.1/D1 scientific
HOLD reports and actual source/mesh/solver/extraction implementations were read.

## Initial audit

1. The qualified mesh was generated on Linux x86_64 in v0.6.1 full_run_001.
2. Its expected archive is mesh_candidates/full_run_001/fine_new/generated/mesh.npz
   beneath experiments/pipeline_v0.6.1.
3. No recoverable original hostname, remote endpoint or shared artifact root is
   recorded. Do not invent one or scan unrelated volumes.
4. Source raster/PNG/manifest/WKB/exact boundary serialization, selected mesh
   manifest, quality/feature/protocol records and meshing code remain available.
5. Frozen fine_new: boundary h=.0033333333333333335 mm, bulk h=.04 mm,
   Gmsh algorithm 6, one thread, curve-length bucketed distance sampling,
   boundary point sizes, 10 Relocate2D iterations on linear triangles, then
   straight quadratic midsides. Actual current Gmsh is 4.15.0.
6. Semantic SHA256 concatenates contiguous nodes, triangles, boundary arrays
   and boundary_groups cast to S8, using their original binary array dtypes.
   Raw NPZ bytes are a separate hash; ZIP serialization is not mesh identity.
7. Recovery/reproduction requires the authenticated source bundle, unchanged
   geometry adapter/generator, frozen protocol/configuration and Gmsh runtime.
8. Authoritative Design9/seed1/native1024 WKB SHA256 is
   4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1.
   Source authentication again confirms 412 holes and 50.0104 mm² solid area.
9. Established transfer is explicit APDL N/EN with PLANE183 TRI6 and components;
   genuine blocked CDB must be produced by ANSYS, not a renamed text deck.
10. Fresh audit observes about 35.6 GB available of 68.4 GB physical RAM,
    20 logical processors and 1.46 TB free disk. Recheck before every large job.
11. v0.6.2 absolute FTOLN=1e-7 mm / FKN=1 produced computed stiffness 2e10
    and coefficient-ratio warning. Compare two looser justified tolerances
    against authenticated baseline, holding geometry/material/loading fixed.
12. A successful first pilot requires a geometrically accepted authenticated
    mesh, real exhaustive/specified import validation, resource gate, frozen
    contact/pilot protocol, actual converged smallest strain, both platen
    force transmission, normalized equilibrium and valid numerical fields.

## Sequence and decisions

Bounded search of current and adjacent Young Dawgs project roots precedes
reproduction. Search scope/errors/candidates are recorded. If no historical
archive is available, reproduce exactly the registered fine_new procedure into
a new local artifact root. This regeneration is explicitly authorized by the
v0.6.3 request; no canonical geometry or frozen criteria change is allowed.
Classify exact semantic identity, newly qualified regenerated mesh, or HOLD.

Add a manifest-based artifact registry with YD_ARTIFACT_ROOT override and a
per-user local cache default. Track source/config/version/byte/semantic hashes,
relative artifact paths and reproduction commands. Large mesh/solver files
remain out of Git; no external upload or cloud service is required.

Reuse direct MAPDL. Stream mesh records and components; suppress command echo.
Perform import only and export all specimen nodes/elements/attributes and all
boundary components for exhaustive comparisons. Reconstruct imported topology
from connectivity; matched counts alone are insufficient. Save a real database
for subsequent model checks/pilot without repeated multi-million-line parsing.

Use a bounded linear assembly-only resource diagnostic if supported. WRFULL is
documented only for linear analyses: do not apply it to nonlinear contact or
call it a mechanical result. Prefer sparse direct for contact; inspect actual
solver memory output. Register an OS reserve and stop before an unsafe job.
No unrestricted factorization, automatic large retries or parallel huge jobs.

After sensitivity/import/resource gates, freeze one PLATEN_CONTACT_ONLY pilot
at 0.01%, then conditionally 0.05% and 0.1%, one stage at a time. Material,
plane stress, initial 1 mm thickness and 10.24 mm envelope remain provisional.
Save only checkpoint fields; stop on resource, contact, convergence or distortion
failure. Internal self-contact and mechanical mesh convergence remain separate.

Commit each completed validated milestone. Run active/archive/real integration
checks separately. Preserve all failed attempts and historical scientific HOLDs.
Stop before batch mechanical comparisons, autonomous optimization or 3D work.
