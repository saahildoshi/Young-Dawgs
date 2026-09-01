# Analysis Scripts

`evaluate_and_plot.py` is the formal periodic ensemble evaluator. It adds
sanity controls, novelty screening, diversity measurement, and publication-
ready diagnostic figures to the compact base-package report.

Run from the repository root:

```bash
python scripts/evaluate_and_plot.py
```

Use `python scripts/evaluate_and_plot.py --help` for custom target, sample,
output, radius, and expected-count arguments.

## Pilot v1.1 feedback trajectories

`plot_feedback_trajectories.py` compares the finite-domain ensemble metrics
for `I0F1`, `I1F1`, and `I2F1` over iterations `0 -> 1 -> 2 -> 3`. It plots
metric trajectories only; it does not produce a Voronoi or sample montage.

Plot the 12 existing reports:

```bash
python scripts/plot_feedback_trajectories.py
```

Reevaluate all 12 generated ensembles before plotting:

```bash
python scripts/plot_feedback_trajectories.py --evaluate
```

The default `--population all` is intentional because `I0F1` iteration 0 has
zero topology-valid samples. Use `--population valid` only when you want the
invalid initial ensemble displayed as missing values.

The successful no-feedback baseline is `I0F0/Run_1` and is included as a
separate diamond marker by default. `I0F0/Run_2` and `Run_3` are excluded. Use
`--no-baseline` to plot only the three feedback trajectories.
