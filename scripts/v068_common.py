"""Separate v0.6.8 tracks using the existing native execution infrastructure."""
from pathlib import Path
import json
from metamaterial_eval.simulation.mesh_artifacts import artifact_root
from metamaterial_eval.simulation.solver_execution import file_hash
from metamaterial_eval.simulation.reporting import write_json
from scripts.v066_restart import compact

REPO=Path(__file__).resolve().parents[1]
RUN=REPO/'experiments/pipeline_v0.6.8/run_001'
BASE=artifact_root()/'solver/v068'
REQUEST=Path(r'C:\Users\sd22446\.codex\attachments\5476de4d-cc32-41f4-9c99-7e0df3e3d77b\Pasted text.txt')


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def copy_evidence(source,category):
    target=RUN/category/source.name
    compact(source,target)
    for name in ['gc_inventory.txt','model_inventory.txt','native_type_after.txt','gc_topology.csv']:
        path=source/name
        if path.exists() and path.stat().st_size<1024**2:
            if path.suffix=='.txt':
                (target/name).write_text('\n'.join(s.rstrip() for s in path.read_text(encoding='utf-8',errors='replace').splitlines())+'\n',encoding='utf-8',newline='\n')
            else:(target/name).write_bytes(path.read_bytes())
    return target
