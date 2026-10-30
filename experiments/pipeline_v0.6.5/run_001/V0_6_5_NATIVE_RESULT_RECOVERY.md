# v0.6.5 native result recovery

Scientific status: **FIRST_ACCEPTED_NATIVE_CHECKPOINT__PRELIMINARY_SINGLE_MESH_RESEARCH_HOLD**. Accepted checkpoints: 1.
Source `4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1`; mesh `e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc`.
Input `bad607c1d0fee99944fdd77a96331c0fd9271e1b6597f60427c03e9884ce5d13`; native RST `8ad26dd081ae2dd42f7a9d6dcec224a9ca8a08f500823e1adc63ed2db3161d14`.

One preregistered full solve executed, status PROCESS_EXITED, native return
code0. No second full solve or additional strain
checkpoint was executed. Exact original source/mesh and working nodal contact
were retained: PLANE183 plane stress, E1000MPa/nu0.3/t1mm, frictionless separable
CONTA172/TARGE169, KEYOPT2=1/4=2/10=1, FKN100, FTOLN−1e−5.
DEFAULT sparse memory mode is retained without forcing INCORE or OUTOFCORE.

Completed Newton updates 7; bisections
0; last native force ratio
0.9531140657802659. Native RST bytes
679018496. Independent result-set inventory
[['1', '0.50000000E-04', '1', '1', '7']]. MODEL-only database and RST provenance,
source input, logs, CSVs and receipt hashes are independently checked.

Actual runtime 327.063s; peak owned-tree RSS
18.5923GiB; minimum sampled available system RAM
21.9146GiB. No process RSS
cutoff exists. The exact sustained emergency policy,1800s wall limit and20GiB
disk reserve are frozen in FULL_RECOVERY_001.json. Native marker first-observed
times are {'equilibrium': 299.11744090006687, 'model_save': 322.11742080003023, 'result_write_reported': 317.75461190007627, 'solution_finished': 321.0979407001287, 'sparse_factorization': 51.22564920014702, 'substep_completed': 315.53201470011845}; these are sampled bounds,
not exact internal phase times. Raw native solver timing tables are retained.

Independent qualification: All required native fields and mechanical gates passed..
