"""Bounded standalone generator runner and exact regular-chat prompt packets."""
import argparse,ast,hashlib,subprocess,sys,time
from pathlib import Path
import numpy as np
from scripts.v070_protocol import REPO,RUN,write,read,sha
from metamaterial_eval.composites import normalized_errors


def audit(source):
    tree=ast.parse(source);fail=[];allowed=set(read(RUN/'protocol/PROTOCOL.json')['generator_dependencies'])
    forbidden={'open','eval','exec','compile','__import__','getattr','setattr','globals','locals','input','breakpoint'}
    forbidden_attrs={'load','save','savez','loadtxt','savetxt','fromfile','tofile','imread','imsave','open','read','write','seed','system','popen','urlopen','request'}
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            names=[x.name for x in node.names] if isinstance(node,ast.Import) else [node.module or '']
            if any(x.split('.')[0] not in allowed for x in names):fail.append('Unapproved import')
        if isinstance(node,ast.Call):
            if isinstance(node.func,ast.Name) and node.func.id in forbidden:fail.append('Forbidden dynamic/I-O call:'+node.func.id)
            if isinstance(node.func,ast.Attribute) and node.func.attr in forbidden_attrs:fail.append('Forbidden I-O/global-random call:'+node.func.attr)
        if isinstance(node,(ast.Global,ast.Nonlocal)):fail.append('Generator global state')
    for node in tree.body:
        if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.AsyncFunctionDef)):continue
        if isinstance(node,ast.Expr) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str):continue
        if isinstance(node,(ast.Assign,ast.AnnAssign)) and not any(isinstance(n,ast.Call) for n in ast.walk(node)):continue
        fail.append('Executable module-scope statement')
    if not any(isinstance(n,ast.FunctionDef) and n.name=='generate_microstructure' for n in tree.body):fail.append('Missing interface')
    return {'passed':not fail,'failures':sorted(set(fail)),'limitation':'Conservative static screening plus human code review,not a formal security/leakage proof'}


def prompts():
    p=read(RUN/'protocol/PROTOCOL.json');base='''Study the attached synthetic reference image and infer a stochastic procedural model of this microstructure family. Generate independent realizations,not matching coordinates or exact pixels. White(label1)=reinforcement;black(label0)=continuous solid matrix,not void. Return one complete Python module in one python code block,preferably at most70 lines,with only imports,functions and literal constants at module scope.
Required interface: generate_microstructure(seed,parameters) returns a NumPy ndarray,shape(256,256),dtype uint8,labels0/1. parameters will be an empty dict. Use a local numpy.random.default_rng(seed). Same seed must reproduce exactly;different seeds must change actual geometry,not just translate/rotate one realization. Keep both phases nonempty and a continuous matrix spanning x/y;multiple disconnected reinforcements are appropriate. Use finite nonperiodic boundaries.
Allowed:NumPy,SciPy,scikit-image,Pillow and basic math/random/collections/itertools. No file I/O,network,subprocess,APIs,reference loading,embedded target arrays,coordinate tracing,global RNG seeding,plotting or generation on import. No tests/demo/print at import. Do not use tools to retrieve other reference information. Infer from this image and only the supplied information. No material properties or mechanics. Code only;no need to explain. You have one initial attempt;make placement loops finite and execution below10 seconds per realization.'''
    records=[]
    for family in p['families']:
        target=read(RUN/'references'/family/'descriptors.json')
        numeric={name:target[name] for name in p['visible_metrics'][family]}
        defs='Particle size is equal-area diameter;aspect ratio is the ratio of covariance-based major/minor ellipse axes. Size and spacing descriptions use components not touching the image edge.' if family=='particle' else 'Angles are axial modulo180°,counterclockwise from image+x with y up. Alignment=|area-weighted mean exp(2i angle)|. For isolated unbranched components,span is projected extent along the principal axis including pixel support;width=component area/span. These are image component proxies,not recovered true curved-fiber lengths. Ambiguous branched components are excluded from these proxies.'
        for condition in ['A','B','C']:
            for trial in [1,2]:
                trialid=f'{family}_{condition}_{trial:02d}';d=RUN/'llm_trials'/trialid;d.mkdir(parents=True,exist_ok=False)
                text=base+f'\nMicrostructure family:{family}-reinforced composite.'
                if condition!='A':text+='\nPreselected target descriptors (pixel units where lengths appear):\n'+str(numeric)+'\n'+defs
                (d/'prompt.txt').write_text(text+'\n',encoding='utf-8',newline='\n')
                manifest={'trial_id':trialid,'family':family,'condition':condition,'independent_trial':trial,'reference_id':family+'_synthetic_001','reference_image_sha256':sha(RUN/'references'/family/'reference.png'),
                    'prompt_sha256':sha(d/'prompt.txt'),'prompt_version':'v070_frozen_001','status':'NOT_RUN','model':None,'backend_version':None,'reasoning_configuration':None,
                    'token_usage':None,'cost':None,'source_mode':'REGULAR_CHATGPT_CHAT','development_seeds':p['development_seeds'],'heldout_seeds':p['heldout_seeds'],'revision_budget':1 if condition=='C' else 0}
                write(d/'manifest.json',manifest);records.append(manifest)
    write(RUN/'protocol/FROZEN_INPUTS.json',{'protocol_sha256':sha(RUN/'protocol/PROTOCOL.json'),'descriptor_code_sha256':sha(REPO/'metamaterial_eval/composites/descriptors.py'),
        'reference_manifest_sha256':{f:sha(RUN/'references'/f/'manifest.json') for f in p['families']},'initial_trials':records,'same_A_prompt_within_family':True,'same_B_C_initial_prompt_within_family':True})
    print('Frozen12 initial prompt packets;4 maximum feedback calls',flush=True)


