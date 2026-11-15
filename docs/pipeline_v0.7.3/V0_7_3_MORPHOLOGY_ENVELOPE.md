# Prospective P3-like morphology envelope

All12 exact baseline calibration outputs and the authenticated target pass. Known lane challenge detection is shown below; it is design-set performance, not blind validation. Historical v0.7.2 acceptance is unchanged.

| Historical cohort | Detected by new rules | Total |
|---|---:|---:|
| BASE | 0 | 10 |
| P3_OPT_MF_01 | 10 | 10 |
| P3_OPT_MF_02 | 10 | 10 |
| P3_OPT_NF_01 | 10 | 10 |
| P3_OPT_NF_02 | 10 | 10 |

| New hard descriptor | Lower | Upper |
|---|---:|---:|
| all_observed.area_weighted_aspect | 1 | 2.59 |
| all_observed.area_weighted_aspect_p95 | 1 | 6.13 |
| all_observed.area_fraction_aspect_gt3 | 0 | 0.27 |
| all_observed.area_fraction_aspect_gt4 | 0 | 0.16 |
| all_observed.defined_aspect_area_fraction | 0.995 | 1 |
| all_observed.axial_order | 0 | 0.59 |
| long_range_abs_S2_difference | 0 | 0.04 |
| limited_gap_run_x | 0 | 0.6 |
| limited_gap_run_y | 0 | 0.56 |
| gap_dilation.2.largest_fraction | 0 | 0.59 |
| nearest_neighbor_cv | 0.1 | 0.69 |
| strips.1.column_std | 0 | 0.18 |
| strips.1.column_max | 0 | 0.79 |
| strips.1.row_std | 0 | 0.2 |
| strips.1.row_max | 0 | 0.78 |
| strips.8.column_std | 0 | 0.17 |
| strips.8.column_max | 0 | 0.74 |
| strips.8.row_std | 0 | 0.19 |
| strips.8.row_max | 0 | 0.75 |
| strips.16.column_std | 0 | 0.16 |
| strips.16.column_max | 0 | 0.71 |
| strips.16.row_std | 0 | 0.17 |
| strips.16.row_max | 0 | 0.69 |
| strips.32.column_std | 0 | 0.14 |
| strips.32.column_max | 0 | 0.64 |
| strips.32.row_std | 0 | 0.16 |
| strips.32.row_max | 0 | 0.63 |

No x/y spanning after2px disk dilation; this detects near organization and does not alter the specimen or establish physical bonding. Inherited phase/topology/population rules remain, with composition tolerance replaced by exact count. Shape statistics cover all observed regions; complete-region statistics remain separately available. Axial orientation weights use area×eigenvalue anisotropy, suppressing nearly circular axes. Correlations and strip windows use finite support with no wrapping. Threshold margins permit moderate shape/orientation/dispersion changes and are empirical P3-family choices, not universal material bounds. Full limits and algorithms are in FEASIBILITY_FROZEN.json and the descriptor source. Independent digital fixtures test circles, orthogonal/balanced ellipses, large shape tails, segmented lanes, gaps, censoring, occupancy, clustering, rotation/reflection and undefined metrics. Passing this envelope cannot establish full natural-material identity.
