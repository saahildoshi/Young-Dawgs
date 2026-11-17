"""Actual F1 native controls/reference/genuine archived generation with explicit void."""
import argparse
import hashlib
import importlib.util
import shutil
from pathlib import Path
import numpy as np
from scripts.v070_protocol import REPO,read,write,sha
from scripts.v074_experiment import RUN,DOC,BASE,MICRO,now
from metamaterial_eval.simulation.three_phase_elastic import solid_mesh,validate_solid_mesh,write_solid_mesh,source_solid,reopen_solid,constraints_solid

def model(name,k):
    properties={1:{'E_MPa':1000.,'nu':.3},2:{'E_MPa':10000.,'nu':.3}};expected=None
    if name=='F1_M0':a=np.zeros((32,32),np.uint8);expected=1000.
    elif name=='F1_M1_VOID':a=np.zeros((32,32),np.uint8);a[:,8:24]=2;expected=500.
    elif name=='F1_M1_PARALLEL':
        a=np.zeros((32,32),np.uint8);a[:,16:]=1;expected=5500.;properties={key:{**value,'nu':0.} for key,value in properties.items()}
    else:
        p=RUN/'f1/source_manifests'/f'{name}.json';source=read(p);path=REPO/source['source_path']
        assert sha(path)==source['source_file_sha256'];a=np.load(path,allow_pickle=False)
    return solid_mesh(a,k),properties,expected

def execute_engine():
    identity={name.replace('\\','/'):digest for name,digest in read(RUN/'audit/QUALIFIED_EVALUATOR.json').items()}
    assert sha(REPO/'scripts/v071_mechanics.py')==identity['scripts/v071_mechanics.py']
    spec=importlib.util.spec_from_file_location('v074_inherited_native_execution',REPO/'scripts/v071_mechanics.py')
    e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e);e.RUN,e.BASE,e.DOC=RUN,BASE,DOC
    return e

def authenticate():
    ref=MICRO/'references/F1/evaluation_only_labels.npy';generated=MICRO/'llm_trials/F1_B_02/evaluation_r0_held/seed_000.npy'
    receipt=read(MICRO/'llm_trials/F1_B_02/RECEIPT_r0.json');source=MICRO/'llm_trials/F1_B_02/generator_r0.py'
    assert sha(source)==receipt['code_sha256'] and receipt['ordinary_ChatGPT'] and not receipt['Work_or_Codex']
    archived=read(generated.with_suffix('.json'));a=np.load(generated)
    assert hashlib.sha256(a.tobytes()).hexdigest()==archived['array_sha256']
    assert archived['source_sha256']==sha(source) and archived['seed']==0
    for name,path in [('F1_M2_REFERENCE',ref),('F1_M3_B02_SEED0',generated)]:
        a=np.load(path);mesh=solid_mesh(a);proof=validate_solid_mesh(mesh)
        write(RUN/'f1/source_manifests'/f'{name}.json',{'source_path':str(path.relative_to(REPO)).replace('\\','/'),
            'source_file_sha256':sha(path),'source_semantic_sha256':hashlib.sha256(a.tobytes()).hexdigest(),
            'labels':{'0':'matrix solid MAT1','1':'carbon-fiber cross-section-like solid MAT2','2':'void no element'},
            'phase_counts':{str(v):int((a==v).sum()) for v in [0,1,2]},'mesh_proof':proof,
            'captured_script_sha256':sha(source) if name.startswith('F1_M3') else None,
            'receipt_sha256':sha(MICRO/'llm_trials/F1_B_02/RECEIPT_r0.json') if name.startswith('F1_M3') else None,
            'provenance':'Original prepared C/PEEK annotation, approximate circular fiber masks; transverse descriptors; unknown physical scale' if name.startswith('F1_M2') else 'Genuine archived ordinary-ChatGPT F1_B_02/r0, evaluator heldout seed0; no source edits or new generator call',
            'illustrative_not_calibrated':True})
    write(RUN/'f1/PROTOCOL.json',{'registered_utc':read(RUN/'protocol/PROTOCOL.json')['registered_utc'],
        'material_protocol':'F1_ILLUSTRATIVE_TRANSVERSE_TWO_SOLIDS_AND_EXPLICIT_VOID','E_MPa':[1000,10000],'nu':.3,
        'void_no_elements':True,'domain_mm':[1,1],'thickness_mm':1,'nominal_stress':'Signed total boundary reaction divided by full1mm envelope width×1mm thickness, including void in denominator',
        'strains':[.001,.002,.003,.004,.005],'plane_stress':'PLANE182 KEYOPT1=0/3=3/6=0','NLGEOM':False,
        'boundaries':'UY0 bottom, imposed negativeUY top; oneUX bottom pin per independent load-carrying component, no hidden springs or hole constraints',
        'floating_islands':'Reject/HOLD if a solid component lacks both loading boundaries or joins another component only at a corner; do not repair geometry',
        'models':['F1_M0','F1_M1_PARALLEL','F1_M1_VOID','F1_M2_REFERENCE','F1_M3_B02_SEED0'],
        'H2':['F1_M2_REFERENCE','F1_M3_B02_SEED0'],'source_hashes':{path.name:sha(path) for path in (RUN/'f1/source_manifests').glob('*.json')}})

