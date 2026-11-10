# v0.6.10 handoff

The highest independently accepted crop compression remains **1.2575%**, at 0.032192 mm top-platen travel, with upper/lower reactions −3.790084913840559/+3.790084911690149 N and nominal compression stress 1.4805019194689684 MPa. This is a new forward-contact E1000 reference run that reproduces the historical maximum; it does not extend it. **30% and 40% crop compression were not achieved.**

The illustrative polymer coupon passed through 40%. No polymer crop source solve was launched because neither registered contact candidate passed the 1.2675% onset gate. The finite campaign stopped at its two-candidate limit with machine time remaining. Local-fixture parent matching did not block either direct crop trial.

## Dr. Wang summary

The approved crop was used for three real reference-material compression attempts. Extending the contact patch and reversing its roles did not resolve the corner crossing: the best mechanically accepted compression remains1.2575%. We established and independently verified an explicitly illustrative polymer law through40% on a homogeneous coupon,but the cropped polymer run remains blocked by contact qualification. The figures show real accepted crop states. No30–40% crop response or calibrated polymer prediction is claimed. The next milestone is a new supported corner-contact treatment followed by a fresh polymer crop trajectory.

## Independent scientific statuses

| Status | Disposition |
|---|---|
| `CROP_SOURCE_AUTHENTICATED` | PASS |
| `CROP_MESH_AUTHENTICATED` | PASS_UNCHANGED_TRI6 |
| `CROP_TOPOLOGY_PRESERVED` | PASS_19_PORES_ONE_SOLID |
| `POLYMER_CLASS_SELECTED` | ILLUSTRATIVE_FLEXIBLE_ELASTOMER |
| `POLYMER_MODEL_DEFINED` | COMPRESSIBLE_NEO_HOOKEAN_E10_NU045 |
| `MATERIAL_PARAMETER_PROVENANCE` | EXPLICIT_ILLUSTRATIVE_NOT_FITTED |
| `MATERIAL_COUPON_VERIFIED` | PASS_LICENSED_1_TO_40_PERCENT |
| `MATERIAL_EXPERIMENTALLY_CALIBRATED` | NO |
| `CONTACT_ONSET_DIAGNOSED` | LOCAL_CORNER_PRESSURE_SUPPORT_LOSS_INTERNAL_CAUSE_UNPROVEN |
| `CONTACT_FORMULATION_SELECTED` | NONE_QUALIFIED_THROUGH_ONSET |
| `CONTACT_PATCH_COVERAGE_VERIFIED` | PASS_EXACT_NONREDUNDANT_NATIVE_PARTITION |
| `CONTACT_FORCE_TRANSFER_VERIFIED` | PASS_ACCEPTED_E1000_PREFIX_ONLY |
| `CONTACT_GEOMETRY_VALID` | PASS_ACCEPTED_PREFIX_LATER_UNSUPPORTED_CROSSING_REJECTED |
| `INTERNAL_CONTACT_CONFIGURED` | PASS_15362_GC_SKINS |
| `INTERNAL_CONTACT_ACTUALLY_ENGAGED` | NO_CLOSED_GC_SKINS_IN_ACCEPTED_PREFIX |
| `CROP_PROGRESSIVE_COMPRESSION_EXECUTED` | YES_THREE_E1000_SOURCES_NO_POLYMER_CROP |
| `CROP_BEYOND_1_2575_PERCENT` | NO |
| `CROP_TWO_PERCENT` | NOT_ACHIEVED |
| `CROP_FIVE_PERCENT` | NOT_ACHIEVED |
| `CROP_TEN_PERCENT` | NOT_ACHIEVED |
| `CROP_TWENTY_PERCENT` | NOT_ACHIEVED |
| `CROP_THIRTY_PERCENT` | NOT_ACHIEVED |
| `CROP_FORTY_PERCENT` | NOT_ACHIEVED |
| `STRESS_STRAIN_CURVE` | PASS_SEPARATE_ACCEPTED_E1000_PREFIXES |
| `FORCE_DISPLACEMENT_CURVE` | PASS_SEPARATE_ACCEPTED_E1000_PREFIXES |
| `NATIVE_STRESS_STRAIN_FIELDS` | PASS_REPEAT_E1000_ACCEPTED_MAXIMUM |
| `TRUE_SCALE_DEFORMATION` | PASS_ACTUAL_NATIVE_CROP_STATES |
| `NATIVE_CONTACT_FIELDS` | PASS_WITH_AVAILABILITY_MASKS |
| `RESTART_VERIFIED` | HISTORICAL_1_2_PERCENT_AUTHENTICATED_ZERO_NEW_RESTARTS |
| `MECHANICAL_MESH_CONVERGENCE` | UNQUALIFIED |
| `DR_WANG_LARGE_STRAIN_OBJECTIVE` | NOT_ACHIEVED |
| `POLYMER_PHYSICAL_VALIDITY` | UNQUALIFIED_NO_GRADE_CALIBRATION |
| `PAPER_READINESS` | HOLD |
| `LLM_FEEDBACK_READY` | NO |
| `LLM_OPTIMIZATION` | NOT_PERFORMED |

