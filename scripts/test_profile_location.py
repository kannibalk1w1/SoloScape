"""SOLOSCAPE_PROFILE_HOME tests: disposable trees and subprocesses only, never the real owner home."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import profiles
from test_profiles import native_save

ENV = profiles.PROFILE_HOME_ENV

DRIVER = r'''
import hashlib, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
import profiles
mode, argument = sys.argv[2], sys.argv[3]
result = {'root': str(profiles.PROFILES)}
if mode == 'create':
    profile = profiles.create('Traveller', 'Tester')
    (profile.state / 'saves' / 'tester.toml').write_bytes(Path(argument).read_bytes())
    result.update(uid=profile.manifest['id'], backup=profile.backup().name)
elif mode == 'corrupt-restore':
    profile = profiles.load(argument)
    (profile.state / 'saves' / 'tester.toml').write_bytes(b'corrupt native save')
    backup = profiles.list_backups(argument)[0]
    assert backup['valid'], backup
    profile.restore(backup['name'])
    restored = (profile.state / 'saves' / 'tester.toml').read_bytes()
    result.update(backup=backup['name'], sha256=hashlib.sha256(restored).hexdigest())
elif mode == 'discover':
    listed = profiles.list_profiles()
    result.update(ids=[row['id'] for row in listed], saved=[row['saved'] for row in listed],
                  loaded=profiles.load(argument).metadata()['saved'])
print(json.dumps(result))
'''


def snapshot(path):
    if not path.exists():
        return None
    return {p.relative_to(path).as_posix(): (p.read_bytes() if p.is_file() else None) for p in sorted(path.rglob('*'))}


class ProfileLocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.code_a = self.copy_code_root('code-a')
        self.code_b = self.copy_code_root('code-b')
        self.external = self.root / 'external-profiles'
        self.default_home = self.code_a / '.runtime/profiles'
        sentinel = self.default_home / 'owner-sentinel'
        sentinel.mkdir(parents=True)
        (sentinel / 'profile.json').write_text('{"owner": "untouched"}\n')
        self.save_file = self.root / 'fixture-save.toml'
        self.save_file.write_bytes(native_save())

    def tearDown(self):
        self.temp.cleanup()

    def copy_code_root(self, name):
        code = self.root / name
        (code / 'scripts').mkdir(parents=True)
        shutil.copy2(profiles.__file__, code / 'scripts/profiles.py')
        return code

    def run_driver(self, code_root, mode, argument='', home=None, check=True):
        env = {k: v for k, v in os.environ.items() if k != ENV}
        if home is not None:
            env[ENV] = str(home)
        # -B and -I keep the disposable code roots free of __pycache__ and inherited PYTHON* settings.
        completed = subprocess.run([sys.executable, '-B', '-I', '-c', DRIVER, str(code_root / 'scripts'), mode, argument],
                                   env=env, cwd=self.root, capture_output=True, text=True, timeout=120)
        if not check:
            return completed
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_default_home_is_unchanged_when_unset(self):
        self.assertEqual(profiles.configured_profile_home({}), profiles.ROOT / '.runtime/profiles')

    def test_absolute_external_home_is_selected_without_creating_it(self):
        self.assertEqual(profiles.configured_profile_home({ENV: str(self.external)}), self.external)
        self.assertFalse(self.external.exists())

    def test_invalid_configuration_is_rejected_and_writes_nothing(self):
        (self.root / 'real').mkdir()
        (self.root / 'linked').symlink_to(self.root / 'real', target_is_directory=True)
        (self.root / 'a-file').write_bytes(b'not a directory')
        before = snapshot(self.root)
        for value in ['', 'relative-profiles', '.', ' ', str(self.root / 'linked'), str(self.root / 'a-file')]:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    profiles.configured_profile_home({ENV: value})
        with self.assertRaises(ValueError):
            profiles.configured_profile_home({ENV: 'bad\0value'})
        self.assertEqual(snapshot(self.root), before)

    def test_external_home_survives_code_root_change_and_restore(self):
        default_before = snapshot(self.default_home)
        created = self.run_driver(self.code_a, 'create', str(self.save_file), home=self.external)
        uid = created['uid']
        self.assertEqual(created['root'], str(self.external))
        self.assertTrue((self.external / uid / 'profile.json').is_file())
        self.assertFalse((self.code_a / '.runtime/profiles' / uid).exists())

        restored = self.run_driver(self.code_a, 'corrupt-restore', uid, home=self.external)
        self.assertEqual(restored['sha256'], hashlib.sha256(native_save()).hexdigest())

        discovered = self.run_driver(self.code_b, 'discover', uid, home=self.external)
        self.assertEqual(discovered['root'], str(self.external))
        self.assertEqual(discovered['ids'], [uid])
        self.assertEqual(discovered['saved'], [True])
        self.assertTrue(discovered['loaded'])

        self.assertEqual(snapshot(self.default_home), default_before)
        self.assertIsNone(snapshot(self.code_b / '.runtime/profiles'))

    def test_bad_configuration_in_real_import_path_writes_nothing(self):
        (self.root / 'real').mkdir()
        (self.root / 'linked').symlink_to(self.root / 'real', target_is_directory=True)
        (self.root / 'a-file').write_bytes(b'not a directory')
        before = snapshot(self.root)
        for value in ['', 'relative-profiles', str(self.root / 'linked'), str(self.root / 'a-file')]:
            with self.subTest(value=value):
                completed = self.run_driver(self.code_a, 'create', str(self.save_file), home=value, check=False)
                self.assertNotEqual(completed.returncode, 0)
                self.assertIn('ValueError', completed.stderr)
        self.assertEqual(snapshot(self.root), before)


if __name__ == '__main__':
    unittest.main()
