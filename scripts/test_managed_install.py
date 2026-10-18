import fcntl
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import managed_fixture as fx
import managed_install as mi
import update_package

SCRIPTS = Path(__file__).resolve().parent


class InstallCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='managed-'))
        self.addCleanup(self.cleanup)
        self.home = self.tmp / 'profiles'
        self.home.mkdir()
        self.root = self.tmp / 'install'

    def cleanup(self):
        for base, dirs, _ in os.walk(self.tmp):
            for d in dirs:
                os.chmod(Path(base) / d, 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install(self, release='r1', **options):
        path, digest, files = fx.make_package(self.tmp, release, **options)
        a = mi.install_first(self.root, path, digest, self.home, self.tmp / 'cache', self.tmp / 'launcher', release=release)
        self.cfg = mi.load_config(self.root)
        return a

    def stage(self, release, storage=(0, 1), **options):
        path, digest, files = fx.make_package(self.tmp, release, storage=storage, **options)
        return update_package.install_zip(self.root, path, digest, expected_release=release)['id']


class FirstInstall(InstallCase):
    def test_creates_guard_pointer_config_bootstrap_and_sealed_version(self):
        a = self.install()
        self.assertEqual(mi.read_pointer(self.root), {'current': a, 'previous': None})
        self.assertEqual(sorted(p.name for p in (self.root / 'bootstrap').iterdir()), sorted(mi.BOOTSTRAP_FILES))
        self.assertEqual(mi.identity(self.root)['release'], 'r1')
        manifest = self.root / 'versions' / a / 'soloscape-runtime.json'
        self.assertEqual(manifest.stat().st_mode & 0o222, 0)
        self.assertTrue(os.access(self.root / 'versions' / a / 'scripts/launcher.sh', os.X_OK))
        self.assertEqual(oct((self.root / 'versions' / a / 'upstream').stat().st_mode & 0o777), '0o555')
        self.assertEqual(stat_mode(self.root / mi.GUARD), 0o600)
        self.assertEqual(json.loads((self.root / 'install.json').read_text())['profile_home'], str(self.home))

    def test_nested_or_shared_homes_and_nonempty_roots_are_refused(self):
        path, digest, _ = fx.make_package(self.tmp, 'r1')
        with self.assertRaises(mi.InstallError):
            mi.install_first(self.root, path, digest, self.home, self.home / 'cache', self.tmp / 'l')
        self.root.mkdir()
        (self.root / 'x').write_text('x')
        with self.assertRaises(mi.InstallError):
            mi.install_first(self.root, path, digest, self.home, self.tmp / 'c', self.tmp / 'l')

    def test_wrong_digest_leaves_no_usable_install(self):
        path, digest, _ = fx.make_package(self.tmp, 'r1')
        with self.assertRaises(update_package.PackageError):
            mi.install_first(self.root, path, '0' * 64, self.home, self.tmp / 'c', self.tmp / 'l')
        self.assertFalse((self.root / mi.POINTER).exists())


def stat_mode(path):
    return os.stat(path).st_mode & 0o777


class Activation(InstallCase):
    def test_good_update_switches_pointer_keeps_saves_and_prunes_only_unreferenced(self):
        a = self.install('r1')
        profile, save = fx.make_profile(self.home)
        before = save.read_bytes()
        b = self.stage('r2')
        mi.activate(self.root, b)
        self.assertEqual(mi.read_pointer(self.root), {'current': b, 'previous': a})
        self.assertEqual(save.read_bytes(), before)
        c = self.stage('r3')
        mi.write_candidate(self.root, c, 'r3', '0' * 64)
        mi.activate(self.root, c)
        self.assertEqual(mi.read_pointer(self.root), {'current': c, 'previous': b})
        self.assertEqual(sorted(os.listdir(self.root / 'versions')), sorted([b, c]))

    def test_already_installed_and_unknown_candidates_are_refused(self):
        a = self.install()
        with self.assertRaises(mi.InstallError):
            mi.activate(self.root, a)
        with self.assertRaises(mi.InstallError):
            mi.activate(self.root, '0' * 64)
        with self.assertRaises(mi.InstallError):
            mi.activate(self.root, 'not-hex')

    def test_unresolved_session_record_blocks_activation_and_rollback(self):
        a = self.install()
        b = self.stage('r2')
        profile, _ = fx.make_profile(self.home, session=True)
        with self.assertRaisesRegex(mi.InstallError, 'earlier session'):
            mi.activate(self.root, b)
        self.assertEqual(mi.read_pointer(self.root)['current'], a)
        (profile / 'session.json').unlink()
        mi.activate(self.root, b)
        (profile / 'session.json').write_text('{}')
        with self.assertRaisesRegex(mi.InstallError, 'earlier session'):
            mi.rollback(self.root)
        self.assertEqual(mi.read_pointer(self.root)['current'], b)

    def test_a_running_world_profile_lock_blocks_activation(self):
        self.install()
        b = self.stage('r2')
        profile, _ = fx.make_profile(self.home)
        fd = os.open(profile / 'profile.lock', os.O_CREAT | os.O_RDWR, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            with self.assertRaisesRegex(mi.InstallError, 'running'):
                mi.activate(self.root, b)
        finally:
            os.close(fd)
        mi.activate(self.root, b)

    def test_a_held_lease_blocks_activation_including_one_inherited_by_an_orphan(self):
        a = self.install()
        b = self.stage('r2')
        lease = mi.acquire(self.root, 'shared')
        with self.assertRaises(mi.Busy):
            mi.activate(self.root, b)
        orphan = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], pass_fds=(lease.fd,))
        try:
            lease.close()  # the launcher is gone; the inherited description keeps the lease
            with self.assertRaises(mi.Busy):
                mi.activate(self.root, b)
        finally:
            orphan.terminate()
            orphan.wait()
        mi.activate(self.root, b)
        self.assertEqual(mi.read_pointer(self.root)['previous'], a)

    def test_current_is_resolved_after_the_lease_is_held(self):
        a = self.install()
        b = self.stage('r2')
        with mi.acquire(self.root, 'exclusive') as lease:
            code = ('import sys; sys.path.insert(0, %r); import managed_install as m\n'
                    'with m.acquire(%r, "shared", blocking=True) as l: print(l.current())' % (str(SCRIPTS), str(self.root)))
            waiter = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True)
            time.sleep(0.3)
            self.assertIsNone(waiter.poll())
            mi._publish(self.root, mi.POINTER, {'format': mi.FORMAT_POINTER, 'current': b, 'previous': a})
        self.assertEqual(waiter.communicate(timeout=10)[0].strip(), b)

    def test_tampered_candidate_or_current_is_refused(self):
        a = self.install()
        b = self.stage('r2')
        target = self.root / 'versions' / b / fx.SERVER
        os.chmod(target.parent, 0o755)
        os.chmod(target, 0o644)
        target.write_bytes(b'tampered')
        with self.assertRaisesRegex(mi.InstallError, 'failed verification'):
            mi.activate(self.root, b)
        self.assertEqual(mi.read_pointer(self.root)['current'], a)


