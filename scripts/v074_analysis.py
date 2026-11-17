"""Descriptive script-level inference, with seeds nested and failures explicit."""
import numpy as np
from scripts.v070_protocol import read, write, sha
from scripts.v074_experiment import RUN, REPO, MICRO, now
from scripts.v073_analysis import statistics, target_metrics, csv_table


def summarize(cases, attempted):
    accepted = [r for r in cases if r['apparent_modulus_MPa'] is not None]
    mods = [r['apparent_modulus_MPa'] for r in accepted]
    errors = [r['absolute_target_error'] for r in accepted]
    hits = sum(r['target_hit'] for r in accepted)
    return {
        'attempted': attempted, 'mechanically_accepted': len(accepted),
        'modulus': statistics(mods), 'target_error': statistics(errors),
        'mean_property_bias': abs(float(np.mean(mods)) - 1640) / 1640 if mods else None,
        'mean_signed_bias': float(np.mean([r['signed_target_error'] for r in accepted])) if accepted else None,
        'target_hits': hits, 'target_hits_per_attempt': hits / attempted,
        'target_hits_per_accepted': hits / len(accepted) if accepted else None,
        'metric_scope': 'Conditional on structural and native acceptance; no invented failure penalty',
    }


def arm_comparison(summaries, changes, excluded=()):
    arms = {}
    for arm in ('IF', 'NF'):
        rows = [r for r in summaries if r['arm'] == arm and r['trial_id'] not in excluded]
        paired = [r for r in changes if r['arm'] == arm and r['trial_id'] not in excluded]
        arms[arm] = {
            'registered_conversations_in_analysis': len(paired),
            'initial_script_errors': statistics([r['target_error']['mean'] for r in rows if r['revision'] == 0 and r['target_error']['mean'] is not None]),
            'revised_script_errors': statistics([r['target_error']['mean'] for r in rows if r['revision'] == 1 and r['target_error']['mean'] is not None]),
            'within_conversation_error_reduction': statistics([r['initial_minus_revised_mean_error'] for r in paired if r['initial_minus_revised_mean_error'] is not None]),
            'fully_qualified_revised_scripts': sum(r['fully_qualified_generator'] for r in rows if r['revision'] == 1),
            'revised_qualified_script_errors': statistics([r['target_error']['mean'] for r in rows if r['revision'] == 1 and r['fully_qualified_generator']]),
        }
    a, b = arms['IF'], arms['NF']
    def difference(field, reverse=False):
        x, y = a[field]['mean'], b[field]['mean']
        return (x - y if reverse else y - x) if x is not None and y is not None else None
    return {'arms': arms, 'excluded_trials': list(excluded),
        'revised_error_advantage_NF_minus_IF': difference('revised_script_errors'),
        'improvement_advantage_IF_minus_NF': difference('within_conversation_error_reduction', True),
        'independent_unit': 'Conversation, four assigned per arm; initial/revised scripts paired within conversation; seeds nested',
        'inference': 'Descriptive only; tiny sample, unequal initial modules, project/memory context variation and NF01 extra nonscientific user turn preclude an unqualified causal or generalization claim'}


