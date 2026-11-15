# Controlled geometry–mechanics development dataset

Eighteen registered source arrays were generated: six baseline and three each in four researcher-designed probe families. Every source has exactly20,731 reinforcement pixels. One baseline seed3104 fails the frozen2px diagnostic-dilation x-spanning rule; its source is preserved, not repaired or replaced, and no mechanics is assigned. All12 variant sources pass. These are researcher probes, not genuine LLM revision trials.

| Family | Accepted native H1 / attempts | Mean MPa | Sample SD MPa | Min–max MPa |
|---|---:|---:|---:|---|
| BASE | 5/6 | 1691.641977 | 34.915836 | 1665.952667–1751.880129 |
| V1_ELONGATION | 3/3 | 1733.730838 | 20.882331 | 1710.508528–1750.964717 |
| V2_VERTICAL | 3/3 | 1753.014414 | 13.225451 | 1738.211449–1763.666544 |
| V3_HORIZONTAL | 3/3 | 1636.445794 | 15.923973 | 1618.089503–1646.550138 |
| V4_DISPERSION | 3/3 | 1708.669769 | 19.145403 | 1690.947330–1728.975761 |

All accepted cases use five actual solved strain levels0.1–0.5% and independent RST readbacks. The first registered development seed in all five families also receives H2. The original qualified source/evaluator is unchanged. Shapes, spatial placement and RNG trajectories covary, so the measured relationships are not isolated single-variable causal estimates. Horizontal loading was not registered/executed. H1/H2 preserve exact categorical geometry; observed changes are not an asymptotic error bound. Baseline mechanics describe5/6 feasible survivors and cannot establish perfect baseline reliability.

| Descriptor | Pooled Pearson diagnostic | n |
|---|---:|---:|
| all_observed.area_weighted_aspect | +0.2515 | 17 |
| all_observed.vertical_alignment | +0.8955 | 17 |
| long_range_abs_S2_difference | -0.0249 | 17 |
| nearest_neighbor_cv | +0.1362 | 17 |
