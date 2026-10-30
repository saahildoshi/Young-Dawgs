"""Authenticate the unchanged baseline and register progressive execution."""
from pathlib import Path
from dataclasses import asdict
from datetime import datetime,timezone
import json
import subprocess
import psutil
import shutil
from metamaterial_eval.simulation.mesh_artifacts import artifact_root,resolve_manifest,SOURCE,HISTORICAL
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.system_health import HealthPolicy
from metamaterial_eval.simulation.reporting import write_json

REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'experiments/pipeline_v0.6.6/run_001'


def main():
    for name in ['audit','protocol','restart_validation','internal_contact','mesh_strategy','progressive_compression',
                 'deformation','mechanical_results','figures','performance','summary','verification']:
        (RUN/name).mkdir(parents=True,exist_ok=False)
    base=artifact_root()/'solver/v065/full_recovery_001'
    receipt=json.loads((base/'execution_receipt.json').read_text());native={}
    for name in ['input.inp','compression.rst','compression.rdb','compression.r001','compression.ldhi','checkpoint.db']:
        path=base/name;digest=file_hash(path)
        expected=receipt['input_sha256'] if name=='input.inp' else receipt['process']['artifacts'][name]['sha256']
        assert digest==expected
        native[name]={'bytes':path.stat().st_size,'sha256':digest}
    geometry=REPO/'experiments/pipeline_v0.5/baseline_vectorization/run_003/fixture_B_design009_seed001/polygon_candidate.wkb'
    assert file_hash(geometry)==SOURCE
    mesh,manifest,_=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    assert manifest['semantic_sha256']==HISTORICAL
    assert json.loads((REPO/'experiments/pipeline_v0.6.5/run_001/mechanical_results/qualification.json').read_text())['accepted']
    audit={
        'schema':'young-dawgs-v0.6.6-audit','started_utc':datetime.now(timezone.utc).isoformat(),
        'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'branch':'master','working_tree_at_start':'CLEAN; audit script is task-created',
        'repository':str(REPO),'former_repository':'OneDrive checkout empty; registered project moved to Projects',
        'source_geometry_sha256':SOURCE,'fine_mesh_semantic_sha256':HISTORICAL,
        'fine_nodes':len(mesh.nodes),'fine_TRI6':len(mesh.triangles),'exposed_edges':len(mesh.boundary),
        'pore_edges':int((mesh.boundary_groups=='pore').sum()),'pores':412,
        'native_v065_directory':str(base),'native_v065_authenticated_files':native,
        'restart_status':'RDB/LDHI/R001 authenticated; actual continuation requires small licensed qualification',
        'v065_output_limitation':'Exporter assumes single LS1/SS1 and normal source exit; add multi-set/last-valid support separately',
        'v065_monitor_limitation':'Total32update/3cutback cap inappropriate for progressive study; use progress-aware monitoring',
        'physical_RAM_bytes':psutil.virtual_memory().total,'available_RAM_bytes':psutil.virtual_memory().available,
        'disk_free_bytes':shutil.disk_usage(artifact_root()).free,
        'request_sha256':file_hash(Path(r'C:\Users\sd22446\.codex\attachments\d65b06fc-03aa-4ee5-91e1-4474d613f90d\Pasted text.txt')),
    }
    write_json(RUN/'audit/initial.json',audit)
    plan={
        'schema':'young-dawgs-v0.6.6-prospective-plan','primary_target':.3,'stretch_target':.4,
        'planned_loading_checkpoints':[.0001,.001,.01,.05,.1,.2,.3,.4],'baseline_strain':.00005,
        'load_control':'Total upper UY=-original_height*engineering_strain; never additive',
        'primary_model':'Authenticated fine v065 nonlinear restart if small tests pass; finalize mesh before campaign',
        'mesh_candidate':{
            'maximum_candidates':1,'boundary_size_mm':.005,'bulk_size_mm':.06,'meshing_policy':'Existing POLICY_B, exact WKB',
            'gate':'Frozen10deg and all topology/area/boundary/mapping gates; actual registered >=3 sampled TRI6 chord criterion; explicitly compare fine observed>=7',
            'benchmark_relative_force_tolerance':.05,'mechanical_mesh_convergence':'UNQUALIFIED',
            'selection':'Smaller only if original gates pass, matched0.005% force within5%, and materially cheaper; otherwise retain fine. No failed8.303deg reuse.',
        },
        'small_restart_tests':{
            'fixtures':['accepted rectangle','compliant nodal fixture'],
            'compare':'Continuous two-load-step versus clean-exit multiframe restart; total targets .0025 then .005',
            'relative_response_tolerance':1e-5,
            'output':'Required fields LAST per distinct load step; enumerate actual sets; reject debug999999/missing states',
        },
        'internal_contact':{
            'method_candidates':['GCGEN/GCDEF general contact','CONTA172/TARGE169 explicit pairs if necessary'],
            'small_fixture':'Initially separated deformable walls; enabled/disabled crossing comparison, normals/exclusions, force/gap/penetration/equilibrium',
            'full_selection':'Qualify small first; assess213150pore edges before full GC. Preserve platen model; platen-only exploratory fallback requires overlap screen.',
        },
        'overlap_screen':{
            'broad_phase':'STRtree; never unrestricted all-pairs',
            'quadratic_boundary':'Adaptive subdivision with exact chord-deviation bound, loop identities and shared-original-vertex exclusions',
            'invalid_crossings':'Quarantine even when Newton converged',
            'uncertainty':'Near-touch within approximation error flagged, not silently certified continuous nonpenetration',
        },
        'nonlinear_controls':{
            'NLGEOM':'ON','NROPT':'FULL','LNSRCH':'ON','NEQIT':24,'AUTOTS':'ON',
            'initial_global_strain_increment_max':.0005,'maximum_global_strain_increment':.005,
            'minimum_global_strain_increment':1e-6,'force_CNVTOL_relative':.005,'force_CNVTOL_minref_N':1e-8,
            'material':'Existing E1000MPa,nu.3,t1,plane stress, linear elasticity; no new plasticity/stabilization/springs',
        },
        'resources':{
            'process_RSS_limit':None,'system_health_policy':asdict(HealthPolicy()),
            'campaign_wall_seconds':21600,'stage_wall_seconds':5400,'no_converged_progress_seconds':1800,
            'disk_reserve_bytes':40*1024**3,'diagnostic_bytes_per_job':2*1024**3,
            'NR_snapshot_count':2,'EFLG_snapshot_count':2,'retained_restart_frames_per_stage':3,'concurrent_large_solvers':1,
        },
        'continuation_gate':{
            'reaction_balance_relative_max':.01,'contact_force_opposition_relative_max':.01,'stored_endpoint_penetration_max_mm':1e-5,
            'deformed_TRI6':'Positive every element under registered analytic polynomial floating-point check',
            'field_completeness':'All-node U/supported native S/EPEL, independent POST1, complete provenance',
            'overlap':'No unexplained nonadjacent crossing/inverted solid loop; near-touch uncertainty classified',
            'last_valid_checkpoint':'Copy immutable parent into new job before restart; never mutate accepted parent',
            'curve':'Only validated actual states; scalar-only native history separate; no invented extension',
        },
        'registered_initial_fit_interval':[.00005,.001],'fit_minimum_points':3,
        'compression_work':'Trapezoidal only with adequate actual sampling; report quadrature limitations',
        'no_3D_batch_or_LLM_optimization':True,'target_work_period':'November2-8,2026; current task authorizes actual execution; no scheduled automation',
        'sources':{
            'restart':'https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_ANTYPE.html',
            'GCGEN':'https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_GCGEN.html',
            'GCDEF':'https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_GCDEF.html',
            'release_limit':'Public v241 command page inaccessible; adjacent primary docs guide syntax, actual v241 tests establish support',
        },
    }
    write_json(RUN/'protocol/LARGE_STRAIN_PLAN_001.json',plan)
    doc=REPO/'docs/pipeline_v0.6.6';doc.mkdir(exist_ok=False)
    (doc/'AUDIT_AND_PLAN.md').write_text('''# v0.6.6 progressive compression protocol

Started clean on master at ce6f601da40784621f3324b7e5805983704973b9.
The repository moved from OneDrive to Projects. Previous pasted AGENTS
instructions were revoked; the current task separately requires descriptive
commits, verification and preservation, followed here. No historical source,
fine mesh, accepted RST or scientific HOLD will be rewritten.

Source WKB, fine semantic mesh and v065 RST/RDB/R001/LDHI/model DB hashes match
saved receipts. Demonstrate actual clean-exit restart and multi-result readback
on rectangle and compliant fixtures before large continuation.

Investigate general contact on a deterministic gap-closing deformable fixture,
including disabled crossing, exclusions and actual force. The fine model has
213150 pore edges. Full activation needs small qualification and feasibility
evidence. A platen-only exploratory fallback must screen actual curved deformed
boundaries and quarantine unmodeled crossing or uncertain near contact.

One optional exact-source lower-cost mesh is registered at0.005mm boundary /
0.06mm bulk with existing POLICY_B. Preserve10degree/area/topology/mapping gates
and the actual registered>=3 sampled-chord criterion; explicitly compare the
fine mesh's observed>=7. Do not reuse the failed8.303degree trial. Compare the
matched0.005% response prospectively within5%; no mechanical mesh convergence
claim. This experiment must not prevent substantive progressive execution.

Target30% compression;40% stretch. Total cumulative displacement, automatic
substeps, complete endpoint fields and compact converged scalar history are
registered in JSON. Retain restart frames separately. Distinguish maximum
Newton-converged strain from maximum fully qualified strain after any failure.

No fixed process RSS cap. Keep sustained system-health safeguards,40GiB disk
reserve, finite6hour campaign/90minute stage windows and30minute no-converged-
progress stop. Copy immutable parents before restart. Gate further loading by
actual fields, force/contact balance, positive mappings and overlap screening.
No fabricated curve, arbitrary material failure thresholds,3D,batch designs or
autonomous optimization. The target week is Nov2-8; the current request also
authorizes preparation and actual execution now, without scheduled automation.
''',encoding='utf-8')
    print('Audit and protocol saved. Available GiB',audit['available_RAM_bytes']/1024**3)


if __name__=='__main__':main()
