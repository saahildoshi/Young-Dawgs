"""Frozen common initial task and measured-information-only same-chat continuations."""
import json
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v074_experiment import RUN,DOC,MICRO,PREV,now

def initial():
    destination=RUN/'feedback_packets/INITIAL_PROMPT.txt';assert not destination.exists()
    p=read(RUN/'protocol/PROTOCOL.json');policy=read(RUN/'protocol/FEASIBILITY_FROZEN.json')
    source=RUN/'starting_generator/generator.py';identity=read(RUN/'starting_generator/COMMON_STARTING_POINT_FROZEN.json')
    assert sha(source)==identity['common_generator_sha256']
    reference=MICRO/'references/P3/microscopy_input.png'
    common={'target_MPa':1640,'J_target':1.640,'target_band_relative':.02,'objective':'Minimize generator-level mean absolute relative target error; do not maximize stiffness',
        'phase_definitions':{'1':'matrix-like solid','5':'provisional reinforcement-like solid; provisionally reprecipitated carbides; not a verified chemistry'},
        'source_provenance':'Supplied horizontally flipped SEM tile, genuine geometry-preserving microscopy augmentation, morphology-selected crop; not an unaugmented original or unbiased RVE',
        'physical_scale':'No microscopy calibration; do not infer micrometers from pixels or simulate experimentally calibrated properties',
        'composition':{'reinforcement':20731,'matrix':44805,'shape':[256,256],'dtype':'uint8'},
        'mechanical_model':{'materials_MPa':{'matrix':1000,'reinforcement':10000},'nu':.30,'plane_stress':True,
            'computational_square_mm':1,'computational_thickness_mm':1,'computational_sizes_not_microscopy_calibration':True,
            'loading':'bottom UY0, prescribed negative top UY through0.5%, one minimal bottom UX pin; free lateral motion, shared-node ideal bonds, linear elasticity, no contact'},
        'feasibility_guardrails':policy['guardrails'],'new_hard_descriptor_bounds':policy['new_descriptor_bounds'],
        'must_be_false':policy['must_be_false'],'descriptor_conventions':policy['boundary_policy'],
        'topology':policy['connectivity_policy'],'diversity':policy['diversity'],
        'generator_parameters':{},'maximum_internal_geometry_candidates':8,'single_output_seconds':30,
        'allowed_dependencies':p['allowed_dependencies']}
    prompt='''Create one complete initial stochastic P3 microstructure generator for the attached raw SEM image and the common scientific specification below. This is the INITIAL generator turn in this conversation. A single later registered revision, if requested, will continue this same conversation. Do not use tools or browse; return code only in ONE complete Python code block, with no prose or demo. Prefer <=500 lines, but completeness and correctness are required.

Use the supplied researcher-prepared template as common scientific background; you may retain its morphology functions and change legitimate geometric construction within the limits. Produce your own identifiable complete initial module in this response; do not tell us merely to load another file. The template is derived from a previous captured LLM generator plus explicitly researcher-authored count/feasibility logic. It is not a new model trial until your actual response is captured. No measured mechanical responses are supplied in this initial task.

Required generate_microstructure(seed, parameters), parameters={}, returns numpy ndarray shape(256,256), uint8, labels exactly1/5, both nonempty. EXACTLY20,731 reinforcement pixels. Finite nonperiodic field with appropriately clipped edge features. Use local numpy.random.default_rng(seed); same seed exactly replays, different seeds change configuration beyond rigid translation/rotation. The evaluator will not repair arrays. If internal candidate construction exhausts its fixed bound, raise an explicit failure. No file/network/API/subprocess access, no external solver or cached mechanics, no reference loading or embedded raster/coordinate tracing, no global RNG seeding, plotting, printing, import-time generation or executable module-scope calls. Module scope only imports, functions and literal constants. Use no dependencies outside the allowed list.

Preserve irregular dispersed-inclusion morphology, matrix connectivity and complete/boundary region populations. Avoid continuous or segmented artificial lanes. Hard shape/tail/alignment measurements include ALL observed regions, not just complete features. New orientation uses area×eigenvalue-anisotropy weights, ignoring anisotropy<.05, axial angles modulo180degrees with image+x right and y up. Finite S2/strip windows never wrap. Two-pixel diagnostic dilation is evaluator geometry only, not a change to the actual mechanical specimen. Diagnostic dilation must not span x or y. The template contains the precise inexpensive definitions for the common hard constraints. Runtime, exact replay and between-seed diversity are evaluated independently.

You may reason about geometry and elasticity, but do not invent measured performance or claim to have run ANSYS. We will independently measure actual mechanics after capturing this exact source. Target accuracy and structural feasibility are separate outcomes. Exceeding1640MPa is not automatically an improvement. There is one initial response and one later continuation opportunity, no manual repairs or retries.

COMMON SCIENTIFIC SPECIFICATION:
'''+json.dumps(common,sort_keys=True,indent=2)+'\n\nCOMMON RESEARCHER-PREPARED TEMPLATE (copy/adapt into one self-contained module):\n```python\n'+source.read_text()+'\n```\n'
    destination.parent.mkdir();destination.write_text(prompt,encoding='utf-8',newline='\n')
    write(RUN/'feedback_packets/INITIAL_FROZEN.json',{'frozen_utc':now(),'prompt_sha256':sha(destination),'common_source_sha256':sha(source),
        'raw_microscopy_image_path':str(reference),'raw_microscopy_image_sha256':sha(reference),'mask_supplied_to_model':False,
        'protocol_sha256':sha(RUN/'protocol/PROTOCOL.json'),'feasibility_sha256':sha(RUN/'protocol/FEASIBILITY_FROZEN.json'),
        'trial_order':p['trial_order'],'identical_initial_prompts':True,'prospective_assignments':{t:t[:2] for t in p['trial_order']},
        'same_chat_revision_requirement':True})
    for trial in p['trial_order']:
        d=RUN/'llm_trials'/trial;d.mkdir(parents=True);(d/'initial_prompt.txt').write_text(prompt,encoding='utf-8',newline='\n')
        write(d/'PLAN.json',{'trial_id':trial,'arm':trial[:2],'initial_prompt_sha256':sha(d/'initial_prompt.txt'),'image_sha256':sha(reference),
            'initial_calls_registered':1,'followup_calls_registered':1,'followup_must_use_initial_chat_URL':True,'actual_initial_calls':0,'actual_followup_calls':0})
    (DOC/'V0_7_4_SAME_CHAT_LLM_WORKFLOW.md').write_text('''# Registered conversation-continuous experiment

Eight independent persistent ordinary-ChatGPT conversations receive an identical initial prompt, the authenticated raw SEM crop and the same researcher-prepared source template. No segmentation mask or measured mechanics is supplied initially. Actual returned initial source modules may differ; they are not replaced by the template or manually repaired. IF/NF assignment and ordering precede any response.

Each exact initial module is evaluated on the same registered development seeds, with invalid attempts retained. IF receives authentic measurements for its own initial source plus the reused v073 paired geometry–mechanics dataset. NF receives the identical continuation structure, physics and structural information without measured responses. Both receive one follow-up in the SAME original URL, with earlier code already present; no old-script attachment to a new chat substitutes for continuity. Capture timestamps, initial and revised response hashes, prompt hashes and chronological UI evidence bind each conversation. All16 actual source modules must freeze before final seeds are generated.

The exposed model/reasoning configuration is held consistent where available. Backend routing, account memory, custom instructions and complete statistical independence cannot be inferred. Conversation identity, exact prompt and response provenance are verified separately from scientific generator validity. No final outcomes are sent to the model, and there are no additional repair or optimization rounds.
''',encoding='utf-8',newline='\n')
    print('INITIAL PACKET FROZEN',len(prompt),'characters; image',reference,flush=True)

