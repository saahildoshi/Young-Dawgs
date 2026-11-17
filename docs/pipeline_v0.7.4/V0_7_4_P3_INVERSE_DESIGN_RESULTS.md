# P3 same-conversation target-matching pilot

H1 descriptive result: IF mean script target error decreased: 0.6920% initial to 0.4296% revised. NF mean script target error decreased: 1.3743% initial to 1.2754% revised.

Initial scripts already produced 39/48 attempted target-band hits; revised scripts produced 42/48. Failed attempts stay in these denominators. The initial hit rate and low initial errors limit the remaining margin for improvement; the target and scoring rule were preserved.

The registered target was 1640 MPa (J = 1.640), with a ±2% hit band of 1607.2–1672.8 MPa. Four IF and four NF initial/revised script pairs were frozen together before final generation. No script was manually repaired or revised after held-out evaluation. IF received its own three actual development curves/moduli/errors and authenticated v0.7.3 controlled geometry–mechanics; NF received matched structural information and unchanged physics/target without measured mechanics. The final seeds and evaluation masks were withheld from every generator conversation.

All 96 held-out attempts are preserved. 94 generated arrays have exact 20,731/44,805 phase composition and pass the complete unchanged morphology envelope; two NF_03 initial attempts exhausted the eight-candidate bound. All 16 generated cohorts pass their observed diversity diagnostics, but only 15/16 initial/revised generators meet the full six-of-six structural criterion. All eight revised scripts pass six-of-six. The two failed initial outputs have null mechanics and remain in denominators.

| Conversation | Initial valid/native | Revised valid/native | Initial mean absolute error | Revised mean absolute error | Initial minus revised (percentage points) |
|---|---:|---:|---:|---:|---:|
| NF_01 | 6/6 | 6/6 | 0.8286% | 2.7960% | -1.9674 |
| IF_01 | 6/6 | 6/6 | 0.5509% | 0.5047% | 0.0461 |
| NF_02 | 6/6 | 6/6 | 1.1424% | 0.8241% | 0.3183 |
| IF_02 | 6/6 | 6/6 | 0.5922% | 0.4768% | 0.1154 |
| IF_03 | 6/6 | 6/6 | 1.2535% | 0.3464% | 0.9070 |
| IF_04 | 6/6 | 6/6 | 0.3713% | 0.3905% | -0.0192 |
| NF_03 | 4/6 | 6/6 | 2.3200% | 0.3598% | 1.9601 |
| NF_04 | 6/6 | 6/6 | 1.2064% | 1.1215% | 0.0849 |

| Arm | Independent conversations | Initial mean script error | Revised mean script error | Mean within-conversation reduction (pp) |
|---|---:|---:|---:|---:|
| IF | 4 | 0.6920% | 0.4296% | 0.2623 |
| NF | 4 | 1.3743% | 1.2754% | 0.0990 |

Revised script-error contrast NF minus IF = 0.8457 percentage points (positive favors IF). The contrast of within-conversation improvements IF minus NF = 0.1634 pp. Excluding NF_01 leaves four IF and three NF conversations: revised-error contrast 0.3388 pp and improvement contrast -0.5254 pp. These are unweighted means of script-level results; stochastic seeds are nested observations, never independent LLM trials. NF_03 initial has only four accepted outputs, so its conditional six-versus-four comparison is supplemented by the common-accepted-seed analysis in the data tables. No failure penalty, significance test, confidence claim or generalized causal advantage is inferred. Excluding the deviating conversation reverses which arm improved more, while IF still has lower revised error. IF also began with lower initial error. The feedback-specific improvement advantage is therefore not stable in this pilot.

Actual accepted H1 source solves: 94/96 attempted slots. Actual H2 source solves: 31/32 slots. Every accepted case contains five solved strain checkpoints and a separate native result-file reopening. Full per-seed moduli, bias, mean/median errors, sample SD, target hits, timing, diversity and failure records are in `target_property_analysis/`; `COMPACT_SCRIPT_TABLE.csv` is the flat sixteen-row comparison.

