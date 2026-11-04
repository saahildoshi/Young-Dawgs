"""Render the frozen 114-question v0.6.8 scientific handoff."""
import json
import subprocess

from scripts.v068_common import REPO, RUN, read, write_json

START='57e6a9546bdb0e344c2e183cc9531257b75bc923'


def git(*args):
    return subprocess.run(['git',*args],cwd=REPO,check=True,text=True,capture_output=True).stdout.strip()


ANSWERS={
 1:'C:/Users/sd22446/Projects/Young-Dawgs-VSCode, on master.',
 2:START+'.',
 3:'Yes. The canonical generator, source geometry and historical experiments were preserved.',
 4:'Yes; the original fine TRI6 mesh remains authenticated by the prior native and manifest checks.',
 5:'Yes; all four authenticated full restart files retain their recorded hashes.',
 6:'Yes; the previous 1% platen-only and Gauss-contact states remain rejected.',
 7:'C:/Users/sd22446/AppData/Local/YoungDawgs/artifacts/solver/v068 for large raw v0.6.8 files.',
 8:'Yes; the original upper exterior hotspot and residual identities were reauthenticated.',
 9:'Faces 27837, 27838, 28504–28506 and residual nodes 98184, 99405, 99399, 4990.',
 10:'Yes; 5,544 original elements and 15 measured full-parent cut histories were included.',
 11:'Later states match well; the first three still fail, with about 88% first-state SYY RMS error.',
 12:'Measured and sampled, but the terminal near-gap mismatch was not resolved sufficiently.',
 13:'Yes; licensed ANSYS 2024 R1 installed KEYOPT(4)=5.',
 14:'Yes; the native general-contact option and small connected fixture were verified.',
 15:'Yes; actual native ETLIST/contact inventories verify the installed option.',
 16:'Yes, only the original-mesh local unified fixture converged to a hypothetical 1%.',
 17:'Local penetration and mapping checks passed; this does not establish full-specimen behavior.',
 18:'No unexplained local crossing passed its local gate; no full-model claim follows.',
 19:'Expanded local solve times were 122.57 s nodal and 128.19 s unified, with about 0.40–0.42 GiB peak tree RSS.',
 20:'No Track A pair branch was justified after the parent mismatch; the separate Track B pair was tested.',
 21:'Yes in Track B: exactly 22 selected GC skins were replaced, with no duplicate physical face.',
 22:'No candidate passed the complete local plus measured-parent entry gate.',
 23:'None for the original full specimen.',
 24:'No; the predeclared parent-match gate failed.',
 25:'No new full-original solve was launched.',
 26:'The historical parent was reauthenticated; compatibility of an unqualified new full formulation was not claimed.',
 27:'No accepted new full 1% state.',
 28:'0.9270608836206897% engineering compression.',
 29:'Authenticated full load step 3/substep 6 at strain 0.009270608836206897.',
 30:'The unresolved early local-to-parent stress mismatch and original curved-contact onset.',
 31:'The preselected central 256×256-pixel window [384,384,640,640] from Design 9/seed 1.',
 32:'A separate physical crop, not a new random realization or a full-source mesh variant.',
 33:'One connected, load-bearing, computationally manageable specimen with 19 enclosed pores.',
 34:'The source coordinates and criteria were frozen before mechanical results in Track B protocol.',
 35:'2.56 × 2.56 mm; assumed plane-stress thickness 1 mm.',
 36:'49.1256713867188%.',
 37:'19 enclosed pores.',
 38:'0.01 mm source-pixel minimum clearance; sampled axial solid chords 1–15 pixels; equivalent pore diameters 0.241–0.655 mm over recorded percentiles.',
 39:'Yes; one connected solid spanning both loading directions.',
 40:'Quadratic TRI6 plane-stress mesh with curved midside geometry.',
 41:'174,746 nodes and 79,678 TRI6 elements.',
 42:'Yes; topology, area, boundary, normal, angle, aspect and quality gates passed.',
 43:'Yes in the reference mesh and every accepted deformed saved state.',
 44:'Frictionless rigid platen pairs, remaining general contact and one localized deformable unified pair.',
 45:'Yes; closed native contact, signed force transfer and reaction balance passed.',
 46:'Yes; general self-contact retained on 15,386 nonselected physical faces.',
 47:'The selected exterior pair engaged; pore/internal general contact remained open through 1.2575%.',
 48:'Yes; connected-neighbor exclusions and exact native face inventory were checked.',
 49:'Yes; the unpressurized selected-arc crossing from 1.2675% onward was rejected.',
 50:'Yes; multiple genuine licensed NLGEOM source solves and restart continuations ran.',
 51:'1.5% native converged on the unified-pair branch.',
 52:'1.2575% as the last continuous independently accepted saved substep.',
 53:'No.',54:'No.',55:'No.',56:'No.',57:'No.',
 58:'0.032192 mm at the accepted 1.2575% saved state.',
 59:'At 1.2675%, a selected pair skin opened during an exterior-arc crossing.',
 60:'Last complete qualified restart: track_B_pair5_to_01200_001 at 1.2%; 1.2575% is a valid saved field inside a failed continuation.',
 61:'Yes, a 12-point native nominal stress–strain curve on the unified-pair branch through 1.2575%.',
 62:'Yes, the same 12 accepted points provide native force versus travel.',
 63:'12 points on the unified-pair curve: five complete-stage endpoints and seven later accepted substeps.',
 64:'3.7900865393 N at the lower platen of the last accepted state.',
 65:'1.48050255 MPa nominal compressive stress.',
 66:'Yes; −3.7900865216 N upper and +3.7900865393 N lower at the maximum.',
 67:'Yes; relative platen reaction imbalance 4.66×10⁻⁹.',
 68:'Yes; signed platen forces and independent opposing structural forces of the selected pair.',
 69:'Maximum selected-pair endpoint penetration at 1.2575% was 9.6554×10⁻⁷ mm, below 5×10⁻⁵ mm.',
 70:'Yes; all 174,746 native nodal displacement vectors at the selected state.',
 71:'Yes; native corner-node stress for all 47,525 TRI6 corner nodes.',
 72:'Yes; native elastic strain at those corner nodes.',
 73:'Yes; internal GC status/pressure were extracted, but those skins were open. The exterior pair reached 18.0355 MPa.',
 74:'Pore-approach trends were not independently established; the verified closing event is exterior-arc contact.',
 75:'No verified complete pore closure.',
 76:'No verified structural buckling or collapse.',
 77:'Yes; zero invalid analytic deformed TRI6 mappings at every accepted state.',
 78:'Yes; the first unpressurized selected crossing at 1.2675% and later states were rejected.',
 79:'At 1.2575%, native elastic EYY ranged from −0.0553843 to +0.0154742.',
 80:'Assumed uncalibrated linear elastic E=1000 MPa and ν=0.3 under 2D plane stress; no failure law.',
 81:'0.9270608836206897%.',
 82:'1.2575%.',
 83:'Yes; original full and crop figures, curves and reports are explicitly separated.',
 84:'No.',85:'No.',86:'No.',
 87:'The valid early crop response is exploratory; there is no accepted 30–40% large-strain result.',
 88:'No mechanical mesh-convergence study was completed.',
 89:'No physical material parameters were calibrated.',
 90:'Show the true-scale crop deformation, 12-point accepted curve and explicit contact stop; show the separate full 0.9271% bound.',
 91:'A valid high-compression contact path, calibrated material, mechanical mesh sensitivity and full-specimen validation.',
 92:'28 actual native source-solve processes (65 SOLVE commands across them).',
 93:'2777.786 s summed source-solver process wall time; 3156.816 s including read-only native processes.',
 94:'3,729,219,584 bytes (3.473 GiB) peak sampled process-tree RSS.',
 95:'No sustained severe paging in recorded samples; maximum sampled page reads 4273.22/s.',
 96:'44,453,512,091 bytes (41.40 GiB) retained raw v0.6.8 artifacts, including copied restart/results.',
 97:'19 actual native restart-continuation processes.',
 98:'799 active tests passed.',
 99:'475 archived replay checks passed across nine groups.',
 100:'140 licensed-artifact checks passed: 131 inherited and nine new v0.6.8 checks.',
 101:'The earlier all-GC crossing, rejected pair setup/readback, nodal-pair distorted-element solve, and unified-pair 1.2675–1.5% crossing are preserved.',
 102:'Yes; authenticated historical source, protected fine mesh and full restart hashes were unchanged.',
 103:'New v0.6.8 protocols, native compact evidence, scripts, validation tests, CSV, figures and nine reports; exact path list in FILE_CHANGES.json.',
 104:'All actual v0.6.8 commits are enumerated below; final reporting-commit hash is supplied in the terminal handoff.',
 105:'Complete hashes and messages for committed implementation/evidence phases are listed below; the final reporting commit is supplied in the terminal handoff.',
 106:'Yes after the final reporting commit, verified in the terminal handoff.',
 107:'No push was made.',
 108:'CONTACT_ONSET_LOCALIZED__NO_QUALIFIED_FULL_CORRECTION__FULL_MAX_0.9270608836206897_PERCENT.',
 109:'NATIVE_CONVERGED_1.5_PERCENT__QUALIFIED_1.2575_PERCENT__CONTACT_SWITCH_STOP.',
 110:'TWO_TRACK_EARLY_DATA_PRESERVED__THIRTY_TO_FORTY_PERCENT_NOT_ACHIEVED.',
 111:'No valid large-strain (30–40%) demonstration; a substantive bounded ANSYS attempt and valid early crop response were completed.',
 112:'First qualify a parent-matched local contact law, then a full fine-mesh restart/fresh branch and independent high-strain gates.',
 113:'Validated high-strain contact, calibrated material, mechanical mesh sensitivity and reproducible independent performance metrics.',
 114:'Resolve the pressure-bearing contact-switch at 1.2675% in a prospectively registered crop study, while repairing Track A parent matching before any full retry.'
}

