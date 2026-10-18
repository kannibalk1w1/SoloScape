import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest
import zipfile
from pathlib import Path

import managed_fixture as fx
import managed_install as mi
import package_builder
import runtime_manifest
import update_package as up

TAG = 'r2'


class SupplyCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='supply-'))
        self.addCleanup(self.cleanup)
        self.root = self.tmp / 'install'
        for name in ('versions', 'staging'):
            (self.root / name).mkdir(parents=True)
        self.path, self.digest, self.files = fx.make_code_only_package(self.tmp, TAG)
        self.checkout = fx.make_checkout(self.tmp, self.files)

    def cleanup(self):
        for base, dirs, _ in os.walk(self.tmp):
            for d in dirs:
                os.chmod(Path(base) / d, 0o755)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def install(self, roots=None, job=None):
        return up.install_zip(self.root, self.path, self.digest, expected_release=TAG, job=job,
                              supply_roots=[self.checkout] if roots is None else roots)

    def assert_nothing_left(self):
        self.assertEqual(os.listdir(self.root / 'versions'), [])
        self.assertEqual([n for n in os.listdir(self.root / 'staging') if n != up.LOCK], [])

    def refused(self, text, **kw):
        with self.assertRaises(up.PackageError) as caught:
            self.install(**kw)
        self.assertIn(text, str(caught.exception))
        self.assert_nothing_left()

    def writable_copy(self, version):
        copy = Path(tempfile.mkdtemp(prefix='copy-', dir=self.tmp)) / 'version'
        shutil.copytree(self.root / 'versions' / version, copy)
        for base, dirs, names in os.walk(copy):
            for item in dirs + names:
                os.chmod(Path(base) / item, 0o755)
        os.chmod(copy, 0o755)
        return copy


class Package(SupplyCase):
    def test_the_package_carries_no_jar_or_data_bytes(self):
        with zipfile.ZipFile(self.path) as archive:
            names = set(archive.namelist())
        self.assertEqual(names, {runtime_manifest.MANIFEST_NAME} | {p for p in self.files if p not in fx.LOCAL_PATHS})
        self.assertTrue(self.path.stat().st_size < 64 * 1024)
        manifest = json.loads(zipfile.ZipFile(self.path).read(runtime_manifest.MANIFEST_NAME))
        self.assertEqual(manifest['files'][fx.SERVER], {'supply': 'local'})

    def test_scripts_and_the_launcher_cannot_be_left_local(self):
        for victim in ('scripts/launcher.sh', 'scripts/managed_install.py'):
            files = {p: d for p, d in self.files.items() if p not in fx.LOCAL_PATHS and p != victim}
            manifest = package_builder.build_manifest(files, TAG, (0, 1), 'c' * 40, fx.PINS, fx.PATCHES, local=fx.LOCAL_PATHS + (victim,))
            with self.assertRaises(ValueError):
                runtime_manifest.parse(manifest)

    def test_other_local_markers_are_refused(self):
        manifest = json.loads(zipfile.ZipFile(self.path).read(runtime_manifest.MANIFEST_NAME))
        manifest['files'][fx.DATA] = {'supply': 'remote'}
        with self.assertRaises(ValueError):
            runtime_manifest.parse(json.dumps(manifest).encode())
        manifest['files'][fx.DATA] = {'supply': 'local', 'sha256': 'a' * 64, 'size': 1}
        with self.assertRaises(ValueError):
            runtime_manifest.parse(json.dumps(manifest).encode())


