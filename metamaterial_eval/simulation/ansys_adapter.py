"""Reviewable MAPDL input templates; solver parsing/physics require real ANSYS.

TRI6 order and PLANE183 KEYOPT(1)=1 must be checked in the target release.
Local linting proves transfer consistency only, never solver acceptance.
"""
from pathlib import Path
import numpy as np
from .contact_setup import platen_plan
from .reporting import mesh_hash, write_json


def component(name, ids):
    ids=sorted(set(int(i) for i in ids))
    if not ids:raise ValueError(f'Empty component {name}')
    lines=['NSEL,NONE']
    lines.extend(f'NSEL,A,NODE,,{i}' for i in ids)
    return lines+[f'CM,{name},NODE','ALLSEL,ALL']


def build_deck(mesh, config, *, contact=True, purpose='rectangle_benchmark'):
    if purpose not in ('rectangle_benchmark','microstructure_pilot'):
        raise ValueError('Unsupported solver purpose')
    plan=platen_plan(mesh,config)
    lines=['! DRAFT_UNVERIFIED: verify element/contact settings in installed ANSYS release',
           '! Actual 2D, provisional mm-N-MPa; quasi-static pseudo-time is not seconds',
           '/BATCH','/CLEAR,START','/FILNAME,compression','/TITLE,Young Dawgs v0.6 2D compression',
           '/PREP7','ET,1,PLANE183','KEYOPT,1,1,1',
           f'KEYOPT,1,3,{3 if config.mode=="plane_stress" else 2}',
           f'R,1,{config.thickness:.16g}', f'MP,EX,1,{config.young_modulus:.16g}',
           f'MP,PRXY,1,{config.poisson_ratio:.16g}','MP,MU,1,0','TYPE,1','REAL,1','MAT,1']
    for n,(x,y) in enumerate(mesh.nodes,1):lines.append(f'N,{n},{x:.16g},{y:.16g},0')
    for e,tri in enumerate(mesh.triangles,1):lines.append('EN,'+str(e)+','+','.join(str(int(n)+1) for n in tri))
    lines+=['ESEL,S,TYPE,,1','CM,SPECIMEN,ELEM','ALLSEL,ALL']
    for group in ['top','bottom','external','pore']:
        edges=mesh.boundary[mesh.boundary_groups==group]
        if len(edges):lines+=component(group.upper()+'_FACE',np.unique(edges)+1)
    count=len(mesh.nodes);eid=len(mesh.triangles)
    controls={}
    bottom=np.asarray(plan['bottom']['nodes'])
    anchor=int(bottom[np.argmin(mesh.nodes[bottom,0])])+1
    if contact:
        lines+=['ET,2,TARGE169','KEYOPT,2,2,1','ET,3,CONTA172','KEYOPT,3,2,0',
                'KEYOPT,3,4,0','KEYOPT,3,5,0','KEYOPT,3,12,0',
                '! Standard frictionless separation, finite sliding; no weak springs or damping',
                '! Review contact force/thickness scaling and actual defaults in target release']
        for offset,group in enumerate(['bottom','top']):
            real=offset+2;y=0 if group=='bottom' else config.height
            left,right,pilot=count+3*offset+1,count+3*offset+2,count+3*offset+3
            controls[group]=pilot
            lines += [f'R,{real}',f'N,{left},{-config.width*.05:.16g},{y:.16g},0',
                      f'N,{right},{config.width*1.05:.16g},{y:.16g},0',
                      f'N,{pilot},{config.width/2:.16g},{y:.16g},0',
                      'TYPE,2',f'REAL,{real}','TSHAP,LINE']
            # Right-hand normals: bottom right->left points upward; top left->right downward.
            eid+=1
            a,b=(right,left) if group=='bottom' else (left,right)
            lines.append(f'EN,{eid},{a},{b}')
            lines+=['TSHAP,PILO'];eid+=1;lines.append(f'EN,{eid},{pilot}')
            lines+=['TYPE,3',f'REAL,{real}','MAT,1']
            contact_ids=[]
            for a,b,mid in plan[group]['edges']:
                eid+=1;contact_ids.append(eid)
                lines.append(f'EN,{eid},{a+1},{b+1},{mid+1}')
            lines+=['ESEL,NONE']+[f'ESEL,A,ELEM,,{i}' for i in contact_ids]
            lines += [f'CM,{group.upper()}_CONTACT,ELEM','ALLSEL,ALL']
            lines+=component(group.upper()+'_PILOT',[pilot])
        lines += [f'D,{controls["bottom"]},UX,0',f'D,{controls["bottom"]},UY,0',
                  f'D,{controls["bottom"]},ROTZ,0', f'D,{controls["top"]},UX,0',
                  f'D,{controls["top"]},ROTZ,0',f'D,{anchor},UX,0']
    else:
        lines+=['CMSEL,S,BOTTOM_FACE','D,ALL,UY,0','ALLSEL,ALL',f'D,{anchor},UX,0']
    lines+=['ALLSEL,ALL','/OUTPUT,model_inventory,txt','ETLIST,ALL','RLIST,ALL','MPLIST,ALL','CMLIST,ALL',
            '*GET,NNCHK,NODE,0,COUNT','*GET,NECHK,ELEM,0,COUNT',
            '*VWRITE,NNCHK,NECHK',"('TRANSFER_COUNTS ',F16.0,1X,F16.0)",
            'NLIST,ALL','ELIST,ALL','DLIST,ALL','/OUTPUT','FINISH',
            '/SOLU','ANTYPE,STATIC','NLGEOM,ON','NROPT,FULL','AUTOTS,ON','NSUBST,10,100,1',
            'NEQIT,50','LNSRCH,ON','CNVTOL,F,,0.005,2','OUTRES,ALL,ALL']
    if contact:lines+=['CNCHECK,DETAIL']
    for strain in config.strains:
        lines.append(f'TIME,{strain:.16g}')
        displacement=-strain*config.height
        if contact:lines.append(f'D,{controls["top"]},UY,{displacement:.16g}')
        else:lines+=['CMSEL,S,TOP_FACE',f'D,ALL,UY,{displacement:.16g}','ALLSEL,ALL']
        lines.append('SOLVE')
    lines+=['FINISH','/POST1','SET,LIST','! Export converged result sets only; raw logs remain authoritative',
            'SET,LAST','*GET,NSETS,ACTIVE,0,SET,NSET','*CFOPEN,history,csv',
            '*VWRITE',"('set,pseudo_time,load_step,substep,top_uy_mm,upper_rf_y_N,lower_rf_y_N')",'SET,FIRST',
            '*DO,JJ,1,NSETS','*GET,TNOW,ACTIVE,0,SET,TIME',
            '*GET,LSTEP,ACTIVE,0,SET,LSTP','*GET,SSTEP,ACTIVE,0,SET,SBST']
    if contact:
        lines += [f'*GET,UYTOP,NODE,{controls["top"]},U,Y',
                  f'*GET,RFTOP,NODE,{controls["top"]},RF,FY',f'*GET,RFBOT,NODE,{controls["bottom"]},RF,FY']
    else:
        # Aggregate reactions using FSUM would include element forces; sum constrained nodal RF directly.
        lines += ['CMSEL,S,TOP_FACE','*GET,NCOUNT,NODE,0,COUNT','NODEID=0','RFTOP=0','UYTOP=0',
                  '*DO,KK,1,NCOUNT','NODEID=NDNEXT(NODEID)','*GET,TMP,NODE,NODEID,RF,FY','RFTOP=RFTOP+TMP',
                  '*GET,UYTOP,NODE,NODEID,U,Y','*ENDDO','CMSEL,S,BOTTOM_FACE','*GET,NCOUNT,NODE,0,COUNT',
                  'NODEID=0','RFBOT=0','*DO,KK,1,NCOUNT','NODEID=NDNEXT(NODEID)',
                  '*GET,TMP,NODE,NODEID,RF,FY','RFBOT=RFBOT+TMP','*ENDDO','ALLSEL,ALL']
    lines += ['*VWRITE,JJ,TNOW,LSTEP,SSTEP,UYTOP,RFTOP,RFBOT',"(F8.0,',',E16.8,',',F8.0,',',F8.0,3(',',E16.8))",
              '*IF,JJ,LT,NSETS,THEN','SET,NEXT','*ENDIF','*ENDDO','*CFCLOS',
              '/INPUT,extract_fields,mac',
              'FINISH','/EXIT,NOSAVE']
    manifest={'schema':'young-dawgs-ansys-input-v0.6','purpose':purpose,'status':'DRAFT_UNVERIFIED',
              'ansys_version':None,'element_documentation_review':'PENDING_ACTUAL_RELEASE',
              'mesh_sha256':mesh_hash(mesh),'specimen_nodes':len(mesh.nodes),'solid_elements':len(mesh.triangles),
              'total_nodes':len(mesh.nodes)+(6 if contact else 0),'total_elements':eid,
              'config':config.manifest(),'platen_contact':contact,'contact_plan':plan if contact else None,
              'internal_self_contact':'UNQUALIFIED_NOT_CONFIGURED','controls':controls,
              'boundary_groups':{g:np.unique(mesh.boundary[mesh.boundary_groups==g]).tolist() for g in set(mesh.boundary_groups)},
              'initial_gaps_mm':{'top':0,'bottom':0},'solver_execution':'NOT_EXECUTED'}
    return '\n'.join(lines)+'\n',manifest