A={
 'A1_SOURCE_GEOMETRY_AUTHENTICATED':'PASS',
 'A2_FINE_MESH_AUTHENTICATED':'PASS',
 'A3_PARENT_RESTART_AUTHENTICATED':'PASS',
 'A4_CURVED_CONTACT_REGION_VERIFIED':'PASS',
 'A5_LOCAL_CONTEXT_IMPROVED':'PASS',
 'A6_UNIFIED_DETECTION_SUPPORTED':'PASS',
 'A7_UNIFIED_DETECTION_MECHANICALLY_VALID':'HOLD_PARENT_MISMATCH',
 'A8_OTHER_CONTACT_CORRECTION_VALID':'NOT_ESTABLISHED',
 'A9_RESTART_COMPATIBILITY':'NOT_ESTABLISHED_FOR_NEW_FORMULATION',
 'A10_FULL_RECOVERY_ATTEMPT':'NOT_EXECUTED_GATE_FAILED',
 'A11_FULL_ONE_PERCENT':'NOT_ACHIEVED',
 'A12_FULL_FIVE_PERCENT':'NOT_ACHIEVED',
 'A13_FULL_TEN_PERCENT':'NOT_ACHIEVED',
 'A14_FULL_TWENTY_PERCENT':'NOT_ACHIEVED',
 'A15_FULL_THIRTY_PERCENT':'NOT_ACHIEVED',
 'A16_FULL_FORTY_PERCENT':'NOT_ACHIEVED',
 'A17_FULL_INTERNAL_CONTACT_ENGAGEMENT':'PASS_HISTORICAL_ACCEPTED_BRANCH',
 'A18_FULL_MECHANICAL_MESH_CONVERGENCE':'NOT_ESTABLISHED'
}
B={
 'B1_DEMONSTRATOR_SOURCE_AUTHENTICATED':'PASS',
 'B2_DEMONSTRATOR_GEOMETRY_QUALIFIED':'PASS',
 'B3_DEMONSTRATOR_MESH_QUALIFIED':'PASS_GEOMETRIC',
 'B4_DEMONSTRATOR_PLATEN_CONTACT_VALID':'PASS_THROUGH_1.2575_PERCENT',
 'B5_DEMONSTRATOR_INTERNAL_CONTACT_VALID':'CONFIGURED_NOT_ENGAGED',
 'B6_DEMONSTRATOR_PROGRESSIVE_LOADING_EXECUTED':'PASS',
 'B7_DEMONSTRATOR_FIVE_PERCENT':'NOT_ACHIEVED',
 'B8_DEMONSTRATOR_TEN_PERCENT':'NOT_ACHIEVED',
 'B9_DEMONSTRATOR_TWENTY_PERCENT':'NOT_ACHIEVED',
 'B10_DEMONSTRATOR_THIRTY_PERCENT':'NOT_ACHIEVED',
 'B11_DEMONSTRATOR_FORTY_PERCENT':'NOT_ACHIEVED',
 'B12_DEMONSTRATOR_STRESS_STRAIN':'PASS_EARLY_12_POINTS',
 'B13_DEMONSTRATOR_DEFORMATION_FIELDS':'PASS_THROUGH_1.2575_PERCENT',
 'B14_DEMONSTRATOR_NO_INVALID_INTERPENETRATION':'PASS_ONLY_ACCEPTED_STATES',
 'B15_DEMONSTRATOR_MECHANICAL_MESH_CONVERGENCE':'NOT_ESTABLISHED'
}
OVERALL={
 'PAPER_READINESS':'NO',
 'MATERIAL_CALIBRATION':'NO',
 'LARGE_STRAIN_MODEL_VALIDITY':'NOT_ESTABLISHED',
 'DR_WANG_LARGE_STRAIN_DELIVERABLE':'NOT_ACHIEVED_EARLY_RESULTS_AVAILABLE',
 'LLM_FEEDBACK_READY':'NO',
 'LLM_OPTIMIZATION':'NOT_STARTED',
 'MANUFACTURING':'NOT_STARTED'
}