class Supplying(SupplyCase):
    def test_a_matching_local_build_supplies_the_jars_and_data(self):
        found = self.install()
        directory = self.root / 'versions' / found['id']
        for path in fx.LOCAL_PATHS:
            self.assertEqual((directory / path).read_bytes(), self.files[path])
            self.assertEqual(stat.S_IMODE((directory / path).stat().st_mode), 0o444)
        record = json.loads((directory / runtime_manifest.SUPPLIED_NAME).read_text())
        self.assertEqual(record['files'][fx.SERVER]['sha256'], hashlib.sha256(self.files[fx.SERVER]).hexdigest())
        manifest, version = runtime_manifest.validate_with_id(directory)
        self.assertEqual(version, found['id'])
        self.assertEqual(runtime_manifest.local_paths(manifest), sorted(fx.LOCAL_PATHS))
        self.assertEqual(sorted(os.listdir(self.checkout / '.runtime')), ['build-stamp.json'])  # the source folder is only read

    def test_the_version_is_independent_of_the_source_folder_afterwards(self):
        found = self.install()
        shutil.rmtree(self.checkout)
        self.assertEqual(runtime_manifest.validate_with_id(self.root / 'versions' / found['id'])[1], found['id'])

    def test_no_registered_build_is_a_plain_instruction(self):
        self.refused('does not include the game programs', roots=[])

    def test_a_build_of_different_patches_or_pins_is_refused_and_named(self):
        for key, value in (('patches', {**fx.PATCHES, 'patches/server/0001-test.patch': 'f' * 64}),
                           ('pins', {**fx.PINS, 'game-server': 'e' * 40})):
            stamp = json.loads((self.checkout / '.runtime/build-stamp.json').read_text())
            stamp[key] = value
            (self.checkout / '.runtime/build-stamp.json').write_text(json.dumps(stamp))
            self.refused('different source than release ' + TAG)

    def test_missing_or_damaged_build_record_is_refused(self):
        stamp = self.checkout / '.runtime/build-stamp.json'
        stamp.write_text('{broken')
        self.refused('no usable local build record')
        stamp.unlink()
        self.refused('no usable local build record')
        stamp.write_text(json.dumps({'pins': fx.PINS, 'patches': fx.PATCHES, 'jars': {'server': 'nope'}}))
        self.refused('not supported')

    def test_a_missing_local_file_names_the_path(self):
        (self.checkout / fx.DATA).unlink()
        self.refused(fx.DATA)

    def test_a_linked_source_file_is_never_followed(self):
        target = self.checkout / fx.SERVER
        outside = self.tmp / 'outside.jar'
        outside.write_bytes(self.files[fx.SERVER])
        target.unlink()
        target.symlink_to(outside)
        self.refused(fx.SERVER)

    def test_a_linked_source_directory_is_never_followed(self):
        data = self.checkout / 'upstream/game-server/data'
        moved = self.tmp / 'moved-data'
        shutil.move(data, moved)
        data.symlink_to(moved)
        self.refused(fx.DATA)

    def test_a_fifo_in_place_of_a_source_file_is_refused_without_blocking(self):
        target = self.checkout / fx.DATA
        target.unlink()
        os.mkfifo(target)
        self.refused(fx.DATA)

    def test_a_jar_that_changed_after_the_build_is_refused(self):
        (self.checkout / fx.CLIENT).write_bytes(b'rebuilt later, stamp not refreshed')
        self.refused('changed after it was built')

    def test_the_second_registered_folder_is_used_when_the_first_does_not_match(self):
        stale = fx.make_checkout(self.tmp, self.files, patches={**fx.PATCHES, 'patches/client/0001-test.patch': 'f' * 64}, name='stale')
        found = self.install(roots=[stale, self.checkout])
        self.assertTrue((self.root / 'versions' / found['id']).is_dir())

    def test_cancelling_while_copying_leaves_nothing(self):
        import threading
        cancel = threading.Event()
        job = up.Job(cancelled=cancel, progress=lambda stage, done, total: cancel.set() if stage == 'copying local build' else None)
        with self.assertRaises(up.Cancelled):
            self.install(job=job)
        self.assert_nothing_left()

    def test_a_source_file_that_grows_while_copied_is_refused(self):
        calls = []
        real = up._open_below

        def growing(source, parts):
            fd = real(source, parts)
            calls.append(parts)
            if len(calls) == len(fx.LOCAL_PATHS) + 1:  # the first copy pass, after every size was recorded
                with open(self.checkout / fx.LOCAL_PATHS[0], 'ab') as handle:
                    handle.write(b'x')
            return fd
        up._open_below = growing
        self.addCleanup(setattr, up, '_open_below', real)
        self.refused('changed while it was being copied')


