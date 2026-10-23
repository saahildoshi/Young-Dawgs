"""Same-fixture original/revised engine allocation and timing observations."""
import gc
import json
import resource
import time
import tracemalloc
from metamaterial_eval.geometry.protected_v2.study import OUT,settings,fixture_from_source
from metamaterial_eval.geometry.protected.guards import prepare_risks,build_guards
from metamaterial_eval.geometry.protected.engine import simplify_protected as old
from metamaterial_eval.geometry.protected_v2.engine import simplify_protected as revised
from metamaterial_eval.geometry.sensitivity.records import write_json


def main():
    p,cfg=settings();fixture=fixture_from_source('design_004_seed_001');records=[]
    for name,fn in [('B2_original',old),('C1_revised',revised)]:
        risk=prepare_risks(fixture,cfg);guard=build_guards(risk,.5,cfg);gc.collect();tracemalloc.start();t=time.perf_counter();engine=fn(fixture['baseline'],.5,risk,guard,cfg);elapsed=time.perf_counter()-t;peak=tracemalloc.get_traced_memory()[1];tracemalloc.stop()
        records.append({'version':name,'instrumented_engine_seconds':elapsed,'engine_traced_peak_bytes':peak,'process_lifetime_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'engine_timing':engine['timing']});del risk,guard,engine;gc.collect()
    write_json(OUT/'performance/TARGETED_PROFILE.json',{'fixture':'design_004_seed_001','epsilon':.5,'records':records,
        'scope':'Source and guard construction excluded from engine allocation tracing; revised frame cache is first-use. RSS is process lifetime highwater including untraced GEOS; macOS bytes. Single observations, not statistical benchmarks.'})
    print('Targeted profile complete',records)


if __name__=='__main__':main()
