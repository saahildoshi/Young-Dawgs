---
title: Evaluator Analytical Validation Results
date: 2026-07-29
tags:
  - metamaterials
  - evaluator-validation
  - python
  - research
---

# Evaluator Analytical Validation Results

## Quick comparison

| Version | Passed | Failed | Decision | SHA-256 |
|---|---:|---:|---|---|
| v1.0 | 36 / 56 | 20 / 56 | Rejected | `de2bcf4a76d24c267bbcb9f7af7027ee364fd6015266cf0b0259ad8d69694b09` |
| v1.1 | 56 / 56 | 0 / 56 | Accepted | `aef73a8d120feb2cf6da8ed67e088fa91bc920e1e9e0824933b039a61ddfa47b` |

The phase convention for both versions is:

$$
\text{solid}=1,\qquad \text{void}=0
$$

The registered v1.1 validity rule is:

$$
f_{\mathrm{largest}}\geq 0.98,\qquad P_x=1,\qquad P_y=1
$$

---

# Evaluator v1.0

## v1.0 summary

v1.0 correctly handled phase convention, volume fraction, 4-connectivity,
percolation, periodic $S_2$, scalar lineal path, NRMSE, malformed inputs,
diversity ordering, and deterministic repeated evaluation.

Its 20 failures came from:

| Failure group | Failed tests | Main problem |
|---|---:|---|
| Registered validity rule | 5 | Rule was used informally but no reusable `structure_is_valid` function existed |
| Strut and pore dimensions | 10 | EDT values were sampled at every phase pixel, biasing results toward boundaries |
| Directional lineal path | 2 | Directional curves were calculated internally but not returned |
| Sample seed audit | 1 | Files were counted, but missing and duplicate seed identities were not reported |
| Ensemble standard deviation | 1 | Used sample deviation with `ddof=1` instead of population deviation with `ddof=0` |
| Copy detection | 1 | Only aligned SSIM/NCC existed; translated, rotated, and mirrored copies were not handled |

## v1.0 phase convention and volume fraction

| # | Test | Short description | Expected | v1.0 result | Status |
|---:|---|---|---|---|:---:|
| 1 | Fully solid image | Confirms that value `1` is interpreted as solid | $\phi_s=1$, one component, $f_{\mathrm{largest}}=1$, $P_x=P_y=1$ | All expected values returned | ✅ |
| 2 | Fully void image | Confirms that value `0` is void and undefined dimensions do not crash | $\phi_s=0$, zero components, $P_x=P_y=0$, undefined dimensions reported safely | Returned zero topology values and `NaN` dimensions without crashing | ✅ |
| 3 | Half-solid vertical split | Checks exact solid fraction for 32,768 solid pixels | $\phi_s=0.5$ within $10^{-12}$ | $\phi_s=0.5$ | ✅ |
| 4 | Quarter-solid block | Checks exact solid fraction for 16,384 solid pixels | $\phi_s=0.25$ within $10^{-12}$ | $\phi_s=0.25$ | ✅ |
| 5 | Single solid pixel | Checks the smallest nonzero fraction in a $256\times256$ image | $\phi_s=1/65536=1.52587890625\times10^{-5}$ | Exact expected value | ✅ |

## v1.0 connectivity and percolation

| # | Test | Short description | Expected | v1.0 result | Status |
|---:|---|---|---|---|:---:|
| 6 | Edge-connected pair | Two pixels share an edge | One 4-connected component; $f_{\mathrm{largest}}=1$ | Correct | ✅ |
| 7 | Diagonal pair | Two pixels touch only at a corner | Two components; $f_{\mathrm{largest}}=0.5$ | Correct; confirms 4-connectivity | ✅ |
| 8 | Three unequal components | Components contain 10, 5, and 1 pixels | Three components; $f_{\mathrm{largest}}=10/16=0.625$ | Correct | ✅ |
| 9 | Horizontal bar | Bar spans left to right only | $P_x=1$, $P_y=0$ | Correct | ✅ |
| 10 | Vertical bar | Bar spans top to bottom only | $P_x=0$, $P_y=1$ | Correct | ✅ |
| 11 | Cross | One network spans both axes | $P_x=P_y=1$ | Correct | ✅ |
| 12 | Separate left/right contacts | Different components touch opposite horizontal boundaries | $P_x=0$ | Correct; no false positive | ✅ |
| 13 | Separate top/bottom contacts | Different components touch opposite vertical boundaries | $P_y=0$ | Correct; no false positive | ✅ |