class Tamper(SupplyCase):
    def setUp(self):
        super().setUp()
        self.version = self.install()['id']
        self.copy = self.writable_copy(self.version)

    def test_untouched_copy_validates(self):
        self.assertEqual(runtime_manifest.validate_with_id(self.copy)[1], self.version)

    def test_an_edited_local_file_is_detected(self):
        (self.copy / fx.SERVER).write_bytes(b'edited')
        with self.assertRaises(ValueError):
            runtime_manifest.validate_with_id(self.copy)

    def test_a_missing_record_is_detected(self):
        (self.copy / runtime_manifest.SUPPLIED_NAME).unlink()
        with self.assertRaises((ValueError, OSError)):
            runtime_manifest.validate_with_id(self.copy)

    def test_a_record_for_other_files_is_detected(self):
        record = json.loads((self.copy / runtime_manifest.SUPPLIED_NAME).read_text())
        record['files']['upstream/game-server/data/extra.toml'] = {'sha256': 'a' * 64, 'size': 1}
        (self.copy / runtime_manifest.SUPPLIED_NAME).write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            runtime_manifest.validate_with_id(self.copy)
        record['files'].pop('upstream/game-server/data/extra.toml')
        record['files'].pop(fx.DATA)
        (self.copy / runtime_manifest.SUPPLIED_NAME).write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            runtime_manifest.validate_with_id(self.copy)

    def test_an_oversized_record_size_is_refused(self):
        record = json.loads((self.copy / runtime_manifest.SUPPLIED_NAME).read_text())
        record['files'][fx.SERVER]['size'] = runtime_manifest.FILE_MAX_BYTES + 1
        (self.copy / runtime_manifest.SUPPLIED_NAME).write_text(json.dumps(record))
        with self.assertRaises(ValueError):
            runtime_manifest.validate_with_id(self.copy)

    def test_a_supplied_record_in_a_fully_released_version_is_an_unlisted_file(self):
        path, digest, _ = fx.make_package(self.tmp, 'r9')
        found = up.install_zip(self.root, path, digest, expected_release='r9')
        copy = self.writable_copy(found['id'])
        (copy / runtime_manifest.SUPPLIED_NAME).write_text('{}')
        with self.assertRaises(ValueError):
            runtime_manifest.validate_with_id(copy)


class BuilderCommand(SupplyCase):
    """checkout_package on a synthetic built source folder (a real git repo for the tracked server data)."""

    def setUp(self):
        super().setUp()
        import subprocess
        import local_dev
        self.built = self.tmp / 'built'
        repo = self.built / 'upstream/game-server'
        (repo / 'data/area').mkdir(parents=True)
        (repo / 'data/area/town.toml').write_text('name = "synthetic town"\n')
        (repo / 'data/area/town.txt').write_text('synthetic\n')
        (repo / 'data/saves').mkdir()
        (repo / 'data/saves/ignored.toml').write_text('state = 1\n')
        subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'add', 'data/area'], check=True)
        for role, content in ((package_builder.SERVER_ROLE, b'synthetic server'), (package_builder.CLIENT_ROLE, b'synthetic client')):
            (self.built / role).parent.mkdir(parents=True, exist_ok=True)
            (self.built / role).write_bytes(content)
        real = Path(package_builder.__file__).resolve().parents[1]
        self.source = self.tmp / 'source'  # a small stand-in source tree: the real scripts, two inert patches, the real selector
        shutil.copytree(real / 'scripts', self.source / 'scripts', ignore=shutil.ignore_patterns('__pycache__', '*.java', 'harness'))
        (self.source / 'experiments/native-prebuilt-server').mkdir(parents=True)
        shutil.copy(real / 'experiments/native-prebuilt-server/runtime_inputs.py', self.source / 'experiments/native-prebuilt-server')
        for side in ('client', 'server'):
            (self.source / 'patches' / side).mkdir(parents=True)
            (self.source / 'patches' / side / '0001-inert.patch').write_text('--- a/README\n+++ b/README\n@@ -1 +1 @@\n-a\n+b\n')
        patches = {p.relative_to(self.source).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted((self.source / 'patches').glob('*/*.patch'))}
        (self.built / '.runtime').mkdir()
        (self.built / '.runtime/build-stamp.json').write_text(json.dumps({
            'format': 1, 'pins': dict(local_dev.PINNED), 'patches': patches,
            'jars': {'server': hashlib.sha256(b'synthetic server').hexdigest(), 'client': hashlib.sha256(b'synthetic client').hexdigest()}}))

    def test_the_package_is_scripts_only_and_installs_from_the_same_build(self):
        out = self.tmp / 'built-package.zip'
        digest = package_builder.checkout_package(self.built, 'local-1', (0, 1), out, source=self.source)
        with zipfile.ZipFile(out) as archive:
            names = set(archive.namelist())
            manifest = json.loads(archive.read(runtime_manifest.MANIFEST_NAME))
        self.assertTrue(all(n == runtime_manifest.MANIFEST_NAME or n.startswith('scripts/') for n in names))
        self.assertEqual(runtime_manifest.local_paths(manifest), sorted([
            package_builder.SERVER_ROLE, package_builder.CLIENT_ROLE, 'upstream/game-server/data/area/town.toml', 'upstream/game-server/data/area/town.txt']))
        found = up.install_zip(self.root, out, digest, expected_release='local-1', supply_roots=[self.built])
        directory = self.root / 'versions' / found['id']
        self.assertEqual((directory / package_builder.SERVER_ROLE).read_bytes(), b'synthetic server')
        self.assertFalse((directory / 'upstream/game-server/data/saves').exists())

    def test_a_build_made_from_other_patches_is_not_packaged(self):
        stamp = json.loads((self.built / '.runtime/build-stamp.json').read_text())
        stamp['patches']['patches/server/0001-x.patch'] = 'f' * 64
        (self.built / '.runtime/build-stamp.json').write_text(json.dumps(stamp))
        with self.assertRaises(ValueError):
            package_builder.checkout_package(self.built, 'local-1', (0, 1), self.tmp / 'nope.zip', source=self.source)
        self.assertFalse((self.tmp / 'nope.zip').exists())


