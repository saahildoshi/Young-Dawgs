"""Prospective full-node POST1 vector study on an already accepted native state."""
import numpy as np
from metamaterial_eval.simulation.native_qualification import stream_csv
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import RUN,BASE,load,export,compact


def main():
    source=BASE/'fine_stage01_001';old=BASE/'fine_stage01_001_post001'
    state={'time':.001,'load_step':3,'substep':2}
    out=export(source,'fine_stage01_full_vectors_001',[state],chunk_size=2766505)
    compact(out,RUN/'performance'/out.name)
    comparisons={}
    columns={'history':['pseudo_time','load_step','substep','top_uy_mm','upper_rf_y_N','lower_rf_y_N'],
        'contact':['pair','element','status','pressure_i_MPa','pressure_j_MPa','gap_i_mm','gap_j_mm','contact_force_y_N'],
        'displacements':['node','ux_mm','uy_mm'],'stress':['node','syy_MPa','seqv_MPa','elastic_eyy','elastic_exx']}
    for field,schema in columns.items():
        left=old/('stage003_'+field+'.csv');right=out/('stage001_'+field+'.csv')
        equal=file_hash(left)==file_hash(right)
        comparisons[field]={'byte_identical':equal,'original_sha256':file_hash(left),'candidate_sha256':file_hash(right)}
        assert equal,'Vector-bound change altered actual native '+field
    assert float((out/'stage001_gate.txt').read_text().split(',')[0])==0
    r=load(out/'execution_receipt.json')['process'];prior=load(old/'execution_receipt.json')['process']
    passed=r['returncode']==0 and r['runtime_seconds']<=.8*(prior['runtime_seconds']/3)
    result={'status':'PASS_NATIVE_FIELDS_IDENTICAL__SELECT_FULL_NODE_VECTORS' if passed else 'FIELDS_IDENTICAL_BUT_SPEED_NOT_QUALIFIED_KEEP_CHUNKS',
        'selected_chunk_size':2766505 if passed else 250000,'comparisons':comparisons,'native_gate':0,
        'candidate_runtime_seconds':r['runtime_seconds'],'candidate_peak_tree_RSS_bytes':r['peak_tree_rss_bytes'],
        'prior_three_set_runtime_seconds':prior['runtime_seconds'],'baseline_cost_scope':'Comparison uses prior three-set mean per state; not an isolated matched single-state timing measurement',
        'minimum_sampled_available_RAM_bytes':min(s['available_RAM_bytes'] for s in r['resource_samples']),
        'same_source_RST_sha256':file_hash(source/'compression.rst'),'physics_or_output_schedule_change':False,
        'memory_bound':'Three U arrays then six stress arrays, never more than actual2766505nodes per array; vectors freed between categories; native HealthPolicy retained.'}
    write_json(RUN/'performance/VECTOR_BENCHMARK.json',result);print(result['status'],r['runtime_seconds'],flush=True)


if __name__=='__main__':main()
