"""Aggregate actual v0.6.8 native process and artifact resource receipts."""
from datetime import datetime,timezone
import os
import re

from scripts.v068_common import BASE,RUN,read,write_json,file_hash


def main():
    runs=[]
    for d in sorted(BASE.iterdir()):
        if not d.is_dir() or not (d/'execution_receipt.json').exists():continue
        r=read(d/'execution_receipt.json');p=r['process']
        deck=(d/'input.inp').read_text(encoding='utf-8',errors='replace') if (d/'input.inp').exists() else ''
        solve_count=len(re.findall(r'^\s*SOLVE\s*$',deck,re.M|re.I))
        restart=bool(re.search(r'^\s*ANTYPE\s*,\s*STATIC\s*,\s*REST',deck,re.M|re.I))
        samples=p.get('resource_samples',[])
        page_reads=[float(x.get('page_reads_per_second') or 0) for x in samples]
        available=[int(x['available_RAM_bytes']) for x in samples if x.get('available_RAM_bytes') is not None]
        runs.append({'name':d.name,'status':r['status'],'returncode':p['returncode'],
                     'licensed_version':r['solver_version'],'native_solve_commands':solve_count,
                     'restart_continuation':restart,'read_only_POST1':not solve_count and '/POST1' in deck,
                     'runtime_seconds':p['runtime_seconds'],'peak_tree_rss_bytes':p.get('peak_tree_rss_bytes'),
                     'sampled_min_available_ram_bytes':min(available) if available else None,
                     'max_page_reads_per_second':max(page_reads,default=0),
                     'input_sha256':r['input_sha256'],
                     'receipt_sha256':file_hash(d/'execution_receipt.json')})
    if not runs:raise ValueError('No actual native process receipts')
    disk=0;files=0
    for root,_,names in os.walk(BASE):
        for name in names:
            try:disk+=os.path.getsize(os.path.join(root,name));files+=1
            except FileNotFoundError:pass
    native_solves=[x for x in runs if x['native_solve_commands']]
    restart=[x for x in native_solves if x['restart_continuation']]
    status={'schema':'young-dawgs-v068-observed-resource-performance',
            'captured_utc':datetime.now(timezone.utc).isoformat(),
            'artifact_root':str(BASE),'native_process_count':len(runs),
            'actual_solver_source_process_count':len(native_solves),
            'actual_solver_commands_count':sum(x['native_solve_commands'] for x in native_solves),
            'native_read_only_POST1_process_count':sum(x['read_only_POST1'] for x in runs),
            'genuine_restart_continuation_process_count':len(restart),
            'source_solver_runtime_seconds':sum(x['runtime_seconds'] for x in native_solves),
            'all_native_process_runtime_seconds':sum(x['runtime_seconds'] for x in runs),
            'peak_observed_process_tree_rss_bytes':max(x['peak_tree_rss_bytes'] or 0 for x in runs),
            'minimum_sampled_available_RAM_bytes':min(x['sampled_min_available_ram_bytes'] for x in runs if x['sampled_min_available_ram_bytes'] is not None),
            'maximum_observed_page_reads_per_second':max(x['max_page_reads_per_second'] for x in runs),
            'sustained_severe_paging':'NOT_OBSERVED_BY_RECEIPT' if all(x['max_page_reads_per_second']<10000 for x in runs) else 'REQUIRES_DURATION_AUDIT',
            'raw_artifact_file_count':files,'raw_artifact_bytes':disk,
            'native_processes':runs,
            'interpretation':'Observed process-tree RSS and system paging samples, not a guarantee of peak whole-system use. Disk sums retained v068 raw artifacts, including copied restart/result files.'}
    write_json(RUN/'performance/PERFORMANCE.json',status)
    print('Native source solves',len(native_solves),'restart continuations',len(restart),
          'raw GiB',round(disk/2**30,2),flush=True)


if __name__=='__main__':main()