def analyse():
    assert (RUN / 'performance/FINAL_MECHANICS_COMPLETE.json').exists()
    protocol = read(RUN / 'protocol/PROTOCOL.json')
    order = protocol['trial_order']
    rows, summaries, curves, morphology, phases = [], [], [], [], []
    for trial in order:
        for revision in (0, 1):
            structure = read(RUN / 'structures' / trial / f'r{revision}' / 'heldout/SUMMARY.json')
            local = []
            for level in (1, 2):
                campaign = read(RUN / 'mechanical_campaigns' / f'{trial}_r{revision}_heldout_H{level}.json')
                assert len(campaign['cases']) == campaign['planned'] == (6 if level == 1 else 2)
                for case in campaign['cases']:
                    s = next(s for s in structure['rows'] if s['seed'] == case['seed'])
                    row = {**case, **target_metrics(case['apparent_modulus_MPa'], 1640, .02),
                        'arm': trial[:2], 'generation_status': s['status'],
                        'exact_composition': s.get('phase_counts') == {'1': 44805, '5': 20731},
                        'generation_seconds': s.get('generation_seconds'),
                        'generator_sha256': s['generator_sha256'],
                        'array_sha256': s.get('array_file_sha256')}
                    rows.append(row)
                    if level == 1:
                        local.append(row)
                        from metamaterial_eval.composites.morphology_v073 import flattened
                        morphology.append({'trial_id': trial, 'revision': revision, 'seed': s['seed'],
                            'feasible': s['feasibility']['passed'], 'failures': s['feasibility']['failures'],
                            **{key: s['descriptors'][key] for key in ('all_regions','complete_regions','boundary_censored_regions','diameter_mean_px','diameter_std_px','aspect_mean','nearest_neighbor_mean_px','interface_density')},
                            **flattened(s.get('morphology_v073', {}))} if s.get('morphology_v073') else {
                                'trial_id': trial, 'revision': revision, 'seed': s['seed'],
                                'feasible': False, 'failures': s['feasibility']['failures']})
                    if case['apparent_modulus_MPa'] is not None:
                        name = f'{trial}_r{revision}_heldout_{case["seed"]}_H{level}_attempt001'
                        result = read(RUN / 'mechanical_response' / f'{name}.json')
                        assert result['accepted'] and all(result['checks'].values())
                        for material, values in result['phase_results'].items():
                            phases.append({'trial_id': trial, 'revision': revision, 'seed': s['seed'],
                                'mesh_level': level, 'native_material': int(material),
                                'raw_phase_label': 1 if material == '1' else 5,
                                'volume_fraction': values['volume_fraction'],
                                'mean_syy_MPa': values['mean_syy_MPa'],
                                'mean_axial_strain': values['mean_axial_strain'],
                                'equivalent_stress_p99_MPa': values['equivalent_percentiles_MPa']['p99'],
                                'equivalent_stress_p99_over_nominal': values['equivalent_percentiles_over_nominal']['p99'],
                                'elastic_energy_fraction': values['elastic_energy_fraction']})
                        for c in result['native_curve']:
                            curves.append({'trial_id': trial, 'revision': revision, 'seed': s['seed'],
                                'mesh_level': level, 'step': int(c[0]),
                                'engineering_compression': -c[2], 'nominal_compression_MPa': -c[5],
                                'top_uy_signed_mm': c[2], 'top_reaction_signed_N': c[5],
                                'bottom_reaction_signed_N': c[6], 'pin_reaction_signed_N': c[7],
                                'strain_energy_Nmm': c[8], 'volume_mm3': c[9],
                                'native_RST_sha256': result['native_result_sha256']})
            summary = summarize(local, 6)
            summary.update(trial_id=trial, revision=revision, arm=trial[:2],
                generated=structure['generated'], exact_composition=sum(r['exact_composition'] for r in local),
                structurally_feasible=structure['feasible'], diversity=structure['diversity'],
                fully_qualified_generator=structure['fully_qualified_generator'] and summary['mechanically_accepted'] == 6,
                runtime=statistics([r['generation_seconds'] for r in local if r['generation_seconds'] is not None]))
            summaries.append(summary)
    changes, mesh = [], []
    for trial in order:
        pair = [next(r for r in summaries if r['trial_id'] == trial and r['revision'] == rev) for rev in (0, 1)]
        errors = [r['target_error']['mean'] for r in pair]
        common = []
        for seed in range(5000, 5006):
            r0, r1 = [next(r for r in rows if r['trial_id'] == trial and r['revision'] == rev and r['seed'] == seed and r['mesh_level'] == 1) for rev in (0, 1)]
            if r0['absolute_target_error'] is not None and r1['absolute_target_error'] is not None:
                common.append(r0['absolute_target_error'] - r1['absolute_target_error'])
        changes.append({'trial_id': trial, 'arm': trial[:2], 'initial_mean_error': errors[0], 'revised_mean_error': errors[1],
            'initial_minus_revised_mean_error': errors[0] - errors[1] if all(e is not None for e in errors) else None,
            'both_scripts_fully_qualified': all(r['fully_qualified_generator'] for r in pair),
            'common_accepted_seed_error_reduction': statistics(common),
            'common_accepted_seed_positive_reductions': sum(x > 0 for x in common),
            'strict_equal_message_budget': trial != 'NF_01'})
        for revision in (0, 1):
            for seed in (5000, 5001):
                first, second = [next(r for r in rows if r['trial_id'] == trial and r['revision'] == revision and r['seed'] == seed and r['mesh_level'] == level) for level in (1, 2)]
                a, b = first['apparent_modulus_MPa'], second['apparent_modulus_MPa']
                mesh.append({'trial_id': trial, 'arm': trial[:2], 'revision': revision, 'seed': seed,
                    'H1_modulus_MPa': a, 'H2_modulus_MPa': b,
                    'H1_target_error': first['absolute_target_error'], 'H2_target_error': second['absolute_target_error'],
                    'H1_hit': first['target_hit'], 'H2_hit': second['target_hit'],
                    'absolute_mesh_change_MPa': abs(b - a) if a is not None and b is not None else None,
                    'relative_mesh_change': abs(b - a) / a if a is not None and b is not None else None,
                    'within_2pct_mesh_tolerance': abs(b - a) / a <= .02 if a is not None and b is not None else None})
    mesh_changes = []
    for trial in order:
        local = []
        for seed in (5000, 5001):
            a, b = [next(r for r in mesh if r['trial_id'] == trial and r['revision'] == revision and r['seed'] == seed) for revision in (0, 1)]
            valid = all(r['H1_target_error'] is not None and r['H2_target_error'] is not None for r in (a, b))
            h1 = a['H1_target_error'] - b['H1_target_error'] if valid else None
            h2 = a['H2_target_error'] - b['H2_target_error'] if valid else None
            noise = (a['absolute_mesh_change_MPa'] + b['absolute_mesh_change_MPa']) / 1640 if valid else None
            local.append({'seed': seed, 'H1_initial_minus_revised_error': h1,
                'H2_initial_minus_revised_error': h2, 'improvement_persists': h1 > 0 and h2 > 0 if valid else None,
                'combined_observed_changes_over_target': noise,
                'H2_improvement_exceeds_combined_observed_changes': h2 > noise if valid else None})
        mesh_changes.append({'trial_id': trial, 'arm': trial[:2], 'paired_checks': local,
            'H1_error_reduction': statistics([r['H1_initial_minus_revised_error'] for r in local if r['H1_initial_minus_revised_error'] is not None]),
            'H2_error_reduction': statistics([r['H2_initial_minus_revised_error'] for r in local if r['H2_initial_minus_revised_error'] is not None])})
    comparison = arm_comparison(summaries, changes)
    sensitivity = arm_comparison(summaries, changes, ('NF_01',))
    from metamaterial_eval.composites.morphology_v073 import describe, flattened
    from scripts.v072_experiment import observe
    reference = np.load(MICRO/'references/P3/evaluation_only_labels.npy')
    observed = observe(reference)
    reference_metrics = {**flattened(describe(reference == 5)),
        **{key: observed['descriptors'][key] for key in ('all_regions','complete_regions','boundary_censored_regions','diameter_mean_px','diameter_std_px','aspect_mean','nearest_neighbor_mean_px','interface_density')}}
    descriptor_summaries = []
    for trial in order:
        for revision in (0,1):
            local = [r for r in morphology if r['trial_id'] == trial and r['revision'] == revision and r['feasible']]
            for key, value in reference_metrics.items():
                if isinstance(value,(bool,int,float)) and key != 'all_observed.preferred_axial_angle_deg':
                    values = [r[key] for r in local if isinstance(r.get(key),(bool,int,float))]
                    descriptor_summaries.append({'trial_id':trial,'revision':revision,'descriptor':key,
                        'reference_value':value,**statistics(values)})
    output = RUN / 'target_property_analysis'
    for name, data in [('HELDOUT_RESULTS', rows), ('SCRIPT_SUMMARIES', summaries), ('WITHIN_CONVERSATION_CHANGES', changes),
            ('IF_VERSUS_NF', comparison), ('SENSITIVITY_WITHOUT_NF01', sensitivity),
            ('MESH_CONFIRMATION', mesh), ('MESH_PAIRED_CHANGES', mesh_changes),
            ('NATIVE_CURVES', curves), ('PHASE_RESULTS', phases), ('MORPHOLOGY', morphology),
            ('MORPHOLOGY_REFERENCE_COMPARISON', descriptor_summaries)]:
        write(output / f'{name}.json', data)
        if isinstance(data, list): csv_table(output / f'{name}.csv', data)
    write(output / 'ANALYSIS_PROVENANCE.json', {'created_utc': now(),
        'protocol_sha256': sha(RUN / 'protocol/PROTOCOL.json'),
        'collective_freeze_sha256': sha(RUN / 'frozen_scripts/ALL_SIXTEEN_SCRIPTS_FROZEN.json'),
        'scripts': 16, 'conversations': 8, 'H1_attempts': 96, 'H2_slots': 32,
        'no_script_changes_after_heldout': True, 'no_pooled_seed_inference': True,
        'source_files': {str(p.relative_to(REPO)).replace('\\', '/'): sha(p) for p in
            sorted((RUN / 'mechanical_campaigns').glob('*heldout*'))}})
    print('DESCRIPTIVE ANALYSIS COMPLETE', flush=True)


if __name__ == '__main__':
    analyse()
