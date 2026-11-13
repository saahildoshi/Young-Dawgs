# P3 + F1 real microscopy LLM pilot

Actual independently returned initial scripts: **10**; paired feedback revisions: **1**. Submission events: 12. Prepared initial packets: 12; unexecuted packets are not trials.

| Script | Revision | Seeds | Valid / requested | Failures | Visible error | Hidden error | Hamming diversity |
|---|---:|---|---:|---:|---:|---:|---:|
| F1_A_01 | 0 | dev | 10/10 | 0 | 0.3322 | 0.2804 | 0.5009 |
| F1_A_02 | 0 | dev | 10/10 | 0 | 0.1996 | 0.2488 | 0.5141 |
| F1_B_01 | 0 | dev | 10/10 | 0 | 0.3239 | 0.2183 | 0.5162 |
| F1_B_02 | 0 | dev | 10/10 | 0 | 0.03205 | 0.1056 | 0.5139 |
| F1_C_01 | 0 | dev | 10/10 | 0 | 0.01807 | 0.1748 | 0.5141 |
| P3_A_01 | 0 | dev | 10/10 | 0 | 0.1466 | 0.101 | 0.4168 |
| P3_A_02 | 0 | dev | 10/10 | 0 | 0.1902 | 0.08583 | 0.4156 |
| P3_B_01 | 0 | dev | 10/10 | 0 | 0.04088 | 0.08736 | 0.3941 |
| P3_B_02 | 0 | dev | 10/10 | 0 | 0.01202 | 0.07537 | 0.4246 |
| P3_C_01 | 0 | dev | 10/10 | 0 | 0.01544 | 0.1013 | 0.4297 |
| P3_C_01 | 1 | dev | 10/10 | 0 | 0.01518 | 0.1081 | 0.4233 |

Errors are absolute descriptor differences divided by prospectively fixed scales, averaged equally within each group; lower is closer, not percentage accuracy. A script mean is NA unless every requested output has a complete group score. Validity and execution failures remain separate. Hamming distance measures variation among nested seeds, not reference accuracy.

## Descriptive condition comparison

| Family | Condition/revision | Partition | Parent scripts | Valid/requested | Visible error | Hidden error | Hamming diversity |
|---|---|---|---:|---:|---:|---:|---:|
| F1 | A/r0 | dev | 2 | 20/20 | 0.2659 | 0.2646 | 0.5075 |
| F1 | B/r0 | dev | 2 | 20/20 | 0.178 | 0.162 | 0.5151 |
| F1 | C/r0 | dev | 1 | 10/10 | 0.01807 | 0.1748 | 0.5141 |
| P3 | A/r0 | dev | 2 | 20/20 | 0.1684 | 0.0934 | 0.4162 |
| P3 | B/r0 | dev | 2 | 20/20 | 0.02645 | 0.08136 | 0.4093 |
| P3 | C/r0 | dev | 1 | 10/10 | 0.01544 | 0.1013 | 0.4297 |
| P3 | C/r1 | dev | 1 | 10/10 | 0.01518 | 0.1081 | 0.4233 |

Condition values average script means equally. C/r0 and C/r1 share the same parent trials; they cannot be added as independent samples. Any missing script score makes its condition score unavailable. JSON tables retain scoring coverage and descriptive between-script SD; this small pilot does not support significance claims.

| Paired parent | Partition | Valid before/after | Visible error change | Hidden error change | Diversity change |
|---|---|---:|---:|---:|---:|
| P3_C_01 | dev | 10/10 | -0.0002628 | 0.006885 | -0.006406 |

Changes are revised minus initial script means. Negative error change is closer agreement; diversity change has no reference-accuracy interpretation.

## P3 descriptor comparison