## v1.0 full validity rule

| # | Test | Short description | Expected | v1.0 result | Status |
|---:|---|---|---|---|:---:|
| 14 | Valid network with a small island | Main spanning component contains more than 98% of solid pixels | `valid=True` | `structure_is_valid` did not exist | ❌ |
| 15 | Invalid 95% connected case | Main network contains approximately 95% of solid pixels | `valid=False` | `structure_is_valid` did not exist | ❌ |
| 16 | Invalid missing-direction case | One connected horizontal network does not span vertically | `valid=False` | `structure_is_valid` did not exist | ❌ |
| 17 | Exact threshold | Tests inclusive boundary at $f_{\mathrm{largest}}=0.98$ | `valid=True` | `structure_is_valid` did not exist | ❌ |
| 18 | Below threshold | Tests $f_{\mathrm{largest}}=97/99\approx0.979798$ | `valid=False` | `structure_is_valid` did not exist | ❌ |

## v1.0 strut thickness and pore diameter

| # | Test | Short description | Expected | v1.0 result | Status |
|---:|---|---|---|---|:---:|
| 19 | Uniform 2 px bar | Calibrates EDT thickness at the smallest resolved bar | Median and P10 near 2 px | Median 2 px; P10 2 px | ✅ |
| 20 | Uniform 4 px bar | Checks recovery of a 4 px bar | Median and P10 near 4 px | Median 2 px; P10 2 px | ❌ |
| 21 | Uniform 8 px bar | Checks recovery of an 8 px bar | Median and P10 near 8 px | Median 4 px; P10 2 px | ❌ |
| 22 | Uniform 16 px bar | Checks recovery of a 16 px bar | Median and P10 near 16 px | Median 8 px; P10 2 px | ❌ |
| 23 | Bar-width trend | Tests widths 2, 4, 8, and 16 px | Strictly increasing response with slope near 1 | Medians $[2,2,4,8]$; not strictly increasing; slope about 0.45 | ❌ |
| 24 | Mixed 4 px and 10 px bars | Checks whether P10 identifies the thin feature | Mean between 4 and 10 px; P10 near 4 px | Mean in range, but P10 was 2 px | ❌ |
| 25 | One-pixel line | Tests minimum thickness and edge-case stability | Finite minimum value; no crash | Median 2 px; finite; no crash | ✅ |
| 26 | Circular pore with $R=5$ px | Checks one pore with nominal $D=10$ px | One diameter near 10 px | Returned 81 pixel-weighted values; median 4 px; maximum 10.198 px | ❌ |
| 27 | Circular pore with $R=10$ px | Checks one pore with nominal $D=20$ px | One diameter near 20 px | Returned 317 pixel-weighted values; median 6.325 px; maximum 20.100 px | ❌ |
| 28 | Circular pore with $R=20$ px | Checks one pore with nominal $D=40$ px | One diameter near 40 px | Returned 1,257 pixel-weighted values; median 12 px; maximum 40.050 px | ❌ |
| 29 | Two enclosed pores | Checks equal per-pore weighting for nominal diameters 10 and 30 px | Two measurements with median near 20 px | Returned 790 pixel-weighted samples | ❌ |
| 30 | Open edge-connected void | Determines whether exterior void is counted as a pore | Open void excluded; zero enclosed-pore values | Returned 480 void-pixel values | ❌ |

## v1.0 two-point correlation $S_2$

| # | Test | Short description | Expected | v1.0 result | Status |
|---:|---|---|---|---|:---:|
| 31 | Solid and void limits | Checks analytical phase limits | Solid: $S_2(r)=1$; void: $S_2(r)=0$ | Correct for all tested radii | ✅ |
| 32 | Target against itself | Checks descriptor and error consistency | $E_{S_2}<10^{-12}$ | $E_{S_2}=0$ | ✅ |
| 33 | Bernoulli field | Averages 24 fields with $p=0.4$ | $S_2(0)\approx0.4$ and $S_2(r>0)\approx p^2=0.16$ | Within the required $\pm0.005$ tolerance | ✅ |
| 34 | Translation and 90° rotation | Tests periodic and radial invariance | Curves equal within $10^{-12}$ | Both invariance checks passed | ✅ |

