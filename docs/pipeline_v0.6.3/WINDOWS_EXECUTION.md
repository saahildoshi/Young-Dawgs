# v0.6.3 Windows reproduction and evidence inspection

Use the tested v0.6.2 Windows dependency set (requirements-v0.6.2-windows.txt),
including Python3.14, Gmsh4.15.0 and Shapely2.2.0. Keep the frozen geometry,
generators, evaluators and previous experiment trees unchanged.

## Locate and authenticate the durable mesh

The actual creation root is recorded in
experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json.
Set YD_ARTIFACT_ROOT to that root or to a destination containing the complete
artifact-relative folder. Windows packaged-app LOCALAPPDATA may differ from a
normal terminal's LOCALAPPDATA; verification can fall back to a recorded existing
root, but explicit selection is clearest for solver workflows.

```powershell
python -m metamaterial_eval.simulation.mesh_artifacts discover
python -m metamaterial_eval.simulation.mesh_artifacts verify --manifest experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json
```

The mesh identity is the registered semantic SHA256. The new NPZ has a separately
recorded byte hash and CRC verification. Copy both manifest and mesh folder for
transfer, verify hydration/sync if using OneDrive, and verify again on receipt.
No global OneDrive settings or automatic upload is required. A local cache is
not an external backup.

If bytes are genuinely lost, use an empty chosen artifact root and a new
evidence path to reproduce the registered fine_new procedure:

```powershell
python -m metamaterial_eval.simulation.mesh_artifacts reproduce --root CHOSEN_EMPTY_ARTIFACT_ROOT --output NEW_EVIDENCE_PATH
```

Never overwrite the v063_regen_001 artifact. The source is authenticated first;
the historical protocol is compared with CRLF→LF normalization only. A different
semantic hash requires independent qualification and its own identity, not a
renaming as historical. No criteria or geometry changes are permitted silently.

## Actual import

microstructure_import streams bounded N/EN chunks and component records, runs
real MAPDL, saves a database and exports a genuine CDWRITE CDB. Its limited
fixed-width reader exhaustively checks actual coordinates, six-node connectivity,
attributes and components; full geometry/topology/feature validation is repeated
on the imported data. It refuses existing job/evidence directories. The saved
run's raw import is under solver/v063/import_001 beneath the artifact root.

```powershell
python -m metamaterial_eval.simulation.microstructure_import --manifest experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json --output NEW_IMPORT_EVIDENCE_PATH
```

The current fixed import_001 job already exists: do not rerun blindly. A new
machine/root or separately versioned job is needed. Large CDB/database files
remain outside Git; tracked receipts record their byte hashes and relative paths.

## Resource and contact checks

The saved linear assembly-only resource diagnostic is solver/v063/assembly_001.
WRFULL was used only in that linear no-contact diagnostic; it is not a nonlinear
solve or factorization acceptance. Actual subsequent sparse factorizations supply
additional memory evidence. Bounds are one SMP core, 20 GiB sampled RSS,
12 GiB available system RAM reserve, 20 GiB disk reserve and 1200 s per pilot.
The -m 4096 value is an initial memory request, not the hard cap.

The first AL contact policy was selected prospectively from two rectangle
sensitivity cases. A full-model residual plateau triggered a documented diagnostic
stop. A pure-penalty FKN1 test failed the unchanged v063 penetration gate, then
the registered FKN100 test passed and repeated. Its fixed-stiffness recommendation
warnings remain. Contact setup_001 and setup_002 and every failed attempt remain.
No source geometry, mesh, material, force/penetration acceptance or stabilization
was altered to obtain a nominal pass.

## Frozen pilot and result extraction

Actual run directories are solver/v063/pilot_001 and pilot_002. Protocols
PILOT_PROTOCOL_001.json and PILOT_PROTOCOL_002.json were committed before their
respective executions. Only two full-model attempts were authorized by this
milestone; do not launch another without a new prospective diagnostic protocol.

The staged driver is implemented by microstructure_pilot.prepare_pilot and
run_input. It resumes the authenticated contact database, solves the smallest
registered stage, exports actual RF/contact/fields, and applies force/contact
gates before any further stage. Subsequent stages use actual multiframe restart
after POST1, verified in a separate real small control. The authoritative loading
is the frozen pilot protocol and actual TIME/D commands, not generic setup-config
defaults. There is no 2% microstructure request in this milestone.

Each checkpoint exporter uses vector UX/UY for every specimen node and masks
corner nodes before stress/elastic-strain retrieval. Contact data distinguish
stored endpoints from element averages; endpoint maxima are not continuous-surface
bounds. No unsupported midside stress is filled. Unconverged states are excluded.

```powershell
python -m metamaterial_eval.simulation.microstructure_results --manifest experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json --execution ACTUAL_ARTIFACT_ROOT/solver/v063/pilot_002 --protocol experiments/pipeline_v0.6.3/run_001/protocol/PILOT_PROTOCOL_002.json --output NEW_RESULT_EVIDENCE_PATH
```

## Verification and reports

```powershell
$env:EVALUATOR_PATH = 'validation/evaluators/evaluator_v1_1.py'
python -m pytest tests validation/test_evaluator.py -q
python -m pytest validation/ansys_v062_integration.py -q
python -m pytest validation/ansys_v063_integration.py -q
python scripts/replay_geometry_archives.py --output NEW_ARCHIVE_REPLAY_PATH
python scripts/report_v063.py
```

The v063 evidence suite intentionally includes a real converged-microstructure
acceptance check. It fails if no checkpoint converged; do not change or skip it
to inflate integration counts. Unit controls and overlapping archived suites
are reported separately. Report generation is fixed to saved run_001, requires
its actual raw artifacts and generates mechanical plots only from validated
checkpoint fields. The saved report and figures are the handoff if raw local
artifacts are unavailable on a receiving machine.

Do not interpret a failed numerical/contact/resource attempt as a physically
poor design. No batch design study, autonomous LLM loop, internal self-contact,
mechanical convergence claim or 3D workflow is implemented here.