## All 102 handoff questions

**1. What repository path was used?**

C:\Users\sd22446\Projects\Young-Dawgs-VSCode

**2. What was the starting HEAD?**

3fda931f857730e2abef04cfd5f04ef08378f7fb

**3. Was the working tree initially clean?**

Yes; master was clean at registration.

**4. Was the original 256 × 256 crop authenticated?**

Yes; audit/BASELINE.json binds the unchanged crop source.

**5. Was the existing crop mesh preserved?**

Yes;174746 nodes,79678 quadratic TRI6,semantic SHA77788b5bc2923de31d4b0b66dad909510bb32c96708b38d1b1bfc001e22f8add.

**6. Were all 19 original pores preserved?**

Yes;19 pores and one connected solid.

**7. Were all historical experiments unchanged?**

Yes; protected historical data/results/generators/evaluator are unchanged. The shared progress monitor adds an opt-in control with its historical default preserved.

**8. Was any original 1024 × 1024 simulation performed?**

No; zero new original full-specimen solves.

**9. Was the last valid crop restart authenticated?**

Yes; historical1.2% RST/RDB authenticated against native receipts; no new restart was launched.

**10. Which new directories were created?**

docs/pipeline_v0.6.10,experiments/pipeline_v0.6.10/run_001 and raw solver/v0610,including reverse; see FILE_INVENTORY.json.

**11. Which polymer class was selected?**

Generic flexible elastomeric polyurethane-like idealization.

**12. Was a specific polymer grade identified?**

No commercial grade is claimed.

**13. What material source or rationale was used?**

Simple objective finite-strain law; E10MPa andν0.45 explicitly illustrative. Manufacturer sources inform the class review only; no coefficients were fitted. See material-selection report.

**14. Is the model experimentally calibrated or illustrative?**

ILLUSTRATIVE_UNCALIBRATED_POLYMER_MODEL.

**15. Which constitutive model was selected?**

Compressible Neo-Hookean,isochoric I1bar plus quadratic volumetric energy.

**16. What are its parameters and units?**

E10MPa,ν0.45,μ3.448275862MPa,K33.33333333MPa,d0.06MPa^-1. ANSYS NEO takesμ,d.

**17. What strain range supports its use?**

Numerical homogeneous coupon agreement through40%; no experimentally supported polymer strain range or crop result.

**18. Was material compressibility considered?**

Yes; finite K,ν0.45,J>0 and lateral/thickness response checked.

**19. Was plane-stress compatibility verified?**

Yes; installed2024R1 PLANE183 TRI6,KEYOPT3=3,KEYOPT6=0,1mm reference thickness; native SZZ≈0.

