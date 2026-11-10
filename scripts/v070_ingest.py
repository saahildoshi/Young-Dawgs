"""Preserve exact UI-captured responses; extract code without researcher repairs."""
import argparse,shutil
from datetime import datetime,timezone
from pathlib import Path
from scripts.v070_protocol import RUN,read,write,sha
from metamaterial_eval.pipeline.scripts import extract_python_script
from scripts.v070_experiment import audit


def ingest(trial,response,url,revision=0,submitted=None):
    d=RUN/'llm_trials'/trial;raw=d/f'response_r{revision}.txt';source=Path(response)
    if source.resolve()!=raw.resolve():
        if raw.exists():raise FileExistsError(raw)
        shutil.copyfile(source,raw)
    generator=d/f'generator_r{revision}.py'
    if generator.exists():raise FileExistsError(generator)
    try:
        code=extract_python_script(raw.read_text(encoding='utf-8-sig'));generator.write_bytes(code.encode('utf-8'));review=audit(code)
        status='RECEIVED_CODE_AUDIT_PASS' if review['passed'] else 'RECEIVED_CODE_AUDIT_FAILED'
    except Exception as e:
        review={'passed':False,'failures':[str(e)]};status='RESPONSE_EXTRACTION_FAILED'
    meta={'trial_id':trial,'revision':revision,'chat_url':url,'normal_ChatGPT_chat':True,'Work_or_Codex_used':False,
        'model_identity_exposed':'ChatGPT;exact backend model/version NOT_AVAILABLE','reasoning_configuration_exposed':'High',
        'submitted_utc':submitted,'captured_utc':datetime.now(timezone.utc).isoformat(),'tokens':None,'cost':None,
        'raw_response_sha256':sha(raw),'code_sha256':sha(generator) if generator.exists() else None,'status':status,'audit':review,
        'capture_method':'Browser generated-code editor select-all/copy;paste into Notepad;save UTF8 text. Original source not edited. UI message-copy preview found truncated and was not used.',
        'normalization':'Raw capture preserved;Python extraction only normalizes CRLF and trailing newline,without changing logic',
        'human_review':'Source reviewed for local RNG,procedural geometry,bounded loops,no reference pixels,I-O or external calls;static screening is not a proof',
        'independence_limit':'Fresh chat per initial attempt;account personalization/memory and backend routing not independently controlled'}
    write(d/f'RECEIPT_r{revision}.json',meta)
    m=read(d/'manifest.json');m.update(status=status,chat_url=url,model=meta['model_identity_exposed'],reasoning_configuration='High');write(d/'manifest.json',m)
    print(trial,revision,status,review,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trial');p.add_argument('response');p.add_argument('url');p.add_argument('--revision',type=int,default=0);p.add_argument('--submitted');a=p.parse_args();ingest(a.trial,a.response,a.url,a.revision,a.submitted)
