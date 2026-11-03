"""Independent two-sided structural force proof at engaged GC interfaces."""
import argparse
from collections import defaultdict,deque
import numpy as np

from metamaterial_eval.simulation.microstructure_import import component
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.general_contact_results import read_table
from metamaterial_eval.simulation.general_contact_output import GC_COLUMNS
from metamaterial_eval.simulation.microstructure_results import numeric
from scripts.v068_common import BASE,RUN,read,write_json,file_hash,copy_evidence


def prepare(source_name):
    source=BASE/source_name;post=BASE/(source_name+'_post1_last')
    sr=read(source/'execution_receipt.json');pr=read(post/'execution_receipt.json')
    pm=read(post/'simulation_manifest.json');setup=read(RUN/'track_B_contact_fixture/SETUP_QUALIFICATION.json')
    if (pr['process']['returncode']!=0 or file_hash(source/'compression.rst')!=pm['source_RST_sha256'] or
        pm['source_execution_receipt_sha256']!=file_hash(source/'execution_receipt.json') or
        file_hash(BASE/'track_B_setup_001/contact_model.db')!=setup['native_database_sha256']):
        raise ValueError('Invalid native source for interface force proof')
    if len(pm['states'])!=1:raise ValueError('Interface force proof requires one selected state')
    state=pm['states'][0];key=(state['load_step'],state['substep'])
    if list(key) not in sr['converged_steps']:raise ValueError('Selected state not native converged')
    prefix='stage001'
    for name in [prefix+'_gc_status.csv',prefix+'_gc_fields.csv']:
        if file_hash(post/name)!=pr['process']['artifacts'][name]['sha256']:
            raise ValueError('Changed native general-contact fields')
    topology=read_table(BASE/'track_B_setup_001/gc_topology.csv',
                        ['element','i','j','mid','type','section']).astype(np.int64)
    by_eid={int(r[0]):r[1:4] for r in topology}
    status=read_table(post/(prefix+'_gc_status.csv'),['element','status'])
    fields=read_table(post/(prefix+'_gc_fields.csv'),GC_COLUMNS)
    closed={int(r[0]) for r in fields if r[1]>=2 and max(r[2:5])>0}
    if not closed:raise ValueError('No pressure-bearing closed interface to prove')
    graph=defaultdict(set)
    for r in fields:
        if int(r[0]) not in closed:continue
        for pressure,target in [(r[2],r[8]),(r[3],r[9])]:
            if pressure>0 and target>0:
                target=int(target)
                if target not in by_eid or target==int(r[0]):raise ValueError('Invalid native target facet')
                graph[int(r[0])].add(target);graph[target].add(int(r[0]))
    if not closed.issubset(graph):raise ValueError('Closed skin lacks positive-pressure native target link')
    patches=[];visited=set()
    for start in sorted(graph):
        if start in visited:continue
        queue=deque([start]);colors={start:0};component_edges=[]
        while queue:
            current=queue.popleft();visited.add(current);component_edges.append(current)
            for neighbor in graph[current]:
                if neighbor in colors:
                    if colors[neighbor]==colors[current]:raise ValueError('Non-bipartite contact interface cannot be separated')
                else:colors[neighbor]=1-colors[current];queue.append(neighbor)
        ids=[sorted(set(int(n) for e,c in colors.items() if c==side for n in by_eid[e])) for side in [0,1]]
        if not all(ids) or set(ids[0])&set(ids[1]):raise ValueError('Contact patches share nodes or are empty')
        patches.append({'skin_elements':component_edges,'native_node_ids_A':ids[0],
                        'native_node_ids_B':ids[1],'closed_source_skin_elements':sorted(closed.intersection(component_edges))})
    for i,a in enumerate(patches):
        for b in patches[i+1:]:
            if (set(a['native_node_ids_A']+a['native_node_ids_B'])&
                set(b['native_node_ids_A']+b['native_node_ids_B'])):
                raise ValueError('Distinct contact components share physical nodes')
    d=BASE/(source_name+'_interface_force_001');d.mkdir(parents=True,exist_ok=False)
    with (d/'input.inp').open('w',encoding='utf-8',newline='\n') as f:
        f.write('/BATCH\n/CLEAR,START\n'+database_resume(BASE/'track_B_setup_001/contact_model.db')+
                '/FILNAME,readonly\n/PREP7\n')
        for i,p in enumerate(patches,1):
            component(f,f'PATCHA{i:03d}',p['native_node_ids_A'])
            component(f,f'PATCHB{i:03d}',p['native_node_ids_B'])
        f.write('FINISH\n/POST1\n'+"FILE,'"+(source/'compression').resolve().as_posix()+"',rst\n"+
                f'SET,{key[0]},{key[1]}\n')
        f.write('*CFOPEN,interface_forces,csv\n*VWRITE\n'
                "('component,side,solid_fx_N,solid_fy_N,platen_fx_N,platen_fy_N,gc_skin_fx_N,gc_skin_fy_N')\n")
        for i in range(1,len(patches)+1):
            for side,label in [(1,'A'),(2,'B')]:
                f.write('ALLSEL,ALL\nCMSEL,S,PATCH'+label+f'{i:03d}\n'
                        'ESEL,S,TYPE,,1\nFSUM\n'
                        '*GET,SFX,FSUM,0,ITEM,FX\n*GET,SFY,FSUM,0,ITEM,FY\n'
                        'ESEL,S,TYPE,,3\nFSUM,,CONT\n'
                        '*GET,PFX,FSUM,0,ITEM,FX\n*GET,PFY,FSUM,0,ITEM,FY\n'
                        'CMSEL,S,INTERNAL_GC\nFSUM,,CONT\n'
                        '*GET,CFX,FSUM,0,ITEM,FX\n*GET,CFY,FSUM,0,ITEM,FY\n'
                        f'*VWRITE,{i},{side},SFX,SFY,PFX,PFY,CFX,CFY\n'
                        "(F8.0,',',F4.0,6(',',E24.16))\n")
        f.write('*CFCLOS\nALLSEL,ALL\nFINISH\n/EXIT,NOSAVE\n')
    m={'schema':'young-dawgs-v068-track-b-two-sided-interface-force',
       'source':source_name,'source_execution_receipt_sha256':file_hash(source/'execution_receipt.json'),
       'source_RST_sha256':file_hash(source/'compression.rst'),
       'source_post_receipt_sha256':file_hash(post/'execution_receipt.json'),
       'source_native_GC_fields_sha256':file_hash(post/(prefix+'_gc_fields.csv')),
       'setup_database_sha256':setup['native_database_sha256'],
       'selected_state':state,'components':patches,'input_sha256':file_hash(d/'input.inp'),
       'read_only':True,'force_interpretation':'All adjacent structural element nodal forces at physical interface nodes; selected GC-skin FSUM reported but not used as the complete two-sided balance.'}
    write_json(d/'simulation_manifest.json',m)
    copy_evidence(d,'track_B_contact_fixture')
    print('Prepared native interface forces',source_name,len(patches),'components',flush=True)


