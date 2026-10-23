"""Verify and index the additive B1 deliverable after reports and visual QA."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

OUTPUT = Path(__file__).resolve().parents[1]
ROOT = OUTPUT.parents[3]
sys.path.insert(0, str(ROOT))
from metamaterial_eval.geometry.reporting import repository_inventory
from metamaterial_eval.geometry.sensitivity.sources import load_fixture


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def main():
    verification = OUTPUT / 'verification'
    initial = read(verification / 'SESSION_INITIAL_INVENTORY.json')
    changed = [p for p, h in initial.items() if not (ROOT / p).is_file() or digest(ROOT / p) != h]
    assert len(initial) == 3226 and not changed, changed
    protocol = read(OUTPUT / 'protocol.json')
    code_changed = [p for p, h in protocol['code_sha256'].items() if digest(ROOT / p) != h]
    assert not code_changed, code_changed
    sources = [load_fixture(ROOT, protocol['config'], name) for name in protocol['config']['fixture_ids']]
    s = read(OUTPUT / 'summary' / 'SIMPLIFICATION_SENSITIVITY.json')
    assert (s['primary_completed'], s['negative_control_completed']) == (40, 3)
    assert not s['execution_failures'] and s['existing_files_unchanged']
    records = [{**r, 'metrics': read(OUTPUT / r['metrics_file'])} for r in s['candidates']]
    assert len({(r['fixture'], r['study_role'], r['epsilon']) for r in records}) == 43
    for r in records:
        m = r['metrics']
        assert m['deterministic_geometry_bytes'] and m['production_accepted'] is False
        assert digest(OUTPUT / r['relative_directory'] / 'diagnostic_candidate.wkb') == r['candidate_sha256'] == m['candidate_sha256']
        raster = np.load(OUTPUT / r['relative_directory'] / 'reconstructed.npy', allow_pickle=False)
        source = next(f for f in sources if f['provenance']['fixture'] == r['fixture'])['mask']
        fp = int(np.count_nonzero((raster == 1) & (source == 0)))
        fn = int(np.count_nonzero((raster == 0) & (source == 1)))
        assert fp == m['raster_from_canonical']['false_positive_pixels']
        assert fn == m['raster_from_canonical']['false_negative_pixels']
        assert fp + fn == m['raster_from_canonical']['xor_pixels']
    primary = [r for r in records if r['study_role'] == 'primary']
    assert all(r['metrics']['validity']['ogc_valid'] and r['metrics']['manifold']['manifold'] for r in primary)
    assert not any(r['events']['hole_topology_change'] or r['events']['continuous_connectivity_change'] or r['events']['exterior_channel_change'] for r in primary)
    assert not any(r['events']['raster_topology_change'] or r['events']['monitored_neck_link_lost'] for r in primary)
    assert all(not r['promising_under_strict_available_diagnostics'] for r in primary)
    moderate = [r for r in primary if r['epsilon'] == .5]
    assert all(r['metrics']['raster_from_canonical']['xor_pixels'] == 0 and not r['metrics']['morphology']['comparison']['any_descriptor_change'] for r in moderate)
    unknown = [n for r in primary if r['epsilon'] == 1 for n in r['metrics']['features']['repairs']]
    assert len(unknown) == 24 and all(n['clearance'] is None and n['contact_remains_resolved'] is None for n in unknown)
    direct = read(verification / 'DIRECT_DISTANCE_CHECKS.json')
    repeat = read(verification / 'REPEATED_RUN_CHECK.json')
    assert direct['passed'] and direct['count'] == 104 and repeat['all_43_reproduce']
    suites = list(ET.parse(verification / 'pytest-junit.xml').getroot().iter('testsuite'))
    assert sum(int(x.get('tests', 0)) for x in suites) == 316
    assert not any(int(x.get(k, 0)) for x in suites for k in ('failures', 'errors', 'skipped'))
    figures = sorted((OUTPUT / 'figures').glob('*.png'))
    assert len(figures) == 14
    image_records = []
    for p in figures:
        with Image.open(p) as im:
            image_records.append({'file': p.relative_to(OUTPUT).as_posix(), 'size_pixels': list(im.size), 'visually_inspected': True})
            im.verify()
    write(verification / 'FIGURE_QA.json', {'figures': image_records,
          'notes': ['Figures 01–11 are frozen reporting outputs. Figure 05 omits unavailable measurements and ends at epsilon .75; Figure 14 additionally displays epsilon 1 and undefined counts.',
                    'Supplemental Figure 13 was re-rendered to reserve title space and recursively draw clipped boundary collections. Final render visually rechecked; metrics and candidate geometry unchanged.']})
    maximum = max(primary, key=lambda r: r['metrics']['distance_from_manifold']['measured_hausdorff_lower'])
    base = read(OUTPUT / 'baselines.json')
    findings = {'status': 'EXPLORATORY_SENSITIVITY_STUDY_COMPLETE', 'units': 'native_1024_raster_cell',
                'unique_configurations': 43, 'retained_evaluations_across_two_runs': 86,
                'primary_all_ogc_valid_manifold_and_region_correspondence_preserved': True,
                'primary_all_raster_connectivity_and_percolation_preserved': True,
                'no_monitored_solid_link_loss_detected': True, 'neck_screening_exhaustive': False,
                'no_common_positive_reduction_all_diagnostic_pass': True,
                'production_tolerance_selected': False, 'full_v0_5B_acceptance': False,
                'repair_clearances_unknown_at_epsilon_1': 24, 'unknown_means_proven_repair_destruction': False,
                'maximum_primary_boundary_distance': {'fixture': maximum['fixture'], 'epsilon': maximum['epsilon'], **maximum['metrics']['distance_from_manifold']},
                'moderate_epsilon_0p5': [{'fixture': r['fixture'], 'vertices': r['vertices'],
                     'reduction_percent': r['vertex_reduction_percent'], 'area_from_manifold': r['metrics']['area_from_manifold'],
                     'area_from_exact': r['metrics']['area_from_exact'],
                     'raster_xor': r['metrics']['raster_from_canonical']['xor_pixels'], 'all_frozen_descriptors_exactly_equal': True,
                     'diagnostic_flags': r['metrics']['diagnostic_flags']} for r in moderate],
                'characterization_seconds': base['characterization_seconds'], 'sweep_seconds': s['total_sweep_seconds'],
                'peak_traced_candidate_bytes': s['peak_traced_candidate_bytes'],
                'process_lifetime_peak_rss_bytes': s['process_lifetime_peak_rss_bytes'],
                'first_event_sequences': s['thresholds'],
                'future_architecture': 'Freeze full feature-region boundary subsets and prevent neighboring chords entering guards; constrain free arcs and validate relevant widths, region identities, manifoldness and independent error budgets; deterministic no-op fallback. Recommendation only.'}
    write(OUTPUT / 'summary' / 'SCIENTIFIC_FINDINGS.json', findings)
    write(verification / 'PRESERVATION.json', {'preexisting_files_checked': len(initial), 'byte_identical': not changed,
          'changed_or_missing': changed, 'registered_code_configuration_hashes_checked': len(protocol['code_sha256']),
          'registered_code_unchanged': not code_changed, 'five_accepted_sources_reauthenticated': True,
          'initial_inventory': 'SESSION_INITIAL_INVENTORY.json',
          'exclusions': ['.git', '.venv', '.venv-macos', '__pycache__', '.pytest_cache', 'metamaterial_eval.egg-info'],
          'preexisting_git_local_changes_preserved': True})
    modules = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'metamaterial_eval/geometry/sensitivity').glob('*.py'))
    docs = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'docs/pipeline_v0.5').glob('*') if p.is_file() and p.relative_to(ROOT).as_posix() not in initial)
    lines = ['# v0.5B1 session changes', '', 'All changes are additive. Zero of the 3,226 pre-existing inventoried files changed.', '',
             '## New implementation', '', *['- `' + p + '`' for p in modules], '', '- `tests/test_simplification_sensitivity.py` (29 tests)', '',
             '## New documentation', '', *['- `' + p + '`' for p in docs], '', '## New experimental artifacts', '',
             '- `experiments/pipeline_v0.5/simplification_sensitivity/run_001/`: retained first 43 evaluations, frozen snapshots and correction coverage note.',
             '- `experiments/pipeline_v0.5/simplification_sensitivity/run_002/`: corrected final 43 evaluations, five baselines, authenticated caches, snapshots, JSON/CSV/Markdown reports, fourteen figures and verification artifacts.',
             '', 'The exact file list, byte sizes and SHA-256 hashes are in new_files.json. That ledger excludes its own bytes to avoid a circular hash. Virtual environments, Git metadata and transient caches are excluded consistently with the initial snapshot.', '',
             'No source generator, frozen evaluator, existing test, exact geometry, accepted manifold candidate, historical experiment or historical acceptance decision was edited. B2 protection remains a proposed architecture only.']
    (verification / 'CHANGES.md').write_text('\n'.join(lines) + '\n')
    completion = {'stage': 'v0.5B1', 'status': 'EXPLORATORY_SENSITIVITY_STUDY_COMPLETE',
                  'authoritative_run': OUTPUT.relative_to(ROOT).as_posix(), 'primary_configurations': 40,
                  'negative_control_configurations': 3, 'execution_failures': 0,
                  'retained_runs': ['run_001', 'run_002'], 'unique_configurations': 43, 'recorded_candidate_evaluations': 86,
                  'reporting_correction_disclosed': True, 'same_geometry_rasters_measurements_reproduced': True,
                  'full_regression': {'passed': 316, 'failed': 0, 'previous_tests': 287, 'new_tests': 29},
                  'historical_files_byte_identical': 3226, 'registered_code_hashes_match': True,
                  'figures_visually_inspected': 14, 'direct_distance_checks': 104,
                  'scientific_acceptance': 'Diagnostic sensitivity study only; no simplified candidate selected for production.',
                  'production_tolerance_selected': False, 'full_v0_5B_acceptance': False,
                  'v0_5B2_implemented': False, 'v0_5C_or_later_implemented': False,
                  'physical_mechanical_manufacturing': 'UNQUALIFIED', 'windows_execution_performed': False,
                  'historical_exact_v0_5A': 'HOLD_UNCHANGED', 'historical_v0_5A_1': 'SCOPED_AMENDED_PASS_UNCHANGED',
                  'sweep_summary_status_note': 'The sweep JSON preserves its execution-stage pending-report status. This additive completion record follows report, regression, QA and preservation verification.'}
    write(verification / 'COMPLETION.json', completion)
    current = repository_inventory(ROOT, ROOT / '__no_output_exclusion__')
    ledger_path = (verification / 'new_files.json').relative_to(ROOT).as_posix()
    new = [{'path': p, 'sha256': h, 'bytes': (ROOT / p).stat().st_size} for p, h in current.items() if p not in initial and p != ledger_path]
    write(verification / 'new_files.json', {'new_files': new, 'count_excluding_ledger': len(new),
          'ledger_self_excluded': ledger_path, 'modified_preexisting_files': [], 'initial_file_count': len(initial)})
    print(f'Complete: 316 tests; 43 configurations; 14 figures; 104 direct distance checks; {len(initial)} historical files unchanged; {len(new)} new files plus this ledger.')


if __name__ == '__main__':
    main()