**20. Were material coupon tests executed?**

Yes; one licensed source coupon and independent POST1 at1%,10%,20%,30%,40%.

**21. Did they pass?**

Yes; maximum nominal-force relative error2.484e−7,below1%.

**22. Were actual ANSYS stress and strain measures interpreted correctly?**

Coupon native normal EPEL matches logarithmic strain; native SYY matches Cauchy stress; reference-area reactions give nominal stress. Crop fields retain native EPEL labels; shear conversion was not separately calibrated.

**23. Was the historical E1000 model kept separate?**

Yes; CROP_LINEAR_ELASTIC_E1000_V068 is distinct from the defined polymer identity.

**24. Did the new material require a fresh solver branch?**

Yes; fresh unloaded material setup required. No polymer crop source was launched because contact entry failed.

**25. Which exact contact skin opened at 1.2675%?**

Historical skin95927,physical face2138; strict extended setup equivalent skin95945.

**26. What interacting physical surfaces were involved?**

Opposing upper-right exterior-notch arcs,including sourcefaces2138/2139 and targetface2637; not internal pore walls.

**27. Was the cause of contact loss identified?**

Local corner pressure-support loss is evidenced; complete internal solver root cause remains unproven. Arc truncation alone is not supported after extension.

**28. Was contact migration across neighboring skins observed?**

Yes; opening95927/face2138 while adjacent95928/2139 remains loaded.

**29. Were general-contact exclusions implicated?**

Partition was investigated; exact native audit shows no missing/duplicated faces after extension. No causal exclusion defect is established.

**30. Was localized pair coverage sufficient?**

Geometric coverage is complete for the intended extended arcs; valid pressure support through onset is insufficient.

**31. Which candidate corrections were tested?**

Forward contiguous arc extension; one strict-equilibrium technical retry; reversed source/target roles as physical candidate2.

**32. Were they actually supported by ANSYS 2024 R1?**

Native2024R1 setup and source runs executed; support/syntax acceptance does not imply mechanical validity.

**33. Which correction was selected, if any?**

None qualified through the barrier.

**34. Did the corrected model transmit opposing contact forces?**

Yes at the accepted forward prefix,including1.2575%; independent opposing structural force proof passes. Later unsupported crossing still rejects.

**35. Was there invalid boundary crossing?**

Yes in later diagnostics; all unsupported crossings rejected from first failure onward.

**36. Was penetration within registered limits?**

Last accepted forward endpoint penetration8.539264e−7mm and continuous arc depth≤3.3646502e−6mm,both<5e−5mm. Small depth alone cannot excuse missing pressure.

**37. Did correct separation behavior remain possible?**

Native open statuses remain possible; no tie or tensile adhesive constraint introduced. No full unloading/separation cycle was validated.

**38. Were redundant contact constraints prevented?**

Yes; exact single-pair face partition,no source/target shared nodes and no duplicate GC exposure. Symmetric double constraints were not added.

**39. Did the actual cropped model pass the onset transition?**

No; forward accepted through1.2575%,reverse only1.154545455%.

**40. What contact problems remain?**

Pressure-bearing support at adjoining corner; future high-strain internal contact transfer; native internal normal/search cause unproven.

**41. Was a real new cropped-specimen compression solve performed?**

Yes; three fresh E1000 crop source processes. Zero polymer crop source processes.

**42. Was the loading trajectory continuous?**

Accepted prefixes are continuous fromzero in their own fresh source. Forward62 states;reverse47. Later failed states do not repair earlier failures.

**43. Was 1.2675% passed with valid contact?**

No.

**44. Was 1.5% independently accepted?**

No; native1.5% was reached in forward strict source but rejected.

**45. Was 2% accepted?**

No.

**46. Was 5% accepted?**

No.

**47. Was 10% accepted?**

No.

**48. Was 20% accepted?**

No.

**49. Was 30% accepted?**

No.

