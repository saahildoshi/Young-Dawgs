"""Authenticate the immutable onset parent and register bounded diagnosis."""
from datetime import datetime, timezone
from pathlib import Path
import json
import re
import shutil
import subprocess
import psutil
from metamaterial_eval.simulation.mesh_artifacts import artifact_root, resolve_manifest, SOURCE, HISTORICAL
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / 'experiments/pipeline_v0.6.7/run_001'
REQUEST = Path(r'C:\Users\sd22446\.codex\attachments\f500b868-4068-4a29-b0a1-138cfd59aa2d\Pasted text.txt')


def main():
    for name in ['audit', 'protocol', 'contact_onset', 'local_fixture', 'contact_correction',
                 'restart_validation', 'progressive_compression', 'deformation',
                 'mechanical_results', 'figures', 'performance', 'summary', 'verification']:
        (RUN / name).mkdir(parents=True, exist_ok=False)
    old = REPO / 'experiments/pipeline_v0.6.6/run_001'
    parent = json.loads((old / 'restart_validation/FINAL_VALID_NATIVE_RESTART.json').read_text(encoding='utf-8'))
    native = {}
    for name, expected in {**parent['required_native_files'], 'compression.rst': parent['RST_binding']}.items():
        path = Path(parent['source']) / name
        assert path.stat().st_size == expected['bytes'] and file_hash(path) == expected['sha256'], name
        native[name] = expected
    source = REPO / 'experiments/pipeline_v0.5/baseline_vectorization/run_003/fixture_B_design009_seed001/polygon_candidate.wkb'
    assert file_hash(source) == SOURCE
    mesh, manifest, location = resolve_manifest(REPO / 'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json', root=Path.home() / 'YoungDawgs-Artifacts')
    assert manifest['semantic_sha256'] == HISTORICAL
    request = REQUEST.read_text(encoding='utf-8')
    questions = [{'number': int(n), 'question': q} for n, q in re.findall(r'^(\d+)\. (.+\?)\s*$', request.split('# 54. REQUIRED FINAL HANDOFF QUESTIONS', 1)[1], re.M)]
    assert [q['number'] for q in questions] == list(range(1, 113))
    write_json(RUN / 'protocol/HANDOFF_QUESTIONS.json', {'request_sha256': file_hash(REQUEST), 'questions': questions})
    started = datetime.now(timezone.utc)
    audit = {'started_utc': started.isoformat(), 'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
             'branch': subprocess.check_output(['git', 'branch', '--show-current'], text=True).strip(),
             'initial_tree': 'CLEAN before task-created script', 'repository': str(REPO),
             'request_sha256': file_hash(REQUEST), 'source_sha256': SOURCE,
             'fine_mesh': {'semantic_sha256': HISTORICAL, 'archive': str(location), 'byte_sha256': file_hash(location),
                           'nodes': len(mesh.nodes), 'TRI6': len(mesh.triangles), 'boundary_faces': len(mesh.boundary)},
             'parent_native_files': native, 'parent_state': parent['state'], 'parent_source': parent['source'],
             'accepted_qualification_sha256': file_hash(old / 'mechanical_results/fine_nodal_recovery01_001_qualification001.json'),
             'available_RAM_bytes': psutil.virtual_memory().available, 'disk_free_bytes': shutil.disk_usage(artifact_root()).free,
             'historical_files_modified': False}
    assert audit['accepted_qualification_sha256'] == parent['parent_qualification_sha256']
    write_json(RUN / 'audit/INITIAL_AUTHENTICATION.json', audit)
    protocol = {
        'registered_utc': started.isoformat(), 'campaign_wall_seconds': 43200,
        'clock_origin': 'INITIAL_AUTHENTICATION.started_utc; no automatic extension',
        'diagnosis_and_local_solver_budget_seconds': 10800, 'local_cases_maximum': 4,
        'full_primary_attempts_maximum': 1, 'conditional_full_retry_maximum': 1,
        'conditional_retry_rule': 'Only an unambiguous technical defect, documented and corrected; no repeated numerical stall.',
        'stage_wall_seconds': 5400, 'no_converged_progress_seconds': 1800,
        'concurrent_native_jobs': 1, 'cores': 8, 'RSS_cap': None, 'disk_reserve_bytes': 80 * 1024**3,
        'primary_target': .30, 'stretch_target': .40,
        'full_checkpoints': [.0095, .01, .011, .015, .02, .05, .10, .20, .30, .40],
        'sequence': ['native residual localization', 'original-mesh fixture with measured parent cut displacements',
                     'bounded local baseline/corrections', 'actual v241 restart-compatibility test',
                     'freeze and commit full correction protocol', 'one full recovery and progressive loading if qualified'],
        'local_candidates': ['unchanged FKN100 baseline', 'smaller onset increments if needed',
                             'GC FKN10 preserving platen FKN100', 'GC FKN1 only if justified by preceding evidence'],
        'candidate_rationale': 'Test excessive penalty stiffness versus contact switching; numerical hypothesis until licensed fixture evidence.',
        'local_parent_match': {'cut_displacement_absolute_mm': 1e-10, 'core_U_RMS_relative_to_parent_maximum': .02,
                               'core_stress_strain_RMS_relative': .10,
                               'near_contact_gap': 'Report signed quadratic gap differences explicitly; no micron-scale match claim for a nanometre near-touch.'},
        'local_future_loading': 'Measured history through parent; any secant extrapolation beyond parent is diagnostic hypothesis only.',
        'local_failure_gate': 'Reproduce native onset or report missing context; no causal qualification from a mismatching fixture.',
        'mechanical_gates': {'signed_reaction_balance_max': .01, 'contact_force_opposition_max': .01,
                             'penetration_max_mm': 1e-5, 'CNVTOL_F': [.005, 2, 1e-8],
                             'Jacobian': 'Positive all deformed TRI6', 'overlap': 'Existing exact quadratic/nodal protocol; no unexplained solid crossing',
                             'fields': 'Native U, S, EPEL, contact and independent POST1 provenance required'},
        'restart_route': 'Only verified numerical real/control changes may use authenticated ENDSTEP clone; topology/integration changes require fresh same-fine-mesh branch.',
        'output': 'Complete accepted checkpoint fields, numeric restart frequency1, bounded NR/EFLG2 and contact iteration diagnostics.',
        'historical_hold': 'Rejected 1% Gauss/platen-only exact crossings remain rejected. No accepted full internal contact yet.',
        'physical_assumptions': 'Unchanged E1000MPa, nu0.3, t1mm, plane stress; uncalibrated elastic material.',
        'prohibitions': ['geometry modification', 'contact deletion', 'tolerance relaxation', 'curve splicing', '3D', 'LLM optimization']}
    write_json(RUN / 'protocol/DIAGNOSTIC_PLAN_001.json', protocol)
    print(json.dumps({'authenticated': audit['parent_state'], 'mesh_nodes': len(mesh.nodes), 'questions': len(questions), 'run': str(RUN)}), flush=True)


if __name__ == '__main__':
    main()
