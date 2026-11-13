# Licensed analytical benchmarks

| Native control/attempt | Analytical E (MPa) | Native E (MPa) | Relative error | Accepted |
|---|---:|---:|---:|---|
| M0_matrix_H1_attempt001 | 1000.00000000 | 1000.00000000 | 1.2619e-14 | True |
| M1_equal_H1_attempt001 | 1000.00000000 | 93.95433940 | 0.90605 | False |
| M1_equal_H1_attempt002 | 1000.00000000 | 1000.00000000 | 7.4931e-13 | True |
| M1_parallel_H1_attempt001 | 5500.00000000 | 5499.99999992 | 1.4535e-11 | True |
| M1_series_H1_attempt001 | 1818.18181818 | 1818.18181797 | 1.1383e-10 | True |

All accepted controls use five actual native result sets and independent read-only RST export. The nu=0 parallel/series controls isolate analytically tractable load sharing; they do not replace nu = 0.30 in the P3 comparison. Native 2024 R1 ETLIST/RLIST/MPLIST, exact connectivity, material IDs, constraints, displacement fields, constitutive stress/strain relations, reactions and integrated energy are verified.

The first dense equal-material attempt is rejected. Default coordinate NSEL tolerance included an interior row, producing771 UY constraints instead of514. The corrected exact node-ID boundary sets and native DLIST gate recovered the control without changing morphology, materials or tolerances. The failed input, RST, exports and rejection remain preserved. A separate Python boolean-serialization failure was fixed by reprocessing existing native data; no fabricated solver output or unnecessary rerun was used.
