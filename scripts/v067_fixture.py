"""Original TRI6 submodel with measured cut-boundary displacement histories."""
from pathlib import Path
import argparse
import json
import numpy as np
from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest, artifact_root
from metamaterial_eval.simulation.mesh_generation import Mesh
from metamaterial_eval.simulation.reporting import write_json, mesh_hash
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.ansys_adapter import component
from metamaterial_eval.simulation.microstructure_pilot import vector_fields
from metamaterial_eval.simulation.general_contact_output import general_contact_vectors
from metamaterial_eval.simulation.progressive_compression import run_progressive
from scripts.v067_audit import REPO, RUN

BASE = artifact_root() / 'solver/v067'


def prepare():
    d = BASE / 'source_fixture_001'
    d.mkdir(parents=True, exist_ok=False)
    m, _, _ = resolve_manifest(REPO / 'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json', root=Path.home() / 'YoungDawgs-Artifacts')
    center = m.nodes[m.triangles[:, :3]].mean(axis=1)
    original_elements = np.flatnonzero((center[:, 0] >= 1.70) & (center[:, 0] <= 2.24) & (center[:, 1] >= 9.95))
    original_nodes = np.unique(m.triangles[original_elements])
    reverse = np.full(len(m.nodes), -1, dtype=np.int64)
    reverse[original_nodes] = np.arange(len(original_nodes))
    triangles = reverse[m.triangles[original_elements]]
    faces = np.concatenate([triangles[:, [0, 1, 3]], triangles[:, [1, 2, 4]], triangles[:, [2, 0, 5]]])
    _, ix, counts = np.unique(np.sort(faces[:, :2], axis=1), axis=0, return_index=True, return_counts=True)
    boundary = faces[ix[counts == 1]]
    original_faces = {tuple(sorted(edge)): i for i, edge in enumerate(m.boundary)}
    parent_boundary = np.array([original_faces.get(tuple(sorted(original_nodes[e])), -1) for e in boundary])
    groups = np.array([str(m.boundary_groups[i]) if i >= 0 else 'artificial_cut' for i in parent_boundary])
    for j, i in enumerate(parent_boundary):
        if i >= 0:
            boundary[j] = reverse[m.boundary[i]]
    cut = np.unique(boundary[parent_boundary < 0])
    mesh = Mesh(m.nodes[original_nodes].copy(), triangles, boundary, groups)
    np.savez_compressed(d / 'mesh.npz', nodes=mesh.nodes, triangles=triangles, boundary=boundary, boundary_groups=groups,
                        original_nodes_one_based=original_nodes + 1, original_elements_one_based=original_elements + 1,
                        original_boundary_indices=parent_boundary, cut_nodes_zero_based=cut)
    old = json.loads((REPO / 'experiments/pipeline_v0.6.6/run_001/summary/V0_6_6_VALIDATION.json').read_text(encoding='utf-8'))
    snapshots = sorted([s for s in old['snapshot_artifacts'] if s['model_variant'] == 'FINE_FULL_SELF_CONTACT_NODAL_V066_021'], key=lambda s: s['engineering_strain'])
    assert len(snapshots) == 15
    fields = []
    for s in snapshots:
        p = Path(s['directory']) / 'native_displacement.npy'
        u = np.load(p, mmap_mode='r')
        fields.append(np.asarray(u[original_nodes, :2]))
        s['native_displacement_sha256'] = file_hash(p)
    np.save(d / 'measured_displacements.npy', np.stack(fields))
    spec = {'schema': 'young-dawgs-v067-original-mesh-submodel', 'directory': str(d),
            'mesh_semantic_sha256': mesh_hash(mesh), 'mesh_archive_sha256': file_hash(d / 'mesh.npz'),
            'history_array_sha256': file_hash(d / 'measured_displacements.npy'), 'source_snapshots': snapshots,
            'ROI_original_mm': [1.70, 2.24, 9.95, 10.24], 'selection': 'Original TRI6 centroids in ROI, all six nodes retained exactly',
            'nodes': len(mesh.nodes), 'TRI6': len(triangles), 'physical_faces': int(sum(parent_boundary >= 0)),
            'artificial_cut_faces': int(sum(parent_boundary < 0)), 'cut_nodes': len(cut),
            'material': 'Unchanged E1000MPa, nu0.3, t1mm, plane stress, NLGEOM ON',
            'contact': 'All retained original physical exposed faces; generated artificial cut skins explicitly deleted. Original top faces retain independent rigid-platen pair.',
            'future_loading': 'Secant extrapolation from the final two measured cut fields, diagnostic only; no inferred full-specimen future field.',
            'parent_match_gate': json.loads((RUN / 'protocol/DIAGNOSTIC_PLAN_001.json').read_text(encoding='utf-8'))['local_parent_match']}
    write_json(d / 'fixture_manifest.json', spec)
    write_json(RUN / 'local_fixture/SOURCE_EXTRACTION.json', spec)
    print(json.dumps({k: spec[k] for k in ['nodes', 'TRI6', 'physical_faces', 'cut_nodes']}), flush=True)


