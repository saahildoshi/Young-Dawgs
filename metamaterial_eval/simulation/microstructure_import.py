"""Streaming N/EN transfer and exhaustive actual solver-written CDB inventory."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import re
import numpy as np
from .config import CompressionConfig
from .mesh_artifacts import artifact_root,resolve_manifest
from .mesh_generation import Mesh
from .mesh_validation import validate_mesh,feature_resolution
from .geometry_adapter import authenticate_fixture
from .reporting import write_json
from .solver_execution import discover_solver,file_hash,solver_release
from .windows_ansys import bounded_run


def component(stream,name,ids,entity='NODE'):
    ids=np.unique(np.asarray(ids,dtype=np.int64))
    if not len(ids):raise ValueError('Empty component '+name)
    stream.write(f'CMBLOCK,{name},{entity},{len(ids)}\n(8i10)\n')
    for offset in range(0,len(ids),8):stream.write(''.join(f'{n:10d}' for n in ids[offset:offset+8])+'\n')


def prepare_import(mesh,directory,config=CompressionConfig()):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    with (directory/'import.inp').open('w',buffering=1024**2) as f:
        f.write('/BATCH\n/CLEAR,START\n/FILNAME,model\n/NOPR\n/PREP7\nET,1,PLANE183\nKEYOPT,1,1,1\nKEYOPT,1,3,3\n'
                f'R,1,{config.thickness:.17g}\nMP,EX,1,{config.young_modulus:.17g}\nMP,PRXY,1,{config.poisson_ratio:.17g}\n'
                'MP,MU,1,0\nTYPE,1\nREAL,1\nMAT,1\n')
        # At most 10k temporary records, never a list of millions of strings.
        for offset in range(0,len(mesh.nodes),10000):
            f.writelines(f'N,{i+1},{x:.17g},{y:.17g},0\n' for i,(x,y) in enumerate(mesh.nodes[offset:offset+10000],offset))
        for offset in range(0,len(mesh.triangles),10000):
            f.writelines('EN,'+str(i+1)+','+','.join(str(int(n)+1) for n in tri)+'\n'
                         for i,tri in enumerate(mesh.triangles[offset:offset+10000],offset))
        f.write('ESEL,S,TYPE,,1\nCM,SPECIMEN,ELEM\nALLSEL,ALL\n')
        for group in sorted(set(mesh.boundary_groups)):
            component(f,group.upper()+'_FACE',np.unique(mesh.boundary[mesh.boundary_groups==group])+1)
        f.write('ALLSEL,ALL\nCHECK\n/OUTPUT,inventory,txt\n/GOPR\nETLIST,ALL\nRLIST,ALL\nMPLIST,ALL\nCMLIST,ALL\n'
                '*GET,NN,NODE,0,COUNT\n*GET,NE,ELEM,0,COUNT\n*VWRITE,NN,NE\n'
                "('SPECIMEN_COUNTS ',F16.0,1X,F16.0)\n/OUTPUT\n/NOPR\nCDWRITE,DB,imported,cdb\nSAVE,specimen,db\nFINISH\n/EXIT,NOSAVE\n")
    return file_hash(directory/'import.inp')


def launch(directory,*,timeout=900,rss_limit=12*1024**3,min_available_ram=0):
    directory=Path(directory).resolve()
    solver=discover_solver()
    if solver is None:raise RuntimeError('MAPDL not available')
    receipt=bounded_run([str(solver),'-b','-smp','-np','1','-m','4096','-j','model',
                         '-i','import.inp','-o','solver.out'],directory,prepared=True,
                        timeout=timeout,rss_limit=rss_limit,min_disk_free=20*1024**3,min_available_ram=min_available_ram)
    log=(directory/'solver.out').read_text(errors='replace') if (directory/'solver.out').exists() else ''
    errors=bool(re.search(r'\*\*\*\s*(?:ERROR|FATAL)\s*\*\*\*',log,re.I))
    status='IMPORT_PROCESS_COMPLETE_PENDING_INVENTORY' if receipt['returncode']==0 and not errors and (directory/'imported.cdb').is_file() else 'IMPORT_FAILED'
    result={'status':status,'solver_version':solver_release(log),'input_sha256':file_hash(directory/'import.inp'),
            'process_receipt_sha256':file_hash(directory/'process_receipt.json'),'process':receipt,
            'warnings':re.findall(r'\*\*\* WARNING \*\*\*[^\n]*\n([^\n]+)',log)}
    write_json(directory/'import_receipt.json',result)
    return result


def read_cdb(path,node_count,element_count):
    """Parse documented solver-generated fixed-width NBLOCK/EBLOCK/CMBLOCK.

    Restrict to the observed 6-node PLANE183 archive; reject unsupported variants.
    This reader is NOT a general CDB importer.
    """
    nodes=np.empty((node_count,2));tri=np.empty((element_count,6),dtype=np.int64)
    attributes=np.empty((element_count,3),dtype=np.int64);components={};ni=ei=0
    with Path(path).open() as f:
        for line in f:
            if line.startswith('NBLOCK'):
                if next(f).strip().lower()!='(3i9,6e21.13e3)':raise ValueError('Unsupported NBLOCK format')
                for line in f:
                    if line.startswith('N,'):break
                    idx=int(line[:9]);values=[float(line[i:i+21].strip() or 0) for i in range(27,90,21)]
                    if idx!=ni+1 or ni>=node_count or values[2]!=0:raise ValueError('Solver node ID/count/planarity mismatch')
                    nodes[ni]=values[:2];ni+=1
            elif line.startswith('EBLOCK'):
                if next(f).strip().lower()!='(19i10)':raise ValueError('Unsupported EBLOCK format')
                for line in f:
                    if line.strip()=='-1':break
                    values=[int(line[i:i+10]) for i in range(0,len(line.rstrip()),10)]
                    if len(values)!=17 or values[8]!=6 or values[10]!=ei+1 or ei>=element_count:
                        raise ValueError('Solver element ID/count/TRI6 mismatch')
                    attributes[ei]=values[:3];tri[ei]=np.array(values[11:17])-1;ei+=1
            elif line.startswith('CMBLOCK'):
                fields=line.split('!')[0].strip().split(',');name,entity,count=fields[1],fields[2],int(fields[3])
                if next(f).strip().lower()!='(8i10)':raise ValueError('Unsupported component format')
                coded=[]
                while len(coded)<count:
                    row=next(f).rstrip();coded.extend(int(row[i:i+10]) for i in range(0,len(row),10))
                expanded=[]
                for value in coded:
                    if value<0:
                        if not expanded:raise ValueError('Invalid compressed component range')
                        expanded.extend(range(expanded[-1]+1,-value+1))
                    else:expanded.append(value)
                components[name]={'entity':entity,'ids':np.asarray(expanded,dtype=np.int64)}
    if (ni,ei)!=(node_count,element_count):raise ValueError('Incomplete solver archive')
    return nodes,tri,attributes,components


def verify(directory,mesh,geometry,config,provenance,output):
    directory,output=Path(directory),Path(output);output.mkdir(parents=True,exist_ok=False)
    receipt=json.loads((directory/'import_receipt.json').read_text())
    if receipt['status']!='IMPORT_PROCESS_COMPLETE_PENDING_INVENTORY' or receipt['solver_version']!='2024 R1':
        raise ValueError('Unsuccessful or incompatible actual import')
    if file_hash(directory/'imported.cdb')!=receipt['process']['artifacts']['imported.cdb']['sha256']:
        raise ValueError('Changed actual import archive')
    nodes,tri,attributes,components=read_cdb(directory/'imported.cdb',len(mesh.nodes),len(mesh.triangles))
    maxerr=float(np.max(np.abs(nodes-mesh.nodes)))
    if maxerr>1e-11 or not np.array_equal(tri,mesh.triangles):raise ValueError('Actual node coordinates/TRI6 order differ')
    if not np.all(attributes==1):raise ValueError('Actual material/type/real attributes differ')
    for group in sorted(set(mesh.boundary_groups)):
        expected=np.unique(mesh.boundary[mesh.boundary_groups==group])+1
        actual=components.get(group.upper()+'_FACE',{})
        if actual.get('entity')!='NODE' or not np.array_equal(actual.get('ids'),expected):
            raise ValueError('Actual boundary component differs: '+group)
    if not np.array_equal(components['SPECIMEN']['ids'],np.arange(1,len(tri)+1)):raise ValueError('Specimen component incomplete')
    inventory=(directory/'inventory.txt').read_text()
    if not re.search(r'KEYOPT\( 1- 6\)=\s+1\s+0\s+3',inventory):raise ValueError('Actual PLANE183 options differ')
    for token in ['PLANE183','1000.000','0.3000000','REAL CONSTANT SET']:
        if token not in inventory:raise ValueError('Actual material/type inventory incomplete')
    constants=re.search(r'REAL CONSTANT SET\s+1\s+ITEMS\s+1 TO\s+6\s+([\d.Ee+\-]+)',inventory)
    if not constants or not np.isclose(float(constants[1]),config.thickness,rtol=0,atol=1e-12):
        raise ValueError('Actual thickness differs')
    actual_mesh=Mesh(nodes,tri,mesh.boundary,mesh.boundary_groups)
    quality,_=validate_mesh(actual_mesh,geometry,config)
    features=feature_resolution(actual_mesh,provenance['source_only_solid_probes'],config)
    result={'status':'ANSYS_IMPORT_PASS' if quality['accepted'] and features['accepted'] else 'ANSYS_IMPORT_HOLD',
            'actual_nodes':len(nodes),'actual_PLANE183_TRI6':len(tri),'coordinate_max_error_mm':maxerr,
            'connectivity':'EXHAUSTIVE_ALL_SIX_NODE_IDS_EQUAL','attributes':'EXHAUSTIVE_ALL_TYPE_MAT_REAL_EQUAL_1',
            'components':'EXHAUSTIVE_ALL_NODE_AND_SPECIMEN_MEMBERSHIPS_EQUAL',
            'pores_from_imported_connectivity':quality['holes'],'components_from_imported_connectivity':quality['components'],
            'bbox_mm':[nodes.min(axis=0).tolist(),nodes.max(axis=0).tolist()],
            'actual_mesh_validation':quality,'actual_feature_validation':features,
            'solver_archive_sha256':file_hash(directory/'imported.cdb'),
            'solver_database_sha256':file_hash(directory/'specimen.db'),'import_receipt_sha256':file_hash(directory/'import_receipt.json'),
            'scientific_scope':'import-only; no force or deformation result'}
    write_json(output/'import_validation.json',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();mesh,manifest,_=resolve_manifest(a.manifest)
    cfg={k:manifest['settings']['config'][k] for k in CompressionConfig.__dataclass_fields__};cfg['strains']=tuple(cfg['strains']);config=CompressionConfig(**cfg)
    geometry,_,provenance=authenticate_fixture(Path(__file__).resolve().parents[2],config)
    directory=artifact_root()/'solver/v063/import_001'
    prepare_import(mesh,directory,config);print('Streaming input written; executing real import',flush=True)
    result=launch(directory);a.output.mkdir(parents=True,exist_ok=False)
    write_json(a.output/'import_execution.json',result)
    print(result['status'],flush=True)
    if result['status']=='IMPORT_PROCESS_COMPLETE_PENDING_INVENTORY':
        result=verify(directory,mesh,geometry,config,provenance,a.output/'validation')
        print(result['status'],result['actual_nodes'],result['actual_PLANE183_TRI6'],flush=True)


if __name__=='__main__':main()