**50. Was 40% accepted?**

No.

**51. What was the highest native-converged strain?**

1.5% in strict forward E1000 source; diagnostic only.

**52. What was the highest independently qualified strain?**

1.2575% E1000 forward; no improvement over historical accepted maximum.

**53. What was the corresponding platen travel?**

0.032192mm top-platen travel.

**54. How many accepted checkpoints were produced?**

62 saved states in the best forward accepted prefix;47 in separate reverse prefix;0 in coarse. Do not splice or sum as one loading trajectory.

**55. How many cutbacks occurred?**

Parsed native cutbacks:coarse1,strict0,reverse10;11 across all three separate sources.

**56. What was the last valid restart?**

Historical1.2% restart remains authenticated; new accepted1.2575% result is LS5/SS8. Its full source includes later rejected states,so no new all-valid restart parent is promoted.

**57. What stopped further compression, if applicable?**

Unmodeled/unsupported corner crossing; two registered physical candidates exhausted. Polymer entry fails. Native reverse later nonconverged at minimum increment; RAM/disk did not stop progress.

**58. Was an actual stress–strain curve generated?**

Yes; separate accepted E1000 branch curves. No polymer crop curve.

**59. Was an actual force–displacement curve generated?**

Yes; separate accepted E1000 branches.

**60. What was the peak accepted compressive force?**

3.790084913840559N.

**61. What was the peak accepted nominal stress?**

1.4805019194689684MPa,reference area2.56mm².

**62. Were upper and lower reactions independently extracted?**

Yes; signed upper/lower native pilot reactions independently read back at all states.

**63. Was force balance acceptable?**

Yes in accepted prefixes; final imbalance5.673778e−10. Coarse initial1.32% imbalance fails.

**64. Were actual native displacement fields saved?**

Yes;174746 native nodes,UX/UY; final repeated exactly.

**65. Were native stress fields saved?**

Yes; native SXX,SYY,SXY,SEQV on47525 corners; no invented midside stresses.

**66. Were native strain fields saved?**

Yes; native EPEL XX,YY,XY on47525 corners; final repeated exactly.

**67. Were native contact pressure fields saved?**

Yes; native status,endpoint pressure/penetration,targets,forces and availability masks. Native farfield absence is preserved.

**68. Was actual internal pore contact observed?**

No closed general-contact pore skins in accepted prefixes. Selected exterior-notch pair engagement is distinct.

**69. Were any pores observed closing?**

No accepted pore closure demonstrated; no minimum pore-area metric is claimed.

**70. Were any structural buckling or collapse modes observed?**

No validated buckling/collapse/densification mode established. Local bending is visible.

**71. Were deformed TRI6 mappings valid?**

Yes in accepted prefixes; minimum analytic determinant2.72197937e−6mm² at final accepted state.

**72. Were invalid intersections rejected?**

Yes; unsupported intersection stops accepted path despite native convergence.

**73. What maximum local strains were observed?**

At final accepted E1000 state native EPEL YY range-0.05538431879 to0.01547414346; maximum |U|0.04281781739mm. Full other tensor components remain in native CSVs.

**74. What physical limitations remain?**

No grade/calibration,rate/temperature,viscoelasticity,plasticity,damage/fracture;2D thickness assumptions;no mesh convergence;no accepted high-strain polymer path.

**75. How many actual ANSYS source solves ran?**

4 source processes:3 crop E1000 +1 polymer coupon;17 native processes total,including setup and readback.

**76. What was total source-solver runtime?**

2589.230673s summed source wall;3202.795419s all native wall. Not CPU time.

**77. What was peak observed process memory?**

3.493458GiB sampled native process-tree peak; no arbitrary RSS cap.

**78. Was sustained severe paging detected?**

No sustained severe paging stop recorded; system hard-fault counters are proxies,not process-specific pagefile reads.

**79. How much disk was used?**

