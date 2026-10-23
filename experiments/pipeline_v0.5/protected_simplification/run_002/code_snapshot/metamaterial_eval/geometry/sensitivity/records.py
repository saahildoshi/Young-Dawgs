"""Append-only candidate artifacts and discrete, non-monotonic threshold scans."""
import hashlib
import json
from pathlib import Path
import numpy as np
import shapely


def write_json(path,data):
    def clean(value):
        if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [clean(v) for v in value]
        if isinstance(value,np.generic):return clean(value.item())
        if isinstance(value,float) and not np.isfinite(value):return None
        return value
    Path(path).write_text(json.dumps(clean(data),indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def save_candidate(folder,candidate,record,reconstructed=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    payload=shapely.to_wkb(candidate,byte_order=1)
    (folder/'diagnostic_candidate.wkb').write_bytes(payload)
    record={**record,'candidate_sha256':hashlib.sha256(payload).hexdigest(),
            'candidate_serialization_bytes':len(payload),'candidate_file':'diagnostic_candidate.wkb'}
    write_json(folder/'metrics.json',record)
    if reconstructed is not None:np.save(folder/'reconstructed.npy',reconstructed,allow_pickle=False)
    if record.get('status')!='DIAGNOSTIC_NO_OBSERVED_FLAGS':
        write_json(folder/'DIAGNOSTIC_FLAGS.json',{'status':record.get('status'),'flags':record.get('diagnostic_flags',[]),
                                                'candidate_retained':True,'automatic_repair_applied':False})
    return record


def threshold_scan(rows):
    rows=sorted(rows,key=lambda r:r['epsilon'])
    names=sorted(set(key for row in rows for key in row['events']))
    result={}
    for name in names:
        sequence=[{'epsilon':r['epsilon'],'event':r['events'].get(name)} for r in rows]
        failed=[i for i,s in enumerate(sequence) if s['event'] is True]
        first=failed[0] if failed else None
        recovery=[]
        last_known=None
        for s in sequence:
            if s['event'] is None:continue
            if last_known is True and s['event'] is False:recovery.append(s['epsilon'])
            last_known=s['event']
        result[name]={'first_tested_failure':sequence[first]['epsilon'] if first is not None else None,
                      'preceding_tested_tolerance':sequence[first-1]['epsilon'] if first is not None and first>0 else None,
                      'observed_failure_bracket':[sequence[first-1]['epsilon'],sequence[first]['epsilon']] if first is not None and first>0 else None,
                      'sequence':sequence,'non_monotonic_observed':bool(recovery),'recovery_tolerances':recovery,
                      'interpretation':'Discrete first tested event, not an exact mathematical threshold; null events mean unavailable diagnostics.'}
    return result