def execute(source_name):
    d=BASE/(source_name+'_interface_force_001');m=read(d/'simulation_manifest.json')
    if file_hash(d/'input.inp')!=m['input_sha256']:
        raise ValueError('Altered native interface proof input')
    r=run_progressive(d,timeout=600,solve=False,cores=2,disk_reserve=80*1024**3)
    copy_evidence(d,'track_B_native_results')
    print('Native interface force readback',r['status'],r['process']['returncode'],flush=True)


def qualify(source_name):
    d=BASE/(source_name+'_interface_force_001');m=read(d/'simulation_manifest.json')
    r=read(d/'execution_receipt.json');source=BASE/source_name
    if (r['process']['returncode']!=0 or r['status']!='PROCESS_EXITED' or
        file_hash(source/'compression.rst')!=m['source_RST_sha256'] or
        file_hash(d/'input.inp')!=r['input_sha256'] or
        file_hash(d/'interface_forces.csv')!=r['process']['artifacts']['interface_forces.csv']['sha256']):
        raise ValueError('Native interface force process/input/result not authenticated')
    data=numeric(d/'interface_forces.csv',
                 ['component','side','solid_fx_N','solid_fy_N','platen_fx_N','platen_fy_N','gc_skin_fx_N','gc_skin_fy_N'])
    if len(data)!=2*len(m['components']):raise ValueError('Incomplete two-sided native force inventory')
    results=[]
    for i,p in enumerate(m['components'],1):
        rows=data[data[:,0]==i]
        if len(rows)!=2 or not np.array_equal(rows[:,1],[1,2]):raise ValueError('Missing native patch side')
        solid=rows[:,2:4];platen=rows[:,4:6];skin=rows[:,6:8]
        scale=float(np.linalg.norm(solid,axis=1).max())
        opposition=float(np.linalg.norm(solid.sum(axis=0))/max(scale,1e-12))
        platen_fraction=float(np.linalg.norm(platen,axis=1).max()/max(scale,1e-12))
        results.append({'component':i,'skin_elements':p['skin_elements'],
                        'native_node_counts':[len(p['native_node_ids_A']),len(p['native_node_ids_B'])],
                        'solid_restoring_forces_A_B_N':solid.tolist(),
                        'platen_forces_A_B_N':platen.tolist(),
                        'selected_GC_skin_forces_A_B_N':skin.tolist(),
                        'opposition_relative':opposition,'platen_fraction':platen_fraction,
                        'passed':bool(scale>1e-8 and opposition<=.01 and platen_fraction<=.01)})
    result={'schema':'young-dawgs-v068-native-structural-interface-force',
            'source_name':source_name,'selected_state':m['selected_state'],
            'native_read_only_receipt_sha256':file_hash(d/'execution_receipt.json'),
            'native_forces_sha256':file_hash(d/'interface_forces.csv'),
            'components':results,'passed':all(x['passed'] for x in results),
            'status':'PASS_TWO_SIDED_NATIVE_STRUCTURAL_FORCE' if all(x['passed'] for x in results) else 'HOLD_INTERFACE_FORCE',
            'scope':'Actual full structural nodal force on both contact-side patches, separately measuring platen contribution. Skin-only FSUM is incomplete.'}
    write_json(RUN/'track_B_contact_fixture'/(source_name+'_interface_force.json'),result)
    print(result['status'],[(x['opposition_relative'],x['platen_fraction']) for x in results],flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','execute','qualify'])
    p.add_argument('source_name');a=p.parse_args()
    {'prepare':prepare,'execute':execute,'qualify':qualify}[a.action](a.source_name)
