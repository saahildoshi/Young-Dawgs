"""Freeze matched revision packets containing only authentic development evidence."""
import json
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v072_experiment import RUN,DOC,TRIALS,now


def prepare():
    assert not (RUN/'feedback_packets/PROMPTS_FROZEN.json').exists()
    p=read(RUN/'protocol/PROTOCOL.json');policy=read(RUN/'protocol/FEASIBILITY_FROZEN.json')
    start=RUN/'starting_generator/generator.py';auth=read(RUN/'starting_generator/COMMON_STARTING_POINT_FROZEN.json')
    assert sha(start)==auth['common_copy_sha256']
    rows=read(RUN/'baseline_development/OBSERVATIONS.json');struct=[];mechanics=[]
    for row in rows:
        seed=row['seed'];r=read(RUN/f'mechanical_response/BASE_development_{seed}_H1_attempt001.json')
        assert r['accepted'] and row['feasibility']['passed']
        struct.append({'seed':seed,'phase_counts':row['phase_counts'],
            'descriptors':{k:v for k,v in row['descriptors'].items() if k not in ['detail','working_map']},
            'topology':row['topology'],'structurally_feasible':True,'generation_seconds':row['generation_seconds']})
        mechanics.append({'seed':seed,'mechanically_accepted':True,'apparent_modulus_MPa':r['effective_modulus_MPa'],
            'normalized_objective':r['normalized_effective_modulus'],'actual_solved_strain':r['engineering_strains'],
            'actual_nominal_compressive_stress_MPa':r['nominal_stresses_MPa'],
            'actual_top_UY_mm':[x[2] for x in r['native_curve']],
            'actual_signed_upper_reaction_N':[x[5] for x in r['native_curve']],
            'actual_signed_lower_reaction_N':[x[6] for x in r['native_curve']],
            'maximum_relative_reaction_imbalance':r['max_reaction_imbalance'],
            'native_RST_sha256':r['native_result_sha256']})
    E=np.array([r['apparent_modulus_MPa'] for r in mechanics]);stress=np.array([r['actual_nominal_compressive_stress_MPa'] for r in mechanics])
    summary={'n':len(E),'mean_modulus_MPa':float(E.mean()),'median_modulus_MPa':float(np.median(E)),
        'sample_standard_deviation_MPa':float(E.std(ddof=1)),'minimum_modulus_MPa':float(E.min()),'maximum_modulus_MPa':float(E.max()),
        'coefficient_of_variation':float(E.std(ddof=1)/E.mean()),'mean_normalized_objective':float(E.mean()/1000),
        'sample_standard_deviation_normalized_objective':float(E.std(ddof=1)/1000),
        'mean_actual_checkpoint_stress_MPa':stress.mean(axis=0).tolist(),'sample_sd_actual_checkpoint_stress_MPa':stress.std(axis=0,ddof=1).tolist(),
        'aggregate_curve_note':'Mean of six independently solved specimens at corresponding actual checkpoints, not a single directly solved specimen',
        'reinforcement_counts':[r['phase_counts']['5'] for r in rows]}
    common={'starting_generator_id':'P3_B_02/r0','starting_generator_sha256':sha(start),
        'objective':'maximize J = apparent vertical elastic modulus / 1000 MPa',
        'phase_definitions':{'1':'matrix-like solid','5':'reinforcement-like solid, provisional carbide chemistry'},
        'composition':{k:policy[k] for k in ['target_count','target_fraction','absolute_pixel_tolerance','absolute_fraction_tolerance']},
        'morphology_guardrails':policy['guardrails'],'connectivity_policy':policy['connectivity_policy'],'diversity_policy':policy['diversity'],
        'mechanical_assumptions':{k:p[k] for k in ['material','element','loading','strain_checkpoints','NLGEOM']},
        'domain':'Computational 1 mm x 1 mm, thickness 1 mm; native shared-node 256x256 quadrilateral H1, pixel-preserving H2. Unknown physical microscopy scale.',
        'generation_parameters':{},'single_output_runtime_limit_seconds':30,'allowed_dependencies':p['allowed_dependencies'],
        'internal_search_limit':p['internal_search_limit'],'baseline_development_structure':struct,
        'limitations':'Illustrative linear isotropic constituents, ideal bonded pixel interfaces; finite-domain vertical apparent modulus only. Provisional chemistry, selected augmented microscopy crop, no physical calibration or RVE claim. Pixel corner contacts are not established physical reinforcement bonds.'}
    feedback={'experiment_id':'v0.7.2/run_001','development_mechanics':mechanics,'baseline_variability':summary,
        'numerical_notes':'All measurements use H1 and five independently extracted native checkpoints. Each source RST was independently reopened. Pixel-preserving H2 checks are prospectively reserved for final confirmation; no current development H2 uncertainty estimate. Differences near numerical sensitivity require confirmation. No causal geometry interpretation supplied.'}
    instructions='''Revise the supplied stochastic P3 microstructure generator to increase apparent VERTICAL elastic stiffness under the stated numerical model while maintaining the common composition and dispersed-inclusion constraints. Return ONE complete Python module in ONE python code block, code only, preferably <=250 lines. One revision opportunity, no repairs or subsequent feedback.

Required interface: generate_microstructure(seed, parameters), parameters={}, returning numpy ndarray shape(256,256), dtype uint8, native labels {1,5}, both phases nonempty. Use local numpy.random.default_rng(seed); identical seed reproduces exactly, different seeds must change configuration beyond global rigid translation/rotation. Finite nonperiodic boundaries, with boundary-censored regions. Do not embed any reference raster, fixed coordinate tracing, seed-specific arrays or mechanical-result cache. No file/network/API/subprocess access, plotting, imports outside the allowed list, printing/demos/tests or generation at import. Module scope only imports, function definitions, literal constants. No tools or browsing. Do not implement a solver. Bounded geometry-only candidate selection is permitted under the common runtime/search limits. Respect all hard constraints; exact reinforcement count is preferred, but the same stated tolerance applies to every arm and the baseline. No evaluator postprocessing will repair your output.

You may alter placement, shapes, orientation, size distribution and spacing within the frozen feasibility envelope. Complete-region metrics use four-connected annotations excluding all border-touching regions; equivalent diameter=2*sqrt(area/pi), mean aspect=major/minor region axis lengths. Matrix/reinforcement largest fractions are fractions of their own phase area. Reinforcement spanning is forbidden under both four- and eight-connectivity. Singleton noise fraction is singleton-region area divided by total reinforcement area. The evaluator will test ten unseen seeds, preserving failures, and separately assess stochastic diversity. Equal seed IDs need not imply the same particle identities across algorithms. Do not invent simulation results or physical performance claims.

COMMON INPUTS (identical in both revision conditions):
'''
    base=instructions+json.dumps(common,sort_keys=True,indent=2)+'\n\nFROZEN STARTING MODULE (identical in all trials):\n```python\n'+start.read_text()+'```\n'
    suffix='\nMEASURED MECHANICAL FEEDBACK (actual development ANSYS results):\n'+json.dumps(feedback,sort_keys=True,indent=2)+'\n'
    write(RUN/'feedback_packets/COMMON_INPUTS.json',common);write(RUN/'feedback_packets/MF_ACTUAL_MECHANICS.json',feedback)
    write(RUN/'baseline_mechanical_results/SUMMARY.json',summary)
    prompts={}
    for trial in TRIALS:
        d=RUN/'llm_trials'/trial;d.mkdir(parents=True,exist_ok=False)
        text=base+(suffix if '_MF_' in trial else '')
        (d/'prompt.txt').write_text(text,encoding='utf-8',newline='\n')
        prompts[trial]=sha(d/'prompt.txt')
        write(d/'manifest.json',{'trial_id':trial,'condition':'MF' if '_MF_' in trial else 'NF','prompt_sha256':prompts[trial],
            'status':'READY_NOT_EXECUTED','response_budget':1,'repair_calls':0,'starting_generator_sha256':sha(start)})
    assert (RUN/'llm_trials/P3_OPT_MF_01/prompt.txt').read_text()==base+suffix
    assert (RUN/'llm_trials/P3_OPT_MF_02/prompt.txt').read_text()==base+suffix
    assert (RUN/'llm_trials/P3_OPT_NF_01/prompt.txt').read_text()==base
    assert (RUN/'llm_trials/P3_OPT_NF_02/prompt.txt').read_text()==base
    for seed in read(RUN/'protocol/EVALUATOR_ONLY_SEEDS.json')['heldout']:
        # Search numeric tokens, not arbitrary substrings that might occur in a hash/float.
        import re
        assert str(seed) not in re.findall(r'(?<![\w.])\d+(?![\w.])',base+suffix),('Held-out seed leaked',seed)
    audit={'common_inputs_exactly_identical':True,'NF_contains_only_common_inputs':True,'MF_equals_NF_plus_exact_measured_packet':True,
        'mechanical_intervention_only':True,'no_researcher_mechanical_hint':True,'heldout_seeds_absent':True,'hidden_morphology_error_scores_absent':True,
        'independent_chats_required':True,'same_revision_budget':True,'prompt_hashes':prompts,'feedback_sha256':sha(RUN/'feedback_packets/MF_ACTUAL_MECHANICS.json')}
    write(RUN/'feedback_packets/PROMPT_DIFFERENCE_AUDIT.json',audit)
    write(RUN/'feedback_packets/PROMPTS_FROZEN.json',{'frozen_utc':now(),**audit,
        'common_inputs_sha256':sha(RUN/'feedback_packets/COMMON_INPUTS.json'),'starting_point_manifest_sha256':sha(RUN/'starting_generator/COMMON_STARTING_POINT_FROZEN.json'),
        'feasibility_sha256':sha(RUN/'protocol/FEASIBILITY_FROZEN.json'),'protocol_sha256':sha(RUN/'protocol/PROTOCOL.json')})
    (DOC/'V0_7_2_BASELINE_MECHANICS.md').write_text('# Authenticated baseline development mechanics\n\nUnchanged captured B02 SHA-256 `'+sha(start)+'`. Exact historical seed0 replay passed. Six new development structures passed composition and morphology; no fallback or adaptation was required.\n\n'+
        '| Development seed | Reinforcement pixels | Apparent E (MPa) | J |\n|---|---:|---:|---:|\n'+''.join(f"| {r['seed']} | {s['phase_counts']['5']} | {r['apparent_modulus_MPa']:.6f} | {r['normalized_objective']:.6f} |\n" for r,s in zip(mechanics,rows))+
        f"\nMean {E.mean():.6f} MPa; sample SD {E.std(ddof=1):.6f} MPa; range {E.min():.6f}–{E.max():.6f} MPa. All six actual native five-checkpoint curves were independently reopened and passed unchanged v0.7.1 equilibrium, energy, field, connectivity, material, displacement and constraint checks. Final-point secant agrees with fitted modulus under the registered tolerance. No unsolved points are labeled native.\n\nThese are H1 results using illustrative E1000/10000 MPa, nu0.30; the phase-count tolerance is ±64 pixels, not exact count equality. The six specimens measure within-generator variation, not independent LLM trials. No development H2 error bound is inferred.\n",encoding='utf-8',newline='\n')
    print('BASELINE MEAN',summary,'PROMPTS FROZEN',prompts,flush=True)


if __name__=='__main__':prepare()