def lint_transfer(deck, mesh, config, *, contact=True):
    """Parse only our emitted mesh records and validate exact transfer inventory.

    This is NOT an APDL parser, command validation or ANSYS import evidence.
    """
    nodes={};elements={};mode=None;material={}
    for line in deck.splitlines():
        fields=line.split(',');command=fields[0].upper()
        if command=='N':nodes[int(fields[1])]=[float(v) for v in fields[2:4]]
        elif command=='EN':elements[int(fields[1])]=[int(v) for v in fields[2:]]
        elif fields[:3]==['KEYOPT','1','3']:mode=int(fields[3])
        elif command=='MP' and fields[1] in ['EX','PRXY']:material[fields[1]]=float(fields[3])
    if len(nodes)!=len(mesh.nodes)+(6 if contact else 0):raise ValueError('Node transfer count mismatch')
    if not np.allclose([nodes[n] for n in range(1,len(mesh.nodes)+1)],mesh.nodes,atol=1e-13,rtol=1e-14):
        raise ValueError('Node coordinate transfer mismatch')
    if [elements[n] for n in range(1,len(mesh.triangles)+1)]!=(mesh.triangles+1).tolist():
        raise ValueError('Solid connectivity transfer mismatch')
    if mode!=(3 if config.mode=='plane_stress' else 2) or material!={'EX':config.young_modulus,'PRXY':config.poisson_ratio}:
        raise ValueError('Material/formulation mismatch')
    if contact:
        transferred_faces={tuple(v) for v in elements.values() if len(v)==3}
        for token in ['ET,2,TARGE169','ET,3,CONTA172','CM,TOP_CONTACT,ELEM','CM,BOTTOM_CONTACT,ELEM','TSHAP,PILO']:
            if token not in deck:raise ValueError(f'Missing contact definition: {token}')
        for group in ['top','bottom']:
            for edge in mesh.boundary[mesh.boundary_groups==group]:
                if tuple((edge+1).tolist()) not in transferred_faces:
                    raise ValueError('Missing transferred contact face')
    return {'transfer_lint':'PASS_LOCAL_RECORD_ROUNDTRIP','ansys_import':'NOT_VERIFIED',
            'syntax_validation':'NOT_VERIFIED_NO_ANSYS','material_assignment':'PREPARED_NOT_SOLVER_VERIFIED'}