## v1.0 lineal-path function $L$

| # | Test | Short description | Expected | v1.0 result | Status |
|---:|---|---|---|---|:---:|
| 35 | Solid and void limits | Checks analytical limits | Solid: $L(r)=1$; void: $L(r)=0$ | Correct | ✅ |
| 36 | Target against itself | Checks self-error | $E_L<10^{-12}$ | $E_L=0$ | ✅ |
| 37 | Directional bar response | Horizontal and vertical bars should exchange $L_x$ and $L_y$ behavior | Long horizontal bar has $L_x>L_y$; vertical bar has $L_y>L_x$ | Directional output function was missing | ❌ |
| 38 | Broken horizontal bar | Confirms that the entire segment, not only endpoints, is checked | A one-pixel gap strongly reduces $L_x$ | Directional output function was missing | ❌ |

## v1.0 NRMSE

| # | Test | Short description | Expected | v1.0 result | Status |
|---:|---|---|---|---|:---:|
| 39 | Direct curve arrays | Tests identical and reversed `[0,1]` curves | Identical: 0; reversed: $\sqrt{2}\approx1.414214$ | Both values correct | ✅ |
| 40 | Constant-zero target | Tests zero normalization denominator | Identical zero curves return 0; nonzero sample against zero target returns explicit infinity | Correct and did not crash | ✅ |

## v1.0 sample discovery and input cleaning

| # | Test | Short description | Expected | v1.0 result | Status |
|---:|---|---|---|---|:---:|
| 41 | Discovery, sorting, and seed audit | Uses NPY files only, natural sorting, and missing/duplicate seed reporting | NPY-only list plus missing seed 2 and duplicate seed 0 | NPY filtering and sorting worked, but seed-audit function was missing | ❌ |
| 42 | Boolean binary input | Checks safe conversion from `bool` | Accepted and converted to `uint8` 0/1 | Correct | ✅ |
| 43 | Float 0/1 input | Checks safe conversion from floating binary data | Accepted and converted to `uint8` 0/1 | Correct | ✅ |
| 44 | Integer 0/255 input | Checks common image-like NPY encoding | Accepted and canonicalized to 0/1 | Correct | ✅ |
| 45 | Grayscale 0/128/255 input | Prevents silent thresholding of arbitrary grayscale NPY data | Rejected clearly | Correctly rejected | ✅ |
| 46 | Invalid values 0/1/2 | Prevents nonbinary material labels | Rejected clearly | Correctly rejected | ✅ |
| 47 | Invalid values -1/0/1 | Prevents treating all nonzero values as solid | Rejected clearly | Correctly rejected | ✅ |
| 48 | Three-dimensional array | Rejects RGB-like or volumetric input | Clear dimensionality error | Correctly rejected | ✅ |
| 49 | One-dimensional array | Rejects non-image input | Clear dimensionality error | Correctly rejected | ✅ |
| 50 | Empty array | Rejects empty data | Clear empty-array error | Correctly rejected | ✅ |
| 51 | Wrong $128\times128$ shape | Enforces expected $256\times256$ geometry | Clear shape error | Correctly rejected | ✅ |

## v1.0 ensemble statistics, diversity, copy detection, and reproducibility

| # | Test | Short description | Expected | v1.0 result | Status |
|---:|---|---|---|---|:---:|
| 52 | Population standard deviation | Uses fractions 0.2, 0.4, and 0.6 | Mean 0.4; $\sigma=0.163299$ using `ddof=0` | Mean 0.4; standard deviation 0.2 using `ddof=1` | ❌ |
| 53 | Diversity ranking | Compares duplicates, small perturbations, and independent fields | $D_A<D_B<D_C$ | Correct ordering | ✅ |
| 54 | Base all/valid aggregation | Checks counts and population statistics for all and valid subsets | All count 3; valid count 2; correct means and deviations | Correct | ✅ |
| 55 | Transformation-aware copy detection | Tests exact, shifted, rotated, mirrored, 1% noise, and unrelated images | Copies flagged; unrelated field not flagged | Transformation-aware function was missing | ❌ |
| 56 | Repeated function evaluation | Runs deterministic functions twice on identical input | Bitwise-identical curves and identical topology dictionary | Identical results | ✅ |

