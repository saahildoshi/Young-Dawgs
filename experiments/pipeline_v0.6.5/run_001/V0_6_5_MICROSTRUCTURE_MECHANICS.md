# v0.6.5 microstructure mechanics

Scientific status: **FIRST_ACCEPTED_NATIVE_CHECKPOINT__PRELIMINARY_SINGLE_MESH_RESEARCH_HOLD**. Accepted checkpoints: 1.
Source `4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1`; mesh `e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc`.
Input `bad607c1d0fee99944fdd77a96331c0fd9271e1b6597f60427c03e9884ce5d13`; native RST `8ad26dd081ae2dd42f7a9d6dcec224a9ca8a08f500823e1adc63ed2db3161d14`.

Actual accepted measurements: [{'compression_displacement_mm': 0.0005120000000000002, 'engineering_compression_strain': 5.0000000000000016e-05, 'lower_rf_y_N': 0.06074445939887244, 'nominal_compression_stress_MPa': 0.005901798352544726, 'pseudo_time': 5e-05, 'reaction_balance_relative': 0.005104074871727321, 'upper_rf_y_N': -0.060434415130058}].
Native signed upper/lower support reactions are independently extracted;
contact sums oppose each support reaction under the unchanged1% limit.
Contact records: [{'closed_elements': 773, 'contact_element_force_y_N': -0.060744459394838, 'max_stored_endpoint_penetration_mm': 5.440885e-10, 'max_stored_endpoint_pressure_MPa': 0.32710794, 'minimum_signed_gap_mm': -7.0687194e-05, 'pair': 'bottom', 'pilot_reaction_y_N': 0.06074445939887244, 'signed_opposition_residual_relative': 6.641658332480353e-11, 'total_elements': 1368}, {'closed_elements': 657, 'contact_element_force_y_N': 0.06043441524864, 'max_stored_endpoint_penetration_mm': 2.830074e-10, 'max_stored_endpoint_pressure_MPa': 0.16914761, 'minimum_signed_gap_mm': -2.4550722e-05, 'pair': 'top', 'pilot_reaction_y_N': -0.060434415130058, 'signed_opposition_residual_relative': 1.9621602206461835e-09, 'total_elements': 1230}].
Maximum stored-endpoint penetration: 5.440885e-10mm;
this does not certify the continuous-contact maximum.

Native field coverage: 2766505nodes,
1261670TRI6, 752212corner field nodes.
All deformed mappings positive: True;
minimum determinant 2.3976378882584983e-06mm².
SYY/SEQV/EPEL Y/X ranges: [[-0.4387852188225906, 0.1866154082759464], [8.419118391648176e-13, 0.4971344469872719], [-0.0003547639109029222, 0.0001283690824192711], [-0.0002274335902292844, 0.0002080286639079577]].
Full native and derived field artifacts remain outside Git, with hashes.
Native displacement is at every node; stress/strain use supported corner-node
averages. Visualization triangle means are rendering, not invented raw data.

Engineering strain is achieved travel/10.24mm. Nominal envelope stress is
compressive upper reaction/(10.24mm×1mm), using totalN forces and1mm thickness.
Single-point secant estimate: 118.03596705089448MPa.
Fitted effective modulus: NOT QUALIFIED. Complete stress–strain curve: NOT
QUALIFIED. Single-mesh refinement, internal self-contact, calibration, yielding,
fracture and manufacturing remain unqualified; prior geometry HOLDs remain.
