#!/usr/bin/env python3
"""Crash only our disposable parent, then recover a real server through verified pidfd ownership.

This is a server lifecycle probe. Native player New/Continue is tested separately.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import zipfile
import local_dev
import profiles
import session_recovery


def main():
    root=local_dev.ROOT/'.runtime/recovery-tests'/str(time.time_ns())
    profiles.PROFILES=root/'profiles'
    profile=profiles.create('Disposable native recovery','RecoverTest')
    # Never touch the legacy/manual mutable world; retain a before/after fingerprint.
    def fingerprint():
        return {str(p):(p.stat().st_size,p.stat().st_mtime_ns)
                for directory in ('data/saves','data/errors','data/.temp')
                for p in (local_dev.SERVER/directory).rglob('*') if p.is_file()}
    before=fingerprint()
    local_dev.probe_port(43596)
    code='''
import sys,threading,signal
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import profiles,profile_session
profiles.PROFILES=Path(sys.argv[2])
cancelled=threading.Event()
signal.signal(signal.SIGTERM,lambda *args:cancelled.set())
profile_session.run(profiles.load(sys.argv[3]),cancelled,lambda *args:None,port=43596,client_enabled=False)
'''
    with (root/'parent.log').open('w') as log:
        parent=subprocess.Popen([sys.executable,'-c',code,str(local_dev.ROOT/'scripts'),str(profiles.PROFILES),profile.manifest['id']],stdout=log,stderr=subprocess.STDOUT)
        try:
            deadline=time.monotonic()+local_dev.READY_TIMEOUT+20
            while True:
                record=session_recovery.read(profile)
                if record and record['phase']=='playing' and 'server' in record['children']:
                    break
                if parent.poll() is not None or time.monotonic()>deadline:
                    raise RuntimeError('Disposable native server did not become ready; inspect its private logs.')
                time.sleep(.1)
            # This PID is our exact Popen child, never a discovered process.
            parent.kill();parent.wait(timeout=5)
            state=session_recovery.inspect(profile)
            if not state['recoverable'] or state['active']!=['server']:
                raise RuntimeError('Native orphan identity/inherited guards were not verified.')
            session_recovery.recover(profile,threading.Event(),lambda stage,message:print(stage,message,flush=True))
            if session_recovery.read(profile) is not None:
                raise RuntimeError('Recovered record remains.')
            reasons=[]
            for backup in (profile.directory/'backups').glob('*.zip'):
                with zipfile.ZipFile(backup) as archive:
                    reasons.append(json.loads(archive.read('backup.json'))['reason'])
            if sorted(reasons)!=['after-recovered-shutdown','before-launch'] or fingerprint()!=before:
                raise RuntimeError('Recovery backup evidence or original-world fingerprint failed.')
            with profile.lock():pass
            evidence={'native_server_recovered':True,'inherited_guards_verified':True,
                      'original_mutable_paths_unchanged':True,'backup_reasons':reasons,
                      'clean_shutdown_confirmed':False,'note':'Real native server only; no player/client/hardware claim.'}
            (root/'summary.json').write_text(json.dumps(evidence,indent=2)+'\n')
            print('Native server pidfd recovery passed; private evidence:',root)
        finally:
            if parent.poll() is None:
                parent.terminate();parent.wait()  # backend/session normal save hooks
            try:
                remaining=session_recovery.read(profile)
                if remaining is not None:
                    status=session_recovery.inspect(profile)
                    if status.get('recoverable'):
                        # Include early parent death and the Popen/record crash gap.
                        session_recovery.recover(profile,threading.Event(),lambda *args:None)
                    else:
                        print('Private session record retained for inspection:',profile.directory/session_recovery.RECORD,file=sys.stderr)
            except Exception as cleanup_error:
                # Preserve the original probe failure; never use a broad-kill fallback.
                print('Ownership-checked cleanup did not finish:',cleanup_error,
                      'Record:',profile.directory/session_recovery.RECORD,file=sys.stderr)


if __name__=='__main__':main()