---

# Evaluator v1.1

## v1.1 summary

v1.1 passed all 56 analytical tests. It retained the correct v1.0 topology and
spatial-statistics behavior while correcting dimensional measurements,
validity registration, seed auditing, population statistics, directional
lineal-path output, and transformed-copy detection.

## v1.1 phase convention and volume fraction

| # | Test | Short description | Expected | v1.1 result | Status |
|---:|---|---|---|---|:---:|
| 1 | Fully solid image | Confirms that value `1` is interpreted as solid | $\phi_s=1$, one component, $f_{\mathrm{largest}}=1$, $P_x=P_y=1$ | All expected values returned | ✅ |
| 2 | Fully void image | Confirms that value `0` is void and undefined dimensions do not crash | $\phi_s=0$, zero components, $P_x=P_y=0$, undefined dimensions reported safely | Returned zero topology values and `NaN` dimensions without crashing | ✅ |
| 3 | Half-solid vertical split | Checks exact solid fraction for 32,768 solid pixels | $\phi_s=0.5$ within $10^{-12}$ | $\phi_s=0.5$ | ✅ |
| 4 | Quarter-solid block | Checks exact solid fraction for 16,384 solid pixels | $\phi_s=0.25$ within $10^{-12}$ | $\phi_s=0.25$ | ✅ |
| 5 | Single solid pixel | Checks the smallest nonzero fraction in a $256\times256$ image | $\phi_s=1/65536=1.52587890625\times10^{-5}$ | Exact expected value | ✅ |

## v1.1 connectivity and percolation

| # | Test | Short description | Expected | v1.1 result | Status |
|---:|---|---|---|---|:---:|
| 6 | Edge-connected pair | Two pixels share an edge | One 4-connected component; $f_{\mathrm{largest}}=1$ | Correct | ✅ |
| 7 | Diagonal pair | Two pixels touch only at a corner | Two components; $f_{\mathrm{largest}}=0.5$ | Correct; confirms 4-connectivity | ✅ |
| 8 | Three unequal components | Components contain 10, 5, and 1 pixels | Three components; $f_{\mathrm{largest}}=10/16=0.625$ | Correct | ✅ |
| 9 | Horizontal bar | Bar spans left to right only | $P_x=1$, $P_y=0$ | Correct | ✅ |
| 10 | Vertical bar | Bar spans top to bottom only | $P_x=0$, $P_y=1$ | Correct | ✅ |
| 11 | Cross | One network spans both axes | $P_x=P_y=1$ | Correct | ✅ |
| 12 | Separate left/right contacts | Different components touch opposite horizontal boundaries | $P_x=0$ | Correct; no false positive | ✅ |
| 13 | Separate top/bottom contacts | Different components touch opposite vertical boundaries | $P_y=0$ | Correct; no false positive | ✅ |

## v1.1 full validity rule

| # | Test | Short description | Expected | v1.1 result | Status |
|---:|---|---|---|---|:---:|
| 14 | Valid network with a small island | Main spanning component contains more than 98% of solid pixels | `valid=True` | Correct | ✅ |
| 15 | Invalid 95% connected case | Main network contains $97/102\approx0.95098$ of solid pixels | `valid=False` | Correct | ✅ |
| 16 | Invalid missing-direction case | One connected horizontal network does not span vertically | `valid=False` | Correct | ✅ |
| 17 | Exact threshold | Tests inclusive boundary at $f_{\mathrm{largest}}=0.98$ | `valid=True` | Correct; confirms `>=` | ✅ |
| 18 | Below threshold | Tests $f_{\mathrm{largest}}=97/99\approx0.979798$ | `valid=False` | Correct | ✅ |

## v1.1 strut thickness and pore diameter

