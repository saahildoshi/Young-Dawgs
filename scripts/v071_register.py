"""Prospective registration of the bounded, additive P3 elastic benchmark."""
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import shutil
import subprocess
import numpy as np
import psutil
from scripts.v070_protocol import REPO, read, write, sha
from scripts.v070_real_pilot import RUN as PILOT
from metamaterial_eval.composites.microscopy import describe, validate
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.windows_ansys import installations

RUN = REPO/'experiments/pipeline_v0.7.1/run_001'
DOC = REPO/'docs/pipeline_v0.7.1'
BASE = artifact_root()/'solver/v071/run_001'
REQUEST = Path(r'C:\Users\sd22446\.codex\attachments\f737da9a-f67d-49f2-ab45-151504f33650\Pasted text.txt')


def register():
    assert not RUN.exists() and not DOC.exists() and not BASE.exists()
    status=subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).splitlines()
    assert all(line=='?? scripts/v071_register.py' for line in status),status
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode().split('\0')
    protected={name:sha(REPO/name) for name in tracked if name and (REPO/name).is_file()}
    frozen=read(PILOT/'protocol/ALL_SCRIPTS_FROZEN.json')
    assert all(sha(PILOT/k)==v for k,v in frozen['files'].items())
    assert read(PILOT/'audit/FINAL_SCIENTIFIC_AUDIT.json')['heldout_valid_outputs']==160
    RUN.mkdir(parents=True);DOC.mkdir();BASE.mkdir(parents=True)
    write(RUN/'audit/PROTECTED_BEFORE.json',protected)
    material={'id':'ILLUSTRATIVE_TWO_PHASE_ELASTIC_CONTRAST_10','units':'mm N MPa',
              'constitutive_model':'small-strain isotropic linear elasticity',
              'materials':{'1':{'E_MPa':1000.,'nu':.30},'2':{'E_MPa':10000.,'nu':.30}},
              'raw_to_material':{'1':1,'5':2},'physical_calibration':False,
              'interface':'perfectly bonded shared nodes, no contact'}
    write(RUN/'material_protocol/MATERIAL.json',material)
    selected=[('M2_reference',None,0),('M3_A01','P3_A_01',0),('M4_B02','P3_B_02',0),
              ('M5_C02_r1','P3_C_02',1),('M6_C02_r0','P3_C_02',0)]
    for specimen,trial,revision in selected:
        if trial is None:
            source=PILOT/'references/P3/evaluation_only_labels.npy';record=None;generator=None
        else:
            d=PILOT/'llm_trials'/trial
            source=d/f'evaluation_r{revision}_held/seed_000.npy'
            record=next(r for r in read(d/f'evaluation_r{revision}_held/EXECUTION.json')['records'] if r['seed']==0)
            assert record['status']=='OK' and record['validity']['passed']
            generator=d/f'generator_r{revision}.py'
            assert sha(generator)==read(d/f'RECEIPT_r{revision}.json')['code_sha256']
        a=np.load(source,allow_pickle=False);validate(a,'P3')
        if record:assert hashlib.sha256(a.tobytes()).hexdigest()==record['array_sha256']
        descriptors=describe(a,'P3')
        counts={str(k):int((a==k).sum()) for k in [1,5]}
        manifest={'specimen_id':specimen,'family_id':'P3','reference_id':'P3',
                  'source_kind':'reference_annotation' if trial is None else 'actual_saved_LLM_realization',
                  'source_array_path':str(source.relative_to(REPO)).replace('\\','/'),
                  'source_array_sha256':sha(source),'shape':list(a.shape),'dtype':str(a.dtype),
                  'raw_phase_labels':[1,5],'phase_counts':counts,
                  'phase_fractions':{k:v/a.size for k,v in counts.items()},
                  'phase_roles':{'1':'matrix_like_solid','5':'reinforcement_like_solid_provisional'},
                  'phase_to_material_id':{'1':1,'5':2},'generator_trial_id':trial,
                  'revision':revision if trial else None,'seed':0 if trial else None,
                  'generator_script_sha256':sha(generator) if generator else None,
                  'structural_validity':record['validity'] if record else {'passed':True,'source':'authenticated reference categorical contract'},
                  'exact_seed_descriptors':descriptors,
                  'visible_morphology_error':record['visible_error'] if record else None,
                  'hidden_morphology_error':record['hidden_error'] if record else None,
                  'width_mm':1.,'height_mm':1.,'thickness_mm':1.,
                  'scale_provenance':'Illustrative computational 1mm square; not physical microscopy calibration',
                  'material_protocol_id':material['id'],'boundary_condition_id':'VERTICAL_FREE_TANGENTIAL_ONE_UX_PIN',
                  'loading_direction':'y','element_formulation':'PLANE182 KEYOPT1=0 KEYOPT3=3 KEYOPT6=0',
                  'requested_strains':[.001,.002,.003,.004,.005],
                  'selection':'User-fixed exploratory morphology-selected script; seed0 fixed before mechanical outcomes',
                  'optional':specimen.startswith('M6')}
        write(RUN/'specimen_manifests'/f'{specimen}.json',manifest)
    controls={'M0_matrix':{'geometry':'all matrix','nu':.3,'E_expected_MPa':1000},
              'M1_parallel':{'geometry':'left matrix/right reinforcement, equal widths','nu':0.,'E_expected_MPa':5500},
              'M1_series':{'geometry':'bottom matrix/top reinforcement, equal heights','nu':0.,'E_expected_MPa':20000/11},
              'M1_equal':{'geometry':'P3 exact source labels, both E1000 nu0.3','nu':.3,'E_expected_MPa':1000}}
    p={'registered_utc':datetime.now(timezone.utc).isoformat(),'starting_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
       'request_sha256':sha(REQUEST),'initial_tree_clean':True,'artifact_root':str(artifact_root()),
       'native_base':str(BASE),'material':material,'controls':controls,
       'specimens':[s for s,_,_ in selected], 'required_generated':['M3_A01','M4_B02','M5_C02_r1'],
       'reference_mesh_levels':[1,2],'H1_elements':65536,'H1_nodes':66049,'H2_elements':262144,'H2_nodes':263169,
       'refinement':'subdivide every source pixel into k*k elements, same label; no resampling',
       'image_mapping':'row0 top; FE y=(height-row)/height; nodes indexed bottom to top; element ordering CCW',
       'element':{'name':'PLANE182','KEYOPT1':0,'KEYOPT3':3,'KEYOPT6':0,'real_constant_THK_mm':1.,
                  'integration':'2x2, full integration B-bar; no uniform reduced integration/hourglass control'},
       'strain_checkpoints':[.001,.002,.003,.004,.005],'NLGEOM':'OFF','loading':'UYbottom0, UYtop=-strain*H, UXbottomleft0; other UX free; sides traction free',
       'tolerances':{'benchmark_relative':.001,'reaction_balance_relative':.001,'horizontal_pin_relative':.001,
                     'energy_relative':.001,'native_displacement_absolute_mm':1e-9,'linear_fit_relative_residual':1e-5,
                     'mesh_modulus_relative':.02,'constitutive_field_relative':1e-5,'native_volume_relative':1e-8},
       'modulus_fit':'Unconstrained least squares slope+intercept over five actual native points; report secant and residuals',
       'local_fields':'ETABLE element-associated averaged centroid components; no cross-material nodal averaging. SENE summed once per element. EXY checked against SXY/G.',
       'resource_limits':{'one_native_job':True,'solve_timeout_s':1800,'readback_timeout_s':900,'native_campaign_seconds':10800,'maximum_native_jobs':32,
                          'rss_cap':None,'disk_reserve_bytes':50*2**30,'cores':2,'health_policy':'existing HealthPolicy defaults;6GiB sustained available reserve'},
       'optional_order':['M6 paired source','H2 checks of selected generated sources to assess unresolved differences'],
       'no_extra_seeds':True,'no_second_axis':True,'F1_mechanics':'DEFERRED','mechanical_LLM_feedback':'NOT_EXECUTED','optimization':'NOT_IMPLEMENTED',
       'physical_calibration':False,'RVE_qualification':False,'push':False}
    write(RUN/'protocol/PROTOCOL.json',p)
    write(RUN/'audit/ENVIRONMENT.json',{'installations':installations(),'physical_RAM_bytes':psutil.virtual_memory().total,
          'available_RAM_bytes':psutil.virtual_memory().available,'disk_free_bytes':shutil.disk_usage(BASE).free,
          'artifact_root_selector':'YD_ARTIFACT_ROOT or established per-user cache','license_secrets_read':False})
    write(RUN/'audit/DOCUMENTATION.json',{'installed_release':'2024 R1, v241','local_documentation_search':'ansys/docu/en-us contains message catalogs only; no PLANE182 manual installed',
          'v241_online_manual':'Requested exact v241 official URLs, unavailable via browsing tool',
          'available_official_adjacent_release':'https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_elem/Hlp_E_PLANE182.html',
          'integration_reference':'https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_thry/thy_el182.html',
          'ETABLE_reference':'https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_cmd/Hlp_C_ETABLE.html',
          'release_specific_gate':'Actual v241 ETLIST/RLIST/MPLIST and licensed analytical/thickness/constitutive behavior must corroborate settings; adjacent manual alone is not installed-release qualification'})
    (DOC/'V0_7_1_PROTOCOL.md').write_text('''# P3 controlled elastic benchmark: prospective protocol

Compare the exact P3 annotation with user-selected P3_A_01/r0, P3_B_02/r0 and P3_C_02/r1 saved held-out seed0 arrays. Optional paired P3_C_02/r0 seed0 follows the primary study. This exploratory selection uses known morphology outcomes, never mechanical outcomes. Preserve every prior source, script and result.

Native labels1 and5 map explicitly to solid materials1 and2. Both fill the domain, sharing nodes at interfaces. E=1000/10000MPa, nu=0.30 are illustrative numerical properties, not calibrated Ni–WC properties. The1mm square and1mm thickness are computational choices, not microscopy calibration. P3 phase5 identity remains provisional, the source is HorizontalFlip augmentation, and the crop is morphology-selected, not an RVE.

Use PLANE182 with KEYOPT(1)=0 (2x2 full integration B-bar), KEYOPT(3)=3 (plane stress with real thickness), KEYOPT(6)=0, NLGEOM OFF. Native2024R1 inventories and analytical controls must verify behavior; only adjacent-release official documentation was retrievable. Homogeneous E1000/nu0.3, parallel and series half-layer nu0 benchmarks, and an equal-material P3 control precede P3 mechanics. No contact is used.

H1 uses65536 quads/66049 nodes; H2 subdivides each pixel into four unchanged-label quads (262144/263169). Image row0 stays at the physical top. Bottom UY=0, top UY=-strain*H, and one bottom-left UX pin; other horizontal motion is free. Solve and save five actual native checkpoints0.1–0.5%. Fit slope and intercept without forcing the origin; an unsolved origin is labeled analytical only.

Before outcomes, register0.1% analytical modulus/reaction/energy/equilibrium tolerances,1e-9mm displacement tolerance,1e-5 relative linear-fit residual, and2% H1/H2 modulus difference. The latter is preliminary sensitivity, not asymptotic convergence or segmentation-resolution qualification. Interpret differences comparable to observed mesh sensitivity as unresolved. Retain element-associated native fields and phase identities; stress percentiles are secondary, pixel-corner maxima exploratory.

Reuse the existing supervised launcher and health monitor, one native job at a time, two cores, no fixed RSS cap,50GiB disk reserve,1800s source/900s readback limits,10800s aggregate native budget and32 native calls maximum. Independently reopen every accepted RST and repeat final-reference extraction. Raw binaries remain under the configured external artifact root; Git retains compact evidence and manifests. No old contact campaign, F1 mechanics, extra seeds, second-axis campaign,3D work or LLM optimization.
''',encoding='utf-8',newline='\n')
    print('Registered',RUN,'protected files',len(protected),'native root',BASE,flush=True)


if __name__=='__main__':register()