| Script/revision/partition | Descriptor | Target | Generated seed mean ± SD | Available outputs |
|---|---|---:|---:|---:|
| P3_A_01/r0/dev | reinforcement_fraction (visible) | 0.3163 | 0.2947 ± 0.0148 | 10/10 |
| P3_A_01/r0/dev | complete_regions (visible) | 57 | 40.2 ± 4.142 | 10/10 |
| P3_A_01/r0/dev | diameter_mean_px (visible) | 15.71 | 17.04 ± 0.8624 | 10/10 |
| P3_A_01/r0/dev | diameter_std_px (visible) | 8.893 | 11.05 ± 1.366 | 10/10 |
| P3_A_01/r0/dev | aspect_mean (visible) | 1.916 | 1.736 ± 0.0815 | 10/10 |
| P3_A_01/r0/dev | nearest_neighbor_mean_px (hidden) | 19.45 | 23.11 ± 1.614 | 10/10 |
| P3_A_01/r0/dev | nearest_neighbor_cv (hidden) | 0.487 | 0.3515 ± 0.07651 | 10/10 |
| P3_A_01/r0/dev | interface_density (hidden) | 0.1126 | 0.08701 ± 0.004858 | 10/10 |
| P3_A_01/r0/dev | S2_x_8 (hidden) | 0.1624 | 0.1633 ± 0.00765 | 10/10 |
| P3_A_01/r0/dev | S2_y_8 (hidden) | 0.1529 | 0.1629 ± 0.0103 | 10/10 |
| P3_A_01/r0/dev | matrix_lcc (hidden) | 0.9906 | 0.9895 ± 0.01127 | 10/10 |
| P3_A_02/r0/dev | reinforcement_fraction (visible) | 0.3163 | 0.2987 ± 0.01546 | 10/10 |
| P3_A_02/r0/dev | complete_regions (visible) | 57 | 84.5 ± 4.717 | 10/10 |
| P3_A_02/r0/dev | diameter_mean_px (visible) | 15.71 | 10.4 ± 0.6976 | 10/10 |
| P3_A_02/r0/dev | diameter_std_px (visible) | 8.893 | 9.501 ± 0.8938 | 10/10 |
| P3_A_02/r0/dev | aspect_mean (visible) | 1.916 | 1.832 ± 0.1011 | 10/10 |
| P3_A_02/r0/dev | nearest_neighbor_mean_px (hidden) | 19.45 | 15.05 ± 1.317 | 10/10 |
| P3_A_02/r0/dev | nearest_neighbor_cv (hidden) | 0.487 | 0.5443 ± 0.0585 | 10/10 |
| P3_A_02/r0/dev | interface_density (hidden) | 0.1126 | 0.1209 ± 0.00567 | 10/10 |
| P3_A_02/r0/dev | S2_x_8 (hidden) | 0.1624 | 0.146 ± 0.01084 | 10/10 |
| P3_A_02/r0/dev | S2_y_8 (hidden) | 0.1529 | 0.1438 ± 0.01181 | 10/10 |
| P3_A_02/r0/dev | matrix_lcc (hidden) | 0.9906 | 0.9931 ± 0.006897 | 10/10 |
| P3_B_01/r0/dev | reinforcement_fraction (visible) | 0.3163 | 0.287 ± 0.007229 | 10/10 |
| P3_B_01/r0/dev | complete_regions (visible) | 57 | 57 ± 0 | 10/10 |
| P3_B_01/r0/dev | diameter_mean_px (visible) | 15.71 | 15.7 ± 0.01326 | 10/10 |
| P3_B_01/r0/dev | diameter_std_px (visible) | 8.893 | 8.873 ± 0.04451 | 10/10 |
| P3_B_01/r0/dev | aspect_mean (visible) | 1.916 | 1.951 ± 0.08883 | 10/10 |
| P3_B_01/r0/dev | nearest_neighbor_mean_px (hidden) | 19.45 | 21.54 ± 0.6951 | 10/10 |
| P3_B_01/r0/dev | nearest_neighbor_cv (hidden) | 0.487 | 0.3317 ± 0.02725 | 10/10 |
| P3_B_01/r0/dev | interface_density (hidden) | 0.1126 | 0.09942 ± 0.001245 | 10/10 |
| P3_B_01/r0/dev | S2_x_8 (hidden) | 0.1624 | 0.1445 ± 0.007143 | 10/10 |
| P3_B_01/r0/dev | S2_y_8 (hidden) | 0.1529 | 0.1425 ± 0.006711 | 10/10 |
| P3_B_01/r0/dev | matrix_lcc (hidden) | 0.9906 | 0.9994 ± 0.0007057 | 10/10 |
| P3_B_02/r0/dev | reinforcement_fraction (visible) | 0.3163 | 0.3162 ± 0.0006491 | 10/10 |
| P3_B_02/r0/dev | complete_regions (visible) | 57 | 57 ± 0 | 10/10 |
| P3_B_02/r0/dev | diameter_mean_px (visible) | 15.71 | 15.69 ± 0.01084 | 10/10 |
| P3_B_02/r0/dev | diameter_std_px (visible) | 8.893 | 8.901 ± 0.01371 | 10/10 |
| P3_B_02/r0/dev | aspect_mean (visible) | 1.916 | 1.985 ± 0.06485 | 10/10 |
| P3_B_02/r0/dev | nearest_neighbor_mean_px (hidden) | 19.45 | 20.43 ± 0.717 | 10/10 |
| P3_B_02/r0/dev | nearest_neighbor_cv (hidden) | 0.487 | 0.3216 ± 0.05668 | 10/10 |
| P3_B_02/r0/dev | interface_density (hidden) | 0.1126 | 0.0964 ± 0.00183 | 10/10 |
| P3_B_02/r0/dev | S2_x_8 (hidden) | 0.1624 | 0.1671 ± 0.002483 | 10/10 |
| P3_B_02/r0/dev | S2_y_8 (hidden) | 0.1529 | 0.1658 ± 0.005394 | 10/10 |
| P3_B_02/r0/dev | matrix_lcc (hidden) | 0.9906 | 0.9994 ± 0.0006211 | 10/10 |
| P3_C_01/r0/dev | reinforcement_fraction (visible) | 0.3163 | 0.3161 ± 0.0006016 | 10/10 |
| P3_C_01/r0/dev | complete_regions (visible) | 57 | 57 ± 0 | 10/10 |
| P3_C_01/r0/dev | diameter_mean_px (visible) | 15.71 | 15.65 ± 0.09898 | 10/10 |
| P3_C_01/r0/dev | diameter_std_px (visible) | 8.893 | 8.632 ± 0.4879 | 10/10 |
| P3_C_01/r0/dev | aspect_mean (visible) | 1.916 | 1.956 ± 0.08625 | 10/10 |
| P3_C_01/r0/dev | nearest_neighbor_mean_px (hidden) | 19.45 | 20.85 ± 0.6997 | 10/10 |
| P3_C_01/r0/dev | nearest_neighbor_cv (hidden) | 0.487 | 0.2982 ± 0.03119 | 10/10 |
| P3_C_01/r0/dev | interface_density (hidden) | 0.1126 | 0.08643 ± 0.002178 | 10/10 |
| P3_C_01/r0/dev | S2_x_8 (hidden) | 0.1624 | 0.1716 ± 0.008198 | 10/10 |
| P3_C_01/r0/dev | S2_y_8 (hidden) | 0.1529 | 0.1701 ± 0.00462 | 10/10 |
| P3_C_01/r0/dev | matrix_lcc (hidden) | 0.9906 | 0.9994 ± 0.0007804 | 10/10 |
| P3_C_01/r1/dev | reinforcement_fraction (visible) | 0.3163 | 0.3165 ± 0.0004481 | 10/10 |
| P3_C_01/r1/dev | complete_regions (visible) | 57 | 57 ± 0 | 10/10 |
| P3_C_01/r1/dev | diameter_mean_px (visible) | 15.71 | 15.7 ± 0.1122 | 10/10 |
| P3_C_01/r1/dev | diameter_std_px (visible) | 8.893 | 8.895 ± 0.5321 | 10/10 |
| P3_C_01/r1/dev | aspect_mean (visible) | 1.916 | 1.902 ± 0.07396 | 10/10 |
| P3_C_01/r1/dev | nearest_neighbor_mean_px (hidden) | 19.45 | 21.11 ± 1.141 | 10/10 |
| P3_C_01/r1/dev | nearest_neighbor_cv (hidden) | 0.487 | 0.3073 ± 0.05281 | 10/10 |
| P3_C_01/r1/dev | interface_density (hidden) | 0.1126 | 0.08508 ± 0.002273 | 10/10 |
| P3_C_01/r1/dev | S2_x_8 (hidden) | 0.1624 | 0.1744 ± 0.005294 | 10/10 |
| P3_C_01/r1/dev | S2_y_8 (hidden) | 0.1529 | 0.1724 ± 0.003065 | 10/10 |
| P3_C_01/r1/dev | matrix_lcc (hidden) | 0.9906 | 0.9997 ± 0.000589 | 10/10 |

