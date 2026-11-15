# Morphology, composition and mechanical trade-offs

The independent scripts all shift toward aligned axial inclusion chains separated by thin matrix ligaments. This was not a researcher-authored procedural baseline or an edit to returned code. It emerges in both measured-feedback and objective-only responses. All outputs pass the frozen complete-region mean, size, population and topology guardrails. Nevertheless, the strong lane organization departs visibly from the original irregular dispersed field. **Numerical-envelope feasibility and strong material-family preservation must remain separate.** Do not retrofit a new rejection threshold, repair the outputs or hide this result.

The complete-region mean aspect rule permits a mixture of a few long, high-area inclusions with many small inclusions. Additional post-hoc area-weighted shape-tail and directional-organization diagnostics quantify this limitation. These new metrics are explicitly descriptive and were not used for feedback, selection or acceptance. Four-connected annotation regions include censored regions; undefined aspect coverage is reported. No annotation descriptor is a physical particle-instance measurement.

| Script | Area-weighted annotation aspect | Vertical alignment cos2theta | Area fraction aspect >3 (defined) | Columns ≥80% reinforcement |
|---|---:|---:|---:|---:|
| REFERENCE | 2.069 | -0.121 | 0.101 | 0.000 |
| BASE | 1.990 | 0.022 | 0.099 | 0.000 |
| P3_OPT_MF_01 | 2.956 | 0.996 | 0.487 | 0.277 |
| P3_OPT_MF_02 | 3.438 | 0.998 | 0.711 | 0.281 |
| P3_OPT_NF_01 | 3.397 | 1.000 | 0.771 | 0.274 |
| P3_OPT_NF_02 | 3.816 | 0.992 | 0.878 | 0.270 |

All MF and NF realizations have identical exact phase counts, so their direct arm comparison has no count variation. BASE counts vary under the registered policy; a purely geometry-only BASE-relative causal attribution is not certified without separate exact-composition confirmation or numerical fraction sensitivity. Report observed counts rather than a guessed correction. Previously visible/hidden reconstruction errors remain distinct from feasibility and the stiffness objective.

Phase-specific element-associated SYY means, equivalent-stress percentiles normalized by each specimen nominal stress, and elastic-energy shares are retained in `optimization_analysis/PHASE_FIELDS.csv`. Compare these under fixed strain and also normalized stress; increased raw stress alone can reflect increased nominal loading. Pixel-corner maxima remain exploratory. No plasticity, damage, yielding, fracture or calibrated failure response is modeled.

## Measured H1 cohort summaries

| Script | Visible descriptor error | Hidden descriptor error | Mean diameter (px) | Mean aspect | NN distance (px) | NN CV | Interface density |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASE | 0.01268 | 0.07915 | 15.68827 | 2.00643 | 20.86034 | 0.31882 | 0.09681 |
| MF_01 | 0.10728 | 0.21196 | 16.38840 | 2.57213 | 20.38149 | 0.40774 | 0.07575 |
| MF_02 | 0.14402 | 0.22508 | 12.89209 | 2.42309 | 15.67349 | 0.57223 | 0.06512 |
| NF_01 | 0.16648 | 0.23610 | 13.62352 | 2.49370 | 16.77213 | 0.63824 | 0.05891 |
| NF_02 | 0.06882 | 0.24190 | 14.51340 | 1.96064 | 14.55337 | 0.52929 | 0.06541 |

Descriptor errors use the unchanged v0.7.0 normalization, not percentage accuracy. Nearest-neighbor statistics describe complete connected annotations, not recovered particle instances or a complete clustering characterization.

| Script | Matrix mean SYY (MPa) | Reinforcement mean SYY (MPa) | Matrix p99 equivalent / nominal | Reinforcement p99 equivalent / nominal | Matrix energy share | Reinforcement energy share |
|---|---:|---:|---:|---:|---:|---:|
| BASE | -6.76253 | -12.13341 | 1.55846 | 3.21744 | 0.86396 | 0.13604 |
| MF_01 | -5.48841 | -40.01954 | 1.56107 | 3.22617 | 0.35776 | 0.64224 |
| MF_02 | -5.34461 | -42.93085 | 0.96558 | 3.27714 | 0.29946 | 0.70054 |
| NF_01 | -5.31758 | -43.48567 | 0.73983 | 3.00168 | 0.29370 | 0.70630 |
| NF_02 | -5.42495 | -41.18742 | 0.84782 | 3.09547 | 0.31901 | 0.68099 |

These are equal-weight means of each script's ten accepted H1 specimens at0.5% compression. Native MAT1 maps to raw matrix label1; native MAT2 maps to raw reinforcement label5. Phase p99/nominal is a stress-localization diagnostic, not a failure prediction. Energy shares are from native element strain energies.
