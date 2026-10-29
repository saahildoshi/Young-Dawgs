# Reproduce v0.6.2 licensed Windows rectangle qualification

The measured run used Windows 11, Python 3.14.6, ANSYS 2024 R1 and the existing
project .venv. Full versions are in run_001/environment/environment.json.
Shapely 2.2.0 was used on this machine, whereas requirements-v0.5.txt pins 2.1.2.
This is an explicitly recorded environment difference. No geometry implementation
or historic dependency record was changed. For the measured Windows package set,
install the project and requirements-v0.6.2-windows.txt into an isolated venv.

```powershell
python -m pip install -e .
python -m pip install -r requirements-v0.6.2-windows.txt
$env:EVALUATOR_PATH = 'validation/evaluators/evaluator_v1_1.py'
python -m pytest tests validation/test_evaluator.py -q
```

Run from the repository root. Use a new output name every time. Discovery reads
AWP_ROOT selectors and actual installation files; do not enter license secrets.
The actual tested executable was ANSYS241.exe under the discovered v241 root.
All production solver jobs use one shared-memory core, request 2048 MB initial
memory and enforce an 8 GiB sampled process-tree RSS limit and 180 s timeout.
The -m option is not a hard memory cap. Only newly owned process trees are stopped.

```powershell
$studyRun = 'experiments/pipeline_v0.6.2/reproduce_001'
$protocol = 'experiments/pipeline_v0.6.2/run_001/protocol/BENCHMARK_PROTOCOL.json'
$correction = 'experiments/pipeline_v0.6.2/run_001/protocol/CONTACT_CORRECTION_001.json'
python -m metamaterial_eval.simulation.windows_ansys audit --output "$studyRun/environment"
python -m metamaterial_eval.simulation.licensed_benchmark prepare --protocol $protocol --output "$studyRun/rectangle_direct/generated/input"
python -m metamaterial_eval.simulation.licensed_benchmark run --source "$studyRun/rectangle_direct/generated/input" --output "$studyRun/rectangle_direct/generated/execution"
python -m metamaterial_eval.simulation.licensed_benchmark analyze --execution "$studyRun/rectangle_direct/generated/execution" --protocol $protocol --output "$studyRun/rectangle_direct/results"
python -m metamaterial_eval.simulation.licensed_benchmark prepare --contact --protocol $protocol --correction $correction --output "$studyRun/rectangle_contact/generated/input"
python -m metamaterial_eval.simulation.licensed_benchmark run --source "$studyRun/rectangle_contact/generated/input" --direct "$studyRun/rectangle_direct/results/qualification.json" --output "$studyRun/rectangle_contact/generated/execution"
python -m metamaterial_eval.simulation.licensed_benchmark analyze --execution "$studyRun/rectangle_contact/generated/execution" --protocol $protocol --output "$studyRun/rectangle_contact/results"
python -m metamaterial_eval.simulation.licensed_benchmark contact-points --execution "$studyRun/rectangle_contact/generated/execution" --output "$studyRun/contact_point_validation"
```

Inspect status JSON after each command. Contact execution requires an authentic
direct qualification token. Input generation or a process exit alone is not
qualification. Failed runs retain all original artifacts. An optional explicit
ANSYS_EXECUTABLE selector must identify a real accessible executable.

The new producer retains native ANSYS RF signs: upper negative, lower positive.
Nominal compression stress is -upper_RF/(initial width × initial thickness).
This is explicitly converted when calling the old positive-compression metric
helper; historical synthetic controls are unchanged. Small-strain analytical
acceptance is registered through 0.5%; 1% and 2% are finite-deformation diagnostics.
All six requested positive stages must actually be achieved. Zero is the actual
initial mesh and CNCHECK configuration, not a fabricated solved field.

Displacement output includes every specimen node. Nodal stress/elastic strain
queries include only corner nodes; v241 does not store these quantities at
midsides. Old raw CONT ETABLE quantities are element averages. The supplemental
RST reader extracts SMISC1/2 pressures, NMISC5/6 endpoint penetration/gap and
NMISC22 total contact-element force. These are not a continuous-surface bound.

For the saved run_001 only, execute real evidence checks separately:

```powershell
python -m pytest validation/ansys_v062_integration.py -q
python scripts/replay_geometry_archives.py --output experiments/pipeline_v0.6.2/archive_replay_new
python scripts/report_v062.py
```

The integration checks fail if genuine local solver artifacts are missing;
they do not mock a solver, skip missing evidence or launch a new solve. The
report script is fixed to the saved run_001 and requires its original raw RST
files. Git contains compact selected fields, sanitized logs and raw hashes;
large databases and RST files remain local under ignored generated directories.
Copy complete run folders separately when transferring between machines.

Workbench/Mechanical journal and embedded scripting both executed. MAPDL is the
selected mesh-and-contact production route. Actual CDWRITE generated blocked
CDB archives locally; no CDB extension was applied to a custom N/EN text deck.
Workbench External Model import of those archives was NOT EXECUTED and is not
a prerequisite for the verified direct MAPDL route. No Workbench project solve
or thin 3D surrogate is claimed.

The selected full microstructure mesh is absent from the checkout. Retrieve the
original authenticated fine_new mesh bytes before import; do not substitute the
rejected coarse mesh or regenerate geometry. Then measure solver import, memory,
disk and license-size capacity and freeze a separate pilot protocol. Current
hardware capacity for a 5.53 million DOF contact solve is UNQUALIFIED.