## F1 descriptor comparison

| Script/revision/partition | Descriptor | Target | Generated seed mean ± SD | Available outputs |
|---|---|---:|---:|---:|
| F1_A_01/r0/dev | fiber_fraction (visible) | 0.4527 | 0.3993 ± 0.008657 | 10/10 |
| F1_A_01/r0/dev | void_fraction (visible) | 0.01958 | 0.01846 ± 0.003234 | 10/10 |
| F1_A_01/r0/dev | complete_fiber_regions (visible) | 464 | 923.9 ± 18.05 | 10/10 |
| F1_A_01/r0/dev | fiber_diameter_mean_px (visible) | 7.905 | 5.495 ± 0.0591 | 10/10 |
| F1_A_01/r0/dev | fiber_diameter_std_px (visible) | 2.812 | 1.783 ± 0.1494 | 10/10 |
| F1_A_01/r0/dev | fiber_nearest_neighbor_mean_px (hidden) | 8.346 | 6.389 ± 0.03829 | 10/10 |
| F1_A_01/r0/dev | fiber_S2_x_8 (hidden) | 0.2296 | 0.1747 ± 0.007642 | 10/10 |
| F1_A_01/r0/dev | fiber_S2_y_8 (hidden) | 0.2138 | 0.1739 ± 0.007378 | 10/10 |
| F1_A_01/r0/dev | matrix_fiber_interface (hidden) | 0.3951 | 0.3858 ± 0.007371 | 10/10 |
| F1_A_01/r0/dev | matrix_lcc (hidden) | 0.93 | 0.9903 ± 0.002446 | 10/10 |
| F1_A_01/r0/dev | void_regions (hidden) | 4 | 10.3 ± 2.147 | 10/10 |
| F1_A_01/r0/dev | void_diameter_mean_px (hidden) | 21.9 | 10.17 ± 1.675 | 10/10 |
| F1_A_01/r0/dev | void_S2_x_8 (hidden) | 0.01148 | 0.007513 ± 0.002005 | 10/10 |
| F1_A_02/r0/dev | fiber_fraction (visible) | 0.4527 | 0.4386 ± 0.006844 | 10/10 |
| F1_A_02/r0/dev | void_fraction (visible) | 0.01958 | 0.02039 ± 0.00558 | 10/10 |
| F1_A_02/r0/dev | complete_fiber_regions (visible) | 464 | 745.9 ± 19.32 | 10/10 |
| F1_A_02/r0/dev | fiber_diameter_mean_px (visible) | 7.905 | 6.238 ± 0.06083 | 10/10 |
| F1_A_02/r0/dev | fiber_diameter_std_px (visible) | 2.812 | 2.324 ± 0.1229 | 10/10 |
| F1_A_02/r0/dev | fiber_nearest_neighbor_mean_px (hidden) | 8.346 | 6.809 ± 0.05519 | 10/10 |
| F1_A_02/r0/dev | fiber_S2_x_8 (hidden) | 0.2296 | 0.2066 ± 0.006298 | 10/10 |
| F1_A_02/r0/dev | fiber_S2_y_8 (hidden) | 0.2138 | 0.2058 ± 0.006585 | 10/10 |
| F1_A_02/r0/dev | matrix_fiber_interface (hidden) | 0.3951 | 0.3971 ± 0.005183 | 10/10 |
| F1_A_02/r0/dev | matrix_lcc (hidden) | 0.93 | 0.9783 ± 0.01016 | 10/10 |
| F1_A_02/r0/dev | void_regions (hidden) | 4 | 11.6 ± 3.441 | 10/10 |
| F1_A_02/r0/dev | void_diameter_mean_px (hidden) | 21.9 | 9.139 ± 2.549 | 10/10 |
| F1_A_02/r0/dev | void_S2_x_8 (hidden) | 0.01148 | 0.01069 ± 0.003731 | 10/10 |
| F1_B_01/r0/dev | fiber_fraction (visible) | 0.4527 | 0.4529 ± 0.0001593 | 10/10 |
| F1_B_01/r0/dev | void_fraction (visible) | 0.01958 | 0.01958 ± 0 | 10/10 |
| F1_B_01/r0/dev | complete_fiber_regions (visible) | 464 | 159.3 ± 11.32 | 10/10 |
| F1_B_01/r0/dev | fiber_diameter_mean_px (visible) | 7.905 | 10.98 ± 0.2024 | 10/10 |
| F1_B_01/r0/dev | fiber_diameter_std_px (visible) | 2.812 | 6.403 ± 0.4668 | 10/10 |
| F1_B_01/r0/dev | fiber_nearest_neighbor_mean_px (hidden) | 8.346 | 12.46 ± 0.4146 | 10/10 |
| F1_B_01/r0/dev | fiber_S2_x_8 (hidden) | 0.2296 | 0.2089 ± 0.004351 | 10/10 |
| F1_B_01/r0/dev | fiber_S2_y_8 (hidden) | 0.2138 | 0.2113 ± 0.004322 | 10/10 |
| F1_B_01/r0/dev | matrix_fiber_interface (hidden) | 0.3951 | 0.2533 ± 0.006774 | 10/10 |
| F1_B_01/r0/dev | matrix_lcc (hidden) | 0.93 | 0.957 ± 0.01212 | 10/10 |
| F1_B_01/r0/dev | void_regions (hidden) | 4 | 6 ± 0 | 10/10 |
| F1_B_01/r0/dev | void_diameter_mean_px (hidden) | 21.9 | 15.94 ± 0.9728 | 10/10 |
| F1_B_01/r0/dev | void_S2_x_8 (hidden) | 0.01148 | 0.009429 ± 0.0008175 | 10/10 |
| F1_B_02/r0/dev | fiber_fraction (visible) | 0.4527 | 0.4503 ± 0.005837 | 10/10 |
| F1_B_02/r0/dev | void_fraction (visible) | 0.01958 | 0.01854 ± 0.003588 | 10/10 |
| F1_B_02/r0/dev | complete_fiber_regions (visible) | 464 | 475 ± 19.09 | 10/10 |
| F1_B_02/r0/dev | fiber_diameter_mean_px (visible) | 7.905 | 7.902 ± 0.0842 | 10/10 |
| F1_B_02/r0/dev | fiber_diameter_std_px (visible) | 2.812 | 2.805 ± 0.1927 | 10/10 |
| F1_B_02/r0/dev | fiber_nearest_neighbor_mean_px (hidden) | 8.346 | 8.513 ± 0.08785 | 10/10 |
| F1_B_02/r0/dev | fiber_S2_x_8 (hidden) | 0.2296 | 0.2133 ± 0.006397 | 10/10 |
| F1_B_02/r0/dev | fiber_S2_y_8 (hidden) | 0.2138 | 0.2124 ± 0.004388 | 10/10 |
| F1_B_02/r0/dev | matrix_fiber_interface (hidden) | 0.3951 | 0.3305 ± 0.005095 | 10/10 |
| F1_B_02/r0/dev | matrix_lcc (hidden) | 0.93 | 0.9874 ± 0.002568 | 10/10 |
| F1_B_02/r0/dev | void_regions (hidden) | 4 | 4 ± 0.6325 | 10/10 |
| F1_B_02/r0/dev | void_diameter_mean_px (hidden) | 21.9 | 20.28 ± 3.187 | 10/10 |
| F1_B_02/r0/dev | void_S2_x_8 (hidden) | 0.01148 | 0.009895 ± 0.002932 | 10/10 |
| F1_C_01/r0/dev | fiber_fraction (visible) | 0.4527 | 0.4528 ± 0.003842 | 10/10 |
| F1_C_01/r0/dev | void_fraction (visible) | 0.01958 | 0.01916 ± 0.00128 | 10/10 |
| F1_C_01/r0/dev | complete_fiber_regions (visible) | 464 | 475.7 ± 9.403 | 10/10 |
| F1_C_01/r0/dev | fiber_diameter_mean_px (visible) | 7.905 | 7.797 ± 0.0715 | 10/10 |
| F1_C_01/r0/dev | fiber_diameter_std_px (visible) | 2.812 | 2.864 ± 0.06057 | 10/10 |
| F1_C_01/r0/dev | fiber_nearest_neighbor_mean_px (hidden) | 8.346 | 8.67 ± 0.095 | 10/10 |
| F1_C_01/r0/dev | fiber_S2_x_8 (hidden) | 0.2296 | 0.2104 ± 0.005517 | 10/10 |
| F1_C_01/r0/dev | fiber_S2_y_8 (hidden) | 0.2138 | 0.2111 ± 0.004072 | 10/10 |
| F1_C_01/r0/dev | matrix_fiber_interface (hidden) | 0.3951 | 0.3133 ± 0.00502 | 10/10 |
| F1_C_01/r0/dev | matrix_lcc (hidden) | 0.93 | 0.9816 ± 0.007317 | 10/10 |
| F1_C_01/r0/dev | void_regions (hidden) | 4 | 6.2 ± 0.8718 | 10/10 |
| F1_C_01/r0/dev | void_diameter_mean_px (hidden) | 21.9 | 12.71 ± 3.325 | 10/10 |
| F1_C_01/r0/dev | void_S2_x_8 (hidden) | 0.01148 | 0.009621 ± 0.001343 | 10/10 |