All 32 registered H2 slots are accounted for: 31 actual refined source solves and one unsolved structurally failed NF_03 initial seed 5001, with no replacement. Every script uses the preselected seeds 5000 and 5001. Observed relative modulus changes range from 0.3971% to 0.5691%; 31/31 meet the registered 2% tolerance. The paired H1/H2 table records whether each initial-to-revised error reduction persists and whether it exceeds the sum of the two observed mesh shifts divided by target. This conservative comparison is a sensitivity diagnostic, not a rigorous error bound or full convergence proof. It tests two seeds per script, not the whole six-seed mean.

| Conversation | Matched refined seeds | H1 error reduction (pp) | H2 error reduction (pp) | Positive at both levels | H2 reduction exceeds combined observed shifts |
|---|---:|---:|---:|---:|---:|
| NF_01 | 2 | -2.2058 | -2.6315 | 0/2 | 0/2 |
| IF_01 | 2 | -0.1677 | -0.7343 | 0/2 | 0/2 |
| NF_02 | 2 | -0.0218 | -0.0243 | 1/2 | 0/2 |
| IF_02 | 2 | 0.6384 | 0.2628 | 1/2 | 0/2 |
| IF_03 | 2 | 0.9519 | 0.6988 | 2/2 | 1/2 |
| IF_04 | 2 | -0.0136 | -0.0313 | 0/2 | 0/2 |
| NF_03 | 1 | 1.8456 | 1.5601 | 1/1 | 1/1 |
| NF_04 | 2 | 0.4696 | -0.6184 | 0/2 | 0/2 |

On only mutually accepted preselected refined seeds, the unweighted conversation-level H2 improvement contrast IF minus NF is 0.4775 pp; excluding NF_01 gives -0.2568 pp. NF_03 contributes one paired seed. This restricted sensitivity comparison is not confirmation of the full six-seed primary arm estimate.

The fixed first-seed figures show dispersed inclusions without the earlier continuous reinforcement lanes. They also show visible differences from the selected reference: some scripts use narrower size populations or more even spacing, and revisions can change orientation. Passing the frozen envelope is not equivalence to the natural image distribution. All successful arrays are unique within each cohort and their rigid-invariant diversity diagnostics pass; these diagnostics do not establish coverage of the true material distribution. Initial/revised paired array differences are recorded separately.

All eight initial generators and eight revisions are genuine ordinary-ChatGPT responses. Every revision used the original /c/conversation ID, without reattaching an old script or starting a replacement chat. The exposed interface setting was High; exact backend identity/version, tokens and cost were not exposed. The first four chats displayed a Pipeline Tests project path on reopening, while the last four displayed normal conversation paths. Project/account memory and personalization were not isolated. NF_01 contains one unintended extra user turn consisting only of the ChatGPT root URL and a nonscientific assistant link reply; it received no extra code or scientific feedback. Thus each trial has one scientific revision, but the strict equal total-message budget fails for NF_01. Chronological UI captures, canonical/observed URLs, exact prompt files, raw returned code and hashes preserve this deviation. The registered trial is retained and a descriptive analysis excluding NF_01 is reported; it does not repair the protocol deviation.

Earlier raw ANSYS folders are currently absent from their recorded local paths. The original committed results, native execution/readback receipts, compact curves, expected hashes, figures and earlier passing test records are preserved, but current rehashing/reopening of those earlier raw files is unavailable. The cause and removal time are unknown. The current held-out raw files were verified directly. No old scientific case was rerun to conceal the gap. Generic slicer G-code was independently reproduced byte-for-byte from the same engine/settings/STLs and its original hashes verified; recovery receipts distinguish those new deterministic slices from the original executions. This is a raw-preservation limitation, not a new native solve failure.

P3 remains one morphology-selected, supplied horizontally flipped SEM crop, a genuine geometry-preserving augmentation with provisional label 5 carbide identity. Labels 1 and 5 are retained in arrays and explicitly mapped to native MAT1/MAT2. Pixel units provide no micrometer calibration. No display overlay or displayed 64-pixel scale bar enters the source geometry or model image. The 1 mm computational square/thickness, E = 1000/10000 MPa, nu = 0.30, ideal shared-node bonding and small-strain plane stress are illustrative. These finite-domain apparent moduli do not establish a physical material prediction, RVE, isotropic tensor, yield, damage or fracture.

See [figures](V0_7_4_FIGURES.md), [validation](V0_7_4_VALIDATION.md), [F1](V0_7_4_F1_MECHANICAL_RESULTS.md) and [handoff](V0_7_4_HANDOFF.md).
