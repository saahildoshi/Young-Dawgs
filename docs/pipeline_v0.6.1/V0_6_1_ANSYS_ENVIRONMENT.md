# v0.6.1 ANSYS environment

**ANSYS_EXECUTION_BLOCKED. No ANSYS process was launched.**

Fresh runtime inspection: Linux x86_64, Python3.12.14; no Mechanical, MAPDL,
Workbench executable found through PATH, ANSYS_EXECUTABLE/AWP_ROOT selectors or
conventional ANSYS installation locations. PyMAPDL/PyMechanical are not installed.
No remote solver endpoint, identity or credential is configured. An unavailable
executable prevents actual license checkout. License is NOT_TESTED_NO_SOLVER;
this is not a measured license denial or proof that no license exists elsewhere.

The environment command was invoked with --smoke. Discovery stopped it before
input generation or process launch. Actual version/interface/solver startup time,
license checkout, supported element/contact formulations and actual solve time
are unverified. Windows has not been executed. Machine-readable evidence is
ansys_environment/run_001/environment.json.

The selected future route is native MAPDL batch, with a bounded licensed direct
rectangle smoke and full evidence receipts. A path existing in configuration
means only DETECTED_FILE_ONLY until an actual recognized-release analysis runs.
Release mismatches, license errors, process failure, missing output, partial
convergence and missing review remain distinct failure states.

Official documentation must match the actual installed release. The managed
network policy excludes ANSYS web help; earlier v0.6 requests returned403.
There is no installed release against which to claim element compatibility.
The APDL templates remain DRAFT_UNVERIFIED: review PLANE183 TRI6 ordering,
KEYOPT(1)/KEYOPT(3), thickness/force scaling, CONTA172/TARGE169 compatibility,
normal direction, finite sliding, pilot DOFs, default stiffness and result items.
Distributed Gmsh4.15.0 API behavior was actually exercised for meshing; that does
not validate any ANSYS command. See WINDOWS_EXECUTION.md for the complete packet.