## Figures and interpretation

![P3_dev_REFERENCE_GENERATED.png](../../../experiments/pipeline_v0.7.0/run_002_real_microscopy/analysis/P3_dev_REFERENCE_GENERATED.png)

![F1_dev_REFERENCE_GENERATED.png](../../../experiments/pipeline_v0.7.0/run_002_real_microscopy/analysis/F1_dev_REFERENCE_GENERATED.png)

Each figure shows the fixed first seed of its partition (development100 or heldout0), chosen prospectively rather than for appearance. The original microscopy image is the model input; phase-colored target panels are evaluator-only. Generated panels come from captured ChatGPT scripts, without researcher repairs.

The small pilot supports descriptive comparisons between independent scripts on two selected fields. Seeds are nested, not independent LLM trials. Condition C receives extra interaction; there is no equal-attempt control for a causal feedback-only claim. Fresh initial ordinary chats were used, but account personalization, memory, connected context and hidden model routing are not controlled; the home screen surfaced project-related suggestions. Only ChatGPT and High effort are exposed; exact backend/version, tokens and cost are unavailable.

Source review found explicit boundary-area allocation in P3_B_01 and P3_B_02, separating border-clipped annotations from complete-region counts. F1_B_01, F1_B_02 and F1_C_01 internally select among multiple stochastic candidates using supplied descriptors. These model-authored behaviors remain unedited. Close supplied-descriptor agreement can reflect fitting the measurement definitions; it does not establish physical fidelity. Internal candidates are nested within one script, and computational effort is not matched across scripts.

P3 is a morphology-selected, horizontally flipped SEM augmentation. Native IDs1/5 are retained; label5 is only provisionally reprecipitated carbide. This is not an unbiased RVE or fully verified chemical map. F1 is original C/PEEK transverse microscopy with distinct matrix0/fiber1/void2; mean-radius circle and void-threshold annotation uncertainty limits region geometry and physical instance interpretation. Both targets lack physical pixel calibration. No mechanical properties, ANSYS results, cross-material generalization, p-values or optimization claims are inferred. Heldout results remain locked until all scripts/revisions are frozen.
