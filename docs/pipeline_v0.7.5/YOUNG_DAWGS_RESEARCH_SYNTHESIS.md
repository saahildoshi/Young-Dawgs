# Young Dawgs research synthesis

The project asks whether an LLM can create stochastic microstructures that resemble a reference, predictably change their simulated response, and benefit from measured feedback. These are separate outcomes with different evidence.

**Porous metamaterials.** The early binary generators produced connected solid and void patterns through procedural geometry. Connectivity, pore preservation and mesh checks qualified selected geometries, including Design 009 seed 001 and its central crop. Later licensed contact runs accepted the crop through 1.2575% compression. The 40% coupon result applied to the illustrative homogeneous polymer coupon, and the cropped polymer campaign stopped at contact qualification. [Porous compression record](../pipeline_v0.6.10/V0_6_10_HANDOFF.md).

**Microscopy reconstruction.** P3 is a supplied horizontally flipped SEM tile selected for dispersed irregular inclusions. Its native labels 1 and 5 represent two solids, with provisional chemistry for label 5. F1 uses prepared C/PEEK microscopy and distinguishes matrix 0, transverse fiber cross-sections 1 and void 2. The circular fiber annotations are approximate. Actual ChatGPT scripts were compared across image-only, descriptor-informed and feedback conditions using phase fractions, component geometry, spatial correlations and other family-specific descriptors. Seeds are nested within scripts. Microscopy calibration is unknown. [Reference provenance](../pipeline_v0.7.0/reference_correction_001/V0_7_0_REFERENCE_CORRECTION.md).

**Mechanical reconstruction.** v0.7.1 measured five actual ANSYS strain checkpoints from 0.1% to 0.5%. The P3 reference and selected generated B02 specimen had H1 apparent moduli 1693.2886 and 1691.4055 MPa. Mesh sensitivity limits interpretation of close values. [P3 native curves and moduli](../pipeline_v0.7.1/V0_7_1_P3_MECHANICAL_RESULTS.md).

**Stiffness optimization and morphology drift.** v0.7.2 revisions gained about 94–106% apparent stiffness by placing reinforcement in segmented vertical lanes. The original envelope admitted these shapes. Mean gains were 98.821% with measurements and 101.673% in the control. v0.7.3 added area-weighted shape tails, orientation, occupancy and near-spanning checks that flagged all 40 historical lane realizations. Controlled development means ranged from 1636.446 to 1753.014 MPa. The registered difficulty rule rejected its proposed target, so that study stopped before LLM revisions. [v0.7.2 results](../pipeline_v0.7.2/V0_7_2_HANDOFF.md) · [v0.7.3 development evidence](../pipeline_v0.7.3/V0_7_3_HANDOFF.md).

**Target matching.** v0.7.4 froze 1640 MPa and evaluated eight genuine same-conversation initial/revision pairs. All 94 generated fields met exact composition and the frozen morphology limits, with two bounded construction failures retained. The stricter envelope preserved dispersed geometries while finite metrics still allowed narrower size distributions or more even spacing than the reference.

| v0.7.4 arm | Initial mean error | Revised mean error | Improvement, pp |
|---|---:|---:|---:|
| IF | 0.6920% | 0.4296% | 0.2623 |
| NF | 1.3743% | 1.2754% | 0.0990 |

IF began closer to target. Excluding NF_01, which had an additional nonscientific turn, changed the IF-minus-NF improvement contrast to -0.5254 percentage points. The pilot left the feedback-specific advantage unresolved. [v0.7.4 pilot](../pipeline_v0.7.4/V0_7_4_P3_INVERSE_DESIGN_RESULTS.md).

**Cross-family mechanics.** F1 native reference/generated H1 moduli were 2230.4453/2147.6014 MPa and H2 moduli were 2158.1510/2093.0766 MPa. Explicit void geometry omits continuum elements and the void-strip control passed. The two mesh levels changed the values by 2.54–3.24%. [F1 benchmark](../pipeline_v0.7.4/V0_7_4_F1_MECHANICAL_RESULTS.md).

**Interpretation.** Reference geometry resemblance, simulated response resemblance, stiffness improvement, target matching and feedback efficacy require different comparisons. Both composite families use illustrative isotropic moduli, ideal bonded interfaces, pixel boundaries and finite-domain plane stress. The microscopy dimensions, constituent response, anisotropic fiber law, RVE qualification and damage behavior remain unverified. Independent trial counts and possible account context and backend variation constrain the inference.

**v0.7.5 replication.** The registered design pairs twelve initial scripts after development measurement and randomizes feedback within each pair. Matched assignment and the feedback comparison remain pending in this historical synthesis. See the versioned trial evidence and analysis for any later measured outcomes.
