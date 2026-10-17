#!/usr/bin/env python3
"""Read-only JVM property precedence probe using original fixture directories, never an owner home."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import local_dev
import profile_session


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java',type=Path,required=True)
    options=parser.parse_args();java=options.java.resolve(strict=True)
    if local_dev.java_version(str(java))!=8:parser.error('Supply the supported client Java8 runtime.')
    parent=ROOT/'.runtime/jvm-profile-options'
    for path in (ROOT/'.runtime',parent):
        if path.is_symlink():parser.error('The fixture lab cannot be a link.')
        path.mkdir(exist_ok=True)
    run=parent/str(time.time_ns());run.mkdir(mode=0o700)
    source=Path(__file__).with_name('OwnedProperties.java')
    subprocess.run([str(java.with_name('javac')),'-d',str(run),str(source)],check=True)
    class Fixture:
        def environment(self,port):return {'storage.players.path':str(run/'fixture-saves')+'/','network.port':str(port)}
    owned={key:run/name for key,name in (('user.home','owned-home'),('soloscape.cache.root','owned-cache'))}
    foreign={key:run/name for key,name in (('user.home','foreign-home'),('soloscape.cache.root','foreign-cache'))}
    options_text=' '.join('-D'+key+'='+str(path) for key,path in foreign.items())
    # The lab path is generated under the known project root. Refuse whitespace so
    # this fixed JVM option string cannot acquire another option through a path.
    if any(char.isspace() for char in str(run)):
        raise ValueError('Use a project path without whitespace for this tiny JVM-options probe.')
    env={'PATH':os.defpath,'_JAVA_OPTIONS':options_text}
    with patch.dict(os.environ,env,clear=True):
        actual=profile_session.owned_environment(Fixture(),43618)
    unsafe=dict(actual,_JAVA_OPTIONS=options_text)  # Deliberate negative/control, not an app option.
    argv=[str(java)]+['-D'+key+'='+str(path) for key,path in owned.items()]+['-cp',str(run),'OwnedProperties']
    rows={}
    for name,environment in (('unsafe_control',unsafe),('actual_owned_environment',actual)):
        completed=subprocess.run(argv,env=environment,text=True,capture_output=True,timeout=15)
        if completed.returncode:raise RuntimeError('Fixture JVM failed: '+completed.stderr)
        properties=dict(line.split('=',1) for line in completed.stdout.splitlines())
        expected=foreign if name=='unsafe_control' else owned
        if properties!={key:str(value) for key,value in expected.items()}:
            raise RuntimeError('Unexpected property ownership in '+name+': '+str(properties))
        rows[name]={'exit':completed.returncode,'properties':{key:Path(value).name for key,value in properties.items()},
                    'late_options_present':'_JAVA_OPTIONS' in environment}
    unchanged=not any(path.exists() for path in (*owned.values(),*foreign.values()))
    if not unchanged:raise RuntimeError('Property observation unexpectedly created fixture homes/cache directories.')
    result={'passed':True,'cases':rows,'fixture_directories_not_created':unchanged,
            'java_version':subprocess.run([str(java),'-version'],capture_output=True,text=True).stderr.splitlines()[0],
            'probe_sha256':local_dev.file_hash(Path(__file__)),'harness_sha256':local_dev.file_hash(source),
            'profile_session_sha256':local_dev.file_hash(ROOT/'scripts/profile_session.py'),
            'scope':'Actual Java8 properties only; no game/cache/profile content or hardware acceptance.'}
    (run/'summary.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2));print('Evidence:',run.relative_to(ROOT)/'summary.json')


if __name__=='__main__':main()
