"""Replay unchanged archived geometry tests with their expected fixture root.

Archive code snapshots omit experiments/data under their own root. Never insert
files into old snapshots: copy only unchanged archived tests to a temporary root
and link the authenticated current repository inputs/implementation read-only by
convention. These are archived-test replays against current code, not additional
unique tests or a recreation of the absent457-test historical environment.
The symlink-based replay has been executed on Linux; Windows needs symlink rights.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def replay(root,output):
    root=Path(root).resolve();output=Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    output.mkdir(parents=True);records=[]
    groups=sorted((root/'experiments/pipeline_v0.5').glob('**/code_snapshot/tests'))
    for index,group in enumerate(groups):
        tests=sorted(group.glob('test_*.py'))
        if not tests:continue
        with tempfile.TemporaryDirectory(prefix='youngdawgs_archive_replay_') as temp:
            context=Path(temp);(context/'tests').mkdir()
            copied=[]
            for test in tests:
                target=context/'tests'/test.name;shutil.copy2(test,target)
                digest=hashlib.sha256(test.read_bytes()).hexdigest()
                assert hashlib.sha256(target.read_bytes()).hexdigest()==digest
                copied.append({'source':str(test.relative_to(root)),'sha256':digest})
            for item in root.iterdir():
                if item.name not in ['tests','.git','.venv','.pytest_cache']:
                    (context/item.name).symlink_to(item,target_is_directory=item.is_dir())
            env=os.environ.copy();env['EVALUATOR_PATH']=str(root/'validation/evaluators/evaluator_v1_1.py')
            xml=output/f'archive_{index:02d}.xml';log=output/f'archive_{index:02d}.log'
            command=[sys.executable,'-m','pytest','--import-mode=importlib','-q','tests','--junitxml='+str(xml)]
            with log.open('w') as stream:
                result=subprocess.run(command,cwd=context,env=env,stdout=stream,stderr=subprocess.STDOUT,check=False)
            records.append({'group':str(group.relative_to(root)),'tests':copied,'returncode':result.returncode,
                            'junit':xml.name,'log':log.name,'implementation':'current unchanged geometry package',
                            'fixture_context':'temporary root with links to authenticated current inputs; no archive changes'})
    (output/'replay_manifest.json').write_text(json.dumps(records,sort_keys=True,indent=2)+'\n')
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();results=replay(args.root,args.output)
    print([(r['group'],r['returncode']) for r in results])
    if any(r['returncode'] for r in results):raise SystemExit(1)
