# Young Dawgs Metamaterial Evaluation

This repository generates and quantitatively evaluates 2-D binary disordered
mechanical metamaterials. The canonical data contract is a `256 x 256`
`uint8` array in which `1` is solid and `0` is void; connected-component and
percolation calculations use 4-connectivity.

## Start here

Current research priority: [Pipeline v0.6 — actual 2D meshing and contact-enabled
ANSYS compression](docs/pipeline_v0.6/2D_COMPRESSION_VALIDATION.md). Three-dimensional
CAD/meshing is deferred. The solver-independent proof of concept preserves all
412 pores of authenticated Design9/seed1; the final fine mesh fails its registered
angle gate, and ANSYS is unavailable. **No ANSYS simulation or mechanical result
has been verified.** Historical scientific HOLD decisions remain unchanged.
See [Windows execution](docs/pipeline_v0.6/WINDOWS_EXECUTION.md) and the prospective
protocol under experiments/pipeline_v0.6/protocol/.

The latest validation-only milestone is
[Pipeline v0.4.3: P10 metric qualification](docs/PIPELINE_V0_4_3_P10_QUALIFICATION.md).
Its amended decision is **PASS within the tested domain**: 10/10 independent
invariant controls, 3/3 deliberate-thinning detections, 4/4 local-neck outcomes,
and 10/10 saved native pairs passed the registered replacement checks.
Whole-mask P10 remains diagnostic. This is not an exhaustive neck-strength or
manufacturing certification, and no CAD has been started.

The preceding milestone is
[Pipeline v0.4.2: thickness convergence verification](docs/PIPELINE_V0_4_2_THICKNESS.md).
All ten native 1024→2048 pairs passed the mean/P10/pore numerical limits. Its
historical status remains **HOLD solely on analytic P10 calibration**.
Generator v0.4.1 and evaluator v1.1 remain unchanged; no CAD has been started.

For the topology correction, thickness/pore convergence investigation, preserved
30-case rerun, and Windows commands, start with
[Pipeline v0.4.1: resolution-convergence stabilization](docs/PIPELINE_V0_4_1_STABILIZATION.md).
That historical v0.4.1 run has topology 30/30 but retains **HOLD** under its
512→1024 mean/P10 thickness gates. Its results are not retroactively changed.

For native 256/512/1024 rendering of the successful v0.3 generator and matched
convergence validation, see [Pipeline v0.4: resolution independence](docs/PIPELINE_V0_4_RESOLUTION.md).
This does not add CAD, vectorization or FEM.

For controlled design variability (10 parameter designs × 2 seeds), see
[Pipeline v0.3: parametric exploration](docs/PIPELINE_V0_3_EXPLORATION.md).
It runs alongside the existing replication workflow, without FEM automation.

The complete file reference, metric definitions, output interpretation, and
copy-paste command catalog are in
[docs/PROJECT_REFERENCE.md](docs/PROJECT_REFERENCE.md).

The automated/resumable I2F1 research workflow is documented in
[docs/PIPELINE_V0_2.md](docs/PIPELINE_V0_2.md), including optional connected-network
reference cleaning and Windows commands. The
[v0.1 guide](docs/PIPELINE_V0_1.md) remains available for historical runs.

```powershell
py -3.10 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pytest -q
```

Start a Pipeline v0.2 run and inspect its manual model boundary (reference
topology is preserved unless `--topology-mode single_connected_network` is added):

```powershell
python -m metamaterial_eval.pipeline start `
  data\reference\reference_binary.npy `
  --run-name concrete_01

python -m metamaterial_eval.pipeline status `
  experiments\pipeline_v0.2\reference_binary\concrete_01
```

Run the stored pilot generator and both evaluation protocols:

```powershell
python experiments\pilot_voronoi\generate_microstructures.py `
  --output-dir experiments\pilot_voronoi\samples

python -m metamaterial_eval evaluate `
  data\reference\reference_binary.npy `
  experiments\pilot_voronoi\samples `
  --output-dir experiments\pilot_voronoi\results\finite_domain

python scripts/evaluate_and_plot.py
```

## Top-level organization

| Path | Role |
|---|---|
| `metamaterial_eval/` | Reusable finite-domain evaluation package |
| `scripts/` | Periodic research evaluator and diagnostic plotting |
| `data/reference/` | Canonical target image and binary array |
| `experiments/` | Generator prompts, source, samples, and results |
| `validation/` | Frozen evaluator versions and analytical acceptance tests |
| `tests/` | Automated tests for the reusable package |
| `docs/` | Scientific definitions and operating instructions |

Use v1.1 for research. The v1.0 evaluator and its outputs are retained only
under versioned validation/archive paths for provenance.
