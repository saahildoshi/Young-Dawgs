"""Bounded, provenance-checked caching of unchanged frozen-evaluator outputs."""
from collections import OrderedDict
import hashlib
import json
from pathlib import Path
import numpy as np

from ...pipeline.config import default_evaluator_path
from ...pipeline.evaluator import load_evaluator
from ...pipeline.resolution_worker import evaluate_native
from ..topology import FROZEN_SHA256
from ..inputs import sha256_file


class DescriptorCache:
    def __init__(self,output_dir,max_entries=16,evaluate=evaluate_native):
        self.output=Path(output_dir);self.output.mkdir(parents=True,exist_ok=True)
        self.maximum=max_entries;self.evaluate=evaluate;self.entries=OrderedDict();self.calls=0
        self.evaluator_hash=sha256_file(default_evaluator_path())
        if self.evaluator_hash!=FROZEN_SHA256:raise ValueError('Frozen evaluator v1.1 hash mismatch.')

    def get(self,mask):
        salt=f'{mask.shape}:{mask.dtype}:{self.evaluator_hash}:evaluate_native:max_r=ceil(N/4)'.encode()
        key=hashlib.sha256(salt+mask.tobytes()).hexdigest()
        reused=key in self.entries;reuse_kind='verified_memory_equality' if reused else None
        if reused:
            saved,data=self.entries.pop(key)
            if not np.array_equal(saved,mask):raise ValueError('Descriptor cache hash/equality mismatch.')
            self.entries[key]=(saved,data)
        else:
            artifact=self.output/(key+'.json')
            if artifact.exists():
                stored=json.loads(artifact.read_text())
                if stored['raster_sha256']!=hashlib.sha256(mask.tobytes()).hexdigest() or stored['evaluator_sha256']!=self.evaluator_hash:
                    raise ValueError('Persisted descriptor cache provenance mismatch.')
                data=stored['result'];reused=True;reuse_kind='verified_disk_raster_and_configuration_hash'
                if 'shape' in data.get('raw',{}) and data['raw']['shape']!=list(mask.shape):raise ValueError('Persisted descriptor grid mismatch.')
            else:
                data=self.evaluate(mask);self.calls+=1
            self.entries[key]=(mask.copy(),data)
            while len(self.entries)>self.maximum:self.entries.popitem(last=False)
            if not artifact.exists():
                artifact.write_text(json.dumps({'raster_sha256':hashlib.sha256(mask.tobytes()).hexdigest(),
                    'evaluator_sha256':self.evaluator_hash,'interface':'pipeline.resolution_worker.evaluate_native',
                    'result':data},indent=2,sort_keys=True,allow_nan=False)+'\n')
        return data,{'key':key,'artifact_name':key+'.json','reused':reused,'reuse_kind':reuse_kind,
                     'reuse_verified_by':'Raster identity, grid, dtype, evaluator and interface-configuration hashes; memory hits also verify np.array_equal.' if reused else None,
                     'evaluator_sha256':self.evaluator_hash,'frozen_evaluation_calls_so_far':self.calls}


def descriptor_comparison(reference,candidate,screen):
    a,b=reference['raw'],candidate['raw']
    keys=('phi_s','component_count','f_largest','Px','Py','mean_strut_thickness','p10_strut_thickness','median_pore_diameter')
    scalars={};any_change=False;notable=[]
    for key in keys:
        x,y=a[key],b[key];equal=x==y
        delta=float(y-x) if x is not None and y is not None else None
        relative=delta/abs(x) if delta is not None and x!=0 else None
        scalars[key]={'reference':x,'candidate':y,'difference':delta,'relative_difference':relative,'exact_equal':bool(equal)}
        any_change|=not equal
        if key=='phi_s' and delta is not None and abs(delta)>screen['density_absolute']:notable.append(key)
        if key in ('mean_strut_thickness','p10_strut_thickness','median_pore_diameter'):
            if relative is not None and abs(relative)>screen['relative_dimensions']:notable.append(key)
            elif (x is None)!=(y is None):notable.append(key+':undefined_change')
    evaluator=load_evaluator(str(default_evaluator_path().resolve()));curves={}
    for key in ('s2','lineal_path','l_x','l_y','l_45','l_135'):
        x=np.asarray(a['curves'][key]);y=np.asarray(b['curves'][key]);equal=np.array_equal(x,y)
        error=float(evaluator.normalized_rmse(y,x))
        curves[key]={'maximum_absolute_difference':float(np.max(abs(y-x))),
                     'nrmse_reference_rms':error,'exact_equal':bool(equal)}
        any_change|=not equal
        if key in ('s2','lineal_path') and error>screen['curve_nrmse']:notable.append(key)
    return {'scalars':scalars,'curves':curves,'any_descriptor_change':bool(any_change),
            'notable_drift_screen':bool(notable),'notable_screen_triggers':notable,
            'screen_interpretation':'Prospective exploratory warning, not scientific acceptance or a production tolerance.',
            'p10_caveat':'Unchanged frozen whole-mask P10 definition. v0.4.3 amended qualification remains scoped; historical v0.4.2 calibration remains FAILED. Raster descriptors do not measure subpixel vector changes.'}
