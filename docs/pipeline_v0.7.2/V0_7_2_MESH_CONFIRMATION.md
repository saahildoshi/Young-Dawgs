# Prospective mesh confirmation

| Script | Seed | H1 E (MPa) | H2 E (MPa) | Mesh change | H1 paired gain | H2 paired gain | H2 gain > observed-change diagnostic |
|---|---:|---:|---:|---:|---:|---:|---|
| BASE | 2000 | 1688.923 | 1679.628 | 0.553% | +0.000% | +0.000% | False |
| BASE | 2001 | 1674.408 | 1665.118 | 0.558% | +0.000% | +0.000% | False |
| BASE | 2002 | 1697.078 | 1687.170 | 0.587% | +0.000% | +0.000% | False |
| P3_OPT_MF_01 | 2000 | 3285.264 | 3273.664 | 0.354% | +94.518% | +94.904% | True |
| P3_OPT_MF_01 | 2001 | 3281.453 | 3268.780 | 0.388% | +95.977% | +96.309% | True |
| P3_OPT_MF_01 | 2002 | 3295.910 | 3284.098 | 0.360% | +94.211% | +94.651% | True |
| P3_OPT_MF_02 | 2000 | 3446.901 | 3437.531 | 0.273% | +104.089% | +104.660% | True |
| P3_OPT_MF_02 | 2001 | 3445.333 | 3435.818 | 0.277% | +105.764% | +106.341% | True |
| P3_OPT_MF_02 | 2002 | 3448.000 | 3438.824 | 0.267% | +103.173% | +103.822% | True |
| P3_OPT_NF_01 | 2000 | 3476.889 | 3471.217 | 0.163% | +105.864% | +106.666% | True |
| P3_OPT_NF_01 | 2001 | 3478.712 | 3472.997 | 0.165% | +107.758% | +108.574% | True |
| P3_OPT_NF_01 | 2002 | 3477.215 | 3471.680 | 0.159% | +104.894% | +105.769% | True |
| P3_OPT_NF_02 | 2000 | 3340.190 | 3333.102 | 0.213% | +97.770% | +98.443% | True |
| P3_OPT_NF_02 | 2001 | 3339.973 | 3332.536 | 0.223% | +99.472% | +100.138% | True |
| P3_OPT_NF_02 | 2002 | 3296.862 | 3289.217 | 0.232% | +94.267% | +94.955% | True |

The first three held-out seeds for EVERY script were registered before H1 outcomes. H2 subdivides each unchanged source pixel into2×2 elements, preserving material assignments, source shape and phase fractions. Candidate-minus-BASE gains are compared at matched mesh levels. The sum of observed candidate and BASE absolute H1/H2 modulus changes is a conservative screening diagnostic, not a rigorous FE error bound or statistical confidence interval.

Matched-subset MF-minus-NF mean script gains: H1=-2.049 percentage points; H2=-2.309 percentage points. Compare these matched subsets, not all-ten H1 against three-seed H2. Refinement evidence applies to these fifteen geometries only; it does not certify asymptotic convergence or all unrefined realizations.
