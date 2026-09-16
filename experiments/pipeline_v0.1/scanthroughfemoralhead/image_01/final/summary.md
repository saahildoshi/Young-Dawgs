# Pipeline Run Summary

Reference: `scanthroughfemoralhead`  
Run ID: `image_01`  
Pipeline version: `0.1.0`  
Evaluator: `v1.1`  
Prompt strategy: `I2F1`  
Iterations completed: `4`

## Target

| Metric | Value |
|---|---:|
| phi_s | 0.310883 |
| f_largest | 0.876755 |
| Px | 1 |
| Py | 1 |
| mean_strut_thickness | 2.655 |
| p10_strut_thickness | 2 |
| median_pore_diameter | 6.32456 |

## Development trajectory

| Iteration | Valid | $\phi_s$ | $f_\mathrm{largest}$ | Mean thickness | P10 | Pore diameter | $S_2$ NRMSE | $L$ NRMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 0/20 | 0.310883 | 0.877481 | 2.63196 | 2 | 5.12373 | 0.0252375 | 0.0303097 |
| 1 | 0/20 | 0.310883 | 0.876755 | 2.6518 | 2 | 8.70282 | 0.0144907 | 0.0341854 |
| 2 | 0/20 | 0.310883 | 0.876755 | 2.65973 | 2 | 4.68547 | 0.03272 | 0.046472 |
| 3 | 0/20 | 0.310883 | 0.876755 | 2.67661 | 2 | 5.21258 | 0.0252745 | 0.0301754 |

## Final development performance

- Valid samples: 0/20
- Mean $S_2$ NRMSE: 0.0252745
- Mean $L$ NRMSE: 0.0301754
- $D_\mathrm{pair}$: 0.427034
- Copy flags: none

## Held-out performance

- Valid samples: 0/20
- Mean $S_2$ NRMSE: 0.0249592
- Mean $L$ NRMSE: 0.031532
- $D_\mathrm{pair}$: 0.426986
- Copy flags: none

## Development vs held-out comparison

- phi_s: development 0.310883; held-out 0.310883; difference 0.
- f_largest: development 0.876755; held-out 0.876755; difference 0.
- mean_strut_thickness: development 2.67661; held-out 2.67459; difference -0.00201425.
- p10_strut_thickness: development 2; held-out 2; difference 0.
- median_pore_diameter: development 5.21258; held-out 5.30144; difference 0.0888539.
- E_S2: development 0.0252745; held-out 0.0249592; difference -0.000315372.
- E_L: development 0.0301754; held-out 0.031532; difference 0.00135658.
- D_pair: development 0.427034; held-out 0.426986; difference -4.83463e-05.

## Generator metadata

- Script hash: `9e321a01ab86f236116658179dc9087af531f7ab1f4f21234db971de6509da35`
- Source iteration: 3
- Line count: 2415
- Held-out runtime: 28.674 s
- Repair usage: `{'0': False, '1': False, '2': False, '3': False}`
- Target information used: solid fraction, largest-component fraction, $S_2$, lineal path, thickness, and pore diameter.

## Notes / warnings

- iteration_0: 0 of 20 samples satisfied topology validity.
- iteration_1: 0 of 20 samples satisfied topology validity.
- iteration_2: 0 of 20 samples satisfied topology validity.
- iteration_3: 0 of 20 samples satisfied topology validity.
- heldout: 0 of 20 samples satisfied topology validity.