def main():
    frozen=read(RUN/'protocol/HANDOFF_QUESTIONS.json')['questions']
    assert [x['number'] for x in frozen]==list(range(1,115))
    assert set(ANSWERS)==set(range(1,115))
    # The status names are frozen in the user request; reject accidental omissions.
    assert len(A)==18 and len(B)==15 and len(OVERALL)==7
    commits=[dict(zip(('hash','message'),line.split('\t',1))) for line in git('log','--reverse','--format=%H%x09%s',START+'..HEAD').splitlines()]
    changes=git('diff','--name-only',START+'..HEAD').splitlines()
    write_json(RUN/'summary/HANDOFF_ANSWERS.json',{'schema':'young-dawgs-v068-frozen-114-question-answers',
               'questions':[{**q,'answer':ANSWERS[q['number']]} for q in frozen]})
    write_json(RUN/'summary/ACCEPTANCE_STATUSES.json',{'schema':'young-dawgs-v068-independent-track-statuses',
               'track_A':A,'track_B':B,'overall':OVERALL})
    write_json(RUN/'summary/FILE_CHANGES.json',{'starting_head':START,'paths_changed_since_start':changes,
               'note':'Git-tracked paths through the pre-reporting commit; final reporting artifacts are added afterward.'})
    out=['# Pipeline v0.6.8 — final handoff','',
         'The original full specimen and separate crop are never combined. The original full maximum is **0.9270608836206897%**; the crop maximum native-converged state is **1.5%** and its maximum independently accepted saved state is **1.2575%**. The 30–40% research target was not reached.','',
         'The answers below follow the frozen [114 questions](../protocol/HANDOFF_QUESTIONS.json). Numerical evidence and scientific limits are in the [validation report](V0_6_8_VALIDATION.md), [Track B outcome](V0_6_8_TRACK_B_LARGE_STRAIN.md), [accepted CSV](../figures/TRACK_B_ACCEPTED_RESPONSE.csv), and [resource ledger](../performance/PERFORMANCE.json).','']
    groups={1:'Repository and provenance',8:'Track A — contact recovery',31:'Track B — demonstrator',
            61:'Mechanical response',81:'Scientific distinction',92:'Resources and tests',108:'Final decision'}
    for q in frozen:
        n=q['number']
        if n in groups:out+=['## '+groups[n],'']
        out+=[f'### {n}. {q["question"]}','',ANSWERS[n],'']
    out+=['## Independent acceptance statuses','','### Track A','','| Category | Status |','|---|---|']
    out += [f'| {k} | {v} |' for k,v in A.items()]
    out += ['','### Track B','','| Category | Status |','|---|---|']
    out += [f'| {k} | {v} |' for k,v in B.items()]
    out += ['','### Overall','','| Category | Status |','|---|---|']
    out += [f'| {k} | {v} |' for k,v in OVERALL.items()]
    out += ['','## Git commits through evidence phase','','The final reporting commit follows this generated ledger; its exact hash is reported in the terminal handoff.','']
    out += [f'- `{x["hash"]}` — {x["message"]}' for x in commits]
    out += ['','## Dr. Wang summary','','A separate 2.56 mm crop was run in real ANSYS through 1.5% solver convergence. Independent contact and geometry checks accept only 1.2575%; the next saved step loses pressure-bearing contact at an exterior crossing. The original full specimen remains accepted through 0.9271%. The 30–40% request remains open. Show the accepted crop curve and true-scale deformation with these limits, then repair contact before a high-compression claim.','','**STOP:** no 3D, manufacturing, batch design or autonomous LLM optimization was started.','']
    (RUN/'summary/V0_6_8_HANDOFF.md').write_text('\n'.join(out),encoding='utf-8',newline='\n')
    print('Rendered',len(frozen),'answers,',len(commits),'pre-report commits,',len(changes),'changed paths',flush=True)


if __name__=='__main__':main()
