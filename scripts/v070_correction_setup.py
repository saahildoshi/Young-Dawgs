"""Additive correction audit; no new model invocation or target freeze is allowed."""
from datetime import datetime,timezone
import subprocess
from scripts.v070_protocol import REPO,RUN,read,write,sha

CORRECTION=RUN.parent/'reference_correction_001'
DOC=REPO/'docs/pipeline_v0.7.0/reference_correction_001'


def register():
    CORRECTION.mkdir(exist_ok=False);DOC.mkdir(parents=True,exist_ok=False)
    request=REPO.parent.parent/'.codex/attachments/61dca7f5-8d02-44c3-bad2-de4250565e67/Pasted text.txt'
    # Explicit user attachment is outside the active checkout.
    request=__import__('pathlib').Path(r'C:\Users\sd22446\.codex\attachments\61dca7f5-8d02-44c3-bad2-de4250565e67\Pasted text.txt')
    write(CORRECTION/'protocol/CORRECTION.json',{'registered_utc':datetime.now(timezone.utc).isoformat(),'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        'starting_status':subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip(),'request_sha256':sha(request),
        'scope':'Audit prior synthetic pilot;inspect actual downloaded microscopy;prepare unapproved visual candidates;STOP for user selection',
        'references_approved':False,'main_experiment_authorized_to_start':False,'new_LLM_calls':0,'new_ANSYS_jobs':0,'new_synthetic_primary_targets_allowed':False,
        'previous_evidence':'Preserve run_001 without rewriting committed scripts,prompts,references or results. Existing uncommitted A02 submission metadata is preserved as a preceding-turn record.',
        'candidate_sources':{'particle':'https://zenodo.org/records/17315241','fiber':'https://doi.org/10.4121/bf11171a-1f57-4a8a-9768-757850d13665'},
        'primary_candidate_rules':['Use supplied scientific microscopy and supplied corresponding annotations','Keep all source phase labels,including void and uncertain classes',
            'No nonuniform resizing','Prefer original unaugmented fiber images;geometry-preserving Ni-WC augmentation only when original absent',
            'No physical pixel calibration inferred from magnification or nominal fiber diameter','Crop recommendation is an explicit proposal,not frozen target',
            'Document annotation errors,representation and train/test/augmentation dependence'],
        'stop':'Present paired micrograph/segmentation/phase legend/ROI and obtain explicit user approval before preparing executable approved-reference trial prompts'})
    inventory=[]
    for d in sorted((RUN/'llm_trials').iterdir()):
        if not(d/'manifest.json').exists():continue
        m=read(d/'manifest.json');baseline=m['condition']=='BASELINE';receipts=list(d.glob('RECEIPT_r*.json'));evaluations=[]
        for p in sorted(d.glob('evaluation*/EXECUTION.json')):
            e=read(p);evaluations.append({'partition':p.parent.name,'status':e['status'],'stochastic_outputs':len(e['records']),'valid_outputs':e.get('valid_outputs'),'evidence_sha256':sha(p)})
        inventory.append({'trial_id':d.name,'classification':'NON_LLM_PROCEDURAL_BASELINE' if baseline else ('GENUINE_RETURNED_LLM_GENERATOR' if receipts else 'GENUINE_SUBMITTED_CHAT_RESPONSE_NOT_INGESTED' if m.get('chat_url') else 'PROMPT_ONLY_NOT_EXECUTED'),
            'original_condition':m['condition'],'reference_kind':'SYNTHETIC_TEST_REFERENCE_NOT_CORRECTED_PRIMARY_TARGET','chat_url':m.get('chat_url'),
            'source_scripts':[{ 'name':p.name,'sha256':sha(p)} for p in d.glob('generator_r*.py')],
            'response_receipts':[{'name':p.name,'sha256':sha(p)} for p in receipts],'manifest_sha256':sha(d/'manifest.json'),'evaluations':evaluations})
    write(CORRECTION/'audit/PRIOR_EXPERIMENT_INVENTORY.json',{'records':inventory,'summary':{'non_LLM_baseline_scripts':2,'non_LLM_baseline_outputs':40,
        'verified_returned_LLM_scripts':1,'verified_returned_LLM_script_outputs':20,'additional_submitted_chats_without_ingested_response':1,
        'initial_prompt_packets_never_submitted':10,'feedback_calls':0,'real_micrograph_LLM_trials':0},
        'limitations':'The first returned generator is an actual ordinary ChatGPT invocation but only a synthetic-reference pilot. The submitted second chat is not a second evaluated script. No framework test or baseline is counted as an independent experimental LLM attempt.'})
    write(CORRECTION/'audit/PRIOR_EVIDENCE_HASHES.json',{str(p.relative_to(REPO)):sha(p) for p in RUN.rglob('*') if p.is_file()})
    print('Registered approval-gated correction and honest prior-trial inventory',flush=True)


if __name__=='__main__':register()
