# v0.6.3 microstructure pilot

**MESH_IDENTITY_AND_IMPORT_PASS — MICROSTRUCTURE_NUMERICAL_HOLD — RESEARCH_HOLD**. Actual selected execution status: RESOURCE_LIMIT.
Two real full-model nonlinear contact attempts executed. The original AL run
was stopped for documented residual stagnation with no converged substep. The
corrected run is separately frozen and retains its own complete native evidence.

Corrected run: TIMEOUT after 1200.102 s, peak sampled
process-tree RSS 18193420288 bytes. Solver-reported converged substeps:
[]. The first 0.01% checkpoint was
attempted but did not converge. Later 0.05% / 0.1% stages: NOT EXECUTED because
the first stage failed. The wall-time cap is BLOCKED_RESOURCE; this is not a
finding of inadequate RAM or measured poor physical material performance.

The specimen is Design9/seed1/native1024; plane stress PLANE183 TRI6; provisional
E1000 MPa / nu .3 / initial thickness 1 mm / 10.24×10.24 mm envelope. Material
is homogeneous linear elastic; NLGEOM/contact introduce structural nonlinearity.
No plasticity, fracture or internal self-contact was configured.

Upper/lower rigid targets are frictionless and permit separation. Actual initial
checks found both pairs closed, initial penetration 0 / 3.55e-15 mm, no specimen
UY constraints. This initial check is not a completed zero-load solution.
The registered requested checkpoints are 0.01%, 0.05% and 0.1%; only actual
converged checkpoints appear below. The setup's generic CompressionConfig
loading defaults are not the executed pilot schedule: the frozen protocol and
actual TIME/D commands are authoritative. No 2% microstructure stage was run.

| Stage | Achieved engineering strain | Upper native RF [N] | Lower native RF [N] | Nominal compression stress [MPa] |
|---|---:|---:|---:|---:|
| — | No converged checkpoint | UNAVAILABLE | UNAVAILABLE | UNAVAILABLE |

Native upper RF is negative and lower positive. Contact CNFY is the opposing
internal resisting-force convention. Nominal stress uses the full initial
envelope W×t; engineering strain uses actual travel/H. Pseudo-time is a load
parameter, not seconds. No rectangle analytical force is assigned to this mesh.

Maximum validated stored-endpoint penetration: UNAVAILABLE — no validated converged checkpoint mm.
Fitted effective modulus: UNAVAILABLE — no validated converged checkpoint MPa; base modulus 1000 MPa.
At least two valid small-strain points are required for the registered
through-origin fit; otherwise fitted modulus is unavailable and any secant
estimate is explicitly separate. Internal self-contact, mechanical convergence
and paper readiness remain unqualified even if a checkpoint is valid.

Full numerical fields exist only where declared in mechanical_summary.json:
all-node UX/UY, corner-node averaged SYY/equivalent stress/elastic EYY/EXX,
actual contact endpoints and deformation mapping checks. No copied midside
stress or assumed deformation field. Unavailable stages/fields are not plotted.
