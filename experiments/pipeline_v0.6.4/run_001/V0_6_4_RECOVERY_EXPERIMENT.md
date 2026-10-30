# v0.6.4 full recovery experiment

**NATIVE_NONZERO_EQUILIBRIUM_RECOVERED__RESOURCE_AND_OUTPUT_QUALIFICATION_HOLD**. One primary full-model retry and one conditional technical
repair executed, each after its input/protocol were committed. User section21
allows this exception for a directly correctable implementation error;
it is not another contact or stiffness search. Final native input SHA256:
d888ed58099f10c1d0f0807d922cc22ec3286e0b3e847072ef986997eec72777.

Original native1024 source/mesh,412pores,PLANE183 TRI6 plane stress,E1000MPa,
nu0.3,t1mm,10.24mm envelope and frictionless separable platen contact retained.
No geometry/mesh changes, no repeated full import and no extra restraints.
Correction: KEYOPT4=2 nodal target-normal detection, with purepenalty1,
fixed KEYOPT10=1,FKN100 and FTOLN−1e−5 retained. NEQIT24 / NSUBST2,20,1 and
twoSMP were verified on the compliant recovery control. Aggressive NEQIT8
failed and was rejected. Two-core capability does not establish total license
entitlement or guarantee full-model speedup.

The primary reached native0.005% after7updates, then hit20.0424GiB during
the next factorization at422.151s. Its nativeRST had no readable data set,
and no restart frame was saved; actual read-only SET1,1 failed. This loss is
preserved. The conditional repair ends at that same known first increment,
with NSUBST1,1,1, OUTRES ALL ALL and a request for one explicit restart frame.
The conditional run stopped before that restart frame was written. A separate
8GiB POST1 process exports fields after solver exit. Small licensed testing
proved these output commands before the amended run.

Primary0.01% target remains unmet. Conditional target0.005% /0.000512mm.
Actual conditional process statusMEMORY_BUDGET_EXCEEDED,
runtime333.559s,
peak sampled RSS21899300864bytes.
Completed Newton updates7;
started factorizations7;
cutbacks0;
best force ratio0.9531140657802659;
last force ratio0.9531140657802659.
Native converged records: [].

The conditional log explicitly declares equilibrium convergence after7updates,
with native force ratio0.9531140657802659. Its ordinary completed-
substep printout is absent because the memory stop occurred during output,
as the resident database grew from2048to4096MB. Read-only SET1,1 recovered
time0.00005 and actual nodal displacements. It did not recover reactions,
contact element results, stress or elastic strain. Ignored GET/VGET requests
left zero/sentinel arrays; these are unavailable data, not physical zeros.
The unchanged scientific gate failed and quarantined them.

Actual displacement-only diagnostics cover2766505nodes;
all deformed TRI6 mappings positive:True.
This is not an accepted mechanical checkpoint. Native CND iteration7 reports
bottom internalFY-0.06074446N and top
internalFY0.06043442N, with pair-force
imbalance0.005104004546258169. That is partial
force-transmission evidence, not an independent support-reaction check.
Primary NLHIST upperRF−0.06043442N is a genuine converged scalar, but the missing
lowerRF/fields prevent full mechanical qualification or stiffness assignment.

Accepted native checkpoints: [].
Accepted endpoint maximum penetration: UNAVAILABLE.
Field and all-element deformed mapping checks: [].
These are actual native results only. Unavailable data remain unavailable.

Single-point preliminary secant modulus: UNAVAILABLE.
Fitted initial modulus: None.
One nonzero accepted point does not establish an initial fitted modulus or a
complete stress–strain curve. The earlier converged substep history is retained
as native history; only checkpoints with complete validation enter mechanics.

The original1200s/20GiB caps,12GiB OS reserve and20GiB disk reserve were not
increased. Diagnostic cap2GiB /4native snapshots;32completed-update cap and
three-cutback cap. Stagnation requires24updates,onecutback and six current-trial
force evaluations; the first large residual cannot trigger it. Complete native
receipts, computed contact histories, residual localization and actual resource
samples are retained. The one conditional repair is the final full-model
attempt; no third run or additional parameter search was launched.
