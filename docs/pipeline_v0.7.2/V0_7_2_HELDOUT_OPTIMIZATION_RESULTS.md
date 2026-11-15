# Held-out apparent-stiffness results

| Script | Feasible / attempted | Native H1 mean E ± sample SD (MPa) | Mean paired gain | Positive pairs |
|---|---:|---:|---:|---:|
| BASE | 10/10 | 1692.509 ± 20.719 | +0.000% | 0% (10 pairs) |
| MF_01 | 10/10 | 3282.328 ± 13.686 | +93.960% | 100% (10 pairs) |
| MF_02 | 10/10 | 3446.853 ± 3.471 | +103.682% | 100% (10 pairs) |
| NF_01 | 10/10 | 3478.258 ± 3.231 | +105.537% | 100% (10 pairs) |
| NF_02 | 10/10 | 3347.538 ± 28.049 | +97.810% | 100% (10 pairs) |

Every scalar uses five actual licensed native checkpoints and independent RST reopening. J=E/1000 MPa. The BASE self-comparison is zero by definition; it is not an LLM revision. All ten attempts per script remain in the denominator. Individual results, native hashes, paired gains and exact fractions are in `optimization_analysis/HELDOUT_RESULTS.csv`; script means/spreads and runtime are in `SCRIPT_SUMMARIES.json`.

MF script-average paired gain=+98.821%; NF=+101.673%; MF minus NF=-2.852 percentage points. Each arm has TWO independent LLM responses; ten seeds are nested replicates per response, not ten model trials. There are no pooled-seed p values or universal causal claims.

All 40 revised outputs have exactly20,731 reinforcement pixels. BASE varies within the prospectively registered ±64-pixel policy; report individual counts and distinguish tolerance-constrained comparisons from exact-composition comparisons. No guessed phase-fraction correction is applied. All revisions produce aligned segmented lanes, a strong visual departure from the irregular reference. Passing the numerical envelope does not establish strong preservation of the intended natural particle family.
