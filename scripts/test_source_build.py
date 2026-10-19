import os
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from pathlib import Path

import managed_fixture as fx
import managed_install as mi
import release_updates
import source_build as sb
import source_fixture as sf
import update_manager as um
import update_package as up

from test_migration_support import snapshot  # noqa: E402


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


class SourceCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='srcbuild-'))
        self.addCleanup(self.cleanup)
        self.source = sf.Source(self.tmp)
        self.player = self.source.player_folder(self.tmp)
        self.root = self.tmp / 'install'
        self.root.mkdir()
        self.cache = self.tmp / 'cache'
        self.cache.mkdir()
        self.config = {'cache_home': str(self.cache), 'server_java': '/opt/jdk21/bin/java', 'client_java': '/opt/jdk8/bin/java'}
        self.environ = {'PATH': os.environ['PATH'], 'FAKE_BUILD_SRC': str(self.source.build_output),
                        'SOLOSCAPE_PROFILE_HOME': '/never/passed', 'SOLOSCAPE_MANAGED_ROOT': '/never/passed',
                        'SOLOSCAPE_LAUNCHER_HOME': '/never/passed'}
        origins = {'SoloScape': str(self.source.origin), **{name: str(repo) for name, repo in self.source.upstream.items()}}
        self.patch(sb, 'ORIGINS', origins)
        self.patch(sb, 'ALLOWED_PROTOCOLS', 'file')

    def patch(self, module, name, value):
        old = getattr(module, name)
        setattr(module, name, value)
        self.addCleanup(setattr, module, name, old)

    def cleanup(self):
        for base, dirs, _ in os.walk(self.tmp):
            for d in dirs:
                os.chmod(Path(base) / d, 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self, manifest=None, job=None, folders=None, environ=None, progress=None):
        manifest = manifest or self.source.manifest()[0]
        return sb.build_workspace(self.root, manifest, self.config, [str(self.player)] if folders is None else folders,
                                  job or up.Job(deadline=60), progress=progress, environ=environ or self.environ)

    def refused(self, code, text, **kw):
        with self.assertRaises(sb.BuildError) as caught:
            self.build(**kw)
        self.assertEqual(caught.exception.code, code)
        self.assertIn(text, str(caught.exception))
        self.assert_clean()

    def assert_clean(self):
        base = self.root / sb.BUILDS
        left = [n for n in os.listdir(base) if n.startswith('.work-')] if base.is_dir() else []
        self.assertEqual(left, [])
        self.assertEqual(sb.built_workspaces(self.root), [])


class Building(SourceCase):
    def test_the_exact_declared_source_is_fetched_verified_built_and_the_players_folder_is_untouched(self):
        before = snapshot(self.player)
        stages = []
        built = self.build(progress=lambda stage, detail='': stages.append((stage, detail)))
        self.assertEqual(built, self.root / sb.BUILDS / self.source.commit[:12])
        self.assertEqual(sb.built_workspaces(self.root), [built])
        for path in fx.LOCAL_PATHS:
            self.assertEqual((built / path).read_bytes(), self.source.files[path])
        self.assertEqual(snapshot(self.player), before)  # no checkout, reset, stash, clean or write in the player's folder
        names = [s for s, _ in stages]
        self.assertEqual(names[:3], ['fetching source', 'verifying source', 'fetching source'])
        self.assertIn(('building', 'game:compileKotlin'), stages)
        self.assertEqual(sf.git(built, 'rev-parse', 'HEAD'), self.source.commit)
        self.assertEqual(sf.git(built / 'upstream/game-server', 'rev-parse', 'HEAD'), self.source.pins['game-server'])

    def test_the_build_gets_only_local_inputs_and_none_of_the_launchers_session_settings(self):
        built = self.build()
        env = dict(line.split('=', 1) for line in (built / '.build-env.txt').read_text().splitlines() if '=' in line)
        self.assertEqual(env['SOLOSCAPE_CACHE_HOME'], str(self.cache))
        self.assertEqual(env['SERVER_JAVA'], '/opt/jdk21/bin/java')
        self.assertNotIn('SOLOSCAPE_PROFILE_HOME', env)
        self.assertNotIn('SOLOSCAPE_MANAGED_ROOT', env)
        self.assertNotIn('SOLOSCAPE_LAUNCHER_HOME', env)
        self.assertTrue(Path((built / '.build-cwd.txt').read_text().strip()).resolve().is_relative_to((self.root / sb.BUILDS).resolve()))
        self.assertTrue((self.root / sb.BUILDS / sb.GRADLE_HOME / 'caches/modules.bin').is_file())
        self.assertIn('org.gradle.offline=true', (self.root / sb.BUILDS / sb.GRADLE_HOME / 'gradle.properties').read_text())

    def test_upstream_pins_come_from_the_fixed_origin_when_no_folder_has_them(self):
        only_cache = self.tmp / 'only-cache'
        (only_cache / '.gradle').mkdir(parents=True)
        (only_cache / '.gradle/modules.bin').write_bytes(b'x')
        built = self.build(folders=[str(only_cache)])
        self.assertEqual(sf.git(built / 'upstream/runelite-client', 'rev-parse', 'HEAD'), self.source.pins['runelite-client'])

    def test_a_previous_workspace_is_replaced_and_one_is_kept(self):
        self.build()
        other = self.source.manifest(commit=self.source.commit)[0]
        (self.root / sb.BUILDS / 'aaaaaaaaaaaa').mkdir()
        shutil.copytree(self.root / sb.BUILDS / self.source.commit[:12] / '.runtime', self.root / sb.BUILDS / 'aaaaaaaaaaaa/.runtime')
        os.utime(self.root / sb.BUILDS / 'aaaaaaaaaaaa', (1, 1))
        self.build(manifest=other)
        self.assertEqual([p.name for p in sb.built_workspaces(self.root)], [self.source.commit[:12]])


