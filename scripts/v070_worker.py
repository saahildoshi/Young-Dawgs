"""Offline evaluator worker; only this trusted harness writes output artifacts."""
import hashlib,importlib.util,sys,time,traceback
from pathlib import Path
import numpy as np
from PIL import Image
from scripts.v070_protocol import write,sha
from metamaterial_eval.composites import describe,validity


def work(source,family,destination,seeds):
    d=Path(destination);write(d/'progress.json',{'phase':'import'})
    spec=importlib.util.spec_from_file_location('trial_generator',source);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for seed in seeds:
        write(d/'progress.json',{'phase':'seed','seed':seed});started=time.perf_counter()
        row={'seed':seed,'status':'ERROR','source_sha256':sha(source)}
        try:
            a=module.generate_microstructure(seed,{});b=module.generate_microstructure(seed,{})
            if not np.array_equal(a,b):raise ValueError('Nondeterministic same-seed output')
            if not isinstance(a,np.ndarray):raise ValueError('Output not ndarray')
            np.save(d/f'seed_{seed:03d}.npy',a,allow_pickle=False);row['array_sha256']=hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()
            row['array_file_sha256']=sha(d/f'seed_{seed:03d}.npy');v=validity(a,family)
            if a.shape==(256,256) and a.dtype==np.uint8 and np.isin(a,[0,1]).all():
                descriptors=describe(a,family);Image.fromarray(a*255).save(d/f'seed_{seed:03d}.png')
                row.update(status='OK',descriptors=descriptors,validity=v,deterministic=True)
            else:row.update(status='INVALID_OUTPUT_CONTRACT',validity=v,deterministic=True)
        except Exception as e:row.update(error=str(e),traceback=traceback.format_exc())
        row['generation_repeat_and_evaluation_seconds']=time.perf_counter()-started;write(d/f'seed_{seed:03d}.json',row)
        write(d/'progress.json',{'phase':'completed_seed','seed':seed})


if __name__=='__main__':work(sys.argv[1],sys.argv[2],sys.argv[3],[int(s) for s in sys.argv[4].split(',')])
