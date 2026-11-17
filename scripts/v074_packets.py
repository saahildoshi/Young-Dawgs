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

if __name__=='__main__':initial()
