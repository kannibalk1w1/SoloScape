import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import managed_fixture as fx
import managed_install as mi
import managed_runtime


class RuntimeBinding(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='runtime-'))
        self.addCleanup(self.cleanup)
        (self.tmp / 'profiles').mkdir()
        path, digest, _ = fx.make_real_package(self.tmp, 'r1')
        self.root = self.tmp / 'install'
        self.version = mi.install_first(self.root, path, digest, self.tmp / 'profiles', self.tmp / 'cache', self.tmp / 'launcher')
        self.cfg = mi.load_config(self.root)

    def cleanup(self):
        for base, dirs, _ in os.walk(self.tmp):
            for d in dirs:
                os.chmod(Path(base) / d, 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def configure(self, **env):
        code = ('import sys, json; sys.path.insert(0, %r); import managed_runtime, local_dev, profiles\n'
                'print(json.dumps([managed_runtime.configure(), str(local_dev.RUNTIME), str(profiles.PROFILES)]))'
                % str(self.root / 'versions' / self.version / 'scripts'))
        base = mi.child_environment(self.root, self.cfg, {k: v for k, v in os.environ.items() if not k.startswith('SOLOSCAPE_')})
        base.update(env)
        return subprocess.run([sys.executable, '-B', '-c', code], env=base, capture_output=True, text=True, cwd=self.tmp)

    def test_unmanaged_configure_and_guard_do_nothing(self):
        old = os.environ.pop(managed_runtime.MANAGED_ROOT_ENV, None)
        try:
            self.assertIsNone(managed_runtime.configure())
            self.assertIsNone(managed_runtime.open_guard())
        finally:
            if old is not None:
                os.environ[managed_runtime.MANAGED_ROOT_ENV] = old

    def test_binds_context_outside_the_payload_and_keys_it_by_version(self):
        result = self.configure()
        self.assertEqual(result.returncode, 0, result.stderr)
        info, runtime, profiles_home = json.loads(result.stdout)
        self.assertEqual(info['release'], 'r1')
        self.assertTrue(runtime.startswith(str(self.tmp / 'launcher' / 'version-contexts')))
        self.assertEqual(profiles_home, str(self.tmp / 'profiles'))

    def test_a_modified_script_or_shared_state_inside_the_payload_is_refused(self):
        script = self.root / 'versions' / self.version / 'scripts' / 'deck_awake.py'
        os.chmod(script.parent, 0o755)
        os.chmod(script, 0o644)
        script.write_bytes(script.read_bytes() + b'# tampered\n')
        self.assertNotEqual(self.configure().returncode, 0)
        script.write_bytes(script.read_bytes()[:-len(b'# tampered\n')])
        os.chmod(script, 0o444)
        self.assertEqual(self.configure().returncode, 0)
        refused = self.configure(SOLOSCAPE_CACHE_HOME=str(self.root / 'versions' / self.version / 'cache'))
        self.assertNotEqual(refused.returncode, 0)

    def test_open_guard_is_an_independent_shared_description_that_blocks_apply(self):
        os.environ[managed_runtime.MANAGED_ROOT_ENV] = str(self.root)
        self.addCleanup(os.environ.pop, managed_runtime.MANAGED_ROOT_ENV)
        with managed_runtime.open_guard():
            with self.assertRaises(mi.Busy):
                mi.acquire(self.root, 'exclusive')
            mi.acquire(self.root, 'shared').close()  # other launchers may still share
        mi.acquire(self.root, 'exclusive').close()


if __name__ == '__main__':
    unittest.main()
