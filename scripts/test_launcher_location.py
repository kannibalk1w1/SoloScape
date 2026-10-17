"""Shared launcher settings survive code changes using original disposable files."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import local_dev


class LauncherLocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_unset_uses_current_version_runtime(self):
        self.assertEqual(local_dev.launcher_directory({}), local_dev.RUNTIME)

    def test_bad_explicit_home_is_refused_without_creation(self):
        (self.root/'file').write_text('canary')
        (self.root/'link').symlink_to(self.root/'missing',target_is_directory=True)
        for value in ('', '.', 'relative', 'bad\0path', str(self.root/'file'), str(self.root/'link')):
            with self.subTest(value=value), self.assertRaises(ValueError):
                local_dev.launcher_directory({local_dev.LAUNCHER_HOME_ENV:value})
        self.assertEqual((self.root/'file').read_text(),'canary')
        self.assertFalse((self.root/'missing').exists())

    def backend(self, version, requests, shared):
        code=self.root/version
        scripts=code/'scripts'
        scripts.mkdir(parents=True)
        for name in ('launcher_backend.py','local_dev.py','profile_session.py','profiles.py',
                     'session_recovery.py','release_updates.py','deck_awake.py'):
            shutil.copy2(Path(__file__).with_name(name),scripts/name)
        env={k:v for k,v in os.environ.items() if not k.startswith('SOLOSCAPE_')}
        env[local_dev.LAUNCHER_HOME_ENV]=str(shared)
        result=subprocess.run([sys.executable,'-B',str(scripts/'launcher_backend.py')],
                              input=''.join(json.dumps(dict(id=i,**request))+'\n' for i,request in enumerate(requests)),
                              text=True,capture_output=True,cwd=code,env=env,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertFalse((code/'.runtime').exists())
        return [json.loads(line) for line in result.stdout.splitlines()]

    def test_real_backend_settings_survive_two_version_roots(self):
        shared=self.root/'shared launcher'
        first=self.backend('version-a',[dict(action='settings',save=True,port=43612)],shared)
        self.assertTrue(first[0]['ok'],first)
        before=(shared/'launcher-settings.json').read_bytes()
        second=self.backend('version-b',[dict(action='settings')],shared)
        self.assertEqual(second[0]['result']['port'],43612)
        self.assertEqual((shared/'launcher-settings.json').read_bytes(),before)
        self.assertEqual(sorted(p.name for p in shared.iterdir()),['launcher-settings.json'])
