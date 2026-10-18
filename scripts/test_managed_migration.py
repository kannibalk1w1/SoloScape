"""Adopting an existing source or Deck-export install, and keeping its state through update and rollback.

Every tree here is a disposable fixture with invented bytes. The password is a canary: it must never appear in
any output, record, copied file or install-root file, and login.json must stay byte-identical (even when empty).
"""
import ast
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import managed_fixture as fx
import managed_install as mi
import update_package as up

CANARY = 'canary-password-do-not-leak-7f3a'
SCRIPTS = Path(__file__).resolve().parent


def snapshot(path):
    """Relative path -> (mode, sha256 | link target) for everything under path."""
    result = {}
    for base, dirs, names in os.walk(path):
        for name in dirs + names:
            full = Path(base) / name
            rel = full.relative_to(path).as_posix()
            if full.is_symlink():
                result[rel] = ('link', os.readlink(full))
            elif full.is_dir():
                result[rel] = ('dir', oct(full.stat().st_mode & 0o7777))
            else:
                result[rel] = (oct(full.stat().st_mode & 0o7777), hashlib.sha256(full.read_bytes()).hexdigest())
    return result


class Migration(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='adopt-'))
        self.addCleanup(self.cleanup)
        self.path, self.digest, self.files = fx.make_code_only_package(self.tmp, 'r1')
        self.old = self.make_old()
        self.root = self.tmp / 'install'
        self.launcher = self.tmp / 'launcher'

    def cleanup(self):
        for base, dirs, _ in os.walk(self.tmp):
            for d in dirs:
                os.chmod(Path(base) / d, 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_old(self, art=True, settings=True, password=CANARY, storage_version=1, name='old-deck'):
        old = fx.make_checkout(self.tmp, self.files, name=name)
        (old / 'scripts').mkdir(exist_ok=True)
        (old / 'scripts/local_dev.py').write_text('# stand-in for the old install\n')
        runtime = old / '.runtime'
        for version, java in (('jdk21', 'java21'), ('jdk8', 'java8')):
            target = runtime / 'jdks' / version / 'bin/java'
            target.parent.mkdir(parents=True)
            target.write_text('#!/bin/sh\n# ' + java + '\n')
            target.chmod(0o755)
        (old / 'config').mkdir()
        (old / 'config/local.env').write_text("SERVER_JAVA='%s'\nCLIENT_JAVA=%s\nIGNORED=$(echo no)\n" % (
            runtime / 'jdks/jdk21/bin/java', runtime / 'jdks/jdk8/bin/java'))
        cache = old / 'upstream/game-server/data/cache'
        cache.mkdir(parents=True)
        (cache / 'main_file_cache.dat2').write_bytes(b'synthetic cache')
        (runtime / 'profiles').mkdir()
        self.directory, self.save = fx.make_profile(runtime / 'profiles', storage_version=storage_version)
        (self.directory / 'login.json').write_text(json.dumps({'account': 'tester', 'password': password}))
        (self.directory / 'client-home').mkdir()
        (self.directory / 'client-home/prefs.properties').write_text('rememberLogin=true\nscale=2\n')
        (self.directory / 'backups').mkdir()
        (self.directory / 'backups/20261001T000000-aaaaaaaa.zip').write_bytes(b'synthetic backup')
        if art:
            (runtime / 'launcher-art').mkdir()
            (runtime / 'launcher-art/brazier.jpg').write_bytes(b'synthetic jpg')
            (runtime / 'launcher-art/brazier-flames.png').write_bytes(b'synthetic png')
        if settings:
            (runtime / 'launcher-settings.json').write_text('{"format": 1, "port": 43600}')
        return old

    def adopt(self, **kw):
        return mi.adopt(self.root, self.old, self.path, self.digest, launcher_home=kw.pop('launcher_home', self.launcher), **kw)

    def assert_no_install(self):
        self.assertTrue(not self.root.exists() or not any(self.root.iterdir()))


class Adopting(Migration):
    def test_state_stays_where_it_is_and_the_old_tree_is_untouched(self):
        before = snapshot(self.old)
        report = self.adopt()
        self.assertEqual(snapshot(self.old), before)
        cfg = mi.load_config(self.root)
        self.assertEqual(cfg['profile_home'], str(self.old / '.runtime/profiles'))
        self.assertEqual(cfg['cache_home'], str(self.old / 'upstream/game-server/data/cache'))
        self.assertEqual(cfg['server_java'], str(self.old / '.runtime/jdks/jdk21/bin/java'))
        self.assertEqual(cfg['client_java'], str(self.old / '.runtime/jdks/jdk8/bin/java'))
        self.assertEqual(cfg['supply_roots'], [str(self.old)])
        self.assertEqual(mi.identity(self.root)['id'], report['version'])
        self.assertEqual(report['profiles'], [{'label': 'Tester', 'storage_version': 1, 'login': 'remembered'}])
        self.assertNotIn(CANARY, json.dumps(report))

    def test_settings_and_artwork_are_copied_never_moved_or_overwritten(self):
        self.launcher.mkdir()
        (self.launcher / 'launcher-settings.json').write_text('{"format": 1, "port": 43700}')
        report = self.adopt()
        self.assertEqual((self.launcher / 'launcher-settings.json').read_text(), '{"format": 1, "port": 43700}')
        self.assertTrue(any('launcher-settings.json already exists' in n for n in report['notes']))
        self.assertEqual((self.launcher / 'launcher-art/brazier.jpg').read_bytes(), b'synthetic jpg')
        self.assertEqual((self.launcher / 'launcher-art/brazier-flames.png').read_bytes(), b'synthetic png')
        self.assertEqual(mi.status(self.root)['launcher_art'], {'brazier.jpg': True, 'brazier-flames.png': True})
        self.assertTrue((self.old / '.runtime/launcher-art/brazier.jpg').is_file())

    def test_missing_optional_artwork_is_reported_plainly_and_does_not_block(self):
        shutil.rmtree(self.old / '.runtime/launcher-art')
        report = self.adopt()
        self.assertEqual(sum('was not found in the old install' in n for n in report['notes']), 2)
        self.assertTrue(any('brazier-flames.png' in n for n in report['notes']))
        self.assertEqual(mi.status(self.root)['launcher_art'], {'brazier.jpg': False, 'brazier-flames.png': False})
        self.assertEqual(mi.identity(self.root)['release'], 'r1')

    def test_a_linked_source_file_is_never_followed(self):
        art = self.old / '.runtime/launcher-art/brazier.jpg'
        art.unlink()
        outside = self.tmp / 'outside.jpg'
        outside.write_bytes(b'elsewhere')
        art.symlink_to(outside)
        with self.assertRaises(mi.InstallError):
            self.adopt()

    def test_an_empty_or_missing_remembered_login_is_reported_and_left_alone(self):
        (self.directory / 'login.json').write_text(json.dumps({'account': 'tester', 'password': ''}))
        other, _ = fx.make_profile(self.old / '.runtime/profiles', label='Second', account='second')
        (other / 'login.json').unlink(missing_ok=True)
        before = (self.directory / 'login.json').read_bytes()
        report = self.adopt()
        logins = sorted(row['login'] for row in report['profiles'])
        self.assertEqual(logins, ['empty', 'missing'])
        self.assertEqual(sum('has no remembered password' in n for n in report['notes']), 2)
        self.assertEqual((self.directory / 'login.json').read_bytes(), before)
        self.assertFalse((other / 'login.json').exists())

    def test_the_old_launcher_folder_that_holds_the_profiles_cannot_be_reused(self):
        with self.assertRaises(mi.InstallError) as caught:
            mi.adopt(self.root, self.old, self.path, self.digest)
        self.assertIn('separate launcher folder', str(caught.exception))
        self.assert_no_install()

    def test_a_separate_old_launcher_folder_is_used_in_place(self):
        shared = self.tmp / 'shared-launcher'
        shared.mkdir()
        (self.old / 'config/local.env').write_text("SOLOSCAPE_LAUNCHER_HOME=%s\n" % shared)
        report = mi.adopt(self.root, self.old, self.path, self.digest)
        self.assertEqual(mi.load_config(self.root)['launcher_home'], str(shared))
        self.assertEqual(report['notes'], [])

    def test_unrelated_or_linked_folders_are_refused(self):
        with self.assertRaises(mi.InstallError):
            mi.adopt(self.root, self.tmp, self.path, self.digest, launcher_home=self.launcher)
        link = self.tmp / 'link-to-old'
        link.symlink_to(self.old)
        with self.assertRaises(mi.InstallError):
            mi.adopt(self.root, link, self.path, self.digest, launcher_home=self.launcher)
        self.assert_no_install()

    def test_an_unresolved_session_record_blocks_adoption_and_leaves_nothing(self):
        (self.directory / 'session.json').write_text('{}')
        before = snapshot(self.old)
        with self.assertRaises(mi.InstallError) as caught:
            self.adopt()
        self.assertIn('Recover Session', str(caught.exception))
        self.assert_no_install()
        self.assertFalse(self.launcher.exists())
        self.assertEqual(snapshot(self.old), before)

    def test_a_running_world_blocks_adoption(self):
        import fcntl
        lock = open(self.directory / 'profile.lock', 'w')
        self.addCleanup(lock.close)
        fcntl.flock(lock, fcntl.LOCK_EX)
        with self.assertRaises(mi.InstallError) as caught:
            self.adopt()
        self.assertIn('running', str(caught.exception))
        self.assert_no_install()

    def test_saves_this_first_version_cannot_read_block_adoption(self):
        path, digest, _ = fx.make_code_only_package(self.tmp, 'r0', storage=(0,))
        with self.assertRaises(mi.InstallError) as caught:
            mi.adopt(self.root, self.old, path, digest, launcher_home=self.launcher)
        self.assertIn('cannot read', str(caught.exception))
        self.assert_no_install()

    def test_the_cli_adopts_without_printing_secrets(self):
        run = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'managed_install.py'), 'init', str(self.root), '--package', str(self.path),
                              '--sha256', self.digest, '--launcher-home', str(self.launcher), '--adopt', str(self.old)],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn(CANARY, run.stdout + run.stderr)
        self.assertEqual(json.loads(run.stdout)['profiles'][0]['login'], 'remembered')
        refused = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'managed_install.py'), 'init', str(self.tmp / 'again'), '--package', str(self.path),
                                  '--sha256', self.digest, '--adopt', str(self.old), '--profile-home', str(self.tmp / 'p'),
                                  '--launcher-home', str(self.tmp / 'l2')], capture_output=True, text=True)
        self.assertEqual(refused.returncode, 2)