| # | Test | Short description | Expected | v1.1 result | Status |
|---:|---|---|---|---|:---:|
| 19 | Uniform 2 px bar | Calibrates skeleton-sampled EDT at the smallest resolved bar | Median and P10 near 2 px | Median 2 px; P10 2 px | ✅ |
| 20 | Uniform 4 px bar | Checks recovery of a 4 px bar | Median and P10 near 4 px | Median 4 px; P10 4 px | ✅ |
| 21 | Uniform 8 px bar | Checks recovery of an 8 px bar | Median and P10 near 8 px | Median 8 px; P10 8 px | ✅ |
| 22 | Uniform 16 px bar | Checks recovery of a 16 px bar | Median and P10 near 16 px | Median 16 px; P10 16 px | ✅ |
| 23 | Bar-width trend | Tests widths 2, 4, 8, and 16 px | Strictly increasing response with slope near 1 | Medians $[2,4,8,16]$; fitted slope 1.0000 | ✅ |
| 24 | Mixed 4 px and 10 px bars | Checks whether P10 identifies the thin feature | Mean between 4 and 10 px; P10 near 4 px | Mean 6.932 px; P10 4 px | ✅ |
| 25 | One-pixel line | Tests minimum thickness and edge-case stability | Finite minimum value; no crash | Median 2 px; finite; no crash | ✅ |
| 26 | Circular pore with $R=5$ px | Checks one pore with nominal $D=10$ px | One diameter near 10 px | One value: 10.198 px | ✅ |
| 27 | Circular pore with $R=10$ px | Checks one pore with nominal $D=20$ px | One diameter near 20 px | One value: 20.100 px | ✅ |
| 28 | Circular pore with $R=20$ px | Checks one pore with nominal $D=40$ px | One diameter near 40 px | One value: 40.050 px | ✅ |
| 29 | Two enclosed pores | Checks equal per-pore weighting for nominal diameters 10 and 30 px | Two measurements with median near 20 px | Two component measurements; median within 1 px of 20 px | ✅ |
| 30 | Open edge-connected void | Determines whether exterior void is counted as a pore | Open void excluded; zero enclosed-pore values | Zero pore values; one open component recorded as excluded | ✅ |

## v1.1 two-point correlation $S_2$

| # | Test | Short description | Expected | v1.1 result | Status |
|---:|---|---|---|---|:---:|
| 31 | Solid and void limits | Checks analytical phase limits | Solid: $S_2(r)=1$; void: $S_2(r)=0$ | Correct for all tested radii | ✅ |
| 32 | Target against itself | Checks descriptor and error consistency | $E_{S_2}<10^{-12}$ | $E_{S_2}=0$ | ✅ |
| 33 | Bernoulli field | Averages 24 fields with $p=0.4$ | $S_2(0)\approx0.4$ and $S_2(r>0)\approx p^2=0.16$ | $S_2(0)=0.400528$; mean nonzero-separation value 0.160440 | ✅ |
| 34 | Translation and 90° rotation | Tests periodic and radial invariance | Curves equal within $10^{-12}$ | Both invariance checks passed | ✅ |

## v1.1 lineal-path function $L$

| # | Test | Short description | Expected | v1.1 result | Status |
|---:|---|---|---|---|:---:|
| 35 | Solid and void limits | Checks analytical limits | Solid: $L(r)=1$; void: $L(r)=0$ | Correct | ✅ |
| 36 | Target against itself | Checks self-error | $E_L<10^{-12}$ | $E_L=0$ | ✅ |
| 37 | Directional bar response | Horizontal and vertical bars should exchange $L_x$ and $L_y$ behavior | Horizontal: $L_x>L_y$; vertical: $L_y>L_x$ | Correct directional ordering | ✅ |
| 38 | Broken horizontal bar | Confirms that the entire segment, not only endpoints, is checked | A one-pixel gap strongly reduces $L_x$ | At $r=20$, $L_x$ fell from 0.0625 to 0.041992; ratio 0.671875 | ✅ |

## v1.1 NRMSE

| # | Test | Short description | Expected | v1.1 result | Status |
|---:|---|---|---|---|:---:|
| 39 | Direct curve arrays | Tests identical and reversed `[0,1]` curves | Identical: 0; reversed: $\sqrt{2}\approx1.414214$ | Both values correct | ✅ |
| 40 | Constant-zero target | Tests zero normalization denominator | Identical zero curves return 0; nonzero sample against zero target returns explicit infinity | Correct and did not crash | ✅ |

