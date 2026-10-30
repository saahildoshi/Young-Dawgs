# v0.6.5 prospective memory and output recovery

Start: clean master at 0de6cd7c77652ad0d265200881642cd0d228a047.
Read repository instructions and the actual v0.6.4 reports under experiments;
requested docs report paths resolve there. Historical inputs, logs, RST and
RDB hashes match their saved execution receipts. No historical file is edited.

The primary run reached its first equilibrium, completed the substep and
started another factorization. OUTRES ALL LAST did not retain its intermediate
checkpoint. The conditional run ended during native output/database growth
after equilibrium. Its RST contains displacement but no required RF, continuum
stress/strain or contact records. Authenticated read-only output proves this;
no restart frame exists. A complete historical checkpoint is not recoverable.
Exact command-specific allocation causality and last-write activity are not
known because historical file-growth telemetry was absent.

The new full run has NO process RSS termination threshold. It uses actual
system health: 6 GiB available-memory reserve sustained for 30 seconds, 1 GiB
critical available for 3 seconds, low-memory notification/commit evidence,
and severe paging with stalled output. Transient lows reset on recovery.
Disk reserve is 20 GiB; prospective wall limit is 1800 seconds, allowing output
and checkpoint writing after the previously observed 5-7 minute equilibrium.
No pagefile settings or unrelated user applications will be changed.

The existing DEFAULT sparse mode automatically selected in-core storage of
about 6 GB in the native logs. Retain DEFAULT rather than force INCORE or
OUTOFCORE. Preserve geometry, mesh, physical assumptions, nodal target-normal
contact, fixed PP100 and original equilibrium/contact acceptance criteria.

Test selective NSOL/RSOL/STRS/EPEL/CONT/MISC LAST output with OUTPR suppressed
and selected-result duplication disabled. Keep one final restart frame and
save the model only after solution output. Verify this on matched full-output
rectangle and compliant fixtures, including separate read-only repeated export,
before freezing and committing the single 0.005% full-model run.

Only complete native fields with independent upper/lower reaction checks,
contact consistency and positive deformed mappings can qualify mechanics.
One accepted point is not a curve or fitted modulus. No additional strain
checkpoints, batch FEM, 3D, autonomous optimization or manufacturing work is
planned. The JSON protocol contains exact limits and source references.
