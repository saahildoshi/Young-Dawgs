# Metric Definitions and Interpretation

## Basic morphology

For a binary solid indicator field $I(\mathbf{x}) \in \{0,1\}$, the solid
volume fraction is

$
\phi_s = \frac{1}{N}\sum_{\mathbf{x}} I(\mathbf{x}).
$

Solid components are labeled with 4-connectivity. The largest-component
fraction is

$
f_\mathrm{largest} =
\frac{N_\mathrm{solid,\ largest}}{N_\mathrm{solid,\ total}}.
$

`percolates_x` requires one labeled component to touch both the left and right
boundaries. `percolates_y` similarly requires contact with the top and bottom
boundaries. A generated sample is valid only when

```text
f_largest >= 0.98 and percolates_x and percolates_y
```

This is a topology filter, not a similarity score.

## Two-point correlation

$S_2(r)$ is the probability that two points separated by distance $r$ both
lie in the solid phase. The implementation uses a zero-padded FFT
autocorrelation, preventing periodic wraparound. Pair counts are normalized by
the number of geometrically available pairs in each nearest-integer radial
annulus. The origin is checked explicitly:

$
S_2(0) = \phi_s.
$

Interpretation:

- the short-range decay reflects characteristic strut and pore length scales;
- oscillations can indicate repeated cell spacing or other spatial order;
- the large-$r$ limit should approach approximately $\phi_s^2$ for a
  statistically homogeneous medium without long-range order.

## Lineal-path function

$L(r)$ is the probability that an entire digital line segment lies in the
solid phase. Here, $r$ is endpoint separation, so the segment contains
$r+1$ pixels and $L(0)=\phi_s$.

The package returns exact horizontal `l_x` and vertical `l_y` curves. The
reported radial estimate is an available-segment-weighted average over the
0°, 45°, 90°, and 135° lattice directions. A slower dense-angular estimator
would be needed if high-resolution anisotropy is a primary research outcome.

## EDT local dimensions

The solid Euclidean distance transform is sampled on the solid skeleton. Each
sample is twice the distance to void, providing a centreline-based local strut
width. Each enclosed 4-connected void component contributes one pore diameter:
twice the maximum void distance. Void touching an image boundary is classified
as external/open and excluded. Reported scalar values are:

- mean solid-phase strut thickness;
- 10th-percentile strut thickness, sensitive to thin load-path bottlenecks;
- median void-phase pore diameter.

All values are in pixels. For a physical pixel scale $s$ in millimeters per
pixel, multiply reported diameters by $s$. A one-pixel and two-pixel bar both
produce the minimum `2 px` EDT width under pixel-centre geometry.

## Curve errors

For $C$ equal to either $S_2$ or $L$,

$
\mathrm{NRMSE}(C) =
\frac{
  \sqrt{\frac{1}{n}\sum_r(C_\mathrm{sample}(r)-C_\mathrm{target}(r))^2}
}{
  \sqrt{\frac{1}{n}\sum_r C_\mathrm{target}(r)^2}
}.
$

Lower is better. NRMSE is dimensionless and should be interpreted together
with volume fraction, connectedness, and local dimensions; a low curve error
does not independently guarantee mechanical equivalence.

## Original v1.0 finite-domain result

The stored pre-validation report records:

- 20/20 samples valid;
- mean solid fraction `0.397624`, versus target `0.394699`;
- mean $S_2$ NRMSE `0.056032`;
- mean lineal-path NRMSE `0.038910`;
- mean strut thickness `4.577 px`, versus target `4.616 px`;
- median pore diameter `7.241 px`, versus target `6.325 px`.

Those dimension values used rejected pixel-weighted EDT sampling and must not
be treated as the physical-dimension baseline. The validated v1.1 baseline is
recorded in `validation/validation_notes.md`.

## Improved periodic evaluator

`scripts/evaluate_and_plot.py` implements an alternative periodic evaluation
protocol. Its $S_2$ uses periodic FFT autocorrelation with minimum-image
radial bins, and its four-direction $L(r)$ wraps segments across boundaries.
Both descriptors are therefore invariant under integer translations generated
with `numpy.roll`.

Additional checks are:

- `SSIM` and zero-lag normalized cross-correlation (`NCC`) against the target;
- a potential-copy flag when transformation-aware periodic `NCC >= 0.85`;
- pairwise pixel disagreement
  $D_{ij}=N^{-1}\sum_\mathbf{x}|I_i(\mathbf{x})-I_j(\mathbf{x})|$;
- ensemble diversity $D_\mathrm{pair}$, the upper-triangle mean of
  $D_{ij}$, with a current healthy-diversity criterion of `> 0.05`;
- target-copy, periodic-translation, and matched-volume-fraction Bernoulli
  sanity controls.

For the stored pilot, the periodic evaluator gives:

- all required sanity checks passing;
- $D_\mathrm{pair}=0.477421$, well above the `0.05` threshold;
- no transformed-copy flags;
- mean periodic $S_2$ error `0.05362`;
- mean periodic lineal-path error `0.04016`.

Both evaluators now use population standard deviation (`ddof=0`) and the same
validated strut/pore definitions. Their curve errors differ because the base
package uses a finite image domain while the plotting evaluator uses periodic
descriptors.
