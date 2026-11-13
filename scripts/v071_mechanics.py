"""Bounded licensed P3 elasticity execution, independent readback and qualification."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import re
import shutil
import numpy as np
import psutil
from scripts.v071_register import RUN,BASE,DOC
from scripts.v070_protocol import REPO,read,write,sha
from metamaterial_eval.simulation.composite_elastic import structured_mesh,validate_mesh,write_mesh,source_input,readonly_input,constraint_inventory
from metamaterial_eval.simulation.windows_ansys import bounded_run,installations
from metamaterial_eval.simulation.system_health import HealthPolicy
from metamaterial_eval.simulation.solver_execution import solver_release,file_hash

CURVE=['load_step','native_time','top_uy_min','top_uy_max','bottom_uy_absmax','top_rf_y','bottom_rf_y','pin_rf_x','strain_energy','volume','nodes','elements']
FIELDS=['element','material','sxx','syy','sxy','seqv','exx','eyy','engineering_gxy','szz','strain_energy','volume']


def model(specimen,k=1):
    protocol=read(RUN/'protocol/PROTOCOL.json')
    properties={int(key):v for key,v in protocol['material']['materials'].items()}
    expected=None
    if specimen in ['M0_matrix','M1_parallel','M1_series']:
        a=np.ones((32,32),dtype=np.uint8)
        if specimen=='M1_parallel':a[:,16:]=5
        if specimen=='M1_series':a[:16,:]=5
        expected=protocol['controls'][specimen]['E_expected_MPa']
        if specimen!='M0_matrix':properties={i:{**p,'nu':0.} for i,p in properties.items()}
    else:
        original='M2_reference' if specimen=='M1_equal' else specimen
        s=read(RUN/'specimen_manifests'/f'{original}.json')
        path=REPO/s['source_array_path']
        if sha(path)!=s['source_array_sha256']:raise ValueError('Altered authenticated categorical source')
        a=np.load(path,allow_pickle=False)
        if specimen=='M1_equal':properties={i:{'E_MPa':1000.,'nu':.3} for i in [1,2]};expected=1000.
    return structured_mesh(a,k),properties,expected


def prepare(specimen,k=1,attempt=1):
    m,properties,expected=model(specimen,k);proof=validate_mesh(m)
    d=BASE/f'{specimen}_H{k}_attempt{attempt:03d}';d.mkdir(parents=True,exist_ok=False)
    write_mesh(m,d/'mesh.inp')
    p=read(RUN/'protocol/PROTOCOL.json')
    (d/'input.inp').write_text(source_input(m,properties,p['strain_checkpoints']),encoding='ascii',newline='\n')
    meta={'specimen_id':specimen,'mesh_level':k,'mesh_id':m['mesh_id'],'mesh_validation':proof,
          'properties':properties,'analytical_modulus_MPa':expected,'source_labels_sha256':hashlib.sha256(m['source'].tobytes()).hexdigest(),
          'mesh_input_sha256':file_hash(d/'mesh.inp'),'input_sha256':file_hash(d/'input.inp'),
          'kind':'LICENSED_SOURCE_SOLVE','source_code_sha256':sha(REPO/'metamaterial_eval/simulation/composite_elastic.py')}
    write(d/'MODEL.json',meta)
    print('PREPARED',d.name,flush=True)
    return d


def execute(d,readonly=False):
    d=Path(d);p=read(RUN/'protocol/PROTOCOL.json');limits=p['resource_limits']
    existing=list(BASE.glob('*/process_receipt.json'))
    elapsed=sum(read(f)['runtime_seconds'] for f in existing)
    if len(existing)>=limits['maximum_native_jobs'] or elapsed>=limits['native_campaign_seconds']:raise RuntimeError('Native campaign budget reached')
    if any((x.info['name'] or '').lower() in ['ansys241.exe','ansys.exe'] for x in psutil.process_iter(['name'])):raise RuntimeError('Another native job is running')
    executable=next(x['mapdl'] for x in installations() if x['release_selector']=='241')
    timeout=min(limits['readback_timeout_s' if readonly else 'solve_timeout_s'],limits['native_campaign_seconds']-elapsed)
    write(d/'PREFLIGHT.json',{'available_RAM_bytes':psutil.virtual_memory().available,'disk_free_bytes':shutil.disk_usage(BASE).free,
          'campaign_native_elapsed_seconds':elapsed,'campaign_native_jobs_before':len(existing),'timeout_seconds':timeout,'RSS_cap':None})
    job='v071_'+hashlib.sha256(str(d.resolve()).encode()).hexdigest()[:12]
    process=bounded_run([executable,'-b','-smp','-np','2','-m','2048','-j',job,'-i','input.inp','-o','solver.out'],
                        d,prepared=True,timeout=timeout,rss_limit=None,min_disk_free=limits['disk_reserve_bytes'],
                        health_policy=HealthPolicy(),resource_sample_seconds=2)
    log=(d/'solver.out').read_text(errors='replace') if (d/'solver.out').exists() else ''
    errors=re.findall(r'\*\*\*\s*(?:ERROR|FATAL)\s*\*\*\*[^\n]*\n\s*([^\n]+)',log,re.I)
    accepted=process['returncode']==0 and process['status']=='PROCESS_EXITED' and not errors
    receipt={'kind':'INDEPENDENT_READ_ONLY_RST_REOPEN' if readonly else 'LICENSED_SOURCE_SOLVE',
             'native_process_ok':accepted,'solver_release':solver_release(log),'native_errors':errors,'process':process,
             'input_sha256':file_hash(d/'input.inp'),'job_name':job}
    write(d/'EXECUTION.json',receipt)
    compact=RUN/'native_result_manifests'/d.name;compact.mkdir(parents=True,exist_ok=False)
    write(compact/'EXECUTION.json',receipt)
    for name in ['input.inp','MODEL.json','PREFLIGHT.json']:
        if (d/name).exists():shutil.copyfile(d/name,compact/name)
    if (d/'inventory.txt').exists():
        text=re.sub(r'(?m)^\s*\d{6,}\s+(VERSION=)',r'[customer identifier omitted] \1',(d/'inventory.txt').read_text(errors='replace'))
        (compact/'inventory.txt').write_text('\n'.join(l.rstrip() for l in text.splitlines())+'\n',encoding='utf-8',newline='\n')
    print('NATIVE',d.name,accepted,process['runtime_seconds'],errors,flush=True)
    return accepted


def readback(source,index=1):
    source=Path(source);meta=read(source/'MODEL.json');m,_,_=model(meta['specimen_id'],meta['mesh_level'])
    hashes={name:file_hash(source/name) for name in ['elastic.rst','model.db']}
    d=BASE/f'{source.name}_read{index:02d}';d.mkdir(exist_ok=False)
    steps=read(RUN/'protocol/PROTOCOL.json')['strain_checkpoints']
    (d/'input.inp').write_text(readonly_input(m,steps,source),encoding='ascii',newline='\n')
    write(d/'MODEL.json',{'kind':'INDEPENDENT_READ_ONLY_RST_REOPEN','source_directory':str(source),'native_source_hashes':hashes})
    if not execute(d,True):return None
    assert all(file_hash(source/name)==v for name,v in hashes.items())
    names=['curve.csv','nodes.csv','fields.csv','native_counts.csv','connectivity.csv']
    compare={name:file_hash(d/name)==file_hash(source/name) for name in names if (source/name).exists()}
    write(d/'READBACK.json',{'source_hashes_unchanged':True,'identical_exports_to_solve':compare,'source_directory':str(source)})
    write(RUN/'native_result_manifests'/d.name/'READBACK.json',read(d/'READBACK.json'))
    if not all(compare.values()):raise ValueError('Independent exports differ from inline source exports')
    return d


def qualify(source,post):
    source,post=Path(source),Path(post);meta=read(source/'MODEL.json')
    m,properties,expected=model(meta['specimen_id'],meta['mesh_level'])
    p=read(RUN/'protocol/PROTOCOL.json');tol=p['tolerances'];strains=np.array(p['strain_checkpoints'])
    curve=np.loadtxt(post/'curve.csv',delimiter=',');nodes=np.loadtxt(post/'nodes.csv',delimiter=',');fields=np.loadtxt(post/'fields.csv',delimiter=',')
    counts=np.loadtxt(post/'native_counts.csv',delimiter=',',usecols=(0,1,2))
    checks={'source_process':read(source/'EXECUTION.json')['native_process_ok'],'readback_process':read(post/'EXECUTION.json')['native_process_ok'],
            'independent_exports_identical':all(read(post/'READBACK.json')['identical_exports_to_solve'].values()),
            'five_sets_and_exact_mesh_counts':np.array_equal(counts,[5,len(m['nodes']),len(m['quads'])]),
            'complete_finite_fields':bool(nodes.shape==(len(m['nodes']),5) and fields.shape==(len(m['quads']),12) and curve.shape==(5,12) and all(np.isfinite(a).all() for a in [curve,nodes,fields]))}
    if not checks['complete_finite_fields']:raise ValueError('Missing/nonfinite actual native fields')
    checks['native_node_ids_and_coordinates']=bool(np.array_equal(nodes[:,0],np.arange(1,len(nodes)+1)) and np.allclose(nodes[:,1:3],m['nodes'],atol=1e-12,rtol=0))
    checks['native_element_ids_and_materials']=bool(np.array_equal(fields[:,0],np.arange(1,len(fields)+1)) and np.array_equal(fields[:,1],m['materials']))
    constraints=constraint_inventory((source/'inventory.txt').read_text(errors='replace'),m)
    checks['exact_native_constraint_inventory']=constraints['passed']
    connectivity=np.loadtxt(post/'connectivity.csv',delimiter=',')
    checks['native_element_connectivity']=bool(connectivity.shape==(len(m['quads']),5) and np.array_equal(connectivity[:,0],np.arange(1,len(m['quads'])+1)) and np.array_equal(connectivity[:,1:],m['quads']+1))
    achieved=np.abs(curve[:,2])/m['height'];force=np.abs(curve[:,5]);stress=force/m['width']
    balance=np.abs(curve[:,5]+curve[:,6])/np.maximum(force,1e-12)
    pin=np.abs(curve[:,7])/np.maximum(force,1e-12)
    energy_error=np.abs(curve[:,8]-.5*force*np.abs(curve[:,2]))/np.maximum(np.abs(curve[:,8]),1e-12)
    checks['native_checkpoint_displacements']=bool(np.allclose(achieved,strains,atol=tol['native_displacement_absolute_mm'],rtol=0) and np.max(np.abs(curve[:,2]-curve[:,3]))<=tol['native_displacement_absolute_mm'] and np.max(curve[:,4])<=tol['native_displacement_absolute_mm'])
    checks['reaction_signs']=bool(np.all(curve[:,5]<0) and np.all(curve[:,6]>0))
    checks['reaction_balance']=bool(max(balance)<=tol['reaction_balance_relative'])
    checks['horizontal_pin_negligible']=bool(max(pin)<=tol['horizontal_pin_relative'])
    checks['native_energy_vs_work']=bool(max(energy_error)<=tol['energy_relative'])
    checks['native_volume']=bool(np.allclose(curve[:,9],m['width']*m['height'],rtol=tol['native_volume_relative'],atol=1e-12))
    checks['final_boundary_kinematics']=bool(np.max(np.abs(nodes[m['top'],4]+strains[-1]*m['height']))<1e-9 and np.max(np.abs(nodes[m['bottom'],4]))<1e-9 and abs(nodes[m['pin'],3])<1e-9)
    slope,intercept=np.polyfit(achieved,stress,1);pred=slope*achieved+intercept
    residual=float(np.max(np.abs(pred-stress))/np.max(stress))
    checks['linear_fit']=residual<=tol['linear_fit_relative_residual']
    checks['positive_energy_stiffness']=bool(slope>0 and np.all(fields[:,10]>=-1e-12))
    phase={};constitutive=[]
    for material,prop in properties.items():
        a=fields[fields[:,1]==material]
        if not len(a):continue
        E,nu=prop['E_MPa'],prop['nu'];G=E/(2*(1+nu))
        eps=np.column_stack(((a[:,2]-nu*a[:,3])/E,(a[:,3]-nu*a[:,2])/E,a[:,4]/G))
        error=float(np.max(np.abs(eps-a[:,6:9]))/max(np.max(np.abs(eps)),1e-12));constitutive.append(error)
        phase[str(material)]={'elements':len(a),'volume':float(a[:,11].sum()),'volume_fraction':float(a[:,11].sum()/fields[:,11].sum()),
                             'mean_sxx_MPa':float(np.average(a[:,2],weights=a[:,11])),'mean_syy_MPa':float(np.average(a[:,3],weights=a[:,11])),
                             'mean_equivalent_MPa':float(np.average(a[:,5],weights=a[:,11])),'mean_axial_strain':float(np.average(a[:,7],weights=a[:,11])),
                             'equivalent_percentiles_MPa':dict(zip(['p50','p90','p95','p99','max'],map(float,np.percentile(a[:,5],[50,90,95,99,100])))),
                             'equivalent_percentiles_over_nominal':dict(zip(['p50','p90','p95','p99','max'],map(float,np.percentile(a[:,5]/stress[-1],[50,90,95,99,100])))),
                             'elastic_energy_Nmm':float(a[:,10].sum()),'elastic_energy_fraction':float(a[:,10].sum()/fields[:,10].sum()),'constitutive_relative_error':error}
    checks['native_plane_stress_constitutive_and_engineering_shear']=bool(max(constitutive)<=tol['constitutive_field_relative'] and np.max(np.abs(fields[:,9]))<1e-8)
    checks['summed_element_energy']=bool(abs(fields[:,10].sum()-curve[-1,8])/curve[-1,8]<=tol['energy_relative'])
    checks['native_phase_area_inventory']=bool(all(abs(phase[str(k)]['volume_fraction']-np.mean(m['materials']==k))<1e-8 for k in [1,2] if np.any(m['materials']==k)))
    benchmark_error=None if expected is None else abs(slope-expected)/expected
    if expected is not None:checks['analytical_modulus']=benchmark_error<=tol['benchmark_relative']
    if meta['specimen_id'] in ['M0_matrix','M1_equal']:
        ux_expected=.3*strains[-1]*m['nodes'][:,0]
        checks['homogeneous_poisson_contraction']=bool(np.max(np.abs(nodes[:,3]-ux_expected))<1e-8)
    checks={key:bool(value) for key,value in checks.items()}
    result={'specimen_id':meta['specimen_id'],'mesh_level':meta['mesh_level'],'mesh_id':m['mesh_id'],'accepted':all(checks.values()),'checks':checks,
            'source_directory':str(source),'independent_readback_directory':str(post),'native_result_sha256':file_hash(source/'elastic.rst'),
            'native_database_sha256':file_hash(source/'model.db'),'native_fields_sha256':file_hash(post/'fields.csv'),
            'curve_columns':CURVE,'native_curve':curve.tolist(),'engineering_strains':achieved.tolist(),'nominal_stresses_MPa':stress.tolist(),
            'effective_modulus_MPa':float(slope),'normalized_effective_modulus':float(slope/1000.),'fit_intercept_MPa':float(intercept),
            'relative_fit_max_residual':residual,'R_squared':float(1-np.sum((pred-stress)**2)/np.sum((stress-stress.mean())**2)),
            'secant_modulus_MPa':float(stress[-1]/achieved[-1]),'analytical_modulus_MPa':expected,'analytical_relative_error':benchmark_error,
            'max_reaction_imbalance':float(max(balance)),'max_pin_force_relative':float(max(pin)),'max_energy_relative_error':float(max(energy_error)),
            'phase_results':phase,'field_columns':FIELDS,'field_location':'ETABLE average element centroid, no cross-material nodal averaging; percentiles over equal-volume elements',
            'mesh':meta['mesh_validation'],'material_properties':properties,'physical_calibration':False,'RVE_qualified':False,
            'execution':{'runtime_seconds':read(source/'EXECUTION.json')['process']['runtime_seconds'],'peak_tree_rss_bytes':read(source/'EXECUTION.json')['process']['peak_tree_rss_bytes']}}
    result['constraint_inventory']=constraints
    write(source/'QUALIFICATION.json',result)
    write(RUN/'mechanical_response'/f'{source.name}.json',result)
    out=RUN/'native_result_manifests'/source.name
    write(out/'NATIVE_ARTIFACTS.json',{name:{'path':str(source/name),'sha256':file_hash(source/name),'bytes':(source/name).stat().st_size} for name in ['elastic.rst','model.db','mesh.inp','solver.out','curve.csv','nodes.csv','fields.csv']})
    shutil.copyfile(post/'curve.csv',out/'curve.csv')
    print('QUALIFIED',source.name,result['accepted'],'E=',slope,'failed=',[k for k,v in checks.items() if not v],flush=True)
    return result


def perform(specimen,k=1,attempt=1):
    def accepted(name,level=1):
        paths=sorted((RUN/'mechanical_response').glob(f'{name}_H{level}_attempt*.json'))
        return bool(paths and read(paths[-1])['accepted'])
    if specimen not in ['M0_matrix','M1_parallel','M1_series','M1_equal']:
        if not all(accepted(name) for name in ['M0_matrix','M1_parallel','M1_series','M1_equal']):
            raise RuntimeError('All four native analytical/equal-material controls must qualify before P3 mechanics')
    if specimen=='M2_reference' and k==2 and not accepted('M2_reference'):
        raise RuntimeError('Reference H1 must qualify before H2')
    if specimen.startswith(('M3','M4','M5','M6')):
        if not all(accepted('M2_reference',level) for level in [1,2]):raise RuntimeError('Reference H1/H2 qualification required')
        reference=[read(sorted((RUN/'mechanical_response').glob(f'M2_reference_H{level}_attempt*.json'))[-1]) for level in [1,2]]
        difference=abs(reference[0]['effective_modulus_MPa']-reference[1]['effective_modulus_MPa'])/reference[1]['effective_modulus_MPa']
        if difference>read(RUN/'protocol/PROTOCOL.json')['tolerances']['mesh_modulus_relative']:
            raise RuntimeError('Reference mesh-sensitivity gate failed; production refinement needs an evidenced protocol supplement')
    if specimen=='M6_C02_r0' and not all(accepted(name) for name in ['M3_A01','M4_B02','M5_C02_r1']):
        raise RuntimeError('Required generated specimens must qualify before optional pair')
    d=prepare(specimen,k,attempt)
    if not execute(d):return None
    post=readback(d)
    return qualify(d,post) if post else None


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('specimen');parser.add_argument('--level',type=int,default=1);parser.add_argument('--attempt',type=int,default=1)
    a=parser.parse_args();r=perform(a.specimen,a.level,a.attempt)
    if not r or not r['accepted']:raise SystemExit(1)