16346065007bytes (15.223459GiB) raw v0610 artifacts at ledger creation; no cleanup of meaningful failures.

**80. How many genuine restarts occurred?**

Zero genuine restart launches; all new source models start unloaded.

**81. How many active tests passed?**

818 active tests,zero skipped/failures/errors.

**82. How many archived replay checks passed?**

475 checks across9 replay groups; unchanged archived tests against current linked fixture context,not a restored historical environment.

**83. How many licensed evidence checks passed?**

175 licensed-artifact checks,including23 new v0610; counts overlap active/archive categories and are not summed.

**84. Were protected historical files preserved?**

Yes; Git protected-path audit and raw baseline SHA verification pass. No evaluator/generator/canonical geometry/historical result changes.

**85. What solver failures were retained?**

Coarse recoverable-error monitor stop plus force-accuracy failure; strict converged unsupported crossing; reversed earlier unsupported crossing and later minimum-increment nonconvergence. All preserved.

**86. Which files were created or modified?**

See validation/FILE_INVENTORY.json for complete versioned path inventory,and performance/PERFORMANCE.json for native directories.

**87. Which Git commits were created?**

All coherent phases were committed; complete evidence-phase list follows.

**88. What are their complete hashes and exact messages?**

Full40-character hashes and exact messages follow and appear in validation/GIT_HISTORY.json. Final report commit is supplied by git log -1/terminal handoff.

**89. Is the final working tree clean?**

The evidence phase was committed clean before report generation. Final report changes are committed,then git status --porcelain is checked; the terminal handoff supplies that observed final result. This report cannot certify its own future commit.

**90. Was anything pushed?**

No push performed.

**91. What is the exact v0.6.10 scientific status?**

HOLD_CONTACT_ONSET__POLYMER_CROP_NOT_EXECUTED__THIRTY_PERCENT_NOT_ACHIEVED

**92. Is the selected polymer model calibrated or illustrative?**

Illustrative and uncalibrated; coupon verified,physical polymer validity unqualified.

**93. Was the previous contact-onset barrier resolved?**

No.

**94. Did the cropped specimen achieve 30%?**

No.

**95. Did it achieve 40%?**

No.

**96. Which results are mechanically accepted?**

Best forward E1000 prefix0.01%–1.2575%,62 saved states; separate reverse prefix to1.154545455%,47 states. Polymer homogeneous coupon numerical response is accepted only in its coupon scope.

**97. Which results are only numerical diagnostics?**

All coarse source states and all forward/reverse states after first rejection; native maximum1.5%; all unexecuted polymer targets are plans,not results.

**98. What can accurately be shown to Dr. Wang?**

Actual accepted E1000 curves/true-scale fields,localized contact failure evidence,and separately verified illustrative polymer coupon. Explain clearly that30–40% crop target is unmet.

**99. What remains before a physically predictive polymer simulation?**

Resolve contact,run fresh polymer crop,measure/fix grade-specific constitutive response and strain/rate/temperature validity,calibrate multiaxially/cyclically as appropriate,verify mesh and dimensional/boundary assumptions.

**100. What remains before a paper-quality mechanical dataset?**

Continuous accepted high-strain native path,mechanical mesh sensitivity,reproducible full fields,calibrated material,experimental comparison and uncertainty/failure criteria.

**101. What is the recommended next milestone?**

Separately register corner-aware supported detection/segmentation or full nonredundant GC treatment; prove native pressure-bearing force transfer through onset on actual crop,then fresh verified polymer continuation.

**102. What remains before controlled LLM-guided design feedback can begin?**

Mechanically accepted,physically qualified multi-design dataset with stable metrics/uncertainty and controlled validation gates. No LLM optimization or design feedback was performed.

## Exact commits through evidence phase

Starting clean HEAD `3fda931f857730e2abef04cfd5f04ef08378f7fb`. Evidence through `35554d8fe1f343463366a6705bc6c91d5d7cbe4e`. The final report commit follows this list and is supplied in the terminal handoff. No push or history rewrite.