class Refusals(SourceCase):
    def test_a_release_that_names_no_source_commit_cannot_be_rebuilt(self):
        self.refused('no-source', 'does not name the exact source', manifest=self.source.manifest(commit='0' * 40)[0])

    def test_a_commit_the_project_does_not_have_is_unavailable_and_nothing_is_built(self):
        self.refused('source-unavailable', 'Could not fetch release source', manifest=self.source.manifest(commit='1' * 40)[0])

    def test_source_with_other_pins_is_refused_before_building(self):
        wrong = {**self.source.pins, 'game-server': 'e' * 40}
        self.refused('source-mismatch', 'pinned upstream commits differ', manifest=self.source.manifest(pins=wrong)[0])
        self.assertFalse(any(self.root.rglob('.build-env.txt')))

    def test_source_with_other_patches_is_refused_before_building(self):
        wrong = {**self.source.patches(), 'patches/server/0001-fixture.patch': 'f' * 64}
        self.refused('source-mismatch', 'patches/server/0001-fixture.patch', manifest=self.source.manifest(patches=wrong)[0])

    def test_a_released_script_or_build_entrypoint_that_differs_is_refused(self):
        for victim in ('scripts/managed_install.py', 'scripts/prepare-build.sh'):
            released = dict(self.source.released)
            released[victim] = b'# not what the source commit holds\n'
            self.refused('source-mismatch', victim, manifest=self.source.manifest(released=released)[0])

    def test_a_source_with_a_symbolic_link_is_never_built(self):
        origin = self.source.origin
        (origin / 'danger').symlink_to('/etc/passwd')
        commit = sf.commit_all(origin)
        self.refused('source-mismatch', 'link or submodule', manifest=self.source.manifest(commit=commit)[0])

    def test_missing_jdks_are_a_plain_prerequisite(self):
        self.config.pop('server_java')
        self.refused('no-tools', 'JDK', environ={'PATH': os.environ['PATH']})

    def test_no_dependency_cache_is_a_plain_prerequisite(self):
        shutil.rmtree(self.player / '.gradle')
        self.refused('no-tools', 'Gradle dependency cache')
        self.assertFalse((self.root / sb.BUILDS / sb.GRADLE_HOME).exists())

    def test_a_failed_build_keeps_the_log_and_says_why(self):
        environ = dict(self.environ, FAKE_FAIL='disk full')
        with self.assertRaises(sb.BuildError) as caught:
            self.build(environ=environ)
        self.assertEqual(caught.exception.code, 'build-failed')
        self.assertIn('boom: disk full', str(caught.exception))
        self.assertIn('boom: disk full', (self.root / sb.BUILDS / sb.LOG).read_text())
        self.assert_clean()

    def test_a_finished_build_that_does_not_match_the_release_is_not_used(self):
        stamp = self.source.build_output / '.runtime/build-stamp.json'
        text = stamp.read_text().replace(self.source.pins['game-server'], 'd' * 40)
        stamp.write_text(text)
        self.refused('build-failed', 'does not match the release')


