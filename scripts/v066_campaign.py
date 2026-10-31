"""Immutable-parent fine-mesh continuation, one qualified stage at a time."""
import argparse
from pathlib import Path
from datetime import datetime,timezone
from metamaterial_eval.simulation.mesh_artifacts import artifact_root,HISTORICAL
from metamaterial_eval.simulation.progressive_compression import authenticated_restart_copy,continuation_input,run_progressive
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v065_recovery import committed
from scripts.v066_restart import REPO,RUN,BASE,PLAN,load,compact

PROTOCOL=RUN/'protocol/FINE_PROGRESSIVE_005.json'


def remaining_solver_budget():
    first=load(BASE/'fine_stage01_001/execution_receipt.json')['process']['started_utc']
    elapsed=(datetime.now(timezone.utc)-datetime.fromisoformat(first.replace('Z','+00:00'))).total_seconds()
    remaining=21600-elapsed
    if remaining<=0:raise RuntimeError('Registered six-hour campaign budget exhausted')
    return min(5400,remaining)


def prepare(label,parent,load_step,substep,previous,targets):
    parent=Path(parent);directory=BASE/label
    assert load(RUN/'restart_validation/RESTART_VALIDATION.json')['status']=='PASS_ACTUAL_LICENSED_NATIVE_RESTART'
    first=BASE/'fine_stage01_001/execution_receipt.json'
    if first.exists():
        started=datetime.fromisoformat(load(first)['process']['started_utc'].replace('Z','+00:00'))
        if (datetime.now(timezone.utc)-started).total_seconds()>21600:raise RuntimeError('Registered six-hour campaign budget exhausted')
    manifest=authenticated_restart_copy(parent,directory,expected_mesh=HISTORICAL)
    text=continuation_input(load_step,substep,targets,previous,manifest['model'],all_fields=True)
    (directory/'input.inp').write_text(text,encoding='utf-8')
    actual_protocol=RUN/'protocol/FULL_GENERAL_CONTACT_014.json' if manifest['model'].get('general_contact_elements') else PROTOCOL
    manifest.update(input_sha256=file_hash(directory/'input.inp'),protocol_sha256=file_hash(actual_protocol),
        target_strain=targets[-1],targets=targets,previous_strain=previous,
        restart_state={'load_step':load_step,'substep':substep,'time':previous},
        contact_limitation='PLATEN_ONLY_EXPLORATORY; no accepted unmodeled wall crossings',
        prepared_utc=datetime.now(timezone.utc).isoformat())
    write_json(directory/'simulation_manifest.json',manifest)
    compact(directory,RUN/'progressive_compression'/('prepared_'+label))
    return directory


def prepare_next(label,parent_label,targets):
    revisions=sorted((RUN/'mechanical_results').glob(parent_label+'_qualification[0-9][0-9][0-9].json'))
    if not revisions:raise ValueError('No independent parent qualification')
    q=load(revisions[-1])
    if not q['last_state_accepted']:raise ValueError('Last parent state did not pass continuation gates')
    state=q['states'][-1]
    if Path(q['source']).resolve()!=(BASE/parent_label).resolve():raise ValueError('Parent qualification identity mismatch')
    return prepare(label,BASE/parent_label,state['load_step'],state['substep'],state['time'],targets)


def freeze():
    protocol={'schema':'young-dawgs-v0.6.6-fine-progressive-execution',
        'plan_sha256':file_hash(PLAN),'primary_target':.3,'stretch_target':.4,
        'mesh':'Preserved fine mesh; rejected candidate not used','mesh_semantic_sha256':HISTORICAL,
        'model':'Unchanged v065 E1000MPa/nu.3/t1mm, linear-elastic plane stress PLANE183, NLGEOM ON',
        'contact':'Unchanged separable frictionless platen CONTA172/TARGE169, penalty FKN100,FTOLN-1e-5,KEYOPT2=1/4=2/10=1',
        'internal_contact':'Small general-contact fixture failed distortion/penetration qualification; no full internal contact. Explicit exploratory fallback, screen actual quadratic boundaries at every qualified state.',
        'targets':load(PLAN)['planned_loading_checkpoints'],'first_stage':[.0001,.001],
        'stage_control':'Authenticate copied native multiframe parent. Independent native readback/field/mapping/overlap/equilibrium gates before starting next stage.',
        'native_restart':'ANTYPE,STATIC,REST,LS,SS,CONTINUE; preserve immutable parent RDB/LDHI/Rnnn/RST',
        'outputs':'NSOL/RSOL/STRS/EPEL/CONT/MISC ALL converged substeps, three rolling total restart frames; no Newton-iterate field acceptance',
        'solver':load(PLAN)['nonlinear_controls'],'resources':load(PLAN)['resources'],'cores':2,
        'stop':'Actual solver fatal/error/distortion; native nonconvergence/minimum increment; resource health; stage/campaign/no-progress limits; failed continuation gates. Preserve last separately qualified parent.',
        'acceptance':load(PLAN)['continuation_gate'],'material_limit':'Large local elastic strains are provisional and cannot predict actual polymer behavior; no experimental/calibrated claim',
        'no_push':True,'no_3D_batch_or_optimization':True}
    write_json(PROTOCOL,protocol)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare-first','prepare-next','run']);p.add_argument('--label',default='fine_stage01_001')
    p.add_argument('--parent');p.add_argument('--targets',type=float,nargs='+');a=p.parse_args()
    if a.action=='prepare-first':
        freeze();d=prepare(a.label,artifact_root()/'solver/v065/full_recovery_001',1,1,.00005,[.0001,.001]);print(d,flush=True)
    elif a.action=='prepare-next':
        if not a.parent or not a.targets:p.error('prepare-next requires --parent and --targets')
        print(prepare_next(a.label,a.parent,a.targets),flush=True)
    else:
        committed(PROTOCOL);committed(RUN/'progressive_compression'/('prepared_'+a.label)/'input.inp')
        d=BASE/a.label;m=load(d/'simulation_manifest.json')
        assert file_hash(d/'input.inp')==m['input_sha256'] and file_hash(d/'input.inp')==file_hash(RUN/'progressive_compression'/('prepared_'+a.label)/'input.inp')
        r=run_progressive(d,timeout=remaining_solver_budget(),no_progress_seconds=1800)
        compact(d,RUN/'progressive_compression'/a.label)
        print(a.label,r['status'],r['process']['returncode'],r['converged_steps'][-1:],flush=True)
