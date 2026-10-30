# Prospective full-model recovery

The compliant diagnostic fixture reproduced the contact failure: fixed pure
penalty with Gauss detection failed despite cutbacks and smaller increments.
Direct-displacement compression converged, but represents different boundary
conditions. Linearized contact also failed. Native contact files measured
chatter while both pairs retained active elements; strongest residuals were
FY at platen boundaries. Neither global loss of contact support nor geometric
nonlinearity alone explains this small-model failure.

Updating normal stiffness or reducing FKN once did not cure it. These are
negative controls, not evidence that all stiffness effects have been excluded.
One prospectively registered detection change, KEYOPT(4)=2, converged with the
original frictionless separable contact, material, geometry, FKN100 and fixed
stiffness. Force, signed contact-force, penetration and field-inventory gates
passed. The matched rectangle also passed. This supports contact-detection
sensitivity/chattering as a small-model mechanism, not retrospective proof of
an unrecorded historical full-model contact history.

Aggressive NEQIT8 failed even with the accepted detection correction and was
rejected. Exact recovery controls NEQIT24 / NSUBST2,20,1 / two SMP cores passed
the compliant control, including a real cutback and subsequent convergence.
Two-core licensed rectangle execution preserved the response; no inference
about unrestricted processors or guaranteed full-model speedup is made.

FULL_RECOVERY_001.json freezes one full-model recovery input and its hash.
The exact authenticated specimen database is reused without geometry changes,
new specimen restraints, altered friction, stabilization or bonded contact.
One nonzero 0.01% checkpoint is requested. The physical model is unchanged;
contact detection, iteration control and verified processor count are explicit
numerical changes. Full historical causality remains to be tested by this run.

The 1200-second / 20-GiB caps and 12-GiB OS RAM / 20-GiB disk reserves remain.
Two NR / two EFLG ring files, 2-GiB diagnostic cap, actual 1-second resource
samples, 32 completed-update cap and three-cutback cap apply. Stagnation may
stop only after at least 24 updates and one cutback, with six current-trial
force evaluations showing plateau/oscillation/growth. A first large residual
is never sufficient. Native ring overwriting is limited to this new job.

The prior linearized small control suffered a monitor file-rotation race.
Its original LAUNCH_FAILURE receipt is retained and is explicitly operationally
invalid: ANSYS had actually launched and continued. The corrected monitor
tolerates missing rotating files and kills owned processes on any unexpected
monitor exception or cancellation. Its unique repeat was preserved separately.

A parser norm check initially used a tighter tolerance than the native CNVV
header's printed precision. The failed check is preserved; the corrected check
uses half the last printed digit, without changing any mechanical acceptance
criterion. All ten licensed small-evidence checks then passed.

Execution requires the full protocol to be committed first. No second full
trial is authorized by this implementation. Failed numerical data remain
ineligible for performance ranking. One valid point gives at most a preliminary
secant response; mesh convergence and all prior physical/scientific HOLDs remain.

## Evidence correction and final outcome — 2026-10-30

The prospective text above is retained as the original decision record. Its
claim of a "real cutback" in the successful NEQIT24 recovery control was
incorrect. Native records show three converged substeps and **zero bisections**;
automatic increment prediction reduced the next increment after convergence.
True failed-trial bisections were demonstrated by separate failed controls.
`audit/STEP_PREDICTION_CORRECTION_012.json` records this distinction.

The primary full run recovered the first nonzero equilibrium at 0.005% strain
after seven Newton updates. It stopped at the unchanged 20-GiB memory guard
while attempting the next increment; its RST contained no readable data set.
Under the user's section 21 exception, the prospectively committed technical
amendment 009 superseded the original no-second-trial restriction solely to
retain that known checkpoint with explicit output controls. No third full run
was performed or authorized by this milestone.

The conditional repair again announced equilibrium after seven updates, but
hit the memory guard during result writing. Read-only SET recovered the native
0.005% displacement field, with every deformed TRI6 mapping positive. Required
reactions, contact-element results, stress and elastic strain were unavailable;
zero/sentinel exports are quarantined. There are **zero mechanically accepted
checkpoints**, no modulus and no performance score. Native contact-pair forces
are diagnostic evidence, not a substitute for independently verified support
reactions. See the final recovery and validation reports in run_001.
