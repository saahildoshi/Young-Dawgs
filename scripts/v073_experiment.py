"""One registered morphology-constrained target-property experiment; additive only."""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scripts.v070_protocol import REPO, read, write, sha
from metamaterial_eval.simulation.mesh_artifacts import artifact_root

RUN = REPO/'experiments/pipeline_v0.7.3/run_001'
DOC = REPO/'docs/pipeline_v0.7.3'
BASE = artifact_root()/'solver/v073/run_001'
PREV = REPO/'experiments/pipeline_v0.7.2/run_001'
REFERENCE = REPO/'experiments/pipeline_v0.7.0/run_002_real_microscopy/references/P3/evaluation_only_labels.npy'
TRIALS = ['IF_01','NF_01','NF_02','IF_02','IF_03','NF_03','NF_04','IF_04']
REQUEST = Path(r'C:\Users\sd22446\.codex\attachments\4059c573-f03d-4f73-aecc-71b4ab860563\Pasted text.txt')

def now(): return datetime.now(timezone.utc).isoformat()

def register():
    assert not RUN.exists() and not DOC.exists() and not BASE.exists()
    status=subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True)
    assert all(line=='?? scripts/v073_experiment.py' for line in status.splitlines()), status
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode().split('\0')
    protected={name:sha(REPO/name) for name in tracked if name}
    for name,digest in read(PREV/'summary/FINAL_PACKAGE_HASHES.json')['files'].items():
        assert sha(REPO/name)==digest,name
    original=PREV/'starting_generator/generator.py'
    assert sha(original)=='6917ffb0ca4f22fa5f8276d04484fdd3208978a0610cb43f3684b24cc18d270d'
    assert int((np.load(REFERENCE)==5).sum())==20731
    # Inventory every historical saved seed array, including worker copies and other families.
    inventory=[]; historical=set()
    for path in (REPO/'experiments').rglob('*.npy'):
        m=re.fullmatch(r'seed_(\d+)(?:_.*)?',path.stem)
        if m:
            historical.add(int(m[1])); inventory.append({'path':str(path.relative_to(REPO)), 'seed':int(m[1])})
    seeds={'calibration':list(range(3000,3012)), 'development':list(range(3100,3106)),
           'heldout':list(range(4000,4010)), 'H2':list(range(4000,4003))}
    assert not (set(sum([seeds[k] for k in ['calibration','development','heldout']],[]))&historical)
    RUN.mkdir(parents=True);DOC.mkdir(parents=True);BASE.mkdir(parents=True)
    write(RUN/'audit/PROTECTED_BEFORE.json',protected)
    write(RUN/'audit/HISTORICAL_SEED_INVENTORY.json',{'seed_arrays':inventory,'unique_seed_ids':sorted(historical),'collision':False})
    write(RUN/'audit/HISTORICAL_AUTHENTICATION.json',{'verified_v072_package_files':len(read(PREV/'summary/FINAL_PACKAGE_HASHES.json')['files']),
        'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'v072_status':read(PREV/'summary/FINAL_SCIENTIFIC_STATUS.json'),
        'v072_script_summaries':read(PREV/'optimization_analysis/SCRIPT_SUMMARIES.json'),
        'v072_feedback_comparison':read(PREV/'optimization_analysis/MF_VERSUS_NF.json'),
        'preservation':'New constraints are prospective; v072 original acceptance remains unchanged.'})
    prior=read(PREV/'protocol/PROTOCOL.json')
    p={'registered_utc':now(),'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'request_sha256':sha(REQUEST),'objective':'match prescribed apparent vertical modulus, not maximize stiffness',
        'reference':{'labels':{'1':'matrix-like solid','5':'provisional reinforcement-like solid / provisionally reprecipitated carbide'},
            'pixels':65536,'reinforcement_pixels':20731,'matrix_pixels':44805,'physical_pixel_scale':None,
            'source':'morphology-selected supplied HorizontalFlip augmented SEM crop; not unaugmented original or unbiased RVE',
            'visual_overlays_or_64px_ruler_in_geometry':False},
        'starting_generator':'P3_B02_EXACT_COMPOSITION_RESEARCHER_ADAPTATION_V073 if unchanged B02 not exact on calibration ensemble',
        'starting_source_sha256':sha(original),'envelope_policy':'Calibrate on reference, 12 new baseline seeds, analytical fixtures, historical observed lanes; freeze before new mechanics or model responses',
        'controlled_variants':'Six baseline development geometries plus four controlled variants with first three development seeds each; parameter matrix freezes before mechanics',
        'target_selection':{'fraction_toward_variant':.60,'direction':'prefer upward, otherwise downward',
            'selection':'Among families with 3/3 feasible, select largest positive mean difference supported by same-sign first-seed H2 effect exceeding sum of observed absolute H1/H2 changes; if no upward eligible, largest absolute downward difference. Ties: variant ID ascending.',
            'difficulty_gate':'Target separation must exceed max(2*baseline sample SD, 2*largest observed absolute development mesh change, 0.03*baseline mean). No target or extension if none qualifies; report valid feasibility outcome.',
            'rounding':'none','target_hit_tolerance_rule':'max(0.02, 2*maximum observed relative development H1/H2 change); tolerance must be less than half relative target-baseline separation, otherwise no target trial'},
        'primary_metric':'mean absolute relative target error within independent script, subject to 10/10 feasibility and diversity',
        'secondary_metrics':['absolute mean-property bias','signed bias','sample SD','CV','min/max','median and max target error','target hits / all attempted and / mechanically accepted','paired BASE error reduction'],
        'feedback_advantage_sign':'mean independent NF script error minus mean independent IF script error; positive favors IF',
        'invalid_policy':'Preserve every attempt; no repair, replacement, or favorable-seed selection. Conditional error excludes infeasible outputs with full denominators. No arm success claim from feasible survivors of unreliable generators.',
        'trial_order':TRIALS,'independent_trials_per_arm':4,'response_budget_per_trial':1,'repair_calls':0,'BF_included':False,
        'seed_manifest':'protocol/EVALUATOR_ONLY_SEEDS.json','heldout_policy':'Do not generate or disclose final seeds until all eight genuine modules and all experimental inputs collectively frozen',
        'generator_parameters':{},'generator_timeout_seconds':30,'generator_worker_timeout_seconds':75,
        'allowed_dependencies':prior['allowed_dependencies'],'candidate_limit':1000,
        'diversity':{'all_arrays_unique':True,'minimum_median_hamming':.1,'minimum_unique_rigid_invariant_signatures':5},
        'mechanical_evaluator_source':'scripts/v071_mechanics.py','mechanical_evaluator_sha256':sha(REPO/'scripts/v071_mechanics.py'),
        **{key:prior[key] for key in ['element','material','loading','strain_checkpoints','tolerances','NLGEOM']},
        'mechanics_route':'Five actual native checkpoints and independent readback for every accepted model; no scalar-only route',
        'secant_confirmation_relative_tolerance':1e-5,
        'development_H2':'First development seed of BASE and all four variants, feasible only; no substitutions',
        'heldout_H2':'First three evaluator-only heldout seeds for BASE and all eight revisions, feasible only; no substitutions',
        'horizontal_mechanics':False,'non_LLM_target_control':False,'F1_scope':'Optional separately registered bounded benchmark only after primary experiment or authentic submission gate; omitted from primary budget',
        'resource_limits':{'maximum_native_jobs':280,'native_campaign_seconds':14400,'solve_timeout_s':1800,'readback_timeout_s':900,
            'cores':2,'one_native_job':True,'rss_cap':None,'disk_reserve_bytes':50*2**30,'raw_storage_budget_bytes':150*2**30},
        'native_base':str(BASE),'model_policy':'Fresh ordinary ChatGPT chats; same exposed model/reasoning settings; no inferred backend identity or usage. No repair calls.',
        'human_submission_gate_if_unavailable':True,'push':False,'physical_calibration':False,'RVE_qualification':False}
    write(RUN/'protocol/PROTOCOL.json',p);write(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json',seeds)
    shutil.copyfile(REQUEST,RUN/'protocol/USER_REQUEST.txt')
    write(RUN/'audit/QUALIFIED_EVALUATOR.json',{str(path.relative_to(REPO)):sha(path) for path in [REPO/'scripts/v071_mechanics.py',REPO/'metamaterial_eval/simulation/composite_elastic.py']})
    (DOC/'V0_7_3_PROTOCOL.md').write_text('''# Registered v0.7.3 morphology-constrained inverse design

Match a data-selected apparent vertical modulus in P3 at exactly20,731 reinforcement pixels. The common starting generator retains B02 procedural morphology, with one explicitly researcher-prepared count adaptation if required. Historical experiments remain unchanged. New morphology limits are calibrated on the target, a new baseline ensemble, independent fixtures and known historical lane controls, then frozen before any new mechanical result or LLM revision.

Four independent IF and four independent NF ordinary-ChatGPT revisions, one response each, no repairs, no BF arm. Both arms receive identical starting source, target, mechanical assumptions, geometry definitions and structural data. IF additionally receives authentic paired development geometry–mechanics measurements. The shared mechanics-derived target itself conveys some information to both arms. Final seeds remain evaluator-only until collective source and protocol freeze. Every attempt is retained; infeasible outputs receive no mechanics and no invented target error. A fully qualified generator requires all ten outputs feasible and diverse. Scripts are independent units; seeds are nested.

The registered target rule selects60% of the distance from baseline toward the most separated eligible upward variant, or downward only if no upward option is eligible. Eligibility requires all three variant outputs feasible and first-seed H2 effect retaining sign and exceeding combined observed mesh changes. Target separation must exceed2 baseline SD,2 largest observed absolute development mesh change and3% of baseline mean. Target tolerance is max(2%, twice observed largest relative development mesh change) and must remain below half the target separation. No qualifying target means a truthful feasibility-study stop, without post-hoc expansion.

Six baseline and four variants×three geometries form the18-case development plan. First development seed in all five families gets H2. Ninety final structures are planned; every feasible geometry gets H1 and first three seeds per family H2, at most27 confirmations. All native cases use five actual solved checkpoints through0.5% and independent reopening of the unchanged qualified evaluator. PLANE182 plane stress, E1000/10000MPa, nu0.30, perfect shared-node bonding, free lateral expansion, bottomUY0/top negativeUY and one bottom-leftUX pin; NLGEOMOFF. Computational1mm square/thickness does not establish microscopy calibration. No RVE, physical calibration, natural-family identity guarantee or isotropic performance claim.

Maximum280 native processes, four aggregate native hours,150GiB raw storage,50GiB free reserve, two cores/one process, inherited health supervision and no fixed RSS cap. No pagefile changes or unrelated process termination. Optional F1 and horizontal loading are outside this primary campaign. No old porous/contact work, autonomous generations,3D or push. Stop after this single registered study, or at an authentic target-feasibility/model-submission gate.
''',encoding='utf-8',newline='\n')
    print('REGISTERED',len(protected),'protected files;',BASE,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['register']);args=parser.parse_args()
    register()
