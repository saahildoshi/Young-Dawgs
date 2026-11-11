"""Register and run actual independently captured ChatGPT microscopy scripts."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image
from scripts.v070_protocol import REPO, read, write, sha
from scripts.v070_experiment import audit
from scripts.v070_reference_preparation import PREP
from metamaterial_eval.composites.microscopy import LABELS, SCALES, VISIBLE, HIDDEN, describe, validate, validity, errors, categorical_diversity
from metamaterial_eval.pipeline.scripts import extract_python_script

RUN = REPO / 'experiments/pipeline_v0.7.0/run_002_real_microscopy'
DOC = REPO / 'docs/pipeline_v0.7.0/run_002_real_microscopy'
BASE = '''Study the attached real microscopy crop and infer a stochastic procedural model of its morphological family. Generate fresh statistically similar realizations, not copied coordinates or matching target pixels. Only the microscopy image is supplied visually; segmentation masks are withheld for evaluation.
Return one complete Python module in one python code block, preferably <=90 lines. Required interface: generate_microstructure(seed, parameters) returns a NumPy ndarray of shape(256,256), dtype uint8, with the categorical labels defined below. parameters is an empty dict. Use a local numpy.random.default_rng(seed). Same seed must reproduce exactly; different seeds must change the actual arrangement and geometry, not merely translate/rotate a fixed pattern. Finite nonperiodic boundaries; allow boundary-clipped features. Keep every defined phase nonempty. No requirement for matrix or reinforcement spanning paths.
Allowed imports: numpy, scipy, skimage, PIL, math, random, collections, itertools. No file/network/subprocess/API access, reference loading, embedded raster/coordinate tracing, global random seeding, plotting, tests/demos/printing or generation at import. Module scope may contain only imports, function definitions and literal constants. No tools, browsing or external reference retrieval. Use bounded loops; less than10 seconds per realization. Return code only. One initial attempt, no repairs outside the registered feedback condition. Do not invent physical calibration or mechanical properties.'''
DEFINITION = {
 'P3': '''Family P3: Ni-WC composite matrix-rich SEM field with dispersed irregular secondary-carbide annotation regions. Output native labels1=Ni-alloy matrix region,5=provisionally identified reprecipitated-carbide regions. Label5 is a provisional interpretation, not a fully verified physical phase. Both labels represent material regions; no void label occurs in this selected crop. Preserve IDs1 and5. The supplied tile is a genuine horizontally flipped geometry-preserving microscopy augmentation, not an unaugmented original. This morphology-selected crop is not an unbiased representative volume element. Physical micrometers per pixel are unknown.''',
 'F1': '''Family F1: original C/PEEK transverse carbon-fiber microscopy cross-section. Output labels0=PEEK matrix,1=carbon-fiber cross-sections,2=void. Matrix and fiber are solids; void is distinct. Preserve all three labels. Model cross-sectional packing and small approximately circular fiber sections, not longitudinal lines or an in-plane fiber-axis orientation. Evaluator fiber annotations approximate detected centers with mean-radius circles; touching circles can merge into annotation regions. Void annotations also have segmentation uncertainty. Physical micrometers per pixel are unknown.'''}
METRIC_DEFINITION = '''Lengths are pixels. Fractions divide by65536. Regions use4-connectivity; complete regions exclude every region touching any image border. Diameter=2*sqrt(region_area/pi), with population mean/std over complete regions; counts/diameters/spacing describe connected annotations, not physically recovered touching-particle/fiber instances. No longitudinal fiber metrics. These values describe the withheld annotation, with the stated uncertainty.'''


def register():
    RUN.mkdir(parents=True,exist_ok=False);DOC.mkdir(parents=True,exist_ok=False)
    old = {str(p.relative_to(REPO)).replace('\\','/'):sha(p) for root in [REPO/'experiments/pipeline_v0.7.0/run_001', PREP, REPO/'experiments/pipeline_v0.7.0/reference_correction_001'] for p in root.rglob('*') if p.is_file()}
    write(RUN/'audit/PRIOR_EVIDENCE_HASHES.json',old)
    p = {'registered_utc':datetime.now(timezone.utc).isoformat(), 'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
         'status':'APPROVED_REFERENCES_FROZEN_BEFORE_MODEL_OUTCOMES', 'references':['P3','F1'], 'shape':[256,256], 'dtype':'uint8',
         'native_labels':LABELS, 'P3_derived_working_mapping':{'1':0,'5':1},
         'P3_approval':'User explicitly accepts provisional label5 and HorizontalFlip augmentation; morphology-based selection bias disclosed; not unbiased RVE',
         'F1_approval':'Original C/PEEK with matrix0 fiber1 void2, transverse descriptors and approximate circle uncertainty',
         'physical_um_per_pixel':None, 'mechanical_properties':None, 'matrix_connectivity_hard_requirement':False,
         'hard_validity':['ndarray','shape256x256','uint8','only_family_native_labels','all_target_phases_nonempty','repeat_seed_determinism'],
         'visible_metrics':VISIBLE, 'hidden_metrics':HIDDEN, 'normalization_scales':SCALES,
         'error_definition':'Absolute difference/fixed scale; equal mean within visible/hidden groups; any missing required value makes full group unavailable; coverage and partial diagnostic separately reported. No overall composite success score.',
         'conditions':['A_image_only','B_image_plus_descriptors','C_B_plus_one_development_feedback'],
         'independent_scripts_per_family_condition':2, 'initial_calls':12, 'maximum_calls':16, 'feedback_calls_per_C':1, 'repair_calls':0,
         'order':['P3_A_01','F1_A_01','P3_A_02','F1_A_02','P3_B_01','F1_B_01','P3_B_02','F1_B_02','P3_C_01','F1_C_01','P3_C_02','F1_C_02'],
         'development_seeds':list(range(100,110)), 'heldout_seeds':list(range(10)),
         'heldout_policy':'Do not execute final heldout seeds until every script and revision is frozen; feedback uses development only',
         'seed_timeout_seconds':30, 'module_timeout_seconds':240, 'single_realization_requested_seconds':10, 'mode':'ORDINARY_CHATGPT_CHAT_NOT_WORK_OR_CODEX',
         'fresh_initial_chat':True, 'chat_folder':'Pipeline Tests',
         'organization':'Initial chats outside project; file completed chats in Pipeline Tests afterward when feasible. Account memory/personalization/backend routing not independently controlled.',
         'unit':'Independently returned LLM script; seeds nested; C revision paired to parent script, not an independent trial',
         'feedback_confound':'C receives extra interaction; no equal-attempt no-feedback control, so feedback-only causal claims are unsupported',
         'solver_jobs':0,'automatic_push':False}
    write(RUN/'protocol/PROTOCOL.json',p)
    origins = {'P3': (PREP/'particle/P3_NiWC_dispersed_reprecipitates/MICROGRAPH_256.png', PREP/'particle/P3_NiWC_dispersed_reprecipitates/NATIVE_LABELS_256.npy'),
               'F1': (PREP/'fiber/F1_transverse_CPEEK/llm_image_only/ORIGINAL_MICROGRAPH_256.png', PREP/'fiber/F1_transverse_CPEEK/evaluation_only/NATIVE_LABELS_256.npy')}
    for family,(image,mask) in origins.items():
        d = RUN/'references'/family;d.mkdir(parents=True)
        shutil.copyfile(image,d/'microscopy_input.png');shutil.copyfile(mask,d/'evaluation_only_labels.npy')
        target = describe(np.load(mask,allow_pickle=False),family);write(d/'descriptors.json',target)
        write(d/'INPUT_MANIFEST.json',{'family':family,'approved':True,'image_origin':str(image.relative_to(REPO)), 'image_sha256':sha(image),
                                      'mask_origin':str(mask.relative_to(REPO)), 'mask_sha256':sha(mask), 'mask_evaluator_only':True,
                                      'added_overlay_ruler_text':False,'physical_um_per_pixel':None,'phase_definition':DEFINITION[family]})
        for condition in ['A','B','C']:
            for index in [1,2]:
                trial=f'{family}_{condition}_{index:02d}';td=RUN/'llm_trials'/trial;td.mkdir(parents=True)
                prompt=BASE+'\n'+DEFINITION[family]
                if condition!='A':
                    prompt+='\nPreselected annotation descriptor targets:\n'+json.dumps({k:target[k] for k in VISIBLE[family]},sort_keys=True)+'\n'+METRIC_DEFINITION
                (td/'prompt.txt').write_text(prompt+'\n',encoding='utf-8',newline='\n')
                write(td/'manifest.json',{'trial_id':trial,'family':family,'condition':condition,'independent_initial_trial':index,'status':'NOT_RUN',
                                         'prompt_sha256':sha(td/'prompt.txt'),'image_sha256':sha(image),'model':None,'chat_url':None,'revision_budget':1 if condition=='C' else 0})
    write(RUN/'protocol/FROZEN_HASHES.json',{'protocol_sha256':sha(RUN/'protocol/PROTOCOL.json'),
                                          'descriptor_code':{str(f.relative_to(REPO)):sha(f) for f in [REPO/'metamaterial_eval/composites/microscopy.py',REPO/'metamaterial_eval/composites/transverse.py',REPO/'metamaterial_eval/composites/descriptors.py',REPO/'metamaterial_eval/metrics.py']},
                                          'prompts':{str(f.relative_to(RUN)):sha(f) for f in RUN.glob('llm_trials/*/prompt.txt')}})
    print('Frozen approved P3+F1 experiment before any new model outcomes;12 initial calls,4 C revisions maximum.')


def ingest(trial,response,url,revision=0,submitted=None):
    d=RUN/'llm_trials'/trial;raw=d/f'response_r{revision}.txt'
    if raw.exists():raise FileExistsError(raw)
    shutil.copyfile(response,raw)
    generator=d/f'generator_r{revision}.py'
    try:
        code=extract_python_script(raw.read_text(encoding='utf-8-sig'));generator.write_text(code,encoding='utf-8',newline='\n');review=audit(code)
        status='RECEIVED_AUDIT_PASS' if review['passed'] else 'RECEIVED_AUDIT_FAILED'
    except Exception as e:
        review={'passed':False,'failures':[str(e)]};status='EXTRACTION_FAILED'
    receipt={'trial_id':trial,'revision':revision,'chat_url':url,'ordinary_ChatGPT':True,'Work_or_Codex':False,
             'model_identity':'ChatGPT; exact backend/version unavailable','effort_label':'High',
             'submitted_utc':submitted,'captured_utc':datetime.now(timezone.utc).isoformat(),'tokens':None,'cost':None,
             'raw_response_sha256':sha(raw),'code_sha256':sha(generator) if generator.exists() else None,'status':status,'audit':review,
             'capture':'Complete UI code editor selection copied into Notepad and saved without edits; or complete accessibility code text if explicitly recorded. No researcher code repair.',
             'independence_limit':'Fresh initial chat; account memory/personalization and hidden routing are uncontrolled'}
    write(d/f'RECEIPT_r{revision}.json',receipt)
    m=read(d/'manifest.json');m.update(status=status,chat_url=url,latest_revision=revision);write(d/'manifest.json',m)
    print(trial,revision,status,review)


def work(source,family,destination,seeds):
    d=Path(destination);write(d/'progress.json',{'phase':'import'})
    spec=importlib.util.spec_from_file_location('captured_generator',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for seed in seeds:
        started=time.perf_counter();write(d/'progress.json',{'seed':seed,'phase':'generate'})
        row={'seed':seed,'status':'ERROR','source_sha256':sha(source)}
        try:
            a=module.generate_microstructure(seed,{});b=module.generate_microstructure(seed,{})
            if not np.array_equal(a,b):raise ValueError('Same-seed nondeterminism')
            validate(a,family);np.save(d/f'seed_{seed:03d}.npy',a,allow_pickle=False)
            row.update(status='OK',array_sha256=hashlib.sha256(a.tobytes()).hexdigest(),deterministic=True,validity=validity(a,family),descriptors=describe(a,family))
            from scripts.v070_microscopy_review import colorize,PARTICLE_PHASES,FIBER_PHASES
            Image.fromarray(colorize(a,PARTICLE_PHASES if family=='P3' else FIBER_PHASES)).save(d/f'seed_{seed:03d}.png')
        except Exception as e:
            row.update(error=str(e),traceback=traceback.format_exc())
        row['generation_repeat_and_evaluation_seconds']=time.perf_counter()-started;write(d/f'seed_{seed:03d}.json',row)
        write(d/'progress.json',{'seed':seed,'phase':'done'})


def run(trial,partition,revision=0):
    d=RUN/'llm_trials'/trial;m=read(d/'manifest.json');p=read(RUN/'protocol/PROTOCOL.json');family=m['family']
    if partition=='held' and not (RUN/'protocol/ALL_SCRIPTS_FROZEN.json').exists():raise ValueError('Heldout locked until all trial scripts/revisions frozen')
    source=d/f'generator_r{revision}.py';out=d/f'evaluation_r{revision}_{partition}';out.mkdir(exist_ok=False)
    review=audit(source.read_text(encoding='utf-8'));write(out/'CODE_AUDIT.json',review)
    seeds=p['development_seeds' if partition=='dev' else 'heldout_seeds']
    if not review['passed']:
        write(out/'EXECUTION.json',{'status':'CODE_AUDIT_FAILED','records':[],'execution_failures':len(seeds),'valid_outputs':0,'trial_id':trial,'revision':revision,'partition':partition});return
    start=time.monotonic();stamp=None;last=start;stop=None
    with (out/'worker.log').open('w') as log:
        process=subprocess.Popen([sys.executable,'-m','scripts.v070_real_pilot','worker','--source',str(source),'--family',family,'--destination',str(out),'--seeds',','.join(map(str,seeds))],cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
        while process.poll() is None:
            progress=out/'progress.json'
            if progress.exists() and progress.stat().st_mtime_ns!=stamp:stamp=progress.stat().st_mtime_ns;last=time.monotonic()
            if time.monotonic()-last>p['seed_timeout_seconds'] or time.monotonic()-start>p['module_timeout_seconds']:
                stop='TIMEOUT';process.kill();break
            time.sleep(.1)
        process.wait()
    rows=[read(f) for f in sorted(out.glob('seed_*.json'))];target=read(RUN/'references'/family/'descriptors.json');arrays=[]
    for row in rows:
        if row['status']=='OK':
            row['visible_error']=errors(row['descriptors'],target,family,VISIBLE[family]);row['hidden_error']=errors(row['descriptors'],target,family,HIDDEN[family]);arrays.append(np.load(out/f"seed_{row['seed']:03d}.npy",allow_pickle=False))
    write(out/'EXECUTION.json',{'trial_id':trial,'revision':revision,'partition':partition,'status':stop or ('COMPLETED' if process.returncode==0 and len(rows)==len(seeds) else 'WORKER_FAILED'),
                               'source_sha256':sha(source),'seeds':seeds,'records':rows,'execution_failures':len(seeds)-len(arrays),'valid_outputs':sum(r.get('validity',{}).get('passed',False) for r in rows),
                               'diversity':categorical_diversity(arrays,family),'wall_seconds':time.monotonic()-start})
    print(trial,revision,partition,'valid',sum(r.get('validity',{}).get('passed',False) for r in rows),'/',len(seeds))


def feedback(trial):
    d=RUN/'llm_trials'/trial;m=read(d/'manifest.json')
    if m['condition']!='C':raise ValueError('Only C receives feedback')
    r=read(d/'evaluation_r0_dev/EXECUTION.json');family=m['family'];target=read(RUN/'references'/family/'descriptors.json')
    measured={}
    for k in VISIBLE[family]:
        values=[row['descriptors'][k] for row in r['records'] if row['status']=='OK' and row['descriptors'].get(k) is not None]
        measured[k]={'mean':float(np.mean(values)) if values else None,'std':float(np.std(values)) if values else None,'n':len(values)}
    packet={'target':{k:target[k] for k in VISIBLE[family]},'development_measurements':measured,'valid_outputs':r['valid_outputs'],'execution_failures':r['execution_failures'],
            'failures':[row.get('error',row.get('validity',{}).get('failures')) for row in r['records'] if row['status']!='OK' or not row.get('validity',{}).get('passed',False)]}
    text='One registered quantitative development-feedback revision. Preserve the original phase definitions, interface and stochastic independence requirements. Return the full revised Python module in one code block. No additional data or repair calls will be supplied. Hidden metrics and final evaluation seeds are withheld. Use only this measured development summary:\n'+json.dumps(packet,sort_keys=True)+'\n'+METRIC_DEFINITION+'\n'
    (d/'feedback_prompt.txt').write_text(text,encoding='utf-8',newline='\n');write(d/'FEEDBACK_PACKET.json',packet);print(text)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['register','ingest','run','feedback','worker']);p.add_argument('--trial');p.add_argument('--response');p.add_argument('--url');p.add_argument('--submitted');p.add_argument('--revision',type=int,default=0);p.add_argument('--partition',choices=['dev','held'],default='dev');p.add_argument('--source');p.add_argument('--family');p.add_argument('--destination');p.add_argument('--seeds');a=p.parse_args()
    if a.action=='register':register()
    elif a.action=='ingest':ingest(a.trial,a.response,a.url,a.revision,a.submitted)
    elif a.action=='run':run(a.trial,a.partition,a.revision)
    elif a.action=='feedback':feedback(a.trial)
    else:work(a.source,a.family,a.destination,[int(k) for k in a.seeds.split(',')])
