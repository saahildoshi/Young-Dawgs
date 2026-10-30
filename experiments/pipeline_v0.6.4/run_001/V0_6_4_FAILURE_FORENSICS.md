# v0.6.4 historical failure forensics

Both v063 failures were independently reconstructed from actual saved inputs,
native solver/monitor files, manifests and receipts. Each input hash agrees
with its original receipt and simulation manifest. Original files are unchanged.
The source/mesh hashes are unchanged; full qualification and import are reused.

Attempt1 completed9 Newton updates, with10 started factorizations and no
converged substep; it was manually stopped for recorded numerical diagnosis
after704.208s. Attempt2 completed14 updates and14 logged pivot summaries,
with no converged substep; it reached1200.102s. Both inherited NSUBST2,20,1,
AUTOTS ON, NEQIT30, full Newton and line search. No bisection was observed
before either termination: neither reached its iteration ceiling.

Requested first strain0.0001 / travel0.001024mm. Initial trial strain0.00005 /
travel0.000512mm is inferred from the inherited stepping prescription, not an
independently recorded historical trial-time/contact history. Actual v063
monitor files contain headers and no completed-substep rows. Source-ordered
force/displacement/line-search/pivot records and printed factorization-note
CPU/wall stamps are retained in historical_failure_forensics/.

Force residuals plateaued/oscillated while displacement convergence often
passed. Printed wall-stamp differences demonstrate expensive iterations;
they are not invented exact iteration timings. No logged negative pivot or
distortion failure was found before stopping, and no RAM-cap failure occurred.

Historical contact activation, transitions, chatter, gap/stiffness changes
and residual-node fields were not recorded. Historical contact causality is
UNRESOLVED. Prospective small and full diagnostics provide new evidence;
they do not retrospectively fill missing histories.
