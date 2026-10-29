"""Replay unchanged archived geometry tests with their expected fixture root.

Archive code snapshots omit experiments/data under their own root. Never insert
files into old snapshots: copy only unchanged archived tests to a temporary root
and link the authenticated current repository inputs/implementation read-only by
convention. These are archived-test replays against current code, not additional
unique tests or a recreation of the absent457-test historical environment.
On Windows use directory junctions and copy individual files, avoiding a symlink
privilege requirement. Archived tests and repository fixtures remain unchanged.
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
    groups=sorted(set((root/'experiments/pipeline_v0.5').glob('**/code_snapshot/tests')) |
                  set((root/'experiments/pipeline_v0.5').glob('**/algorithm_version/tests')))
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
            # Some archived cases authenticate other repository test sources.
            # Provide those bytes as fixtures, but collect ONLY the archive's
            # explicit test files below, avoiding extra/duplicate replay counts.
            support=[]
            for test in (root/'tests').glob('*.py'):
                target=context/'tests'/test.name
                if not target.exists():
                    shutil.copy2(test,target)
                    support.append({'source':str(test.relative_to(root)),
                                    'sha256':hashlib.sha256(test.read_bytes()).hexdigest()})
            for item in root.iterdir():
                if item.name not in ['tests','.git','.venv','.pytest_cache']:
                    target=context/item.name
                    if os.name=='nt' and item.is_dir():
                        link_env={**os.environ,'YD_ARCHIVE_LINK_DEST':str(target),'YD_ARCHIVE_LINK_SOURCE':str(item)}
                        subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',
                            'New-Item -ItemType Junction -Path $env:YD_ARCHIVE_LINK_DEST -Target $env:YD_ARCHIVE_LINK_SOURCE | Out-Null'],
                            env=link_env,check=True,stdout=subprocess.DEVNULL)
                    elif os.name=='nt':shutil.copy2(item,target)
                    else:target.symlink_to(item,target_is_directory=item.is_dir())
            env=os.environ.copy();env['EVALUATOR_PATH']=str(root/'validation/evaluators/evaluator_v1_1.py')
            xml=output/f'archive_{index:02d}.xml';log=output/f'archive_{index:02d}.log'
            command=[sys.executable,'-m','pytest','--import-mode=importlib','-q',
                     *(str(context/'tests'/test.name) for test in tests),'--junitxml='+str(xml)]
            with log.open('w') as stream:
                result=subprocess.run(command,cwd=context,env=env,stdout=stream,stderr=subprocess.STDOUT,check=False)
            records.append({'group':str(group.relative_to(root)),'tests':copied,'returncode':result.returncode,
                            'supporting_test_sources_not_collected':support,
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