class SaveFormat(InstallCase):
    def test_candidate_that_cannot_read_the_logical_storage_version_is_refused(self):
        a = self.install('r1')
        profile, save = fx.make_profile(self.home, storage_version=1)
        old_only = self.stage('r0', storage=(0,))
        before = save.read_bytes()
        with self.assertRaisesRegex(mi.InstallError, 'storage version 1.*cannot read'):
            mi.activate(self.root, old_only)
        self.assertEqual(save.read_bytes(), before)
        self.assertEqual(mi.read_pointer(self.root)['current'], a)

    def test_pending_journal_overrides_the_canonical_account_version(self):
        self.install('r1')
        profile, save = fx.make_profile(self.home, storage_version=0)
        journal = save.parent / mi.JOURNAL
        journal.mkdir()
        (journal / 'tester.toml').write_text('storage_version = 1\naccountName = "Tester"\n')
        (journal / mi.WORLD_FILE).write_text('world')
        (journal / 'manifest.tsv').write_text('x')
        self.assertEqual(mi.scan_profiles(self.home)[0]['storage_version'], 1)

    def test_version_one_without_world_file_and_damaged_saves_fail_closed(self):
        self.install('r1')
        b = self.stage('r2')
        profile, save = fx.make_profile(self.home, storage_version=1, world=False)
        with self.assertRaisesRegex(mi.InstallError, 'world file'):
            mi.activate(self.root, b)
        save.write_text('this is = = not toml')
        with self.assertRaisesRegex(mi.InstallError, 'damaged'):
            mi.activate(self.root, b)
        save.write_text('storage_version = "one"\n')
        with self.assertRaisesRegex(mi.InstallError, 'invalid storage version'):
            mi.activate(self.root, b)

    def test_rollback_refuses_a_previous_version_that_cannot_read_newer_saves(self):
        self.install('r0', storage=(0,))
        profile, save = fx.make_profile(self.home, storage_version=0, world=False)
        b = self.stage('r2', storage=(0, 1))
        mi.activate(self.root, b)
        save.write_text('storage_version = 1\naccountName = "Tester"\n')
        (save.parent / mi.WORLD_FILE).write_text('w')
        before = save.read_bytes()
        with self.assertRaisesRegex(mi.InstallError, 'cannot read'):
            mi.rollback(self.root)
        self.assertEqual(mi.read_pointer(self.root)['current'], b)
        self.assertEqual(save.read_bytes(), before)

    def test_rollback_keeps_newer_saved_progress(self):
        a = self.install('r1')
        profile, save = fx.make_profile(self.home)
        b = self.stage('r2')
        mi.activate(self.root, b)
        save.write_text('storage_version = 1\naccountName = "Tester"\nprogress = "played in r2"\n')
        newer = save.read_bytes()
        self.assertEqual(mi.rollback(self.root), a)
        self.assertEqual(mi.read_pointer(self.root), {'current': a, 'previous': b})
        self.assertEqual(save.read_bytes(), newer)
        self.assertTrue((self.root / 'versions' / b).is_dir())


