"""Actual connected C-cell self-contact versus disabled crossing control."""
from dataclasses import replace
import argparse
from pathlib import Path
import numpy as np
import shapely
from metamaterial_eval.simulation.config import CompressionConfig
from metamaterial_eval.simulation.mesh_generation import generate_mesh,save_mesh
from metamaterial_eval.simulation.mesh_remediation import POLICY_B
from metamaterial_eval.simulation.microstructure_import import prepare_import,component
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.reporting import write_json,mesh_hash
from scripts.v064_small_study import direct_post
from scripts.v066_restart import REPO,RUN,BASE,load,compact


def post_commands(mesh):
    lines=direct_post({'specimen_nodes':len(mesh.nodes)},.4)
    lines+=['ESEL,S,REAL,,0','ESEL,R,ENAME,,172','*GET,NC,ELEM,0,COUNT',
        '*CFOPEN,internal_contact,csv','*VWRITE',"('element,status,pressure_i,pressure_j,gap_i,gap_j,internal_FY,i_node')",'EID=0',
        '*DO,KK,1,NC','EID=ELNEXT(EID)','*GET,STV,ELEM,EID,NMISC,19','*GET,PI,ELEM,EID,SMISC,1',
        '*GET,PJ,ELEM,EID,SMISC,2','*GET,GI,ELEM,EID,NMISC,5','*GET,GJ,ELEM,EID,NMISC,6',
        '*GET,FYV,ELEM,EID,NMISC,22','*GET,INV,ELEM,EID,NODE,1','*VWRITE,EID,STV,PI,PJ,GI,GJ,FYV,INV',"(F12.0,',',F4.0,5(',',E24.16),',',F12.0)",'*ENDDO','*CFCLOS','ALLSEL,ALL']
    return lines


