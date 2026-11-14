"""Explicit, single-generation P3 mechanical-feedback experiment and provenance."""
import argparse
import hashlib
import importlib.util
import itertools
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.spatial.distance import pdist
from skimage.measure import regionprops
from PIL import Image
from scripts.v070_protocol import REPO, read, write, sha
from scripts.v070_experiment import audit
from metamaterial_eval.composites.microscopy import describe, errors, VISIBLE, HIDDEN
from metamaterial_eval.simulation.mesh_artifacts import artifact_root

RUN = REPO/'experiments/pipeline_v0.7.2/run_001'
DOC = REPO/'docs/pipeline_v0.7.2'
BASE = artifact_root()/'solver/v072/run_001'
OLD = REPO/'experiments/pipeline_v0.7.0/run_002_real_microscopy'
TRIALS = ['P3_OPT_MF_01','P3_OPT_NF_01','P3_OPT_NF_02','P3_OPT_MF_02']


def now(): return datetime.now(timezone.utc).isoformat()


def register():
    assert not RUN.exists() and not DOC.exists() and not BASE.exists()
    status=subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True)
    assert all(line=='?? scripts/v072_experiment.py' for line in status.splitlines()),status
    RUN.mkdir(parents=True); DOC.mkdir(parents=True); BASE.mkdir(parents=True)
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode().split('\0')
    protected={s:sha(REPO/s) for s in tracked if s}
    write(RUN/'audit/PROTECTED_BEFORE.json',protected)
    source=OLD/'llm_trials/P3_B_02/generator_r0.py'
    receipt=read(source.parent/'RECEIPT_r0.json')
    assert sha(source)==receipt['code_sha256']
    history_seeds=sorted({int(p.stem.split('_')[1]) for p in (OLD/'llm_trials').glob('P3_*/evaluation_*/seed_*.npy')})
    dev=list(range(1000,1006)); held=list(range(2000,2010))
    assert not (set(dev+held)&set(history_seeds))
    labels=np.load(OLD/'references/P3/evaluation_only_labels.npy',allow_pickle=False)
    target=int(np.count_nonzero(labels==5))
    prior=read(REPO/'experiments/pipeline_v0.7.1/run_001/protocol/PROTOCOL.json')
    source_copy=RUN/'starting_generator/generator.py';source_copy.parent.mkdir()
    shutil.copyfile(source,source_copy)
    protocol={'registered_utc':now(),'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'request_sha256':sha(Path(r'C:\Users\sd22446\.codex\attachments\33ff8f78-89e6-4491-87fa-376cd85e7925\Pasted text.txt')),
        'objective':'maximize J = apparent vertical elastic modulus / 1000 MPa',
        'starting_generator_policy':'B02 preferred; C02/r1 fallback based only on development structural feasibility; explicit common adaptation only if neither feasible',
        'reference_count':target,'reference_fraction':target/65536,'composition_maximum_absolute_fraction_tolerance':.001,
        'development_seeds':dev,'heldout_seed_manifest':'protocol/EVALUATOR_ONLY_SEEDS.json',
        'trial_order':TRIALS,'independent_trials_per_arm':2,'response_budget_per_trial':1,'repair_calls':0,
        'heldout_policy':'No final generation before all four authentic responses and frozen scripts; evaluator-only seeds never enter prompts',
        'history_seed_collision_check':{'historical_P3_seed_ids':history_seeds,'new_partitions_disjoint':True},
        'mechanical_protocol_source':'experiments/pipeline_v0.7.1/run_001/protocol/PROTOCOL.json',
        'mechanical_protocol_sha256':sha(REPO/'experiments/pipeline_v0.7.1/run_001/protocol/PROTOCOL.json'),
        **{key:prior[key] for key in ['element','material','loading','strain_checkpoints','tolerances','NLGEOM']},
        'mechanics_route':'Five actual native checkpoints and independent RST reopening for EVERY accepted geometry; no separate one-point-only screening route',
        'secant_confirmation_relative_tolerance':1e-5,
        'H2_selection':'First three registered held-out seeds, every script including BASE; no outcome-based subset; no optional expansion in this run',
        'full_curve_selection':'All feasible development, H1 heldout, and H2 confirmation geometries',
        'resource_limits':{'maximum_native_jobs':150,'native_campaign_seconds':10800,'solve_timeout_s':1800,'readback_timeout_s':900,
            'cores':2,'one_native_job':True,'rss_cap':None,'disk_reserve_bytes':50*2**30,'raw_storage_budget_bytes':120*2**30},
        'generator_parameters':{},'generator_timeout_seconds':30,'generator_total_worker_timeout_seconds':700,
        'allowed_dependencies':read(REPO/'experiments/pipeline_v0.7.0/run_001/protocol/PROTOCOL.json')['generator_dependencies'],
        'internal_search_limit':'At most 1000 full-domain candidate arrays per output; bounded geometry-only scoring, no mechanics/cache access; wall limit applies to all',
        'model_policy':'Independent ordinary ChatGPT chats, consistent exposed configuration; backend/memory routing not inferred',
        'human_submission_gate_if_unavailable':True,'push':False,'physical_calibration':False,'RVE_qualification':False,
        'previous_native_artifact_root':prior['native_base'],'native_base':str(BASE)}
    write(RUN/'protocol/PROTOCOL.json',protocol)
    write(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json',{'development':dev,'heldout':held,'H2':held[:3],'not_for_model_prompts':True})
    write(RUN/'starting_generator/CANDIDATE_AUTHENTICATION.json',{'source_path':str(source.relative_to(REPO)),'source_sha256':sha(source),
        'captured_LLM_receipt_sha256':sha(source.parent/'RECEIPT_r0.json'),'common_copy_sha256':sha(source_copy),'adapted':False})
    write(RUN/'audit/QUALIFIED_EVALUATOR.json',{str(p.relative_to(REPO)):sha(p) for p in [
        REPO/'scripts/v071_mechanics.py',REPO/'metamaterial_eval/simulation/composite_elastic.py',
        REPO/'experiments/pipeline_v0.7.1/run_001/summary/FINAL_PACKAGE_HASHES.json']})
    (DOC/'V0_7_2_PROTOCOL.md').write_text('''# Registered v0.7.2 controlled mechanical-feedback pilot

Maximize normalized finite-domain apparent vertical stiffness at fixed composition in dispersed P3 inclusions. Four independent ordinary-ChatGPT revisions share one authenticated starting generator: two measured-mechanical-feedback (MF), two no-mechanical-feedback (NF), one response each, no repair calls. Seeds are nested within scripts. This is one registered generation, not autonomous multigeneration optimization.

Six new development realizations establish structural feasibility before the final numeric morphology envelope and composition tolerance are frozen. B02 is preferred; C02/r1 is the prospectively allowed structural-only fallback. No selection uses new mechanical outcomes. Final guardrails must freeze before any ANSYS development mechanics or model call. The exact reference count is measured from the authenticated mask; no mask enters model input.

Every mechanically evaluated geometry receives five actual native ANSYS checkpoints through 0.5% and an independent result reopening using the unchanged v0.7.1 qualifier. We deliberately retain full curves rather than introduce a new single-point acceptance route. Final-point secant versus fitted modulus is checked. H1 is one element per pixel; H2 subdivides each unchanged pixel into four. The first three held-out seeds for all five scripts receive H2, prospectively, with no outcome-based expansion.

The evaluator-only seed partition is frozen separately; its held-out values never enter model prompts. Final generation waits until all four authentic responses and code hashes are frozen. All ten final outputs must pass the hard constraints for a fully qualified stochastic generator. Invalid outputs are retained, never repaired or replaced. MF/NF receive identical starting code, objective, material assumptions, structural data and computational budgets; only MF receives actual measured mechanical evidence. Prompt hashes and a difference audit precede submission.

Reuse PLANE182 full integration B-bar, plane stress, E=1000/10000 MPa, nu=0.30, shared nodes, free lateral expansion, bottom UY zero/top negative UY and one bottom-left UX pin. The 1 mm square/thickness is a computational convention, not microscopy calibration. No physical chemistry, calibration, RVE, isotropic or experimental-performance claim. Shared pixel corner contacts are numerical connections, not verified physical bonds. No F1 mechanics or old porous/contact campaign.

Finite budget: 150 native processes, 3 hours aggregate native time, two cores/one job, existing health monitoring, 50 GiB disk reserve, 120 GiB raw-artifact budget, no fixed RSS cap. Inputs, failed attempts and native evidence are preserved outside Git. No automatic push. If genuine independent model execution is unavailable, complete baseline measurements and exact packets and stop at the explicitly labeled human-submission gate.
''',encoding='utf-8',newline='\n')
    print('REGISTERED',RUN,'protected',len(protected),'target pixels',target,flush=True)


def topology(mask,connectivity):
    lab,n=ndi.label(mask,ndi.generate_binary_structure(2,connectivity));counts=np.bincount(lab.ravel())[1:]
    def spans(a,b):return bool((set(np.unique(a))&set(np.unique(b)))-{0})
    return {'regions':int(n),'largest_fraction':float(counts.max()/mask.sum()) if counts.size else 0.,
        'spans_y':spans(lab[0],lab[-1]),'spans_x':spans(lab[:,0],lab[:,-1]),
        'one_pixel_area_fraction':float(counts[counts==1].sum()/mask.sum()) if counts.size else 0.}


def observe(a):
    d=describe(a,'P3')
    return {'phase_counts':{str(k):int((a==k).sum()) for k in [1,5]},'descriptors':d,
        'topology':{f'{phase}_{conn}':topology(a==value,conn) for phase,value in [('matrix',1),('reinforcement',5)] for conn in [1,2]}}


def feasibility(row,policy):
    if row.get('status')!='GENERATED':return {'passed':False,'failures':['generation_or_output_contract_failed']}
    d,t=row['descriptors'],row['topology'];rules=policy['guardrails']
    checks={'phase_count':abs(row['phase_counts']['5']-policy['target_count'])<=policy['absolute_pixel_tolerance'],
        'both_phases':all(row['phase_counts'][str(k)]>0 for k in [1,5]),
        'runtime':row['generation_seconds']<=policy['single_generation_timeout_seconds'],
        'deterministic':row['deterministic'],
        'matrix_lcc':t['matrix_1']['largest_fraction']>=rules['matrix_lcc_minimum'],
        'matrix_spans_both':t['matrix_1']['spans_x'] and t['matrix_1']['spans_y'],
        'no_reinforcement_4_spanning':not(t['reinforcement_1']['spans_x'] or t['reinforcement_1']['spans_y']),
        'no_reinforcement_8_spanning':not(t['reinforcement_2']['spans_x'] or t['reinforcement_2']['spans_y']),
        'no_dominant_4_region':t['reinforcement_1']['largest_fraction']<=rules['reinforcement_largest_fraction_maximum'],
        'no_dominant_8_region':t['reinforcement_2']['largest_fraction']<=rules['reinforcement_largest_fraction_maximum'],
        'single_pixel_noise':t['reinforcement_1']['one_pixel_area_fraction']<=rules['single_pixel_reinforcement_fraction_maximum']}
    for metric,bounds in rules['descriptor_ranges'].items():
        value=d.get(metric);checks[metric]=value is not None and bounds[0]<=value<=bounds[1]
    return {'passed':all(checks.values()),'checks':checks,'failures':[k for k,v in checks.items() if not v]}


def arrangement_signature(a):
    lab,_=ndi.label(a==5)
    regions=regionprops(lab)
    centers=np.array([r.centroid for r in regions])
    signature={'areas':sorted(int(r.area) for r in regions),'pairwise_centroid_distances':np.round(np.sort(pdist(centers)),5).tolist()}
    return hashlib.sha256(str(signature).encode()).hexdigest()


def diversity(arrays,policy):
    n=len(arrays);hashes=[hashlib.sha256(a.tobytes()).hexdigest() for a in arrays]
    distances=[float(np.mean(a!=b)) for a,b in itertools.combinations(arrays,2)]
    signatures=[arrangement_signature(a) for a in arrays]
    return {'outputs':n,'unique_arrays':len(set(hashes)),'unique_arrangement_signatures':len(set(signatures)),
        'median_pairwise_hamming':float(np.median(distances)) if distances else None,
        'minimum_pairwise_hamming':min(distances) if distances else None,
        'passed':bool(n>=2 and len(set(hashes))==n and len(set(signatures))>=int(np.ceil(n/2)) and np.median(distances)>=policy['diversity']['minimum_median_hamming']),
        'signature_limitation':'Region areas and pairwise centroid distances are rigid-motion invariants; boundary clipping and region merging can alter signatures. Diagnostic, not proof of distributional diversity.'}


def freeze_feasibility():
    path=RUN/'protocol/FEASIBILITY_FROZEN.json';assert not path.exists()
    p=read(RUN/'protocol/PROTOCOL.json')
    policy={'frozen_utc':now(),'target_count':p['reference_count'],'target_fraction':p['reference_fraction'],
        'absolute_pixel_tolerance':64,'absolute_fraction_tolerance':64/65536,
        'composition_rationale':'Unchanged B02 development counts deviate at most 53 pixels; 64-pixel ceiling is below the requested 0.001 maximum. No post-generation count correction. Exact counts preferred for revisions but identical acceptance for all arms.',
        'single_generation_timeout_seconds':30,'generator_acceptance':'10/10 held-out outputs feasible and diversity passes; partial validity reported with denominator',
        'guardrails':{'matrix_lcc_minimum':.95,'reinforcement_largest_fraction_maximum':.15,
            'single_pixel_reinforcement_fraction_maximum':.001,
            'descriptor_ranges':{'complete_regions':[40,75],'all_regions':[50,125],'boundary_censored_regions':[5,50],
                'diameter_mean_px':[12,20],'aspect_mean':[1.2,3.0]}},
        'connectivity_policy':'4-connected matrix must span x/y; reinforcement prohibited from spanning under both 4 and 8 connectivity. Largest reinforcement fraction <=0.15 under both. Corner contacts retained as mesh artifact, never claimed physical bonds.',
        'diversity':{'all_arrays_unique':True,'minimum_median_hamming':.1,'minimum_unique_rigid_invariant_signatures':'ceil(number_outputs/2)'},
        'selection':'Unchanged captured P3_B_02/r0; no fallback or adaptation needed',
        'selection_basis':'Six development structural observations and reference only, before any new mechanics or revisions',
        'guardrail_rationale':'Reference complete/all/boundary counts57/78/21, diameter15.7067px, aspect1.916, matrixLCC0.9906. B02 six development complete57, all77-80, boundary20-23, diameter15.6855-15.7349px, aspect1.826-2.157. Broad ranges allow meaningful rearrangement and shape changes without bands/noise.',
        'composition_claim_limit':'Residual count variation forbids strong geometry-only attribution without separately registered exact-composition confirmation or numerical composition sensitivity. No guessed correction.'}
    rows=read(RUN/'baseline_development/OBSERVATIONS.json')
    for row in rows:
        row['feasibility']=feasibility(row,policy)
        assert row['feasibility']['passed'],row
        write(RUN/f'baseline_development/seed_{row["seed"]}.json',row)
    arrays=[np.load(RUN/f'baseline_development/seed_{r["seed"]}.npy',allow_pickle=False) for r in rows]
    div=diversity(arrays,policy);assert div['passed']
    write(RUN/'baseline_development/OBSERVATIONS.json',rows);write(RUN/'baseline_development/DIVERSITY.json',div)
    write(path,policy)
    auth=read(RUN/'starting_generator/CANDIDATE_AUTHENTICATION.json')
    write(RUN/'starting_generator/COMMON_STARTING_POINT_FROZEN.json',{'frozen_utc':now(),**auth,
        'selected_id':'P3_B_02/r0','parameters':{},'composition_morphology_sha256':sha(path),
        'protocol_sha256':sha(RUN/'protocol/PROTOCOL.json'),'evaluator_only_seed_partition_sha256':sha(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json'),
        'source_code_file':'starting_generator/generator.py','independent_scripts':4,'heldout_evaluation_started':False})
    print('FROZEN baseline feasibility6/6; diversity',div,'tolerance64 pixels',flush=True)


def generate(source,destination,seeds):
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=False)
    review=audit(Path(source).read_text(encoding='utf-8-sig'));write(destination/'CODE_AUDIT.json',review)
    if not review['passed']:raise ValueError(review)
    spec=importlib.util.spec_from_file_location('v072_returned_generator',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    rows=[]
    for seed in seeds:
        started=time.perf_counter();row={'seed':seed,'generator_sha256':sha(source),'status':'EXECUTION_ERROR'}
        try:
            t=time.perf_counter();a=module.generate_microstructure(seed,{});elapsed=time.perf_counter()-t
            b=module.generate_microstructure(seed,{})
            if not np.array_equal(a,b):raise ValueError('Same-seed determinism failed')
            np.save(destination/f'seed_{seed}.npy',a,allow_pickle=False)
            row.update(status='GENERATED',deterministic=True,generation_seconds=elapsed,array_file_sha256=sha(destination/f'seed_{seed}.npy'),
                array_bytes_sha256=hashlib.sha256(a.tobytes()).hexdigest(),**observe(a))
            Image.fromarray(np.where(a==5,255,0).astype(np.uint8)).save(destination/f'seed_{seed}.png')
        except Exception as e:row['error']=repr(e)
        row['repeat_and_measure_seconds']=time.perf_counter()-started
        write(destination/f'seed_{seed}.json',row);rows.append(row)
        print(seed,row['status'],row.get('phase_counts'),flush=True)
    write(destination/'OBSERVATIONS.json',rows)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action');p.add_argument('args',nargs='*');a=p.parse_args()
    if a.action=='register':register()
    elif a.action=='generate':generate(Path(a.args[0]),Path(a.args[1]),list(map(int,a.args[2].split(','))))
    elif a.action=='freeze_feasibility':freeze_feasibility()