class Crash(InstallCase):
    def activate_in_child(self, candidate, cutpoint):
        code = ('import sys; sys.path.insert(0, %r); import managed_install as m\nm.activate(%r, %r, cutpoint=%r)'
                % (str(SCRIPTS), str(self.root), candidate, cutpoint))
        return subprocess.run([sys.executable, '-c', code]).returncode

    def test_process_kill_before_replace_leaves_the_old_version_and_run_recovers(self):
        a = self.install('r1')
        b = self.stage('r2')
        self.assertEqual(self.activate_in_child(b, 'after-temp-fsync'), mi.CUT_EXIT)
        self.assertEqual(mi.read_pointer(self.root)['current'], a)
        self.assertTrue(any(p.name.startswith('.active.json.') for p in self.root.iterdir()))
        mi.recover(self.root)
        self.assertFalse(any(p.name.startswith('.active.json.') for p in self.root.iterdir()))
        self.assertFalse((self.root / mi.TRIAL).exists())  # trial named a candidate that never became current
        mi.activate(self.root, b)

    def test_process_kill_after_replace_leaves_the_new_version_in_trial(self):
        a = self.install('r1')
        b = self.stage('r2')
        self.assertEqual(self.activate_in_child(b, 'after-replace'), mi.CUT_EXIT)
        self.assertEqual(mi.read_pointer(self.root), {'current': b, 'previous': a})
        mi.recover(self.root)
        self.assertTrue((self.root / mi.TRIAL).exists())
        self.assertEqual(mi.rollback(self.root), a)

    def test_malformed_pointer_is_refused_not_guessed(self):
        self.install()
        (self.root / mi.POINTER).write_text('{"format": "soloscape-install-pointer-1", "current": "' + 'a' * 64 + '", "previous": "' + 'a' * 64 + '"}')
        with self.assertRaises(mi.InstallError):
            mi.read_pointer(self.root)