class ThroughTheInstaller(SupplyCase):
    def setUp(self):
        super().setUp()
        shutil.rmtree(self.root)
        self.home = self.tmp / 'profiles'
        self.home.mkdir()

    def first(self, **kw):
        return mi.install_first(self.root, self.path, self.digest, self.home, self.tmp / 'cache', self.tmp / 'launcher',
                                supply_roots=[self.checkout], **kw)

    def test_first_install_registers_the_source_folder_and_launches_from_the_copies(self):
        version = self.first()
        self.assertEqual(mi.load_config(self.root)['supply_roots'], [str(self.checkout)])
        self.assertEqual(mi.identity(self.root)['id'], version)
        self.assertEqual((self.root / 'versions' / version / fx.SERVER).read_bytes(), self.files[fx.SERVER])

    def test_first_install_without_a_build_leaves_no_install(self):
        with self.assertRaises(up.PackageError):
            mi.install_first(self.root, self.path, self.digest, self.home, self.tmp / 'cache', self.tmp / 'launcher')
        self.assertFalse(os.path.lexists(self.root / mi.POINTER))

    def test_registered_folders_are_replaced_only_under_the_exclusive_lease(self):
        self.first()
        other = self.tmp / 'other'
        self.assertEqual(mi.set_supply_roots(self.root, [other]), [str(other)])
        self.assertEqual(mi.load_config(self.root)['supply_roots'], [str(other)])
        with mi.acquire(self.root, 'shared'):
            with self.assertRaises(mi.Busy):
                mi.set_supply_roots(self.root, [])
        mi.set_supply_roots(self.root, [])
        self.assertNotIn('supply_roots', mi.load_config(self.root))

    def test_relative_or_excessive_folders_are_refused(self):
        self.first()
        with self.assertRaises(mi.InstallError):
            mi.set_supply_roots(self.root, ['relative'])
        with self.assertRaises(mi.InstallError):
            mi.set_supply_roots(self.root, ['/a', '/b', '/c', '/d', '/e'])

    def test_an_update_with_local_files_activates_and_rolls_back_over_the_same_saves(self):
        first = self.first()
        _, saves = fx.make_profile(self.home, storage_version=1)
        before = saves.read_bytes()
        path, digest, files2 = fx.make_code_only_package(self.tmp, 'r3')
        checkout = fx.make_checkout(self.tmp, files2, name='checkout2')
        mi.set_supply_roots(self.root, [checkout])
        second = up.install_zip(self.root, path, digest, expected_release='r3', supply_roots=mi.load_config(self.root)['supply_roots'])['id']
        mi.activate(self.root, second)
        self.assertEqual(mi.identity(self.root)['release'], 'r3')
        mi.rollback(self.root)
        self.assertEqual(mi.identity(self.root)['id'], first)
        self.assertEqual(saves.read_bytes(), before)

    def test_pruning_keeps_what_the_two_kept_versions_hold(self):
        first = self.first()
        path, digest, files2 = fx.make_code_only_package(self.tmp, 'r3')
        checkout = fx.make_checkout(self.tmp, files2, name='checkout2')
        second = up.install_zip(self.root, path, digest, expected_release='r3', supply_roots=[checkout])['id']
        mi.activate(self.root, second)
        for version in (first, second):
            mi.verify_version(self.root, version)


if __name__ == '__main__':
    unittest.main()
