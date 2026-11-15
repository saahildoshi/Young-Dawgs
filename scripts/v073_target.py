"""Apply the prospectively registered target rule; never inspect LLM revisions."""
import numpy as np
from scripts.v070_protocol import read,write,sha
from scripts.v073_experiment import RUN,DOC,now

def choose(h1,h2):
    accepted=[r for r in h1 if r['status']=='ACCEPTED_NATIVE_RESULT']
    cohorts=sorted({r['trial_id'] for r in h1});base=[r['apparent_modulus_MPa'] for r in accepted if r['trial_id']=='BASE']
    assert len(base)>=2
    bmean=float(np.mean(base));bsd=float(np.std(base,ddof=1))
    pairs=[]
    for r in h2:
        if r['status']!='ACCEPTED_NATIVE_RESULT':continue
        first=next(v for v in accepted if v['trial_id']==r['trial_id'] and v['seed']==r['seed'])
        pairs.append({'trial_id':r['trial_id'],'seed':r['seed'],'H1':first['apparent_modulus_MPa'],'H2':r['apparent_modulus_MPa'],
            'absolute_mesh_change':abs(r['apparent_modulus_MPa']-first['apparent_modulus_MPa']),
            'relative_mesh_change':abs(r['apparent_modulus_MPa']-first['apparent_modulus_MPa'])/first['apparent_modulus_MPa']})
    assert any(r['trial_id']=='BASE' for r in pairs)
    bp=next(r for r in pairs if r['trial_id']=='BASE');eligible=[];reasons=[]
    maxchange=max(r['absolute_mesh_change'] for r in pairs);maxrelative=max(r['relative_mesh_change'] for r in pairs)
    gate=max(2*bsd,2*maxchange,.03*bmean)
    for trial in cohorts:
        if trial=='BASE':continue
        rows=[r for r in accepted if r['trial_id']==trial]
        rp=next((r for r in pairs if r['trial_id']==trial),None)
        mean=float(np.mean([r['apparent_modulus_MPa'] for r in rows])) if rows else None
        effect=mean-bmean if mean is not None else None
        good=len(rows)==3 and rp is not None
        if good:
            e1=rp['H1']-bp['H1'];e2=rp['H2']-bp['H2'];sensitivity=rp['absolute_mesh_change']+bp['absolute_mesh_change']
            good=bool(effect*e1>0 and e1*e2>0 and abs(e2)>sensitivity)
        reasons.append({'trial_id':trial,'n':len(rows),'mean_MPa':mean,'mean_difference_MPa':effect,'mesh_effect_eligible':good})
        if good:eligible.append((trial,effect,mean))
    upward=sorted([r for r in eligible if r[1]>0],key=lambda r:(-r[1],r[0]))
    downward=sorted([r for r in eligible if r[1]<0],key=lambda r:(r[1],r[0]))
    selected=(upward or downward)
    chosen=selected[0] if selected else None
    target=bmean+.60*chosen[1] if chosen else None
    tolerance=max(.02,2*maxrelative)
    qualified=bool(chosen and abs(target-bmean)>gate and tolerance<abs(target-bmean)/target/2)
    return {'baseline_n':len(base),'baseline_mean_MPa':bmean,'baseline_sample_SD_MPa':bsd,'feasible_variant_results':reasons,
        'development_mesh_pairs':pairs,'largest_absolute_mesh_change_MPa':maxchange,'largest_relative_mesh_change':maxrelative,
        'difficulty_threshold_MPa':gate,'selected_variant':chosen[0] if chosen else None,'proposed_target_MPa':target,
        'target_MPa':target if qualified else None,'J_target':target/1000 if qualified else None,
        'relative_target_separation':abs(target-bmean)/target if target else None,'target_hit_relative_tolerance':tolerance,
        'qualified_target':qualified,'status':'ATTAINABLE_TARGET_FROZEN' if qualified else 'NO_TARGET_PASSES_REGISTERED_DIFFICULTY_GATE'}

def freeze():
    path=RUN/'target_selection/TARGET_FROZEN.json';assert not path.exists()
    assert not list((RUN/'llm_trials').glob('*/response.txt'))
    one=RUN/'development_mechanics_h1/CAMPAIGN.json';two=RUN/'development_mechanics_h2/CAMPAIGN.json'
    decision=choose(read(one)['cases'],read(two)['cases'])
    decision.update(frozen_utc=now(),rule_sha256=sha(RUN/'protocol/PROTOCOL.json'),
        development_H1_sha256=sha(one),development_H2_sha256=sha(two),feasibility_sha256=sha(RUN/'protocol/FEASIBILITY_FROZEN.json'),
        baseline_mean_scope='Only structurally feasible native accepted development outputs, with full six-attempt denominator retained; no seed replacements',
        uncertainty='Observed H1/H2 changes are sensitivity diagnostics, not rigorous FE bounds or calibration uncertainty')
    write(path,decision)
    body='# Registered target-selection outcome\n\n'+ '\n'.join(f'- {k}: {v}' for k,v in decision.items() if k not in ['development_mesh_pairs','feasible_variant_results'])+'\n\n'
    body+='| Variant | Accepted n | Mean MPa | Mean difference MPa | H2 effect eligible |\n|---|---:|---:|---:|---|\n'
    body+=''.join(f"| {r['trial_id']} | {r['n']} | {r['mean_MPa']:.6f} | {r['mean_difference_MPa']:+.6f} | {r['mesh_effect_eligible']} |\n" for r in decision['feasible_variant_results'])
    body+='\nThe target and all geometry–mechanics outcomes precede model submission. The target value and selection rule are common information; measured development responses and associations are IF-only. No target extrapolation from historical lane designs or final responses. No physical material accuracy is implied.\n'
    (DOC/'V0_7_3_TARGET_SELECTION.md').write_text(body,encoding='utf-8',newline='\n')
    print(decision,flush=True)

if __name__=='__main__':freeze()
