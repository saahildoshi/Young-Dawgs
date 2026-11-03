"""Authenticate historical foundation and register independent execution tracks."""
from datetime import datetime,timezone
from pathlib import Path
import re
import subprocess
import shutil
import psutil
from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest,SOURCE,HISTORICAL,artifact_root
from metamaterial_eval.simulation.system_health import HealthPolicy
from dataclasses import asdict
from scripts.v068_common import REPO,RUN,BASE,REQUEST,read,write_json,file_hash


def main():
    assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip() or not (RUN/'audit/INITIAL.json').exists()
    for name in ['audit','protocol','track_A_local_fixture','track_A_unified_detection','track_A_restart','track_B_geometry',
                 'track_B_mesh','track_B_contact_fixture','track_B_progressive_compression','track_B_native_results',
                 'track_B_deformation','mechanical_results','contact_diagnostics','performance','figures','summary','verification']:
        (RUN/name).mkdir(parents=True,exist_ok=False)
    old=REPO/'experiments/pipeline_v0.6.6/run_001'
    parent=read(old/'restart_validation/FINAL_VALID_NATIVE_RESTART.json'); authenticated={}
    for name,entry in {**parent['required_native_files'],'compression.rst':parent['RST_binding']}.items():
        p=Path(parent['source'])/name
        assert file_hash(p)==entry['sha256'] and p.stat().st_size==entry['bytes'],name
        authenticated[name]=entry
    source=REPO/'experiments/pipeline_v0.5/baseline_vectorization/run_003/fixture_B_design009_seed001/polygon_candidate.wkb'
    assert file_hash(source)==SOURCE
    mesh,manifest,location=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    assert manifest['semantic_sha256']==HISTORICAL
    questions=[{'number':int(n),'question':q} for n,q in re.findall(r'^(\d+)\. (.+\?)\s*$',REQUEST.read_text(encoding='utf-8').split('# 47. REQUIRED FINAL HANDOFF',1)[1],re.M)]
    assert [q['number'] for q in questions]==list(range(1,115))
    write_json(RUN/'protocol/HANDOFF_QUESTIONS.json',{'source_sha256':file_hash(REQUEST),'questions':questions})
    started=datetime.now(timezone.utc).isoformat()
    audit={'started_utc':started,'user_facing_date':'2026-11-03 America/New_York','repository':str(REPO),
           'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'branch':'master',
           'initial_tree':'CLEAN before task-created files','source_sha256':SOURCE,'mesh_semantic_sha256':HISTORICAL,
           'mesh_archive':str(location),'mesh_bytes_sha256':file_hash(location),'structural_nodes':len(mesh.nodes),'TRI6':len(mesh.triangles),
           'full_parent_source':parent['source'],'full_parent_state':parent['state'],'authenticated_parent_files':authenticated,
           'physical_RAM_bytes':psutil.virtual_memory().total,'available_RAM_bytes':psutil.virtual_memory().available,
           'disk_free_bytes':shutil.disk_usage(artifact_root()).free,'artifact_root':str(artifact_root()),'request_sha256':file_hash(REQUEST)}
    write_json(RUN/'audit/INITIAL.json',audit)
    common={'campaign_wall_seconds':43200,'clock_origin':started,'concurrent_native_jobs':1,'RSS_cap':None,
            'health_policy':asdict(HealthPolicy()),'disk_reserve_bytes':80*1024**3,'source_parents_immutable':True,
            'track_B_solver_seconds_reserved':21600,'track_A_local_seconds_cap':5400,'track_A_full_primary_attempt_cap':1,
            'track_A_conditional_retry':'Only a diagnosed technical defect, registered before execution; no identical stalled retry.',
            'stage_wall_seconds':5400,'no_converged_progress_seconds':1200,'cores_large':8,'cores_small':2,
            'no_3D_manufacturing_batch_or_LLM_optimization':True,'no_push':True}
    write_json(RUN/'protocol/CAMPAIGN.json',common)
    trackA={'source':'Original Design9 seed1 native1024, unchanged','initial_full_maximum_strain':.009270608836206897,
            'first_priority':'One expanded original-mesh local fixture; compare early/final stress, displacement and nanogap/contact context.',
            'local_matrix':['Expanded-context nodal2 baseline','Unified5 if native support confirmed','One localized pair alternative if justified','One stepping variant only if geometry-valid'],
            'no_repeat_old_FKN_sweep':True,'full_entry_gate':'Complete geometry-valid local path, actual opposing forces, unchanged1% reaction/1e-5mm penetration/positive TRI6/crossing gates.',
            'restart':'Topology or integration changes require fresh full fine branch and precontact comparison; supported controls require authenticated native continuation.',
            'track_B_independent':True}
    write_json(RUN/'protocol/TRACK_A.json',trackA)
    trackB={'selection':'One primary central256x256pixel crop of original canonical WKB, pixel box[384,384,640,640], independent specimen.',
            'selection_rationale':'A priori central quarter of each axis; preserves disorder and original pixel-scale struts without choosing by mechanical outcome.',
            'crop_operation':'Exact integer-pixel areal intersection; discard only zero-area line/point intersections, retain all positive-area components and qualify one connected load-bearing solid. Translate to local pixel origin, apply existing x-right/y-up engineering transform.',
            'width_mm':2.56,'height_mm':2.56,'material':{'E_MPa':1000,'nu':.3,'thickness_mm':1,'mode':'plane_stress','NLGEOM':'ON','constitutive':'Uncalibrated homogeneous isotropic linear elasticity'},
            'mesh':{'boundary_size_mm':.01/3,'bulk_size_mm':.04,'policy':'Existing POLICY_B relocate10, quadratic straight original boundary',
                    'angle_min_deg':10,'feature_resolution':'At least3 distinct TRI6 across registered source-only axial chords; no mechanical convergence claim.',
                    'other_gates':'Existing validate_mesh: area, exact boundary/holes/connectivity, outward normals, positive whole-domain quadratic maps, quality>=.1,aspect<=20.'},
            'geometry_failure':'Do not remove positive-area pieces or repair geometry; register any alternative scope before mechanics if the primary fails topology.',
            'contact_selection':'Verify unified5 on an inexpensive licensed internal-contact fixture first. If unsupported/invalid use previously validated nodal2 general contact; original platen model nodal2,penalty100. No redundant pair+GC constraints.',
            'GC_FKN':10,'force_CNVTOL':[.005,2,1e-8],'NEQIT':40,'NROPT':'FULL','LNSRCH':'ON','AUTOTS':'ON',
            'initial_strain_increment':.0005,'maximum_strain_increment':.0025,'minimum_strain_increment':1e-6,
            'targets':[.005,.01,.02,.05,.10,.15,.20,.25,.30,.35,.40],
            'acceptance':{'signed_reaction_balance_max':.01,'platen_force_opposition_max':.01,'internal_force_opposition_max':.01,
                          'penetration_max_mm':5e-5,'penetration_rationale':'0.5% of the one-pixel0.01mm minimum source ligament; bound fixed prospectively for this separate demonstrator,not a TrackA tolerance change.',
                          'deformed_mapping':'Positive all TRI6','overlap':'No unexplained quadratic crossing; native positive-pressure facet link or independently bounded physical contact explanation,never proximity alone.',
                          'native_fields':'Independent POST1 complete U,corner S/EPEL,actual pilot RF,platen/internal contact and source/input/RST hashes.'},
            'output':'All-substep native fields for bounded stages; extract every actual set where practical, preserve last accepted native restart before continuation.',
            'continuation':'No advance from a failed mechanical checkpoint. One evidence-directed contact/control recovery branch may be preregistered; no undocumented geometry search.',
            'execution_priority':'Begin TrackB actual compression promptly after basic geometry/mesh/contact qualification; TrackA cannot block it.',
            'physical_limitations':['Different geometry/load paths from full specimen','Exploratory linear material at large deformation','No out-of-plane buckling','Mechanical mesh convergence unqualified']}
    write_json(RUN/'protocol/TRACK_B.json',trackB)
    print('Authenticated original full foundation; registered independent central-crop demonstrator',flush=True)


if __name__=='__main__':main()
