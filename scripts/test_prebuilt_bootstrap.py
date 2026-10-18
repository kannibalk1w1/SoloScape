"""Private runtime adapter checks: actual copied modules, inert jars/JREs and external fixture state."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import local_dev

CONTRACT=Path(__file__).resolve().parents[1]/'experiments/prebuilt-runtime-contract'
SERVER='upstream/game-server/game/build/libs/void-server-fixture.jar'
CLIENT='upstream/runelite-client/client/build/libs/void-client-fixture.jar'
DRIVER='''
import json,sys
from pathlib import Path
sys.path.insert(0,sys.argv[1])
import prebuilt_bootstrap,local_dev
context=prebuilt_bootstrap.configure()
messages=[]
context['doctor']=local_dev.doctor(require_display=False,check_port=False,output=lambda *a:messages.append(' '.join(map(str,a))))
context['messages']=messages
with local_dev.build_lock(shared=True): context['locked']=True
try: local_dev.prepare()
except RuntimeError: context['build_refused']=True
print(json.dumps(context))
'''


class PrivateBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.shared={key:self.base/name for key,name in
                     [('SOLOSCAPE_PROFILE_HOME','profiles'),('SOLOSCAPE_CACHE_HOME','cache'),
                      ('SOLOSCAPE_LAUNCHER_HOME','launcher')]}
        for path in self.shared.values(): path.mkdir()
        for name in ('main_file_cache.dat2','main_file_cache.idx255'):
            (self.shared['SOLOSCAPE_CACHE_HOME']/name).write_bytes(b'original fake cache; no native loading')
        self.env={k:v for k,v in os.environ.items() if not k.startswith(('SOLOSCAPE_','PYTHON')) and k!='DISPLAY'}
        self.env.update({k:str(v) for k,v in self.shared.items()})
        for key,version in [('SERVER_JAVA','21.0.0'),('CLIENT_JAVA','1.8.0')]:
            executable=self.base/key
            executable.write_text('#!/bin/sh\nprintf \'%s\\n\' \'openjdk version "'+version+'"\' >&2\n')
            executable.chmod(0o755)
            self.env[key]=str(executable)
        self.env['PYTHONDONTWRITEBYTECODE']='1'

    def payload(self,name):
        root=self.base/name
        (root/'scripts').mkdir(parents=True)
        for name in ('local_dev.py','profiles.py','death_loot_state.py','profile_session.py','session_recovery.py','release_updates.py','deck_awake.py','launcher.sh'):
            shutil.copy2(Path(__file__).with_name(name),root/'scripts'/name)
        shutil.copy2(Path(__file__).with_name('launcher_backend.py'),root/'scripts/owned_launcher_backend.py')
        shutil.copy2(CONTRACT/'manifest.py',root/'scripts/prebuilt_manifest.py')
        shutil.copy2(CONTRACT/'prebuilt_bootstrap.py',root/'scripts/prebuilt_bootstrap.py')
        (root/'scripts/launcher_backend.py').write_text('from prebuilt_bootstrap import main\nmain()\n')
        for name in (SERVER,CLIENT):
            path=root/name;path.parent.mkdir(parents=True);path.write_bytes(b'original inert jar fixture')
        files={p.relative_to(root).as_posix():dict(size=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
               for p in root.rglob('*') if p.is_file()}
        manifest=dict(format=1,source_commit='1'*40,platform='linux-x86_64',cache_revision=634,
                      pins=local_dev.PINNED,patches={'patches/client/0001-fixture.patch':'2'*64,'patches/server/0001-fixture.patch':'3'*64},
                      roles=dict(server=SERVER,client=CLIENT,launcher='scripts/launcher.sh'),files=files)
        (root/'soloscape-runtime.json').write_text(json.dumps(manifest,sort_keys=True))
        return root

    def run_driver(self,root,env=None,check=True):
        result=subprocess.run([sys.executable,'-B','-c',DRIVER,str(root/'scripts')],env=env or self.env,
                              cwd=self.base,text=True,capture_output=True,timeout=15)
        if not check: return result
        self.assertEqual(result.returncode,0,result.stderr)
        return json.loads(result.stdout)

    def test_real_preflight_needs_no_git_gradle_compiler_or_source_stamp(self):
        root=self.payload('version-a')
        result=self.run_driver(root)
        self.assertTrue(result['doctor'],result)
        self.assertTrue(result['locked']);self.assertTrue(result['build_refused'])
        self.assertFalse((root/'.runtime').exists())
        self.assertFalse((root/'.git').exists())
        self.assertTrue(Path(result['runtime_context']).is_relative_to(self.shared['SOLOSCAPE_LAUNCHER_HOME']))

    def test_same_version_reuses_context_other_code_root_cannot_take_it(self):
        a=self.payload('version-a');b=self.payload('version-b')
        first=self.run_driver(a);again=self.run_driver(a);other=self.run_driver(b)
        self.assertEqual(first['context_key'],again['context_key'])
        self.assertEqual(first['manifest_sha256'],other['manifest_sha256'])
        self.assertNotEqual(first['runtime_context'],other['runtime_context'])

    def test_missing_or_overlapping_external_state_fails_before_context_creation(self):
        root=self.payload('version-a')
        for key in self.shared:
            env=dict(self.env);env.pop(key)
            result=self.run_driver(root,env,False)
            self.assertNotEqual(result.returncode,0,result.stdout)
        env=dict(self.env,SOLOSCAPE_CACHE_HOME=self.env['SOLOSCAPE_PROFILE_HOME'])
        self.assertNotEqual(self.run_driver(root,env,False).returncode,0)
        env=dict(self.env,SOLOSCAPE_LAUNCHER_HOME=str(root/'new-state'))
        self.assertNotEqual(self.run_driver(root,env,False).returncode,0)
        self.assertFalse((root/'new-state').exists())
        self.assertFalse((self.shared['SOLOSCAPE_LAUNCHER_HOME']/'version-contexts').exists())

    def test_corrupt_payload_refuses_before_creating_runtime_context(self):
        root=self.payload('version-a');(root/CLIENT).write_bytes(b'corrupt')
        self.assertNotEqual(self.run_driver(root,check=False).returncode,0)
        self.assertFalse((self.shared['SOLOSCAPE_LAUNCHER_HOME']/'version-contexts').exists())