The registered formula is:

$$
\operatorname{NRMSE}
=
\frac{
\sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i-\hat{y}_i)^2}
}{
\sqrt{\frac{1}{n}\sum_{i=1}^{n}y_i^2}
}
$$

## v1.1 sample discovery and input cleaning

| # | Test | Short description | Expected | v1.1 result | Status |
|---:|---|---|---|---|:---:|
| 41 | Discovery, sorting, and seed audit | Uses NPY files only, natural sorting, and missing/duplicate seed reporting | NPY-only list plus missing seed 2 and duplicate seed 0 | Correct file list and audit | ✅ |
| 42 | Boolean binary input | Checks safe conversion from `bool` | Accepted and converted to `uint8` 0/1 | Correct | ✅ |
| 43 | Float 0/1 input | Checks safe conversion from floating binary data | Accepted and converted to `uint8` 0/1 | Correct | ✅ |
| 44 | Integer 0/255 input | Checks common image-like NPY encoding | Accepted and canonicalized to 0/1 | Correct | ✅ |
| 45 | Grayscale 0/128/255 input | Prevents silent thresholding of arbitrary grayscale NPY data | Rejected clearly | Correctly rejected | ✅ |
| 46 | Invalid values 0/1/2 | Prevents nonbinary material labels | Rejected clearly | Correctly rejected | ✅ |
| 47 | Invalid values -1/0/1 | Prevents treating all nonzero values as solid | Rejected clearly | Correctly rejected | ✅ |
| 48 | Three-dimensional array | Rejects RGB-like or volumetric input | Clear dimensionality error | Correctly rejected | ✅ |
| 49 | One-dimensional array | Rejects non-image input | Clear dimensionality error | Correctly rejected | ✅ |
| 50 | Empty array | Rejects empty data | Clear empty-array error | Correctly rejected | ✅ |
| 51 | Wrong $128\times128$ shape | Enforces expected $256\times256$ geometry | Clear shape error | Correctly rejected | ✅ |

## v1.1 ensemble statistics, diversity, copy detection, and reproducibility

| # | Test | Short description | Expected | v1.1 result | Status |
|---:|---|---|---|---|:---:|
| 52 | Population standard deviation | Uses fractions 0.2, 0.4, and 0.6 | Mean 0.4; $\sigma=0.163299$ using `ddof=0` | Mean 0.4; $\sigma=0.163299$ | ✅ |
| 53 | Diversity ranking | Compares duplicates, small perturbations, and independent fields | $D_A<D_B<D_C$ | $D_A=0$, $D_B=0.009722$, $D_C=0.479338$ | ✅ |
| 54 | Base all/valid aggregation | Checks counts and population statistics for all and valid subsets | All count 3; valid count 2; correct means and deviations | Correct | ✅ |
| 55 | Transformation-aware copy detection | Tests exact, shifted, rotated, mirrored, 1% noise, and unrelated images | Copies flagged; unrelated field not flagged | Scores: exact 1.0000, shifted 1.0000, rotated 1.0000, mirrored 1.0000, 1% noise 0.978991, unrelated 0.064759 | ✅ |
| 56 | Repeated function evaluation | Runs deterministic functions twice on identical input | Bitwise-identical curves and identical topology dictionary | Identical results | ✅ |

## v1.1 full-run reproducibility

Two complete runs were also performed on the 20 pilot samples.

| Check | Result |
|---|---|
| Numerical JSON after removing output-directory path strings | Identical |
| Montage PNG | Byte-identical |
| $S_2$ plot PNG | Byte-identical |
| $L$ plot PNG | Byte-identical |
| Pore-distribution PNG | Byte-identical |
| Diversity heatmap PNG | Byte-identical |
| Samples discovered | 20 |
| Valid samples | 20 |
| Missing or duplicate seeds | None |
| Sanity controls | All passed |
| Target-copy flags | 0 |

## Final conclusion

v1.0 should be kept only for provenance. Its topology and periodic descriptors
were mostly correct, but its dimensional metrics and several supporting checks
were not suitable for the intended experiment.

v1.1 is the accepted evaluator for future generator comparisons. Old v1.0
strut and pore values must not be compared directly with v1.1 results because
the measurement definitions changed.
