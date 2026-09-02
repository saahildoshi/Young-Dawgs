# Young Dawgs Metamaterial Evaluation

This repository generates and quantitatively evaluates 2-D binary disordered
mechanical metamaterials. The canonical data contract is a `256 x 256`
`uint8` array in which `1` is solid and `0` is void; connected-component and
percolation calculations use 4-connectivity.

## Start here

The complete file reference, metric definitions, output interpretation, and
copy-paste command catalog are in
[docs/PROJECT_REFERENCE.md](docs/PROJECT_REFERENCE.md).

The automated/resumable I2F1 research workflow is documented in
[docs/PIPELINE_V0_1.md](docs/PIPELINE_V0_1.md).

```bash
python3 -m venv .venv-macos
source .venv-macos/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
python -m pytest -q
```

Start a Pipeline v0.1 run and inspect its manual model boundary:

```bash
python -m metamaterial_eval.pipeline start \
  data/reference/reference_binary.npy \
  --run-name concrete_01

python -m metamaterial_eval.pipeline status \
  experiments/pipeline_v0.1/reference_binary/concrete_01
```

Run the stored pilot generator and both evaluation protocols:

```bash
python experiments/pilot_voronoi/generate_microstructures.py \
  --output-dir experiments/pilot_voronoi/samples

python -m metamaterial_eval evaluate \
  data/reference/reference_binary.npy \
  experiments/pilot_voronoi/samples \
  --output-dir experiments/pilot_voronoi/results/finite_domain

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