- `02fecac1456b6ff9085138c66598664dd74792b9` — docs(fem): register v0.6.10 cropped polymer compression protocol
- `4e0982017454dcf1f2977a9c738f208f6260b097` — feat(material): define illustrative Neo-Hookean polymer and analytical plane-stress coupon
- `6c070f5309cffec5be980aee7ac2ca40b2a4acab` — test(ansys): verify illustrative polymer coupon and register extended-arc crop trial
- `ec7ae8e2ad508a38ad626bf60ce35ebec2559a25` — feat(contact): verify extended native arc coverage and prepare fresh cropped-specimen loading
- `8c9b246209fe7d8b425c77ffac7e5d380b10e5c4` — feat(contact): support isolated directional arc trials with unique launcher identities
- `b35d3b965c646293ee49134ca77da65c30d46ca9` — docs(material): record manufacturer data review and illustrative parameter limits
- `551315dc42ffedb912e9c2b83be31b9225def569` — feat(material): export verified native coupon response and analytical comparison
- `128bac6da2e8218942c20e1d091b170c0f66796b` — feat(ansys): enforce campaign clock and isolate registered directional contact trials
- `d7d5d76482495fa6fdcf51c95785a89ea8427b91` — fix(ansys): allow registered native trial cutbacks while preserving acceptance gates
- `88090db29a49ee95f1570cdb12785685f90e67e3` — feat(ansys): preserve rejected crop path and register stricter fresh equilibrium retry
- `a6aa4e9982ea8ed20a4a0c3b056c5a6e72ed43d5` — fix(results): normalize compact native inventories and preserve raw hash provenance
- `7d0b90259b8bad0f3c8f1de9897c1c6e5e716c00` — feat(material): prepare gated fresh polymer branch and authenticated progressive loading
- `734f8c548138ca353ec0ca0332b1cec14ddfd52f` — feat(material): gate fresh polymer loading on a continuous qualified onset path
- `1e5cce5565dd904689303f99c05e162ae0f32d4d` — test(fem): prevent promotion across rejected contact histories
- `b6f6caa6ab091ca317dc683416a4ee97c2759f28` — feat(contact): add conservative continuous quadratic-arc depth certification
- `b0398aaa5f0086cd42ce769088d56dd8cba6c229` — feat(contact): register isolated reversed-role test after extended coverage fails
- `457b3137b49ad07a6b0c2c8de784bc14ff95ff74` — feat(fem): preserve strict crop path and continuous-arc hold through contact onset
- `b7e26eeadfad866f76943a4a9873942afec113ff` — feat(contact): verify native reversed-arc setup and freeze fresh crop test
- `f81b9af57568ac08eddbf9e93377eac86e154523` — docs(fem): freeze v0.6.10 handoff questions and independent scientific status catalog
- `0917feff217c21924ff2e72017f6528818a3274c` — test(contact): bind pressure-bearing endpoints to native target inventory
- `3b826db98e84383249bd70724f5ca6c0ab8f9dae` — fix(fem): bind continuous geometry and polymer setup to verified native sources
- `b0dc8588257de4cc6f7d9bac5d86048a24e695c4` — fix(ansys): cap each native job by remaining campaign time
- `e9b025e9900679ce856e65d3a2a87b3f2a8acab4` — docs(material): explain constitutive-law choice and unsupported fitting freedom
- `5b30d0c2d85c928b483a322d34eb876d772243b7` — feat(ansys): preserve reversed-contact rejection and repeat accepted-state extraction
- `35554d8fe1f343463366a6705bc6c91d5d7cbe4e` — feat(results): archive accepted crop fields curves and contact-gated campaign outcome

## Evidence index and reproduction

