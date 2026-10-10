import os
import argparse
import selectors
from pathlib import Path
import subprocess
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import local_dev, profile_session, profiles
from unittest.mock import patch
import signal
import json
from native_metrics import NativeMetrics

def _main():
    parser=argparse.ArgumentParser(description="Disposable native New/Continue/save and optional adventure UI probe.")
    parser.add_argument("--adventure",action="store_true",help="Probe real native adventure tabs, local settings and software overlay intervals.")
    parser.add_argument("--journey",action="store_true",help="Actual Lumbridge kitchen/bank round trip, Withdraw-X cancellation and bank search in disposable worlds.")
    parser.add_argument("--text",action="store_true",help="Focused native text fixture plus logout/relog/save checks; skips adventure-tab/performance stages.")
    parser.add_argument("--desktop",action="store_true",help="Use the explicitly authorized current X11/XWayland display; never stop that display.")
    options=parser.parse_args()
    if options.text or options.journey:options.adventure=True
    signal.signal(signal.SIGTERM, local_dev.interrupted)
    root=local_dev.ROOT;testroot=root/'.runtime/alpha-tests'/('session-'+str(time.time_ns()));testroot.mkdir(parents=True,exist_ok=True)
    profiles.PROFILES=testroot/'profiles'
    profile=profiles.create('Native isolated smoke','AlphaTest')
    marker=testroot/'native-login.marker';marker.unlink(missing_ok=True)
    original=subprocess.Popen
    def fingerprint():
        result={}
        for name in ('data/saves','data/errors','data/.temp'):
            base=local_dev.SERVER/name
            for path in base.rglob('*'):
                if path.is_file():
                    st=path.stat();result[str(path)]=(st.st_size,st.st_mtime_ns)
        return result
    before=fingerprint()
    savebefore=None
    harness=root/'.runtime/alpha-tests/harness'
    harness.mkdir(parents=True,exist_ok=True)
    clientjar=local_dev.jar(local_dev.CLIENT/'client','void-client-*.jar')
    javac=Path(os.environ['CLIENT_JAVA']).with_name('javac')
    subprocess.run([str(javac),'-cp',str(clientjar),'-d',str(harness),str(root/'scripts/harness/NativeSessionSmoke.java'),str(root/'scripts/harness/NativeAdventureProbe.java'),str(root/'scripts/harness/NativeTextProbe.java'),str(root/'scripts/harness/NativePlayableLoopProbe.java')],check=True)
    x=None
    if options.desktop:
        if not os.environ.get('DISPLAY'):
            raise RuntimeError('--desktop requires an explicit DISPLAY and working X11 authorization.')
    else:
        read_display,write_display=os.pipe()
        x=original(['Xvfb','-displayfd',str(write_display),'-screen','0','1280x800x24','-nolisten','tcp'],pass_fds=(write_display,),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        os.close(write_display)
    try:
        if x is not None:
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(read_display,selectors.EVENT_READ)
                    if not selector.select(10):raise RuntimeError('Private Xvfb display handshake timed out.')
                display_number=os.read(read_display,128).decode('ascii').strip()
                if not display_number.isdigit() or x.poll() is not None:raise RuntimeError('Private Xvfb failed to allocate its own display.')
                os.environ['DISPLAY']=':'+display_number
            finally:os.close(read_display)
        def popen(argv,**kwargs):
            if '-jar' in argv and any('void-client-' in arg for arg in argv):
                i=argv.index('-jar');jar=argv[i+1]
                label='Existing authorized X11/XWayland desktop; native overlay-render intervals, real Gateway/synthetic UI input and AWT events through native canvas mouse handlers. No physical controller or Gaming Mode acceptance.' if options.desktop else 'Private owned Xvfb/software rendering; native overlay-render intervals, real Gateway/synthetic UI input and native Robot mouse logout. No GPU/Deck/controller acceptance.'
                argv=argv[:i]+['-Dsoloscape.probe.environment='+label]+(['-Dsoloscape.probe.awt.mouse=true'] if options.desktop else [])+(['-Dsoloscape.adventure.probe=true'] if options.adventure else [])+(['-Dsoloscape.text.probe.fast=true'] if options.text else [])+(['-Dsoloscape.playable.probe=true'] if options.journey else [])+['-cp',jar+':'+str(harness),'NativeSessionSmoke',str(marker),'43595']
            process=original(argv,**kwargs)
            if any('void-server-' in arg for arg in argv):metrics.add(process,'server')
            elif any('void-client-' in arg for arg in argv):metrics.add(process,'client')
            return process
        elapsed=[];adventure=[];observations=[]
        for iteration in range(2):
            if x is not None and x.poll() is not None:raise RuntimeError('Owned private display exited; refusing another display.')
            session_started=time.monotonic()
            marker.unlink(missing_ok=True)
            metrics=NativeMetrics();metrics.start()
            try:
                with patch.object(subprocess,'Popen',side_effect=popen):
                    def notify(stage,message):
                        metrics.stage(stage)
                        print(stage,message,flush=True)
                    code=profile_session.run(profile,threading.Event(),notify,port=43595)
            finally:
                observation=metrics.finish();observations.append(observation)
                (testroot/('resources-new.json' if iteration==0 else 'resources-continue.json')).write_text(json.dumps(observation,indent=2)+'\n')
            elapsed.append(round(time.monotonic()-session_started,3))
            if code or not marker.exists() or not profile.metadata()['saved']:
                raise RuntimeError('Native smoke failed; inspect this disposable profile’s logs.')
            if options.adventure:
                adventure.append(json.loads(Path(str(marker)+'.adventure.json').read_text()))
                Path(str(marker)+'.adventure.json').replace(testroot/('adventure-new.json' if iteration==0 else 'adventure-continue.json'))
            saved=profiles.validate_save((profile.state/'saves/alphatest.toml').read_bytes())
            if savebefore is not None:
                if not all(savebefore[k]==saved[k] for k in ('accountName','experience','inventories','tile')):
                    raise RuntimeError('Native save/reload changed a tested field.')
            savebefore=saved
        saveafter=profiles.validate_save((profile.state/'saves/alphatest.toml').read_bytes())
        print('Native save/reload fields preserved:',all(savebefore[k]==saveafter[k] for k in ('accountName','experience','inventories','tile')))
        print('Smoke client exit:',code)
        print('In-game marker:',marker.exists())
        print('Native character save:',profile.metadata()['saved'])
        print('Verified backups:',len(list((profile.directory/'backups').glob('*.zip'))))
        print('Original mutable paths unchanged:',before==fingerprint())
        if code or not marker.exists() or not profile.metadata()['saved'] or before!=fingerprint():raise RuntimeError('Native smoke failed; see private profile logs')
        # Cancel a real native startup while content is still loading. Compare the entire
        # saved world, including exchange files; never touch the legacy world.
        saved_world={str(p.relative_to(profile.state/'saves')):p.read_bytes() for p in (profile.state/'saves').rglob('*') if p.is_file()}
        cancelled=threading.Event()
        def cancel_loading():
            deadline=time.monotonic()+60
            log=profile.directory/'session-logs/server.log'
            while time.monotonic()<deadline:
                text=log.read_text(errors='replace') if log.exists() else ''
                # The current log is truncated before startup. Use cache/content loader output,
                # never the previous fully-ready log or a fixed delay.
                if ('MemoryCache' in text or 'DefinitionDecoder' in text) and 'Void loaded in' not in text:
                    cancelled.set();return
                time.sleep(.02)
            cancelled.set()
        observer=threading.Thread(target=cancel_loading)
        observer.start()
        try:
            code=profile_session.run(profile,cancelled,lambda stage,message:print(stage,message,flush=True),port=43595,client_enabled=False)
        finally:observer.join(65)
        log=(profile.directory/'session-logs/server.log').read_text(errors='replace')
        if 'Void loaded in' in log or not ('MemoryCache' in log or 'DefinitionDecoder' in log):
            raise RuntimeError('Native early cancellation was not observed; cannot claim this check.')
        after_cancel={str(p.relative_to(profile.state/'saves')):p.read_bytes() for p in (profile.state/'saves').rglob('*') if p.is_file()}
        if code or after_cancel!=saved_world or before!=fingerprint():raise RuntimeError('Cancelled native startup changed saved-world bytes.')
        print('Cancelled native startup preserved entire saved world:',after_cancel==saved_world)
        print('New/Continue complete-session seconds (includes client readiness and save):',elapsed)
        (testroot/'native-smoke-summary.json').write_text(json.dumps({'new_session_seconds':elapsed[0],'continue_session_seconds':elapsed[1],
            'native_startup_cancel_preserved':True,'original_mutable_paths_unchanged':before==fingerprint(),
            'adventure':adventure,'text_focused':options.text,'playable_journey':options.journey,'display':'existing-desktop' if options.desktop else 'private-xvfb',
            'precondition':'Desktop probes require hands off, awake display; real input/focus may interfere.' if options.desktop else 'Owned private display.',
            'screenshots':'Private evidence only; desktop overlays may appear or Wayland capture may be unavailable. Review before publishing.',
            'note':'Native session totals and overlay-render intervals; not physical controller or Gaming Mode acceptance.'},indent=2)+'\n')
        (testroot/'native-smoke-profile.txt').write_text(profile.manifest['id'])
    finally:
        if x is not None:
            x.terminate()
            try:x.wait(timeout=5)
            except subprocess.TimeoutExpired:
                x.kill();x.wait(timeout=5)  # Only this probe's owned display, never a game/save process.


def main():
    with local_dev.build_lock(shared=True):
        _main()


if __name__ == "__main__":
    main()