def make_case(label, fkn, detection=2):
    source = BASE / 'source_fixture_001'
    spec = json.loads((source / 'fixture_manifest.json').read_text(encoding='utf-8'))
    assert file_hash(source / 'mesh.npz') == spec['mesh_archive_sha256']
    z = np.load(source / 'mesh.npz')
    xy, tri, boundary, groups = [z[k] for k in ['nodes', 'triangles', 'boundary', 'boundary_groups']]
    cut = z['cut_nodes_zero_based']
    history = np.load(source / 'measured_displacements.npy')
    n, ne = len(xy), len(tri)
    top_edges = boundary[groups == 'top']
    assert len(top_edges) > 0
    left, right, pilot = n + 1, n + 2, n + 3
    lines = ['/BATCH', '/CLEAR,START', '/FILNAME,compression', '/NOPR', '/PREP7',
             'ET,1,PLANE183', 'KEYOPT,1,1,1', 'KEYOPT,1,3,3', 'R,1,1', 'MP,EX,1,1000', 'MP,PRXY,1,.3', 'MP,MU,1,0', 'TYPE,1', 'REAL,1', 'MAT,1']
    lines += [f'N,{i},{x:.17g},{y:.17g}' for i, (x, y) in enumerate(xy, 1)]
    lines += ['EN,' + str(i) + ',' + ','.join(str(int(k) + 1) for k in t) for i, t in enumerate(tri, 1)]
    lines += component('CORNERS', np.unique(tri[:, :3]) + 1)
    lines += component('CUT_NODES', cut + 1)
    lines += ['ET,2,TARGE169', 'KEYOPT,2,2,1', 'ET,3,CONTA172', 'KEYOPT,3,2,1', 'KEYOPT,3,4,2', 'KEYOPT,3,10,1', 'R,3,,,100,-1e-5',
              f'N,{left},1.5,10.24', f'N,{right},2.45,10.24', f'N,{pilot},1.975,10.24', 'TYPE,2', 'REAL,3', 'TSHAP,LINE',
              f'EN,{ne+1},{left},{right}', 'TSHAP,PILO', f'EN,{ne+2},{pilot}', 'TYPE,3', 'MAT,1']
    lines += [f'EN,{ne+3+i},{a+1},{b+1},{mid+1}' for i, (a, b, mid) in enumerate(top_edges)]
    lines += ['ALLSEL,ALL', 'ESEL,S,TYPE,,1', 'GCGEN,NEW,42,0,PART,SELECT', 'GCGEN,SELECT', 'CM,ALL_GC,ELEM', 'ALLSEL,ALL']
    lines += component('PHYSICAL_NODES', np.unique(boundary[groups != 'artificial_cut']) + 1)
    lines += ['CMSEL,S,PHYSICAL_NODES', 'ESLN,S,1,ALL', 'CMSEL,R,ALL_GC', 'CM,INTERNAL_GC,ELEM',
              'CMSEL,S,ALL_GC', 'CMSEL,U,INTERNAL_GC', 'EDELE,ALL', 'ALLSEL,ALL',
              'CMSEL,S,INTERNAL_GC', 'EMODIF,ALL,TYPE,4', 'EMODIF,ALL,SECNUM,4', 'ALLSEL,ALL',
              '*GET,ETMAX,ETYP,0,NUM,MAX', '*DO,IT,4,ETMAX', 'KEYOPT,IT,2,1', f'KEYOPT,IT,4,{detection}', 'KEYOPT,IT,10,0', '*ENDDO',
              f'R,100,,,{fkn},-1e-5', 'GCDEF,SYMM,ALL,SELF,1,100',
              f'D,{pilot},UX,0', f'D,{pilot},UY,0', f'D,{pilot},ROTZ,0', '/GOPR', '/OUTPUT,local_inventory,txt',
              'ETLIST,ALL', 'RLIST,ALL', 'GCDEF,LIST', 'CMSEL,S,INTERNAL_GC', '*GET,NGC,ELEM,0,COUNT', '*STATUS,NGC', 'ALLSEL,ALL', '/OUTPUT',
              'CMSEL,S,INTERNAL_GC', '*CFOPEN,gc_topology,csv', '*VWRITE', "('element,i,j,mid,type,section')", 'IE=0', '*DO,KK,1,NGC', 'IE=ELNEXT(IE)',
              '*GET,NI,ELEM,IE,NODE,1', '*GET,NJ,ELEM,IE,NODE,2', '*GET,NM,ELEM,IE,NODE,3', '*GET,TY,ELEM,IE,ATTR,TYPE', '*GET,SC,ELEM,IE,ATTR,SECN',
              '*VWRITE,IE,NI,NJ,NM,TY,SC', "(F12.0,5(',',F12.0))", '*ENDDO', '*CFCLOS', 'ALLSEL,ALL',
              'FINISH', 'SAVE,initial,db', '/SOLU', 'ANTYPE,STATIC', 'NLGEOM,ON', 'EQSLV,SPARSE', 'NROPT,FULL', 'LNSRCH,ON',
              'CNVTOL,F,,.005,2,1e-8', 'NEQIT,24', 'AUTOTS,ON', 'RESCONTROL,DEFINE,ALL,1,-1,,3',
              'NLDIAG,CONT,ITER', 'NLDIAG,NRRE,ON,2', 'NLDIAG,EFLG,ON,2', 'OUTRES,ALL,ALL']
    times = [s['engineering_strain'] for s in spec['source_snapshots']]
    # Continue slightly past both historical failed trial times under explicitly hypothetical cut motion.
    targets = times + [.009387795, .009504981, .00975, .01]
    for j, time in enumerate(targets):
        values = history[j] if j < len(times) else history[-1] + (history[-1] - history[-2]) * ((time - times[-1]) / (times[-1] - times[-2]))
        lines += [f'TIME,{time:.17g}', 'NSUBST,2,240,1,OFF', f'D,{pilot},UY,{-10.24*time:.17g}']
        for i in cut:
            lines += [f'D,{i+1},UX,{values[i,0]:.17g}', f'D,{i+1},UY,{values[i,1]:.17g}']
        lines += ['SOLVE']
    lines += ['FINISH', 'SAVE,checkpoint,db,,MODEL', '/EXIT,NOSAVE']
    d = BASE / label
    d.mkdir(parents=True, exist_ok=False)
    (d / 'input.inp').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    manifest = {'model_variant': 'ORIGINAL_MESH_LOCAL_DIAGNOSTIC', 'fixture_sha256': file_hash(source / 'fixture_manifest.json'),
                'input_sha256': file_hash(d / 'input.inp'), 'GC_FKN': fkn, 'platen_FKN': 100, 'FTOLN_mm': -1e-5, 'GC_detection_keyopt4': detection,
                'targets': targets, 'measured_parent_count': len(times), 'diagnostic_extrapolation_after': times[-1],
                'source_body_section_preserved': 4, 'source_body_section_evidence': 'parent_section_probe_001 actual licensed v241 readback',
                'model': {'specimen_nodes': n, 'specimen_TRI6': ne, 'user_model_nodes': n+3,
                          'user_model_elements': ne + 2 + len(top_edges) + 2*len(boundary), 'controls': {'top': pilot},
                          'general_contact_component': 'INTERNAL_GC'}}
    write_json(d / 'simulation_manifest.json', manifest)
    target = RUN / 'local_fixture' / ('prepared_' + label)
    target.mkdir(exist_ok=False)
    (target / 'input.inp').write_bytes((d / 'input.inp').read_bytes())
    write_json(target / 'simulation_manifest.json', manifest)
    print(d, flush=True)


