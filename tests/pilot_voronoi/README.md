# Pilot Voronoi Generator

This experiment uses jittered staggered generator points, smooth coordinate
warping, Voronoi cell boundaries, and spatially varying interface thickness to
produce irregular cellular solid networks.

The principal parameters are defined near the top of `iteration_0.py`:

- `CELL_SPACING`: typical pore-cell spacing;
- `POINT_JITTER` and `POINT_DROPOUT`: cell-size disorder;
- `WARP_AMPLITUDE` and `WARP_SIGMA`: interface curvature scale;
- `SOLID_HALF_WIDTH`: baseline half-strut thickness;
- `WIDTH_VARIATION`: coarse thickness variability;
- `ROUGHNESS_AMPLITUDE`: fine boundary roughness.

Run from the repository root:

```bash
python tests/pilot_voronoi/iteration_0.py \
  --output-dir tests/pilot_voronoi/generated_microstructures
```

Then evaluate:

```bash
python -m metamaterial_eval evaluate \
  data/reference/reference_binary.npy \
  tests/pilot_voronoi/generated_microstructures
```

Generate the periodic ensemble diagnostics and figures:

```bash
python scripts/evaluate_and_plot.py
```

The generator is deterministic for a specified seed. Re-running seeds 0-19
with unchanged code reproduces the existing arrays exactly.

`generated_microstructures/metrics_report.json` and `.txt` use the validated
v1.1 dimension definitions. The files containing `v1_0_legacy` preserve the
pre-validation pixel-weighted EDT report for provenance only and must not be
used as the research baseline.