class Cancelling(SourceCase):
    def test_cancel_stops_only_the_owned_build_and_removes_the_workspace(self):
        sentinel = subprocess.Popen(['sleep', '120'], start_new_session=True)
        self.addCleanup(sentinel.kill)
        pid_file = self.tmp / 'build.pid'
        environ = dict(self.environ, FAKE_SLEEP='120', FAKE_PID_FILE=str(pid_file))
        cancel = threading.Event()
        errors = []

        def run():
            try:
                self.build(job=up.Job(cancelled=cancel, deadline=300), environ=environ)
            except BaseException as exc:
                errors.append(exc)
        worker = threading.Thread(target=run)
        worker.start()
        end = time.monotonic() + 30
        while not pid_file.exists() and time.monotonic() < end:
            time.sleep(0.05)
        pid = int(pid_file.read_text())
        self.assertTrue(alive(pid))
        cancel.set()
        worker.join(30)
        self.assertFalse(worker.is_alive())
        self.assertIsInstance(errors[0], up.Cancelled)
        time.sleep(0.3)
        self.assertFalse(alive(pid))  # the owned build's descendants are gone
        self.assertTrue(alive(sentinel.pid))  # an unrelated process is not
        self.assert_clean()

    def test_the_whole_job_deadline_ends_a_build_that_never_finishes(self):
        environ = dict(self.environ, FAKE_SLEEP='120', FAKE_PID_FILE=str(self.tmp / 'd.pid'))
        started = time.monotonic()
        with self.assertRaises(up.PackageError) as caught:
            self.build(job=up.Job(deadline=1.5), environ=environ)
        self.assertLess(time.monotonic() - started, 20)
        self.assertIn('took too long', str(caught.exception))
        self.assert_clean()


