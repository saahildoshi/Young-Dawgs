"""Read-only installed-v241 source contact section and interaction audit."""
import json
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.microstructure_pilot import database_resume
from metamaterial_eval.simulation.progressive_compression import run_progressive
from metamaterial_eval.simulation.reporting import write_json
from metamaterial_eval.simulation.solver_execution import file_hash
from scripts.v066_restart import compact
from scripts.v067_fixture import BASE, RUN


def main():
    source=artifact_root()/'solver/v066/fine_gc_setup_001/contact_model_gc.db'
    d=BASE/'parent_section_probe_001';d.mkdir(parents=True,exist_ok=False)
    skins=[1295993,1494296,1494295,1285266,1383913,1264273,1507848]
    lines=['/BATCH','/CLEAR,START',database_resume(source).strip(),'/FILNAME,readonly','/GOPR','/PREP7',
           '/OUTPUT,parent_sections,txt','GCDEF,LIST','GCDEF,TABLE,TOTAL','ETLIST,ALL','/OUTPUT',
           '*CFOPEN,parent_skin_sections,csv','*VWRITE',"('element,type,section,i,j,mid')"]
    for eid in skins:
        lines += [f'*GET,TY,ELEM,{eid},ATTR,TYPE',f'*GET,SC,ELEM,{eid},ATTR,SECN',
                  f'*GET,NI,ELEM,{eid},NODE,1',f'*GET,NJ,ELEM,{eid},NODE,2',f'*GET,NM,ELEM,{eid},NODE,3',
                  f'*VWRITE,{eid},TY,SC,NI,NJ,NM',"(F12.0,5(',',F12.0))"]
    lines+=['*CFCLOS','FINISH','/EXIT,NOSAVE']
    (d/'input.inp').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
    write_json(d/'provenance.json',{'source_database_sha256':file_hash(source),'source':str(source),'read_only':True})
    r=run_progressive(d,timeout=300,solve=False,cores=1)
    compact(d,RUN/'contact_onset'/d.name)
    for name in ['parent_sections.txt','parent_skin_sections.csv']:
        (RUN/'contact_onset'/d.name/name).write_bytes((d/name).read_bytes())
    print(r['status'],r['process']['returncode'],(d/'parent_skin_sections.csv').read_text(encoding='utf-8'),flush=True)


if __name__=='__main__':main()
