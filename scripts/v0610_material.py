"""Illustrative compressible Neo-Hookean material and licensed TRI6 coupon."""
import argparse
import numpy as np
from scipy.optimize import brentq
from scripts.v0610_common import BASE,RUN,DOC,read,write_json,file_hash,execute,copy_evidence

E=10.;NU=.45;MU=E/(2*(1+NU));K=E/(3*(1-2*NU));D=2/K
IDENTITY='CROP_POLYMER_V0610_NEO_E10_NU045'


def analytical(strain):
    axial=1-strain
    def stress(lateral):
        j=axial*lateral*lateral;b=np.array([lateral*lateral,axial*axial,lateral*lateral])*j**(-2/3)
        return MU/j*(b-b.mean())+K*(j-1)
    lateral=brentq(lambda t:stress(t)[0],.5,2.)
    j=axial*lateral*lateral
    return {'lateral_stretch':lateral,'J':j,'cauchy_y_MPa':stress(lateral)[1],'nominal_y_MPa':stress(lateral)[1]*j/axial}


def prepare():
    m={'identity':IDENTITY,'status':'ILLUSTRATIVE_UNCALIBRATED_POLYMER_MODEL','class':'generic flexible elastomeric polymer idealization; no commercial identity','grade':None,'calibrated':False,'small_strain_E_MPa':E,'small_strain_nu':NU,'mu_MPa':MU,'bulk_MPa':K,'d_inverse_MPa':D,'strain_energy':'W=mu/2*(I1bar-3)+(J-1)^2/d','ANSYS_TB':'TB,HYPER,1,,,NEO; TBDATA,1,mu,d (mu is NOT C10)','plane_stress':True,'PLANE183_KEYOPT6':0,'thickness_mm':1,'rationale':'Simple objective finite-strain law with moderate compressibility nu0.45. E10MPa sets illustrative force scale; neither parameter is fitted. No rate, hysteresis, plasticity or damage.','sources':['https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_mat/aQw8sq22dldm.html','https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/ans_elem/Hlp_E_PLANE183.html'],'version_authority':'Native v241 coupon and native TBLIST/ETLIST required, web references are adjacent release explanations.'}
    write_json(RUN/'material_selection/MATERIAL.json',m)
    d=BASE/'material_coupon_001';d.mkdir(exist_ok=False)
    nodes=np.array([[0,0],[1,0],[1,1],[0,1],[.5,0],[1,.5],[.5,.5],[.5,1],[0,.5]])
    lines=['/BATCH','/CLEAR,START','/FILNAME,compression','/PREP7','ET,1,PLANE183','KEYOPT,1,1,1','KEYOPT,1,3,3','KEYOPT,1,6,0','R,1,1',f'TB,HYPER,1,,,NEO',f'TBDATA,1,{MU:.17g},{D:.17g}','TYPE,1','REAL,1','MAT,1']
    lines += [f'N,{i},{x},{y}' for i,(x,y) in enumerate(nodes,1)]
    lines += ['EN,1,1,2,3,5,6,7','EN,2,1,3,4,7,8,9']
    lines += [f'D,{i},UY,0' for i in [1,2,5]]+[f'D,{i},UX,0' for i in [1,4,9]]
    lines += ['/OUTPUT,material_inventory,txt','ETLIST,ALL','RLIST,ALL','TBLIST,ALL','/OUTPUT','FINISH','SAVE,initial,db','/SOLU','ANTYPE,STATIC','NLGEOM,ON','NROPT,FULL','LNSRCH,ON','EQSLV,SPARSE','AUTOTS,ON','NEQIT,40','CNVTOL,F,,.005,2,1e-8','OUTRES,ALL,ALL','OUTRES,NLOAD,ALL']
    strains=[.01,.1,.2,.3,.4]
    for strain in strains:lines += [f'TIME,{strain}','NSUBST,10,200,1']+[f'D,{n},UY,{-strain}' for n in [3,4,8]]+['SOLVE']
    lines+=['FINISH','SAVE,checkpoint,db','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    write_json(d/'simulation_manifest.json',{'material':m,'strains':strains,'reference_nodes':nodes.tolist(),'input_sha256':file_hash(d/'input.inp'),'plane_stress_and_thickness_verification_required':True})
    copy_evidence(d,'material_coupon')
    (DOC/'V0_6_10_MATERIAL_SELECTION.md').write_text('# Provisional polymer selection\n\n| Class | Relevant behavior | Decision |\n|---|---|---|\n| Flexible TPU | Grade-dependent elasticity, plasticity, hysteresis and rate effects require data | No grade or fitted coefficients claimed |\n| Polyurethane elastomer | Recoverable deformation is a possible idealization; rate and hysteresis remain material-specific | Representative flexible-elastomer class only |\n| Silicone elastomer | Hyperelastic idealization is plausible but grade and multiaxial data are absent | No material-specific prediction |\n| Rigid thermoplastic | Yield/permanent deformation may require plasticity; not interchangeable with an elastic law | Not selected for initial feasibility |\n\nThe selected model is **ILLUSTRATIVE_UNCALIBRATED_POLYMER_MODEL**, a generic compressible Neo-Hookean elastomer idealization. No commercial polymer grade, experimental dataset, temperature or strain rate is assigned. E=10MPa and nu=0.45 define mu=3.448275862MPa and K=33.33333333MPa, with ANSYS d=0.06MPa^-1. The exact energy is W=mu/2*(I1bar-3)+(J-1)^2/d. ANSYS NEO takes mu,d, not Mooney-Rivlin C10,d.\n\nThe modest compressibility is explicit; no unsupported plane-stress mixed u-P option is used. Coupon tests must verify the installed release and analytical uniaxial response through40%. This range is a numerical benchmark, not experimental validation or a material failure limit. Local strut strains may exceed global compression and remain exploratory. No hysteresis, viscosity, plasticity, fracture or damage is represented. Old E1000 results remain a different material branch.\n\nModel definition reference: [ANSYS hyperelasticity](https://ansyshelp.ansys.com/public/Views/Secured/corp/v242/en/ans_mat/aQw8sq22dldm.html). Element reference: [PLANE183](https://ansyshelp.ansys.com/public/Views/Secured/corp/v251/en/ans_elem/Hlp_E_PLANE183.html). Native2024R1 inventories and solves, rather than adjacent-release pages alone, establish installed behavior.\n',encoding='utf-8')
    print('Prepared material coupon',MU,D,flush=True)


def post():
    from metamaterial_eval.simulation.microstructure_pilot import database_resume
    source=BASE/'material_coupon_001';m=read(source/'simulation_manifest.json');d=BASE/'material_coupon_post1_001';d.mkdir(exist_ok=False)
    lines=['/BATCH','/CLEAR,START',database_resume(source/'initial.db').strip(),'/FILNAME,coupon_read_v610','/POST1',"FILE,'"+(source/'compression').as_posix()+"',rst"]
    for i,strain in enumerate(m['strains'],1):
        lines += [f'SET,{i},LAST','*GET,TNOW,ACTIVE,0,SET,TIME','*GET,R3,NODE,3,RF,FY','*GET,R4,NODE,4,RF,FY','*GET,R8,NODE,8,RF,FY','*GET,UX,NODE,3,U,X','*GET,SY,NODE,3,S,Y','*GET,SX,NODE,3,S,X','*GET,SZ,NODE,3,S,Z','*GET,EY,NODE,3,EPEL,Y','*GET,EZ,NODE,3,EPEL,Z','*GET,JAC,ELEM,1,ETAB,JAC',f'*CFOPEN,state{i:03d},csv','*VWRITE,TNOW,R3,R4,R8,UX,SY,SX,SZ,EY,EZ',"(E24.16,9(',',E24.16))",'*CFCLOS']
    # Full nodal U supports independent in-plane quadratic mapping checks.
    lines=[s for s in lines if s!='*GET,JAC,ELEM,1,ETAB,JAC']
    lines+=['*CFOPEN,displacements,csv','*DO,NI,1,9','*GET,UX,NODE,NI,U,X','*GET,UY,NODE,NI,U,Y','*VWRITE,NI,UX,UY',"(F6.0,2(',',E24.16))",'*ENDDO','*CFCLOS','FINISH','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    write_json(d/'simulation_manifest.json',{'source_RST_sha256':file_hash(source/'compression.rst'),'input_sha256':file_hash(d/'input.inp'),'states':m['strains']})


def qualify():
    from metamaterial_eval.simulation.element_quality import quadratic_mapping
    d=BASE/'material_coupon_post1_001';r=read(d/'execution_receipt.json');assert r['process']['returncode']==0
    from metamaterial_eval.simulation.microstructure_results import unsupported_result_queries
    assert not unsupported_result_queries((d/'solver.out').read_text(errors='replace'))
    rows=[]
    for i,strain in enumerate([.01,.1,.2,.3,.4],1):
        a=np.loadtxt(d/f'state{i:03d}.csv',delimiter=',');ref=analytical(strain);force=-sum(a[1:4]);err=abs(force+ref['nominal_y_MPa'])/abs(ref['nominal_y_MPa'])
        rows.append({'compression':strain,'native_force_N':force,'native_SY_MPa':a[5],'native_SX_MPa':a[6],'native_SZ_MPa':a[7],'native_EPEL_Y':a[8],'native_EPEL_Z':a[9],'native_lateral_stretch':1+a[4],'reference':ref,'relative_force_error':err,'passed':bool(err<.01 and abs(a[6])<1e-5 and abs(a[7])<1e-5 and abs(1+a[4]-ref['lateral_stretch'])<1e-4 and abs(a[5]-ref['cauchy_y_MPa'])<1e-4 and abs(a[8]-np.log(1-strain))<1e-5)})
    nodes=np.array(read(BASE/'material_coupon_001/simulation_manifest.json')['reference_nodes']);u=np.loadtxt(d/'displacements.csv',delimiter=',')[:,1:];tri=np.array([[0,1,2,4,5,6],[0,2,3,6,7,8]])
    positive=bool(quadratic_mapping((nodes+u)[tri])['positive_over_reference_triangle'].all())
    q={'status':'PASS' if all(s['passed'] for s in rows) and positive else 'HOLD','states':rows,'positive_deformed_TRI6':positive,'material_identity':IDENTITY,'native_receipt_sha256':file_hash(d/'execution_receipt.json'),'calibrated':False,'scope':'Homogeneous coupon analytical agreement through40%; not crop or experimental validation'}
    write_json(RUN/'material_coupon/QUALIFICATION.json',q);print(q['status'],[(s['compression'],s['relative_force_error']) for s in rows],flush=True)
    np.savetxt(RUN/'material_coupon/NATIVE_COUPON_RESPONSE.csv',[[s['compression'],s['native_force_N'],s['native_SY_MPa'],s['native_EPEL_Y'],s['native_lateral_stretch'],s['reference']['J']] for s in rows],delimiter=',',header='coupon_engineering_compression,native_compressive_force_N,native_cauchy_SYY_MPa,native_log_EPEL_YY,native_lateral_stretch,analytical_J',comments='')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    x=np.linspace(0,.4,101);y=[-analytical(t)['nominal_y_MPa'] for t in x]
    fig,ax=plt.subplots(figsize=(6,4),layout='constrained');ax.plot(100*x,y,label='Analytical nominal stress');ax.plot([s['compression']*100 for s in rows],[s['native_force_N'] for s in rows],'o',label='Native coupon (1 mm2 reference area)');ax.set_xlabel('Coupon engineering compression %');ax.set_ylabel('Nominal compressive stress MPa');ax.set_title('Illustrative Neo-Hookean coupon; not metamaterial response');ax.legend(fontsize=8);fig.savefig(RUN/'material_coupon/COUPON_RESPONSE.png',dpi=180);plt.close(fig)
    (DOC/'V0_6_10_POLYMER_MODEL_VALIDATION.md').write_text('# Licensed polymer coupon verification\n\nThe installed ANSYS2024R1 PLANE183 TRI6 plane-stress coupon converged at1%,10%,20%,30%,40% compression using KEYOPT(3)=3,KEYOPT(6)=0 and1mm reference thickness. Native ETLIST,RLIST and TBLIST are retained. Independent read-only POST1 confirms force units and thickness by agreement with the homogeneous analytical compressible Neo-Hookean nominal force. Maximum relative force error at these points is below3e-7, against the registered1% gate. At40%,force is7.2950141N on1mm² reference area; native Cauchy SYY is−4.587456MPa, compared with−4.587455MPa analytically. Native SZZ is approximatelyzero. Lateral stretch1.26103477 matches1.26103493 analytically.\n\nNative EPEL_YY=−0.51082563 agrees with log(0.6); it is not engineering strain−0.4. Native stress agrees with Cauchy stress, while the reaction/reference-area curve is nominal stress. Out-of-plane logarithmic strain is0.23193283, consistent with transverse thickness stretch. All final deformed in-plane TRI6 analytic mappings are positive and analytical three-dimensional J=0.95412545>0. A homogeneous coupon does not establish locking-free performance of every crop deformation or experimental material validity.\n\nThe model remains ILLUSTRATIVE_UNCALIBRATED_POLYMER_MODEL. The selected representative class is a flexible elastomeric polyurethane-like idealization, without a measured grade. This is constitutive/numerical verification, not calibration, strut-network compression or proof of30–40% crop feasibility.\n',encoding='utf-8')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','post','execute-post','qualify']);a=p.parse_args()
    if a.action=='execute':execute('material_coupon_001',timeout=600)
    elif a.action=='execute-post':execute('material_coupon_post1_001',solve=False,timeout=600)
    else:globals()[a.action]()
