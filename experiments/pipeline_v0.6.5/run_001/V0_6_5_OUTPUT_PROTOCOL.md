# v0.6.5 verified native output protocol

Scientific status: **FIRST_ACCEPTED_NATIVE_CHECKPOINT__PRELIMINARY_SINGLE_MESH_RESEARCH_HOLD**. Accepted checkpoints: 1.
Source `4700d4581d2f86c19e382eb2406a57f98724e478c3391acc4d3dc0425d4b8dc1`; mesh `e26863263774cf86c777b1485ac0e639216a91644007c4da272469a7447000bc`.
Input `bad607c1d0fee99944fdd77a96331c0fd9271e1b6597f60427c03e9884ce5d13`; native RST `8ad26dd081ae2dd42f7a9d6dcec224a9ca8a08f500823e1adc63ed2db3161d14`.

Selected commands:

```apdl
OUTRES,ERASE
OUTRES,ALL,NONE
OUTRES,NSOL,LAST
OUTRES,RSOL,LAST
OUTRES,STRS,LAST
OUTRES,EPEL,LAST
OUTRES,CONT,LAST
OUTRES,MISC,LAST
OUTPR,ALL,NONE
OSRESULT,ERASE
RESCONTROL,DEFINE,ALL,LAST,1
OUTRES,STAT
RESCONTROL,STATUS
SAVE,checkpoint,db,,MODEL
```

NSOL/RSOL preserve displacement and reactions; STRS/EPEL preserve continuum
stress and elastic strain; CONT/MISC support the required contact queries.
OUTPR suppresses large text listings; OSRESULT ERASE avoids additional selected
result records. This is a verified sufficient subset, not proof of globally
optimal minimum output. BASIC alone was not relied upon. One final restart
frame is requested; the RST is independently verified, not accepted by size.

Actual v241 full/selective rectangle and compliant solves passed. RST sizes:
rectangle524288→458752bytes; compliant3145728→2293760bytes. Fresh read-only
exports from MODEL-only databases recovered every required field. Different
chunk sizes gave identical repeated values. A deliberately omitted EPEL record
was detected and quarantined. Audit002 preserves a first overly strict
comparison assertion and actual tiny full/selective contact differences;
the corrected1e-6 column-scale comparison leaves all physical gates unchanged.

APDL vectors are limited to250000nodes; Python streams100000rows and validates
20000elements at a time with memory-mapped field storage. Stress/strain are
native supported corner-node averages, without invented midside data.
Official adjacent-release references are recorded in RECOVERY_PLAN_001.json;
installed2024R1 behavior is established by actual licensed jobs.
