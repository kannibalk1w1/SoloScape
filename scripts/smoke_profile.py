import os
from pathlib import Path
import subprocess
import sys
import threading
import time
sys.path.insert(0,str(Path(__file__).resolve().parent))
import local_dev, profile_session, profiles
from unittest.mock import patch
import signal

def main():
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
    subprocess.run([str(javac),'-cp',str(clientjar),'-d',str(harness),str(root/'scripts/harness/NativeSessionSmoke.java')],check=True)
    x=original(['Xvfb',':197','-screen','0','1280x800x24'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        time.sleep(.3)
        if x.poll() is not None:raise RuntimeError(x.stderr.read().decode())
        os.environ['DISPLAY']=':197'
        def popen(argv,**kwargs):
            if '-jar' in argv and any('void-client-' in arg for arg in argv):
                i=argv.index('-jar');jar=argv[i+1]
                argv=argv[:i]+['-cp',jar+':'+str(harness),'NativeSessionSmoke',str(marker),'43595']
            return original(argv,**kwargs)
        for iteration in range(2):
            marker.unlink(missing_ok=True)
            with patch.object(subprocess,'Popen',side_effect=popen):
                code=profile_session.run(profile,threading.Event(),lambda stage,message:print(stage,message,flush=True),port=43595)
            if code or not marker.exists() or not profile.metadata()['saved']:
                raise RuntimeError('Native smoke failed; inspect this disposable profile’s logs.')
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
        (testroot/'native-smoke-profile.txt').write_text(profile.manifest['id'])
    finally:
        x.terminate();x.wait(timeout=5)


if __name__ == "__main__":
    main()
