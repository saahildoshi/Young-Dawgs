"""Reopen actual converged progressive states and qualify every selected field set."""
import argparse
from pathlib import Path
from metamaterial_eval.simulation.mesh_artifacts import resolve_manifest
from metamaterial_eval.simulation.progressive_results import qualify_state
from metamaterial_eval.simulation.reporting import write_json
from scripts.v066_restart import REPO,RUN,BASE,load,compact,export


def selected_states(source,maximum=8):
    rows=load(source/'nonlinear_telemetry.json')['converged_substeps']
    if not rows:raise ValueError('No actual converged native states')
    if load(source/'simulation_manifest.json')['model'].get('general_contact_detection_keyopt4')==2:
        # Preserve a continuous screened trajectory through first corner contact.
        return [{'time':r['pseudo_time'],'load_step':r['load_step'],'substep':r['substep']} for r in rows]
    indices={0,len(rows)-1}
    for i in range(len(rows)-1):
        if rows[i]['load_step']!=rows[i+1]['load_step']:indices.add(i)
    if len(rows)<=maximum:indices.update(range(len(rows)))
    else:
        import numpy as np
        indices.update(np.linspace(0,len(rows)-1,maximum,dtype=int).tolist())
    return [{'time':rows[i]['pseudo_time'],'load_step':rows[i]['load_step'],'substep':rows[i]['substep']} for i in sorted(indices)]


def process(label,revision='001',chunk_size=250000,farfield=False,reuse_export=None):
    source=BASE/label;states=selected_states(source)
    if reuse_export:
        out=BASE/reuse_export;provenance=load(out/'provenance.json')
        if Path(provenance['source']).resolve()!=source.resolve():raise ValueError('Wrong existing native export source')
        states=provenance['states']
    else:out=export(source,label+'_post'+revision,states,chunk_size=chunk_size,farfield=farfield)
    if not (RUN/'progressive_compression'/out.name).exists():compact(out,RUN/'progressive_compression'/out.name)
    mesh,_,_=resolve_manifest(REPO/'experiments/pipeline_v0.6.3/run_001/mesh_reproduction/attempt_002/artifact_manifest.json',root=Path.home()/'YoungDawgs-Artifacts')
    results=[]
    for i,state in enumerate(states,1):
        raw=BASE/(label+'_qualified'+revision)/f'state{i:03d}'
        setup=BASE/'fine_gc_setup_001' if load(source/'simulation_manifest.json')['model'].get('general_contact_elements') else None
        q=qualify_state(source,out,mesh,i,state,raw,general_contact_setup=setup)
        target=RUN/'mechanical_results'/(label+'_qualified'+revision)/f'state{i:03d}'
        target.mkdir(parents=True,exist_ok=False)
        for name in ['qualification.json','boundary_screen.json']:
            p=raw/name
            if p.exists():
                if name=='boundary_screen.json' and p.stat().st_size>1024**2:
                    from metamaterial_eval.simulation.solver_execution import file_hash
                    compact_boundary=load(p);compact_boundary['examples']=compact_boundary['examples'][:32];compact_boundary.update(compact_copy=True,raw_boundary_screen_sha256=file_hash(p))
                    write_json(target/name,compact_boundary)
                else:(target/name).write_bytes(p.read_bytes())
        results.append(q)
        print(label,state,q['status'],q['failures'],flush=True)
    actual_states=[q.get('state',state) for q,state in zip(results,states)]
    write_json(RUN/'mechanical_results'/(label+'_qualification'+revision+'.json'),{'source':str(source),'states':actual_states,'results':results,
        'last_state_accepted':bool(results[-1]['accepted']),'last_accepted':next((q for q in reversed(results) if q['accepted']),None)})
    return results


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('--revision',default='001');p.add_argument('--chunk-size',type=int,default=250000);p.add_argument('--farfield',action='store_true');p.add_argument('--reuse-export')
    a=p.parse_args();process(a.label,a.revision,a.chunk_size,a.farfield,a.reuse_export)