class Manager(SourceCase):
    """The whole flow through the production UpdateManager: refuse, rebuild on request, stage, then install."""

    def setUp(self):
        super().setUp()
        shutil.rmtree(self.root)
        self.home = self.tmp / 'profiles'
        self.home.mkdir()
        first_path, first_digest, self.first_files = fx.make_code_only_package(self.tmp, 'r1')
        first_checkout = fx.make_checkout(self.tmp, self.first_files, name='first-build')
        self.current = mi.install_first(self.root, first_path, first_digest, self.home, self.cache, self.tmp / 'launcher',
                                        supply_roots=[first_checkout], server_java='/opt/jdk21/bin/java', client_java='/opt/jdk8/bin/java')
        self.config = mi.load_config(self.root)
        old = fx.make_checkout(self.tmp, self.first_files, name='unused')
        shutil.copy(old / '.runtime/build-stamp.json', self.player / '.runtime/build-stamp.json') if (self.player / '.runtime').is_dir() else None
        (self.player / '.runtime').mkdir(exist_ok=True)
        shutil.copy(old / '.runtime/build-stamp.json', self.player / '.runtime/build-stamp.json')
        mi.set_supply_roots(self.root, [self.player])
        os.environ['SOLOSCAPE_MANAGED_ROOT'] = str(self.root)
        self.addCleanup(os.environ.pop, 'SOLOSCAPE_MANAGED_ROOT', None)
        for key, value in self.environ.items():
            if key.startswith('FAKE_') or key == 'PATH':
                os.environ[key] = value
                self.addCleanup(os.environ.pop, key, None) if key.startswith('FAKE_') else None
        self.zip_path, digest = self.source.package(self.tmp)
        size = self.zip_path.stat().st_size
        package = dict(name='soloscape-package-r2.zip', size=size, sha256=digest, tag='r2',
                       url=release_updates.asset_url('r2', 'soloscape-package-r2.zip'))
        self.release = release_updates.result('release_available', 'Published release: r2.', tag='r2', title='r2', notes='n', bundle=None,
                                              package=package, url='https://github.com/kannibalk1w1/SoloScape/releases/tag/r2') | {'install_available': True}
        self.managed = {'release': 'r1', 'version': self.current, 'storage_versions': [0, 1]}

    def manager(self):
        return um.UpdateManager(self.managed, transport=lambda url: open(self.zip_path, 'rb'), check=lambda: self.release)

    def wait(self, manager, stages, seconds=60):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            status = manager.status()
            if status['stage'] in stages and not status['can_cancel']:
                return status
            time.sleep(0.05)
        self.fail('never reached %s: %s' % (stages, manager.status()))

    def test_refuse_then_rebuild_on_request_then_stage_and_install(self):
        before = snapshot(self.player)
        manager = self.manager()
        manager.check()
        manager.download()
        refused = self.wait(manager, ('error',))
        self.assertEqual(refused['needs_build'], 'needs-rebuild')  # the registered folder holds an older build
        self.assertTrue(refused['can_rebuild'])
        manager.rebuild()
        staged = self.wait(manager, ('staged', 'error'))
        self.assertEqual(staged['stage'], 'staged', staged['message'])
        self.assertTrue(staged['can_apply'])
        self.assertFalse(staged['can_rebuild'])
        version = self.root / 'versions' / staged['candidate']['id']
        self.assertEqual((version / fx.SERVER).read_bytes(), self.source.files[fx.SERVER])
        self.assertEqual(snapshot(self.player), before)
        # a later Download of the same release reuses the finished workspace and needs no second rebuild
        self.assertEqual(mi.preflight(self.root, staged['candidate']['id']), [])

    def test_rebuild_is_only_offered_after_a_refusal_and_never_while_a_world_runs(self):
        manager = self.manager()
        manager.check()
        self.assertFalse(manager.status()['can_rebuild'])
        manager.download()
        self.wait(manager, ('error',))
        self.assertTrue(manager.status()['can_rebuild'])
        self.assertFalse(manager.status(world_running=True)['can_rebuild'])

    def test_a_declared_source_that_does_not_match_cannot_be_retried(self):
        self.release['package']['tag'] = 'r2'
        wrong = self.source.manifest(pins={**self.source.pins, 'game-server': 'e' * 40})
        path = self.tmp / 'wrong.zip'
        released = self.source.released
        digest = up.hashlib.sha256()
        import package_builder
        package_builder.write_zip(released, wrong[1], path)
        digest = up.hashlib.sha256(path.read_bytes()).hexdigest()
        self.zip_path = path
        self.release['package'].update(size=path.stat().st_size, sha256=digest)
        manager = self.manager()
        manager.check()
        manager.rebuild()
        status = self.wait(manager, ('error',))
        self.assertEqual(status['needs_build'], 'source-mismatch')
        self.assertFalse(status['can_rebuild'])
        self.assertEqual(os.listdir(self.root / 'versions'), [self.current])

    def test_cancelling_a_rebuild_leaves_the_installed_version_and_no_workspace(self):
        os.environ['FAKE_SLEEP'] = '120'
        os.environ['FAKE_PID_FILE'] = str(self.tmp / 'm.pid')
        self.addCleanup(os.environ.pop, 'FAKE_SLEEP', None)
        self.addCleanup(os.environ.pop, 'FAKE_PID_FILE', None)
        manager = self.manager()
        manager.check()
        manager.rebuild()
        end = time.monotonic() + 30
        while not (self.tmp / 'm.pid').exists() and time.monotonic() < end:
            time.sleep(0.05)
        pid = int((self.tmp / 'm.pid').read_text())
        manager.cancel()
        status = self.wait(manager, ('cancelled',))
        time.sleep(0.3)
        self.assertFalse(alive(pid))
        self.assertEqual(os.listdir(self.root / 'versions'), [self.current])
        self.assertEqual(sb.built_workspaces(self.root), [])
        self.assertEqual(status['stage'], 'cancelled')

    def test_closing_the_backend_during_a_rebuild_stops_the_owned_build_promptly(self):
        os.environ['FAKE_SLEEP'] = '120'
        os.environ['FAKE_PID_FILE'] = str(self.tmp / 'c.pid')
        self.addCleanup(os.environ.pop, 'FAKE_SLEEP', None)
        self.addCleanup(os.environ.pop, 'FAKE_PID_FILE', None)
        manager = self.manager()
        manager.check()
        manager.rebuild()
        end = time.monotonic() + 30
        while not (self.tmp / 'c.pid').exists() and time.monotonic() < end:
            time.sleep(0.05)
        pid = int((self.tmp / 'c.pid').read_text())
        started = time.monotonic()
        manager.close()
        self.assertLess(time.monotonic() - started, 15)
        time.sleep(0.3)
        self.assertFalse(alive(pid))
        self.assertEqual(os.listdir(self.root / 'versions'), [self.current])


if __name__ == '__main__':
    unittest.main()
