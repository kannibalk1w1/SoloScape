"""User-triggered rollback: advisory pre-check, launcher request, and the bootstrap's stopped-launcher handshake."""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

import managed_fixture as fx
import managed_install as mi
import update_manager as um
import update_package as up
from test_migration_support import snapshot


class RollbackCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rollback-'))
        self.addCleanup(self.cleanup)
        self.home = self.tmp / 'profiles'
        self.home.mkdir()
        self.root = self.tmp / 'install'
        self.marks = self.tmp / 'marks'
        self.marks.mkdir()

    def cleanup(self):
        for base, dirs, _ in os.walk(self.tmp):
            for d in dirs:
                os.chmod(Path(base) / d, 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install(self, release='r1', **options):
        path, digest, files = fx.make_package(self.tmp, release, **options)
        return mi.install_first(self.root, path, digest, self.home, self.tmp / 'cache', self.tmp / 'launcher', release=release)

    def stage(self, release, storage=(0, 1), **options):
        path, digest, _ = fx.make_package(self.tmp, release, storage=storage, **options)
        return up.install_zip(self.root, path, digest, expected_release=release)['id']

    def two_versions(self, **second):
        a = self.install('r1', launcher='if [ -e %s/A ]; then exit 0; fi; touch %s/A; exit 75\n' % (self.marks, self.marks))
        b = self.stage('r2', **second)
        mi.activate(self.root, b)
        return a, b

    def manager(self):
        os.environ['SOLOSCAPE_MANAGED_ROOT'] = str(self.root)
        self.addCleanup(os.environ.pop, 'SOLOSCAPE_MANAGED_ROOT', None)
        current = mi.read_pointer(self.root)['current']
        return um.UpdateManager({'release': mi.identity(self.root)['release'], 'version': current, 'storage_versions': [0, 1]})

    def run_loop(self):
        return mi.run(self.root, trial_seconds=0, output=lambda *a, **k: None)


class Preflight(RollbackCase):
    def test_no_earlier_version(self):
        self.install()
        state = mi.rollback_preflight(self.root)
        self.assertIsNone(state['previous'])
        self.assertEqual(state['reasons'], ['There is no earlier version to return to.'])

    def test_previous_version_and_no_reasons_after_an_update(self):
        a, _ = self.two_versions()
        state = mi.rollback_preflight(self.root)
        self.assertEqual(state, {'previous': {'release': 'r1', 'id': a}, 'reasons': []})

    def test_each_blocker_is_a_plain_actionable_reason(self):
        self.two_versions()
        profile, _ = fx.make_profile(self.home, session=True, label='Ana')
        reasons = mi.rollback_preflight(self.root)['reasons']
        self.assertTrue(any('Ana' in r and 'Recover Session' in r for r in reasons), reasons)

    def test_a_previous_version_that_cannot_read_the_saves_is_refused_without_touching_them(self):
        self.install('r1', storage=(0,))
        _, save = fx.make_profile(self.home, storage_version=1)
        b = self.stage('r2', storage=(0, 1))
        mi.activate(self.root, b)
        before = save.read_bytes()
        reasons = mi.rollback_preflight(self.root)['reasons']
        self.assertTrue(any('cannot read' in r for r in reasons), reasons)
        self.assertEqual(save.read_bytes(), before)

    def test_a_damaged_previous_version_is_reported(self):
        a, _ = self.two_versions()
        victim = self.root / 'versions' / a / 'scripts/launcher.sh'
        os.chmod(victim.parent, 0o755)
        os.chmod(victim, 0o644)
        victim.write_text('tampered')
        state = mi.rollback_preflight(self.root)
        self.assertEqual(state['previous']['id'], a)
        self.assertTrue(any('failed verification' in r for r in state['reasons']))


class Manager(RollbackCase):
    def test_status_shows_current_previous_and_whether_a_rollback_is_possible(self):
        a, b = self.two_versions()
        status = self.manager().status()
        self.assertEqual(status['installed']['release'], 'r2')
        self.assertEqual(status['previous'], {'release': 'r1', 'id': a})
        self.assertTrue(status['can_rollback'])
        self.assertEqual(status['rollback_message'], '')

    def test_status_explains_a_refusal_and_disables_the_button(self):
        self.two_versions()
        fx.make_profile(self.home, session=True, label='Ana')
        status = self.manager().status()
        self.assertFalse(status['can_rollback'])
        self.assertIn('Recover Session', status['rollback_message'])

    def test_a_running_world_disables_rollback_and_the_action_refuses(self):
        self.two_versions()
        manager = self.manager()
        self.assertFalse(manager.status(world_running=True)['can_rollback'])
        with self.assertRaises(RuntimeError) as caught:
            manager.rollback(world_running=True)
        self.assertIn('Save & Quit', str(caught.exception))
        self.assertFalse((self.root / mi.REQUEST).exists())

    def test_the_action_records_a_request_and_explains_that_progress_is_kept(self):
        a, _ = self.two_versions()
        reply = self.manager().rollback(world_running=False)
        self.assertTrue(reply['restart'])
        self.assertIn('nothing is restored from a backup', reply['message'])
        self.assertIn('current progress stays', reply['message'])
        self.assertEqual(mi._take_request(self.root), mi.ROLLBACK)
        self.assertEqual(mi.read_pointer(self.root)['previous'], a)  # asking changes nothing

    def test_a_refused_action_raises_the_reasons_and_records_nothing(self):
        self.install()
        manager = self.manager()
        with self.assertRaises(RuntimeError) as caught:
            manager.rollback(world_running=False)
        self.assertIn('no earlier version', str(caught.exception))
        self.assertFalse((self.root / mi.REQUEST).exists())

    def test_not_managed_cannot_roll_back(self):
        with self.assertRaises(RuntimeError):
            um.UpdateManager(None).rollback(world_running=False)


class Handshake(RollbackCase):
    def test_a_stopped_launcher_request_returns_to_the_previous_version_and_keeps_newer_progress(self):
        a, b = self.two_versions()
        # the running (newer) version exits 75 once, asking to be rolled back; the older one then runs to completion
        profile, save = fx.make_profile(self.home)
        newer = save.read_text().replace('progress = "start"', 'progress = "newer version"')
        save.write_text(newer)
        backups = snapshot(profile)
        mi.request_rollback(self.root)
        code = mi.run(self.root, trial_seconds=0, output=lambda *a, **k: None,
                      launcher=['bash', '-c', 'if [ -e %s/once ]; then exit 0; fi; touch %s/once; exit 75' % (self.marks, self.marks)])
        self.assertEqual(code, 0)
        self.assertEqual(mi.read_pointer(self.root), {'current': a, 'previous': b})
        self.assertEqual(save.read_text(), newer)
        self.assertEqual(snapshot(profile), backups)
        result = mi.read_result(self.root)
        self.assertTrue(result['ok'])
        self.assertIn('Rolled back to release r1', result['message'])
        self.assertIn('nothing was restored from a backup', result['message'])

    def test_a_refusal_at_the_handshake_keeps_the_working_version_with_a_plain_result(self):
        a, b = self.two_versions()
        fx.make_profile(self.home, session=True)
        mi.request_rollback(self.root)
        code = mi.run(self.root, trial_seconds=0, output=lambda *a, **k: None,
                      launcher=['bash', '-c', 'if [ -e %s/once ]; then exit 0; fi; touch %s/once; exit 75' % (self.marks, self.marks)])
        self.assertEqual(code, 0)
        self.assertEqual(mi.read_pointer(self.root)['current'], b)
        result = mi.read_result(self.root)
        self.assertFalse(result['ok'])
        self.assertIn('Roll back not applied', result['message'])

    def test_a_request_without_a_restart_exit_is_discarded_and_never_applied_later(self):
        a, b = self.two_versions()
        mi.request_rollback(self.root)
        self.assertEqual(mi.run(self.root, trial_seconds=0, output=lambda *a, **k: None, launcher=['bash', '-c', 'exit 0']), 0)
        self.assertEqual(mi.read_pointer(self.root)['current'], b)
        self.assertFalse((self.root / mi.REQUEST).exists())

    def test_rolling_forward_again_works_because_the_old_current_becomes_previous(self):
        a, b = self.two_versions()
        mi.rollback(self.root)
        self.assertEqual(mi.rollback_preflight(self.root)['previous']['id'], b)
        mi.rollback(self.root)
        self.assertEqual(mi.read_pointer(self.root)['current'], b)


if __name__ == '__main__':
    unittest.main()
