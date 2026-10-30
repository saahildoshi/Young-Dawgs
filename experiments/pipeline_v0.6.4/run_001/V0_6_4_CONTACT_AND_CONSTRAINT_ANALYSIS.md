# v0.6.4 contact and constraint analysis

| Hypothesis | Mechanism | Evidence | Certainty |
|---|---|---|---|
| A | Contact chattering | Measured in synthetic and prospective full CND; historical v063 iteration contact file absent. Changing detection enabled the small control and not an accepted full checkpoint. | SUPPORTED_DETECTION_SENSITIVITY; exclusive microscopic cause not proven |
| B | Inadequate initial contact constraint | Both prospective full pairs retain active elements in recorded CND; no observed total support loss. Initial closure alone was never used as proof. | GLOBAL_PAIR_LOSS_NOT_OBSERVED; unrecorded historical states unresolved |
| C | Flexible structural modes | No negative pivots reported; residual snapshots localize actual nodes, not eigenmodes. Direct synthetic model converges with changed boundary conditions. | FULL_FLEXIBLE_MODES_NOT_EIGENQUALIFIED |
| D | Excessive/inappropriate stiffness | Printed native stiffness inspected. Updating PP100 and reducing fixed FKN to1 did not cure synthetic failure; correction retainsFKN100. No formal condition number measured. | STIFFNESS_ALONE_NOT_SUFFICIENT_EXPLANATION |
| E | Load increments | Gauss contact failed across real cutbacks and smaller initial increments. Aggressive NEQIT8 also prevented corrected fixture convergence; exact24 control passed with automatic increment prediction. | STEP_SIZE_ALONE_NOT_A_CURE |
| F | Geometric nonlinearity | Linearized synthetic contact also failed; direct nonlinear fixture converged. Full NLGEOM retainedON. | NLGEOM_ALONE_CONTRADICTED_IN_FIXTURE |
| G | Boundary implementation | Analytical distributed closed-contact rigid-motion rank3; no extra specimen restraints introduced; actual corrected inventory verifies supports. | INTENDED_CONSTRAINTS_VERIFIED; contact state still necessary |
| H | Resource-limited progress | Historical9/14 completedupdates with approximately minute-scale note intervals. Full sampled runtime and memory retained; twoSMP actual capability verified, no guaranteed speedup claim. | HISTORICAL_ITERATION_COST_SUPPORTED; not RAM exhaustion |

The deterministic synthetic fixture has two0.12mm zigzag bending struts and
separate caps. It is explicitly different from Design9. Direct imposed-face
compression changes boundary conditions and cannot be treated as an equivalent
frictionless separable-contact physical reference. Its convergence does not
prove full-domain stiffness or eliminate every compliant mode.

The Gauss PP100 fixture measured chatter15/12 with both pairs still active;
peak residuals were FY at contact boundaries. Update100 and fixedFKN1 did not
cure it. Nodal target-normal detection alone enabled a valid checkpoint with
unchanged physical assumptions and unchanged penetration/equilibrium gates.
Some native chatter remains even in converged runs; zero chatter was never
an acceptance prerequisite. This is evidence of detection sensitivity, not
proof of a unique microscopic explanation or a universal contact policy.

There are no new specimen UY restraints, arbitrary springs, stabilization,
bonded/no-separation replacements, friction changes or internal self-contact.
Analytical rank3 concerns planar rigid motions under distributed active
normal constraints, not an unrestricted full FE eigenanalysis. If both pairs
opened, the lone UX anchor would not suppress all rigid modes. Flexible
full-domain modes are not independently eigenqualified.

[CONTA172 detection and real constants](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_CONTA172.html)
is an adjacent-release reference; actual v241 listings corroborate the applied
options. FTOLN−1e−5 is the absolute penetration tolerance; it is not a prescribed
pure-penalty stiffness. Native computed stiffness was inspected directly.
