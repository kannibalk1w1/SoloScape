import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

import managed_fixture as fx
import managed_install as mi
import release_updates
import update_manager as um
import update_package

SCRIPTS = Path(__file__).resolve().parent


def release_result(tag, package=None):
    return release_updates.result('release_available', 'Published release: ' + tag + '.', tag=tag, title=tag, notes='Plain notes',
                                  url='https://github.com/kannibalk1w1/SoloScape/releases/tag/' + tag, bundle=None, package=package) | {
        'install_available': package is not None}


class ManagerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='mgr-'))
        self.addCleanup(self.cleanup)
        self.home = self.tmp / 'profiles'
        self.home.mkdir()
        self.root = self.tmp / 'install'
        path, digest, _ = fx.make_package(self.tmp, 'r1')
        self.current = mi.install_first(self.root, path, digest, self.home, self.tmp / 'cache', self.tmp / 'launcher')
        os.environ['SOLOSCAPE_MANAGED_ROOT'] = str(self.root)
        self.addCleanup(os.environ.pop, 'SOLOSCAPE_MANAGED_ROOT', None)
        self.managed = {'release': 'r1', 'version': self.current, 'storage_versions': [0, 1]}
        self.payload_path, self.payload_digest, self.files = fx.make_package(self.tmp, 'r2')
        self.payload = self.payload_path.read_bytes()
        self.package = dict(name='soloscape-package-r2.zip', size=len(self.payload), sha256=self.payload_digest,
                            url=release_updates.asset_url('r2', 'soloscape-package-r2.zip'), tag='r2')

    def cleanup(self):
        for base, dirs, _ in os.walk(self.tmp):
            for d in dirs:
                os.chmod(Path(base) / d, 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def manager(self, release=None, transport=None, **kw):
        release = release or release_result('r2', self.package)
        return um.UpdateManager(self.managed, transport=transport or (lambda url: io_bytes(self.payload)), check=lambda: release, **kw)

    def wait(self, manager, stage, seconds=10):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if manager.status()['stage'] == stage:
                return manager.status()
            time.sleep(0.02)
        self.fail('stage %s never reached: %s' % (stage, manager.status()))


def io_bytes(data):
    import io
    return io.BytesIO(data)


class Flow(ManagerCase):
    def test_check_download_apply_request_end_to_end(self):
        manager = self.manager()
        checked = manager.check()
        self.assertEqual(checked['installed']['release'], 'r1')
        self.assertTrue(checked['install_available'])
        self.assertTrue(manager.status()['can_download'])
        self.assertFalse(manager.status()['can_apply'])
        manager.download()
        status = self.wait(manager, 'staged')
        self.assertEqual(status['candidate']['release'], 'r2')
        self.assertTrue(status['can_apply'])
        self.assertFalse(status['can_download'])  # already downloaded: nothing left to fetch
        self.assertFalse(status['can_download'] and status['stage'] == 'downloading')
        result = manager.apply(world_running=False)
        self.assertTrue(result['restart'])
        self.assertEqual(mi._take_request(self.root), status['candidate']['id'])

    def test_staged_candidate_survives_a_relaunch_without_downloading_again(self):
        first = self.manager()
        first.check()
        first.download()
        self.wait(first, 'staged')
        again = self.manager(transport=lambda url: self.fail('must not download again'))
        self.assertTrue(again.status()['can_apply'])
        again.check()
        again.download()
        self.assertEqual(again.status()['stage'], 'staged')

    def test_no_release_offline_and_unpackaged_releases_change_nothing(self):
        for state, result in (('no_public_release', release_updates.result('no_public_release', 'No public SoloScape release is available yet.')),
                              ('unavailable', release_updates.result('unavailable', 'Update check unavailable. You can keep using your installed version.')),
                              ('no package', release_result('r2', None))):
            with self.subTest(state):
                manager = self.manager(release=result, transport=lambda url: self.fail('no network download'))
                self.assertEqual(manager.check()['installed']['release'], 'r1')
                self.assertFalse(manager.status()['can_download'])
                with self.assertRaisesRegex(RuntimeError, 'Check for updates first'):
                    manager.download()
        self.assertEqual(os.listdir(self.root / 'versions'), [self.current])

    def test_the_same_release_label_is_reported_as_up_to_date(self):
        package = dict(self.package, tag='r1', url=release_updates.asset_url('r1', 'soloscape-package-r2.zip'))
        manager = self.manager(release=release_result('r1', package))
        self.assertTrue(manager.check()['up_to_date'])
        self.assertFalse(manager.status()['can_download'])
        with self.assertRaisesRegex(RuntimeError, 'already have'):
            manager.download()

    def test_download_errors_are_plain_and_a_retry_works(self):
        attempts = []

        def flaky(url):
            attempts.append(url)
            if len(attempts) == 1:
                raise OSError('offline')
            return io_bytes(self.payload)
        manager = self.manager(transport=flaky)
        manager.check()
        manager.download()
        status = self.wait(manager, 'error')
        self.assertIn('interrupted or is unavailable', status['message'])
        self.assertTrue(status['can_download'])
        manager.download()
        self.wait(manager, 'staged')
        self.assertEqual(os.listdir(self.root / 'staging'), [update_package.LOCK])

    def test_corrupt_download_is_refused_and_leaves_the_installed_version_alone(self):
        manager = self.manager(transport=lambda url: io_bytes(self.payload[:-1] + b'x'))
        manager.check()
        manager.download()
        self.assertIn('digest', self.wait(manager, 'error')['message'])
        self.assertEqual(os.listdir(self.root / 'versions'), [self.current])
        self.assertIsNone(manager.status()['candidate'])

    def test_cancel_stops_a_blocked_download_and_close_is_prompt(self):
        gate = threading.Event()

        class Blocked:
            def read(self, n):
                gate.wait(5)
                return b''
            close = Mock()
        manager = self.manager(transport=lambda url: Blocked())
        manager.check()
        manager.download()
        self.assertTrue(manager.status()['can_cancel'])
        manager.cancel()
        gate.set()
        status = self.wait(manager, 'cancelled')
        self.assertIn('cancelled', status['message'].lower())
        self.assertEqual(os.listdir(self.root / 'versions'), [self.current])
        start = time.monotonic()
        manager.close()
        self.assertLess(time.monotonic() - start, 2)

    def test_apply_is_refused_while_a_world_runs_downloads_run_or_nothing_is_staged(self):
        manager = self.manager()
        with self.assertRaisesRegex(RuntimeError, 'Download an update first'):
            manager.apply(False)
        manager.check()
        manager.download()
        self.wait(manager, 'staged')
        with self.assertRaisesRegex(RuntimeError, 'Save & Quit'):
            manager.apply(True)
        self.assertFalse(manager.status(world_running=True)['can_apply'])
        self.assertFalse(manager.status(world_running=True)['can_download'])
        self.assertFalse((self.root / mi.REQUEST).exists())

    def test_apply_preflight_refuses_orphan_sessions_and_unreadable_save_formats_without_a_request(self):
        manager = self.manager()
        manager.check()
        manager.download()
        self.wait(manager, 'staged')
        profile, save = fx.make_profile(self.home, session=True)
        with self.assertRaisesRegex(RuntimeError, 'earlier session'):
            manager.apply(False)
        (profile / 'session.json').unlink()
        save.write_text('storage_version = 7\naccountName = "Tester"\n')
        with self.assertRaisesRegex(RuntimeError, 'storage version'):
            manager.apply(False)
        self.assertFalse((self.root / mi.REQUEST).exists())

    def test_unmanaged_copies_discover_but_never_install(self):
        manager = um.UpdateManager(None, check=lambda: release_result('r2', self.package))
        self.assertIn('cannot install updates', manager.check()['message'])
        status = manager.status()
        self.assertFalse(status['managed'])
        self.assertFalse(status['can_download'] or status['can_apply'])
        for action in (manager.download, lambda: manager.apply(False)):
            with self.assertRaisesRegex(RuntimeError, 'cannot install updates'):
                action()

    def test_last_apply_result_is_reported_once(self):
        mi.record_result(self.root, False, 'Update not applied: test reason')
        manager = self.manager()
        self.assertEqual(manager.status()['last_result']['message'], 'Update not applied: test reason')
        self.assertIsNone(manager.status()['last_result'])
        self.assertIsNone(self.manager().status()['last_result'])  # not repeated at the next launch


class RealBackend(unittest.TestCase):
    """The real launcher_backend.py started the way the bootstrap starts it, over its stdio JSON protocol."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='backend-'))
        self.addCleanup(self.cleanup)
        self.home = self.tmp / 'profiles'
        self.home.mkdir()
        self.root = self.tmp / 'install'

    def cleanup(self):
        for base, dirs, _ in os.walk(self.tmp):
            for d in dirs:
                os.chmod(Path(base) / d, 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def converse(self, version, requests):
        env = mi.child_environment(self.root, mi.load_config(self.root), {k: v for k, v in os.environ.items() if not k.startswith('SOLOSCAPE_')})
        script = self.root / 'versions' / version / 'scripts' / 'launcher_backend.py'
        result = subprocess.run([sys.executable, '-B', str(script)], env=env, cwd=script.parent.parent, timeout=60,
                                input=''.join(json.dumps(dict(id=i, **r)) + '\n' for i, r in enumerate(requests)),
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return [json.loads(line) for line in result.stdout.splitlines()]

    def test_managed_status_download_guard_and_apply_over_the_real_protocol(self):
        a_path, a_digest, _ = fx.make_real_package(self.tmp, 'r1')
        a = mi.install_first(self.root, a_path, a_digest, self.home, self.tmp / 'cache', self.tmp / 'launcher')
        b_path, b_digest, _ = fx.make_real_package(self.tmp, 'r2')
        b = update_package.install_zip(self.root, b_path, b_digest, expected_release='r2')['id']
        mi.write_candidate(self.root, b, 'r2', b_digest)
        responses = self.converse(a, [{'action': 'update_status'}, {'action': 'update_download'}, {'action': 'update_apply'},
                                      {'action': 'update_cancel'}])
        status, download, apply, cancel = responses
        self.assertEqual(status['result']['installed'], {'release': 'r1', 'id': a})
        self.assertTrue(status['result']['can_apply'])
        self.assertEqual(status['result']['candidate']['release'], 'r2')
        self.assertFalse(download['ok'])
        self.assertIn('Check for updates first', download['error'])
        self.assertTrue(apply['ok'] and apply['result']['restart'])
        self.assertEqual(mi._take_request(self.root), b)
        self.assertTrue(cancel['ok'])
        # The version's own context lives under the external launcher home, not inside the sealed payload.
        self.assertTrue((self.tmp / 'launcher' / 'version-contexts').is_dir())
        self.assertEqual(sorted(p.name for p in (self.root / 'versions' / a).iterdir()), ['scripts', 'soloscape-runtime.json', 'upstream'])

    def test_real_backend_refuses_apply_for_an_orphan_session_record(self):
        a_path, a_digest, _ = fx.make_real_package(self.tmp, 'r1')
        a = mi.install_first(self.root, a_path, a_digest, self.home, self.tmp / 'cache', self.tmp / 'launcher')
        b_path, b_digest, _ = fx.make_real_package(self.tmp, 'r2')
        b = update_package.install_zip(self.root, b_path, b_digest, expected_release='r2')['id']
        mi.write_candidate(self.root, b, 'r2', b_digest)
        fx.make_profile(self.home, session=True)
        (response,) = self.converse(a, [{'action': 'update_apply'}])
        self.assertFalse(response['ok'])
        self.assertIn('earlier session', response['error'])
        self.assertFalse((self.root / mi.REQUEST).exists())


if __name__ == '__main__':
    unittest.main()
