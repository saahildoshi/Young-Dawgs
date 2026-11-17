"""Register the three required v074 deliverables, before any new model outcomes."""
import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from metamaterial_eval.simulation.mesh_artifacts import artifact_root

RUN=REPO/'experiments/pipeline_v0.7.4/run_001'
DOC=REPO/'docs/pipeline_v0.7.4'
ASSETS=REPO/'presentation_assets/v0.7.4'
BASE=artifact_root()/'solver/v074/run_001'
PREV=REPO/'experiments/pipeline_v0.7.3/run_001'
MICRO=REPO/'experiments/pipeline_v0.7.0/run_002_real_microscopy'
REQUEST=Path(r'C:\Users\sd22446\.codex\attachments\0010ea44-a206-4bc9-bd39-fabfca8a59b3\Pasted text.txt')

def now():return datetime.now(timezone.utc).isoformat()

def register():
    assert not RUN.exists() and not DOC.exists() and not ASSETS.exists() and not BASE.exists()
    status=subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True)
    assert status.strip()=='?? scripts/v074_experiment.py',status
    prior=read(PREV/'protocol/PROTOCOL.json');protected={name:sha(REPO/name) for name in subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode().split('\0') if name}
    for name,digest in read(PREV/'summary/FINAL_PACKAGE_HASHES.json')['files'].items():assert sha(REPO/name)==digest,name
    # All saved historical arrays plus every previously registered seed list.
    import re
    historical=set()
    for path in (REPO/'experiments').rglob('seed_*.npy'):
        match=re.match(r'seed_(\d+)',path.name)
        if match:historical.add(int(match[1]))
    for version in ['v0.7.2','v0.7.3']:
        seed=read(REPO/f'experiments/pipeline_{version}/run_001/protocol/EVALUATOR_ONLY_SEEDS.json')
        for values in seed.values():
            if isinstance(values,list):historical.update(x for x in values if isinstance(x,int))
    seeds={'common_calibration':list(range(4300,4306)),'verification':list(range(4100,4103)),
        'development':list(range(4200,4203)),'heldout':list(range(5000,5006)),'H2':list(range(5000,5002))}
    assert not set(sum([seeds[k] for k in ['common_calibration','verification','development','heldout']],[]))&historical
    rng=np.random.default_rng(74016);arms=['IF']*4+['NF']*4;rng.shuffle(arms)
    counters={'IF':0,'NF':0};order=[]
    for arm in arms:counters[arm]+=1;order.append(f'{arm}_{counters[arm]:02d}')
    RUN.mkdir(parents=True);DOC.mkdir(parents=True);ASSETS.mkdir(parents=True);BASE.mkdir(parents=True)
    write(RUN/'audit/PROTECTED_BEFORE.json',protected)
    write(RUN/'audit/HISTORICAL_AUTHENTICATION.json',{'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'v073_status':read(PREV/'summary/FINAL_SCIENTIFIC_STATUS.json'),'verified_prior_package_files':len(read(PREV/'summary/FINAL_PACKAGE_HASHES.json')['files']),
        'registered_and_observed_historical_seed_ids':sorted(historical),'no_seed_collisions':True,
        'free_disk_bytes':shutil.disk_usage(BASE).free,'previous_native_budget_evidence':read(PREV/'performance/FINAL_SUMMARY.json')})
    policy=RUN/'protocol/FEASIBILITY_FROZEN.json';policy.parent.mkdir(exist_ok=True);shutil.copyfile(PREV/'protocol/FEASIBILITY_FROZEN.json',policy)
    shutil.copyfile(REQUEST,RUN/'protocol/USER_REQUEST.txt')
    p={'registered_utc':now(),'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'request_sha256':sha(REQUEST),'target_MPa':1640.,'J_target':1.640,'target_hit_tolerance':.02,'target_band_MPa':[1607.2,1672.8],
        'target_selection':'User-specified prospective target supported by authenticated v073 horizontal-family measurements; no old two-SD gate reapplied',
        'primary_metric':'Per-script mean absolute relative target error, conditional on feasibility with full attempted denominators; 6/6 required for full generator qualification',
        'secondary_metrics':['within-conversation initial-minus-revised target error','mean-property bias','median error','sample SD','hit rate','validity','diversity','H1/H2 sensitivity'],
        'arm_comparison':'Mean independent NF final-script error minus mean independent IF final-script error; positive favors IF. Also compare per-conversation error reductions. Missing/invalid scores null, never zero.',
        'initial_variation':'Identical prompt/reference/common source template, but actual independent initial responses may differ. Do not claim common-source paired design.',
        'trial_order':order,'randomization_seed':74016,'independent_conversations_per_arm':4,'initial_turns_per_trial':1,'followup_turns_per_trial':1,
        'same_conversation_required':True,'repairs':False,'additional_rounds':False,'model_policy':'Ordinary persistent ChatGPT chats, one initial and one continuation in each original URL; exposed model/reasoning consistent, backend/personalization limitations recorded',
        'initial_prompt_images':'Authenticated raw P3 microscopy input; segmentation mask remains evaluator-only. Common source/structural descriptions may be supplied identically.',
        'phase_map':{'1':'matrix-like solid / native MAT1','5':'provisional reinforcement-like solid / native MAT2'},
        'exact_reinforcement_count':20731,'exact_matrix_count':44805,'microscopy_physical_pixel_scale':None,
        'morphology_policy_sha256':sha(policy),'morphology_policy':'Byte-identical v073 numerical envelope; cohort all-valid criterion adapted to six final seeds without changing per-array thresholds',
        'starting_candidate_maximum':8,'generator_parameters':{},'single_generation_timeout_seconds':30,'worker_timeout_seconds':75,
        'allowed_dependencies':prior['allowed_dependencies'],'generator_failure_policy':'Bounded explicit failure preserved; evaluator never repairs or substitutes seeds',
        'heldout_policy':'No final generation before all16 authentic initial/revised modules plus prompts/protocol collectively frozen; no final seeds/results reach any model',
        'H2_selection':'First two final heldout seeds of every initial and revised script, feasible only; no substitutions or favorable expansion',
        'native_base':str(BASE),**{k:prior[k] for k in ['element','material','loading','strain_checkpoints','tolerances','NLGEOM']},
        'native_route':'Five actual native solved checkpoints and independent RST reopening for every accepted model',
        'resource_limits':{'maximum_native_jobs':350,'native_campaign_seconds':18000,'solve_timeout_s':1800,'readback_timeout_s':900,
            'cores':2,'one_native_job':True,'rss_cap':None,'disk_reserve_bytes':70*2**30,'raw_storage_budget_bytes':200*2**30},
        'planned_P3_maximum_source_models':152,'estimated_total_sources_including_F1_and_directional':162,
        'F1':{'required':True,'labels':{'0':'matrix solid MAT1','1':'transverse fiber-like solid MAT2','2':'void; no elements'},
            'material_protocol':'F1_ILLUSTRATIVE_TRANSVERSE_TWO_SOLIDS_AND_EXPLICIT_VOID','properties_MPa':{'1':1000.,'2':10000.},'nu':.30,
            'controls':['homogeneous rectangle','parallel two-material rectangle','two disconnected-by-void load-carrying vertical strips, each minimally restrained'],
            'reference':'F1 evaluation_only_labels.npy','generated':'F1_B_02/r0/seed0','refinement':'H1 and H2 reference and selected generated source if mechanical connectivity qualifies',
            'island_policy':'No removal/filling/weak springs; audit edge and node connectivity. Only unloaded floating islands may be explicitly minimally grounded as a separately documented physical assumption; otherwise HOLD that configuration.'},
        'directional_extension':{'source_partition':'v073 development seed3100','families':['BASE','V2_VERTICAL','V3_HORIZONTAL'],
            'vertical':'Reuse authentic previous H1 result','horizontal':'Rotate unchanged source by90degrees, identical evaluator, H1; transformed-domain x loading and free transverse displacement. Record phase/source maps; not a homogenized tensor.'},
        'STL':{'required':True,'source':'Authenticated P3 reference annotation','field_mm':160.,'border_mm':4.,'outer_mm':168.,'base_mm':2.4,'relief_mm':1.2,
            'nozzle_assumption_mm':.4,'layer_height_mm':.2,'minimum_detail_goal_mm':.8,
            'exact':'Preserve XY pixel support; explicitly diagnose point-only connections and small details',
            'print_ready':'If needed, registered 3x3 square binary opening then closing within field; retain source unchanged, quantify every changed pixel/region and preserve small-feature diagnostics. No outcome-based aesthetic redraw.',
            'geometry':'Single coherent height-field boundary surface, no internal overlapped shells; independent STL re-import and edge/link/volume/intersection validation',
            'slicer':'Search installed supported slicers and slice if available; otherwise mark NOT_VERIFIED; no actual printer assumed',
            'interpretation':'Enlarged educational relief, arbitrary presentation XY/Z scale, no genuine3D reconstruction or mechanical specimen'},
        'prohibited':['old contact campaign','large strain','3D mechanical FEM','manufacturing claims','automatic push','post-heldout model calls'],
        'human_submission_gate':'If actual UI unavailable, preserve exact chat URL and next same-chat message; still complete required F1 and STL'}
    write(RUN/'protocol/PROTOCOL.json',p);write(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json',seeds)
    write(RUN/'audit/QUALIFIED_EVALUATOR.json',{str(f.relative_to(REPO)):sha(f) for f in [REPO/'scripts/v071_mechanics.py',REPO/'metamaterial_eval/simulation/composite_elastic.py',REPO/'metamaterial_eval/composites/morphology_v073.py']})
    (DOC/'V0_7_4_PROTOCOL.md').write_text('''# Registered v0.7.4 three-deliverable study

P3: target1640MPa, ±2%, unchanged illustrative plane-stress materials, exact20,731 reinforcement pixels and byte-identical v073 morphology policy. The primary outcome is script-level mean absolute target error, with feasibility and attempted denominators retained. No v073 two-SD difficulty gate is applied. Four IF/four NF conversations are assigned before any response, each one genuine initial generator and one revision in that SAME persistent ordinary ChatGPT conversation. Initial sources may differ; before/after comparisons are within conversations, seeds nested. No repairs, hidden seed leakage, selective retries or extra revisions. Initial-generation information is common; follow-up structural data are matched, while actual measured mechanics and historical geometry–mechanics evidence are IF-only. All scripts freeze before final evaluation. The first two final seeds per initial/revised script get H2 if feasible.

The new common template uses at most8 deterministic geometry-only candidates from inherited B02 exact-count generation, checking the unchanged structural limits internally. Its researcher origin is explicit; actual initial assistant responses are separately captured. New seed partitions, protocol and trial order are frozen in JSON before submission.

F1 is required: distinct matrix0, transverse fiber1 and void2; no solid element in void. Separate illustrative properties, native homogeneous/two-material/void controls, source connectivity audit, reference and predetermined archived F1_B_02/r0/seed0, actual curves and independent readbacks. No geometry repairs, hidden weak springs or nonlinear contact. H2 on reference/generated if qualified. Three predetermined historical P3 sources receive new horizontal diagnostics; vertical results are reused.

The required presentation prop is a168mm square plaque with160mm reference field,4mm border,2.4mm base and1.2mm relief. Exact and, if needed, explicitly simplified print versions retain authenticated provenance. A single boundary solid is re-imported and validated, with actual STL-derived previews and printing instructions. Printer assumptions are0.4mm nozzle/0.2mm layers; no actual printer, slicer success, physical print or material calibration is assumed.

Budget: at most350 native processes, five aggregate native hours,200GiB raw artifacts,70GiB free reserve, two cores/one native job, inherited system-health monitoring, no fixed RSS cap. Planned maximum162 source models includes152 P3, seven F1 and three directional models. No old native reruns merely for feedback. All prior evidence remains unchanged. Actual UI blockage can stop model submission, but must not defer required F1/STL work. Commit coherent results, do not push, and stop after this single registered study.
''',encoding='utf-8',newline='\n')
    print('REGISTERED',len(protected),'protected files; trial order',order,'native root',BASE,flush=True)

if __name__=='__main__':register()