Active repository: `C:\Users\sd22446\Projects\Young-Dawgs-VSCode`. Raw artifacts: `C:\Users\sd22446\AppData\Local\YoungDawgs\artifacts\solver\v0610`. Versioned run: `C:\Users\sd22446\Projects\Young-Dawgs-VSCode\experiments\pipeline_v0.6.10\run_001`.

The raw root contains immutable source inputs,DB/RST/restart files,native logs and complete all-state scientific CSVs. Git contains compact native receipts,selected small output records,topology tables,qualification JSONs,plots and source scripts. Retained binaries are deliberately outside Git. Per-file native artifact hashes come from execution receipts; source/mesh/material references and RST hashes are cross-bound in audit/readback/branch manifests.

- `audit/BASELINE.json`, `audit/PROTECTED_HISTORY.json`: source/mesh/restart authentication and protected paths.
- `material_selection/MATERIAL.json`, `SOURCE_REVIEW.json`; `material_coupon/QUALIFICATION.json`, `NATIVE_COUPON_RESPONSE.csv`, `COUPON_RESPONSE.png`: exact illustrative law and separate coupon evidence.
- `protocol/`: original budgets,accuracy/supervisor corrections,reversed candidate,continuous geometry,polymer gate and final stop.
- `track_B_progressive_compression/` and `reverse/track_B_progressive_compression/`: native/continuous/final mechanical gates; final suffix `_mechanical_qualification.json` governs promotion.
- `mechanical_response/ALL_NATIVE_CHECKPOINTS.csv`, `BRANCH_SUMMARY.json`, `METRICS.json`: all219 actual crop states,branch identity and accepted-prefix metrics.
- `fields/REPEAT_READBACK.json`: two identical native tensor/displacement/reaction/contact exports at accepted LS5/SS8.
- `figures/FIGURE_INVENTORY.json`: actual accepted/rejected-state figure sources and hashes.
- `performance/PERFORMANCE.json`: all17 actual native process paths,runtimes,source/setup/readback classification,unique launcher IDs and receipt hashes.
- `verification/TEST_SUMMARY.json`, XML/logs and archived manifest: separate active/archive/licensed checks.
- `validation/SCIENTIFIC_STATUSES.json`, `HANDOFF_ANSWERS.json`, `FILE_INVENTORY.json`, `GIT_HISTORY.json`: independent status and handoff records.
- `validation/EXPERIMENT_PROVENANCE.json`: explicit material-configuration SHA for every source experiment,cross-bound to input,source manifest,native receipt,RST and mesh. The E1000 property index is retrospective documentation of unchanged historical material,not a parameter change.

Use `.venv/Scripts/python.exe` in the active repository. The scripts intentionally refuse to recreate existing native directories. Reproduction requires a separately registered new run and isolated raw root; never overwrite preserved evidence. Sequence: `scripts.v0610_common` registration; `scripts.v0610_material` prepare/execute/post/execute-post/qualify; `scripts.v0610_crop` setup/unified/trial/export/force/qualify; `--strict` selects the accuracy retry; `scripts.v0610_reverse` repeats the second isolated candidate; `scripts.v0610_geometry SOURCE --branch reverse` adds final geometry. `scripts.v0610_final_fields prepare/run --index 1` then2 and `compare` gives final repeated readback. `scripts.v0610_results` produces actual-data plots. `scripts.v0610_report` writes reports. These names identify this run; do not rerun mutation/preparation actions over existing directories.

Tests: set EVALUATOR_PATH to `validation/evaluators/evaluator_v1_1.py`,run pytest `tests`; run `scripts.replay_geometry_archives --output NEW_OUTPUT`; run pytest on `validation/ansys_v066_integration.py` through `ansys_v069_integration.py` plus `ansys_v0610_integration.py`. Licensed integration checks require retained local native artifacts; software-only tests do not. Read-only checks do not require a new source solve.

No automated rerun or additional native job is left running. The material-gated polymer framework is present for a future qualified contact result; it was not executed and establishes no polymer crop acceptance.