class RunLoop(InstallCase):
    def run_loop(self, **kw):
        env = dict(os.environ)
        return mi.run(self.root, base_env=env, output=lambda *a: self.log.append(' '.join(map(str, a))), **kw)

    def setUp(self):
        super().setUp()
        self.log = []
        self.marks = self.tmp / 'marks'
        self.marks.mkdir()

    def mark(self, name, code):
        return 'echo "$SOLOSCAPE_MANAGED_ROOT|$SOLOSCAPE_PROFILE_HOME|$SOLOSCAPE_CACHE_HOME|$SOLOSCAPE_LAUNCHER_HOME" > %s/%s\nexit %d\n' % (self.marks, name, code)

    def test_restart_request_applies_then_launches_the_new_version_with_external_state(self):
        a = self.install('r1', launcher=self.mark('A', 75))
        profile, save = fx.make_profile(self.home)
        before = save.read_bytes()
        b = self.stage('r2', launcher=self.mark('B', 0))
        mi.request_activation(self.root, b)
        self.assertEqual(self.run_loop(), 0)
        self.assertEqual(mi.read_pointer(self.root), {'current': b, 'previous': a})
        self.assertEqual((self.marks / 'B').read_text().strip(),
                         '|'.join([str(self.root), str(self.home), str(self.tmp / 'cache'), str(self.tmp / 'launcher')]))
        self.assertEqual(save.read_bytes(), before)
        self.assertEqual(mi.read_result(self.root)['ok'], True)
        self.assertFalse((self.root / mi.REQUEST).exists())

    def test_request_is_ignored_without_a_restart_exit_and_never_applied_later(self):
        a = self.install('r1', launcher=self.mark('A', 0))
        b = self.stage('r2', launcher=self.mark('B', 0))
        mi.request_activation(self.root, b)
        self.assertEqual(self.run_loop(), 0)
        self.assertEqual(mi.read_pointer(self.root)['current'], a)
        self.assertFalse((self.root / mi.REQUEST).exists())

    def test_refused_apply_keeps_the_player_on_the_working_version_with_a_plain_result(self):
        a = self.install('r1', launcher='if [ -e %s/once ]; then exit 0; fi; touch %s/once; exit 75\n' % (self.marks, self.marks))
        b = self.stage('r2', launcher=self.mark('B', 0))
        fx.make_profile(self.home, session=True)
        mi.request_activation(self.root, b)
        self.assertEqual(self.run_loop(), 0)
        self.assertEqual(mi.read_pointer(self.root)['current'], a)
        self.assertFalse((self.marks / 'B').exists())
        result = mi.read_result(self.root)
        self.assertFalse(result['ok'])
        self.assertIn('Update not applied', result['message'])

    def test_a_new_version_that_fails_at_once_is_rolled_back_and_the_old_one_relaunched(self):
        a = self.install('r1', launcher='if [ -e %s/A ]; then exit 0; fi; touch %s/A; exit 75\n' % (self.marks, self.marks))
        profile, save = fx.make_profile(self.home)
        before = save.read_bytes()
        b = self.stage('r2', launcher='exit 3\n')
        mi.request_activation(self.root, b)
        self.assertEqual(self.run_loop(), 0)
        self.assertEqual(mi.read_pointer(self.root)['current'], a)
        self.assertIn('previous version restored', ' '.join(self.log))
        self.assertFalse(mi.read_result(self.root)['ok'])
        self.assertEqual(save.read_bytes(), before)
        self.assertFalse((self.root / mi.TRIAL).exists())

    def test_trial_failure_rollback_is_still_gated_by_the_save_format(self):
        once = 'if [ -e %s/A ]; then exit 0; fi; touch %s/A; exit 75\n' % (self.marks, self.marks)
        a = self.install('r1', launcher=once, storage=(0,))
        profile, save = fx.make_profile(self.home, storage_version=0, world=False)
        # The new version writes storage version 1 progress and then dies at once.
        crash = ("printf 'storage_version = 1\\naccountName = \"Tester\"\\n' > %s; touch %s/%s; exit 3\n"
                 % (save, save.parent, '.soloscape-death-loot.v1'))
        b = self.stage('r2', launcher=crash, storage=(0, 1))
        mi.request_activation(self.root, b)
        self.assertEqual(self.run_loop(), 3)
        self.assertEqual(mi.read_pointer(self.root)['current'], b)  # rollback refused: r1 cannot read storage 1
        self.assertTrue(save.read_text().startswith('storage_version = 1'))
        self.assertIn('Could not restore the previous version', ' '.join(self.log))

    def test_the_launcher_inherits_a_shared_lease_so_an_orphan_blocks_apply(self):
        self.install('r1', launcher='sleep 0.2 & disown; exit 0\n')
        b = self.stage('r2')
        self.run_loop()
        # a backgrounded child outlived the launcher and inherited the descriptor
        with self.assertRaises(mi.Busy):
            mi.activate(self.root, b)
        time.sleep(0.6)
        mi.activate(self.root, b)

    def test_tampered_current_version_refuses_to_launch_without_switching(self):
        a = self.install('r1', launcher=self.mark('A', 0))
        target = self.root / 'versions' / a / fx.CLIENT
        os.chmod(target.parent, 0o755)
        os.chmod(target, 0o644)
        target.write_bytes(b'tampered')
        with self.assertRaises(mi.InstallError):
            self.run_loop()
        self.assertFalse((self.marks / 'A').exists())
        self.assertEqual(mi.read_pointer(self.root)['current'], a)


if __name__ == '__main__':
    unittest.main()
