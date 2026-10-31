"""Check existing licensed SMP entitlement and actual output equivalence."""
import re
import numpy as np
from metamaterial_eval.simulation.progressive_compression import authenticated_restart_copy,continuation_input,run_progressive
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import BASE,RUN,load,export,compact,endpoint_states
from scripts.v065_recovery import committed

PROTOCOL=RUN/'protocol/SMP_RESOURCE_018.json'


def main():
    committed(PROTOCOL);records=[];selected=2
    for cores in [8,4]:
        source=BASE/'rectangle_pause_002';d=BASE/f'rectangle_smp{cores}_001'
        m=authenticated_restart_copy(source,d);point=endpoint_states(source,[.0025])[0]
        text=continuation_input(point['load_step'],point['substep'],[.005],.0025,m['model'],initial=.00125,all_fields=False)
        (d/'input.inp').write_text(text);m.update(input_sha256=file_hash(d/'input.inp'),targets=[.005],target_strain=.005,protocol_sha256=file_hash(PROTOCOL),execution_cores=cores)
        write_json(d/'simulation_manifest.json',m)
        r=run_progressive(d,timeout=180,cores=cores);compact(d,RUN/'performance'/d.name)
        actual=[int(n) for n in re.findall(r'NUMBER OF SMP THREADS USED\s*=\s*(\d+)',(d/'solver.out').read_text(errors='replace'),re.I)]
        result={'requested_cores':cores,'native_observed_thread_counts':sorted(set(actual)),'status':r['status'],'returncode':r['process']['returncode'],'passed':False}
        if r['process']['returncode']==0 and actual and max(actual)==cores:
            states=endpoint_states(d,[.005]);post=export(d,d.name+'_post001',states,chunk_size=128,farfield=True);compact(post,RUN/'performance'/post.name)
            comparisons={}
            for field in ['history','contact','displacements','stress']:
                a=np.loadtxt(BASE/'rectangle_restart_002_post003'/('stage002_'+field+'.csv'),delimiter=',',skiprows=1,ndmin=2)
                b=np.loadtxt(post/('stage001_'+field+'.csv'),delimiter=',',skiprows=1,ndmin=2)
                if a.shape!=b.shape:raise ValueError('SMP comparison inventory mismatch')
                error=float(np.max(np.max(abs(a-b),axis=0)/np.maximum(np.max(abs(a),axis=0),1e-12)))
                comparisons[field]={'max_column_scaled_difference':error,'passed':error<1e-5}
            result['comparisons']=comparisons
            result['passed']=bool(all(c['passed'] for c in comparisons.values()) and float((post/'stage001_gate.txt').read_text().split(',')[0])==0)
        records.append(result)
        if result['passed']:selected=cores;break
    write_json(RUN/'performance/SMP_QUALIFICATION.json',{'status':'PASS_ACTUAL_LICENSED_EQUIVALENT_SMP' if selected>2 else 'KEEP_TWO_SMP_HIGHER_ENTITLEMENT_NOT_VERIFIED','selected_cores':selected,'attempts':records,
        'physics_or_gate_change':False,'concurrent_solver_jobs':1,'no_license_configuration_change_or_bypass':True})
    print('Qualified solver cores',selected,flush=True)


if __name__=='__main__':main()
