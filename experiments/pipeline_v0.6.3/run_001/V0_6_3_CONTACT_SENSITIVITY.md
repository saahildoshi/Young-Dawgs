# v0.6.3 bounded contact investigation

All rectangle comparisons retain the v0.6.2 geometry, mesh, material, thickness
and six-stage loading. AL FTOLN=1e-6 and 1e-5 mm passed force/equilibrium and
stored-endpoint penetration checks, removed the original coefficient-ratio
warning, and the selected 1e-5 case repeated identically. This justified a
prospective full-model trial, not automatic microstructure contact acceptance.

The first full-model AL trial had no converged substep and a non-monotone force
residual plateau. It was deliberately stopped for diagnosis, not a memory
failure or measured poor physical design. Contact multiplier/stiffness-update
chatter is a hypothesis, not a proven isolated cause.

A registered pure-penalty/fixed-initial-stiffness correction was tested first
on the rectangle. FKN=1 produced max endpoint penetration 0.00058725016 mm,
failing the unchanged v063 1e-5 mm gate despite passing the older generic
numeric screen. It was rejected. FTOLN did not set pure-penalty stiffness as it
had for AL; actual printed stiffness was inspected rather than assumed.

The observed penetration/gate ratio motivated a prospective 100x FKN test.
It passed the unchanged gate (5.9051026e-6 mm maximum endpoint penetration),
balanced actual contact-element forces/reactions, reproduced history bytes and
passed the matched force screen. Fixed stiffness deliberately retains the
solver recommendation to use KEYOPT(10)=0. This warning is not suppressed or
confused with a coefficient-ratio warning. No formal condition-number bound,
full microstructure sensitivity qualification or causal ablation is claimed.

Only one corrected full-model attempt was registered: pure penalty KEYOPT(2)=1,
KEYOPT(10)=1, FKN=100, FTOLN=-1e-5 mm. Same physical model, acceptance thresholds,
load targets and resource reserves; no geometry, stabilization or bonded-contact
substitution. All failed candidates and the original pilot are preserved.
