#!/usr/bin/env python3
"""Drive a prepared private launcher's real New/Continue buttons on an owned Xvfb display."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'experiments/native-prebuilt-server'))
import profiles


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--server-java',type=Path,required=True)
    parser.add_argument('--client-java',type=Path,required=True)
    options=parser.parse_args()
    run=options.run.resolve(strict=True)
    expected=(ROOT/'.runtime/prebuilt-runtime').resolve()
    if run.parent!=expected or not run.name.isdecimal():
        parser.error('Choose a uniquely prepared private lab run, never an owner installation.')
    preparation=json.loads((run/'preparation.json').read_text())
    if not preparation.get('passed'):
        parser.error('The preparation did not pass.')
    payload=run/'payload';state=run/'state';cache=run/'cache'
    support=load(ROOT/'experiments/native-prebuilt-server/run.py','probe_payload_helpers')
    digest,tree=support.digest,support.tree
    before=tree(payload);cache_before=tree(cache)
    if support.tree_digest(before)!=preparation['payload_tree_sha256']:
        raise RuntimeError('The prepared payload changed before this probe.')
    if (run/'probe.json').exists() or any((state/'profiles').iterdir()):
        raise RuntimeError('Use a fresh prepared fixture, not an existing profile or completed probe.')
    java21=options.server_java.resolve(strict=True);java8=options.client_java.resolve(strict=True)
    harness=state/'instrumentation';harness.mkdir()
    sessions=load(ROOT/'experiments/native-prebuilt-session/run.py','prebuilt_session_helpers')
    subprocess.run([str(java8.with_name('javac')),'-encoding','UTF-8','-cp',str(payload/preparation['roles']['client']),
                    '-d',str(harness),str(Path(__file__).with_name('LauncherProbe.java'))]+
                   [str(ROOT/'scripts/harness'/(name+'.java')) for name in sessions.HARNESS],check=True)
    wrappers={}
    for role,java in [('server',java21),('client',java8)]:
        wrapper=state/(role+'-java')
        code='''import os,sys
from pathlib import Path
java=JAVA
args=['-Djava.io.tmpdir='+TEMP]+sys.argv[1:]
if ROLE=='client' and '-jar' in args:
 i=args.index('-jar'); jar=args[i+1]
 count_file=Path(COUNTER)
 count=int(count_file.read_text())+1 if count_file.exists() else 1
 count_file.write_text(str(count))
 port=args[args.index('--port')+1]
 args=args[:i]+['-cp',jar+os.pathsep+HARNESS,'NativeSessionSmoke',MARKER+str(count),port]
os.execv(java,[java]+args)
'''
        substitutions={'JAVA':str(java),'TEMP':str(state/'temp'),'ROLE':role,'COUNTER':str(state/'client-launches'),
                       'HARNESS':str(harness),'MARKER':str(state/'native-')}
        for name,value in substitutions.items():code=code.replace(name,repr(value))
        wrapper.write_text('#!'+sys.executable+'\n'+code);wrapper.chmod(0o700);wrappers[role]=wrapper
    env={'PATH':os.defpath,'HOME':str(state/'home'),'TMPDIR':str(state/'temp'),'LANG':'C.UTF-8',
         'PYTHONDONTWRITEBYTECODE':'1','ALSA_CONFIG_PATH':str(state/'alsa.conf'),
         'SOLOSCAPE_PROFILE_HOME':str(state/'profiles'),'SOLOSCAPE_CACHE_HOME':str(cache),
         'SOLOSCAPE_LAUNCHER_HOME':str(state/'launcher'),'SERVER_JAVA':str(wrappers['server']),
         'CLIENT_JAVA':str(wrappers['client'])}
    result={'passed':False,'audio_excluded':True,'physical_input':False,'scope':'Private experimental prebuilt preflight plus actual graphical launcher/native New/Continue. No release/update/Deck acceptance.'}
    display=frontend=None
    try:
        read_fd,write_fd=os.pipe()
        try:
            display=subprocess.Popen(['Xvfb','-displayfd',str(write_fd),'-screen','0','1280x800x24','-nolisten','tcp'],
                                     env=env,pass_fds=(write_fd,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            os.close(write_fd);write_fd=None
            with selectors.DefaultSelector() as selector:
                selector.register(read_fd,selectors.EVENT_READ)
                if not selector.select(10):raise RuntimeError('Private Xvfb handshake timed out.')
                number=os.read(read_fd,64).decode().strip()
            if not number.isdecimal() or display.poll() is not None:raise RuntimeError('Private display failed.')
            env['DISPLAY']=':'+number
        finally:
            os.close(read_fd)
            if write_fd is not None:os.close(write_fd)
        with socket.socket() as port_probe:
            port_probe.bind(('127.0.0.1',0));port=port_probe.getsockname()[1]
        requests=[dict(id=1,action='diagnostics',port=port),dict(id=2,action='settings',save=True,port=port),
                  dict(id=3,action='create',label='Private runtime fixture',account='BundleProbe')]
        setup=subprocess.run([sys.executable,'-B',str(payload/'scripts/launcher_backend.py')],
                             input=''.join(json.dumps(r)+'\n' for r in requests),env=env,cwd=payload,
                             text=True,capture_output=True,timeout=60)
        (run/'setup.stderr').write_text(setup.stderr)
        replies=[json.loads(line) for line in setup.stdout.splitlines()]
        if setup.returncode or len(replies)!=3 or not all(row.get('ok') for row in replies) or not replies[0]['result']['ok']:
            raise RuntimeError('Prebuilt diagnostics/setup failed: '+setup.stdout[:1000])
        result['preflight']=replies[0]['result']
        uid=replies[2]['result']['id'];profile=profiles.Profile(state/'profiles'/uid)
        fields=[];rounds=[];started=time.monotonic()
        with (run/'launcher.log').open('w') as log:
            frontend=subprocess.Popen([str(java8),'-Djava.io.tmpdir='+str(state/'temp'),'-cp',
                      str(payload/preparation['roles']['client'])+os.pathsep+str(harness),'LauncherProbe',
                      str(payload),str(run/'gui.json'),str(port)],env=env,cwd=payload,stdout=log,stderr=subprocess.STDOUT)
            while frontend.poll() is None:
                for index in range(2):
                    checkpoint=run/('round'+str(index)+'.json');ack=run/('round'+str(index)+'.ack')
                    if checkpoint.exists() and not ack.exists():
                        marker=state/('native-'+str(index+1))
                        if not marker.is_file() or 'serverCapabilities=verified' not in marker.read_text():
                            raise RuntimeError('Native readiness/capability marker missing.')
                        account=profiles.validate_save((profile.state/'saves/bundleprobe.toml').read_bytes())
                        selected={key:account[key] for key in ('accountName','experience','inventories','tile')}
                        if fields and selected!=fields[0]:raise RuntimeError('Continue changed compared account fields.')
                        fields.append(selected);rounds.append(json.loads(checkpoint.read_text()))
                        ack.write_text('Coordinator verified the stopped-world fixture.\n')
                if time.monotonic()-started>500:raise RuntimeError('Private graphical probe timed out.')
                time.sleep(.05)
        if frontend.returncode or len(fields)!=2 or not json.loads((run/'gui.json').read_text()).get('passed'):
            raise RuntimeError('The real graphical launcher did not pass both native sessions.')
        # Verify through the real profile API without selecting its global owner/default home.
        with patch.object(profiles,'PROFILES',state/'profiles'):
            backups=profiles.list_backups(uid)
        if len(backups)!=4 or not all(row['valid'] for row in backups):raise RuntimeError('Four verified fixture backups were not retained.')
        result.update(rounds=rounds,compared_account_fields_equal=True,verified_backups=len(backups),
                      payload_unchanged=tree(payload)==before,cache_unchanged=tree(cache)==cache_before,
                      manifest_sha256=preparation['manifest_sha256'],jars=preparation['jars'],
                      source_commit=preparation['source_commit'],runtime_contexts=len(list((state/'launcher/version-contexts').iterdir())),
                      source_build_doctor_bypassed=False,native_source_checkout_in_payload=False)
        if not result['payload_unchanged'] or not result['cache_unchanged']:raise RuntimeError('Payload/cache inventory changed.')
        result['passed']=True
    except BaseException as exc:
        result['failure']=type(exc).__name__+': '+str(exc)
        raise
    finally:
        if frontend is not None and frontend.poll() is None:
            frontend.terminate()
            try:
                frontend.wait(timeout=120)  # Backend EOF requests normal owned-world closure.
            except subprocess.TimeoutExpired:
                result['passed']=False
                result['frontend_shutdown_unverified']=True
        if display is not None and display.poll() is None and (frontend is None or frontend.poll() is not None):
            display.terminate()
            try:display.wait(timeout=5)
            except subprocess.TimeoutExpired:display.kill();display.wait(timeout=5)
        result['probe_sha256']=digest(Path(__file__))
        (run/'probe.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        print('Evidence:',run.relative_to(ROOT)/'probe.json',flush=True)


if __name__=='__main__':main()