def structural(row,policy):
    from metamaterial_eval.composites.morphology_v073 import flattened
    result={key:row.get(key) for key in ['seed','status','phase_counts','generation_seconds','deterministic','error']}
    result['feasibility']={key:row['feasibility'][key] for key in ['passed','failures']}
    if row.get('status')=='GENERATED':
        values=flattened(row['morphology_v073'])
        result['common_descriptors']={key:value for key,value in row['descriptors'].items() if key not in ['detail','working_map']}
        result['new_descriptors']={key:values.get(key) for key in list(policy['new_descriptor_bounds'])+policy['must_be_false']+
            ['all_observed.vertical_alignment','all_observed.preferred_axial_angle_deg','interface_density','nearest_neighbor_mean_px']}
    def compact(value):
        if isinstance(value,float):return round(value,6)
        if isinstance(value,dict):return {k:compact(v) for k,v in value.items()}
        if isinstance(value,list):return [compact(v) for v in value]
        return value
    return compact(result)


def followup(trial):
    import numpy as np
    p=read(RUN/'protocol/PROTOCOL.json');assert trial in p['trial_order']
    d=RUN/'llm_trials'/trial;destination=d/'followup_prompt.txt';assert not destination.exists()
    receipt=read(d/'RECEIPT_r0.json');source=d/'generator_r0.py';assert sha(source)==receipt['code_sha256']
    policy=read(RUN/'protocol/FEASIBILITY_FROZEN.json')
    own=read(RUN/'structures'/trial/'r0/development/SUMMARY.json')
    campaign=read(RUN/'mechanical_campaigns'/f'{trial}_r0_development_H1.json')
    assert len(campaign['cases'])==3 and campaign['planned']==3
    historic=read(PREV/'controlled_variants/GEOMETRY_DATASET_FROZEN.json')['rows']
    geometry={'own_initial_source_sha256':sha(source),'development_structures':[structural(row,policy) for row in own['rows']],
        'own_development_diversity':own['diversity'],
        'previous_controlled_geometry':[{'family':row['trial_id'],**structural(row,policy)} for row in historic],
        'previous_variant_definitions':read(PREV/'controlled_variants/VARIANTS_FROZEN.json')['matrix'],
        'historical_caution':'Researcher-controlled probes, not independent LLM responses; parameters change random trajectories and multiple descriptors can covary. No causal single-descriptor claim.'}
    measured={'own_initial':[],'historical_controlled_H1':[],'historical_controlled_H2':[]}
    def response(row,result):
        return {'family':row['trial_id'],'seed':row['seed'],'mesh_level':result['mesh_level'],
            'apparent_modulus_MPa':result['effective_modulus_MPa'],
            'actual_curve_strain_stress_MPa':list(map(list,zip(result['engineering_strains'],result['nominal_stresses_MPa']))),
            'absolute_relative_target_error':abs(result['effective_modulus_MPa']-1640)/1640,
            'native_RST_sha256':result['native_result_sha256'],'all_native_acceptance_checks_passed':result['accepted']}
    for row in campaign['cases']:
        if row['status']=='ACCEPTED_NATIVE_RESULT':
            result=read(RUN/'mechanical_response'/f'{trial}_r0_development_{row["seed"]}_H1_attempt001.json')
            measured['own_initial'].append(response(row,result))
        else:measured['own_initial'].append({'seed':row['seed'],'status':row['status'],'apparent_modulus_MPa':None})
    for level in [1,2]:
        for row in read(PREV/f'development_mechanics_h{level}/CAMPAIGN.json')['cases']:
            if row['status']!='ACCEPTED_NATIVE_RESULT':continue
            result=read(PREV/'mechanical_response'/f'{row["trial_id"]}_development_{row["seed"]}_H{level}_attempt001.json')
            measured[f'historical_controlled_H{level}'].append(response(row,result))
    values=[r['apparent_modulus_MPa'] for r in measured['own_initial'] if r.get('apparent_modulus_MPa') is not None]
    measured['own_summary']={'attempted':3,'mechanically_accepted':len(values),
        'mean_modulus_MPa':float(np.mean(values)) if values else None,
        'sample_SD_MPa':float(np.std(values,ddof=1)) if len(values)>1 else None,
        'mean_absolute_relative_target_error':float(np.mean(np.abs(np.asarray(values)-1640)/1640)) if values else None,
        'target_hits_over_all_attempted':sum(abs(v-1640)/1640<=.02 for v in values)/3}
    common='''You generated the initial Python microstructure module earlier in THIS conversation. We executed that exact captured module on the three registered development seeds before this continuation. This is the ONE registered revision request; revise your own earlier generator toward the fixed1640MPa apparent-modulus target while preserving the morphology and procedural constraints. Return ONE COMPLETE self-contained revised Python module in one Python code block, no prose or demo. Do not use tools or browse. Do not claim to have run ANSYS yourself. No additional repair or optimization round is available.

Keep generate_microstructure(seed, parameters), parameters={}, uint8 shape(256,256), native labels1=matrix-like solid and5=provisional reinforcement-like solid. EXACTLY20,731 label5 pixels and44,805 label1 pixels; finite nonperiodic support. Preserve local RNG replay and independent arrangement variation. At most8 geometry candidates and30seconds per output. No I/O, files, external caches, mechanical solver, reference loading/tracing, global RNG state, import-time calls, or dependencies beyond the initial allowed list. If no feasible candidate is found, raise an explicit failure; the evaluator will not repair outputs.

Unchanged illustrative physics: E_matrix1000MPa, E_reinforcement10000MPa, bothnu0.30, linear plane stress, shared-node ideal bonds,1mm computational square and thickness; bottomUY0/top negativeUY at0.001,0.002,0.003,0.004,0.005 engineering strain, one bottomUXpin, free lateral displacement, no contact or large strain. Computational dimensions do not calibrate microscopy. Fixed target1640MPa,±2% hit band1607.2–1672.8MPa. Objective is generator-level mean absolute relative target error, not maximum stiffness. All outputs must also satisfy the unchanged full morphology envelope and diversity.

Raw SEM provenance and provisional phase definition remain as supplied initially. The image is a horizontally flipped authentic microscopy tile and a morphology-selected crop, not an unaugmented original or unbiased RVE. No segmentation mask or held-out seeds/results are provided. No other contemporary trial's source or results are included. The initial code is already in this same conversation; it is not reattached.

FULL UNCHANGED MORPHOLOGY POLICY (historical ten-output wording does not change per-array thresholds; current final cohort has six outputs):
'''+json.dumps(policy,sort_keys=True,indent=2)+'\n\nSTRUCTURAL DEVELOPMENT INFORMATION (consistent schema in both conditions; structural decimals rounded to6 places for readability, raw evaluator records retained):\n'+json.dumps(geometry,sort_keys=True,separators=(',',':'))
    if trial.startswith('IF'):
        message=common+'\n\nACTUAL LICENSED ANSYS DEVELOPMENT MEASUREMENTS:\n'+json.dumps(measured,sort_keys=True,separators=(',',':'))+'\nUse these measurements to improve target matching in your single revised generator. H1/H2 sensitivity is exploratory, not an error bound. All curves are actual five-checkpoint solves with independent native readback; historical records were reused, not rerun. No manually supplied optimization recommendation accompanies the measurements.\n'
    else:
        message=common+'\n\nNO MEASURED MECHANICAL INFORMATION IS SUPPLIED IN THIS CONTROL CONDITION. Reason toward the same target from the unchanged physical assumptions, raw microscopy already in this conversation, and structural information above. Produce your single complete revision.\n'
    destination.write_text(message,encoding='utf-8',newline='\n')
    write(d/'FOLLOWUP_PACKET_FROZEN.json',{'frozen_utc':now(),'trial_id':trial,'arm':trial[:2],
        'same_chat_url':read(d/'SUBMISSION_r0.json')['chat_url'],'prompt_sha256':sha(destination),
        'initial_code_sha256':sha(source),'development_summary_sha256':sha(RUN/'structures'/trial/'r0/development/SUMMARY.json'),
        'private_mechanics_campaign_sha256':sha(RUN/'mechanical_campaigns'/f'{trial}_r0_development_H1.json'),
        'geometry':geometry,'measured_mechanics_in_prompt':trial.startswith('IF'),
        'mechanical_feedback':measured if trial.startswith('IF') else None,
        'complete_morphology_policy_sha256':sha(RUN/'protocol/FEASIBILITY_FROZEN.json'),
        'heldout_excluded':True,'mask_excluded':True,'initial_code_not_reattached':True})
    print('FOLLOWUP FROZEN',trial,len(message),'characters, same chat',read(d/'SUBMISSION_r0.json')['chat_url'],flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['initial','followup'],default='initial',nargs='?');parser.add_argument('trial',nargs='?');args=parser.parse_args()
    if args.action=='initial':initial()
    else:followup(args.trial)