def run(trialid,partition,revision=0):
    d=RUN/'llm_trials'/trialid;manifest=read(d/'manifest.json');p=read(RUN/'protocol/PROTOCOL.json');source=d/f'generator_r{revision}.py'
    result=d/f'evaluation_r{revision}_{partition}'
    if result.exists():raise FileExistsError(result)
    result.mkdir();review=audit(source.read_text(encoding='utf-8'));write(result/'CODE_AUDIT.json',review)
    if not review['passed']:
        write(result/'EXECUTION.json',{'status':'CODE_AUDIT_FAILED','records':[],'failures':review['failures']});return
    seeds=p['development_seeds'] if partition=='dev' else p['heldout_seeds'];started=time.perf_counter()
    cmd=[sys.executable,'-m','scripts.v070_worker',str(source),manifest['family'],str(result),','.join(map(str,seeds))]
    with (result/'worker.log').open('w') as log:
        process=subprocess.Popen(cmd,cwd=REPO,stdout=log,stderr=subprocess.STDOUT)
        progress=result/'progress.json';last=time.monotonic();previous=None;stop=None
        while process.poll() is None:
            if progress.exists():
                stamp=progress.stat().st_mtime_ns
                if stamp!=previous:last=time.monotonic();previous=stamp
            if time.monotonic()-last>p['generation_timeout_seconds_per_seed']+2:stop='NO_SEED_PROGRESS_TIMEOUT';process.kill();break
            if time.perf_counter()-started>p['module_timeout_seconds']:stop='MODULE_TIMEOUT';process.kill();break
            time.sleep(.1)
        process.wait()
    records=[read(path) for path in sorted(result.glob('seed_*.json'))]
    target=read(RUN/'references'/manifest['family']/'descriptors.json')
    for row in records:
        if row['status']=='OK':
            row['visible_error']=normalized_errors(row['descriptors'],target,p['visible_metrics'][manifest['family']],p['normalization_scales'])
            row['holdout_error']=normalized_errors(row['descriptors'],target,p['holdout_metrics'][manifest['family']],p['normalization_scales'])
    report={'status':stop or ('COMPLETED' if process.returncode==0 and len(records)==len(seeds) else 'WORKER_FAILED'),'returncode':process.returncode,'wall_seconds':time.perf_counter()-started,
        'trial_id':trialid,'partition':partition,'revision':revision,'source_sha256':sha(source),'prompt_sha256':manifest['prompt_sha256'],'seeds':seeds,'records':records,
        'execution_failures':len(seeds)-sum(r['status']=='OK' for r in records),'valid_outputs':sum(r.get('validity',{}).get('passed',False) for r in records)}
    write(result/'EXECUTION.json',report);print(trialid,revision,partition,report['status'],report['valid_outputs'],'/',len(seeds),flush=True)


def feedback(trialid):
    d=RUN/'llm_trials'/trialid;m=read(d/'manifest.json');assert m['condition']=='C';r=read(d/'evaluation_r0_dev/EXECUTION.json');p=read(RUN/'protocol/PROTOCOL.json')
    metrics=p['visible_metrics'][m['family']];target=read(RUN/'references'/m['family']/'descriptors.json');observed={}
    for name in metrics:
        values=[row['descriptors'].get(name) for row in r['records'] if row['status']=='OK'];values=[x for x in values if x is not None]
        if name=='axial_mean_deg' and values:
            z=np.mean(np.exp(2j*np.deg2rad(values)));observed[name]={'axial_mean':float(np.rad2deg(np.angle(z))/2%180),'n':len(values)}
        else:observed[name]={'mean':float(np.mean(values)) if values else None,'std':float(np.std(values)) if values else None,'n':len(values)}
    packet={'development_seed_count':10,'target':{name:target[name] for name in metrics},'measured':observed,'valid_outputs':r['valid_outputs'],'execution_failures':r['execution_failures'],
        'validity_failures':[row.get('validity',{}).get('failures',[]) for row in r['records'] if not row.get('validity',{}).get('passed',False)]}
    text='One registered quantitative feedback revision. Keep the same interface,phase meanings,dependencies,seed independence and procedural restrictions. Revise using only the following measured development summary;do not request additional data. Return the full revised module in one python code block,preferably <=70 lines. No hidden/held-out descriptors or final seeds are provided.\n'+str(packet)+'\n'
    (d/'feedback_prompt.txt').write_text(text,encoding='utf-8',newline='\n');write(d/'FEEDBACK_PACKET.json',packet);print(trialid,text,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prompts','run','feedback']);p.add_argument('--trial');p.add_argument('--partition',choices=['dev','held'],default='dev');p.add_argument('--revision',type=int,default=0);a=p.parse_args()
    if a.action=='prompts':prompts()
    elif a.action=='feedback':feedback(a.trial)
    else:run(a.trial,a.partition,a.revision)
