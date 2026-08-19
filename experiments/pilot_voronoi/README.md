# Pilot Voronoi Experiment

This is the first stored procedural-generation trial. It creates 20
deterministic, seed-controlled cellular networks using jittered generator
points, smooth coordinate warping, Voronoi interfaces, and spatially varying
strut thickness.

| Path | Meaning |
|---|---|
| `generator_prompt.txt` | Original LLM prompt used to request the generator |
| `generate_microstructures.py` | Reproducible generator for seeds 0 through 19 |
| `provenance/` | Original LLM transcript retained as research provenance |
| `samples/` | Numerical NPY samples and matching visualization PNGs |
| `results/finite_domain/` | Current compact package report |
| `results/periodic/` | Current v1.1 diagnostics, JSON, and five figures |
| `archive/v1_0/` | Superseded v1.0 outputs; do not use as the baseline |

Run from the repository root:

```bash
python experiments/pilot_voronoi/generate_microstructures.py \
  --output-dir experiments/pilot_voronoi/samples

python -m metamaterial_eval evaluate \
  data/reference/reference_binary.npy \
  experiments/pilot_voronoi/samples \
  --output-dir experiments/pilot_voronoi/results/finite_domain

python scripts/evaluate_and_plot.py
```

The main generator parameters are defined near the top of
`generate_microstructures.py`: `CELL_SPACING`, `POINT_JITTER`,
`POINT_DROPOUT`, `WARP_AMPLITUDE`, `WARP_SIGMA`, `SOLID_HALF_WIDTH`,
`WIDTH_VARIATION`, and `ROUGHNESS_AMPLITUDE`.
