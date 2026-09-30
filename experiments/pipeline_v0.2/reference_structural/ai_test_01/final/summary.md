# Pipeline Run Summary

Reference: `reference_structural`  
Run ID: `ai_test_01`  
Pipeline version: `0.2.0`  
Evaluator: `v1.1`  
Topology policy: `single_connected_network`  
Validity: `component_count == 1 and Px == 1 and Py == 1`  
Prompt strategy: `I2F1`  
Iterations completed: `4`

## Target

| Metric | Value |
|---|---:|
| component_count | 1 |
| phi_s | 0.477341 |
| f_largest | 1 |
| Px | 1 |
| Py | 1 |
| mean_strut_thickness | 4.11262 |
| p10_strut_thickness | 2.82843 |
| median_pore_diameter | 7.2111 |

## Reference preprocessing

- Solid components: 1 raw; 1 retained.
- Removed components: 0.
- Removed solid pixels: 0 (0.0000% of raw solid).
- Removed image-area fraction: 0.000000.
- Retained image solid fraction: 0.477341.

## Development trajectory

| Iteration | Policy valid | Mean components | $\phi_s$ | $f_\mathrm{largest}$ | Mean thickness | P10 | Pore diameter | $S_2$ NRMSE | $L$ NRMSE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | 20/20 | 1 | 0.477341 | 1 | 3.27613 | 2 | 4.88679 | 0.0407423 | 0.0826854 |
| 1 | 20/20 | 1 | 0.477341 | 1 | 4.07073 | 2.82843 | 7.2111 | 0.00900864 | 0.0309354 |
| 2 | 20/20 | 1 | 0.477341 | 1 | 4.10663 | 2.82843 | 7.2111 | 0.00939101 | 0.0289245 |
| 3 | 20/20 | 1 | 0.477341 | 1 | 4.11264 | 2.82843 | 7.2111 | 0.00976009 | 0.0268793 |

## Final development performance

- Valid samples: 20/20
- Mean solid component count: 1 +/- 0 (population SD)
- Legacy v1.1 valid samples: 20/20
- Mean $S_2$ NRMSE: 0.00976009
- Mean $L$ NRMSE: 0.0268793
- $D_\mathrm{pair}$: 0.488144
- Copy flags: none

## Held-out performance

- Valid samples: 20/20
- Mean solid component count: 1 +/- 0 (population SD)
- Legacy v1.1 valid samples: 20/20
- Mean $S_2$ NRMSE: 0.0105529
- Mean $L$ NRMSE: 0.027827
- $D_\mathrm{pair}$: 0.488207
- Copy flags: none

## Development vs held-out comparison

- component_count: development 1; held-out 1; difference 0.
- phi_s: development 0.477341; held-out 0.477341; difference 0.
- f_largest: development 1; held-out 1; difference 0.
- mean_strut_thickness: development 4.11264; held-out 4.10957; difference -0.00306506.
- p10_strut_thickness: development 2.82843; held-out 2.82843; difference 0.
- median_pore_diameter: development 7.2111; held-out 7.2111; difference 0.
- E_S2: development 0.00976009; held-out 0.0105529; difference 0.000792836.
- E_L: development 0.0268793; held-out 0.027827; difference 0.000947686.
- D_pair: development 0.488144; held-out 0.488207; difference 6.31232e-05.

## Generator metadata

- Script hash: `0b33b526c414cb9650398264153d79f25368bb59d47abeb269db20b9b2e7859f`
- Source iteration: 3
- Line count: 1283
- Held-out runtime: 1.474 s
- Repair usage: `{'0': True, '1': False, '2': False, '3': False}`
- Target information used: solid fraction, largest-component fraction, $S_2$, lineal path, thickness, and pore diameter.

## Notes / warnings

- No automated warnings were recorded.