def write_input(folder, mesh, config, *, contact=True, purpose='rectangle_benchmark'):
    folder=Path(folder)
    folder.mkdir(parents=True,exist_ok=False)
    deck,manifest=build_deck(mesh,config,contact=contact,purpose=purpose)
    lint=lint_transfer(deck,mesh,config,contact=contact)
    (folder/'compression.inp').write_text(deck)
    from .result_extraction import field_export_macro
    (folder/'extract_fields.mac').write_text(field_export_macro(len(mesh.nodes),contact))
    write_json(folder/'input_manifest.json',manifest)
    write_json(folder/'transfer_lint.json',lint)
    return manifest


def prepare_pilot_input(mesh_level, output, root):
    """Reauthenticate all inputs and gates before preparing a pilot input bundle."""
    import json
    from .config import CompressionConfig
    from .geometry_adapter import authenticate_fixture
    from .mesh_generation import Mesh
    from .mesh_validation import validate_mesh,feature_resolution
    source=Path(mesh_level)
    if (source.parent/'FAILURE.json').exists():
        raise RuntimeError('Pilot blocked by recorded mesh-study failure; preserve it and register a new protocol/run')
    stored=json.loads((source/'simulation_manifest.json').read_text())
    fields={k:stored['config'][k] for k in CompressionConfig.__dataclass_fields__}
    fields['strains']=tuple(fields['strains']);config=CompressionConfig(**fields)
    z=np.load(source/'generated/mesh.npz',allow_pickle=False)
    mesh=Mesh(z['nodes'],z['triangles'],z['boundary'],z['boundary_groups'])
    if mesh_hash(mesh)!=stored['mesh_sha256']:raise ValueError('Persisted mesh hash mismatch')
    geometry,_,provenance=authenticate_fixture(root,config)
    if provenance['geometry_sha256']!=stored['geometry_sha256']:raise ValueError('Mesh source geometry mismatch')
    quality,_=validate_mesh(mesh,geometry,config)
    features=feature_resolution(mesh,provenance['source_only_solid_probes'],config)
    if not quality['accepted'] or not features['accepted']:
        raise ValueError('Pilot input blocked by mesh or sampled narrow-feature gate')
    manifest=write_input(output,mesh,config,purpose='microstructure_pilot')
    manifest['geometry_provenance']=provenance
    manifest['execution_gate']='BLOCKED_UNTIL_REAL_RECTANGLE_IMPORT_MATERIAL_CONTACT_ACCEPTANCE'
    write_json(Path(output)/'input_manifest.json',manifest)
    return manifest
