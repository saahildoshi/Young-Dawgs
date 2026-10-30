# Durable local mesh artifacts

Large files use YD_ARTIFACT_ROOT when configured. Default Windows storage is
LOCALAPPDATA/YoungDawgs/artifacts; Linux uses XDG_CACHE_HOME/YoungDawgs/artifacts
or ~/.cache/YoungDawgs/artifacts. This is a local cache, not an assumed backup.
There is no automatic upload, required cloud service or proprietary transfer.

For this completed run, a second copy of the qualified mesh and its manifest
is retained under `C:/Users/sd22446/YoungDawgs-Artifacts`, outside both the
application cache and the repository. Its relative path and independent full
CRC/byte/semantic verification are recorded in
`experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/durable_copy.json`.
This user-profile copy survives ordinary application-cache removal; it is on
the same computer and does not establish an off-device backup. Set
YD_ARTIFACT_ROOT to that directory to retrieve this mesh using the original
tracked manifest. Raw solver databases remain in the original local cache.

Each mesh resides under meshes/<design>/<version>/mesh.npz with its own
artifact_manifest.json. Track the same manifest under the experiment directory.
It records a stable logical ID, artifact-relative path, source/config/Gmsh
identity, semantic and file-byte hashes, node/element counts, qualification,
known root at creation and reproduction command. Generation output is never
silently overwritten. Default discovery searches only this registry.

```powershell
python -m metamaterial_eval.simulation.mesh_artifacts discover
python -m metamaterial_eval.simulation.mesh_artifacts verify --manifest experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json
```

To transfer, copy the complete artifact-relative mesh folder and its manifest
to the same relative path under the destination's chosen artifact root. Set
YD_ARTIFACT_ROOT there, then run verify. Registry discovery verifies filenames
and manifests only; it never establishes content acceptance. Verify reads all
archive members/CRC and authenticates both byte and semantic hashes.
The resolver normalizes Windows backslashes in recorded relative paths before
joining them on any platform. Absolute/drive/UNC paths and escaping traversal
are rejected; portable manifests never require a hard-coded artifact root.

OneDrive may be chosen explicitly as an artifact root. After copying, use its
normal client controls to keep the mesh folder available on this device, wait
for sync completion and verify on each receiving computer. A filename/cloud
placeholder is insufficient: inability to read/hydrate actual bytes is failure.
No global OneDrive configuration is changed by this workflow.

The historical source WKB and selected semantic mesh SHA256 remain authoritative.
NPZ ZIP bytes may differ across compression runtimes while mesh arrays remain
identical. This v0.6.3 reproduction exactly matches the registered semantic hash;
the original Linux NPZ archive was not recovered and byte identity is not claimed.

On this Windows checkout, the frozen mesh protocol has CRLF line endings.
Its raw hash differs from the recorded Linux LF hash. Only CRLF→LF comparison
is permitted, and it reproduces the original hash exactly. The historical file
is not modified; both hashes and the initial strict-check failure are recorded.

For regeneration after genuine loss, invoke mesh_artifacts reproduce with a new
evidence output path and an unused versioned artifact directory. The current
registered v063_regen_001 destination refuses overwrite. A future additional
candidate needs a new prospective protocol/version, not a silent rerun.
