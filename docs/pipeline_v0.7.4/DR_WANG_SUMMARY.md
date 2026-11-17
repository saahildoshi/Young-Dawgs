# Research summary for Dr. Wang

The project has demonstrated genuine LLM generation of multiple microscopy-based microstructure families and actual ANSYS stress–strain evaluation of P3 composites. Earlier stiffness maximization produced large gains through artificial reinforcement lanes, motivating stronger shape, orientation and spatial constraints.

This pilot prescribed a 1640 MPa apparent-modulus target. Eight ordinary-ChatGPT conversations each produced an initial generator and one revision in that same conversation. Four received measured mechanical feedback (IF); four received structural information without measured mechanics (NF). All sixteen scripts froze before six new seeds per script were evaluated.

| Arm | Independent conversations | Initial mean script error | Revised mean script error | Mean within-conversation reduction (pp) |
|---|---:|---:|---:|---:|
| IF | 4 | 0.6920% | 0.4296% | 0.2623 |
| NF | 4 | 1.3743% | 1.2754% | 0.0990 |

Of 96 held-out attempts, 94 produced exact-composition, morphology-feasible fields and actual five-checkpoint ANSYS curves with independent readback. Two bounded generator failures were retained. All eight revised scripts passed six-of-six structural checks. 31 preselected H2 refinements passed, with a maximum observed modulus change of 0.5691%; these are sensitivity checks, not full convergence.

The lower revised IF error is descriptive. IF began closer to target, and excluding NF_01 reverses which arm improved more. That conversation had an extra nonscientific URL turn, although every conversation had only one scientific revision. Shared account/project context was not isolated. Four conversations per arm cannot establish a general feedback advantage. Initial IF outputs already all met the ±2% band; the measured improvement concerns precision within that band.

For F1, a distinct transverse matrix/fiber/void reference and an authenticated LLM-generated field were solved with void regions omitted from the mesh. Reference/generated apparent moduli were 2230.45/2147.60 MPa at H1 and 2158.15/2093.08 MPa at H2. Approximate circular fiber annotations and illustrative isotropic properties limit interpretation.

An enlarged P3 relief and a historical porous through-hole model passed mesh re-import and actual generic slicer checks. They are educational extrusions of 2D geometry; neither is a measured 3D reconstruction or a completed physical print.

P3 remains one morphology-selected, horizontally flipped SEM crop with provisional phase-5 chemistry. Microscopy scale and material properties are not experimentally calibrated; no RVE or physical predictive claim follows. Earlier external raw ANSYS folders are currently missing. Their committed results, curves and prior checks remain intact; the new held-out raw evidence was directly verified. Full results, failure denominators and this preservation limitation accompany the figures.