def main(short_gap=False):
    revision='002' if short_gap else '001';gap=.01 if short_gap else .1
    height=.3+gap;travel=.02 if short_gap else .16;strain=travel/height
    protocol={'fixture':f'Connected C-cell, two0.15mm arms separated by{gap}mm gap,0.12mm left bridge',
        'geometry':f'union rectangles [0,0,1,.15], [0,{.15+gap},1,{height}], [0,0,.12,{height}]',
        'general_contact':'GCGEN NEW,42,0,PART,SELECT; keep only opposed exposed inner arms; GCDEF SYMM ALL SELF',
        'interface':'Frictionless pure penalty, updating default general-contact stiffness, FKN100/FTOLN-1e-5',
        'constraints':f'Bottom UY0, upper UY-{travel}mm(total{strain} height), one bottom-left UX anchor',
        'enabled_disabled_comparison':True,'scope':'Small diagnostic fixture, not Design9 response',
        'acceptance':'Actual active general-contact elements, nonzero forces, pressure, native pen<=1e-5, signed support balance<=1%, positive deformed mappings; disabled may cross',
        'revision_reason':'002 closes a shorter initial gap without crushing the connecting bridge; fixes actual /FILNAME to compression; keeps original001 failure and unchanged acceptance gates' if short_gap else 'Original004 fixture'}
    write_json(RUN/('protocol/INTERNAL_CONTACT_FIXTURE_006.json' if short_gap else 'protocol/INTERNAL_CONTACT_FIXTURE_004.json'),protocol)
    cfg=replace(CompressionConfig(),width=1,height=height,boundary_size=.015,bulk_size=.025)
    geometry=shapely.union_all([shapely.box(0,0,1,.15),shapely.box(0,.15+gap,1,height),shapely.box(0,0,.12,height)])
    mesh=generate_mesh(geometry,cfg,policy=POLICY_B)
    local=BASE/('internal_fixture_geometry_'+revision);local.mkdir(parents=True,exist_ok=False);save_mesh(mesh,local/'mesh.npz')
    source_name='source_002.wkt' if short_gap else 'source.wkt';manifest_name='fixture_manifest_002.json' if short_gap else 'fixture_manifest.json'
    (RUN/'internal_contact'/source_name).write_text(geometry.wkt)
    write_json(RUN/'internal_contact'/manifest_name,{'nodes':len(mesh.nodes),'TRI6':len(mesh.triangles),'mesh_semantic_sha256':mesh_hash(mesh),'geometry_sha256':file_hash(RUN/'internal_contact'/source_name),'config':cfg.manifest(),'scope':'Distinct connected synthetic self-contact fixture'})
    lower=np.flatnonzero(np.isclose(mesh.nodes[:,1],.15)&(mesh.nodes[:,0]>=.12-1e-10))+1
    upper=np.flatnonzero(np.isclose(mesh.nodes[:,1],.15+gap)&(mesh.nodes[:,0]>=.12-1e-10))+1
    bottoms=np.unique(mesh.boundary[mesh.boundary_groups=='bottom']);anchor=int(bottoms[np.argmin(mesh.nodes[bottoms,0])])+1
    for enabled in [False,True]:
        directory=BASE/(('internal_fixture_enabled_' if enabled else 'internal_fixture_disabled_')+revision)
        prepare_import(mesh,directory,cfg)
        source=(directory/'import.inp').read_text();source=source[:source.index('ALLSEL,ALL\nCHECK')]
        if short_gap:source=source.replace('/FILNAME,model','/FILNAME,compression',1)
        with (directory/'input.inp').open('w',encoding='utf-8') as f:
            f.write(source)
            component(f,'CORNERS',np.unique(mesh.triangles[:,:3])+1)
            component(f,'INNER_LOW',lower);component(f,'INNER_UP',upper)
            f.write('/GOPR\n')
            if enabled:
                f.write('ESEL,S,TYPE,,1\nGCGEN,NEW,42,0,PART,SELECT\nGCGEN,SELECT\nCM,ALL_GC,ELEM\nALLSEL,ALL\n'
                    'CMSEL,S,INNER_LOW\nCMSEL,A,INNER_UP\nESLN,S,1\nESEL,R,REAL,,0\nESEL,R,ENAME,,172\nCM,INTERNAL_GC,ELEM\n'
                    'CMSEL,S,ALL_GC\nCMSEL,U,INTERNAL_GC\nEDELE,ALL\nALLSEL,ALL\nR,100,,,100,-1e-5\n'
                    'GCDEF,SYMM,ALL,SELF,1,100\n/OUTPUT,gc_inventory,txt\nGCDEF,LIST\nETLIST,ALL\nELIST,ALL\n/OUTPUT\n')
            f.write(f'CMSEL,S,BOTTOM_FACE\nD,ALL,UY,0\nALLSEL,ALL\nD,{anchor},UX,0\n'
                f'CMSEL,S,TOP_FACE\nD,ALL,UY,{-travel:.17g}\nALLSEL,ALL\nFINISH\n/SOLU\nANTYPE,STATIC\nNLGEOM,ON\n'
                'EQSLV,SPARSE\nNROPT,FULL\nAUTOTS,ON\nNSUBST,20,1000,10\nNEQIT,40\nLNSRCH,ON\nCNVTOL,F,,.005,2,1e-8\n'
                f'OUTRES,ALL,ALL\nRESCONTROL,DEFINE,ALL,ALL,-1,,3\nNLDIAG,CONT,ITER\nTIME,{strain:.17g}\nSOLVE\n')
            f.write('\n'.join(post_commands(mesh)))
            f.write('\nFINISH\nSAVE,checkpoint,db,,MODEL\n/EXIT,NOSAVE\n')
        write_json(directory/'simulation_manifest.json',{'model':{'specimen_nodes':len(mesh.nodes),'specimen_TRI6':len(mesh.triangles),'config':cfg.manifest()},'internal_contact':enabled,'input_sha256':file_hash(directory/'input.inp'),'mesh_semantic_sha256':mesh_hash(mesh),'target_strain':strain})
        r=run_progressive(directory,timeout=300,no_progress_seconds=180,cores=2)
        compact(directory,RUN/'internal_contact'/directory.name)
        for name in ['direct_history.csv','direct_displacements.csv','direct_stress.csv','internal_contact.csv','gc_inventory.txt']:
            path=directory/name
            if path.exists() and path.stat().st_size<1024**2:
                if path.suffix=='.txt':(RUN/'internal_contact'/directory.name/name).write_text('\n'.join(s.rstrip() for s in path.read_text(errors='replace').splitlines())+'\n',encoding='utf-8')
                else:(RUN/'internal_contact'/directory.name/name).write_bytes(path.read_bytes())
        print(directory.name,r['status'],r['process']['returncode'],r['converged_steps'][-1:] if r['converged_steps'] else [],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--short-gap',action='store_true');a=p.parse_args();main(a.short_gap)