def qualify(source,post,m,properties,expected,name,k):
    p=read(RUN/'protocol/PROTOCOL.json');tol=p['tolerances']
    c=np.loadtxt(post/'curve.csv',delimiter=',');n=np.loadtxt(post/'nodes.csv',delimiter=',');f=np.loadtxt(post/'fields.csv',delimiter=',');conn=np.loadtxt(post/'connectivity.csv',delimiter=',')
    inventory=(source/'inventory.txt').read_text(errors='replace');constraints=constraints_solid(inventory,m)
    strain=-c[:,2];stress=-c[:,5];force=np.abs(c[:,5]);slope,intercept=np.polyfit(strain,stress,1)
    volumes=f[:,-1];energy=f[:,-2];sxx,syy,sxy=f[:,2:5].T;exx,eyy,gxy=f[:,6:9].T
    checks={'source_process':read(source/'EXECUTION.json')['native_process_ok'],'readback_process':read(post/'EXECUTION.json')['native_process_ok'],
        'independent_exports_identical':all(read(post/'READBACK.json')['identical_exports_to_solve'].values()),
        'mesh_counts':bool(c.shape==(5,12) and np.all(c[:,10]==len(m['nodes'])) and np.all(c[:,11]==len(m['quads']))),
        'actual_five_strains':bool(np.allclose(strain,p['strain_checkpoints'],atol=1e-9,rtol=0)),
        'native_node_ids_coordinates':bool(n.shape==(len(m['nodes']),5) and np.array_equal(n[:,0],np.arange(1,len(n)+1)) and np.allclose(n[:,1:3],m['nodes'],atol=1e-9,rtol=0)),
        'native_element_connectivity':bool(conn.shape==(len(m['quads']),5) and np.array_equal(conn[:,1:],m['quads']+1)),
        'native_phase_ids':bool(f.shape==(len(m['quads']),12) and np.array_equal(f[:,0],np.arange(1,len(f)+1)) and np.array_equal(f[:,1],m['materials'])),
        'complete_constraints_no_void_restraints':constraints['passed'],'finite_fields':bool(np.isfinite(f).all() and np.isfinite(n).all()),
        'reactions_signed':bool(np.all(c[:,5]<0) and np.all(c[:,6]>0)),
        'reaction_balance':bool(np.max(np.abs(c[:,5]+c[:,6])/force)<.001),
        'pin_sum_negligible':bool(np.max(np.abs(c[:,7])/force)<.001),
        'energy_work':bool(np.max(np.abs(c[:,8]-.5*force*strain)/c[:,8])<.001),
        'solid_volume_not_envelope':bool(np.allclose(c[:,9],np.mean(m['source']!=2),atol=1e-8,rtol=0) and abs(volumes.sum()-np.mean(m['source']!=2))<1e-8),
        'summed_element_energy':abs(energy.sum()-c[-1,8])/c[-1,8]<.001,
        'envelope_stress_equals_integrated_solid_stress':abs(np.sum(syy*volumes)-c[-1,5])/force[-1]<.001,
        'positive_stiffness_energy':bool(slope>0 and np.all(c[:,8]>0)),
        'linear_fit':bool(np.max(np.abs(np.polyval([slope,intercept],strain)-stress))/stress.max()<1e-5 and abs(intercept)/stress.max()<1e-5),
        'plane_stress_constitutive':True,'native_plane182_options':bool('PLANE182' in inventory and '0  0  3' in inventory)}
    # Native KEYOPT inventory can vary spacing; match actual option rows explicitly.
    import re
    checks['native_plane182_options']=bool(re.search(r'KEYOPT\( 1- 6\)=\s*0\s+0\s+3\s+0\s+0\s+0',inventory))
    phase={}
    for mid,props in properties.items():
        use=f[:,1]==mid
        if not use.any():continue
        E,nu=props['E_MPa'],props['nu'];pred=np.column_stack([(sxx[use]-nu*syy[use])/E,(syy[use]-nu*sxx[use])/E,2*(1+nu)*sxy[use]/E])
        actual=np.column_stack([exx[use],eyy[use],gxy[use]])
        err=float(np.max(np.abs(actual-pred))/max(np.max(np.abs(actual)),1e-12));checks['plane_stress_constitutive']&=err<1e-4 and np.max(np.abs(f[use,9]))<1e-7*max(E,1)
        phase[str(mid)]={'elements':int(use.sum()),'envelope_volume_fraction':float(volumes[use].sum()),
            'solid_volume_fraction':float(volumes[use].sum()/volumes.sum()),'mean_syy_MPa':float(np.average(syy[use],weights=volumes[use])),
            'mean_axial_strain':float(np.average(eyy[use],weights=volumes[use])),'equivalent_percentiles_MPa':{str(q):float(np.percentile(f[use,5],q)) for q in [50,90,95,99,100]},
            'elastic_energy_fraction':float(energy[use].sum()/energy.sum()),'constitutive_relative_error':err}
    if expected is not None:checks['analytical_modulus']=abs(slope-expected)/expected<.005
    checks={key:bool(v) for key,v in checks.items()}
    r={'specimen_id':name,'family':'F1','mesh_level':k,'accepted':all(checks.values()),'checks':checks,'mesh_proof':validate_solid_mesh(m),
        'actual_engineering_strains':strain.tolist(),'nominal_stresses_MPa':stress.tolist(),'signed_native_curve':c.tolist(),
        'effective_modulus_MPa':float(slope),'fit_intercept_MPa':float(intercept),'analytical_expected_MPa':expected,
        'phase_results':phase,'constraints':constraints,'properties':properties,'source_directory':str(source),'independent_readback_directory':str(post),
        'native_result_sha256':sha(source/'elastic.rst'),'native_database_sha256':sha(source/'model.db'),'native_fields_sha256':sha(post/'fields.csv'),
        'nominal_stress_denominator':'Full envelope width×thickness, includes void; solid stress integration checked separately',
        'field_location':'Native element-associated ETABLE; no cross-material nodal stress averaging','physical_calibration':False,'RVE_qualified':False}
    write(RUN/'f1/mechanical_response'/f'{source.name}.json',r)
    write(RUN/'native_result_manifests'/source.name/'F1_QUALIFICATION.json',r)
    write(RUN/'native_result_manifests'/source.name/'NATIVE_ARTIFACTS.json',{key:{'path':str(source/key),'sha256':sha(source/key),'bytes':(source/key).stat().st_size} for key in ['elastic.rst','model.db','mesh.inp','solver.out','curve.csv','nodes.csv','fields.csv']})
    print('F1 QUALIFIED',source.name,r['accepted'],'E',slope,'failed',[key for key,v in checks.items() if not v],flush=True)
    return r