def execute(label):
    d = BASE / label
    r = run_progressive(d, timeout=1200, no_progress_seconds=240, cores=2, disk_reserve=80*1024**3)
    from scripts.v066_restart import compact
    compact(d, RUN / 'local_fixture' / label)
    print(label, r['status'], r['process']['returncode'], r['converged_steps'][-3:], flush=True)


def post(label):
    from metamaterial_eval.simulation.microstructure_pilot import database_resume
    from scripts.v066_restart import compact
    source = BASE / label
    manifest = json.loads((source / 'simulation_manifest.json').read_text(encoding='utf-8'))
    telemetry = json.loads((source / 'nonlinear_telemetry.json').read_text(encoding='utf-8'))
    z = np.load(BASE / 'source_fixture_001/mesh.npz')
    last = {}
    for r in telemetry['converged_substeps']:
        last[r['load_step']] = r
    d = BASE / (label + '_post001')
    d.mkdir(parents=True, exist_ok=False)
    lines = ['/BATCH', '/CLEAR,START', database_resume(source / 'initial.db').strip(), '/FILNAME,readonly', '/POST1',
             "FILE,'" + (source / 'compression').as_posix() + "',rst", '/OUTPUT,result_sets,txt', 'SET,LIST', '/OUTPUT']
    states = []
    for j, (ls, r) in enumerate(last.items(), 1):
        prefix = f'state{j:03d}'
        lines += [f"SET,{ls},{r['substep']}", '*GET,NTIME,ACTIVE,0,SET,TIME', f'*CFOPEN,{prefix}_time,csv', '*VWRITE', "('pseudo_time')", '*VWRITE,NTIME', '(E24.16)', '*CFCLOS'] + vector_fields(manifest['model']['specimen_nodes'], prefix)
        lines += ['ALLSEL,ALL', 'ETABLE,ERAS', 'ETABLE,CNSTAT,NMISC,19']
        lines += general_contact_vectors(manifest['model'], prefix, chunk_size=10000)
        lines += [f'*CFOPEN,{prefix}_reactions,csv', '*VWRITE', "('node,rx_N,ry_N')"]
        for i in list(z['cut_nodes_zero_based'] + 1) + [manifest['model']['controls']['top']]:
            lines += [f'*GET,RX,NODE,{i},RF,FX', f'*GET,RY,NODE,{i},RF,FY', f'*VWRITE,{i},RX,RY', "(F12.0,2(',',E24.16))"]
        lines += ['*CFCLOS']
        states.append({'prefix': prefix, 'load_step': ls, 'substep': r['substep'], 'time': r['pseudo_time']})
    lines += ['FINISH', '/EXIT,NOSAVE']
    (d / 'input.inp').write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
    write_json(d / 'provenance.json', {'source_RST_sha256': file_hash(source / 'compression.rst'),
                                      'source_database_sha256': file_hash(source / 'initial.db'), 'states': states,
                                      'source_receipt_sha256': file_hash(source / 'execution_receipt.json'),
                                      'input_sha256': file_hash(d / 'input.inp'), 'mode': 'READ_ONLY_NATIVE_POST1'})
    r = run_progressive(d, timeout=180, solve=False, cores=1)
    compact(d, RUN / 'local_fixture' / d.name)
    print(d.name, r['status'], r['process']['returncode'], flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('action', choices=['prepare', 'case', 'execute', 'post'])
    p.add_argument('--label', default='local_baseline_001')
    p.add_argument('--fkn', type=float, default=100)
    p.add_argument('--detection', type=int, choices=[2,3], default=2)
    a = p.parse_args()
    if a.action == 'prepare': prepare()
    elif a.action == 'case': make_case(a.label, a.fkn, a.detection)
    elif a.action == 'execute': execute(a.label)
    else: post(a.label)