class KeepingState(Migration):
    def stage(self, release, **kw):
        path, digest, files = fx.make_code_only_package(self.tmp, release, **kw)
        return up.install_zip(self.root, path, digest, expected_release=release, supply_roots=mi.load_config(self.root)['supply_roots'])['id']

    def state_snapshot(self):
        return {'profiles': snapshot(self.old / '.runtime/profiles'), 'cache': snapshot(self.old / 'upstream/game-server/data/cache'),
                'launcher': snapshot(self.launcher), 'old_art': snapshot(self.old / '.runtime/launcher-art')}

    def test_update_and_rollback_leave_every_kind_of_state_byte_identical(self):
        self.adopt()
        before = self.state_snapshot()
        second = self.stage('r2')
        mi.activate(self.root, second)
        self.assertEqual(mi.identity(self.root)['release'], 'r2')
        self.assertEqual(self.state_snapshot(), before)
        mi.rollback(self.root)
        self.assertEqual(mi.identity(self.root)['release'], 'r1')
        self.assertEqual(self.state_snapshot(), before)
        login = json.loads((self.directory / 'login.json').read_text())
        self.assertEqual(login, {'account': 'tester', 'password': CANARY})
        self.assertEqual((self.directory / 'client-home/prefs.properties').read_text(), 'rememberLogin=true\nscale=2\n')

    def test_an_update_that_cannot_read_the_saves_is_refused_without_touching_them(self):
        self.adopt()
        before = self.state_snapshot()
        old_only = self.stage('r2', storage=(0,))
        with self.assertRaises(mi.InstallError) as caught:
            mi.activate(self.root, old_only)
        self.assertIn('cannot read', str(caught.exception))
        self.assertEqual(self.state_snapshot(), before)
        self.assertEqual(mi.identity(self.root)['release'], 'r1')

    def test_rollback_after_newer_progress_keeps_the_progress(self):
        self.adopt()
        mi.activate(self.root, self.stage('r2'))
        newer = self.save.read_text().replace('progress = "start"', 'progress = "newer version"')
        self.assertNotEqual(newer, self.save.read_text())
        self.save.write_text(newer)
        mi.rollback(self.root)
        self.assertEqual(self.save.read_text(), newer)

    def test_a_running_world_or_orphan_session_blocks_apply_after_adoption(self):
        self.adopt()
        second = self.stage('r2')
        (self.directory / 'session.json').write_text('{}')
        with self.assertRaises(mi.InstallError):
            mi.activate(self.root, second)
        (self.directory / 'session.json').unlink()
        with mi.acquire(self.root, 'shared'):
            with self.assertRaises(mi.Busy):
                mi.activate(self.root, second)

    def test_the_password_never_reaches_the_install_root_launcher_home_or_any_output(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            self.adopt()
            second = self.stage('r2')
            mi.activate(self.root, second)
            mi.record_result(self.root, True, 'Updated.', second)
            mi.rollback(self.root)
            print(json.dumps(mi.status(self.root)))
        self.assertNotIn(CANARY, out.getvalue() + err.getvalue())
        needle = CANARY.encode()
        for tree in (self.root, self.launcher):
            for base, _, names in os.walk(tree):
                for name in names:
                    self.assertNotIn(needle, (Path(base) / name).read_bytes(), name)
        cli = subprocess.run([sys.executable, '-B', str(self.root / 'bootstrap/managed_install.py'), 'status', str(self.root)],
                             capture_output=True, text=True)
        self.assertNotIn(CANARY, cli.stdout + cli.stderr)
        self.assertIn('"login": "remembered"', cli.stdout)

    def test_status_reports_art_and_login_state_without_secrets(self):
        self.adopt()
        status = mi.status(self.root)
        self.assertEqual(status['launcher_art'], {'brazier.jpg': True, 'brazier-flames.png': True})
        self.assertEqual(status['profiles'][0]['login'], 'remembered')
        self.assertEqual(status['supply_roots'], [str(self.old)])

    def test_the_updater_never_deletes_artwork_even_after_pruning_old_versions(self):
        self.adopt()
        for release in ('r2', 'r3'):
            mi.activate(self.root, self.stage(release))
        self.assertEqual(mi.status(self.root)['launcher_art'], {'brazier.jpg': True, 'brazier-flames.png': True})


class LoginState(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='login-'))
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def check(self, content, expected):
        (self.tmp / 'login.json').write_text(content)
        self.assertEqual(mi.login_state(self.tmp), expected)

    def test_classification(self):
        self.assertEqual(mi.login_state(self.tmp), 'missing')
        self.check('{"account": "a", "password": "x"}', 'remembered')
        self.check('{"account": "a", "password": ""}', 'empty')
        self.check('{"account": "a"}', 'empty')
        self.check('{"account": "a", "password": 7}', 'empty')
        self.check('not json', 'unreadable')
        self.check('{"password": "a", "password": "b"}', 'unreadable')
        self.check('x' * 5000, 'unreadable')

    def test_a_linked_login_file_is_unreadable_not_followed(self):
        (self.tmp / 'real.json').write_text('{"password": "x"}')
        (self.tmp / 'login.json').symlink_to(self.tmp / 'real.json')
        self.assertEqual(mi.login_state(self.tmp), 'unreadable')


class Boundaries(unittest.TestCase):
    def test_the_managed_updater_never_touches_cross_device_save_bundles(self):
        for name in ('managed_install', 'update_package', 'update_manager', 'managed_runtime', 'runtime_manifest', 'package_builder'):
            tree = ast.parse((SCRIPTS / (name + '.py')).read_text())
            imported = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
            imported |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
            self.assertNotIn('save_sync', imported, name)


if __name__ == '__main__':
    unittest.main()
