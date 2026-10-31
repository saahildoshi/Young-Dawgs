# v0.6.7 contact-onset forensics

The retained v241 Newton residual snapshots localize the difficulty to approaching external surfaces near the upper edge. This is self-contact in general-contact group −4, adjacent to a free/top corner; it is not evidence of an internal pore wall engaging. The residuals, pair-level switching, and prior exact crossing share the same location. Causality still requires a mechanically matching local experiment.

| File | Native time | LS/SS/iteration | Specimen residual L2 (N) | Largest node | Original x, y (mm) | Accepted x, y (mm) | Magnitude (N) |
|---|---:|---|---:|---:|---|---|---:|
| nr001 | 0.009387796 | 3/7/8 | 0.400705372 | 98184 | [1.98, 10.226666666666482] | [1.9339765727910312, 10.130488246201406] | 0.297755958 |
| nr002 | 0.009387796 | 3/7/9 | 7.33042006 | 98198 | [1.98, 10.228333333333413] | [1.9339569525893745, 10.132154716853547] | 5.68167133 |

The largest components are FX. Native residual values are component magnitudes; their signs and failed-trial coordinates are unavailable. The close-up uses the last accepted displacement field and does not portray the failed trial as converged.

Relevant zero-based boundary indices 27837, 28505 and 28506 map to native GC skin IDs 1295993, 1494296 and 1494295. Adjacent surfaces include 27838/1285266 and 28504/1383913. Original nodes 98184, 99405, 99399 and 4990 dominate the terminal region. Full top-64 mappings and source hashes are in the residual JSON files.

At the accepted parent, an approximate closest-point normal dot product is -0.999406023; the normals oppose. This numerical estimate is not a rigorous global gap measurement. Prior exact subdivision proved positive lower bounds 5.490409559e−11 and 1.112294602e−10 mm for the two suspicious pairs; those tiny values are geometric bounds, not physical resolution.

Accepted parent general contact is open with zero pressure. The terminal UNCONVERGED group −4 record reports three active skins, chattering level4, penetration 3.178046e−6 mm, pressure4906.241 MPa, stiffness1.543792e9 and FY−2.060718 N. Pair-level diagnostics do not identify individual switching skins or their pressures. Their locations are inferred from residual concentration, not invented per-element trial fields.

Strongest hypothesis: near endpoint contact activates a stiff penalty constraint and cycles between surfaces. FKN 100 may amplify the switching; reducing it is a candidate only if the licensed local fixture preserves force transmission and the unchanged penetration/overlap gates. Other unresolved contributions include missing global compliance and nonlinear boundary-path sensitivity.

The previous platen-only and Gauss-GC 1% states remain rejected for exact quadratic solid crossing. The 15 accepted nodal-branch states through 0.9270608836206897% remain preserved. No new full-model solve has been run.

## Final diagnostic findings

Actual licensed source readback confirms the principal skins use section 4. All five reported original faces belong to original mesh loop0, among413 total boundary loops. Original and accepted quadratic coordinates are retained in ORIGINAL_BOUNDARY_LOOPS_AND_FACES.json. Automatic local body partitioning must not change that identity. With section identity preserved, FKN 100/10/1 all reproduce onset difficulty; penalty scale alone is insufficient. Projection 3 removes Newton failure locally but fails unchanged quadratic contact geometry and is rejected. The NEQIT 64 local restart gains one mechanically valid state then fails; no full retry is selected. The local parent bulk-field match is good at the final accepted state, but early stress and tiny-gap/contact-state mismatches limit exact causal inference. Two-sided native structural patch forces prove local force transmission; selected-skin FSUM alone was not a complete interface balance.