def perform(name,k=1):
    previous=RUN/'f1/mechanical_response'/f'{name}_H{k}_attempt001.json'
    if previous.exists():r=read(previous);assert r['accepted'];return r
    m,props,expected=model(name,k);proof=validate_solid_mesh(m)
    source=BASE/f'{name}_H{k}_attempt001'
    if source.exists():
        assert not (source/'EXECUTION.json').exists(),'Existing native attempt is never silently rerun'
        assert read(source/'MODEL.json')['input_sha256']==sha(source/'input.inp')
    else:source.mkdir(exist_ok=False)
    write_solid_mesh(m,source/'mesh.inp');steps=read(RUN/'protocol/PROTOCOL.json')['strain_checkpoints']
    (source/'input.inp').write_text(source_solid(m,props,steps),encoding='ascii',newline='\n')
    write(source/'MODEL.json',{'kind':'F1_LICENSED_SOURCE_SOLVE','specimen_id':name,'mesh_level':k,'proof':proof,'source_semantic_sha256':hashlib.sha256(m['source'].tobytes()).hexdigest(),
        'input_sha256':sha(source/'input.inp'),'mesh_input_sha256':sha(source/'mesh.inp'),'properties':props})
    engine=execute_engine();assert engine.execute(source)
    post=BASE/f'{source.name}_read01';post.mkdir(exist_ok=False)
    originals={key:sha(source/key) for key in ['elastic.rst','model.db']}
    (post/'input.inp').write_text(reopen_solid(m,steps,source),encoding='ascii',newline='\n')
    write(post/'MODEL.json',{'kind':'F1_INDEPENDENT_READ_ONLY_RST_REOPEN','source_directory':str(source),'native_source_hashes':originals})
    assert engine.execute(post,True)
    assert all(sha(source/key)==digest for key,digest in originals.items())
    same={key:sha(source/key)==sha(post/key) for key in ['curve.csv','nodes.csv','fields.csv','native_counts.csv','connectivity.csv']}
    write(post/'READBACK.json',{'identical_exports_to_solve':same,'source_hashes_unchanged':True});write(RUN/'native_result_manifests'/post.name/'READBACK.json',read(post/'READBACK.json'))
    r=qualify(source,post,m,props,expected,name,k);assert r['accepted'];return r

def campaign():
    if not (RUN/'f1/PROTOCOL.json').exists():authenticate()
    for name,k in [('F1_M0',1),('F1_M1_PARALLEL',1),('F1_M1_VOID',1),('F1_M2_REFERENCE',1),('F1_M3_B02_SEED0',1),('F1_M2_REFERENCE',2),('F1_M3_B02_SEED0',2)]:perform(name,k)

if __name__=='__main__':campaign()
