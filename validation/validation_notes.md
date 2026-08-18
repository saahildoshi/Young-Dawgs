# Evaluator Validation Notes

## Decision

`evaluator_v1_0.py` is rejected for research use. It passed 36 of 56 final
acceptance tests and failed 20.

`evaluator_v1_1.py` is accepted. It passed all 56 analytical, edge-case,
statistical, discovery, diversity, and copy-detection tests. Two complete pilot
runs produced identical numerical JSON after removing output-directory paths
and byte-identical copies of all five figures.

## Frozen environment

| Item | Value |
|---|---|
| Python | 3.10.0 |
| NumPy | 2.2.6 |
| SciPy | 1.15.3 |
| scikit-image | 0.25.2 |
| Matplotlib | 3.10.9 |
| v1.0 SHA-256 | `de2bcf4a76d24c267bbcb9f7af7027ee364fd6015266cf0b0259ad8d69694b09` |
| v1.1 SHA-256 | `aef73a8d120feb2cf6da8ed67e088fa91bc920e1e9e0824933b039a61ddfa47b` |
| Git commit | unavailable; repository has no commits |

## v1.0 findings

The core topology and spatial descriptors were correct:

- `1` was consistently solid and `0` void;
- exact volume fractions passed at `1e-12` tolerance;
- edge contact and diagonal contact confirmed 4-connectivity;
- percolation required one shared spanning component;
- periodic radial \(S_2\) passed solid, void, Bernoulli, translation, rotation,
  and self-error controls;
- periodic scalar \(L\) passed solid, void, and self-error controls;
- target-RMS NRMSE passed direct numerical tests;
- malformed input rejection and diversity ordering passed.

The rejected behavior was:

1. No registered function/report field for the full validity rule.
2. Solid EDT sampled every solid pixel, causing boundary pixels to dominate.
   An 8-pixel bar returned median `4 px` and P10 `2 px`.
3. Void EDT sampled every void pixel, so a radius-10 circular pore returned 317
   local samples and median `6.325 px`, rather than one approximately `20 px`
   pore diameter.
4. Boundary-connected exterior void was included as pore material.
5. Directional lineal paths were calculated internally but not returned.
6. Sample count was checked, but missing and duplicate seed identities were not
   audited.
7. Ensemble standard deviation used `ddof=1`, conflicting with the registered
   population-statistic convention.
8. Copy detection used aligned SSIM only and did not catch translated, rotated,
   or mirrored target copies.

## Registered v1.1 conventions

### Topology

- phase convention: solid `1`, void `0`;
- solid components: 4-connectivity;
- valid sample:
  `f_largest >= 0.98 and Px == 1 and Py == 1`;
- the threshold is inclusive.

### Strut thickness

The solid Euclidean distance transform is sampled on the solid skeleton:

\[
t = 2d_\mathrm{solid}
\]

This exactly recovered median widths `2, 4, 8, 16 px` for the corresponding
uniform bars. With pixel-center EDT geometry, both a one-pixel and a two-pixel
bar report the minimum `2 px`; sub-two-pixel discrimination is impossible on
this raster.

### Pore diameter

Void components use 4-connectivity. Each enclosed component contributes one
maximal-inscribed diameter:

\[
d_p = 2\max(d_\mathrm{void}).
\]

Components touching any image boundary are classified as open/external void
and excluded. Circular pores with nominal diameters `10, 20, 40 px` measured
`10.198, 20.100, 40.050 px`.

### Spatial descriptors

- \(S_2\): periodic FFT circular autocorrelation, minimum-image distance,
  nearest-integer radial bins;
- \(L\): periodic complete-segment probability in 0°, 45°, 90°, and 135°
  directions;
- a separation \(r\) contains `r + 1` digital pixels;
- directional `l_x`, `l_y`, `l_45`, and `l_135` curves are retained;
- NRMSE: `RMSE(sample,target) / RMS(target)`.

### Discovery and cleaning

- only top-level `.npy` files are evaluated;
- PNG figures and other files are ignored;
- Boolean, `0/1` float, `0/1` integer, and `0/255` arrays are canonicalized;
- grayscale and other invalid values are rejected;
- wrong shape, dimensionality, and empty arrays fail clearly;
- expected, missing, unexpected, duplicate, and unparseable seed names are
  reported.

### Ensemble statistics and novelty

- ensemble standard deviation is population `ddof=0`;
- diversity is reported separately from similarity;
- transformed-copy screening maximizes periodic normalized cross-correlation
  across translations and the eight rotations/reflections of a square;
- the copy threshold is `max_transform_NCC >= 0.85`.

## Pilot baseline after corrected dimensions

All 20 stored samples are topology-valid and seeds 0-19 are complete and
unique. Evaluator sanity checks pass, no target-copy flags occur, and
`D_pair = 0.477421`.

| Metric | Target | Generated mean |
|---|---:|---:|
| Mean skeleton strut thickness | 6.540 px | 6.712 px |
| P10 skeleton strut thickness | 4.000 px | 4.472 px |
| Median enclosed-pore diameter | 16.492 px | 18.494 px |
| Periodic \(S_2\) NRMSE | — | 0.05362 |
| Periodic \(L\) NRMSE | — | 0.04016 |

The corrected dimension values must be treated as a new baseline. They are not
numerically comparable to v1.0 pixel-weighted EDT results.
